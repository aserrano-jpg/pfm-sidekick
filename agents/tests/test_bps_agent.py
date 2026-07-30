import pandas as pd
import pytest
from agents.bps_agent import transform_and_enrich, compute_impression_share_metrics


def make_sample_ga():
    return pd.DataFrame([
        {"campaign_id": "111", "campaign_name": "Brand - US", "date": "2026-06-01", "impressions": 1000, "clicks": 50, "cost_micros": 25000000, "impression_share": 0.75, "eligible_impressions": 1200},
        {"campaign_id": "222", "campaign_name": "Brand - EU", "date": "2026-06-01", "impressions": 50, "clicks": 2, "cost_micros": 500000, "impression_share": 0.2, "eligible_impressions": 300},
    ])


def test_transform_and_compute():
    ga = make_sample_ga()
    paid = pd.DataFrame([{"campaign_id": "111", "campaign_name": "Brand - US (Paid)", "program": "BAU", "advertised_product": "Jira Product Discovery", "business_domain_d1to6": 12.0}])
    mapping = pd.DataFrame([{"google_campaign_id": "111", "google_campaign_name": "Brand - US", "paid_campaign_id": "111", "paid_campaign_name": "Brand - US (Paid)"}])
    merged = transform_and_enrich(ga, paid, mapping_df=mapping, fuzzy_cutoff=0.7)
    assert "business_domain_d1to6" in merged.columns

    computed = compute_impression_share_metrics(merged)
    assert "impression_share_pct" in computed.columns
    assert computed.loc[computed["campaign_id"] == "111", "impression_share_pct"].iloc[0] == 75.0
    # CPM check (cost 25 USD over 1000 impressions -> 25/1000*1000 = 25)
    cpm = computed.loc[computed["campaign_id"] == "111", "cpm"].iloc[0]
    assert pytest.approx(cpm, rel=1e-3) == 25.0
