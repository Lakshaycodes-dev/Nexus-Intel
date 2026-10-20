"""Nexus-Intel FastAPI backend.

Importing this package makes the repository root importable so that backend
modules can use the existing top-level packages (``orchestrator``, ``services``,
``schemas``, ``utils``) regardless of the working directory. This mirrors the
``sys.path`` convention already used in ``tests/test_pipeline.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
