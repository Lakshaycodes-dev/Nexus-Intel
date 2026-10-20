"""Directly runnable pipeline for TinyFish Search, Web Agent, and Fetch."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from config import MOCK_MODE
from services.agent_prompts import DEFAULT_OBJECTIVE
from services.tinyfish_agent import TinyFishAgentError, WebAgentResult
from services.tinyfish_agent import run_web_agent as extract_web_intelligence
from services.tinyfish_fetch import TinyFishFetchError, fetch_markdown
from services.tinyfish_search import TinyFishSearchError, search_web

DUMMY_QUERY = "Stripe pricing"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
logger = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "report"


async def run_web_agent(url: str, mock: bool) -> WebAgentResult:
    """Run the TinyFish Web Agent for one competitor URL."""

    return await extract_web_intelligence(url, DEFAULT_OBJECTIVE, mock=mock)


async def run_pipeline(query: str, mock: bool = MOCK_MODE) -> Path:
    """Run Search -> Web Agent -> Fetch and save the combined Markdown report."""

    print(f"Searching for: {query!r} (mock={mock})")
    urls = await search_web(query, mock=mock)
    print(f"Found {len(urls)} URL(s):")
    for index, url in enumerate(urls, start=1):
        print(f"  {index}. {url}")

    if not urls:
        raise RuntimeError("Search returned no URLs; nothing to fetch")

    agent_results = await asyncio.gather(
        *(run_web_agent(url, mock=mock) for url in urls)
    )
    for url, agent_result in zip(urls, agent_results):
        session = agent_result.session_id or agent_result.session_id_missing_reason
        print(f"  Session for {url}: {session}")
        print(
            f"  Extraction for {url}: success={agent_result.success}, "
            f"status={agent_result.status}, run_id={agent_result.run_id}"
        )

    fetch_results = await asyncio.gather(
        *(
            fetch_markdown(url, mock=mock, session_id=agent_result.session_id)
            for url, agent_result in zip(urls, agent_results)
        ),
        return_exceptions=True,
    )

    sections: list[str] = []
    for index, (url, fetch_result) in enumerate(zip(urls, fetch_results)):
        agent_result = agent_results[index]
        fetched_text: str | None = None
        if isinstance(fetch_result, Exception):
            logger.warning("Skipping fetch for %s: %s", url, fetch_result)
            print(f"  ! Failed to fetch {url}: {fetch_result}")
        else:
            fetched_text = fetch_result

        if agent_result.data is None and fetched_text is None:
            continue

        session = agent_result.session_id or "not provided by the Agent API"
        intelligence = (
            json.dumps(agent_result.data, indent=2, ensure_ascii=False)
            if agent_result.data is not None
            else "null"
        )
        fetch_section = fetched_text or "_Fetch did not return content for this URL._"
        sections.append(
            f"## Source: {url}\n\n"
            f"- **Agent run:** {agent_result.run_id or 'n/a'}\n"
            f"- **Browser session:** {session}\n"
            f"- **Session note:** {agent_result.session_id_missing_reason or 'n/a'}\n"
            f"- **Extraction success:** {agent_result.success}\n"
            f"- **Extraction status:** {agent_result.status}\n\n"
            f"### Structured intelligence\n\n"
            f"```json\n{intelligence}\n```\n\n"
            f"### Fetched content\n\n"
            f"{fetch_section}"
        )

    if not sections:
        raise RuntimeError("Every extraction and fetch failed; no report was produced")

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report = (
        "# Market Intelligence Report\n\n"
        f"- **Query:** {query}\n"
        f"- **Generated:** {generated_at}\n"
        f"- **Mock mode:** {mock}\n"
        f"- **Sources reported:** {len(sections)}/{len(urls)}\n\n"
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
    except (TinyFishSearchError, TinyFishFetchError, TinyFishAgentError, RuntimeError, ValueError) as exc:
        logger.error("Pipeline failed: %s", exc)
        return 1

    print("\n" + output_path.read_text(encoding="utf-8"))
    print(f"Saved report to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
