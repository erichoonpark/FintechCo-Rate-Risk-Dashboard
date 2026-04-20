# FinTechCo Rate Risk Dashboard

Internal tool for monitoring macroeconomic risk indicators relevant to FinTechCo's lending and payments business. Runs monthly to produce an executive briefing and interactive dashboard for the CTO and CFO.

## Overview

Fetches key Federal Reserve economic series from the FRED API, computes a composite rate-risk signal across inflation, monetary policy, and long-term rate expectations, and produces two outputs:

- **Interactive HTML dashboard** — shareable, self-contained, no server required
- **Executive briefing + structured alert** — plain-English memo and machine-readable JSON for downstream systems

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# FRED_API_KEY      — free at https://fred.stlouisfed.org/docs/api/api_key.html
# ANTHROPIC_API_KEY — required for briefing and alert generation
```

## Run

Full pipeline (recommended):

```bash
python run.py
```

Individual steps:

```bash
python src/ingest/fred_client.py      # fetch raw data → data/
python src/analysis/rate_risk.py      # compute signals → output/risk_signal.json
python src/reporting/risk_memo.py     # executive briefing → output/risk_memo.md
python src/reporting/risk_alert.py    # structured alert → output/risk_alert.json
python src/dashboard/render.py        # dashboard → output/risk_dashboard.html
```

## Data sources

| Series | Description |
|--------|-------------|
| FEDFUNDS | Effective Federal Funds Rate |
| CPIAUCSL | Consumer Price Index (all urban, seasonally adjusted) |
| DGS10 | 10-Year Treasury Constant Maturity Rate |

## Alert severity levels

| Level | Condition |
|-------|-----------|
| Normal | \|risk_index\| < 0.75σ |
| Elevated | 0.75σ – 1.5σ |
| Critical | \|risk_index\| ≥ 1.5σ |

## Output files

| File | Description |
|------|-------------|
| `output/risk_signal.json` | Monthly risk index with component z-scores |
| `output/risk_memo.md` | Plain-English executive briefing |
| `output/risk_alert.json` | Structured alert (severity, driver, recommended actions) |
| `output/risk_dashboard.html` | Self-contained interactive dashboard |
