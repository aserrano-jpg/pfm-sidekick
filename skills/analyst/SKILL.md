---
name: analyst
description: >
  Performance marketing analyst skill for Atlassian data. Routes paid channel
  efficiency, spend, and CPBD1to6 questions to paid.md; page-level funnel,
  entrances, bounce rate, and all-channel signup questions to gtm.md; OKR
  pacing, BD1to6AI actuals vs. targets, and YoY questions to bd1-6.md.
  Use for any Socrates/Databricks query across Jira, JPD, Confluence, JSM,
  Loom, Rovo, and other Atlassian products.
---

# Analyst Skill

Three dashboards. Three tables. Three jobs. Load the right reference first.

---

## Routing: which reference to load

| Question type | Reference file | Table |
|---|---|---|
| Paid channel spend, CPBD1to6, BD1-6 by program, halo, IMC/BAU/GDC/CLM, xflow vs. land via paid campaigns | `references/paid.md` | `marketing_paid_performance.paid_performance_campaigns` |
| Page-level funnel, all-channel mix, entrances, bounce rate, signup rate, UTM campaigns, WAC pages, organic vs. paid split | `references/gtm.md` | `marketing_insights.gtm_dash` |
| OKR pacing, total BD1to6AI (all channels), actuals vs. target vs. stretch scenarios, YoY, `go/fy26d16` | `references/bd1-6.md` | `production.marketing_insights.business_d1to6ai_tracking` |

**If unsure:** paid questions are about spend and channel efficiency. GTM questions are about pages and all-channel traffic. BD1-6 tracking questions are about pacing, OKR attainment, and cross-channel signup quality.

---

## Three dashboards, three jobs

**Paid Performance (`go/paiddash`) to `references/paid.md`**
Are my paid dollars working? Which platform is most efficient? Spend, CPBD1to6, paid channel BD1-6, halo for IMC.

**GTM Dashboard (`go/newgtmdash`) to `references/gtm.md`**
Why did signups drop last week? Which pages are underperforming? Full web funnel. all channels, all pages, 14 months of history.

**Biz D1to6AI (`go/fy26d16`) to `references/bd1-6.md`**
Are we generating enough quality activations this quarter? Total BD1to6AI (organic + paid), actuals vs. KR target, YoY.

---

## Rules that apply everywhere

- **Never invent data.** If the number is missing, say so and point to the right source.
- **Always include a totals row** in any breakdown table. Use `ROLLUP` or `UNION`. never present a split without the aggregate it adds up to.
- **BD1-6 has a 7-day bake lag.** The last 7 days will be understated. Always flag this when reporting recent periods.
- **Date syntax in Databricks:** use `current_date() - interval 1 day`. not `current_date() - 1`.
- **Division syntax in Databricks:** use `SUM(x) / NULLIF(SUM(y), 0)`. not `SAFE_DIVIDE`.
- **Default to business domain** (`domain_type = 'Business'` or equivalent) unless explicitly asked for all domains.
- **Spend is directional.** Data lags, IMC channels load separately, figures may not reconcile across sources. Always present spend as directional. flag it rather than reporting as a precise final number.

---

## Atlassian fiscal calendar

| Period | Dates |
|---|---|
| FY26 | Jul 1 2025 to Jun 30 2026 |
| FY26 H1 | Jul 1 2025 to Dec 31 2025 |
| FY26 H2 | Jan 1 2026 to Jun 30 2026 |
| FY26 Q1 | Jul 1 to Sep 30 2025 |
| FY26 Q2 | Oct 1 to Dec 31 2025 |
| FY26 Q3 | Jan 1 to Mar 31 2026 |
| FY26 Q4 | Apr 1 to Jun 30 2026 |
| FY25 | Jul 1 2024 to Jun 30 2025 |


---

## Writing style

Apply all rules from `../../writing-style.md` to any written output. narratives, summaries, data descriptions, and recommendations. No em dashes, no AI tropes, no filler transitions.

---

## Escalation

- DS requests: `#mat-funnels` or [request portal](https://hello.help.atlassian.cloud/servicedesk/customer/portal/310)
- Data alerts: `#mat-data-alerts`
