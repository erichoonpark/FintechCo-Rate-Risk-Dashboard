# RISK-101 — Portfolio Impact Estimator

**Status:** Open  
**Priority:** High  
**Assignee:** Unassigned

## Summary
Add a portfolio impact estimator panel to the rate risk dashboard.

## Description
The CFO wants to know what a rate hike means in dollars, not in standard deviations. Add an interactive panel to the dashboard that shows the estimated dollar impact of rate shocks across the lending portfolio.

**Inputs:** Loan book size (slider, $500M–$10B)  
**Outputs:** Estimated NII (net interest income) impact and prepayment risk for three scenarios: +25 bps, +50 bps, +100 bps

## Acceptance Criteria
- Panel renders in `output/risk_dashboard.html` without requiring a server
- Uses current `risk_signal.json` data (no new API calls)
- Loan book slider is interactive — scenarios update live
- Methodology: 60% variable-rate assumption, 0.72 bps NIM compression per 100 bps rate move
- Shows NIM compression (bps) and estimated P&L impact ($M) per scenario
