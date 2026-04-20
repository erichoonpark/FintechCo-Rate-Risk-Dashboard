"""
Executive risk memo generator.
Loads risk_signal.json and calls Claude to produce a plain-English briefing
suitable for a CFO or Head of Risk — no charts required.

System prompt is cached (ephemeral) — static role/context stays warm across runs,
only the dynamic data payload is re-sent each call.
"""

import json
import os
from datetime import date
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(__file__).parents[2] / "output"
SIGNAL_PATH = OUTPUT_DIR / "risk_signal.json"
MEMO_PATH = OUTPUT_DIR / "risk_memo.md"

MODEL = "claude-sonnet-4-6"

# Static system context — sent once, then served from cache on repeat calls.
SYSTEM_PROMPT = """You are a senior macro risk analyst at FinTechCo, a fintech company with lending and digital payments businesses. You write concise executive risk memos for the CTO and CFO.

You have access to a composite Rate Risk Index built from three Federal Reserve data series:
- Fed Funds Rate (FEDFUNDS) — monetary policy signal
- Consumer Price Index (CPIAUCSL) — inflation signal
- 10-Year Treasury Yield (DGS10) — long-term rate expectations

The index measures month-over-month z-score changes. Values above +1.5σ indicate elevated rate-tightening risk. Values below -1.5σ indicate sudden easing (e.g., crisis response).

Write a professional executive memo with these sections:
1. **Current Risk Environment** — 2-3 sentences on where we stand today
2. **Key Stress Periods** — what drove each flagged period and why it mattered for a fintech lender/payments company
3. **What to Watch (Next 30 Days)** — 2-3 specific macro indicators or events

Tone: Direct, factual, no jargon. Written for executives who are not economists.
Length: 300-400 words. No bullet points in section 1 or 3 — prose only."""


def load_signal_summary() -> dict:
    records = json.loads(SIGNAL_PATH.read_text())
    flagged = [r for r in records if r["flagged"]]
    recent = records[-6:]
    return {
        "total_months": len(records),
        "flagged_months": flagged,
        "recent_months": recent,
        "date_range": f"{records[0]['date'][:7]} – {records[-1]['date'][:7]}",
        "current_risk_index": records[-1]["risk_index"],
        "current_date": date.today().isoformat(),
    }


def build_user_prompt(summary: dict) -> str:
    """Dynamic portion — changes each run as new data arrives."""
    flagged_text = "\n".join(
        f"  - {r['date'][:7]}: risk_index={r['risk_index']:+.3f} "
        f"(fed={r['fedfunds_z']:+.2f}, cpi={r['cpiaucsl_z']:+.2f}, treasury={r['dgs10_z']:+.2f})"
        for r in summary["flagged_months"]
    )
    recent_text = "\n".join(
        f"  - {r['date'][:7]}: risk_index={r['risk_index']:+.3f}"
        for r in summary["recent_months"]
    )
    return f"""DATA SUMMARY
Date range analyzed: {summary["date_range"]}
Total months: {summary["total_months"]}
Current risk index (most recent month): {summary["current_risk_index"]:+.3f}

FLAGGED STRESS PERIODS (|risk_index| > 1.5σ):
{flagged_text}

RECENT 6 MONTHS:
{recent_text}

Date the memo {summary["current_date"]}."""


def generate_memo() -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    summary = load_signal_summary()

    print("  Calling Claude...\n")
    memo_lines = [f"# FinTechCo Rate Risk Briefing\n**{summary['current_date']}**\n\n"]

    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": build_user_prompt(summary)}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            memo_lines.append(text)
        usage = stream.get_final_message().usage

    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    print(f"\n\n  Token usage — input: {usage.input_tokens} | "
          f"cache write: {cache_write} | cache read: {cache_read} | "
          f"output: {usage.output_tokens}")

    return "".join(memo_lines)


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise EnvironmentError("ANTHROPIC_API_KEY not set in .env")

    print("Generating executive risk memo...")
    memo = generate_memo()
    MEMO_PATH.write_text(memo)
    print(f"Saved → {MEMO_PATH}")
