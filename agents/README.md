BPS Impression Share Agent

Purpose
- Pull Google Ads metrics for Brand Paid Search (BPS), compute impression share and derived metrics, enrich with internal paid pipeline data, and surface a Databricks dashboard.

Quickstart (local run)

1. Create a sample CSV at `agents/sample/google_ads_sample.csv` with Google Ads export columns (campaignId, campaignName, date, impressions, clicks, cost_micros, impression_share).

2. Run:

```bash
python agents/bps_agent.py --mode localrun
```

Next steps to productionize
- Implement `fetch_google_ads_metrics()` using the `google-ads` library and a service account/OAuth flow.
- Implement Databricks write via `databricks-sql-connector` or writing to a mounted DBFS path, and register the output as a Databricks SQL view.
- Add robust mapping and a campaign_id-to-paid_performance mapping table.
- Schedule daily runs on Airflow/Cloud Scheduler and add alerting for major drops in impression share.

Files
- `agents/bps_agent.py` - main agent skeleton and pure-data transform functions
- `agents/config.example.yaml` - example config
- `agents/tests/` - unit tests
