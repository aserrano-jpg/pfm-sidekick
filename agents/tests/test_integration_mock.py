import yaml
import pandas as pd
import agents.bps_agent as bps
from pathlib import Path


def test_fetch_flow_with_mocks(tmp_path, monkeypatch):
    # create a minimal config file
    cfg = {
        "google_ads": {"client_customer_ids": ["1234567890"]},
        "local_output_dir": str(tmp_path / "out")
    }
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))

    # monkeypatch the fetch and databricks writer
    from agents.mocks.mock_google_ads import fetch_google_ads_metrics as mock_fetch
    from agents.mocks.mock_databricks import write_dataframe_to_databricks as mock_writer

    monkeypatch.setattr(bps, "fetch_google_ads_metrics", mock_fetch)
    monkeypatch.setattr(bps, "write_to_databricks", lambda df, cfg, table_name=None: mock_writer(df, cfg if cfg else {"local_output_dir": str(tmp_path / "out")}, table_name))

    # call main in fetch mode
    argv = ["--mode", "fetch", "--config", str(cfg_path), "--start_date", "2026-06-01", "--end_date", "2026-06-01"]
    bps.main(argv)

    # verify output was written
    out_files = list((tmp_path / "out").glob("*.parquet"))
    assert len(out_files) == 1

    # verify contents have impression_share_pct
    df = pd.read_parquet(out_files[0])
    assert "impression_share_pct" in df.columns
    assert df["impression_share_pct"].iloc[0] == 75.0
