"""Demo-only handling for the two unqualified section packages (HELIX_DEMO_UNQUALIFIED_PACKAGES).

DEMO ONLY. THIS IS NOT QUALIFICATION. With the flag off (the default) nothing here is
consulted and every gate behaves exactly as it does without this module.

With the flag on:
- The Pinned Run gate accepts section.5_2_3_body_weight and section.5_3_discussion while
  their qualification_status is still "pending". No other package, status, or hash is
  affected, and the package files are never written.
- For 5.2.3 only (option 2 of upstream commit 47c19c4), a table cell may cite the Section
  Execution Envelope's executor receipt instead of a Validated Claim. The provenance compiler
  binds such a cell only when every number in it is a value the executor computed.
- Every surface that shows these sections carries the exact label "Demo: not qualified":
  the workspace payload, the UI, and the exported artifacts of a demo-frozen run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEMO_FLAG_ENV = "HELIX_DEMO_UNQUALIFIED_PACKAGES"
DEMO_LABEL = "Demo: not qualified"
DEMO_NOTE = (
    "Demo only, not qualification. These section packages are qualification_status "
    '"pending"; HELIX_DEMO_UNQUALIFIED_PACKAGES let this run proceed without a passing '
    "qualification."
)
# Exactly the two packages named in the ticket. Anything else keeps the strict gate.
DEMO_UNQUALIFIED_PACKAGE_IDS: tuple[str, ...] = (
    "section.5_2_3_body_weight",
    "section.5_3_discussion",
)
# Option 2 (executor receipt backs a table cell) applies to 5.2.3 only.
RECEIPT_BACKED_CELL_PACKAGE_IDS: frozenset[str] = frozenset({"section.5_2_3_body_weight"})
# Recorded on the run_requested event of a demo-frozen Pinned Run (comma-separated ids).
DEMO_EVENT_DETAIL = "demo_unqualified_packages"
# Receipt facts that describe the run, not a table value (mirrors verify-claim-coverage.mjs).
RECEIPT_METADATA_KEYS = frozenset({"recording_days", "duration_days", "unit", "groups", "grading_scale"})


def demo_packages_of(pinned_run: Any) -> list[str]:
    """Package ids whose qualification was skipped when this Pinned Run was frozen."""
    if pinned_run is None:
        return []
    for event in pinned_run.event_history:
        if event.event == "run_requested":
            value = event.details.get(DEMO_EVENT_DETAIL)
            if isinstance(value, str) and value:
                return [item for item in value.split(",") if item]
    return []


def receipt_values(facts: object) -> list[float]:
    """Every numeric leaf the executor computed, excluding run metadata."""
    values: list[float] = []

    def walk(node: object) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, int | float):
            values.append(float(node))
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for item in node.values():
                walk(item)

    if isinstance(facts, dict):
        for key, value in facts.items():
            if key not in RECEIPT_METADATA_KEYS:
                walk(value)
    return values


def demo_notice(package_ids: list[str], titles: dict[str, str]) -> dict[str, object]:
    return {
        "label": DEMO_LABEL,
        "note": DEMO_NOTE,
        "sections": [
            {
                "section_package_id": package_id,
                "title": titles.get(package_id, package_id),
                "qualification_status": "pending",
                "label": DEMO_LABEL,
            }
            for package_id in package_ids
        ],
    }


def section_package_definitions(repository_root: Path) -> dict[str, dict[str, Any]]:
    sections = repository_root / "skills" / "helix-evidence-pipeline" / "packages" / "sections"
    definitions: dict[str, dict[str, Any]] = {}
    for path in sorted(sections.glob("*/package.json")):
        definition = json.loads(path.read_text())
        definitions[str(definition["package_id"])] = definition
    return definitions


def demo_package_ids(repository_root: Path, *, flag_on: bool, pinned_run: Any) -> list[str]:
    """Packages to label: those a demo-frozen run skipped, plus (flag on) the pending demo packages."""
    ids = set(demo_packages_of(pinned_run))
    if flag_on:
        definitions = section_package_definitions(repository_root)
        for package_id in DEMO_UNQUALIFIED_PACKAGE_IDS:
            skill = (definitions.get(package_id) or {}).get("skill") or {}
            if skill.get("qualification_status") == "pending":
                ids.add(package_id)
    return [package_id for package_id in DEMO_UNQUALIFIED_PACKAGE_IDS if package_id in ids]


def demo_package_labels(repository_root: Path, *, flag_on: bool, pinned_run: Any) -> list[dict[str, str]]:
    ids = demo_package_ids(repository_root, flag_on=flag_on, pinned_run=pinned_run)
    if not ids:
        return []
    definitions = section_package_definitions(repository_root)
    return [
        {
            "section_package_id": package_id,
            "section_id": str(definitions.get(package_id, {}).get("section_id", "")),
            "prototype_section_id": str(definitions.get(package_id, {}).get("prototype_section_id", "")),
            "title": str(definitions.get(package_id, {}).get("title", package_id)),
            "qualification_status": "pending",
            "label": DEMO_LABEL,
        }
        for package_id in ids
    ]


DEFAULT_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def section_titles(repository_root: Path = DEFAULT_REPOSITORY_ROOT) -> dict[str, str]:
    return {
        package_id: str(definition.get("title", package_id))
        for package_id, definition in section_package_definitions(repository_root).items()
    }
