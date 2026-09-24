import copy
import fcntl
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import orch


def proof(head_sha="head-1", stack_fingerprint=None, passed=True, policy_digest=None):
    result = {
        "head_sha": head_sha,
        "stack_fingerprint": stack_fingerprint,
        "passed": passed,
    }
    if policy_digest is not None:
        result["policy_digest"] = policy_digest
    return result


def issue(number=1, priority="P1", dependencies=None, claimed=False, created_at=None, state="open"):
    return {
        "number": number,
        "priority": priority,
        "dependencies": dependencies or [],
        "claimed": claimed,
        "created_at": created_at or f"2026-01-{number:02d}T00:00:00Z",
        "state": state,
    }


def pull_request(
    number=101,
    issue_number=1,
    state="open",
    draft=False,
    head_sha="head-1",
    base_ref="main",
    parent_pr=None,
    parent_head_sha=None,
    checks=None,
    findings=None,
    review_proofs=None,
    test_proofs=None,
    ready=False,
):
    fingerprint = orch.stack_fingerprint(base_ref, parent_pr, parent_head_sha)
    return {
        "number": number,
        "issue_number": issue_number,
        "state": state,
        "draft": draft,
        "head_sha": head_sha,
        "base_ref": base_ref,
        "parent_pr": parent_pr,
        "parent_head_sha": parent_head_sha,
        "checks": checks if checks is not None else [{"name": "ci", "status": "success"}],
        "findings": findings or [],
        "review_proofs": review_proofs if review_proofs is not None else [proof(head_sha, fingerprint)],
        "test_proofs": test_proofs if test_proofs is not None else [proof(head_sha, fingerprint)],
        "ready": ready,
    }


def snapshot(issues=None, pull_requests=None):
    return {
        "version": 1,
        "repository": "example/project",
        "issues": issues or [],
        "pull_requests": pull_requests or [],
    }


class OrchestratorTests(unittest.TestCase):
    def reconcile(self, snapshot_data, old=None):
        normalized = orch.parse_snapshot(snapshot_data)
        return orch.reconcile(old or orch.ProgramState.empty(normalized.repository), normalized)

    def test_duplicate_next_ticks_keep_same_reserved_action(self):
        state = self.reconcile(snapshot([issue()]))

        first = orch.reserve_next_action(state)
        second = orch.reserve_next_action(first)

        self.assertEqual(first.pending_action, second.pending_action)
        self.assertEqual("claim_issue", first.pending_action.kind)

    def test_claim_reservation_survives_reload_and_advances_when_observed(self):
        state = orch.reserve_next_action(self.reconcile(snapshot([issue()])))

        reloaded = orch.ProgramState.from_dict(state.to_dict())
        self.assertEqual(state.pending_action, orch.reserve_next_action(reloaded).pending_action)

        claimed_snapshot = snapshot([issue(claimed=True)])
        reconciled = self.reconcile(claimed_snapshot, reloaded)
        advanced = orch.reserve_next_action(reconciled)
        self.assertEqual("implement_issue", advanced.pending_action.kind)
        self.assertNotEqual(state.pending_action.action_id, advanced.pending_action.action_id)

    def test_new_head_sha_invalidates_old_review_and_test_proof(self):
        old_pr = pull_request()
        state = self.reconcile(snapshot([issue(claimed=True)], [old_pr]))
        self.assertTrue(orch.ready_check(state, 101).ready)

        changed = copy.deepcopy(old_pr)
        changed["head_sha"] = "head-2"
        changed["review_proofs"] = old_pr["review_proofs"]
        changed["test_proofs"] = old_pr["test_proofs"]
        state = self.reconcile(snapshot([issue(claimed=True)], [changed]), state)

        verdict = orch.ready_check(state, 101)
        self.assertFalse(verdict.ready)
        self.assertIn("missing_review_proof", verdict.reasons)
        self.assertIn("missing_test_proof", verdict.reasons)

    def test_only_unresolved_p0_and_p1_findings_block(self):
        blocking = [
            {"severity": "P0", "resolved": False},
            {"severity": "P1", "resolved": False},
            {"severity": "P2", "resolved": False},
        ]
        state = self.reconcile(snapshot([issue(claimed=True)], [pull_request(findings=blocking)]))
        self.assertIn("unresolved_p0_p1", orch.ready_check(state, 101).reasons)

        nonblocking = [
            {"severity": "P2", "resolved": False},
            {"severity": "P3", "resolved": False},
        ]
        state = self.reconcile(snapshot([issue(claimed=True)], [pull_request(findings=nonblocking)]), state)
        self.assertTrue(orch.ready_check(state, 101).ready)

    def test_stack_identity_changes_invalidate_proof(self):
        variants = [
            {"base_ref": "release", "parent_pr": None, "parent_head_sha": None},
            {"base_ref": "main", "parent_pr": 100, "parent_head_sha": "parent-1"},
            {"base_ref": "main", "parent_pr": 100, "parent_head_sha": "parent-2"},
        ]
        for changes in variants:
            with self.subTest(changes=changes):
                original = pull_request()
                changed = pull_request(**changes)
                changed["review_proofs"] = original["review_proofs"]
                changed["test_proofs"] = original["test_proofs"]
                prs = [changed]
                if changes["parent_pr"]:
                    prs.append(pull_request(number=100, issue_number=2, head_sha=changes["parent_head_sha"]))
                state = self.reconcile(snapshot([issue(claimed=True), issue(number=2, claimed=True)], prs))
                verdict = orch.ready_check(state, 101)
                self.assertFalse(verdict.ready)
                self.assertIn("missing_review_proof", verdict.reasons)
                self.assertIn("missing_test_proof", verdict.reasons)

    def test_snapshot_order_does_not_change_action_selection(self):
        issues = [
            issue(number=9, priority="P1", created_at="2026-01-01T00:00:00Z"),
            issue(number=3, priority="P0", created_at="2026-01-03T00:00:00Z"),
            issue(number=2, priority="P0", dependencies=[99], created_at="2026-01-01T00:00:00Z"),
        ]
        first = orch.reserve_next_action(self.reconcile(snapshot(issues))).pending_action
        second = orch.reserve_next_action(self.reconcile(snapshot(list(reversed(issues))))).pending_action
        self.assertEqual(first, second)
        self.assertEqual(3, first.issue_number)

    def test_ready_check_fails_closed_for_each_required_gate(self):
        parent = pull_request(number=100, issue_number=2, head_sha="parent-1")
        cases = {
            "draft": (pull_request(draft=True), "draft"),
            "failing_checks": (pull_request(checks=[{"name": "ci", "status": "failure"}]), "checks_not_successful"),
            "missing_checks": (pull_request(checks=[]), "checks_not_successful"),
            "missing_review": (pull_request(review_proofs=[]), "missing_review_proof"),
            "missing_test": (pull_request(test_proofs=[]), "missing_test_proof"),
            "missing_parent": (pull_request(parent_pr=100, parent_head_sha="parent-1"), "invalid_stack_parent"),
            "changed_parent": (
                pull_request(parent_pr=100, parent_head_sha="stale-parent"),
                "invalid_stack_parent",
            ),
        }
        for name, (pr, reason) in cases.items():
            with self.subTest(name=name):
                prs = [pr]
                if name == "changed_parent":
                    prs.append(parent)
                state = self.reconcile(snapshot([issue(claimed=True), issue(number=2, claimed=True)], prs))
                verdict = orch.ready_check(state, 101)
                self.assertFalse(verdict.ready)
                self.assertIn(reason, verdict.reasons)

    def test_planner_prefers_active_pr_over_historical_merge(self):
        active = pull_request(number=102, review_proofs=[])
        historical = pull_request(number=101, state="merged")
        state = self.reconcile(snapshot([issue(claimed=True)], [historical, active]))

        action = orch.reserve_next_action(state).pending_action

        self.assertEqual("review_pr", action.kind)
        self.assertEqual(102, action.pr_number)

    def test_planner_never_marks_draft_or_invalid_stack_ready(self):
        draft_state = self.reconcile(snapshot([issue(claimed=True)], [pull_request(draft=True)]))
        draft_action = orch.reserve_next_action(draft_state).pending_action
        self.assertEqual("implement_issue", draft_action.kind)

        child = pull_request(parent_pr=100, parent_head_sha="missing-parent")
        invalid_parent_state = self.reconcile(snapshot([issue(claimed=True)], [child]))
        parent_action = orch.reserve_next_action(invalid_parent_state).pending_action
        self.assertEqual("wait", parent_action.kind)
        self.assertEqual(101, parent_action.pr_number)

    def test_boundary_validation_and_cli_exit_codes(self):
        with self.assertRaisesRegex(orch.BoundaryError, "priority"):
            orch.parse_snapshot(snapshot([issue(priority="urgent")]))

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory)
            snapshot_path = root / "snapshot.json"
            state_path = root / "state.json"
            snapshot_path.write_text(json.dumps(snapshot([issue(claimed=True)], [pull_request(draft=True)])))
            reconcile_result = subprocess.run(
                [str(HERE / "orch"), "reconcile", "--snapshot", str(snapshot_path), "--state", str(state_path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, reconcile_result.returncode, reconcile_result.stderr)

            not_ready = subprocess.run(
                [str(HERE / "orch"), "ready-check", "--pr", "101", "--state", str(state_path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(1, not_ready.returncode)
            self.assertEqual(False, json.loads(not_ready.stdout)["ready"])

            invalid_path = root / "invalid.json"
            invalid_path.write_text("{}")
            invalid = subprocess.run(
                [str(HERE / "orch"), "reconcile", "--snapshot", str(invalid_path), "--state", str(state_path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, invalid.returncode)
            self.assertIn("error", json.loads(invalid.stderr))

    def test_emit_pretty_prints_for_terminal_and_stays_compact_for_pipes(self):
        class TerminalBuffer(io.StringIO):
            def isatty(self):
                return True

        terminal = TerminalBuffer()
        pipe = io.StringIO()

        orch._emit({"b": 2, "a": 1}, terminal)
        orch._emit({"b": 2, "a": 1}, pipe)

        self.assertEqual('{\n  "a": 1,\n  "b": 2\n}\n', terminal.getvalue())
        self.assertEqual('{"a": 1, "b": 2}\n', pipe.getvalue())


class FakeGhRunner:
    def __init__(self, responses=None, error=None):
        self.responses = responses or {}
        self.error = error
        self.calls = []

    def __call__(self, argv):
        self.calls.append(argv)
        if self.error is not None:
            raise orch.GhCommandError(self.error)
        return json.dumps(self.responses.get(tuple(argv)))


def github_issue(number=1, labels=None, blocked_by=None):
    return {
        "number": number,
        "createdAt": f"2026-02-{number:02d}T00:00:00Z",
        "state": "OPEN",
        "labels": [{"name": label} for label in (labels or ["priority:p1"])],
        "blockedBy": [{"number": dependency} for dependency in (blocked_by or [])],
    }


def github_pr(number=101, issue_number=1, head="head-1", head_ref="ticket-1", base_ref="main", labels=None, state="OPEN"):
    return {
        "number": number,
        "state": state,
        "isDraft": False,
        "headRefOid": head,
        "headRefName": head_ref,
        "baseRefName": base_ref,
        "closingIssuesReferences": [{"number": issue_number}],
        "labels": [{"name": label} for label in (labels or [])],
        "statusCheckRollup": [
            {"__typename": "CheckRun", "name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS"}
        ],
    }


class LiveGitHubSliceTests(unittest.TestCase):
    def github_runner(self, issues=None, prs=None, comments=None):
        repo = "example/project"
        responses = {
            tuple(orch.GitHubAdapter.repo_argv(repo)): {
                "nameWithOwner": repo,
                "defaultBranchRef": {"name": "main"},
            },
            tuple(orch.GitHubAdapter.issue_argv(repo)): issues or [],
            tuple(orch.GitHubAdapter.pr_argv(repo)): prs or [],
        }
        for pr_number, bodies in (comments or {}).items():
            responses[tuple(orch.GitHubAdapter.comment_argv(repo, pr_number))] = [
                {"body": body, "author_association": "OWNER"} for body in bodies
            ]
        return FakeGhRunner(responses)

    def test_live_snapshot_uses_exact_gh_argv_and_normalizes_stack_and_comments(self):
        parent = github_pr(number=100, issue_number=2, head="parent-head", head_ref="stack-parent")
        child = github_pr(base_ref="stack-parent", labels=["READY-FOR-MERGE"])
        fingerprint = orch.stack_fingerprint("stack-parent", 100, "parent-head")
        proof_marker = orch.proof_marker("review", "action-1", "head-1", fingerprint, True)
        finding_marker = '<!-- orch-finding:{"resolved":false,"severity":"P1"} -->'
        runner = self.github_runner(
            issues=[github_issue(labels=["priority:p0", "agent:claimed"], blocked_by=[2]), github_issue(number=2)],
            prs=[child, parent],
            comments={101: [proof_marker, finding_marker, "[P0] ordinary prose is untrusted"], 100: []},
        )

        result = orch.GitHubAdapter(runner).snapshot("example/project")

        self.assertEqual(
            [
                orch.GitHubAdapter.repo_argv("example/project"),
                orch.GitHubAdapter.issue_argv("example/project"),
                orch.GitHubAdapter.pr_argv("example/project"),
                orch.GitHubAdapter.comment_argv("example/project", 100),
                orch.GitHubAdapter.comment_argv("example/project", 101),
            ],
            runner.calls,
        )
        issue_one = next(item for item in result.issues if item.number == 1)
        child_pr = next(item for item in result.pull_requests if item.number == 101)
        self.assertEqual((2,), issue_one.dependencies)
        self.assertEqual("P0", issue_one.priority)
        self.assertTrue(issue_one.claimed)
        self.assertEqual(100, child_pr.parent_pr)
        self.assertEqual("parent-head", child_pr.parent_head_sha)
        self.assertTrue(child_pr.ready)
        self.assertEqual((orch.FindingSnapshot("P1", False),), child_pr.findings)
        self.assertEqual((orch.ProofReceipt("head-1", fingerprint, True),), child_pr.review_proofs)

    def test_live_snapshot_fetches_comments_only_for_open_single_issue_prs(self):
        open_pr = github_pr()
        closed_pr = github_pr(number=102, issue_number=2, head_ref="ticket-2", state="MERGED")
        unmanaged = github_pr(number=103, issue_number=3, head_ref="ticket-3")
        unmanaged["closingIssuesReferences"] = []
        runner = self.github_runner(
            issues=[github_issue(), github_issue(number=2), github_issue(number=3)],
            prs=[closed_pr, unmanaged, open_pr],
            comments={101: []},
        )

        orch.GitHubAdapter(runner).snapshot("example/project")

        self.assertEqual(
            [
                orch.GitHubAdapter.repo_argv("example/project"),
                orch.GitHubAdapter.issue_argv("example/project"),
                orch.GitHubAdapter.pr_argv("example/project"),
                orch.GitHubAdapter.comment_argv("example/project", 101),
            ],
            runner.calls,
        )

    def test_live_snapshot_treats_null_blocked_by_as_no_dependencies(self):
        raw_issue = github_issue()
        raw_issue["blockedBy"] = None
        runner = self.github_runner(issues=[raw_issue])

        result = orch.GitHubAdapter(runner).snapshot("example/project")

        self.assertEqual((), result.issues[0].dependencies)

    def test_live_snapshot_reads_blocked_by_connection(self):
        raw_issue = github_issue()
        raw_issue["blockedBy"] = {"nodes": [{"number": 2}], "totalCount": 1}
        runner = self.github_runner(issues=[raw_issue, github_issue(number=2)])

        result = orch.GitHubAdapter(runner).snapshot("example/project")

        self.assertEqual((2,), result.issues[0].dependencies)

    def test_live_snapshot_rejects_truncated_blocked_by_connection(self):
        raw_issue = github_issue()
        raw_issue["blockedBy"] = {"nodes": [{"number": 2}], "totalCount": 2}
        runner = self.github_runner(issues=[raw_issue, github_issue(number=2)])

        with self.assertRaisesRegex(orch.BoundaryError, "truncated"):
            orch.GitHubAdapter(runner).snapshot("example/project")

    def test_ticket_envelope_is_stable_and_starts_with_poteto_mode(self):
        state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True)])),
            )
        )

        first = orch.execute_action(state, state.pending_action.action_id, apply=False)
        second = orch.execute_action(state, state.pending_action.action_id, apply=False)

        self.assertEqual(first, second)
        self.assertEqual("ticket_run", first["status"])
        self.assertTrue(first["envelope"]["prompt"].startswith("$pstack:poteto-mode\n"))
        self.assertEqual(state.pending_action.action_id, first["envelope"]["action_id"])

    def test_review_envelope_invokes_code_review_skill(self):
        state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True)], [pull_request(review_proofs=[])])),
            )
        )

        result = orch.execute_action(state, state.pending_action.action_id, apply=False)

        self.assertIn("$mattpocock-skills:code-review", result["envelope"]["prompt"])

    def test_execute_is_dry_run_by_default_and_duplicate_claim_apply_converges(self):
        state = orch.reserve_next_action(
            orch.reconcile(orch.ProgramState.empty("example/project"), orch.parse_snapshot(snapshot([issue()])))
        )
        runner = self.github_runner(issues=[github_issue()])
        adapter = orch.GitHubAdapter(runner)

        dry = orch.execute_action(state, state.pending_action.action_id, adapter=adapter, apply=False)
        self.assertEqual("planned", dry["status"])
        self.assertEqual([], runner.calls)

        first = orch.execute_action(state, state.pending_action.action_id, adapter=adapter, apply=True)
        runner.responses[tuple(orch.GitHubAdapter.issue_argv("example/project"))] = [
            github_issue(labels=["priority:p1", "agent:claimed"])
        ]
        second = orch.execute_action(state, state.pending_action.action_id, adapter=adapter, apply=True)
        expected = ["gh", "issue", "edit", "1", "--repo", "example/project", "--add-label", "agent:claimed"]
        self.assertEqual(expected, first["mutation"]["argv"])
        self.assertEqual(1, runner.calls.count(expected))
        self.assertEqual("observed", second["status"])

    def test_live_snapshot_fails_closed_for_orphan_stack_base(self):
        runner = self.github_runner(
            issues=[github_issue()],
            prs=[github_pr(base_ref="missing-parent")],
            comments={101: []},
        )

        with self.assertRaisesRegex(orch.BoundaryError, "stack parent"):
            orch.GitHubAdapter(runner).snapshot("example/project")

    def test_execute_rejects_stale_action(self):
        state = orch.reserve_next_action(
            orch.reconcile(orch.ProgramState.empty("example/project"), orch.parse_snapshot(snapshot([issue()])))
        )
        with self.assertRaisesRegex(orch.BoundaryError, "action_id"):
            orch.execute_action(state, "stale", apply=False)

    def test_complete_comment_roundtrip_and_new_head_invalidates_it(self):
        original = pull_request(review_proofs=[])
        state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True)], [original])),
            )
        )
        action = state.pending_action
        result = {
            "action_id": action.action_id,
            "findings": [],
            "head_sha": action.head_sha,
            "issue_number": action.issue_number,
            "passed": True,
            "pr_number": action.pr_number,
            "stack_fingerprint": action.stack_fingerprint,
            "summary": "reviewed",
        }
        completion = orch.complete_action(state, action.action_id, result, apply=False)
        marker = completion["mutation"]["body"]
        parsed = orch.parse_comment_artifacts([marker])
        self.assertEqual(1, len(parsed["review_proofs"]))

        changed = pull_request(head_sha="head-2", review_proofs=parsed["review_proofs"], test_proofs=[])
        changed_state = orch.reconcile(state, orch.parse_snapshot(snapshot([issue(claimed=True)], [changed])))
        self.assertIn("missing_review_proof", orch.ready_check(changed_state, 101).reasons)

    def test_duplicate_complete_apply_observes_existing_marker(self):
        original = pull_request(review_proofs=[])
        state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True)], [original])),
            )
        )
        action = state.pending_action
        result = {
            "action_id": action.action_id,
            "findings": [],
            "head_sha": action.head_sha,
            "issue_number": action.issue_number,
            "passed": True,
            "pr_number": action.pr_number,
            "stack_fingerprint": action.stack_fingerprint,
            "summary": "reviewed",
        }
        body = orch.complete_action(state, action.action_id, result, apply=False)["mutation"]["body"]
        runner = self.github_runner(
            issues=[github_issue(labels=["priority:p1", "agent:claimed"])],
            prs=[github_pr()],
            comments={101: [body]},
        )

        applied = orch.complete_action(
            state,
            action.action_id,
            result,
            adapter=orch.GitHubAdapter(runner),
            apply=True,
        )

        self.assertEqual("observed", applied["status"])
        self.assertFalse(any(call[:3] == ["gh", "pr", "comment"] for call in runner.calls))

    def test_complete_requires_full_exact_agent_result_schema(self):
        original = pull_request(review_proofs=[])
        state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True)], [original])),
            )
        )
        action = state.pending_action

        with self.assertRaisesRegex(orch.BoundaryError, "missing keys"):
            orch.complete_action(state, action.action_id, {
                "action_id": action.action_id,
                "head_sha": action.head_sha,
                "passed": True,
                "stack_fingerprint": action.stack_fingerprint,
                "summary": "incomplete",
            })

    def test_complete_rejects_result_for_changed_stack_parent(self):
        parent = pull_request(number=100, issue_number=2, head_sha="parent-1")
        child = pull_request(parent_pr=100, parent_head_sha="parent-1", review_proofs=[])
        state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True), issue(number=2, claimed=True)], [child, parent])),
            )
        )
        action = state.pending_action
        changed_parent = pull_request(number=100, issue_number=2, head_sha="parent-2")
        current = orch.reconcile(
            state,
            orch.parse_snapshot(snapshot([issue(claimed=True), issue(number=2, claimed=True)], [child, changed_parent])),
        )
        result = {
            "action_id": action.action_id,
            "findings": [],
            "head_sha": action.head_sha,
            "issue_number": action.issue_number,
            "passed": True,
            "pr_number": action.pr_number,
            "stack_fingerprint": action.stack_fingerprint,
            "summary": "reviewed",
        }
        with self.assertRaisesRegex(orch.BoundaryError, "stale"):
            orch.complete_action(current, action.action_id, result, apply=False)

    def test_mark_ready_live_refresh_blocks_p0_and_parent_change(self):
        child = pull_request(parent_pr=100, parent_head_sha="parent-1")
        parent = pull_request(number=100, issue_number=2, head_sha="parent-1", ready=True)
        state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True), issue(number=2, claimed=True)], [child, parent])),
            )
        )
        self.assertEqual("mark_ready", state.pending_action.kind)

        blocking_child = github_pr(base_ref="ticket-2")
        changed_parent = github_pr(number=100, issue_number=2, head="parent-2", head_ref="ticket-2", labels=["READY-FOR-MERGE"])
        fingerprint = orch.stack_fingerprint("ticket-2", 100, "parent-2")
        review = orch.proof_marker("review", "r", "head-1", fingerprint, True)
        test = orch.proof_marker("test", "t", "head-1", fingerprint, True)
        runner = self.github_runner(
            issues=[github_issue(labels=["priority:p1", "agent:claimed"]), github_issue(number=2, labels=["priority:p1", "agent:claimed"])],
            prs=[blocking_child, changed_parent],
            comments={101: [review, test, "[P0] unsafe"], 100: []},
        )
        with self.assertRaisesRegex(orch.BoundaryError, "stale|not ready"):
            orch.execute_action(state, state.pending_action.action_id, adapter=orch.GitHubAdapter(runner), apply=True)
        self.assertFalse(any(call[:3] == ["gh", "pr", "edit"] for call in runner.calls))

    def test_existing_ready_label_is_checked_against_current_policy_before_observed(self):
        original = pull_request(ready=False)
        state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True)], [original])),
            )
        )
        state = orch.replace(state, policy_digest="current-policy")
        fingerprint = orch.stack_fingerprint("main", None, None)
        review = orch.proof_marker("review", "review", "head-1", fingerprint, True)
        test = orch.proof_marker("test", "test", "head-1", fingerprint, True)
        runner = self.github_runner(
            issues=[github_issue(labels=["priority:p1", "agent:claimed"])],
            prs=[github_pr(labels=["READY-FOR-MERGE"])],
            comments={101: [review, test]},
        )

        with self.assertRaisesRegex(orch.BoundaryError, "missing_review_proof,missing_test_proof"):
            orch.execute_action(state, state.pending_action.action_id, adapter=orch.GitHubAdapter(runner), apply=True)

        self.assertFalse(any(call[:3] == ["gh", "pr", "edit"] for call in runner.calls))

    def test_duplicate_mark_ready_apply_observes_existing_label(self):
        original = pull_request(ready=False)
        state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True)], [original])),
            )
        )
        fingerprint = orch.stack_fingerprint("main", None, None)
        review = orch.proof_marker("review", "review", "head-1", fingerprint, True)
        test = orch.proof_marker("test", "test", "head-1", fingerprint, True)
        runner = self.github_runner(
            issues=[github_issue(labels=["priority:p1", "agent:claimed"])],
            prs=[github_pr(labels=["READY-FOR-MERGE"])],
            comments={101: [review, test]},
        )

        result = orch.execute_action(
            state,
            state.pending_action.action_id,
            adapter=orch.GitHubAdapter(runner),
            apply=True,
        )

        self.assertEqual("observed", result["status"])
        self.assertFalse(any(call[:3] == ["gh", "pr", "edit"] for call in runner.calls))

    def test_untrusted_comment_markers_do_not_count_as_proof(self):
        fingerprint = orch.stack_fingerprint("main", None, None)
        marker = orch.proof_marker("review", "forged", "head-1", fingerprint, True)
        runner = self.github_runner(
            issues=[github_issue(labels=["priority:p1", "agent:claimed"])],
            prs=[github_pr()],
            comments={101: []},
        )
        runner.responses[tuple(orch.GitHubAdapter.comment_argv("example/project", 101))] = [
            {"body": marker, "author_association": "NONE"}
        ]

        result = orch.GitHubAdapter(runner).snapshot("example/project")

        self.assertEqual((), result.pull_requests[0].review_proofs)

    def test_safe_gh_error_does_not_expose_stderr(self):
        runner = FakeGhRunner(error="token ghp_secret was rejected")
        with self.assertRaisesRegex(orch.BoundaryError, "GitHub command failed") as raised:
            orch.GitHubAdapter(runner).snapshot("example/project")
        self.assertNotIn("ghp_secret", str(raised.exception))


class SimulatedRunAdapter:
    def __init__(self):
        self.issue = issue(claimed=False)
        self.pr = None
        self.comments = []
        self.mutations = []

    def snapshot(self, repository):
        return orch.parse_snapshot(snapshot([self.issue], [] if self.pr is None else [self.pr]))

    def comment_bodies(self, repository, pr_number):
        return list(self.comments)

    def mutate(self, argv):
        self.mutations.append(argv)
        if argv[:3] == ["gh", "issue", "edit"]:
            self.issue["claimed"] = True
        elif argv[:3] == ["gh", "pr", "comment"]:
            body = argv[argv.index("--body") + 1]
            self.comments.append(body)
            artifacts = orch.parse_comment_artifacts(self.comments)
            self.pr["findings"] = artifacts["findings"]
            self.pr["review_proofs"] = artifacts["review_proofs"]
            self.pr["test_proofs"] = artifacts["test_proofs"]
        elif argv[:3] == ["gh", "pr", "edit"]:
            self.pr["ready"] = True


class RunModeTests(unittest.TestCase):
    def policy(self, root, max_attempts=2):
        return orch.RunPolicy.from_dict({
            "repository_root": str(root),
            "agent_argv": ["agent"],
            "verification_commands": [{"name": "unit", "argv": ["verify", "--exact"]}],
            "poll_seconds": 0,
            "timeout_seconds": 10,
            "max_attempts": max_attempts,
        })

    @staticmethod
    def agent_result(prompt):
        contract = json.loads(prompt.splitlines()[-2])
        contract["summary"] = "done"
        if "findings" in contract:
            contract["findings"] = []
        return contract

    def test_dry_run_reports_planned_without_effects(self):
        adapter = SimulatedRunAdapter()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = orch.run_program(
                "example/project",
                self.policy(root),
                root / "state.json",
                dry_run=True,
                adapter=adapter,
            )

        self.assertEqual("planned", outcome.disposition)
        self.assertEqual([], adapter.mutations)

    def test_full_run_stops_ready_and_rerun_after_merge_completes(self):
        adapter = SimulatedRunAdapter()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = self.policy(root)
            state_path = root / "state.json"

            def invoke(argv, cwd, timeout, input_text=None):
                if argv == ["git", "rev-parse", "HEAD"]:
                    return subprocess.CompletedProcess(argv, 0, "head-1\n", "")
                if argv in (["git", "status", "--porcelain=v1", "--untracked-files=all"], ["verify", "--exact"]):
                    return subprocess.CompletedProcess(argv, 0, "", "")
                result = self.agent_result(input_text)
                if adapter.pr is None:
                    adapter.pr = pull_request(review_proofs=[], test_proofs=[])
                return subprocess.CompletedProcess(argv, 0, json.dumps(result), "")

            with mock.patch.object(orch, "_run_process", side_effect=invoke):
                outcome = orch.run_program("example/project", policy, state_path, adapter=adapter)

            self.assertEqual("ready_for_merge", outcome.disposition)
            self.assertFalse(any(call[:3] == ["gh", "pr", "merge"] for call in adapter.mutations))

            paused = orch.run_program("example/project", policy, state_path, adapter=adapter)
            self.assertEqual("ready_for_merge", paused.disposition)
            adapter.issue["state"] = "closed"
            adapter.pr["state"] = "merged"
            adapter.pr["ready"] = False
            completed = orch.run_program("example/project", policy, state_path, adapter=adapter)
            self.assertEqual("complete", completed.disposition)

    def test_retry_then_success_and_postcondition_observation_before_retry(self):
        for observe_on_failure, expected_calls in ((False, 2), (True, 1)):
            with self.subTest(observe_on_failure=observe_on_failure), tempfile.TemporaryDirectory() as directory:
                adapter = SimulatedRunAdapter()
                adapter.issue["claimed"] = True
                root = Path(directory)
                run_policy = self.policy(root)
                calls = 0

                def ready_pr():
                    pr = pull_request(ready=True)
                    for receipts in (pr["review_proofs"], pr["test_proofs"]):
                        receipts[0]["policy_digest"] = run_policy.digest
                    return pr

                def invoke(argv, cwd, timeout, input_text=None):
                    nonlocal calls
                    calls += 1
                    if calls == 1:
                        if observe_on_failure:
                            adapter.pr = ready_pr()
                        return subprocess.CompletedProcess(argv, 1, "", "")
                    adapter.pr = ready_pr()
                    return subprocess.CompletedProcess(argv, 0, json.dumps(self.agent_result(input_text)), "")

                with mock.patch.object(orch, "_run_process", side_effect=invoke):
                    outcome = orch.run_program("example/project", run_policy, root / "state.json", adapter=adapter)
                self.assertEqual("ready_for_merge", outcome.disposition)
                self.assertEqual(expected_calls, calls)

    def test_retry_exhaustion(self):
        adapter = SimulatedRunAdapter()
        adapter.issue["claimed"] = True
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            failed = subprocess.CompletedProcess(["agent"], 1, "", "")
            with mock.patch.object(orch, "_run_process", return_value=failed) as invoked:
                outcome = orch.run_program("example/project", self.policy(root), root / "state.json", adapter=adapter)
            self.assertEqual("failed", outcome.disposition)
            self.assertEqual(2, invoked.call_count)

    def test_prompt_contract_and_strict_result_rejection(self):
        state = orch.reserve_next_action(self.reconcile_state(review=True))
        action = state.pending_action
        policy = self.policy(HERE)
        prompt = orch._ticket_run_envelope(state, action, policy)["prompt"]
        self.assertIn("Output JSON only. No Markdown. No extra keys.", prompt)
        contract = json.loads(prompt.splitlines()[-2])
        self.assertEqual(action.action_id, contract["action_id"])
        bad = dict(contract)
        bad["summary"] = "ok"
        bad["findings"] = []
        bad["extra"] = True
        with self.assertRaisesRegex(orch.BoundaryError, "unknown keys"):
            orch._parse_agent_result(action, bad)
        bad.pop("extra")
        bad["head_sha"] = "wrong"
        with self.assertRaisesRegex(orch.BoundaryError, "does not match"):
            orch._parse_agent_result(action, bad)

    def reconcile_state(self, review=False):
        pr = pull_request(review_proofs=[] if review else None)
        return orch.reconcile(
            orch.ProgramState.empty("example/project"),
            orch.parse_snapshot(snapshot([issue(claimed=True)], [pr])),
        )

    def test_policy_commands_are_verbatim_and_digest_invalidates_proof(self):
        policy = self.policy(HERE)
        fingerprint = orch.stack_fingerprint("main", None, None)
        pr_for_verify = pull_request(
            review_proofs=[proof(policy_digest=policy.digest, stack_fingerprint=fingerprint)],
            test_proofs=[],
        )
        state = orch.reconcile(
            orch.ProgramState.empty("example/project"),
            orch.parse_snapshot(snapshot([issue(claimed=True)], [pr_for_verify])),
        )
        state = orch.reserve_next_action(orch.replace(state, policy_digest=policy.digest))
        prompt = orch._ticket_run_envelope(state, state.pending_action, policy, [
            {"name": "unit", "argv": ["verify", "--exact"], "exit_status": 0}
        ])["prompt"]
        self.assertIn('["verify","--exact"]', prompt)

        pr = pull_request()
        for receipts in (pr["review_proofs"], pr["test_proofs"]):
            receipts[0]["policy_digest"] = policy.digest
        ready_state = orch.reconcile(orch.ProgramState.empty("example/project"), orch.parse_snapshot(snapshot([issue(claimed=True)], [pr])))
        self.assertTrue(orch.ready_check(ready_state, 101, policy.digest).ready)
        self.assertFalse(orch.ready_check(ready_state, 101, "changed").ready)

    def test_finding_lifecycle_folds_and_old_head_does_not_block(self):
        fingerprint = orch.stack_fingerprint("main", None, None)
        markers = [
            '<!-- orch-finding:{"finding_id":"f1","head_sha":"head-1","resolved":false,"severity":"P1","stack_fingerprint":"%s"} -->' % fingerprint,
            '<!-- orch-finding:{"finding_id":"f1","head_sha":"head-1","resolved":true,"severity":"P1","stack_fingerprint":"%s"} -->' % fingerprint,
        ]
        folded = orch.parse_comment_artifacts(markers)["findings"]
        self.assertEqual(1, len(folded))
        self.assertTrue(folded[0]["resolved"])
        current = pull_request(head_sha="head-2", findings=[{
            "finding_id": "old", "head_sha": "head-1", "stack_fingerprint": fingerprint,
            "severity": "P0", "resolved": False,
        }])
        state = orch.reconcile(orch.ProgramState.empty("example/project"), orch.parse_snapshot(snapshot([issue(claimed=True)], [current])))
        self.assertNotIn("unresolved_p0_p1", orch.ready_check(state, 101).reasons)

    def test_multiple_open_prs_and_cap_fail_closed(self):
        with self.assertRaisesRegex(orch.BoundaryError, "101,102"):
            orch.parse_snapshot(snapshot([issue()], [pull_request(), pull_request(number=102)]))
        runner = FakeGhRunner({
            tuple(orch.GitHubAdapter.repo_argv("example/project")): {"nameWithOwner": "example/project", "defaultBranchRef": {"name": "main"}},
            tuple(orch.GitHubAdapter.issue_argv("example/project")): [github_issue(number=index + 1) for index in range(1000)],
            tuple(orch.GitHubAdapter.pr_argv("example/project")): [],
        })
        with self.assertRaisesRegex(orch.BoundaryError, "1000-item cap"):
            orch.GitHubAdapter(runner).snapshot("example/project")

    def test_closed_issue_with_open_managed_pr_is_not_complete(self):
        adapter = SimulatedRunAdapter()
        adapter.issue["state"] = "closed"
        adapter.pr = pull_request(review_proofs=[], test_proofs=[])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = orch.run_program(
                "example/project",
                self.policy(root),
                root / "state.json",
                adapter=adapter,
            )

        self.assertEqual("blocked", outcome.disposition)
        self.assertIn("open managed pull request remains", outcome.reason)

    def test_review_agent_requires_clean_exact_pr_checkout(self):
        adapter = SimulatedRunAdapter()
        adapter.issue["claimed"] = True
        adapter.pr = pull_request(review_proofs=[], test_proofs=[])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(orch, "_invoke_agent") as invoked:
                outcome = orch.run_program(
                    "example/project",
                    self.policy(root, max_attempts=1),
                    root / "state.json",
                    adapter=adapter,
                )

        self.assertEqual("failed", outcome.disposition)
        self.assertIn("Git worktree", outcome.reason)
        invoked.assert_not_called()

    def test_existing_ready_label_is_blocked_with_all_live_gate_reasons(self):
        adapter = SimulatedRunAdapter()
        adapter.issue["claimed"] = True
        adapter.pr = pull_request(
            ready=True,
            draft=True,
            checks=[{"name": "ci", "status": "failure"}],
            findings=[{"severity": "P1", "resolved": False}],
            review_proofs=[],
            test_proofs=[],
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = orch.run_program("example/project", self.policy(root), root / "state.json", adapter=adapter)

        self.assertEqual("blocked", outcome.disposition)
        for reason in ("draft", "checks_not_successful", "unresolved_p0_p1", "missing_review_proof", "missing_test_proof"):
            self.assertIn(reason, outcome.reason)

    def test_wait_for_ci_polls_pending_with_budget_and_blocks_terminal_checks(self):
        for status, disposition, sleeps in (("pending", "failed", 2), ("failure", "blocked", 0)):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                adapter = SimulatedRunAdapter()
                adapter.issue["claimed"] = True
                root = Path(directory)
                policy = self.policy(root)
                fingerprint = orch.stack_fingerprint("main", None, None)
                adapter.pr = pull_request(
                    checks=[{"name": "ci", "status": status}],
                    review_proofs=[proof(stack_fingerprint=fingerprint, policy_digest=policy.digest)],
                    test_proofs=[proof(stack_fingerprint=fingerprint, policy_digest=policy.digest)],
                )
                sleeper = mock.Mock()

                outcome = orch.run_program(
                    "example/project",
                    policy,
                    root / "state.json",
                    adapter=adapter,
                    sleeper=sleeper,
                )

                self.assertEqual(disposition, outcome.disposition)
                self.assertEqual(sleeps, sleeper.call_count)

    def test_retryable_claim_error_is_bounded_reconciled_and_slept(self):
        class RetryClaimAdapter(SimulatedRunAdapter):
            def __init__(self):
                super().__init__()
                self.snapshots = 0

            def snapshot(self, repository):
                self.snapshots += 1
                if self.snapshots == 2:
                    raise orch.BoundaryError("temporary")
                return super().snapshot(repository)

            def mutate(self, argv):
                super().mutate(argv)
                if argv[:3] == ["gh", "issue", "edit"]:
                    self.issue["state"] = "closed"

        adapter = RetryClaimAdapter()
        sleeper = mock.Mock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = orch.run_program(
                "example/project",
                self.policy(root),
                root / "state.json",
                adapter=adapter,
                sleeper=sleeper,
            )

        self.assertEqual("complete", outcome.disposition)
        self.assertEqual(1, sleeper.call_count)
        self.assertEqual(1, len(adapter.mutations))

    def test_policy_digest_change_clears_persisted_attempt(self):
        adapter = SimulatedRunAdapter()
        adapter.issue["claimed"] = True
        state = orch.reserve_next_action(
            orch.reconcile(orch.ProgramState.empty("example/project"), adapter.snapshot("example/project"))
        )
        state = orch.replace(
            state,
            policy_digest="old",
            run_attempt=orch.RunAttempt(state.pending_action.action_id, 2),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            refreshed = orch._refresh_run_state(state, adapter, self.policy(root), root / "state.json")

        self.assertIsNone(refreshed.run_attempt)

    def test_review_and_patch_prompts_include_current_finding_ids(self):
        finding = {
            "finding_id": "finding-7",
            "head_sha": "head-1",
            "stack_fingerprint": orch.stack_fingerprint("main", None, None),
            "severity": "P1",
            "resolved": False,
        }
        patch_state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True)], [pull_request(findings=[finding])])),
            )
        )
        review_pr = pull_request(findings=[{**finding, "severity": "P2"}], review_proofs=[])
        review_state = orch.reserve_next_action(
            orch.reconcile(
                orch.ProgramState.empty("example/project"),
                orch.parse_snapshot(snapshot([issue(claimed=True)], [review_pr])),
            )
        )

        for state in (patch_state, review_state):
            prompt = orch._ticket_run_envelope(state, state.pending_action)["prompt"]
            self.assertIn('"finding_id":"finding-7"', prompt)
            self.assertIn("Preserve each finding_id", prompt)

    def test_verification_requires_clean_exact_git_head_before_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            (root / "tracked").write_text("ok")
            subprocess.run(["git", "-C", str(root), "add", "tracked"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
            head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            marker = root.parent / f"{root.name}-verified"
            policy = orch.RunPolicy.from_dict({
                "repository_root": str(root),
                "agent_argv": ["agent"],
                "verification_commands": [{
                    "name": "marker",
                    "argv": [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('passed')"],
                }],
                "poll_seconds": 0,
                "timeout_seconds": 2,
                "max_attempts": 1,
            })
            action = orch.PendingAction("verify", "verify_pr", 1, 101, head, "fingerprint")

            results = orch._run_verification_commands(policy, action)
            self.assertEqual(0, results[0]["exit_status"])
            marker.unlink()
            mismatched = orch.replace(action, head_sha="not-the-head")
            with self.assertRaisesRegex(orch.BoundaryError, "HEAD"):
                orch._run_verification_commands(policy, mismatched)
            self.assertFalse(marker.exists())
            state_path = root / ".codex" / "orchestrator" / "state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text("{}")
            state_path.with_name("state.json.lock").touch()
            state_path.with_name("state.json.run.lock").touch()
            allowed = orch._run_verification_commands(policy, action, state_path)
            self.assertEqual(0, allowed[0]["exit_status"])
            marker.unlink()
            (root / "dirty").write_text("dirty")
            with self.assertRaisesRegex(orch.BoundaryError, "clean"):
                orch._run_verification_commands(policy, action, state_path)
            self.assertFalse(marker.exists())

    def test_process_timeout_kills_child_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "child-finished"
            child = "import time; from pathlib import Path; time.sleep(.3); Path(%r).write_text('alive')" % str(marker)
            parent = "import subprocess,time,sys; subprocess.Popen([sys.executable,'-c',%r]); time.sleep(5)" % child

            with self.assertRaises(subprocess.TimeoutExpired):
                orch._run_process([sys.executable, "-c", parent], root, .05)
            time.sleep(.4)

            self.assertFalse(marker.exists())

    def test_whole_run_lock_is_nonblocking(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            with orch._run_lock(path):
                with self.assertRaisesRegex(orch.BoundaryError, "state or whole-run lock"):
                    with orch._run_lock(path):
                        pass
                state_lock = path.with_name("state.json.lock").open("a+")
                try:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(state_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                finally:
                    state_lock.close()


if __name__ == "__main__":
    unittest.main()
