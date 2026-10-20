"""Directly runnable Part 2A pipeline for TinyFish Search and Fetch."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from config import MOCK_MODE
from services.tinyfish_fetch import TinyFishFetchError, fetch_markdown
from services.tinyfish_search import TinyFishSearchError, search_web

DUMMY_QUERY = "Stripe pricing"
MOCK_SESSION_ID = "mock_session_9876"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
logger = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "report"


async def run_web_agent(url: str, mock: bool) -> str | None:
    """Placeholder for Part 2B; return the browser session used for extraction."""
    # Alternative approach: ask the TinyFish Agent to "expand every pricing toggle and
    # accordion, then return the entire page content as clean Markdown." The Agent can
    # interact and extract in one run, eliminating the separate Fetch call and session handoff.
    if mock:
        logger.info("Mock Web Agent prepared %s in session %s", url, MOCK_SESSION_ID)
        return MOCK_SESSION_ID

    logger.warning(
        "Web Agent is not connected yet; %s will be fetched in a fresh browser",
        url,
    )
    return None


async def run_pipeline(query: str, mock: bool = MOCK_MODE) -> Path:
    """Run Search -> Web Agent -> Fetch and save the combined Markdown report."""
    print(f"Searching for: {query!r} (mock={mock})")
    urls = await search_web(query, mock=mock)
    print(f"Found {len(urls)} URL(s):")
    for index, url in enumerate(urls, start=1):
        print(f"  {index}. {url}")

    if not urls:
        raise RuntimeError("Search returned no URLs; nothing to fetch")

    session_ids = await asyncio.gather(
        *(run_web_agent(url, mock=mock) for url in urls)
    )
    for url, session_id in zip(urls, session_ids):
        print(f"  Session for {url}: {session_id or 'fresh page'}")

    results = await asyncio.gather(
        *(
            fetch_markdown(url, mock=mock, session_id=session_id)
            for url, session_id in zip(urls, session_ids)
        ),
        return_exceptions=True,
    )

    sections: list[str] = []
    for index, (url, result) in enumerate(zip(urls, results)):
        if isinstance(result, Exception):
            logger.warning("Skipping %s: %s", url, result)
            print(f"  ! Failed to fetch {url}: {result}")
            continue
        session_id = session_ids[index] or "fresh page"
        sections.append(
            f"## Source: {url}\n\n"
            f"- **Browser session:** {session_id}\n\n"
            f"{result}"
        )

    if not sections:
        raise RuntimeError("Every fetch failed; no Markdown was produced")

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report = (
        "# Market Intelligence Report\n\n"
        f"- **Query:** {query}\n"
        f"- **Generated:** {generated_at}\n"
        f"- **Mock mode:** {mock}\n"
        f"- **Sources fetched:** {len(sections)}/{len(urls)}\n\n"
        "---\n\n"
        + "\n\n---\n\n".join(sections)
        + "\n"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{_slugify(query)}_market_intelligence.md"
    output_path.write_text(report, encoding="utf-8")
    return output_path


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        output_path = asyncio.run(run_pipeline(DUMMY_QUERY, mock=MOCK_MODE))
    except (TinyFishSearchError, TinyFishFetchError, RuntimeError, ValueError) as exc:
        logger.error("Pipeline failed: %s", exc)
        return 1

    print("\n" + output_path.read_text(encoding="utf-8"))
    print(f"Saved report to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
