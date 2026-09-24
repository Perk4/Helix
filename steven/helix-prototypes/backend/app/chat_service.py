"""Per-study chat, grounded in verified study data.

The model is stateless; memory is built here by persisting every turn and
replaying a recent window on each request. Answers are grounded: the model
gets the study summary and (for section-scoped questions) that section's
computed facts + current draft, and is told never to invent a number.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from . import section_catalog
from .draft_service import DraftCycleError, DraftService
from .repository import StudyPackageRepository
from .schemas import ChatMessage, ChatTurn
from .section_executor import REGISTRY, run_section

RenderFn = Callable[[list[dict]], str]

HISTORY_WINDOW = 10  # recent turns replayed for context

_SYSTEM_RULES = (
    "You are a GLP nonclinical study assistant for study {study_id}. Help a "
    "research scientist or pathologist understand and refine the report.\n\n"
    "RULES:\n"
    "- Answer using ONLY the verified data provided below. Never invent, estimate, "
    "or extrapolate a study number. If a value is not in the provided data, say it "
    "is not available yet / needs review.\n"
    "- For general or domain questions (definitions, methods, what a grade means), "
    "you may use general knowledge, but keep it clearly separate from this study's "
    "figures and never fabricate this study's numbers.\n"
    "- Be concise and specific. Prefer a short, direct answer."
)


def _study_summary(package: Any) -> str:
    study = package.study
    groups = ", ".join(
        f"{g.group_id} {g.label} {g.dose:g} {g.dose_unit}" for g in study.dose_groups
    )
    claims = "; ".join(
        f"{c.claim_id}={c.value} {c.unit} ({c.field_id})" if c.value is not None
        else f"{c.claim_id}=unset ({c.field_id})"
        for c in package.claims
    )
    sections = ", ".join(
        f"{meta.title}{'' if meta.has_verified_claims else ' [review]'}"
        for meta in section_catalog.CATALOG
    )
    return (
        f"Study {study.study_id}: {study.duration_days}-day {study.route} study in "
        f"{study.species}, protocol {study.protocol_version}.\n"
        f"Dose groups: {groups}.\n"
        f"Validated claims: {claims}.\n"
        f"Report sections: {sections}."
    )


def _section_context(package: Any, section_id: str, current_narrative: str | None) -> str:
    if section_id not in REGISTRY:
        return ""
    result = run_section(section_id, package)
    parts = [
        f"CURRENT SECTION: {result.title}",
        f"data_available: {result.data_available}",
    ]
    if result.note:
        parts.append(f"note: {result.note}")
    parts.append("computed facts (verified; the only numbers you may cite):")
    parts.append(json.dumps(result.facts, indent=2))
    if current_narrative:
        parts.append("current draft narrative:")
        parts.append(current_narrative)
    return "\n".join(parts)


class ChatService:
    def __init__(self, session: Session, render_fn: RenderFn | None = None):
        self.session = session
        self.render_fn = render_fn
        self.repository = StudyPackageRepository(session)

    def history(self, study_id: str) -> list[ChatMessage]:
        self.repository.get(study_id)  # 404 if unknown study
        return [_to_schema(row) for row in self.repository.list_chat_messages(study_id)]

    def ask(
        self,
        study_id: str,
        message: str,
        *,
        scope: str = "section",
        section_id: str | None = None,
    ) -> ChatTurn:
        """One turn. The model decides answer-vs-edit; an edit yields a proposed
        rewrite (gated by the reviewer's 👍/👎). Nothing is applied here."""
        package = self.repository.get(study_id)
        prior = self.repository.recent_chat_messages(study_id, HISTORY_WINDOW)
        messages = self._build_messages(package, message, scope, section_id, prior)
        intent, reply = self._parse(self._render(messages))

        proposed = None
        if intent == "edit" and section_id and section_id in REGISTRY:
            try:
                proposed = DraftService(self.session, self.render_fn).revise(
                    study_id, section_id, message
                )
                reply = reply or (
                    f"Proposed a rewrite (v{proposed.version}) — approve or discard below."
                )
            except DraftCycleError as error:
                reply = str(error)
            except Exception:
                reply = reply or "I could not draft that change just now. Please try again."

        recorded_intent = "revise" if proposed is not None else "ask"
        draft_version = proposed.version if proposed is not None else None
        self.repository.add_chat_message(
            study_id=study_id,
            role="user",
            content=message,
            scope=scope,
            section_id=section_id,
            intent=recorded_intent,
        )
        assistant = self.repository.add_chat_message(
            study_id=study_id,
            role="assistant",
            content=reply,
            scope=scope,
            section_id=section_id,
            intent=recorded_intent,
            draft_version=draft_version,
        )
        self.session.commit()
        return ChatTurn(message=_to_schema(assistant), proposed=proposed)

    @staticmethod
    def _parse(raw: str) -> tuple[str, str]:
        """Extract {intent, reply} from the model output; default to answer."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.find("{") :] if "{" in text else text
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            try:
                data = json.loads(text[start : end + 1])
                intent = data.get("intent", "answer")
                reply = str(data.get("reply", "")).strip()
                if intent == "edit":
                    return "edit", reply
                if reply:
                    return "answer", reply
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass
        return "answer", raw.strip()

    def _build_messages(
        self,
        package: Any,
        message: str,
        scope: str,
        section_id: str | None,
        prior: list[Any],
    ) -> list[dict]:
        grounding = _SYSTEM_RULES.format(study_id=package.study.study_id)
        grounding += "\n\nSTUDY CONTEXT:\n" + _study_summary(package)
        if scope == "section" and section_id:
            current = self.repository.current_section_draft(package.study.study_id, section_id)
            context = _section_context(package, section_id, current.narrative_md if current else None)
            if context:
                grounding += "\n\n" + context
        grounding += (
            "\n\nRESPONSE FORMAT: reply with a single JSON object and nothing else — "
            '{"intent": "answer" | "edit", "reply": "<text>"}. '
            'Use "edit" ONLY when the user is asking to change, rewrite, shorten, or add '
            "to THIS section's drafted content; then put a one-sentence acknowledgement in "
            '"reply" (the rewrite is produced separately). For any question or discussion, '
            'use "answer" and put your grounded answer in "reply".'
        )
        messages: list[dict] = [{"role": "system", "content": grounding}]
        for row in prior:
            messages.append({"role": row.role, "content": row.content})
        messages.append({"role": "user", "content": message})
        return messages

    def _render(self, messages: list[dict]) -> str:
        if self.render_fn is None:
            return "The assistant is unavailable — the model is not configured."
        try:
            reply = self.render_fn(messages)
        except Exception:
            return "The assistant could not reach the model. Please try again."
        return reply or "(no response)"


def _to_schema(row: Any) -> ChatMessage:
    created = row.created_at
    created_at = created.isoformat() if hasattr(created, "isoformat") else str(created)
    return ChatMessage(
        message_id=row.id,
        role=row.role,
        content=row.content,
        scope=row.scope,
        section_id=row.section_id,
        intent=row.intent,
        draft_version=row.draft_version,
        created_at=created_at,
    )
