---
name: paid
description: >
  Reference for the Paid Performance Dashboard (go/paiddash) and the
  marketing_paid_performance schema in Socrates/Databricks. Covers paid channel
  spend, BD1-6, CPBD1to6, halo methodology for IMC, program breakdowns
  (IMC/BAU/GDC/CLM), advertised vs. base product logic, land vs. xflow motion,
  and KR pacing. Use for any question about paid channel efficiency, spend
  analysis, or ROI. Does not cover organic, direct, or in-product traffic.
---

# Paid Performance Reference

Bailey owns the paid performance flywheel for JPD, Jira/TWC, and Rovo Dev. This reference covers all queries against `marketing_paid_performance` tables in Socrates.

---

## Core mental model: Advertised Product vs. Base Product

The most important concept in the pipeline. Always clarify which dimension is being used.

| Dimension | Definition | Use for |
|---|---|---|
| Advertised product | The product featured in the ad | Spend, CPBD1to6, channel efficiency |
| Base product | The product the user signed up for | BD1-6 KR attainment, signup volume |

**The critical rule:** Spend always follows advertised product. BD1-6 KR attainment always follows base product. Never mix them in the same filter.

**Land vs. X-flow:**
- Land = advertised product = base product. The ad drove a signup for the same product.
- X-flow = advertised product ≠ base product. E.g. a Jira ad drove a JPD signup. spend lives under Jira, BD1-6 credited to JPD.

When asked about BD1-6 for any product: filter `base_product = '[product]'` and break out by both motion (Land vs. xflow) and advertised product.

When asked about spend or CPBD1to6 for any product: filter `advertised_product = '[product]'`. never filter by base product for spend queries.

---

## Tables

| Table | Schema | Purpose |
|---|---|---|
| `paid_performance_campaigns` | `marketing_paid_performance` | Daily campaign-level actuals: spend, signups, D1to6, PV. Source of truth. |
| `halo_performance_dashboard` | `marketing_paid_performance` | Halo-adjusted metrics for IMC channels. Separate from campaigns table. |
| `paid_performance_pacing` | `marketing_paid_performance` | Actuals + targets joined. Powers the dashboard. don't use for ad-hoc. |
| `paid_performance_targets` | `marketing_paid_performance` | Target-only table |
| `paid_performance_agg` | `marketing_paid_performance` | Aggregated version of campaigns (less granular) |
| `eval_ata_base` | `zone_gtm` | Anytouch Attribution. 60-day web visit history per entitlement_id |
| `pfm_quartely_master_bau` | `zone_gtm` | BAU quarterly goals |
| `pfm_quartely_imc_clm` | `zone_gtm` | IMC/CLM quarterly goals |

> ⚠️ `halo_performance_dash` is stale (data ends Sep 2025). do NOT use. Always use `halo_performance_dashboard`.

Pipeline refreshes 3x/day at 5:30AM, 2:30PM, and 10:30PM UTC.

---

## Key column names in paid_performance_campaigns

| Concept | Column name | Type |
|---|---|---|
| Signups / evaluations | `evaluations` | DOUBLE |
| Business domain BD1-6 | `business_domain_d1to6` | DOUBLE |
| Personal domain D1-6 | `personal_domain_d1to6` | DOUBLE |
| Spend | `spend` | DOUBLE |
| Channel | `channel` | STRING |
| Program | `program` | STRING |
| Advertised product | `advertised_product` | STRING |
| Base product | `base_product` | STRING |
| Date | `date` | DATE |
| Channel group | `channel_group` | STRING |
| Expand type grouping | `expand_type_grouping` | STRING |
| ROI | `roi` | DOUBLE |
| CVR (signup rate) | `cvr` | DOUBLE |
| Cost per D1-6 | `cost_per_d1t6dai` | DOUBLE |
| Projected value | `projected_value` | DOUBLE |

> There is NO `signups`, `biz_d1to6`, `halo_biz_d1to6`, or `halo_signups` column in `paid_performance_campaigns`. Halo metrics are in the separate `halo_performance_dashboard` table.

---

## Product strings (exact, case-sensitive)

| Product | Exact string |
|---|---|
| Jira Product Discovery | `'Jira Product Discovery'` |
| Jira | `'Jira'` |
| Confluence | `'Confluence'` |
| Jira Service Management | `'JIRA Service Management'` |
| Atlassian Guard | `'Atlassian Guard'` |
| Loom | `'Loom'` |
| Rovo | `'Rovo'` |
| Bitbucket | `'Bitbucket'` |
| Compass | `'Compass'` |
| Service Collection | `'Service Collection'` |
| Teamwork Collection | `'Teamwork Collection'` |
| Marketplace Addon | `'Marketplace Addon'` |

> `'JPD'` does NOT exist in the table. Always use `'Jira Product Discovery'`.

---

## Program values (exact strings in `program` column)

| Program | Exact string | Notes |
|---|---|---|
| IMC | `'IMC'` | Awareness. Use halo table for these, NOT raw campaigns. |
| BAU | `'BAU'` | Paid search (brand + non-brand) |
| CLM | `'CLM'` | Customer lifecycle / cross-sell |
| Experiment | `'Experiment'` | Includes podcast in FY26 |
| ABM | `'ABM'` | Account-based marketing |
| other | `'other'` | Catch-all |

> Podcast (`paid-podcast`) shows up under `program = 'Experiment'` in FY26, NOT under IMC. Always check `program` filter when querying podcast.

---

## Channel values (exact strings in `channel` column)

| Channel | Exact string | Program | Notes |
|---|---|---|---|
| Brand Paid Search (BPS) | `'paid-search-branded'` | BAU | High intent, low volume |
| Non-Brand Paid Search (NBPS) | `'paid-search-non-branded'` | BAU/IMC | Volume driver |
| Paid Social | `'paid-social'` | BAU/GDC/IMC/CLM | Across multiple programs |
| Paid Display | `'paid-display'` | BAU/GDC/IMC/CLM | |
| Podcast | `'paid-podcast'` | Experiment | Not in IMC in FY26 |
| Review sites | `'paid-review-sites'` | BAU/IMC/Experiment | |
| Affiliate | `'paid-affiliate'` | BAU | |

> `'BPS'`, `'NBPS'`, `'Podcast'`, `'Reddit'`, `'YouTube'`, `'LinkedIn'` are NOT valid channel strings. Reddit and LinkedIn brand awareness live within `paid-social`.

---

## Programs. what they are and what metric to use

| Program | What it is | Metric to use |
|---|---|---|
| IMC | Awareness. Podcast, Reddit, LinkedIn brand, Video | Halo BD1-6 (from `halo_performance_dashboard`) |
| BAU | Paid search. brand (BPS) and non-brand (NBPS) | `business_domain_d1to6`, CPBD1to6 |
| GDC | Growth demand. mid-funnel paid social and display | `business_domain_d1to6`, `evaluations` |
| CLM | Customer lifecycle. cross-sell, upsell to existing customers | `business_domain_d1to6`, `evaluations` |
| Experiment | Test campaigns (includes Podcast in FY26) | Depends on test objective |

For IMC always use halo metrics. For BAU/GDC/CLM use raw LTA unless a specific incrementality test applies.

---

## Reporting rules

| What you're reporting | Filter to use |
|---|---|
| BD1-6 KR attainment | `WHERE base_product = '[exact product string]'` |
| Spend / CPBD1to6 | `WHERE advertised_product = '[exact product string]'` |
| Xflow BD1-6 | `WHERE base_product = '[product]' AND advertised_product != '[product]'` |
| Land BD1-6 | `WHERE base_product = '[product]' AND advertised_product = '[product]'` |
| Halo metrics (IMC) | Query `halo_performance_dashboard` separately. no halo columns in campaigns table |
| Signups | `evaluations` column (total), `evaluations_with_business_domain` (biz domain only) |
| BD1-6 | `business_domain_d1to6` column |

---

## Halo methodology (IMC channels only)

Halo metrics live in `marketing_paid_performance.halo_performance_dashboard`.

Only applies to IMC (Awareness) campaigns. Reddit, Podcasts, LinkedIn, Video.

1. Run incrementality tests (geo holdout or matched market) per channel
2. Get calibration multiplier from test results
3. Apply: `Halo metric = LTA metric × calibration multiplier`

The 40x Podcast halo multiplier means 1 podcast BD1-6 generates 40x downstream revenue vs. direct BD1-6.

**Halo table notes (verified May 2026):**
- Date range: Jun 2025 to Jun 2026
- Key columns: `program_signups` (LTA signups), `new_total_signups` (halo+LTA signups), `program_biz_d1to6` (LTA BD1-6), `adjusted_biz_d1to6` (halo add-on), `new_total_biz_d1to6` (combined BD1-6), `impressions`
- `product` = base product. Filtering by `product` returns ALL advertised products that drove signups for that base product. including xflow. To restrict to a specific advertised product, filter by `program LIKE '%[product]%'`.
- `date` column is STRING type. use `CAST(date AS DATE)` for date operations.
- Always filter `program LIKE '%[product]%'` when querying halo for a specific product. Without this, the table returns ALL campaigns from any advertised product that drove halo credit. including unrelated xflow.

```sql
-- Halo metrics for IMC
SELECT
  CAST(date_trunc('month', CAST(date AS DATE)) AS DATE) AS month,
  product,
  program,
  SUM(program_biz_d1to6)   AS biz_d1to6_lta,
  SUM(adjusted_biz_d1to6)  AS halo_only,
  SUM(new_total_biz_d1to6) AS biz_d1to6_halo_lta,
  SUM(spend)               AS spend
FROM marketing_paid_performance.halo_performance_dashboard
WHERE product = 'Jira Product Discovery'
  AND program LIKE '%Jira Product Discovery%'
  AND CAST(date AS DATE) >= '2026-04-01'
  AND CAST(date AS DATE) <= CAST(current_date() - interval 1 day AS DATE)
GROUP BY 1, 2, 3
ORDER BY 6 DESC NULLS LAST
```

---

## SQL syntax rules (Databricks)

```sql
-- Date: use interval syntax
date <= current_date() - interval 1 day   -- correct
date <= current_date() - 1                -- wrong

-- Division: avoid divide by zero
SUM(spend) / NULLIF(SUM(business_domain_d1to6), 0) AS cpbd1_6   -- correct
SAFE_DIVIDE(SUM(spend), SUM(business_domain_d1to6))              -- wrong (BigQuery only)
```

---

## Land vs. xflow motion filters

```sql
-- Land only: advertised product = base product
WHERE advertised_product = base_product

-- X-flow only: advertised product ≠ base product
WHERE advertised_product != base_product

-- X-flow to JPD specifically
WHERE base_product = 'Jira Product Discovery'
  AND advertised_product != 'Jira Product Discovery'

-- JPD Land only
WHERE base_product = 'Jira Product Discovery'
  AND advertised_product = 'Jira Product Discovery'
```

---

## Program filters

```sql
-- BAU (paid search. brand + non-brand)
WHERE program = 'BAU'
  AND channel IN ('paid-search-branded', 'paid-search-non-branded')

-- BPS only
WHERE program = 'BAU'
  AND channel = 'paid-search-branded'

-- NBPS only
WHERE program = 'BAU'
  AND channel = 'paid-search-non-branded'

-- IMC (use halo table for metrics, not campaigns)
WHERE program = 'IMC'

-- Podcast (Experiment program in FY26)
WHERE channel = 'paid-podcast'

-- CLM
WHERE program = 'CLM'
```

---

## Core query templates

### BD1-6 by month. any product (base product view)
```sql
SELECT
  date_trunc('month', date)    AS month,
  channel,
  advertised_product,
  base_product,
  SUM(spend)                   AS spend,
  SUM(evaluations)             AS signups,
  SUM(business_domain_d1to6)   AS bd1_6,
  SUM(spend) / NULLIF(SUM(business_domain_d1to6), 0) AS cpbd1_6
FROM marketing_paid_performance.paid_performance_campaigns
WHERE base_product = 'Jira Product Discovery'
  AND date >= '2025-08-01'
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 7 DESC
```

### Land vs. xflow motion breakdown
```sql
SELECT
  date_trunc('month', date) AS month,
  CASE WHEN advertised_product = base_product
       THEN 'Land'
       ELSE 'X-flow (' || advertised_product || ' -> ' || base_product || ')'
  END                        AS motion,
  advertised_product,
  channel,
  program,
  SUM(spend)                 AS spend,
  SUM(evaluations)           AS signups,
  SUM(business_domain_d1to6) AS bd1_6
FROM marketing_paid_performance.paid_performance_campaigns
WHERE base_product = 'Jira Product Discovery'
  AND date >= '2025-07-01'
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1 DESC, 8 DESC
```

### BPS + NBPS breakdown
```sql
SELECT
  date_trunc('month', date)  AS month,
  channel,
  advertised_product,
  SUM(spend)                 AS spend,
  SUM(evaluations)           AS signups,
  SUM(business_domain_d1to6) AS bd1_6,
  SUM(spend) / NULLIF(SUM(business_domain_d1to6), 0) AS cpbd1_6
FROM marketing_paid_performance.paid_performance_campaigns
WHERE channel IN ('paid-search-branded', 'paid-search-non-branded')
  AND advertised_product = 'Jira Product Discovery'
  AND date >= '2025-07-01'
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 2
```

### WoW BD1-6 trend
```sql
SELECT
  date_trunc('week', date)   AS week,
  channel,
  program,
  SUM(spend)                 AS spend,
  SUM(evaluations)           AS signups,
  SUM(business_domain_d1to6) AS bd1_6
FROM marketing_paid_performance.paid_performance_campaigns
WHERE base_product = 'Jira Product Discovery'
  AND date >= current_date() - interval 56 day
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 6 DESC
```

### Xflow sources driving BD1-6 for a product
```sql
SELECT
  date_trunc('month', date)  AS month,
  advertised_product,
  channel,
  program,
  SUM(evaluations)           AS signups,
  SUM(business_domain_d1to6) AS bd1_6
FROM marketing_paid_performance.paid_performance_campaigns
WHERE base_product = 'Jira Product Discovery'
  AND advertised_product != 'Jira Product Discovery'
  AND date >= '2025-07-01'
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 6 DESC
```

### Spend efficiency (advertised product view)
```sql
SELECT
  date_trunc('month', date) AS month,
  channel,
  SUM(spend)                 AS spend,
  SUM(business_domain_d1to6) AS bd1_6,
  SUM(spend) / NULLIF(SUM(business_domain_d1to6), 0) AS cpbd1_6
FROM marketing_paid_performance.paid_performance_campaigns
WHERE advertised_product = 'Jira Product Discovery'
  AND date >= '2025-07-01'
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2
ORDER BY 1 DESC
```

### Check table freshness
```sql
DESC HISTORY marketing_paid_performance.paid_performance_pacing;
```

---

## Diagnostic framework. what drove the change

Work through this order when performance shifts WoW or MoM:

1. **Motion split**. Land vs. X-flow? Different levers, different owners.
2. **Paid vs. organic**. Is it paid channels or unpaid? (Organic = GTM/flywheel data, not this pipeline.)
3. **Program**. IMC, BAU, GDC, CLM, Experiment?
4. **Channel**. BPS, NBPS, paid-social, paid-display, paid-podcast?
5. **Advertised product**. Which product's campaign drove it?
6. **Spend**. Did budget change, or did CVR change with flat spend?
7. **CVR**. Same signups, fewer BD1-6? Points to FFP quality, product experiment, or targeting shift.
8. **Product/experiment event**. Any product changes, ML model updates, or experiments in that window?
9. **Data artifact**. Check known bad periods before concluding anything.

| Signal | Likely cause |
|---|---|
| BD1-6 drops, signups flat | CVR / FFP quality issue. Check product events, targeting, expand type. |
| BD1-6 drops, signups drop | Volume issue. Check spend, channel health, campaign pauses. |
| Xflow BD1-6 drops, Land flat | Product-surface or ML model change (Nav4, MSR, YBR). Not paid media. |
| CPBD1to6 spikes | Spend up but BD1-6 didn't follow. Check CVR, channel mix shift. |
| Sudden spike in one advertised product | Could be pipeline artifact. always verify before reporting. |

---

## Gotchas

| Gotcha | Rule |
|---|---|
| `entitlement_type` filter for Jira | Add `AND entitlement_type = 'standalone'` when querying Jira `business_domain_d1to6` in `paid_performance_pacing` to avoid inflation from collection children. Confirmed fix as of May 2026 recalibration. |
| NBPS anomalies May 2026 | NBPS had data quality flags on May 5, 7, 17 2026 (Anomalo alerts). Treat May NBPS numbers as directional. |
| `'JPD'` doesn't exist | Always use `'Jira Product Discovery'` |
| No halo columns in campaigns table | Halo lives in `halo_performance_dashboard` (NOT `halo_performance_dash`). query separately |
| `SAFE_DIVIDE` is BigQuery | Use `SUM(x) / NULLIF(SUM(y), 0)` in Databricks |
| `current_date() - 1` doesn't work | Use `current_date() - interval 1 day` |
| Spend ≠ base product | Never filter `base_product = '[product]'` and report spend. spend is by advertised product |
| Podcast is in Experiment program | `channel = 'paid-podcast'` AND `program = 'Experiment'` in FY26 |
| Mar...Apr 2026 Jira xflow spike | `content_product` artifact confirmed by DS. do not use for planning |
| `evaluations` ≠ unique signups | `evaluations` may include eval-level counting. Clarify with DS if deduplication needed. |
| Targets: original vs. current | Use original targets for KR attainment reporting. Current targets are PA internal only. |
| Don't use `paid_performance_pacing` for ad-hoc | It has targets baked in. use `paid_performance_campaigns` |
| Halo cols are null for non-IMC channels | BPS/NBPS = null halo. Never SUM halo across all channels |

---

## Pipeline data flow

```
Platform APIs (Google, Meta, LinkedIn, Reddit, etc.)
    |
zone_gtm raw tables (eval_attr_base, channel_override, identity_map)
    |
marketing_paid_performance.paid_performance_campaigns  [refreshed 3x/day]
    |
marketing_paid_performance.paid_performance_pacing     [actuals + targets]
    |
Tableau: Paid Performance Dashboard
```

Halo columns added post-join from incrementality test multipliers.

---

## Fiscal year date ranges

| Period | Date range |
|---|---|
| FY26 | `'2025-07-01'` to `'2026-06-30'` |
| FY26 H1 | `'2025-07-01'` to `'2025-12-31'` |
| FY26 H2 | `'2026-01-01'` to `'2026-06-30'` |
| FY26 Q1 | `'2025-07-01'` to `'2025-09-30'` |
| FY26 Q2 | `'2025-10-01'` to `'2025-12-31'` |
| FY26 Q3 | `'2026-01-01'` to `'2026-03-31'` |
| FY26 Q4 | `'2026-04-01'` to `'2026-06-30'` |
| FY25 | `'2024-08-01'` to `'2025-07-31'` |

---

## Escalation and documentation

- DS requests: `#mat-funnels` or [request portal](https://hello.help.atlassian.cloud/servicedesk/customer/portal/310)
- Data alerts: `#mat-data-alerts`
- Dashboard: [go/paiddash](https://data-portal.internal.atlassian.com/reveal/tableau_workbook/49c773bf-7047-4a7a-a52c-e1a5e8de157e)
- [Paid Performance Dashboard User Guide](https://hello.atlassian.net/wiki/spaces/ANALYTICS/pages/2855403840)
- [Paid Performance Analyst Guide](https://hello.atlassian.net/wiki/spaces/ANALYTICS/pages/2930442253)
- [Advertised vs. Base Product](https://hello.atlassian.net/wiki/spaces/ANALYTICS/pages/3326030695)
- [Halo Columns Pipeline](https://hello.atlassian.net/wiki/spaces/ANALYTICS/pages/3909848717)
- [GTM DS home](https://hello.atlassian.net/wiki/spaces/ANALYTICS/pages/342970189)
