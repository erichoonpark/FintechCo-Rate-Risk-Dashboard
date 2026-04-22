"""Full pipeline: ingest → analyze → render dashboard."""

import webbrowser
from src.ingest.fred_client import fetch_and_save, SERIES
from src.analysis.rate_risk import compute_risk_signal, save_results
from src.dashboard.render import render_html, OUT_HTML

if __name__ == "__main__":
    print("=== Step 1: Ingest ===")
    for series_id, label in SERIES.items():
        print(f"  {series_id}: {label}")
        fetch_and_save(series_id)

    print("\n=== Step 2: Analyze ===")
    df = compute_risk_signal()
    flagged = df[df["flagged"]]
    print(f"  {len(df)} months analyzed, {len(flagged)} flagged (|risk_index| > 1.5σ)")
    out_path = save_results(df)
    print(f"  Saved → {out_path}")

    print("\n=== Step 3: Render Dashboard ===")
    render_html()
    webbrowser.open(OUT_HTML.as_uri())

    print("\nDone.")
