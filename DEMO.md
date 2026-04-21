# FinTechCo Rate Risk — Demo Script

**Audience:** Technical evaluators, product leaders, or enterprise buyers  
**Total time:** ~20 minutes  
**Format:** Live terminal + browser. Do not use slides until the end.

---

## Before You Start

```bash
cd ~/projects/fintech-fed-risk-claude-demo
source .venv/bin/activate
# Confirm keys are set
grep -E "FRED|ANTHROPIC|SLACK" .env
```

Have open in your browser:
- `output/risk_dashboard.html` (from last run)
- Slack `#risk-alerts` channel
- JIRA board (optional)

Have open in your editor:
- `src/reporting/risk_memo.py`
- `src/reporting/risk_alert.py`

---

## Act 1 — Set the Scene (2 min)

**Say:**
> "FinTechCo is a fintech with a lending book and a payments business. Their biggest operational risk right now is the rate environment — Fed tightening compresses their net interest margin, raises their cost of capital, and slows loan origination. The problem isn't getting the data. It's the last mile: turning a FRED data pull into something a CFO can act on, automatically, every month."

> "What I'm going to show you is a pipeline that does exactly that. But more importantly, I want to show you *how it was built* — because the way Claude Code collapses the distance between idea and working software is the actual story here."

**Open the terminal. Type:**
```
claude
```

**In Claude Code, ask:**
```
Give me a one-paragraph tour of this codebase — what it does, how it's structured, and what Claude API features it uses.
```

**Why this matters:** You're showing Claude Code's first superpower — it reads the entire repo and gives you an accurate mental model in seconds. This is what a senior engineer joining the team would take a week to build.

---

## Act 2 — Run the Pipeline (4 min)

**Say:**
> "Let me show you the full pipeline end to end. Five steps: ingest from the Fed, compute the risk signal, generate an executive memo, produce a structured alert, and render a dashboard."

**Type:**
```bash
python run.py
```

**As it runs, narrate each step:**

**Step 1 — Ingest:**
> "We're pulling three FRED series live — Fed Funds Rate, CPI, 10-Year Treasury. 130-plus months of data."

**Step 2 — Analyze:**
> "Pure Python. Month-over-month z-scores, equal-weight composite. 8 months flagged as stress periods since 2015. No model, no ML — just math that a risk analyst would recognize."

**Step 3 — Executive Briefing (watch the tokens stream):**
> "Here's where Claude comes in. We're not summarizing data — we're asking Claude to reason about what the data means for a fintech operator. Watch the token output."

Point to the token line when it appears:
```
Token usage — input: 801 | cache write: 0 | cache read: 0 | output: 645
```
> "Hold that number. We'll come back to it."

**Step 4 — Structured Alert:**
> "Now watch the second Claude call."

Point to:
```
Severity:    ELEVATED
Driver:      Federal Reserve rate tightening cycle...
Threshold:   70% of 1.5σ
Actions:     5 items
```
> "Same system prompt as the memo. Different call. Structured JSON output — severity, primary driver, recommended actions, threshold proximity. Machine-readable. Ready for a webhook, a PagerDuty, a Slack post."

**Step 5 — Dashboard:**
> "Self-contained HTML. No server. Shareable by email."

Switch to the browser. Let the dashboard speak for itself for 10 seconds.

---

## Act 3 — Open the Hood: Claude API Features (5 min)

**Say:**
> "Three Claude API patterns are doing real work here. Let me show you each one."

### 3a — Prompt Caching

Open `src/reporting/risk_memo.py`. Point to lines 68–73:

```python
system=[{
    "type": "text",
    "text": SYSTEM_PROMPT,
    "cache_control": {"type": "ephemeral"},
}],
```

**Say:**
> "The system prompt is 300 tokens of static context — who FinTechCo is, what the index means, how to write the memo. We mark it `ephemeral`. Anthropic caches it server-side for 5 minutes."

> "On the first call — cold cache — we pay full price to write it. But `risk_alert.py` imports the exact same `SYSTEM_PROMPT` constant and sends it again within the same pipeline run. That second call hits cache. Cache reads are 90% cheaper than input tokens."

> "At scale — monthly runs, multiple analysts, CI pipelines — that compounds. But the bigger point is developer ergonomics: you *never* have to think about truncating your context to save money. You just write the full prompt and cache it."

**Point to `risk_alert.py` line 1:**
```python
from src.reporting.risk_memo import SYSTEM_PROMPT, load_signal_summary, MODEL
```
> "One import. Cache reuse is automatic."

---

### 3b — Streaming

Back in `risk_memo.py`, point to the stream block:

```python
with client.messages.stream(...) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
        memo_lines.append(text)
```

**Say:**
> "Streaming isn't just a UX nicety. For a 400-word memo, non-streaming means a CFO stares at a spinner for 8 seconds then gets a wall of text. Streaming means they see the answer forming in real time — it reads like a human is writing it. That changes how people trust the output."

> "It also means you can bail early if the model goes off-track. In a longer agentic pipeline, that matters."

---

### 3c — Forced Tool Use

Open `src/reporting/risk_alert.py`. Point to the tool definition and:

```python
tool_choice={"type": "tool", "name": "submit_risk_alert"},
```

**Say:**
> "The memo is prose — free-form, for humans. The alert is for machines. It needs to be a typed JSON object every single time, not 'here's a JSON-ish response.'"

> "Forced tool use guarantees the schema. Severity is always one of four enums. `recommended_actions` is always an array of strings. `threshold_proximity_pct` is always a float. If the downstream system is a PagerDuty webhook or a risk database insert, you need that contract."

> "This is the pattern that makes Claude production-safe in agentic workflows. You're not parsing LLM output — you're calling a typed function."

---

## Act 4 — Live Feature: Portfolio Impact Estimator (3 min)

Switch to the browser. Scroll to the **Portfolio Impact Estimator** panel.

**Say:**
> "While I had Claude Code open earlier today, I pulled up the JIRA board and saw SCRUM-2 — the CFO wanted a portfolio impact estimator. Loan book slider, three rate scenarios, live P&L math."

> "I described it to Claude Code in one message. It wrote the CSS, the HTML panel, and the JavaScript. It placed it correctly in the dashboard between the chart and the actions section. The whole thing took about 90 seconds."

Drag the loan book slider from $2B to $8B. Watch the numbers update.

> "This is $8B book. At +100 bps, you're looking at 60 bps of NIM compression and $48M of P&L impact. That's a number a CFO can take to a board."

> "What I want you to notice is what Claude Code *didn't* do. It didn't refactor the renderer. It didn't add abstractions. It didn't touch the Python pipeline. It made the exact minimal change the ticket asked for. That's the discipline that makes AI-generated code maintainable."

---

## Act 5 — Slack: Closing the Loop (2 min)

Switch to Slack, `#risk-alerts`.

**Say:**
> "The last step in the pipeline posts this to Slack automatically."

Point to the message:
> "Severity badge. Risk index. Threshold proximity bar. Primary driver. Five recommended actions. Context footer."

> "This is the same structured alert from Step 4 — the forced tool use output — formatted for humans. The JSON was the intermediate representation. Slack is the last mile."

> "We also have a second script — `daily_dgs10.py` — that runs every weekday morning on a cron. It checks the 10-Year Treasury yield. If it moves 10 basis points or more day-over-day, it fires an alert independently of the monthly pipeline. That's the real-time layer."

---

## Act 6 — The Meta Point (2 min)

**Say:**
> "Let me zoom out, because I don't want the demo to just be impressive-looking outputs."

> "What you just saw was built by one person, in one session, using Claude Code as a development partner. Not a code autocomplete. A partner that reads the repo, understands the architecture, pulls JIRA tickets, writes production-quality code, and connects to your existing toolchain."

> "The three Claude API patterns — caching, streaming, forced tool use — aren't features for their own sake. Caching makes repeated context cheap. Streaming makes long outputs feel human. Forced tool use makes unstructured language safe for structured systems. Each one closes a specific gap between 'impressive demo' and 'production deployment.'"

> "The question for any enterprise isn't 'can AI do this?' It's 'can I trust it, maintain it, and build on it?' This codebase is the answer to that question."

---

## Appendix: Likely Questions

**"How does this handle stale data or FRED API downtime?"**
> The ingest step raises on HTTP errors. The pipeline will fail loudly at Step 1 rather than silently producing a memo from old data. You'd add a freshness check and retry in production.

**"Why not just use a fine-tuned model instead of prompting?"**
> Fine-tuning fixes style, not reasoning. The value here is Claude reasoning about *new data* each month — flagging which stress periods matter for a fintech operator vs. a bank. That requires the general model.

**"What's the cost per run?"**
> With caching: roughly $0.004 per pipeline run at current pricing (memo + alert, ~1400 input tokens total, 900 output). At daily DGS10 checks with no trigger, it's zero — we only call Claude in the monthly pipeline.

**"Could this run in CI on a schedule?"**
> Yes. `run.py` is a plain Python script. Add a GitHub Actions workflow with a cron trigger, store the keys as secrets, and commit the output artifacts. Done.

**"What would production look like?"**
> Replace the local HTML file with an S3 upload + CloudFront URL. Replace the Slack webhook with a webhook router that fans out to PagerDuty, email, and Slack based on severity. Add a Postgres write for the `risk_signal.json` records. The pipeline logic doesn't change.
