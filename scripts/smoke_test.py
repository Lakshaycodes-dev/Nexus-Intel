"""Live smoke test against a running uvicorn instance (real MongoDB, mock pipeline).

Usage: python scripts/smoke_test.py [base_url]
Exits non-zero on the first failed check.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
FAILURES: list[str] = []


def request(method: str, path: str, body: dict | None = None, headers: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read().decode()
            if "application/json" not in resp.headers.get("Content-Type", "") or not payload:
                return resp.status, {}
            return resp.status, json.loads(payload)
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        if not payload:
            return exc.code, {}
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, {"raw": payload}


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


# 1. Health
code, body = request("GET", "/health")
check("GET /health 200", code == 200, str(body.get("database")))
check("health hides credentials", "mongodb://" not in json.dumps(body))

# 2. Analyze (mock pipeline, real MongoDB persistence)
code, body = request(
    "POST",
    "/api/v1/analyze",
    {"domain": "https://www.stripe.com/pricing", "parameters": {"pricing_tiers": True, "feature_accordions": True, "offsite_mentions": True}},
)
check("POST /analyze 200", code == 200, f"analysis_id={body.get('analysis_id')}")
analysis_id = body.get("analysis_id", "")
data = body.get("data", {})
check(
    "response.data matches frontend CompetitorData shape",
    isinstance(data.get("domain"), str)
    and isinstance(data.get("pricing"), list)
    and isinstance(data.get("offsiteNews"), list)
    and isinstance(data.get("capabilities"), list)
    and isinstance(data.get("executionTimeSec"), (int, float)),
    json.dumps({k: (type(v).__name__) for k, v in data.items()}),
)
check("domain normalised to stripe.com", data.get("domain") == "stripe.com")
check("mock pricing rows extracted", len(data.get("pricing", [])) >= 1, json.dumps(data.get("pricing", [])[:2]))

# 3. Retrieval by analysis ID
code, body = request("GET", f"/api/v1/analyze/{analysis_id}")
check("GET /analyze/{id} 200", code == 200, body.get("status"))
check("record completed with results", body.get("status") == "completed" and body.get("data") is not None)
check("timestamps present", bool(body.get("created_at")) and bool(body.get("completed_at")))

# 4. Competitor retrieval by domain
code, body = request("GET", "/api/v1/competitors/stripe.com")
check("GET /competitors/{domain} 200", code == 200, body.get("competitor_id"))
check("competitor carries pricing data", bool(body.get("data", {}).get("pricing")))

# 5. 404s
code, body = request("GET", "/api/v1/competitors/unknown-domain-xyz.com")
check("unknown competitor 404", code == 404 and body.get("error", {}).get("code") == "not_found")
code, body = request("GET", f"/api/v1/analyze/{'0' * 32}")
check("unknown analysis 404", code == 404 and body.get("error", {}).get("code") == "not_found")

# 6. Validation + SSRF guard
code, body = request("POST", "/api/v1/analyze", {"domain": "localhost"})
check("localhost rejected (SSRF guard)", code == 422 and body.get("error", {}).get("code") == "validation_error")
code, body = request("POST", "/api/v1/analyze", {})
check("missing domain rejected", code == 422)

# 7. CORS preflight
import urllib.error as _urllib_error

_preflight = urllib.request.Request(
    BASE + "/api/v1/analyze",
    method="OPTIONS",
    headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
)
try:
    with urllib.request.urlopen(_preflight, timeout=15) as _resp:
        _origin_header = _resp.headers.get("access-control-allow-origin", "")
        check(
            "CORS preflight allows frontend origin",
            _resp.status in (200, 204) and _origin_header == "http://localhost:3000",
            f"status={_resp.status} allow-origin={_origin_header!r}",
        )
except _urllib_error.URLError as exc:
    check("CORS preflight allows frontend origin", False, str(exc))

# 8. Docs
code, _ = request("GET", "/openapi.json")
check("OpenAPI schema served", code == 200)

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) FAILED: {FAILURES}")
    sys.exit(1)
print("All smoke checks passed.")
