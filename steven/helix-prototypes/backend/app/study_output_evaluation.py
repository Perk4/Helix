import json
from pathlib import Path
from uuid import uuid4

from .run_plans import file_hash
from .schemas import (
    SectionDraftCandidate,
    StudyOutputAssertionResult,
    StudyOutputEvaluationReceipt,
    SuiteFixtureGuardrailChecks,
)

GUARDRAIL_SUITE_RELATIVE = ".agents/skills/helix-section-agent/evals/glp-guardrails.yaml"


def load_promptfoo_guardrail_results(path: Path) -> list[StudyOutputAssertionResult]:
    """Read the llm-rubric component verdicts from a promptfoo ``--output`` JSON file.

    promptfoo writes an ``OutputFile``: ``{"evalId", "results": EvaluateSummaryV3, "config", ...}``
    where ``EvaluateSummaryV3`` is ``{"version": 3, "timestamp", "results": [EvaluateResult],
    "prompts", "stats"}``. The per-test rows are therefore at ``results.results[]`` and each
    row's verdicts at ``gradingResult.componentResults[]``. Unreadable or unexpected files yield
    no results instead of raising.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    summary = data.get("results") if isinstance(data, dict) else None
    rows = summary.get("results") if isinstance(summary, dict) else None
    if not isinstance(rows, list):
        return []
    out: list[StudyOutputAssertionResult] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        grading = row.get("gradingResult")
        test_case = row.get("testCase")
        description = test_case.get("description", "") if isinstance(test_case, dict) else ""
        components = grading.get("componentResults") if isinstance(grading, dict) else None
        for component in components or []:
            if not isinstance(component, dict):
                continue
            assertion_info = component.get("assertion")
            if not isinstance(assertion_info, dict):
                assertion_info = {}
            metric = assertion_info.get("metric") or assertion_info.get("type") or "llm-rubric"
            label = f"{metric}:{description}" if description else str(metric)
            out.append(
                StudyOutputAssertionResult(
                    assertion=label,
                    status="passed" if component.get("pass") else "failed",
                    message=component.get("reason") or "No reason provided.",
                )
            )
    return out


def suite_fixture_guardrail_checks(
    result_path: Path, *, repository_root: Path
) -> SuiteFixtureGuardrailChecks | None:
    """Wrap the promptfoo guardrail verdicts as a suite-level fixture check.

    ``glp-guardrails.yaml`` runs its judges with an ``echo`` provider over canned fixtures, so
    its G-1/G-2/A-1 verdicts qualify the judge, not the evaluated candidate. They are kept for
    the record, but never inside a candidate's study-output receipt.
    """
    if not result_path.is_file():
        return None
    results = load_promptfoo_guardrail_results(result_path)
    if not results:
        return None
    try:
        relative = result_path.resolve().relative_to(repository_root.resolve()).as_posix()
    except ValueError:
        relative = result_path.name
    return SuiteFixtureGuardrailChecks(
        schema_version="helix.suite-fixture-guardrail-checks/v1",
        scope="suite_fixture",
        candidate_evaluated=False,
        suite_path=GUARDRAIL_SUITE_RELATIVE,
        result_path=relative,
        result_hash=file_hash(result_path),
        results=results,
    )


def evaluate_study_output(
    candidate: SectionDraftCandidate,
    *,
    candidate_hash: str,
    suite_id: str,
    suite_version: str,
    suite_path: Path,
    receipt_id: str | None = None,
) -> StudyOutputEvaluationReceipt:
    payload = json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False)
    results: list[StudyOutputAssertionResult] = []
    for assertion_type, expected in load_suite_asserts(suite_path):
        results.append(_apply(assertion_type, expected, payload, candidate.model_dump(mode="json")))
    failed = any(item.status == "failed" for item in results)
    return StudyOutputEvaluationReceipt(
        schema_version="helix.study-output-evaluation-receipt/v1",
        receipt_id=receipt_id or f"SOE-{uuid4().hex[:12].upper()}",
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate_hash,
        suite_id=suite_id,
        suite_version=suite_version,
        suite_hash=file_hash(suite_path),
        status="failed" if failed else "passed",
        enforcement_class="review_required",
        waivable=False,
        results=results,
    )


def load_suite_asserts(path: Path) -> list[tuple[str, str | None]]:
    asserts: list[tuple[str, str | None]] = []
    pending: str | None = None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line.startswith("- type:"):
            pending = line.split(":", 1)[1].strip()
            if pending == "is-json":
                asserts.append((pending, None))
                pending = None
            continue
        if line.startswith("value:") and pending is not None:
            value = line.split(":", 1)[1].strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            asserts.append((pending, value))
            pending = None
    return asserts


def _apply(
    assertion_type: str,
    expected: str | None,
    payload: str,
    parsed: object,
) -> StudyOutputAssertionResult:
    if assertion_type == "is-json":
        ok = isinstance(parsed, dict)
        return StudyOutputAssertionResult(
            assertion="is-json",
            status="passed" if ok else "failed",
            message="Candidate JSON parsed." if ok else "Candidate JSON did not parse.",
        )
    if assertion_type == "contains":
        needle = expected or ""
        ok = needle in payload
        return StudyOutputAssertionResult(
            assertion=f"contains:{needle}",
            status="passed" if ok else "failed",
            message=f"Candidate contains {needle}." if ok else f"Candidate is missing {needle}.",
        )
    if assertion_type == "not-contains":
        needle = expected or ""
        ok = needle not in payload
        return StudyOutputAssertionResult(
            assertion=f"not-contains:{needle}",
            status="passed" if ok else "failed",
            message=(
                f"Candidate omits {needle}."
                if ok
                else f"Candidate contains advisory-forbidden {needle}."
            ),
        )
    return StudyOutputAssertionResult(
        assertion=assertion_type,
        status="failed",
        message=f"Unknown study-output assertion {assertion_type}.",
    )
