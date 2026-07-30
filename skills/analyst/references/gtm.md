---
name: gtm
description: >
  Reference for the GTM Dashboard (go/newgtmdash) and its underlying
  marketing_insights.gtm_dash table. Covers all traffic sources. organic,
  paid, direct, referral, in-product. at page and channel level. Use for
  entrances, bounce rate, signup rate, D1to6AI rate, FFP, WAC page performance,
  UTM campaign tracking, and all-channel funnel diagnostics.
---

# GTM Dashboard Reference

The GTM Dashboard (`go/newgtmdash`) is the single source for page and campaign-level metrics across all traffic sources. It answers: what pages and channels drove traffic, signups, and D1to6AI? It covers organic, direct, paid, referral, in-product, and all other channels together.

**Key distinction from paid reference:**
- GTM Dash: all traffic sources, page-level granularity, entrances + signups + D1to6AI + FFP + bounce rate
- Paid Performance: paid channels only, campaign-level spend + BD1-6 + CPBD1to6

---

## Primary table

```
marketing_insights.gtm_dash
```

- Refreshes daily (runs on previous day's snapshot of `zone_marketing.eval_attr_base`)
- Covers last 14 months of data
- Partition column: `date` (DATE type)
- Large dataset. page × channel × day granularity. Always aggregate and filter. Queries across 3+ months can take 3 to 5 minutes.

---

## Dimension columns

| Column | Type | Description |
|---|---|---|
| `date` | DATE | Partition column |
| `content_type` | STRING | Content type credited with the signup |
| `site` | STRING | Site credited with the signup (WAC, Self-help, Trello, Marketplace, etc.) |
| `page_type` | STRING | Page type (Homepage, Product Tour, Sign In & Sign Up, Work Life Blogs, etc.) |
| `content_product` | STRING | Product the page's content maps to |
| `page` | STRING | Individual page URL/path |
| `content_split` | STRING | "WAC - sign up intent", "WAC - top of funnel", or "Other" |
| `channel` | STRING | Marketing channel. last-touch attribution (LTA) |
| `campaign_name` | STRING | From `utm_campaign` parameter. can be null/blank |
| `campaign_type_der` | STRING | Extracted campaign type from campaign_name |
| `campaign_geo_der` | STRING | Extracted campaign geo from campaign_name |
| `campaign_asset_der` | STRING | Extracted campaign asset from campaign_name |
| `campaign_language_der` | STRING | Extracted campaign language from campaign_name |
| `campaign_funnel_der` | STRING | Extracted campaign funnel from campaign_name |
| `campaign_device_der` | STRING | Extracted campaign device from campaign_name |
| `country` | STRING | Country by IP address |
| `continent` | STRING | Continent by IP address |
| `language` | STRING | Language of landing page |
| `language_country` | STRING | Language-country combination |
| `device_type` | STRING | Device used (desktop, mobile, tablet) |
| `base_product` | STRING | Product the user signed up for |
| `expand_type` | STRING | Expand type tier 1 |
| `expand_type_tier2` | STRING | Expand type tier 2 |
| `domain_type` | STRING | Business vs. personal. Values: `'Business'`, `'Personal'`, null. Default: always filter `domain_type = 'Business'` unless explicitly asked. |
| `edition` | STRING | Free, Standard, Trial, Premium |
| `job_function` | STRING | Job function of the account owner |
| `team_type` | STRING | Tech vs. business team type |
| `signup_quality` | STRING | Signup quality score |
| `is_paid_customer` | BOOLEAN | Entitlement level is "Full" |
| `account_segment` | STRING | Account segment |
| `sales_classification` | STRING | High-touch vs. low-touch |
| `entitlement_type` | STRING | standalone / collection-child / collection-parent |
| `ai_source_flag` | STRING | AI source flag (added Jan 2026) |
| `ai_source_platform_name` | STRING | AI source platform name |

---

## Metric columns

| Column | Type | Description |
|---|---|---|
| `total_entrances` | LONG | Entrances from `zone_marketing.traffic_agg` |
| `total_page_views` | LONG | Page views |
| `bounced_entrances` | LONG | Bounced entrances (bounce=1 AND session=1) |
| `first_time_visitor` | LONG | First-time visitors |
| `evaluations` | DOUBLE | Signups |
| `evals_with_d1to6d` | DOUBLE | D1to6AI. signups that activated in days 1 to 6 |
| `pv` | DOUBLE | Lifetime projected value |
| `purchases` | DOUBLE | Purchase credit |
| `first_full_purchases` | DOUBLE | First full purchases (FFP). based on FFP date, not cohort |
| `w2wai` | DOUBLE | Week 2 WAU instance credit |

---

## Derived conversion rates

| Rate | Formula |
|---|---|
| Bounce Rate | `SUM(bounced_entrances) / NULLIF(SUM(total_entrances), 0)` |
| Signup Rate | `SUM(evaluations) / NULLIF(SUM(total_entrances), 0)` |
| D1to6AI Rate | `SUM(evals_with_d1to6d) / NULLIF(SUM(evaluations), 0)` |
| Purchase Rate | `SUM(purchases) / NULLIF(SUM(evaluations), 0)` |
| FFP Rate | `SUM(first_full_purchases) / NULLIF(SUM(evaluations), 0)` |

---

## Output labeling: always use these aliases

When filtering `domain_type = 'Business'` (the default):
- `SUM(evaluations)` to `biz_signups`
- `SUM(evals_with_d1to6d)` to `bd1_6`
- `SUM(first_full_purchases)` to `ffp`

When querying all domain types (no domain_type filter):
- `SUM(evaluations)` to `total_signups`
- `SUM(evals_with_d1to6d)` to `d1to6ai`

---

## Verified channel strings (confirmed May 2026)

| Channel value | Category | Notes |
|---|---|---|
| `'paid-search-branded'` | Paid | Brand paid search (BPS) |
| `'paid-search-non-branded'` | Paid | Non-brand paid search (NBPS) |
| `'paid-social'` | Paid | Paid social (all platforms) |
| `'paid-display'` | Paid | Paid display |
| `'paid-podcast'` | Paid | Podcast |
| `'paid-review-sites'` | Paid | Review sites |
| `'paid-affiliate'` | Paid | Affiliate |
| `'organic'` | Organic | Organic search / SEO |
| `'direct'` | Direct | Direct traffic |
| `'email'` | Email | Email / IPM |
| `'referral-external'` | Referral | External referral |
| `'referral-internal'` | Referral | Internal referral |
| `'self-referral'` | Referral | Self-referral |
| `'in-product'` | In-product | In-product touchpoints |
| `'in-product-referral'` | In-product | In-product referral |
| `'unpaid-social'` | Social | Organic social |
| `'unpaid-video'` | Social | Organic video |
| `'engagement-engine'` | In-product | Engagement engine |
| `'comarketing'` | Other | Co-marketing |
| `'no-traffic'` | Other | No traffic attribution |
| `'other'` | Other | Other |
| `'Slack App Directory'` | Other | Slack App Directory |
| `'mobile-appstore'` | Other | Mobile app store |

> Paid-only: `WHERE channel LIKE 'paid-%'`
> Organic only: `WHERE channel = 'organic'`
> Exclude no-attribution: `WHERE channel NOT IN ('no-traffic', 'other')`

---

## Verified base_product strings (confirmed May 2026)

| Product | Exact string |
|---|---|
| Jira Product Discovery | `'Jira Product Discovery'` |
| Jira | `'Jira'` |
| Confluence | `'Confluence'` |
| Jira Service Management | `'JIRA Service Management'` |
| Customer Service Management | `'Customer Service Management'` |
| Loom | `'Loom'` |
| Atlassian Guard | `'Atlassian Guard'` |
| Bitbucket | `'Bitbucket'` |
| Compass | `'Compass'` |
| Trello | `'Trello'` |
| Opsgenie | `'Opsgenie'` |
| Service Collection | `'Service Collection'` |
| Teamwork Collection | `'Teamwork Collection'` |
| Atlassian Analytics | `'Atlassian Analytics'` |
| StatusPage | `'StatusPage'` |
| Marketplace Addon | `'Marketplace Addon'` |

---

## Key dimension hierarchies

| Dimension | Hierarchy |
|---|---|
| Channel | Macro channel to Channel group to Individual channel |
| Site | Site group (Other/WAC/Trello/Self-help/Customer Success/Marketplace/Bitbucket) to Individual site |
| Page type | Page type group (Other/Product Tour/Homepage/Sign In & Sign Up/Work Life Blogs) to Page type |
| Content product | Content Product Group (Other/Jira+JSM+CON/Trello/Bitbucket) to Content Product |
| Base product | Base Product Group to Base Product |
| Country | Country Group to Country |
| Language | Language Group (English/French/German/Japanese/Portuguese Brazil/Spanish/Other) to Language |
| Expand type | Expand Type Tier 2 to Expand Type |

---

## Core queries

### Channel mix overview for any product
```sql
SELECT
  date_trunc('month', date)                                AS month,
  channel,
  base_product,
  SUM(total_entrances)                                     AS entrances,
  SUM(evaluations)                                         AS biz_signups,
  SUM(evals_with_d1to6d)                                   AS bd1_6,
  SUM(first_full_purchases)                                AS ffp,
  SUM(evaluations) / NULLIF(SUM(total_entrances), 0)       AS signup_rate,
  SUM(evals_with_d1to6d) / NULLIF(SUM(evaluations), 0)    AS bd1_6_rate,
  SUM(first_full_purchases) / NULLIF(SUM(evaluations), 0) AS ffp_rate
FROM marketing_insights.gtm_dash
WHERE base_product = 'Jira Product Discovery'   -- change per product
  AND domain_type = 'Business'
  AND date >= '2025-07-01'
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 5 DESC
```

### Paid vs. organic split
```sql
SELECT
  date_trunc('month', date)    AS month,
  CASE
    WHEN channel LIKE 'paid-%' THEN 'Paid'
    WHEN channel = 'organic'   THEN 'Organic'
    WHEN channel = 'direct'    THEN 'Direct'
    WHEN channel IN ('in-product', 'in-product-referral', 'engagement-engine') THEN 'In-product'
    WHEN channel = 'email'     THEN 'Email'
    ELSE 'Other'
  END                           AS channel_category,
  base_product,
  SUM(total_entrances)          AS entrances,
  SUM(evaluations)              AS biz_signups,
  SUM(evals_with_d1to6d)        AS bd1_6
FROM marketing_insights.gtm_dash
WHERE base_product = 'Jira Product Discovery'
  AND domain_type = 'Business'
  AND date >= '2025-07-01'
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 5 DESC
```

### Top WAC pages by BD1-6
```sql
SELECT
  page,
  site,
  content_product,
  SUM(total_entrances)          AS entrances,
  SUM(evaluations)              AS biz_signups,
  SUM(evals_with_d1to6d)        AS bd1_6,
  SUM(first_full_purchases)     AS ffp,
  SUM(evals_with_d1to6d) / NULLIF(SUM(evaluations), 0) AS bd1_6_rate
FROM marketing_insights.gtm_dash
WHERE base_product = 'Jira Product Discovery'
  AND domain_type = 'Business'
  AND site LIKE '%atlassian.com%'
  AND date >= '2026-01-01'
  AND date <= current_date() - interval 1 day
  AND evaluations > 0
GROUP BY 1, 2, 3
ORDER BY 6 DESC
LIMIT 30
```

### UTM campaign tracking
```sql
SELECT
  date_trunc('month', date)     AS month,
  campaign_name,
  channel,
  SUM(total_entrances)          AS entrances,
  SUM(evaluations)              AS biz_signups,
  SUM(evals_with_d1to6d)        AS bd1_6,
  SUM(first_full_purchases)     AS ffp
FROM marketing_insights.gtm_dash
WHERE campaign_name LIKE '%jpd%'          -- adjust for your campaign naming
  AND domain_type = 'Business'
  AND date >= '2025-07-01'
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 5 DESC
```

### WoW signup and D1to6AI trend
```sql
SELECT
  date_trunc('week', date)      AS week,
  channel,
  SUM(total_entrances)          AS entrances,
  SUM(evaluations)              AS biz_signups,
  SUM(evals_with_d1to6d)        AS bd1_6,
  SUM(evals_with_d1to6d) / NULLIF(SUM(evaluations), 0) AS bd1_6_rate
FROM marketing_insights.gtm_dash
WHERE base_product = 'Jira Product Discovery'
  AND domain_type = 'Business'
  AND date >= current_date() - interval 56 day
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2
ORDER BY 1 DESC, 4 DESC
```

### Expand type breakdown (Land vs. xflow proxy)
```sql
SELECT
  date_trunc('month', date)     AS month,
  expand_type,
  expand_type_tier2,
  SUM(evaluations)              AS biz_signups,
  SUM(evals_with_d1to6d)        AS bd1_6,
  SUM(first_full_purchases)     AS ffp
FROM marketing_insights.gtm_dash
WHERE base_product = 'Jira Product Discovery'
  AND domain_type = 'Business'
  AND date >= '2025-07-01'
  AND date <= current_date() - interval 1 day
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 4 DESC
```

---

## Gotchas

| Gotcha | Rule |
|---|---|
| `evals_with_d1to6d` ≠ `business_domain_d1to6` | GTM dash D1to6AI includes personal + business domain signups. For business-only BD1-6, use `paid_performance_campaigns`. |
| FFP is date-based, not cohort-based | `first_full_purchases` uses the FFP effective date, not signup cohort. Changed Mar 14, 2025. |
| Pipeline runs on prior day snapshot | May differ slightly from raw `eval_attr_base`. Intentional. |
| Influenced D1to6AI (ATA) removed | Removed Apr 21, 2025. For anytouch attribution, query `zone_gtm.eval_ata_base` directly with 60-day lookback. |
| vNext migration Jul 5, 2025 | Dashboard switched to DE-owned vNext data endpoint. |
| AI Source Flag added Jan 14, 2026 | `ai_source_flag` and `ai_source_platform_name` only populated from Jan 2026 onwards. |
| Child License Toggle added Feb 13, 2026 | `entitlement_type` added to distinguish standalone / collection-child / collection-parent. |
| Data window | Only last 14 months available. For older data, use upstream tables. |
| `content_product` ≠ `base_product` | `content_product` = what the page is about. `base_product` = what the user signed up for. They can differ. |
| 7-day BD1-6 lag | `evals_with_d1to6d` has a ~7-day lag to fully bake. Always flag for recent periods. |

---

## Escalation

- Slack: `#mat-funnels` or `#mat-data-alerts`
- Owner: Mary Xu
- Dashboard: [go/newgtmdash](https://data-portal.internal.atlassian.com/reveal/tableau_workbook/4f0f95ad-f71c-4386-8f6e-2e3383c9813f)
- Confluence: [GTM Dashboard User Guide](https://hello.atlassian.net/wiki/spaces/ANALYTICS/pages/3021448832)
