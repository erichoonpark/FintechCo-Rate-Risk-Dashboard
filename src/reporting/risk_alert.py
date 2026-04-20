"""
Structured risk alert generator.
Uses tool use to force a typed JSON payload — suitable for downstream systems
(webhooks, Slack, PagerDuty, data pipelines) that need machine-readable output
rather than prose.

Reuses the same cached system prompt as risk_memo.py.
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from src.reporting.risk_memo import SYSTEM_PROMPT, load_signal_summary, MODEL

load_dotenv()

OUTPUT_DIR = Path(__file__).parents[2] / "output"
ALERT_PATH = OUTPUT_DIR / "risk_alert.json"

ALERT_TOOL = {
    "name": "submit_risk_alert",
    "description": (
        "Submit a structured risk alert for downstream processing. "
        "Called once with a complete assessment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "enum": ["LOW", "ELEVATED", "HIGH", "CRITICAL"],
                "description": "Overall severity based on current risk_index relative to the 1.5σ threshold",
            },
            "primary_driver": {
                "type": "string",
                "description": "The single macro factor most responsible for the current reading",
            },
            "recommended_actions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 specific, concrete actions for the risk team this month",
            },
            "threshold_proximity_pct": {
                "type": "number",
                "description": "Current |risk_index| as a percentage of the 1.5σ threshold (100 = at threshold, >100 = breached)",
            },
        },
        "required": ["severity", "primary_driver", "recommended_actions", "threshold_proximity_pct"],
    },
}


def generate_alert() -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    summary = load_signal_summary()

    flagged_text = "\n".join(
        f"  - {r['date'][:7]}: risk_index={r['risk_index']:+.3f}"
        for r in summary["flagged_months"]
    )
    user_prompt = f"""Analyze this rate risk data and submit a structured alert.

Current risk index: {summary['current_risk_index']:+.3f} (threshold: ±1.5σ)
Date range: {summary['date_range']}
Flagged stress periods:
{flagged_text}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        tools=[ALERT_TOOL],
        tool_choice={"type": "tool", "name": "submit_risk_alert"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    alert = response.content[0].input
    cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
    print(f"  Token usage — input: {response.usage.input_tokens} | "
          f"cache write: {cache_write} | cache read: {cache_read} | "
          f"output: {response.usage.output_tokens}")
    return alert


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")

    print("Generating structured risk alert...")
    alert = generate_alert()
    ALERT_PATH.write_text(json.dumps(alert, indent=2))
    print(json.dumps(alert, indent=2))
    print(f"\nSaved → {ALERT_PATH}")
