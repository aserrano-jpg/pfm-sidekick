"""
BPS Impression Share Reporting Agent - skeleton

Usage:
  python agents/bps_agent.py --config agents/config.example.yaml --mode localrun

This module provides:
- placeholders for Google Ads ingestion
- transform/enrichment functions to join with internal paid tables
- compute impression share and derived metrics
- writer to Databricks (skeleton: writes CSV/Parquet locally)

Runbook and auth steps are documented in agents/README.md
"""

from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Any

import pandas as pd

logger = logging.getLogger("bps_agent")


from agents.google_ads_connector import fetch_google_ads_metrics


def transform_and_enrich(ga_df: pd.DataFrame, paid_perf_df: pd.DataFrame, mapping_df: pd.DataFrame | None = None, fuzzy_cutoff: float = 0.8) -> pd.DataFrame:
    """
    Normalize Google Ads fields and perform an enrichment join with internal paid performance table.

    Joins on campaign name or campaign_id depending on data availability. This is intentionally
    permissive: callers should validate join quality and provide mapping tables in production.
    """
    df = ga_df.copy()

    # normalize column names
    mapping = {
        "campaignId": "campaign_id",
        "campaign_id": "campaign_id",
        "campaign": "campaign_name",
        "campaignName": "campaign_name",
        "impr": "impressions",
        "impressions": "impressions",
        "clicks": "clicks",
        "cost_micros": "cost_micros",
        "cost": "cost",
        "impression_share": "impression_share",
        "absolute_top_impression_share": "absolute_top_impression_share",
        "eligible_impressions": "eligible_impressions",
    }
    df.rename(columns={k: v for k, v in mapping.items() if k in df.columns}, inplace=True)

    # ensure numeric types
    for col in ["impressions", "clicks", "impression_share", "absolute_top_impression_share", "eligible_impressions", "cost_micros"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # convert cost_micros -> cost (USD) if present
    if "cost_micros" in df.columns and "cost" not in df.columns:
        df["cost"] = df["cost_micros"] / 1_000_000

    # If a mapping table is provided, use it to map Google campaign -> paid pipeline keys
    # Expected mapping columns (example): google_campaign_id, google_campaign_name, paid_campaign_id, paid_campaign_name
    if mapping_df is not None and not mapping_df.empty:
        # normalize mapping column names
        m = mapping_df.copy()
        m_cols = {c: c.strip() for c in m.columns}
        m.rename(columns=m_cols, inplace=True)

        # attempt join by campaign_id
        if "campaign_id" in df.columns and "google_campaign_id" in m.columns:
            df = df.merge(m, left_on="campaign_id", right_on="google_campaign_id", how="left")
        elif "campaign_name" in df.columns and "google_campaign_name" in m.columns:
            df = df.merge(m, left_on="campaign_name", right_on="google_campaign_name", how="left")
        else:
            # no direct mapping columns found; skip mapping join
            logger.info("Mapping table provided but no matching join columns found; skipping mapping join")

    # join with paid_perf_df on campaign_id or campaign_name with fuzzy fallback
    merged = df.copy()
    if paid_perf_df is not None and not paid_perf_df.empty:
        # prefer paid_campaign_id if mapping produced it
        if "paid_campaign_id" in merged.columns and "campaign_id" in paid_perf_df.columns:
            merged = merged.merge(paid_perf_df, left_on="paid_campaign_id", right_on="campaign_id", how="left", suffixes=("", "_paid"))
        else:
            # try direct campaign_id
            if "campaign_id" in merged.columns and "campaign_id" in paid_perf_df.columns:
                merged = merged.merge(paid_perf_df, on="campaign_id", how="left", suffixes=("", "_paid"))
            else:
                # exact name join first
                if "campaign_name" in merged.columns and "campaign_name" in paid_perf_df.columns:
                    merged = merged.merge(paid_perf_df, on="campaign_name", how="left", suffixes=("", "_paid"))

                # fuzzy match fallback for unmatched rows
                unmatched = merged[merged[[c for c in paid_perf_df.columns if c in merged.columns or c=="campaign_name"]].isna().any(axis=1)] if not merged.empty else pd.DataFrame()
                if not unmatched.empty and "campaign_name" in merged.columns and "campaign_name" in paid_perf_df.columns:
                    from difflib import get_close_matches

                    paid_names = paid_perf_df["campaign_name"].dropna().unique().tolist()
                    fuzzy_matches = {}
                    for idx, row in unmatched.iterrows():
                        name = row.get("campaign_name")
                        if not name or not isinstance(name, str):
                            continue
                        matches = get_close_matches(name, paid_names, n=1, cutoff=fuzzy_cutoff)
                        if matches:
                            fuzzy_matches[idx] = matches[0]

                    if fuzzy_matches:
                        fm_df = pd.DataFrame([{"_idx": k, "fuzzy_match_name": v} for k, v in fuzzy_matches.items()])
                        # map fuzzy names back to paid_perf_df rows and merge
                        fm_df = fm_df.merge(paid_perf_df, left_on="fuzzy_match_name", right_on="campaign_name", how="left")
                        # apply fuzzy merge results to merged dataframe
                        for _, fm in fm_df.iterrows():
                            i = fm["_idx"]
                            for c in paid_perf_df.columns:
                                merged.at[i, c] = fm.get(c)

    # log join quality
    try:
        total = len(df)
        matched = merged[~merged[[c for c in paid_perf_df.columns if c in merged.columns]].isna().all(axis=1)] if not paid_perf_df.empty else merged
        matched_count = len(matched)
        logger.info("Join summary: total=%d, matched=%d, unmatched=%d", total, matched_count, total - matched_count)
    except Exception:
        logger.debug("Could not compute join quality metrics")

    return merged


def compute_impression_share_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute derived impression share metrics and basic quality checks.

    Adds columns:
      - impression_share_pct (0-100)
      - lost_impr_to_rank_pct (if available via "loss_to_rank" or derived)
      - lost_impr_to_budget_pct (if available via "loss_to_budget")
      - cost_per_1e3_impr (CPM)

    The function is pure-data and can be unit tested.
    """
    out = df.copy()

    # impression_share may be in 0-1 or 0-100, normalize to 0-100
    if "impression_share" in out.columns:
        out["impression_share"] = pd.to_numeric(out["impression_share"], errors="coerce")
        # detect scale: if max <= 1 then it's fractional
        if out["impression_share"].max(skipna=True) <= 1:
            out["impression_share_pct"] = out["impression_share"] * 100
        else:
            out["impression_share_pct"] = out["impression_share"]
    else:
        out["impression_share_pct"] = pd.NA

    # basic CPM
    if "cost" in out.columns and "impressions" in out.columns:
        out["cpm"] = (out["cost"] / out["impressions"]).replace([pd.NA, float("inf")], pd.NA) * 1000
    else:
        out["cpm"] = pd.NA

    # placeholder for lost impression calculations if eligible_impressions present
    if "eligible_impressions" in out.columns and "impressions" in out.columns:
        out["eligible_impressions"] = pd.to_numeric(out["eligible_impressions"], errors="coerce")
        out["lost_impr"] = out["eligible_impressions"] - out["impressions"]
        out["lost_impr_pct"] = out["lost_impr"] / out["eligible_impressions"] * 100
    else:
        out["lost_impr"] = pd.NA
        out["lost_impr_pct"] = pd.NA

    return out


def write_to_databricks(df: pd.DataFrame, config: Dict[str, Any], table_name: str | None = None, local_path: Path | None = None) -> None:
    """
    Write DataFrame to Databricks. If Databricks config is provided, upload to DBFS and register table optionally.
    Falls back to writing locally when Databricks config is missing.
    """
    databricks_cfg = config.get("databricks") or {}
    if databricks_cfg.get("host") and databricks_cfg.get("access_token"):
        # use databricks writer
        try:
            from agents.databricks_writer import write_dataframe_to_databricks
        except Exception:
            logger.exception("databricks_writer module not available; falling back to local write")
            databricks_cfg = {}

        if databricks_cfg.get("host") and databricks_cfg.get("access_token"):
            dbfs_path = write_dataframe_to_databricks(df, {**config, "databricks": databricks_cfg}, table_name)
            logger.info("Uploaded data to dbfs:%s", dbfs_path)
            return

    # fallback: write locally
    out_dir = Path(config.get("local_output_dir", "./tmp/bps_output")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if local_path is None:
        local_path = out_dir / f"bps_impr_share_{pd.Timestamp('now').strftime('%Y%m%d%H%M%S')}.parquet"
    df.to_parquet(local_path, index=False)
    logger.info("Wrote output to %s", local_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="BPS Impression Share Agent")
    parser.add_argument("--config", required=False, help="Path to config YAML (optional)")
    parser.add_argument("--start_date", required=False, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end_date", required=False, help="End date (YYYY-MM-DD)")
    parser.add_argument("--mode", required=False, choices=["localrun", "fetch"], default="localrun")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # minimal local run: read sample CSV if present
    config = {"local_output_dir": "./tmp/bps_output"}

    if args.mode == "localrun":
        sample_csv = Path("./agents/sample/google_ads_sample.csv")
        if sample_csv.exists():
            ga = pd.read_csv(sample_csv)
            logger.info("Loaded sample Google Ads CSV with %d rows", len(ga))
        else:
            logger.error("No sample CSV found at %s. Exiting.", sample_csv)
            sys.exit(2)

        # no paid perf table in localrun; pass empty DF
        enriched = transform_and_enrich(ga, pd.DataFrame())
        computed = compute_impression_share_metrics(enriched)
        write_to_databricks(computed, config)
        logger.info("Local run complete. Output written to %s", config["local_output_dir"])
    else:
        # fetch mode: requires a config file path or environment-configured google-ads credentials
        if args.config:
            cfg_path = Path(args.config)
            if not cfg_path.exists():
                logger.error("Config file %s not found.", cfg_path)
                sys.exit(2)
            import yaml
            with cfg_path.open() as fh:
                cfg = yaml.safe_load(fh)
        else:
            logger.error("--config is required for fetch mode to provide Google Ads credentials.")
            sys.exit(2)

        if not args.start_date or not args.end_date:
            logger.error("--start_date and --end_date are required for fetch mode.")
            sys.exit(2)

        try:
            ga_df = fetch_google_ads_metrics(cfg, args.start_date, args.end_date)
        except Exception as e:
            logger.exception("Error fetching Google Ads metrics: %s", e)
            sys.exit(2)

        enriched = transform_and_enrich(ga_df, pd.DataFrame())
        computed = compute_impression_share_metrics(enriched)
        write_to_databricks(computed, cfg)
        logger.info("Fetch run complete. Output written to %s", cfg.get("local_output_dir", "./tmp/bps_output"))


if __name__ == "__main__":
    main()
