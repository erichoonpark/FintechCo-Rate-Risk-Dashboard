"""
Dashboard renderer: generates a self-contained HTML dashboard for CFO/stakeholder use
from risk_signal.json.

Also retains the legacy PNG render() function for internal use.
"""

import json
import datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import plotly.graph_objects as go
from plotly.subplots import make_subplots

OUTPUT_DIR = Path(__file__).parents[2] / "output"
DATA_DIR   = Path(__file__).parents[2] / "data"

SIGNAL_PATH = OUTPUT_DIR / "risk_signal.json"
OUT_PNG     = OUTPUT_DIR / "risk_dashboard.png"
OUT_HTML    = OUTPUT_DIR / "risk_dashboard.html"

# Legacy PNG constants
BG         = "#0F1117"
PANEL_BG   = "#1A1D27"
GRID_CLR   = "#222233"
TEXT       = "#AAAAAA"
TEXT_BRIGHT = "#EEEEEE"
RED        = "#FF5252"
BLUE       = "#40C4FF"
THRESHOLD  = 1.5

SERIES_COLORS = {
    "fedfunds": ("#2196F3", "Fed Funds Rate (%)"),
    "cpiaucsl": ("#FF9800", "CPI Index"),
    "dgs10":    ("#9C27B0", "10-Yr Treasury Yield (%)"),
}

_SEVERITY_CONFIG = {
    "NORMAL": {
        "color":    "#059669",
        "bg":       "#ECFDF5",
        "border":   "#A7F3D0",
        "label":    "Normal",
    },
    "ELEVATED": {
        "color":    "#B45309",
        "bg":       "#FFFBEB",
        "border":   "#FCD34D",
        "label":    "Elevated",
    },
    "CRITICAL": {
        "color":    "#DC2626",
        "bg":       "#FEF2F2",
        "border":   "#FCA5A5",
        "label":    "Critical",
    },
}

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FinTechCo Rate Risk Dashboard &middot; %%CURRENT_DATE%%</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      background: #F8FAFC;
      color: #0F172A;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }

    /* ── Layout ── */
    .page { max-width: 1080px; margin: 0 auto; padding: 0 24px 56px; }

    /* ── Header ── */
    .header { background: #1E3A5F; padding: 18px 0; margin-bottom: 28px; }
    .header-inner {
      max-width: 1080px; margin: 0 auto; padding: 0 24px;
      display: flex; justify-content: space-between; align-items: center;
    }
    .header-logo-name { font-size: 18px; font-weight: 700; color: white; letter-spacing: -0.3px; }
    .header-logo-sub  { font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 3px; }
    .header-meta      { text-align: right; }
    .header-period    { font-size: 15px; font-weight: 600; color: white; }
    .header-gen       { font-size: 11px; color: rgba(255,255,255,0.45); margin-top: 3px; }

    /* ── Cards ── */
    .card {
      background: white;
      border: 1px solid #E2E8F0;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 1px 3px rgba(15,23,42,0.05);
    }
    .section { margin-bottom: 20px; }

    /* ── Hero ── */
    .hero { border-left: 4px solid %%SEVERITY_COLOR%%; }
    .hero-top   { display: flex; align-items: flex-start; gap: 20px; margin-bottom: 16px; }
    .badge {
      display: inline-flex; align-items: center;
      padding: 3px 10px; border-radius: 99px;
      font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
      background: %%SEVERITY_COLOR%%; color: white;
      margin-bottom: 8px;
    }
    .hero-val {
      font-size: 40px; font-weight: 800; letter-spacing: -1.5px;
      color: %%SEVERITY_COLOR%%; font-variant-numeric: tabular-nums; line-height: 1;
    }
    .hero-val-sub { font-size: 12px; color: #94A3B8; margin-top: 5px; }

    /* ── Section label ── */
    .label {
      font-size: 10px; font-weight: 700; letter-spacing: 1px;
      text-transform: uppercase; color: #94A3B8; margin-bottom: 16px;
    }

    /* ── Two-column grid ── */
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }

    /* ── Actions ── */
    .action-list { list-style: none; display: flex; flex-direction: column; gap: 12px; }
    .action-item { display: flex; gap: 12px; align-items: flex-start; }
    .action-num {
      flex-shrink: 0; width: 22px; height: 22px;
      background: #1E3A5F; color: white; border-radius: 50%;
      font-size: 11px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
    }
    .action-text { font-size: 13.5px; color: #334155; line-height: 1.55; padding-top: 1px; }

    /* ── Hero driver & pending placeholder ── */
    .hero-driver { font-size: 13px; color: #64748B; margin-top: 8px; }
    .pending     { font-size: 13px; color: #94A3B8; font-style: italic; }

    /* ── Stats ── */
    .stat + .stat { margin-top: 18px; padding-top: 18px; border-top: 1px solid #F1F5F9; }
    .stat-label {
      font-size: 10px; font-weight: 700; letter-spacing: 0.7px;
      text-transform: uppercase; color: #94A3B8; margin-bottom: 4px;
    }
    .stat-value { font-size: 15px; font-weight: 600; color: #0F172A; }

    /* ── Gauge ── */
    .gauge-track {
      height: 6px; background: #E2E8F0;
      border-radius: 99px; overflow: hidden; margin: 8px 0 5px;
    }
    .gauge-fill {
      height: 100%; width: %%THRESHOLD_PCT%%%;
      background: %%SEVERITY_COLOR%%; border-radius: 99px;
    }
    .gauge-labels { display: flex; justify-content: space-between; font-size: 11px; color: #CBD5E1; }
    .gauge-labels .mid { color: %%SEVERITY_COLOR%%; font-weight: 700; }

    /* ── Accordion ── */
    .accordion-btn {
      width: 100%; display: flex; justify-content: space-between; align-items: center;
      background: none; border: none; cursor: pointer; padding: 0; color: #0F172A; text-align: left;
    }
    .accordion-btn:hover .accordion-title { color: #1E3A5F; }
    .accordion-title { font-size: 15px; font-weight: 600; }
    .accordion-caret { font-size: 12px; color: #CBD5E1; transition: transform 0.2s ease; display: inline-block; }
    .accordion-caret.open { transform: rotate(180deg); }
    .accordion-body { display: none; margin-top: 20px; padding-top: 20px; border-top: 1px solid #F1F5F9; }
    .accordion-body.open { display: block; }

    /* ── Memo prose ── */
    .memo h1 { font-size: 17px; font-weight: 700; color: #0F172A; margin-bottom: 2px; }
    .memo h2 {
      font-size: 11px; font-weight: 700; letter-spacing: 0.8px;
      text-transform: uppercase; color: #1E3A5F; margin: 22px 0 8px;
    }
    .memo p  { font-size: 14px; color: #374151; line-height: 1.75; margin-bottom: 10px; }
    .memo p strong { color: #0F172A; }
    .memo hr { border: none; border-top: 1px solid #F1F5F9; margin: 14px 0; }

    /* ── Footer ── */
    .footer {
      margin-top: 36px; padding-top: 16px; border-top: 1px solid #E2E8F0;
      display: flex; justify-content: space-between;
      font-size: 11px; color: #CBD5E1;
    }
  </style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div>
      <div class="header-logo-name">FinTechCo</div>
      <div class="header-logo-sub">Rate Risk Dashboard</div>
    </div>
    <div class="header-meta">
      <div class="header-period">%%CURRENT_DATE%%</div>
      <div class="header-gen">Generated %%GENERATED_DATE%%</div>
    </div>
  </div>
</div>

<div class="page">

  <!-- ── Hero: current status & recommendation ── -->
  <div class="section">
    <div class="card hero">
      <div class="hero-top">
        <div>
          <div class="badge">%%SEVERITY_LABEL%%</div>
          <div class="hero-val">%%CURRENT_INDEX%%</div>
          <div class="hero-val-sub">Rate Risk Index &middot; %%CURRENT_DATE%%</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── Risk index chart ── -->
  <div class="section">
    <div class="card">
      <div class="label">Rate Risk Index &mdash; Historical View</div>
      <div id="chart"></div>
    </div>
  </div>

  <!-- ── Risk details + Recommended Actions ── -->
  <div class="section">
    <div class="grid-2">

      <div class="card">
        <div class="label">Risk Details</div>

        <div class="stat">
          <div class="stat-label">Threshold Proximity</div>
          <div class="gauge-track"><div class="gauge-fill"></div></div>
          <div class="gauge-labels">
            <span>0%</span>
            <span class="mid">%%THRESHOLD_PCT%%%</span>
            <span>Alert (100%)</span>
          </div>
        </div>

        <div class="stat">
          <div class="stat-label">Current Index</div>
          <div class="stat-value">
            %%CURRENT_INDEX%%
            <span style="font-size:12px;font-weight:400;color:#94A3B8">&nbsp;(threshold &plusmn;1.5&sigma;)</span>
          </div>
        </div>

        <div class="stat">
          <div class="stat-label">Severity</div>
          <div class="stat-value" style="color:%%SEVERITY_COLOR%%">%%SEVERITY_LABEL%%</div>
        </div>

        <div class="stat">
          <div class="stat-label">Reporting Period</div>
          <div class="stat-value" style="font-weight:400;font-size:14px">%%CURRENT_DATE%%</div>
        </div>
      </div>

    </div>
  </div>

  <div class="footer">
    <span>Source: Federal Reserve FRED &nbsp;&middot;&nbsp; Series: FEDFUNDS, CPIAUCSL, DGS10</span>
    <span>FinTechCo Macro Risk &nbsp;&middot;&nbsp; Confidential</span>
  </div>

</div>

<script>
const spec = %%CHART_JSON%%;
Plotly.newPlot('chart', spec.data, spec.layout, {responsive: true, displayModeBar: false});


</script>

</body>
</html>
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_chart(signal: pd.DataFrame) -> str:
    """Return Plotly figure JSON for the risk index chart."""
    dates = signal.index
    idx   = signal["risk_index"]
    flagged = signal[signal["flagged"]]
    latest  = signal.iloc[-1]

    # Separate fills above/below zero
    pos = idx.clip(lower=0)
    neg = idx.clip(upper=0)

    fig = go.Figure()

    # Shaded fill areas
    fig.add_trace(go.Scatter(
        x=dates, y=pos, fill="tozeroy",
        fillcolor="rgba(239,68,68,0.10)", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=neg, fill="tozeroy",
        fillcolor="rgba(59,130,246,0.10)", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))

    # Main risk index line
    fig.add_trace(go.Scatter(
        x=dates, y=idx, name="Risk Index",
        line=dict(color="#1E3A5F", width=2),
        hovertemplate="%{x|%b %Y}: %{y:+.3f}\u03c3<extra></extra>",
    ))

    # Flagged period markers
    fig.add_trace(go.Scatter(
        x=flagged.index, y=flagged["risk_index"],
        mode="markers", name="Flagged period",
        marker=dict(color="#EF4444", size=8, symbol="circle",
                    line=dict(color="#DC2626", width=1.5)),
        hovertemplate="%{x|%b %Y}: %{y:+.3f}\u03c3<extra>Flagged</extra>",
    ))

    # Current month marker
    fig.add_trace(go.Scatter(
        x=[signal.index[-1]], y=[latest["risk_index"]],
        mode="markers", name="Current month",
        marker=dict(color="#F59E0B", size=13, symbol="diamond",
                    line=dict(color="#D97706", width=2)),
        hovertemplate="%{x|%b %Y}: %{y:+.3f}\u03c3<extra>Current</extra>",
    ))

    # Threshold lines
    fig.add_hline(
        y=THRESHOLD, line=dict(color="#EF4444", dash="dash", width=1.5),
        annotation_text="Alert +1.5\u03c3", annotation_position="top right",
        annotation_font=dict(color="#EF4444", size=11),
    )
    fig.add_hline(
        y=-THRESHOLD, line=dict(color="#3B82F6", dash="dash", width=1.5),
        annotation_text="Alert \u22121.5\u03c3", annotation_position="bottom right",
        annotation_font=dict(color="#3B82F6", size=11),
    )
    fig.add_hline(y=0, line=dict(color="#CBD5E1", width=1))

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FAFAFA",
        height=360,
        margin=dict(t=12, b=40, l=56, r=40),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
            bgcolor="rgba(255,255,255,0.85)", bordercolor="#E2E8F0", borderwidth=1,
            font=dict(size=12),
        ),
        xaxis=dict(gridcolor="#F1F5F9", showgrid=True, tickfont=dict(size=11)),
        yaxis=dict(
            gridcolor="#F1F5F9", showgrid=True,
            title=dict(text="Risk Index (\u03c3)", font=dict(size=12)),
            tickfont=dict(size=11),
        ),
        hovermode="x unified",
    )

    return fig.to_json()


# ── Public API ────────────────────────────────────────────────────────────────

def load_signal() -> pd.DataFrame:
    records = json.loads(SIGNAL_PATH.read_text())
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def load_raw_series() -> pd.DataFrame:
    frames = {}
    for series_id in ("fedfunds", "cpiaucsl", "dgs10"):
        path = DATA_DIR / f"{series_id}.json"
        raw  = json.loads(path.read_text())
        s    = pd.DataFrame(raw)
        s["date"] = pd.to_datetime(s["date"])
        frames[series_id] = s.set_index("date")["value"]
    return pd.DataFrame(frames)


def render_html() -> None:
    """Render the CFO-grade interactive HTML dashboard."""
    signal = load_signal()

    # Current state
    latest        = signal.iloc[-1]
    current_index = latest["risk_index"]
    current_date  = signal.index[-1].strftime("%B %Y")
    abs_idx       = abs(current_index)
    if abs_idx >= 1.5:
        severity = "CRITICAL"
    elif abs_idx >= 0.75:
        severity = "ELEVATED"
    else:
        severity = "NORMAL"
    threshold_pct = min(abs_idx / 1.5 * 100, 100.0)

    sc = _SEVERITY_CONFIG.get(severity, _SEVERITY_CONFIG["NORMAL"])

    # Build substitutions
    idx_display = f"{current_index:+.3f}\u03c3"
    chart_json  = _build_chart(signal)
    gen_date    = datetime.date.today().strftime("%B %d, %Y")
    tpct        = f"{threshold_pct:.1f}"

    html = (
        _HTML_TEMPLATE
        .replace("%%CHART_JSON%%",        chart_json)
        .replace("%%SEVERITY%%",          severity)
        .replace("%%SEVERITY_COLOR%%",    sc["color"])
        .replace("%%SEVERITY_BG%%",       sc["bg"])
        .replace("%%SEVERITY_BORDER%%",   sc["border"])
        .replace("%%SEVERITY_LABEL%%",    sc["label"])
        .replace("%%CURRENT_INDEX%%",     idx_display)
        .replace("%%CURRENT_DATE%%",      current_date)
        .replace("%%THRESHOLD_PCT%%",     tpct)
        .replace("%%GENERATED_DATE%%",    gen_date)
    )
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"  Saved → {OUT_HTML}")


# ── Legacy PNG render (kept for internal use) ─────────────────────────────────

def _style_ax(ax):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors=TEXT, labelsize=8)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_CLR)
    ax.grid(color=GRID_CLR, linewidth=0.5, linestyle="--", alpha=0.7)


def render() -> None:
    """Render a dark-theme PNG dashboard (legacy, internal use)."""
    signal = load_signal()
    raw    = load_raw_series()

    fig = plt.figure(figsize=(14, 12), facecolor=BG)
    fig.suptitle("FinTechCo Rate Risk Monitor",
                 color=TEXT_BRIGHT, fontsize=18, fontweight="bold", y=0.97)

    gs = gridspec.GridSpec(
        3, 1, figure=fig,
        height_ratios=[2.2, 2.2, 1.6],
        hspace=0.45, top=0.92, bottom=0.06, left=0.08, right=0.97,
    )

    ax1 = fig.add_subplot(gs[0])
    _style_ax(ax1)
    ax1.set_title("Raw Macro Indicators", color=TEXT_BRIGHT, fontsize=11, pad=6)
    ax1_r = ax1.twinx()
    ax1_r.set_facecolor(PANEL_BG)
    ax1_r.tick_params(colors=TEXT, labelsize=8)
    for spine in ax1_r.spines.values():
        spine.set_edgecolor(GRID_CLR)

    handles = []
    for series_id, (color, label) in SERIES_COLORS.items():
        s = raw[series_id].dropna()
        if series_id == "cpiaucsl":
            line, = ax1_r.plot(s.index, s.values, color=color, linewidth=1.2, label=label)
            ax1_r.set_ylabel("CPI Index", color=TEXT, fontsize=8)
            ax1_r.yaxis.label.set_color(TEXT)
            ax1_r.tick_params(axis="y", colors=TEXT, labelsize=8)
        else:
            line, = ax1.plot(s.index, s.values, color=color, linewidth=1.2, label=label)
        handles.append(line)

    ax1.set_ylabel("Rate (%)", color=TEXT, fontsize=8)
    ax1.legend(handles=handles, loc="upper left", fontsize=8,
               facecolor=PANEL_BG, edgecolor=GRID_CLR, labelcolor=TEXT_BRIGHT)

    ax2 = fig.add_subplot(gs[1])
    _style_ax(ax2)
    ax2.set_title("Composite Rate Risk Index", color=TEXT_BRIGHT, fontsize=11, pad=6)

    dates   = signal.index
    idx     = signal["risk_index"]
    flagged = signal[signal["flagged"]]

    ax2.fill_between(dates, idx, 0, where=(idx > 0), color=RED,  alpha=0.15)
    ax2.fill_between(dates, idx, 0, where=(idx < 0), color=BLUE, alpha=0.15)
    ax2.plot(dates, idx, color=TEXT_BRIGHT, linewidth=1.2, label="Risk Index")
    ax2.scatter(flagged.index, flagged["risk_index"], color=RED, s=40, zorder=5,
                label=f"Flagged (|\u03c3| > {THRESHOLD})")
    ax2.axhline(THRESHOLD,  color=RED,  linewidth=1, linestyle="--", alpha=0.7)
    ax2.axhline(-THRESHOLD, color=BLUE, linewidth=1, linestyle="--", alpha=0.7)
    ax2.axhline(0, color=GRID_CLR, linewidth=0.8)
    ax2.set_ylabel("Risk Index (\u03c3)", color=TEXT, fontsize=8)
    ax2.legend(loc="upper left", fontsize=8,
               facecolor=PANEL_BG, edgecolor=GRID_CLR, labelcolor=TEXT_BRIGHT)

    ax3 = fig.add_subplot(gs[2])
    ax3.set_facecolor(PANEL_BG)
    ax3.axis("off")
    ax3.set_title("Recent Stress Periods  (|Risk Index| > 1.5\u03c3)",
                  color=TEXT_BRIGHT, fontsize=11, pad=6)

    stress = (
        signal[signal["flagged"]][["risk_index", "fedfunds_z", "cpiaucsl_z", "dgs10_z"]]
        .sort_index(ascending=False)
        .head(6)
    )
    stress.index = stress.index.strftime("%b %Y")
    rows = [
        [date, f"{r['risk_index']:+.3f}\u03c3",
         f"{r['fedfunds_z']:+.3f}", f"{r['cpiaucsl_z']:+.3f}", f"{r['dgs10_z']:+.3f}"]
        for date, r in stress.iterrows()
    ]
    table = ax3.table(
        cellText=rows,
        colLabels=["Date", "Risk Index", "Fed Funds Z", "CPI Z", "10-Yr Z"],
        loc="center", cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.6)
    for (r, c), cell in table.get_celld().items():
        cell.set_facecolor("#252836" if r % 2 == 0 else PANEL_BG)
        cell.set_edgecolor(GRID_CLR)
        cell.set_text_props(color=TEXT_BRIGHT if r == 0 else TEXT)
        if r == 0:
            cell.set_facecolor("#1E2235")

    fig.text(0.5, 0.01,
             "Source: Federal Reserve FRED  |  Series: FEDFUNDS, CPIAUCSL, DGS10",
             ha="center", fontsize=8, color="#555566")
    fig.savefig(OUT_PNG, dpi=150, facecolor=BG, bbox_inches="tight")
    print(f"  Saved → {OUT_PNG}")


if __name__ == "__main__":
    print("Rendering dashboard...")
    render_html()
