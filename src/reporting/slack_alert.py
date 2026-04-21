"""
Slack notifier for the full pipeline risk alert.
Posts a rich Block Kit message to #risk-alerts via incoming webhook.

Requires SLACK_WEBHOOK_URL in .env.
"""

import json
import os
import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR  = Path(__file__).parents[2] / "output"
ALERT_PATH  = OUTPUT_DIR / "risk_alert.json"
SIGNAL_PATH = OUTPUT_DIR / "risk_signal.json"

_SEVERITY_EMOJI = {
    "LOW":      ":white_circle:",
    "ELEVATED": ":large_yellow_circle:",
    "HIGH":     ":large_orange_circle:",
    "CRITICAL": ":red_circle:",
}

_BAR_WIDTH = 20


def _threshold_bar(pct: float) -> str:
    filled = min(int(_BAR_WIDTH * pct / 100), _BAR_WIDTH)
    return "█" * filled + "░" * (_BAR_WIDTH - filled) + f"  {pct:.0f}% of 1.5σ threshold"


def build_payload(alert: dict, current_index: float, period: str) -> dict:
    severity = alert.get("severity", "NORMAL")
    emoji    = _SEVERITY_EMOJI.get(severity, ":white_circle:")
    driver   = alert.get("primary_driver", "—")
    actions  = alert.get("recommended_actions", [])
    tpct     = alert.get("threshold_proximity_pct", 0.0)
    today    = datetime.date.today().strftime("%B %d, %Y")
    bar      = _threshold_bar(tpct)
    actions_text = "\n".join(f"• {a}" for a in actions[:5])

    return {
        "text": f"{emoji} Rate Risk Alert — {severity} ({current_index:+.3f}σ)",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"FinTechCo Rate Risk Alert — {period}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Severity*\n{emoji} {severity}"},
                    {"type": "mrkdwn", "text": f"*Risk Index*\n`{current_index:+.3f}σ`"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Threshold Proximity*\n`{bar}`"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Primary Driver*\n{driver}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Recommended Actions*\n{actions_text}"},
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Source: FRED (FEDFUNDS, CPIAUCSL, DGS10)  ·  Generated {today}"},
                ],
            },
        ],
    }


def post_alert() -> None:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise EnvironmentError("SLACK_WEBHOOK_URL not set in .env")

    alert         = json.loads(ALERT_PATH.read_text())
    records       = json.loads(SIGNAL_PATH.read_text())
    latest        = records[-1]
    current_index = latest["risk_index"]
    period        = latest["date"][:7]

    payload  = build_payload(alert, current_index, period)
    resp     = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"  Posted to #risk-alerts (severity={alert.get('severity')}, index={current_index:+.3f}σ)")


if __name__ == "__main__":
    post_alert()
