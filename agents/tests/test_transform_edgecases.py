import pandas as pd
from agents.bps_agent import transform_and_enrich


def test_fuzzy_no_match():
    ga = pd.DataFrame([
        {"campaign_id": "999", "campaign_name": "Brand - Unknown", "impressions": 100}
    ])
    paid = pd.DataFrame([
        {"campaign_id": "111", "campaign_name": "Brand - US (Paid)", "business_domain_d1to6": 5.0}
    ])

    # Use high fuzzy cutoff to prevent matches
    merged = transform_and_enrich(ga, paid, mapping_df=pd.DataFrame(), fuzzy_cutoff=0.99)

    # No paid fields should be populated for the unknown campaign
    assert "business_domain_d1to6" in merged.columns
    assert pd.isna(merged.loc[0, "business_domain_d1to6"]) or merged.loc[0, "business_domain_d1to6"] == None
