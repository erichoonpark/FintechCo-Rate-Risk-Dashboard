# FinTechCo Rate Risk Monitor — Project Guide

## Overview

FinTechCo is a fintech company operating a consumer lending book and a digital payments business. This system monitors the macroeconomic rate environment by pulling Federal Reserve data, computing a composite risk signal, and delivering actionable outputs to the CTO, CFO, and Head of Risk on a monthly cadence.

The core business question the system answers: **how does the current rate environment affect our cost of capital, net interest margin, and credit risk posture — and what should we do about it?**

---

## Architecture

The pipeline runs in three sequential steps, orchestrated by `run.py`:

```
Step 1 — Ingest       src/ingest/fred_client.py
Step 2 — Analyze      src/analysis/rate_risk.py
Step 3 — Dashboard    src/dashboard/render.py
```

### Data sources

| FRED Series | Description | Frequency |
|-------------|-------------|-----------|
| `FEDFUNDS`  | Effective Federal Funds Rate | Monthly |
| `CPIAUCSL`  | Consumer Price Index (all urban, SA) | Monthly |
| `DGS10`     | 10-Year Treasury Constant Maturity Rate | Daily |

Raw data is cached in `data/` as JSON. Re-running ingest overwrites with the latest observations.

### Risk signal methodology

Each series is resampled to monthly frequency, differenced (month-over-month change), and z-score normalized over the full history. The three z-scores are equal-weighted into a composite `risk_index`. Months where `|risk_index| > 1.5σ` are flagged as stress periods.

### Alert severity thresholds

| Severity | Condition |
|----------|-----------|
| Normal   | `|risk_index| < 0.75σ` |
| Elevated | `0.75σ – 1.5σ` |
| Critical | `|risk_index| ≥ 1.5σ` |

---

## Outputs

| File | Description |
|------|-------------|
| `output/risk_signal.json` | Monthly index values with component z-scores and flagged periods |
| `output/risk_dashboard.html` | Self-contained interactive dashboard — no server required |

---

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add: FRED_API_KEY
```

## Running

Full pipeline:
```bash
python run.py
```

Individual steps:
```bash
python src/ingest/fred_client.py       # fetch FRED data → data/
python src/analysis/rate_risk.py       # compute signal → output/risk_signal.json
python src/dashboard/render.py         # dashboard → output/risk_dashboard.html
```

---

## Open Tickets

Active work is tracked in `tickets/`:

| Ticket | Priority | Summary |
|--------|----------|---------|
| `RISK-101` | High | Portfolio Impact Estimator — interactive loan book slider with NIM/P&L scenarios |
| `RISK-102` | Medium | Historical Stress Comparison — overlay 2018 and 2020 periods on risk chart |
| `RISK-103` | Medium | Yield Curve Inversion Signal — 10Y–2Y spread as secondary recession indicator |

When implementing a ticket, read the acceptance criteria in `tickets/<id>.md` before making changes. Prefer minimal, targeted edits — do not refactor surrounding code unless the ticket explicitly requires it.

---

## Conventions

- **No new FRED series** without a corresponding entry in `SERIES` in `fred_client.py` and a cached file in `data/`
- **Dashboard changes** go in `src/dashboard/render.py` only — the HTML template is embedded in `_HTML_TEMPLATE`; Python data pipeline code is never modified for display-only changes
- **Output files** are regenerated on every run — do not hand-edit files in `output/`
- **Secrets** live in `.env` only — never commit API keys
