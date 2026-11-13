"""Directly runnable Playwright collection pipeline.

This is the compatibility entry point used by ``app.services.orchestrator_service``.
It keeps the original ``run_pipeline(query, mock) -> Path`` contract while the
actual work is performed by :mod:`services.collection`.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from config import MOCK_MODE
from services.collection import CollectionSettings, run_collection_pipeline
from services.collection.tracking import TrackingStore

DUMMY_QUERY = "Stripe pricing"
logger = logging.getLogger(__name__)


async def run_pipeline(
    query: str,
    mock: bool = MOCK_MODE,
    *,
    domain: Optional[str] = None,
    tracking_store: Optional[TrackingStore] = None,
    force: bool = False,
) -> Path:
    """Run the Playwright collection pipeline and return the Markdown report path."""
    return await run_collection_pipeline(
        query,
        domain=domain,
        mock=mock,
        settings=CollectionSettings.from_env(),
        tracking_store=tracking_store,
        force=force,
    )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        output_path = asyncio.run(run_pipeline(DUMMY_QUERY, mock=MOCK_MODE))
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        return 1
    print(output_path.read_text(encoding="utf-8"))
    print(f"Saved report to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
