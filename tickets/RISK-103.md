# RISK-103 — Yield Curve Inversion Signal

**Status:** Open  
**Priority:** Medium  
**Assignee:** Unassigned

## Summary
Add a yield curve inversion signal as a secondary recession leading indicator.

## Description
Add a secondary signal to the dashboard that flags when the 10Y–2Y Treasury spread inverts (goes negative). Yield curve inversion is a well-established leading indicator for recession and is relevant to FinTechCo's credit risk posture.

## Acceptance Criteria
- 10Y–2Y spread computed from existing FRED data (DGS10 already ingested; add DGS2 series)
- Inversion periods flagged visually on the dashboard
- Signal displayed alongside or below the existing risk index chart
- Alert fires when spread < 0 for 2+ consecutive months
