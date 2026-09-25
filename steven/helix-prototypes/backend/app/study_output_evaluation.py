import json
from pathlib import Path
from uuid import uuid4

from .run_plans import file_hash
from .schemas import SectionDraftCandidate, StudyOutputAssertionResult, StudyOutputEvaluationReceipt


def _load_promptfoo_results(path: Path) -> list[StudyOutputAssertionResult]:
    # Alongside wiring (T2.1): Promptfoo runs in CI before the evaluation POST
    # fires, writes --output to this path, and the results are merged here so
    # the llm-rubric verdicts (G-1, G-2, A-1) land in the same receipt as the
    # deterministic checks rather than as a separate artifact.
    # Output format: EvaluateSummaryV3 — results[].gradingResult.componentResults[].
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[StudyOutputAssertionResult] = []
    for result in data.get("results", []):
        grading = result.get("gradingResult") or {}
        description = (result.get("testCase") or {}).get("description", "")
        for component in grading.get("componentResults") or []:
            assertion_info = component.get("assertion") or {}
            metric = assertion_info.get("metric") or assertion_info.get("type", "llm-rubric")
            label = f"{metric}:{description}" if description else metric
            out.append(StudyOutputAssertionResult(
                assertion=label,
                status="passed" if component.get("pass") else "failed",
                message=component.get("reason") or "No reason provided.",
            ))
    return out


def evaluate_study_output(
    candidate: SectionDraftCandidate,
    *,
    candidate_hash: str,
    suite_id: str,
    suite_version: str,
    suite_path: Path,
    receipt_id: str | None = None,
    promptfoo_result_path: Path | None = None,
) -> StudyOutputEvaluationReceipt:
    payload = json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False)
    results: list[StudyOutputAssertionResult] = []
    for assertion_type, expected in load_suite_asserts(suite_path):
        results.append(_apply(assertion_type, expected, payload, candidate.model_dump(mode="json")))
    if promptfoo_result_path is not None and promptfoo_result_path.exists():
        results.extend(_load_promptfoo_results(promptfoo_result_path))
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
