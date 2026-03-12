
import os
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy import create_engine, text


def _read_sql_source(connection_url: str, sql: str) -> pd.DataFrame:
    engine = create_engine(connection_url, future=True)
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def load_dataset_frame(source_type: str, connection_metadata: dict, dataset: dict) -> pd.DataFrame:
    if source_type == "csv":
        path = dataset.get("actual_path") or connection_metadata.get("path")
        if not path:
            raise ValueError("CSV dataset requires actual_path or source path")
        return pd.read_csv(path)

    if source_type in {"sqlite", "postgres", "mysql", "mssql"}:
        connection_url = connection_metadata.get("connection_url")
        if not connection_url:
            raise ValueError("SQL source requires connection_url")
        if dataset.get("actual_query"):
            sql = dataset["actual_query"]
        elif dataset.get("actual_table"):
            sql = f"SELECT * FROM {dataset['actual_table']}"
        else:
            raise ValueError("SQL dataset requires actual_table or actual_query")
        return _read_sql_source(connection_url, sql)

    raise ValueError(f"Unsupported source_type: {source_type}")


def dataset_freshness_value(source_type: str, connection_metadata: dict, dataset: dict, frame: pd.DataFrame | None = None):
    if dataset.get("freshness_column"):
        if frame is None:
            frame = load_dataset_frame(source_type, connection_metadata, dataset)
        if dataset["freshness_column"] not in frame.columns:
            raise ValueError("Freshness column not found in dataset")
        series = pd.to_datetime(frame[dataset["freshness_column"]], errors="coerce").dropna()
        if series.empty:
            return None
        value = series.max()
        if hasattr(value, "to_pydatetime"):
            value = value.to_pydatetime()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    if source_type == "csv":
        path = dataset.get("actual_path") or connection_metadata.get("path")
        if not path or not os.path.exists(path):
            return None
        return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)

    return None
