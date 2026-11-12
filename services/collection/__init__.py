"""Playwright-based competitor collection pipeline for Nexus Intel.

This package replaces the former TinyFish Search/Web Agent/Fetch clients while
preserving the downstream contract: a Markdown report written to ``output/``
with one ``## Source: <url>`` section per crawled page. The existing Gemini
validation/extraction pipeline consumes that report unchanged.
"""

from __future__ import annotations

from .config import CollectionSettings
from .pipeline import CollectionError, run_collection_pipeline

__all__ = ["CollectionError", "CollectionSettings", "run_collection_pipeline"]
