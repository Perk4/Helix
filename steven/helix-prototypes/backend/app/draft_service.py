"""Per-section draft generation, storage, and read.

A section draft = **verified tables drawn from computed data** + **AI-written
prose**. Numbers come only from the deterministic section executor, so tables
never drift; the model writes narrative only. Reruns are anchored to the current
draft and the reviewer's feedback, so they refine rather than reinvent.

The LLM call is injected (`render_fn`) so the deterministic assembly — tables,
provenance, status — is fully testable without any credentials.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from . import section_catalog
from .repository import StudyPackageRepository
from .schemas import SectionContentDraft, SectionListItem
from .section_executor import (
    REGISTRY,
    SectionNotDraftable,
    SectionResult,
    build_draft_messages,
    run_section,
)

RenderFn = Callable[[list[dict]], str]


class DraftCycleError(RuntimeError):
    """Raised on an invalid revise/apply/discard transition."""

_PROSE_ONLY_INSTRUCTION = (
    "\n\nIMPORTANT: Write the narrative PROSE only. Do NOT output any tables — "
    "the numeric tables are rendered separately from verified data. Do not repeat "
    "the raw numbers as a table."
)


# --------------------------------------------------------------------------- #
# Facts -> structured table blocks (one converter per tabular section)
# --------------------------------------------------------------------------- #

def _group_label(group: dict) -> str:
    return f"{group['group_id']} - {group['label']} ({group['dose']:g} {group['dose_unit']})"


def _body_weight_tables(facts: dict) -> list[dict]:
    days = facts["recording_days"]
    groups = facts["groups"]

    def table(title: str, means: dict) -> dict:
        columns = ["Group", *[f"Day {d}" for d in days]]
        rows = [
            [_group_label(g), *[str(means.get(g["group_id"], {}).get(d, "—")) for d in days]]
            for g in groups
        ]
        return {"kind": "table", "title": title, "columns": columns, "rows": rows}

    return [
        table("Male mean body weight (g)", facts["male_means"]),
        table("Female mean body weight (g)", facts["female_means"]),
    ]


def _organ_weight_tables(facts: dict) -> list[dict]:
    organs = facts["organs"]
    gids = [g["group_id"] for g in facts["groups"]]

    def table(title: str, means: dict) -> dict:
        columns = ["Organ", *gids]
        rows = [[organ, *[str(means.get(organ, {}).get(gid, "—")) for gid in gids]] for organ in organs]
        return {"kind": "table", "title": title, "columns": columns, "rows": rows}

    return [
        table("Male terminal organ weight (g)", facts["male_means"]),
        table("Female terminal organ weight (g)", facts["female_means"]),
    ]


def _formulation_tables(facts: dict) -> list[dict]:
    tps = facts["timepoints"]
    measured = facts["measured"]
    columns = ["Group", *tps]
    rows = [
        [_group_label(g), *[str(measured.get(g["group_id"], {}).get(tp, "—")) for tp in tps]]
        for g in facts["groups"]
    ]
    return [{"kind": "table", "title": f"Measured concentration ({facts['unit']})",
             "columns": columns, "rows": rows}]


def _experimental_design_tables(facts: dict) -> list[dict]:
    columns = ["Group", "Dose", "Males", "Females"]
    rows = [
        [f"{a['group_id']} - {a['label']}", f"{a['dose']:g} {a['dose_unit']}",
         str(a["males"]), str(a["females"])]
        for a in facts["allocation"]
    ]
    return [{"kind": "table", "title": "Group allocation", "columns": columns, "rows": rows}]


def _clinical_obs_tables(facts: dict) -> list[dict]:
    columns = ["Group", "Animals affected", "Total"]
    rows = []
    for g in facts["groups"]:
        cell = facts["incidence"].get(g["group_id"], {})
        rows.append([_group_label(g), str(cell.get("n_affected", 0)), str(cell.get("n_total", 0))])
    return [{"kind": "table", "title": "Abnormal clinical observations", "columns": columns, "rows": rows}]


def _microscopic_tables(facts: dict) -> list[dict]:
    gids = [g["group_id"] for g in facts["groups"]]
    columns = ["Tissue", "Finding", *gids]
    rows = []
    for tissue, findings in facts["findings"].items():
        for finding, per_group in findings.items():
            row = [tissue, finding]
            for gid in gids:
                cell = per_group.get(gid)
                row.append(f"{cell['count']}/{cell['n_total']}" if cell else "—")
            rows.append(row)
    return [{"kind": "table", "title": "Microscopic finding incidence (affected/total)",
             "columns": columns, "rows": rows}]


_TABLE_BUILDERS: dict[str, Callable[[dict], list[dict]]] = {
    "5_2_3_body_weight": _body_weight_tables,
    "5_3_1_organ_weights": _organ_weight_tables,
    "5_1_formulation": _formulation_tables,
    "2_experimental_design": _experimental_design_tables,
    "5_2_2_clinical_obs": _clinical_obs_tables,
    "5_3_3_microscopic": _microscopic_tables,
}


def structured_tables(result: SectionResult) -> list[dict]:
    """Verified tables for a section, drawn from computed facts. [] if none."""
    builder = _TABLE_BUILDERS.get(result.section_id)
    if builder is None or not result.data_available:
        return []
    try:
        return builder(result.facts)
    except (KeyError, TypeError, IndexError):
        return []


def assemble_blocks(result: SectionResult, narrative_md: str | None) -> list[dict]:
    """Order: prose (or needs-review note) first, then the verified tables."""
    blocks: list[dict] = []
    if narrative_md:
        blocks.append({"kind": "prose", "markdown": narrative_md})
    elif not result.data_available:
        blocks.append({"kind": "note", "text": result.note or "[NEEDS REVIEW]"})
    else:
        blocks.append({"kind": "note", "text": "Narrative pending — the model is not configured."})
    blocks.extend(structured_tables(result))
    if result.data_available and result.note:
        blocks.append({"kind": "note", "text": result.note})
    return blocks


# --------------------------------------------------------------------------- #
# Draft service
# --------------------------------------------------------------------------- #

class DraftService:
    def __init__(self, session: Session, render_fn: RenderFn | None = None):
        self.session = session
        self.render_fn = render_fn
        self.repository = StudyPackageRepository(session)

    def list_sections(self, study_id: str) -> list[SectionListItem]:
        self.repository.get(study_id)  # 404 if unknown study
        items: list[SectionListItem] = []
        for meta in section_catalog.CATALOG:
            current = self.repository.current_section_draft(study_id, meta.section_id)
            items.append(
                SectionListItem(
                    section_id=meta.section_id,
                    title=meta.title,
                    order=meta.order,
                    template_section=meta.template_section,
                    has_verified_claims=meta.has_verified_claims,
                    status=current.status if current else "empty",  # type: ignore[arg-type]
                    version=current.version if current else None,
                    data_available=current.data_available if current else None,
                )
            )
        return items

    def get_current(self, study_id: str, section_id: str) -> SectionContentDraft | None:
        self._require_section(section_id)
        row = self.repository.current_section_draft(study_id, section_id)
        return _to_schema(row) if row else None

    def generate(
        self,
        study_id: str,
        section_id: str,
        *,
        feedback: list[str] | None = None,
        status: str = "needs_review",
        anchor: str | None = None,
    ) -> SectionContentDraft:
        self._require_section(section_id)
        feedback = feedback or []
        package = self.repository.get(study_id)
        result = run_section(section_id, package)

        if anchor is None:
            current = self.repository.current_section_draft(study_id, section_id)
            anchor = current.narrative_md if current else None
        narrative_md = self._render(result, feedback, anchor)

        version = self.repository.next_section_draft_version(study_id, section_id)
        row = self.repository.add_section_draft(
            study_id=study_id,
            section_id=section_id,
            version=version,
            status=status,
            title=result.title,
            blocks=assemble_blocks(result, narrative_md),
            narrative_md=narrative_md,
            provenance=[
                {"claim": p.claim, "source_record_ids": list(p.source_record_ids), "agg": p.agg}
                for p in result.provenance
            ],
            note=result.note or None,
            model=_model_name() if narrative_md else None,
            feedback=feedback,
            data_available=result.data_available,
        )
        self.session.commit()
        return _to_schema(row)

    MAX_OPEN_ATTEMPTS = 3

    def revise(self, study_id: str, section_id: str, feedback: str) -> SectionContentDraft:
        """A feedback-driven rerun -> a new *proposed* version (not applied).

        Anchored to the latest active draft so it refines rather than reinvents.
        """
        self._require_section(section_id)
        versions = self.repository.list_section_drafts(study_id, section_id)
        open_proposals = [row for row in versions if row.status == "proposed"]
        if len(open_proposals) >= self.MAX_OPEN_ATTEMPTS:
            raise DraftCycleError(
                f"{self.MAX_OPEN_ATTEMPTS} open attempts already exist. Apply or discard one first."
            )
        active = self.repository.latest_active_section_draft(study_id, section_id)
        prior_feedback = list(active.feedback) if active else []
        anchor = active.narrative_md if active else None
        return self.generate(
            study_id,
            section_id,
            feedback=[*prior_feedback, feedback],
            status="proposed",
            anchor=anchor,
        )

    def apply(self, study_id: str, section_id: str, version: int) -> SectionContentDraft:
        row = self._require_draft(study_id, section_id, version)
        if row.status != "proposed":
            raise DraftCycleError("Only a proposed version can be applied.")
        for other in self.repository.list_section_drafts(study_id, section_id):
            if other.status == "proposed" and other.version != version:
                other.status = "discarded"
        row.status = "needs_review"
        self._event(study_id, "section_draft_applied", section_id, version)
        self.session.commit()
        return _to_schema(row)

    def discard(self, study_id: str, section_id: str, version: int) -> SectionContentDraft:
        row = self._require_draft(study_id, section_id, version)
        if row.status != "proposed":
            raise DraftCycleError("Only a proposed version can be discarded.")
        row.status = "discarded"
        self._event(study_id, "section_draft_discarded", section_id, version)
        self.session.commit()
        return _to_schema(row)

    def verify(self, study_id: str, section_id: str) -> SectionContentDraft:
        self._require_section(section_id)
        row = self.repository.current_section_draft(study_id, section_id)
        if row is None:
            raise KeyError(f"No draft to verify for section '{section_id}'")
        row.status = "verified"
        self._event(study_id, "section_draft_verified", section_id, row.version)
        self.session.commit()
        return _to_schema(row)

    def _require_draft(self, study_id: str, section_id: str, version: int):
        self._require_section(section_id)
        row = self.repository.get_section_draft(study_id, section_id, version)
        if row is None:
            raise KeyError(f"Unknown draft version {version} for section '{section_id}'")
        return row

    def _event(self, study_id: str, event_type: str, section_id: str, version: int) -> None:
        self.repository.append_event(
            study_id=study_id,
            event_type=event_type,
            actor="research scientist",
            payload={"section_id": section_id, "version": version},
        )

    def _render(
        self,
        result: SectionResult,
        feedback: list[str],
        existing_narrative: str | None,
    ) -> str | None:
        if not result.data_available or self.render_fn is None:
            return None
        try:
            messages = build_draft_messages(result)
        except SectionNotDraftable:
            return None
        anchor = ""
        if existing_narrative:
            anchor += (
                "CURRENT DRAFT (revise minimally — change only what the feedback requires, "
                "keep all other wording and structure identical, never alter a number):\n"
                f"{existing_narrative}\n\n---\n\n"
            )
        if feedback:
            bullets = "\n".join(f"- {f}" for f in feedback)
            anchor += f"REVIEWER FEEDBACK (apply all):\n{bullets}\n\n---\n\n"
        messages[0]["content"] += _PROSE_ONLY_INSTRUCTION
        if anchor:
            messages[1]["content"] = anchor + messages[1]["content"]
        try:
            text = self.render_fn(messages)
        except Exception:
            # Model unavailable (e.g. APIM not configured) — degrade to tables + note.
            return None
        return text or None

    @staticmethod
    def _require_section(section_id: str) -> None:
        if section_id not in REGISTRY:
            raise KeyError(f"Unknown section '{section_id}'")


def _model_name() -> str | None:
    import os

    return os.environ.get("APIM_MODEL", "gpt-5.5")


def _to_schema(row: Any) -> SectionContentDraft:
    created = row.created_at
    created_at = created.isoformat() if hasattr(created, "isoformat") else str(created)
    return SectionContentDraft(
        section_id=row.section_id,
        title=row.title,
        version=row.version,
        status=row.status,
        data_available=row.data_available,
        blocks=row.blocks,
        narrative_md=row.narrative_md,
        note=row.note,
        provenance_count=len(row.provenance or []),
        feedback=row.feedback or [],
        model=row.model,
        created_at=created_at,
    )
