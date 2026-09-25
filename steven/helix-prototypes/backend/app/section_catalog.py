"""The 14 report sections shown in the workbench.

Single source of truth for section order, titles, the flat template section each
maps to (for later gate work), and whether it currently has verified numbers.
Section ids match the executor REGISTRY and the skill filenames.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionMeta:
    section_id: str
    title: str
    order: int
    template_section: str | None
    has_verified_claims: bool


# (section_id, title, template_section, has_verified_claims)
_CATALOG: list[tuple[str, str, str | None, bool]] = [
    ("summary", "Summary", "S8", False),
    ("1_objective", "1. Objective", "S2", False),
    ("2_experimental_design", "2. Experimental Design", "S3", True),
    ("3_materials_methods", "3. Materials and Methods", "S3", False),
    ("4_deviations", "4. Deviations from Protocol", "S2", False),
    ("5_1_formulation", "5.1 Formulation Analysis", "S4", True),
    ("5_2_1_mortality", "5.2.1 Mortality", "S5", True),
    ("5_2_2_clinical_obs", "5.2.2 Clinical Observations", "S5", True),
    ("5_2_3_body_weight", "5.2.3 Body Weight", "S5", True),
    ("5_3_1_organ_weights", "5.3.1 Organ Weights", "S7", True),
    ("5_3_2_macroscopic", "5.3.2 Macroscopic Observations", "S7", False),
    ("5_3_3_microscopic", "5.3.3 Microscopic Findings", "S7", True),
    ("5_3_4_conclusion", "5.3.4 Conclusion", "S8", False),
    ("7_qa_statement", "7. Quality Assurance Statement", "S1", False),
]

CATALOG: list[SectionMeta] = [
    SectionMeta(sid, title, order, template, verified)
    for order, (sid, title, template, verified) in enumerate(_CATALOG)
]

BY_ID: dict[str, SectionMeta] = {meta.section_id: meta for meta in CATALOG}


def section_ids() -> list[str]:
    return [meta.section_id for meta in CATALOG]
