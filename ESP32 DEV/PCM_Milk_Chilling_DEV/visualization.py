"""Matplotlib and Seaborn visualization helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")


def scatter_temperature(data: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(10, 4))[1]
    if data.empty:
        ax.text(0.5, 0.5, "No valid readings available", ha="center", va="center")
        ax.set_axis_off()
        return ax
    sns.scatterplot(data=data, x="Timestamp", y="Milk_Temperature", ax=ax, color="#2563eb")
    ax.set(title="Milk Temperature Scatter Plot", xlabel="Timestamp", ylabel="Temperature (C)")
    ax.tick_params(axis="x", rotation=35)
    return ax


def box_plot(data: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(6, 4))[1]
    if data.empty:
        ax.text(0.5, 0.5, "No valid readings available", ha="center", va="center")
        ax.set_axis_off()
        return ax
    sns.boxplot(data=data, y="Milk_Temperature", ax=ax, color="#38bdf8")
    ax.set(title="Milk Temperature Distribution", ylabel="Temperature (C)")
    return ax


def line_chart(data: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(10, 4))[1]
    if data.empty:
        ax.text(0.5, 0.5, "No valid readings available", ha="center", va="center")
        ax.set_axis_off()
        return ax
    sns.lineplot(data=data, x="Timestamp", y="Milk_Temperature", ax=ax, color="#0ea5e9", lw=2)
    ax.set(title="Milk Temperature vs Time", xlabel="Timestamp", ylabel="Temperature (C)")
    ax.tick_params(axis="x", rotation=35)
    return ax


def histogram(data: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(7, 4))[1]
    if data.empty:
        ax.text(0.5, 0.5, "No valid readings available", ha="center", va="center")
        ax.set_axis_off()
        return ax
    sns.histplot(data=data, x="Milk_Temperature", bins="auto", kde=True, ax=ax, color="#14b8a6")
    ax.set(title="Temperature Frequency Distribution", xlabel="Temperature (C)", ylabel="Frequency")
    return ax


def heatmap(data: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(7, 5))[1]
    if data.empty or len(data) < 4:
        ax.text(0.5, 0.5, "At least 4 readings are required", ha="center", va="center")
        ax.set_axis_off()
        return ax
    pattern = data.copy()
    pattern["Time Group"] = pattern["Timestamp"].dt.strftime("%H:%M")
    values = pattern.groupby("Time Group", as_index=False)["Milk_Temperature"].mean()
    matrix = pd.DataFrame({"Temperature": values["Milk_Temperature"].values}, index=values["Time Group"])
    sns.heatmap(matrix.T, annot=True, cmap="coolwarm", fmt=".1f", ax=ax)
    ax.set(title="Temperature Pattern by Time", xlabel="Time", ylabel="")
    return ax


def statistics_bar_chart(data: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(8, 4))[1]
    if data.empty:
        ax.text(0.5, 0.5, "No valid readings available", ha="center", va="center")
        ax.set_axis_off()
        return ax
    temperatures = data["Milk_Temperature"]
    values = {
        "Mean": temperatures.mean(),
        "Median": temperatures.median(),
        "Minimum": temperatures.min(),
        "Maximum": temperatures.max(),
    }
    ax.bar(values.keys(), values.values(), color=["#2563eb", "#14b8a6", "#22c55e", "#f97316"])
    ax.set(title="Temperature Statistics", ylabel="Temperature (C)")
    return ax


def rolling_average(data: pd.DataFrame, window: int = 10, ax: Optional[plt.Axes] = None) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(10, 4))[1]
    if data.empty:
        ax.text(0.5, 0.5, "No valid readings available", ha="center", va="center")
        ax.set_axis_off()
        return ax
    plot_data = data.copy()
    plot_data["rolling_average"] = plot_data["Milk_Temperature"].rolling(
        window=max(1, window), min_periods=1
    ).mean()
    ax.plot(plot_data["Timestamp"], plot_data["Milk_Temperature"], alpha=0.45, label="Actual")
    ax.plot(plot_data["Timestamp"], plot_data["rolling_average"], linewidth=2.5, label=f"Rolling average ({window})")
    ax.set(title="Actual Temperature and Rolling Average", xlabel="Timestamp", ylabel="Temperature (C)")
    ax.tick_params(axis="x", rotation=35)
    ax.legend()
    return ax


def case_comparison(data: pd.DataFrame, ax: Optional[plt.Axes] = None) -> plt.Axes:
    ax = ax or plt.subplots(figsize=(9, 4))[1]
    if data.empty or "experiment_case" not in data.columns:
        ax.text(0.5, 0.5, "No experimental case data available", ha="center", va="center")
        ax.set_axis_off()
        return ax
    summary = (
        data.groupby("experiment_case", as_index=False)["milk_temperature"]
        .mean()
        .sort_values("experiment_case")
    )
    if summary.empty:
        ax.text(0.5, 0.5, "No experimental case data available", ha="center", va="center")
        ax.set_axis_off()
        return ax
    ax.bar(summary["experiment_case"], summary["milk_temperature"], color="#6366f1")
    ax.set(title="Mean Temperature by Actual Experimental Case", xlabel="Case", ylabel="Mean Temperature (C)")
    ax.tick_params(axis="x", rotation=25)
    return ax


def save_figure(fig: plt.Figure, output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
