"""Load, inspect, and clean the temperature dataset without modifying the original."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from utils.config import (
    DATASET_PATH,
    MAX_VALID_TEMPERATURE_C,
    MIN_VALID_TEMPERATURE_C,
)


def load_dataset(dataset_path: Path = DATASET_PATH) -> pd.DataFrame:
    path = Path(dataset_path)
    if not path.exists():
        return pd.DataFrame(columns=["Timestamp", "Milk_Temperature"])
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["Timestamp", "Milk_Temperature"])


def clean_dataset(original: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    data = original.copy()
    data.columns = [str(column).strip() for column in data.columns]
    renamed = {
        "timestamp": "Timestamp",
        "milk_temperature": "Milk_Temperature",
    }
    data = data.rename(columns={key: value for key, value in renamed.items() if key in data.columns})
    if "Timestamp" not in data.columns:
        data["Timestamp"] = pd.NaT
    if "Milk_Temperature" not in data.columns:
        data["Milk_Temperature"] = pd.NA

    missing_before = int(data.isna().sum().sum()) if not data.empty else 0
    duplicate_before = int(data.duplicated().sum()) if not data.empty else 0

    # Detect one timezone from the CSV, then normalize every valid timestamp to it.
    target_timezone = None
    for raw_timestamp in data["Timestamp"].dropna():
        try:
            parsed_sample = pd.Timestamp(raw_timestamp)
            if parsed_sample.tzinfo is not None:
                target_timezone = parsed_sample.tzinfo
                break
        except (TypeError, ValueError):
            continue

    try:
        if target_timezone is not None:
            parsed_timestamps = pd.to_datetime(
                data["Timestamp"],
                errors="coerce",
                format="mixed",
                utc=True,
            )
            data["Timestamp"] = parsed_timestamps.dt.tz_convert(target_timezone)
        else:
            data["Timestamp"] = pd.to_datetime(
                data["Timestamp"],
                errors="coerce",
                format="mixed",
            )
    except (TypeError, ValueError):
        data["Timestamp"] = pd.to_datetime(
            data["Timestamp"], errors="coerce"
        )
    data["Milk_Temperature"] = pd.to_numeric(data["Milk_Temperature"], errors="coerce")

    invalid_mask = (
        data["Timestamp"].isna()
        | data["Milk_Temperature"].isna()
        | ~data["Milk_Temperature"].between(
            MIN_VALID_TEMPERATURE_C, MAX_VALID_TEMPERATURE_C
        )
    )
    invalid_count = int(invalid_mask.sum())
    data = data.loc[~invalid_mask].copy()

    duplicate_count = int(data.duplicated().sum())
    data = data.drop_duplicates().copy()
    data = data.sort_values("Timestamp").reset_index(drop=True)

    summary = {
        "missing_values_before": missing_before,
        "duplicate_records_before": duplicate_before,
        "invalid_records_removed": invalid_count,
        "duplicate_records_removed": duplicate_count,
        "rows_retained": len(data),
    }
    return data, summary

