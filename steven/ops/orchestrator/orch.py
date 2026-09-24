#!/usr/bin/env python3
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Optional


STATE_VERSION = 1
PRIORITIES = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
PR_STATES = {"open", "closed", "merged"}
ISSUE_STATES = {"open", "closed"}
CHECK_STATES = {"success", "failure", "pending", "cancelled", "skipped", "neutral"}
DEFAULT_STATE = Path(".codex/orchestrator/state.json")


class BoundaryError(ValueError):
    pass


class GhCommandError(RuntimeError):
    pass


@dataclass(frozen=True)
class IssueSnapshot:
    number: int
    priority: str
    dependencies: tuple[int, ...]
    claimed: bool
    created_at: str
    state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claimed": self.claimed,
            "created_at": self.created_at,
            "dependencies": list(self.dependencies),
            "number": self.number,
            "priority": self.priority,
            "state": self.state,
        }


@dataclass(frozen=True)
class CheckSnapshot:
    name: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status}


@dataclass(frozen=True)
class FindingSnapshot:
    severity: str
    resolved: bool
    finding_id: str = field(default="", compare=False)
    head_sha: str = field(default="", compare=False)
    stack_fingerprint: str = field(default="", compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "head_sha": self.head_sha,
            "resolved": self.resolved,
            "severity": self.severity,
            "stack_fingerprint": self.stack_fingerprint,
        }


@dataclass(frozen=True)
class ProofReceipt:
    head_sha: str
    stack_fingerprint: str
    passed: bool
    policy_digest: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "head_sha": self.head_sha,
            "passed": self.passed,
            "stack_fingerprint": self.stack_fingerprint,
        }
        if self.policy_digest is not None:
            result["policy_digest"] = self.policy_digest
        return result


@dataclass(frozen=True)
class RunAttempt:
    action_id: str
    count: int

    def to_dict(self) -> dict[str, Any]:
        return {"action_id": self.action_id, "count": self.count}


@dataclass(frozen=True)
class VerificationCommand:
    name: str
    argv: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"argv": list(self.argv), "name": self.name}


@dataclass(frozen=True)
class RunPolicy:
    repository_root: Path
    agent_argv: tuple[str, ...]
    verification_commands: tuple[VerificationCommand, ...]
    poll_seconds: float
    timeout_seconds: float
    max_attempts: int

    @classmethod
    def from_dict(cls, value: Any) -> "RunPolicy":
        mapping = _strict_mapping(
            value,
            "policy",
            {"repository_root", "agent_argv", "verification_commands", "poll_seconds", "timeout_seconds", "max_attempts"},
        )
        root = Path(_string(mapping, "repository_root", "policy")).expanduser().resolve()
        agent = _argv(mapping.get("agent_argv"), "policy.agent_argv")
        commands_value = _list(mapping, "verification_commands", "policy")
        commands = []
        for index, item in enumerate(commands_value):
            path = f"policy.verification_commands[{index}]"
            command = _strict_mapping(item, path, {"name", "argv"})
            commands.append(VerificationCommand(_string(command, "name", path), _argv(command.get("argv"), f"{path}.argv")))
        poll = _positive_number(mapping.get("poll_seconds"), "policy.poll_seconds", allow_zero=True)
        timeout = _positive_number(mapping.get("timeout_seconds"), "policy.timeout_seconds")
        attempts = _positive_integer(mapping, "max_attempts", "policy")
        if not root.is_dir():
            raise BoundaryError("policy.repository_root must be an existing directory")
        return cls(root, agent, tuple(commands), poll, timeout, attempts)

    @property
    def digest(self) -> str:
        canonical = {
            "agent_argv": list(self.agent_argv),
            "max_attempts": self.max_attempts,
            "poll_seconds": self.poll_seconds,
            "repository_root": str(self.repository_root),
            "timeout_seconds": self.timeout_seconds,
            "verification_commands": [command.to_dict() for command in self.verification_commands],
        }
        return hashlib.sha256(json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class RunOutcome:
    disposition: str
    reason: str
    action_id: Optional[str] = None
    pr_number: Optional[int] = None

    def __post_init__(self) -> None:
        if self.disposition not in {"complete", "ready_for_merge", "planned", "blocked", "failed"}:
            raise BoundaryError("invalid run outcome disposition")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "disposition": self.disposition,
            "pr_number": self.pr_number,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PullRequestSnapshot:
    number: int
    issue_number: int
    state: str
    draft: bool
    head_sha: str
    base_ref: str
    parent_pr: Optional[int]
    parent_head_sha: Optional[str]
    checks: tuple[CheckSnapshot, ...]
    findings: tuple[FindingSnapshot, ...]
    review_proofs: tuple[ProofReceipt, ...]
    test_proofs: tuple[ProofReceipt, ...]
    ready: bool

    @property
    def fingerprint(self) -> str:
        return stack_fingerprint(self.base_ref, self.parent_pr, self.parent_head_sha)

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_ref": self.base_ref,
            "checks": [check.to_dict() for check in self.checks],
            "draft": self.draft,
            "findings": [finding.to_dict() for finding in self.findings],
            "head_sha": self.head_sha,
            "issue_number": self.issue_number,
            "number": self.number,
            "parent_head_sha": self.parent_head_sha,
            "parent_pr": self.parent_pr,
            "ready": self.ready,
            "review_proofs": [receipt.to_dict() for receipt in self.review_proofs],
            "state": self.state,
            "test_proofs": [receipt.to_dict() for receipt in self.test_proofs],
        }


@dataclass(frozen=True)
class RepositorySnapshot:
    repository: str
    issues: tuple[IssueSnapshot, ...]
    pull_requests: tuple[PullRequestSnapshot, ...]


@dataclass(frozen=True)
class PendingAction:
    action_id: str
    kind: str
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None
    head_sha: Optional[str] = None
    stack_fingerprint: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "head_sha": self.head_sha,
            "issue_number": self.issue_number,
            "kind": self.kind,
            "pr_number": self.pr_number,
            "stack_fingerprint": self.stack_fingerprint,
        }


@dataclass(frozen=True)
class ProgramState:
    repository: str
    issues: tuple[IssueSnapshot, ...]
    pull_requests: tuple[PullRequestSnapshot, ...]
    pending_action: Optional[PendingAction] = None
    run_attempt: Optional[RunAttempt] = None
    policy_digest: Optional[str] = None
    version: int = STATE_VERSION

    @classmethod
    def empty(cls, repository: str) -> "ProgramState":
        return cls(repository=repository, issues=(), pull_requests=())

    @classmethod
    def from_dict(cls, value: Any) -> "ProgramState":
        mapping = _mapping(value, "state")
        version = _integer(mapping, "version", "state")
        if version != STATE_VERSION:
            raise BoundaryError(f"state.version must be {STATE_VERSION}")
        normalized = parse_snapshot(mapping)
        pending_value = mapping.get("pending_action")
        pending = None if pending_value is None else _parse_pending(pending_value)
        attempt_value = mapping.get("run_attempt")
        attempt = None if attempt_value is None else _parse_attempt(attempt_value)
        policy_digest = _optional_string(mapping.get("policy_digest"), "state.policy_digest")
        if attempt is not None and (pending is None or attempt.action_id != pending.action_id):
            raise BoundaryError("state.run_attempt must belong to the pending action")
        return cls(
            repository=normalized.repository,
            issues=normalized.issues,
            pull_requests=normalized.pull_requests,
            pending_action=pending,
            run_attempt=attempt,
            policy_digest=policy_digest,
            version=version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "issues": [item.to_dict() for item in self.issues],
            "pending_action": None if self.pending_action is None else self.pending_action.to_dict(),
            "policy_digest": self.policy_digest,
            "pull_requests": [item.to_dict() for item in self.pull_requests],
            "repository": self.repository,
            "run_attempt": None if self.run_attempt is None else self.run_attempt.to_dict(),
            "version": self.version,
        }


@dataclass(frozen=True)
class ReadyVerdict:
    ready: bool
    pr_number: int
    head_sha: Optional[str]
    stack_fingerprint: Optional[str]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "head_sha": self.head_sha,
            "pr_number": self.pr_number,
            "ready": self.ready,
            "reasons": list(self.reasons),
            "stack_fingerprint": self.stack_fingerprint,
        }


class GitHubAdapter:
    TRUSTED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
    LIST_CAP = 1000
    REPO_FIELDS = "nameWithOwner,defaultBranchRef"
    ISSUE_FIELDS = "number,createdAt,state,labels,blockedBy"
    PR_FIELDS = (
        "number,state,isDraft,headRefOid,headRefName,baseRefName,"
        "closingIssuesReferences,labels,statusCheckRollup"
    )

    def __init__(self, runner: Optional[Any] = None):
        self._runner = runner or _run_gh

    @classmethod
    def repo_argv(cls, repository: str) -> list[str]:
        return ["gh", "repo", "view", repository, "--json", cls.REPO_FIELDS]

    @classmethod
    def issue_argv(cls, repository: str) -> list[str]:
        return [
            "gh", "issue", "list", "--repo", repository, "--state", "all",
            "--limit", str(cls.LIST_CAP), "--json", cls.ISSUE_FIELDS,
        ]

    @classmethod
    def pr_argv(cls, repository: str) -> list[str]:
        return [
            "gh", "pr", "list", "--repo", repository, "--state", "all",
            "--limit", str(cls.LIST_CAP), "--json", cls.PR_FIELDS,
        ]

    @staticmethod
    def comment_argv(repository: str, pr_number: int) -> list[str]:
        return [
            "gh", "api", f"repos/{repository}/issues/{pr_number}/comments", "--paginate", "--slurp",
        ]

    def snapshot(self, repository: str) -> RepositorySnapshot:
        repo = self._object(self.repo_argv(repository), "repository")
        if _raw_string(repo, "nameWithOwner", "GitHub repository") != repository:
            raise BoundaryError("GitHub returned a different repository")
        default_ref = _mapping(repo.get("defaultBranchRef"), "GitHub repository.defaultBranchRef")
        default_branch = _raw_string(default_ref, "name", "GitHub repository.defaultBranchRef")
        issues = self._json(self.issue_argv(repository), "issues")
        raw_prs = self._json(self.pr_argv(repository), "pull requests")
        if len(issues) == self.LIST_CAP:
            raise BoundaryError(f"issue query returned its {self.LIST_CAP}-item cap; complete pagination is required")
        if len(raw_prs) == self.LIST_CAP:
            raise BoundaryError(f"pull request query returned its {self.LIST_CAP}-item cap; complete pagination is required")
        comments = {
            _raw_positive_integer(item, "number", "pull request"): self._comments(
                self.comment_argv(repository, _raw_positive_integer(item, "number", "pull request")),
            )
            for item in sorted(raw_prs, key=lambda value: value.get("number", 0))
            if item.get("state") == "OPEN"
            and isinstance(item.get("closingIssuesReferences"), list)
            and len(item["closingIssuesReferences"]) == 1
        }
        return _normalize_github_snapshot(repository, default_branch, issues, raw_prs, comments)

    def comment_bodies(self, repository: str, pr_number: int) -> list[str]:
        return [
            _raw_string(item, "body", "pull request comment")
            for item in self._comments(self.comment_argv(repository, pr_number))
        ]

    def mutate(self, argv: list[str]) -> None:
        try:
            self._runner(argv)
        except Exception as error:
            raise BoundaryError("GitHub command failed") from error

    def _json(self, argv: list[str], name: str) -> list[Any]:
        try:
            value = json.loads(self._runner(argv))
        except Exception as error:
            raise BoundaryError("GitHub command failed") from error
        if not isinstance(value, list):
            raise BoundaryError(f"GitHub returned invalid {name}")
        return value

    def _object(self, argv: list[str], name: str) -> dict[str, Any]:
        try:
            value = json.loads(self._runner(argv))
        except Exception as error:
            raise BoundaryError("GitHub command failed") from error
        if not isinstance(value, dict):
            raise BoundaryError(f"GitHub returned invalid {name}")
        return value

    def _comments(self, argv: list[str]) -> list[Any]:
        value = self._json(argv, "pull request comments")
        if value and all(isinstance(page, list) for page in value):
            value = [comment for page in value for comment in page]
        trusted = []
        for item in value:
            mapping = _mapping(item, "pull request comment")
            association = mapping.get("author_association")
            if isinstance(association, str) and association.upper() in self.TRUSTED_ASSOCIATIONS:
                trusted.append(item)
        return trusted


def stack_fingerprint(base_ref: str, parent_pr: Optional[int], parent_head_sha: Optional[str]) -> str:
    identity = {
        "base_ref": base_ref,
        "parent_head_sha": parent_head_sha,
        "parent_pr": parent_pr,
    }
    encoded = json.dumps(identity, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def proof_marker(
    kind: str,
    action_id: str,
    head_sha: str,
    fingerprint: str,
    passed: bool,
    policy_digest: Optional[str] = None,
) -> str:
    if kind not in {"review", "test"}:
        raise BoundaryError("proof kind must be review or test")
    payload = {
        "action_id": action_id,
        "head_sha": head_sha,
        "kind": kind,
        "passed": passed,
        "stack_fingerprint": fingerprint,
    }
    if policy_digest is not None:
        payload["policy_digest"] = policy_digest
    return f"<!-- orch-proof:{json.dumps(payload, separators=(',', ':'), sort_keys=True)} -->"


def parse_comment_artifacts(bodies: list[str]) -> dict[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    review_proofs: list[dict[str, Any]] = []
    test_proofs: list[dict[str, Any]] = []
    for body in bodies:
        for encoded in re.findall(r"<!--\s*orch-proof:(.*?)-->", body, re.DOTALL):
            try:
                payload = json.loads(encoded)
                kind = payload.get("kind")
                receipt = {
                    "head_sha": payload["head_sha"],
                    "stack_fingerprint": payload["stack_fingerprint"],
                    "passed": payload["passed"],
                }
                if "policy_digest" in payload:
                    receipt["policy_digest"] = payload["policy_digest"]
                if kind == "review":
                    review_proofs.append(receipt)
                elif kind == "test":
                    test_proofs.append(receipt)
                else:
                    raise BoundaryError("invalid orchestrator proof marker")
            except (KeyError, TypeError, json.JSONDecodeError) as error:
                raise BoundaryError("invalid orchestrator proof marker") from error
        if "orch-proof:" in body and not re.search(r"<!--\s*orch-proof:.*?-->", body, re.DOTALL):
            raise BoundaryError("invalid orchestrator proof marker")
        for encoded in re.findall(r"<!--\s*orch-finding:(.*?)-->", body, re.DOTALL):
            try:
                payload = json.loads(encoded)
                severity = payload["severity"]
                resolved = payload["resolved"]
                if not isinstance(severity, str) or severity.upper() not in PRIORITIES:
                    raise BoundaryError("invalid orchestrator finding marker")
                if not isinstance(resolved, bool):
                    raise BoundaryError("invalid orchestrator finding marker")
                finding_id = payload.get("finding_id")
                if finding_id is None:
                    finding_id = "legacy-" + hashlib.sha256(encoded.strip().encode()).hexdigest()[:20]
                if not isinstance(finding_id, str) or not finding_id:
                    raise BoundaryError("invalid orchestrator finding marker")
                finding = {
                    "finding_id": finding_id,
                    "head_sha": payload.get("head_sha", ""),
                    "resolved": resolved,
                    "severity": severity.upper(),
                    "stack_fingerprint": payload.get("stack_fingerprint", ""),
                }
                previous = next((index for index, item in enumerate(findings) if item["finding_id"] == finding_id), None)
                if previous is None:
                    findings.append(finding)
                else:
                    findings[previous] = finding
            except (KeyError, TypeError, json.JSONDecodeError) as error:
                raise BoundaryError("invalid orchestrator finding marker") from error
        if "orch-finding:" in body and not re.search(r"<!--\s*orch-finding:.*?-->", body, re.DOTALL):
            raise BoundaryError("invalid orchestrator finding marker")
    return {
        "findings": findings,
        "review_proofs": review_proofs,
        "test_proofs": test_proofs,
    }


def _normalize_github_snapshot(
    repository: str,
    default_branch: str,
    raw_issues: list[Any],
    raw_prs: list[Any],
    comments: dict[int, list[Any]],
) -> RepositorySnapshot:
    issues = [_normalize_github_issue(item) for item in raw_issues]
    branch_prs: dict[str, list[Any]] = {}
    for item in raw_prs:
        branch_prs.setdefault(_raw_string(item, "headRefName", "pull request"), []).append(item)
    prs = [
        normalized
        for item in raw_prs
        if (normalized := _normalize_github_pr(item, default_branch, branch_prs, comments)) is not None
    ]
    return parse_snapshot({
        "version": STATE_VERSION,
        "repository": repository,
        "issues": issues,
        "pull_requests": prs,
    })


def _normalize_github_issue(value: Any) -> dict[str, Any]:
    mapping = _mapping(value, "GitHub issue")
    labels = _github_labels(mapping.get("labels"), "GitHub issue.labels")
    priority_labels = [label for label in labels if re.fullmatch(r"priority:p[0-3]", label.lower())]
    priority = priority_labels[0].split(":", 1)[1].upper() if priority_labels else "P2"
    blocked_by = mapping.get("blockedBy")
    if blocked_by is None:
        blocked_by = []
    elif isinstance(blocked_by, dict):
        nodes = blocked_by.get("nodes")
        total_count = blocked_by.get("totalCount")
        if not isinstance(nodes, list) or not isinstance(total_count, int) or isinstance(total_count, bool):
            raise BoundaryError("GitHub returned invalid issue dependencies")
        if total_count != len(nodes):
            raise BoundaryError("GitHub returned truncated issue dependencies")
        blocked_by = nodes
    if not isinstance(blocked_by, list):
        raise BoundaryError("GitHub returned invalid issue dependencies")
    return {
        "number": _raw_positive_integer(mapping, "number", "GitHub issue"),
        "priority": priority,
        "dependencies": sorted(
            _raw_positive_integer(item, "number", "GitHub issue dependency")
            for item in blocked_by
        ),
        "claimed": "agent:claimed" in {label.lower() for label in labels},
        "created_at": _raw_string(mapping, "createdAt", "GitHub issue"),
        "state": _raw_string(mapping, "state", "GitHub issue").lower(),
    }


def _normalize_github_pr(
    value: Any,
    default_branch: str,
    branch_prs: dict[str, list[Any]],
    comments: dict[int, list[Any]],
) -> Optional[dict[str, Any]]:
    mapping = _mapping(value, "GitHub pull request")
    closing = mapping.get("closingIssuesReferences", [])
    if not isinstance(closing, list) or not closing:
        return None
    if len(closing) != 1:
        raise BoundaryError("managed pull request must close exactly one issue")
    number = _raw_positive_integer(mapping, "number", "GitHub pull request")
    base_ref = _raw_string(mapping, "baseRefName", "GitHub pull request")
    parents = branch_prs.get(base_ref, [])
    if base_ref == default_branch:
        parent = None
    elif len(parents) == 1:
        parent = parents[0]
    else:
        raise BoundaryError("pull request stack parent is missing or ambiguous")
    parent_number = None if parent is None else _raw_positive_integer(parent, "number", "parent pull request")
    parent_head = None if parent is None else _raw_string(parent, "headRefOid", "parent pull request")
    comment_values = comments.get(number, [])
    if not isinstance(comment_values, list):
        raise BoundaryError("GitHub returned invalid pull request comments")
    bodies = [_raw_string(item, "body", "pull request comment") for item in comment_values]
    artifacts = parse_comment_artifacts(bodies)
    labels = _github_labels(mapping.get("labels"), "GitHub pull request.labels")
    state = _raw_string(mapping, "state", "GitHub pull request").lower()
    return {
        "number": number,
        "issue_number": _raw_positive_integer(closing[0], "number", "closing issue"),
        "state": state,
        "draft": _raw_boolean(mapping, "isDraft", "GitHub pull request"),
        "head_sha": _raw_string(mapping, "headRefOid", "GitHub pull request"),
        "base_ref": base_ref,
        "parent_pr": parent_number,
        "parent_head_sha": parent_head,
        "checks": _normalize_github_checks(mapping.get("statusCheckRollup")),
        "findings": artifacts["findings"],
        "review_proofs": artifacts["review_proofs"],
        "test_proofs": artifacts["test_proofs"],
        "ready": "ready-for-merge" in {label.lower() for label in labels},
    }


def _normalize_github_checks(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise BoundaryError("GitHub returned invalid status checks")
    checks = []
    for position, item in enumerate(value):
        mapping = _mapping(item, f"GitHub status check[{position}]")
        name = mapping.get("name") or mapping.get("context")
        if not isinstance(name, str) or not name:
            raise BoundaryError("GitHub returned invalid status check name")
        conclusion = str(mapping.get("conclusion") or mapping.get("state") or "").upper()
        status = str(mapping.get("status") or "").upper()
        if conclusion in {"SUCCESS", "NEUTRAL", "SKIPPED"}:
            normalized = conclusion.lower()
        elif conclusion in {"FAILURE", "ERROR", "TIMED_OUT", "ACTION_REQUIRED"}:
            normalized = "failure"
        elif conclusion in {"CANCELLED", "STALE"}:
            normalized = "cancelled"
        elif status in {"QUEUED", "IN_PROGRESS", "PENDING", "EXPECTED", "REQUESTED", "WAITING"}:
            normalized = "pending"
        else:
            normalized = "pending"
        checks.append({"name": name, "status": normalized})
    return checks


def _github_labels(value: Any, path: str) -> list[str]:
    if not isinstance(value, list):
        raise BoundaryError(f"GitHub returned invalid {path}")
    return [_raw_string(item, "name", path) for item in value]


def _raw_string(mapping: Any, key: str, path: str) -> str:
    return _string(_mapping(mapping, path), key, path)


def _raw_positive_integer(mapping: Any, key: str, path: str) -> int:
    return _positive_integer(_mapping(mapping, path), key, path)


def _raw_boolean(mapping: Any, key: str, path: str) -> bool:
    return _boolean(_mapping(mapping, path), key, path)


def parse_snapshot(value: Any) -> RepositorySnapshot:
    mapping = _mapping(value, "snapshot")
    version = _integer(mapping, "version", "snapshot")
    if version != STATE_VERSION:
        raise BoundaryError(f"snapshot.version must be {STATE_VERSION}")
    repository = _string(mapping, "repository", "snapshot")
    issues_value = _list(mapping, "issues", "snapshot")
    prs_value = _list(mapping, "pull_requests", "snapshot")
    issues = tuple(sorted((_parse_issue(item, index) for index, item in enumerate(issues_value)), key=lambda item: item.number))
    prs = tuple(sorted((_parse_pr(item, index) for index, item in enumerate(prs_value)), key=lambda item: item.number))
    _unique_numbers(issues, "snapshot.issues")
    _unique_numbers(prs, "snapshot.pull_requests")
    active_by_issue: dict[int, list[int]] = {}
    for pr in prs:
        if pr.state == "open":
            active_by_issue.setdefault(pr.issue_number, []).append(pr.number)
    for issue_number, numbers in sorted(active_by_issue.items()):
        if len(numbers) > 1:
            rendered = ",".join(str(number) for number in sorted(numbers))
            raise BoundaryError(f"issue #{issue_number} has multiple open managed pull requests: {rendered}")
    return RepositorySnapshot(repository=repository, issues=issues, pull_requests=prs)


def reconcile(previous: ProgramState, snapshot: RepositorySnapshot) -> ProgramState:
    if previous.repository != snapshot.repository:
        raise BoundaryError("snapshot.repository must match state.repository")
    pending = previous.pending_action
    candidate = ProgramState(
        repository=snapshot.repository,
        issues=snapshot.issues,
        pull_requests=snapshot.pull_requests,
        pending_action=pending,
        run_attempt=previous.run_attempt,
        policy_digest=previous.policy_digest,
    )
    if pending is not None and _action_observed(candidate, pending):
        return replace(candidate, pending_action=None, run_attempt=None)
    return candidate


def reserve_next_action(state: ProgramState) -> ProgramState:
    if state.pending_action is not None:
        return state
    return replace(state, pending_action=_plan_action(state), run_attempt=None)


def ready_check(state: ProgramState, pr_number: int, policy_digest: Optional[str] = None) -> ReadyVerdict:
    pr = _pr_by_number(state, pr_number)
    if pr is None:
        return ReadyVerdict(False, pr_number, None, None, ("pr_not_found",))
    reasons: list[str] = []
    if pr.state != "open":
        reasons.append("pr_not_open")
    if pr.draft:
        reasons.append("draft")
    if not _checks_successful(pr):
        reasons.append("checks_not_successful")
    if _has_blocking_findings(pr):
        reasons.append("unresolved_p0_p1")
    required_digest = policy_digest if policy_digest is not None else state.policy_digest
    if not _has_current_proof(pr.review_proofs, pr, required_digest):
        reasons.append("missing_review_proof")
    if not _has_current_proof(pr.test_proofs, pr, required_digest):
        reasons.append("missing_test_proof")
    if not _valid_parent(state, pr):
        reasons.append("invalid_stack_parent")
    return ReadyVerdict(
        ready=not reasons,
        pr_number=pr.number,
        head_sha=pr.head_sha,
        stack_fingerprint=pr.fingerprint,
        reasons=tuple(reasons),
    )


def execute_action(
    state: ProgramState,
    action_id: str,
    adapter: Optional[GitHubAdapter] = None,
    apply: bool = False,
) -> dict[str, Any]:
    action = _require_action(state, action_id)
    github = adapter or GitHubAdapter()
    if action.kind == "claim_issue":
        argv = [
            "gh", "issue", "edit", str(action.issue_number), "--repo", state.repository,
            "--add-label", "agent:claimed",
        ]
        result = _mutation_result("claim_issue", argv)
        if apply:
            live = github.snapshot(state.repository)
            issue = next((item for item in live.issues if item.number == action.issue_number), None)
            if issue is None or issue.state == "closed" or issue.claimed:
                result["status"] = "observed"
                return result
            github.mutate(argv)
            result["status"] = "applied"
        return result
    if action.kind in {"implement_issue", "review_pr", "patch_pr", "verify_pr"}:
        return {
            "status": "ticket_run",
            "envelope": _ticket_run_envelope(state, action),
        }
    if action.kind == "mark_ready":
        live = github.snapshot(state.repository)
        live_pr = next((item for item in live.pull_requests if item.number == action.pr_number), None)
        argv = [
            "gh", "pr", "edit", str(action.pr_number), "--repo", state.repository,
            "--add-label", "READY-FOR-MERGE",
        ]
        result = _mutation_result("mark_ready", argv)
        refreshed = reconcile(state, live)
        if (
            live_pr is None
            or live_pr.head_sha != action.head_sha
            or live_pr.fingerprint != action.stack_fingerprint
        ):
            raise BoundaryError("action is stale after live refresh")
        verdict = ready_check(refreshed, live_pr.number, state.policy_digest)
        if not verdict.ready:
            raise BoundaryError(f"pull request is not ready: {','.join(verdict.reasons)}")
        if live_pr.ready:
            result["status"] = "observed"
            return result
        if refreshed.pending_action is None or refreshed.pending_action.action_id != action_id:
            raise BoundaryError("action is stale after live refresh")
        if apply:
            github.mutate(argv)
            result["status"] = "applied"
        return result
    return {
        "action_id": action.action_id,
        "kind": action.kind,
        "status": "no_mutation",
    }


def complete_action(
    state: ProgramState,
    action_id: str,
    result: Any,
    adapter: Optional[GitHubAdapter] = None,
    apply: bool = False,
) -> dict[str, Any]:
    action = _require_action(state, action_id)
    if action.kind not in {"review_pr", "verify_pr"}:
        raise BoundaryError("only review_pr and verify_pr actions accept proof completion")
    if action.pr_number is None:
        raise BoundaryError("proof action has no pull request")
    current_pr = _pr_by_number(state, action.pr_number)
    if (
        current_pr is None
        or current_pr.head_sha != action.head_sha
        or current_pr.fingerprint != action.stack_fingerprint
        or not _valid_parent(state, current_pr)
    ):
        raise BoundaryError("action is stale")
    mapping = _parse_agent_result(action, result)
    passed = mapping["passed"]
    summary = mapping["summary"]
    kind = "review" if action.kind == "review_pr" else "test"
    marker = proof_marker(kind, action.action_id, action.head_sha, action.stack_fingerprint, passed, state.policy_digest)
    body_parts = [marker, summary]
    findings = mapping.get("findings", [])
    for finding in findings:
        finding_payload = json.dumps(
            {
                "finding_id": finding["finding_id"],
                "head_sha": action.head_sha,
                "resolved": finding["resolved"],
                "severity": finding["severity"].upper(),
                "stack_fingerprint": action.stack_fingerprint,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        body_parts.append(f"<!-- orch-finding:{finding_payload} -->")
    body = "\n\n".join(body_parts)
    argv = [
        "gh", "pr", "comment", str(action.pr_number), "--repo", state.repository,
        "--body", body,
    ]
    response = _mutation_result(f"complete_{kind}", argv, body)
    if apply:
        github = adapter or GitHubAdapter()
        if any(marker in existing for existing in github.comment_bodies(state.repository, action.pr_number)):
            response["status"] = "observed"
            return response
        refreshed = reconcile(state, github.snapshot(state.repository))
        _require_action(refreshed, action_id)
        github.mutate(argv)
        response["status"] = "applied"
    return response


def _require_action(state: ProgramState, action_id: str) -> PendingAction:
    action = state.pending_action
    if action is None or action.action_id != action_id:
        raise BoundaryError("action_id does not match the pending action")
    if action.pr_number is not None:
        pr = _pr_by_number(state, action.pr_number)
        if pr is None or pr.head_sha != action.head_sha or pr.fingerprint != action.stack_fingerprint:
            raise BoundaryError("action is stale")
    return action


def _ticket_run_envelope(
    state: ProgramState,
    action: PendingAction,
    policy: Optional[RunPolicy] = None,
    verification_results: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    target = (
        f"PR #{action.pr_number}" if action.pr_number is not None else f"issue #{action.issue_number}"
    )
    action_instruction = {
        "implement_issue": "Implement the issue acceptance criteria, run proof tests, push the ticket branch, and open its correctly based PR.",
        "review_pr": "Invoke $mattpocock-skills:code-review on the current PR head and report every finding with severity and resolution state.",
        "patch_pr": "Patch the unresolved review findings only, run focused proof tests, and push the updated head.",
        "verify_pr": "Run the trusted repository verification commands and report their exact exit status and evidence.",
    }[action.kind]
    identity = {
        "action_id": action.action_id,
        "head_sha": action.head_sha,
        "issue_number": action.issue_number,
        "pr_number": action.pr_number,
        "stack_fingerprint": action.stack_fingerprint,
    }
    contracts = {
        "implement_issue": {**identity, "completed": True, "summary": "string"},
        "patch_pr": {**identity, "completed": True, "summary": "string"},
        "review_pr": {
            **identity,
            "findings": [{"finding_id": "stable-string", "resolved": False, "severity": "P0|P1|P2|P3"}],
            "passed": True,
            "summary": "string",
        },
        "verify_pr": {**identity, "passed": True, "summary": "string"},
    }
    findings_section = ""
    if action.kind in {"review_pr", "patch_pr"} and action.pr_number is not None:
        pr = _pr_by_number(state, action.pr_number)
        findings = [] if pr is None else [finding.to_dict() for finding in pr.findings]
        findings_section = (
            "\nCurrent identified findings, verbatim as JSON:\n"
            f"{json.dumps(findings, separators=(',', ':'), sort_keys=True)}\n"
            "Preserve each finding_id when reporting the same finding or resolving it.\n"
        )
    verification_section = ""
    if action.kind == "verify_pr" and policy is not None:
        commands = [list(command.argv) for command in policy.verification_commands]
        verification_section = (
            "\nVerification commands, selected only by policy, verbatim as JSON argv arrays:\n"
            f"{json.dumps(commands, separators=(',', ':'))}\n"
        )
        if verification_results is not None:
            verification_section += (
                "Orchestrator-observed exact command results:\n"
                f"{json.dumps(verification_results, separators=(',', ':'), sort_keys=True)}\n"
            )
    contract = json.dumps(contracts[action.kind], separators=(",", ":"), sort_keys=True)
    prompt = (
        "$pstack:poteto-mode\n\n"
        f"Execute orchestrator action {action.kind} for {target} in {state.repository}.\n"
        f"Action ID: {action.action_id}\n"
        f"Expected head SHA: {action.head_sha or 'none'}\n"
        f"Expected stack fingerprint: {action.stack_fingerprint or 'none'}.\n\n"
        f"{action_instruction}\n"
        f"{findings_section}"
        f"{verification_section}\n"
        "Work only on this ticket. Preserve unrelated changes. Do not label the PR READY-FOR-MERGE.\n"
        "Write exactly one JSON object to stdout. Use this exact schema and identity values:\n"
        f"{contract}\n"
        "Output JSON only. No Markdown. No extra keys."
    )
    return {
        "action_id": action.action_id,
        "head_sha": action.head_sha,
        "issue_number": action.issue_number,
        "kind": action.kind,
        "pr_number": action.pr_number,
        "prompt": prompt,
        "repository": state.repository,
        "stack_fingerprint": action.stack_fingerprint,
    }


def _mutation_result(kind: str, argv: list[str], body: Optional[str] = None) -> dict[str, Any]:
    mutation: dict[str, Any] = {"argv": argv}
    if body is not None:
        mutation["body"] = body
    return {"kind": kind, "mutation": mutation, "status": "planned"}


def _plan_action(state: ProgramState) -> PendingAction:
    open_issues = [item for item in state.issues if item.state == "open"]
    if not open_issues:
        open_prs = [item for item in state.pull_requests if item.state == "open"]
        if open_prs:
            pr = min(open_prs, key=lambda item: item.number)
            return _make_action("wait", _issue_by_number(state, pr.issue_number), pr)
        return _make_action("complete")
    closed_numbers = {item.number for item in state.issues if item.state == "closed"}
    eligible = [item for item in open_issues if set(item.dependencies).issubset(closed_numbers)]
    if not eligible:
        return _make_action("wait")
    selected = min(eligible, key=lambda item: (PRIORITIES[item.priority], item.created_at, item.number))
    prs = [item for item in state.pull_requests if item.issue_number == selected.number]
    active = next((item for item in prs if item.state == "open"), None)
    merged = next((item for item in prs if item.state == "merged"), None)
    if active is None and merged is not None:
        return _make_action("wait_for_merge", selected, merged)
    if active is None:
        return _make_action("implement_issue" if selected.claimed else "claim_issue", selected)
    if active.draft:
        return _make_action("implement_issue", selected, active)
    if not _valid_parent(state, active):
        return _make_action("wait", selected, active)
    if _has_blocking_findings(active):
        return _make_action("patch_pr", selected, active)
    if not _has_current_proof(active.review_proofs, active, state.policy_digest):
        return _make_action("review_pr", selected, active)
    if not _has_current_proof(active.test_proofs, active, state.policy_digest):
        return _make_action("verify_pr", selected, active)
    if not _checks_successful(active):
        return _make_action("wait_for_ci", selected, active)
    if not active.ready:
        return _make_action("mark_ready", selected, active)
    return _make_action("wait_for_merge", selected, active)


def _make_action(kind: str, issue: Optional[IssueSnapshot] = None, pr: Optional[PullRequestSnapshot] = None) -> PendingAction:
    identity = {
        "head_sha": None if pr is None else pr.head_sha,
        "issue_number": None if issue is None else issue.number,
        "kind": kind,
        "pr_number": None if pr is None else pr.number,
        "stack_fingerprint": None if pr is None else pr.fingerprint,
    }
    encoded = json.dumps(identity, separators=(",", ":"), sort_keys=True).encode()
    return PendingAction(action_id=hashlib.sha256(encoded).hexdigest()[:20], **identity)


def _action_observed(state: ProgramState, action: PendingAction) -> bool:
    issue = _issue_by_number(state, action.issue_number)
    pr = _pr_by_number(state, action.pr_number)
    if action.kind == "claim_issue":
        return issue is None or issue.state == "closed" or issue.claimed
    if action.kind == "implement_issue":
        return issue is None or issue.state == "closed" or any(
            item.issue_number == action.issue_number and item.state in {"open", "merged"}
            for item in state.pull_requests
        )
    if action.kind in {"review_pr", "patch_pr", "verify_pr", "wait_for_ci", "mark_ready"}:
        if pr is None or pr.head_sha != action.head_sha or pr.fingerprint != action.stack_fingerprint:
            return True
    if action.kind == "review_pr":
        return _has_blocking_findings(pr) or _has_current_proof(pr.review_proofs, pr, state.policy_digest)
    if action.kind == "patch_pr":
        return not _has_blocking_findings(pr)
    if action.kind == "verify_pr":
        return _has_current_proof(pr.test_proofs, pr, state.policy_digest)
    if action.kind == "wait_for_ci":
        return _checks_successful(pr)
    if action.kind == "mark_ready":
        return pr.ready
    if action.kind == "wait_for_merge":
        return issue is None or issue.state == "closed" or (pr is not None and pr.state == "merged")
    if action.kind == "wait":
        return True
    if action.kind == "complete":
        return not any(item.state == "open" for item in state.issues)
    return False


def _has_current_proof(
    receipts: tuple[ProofReceipt, ...],
    pr: PullRequestSnapshot,
    policy_digest: Optional[str] = None,
) -> bool:
    return any(
        receipt.passed
        and receipt.head_sha == pr.head_sha
        and receipt.stack_fingerprint == pr.fingerprint
        and (policy_digest is None or receipt.policy_digest == policy_digest)
        for receipt in receipts
    )


def _has_blocking_findings(pr: PullRequestSnapshot) -> bool:
    return any(
        not finding.resolved
        and finding.severity in {"P0", "P1"}
        and (not finding.head_sha or finding.head_sha == pr.head_sha)
        and (not finding.stack_fingerprint or finding.stack_fingerprint == pr.fingerprint)
        for finding in pr.findings
    )


def _checks_successful(pr: PullRequestSnapshot) -> bool:
    return bool(pr.checks) and all(check.status == "success" for check in pr.checks)


def _valid_parent(state: ProgramState, pr: PullRequestSnapshot) -> bool:
    if pr.parent_pr is None:
        return pr.parent_head_sha is None
    parent = _pr_by_number(state, pr.parent_pr)
    return parent is not None and parent.state in {"open", "merged"} and parent.head_sha == pr.parent_head_sha


def _issue_by_number(state: ProgramState, number: Optional[int]) -> Optional[IssueSnapshot]:
    return next((item for item in state.issues if item.number == number), None)


def _pr_by_number(state: ProgramState, number: Optional[int]) -> Optional[PullRequestSnapshot]:
    return next((item for item in state.pull_requests if item.number == number), None)


def _parse_issue(value: Any, index: int) -> IssueSnapshot:
    path = f"snapshot.issues[{index}]"
    mapping = _mapping(value, path)
    priority = _string(mapping, "priority", path).upper()
    if priority not in PRIORITIES:
        raise BoundaryError(f"{path}.priority must be one of P0, P1, P2, P3")
    state = _string(mapping, "state", path)
    if state not in ISSUE_STATES:
        raise BoundaryError(f"{path}.state must be open or closed")
    dependencies = tuple(sorted(_integer_value(item, f"{path}.dependencies[{position}]") for position, item in enumerate(_list(mapping, "dependencies", path))))
    return IssueSnapshot(
        number=_positive_integer(mapping, "number", path),
        priority=priority,
        dependencies=dependencies,
        claimed=_boolean(mapping, "claimed", path),
        created_at=_string(mapping, "created_at", path),
        state=state,
    )


def _parse_pr(value: Any, index: int) -> PullRequestSnapshot:
    path = f"snapshot.pull_requests[{index}]"
    mapping = _mapping(value, path)
    state = _string(mapping, "state", path)
    if state not in PR_STATES:
        raise BoundaryError(f"{path}.state must be open, closed, or merged")
    parent_pr = _optional_positive_integer(mapping.get("parent_pr"), f"{path}.parent_pr")
    parent_head_sha = _optional_string(mapping.get("parent_head_sha"), f"{path}.parent_head_sha")
    if (parent_pr is None) != (parent_head_sha is None):
        raise BoundaryError(f"{path}.parent_pr and parent_head_sha must both be set or both be null")
    checks = tuple(_parse_check(item, path, position) for position, item in enumerate(_list(mapping, "checks", path)))
    findings = tuple(_parse_finding(item, path, position) for position, item in enumerate(_list(mapping, "findings", path)))
    review_proofs = tuple(_parse_proof(item, f"{path}.review_proofs[{position}]") for position, item in enumerate(_list(mapping, "review_proofs", path)))
    test_proofs = tuple(_parse_proof(item, f"{path}.test_proofs[{position}]") for position, item in enumerate(_list(mapping, "test_proofs", path)))
    return PullRequestSnapshot(
        number=_positive_integer(mapping, "number", path),
        issue_number=_positive_integer(mapping, "issue_number", path),
        state=state,
        draft=_boolean(mapping, "draft", path),
        head_sha=_string(mapping, "head_sha", path),
        base_ref=_string(mapping, "base_ref", path),
        parent_pr=parent_pr,
        parent_head_sha=parent_head_sha,
        checks=tuple(sorted(checks, key=lambda item: item.name)),
        findings=tuple(sorted(findings, key=lambda item: (item.severity, item.resolved))),
        review_proofs=tuple(sorted(review_proofs, key=lambda item: (item.head_sha, item.stack_fingerprint, item.passed))),
        test_proofs=tuple(sorted(test_proofs, key=lambda item: (item.head_sha, item.stack_fingerprint, item.passed))),
        ready=_boolean(mapping, "ready", path),
    )


def _parse_check(value: Any, parent: str, index: int) -> CheckSnapshot:
    path = f"{parent}.checks[{index}]"
    mapping = _mapping(value, path)
    status = _string(mapping, "status", path)
    if status not in CHECK_STATES:
        raise BoundaryError(f"{path}.status must be success, failure, pending, cancelled, skipped, or neutral")
    return CheckSnapshot(name=_string(mapping, "name", path), status=status)


def _parse_finding(value: Any, parent: str, index: int) -> FindingSnapshot:
    path = f"{parent}.findings[{index}]"
    mapping = _mapping(value, path)
    severity = _string(mapping, "severity", path).upper()
    if severity not in PRIORITIES:
        raise BoundaryError(f"{path}.severity must be one of P0, P1, P2, P3")
    finding_id = mapping.get("finding_id", "")
    head_sha = mapping.get("head_sha", "")
    fingerprint = mapping.get("stack_fingerprint", "")
    for value_name, item in (("finding_id", finding_id), ("head_sha", head_sha), ("stack_fingerprint", fingerprint)):
        if not isinstance(item, str):
            raise BoundaryError(f"{path}.{value_name} must be a string")
    if not finding_id:
        encoded = json.dumps(mapping, separators=(",", ":"), sort_keys=True).encode()
        finding_id = "legacy-" + hashlib.sha256(encoded).hexdigest()[:20]
    return FindingSnapshot(severity, _boolean(mapping, "resolved", path), finding_id, head_sha, fingerprint)


def _parse_proof(value: Any, path: str) -> ProofReceipt:
    mapping = _mapping(value, path)
    return ProofReceipt(
        head_sha=_string(mapping, "head_sha", path),
        stack_fingerprint=_string(mapping, "stack_fingerprint", path),
        passed=_boolean(mapping, "passed", path),
        policy_digest=_optional_string(mapping.get("policy_digest"), f"{path}.policy_digest"),
    )


def _parse_attempt(value: Any) -> RunAttempt:
    mapping = _strict_mapping(value, "state.run_attempt", {"action_id", "count"})
    return RunAttempt(
        _string(mapping, "action_id", "state.run_attempt"),
        _positive_integer(mapping, "count", "state.run_attempt"),
    )


def _parse_pending(value: Any) -> PendingAction:
    path = "state.pending_action"
    mapping = _mapping(value, path)
    return PendingAction(
        action_id=_string(mapping, "action_id", path),
        kind=_string(mapping, "kind", path),
        issue_number=_optional_positive_integer(mapping.get("issue_number"), f"{path}.issue_number"),
        pr_number=_optional_positive_integer(mapping.get("pr_number"), f"{path}.pr_number"),
        head_sha=_optional_string(mapping.get("head_sha"), f"{path}.head_sha"),
        stack_fingerprint=_optional_string(mapping.get("stack_fingerprint"), f"{path}.stack_fingerprint"),
    )


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BoundaryError(f"{path} must be an object")
    return value


def _strict_mapping(value: Any, path: str, keys: set[str]) -> dict[str, Any]:
    mapping = _mapping(value, path)
    unknown = sorted(set(mapping) - keys)
    missing = sorted(keys - set(mapping))
    if unknown:
        raise BoundaryError(f"{path} has unknown keys: {','.join(unknown)}")
    if missing:
        raise BoundaryError(f"{path} is missing keys: {','.join(missing)}")
    return mapping


def _argv(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise BoundaryError(f"{path} must be a non-empty argv array")
    if any(not isinstance(item, str) or not item for item in value):
        raise BoundaryError(f"{path} must contain only non-empty strings")
    return tuple(value)


def _positive_number(value: Any, path: str, allow_zero: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise BoundaryError(f"{path} must be a number")
    result = float(value)
    if result < 0 or (result == 0 and not allow_zero):
        raise BoundaryError(f"{path} must be {'non-negative' if allow_zero else 'positive'}")
    return result


def _list(mapping: dict[str, Any], key: str, path: str) -> list[Any]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise BoundaryError(f"{path}.{key} must be an array")
    return value


def _string(mapping: dict[str, Any], key: str, path: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise BoundaryError(f"{path}.{key} must be a non-empty string")
    return value


def _optional_string(value: Any, path: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise BoundaryError(f"{path} must be a non-empty string or null")
    return value


def _boolean(mapping: dict[str, Any], key: str, path: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise BoundaryError(f"{path}.{key} must be a boolean")
    return value


def _integer(mapping: dict[str, Any], key: str, path: str) -> int:
    return _integer_value(mapping.get(key), f"{path}.{key}")


def _integer_value(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise BoundaryError(f"{path} must be an integer")
    return value


def _positive_integer(mapping: dict[str, Any], key: str, path: str) -> int:
    value = _integer(mapping, key, path)
    if value <= 0:
        raise BoundaryError(f"{path}.{key} must be positive")
    return value


def _optional_positive_integer(value: Any, path: str) -> Optional[int]:
    if value is None:
        return None
    parsed = _integer_value(value, path)
    if parsed <= 0:
        raise BoundaryError(f"{path} must be positive or null")
    return parsed


def _unique_numbers(items: tuple[Any, ...], path: str) -> None:
    numbers = [item.number for item in items]
    if len(numbers) != len(set(numbers)):
        raise BoundaryError(f"{path} numbers must be unique")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except OSError as error:
        raise BoundaryError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise BoundaryError(f"{path} is not valid JSON: {error.msg}") from error


def _load_state(path: Path) -> ProgramState:
    if not path.exists():
        raise BoundaryError(f"state file does not exist: {path}")
    return ProgramState.from_dict(_load_json(path))


def _run_gh(argv: list[str]) -> str:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    except OSError as error:
        raise GhCommandError("GitHub command could not start") from error
    if completed.returncode != 0:
        raise GhCommandError("GitHub command failed")
    return completed.stdout


def _write_state(path: Path, state: ProgramState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n"
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None and os.path.exists(temporary_name):
            os.unlink(temporary_name)


@contextlib.contextmanager
def _state_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f"{path.name}.lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def _run_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    run_path = path.with_name(f"{path.name}.run.lock")
    state_path = path.with_name(f"{path.name}.lock")
    with run_path.open("a+") as run_lock, state_path.open("a+") as state_lock:
        try:
            fcntl.flock(run_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(state_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            with contextlib.suppress(OSError):
                fcntl.flock(run_lock.fileno(), fcntl.LOCK_UN)
            raise BoundaryError("another orchestrator command holds the state or whole-run lock") from error
        try:
            yield
        finally:
            fcntl.flock(state_lock.fileno(), fcntl.LOCK_UN)
            fcntl.flock(run_lock.fileno(), fcntl.LOCK_UN)


def _parse_agent_result(action: PendingAction, value: Any) -> dict[str, Any]:
    identity_keys = {"action_id", "head_sha", "issue_number", "pr_number", "stack_fingerprint"}
    if action.kind in {"implement_issue", "patch_pr"}:
        keys = identity_keys | {"completed", "summary"}
    elif action.kind == "review_pr":
        keys = identity_keys | {"findings", "passed", "summary"}
    else:
        keys = identity_keys | {"passed", "summary"}
    mapping = _strict_mapping(value, "agent result", keys)
    expected = {
        "action_id": action.action_id,
        "head_sha": action.head_sha,
        "issue_number": action.issue_number,
        "pr_number": action.pr_number,
        "stack_fingerprint": action.stack_fingerprint,
    }
    for key, expected_value in expected.items():
        if mapping.get(key) != expected_value:
            raise BoundaryError(f"agent result.{key} does not match action")
    _string(mapping, "summary", "agent result")
    if action.kind in {"implement_issue", "patch_pr"}:
        _boolean(mapping, "completed", "agent result")
    else:
        _boolean(mapping, "passed", "agent result")
    if action.kind == "review_pr":
        findings = _list(mapping, "findings", "agent result")
        for index, finding in enumerate(findings):
            path = f"agent result.findings[{index}]"
            parsed = _strict_mapping(finding, path, {"finding_id", "resolved", "severity"})
            _string(parsed, "finding_id", path)
            _boolean(parsed, "resolved", path)
            if _string(parsed, "severity", path).upper() not in PRIORITIES:
                raise BoundaryError(f"{path}.severity must be P0, P1, P2, or P3")
    return mapping


def _run_process(
    argv: list[str],
    cwd: Path,
    timeout: float,
    input_text: Optional[str] = None,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        shell=False,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(input=input_text, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(argv, timeout, output=stdout, stderr=stderr) from error
    return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


def _invoke_agent(policy: RunPolicy, prompt: str) -> Any:
    try:
        completed = _run_process(
            list(policy.agent_argv),
            policy.repository_root,
            policy.timeout_seconds,
            prompt,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BoundaryError("agent command failed") from error
    if completed.returncode != 0:
        raise BoundaryError(f"agent command exited with status {completed.returncode}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise BoundaryError("agent stdout must be exactly one JSON object") from error


def _require_verification_checkout(
    policy: RunPolicy,
    action: PendingAction,
    state_path: Optional[Path] = None,
) -> None:
    try:
        head = _run_process(["git", "rev-parse", "HEAD"], policy.repository_root, policy.timeout_seconds)
        status = _run_process(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            policy.repository_root,
            policy.timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BoundaryError("verification checkout could not be inspected") from error
    if head.returncode != 0 or status.returncode != 0:
        raise BoundaryError("policy.repository_root must be a Git worktree")
    if head.stdout.strip() != action.head_sha:
        raise BoundaryError("verification checkout HEAD does not match action.head_sha")
    allowed: set[str] = set()
    if state_path is not None:
        resolved = state_path.resolve()
        try:
            relative = resolved.relative_to(policy.repository_root).as_posix()
        except ValueError:
            pass
        else:
            allowed = {relative, f"{relative}.lock", f"{relative}.run.lock"}
    dirty = [line for line in status.stdout.splitlines() if line[3:] not in allowed]
    if dirty:
        raise BoundaryError("verification checkout must be clean except for orchestrator state")


def _run_verification_commands(
    policy: RunPolicy,
    action: PendingAction,
    state_path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    _require_verification_checkout(policy, action, state_path)
    results = []
    for command in policy.verification_commands:
        try:
            completed = _run_process(list(command.argv), policy.repository_root, policy.timeout_seconds)
            status = completed.returncode
        except subprocess.TimeoutExpired:
            status = 124
        except OSError:
            status = 127
        results.append({"argv": list(command.argv), "exit_status": status, "name": command.name})
    return results


def _refresh_run_state(
    state: ProgramState,
    adapter: GitHubAdapter,
    policy: RunPolicy,
    state_path: Path,
) -> ProgramState:
    if state.policy_digest != policy.digest:
        state = replace(state, run_attempt=None)
    refreshed = reconcile(state, adapter.snapshot(state.repository))
    refreshed = replace(refreshed, policy_digest=policy.digest)
    _write_state(state_path, refreshed)
    return refreshed


def run_program(
    repository: str,
    policy: RunPolicy,
    state_path: Path = DEFAULT_STATE,
    dry_run: bool = False,
    adapter: Optional[GitHubAdapter] = None,
    sleeper: Any = time.sleep,
) -> RunOutcome:
    github = adapter or GitHubAdapter()
    with _run_lock(state_path):
        state = _load_state(state_path) if state_path.exists() else ProgramState.empty(repository)
        if state.repository != repository:
            raise BoundaryError("state.repository must match --repo")
        while True:
            state = _refresh_run_state(state, github, policy, state_path)
            ready_prs = sorted(
                (pr for pr in state.pull_requests if pr.state == "open" and pr.ready),
                key=lambda pr: pr.number,
            )
            if ready_prs:
                pr = ready_prs[0]
                verdict = ready_check(state, pr.number, policy.digest)
                if verdict.ready:
                    return RunOutcome("ready_for_merge", "READY-FOR-MERGE label observed after all gates passed", pr_number=pr.number)
                return RunOutcome("blocked", f"READY-FOR-MERGE gates failed: {','.join(verdict.reasons)}", pr_number=pr.number)
            state = reserve_next_action(state)
            _write_state(state_path, state)
            action = state.pending_action
            if action is None:
                raise BoundaryError("planner did not reserve an action")
            if action.kind == "complete":
                return RunOutcome("complete", "no open managed issues", action.action_id)
            if action.kind == "wait":
                reason = (
                    "no open issues, but an open managed pull request remains"
                    if not any(issue.state == "open" for issue in state.issues) and action.pr_number is not None
                    else "no eligible issue; dependencies or stack parent are unresolved"
                )
                return RunOutcome("blocked", reason, action.action_id, action.pr_number)
            if action.kind == "wait_for_merge":
                return RunOutcome("blocked", "pull request is waiting for human merge", action.action_id, action.pr_number)
            if dry_run:
                return RunOutcome("planned", f"dry run planned {action.kind}", action.action_id, action.pr_number)
            if action.kind == "wait_for_ci":
                pr = _pr_by_number(state, action.pr_number)
                pending = [] if pr is None else [check for check in pr.checks if check.status == "pending"]
                terminal = [] if pr is None else [check for check in pr.checks if check.status not in {"success", "pending"}]
                if terminal or not pending:
                    statuses = "no pending checks" if not terminal else ",".join(
                        f"{check.name}={check.status}" for check in terminal
                    )
                    return RunOutcome("blocked", f"status checks are terminal non-success: {statuses}", action.action_id, action.pr_number)

            previous_count = state.run_attempt.count if state.run_attempt and state.run_attempt.action_id == action.action_id else 0
            if previous_count >= policy.max_attempts:
                return RunOutcome("failed", "retry exhaustion: attempt budget was already consumed", action.action_id, action.pr_number)
            attempt = RunAttempt(action.action_id, previous_count + 1)
            state = replace(state, run_attempt=attempt)
            _write_state(state_path, state)
            if action.kind == "wait_for_ci":
                sleeper(policy.poll_seconds)
                continue

            invocation_error: Optional[BoundaryError] = None
            try:
                if action.kind in {"claim_issue", "mark_ready"}:
                    execute_action(state, action.action_id, adapter=github, apply=True)
                else:
                    if action.kind in {"review_pr", "patch_pr"}:
                        _require_verification_checkout(policy, action, state_path)
                    verification_results = _run_verification_commands(policy, action, state_path) if action.kind == "verify_pr" else None
                    envelope = _ticket_run_envelope(state, action, policy, verification_results)
                    result = _parse_agent_result(action, _invoke_agent(policy, envelope["prompt"]))
                    if action.kind in {"review_pr", "verify_pr"}:
                        proof_result = dict(result)
                        if action.kind == "verify_pr":
                            proof_result["passed"] = bool(verification_results) and all(
                                item["exit_status"] == 0 for item in verification_results
                            ) and result["passed"]
                            proof_result["summary"] = json.dumps(verification_results, separators=(",", ":"), sort_keys=True)
                        complete_action(state, action.action_id, proof_result, adapter=github, apply=True)
            except BoundaryError as error:
                invocation_error = error

            state = _refresh_run_state(state, github, policy, state_path)
            if state.pending_action is None or state.pending_action.action_id != action.action_id:
                continue
            if attempt.count >= policy.max_attempts:
                reason = str(invocation_error) if invocation_error else f"{action.kind} postcondition was not observed"
                return RunOutcome("failed", f"retry exhaustion: {reason}", action.action_id, action.pr_number)
            sleeper(policy.poll_seconds)


def _emit(value: Any, stream: Any = sys.stdout) -> None:
    is_terminal = bool(getattr(stream, "isatty", lambda: False)())
    print(json.dumps(value, indent=2 if is_terminal else None, sort_keys=True), file=stream)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orch")
    commands = parser.add_subparsers(dest="command", required=True)
    reconcile_parser = commands.add_parser("reconcile")
    reconcile_source = reconcile_parser.add_mutually_exclusive_group(required=True)
    reconcile_source.add_argument("--snapshot", type=Path)
    reconcile_source.add_argument("--github", action="store_true")
    reconcile_parser.add_argument("--repo")
    reconcile_parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    next_parser = commands.add_parser("next")
    next_parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    ready_parser = commands.add_parser("ready-check")
    ready_parser.add_argument("--pr", type=int, required=True)
    ready_parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    execute_parser = commands.add_parser("execute")
    execute_parser.add_argument("--action-id", required=True)
    execute_parser.add_argument("--apply", action="store_true")
    execute_parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    complete_parser = commands.add_parser("complete")
    complete_parser.add_argument("--action-id", required=True)
    complete_parser.add_argument("--result", type=Path, required=True)
    complete_parser.add_argument("--apply", action="store_true")
    complete_parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--repo", required=True)
    run_parser.add_argument("--policy", type=Path, required=True)
    run_parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    run_parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    try:
        arguments = _build_parser().parse_args(argv)
        if arguments.command == "reconcile":
            if arguments.github:
                if not arguments.repo:
                    raise BoundaryError("reconcile --github requires --repo OWNER/REPO")
                normalized = GitHubAdapter().snapshot(arguments.repo)
            else:
                normalized = parse_snapshot(_load_json(arguments.snapshot))
            with _state_lock(arguments.state):
                old = _load_state(arguments.state) if arguments.state.exists() else ProgramState.empty(normalized.repository)
                state = reconcile(old, normalized)
                _write_state(arguments.state, state)
            _emit(state.to_dict())
            return 0
        if arguments.command == "next":
            with _state_lock(arguments.state):
                state = reserve_next_action(_load_state(arguments.state))
                _write_state(arguments.state, state)
            _emit(state.pending_action.to_dict())
            return 0
        if arguments.command == "ready-check":
            with _state_lock(arguments.state):
                verdict = ready_check(_load_state(arguments.state), arguments.pr)
            _emit(verdict.to_dict())
            return 0 if verdict.ready else 1
        if arguments.command == "execute":
            with _state_lock(arguments.state):
                state = _load_state(arguments.state)
            response = execute_action(state, arguments.action_id, apply=arguments.apply)
            _emit(response)
            return 0
        if arguments.command == "run":
            policy = RunPolicy.from_dict(_load_json(arguments.policy))
            outcome = run_program(
                arguments.repo,
                policy,
                state_path=arguments.state,
                dry_run=arguments.dry_run,
            )
            _emit(outcome.to_dict())
            return 0 if outcome.disposition in {"complete", "ready_for_merge", "planned"} else 1
        with _state_lock(arguments.state):
            state = _load_state(arguments.state)
        response = complete_action(
            state,
            arguments.action_id,
            _load_json(arguments.result),
            apply=arguments.apply,
        )
        _emit(response)
        return 0
    except BoundaryError as error:
        _emit({"error": str(error)}, sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
