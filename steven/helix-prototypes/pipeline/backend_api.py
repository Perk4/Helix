"""The backend objects this pipeline uses, re-exported under one name.

Importing anything from `pipeline` runs `pipeline/__init__`, which puts
`backend/` on the path, so callers reach these through `pipeline.backend_api`
rather than importing `app.*` directly. That keeps the import order irrelevant:
sorting these lines any way at all still works.
"""

from app.schemas import StudyEvidencePackage
from app.section_executor import (
    REGISTRY,
    SectionNotDraftable,
    SectionResult,
    build_draft_messages,
)

__all__ = [
    "REGISTRY",
    "SectionNotDraftable",
    "SectionResult",
    "StudyEvidencePackage",
    "build_draft_messages",
]
