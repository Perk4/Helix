import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from app.schemas import (
    CandidateEvaluation,
    CrossSectionQueryReceipt,
    ProvenanceReceipt,
    StudyOutputEvaluationReceipt,
    TemplateConformanceReceipt,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "skills" / "helix-evidence-pipeline" / "contracts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "invalid-receipts"

RECEIPT_CASES = [
    ("provenance-receipt.schema.json", ProvenanceReceipt, "provenance.json"),
    (
        "study-output-evaluation-receipt.schema.json",
        StudyOutputEvaluationReceipt,
        "study-output.json",
    ),
    (
        "template-conformance-receipt.schema.json",
        TemplateConformanceReceipt,
        "template-conformance.json",
    ),
    ("cross-section-query-receipt.schema.json", CrossSectionQueryReceipt, "cross-section-query.json"),
    ("candidate-evaluation.schema.json", CandidateEvaluation, "candidate-evaluation.json"),
]


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def validator_for(filename: str) -> Draft202012Validator:
    return Draft202012Validator(load_json(CONTRACTS / filename))


def test_valid_receipt_fixtures_pass_schema_and_pydantic() -> None:
    for schema_name, model, fixture_name in RECEIPT_CASES:
        payload = load_json(FIXTURES.parent / "valid-receipts" / fixture_name)
        validator_for(schema_name).validate(payload)
        model.model_validate(payload)


def test_invalid_receipts_are_rejected_by_schema_and_pydantic() -> None:
    for schema_name, model, fixture_name in RECEIPT_CASES:
        for variant in ["unknown-property.json", "missing-required.json"]:
            path = FIXTURES / fixture_name.replace(".json", "") / variant
            payload = load_json(path)
            schema_errors = list(validator_for(schema_name).iter_errors(payload))
            pydantic_failed = False
            try:
                model.model_validate(payload)
            except ValidationError:
                pydantic_failed = True
            assert schema_errors, f"{path} must fail JSON Schema"
            assert pydantic_failed, f"{path} must fail Pydantic"


def test_unknown_property_is_rejected_from_a_valid_receipt() -> None:
    payload = load_json(FIXTURES.parent / "valid-receipts" / "provenance.json")
    mutated = deepcopy(payload)
    mutated["invented"] = True
    assert list(validator_for("provenance-receipt.schema.json").iter_errors(mutated))
    try:
        ProvenanceReceipt.model_validate(mutated)
        raise AssertionError("Pydantic accepted an unknown property")
    except ValidationError:
        pass
