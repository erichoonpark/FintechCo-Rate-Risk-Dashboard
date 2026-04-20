"""Full pipeline: ingest → analyze → executive memo → structured alert → render dashboard."""

import json
import webbrowser
from src.ingest.fred_client import fetch_and_save, SERIES
from src.analysis.rate_risk import compute_risk_signal, save_results
from src.dashboard.render import render_html, OUT_HTML
from src.reporting.risk_memo import generate_memo, MEMO_PATH
from src.reporting.risk_alert import generate_alert, ALERT_PATH
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

    print("\n=== Step 3: Executive Briefing ===")
    memo = generate_memo()
    MEMO_PATH.write_text(memo)
    print(f"  Saved → {MEMO_PATH}")

    print("\n=== Step 4: Structured Alert ===")
    alert = generate_alert()
    ALERT_PATH.write_text(json.dumps(alert, indent=2))
    print(f"  Severity:    {alert['severity']}")
    print(f"  Driver:      {alert['primary_driver']}")
    print(f"  Threshold:   {alert['threshold_proximity_pct']:.0f}% of 1.5σ")
    print(f"  Actions:     {len(alert['recommended_actions'])} items")
    print(f"  Saved → {ALERT_PATH}")

    print("\n=== Step 5: Render Dashboard ===")
    render_html()
    webbrowser.open(OUT_HTML.as_uri())

    print("\nDone.")
