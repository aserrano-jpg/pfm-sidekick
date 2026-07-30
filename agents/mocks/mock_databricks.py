"""
CI-friendly mock for Databricks writer.
Provides `write_dataframe_to_databricks(df, cfg, table_name=None)` that writes locally and returns a fake DBFS path.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import logging

logger = logging.getLogger("mock_databricks")


def write_dataframe_to_databricks(df: pd.DataFrame, cfg: dict, table_name: str | None = None) -> str:
    out_dir = Path(cfg.get("local_output_dir", "./tmp/bps_output")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    local_file = out_dir / f"mock_bps_{pd.Timestamp('now').strftime('%Y%m%d%H%M%S')}.parquet"
    df.to_parquet(local_file, index=False)
    logger.info("Mock uploaded dataframe to %s", local_file)
    # return a fake dbfs path
    return str(local_file)
