"""Exploratory statistical analysis for cleaned temperature data."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_eda(cleaned: pd.DataFrame) -> dict:
    if cleaned.empty:
        return {
            "observations": 0,
            "mean": np.nan,
            "median": np.nan,
            "mode": np.nan,
            "minimum": np.nan,
            "maximum": np.nan,
            "standard_deviation": np.nan,
            "variance": np.nan,
            "range": np.nan,
            "q1": np.nan,
            "q3": np.nan,
            "iqr": np.nan,
            "temperature_change": np.nan,
            "cooling_rate_c_per_min": np.nan,
        }

    temperatures = cleaned["Milk_Temperature"].astype(float)
    mode_values = temperatures.mode()
    mode_value = float(mode_values.iloc[0]) if not mode_values.empty else np.nan

    temperature_change = float(temperatures.iloc[-1] - temperatures.iloc[0])
    elapsed_minutes = 0.0
    if len(cleaned) > 1:
        elapsed_minutes = (
            cleaned["Timestamp"].iloc[-1] - cleaned["Timestamp"].iloc[0]
        ).total_seconds() / 60.0
    cooling_rate = (
        temperature_change / elapsed_minutes if elapsed_minutes > 0 else np.nan
    )

    q1 = float(temperatures.quantile(0.25))
    q3 = float(temperatures.quantile(0.75))
    return {
        "observations": int(len(cleaned)),
        "mean": float(temperatures.mean()),
        "median": float(temperatures.median()),
        "mode": mode_value,
        "minimum": float(temperatures.min()),
        "maximum": float(temperatures.max()),
        "standard_deviation": float(temperatures.std(ddof=1)) if len(temperatures) > 1 else 0.0,
        "variance": float(temperatures.var(ddof=1)) if len(temperatures) > 1 else 0.0,
        "range": float(temperatures.max() - temperatures.min()),
        "q1": q1,
        "q3": q3,
        "iqr": float(q3 - q1),
        "temperature_change": temperature_change,
        "cooling_rate_c_per_min": float(cooling_rate),
    }
