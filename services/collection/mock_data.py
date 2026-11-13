"""Deterministic offline pages for ``MOCK_MODE``.

Mock mode runs the *same* classifier/extractor/report code as the live pipeline;
only the page snapshots are generated locally. This keeps the Gemini handoff
contract exercised without network access.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from .models import PageSnapshot, iso_now


def _label(domain: str) -> str:
    label = (domain or "competitor").split(".")[0]
    return label.replace("-", " ").replace("_", " ").title() or "Competitor"


def _pricing_table(annual: bool) -> dict[str, Any]:
    if annual:
        return {
            "headers": ["Plan", "Annual price", "Seats", "Features"],
            "rows": [
                ["Starter", "$0/yr", "1", "Basic dashboard and email support"],
                ["Growth", "$468/yr", "10", "Advanced analytics and priority support"],
                ["Scale", "$1,908/yr", "50", "SSO, audit logs, and dedicated support"],
            ],
        }
    return {
        "headers": ["Plan", "Monthly price", "Seats", "Features"],
        "rows": [
            ["Starter", "$0/mo", "1", "Basic dashboard and email support"],
            ["Growth", "$49/mo", "10", "Advanced analytics and priority support"],
            ["Scale", "$199/mo", "50", "SSO, audit logs, and dedicated support"],
        ],
    }


def _pricing_text(name: str, annual: bool) -> str:
    if annual:
        return (
            f"# {name} Pricing\n\nChoose the plan that fits your team. Prices are billed annually.\n\n"
            "Starter $0/yr\nBasic dashboard and email support\n\n"
            "Growth $468/yr\nAdvanced analytics and priority support\n\n"
            "Scale $1,908/yr\nSSO, audit logs, and dedicated support\n\n"
            "All annual plans include a 14-day free trial. Enterprise: contact sales for a custom quote.\n"
        )
    return (
        f"# {name} Pricing\n\nChoose the plan that fits your team. Prices are billed monthly.\n\n"
        "Starter $0/mo\nBasic dashboard and email support\n\n"
        "Growth $49/mo\nAdvanced analytics and priority support\n\n"
        "Scale $199/mo\nSSO, audit logs, and dedicated support\n\n"
        "All plans include a 14-day free trial. Enterprise: contact sales for a custom quote.\n"
    )


def mock_snapshots(domain: str) -> list[PageSnapshot]:
    name = _label(domain)
    scheme = "https"
    root = f"{scheme}://{domain or 'example.com'}"
    now = iso_now()
    pages = [
        PageSnapshot(
            url=f"{root}/pricing",
            final_url=f"{root}/pricing",
            title=f"{name} Pricing",
            meta_description=f"Plans and pricing for {name}.",
            headings=["Pricing", "Plans", "Compare plans"],
            text=_pricing_text(name, annual=False),
            tables=[_pricing_table(annual=False)],
            links=[f"{root}/features", f"{root}/changelog", f"{root}/about"],
            billing_state="monthly",
            retrieved_at=now,
        ),
        PageSnapshot(
            url=f"{root}/pricing",
            final_url=f"{root}/pricing",
            title=f"{name} Pricing",
            meta_description=f"Plans and pricing for {name}.",
            headings=["Pricing", "Plans", "Compare plans"],
            text=_pricing_text(name, annual=True),
            tables=[_pricing_table(annual=True)],
            links=[f"{root}/features", f"{root}/changelog", f"{root}/about"],
            billing_state="annual",
            retrieved_at=now,
        ),
        PageSnapshot(
            url=f"{root}/features",
            final_url=f"{root}/features",
            title=f"{name} Features",
            meta_description=f"Product capabilities available in {name}.",
            headings=["Features", "Analytics", "Security"],
            text=(
                f"# {name} Features\n\n## Analytics\n"
                "- Real-time dashboards\n- Competitor tracking\n- Custom alerts\n"
                "## Security\n- Single sign-on (SSO)\n- Audit logs\n- Role-based access control\n"
            ),
            lists=[
                {"heading": "Analytics", "items": ["Real-time dashboards", "Competitor tracking", "Custom alerts"]},
                {"heading": "Security", "items": ["Single sign-on (SSO)", "Audit logs", "Role-based access control"]},
            ],
            links=[f"{root}/pricing", f"{root}/changelog"],
            retrieved_at=now,
        ),
        PageSnapshot(
            url=f"{root}/changelog",
            final_url=f"{root}/changelog",
            title=f"{name} Changelog",
            meta_description=f"Recent product updates from {name}.",
            headings=["Changelog", "Recent updates"],
            text=(
                f"# {name} Changelog\n\n"
                "## Recent updates\n\n"
                "2026-10-02 New analytics dashboard\n"
                "Added real-time competitor tracking and custom alerts.\n\n"
                "2026-08-14 Improved audit logs\n"
                "Audit log retention increased and filters were improved.\n"
            ),
            lists=[
                {
                    "heading": "Recent updates",
                    "items": [
                        "2026-10-02 New analytics dashboard - Added real-time competitor tracking",
                        "2026-08-14 Improved audit logs - retention increased",
                    ],
                }
            ],
            links=[f"{root}/pricing", f"{root}/features"],
            retrieved_at=now,
        ),
        PageSnapshot(
            url=f"{root}/about",
            final_url=f"{root}/about",
            title=f"About {name}",
            meta_description=f"About {name}.",
            headings=["About us", "Our mission"],
            text=(
                f"# About {name}\n\n{name} builds competitive intelligence software for "
                "product, marketing, and strategy teams.\n\nOur mission is to make market "
                "changes visible and actionable.\n"
            ),
            links=[f"{root}/pricing", f"{root}/features"],
            retrieved_at=now,
        ),
    ]
    return pages


def mock_discovery(domain: str) -> list[dict[str, Any]]:
    root = f"https://{domain or 'example.com'}"
    return [
        {"url": f"{root}/pricing", "source": "mock", "depth": 0, "priority": 0},
        {"url": f"{root}/features", "source": "mock", "depth": 1, "priority": 3},
        {"url": f"{root}/changelog", "source": "mock", "depth": 1, "priority": 1},
        {"url": f"{root}/about", "source": "mock", "depth": 1, "priority": 6},
    ]


def mock_domain_for_query(query: str) -> str:
    value = (query or "").strip().lower()
    if "://" in value:
        return urlsplit(value).hostname or "example.com"
    if "." in value and " " not in value:
        return value.split("/")[0]
    label = value.replace(" pricing", "").strip().replace(" ", "-") or "competitor"
    return f"{label}.example.com"
