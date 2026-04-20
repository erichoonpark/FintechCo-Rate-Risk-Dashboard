"""
Rate risk analysis: loads FRED series, computes MoM changes, z-score normalizes,
combines into a composite risk index, and flags months exceeding 1.5 std devs.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parents[2] / "data"
OUTPUT_DIR = Path(__file__).parents[2] / "output"

SERIES = ["fedfunds", "cpiaucsl", "dgs10"]


def load_series(name: str) -> pd.Series:
    path = DATA_DIR / f"{name}.json"
    records = json.loads(path.read_text())
    s = pd.Series(
        {r["date"]: r["value"] for r in records},
        name=name,
    )
    s.index = pd.to_datetime(s.index)
    return s


def to_monthly(s: pd.Series) -> pd.Series:
    """Resample to month-start means to align daily and monthly series."""
    return s.resample("MS").mean()


def mom_change(s: pd.Series) -> pd.Series:
    return s.diff()


def z_score(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std()


def compute_risk_signal() -> pd.DataFrame:
    series = {name: to_monthly(load_series(name)) for name in SERIES}
    df = pd.DataFrame(series)

    # Month-over-month change for each series
    changes = df.apply(mom_change)

    # Z-score each change series
    z = changes.apply(z_score)
    z.columns = [f"{c}_z" for c in z.columns]

    # Equal-weight composite index
    composite = z.mean(axis=1)
    composite.name = "risk_index"

    result = pd.concat([composite, z], axis=1).dropna()
    result["flagged"] = result["risk_index"].abs() > 1.5

    return result


def save_results(df: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    records = []
    for date, row in df.iterrows():
        records.append({
            "date": date.strftime("%Y-%m-%d"),
            "risk_index": round(row["risk_index"], 4),
            "fedfunds_z": round(row["fedfunds_z"], 4),
            "cpiaucsl_z": round(row["cpiaucsl_z"], 4),
            "dgs10_z": round(row["dgs10_z"], 4),
            "flagged": bool(row["flagged"]),
        })
    out_path = OUTPUT_DIR / "risk_signal.json"
    out_path.write_text(json.dumps(records, indent=2))
    return out_path


if __name__ == "__main__":
    print("Computing rate risk signal...")
    df = compute_risk_signal()

    flagged = df[df["flagged"]]
    print(f"  {len(df)} months analyzed, {len(flagged)} flagged (|risk_index| > 1.5σ)")
    if not flagged.empty:
        print("  Flagged months:")
        for date, row in flagged.iterrows():
            print(f"    {date.strftime('%Y-%m')}  risk_index={row['risk_index']:+.3f}")

    out_path = save_results(df)
    print(f"  Saved → {out_path}")
