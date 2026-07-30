"""
Databricks writer utilities.

Features:
- Write a pandas DataFrame to a local parquet file
- Upload the parquet file to DBFS via the Databricks REST API (chunked upload)
- Optionally register the uploaded file as a table using databricks-sql-connector

Config expectations (config.databricks):
- host: https://<workspace>.cloud.databricks.com
- access_token: <PAT with appropriate permissions>
- http_path: optional, for databricks-sql-connector to execute SQL commands

This module intentionally keeps dependencies minimal and provides clear
logging for each step.
"""
from __future__ import annotations
import base64
import json
import logging
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import requests

logger = logging.getLogger("databricks_writer")


def _upload_file_to_dbfs(local_path: Path, dbfs_path: str, host: str, token: str, chunk_size: int = 1_000_000) -> None:
    """
    Upload `local_path` to `dbfs_path` using Databricks DBFS REST API with chunked upload.

    Steps:
    1. POST /api/2.0/dbfs/create to get handle
    2. POST /api/2.0/dbfs/add for chunks
    3. POST /api/2.0/dbfs/close to finalize
    """
    api = host.rstrip("/") + "/api/2.0/dbfs"
    headers = {"Authorization": f"Bearer {token}"}

    # create
    create_payload = {"path": dbfs_path, "overwrite": True}
    r = requests.post(api + "/create", headers=headers, json=create_payload)
    if r.status_code != 200:
        raise RuntimeError(f"DBFS create failed: {r.status_code} {r.text}")
    handle = r.json().get("handle")
    logger.info("Created DBFS handle %s for %s", handle, dbfs_path)

    # add chunks
    with local_path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            b64 = base64.b64encode(chunk).decode("ascii")
            add_payload = {"handle": handle, "data": b64}
            r = requests.post(api + "/add", headers=headers, json=add_payload)
            if r.status_code != 200:
                raise RuntimeError(f"DBFS add failed: {r.status_code} {r.text}")
    # close
    r = requests.post(api + "/close", headers=headers, json={"handle": handle})
    if r.status_code != 200:
        raise RuntimeError(f"DBFS close failed: {r.status_code} {r.text}")
    logger.info("Uploaded %s to DBFS path %s", local_path, dbfs_path)


def register_view_from_dbfs(dbfs_path: str, view_name: str, databricks_cfg: Dict[str, Any]) -> None:
    """
    Optionally register a Databricks SQL view on the Parquet file at `dbfs_path`.

    Requires databricks-sql-connector and that `databricks_cfg` contains `host`, `http_path`, and `access_token`.
    """
    try:
        from databricks import sql
    except Exception as e:
        raise RuntimeError("databricks-sql-connector is required to register views. Install databricks-sql-connector.") from e

    if not all(k in databricks_cfg for k in ("host", "http_path", "access_token")):
        raise ValueError("databricks_cfg must contain host, http_path, and access_token to register view")

    # build connection
    with sql.connect(server_hostname=databricks_cfg["host"].replace("https://", "").rstrip("/"), http_path=databricks_cfg["http_path"], access_token=databricks_cfg["access_token"]) as conn:
        with conn.cursor() as cur:
            sql_stmt = f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM parquet.`dbfs:{dbfs_path}`"
            logger.info("Running view registration SQL: %s", sql_stmt)
            cur.execute(sql_stmt)
            logger.info("View %s registered (or replaced)", view_name)


def write_dataframe_to_databricks(df: pd.DataFrame, cfg: Dict[str, Any], table_name: str | None = None) -> str:
    """
    Write DataFrame to a local Parquet, upload to DBFS, and optionally register as a table.

    Returns the DBFS path of the uploaded file.
    """
    tmp_dir = Path(cfg.get("local_output_dir", "./tmp/bps_output")).resolve()
    tmp_dir.mkdir(parents=True, exist_ok=True)
    local_file = tmp_dir / f"bps_impr_share_{pd.Timestamp('now').strftime('%Y%m%d%H%M%S')}.parquet"

    df.to_parquet(local_file, index=False)
    logger.info("Wrote temporary parquet to %s", local_file)

    databricks_cfg = cfg.get("databricks") or {}
    host = databricks_cfg.get("host")
    token = databricks_cfg.get("access_token")
    if not host or not token:
        raise ValueError("databricks.host and databricks.access_token are required in config to upload to DBFS")

    # Default DBFS path
    dbfs_dir = databricks_cfg.get("dbfs_dir", "/tmp/bps_agent")
    dbfs_path = f"{dbfs_dir.rstrip('/')}/{local_file.name}"

    _upload_file_to_dbfs(local_file, dbfs_path, host, token)

    # optionally register as view
    view_name = databricks_cfg.get("view_name")
    if view_name and databricks_cfg.get("http_path") and databricks_cfg.get("access_token"):
        register_view_from_dbfs(dbfs_path, view_name, databricks_cfg)

    return dbfs_path
