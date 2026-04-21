"""
Daily DGS10 rate monitor.
Fetches the latest 10-Year Treasury yield from FRED, compares to the prior
trading day, and posts a Slack alert to #risk-alerts if the move is >= THRESHOLD_BPS.

Run this on a daily cron (weekdays only — FRED has no weekend data).
"""

import os
import datetime
import requests
from dotenv import load_dotenv

from src.ingest.fred_client import fetch_series, parse_observations

load_dotenv()

THRESHOLD_BPS = 10  # alert if |day-over-day move| >= this


def _fetch_recent_dgs10(n: int = 5) -> list[dict]:
    start = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
    obs   = fetch_series("DGS10", start_date=start)
    return parse_observations(obs)[-n:]


def check_and_alert() -> None:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise EnvironmentError("SLACK_WEBHOOK_URL not set in .env")

    recent = _fetch_recent_dgs10()
    if len(recent) < 2:
        print("  Not enough DGS10 data to compare — skipping.")
        return

    prev, latest   = recent[-2], recent[-1]
    change_bps     = round((latest["value"] - prev["value"]) * 100, 1)
    abs_change     = abs(change_bps)

    print(f"  DGS10: {prev['value']:.3f}% → {latest['value']:.3f}%  ({change_bps:+.1f} bps)")

    if abs_change < THRESHOLD_BPS:
        print(f"  Move {abs_change:.1f} bps < {THRESHOLD_BPS} bps threshold — no alert.")
        return

    direction = "↑" if change_bps > 0 else "↓"
    emoji     = ":large_red_square:" if change_bps > 0 else ":large_blue_square:"
    tone      = "tightening" if change_bps > 0 else "easing"

    payload = {
        "text": f"{emoji} DGS10 {direction} {change_bps:+.1f} bps ({prev['value']:.3f}% → {latest['value']:.3f}%)",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Daily Rate Alert — 10-Yr Treasury {direction} {abs_change:.0f} bps"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Today ({latest['date']})*\n`{latest['value']:.3f}%`"},
                    {"type": "mrkdwn", "text": f"*Prior Day ({prev['date']})*\n`{prev['value']:.3f}%`"},
                    {"type": "mrkdwn", "text": f"*Move*\n{emoji} `{change_bps:+.1f} bps`"},
                    {"type": "mrkdwn", "text": f"*Signal*\nRate {tone} pressure"},
                ],
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Source: FRED DGS10  ·  Threshold: ±{THRESHOLD_BPS} bps  ·  {datetime.date.today().isoformat()}"},
                ],
            },
        ],
    }

    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    print("  Posted to #risk-alerts.")


if __name__ == "__main__":
    check_and_alert()
