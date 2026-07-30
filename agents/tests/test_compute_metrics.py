import pandas as pd
import numpy as np
from agents.bps_agent import compute_impression_share_metrics


def test_compute_metrics_zero_impr():
    df = pd.DataFrame([
        {"campaign_id": "1", "impressions": 0, "cost": 100.0, "impression_share": 0.5}
    ])
    out = compute_impression_share_metrics(df)
    assert "cpm" in out.columns
    assert pd.isna(out.loc[0, "cpm"])


def test_compute_metrics_missing_impr_share():
    df = pd.DataFrame([
        {"campaign_id": "1", "impressions": 1000, "cost": 50.0}
    ])
    out = compute_impression_share_metrics(df)
    assert "impression_share_pct" in out.columns
    assert pd.isna(out.loc[0, "impression_share_pct"]) or out.loc[0, "impression_share_pct"] == None
