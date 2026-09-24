import hashlib
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .schemas import (
    Claim,
    ClaimStatus,
    Measurement,
    ProvenanceEdge,
    StudyEvidencePackage,
)

PACKAGE_ID = "validation.body_weight"
PACKAGE_VERSION = "0.1.0"
EXECUTOR_ID = "body-weight-summary"
EXECUTOR_VERSION = "1.0.0"
OUTPUT_GRAIN = "study_day_x_sex_x_dose_group"
TERMINAL_CLAIM_ID = "C-BW-HIGH"
TRANSFORM_VERSION = "1.0.0"
FIXTURE_PATH = Path("backend/tests/fixtures/body-weight-summary.json")
SOURCE_ARTIFACT_ID = "A-BW"
ROUNDING_DIGITS = 1

CLAIM_TYPES = (
    "body_weight.mean",
    "body_weight.standard_deviation",
    "body_weight.percent_change",
)
RULES = (
    ("body-weight-required-grain", "1.0.0", "hard_blocker"),
    ("body-weight-summary-recompute", "1.0.0", "hard_blocker"),
    ("body-weight-cell-provenance", "1.0.0", "hard_blocker"),
)
SECTION_CONSUMERS = (
    ("S5", "section.5_2_3_body_weight", "5.2.3 Body Weight"),
    ("S8", "section.5_3_discussion", "Discussion and conclusion"),
)
TRANSFORM_BY_CLAIM_TYPE = {
    "body_weight.mean": "body-weight-mean-v1",
    "body_weight.standard_deviation": "body-weight-sd-v1",
    "body_weight.percent_change": "body-weight-percent-change-v1",
}


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def file_hash(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def round_value(value: float) -> float:
    return round(value, ROUNDING_DIGITS)


def day_token(timepoint: str) -> str:
    return timepoint.replace("DAY ", "D").replace(" ", "")


def load_frozen_fixture(repository_root: Path | None = None) -> dict[str, object]:
    candidates = []
    if repository_root is not None:
        candidates.append(repository_root / FIXTURE_PATH)
    candidates.append(Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "body-weight-summary.json")
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text())
    raise FileNotFoundError("Frozen body-weight summary fixture is missing")


@dataclass(frozen=True)
class CellKey:
    study_day: str
    sex: Literal["M", "F"]
    dose_group: str


@dataclass
class GrainIssue:
    record_id: str
    reason: str


@dataclass
class BodyWeightComputation:
    claims: list[Claim]
    provenance_edges: list[ProvenanceEdge]
    grain_issues: list[GrainIssue]
    cell_count: int


def compute_body_weight_summary(package: StudyEvidencePackage) -> BodyWeightComputation:
    animals = {animal.animal_id: animal for animal in package.records.animals}
    grain_issues: list[GrainIssue] = []
    grouped: dict[CellKey, list[Measurement]] = defaultdict(list)
    for record in package.records.body_weights:
        issue = _grain_issue(record, animals)
        if issue is not None:
            grain_issues.append(issue)
            continue
        animal = animals[record.animal_id or ""]
        grouped[
            CellKey(study_day=record.timepoint, sex=animal.sex, dose_group=animal.group_id)
        ].append(record)

    if grain_issues:
        return BodyWeightComputation(
            claims=[],
            provenance_edges=[],
            grain_issues=grain_issues,
            cell_count=0,
        )

    day1_means = {
        (key.sex, key.dose_group): _mean(records)
        for key, records in grouped.items()
        if key.study_day == "DAY 1"
    }
    claims: list[Claim] = []
    edges: list[ProvenanceEdge] = []
    rule_versions = {rule_id: version for rule_id, version, _ in RULES}
    for key in sorted(grouped, key=lambda item: (item.study_day, item.sex, item.dose_group)):
        records = grouped[key]
        mean = _mean(records)
        deviation = _sample_sd(records)
        baseline = day1_means.get((key.sex, key.dose_group))
        percent_change = 0.0 if baseline in {None, 0.0} else round_value((mean - baseline) / baseline * 100)
        values = {
            "body_weight.mean": mean,
            "body_weight.standard_deviation": deviation,
            "body_weight.percent_change": percent_change,
        }
        for claim_type, value in values.items():
            claim, claim_edges = _cell_claim(
                key,
                claim_type,
                value,
                records,
                rule_versions,
            )
            claims.append(claim)
            edges.extend(claim_edges)

    terminal_records = [
        record
        for key, records in grouped.items()
        if key.study_day == "DAY 28" and key.dose_group == "G4"
        for record in records
    ]
    if terminal_records:
        claim, claim_edges = _terminal_claim(terminal_records, rule_versions)
        claims.append(claim)
        edges.extend(claim_edges)

    return BodyWeightComputation(
        claims=claims,
        provenance_edges=edges,
        grain_issues=[],
        cell_count=len(grouped),
    )


def recompute_matches_fixture(
    computation: BodyWeightComputation,
    fixture: dict[str, object],
) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    cells = {
        (str(item["study_day"]), str(item["sex"]), str(item["dose_group"])): item
        for item in _object_list(fixture.get("cells"))
    }
    by_id = {claim.claim_id: claim for claim in computation.claims}
    for key, expected in cells.items():
        mean_id = _cell_claim_id("body_weight.mean", CellKey(*key))
        sd_id = _cell_claim_id("body_weight.standard_deviation", CellKey(*key))
        pct_id = _cell_claim_id("body_weight.percent_change", CellKey(*key))
        if not _matches(by_id.get(mean_id), expected["mean"]):
            evidence.append(mean_id)
        if not _matches(by_id.get(sd_id), expected["standard_deviation"]):
            evidence.append(sd_id)
        if not _matches(by_id.get(pct_id), expected["percent_change"]):
            evidence.append(pct_id)
    terminal = fixture.get("terminal_high_dose")
    if not isinstance(terminal, dict) or not _matches(by_id.get(TERMINAL_CLAIM_ID), terminal.get("value")):
        evidence.append(TERMINAL_CLAIM_ID)
    expected_cell_claims = len(cells) * len(CLAIM_TYPES)
    if computation.cell_count != len(cells) or len(computation.claims) != expected_cell_claims + 1:
        evidence.append("claim-count")
    return not evidence, evidence


def provenance_failures(computation: BodyWeightComputation) -> list[str]:
    failures: list[str] = []
    edges_by_claim: dict[str, list[ProvenanceEdge]] = defaultdict(list)
    for edge in computation.provenance_edges:
        edges_by_claim[edge.claim_id].append(edge)
    for claim in computation.claims:
        if claim.value is None:
            continue
        claim_edges = edges_by_claim.get(claim.claim_id, [])
        if not claim_edges:
            failures.append(claim.claim_id)
            continue
        if any(
            not edge.source_record_id
            or not edge.source_pointer
            or not edge.source_hash
            or not edge.transform_id
            or edge.transform_version != TRANSFORM_VERSION
            for edge in claim_edges
        ):
            failures.append(claim.claim_id)
            continue
        edge_hashes = [edge.source_hash for edge in claim_edges if edge.source_hash is not None]
        if sorted(edge_hashes) != sorted(claim.source_hashes):
            failures.append(claim.claim_id)
    if not computation.claims:
        failures.append("missing-validated-claims")
    return failures


def _grain_issue(record: Measurement, animals: dict[str, object]) -> GrainIssue | None:
    if not record.grain.strip():
        return GrainIssue(record.record_id, "missing_grain")
    if not record.timepoint.strip():
        return GrainIssue(record.record_id, "missing_study_day")
    if record.animal_id is None or record.animal_id not in animals:
        return GrainIssue(record.record_id, "missing_animal")
    animal = animals[record.animal_id]
    sex = getattr(animal, "sex", None)
    group_id = getattr(animal, "group_id", None)
    if sex not in {"M", "F"} or not group_id:
        return GrainIssue(record.record_id, "missing_sex_or_dose_group")
    return None


def _cell_claim(
    key: CellKey,
    claim_type: str,
    value: float,
    records: list[Measurement],
    rule_versions: dict[str, str],
) -> tuple[Claim, list[ProvenanceEdge]]:
    transform_id = TRANSFORM_BY_CLAIM_TYPE[claim_type]
    claim_id = _cell_claim_id(claim_type, key)
    hashed_records = [(record, canonical_hash(record.model_dump(mode="json"))) for record in records]
    hashed_records = [
        (record, digest) for record, digest in hashed_records if record.source_pointer.strip()
    ]
    field_token = claim_type.removeprefix("body_weight.").replace("_", "-")
    claim = Claim(
        claim_id=claim_id,
        section_id="BW",
        field_id=f"{field_token}-{day_token(key.study_day).lower()}-{key.dose_group.lower()}-{key.sex.lower()}",
        value=value,
        unit="g" if claim_type != "body_weight.percent_change" else "%",
        grain=OUTPUT_GRAIN,
        status=ClaimStatus.VALIDATED,
        claim_type=claim_type,
        grain_key={"study_day": key.study_day, "sex": key.sex, "dose_group": key.dose_group},
        source_hashes=[digest for _, digest in hashed_records],
        transform_id=transform_id,
        transform_version=TRANSFORM_VERSION,
        rule_versions=rule_versions,
        package_id=PACKAGE_ID,
        package_version=PACKAGE_VERSION,
        executor_id=EXECUTOR_ID,
        executor_version=EXECUTOR_VERSION,
    )
    edges = [
        ProvenanceEdge(
            edge_id=f"PE-{claim_id}-{index}",
            claim_id=claim_id,
            source_record_id=record.record_id,
            transform_id=transform_id,
            source_pointer=record.source_pointer,
            authority_tier=1,
            source_hash=digest,
            transform_version=TRANSFORM_VERSION,
        )
        for index, (record, digest) in enumerate(hashed_records, start=1)
    ]
    return claim, edges


def _terminal_claim(
    records: list[Measurement],
    rule_versions: dict[str, str],
) -> tuple[Claim, list[ProvenanceEdge]]:
    hashed_records = [
        (record, canonical_hash(record.model_dump(mode="json")))
        for record in records
        if record.source_pointer.strip()
    ]
    claim = Claim(
        claim_id=TERMINAL_CLAIM_ID,
        section_id="S5",
        field_id="terminal-body-weight-high",
        value=_mean(records),
        unit="g",
        grain="dose_group",
        status=ClaimStatus.VALIDATED,
        claim_type="body_weight.mean",
        grain_key={"study_day": "DAY 28", "dose_group": "G4"},
        source_hashes=[digest for _, digest in hashed_records],
        transform_id="mean-v1",
        transform_version=TRANSFORM_VERSION,
        rule_versions=rule_versions,
        package_id=PACKAGE_ID,
        package_version=PACKAGE_VERSION,
        executor_id=EXECUTOR_ID,
        executor_version=EXECUTOR_VERSION,
    )
    edges = [
        ProvenanceEdge(
            edge_id=f"PE-{TERMINAL_CLAIM_ID}-{index}",
            claim_id=TERMINAL_CLAIM_ID,
            source_record_id=record.record_id,
            transform_id="mean-v1",
            source_pointer=record.source_pointer,
            authority_tier=1,
            source_hash=digest,
            transform_version=TRANSFORM_VERSION,
        )
        for index, (record, digest) in enumerate(hashed_records, start=1)
    ]
    return claim, edges


def _cell_claim_id(claim_type: str, key: CellKey) -> str:
    token = {
        "body_weight.mean": "MEAN",
        "body_weight.standard_deviation": "SD",
        "body_weight.percent_change": "PCT",
    }[claim_type]
    return f"C-BW-{token}-{day_token(key.study_day)}-{key.dose_group}-{key.sex}"


def _mean(records: list[Measurement]) -> float:
    values = [float(record.value) for record in records]
    return round_value(sum(values) / len(values))


def _sample_sd(records: list[Measurement]) -> float:
    values = [float(record.value) for record in records]
    return round_value(statistics.stdev(values))


def _matches(claim: Claim | None, expected: object) -> bool:
    return claim is not None and claim.value == expected


def _object_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
