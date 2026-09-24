"""Standalone drafting pipeline.

This package holds only what has no counterpart in the backend. The executor
and the domain schemas live in `backend/app/`, and importing this package puts
that directory on the path so they resolve by their real names.

`pipeline/` previously carried its own copies of both. They drifted: the copy
of `schemas.py` never gained `SectionDraftCandidate`, and the copy of
`section_executor.py` missed a later fix that stopped the drafting prompt from
naming a statistical test nothing runs. A copy that lags the original is worse
than an import, because the path that actually calls a model was the one
running the stale code.
"""

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
