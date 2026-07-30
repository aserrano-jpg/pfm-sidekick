# Source Routing Reference

Decision table for the insights ingestion skill. For each metric or question,
this tells you which source to use and which query to run.

Load `@skills/analyst/SKILL.md` before running any Socrates query.

---

## Primary routing table

| Metric or question | Source | Query | Notes |
|---|---|---|---|
| BD1-6 actuals vs. target (paid channels) | Socrates: paid.md | MBR-1 | Paid channels only; excludes organic |
| BD1-6 total (all channels) vs. OKR target | Socrates: bd1-6.md | MBR-3 | Use for MBR; this is the OKR metric |
| Land vs. xflow motion split | Socrates: paid.md | MBR-2 | Paid only; no organic xflow |
| Channel group breakdown (paid vs. organic share) | Socrates: bd1-6.md | MBR-4 | All channels; use for MBR channel mix |
| Paid spend, CPBD1-6, CAC by channel | Socrates: paid.md | MBR-1 / TW-1 | Spend is directional |
| WoW BD1-6 trend | Socrates: paid.md | TW-1 | Paid channels; flag 7-day lag |
| All-channel WoW trend (organic + paid) | Socrates: gtm.md | TW-2 | GTM table; all sources |
| Paid vs. organic split | Socrates: gtm.md | TW-3 | GTM table; use CASE for grouping |
| Page-level funnel (entrance, signup, BD1-6 by page) | Socrates: gtm.md | Custom | gtm_dash only; not in paid table |
| YoY BD1-6 comparison | Socrates: bd1-6.md | MBR-5 | Only at quarter-end or on request |
| Competitor actions and market signals | Optimal deck | Manual extraction | Not in Socrates; deck is primary source |
| Upcoming initiatives, owners, timelines | Optimal deck | Manual extraction | Not in Socrates; deck is primary source |
| Risks, blockers, contingencies | Optimal deck | Manual extraction | May appear in Slack or Confluence too |
| BD1-6 target for the period | Optimal deck or Atlas KR | Manual extraction | Target is set in Atlas; deck usually shows it |
| Creative or audience test results | Optimal deck | Manual extraction | Not in Socrates |

---

## Which table for which question

### Use `marketing_paid_performance.paid_performance_campaigns` (paid.md) when:
- Question is about paid channel efficiency, spend, CPBD1-6
- You need Land vs. xflow motion split for paid only
- You need BPS vs. NBPS breakdown
- You need program-level breakdown (IMC, BAU, GDC, CLM)

### Use `marketing_insights.gtm_dash` (gtm.md) when:
- Question is about all-channel traffic mix (organic + paid combined)
- You need page-level funnel data (entrances, bounce rate, signup rate)
- You need UTM campaign attribution
- You need paid vs. organic share of total

### Use `production.marketing_insights.business_d1to6ai_tracking` (bd1-6.md) when:
- Question is about OKR pacing or attainment vs. KR target
- You need total BD1to6AI across all channels (the MBR headline number)
- You need channel group breakdown (paid vs. organic as share of total)
- You need YoY comparison

---

## Optimal deck extraction routing

When an Optimal deck URL is provided, use this extraction map:

| Slide section to look for | Maps to insights block field |
|---|---|
| BD1-6 / Activation scorecard | METRICS: BD1-6 actuals, target, delta |
| Paid channel performance table | CHANNEL BREAKDOWN: by channel |
| Spend summary | METRICS: Spend (mark as directional) |
| Organic / email performance | CHANNEL BREAKDOWN: organic row |
| Market or competitive slide | COMPETITIVE section |
| Forward-looking / roadmap slide | OPPORTUNITIES section |
| Risks or blockers slide | RISKS AND BLOCKERS section |
| CAC / LTV / unit economics slide | METRICS: CAC, LTV to CAC ratio |

If the deck does not have a dedicated risks or competitive slide, check the
"key insights" or "summary" slides. Those often contain flagged items.

---

## Data source priority order

When both deck and Socrates are available for the same metric:

1. Use Socrates for all quantitative metrics (more reliable, auditable).
2. Use deck for context, competitive signals, forward-looking initiatives, and
   any metric not in Socrates (targets, CAC, LTV if not in tables).
3. If the two sources conflict, note the discrepancy in the MISSING DATA field.
   Do not silently resolve it. Flag it for the human reviewer.

---

## Report type to query set mapping

### TOFU Weekly
Minimum query set: TW-1, TW-2, TW-3
Optional: MBR-1 (if month-to-date context is needed)

### MBR LAND
Minimum query set: MBR-1, MBR-3, MBR-4
Optional: MBR-2 (if Land vs. xflow split is a focus), MBR-5 (quarter-end only)

---

## Fiscal calendar (Atlassian)

| Period | Dates |
|---|---|
| FY26 Q4 | Apr 1 to Jun 30 2026 |
| FY26 Q3 | Jan 1 to Mar 31 2026 |
| FY26 Q2 | Oct 1 to Dec 31 2025 |
| FY26 Q1 | Jul 1 to Sep 30 2025 |
| FY26 | Jul 1 2025 to Jun 30 2026 |

Use these date ranges in WHERE clauses when filtering by fiscal period.
