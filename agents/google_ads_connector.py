"""
Google Ads connector utilities.

Requires `google-ads` python package. The connector supports two auth flows:
- Provide a path to a google-ads YAML config file via `google_ads_config_path` in config.
- Provide keys in the `google_ads` section of the config and use `GoogleAdsClient.from_dict`.

Functions:
- fetch_google_ads_metrics(config, start_date, end_date) -> pandas.DataFrame

Notes:
- Service account flows may require additional setup (not covered here). Prefer OAuth credentials
  or a stored google-ads YAML file for interactive/service usage.
"""
from __future__ import annotations
from typing import Dict, Any, List
import logging

import pandas as pd

logger = logging.getLogger("google_ads_connector")


def _build_client(config: Dict[str, Any]):
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except Exception as e:
        raise RuntimeError("google-ads library is required. Install with 'pip install google-ads'.") from e

    ga_config = config.get("google_ads", {}) or {}

    # If a config path is provided, load from storage
    if ga_config.get("google_ads_config_path"):
        path = ga_config.get("google_ads_config_path")
        logger.info("Loading Google Ads configuration from %s", path)
        client = GoogleAdsClient.load_from_storage(path)
        return client

    # Otherwise try to build a dict
    # Expected keys: developer_token, client_id, client_secret, refresh_token, login_customer_id
    client_cfg = {
        "developer_token": ga_config.get("developer_token"),
        "use_proto_plus": True,
    }
    if ga_config.get("login_customer_id"):
        client_cfg["login_customer_id"] = ga_config.get("login_customer_id")

    # OAuth keys
    if ga_config.get("client_id"):
        client_cfg["client_id"] = ga_config.get("client_id")
    if ga_config.get("client_secret"):
        client_cfg["client_secret"] = ga_config.get("client_secret")
    if ga_config.get("refresh_token"):
        client_cfg["refresh_token"] = ga_config.get("refresh_token")

    # If minimal keys missing, raise informative error
    if not client_cfg.get("developer_token"):
        raise ValueError("No developer_token found in config.google_ads. Provide google_ads_config_path or keys.")

    load_dict = {
        "developer_token": client_cfg["developer_token"],
        "use_proto_plus": True,
    }
    for key in ("client_id", "client_secret", "refresh_token", "login_customer_id"):
        if client_cfg.get(key):
            load_dict[key] = client_cfg[key]

    client = GoogleAdsClient.load_from_dict(load_dict)
    return client


def fetch_google_ads_metrics(config: Dict[str, Any], start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch campaign-level metrics from Google Ads for the specified date range.

    Returns a pandas DataFrame with columns:
      - campaign_id
      - campaign_name
      - date
      - impressions
      - clicks
      - cost_micros
      - impression_share
      - absolute_top_impression_share
      - eligible_impressions (may be null)

    Notes:
    - Aggregates by campaign and date.
    - Requires appropriate OAuth/credentials to access customer accounts.
    - `config.google_ads.client_customer_ids` may contain one or more account IDs to pull.
    """
    client = _build_client(config)

    ga_cfg = config.get("google_ads", {}) or {}
    client_customer_ids: List[str] = ga_cfg.get("client_customer_ids") or []
    if not client_customer_ids:
        raise ValueError("No client_customer_ids provided in config.google_ads.client_customer_ids")

    reports = []

    # GAQL query
    query = f"""
        SELECT
          campaign.id,
          campaign.name,
          segments.date,
          metrics.impressions,
          metrics.clicks,
          metrics.cost_micros,
          metrics.conversions
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY segments.date
    """

    try:
        ga_service = client.get_service("GoogleAdsService")
    except Exception as e:
        raise RuntimeError("Failed to initialize GoogleAdsService client") from e

    for cid in client_customer_ids:
        # Remove dashes if present
        normalized_cid = cid.replace("-", "")
        logger.info("Querying Google Ads for customer %s (%s to %s)", cid, start_date, end_date)

        try:
            response = ga_service.search_stream(customer_id=normalized_cid, query=query)
        except Exception as e:
            logger.exception("Google Ads query failed for customer %s: %s", cid, e)
            continue

        rows = []
        for batch in response:
            for row in batch.results:
                camp = row.campaign
                seg = row.segments
                metrics = row.metrics
                rows.append({
                    "campaign_id": str(camp.id),
                    "campaign_name": getattr(camp, "name", None),
                    "date": str(seg.date) if hasattr(seg, "date") else None,
                    "impressions": getattr(metrics, "impressions", None),
                    "clicks": getattr(metrics, "clicks", None),
                    "cost_micros": getattr(metrics, "cost_micros", None),
                    "conversions": getattr(metrics, "conversions", None),
                })

        if rows:
            df = pd.DataFrame(rows)
            reports.append(df)

    if reports:
        out = pd.concat(reports, ignore_index=True)
    else:
        out = pd.DataFrame(columns=["campaign_id", "campaign_name", "date", "impressions", "clicks", "cost_micros", "impression_share", "absolute_top_impression_share", "eligible_impressions"]) 

    return out
