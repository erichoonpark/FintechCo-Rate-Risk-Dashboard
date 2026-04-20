"""
FRED API client for fetching macroeconomic risk indicators.
Pulls series used by FinTechCo's rate-risk monitoring workflow.
"""

import os
import json
import warnings
warnings.filterwarnings("ignore", message=".*LibreSSL.*")
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
DATA_DIR = Path(__file__).parents[2] / "data"

SERIES = {
    "FEDFUNDS": "Effective Federal Funds Rate",
    "CPIAUCSL": "Consumer Price Index",
    "DGS10":    "10-Year Treasury Yield",
}


def fetch_series(series_id: str, start_date: str = "2015-01-01") -> list[dict]:
    """Fetch observations for a FRED series. Returns list of {date, value} dicts."""
    if not FRED_API_KEY:
        raise EnvironmentError("FRED_API_KEY not set. Copy .env.example to .env and add your key.")

    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date,
    }
    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()["observations"]


def parse_observations(observations: list[dict]) -> list[dict]:
    """Parse raw FRED observations into clean {date, value} records, skipping missing data."""
    results = []
    for obs in observations:
        if obs["value"] == ".":
            continue
        results.append({
            "date": obs["date"],
            "value": float(obs["value"]),
        })
    return results


def fetch_and_save(series_id: str, start_date: str = "2015-01-01") -> Path:
    """Fetch a series and save as JSON to data/."""
    DATA_DIR.mkdir(exist_ok=True)
    raw = fetch_series(series_id, start_date)
    clean = parse_observations(raw)
    out_path = DATA_DIR / f"{series_id.lower()}.json"
    out_path.write_text(json.dumps(clean, indent=2))
    print(f"  Saved {len(clean)} observations → {out_path}")
    return out_path


if __name__ == "__main__":
    print("Fetching FRED series...")
    for series_id, label in SERIES.items():
        print(f"  {series_id}: {label}")
        fetch_and_save(series_id)
    print("Done.")
