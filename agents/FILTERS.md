# Campaign Filter Reference

Last updated: 2026-08-12

All filters used across `refresh_statlas.py`, `refresh_jira_max.py`, and Socrates queries.
Do not overwrite unless conventions change.

---

## Google Ads API Campaign Naming Convention

Campaigns follow a structured pipe-delimited naming convention:

```
P:product|O:objective|V:vendor|G:geo|L:language|F:funnel-stage|S:strategy|M:match|Z:flight|A:asset|D:device
```

### P: Product
| Tag | Product |
|---|---|
| `P:jira` | Jira (all campaigns in Jira search account) |
| `P:confluence` | Confluence |
| `P:teamwork-collection` | Teamwork Collection (TWC) |
| `P:trello` | Trello (exclude from Jira pulls with `NOT LIKE '%trello%'`) |

**API filter for Jira:** `campaign.name LIKE '%P:jira%'`
Do NOT use `LIKE '%jira%'` (too broad, misses campaigns, catches Trello).

---

### G: Geo
21 active geo codes. Parse with `re.search(r'g:([a-z]+)', name)`.

| Tag | Region | Notes |
|---|---|---|
| `G:us` | United States | Highest IS, highest volume |
| `G:uk` | United Kingdom | Note: UK not GB |
| `G:aunz` | Australia + New Zealand | Combined market |
| `G:in` | India | |
| `G:ca` | Canada | French language (`L:fr`) |
| `G:de` | Germany | |
| `G:row` | Rest of World | Catch-all, `L:de` (historical naming quirk) |
| `G:br` | Brazil | `L:pt` |
| `G:fr` | France | `L:fr` |
| `G:jp` | Japan | `L:jp` |
| `G:es` | Spain | `L:es` |
| `G:mx` | Mexico | `L:es` |
| `G:it` | Italy | |
| `G:bene` | Belgium + Netherlands | |
| `G:ch` | Switzerland | |
| `G:seas` | Southeast Asia | |
| `G:se` | Sweden | |
| `G:kr` | Korea | |
| `G:is` | Israel | |
| `G:nafr` | North Africa | `L:fr` |
| `G:pt` | Portugal | `L:pt` |

**BPS IS Dashboard top 6 (by impression volume, auto-selected by API):**
US, UK, AUNZ, IN, ROW, DE

---

### F: Funnel Stage
F: does NOT indicate channel type. All campaigns in the Jira search account are paid search.

| Tag | Meaning | Notes |
|---|---|---|
| `F:consider` | Paid search, consideration stage | Branded + NBPS search |
| `F:disc` | Discovery/Demand Gen | Search network, not display |
| `F:display` | Paid Display | Separate account |
| `F:video` | YouTube/Video | Separate account |

---

### S: Strategy (BPS vs NBPS)
| Tag | Channel | Socrates channel value |
|---|---|---|
| `S:brand-trademark` | BPS (branded paid search) | `paid-search-branded` |
| `S:project-management-plus` | NBPS theme | `paid-search-non-branded` |
| `S:competitor` | NBPS theme | `paid-search-non-branded` |
| `S:methodologies` | NBPS theme | `paid-search-non-branded` |

**BPS IS filter (Ads API):**
```sql
AND campaign.name LIKE '%S:brand-trademark%'
```

---

### Other Parameters
| Parameter | Values | Notes |
|---|---|---|
| `L:` | `en`, `de`, `fr`, `pt`, `es`, `jp` | Language |
| `M:` | `exact`, `broad`, `all` | Match type |
| `Z:` | `evergreen`, `expansion` | Flight type |
| `A:` | `text`, `image`, `video` | Asset type |
| `D:` | `all`, `desktop`, `mobile` | Device |

---

## Socrates Filters

### Table
`marketing_paid_performance.paid_performance_campaigns`

### Key Fields
| Field | Values | Notes |
|---|---|---|
| `advertised_product` | `'Jira'`, `'Teamwork Collection'`, `'Confluence'`, `'Trello'` | Product filter |
| `program` | `'BAU'`, `'Experiment'` | Always filter `BAU` for standard reporting |
| `channel` | See below | Channel filter |
| `campaign_geo` | `'us'`, `'uk'`, etc. | Lowercase geo code |
| `campaign_geo_group` | `'US'`, `'UK'`, `'BR-IN'`, `'ROW'` | Grouped geo (use for geo breakdown) |
| `evaluations_with_business_domain` | integer | Biz Sign-ups |
| `business_domain_d1to6` | float | BD1-6 (7-day reporting lag) |
| `spend` | float | Spend in USD |
| `evaluations` | integer | All sign-ups (incl. personal) |

### Channel Values
| Socrates channel | Description |
|---|---|
| `paid-search-branded` | BPS |
| `paid-search-non-branded` | NBPS |
| `paid-display` | Paid Display |
| `paid-social` | Paid Social |
| `paid-video` | Paid Video |

### Standard Paid Search Filter
```sql
WHERE advertised_product = 'Jira'
  AND program = 'BAU'
  AND channel IN ('paid-search-branded', 'paid-search-non-branded')
```

### TWC BAU Filter
```sql
WHERE advertised_product = 'Teamwork Collection'
  AND program = 'BAU'
  AND channel IN ('paid-search-branded', 'paid-search-non-branded')
```

---

## BD1-6 Reporting Notes

- **7-day lag:** BD1-6 data in Socrates lags by 7 days. Most recent month will be understated until ~7 days after month end.
- **Attribution:** Socrates `business_domain_d1to6` uses base product attribution which can differ from PowerBI by up to 5x (PowerBI base product view credits across all channels; Socrates is per-channel).
- **Cross-channel vs. paid search only:** Socrates all-channel BD1-6 total will be higher than paid-search-only. Always specify `channel IN (...)` to scope correctly.
- **Jira paid search BD1-6 is BPS-heavy:** BPS drives ~90%+ of BD1-6. NBPS contributes volume but lower funnel quality.

---

## Date Range Conventions

| Dashboard | Range | Notes |
|---|---|---|
| BPS IS Dashboard | 13 months rolling | `LAST_13_MONTHS` in Ads API |
| Jira Efficiency Dashboard | 6 full months rolling | Capped at last day of previous month (no partial months) |
| TWC BAU Learnings | Mar 16 - Jun 30, 2026 | Fixed program dates |
