import pandas as pd
from pathlib import Path
from agents.bps_agent import write_to_databricks


def test_writer_local_fallback(tmp_path):
    df = pd.DataFrame([{"a": 1, "b": 2}])
    cfg = {"local_output_dir": str(tmp_path / "out")}
    write_to_databricks(df, cfg)
    files = list((tmp_path / "out").glob("*.parquet"))
    assert len(files) == 1
    # Read back
    df2 = pd.read_parquet(files[0])
    assert df2.iloc[0]["a"] == 1
