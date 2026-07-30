"""
CI-friendly mock for Google Ads connector.
Provides `fetch_google_ads_metrics(config, start_date, end_date)` returning a small DataFrame.
"""
from __future__ import annotations
import pandas as pd
import logging

logger = logging.getLogger("mock_google_ads")


def fetch_google_ads_metrics(config, start_date: str, end_date: str) -> pd.DataFrame:
    logger.info("Mock fetch_google_ads_metrics called: %s - %s", start_date, end_date)
    return pd.DataFrame([
        {"campaign_id": "111", "campaign_name": "Brand - US", "date": start_date, "impressions": 1000, "clicks": 50, "cost_micros": 25000000, "impression_share": 0.75, "eligible_impressions": 1200},
        {"campaign_id": "222", "campaign_name": "Brand - EU", "date": start_date, "impressions": 50, "clicks": 2, "cost_micros": 500000, "impression_share": 0.2, "eligible_impressions": 300},
    ])
