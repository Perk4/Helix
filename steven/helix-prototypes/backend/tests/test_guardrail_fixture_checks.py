"""Promptfoo guardrail output parsing and its separation from candidate receipts."""

import json
import shutil
from pathlib import Path

from test_study_output_evaluation import ROOT, candidate

from app.candidate_evaluations import CandidateEvaluationService
from app.contract_schema import draft202012_validator
from app.run_plans import canonical_hash
from app.schemas import CandidateEvaluation, StoredSectionRun
from app.seed import load_seed_package
from app.study_output_evaluation import (
    load_promptfoo_guardrail_results,
    load_suite_asserts,
    suite_fixture_guardrail_checks,
)

FIXTURE = Path(__file__).parent / "fixtures" / "promptfoo" / "glp-guardrails-output.json"
SEED = ROOT / "synthetic-e2e" / "helix-synthetic-bundle.json"
STUDY_SUITE = ROOT / ".agents" / "skills" / "helix-section-agent" / "evals" / "study-output.yaml"
HASH = "sha256:" + "ab" * 32


def test_promptfoo_output_file_is_read_at_results_results() -> None:
    data = json.loads(FIXTURE.read_text())
    # The real promptfoo OutputFile shape: results is an EvaluateSummaryV3 object, not a list.
    assert data["results"]["version"] == 3
    assert isinstance(data["results"]["results"], list)

    results = load_promptfoo_guardrail_results(FIXTURE)

    assert [item.assertion for item in results] == [
        "G-1:G-1 holds when the NOAEL matches the findings",
        "G-1:G-1 catches a NOAEL set at a dose with adverse findings",
        "G-2:G-2 catches a non-adverse call asserted without criteria",
        "A-1:A-1 holds when prose stays within the claim's scope",
    ]
    assert [item.status for item in results] == ["passed", "passed", "failed", "passed"]
    assert results[2].message.startswith("The judge accepted")


def test_unexpected_or_unreadable_promptfoo_files_yield_no_results(tmp_path: Path) -> None:
    cases = {
        "legacy-list.json": {"results": [{"gradingResult": {}}]},
        "string-results.json": {"results": "oops"},
        "not-an-object.json": ["results"],
        "rows-not-objects.json": {"results": {"version": 3, "results": ["x", 1, None]}},
    }
    for name, payload in cases.items():
        path = tmp_path / name
        path.write_text(json.dumps(payload))
        assert load_promptfoo_guardrail_results(path) == []
    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    assert load_promptfoo_guardrail_results(broken) == []
    assert load_promptfoo_guardrail_results(tmp_path / "missing.json") == []


def test_fixture_checks_are_suite_level_and_marked_not_candidate_evaluated(tmp_path: Path) -> None:
    result_path = tmp_path / "promptfoo-guardrails-result.json"
    shutil.copy(FIXTURE, result_path)

    checks = suite_fixture_guardrail_checks(result_path, repository_root=tmp_path)

    assert checks is not None
    assert checks.scope == "suite_fixture"
    assert checks.candidate_evaluated is False
    assert checks.suite_path.endswith("glp-guardrails.yaml")
    assert checks.result_path == "promptfoo-guardrails-result.json"
    assert checks.result_hash.startswith("sha256:")
    assert {item.assertion.split(":", 1)[0] for item in checks.results} == {"G-1", "G-2", "A-1"}
    assert suite_fixture_guardrail_checks(tmp_path / "absent.json", repository_root=tmp_path) is None


def stored_run() -> StoredSectionRun:
    item = candidate("Terminal high-dose body weight was 286.2 g.")
    return StoredSectionRun.model_validate(
        {
            "receipt": {
                "run_id": item.run_id,
                "section_id": item.section_id,
                "section_package_id": item.section_package_id,
                "status": "candidate_recorded",
                "candidate_id": item.candidate_id,
                "candidate_hash": canonical_hash(item.model_dump(mode="json")),
                "envelope_hash": HASH,
                "agent_runtime": "codex_sdk",
                "codex_thread_id": "thread-test-001",
                "skill_name": "helix-section-agent",
                "skill_hash": HASH,
                "skill_references_hash": HASH,
                "review_scaffold_revision": 1,
            },
            "candidate": item.model_dump(mode="json"),
            "envelope": {},
            "review_scaffold": {},
        }
    )


def compile_with(result_path: Path) -> CandidateEvaluation:
    service = CandidateEvaluationService(None, ROOT)  # _compile touches no session
    service.guardrail_result_path = result_path
    return service._compile(load_seed_package(SEED), stored_run())


def test_candidate_receipt_never_contains_guardrail_verdicts_not_computed_on_it(tmp_path: Path) -> None:
    result_path = tmp_path / "promptfoo-guardrails-result.json"
    shutil.copy(FIXTURE, result_path)

    evaluation = compile_with(result_path)

    receipt = evaluation.study_output_evaluation_receipt
    suite_labels = {
        f"{kind}:{value}" if value is not None else kind for kind, value in load_suite_asserts(STUDY_SUITE)
    }
    receipt_labels = {item.assertion for item in receipt.results}
    # Only the deterministic study-output assertions run on this candidate are in its receipt.
    assert receipt_labels <= suite_labels
    assert not any(label.split(":", 1)[0] in {"G-1", "G-2", "A-1"} for label in receipt_labels)
    assert receipt.status == "passed"  # the failed G-2 fixture verdict does not flip the candidate

    # The fixture verdicts are kept, but apart, marked as a suite-level fixture check.
    checks = evaluation.suite_fixture_guardrail_checks
    assert checks is not None
    assert checks.candidate_evaluated is False
    assert len(checks.results) == 4
    # Nothing governed about the candidate changes when the fixture file is present.
    baseline = compile_with(tmp_path / "absent.json")
    assert receipt.results == baseline.study_output_evaluation_receipt.results
    assert evaluation.next_attempt_decision.action == baseline.next_attempt_decision.action
    assert evaluation.next_attempt_decision.reasons == baseline.next_attempt_decision.reasons
    assert evaluation.provenance_receipt.status == baseline.provenance_receipt.status

    schema_dir = ROOT / "skills" / "helix-evidence-pipeline" / "contracts"
    schema = json.loads((schema_dir / "candidate-evaluation.schema.json").read_text())
    payload = evaluation.model_dump(mode="json")
    assert payload["hashes"]["evaluation"] == canonical_hash(
        {key: value for key, value in payload.items() if key != "hashes"}
    )
    lying = json.loads(json.dumps(payload))
    lying["suite_fixture_guardrail_checks"]["candidate_evaluated"] = True
    validator = draft202012_validator(schema, schema_dir)
    assert not list(validator.iter_errors(payload))
    assert list(validator.iter_errors(lying))


def test_without_a_promptfoo_result_the_evaluation_has_no_fixture_checks(tmp_path: Path) -> None:
    evaluation = compile_with(tmp_path / "promptfoo-guardrails-result.json")
    assert evaluation.suite_fixture_guardrail_checks is None
    assert evaluation.study_output_evaluation_receipt.status == "passed"
