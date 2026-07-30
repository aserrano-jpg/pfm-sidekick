# Socrates Query Templates: Insights Ingestion

Ready-to-run SQL for the insights ingestion skill. Copy, paste period and
product values, and run in Socrates. All queries use Databricks syntax.

See `@skills/analyst/SKILL.md` for routing rules and table documentation.

---

## Syntax rules (apply to all queries)

- Date arithmetic: `current_date() - interval N day` (not `current_date() - N`)
- Safe division: `SUM(x) / NULLIF(SUM(y), 0)` (not `SAFE_DIVIDE`)
- Default domain filter: `domain_type = 'Business'` unless all domains requested
- Spend is directional. Present as approximate, not precise.
- BD1-6 has a 7-day bake lag. Flag when reporting last 7 days.

---

## TOFU Weekly Queries

### TW-1: WoW BD1-6 trend (paid channels)
Source table: `marketing_paid_performance.paid_performance_campaigns`

```sql
SELECT
    date_trunc('week', date) AS week_start,
    channel,
    SUM(bd1_6)              AS bd1_6,
    SUM(spend)              AS spend,
    SUM(bd1_6) / NULLIF(SUM(spend), 0) * 1000 AS cpbd1_6_per_k
FROM marketing_paid_performance.paid_performance_campaigns
WHERE
    date >= current_date() - interval 28 day
    AND base_product = '<PRODUCT>'       -- e.g. 'Jira', 'Confluence', 'Rovo'
    AND domain_type = 'Business'
    AND motion = 'Land'
GROUP BY 1, 2
ORDER BY 1 DESC, bd1_6 DESC
```

Replace `<PRODUCT>` with exact product string from `paid.md` product strings table.

---

### TW-2: Channel mix overview (all channels, WoW)
Source table: `marketing_insights.gtm_dash`

```sql
SELECT
    date_trunc('week', date)             AS week_start,
    channel,
    SUM(entrances)                       AS entrances,
    SUM(biz_signups)                     AS biz_signups,
    SUM(d1to6ai)                         AS bd1_6,
    SUM(d1to6ai) / NULLIF(SUM(entrances), 0) AS signup_to_bd1_6_rate
FROM marketing_insights.gtm_dash
WHERE
    date >= current_date() - interval 28 day
    AND base_product = '<PRODUCT>'
    AND domain_type = 'Business'
GROUP BY 1, 2
ORDER BY 1 DESC, bd1_6 DESC
```

---

### TW-3: Paid vs. organic split (WoW)
Source table: `marketing_insights.gtm_dash`

```sql
SELECT
    date_trunc('week', date)                              AS week_start,
    CASE
        WHEN channel IN ('Paid Search', 'Paid Social',
                         'Display', 'Video')              THEN 'Paid'
        ELSE 'Organic'
    END                                                   AS channel_type,
    SUM(d1to6ai)                                          AS bd1_6,
    SUM(biz_signups)                                      AS biz_signups,
    SUM(d1to6ai) / NULLIF(SUM(SUM(d1to6ai))
        OVER (PARTITION BY date_trunc('week', date)), 0)  AS share_of_total
FROM marketing_insights.gtm_dash
WHERE
    date >= current_date() - interval 28 day
    AND base_product = '<PRODUCT>'
    AND domain_type = 'Business'
GROUP BY 1, 2
ORDER BY 1 DESC, channel_type
```

---

## MBR Monthly Queries

### MBR-1: BD1-6 actuals by product (monthly)
Source table: `marketing_paid_performance.paid_performance_campaigns`

```sql
SELECT
    date_trunc('month', date)            AS month,
    base_product,
    channel,
    SUM(bd1_6)                           AS bd1_6,
    SUM(spend)                           AS spend,
    SUM(bd1_6) / NULLIF(SUM(spend), 0) * 1000 AS cpbd1_6_per_k
FROM marketing_paid_performance.paid_performance_campaigns
WHERE
    date >= date_trunc('month', current_date() - interval 2 month)
    AND date <  date_trunc('month', current_date())
    AND base_product = '<PRODUCT>'
    AND domain_type = 'Business'
    AND motion = 'Land'
GROUP BY 1, 2, 3
ORDER BY 1 DESC, bd1_6 DESC
```

Adjust the lookback to cover the reporting month and prior month for MoM delta.

---

### MBR-2: Land vs. xflow motion breakdown (monthly)
Source table: `marketing_paid_performance.paid_performance_campaigns`

```sql
SELECT
    date_trunc('month', date)            AS month,
    motion,
    SUM(bd1_6)                           AS bd1_6,
    SUM(spend)                           AS spend,
    SUM(bd1_6) / NULLIF(SUM(spend), 0) * 1000 AS cpbd1_6_per_k
FROM marketing_paid_performance.paid_performance_campaigns
WHERE
    date >= date_trunc('month', current_date() - interval 2 month)
    AND date <  date_trunc('month', current_date())
    AND base_product = '<PRODUCT>'
    AND domain_type = 'Business'
GROUP BY 1, 2
ORDER BY 1 DESC, motion
```

---

### MBR-3: Total BD1to6AI actuals vs. target (all channels, monthly)
Source table: `production.marketing_insights.business_d1to6ai_tracking`

```sql
SELECT
    month,
    base_product,
    SUM(bd1to6ai_actuals)                AS bd1_6_actuals,
    MAX(bd1to6ai_target)                 AS bd1_6_target,
    SUM(bd1to6ai_actuals) / NULLIF(MAX(bd1to6ai_target), 0) AS pct_to_target
FROM production.marketing_insights.business_d1to6ai_tracking
WHERE
    month >= date_trunc('month', current_date() - interval 2 month)
    AND month <  date_trunc('month', current_date())
    AND base_product = '<PRODUCT>'
    AND domain_type = 'Business'
GROUP BY 1, 2
ORDER BY 1 DESC
```

---

### MBR-4: Channel group breakdown (paid vs. organic, monthly)
Source table: `production.marketing_insights.business_d1to6ai_tracking`

```sql
SELECT
    month,
    channel_group,
    SUM(bd1to6ai_actuals)               AS bd1_6,
    SUM(bd1to6ai_actuals) / NULLIF(SUM(SUM(bd1to6ai_actuals))
        OVER (PARTITION BY month), 0)   AS share_of_total
FROM production.marketing_insights.business_d1to6ai_tracking
WHERE
    month >= date_trunc('month', current_date() - interval 2 month)
    AND month <  date_trunc('month', current_date())
    AND base_product = '<PRODUCT>'
    AND domain_type = 'Business'
GROUP BY 1, 2
ORDER BY 1 DESC, bd1_6 DESC
```

---

### MBR-5: YoY comparison (use at quarter-end or for annual context)
Source table: `production.marketing_insights.business_d1to6ai_tracking`

```sql
SELECT
    month,
    base_product,
    SUM(bd1to6ai_actuals)               AS bd1_6_actuals,
    SUM(bd1to6ai_yoy)                   AS bd1_6_yoy,
    SUM(bd1to6ai_actuals) / NULLIF(SUM(bd1to6ai_yoy), 0) - 1 AS yoy_growth
FROM production.marketing_insights.business_d1to6ai_tracking
WHERE
    month IN (
        date_trunc('month', current_date() - interval 1 month),
        date_trunc('month', current_date() - interval 13 month)
    )
    AND base_product = '<PRODUCT>'
    AND domain_type = 'Business'
GROUP BY 1, 2
ORDER BY 1 DESC
```

Only run this for quarter-end MBRs or when YoY context is explicitly requested.

---

## Query Output Format

After running any query, paste results in this normalized format before adding
to the insights block:

```
Query: [query name, e.g. MBR-1]
Run date: [date run]
Period covered: [date range]
Product filter: [product string used]
Lag flag: [yes/no - are last 7 days included?]

[paste query results as table]
```

This makes it easy to trace any number in the insights block back to its source.

---

## Common Errors

| Error | Fix |
|---|---|
| Zero rows returned | Check exact product string against product strings table in paid.md or gtm.md |
| Spend looks too low | Confirm IMC channels load separately; flag as directional |
| BD1-6 looks low for recent dates | Expected: 7-day bake lag. Note in insights block |
| Division error | Confirm `NULLIF` wrapping on denominator |
| `current_date() - 1` syntax error | Use `current_date() - interval 1 day` |
