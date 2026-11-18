"""Streamlit dashboard for real-time ESP32 milk temperature monitoring."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from analysis import calculate_eda
from preprocessing import clean_dataset, load_dataset
from utils.config import (
    DATASET_PATH,
    DEFAULT_ESP32_IP,
    DEFAULT_INTERVAL_SECONDS,
)


PROJECT_ROOT = Path(__file__).resolve().parent
CSS = """
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
[data-testid="stMetric"] { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { height: 44px; }
</style>
"""


def format_metric(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:.{digits}f}"


def align_filter_timestamp(value, reference_series: pd.Series) -> pd.Timestamp:
    """Convert a Streamlit timestamp to the same timezone mode as the dataset."""
    timestamp = pd.Timestamp(value)

    if len(reference_series) == 0:
        return timestamp

    sample = reference_series.dropna().iloc[0]
    reference_timestamp = pd.Timestamp(sample)
    reference_timezone = getattr(reference_timestamp, "tzinfo", None)

    if reference_timezone is not None:
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(reference_timezone)
        else:
            timestamp = timestamp.tz_convert(reference_timezone)
    elif timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)

    return timestamp


def esp32_status(ip: str) -> tuple[bool, str]:
    try:
        response = requests.get(f"http://{ip}/data", timeout=3)
        response.raise_for_status()
        payload = response.json()
        if "milk_temperature" not in payload:
            return False, "Connected, but milk_temperature field is missing"
        return True, "Connected"
    except requests.Timeout:
        return False, "Connection timed out"
    except requests.ConnectionError:
        return False, "Cannot reach ESP32"
    except requests.JSONDecodeError:
        return False, "ESP32 returned invalid JSON"
    except requests.RequestException as exc:
        return False, f"Request failed: {exc}"


def start_collector(ip: str, interval: float, case: str) -> None:
    process = st.session_state.collector_process
    if process is not None and process.poll() is None:
        st.warning("Data collection is already running.")
        return

    log_path = PROJECT_ROOT / "collector.log"
    log_file = open(log_path, "a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                str(PROJECT_ROOT / "collect_data.py"),
                "--ip",
                ip,
                "--interval",
                str(interval),
                "--case",
                case,
            ],
            cwd=str(PROJECT_ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
    except OSError as exc:
        log_file.close()
        st.error(f"Could not start the collector: {exc}")
        st.session_state.collector_process = None
        return

    # Popen owns a duplicated OS handle, so the Python file object can be closed.
    log_file.close()
    st.session_state.collector_process = process
    st.success(f"Collector started (PID {process.pid}).")


def stop_collector() -> None:
    process = st.session_state.collector_process
    if process is None:
        st.info("Data collection is not running.")
        return
    if process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=5)
            st.success("Collector stopped safely.")
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            st.warning("Collector did not stop normally; it was terminated.")
    st.session_state.collector_process = None


def read_collector_log() -> str:
    log_path = PROJECT_ROOT / "collector.log"
    if not log_path.exists():
        return "No collector log has been created yet."
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-40:])
    except OSError as exc:
        return f"Could not read collector.log: {exc}"


st.set_page_config(
    page_title="PCM Milk Chilling DEV",
    page_icon="🧊",
    layout="wide",
)
st.markdown(CSS, unsafe_allow_html=True)

if "collector_process" not in st.session_state:
    st.session_state.collector_process = None

with st.sidebar:
    st.title("⚙️ Collection Controls")
    esp32_ip = st.text_input("ESP32 IP address", value=DEFAULT_ESP32_IP)
    interval = st.number_input(
        "Collection interval (seconds)",
        min_value=0.5,
        max_value=3600.0,
        value=float(DEFAULT_INTERVAL_SECONDS),
        step=0.5,
        disabled=True,
        help="Collection is fixed at 5 seconds.",
    )
    case = st.selectbox(
        "Experimental case",
        [
            "Unlabelled",
            "Case A: Without PCM",
            "Case B: PCM only",
            "Case C: PCM with evaporative sleeve",
            "Case D: PCM with sleeve and agitation",
        ],
    )
    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("▶ Start", use_container_width=True):
            start_collector(esp32_ip, float(interval), case)
    with col_stop:
        if st.button("⏹ Stop", use_container_width=True):
            stop_collector()

    process = st.session_state.collector_process
    running = process is not None and process.poll() is None
    st.markdown(
        f"<b>Collector:</b> {'🟢 Running' if running else '🔴 Stopped'}",
        unsafe_allow_html=True,
    )
    if process is not None and not running:
        st.caption(f"Collector exit code: {process.poll()}")
    connected, status_text = esp32_status(esp32_ip)
    st.markdown(
        f"<b>ESP32:</b> {'🟢' if connected else '🔴'} {status_text}",
        unsafe_allow_html=True,
    )
    with st.expander("Collector log"):
        st.code(read_collector_log(), language="text")
    refresh_seconds = st.slider("Dashboard refresh (seconds)", 2, 60, 5)

st_autorefresh(interval=refresh_seconds * 1000, key="dashboard_refresh")

st.title("🥛 Real-Time PCM Milk Chilling")
st.caption("Hybrid PCM-based milk chilling can: collection, exploration and visualization")

tabs = st.tabs(
    [
        "Overview",
        "Live Monitoring",
        "EDA & Statistics",
        "Visualizations",
        "Data & Cleaning",
        "Experimental Cases",
    ]
)

original = load_dataset(DATASET_PATH)
cleaned, cleaning_summary = clean_dataset(original)
eda = calculate_eda(cleaned)

with tabs[0]:
    st.subheader("Project Overview")
    st.write(
        "This dashboard monitors actual milk temperature readings delivered over Wi-Fi "
        "by an ESP32 and one DS18B20 sensor. A new reading is appended to the CSV without "
        "fabricating or replacing historical measurements."
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Temperature", format_metric(cleaned["Milk_Temperature"].iloc[-1]) + " °C" if not cleaned.empty else "N/A")
    m2.metric("Average", format_metric(eda["mean"]) + " °C")
    m3.metric("Minimum", format_metric(eda["minimum"]) + " °C")
    m4.metric("Maximum", format_metric(eda["maximum"]) + " °C")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Total Readings", eda["observations"])
    m6.metric("Temperature Change", format_metric(eda["temperature_change"]) + " °C")
    m7.metric("Cooling Rate", format_metric(eda["cooling_rate_c_per_min"]) + " °C/min")
    m8.metric("ESP32", "Connected" if connected else "Disconnected")

with tabs[1]:
    st.subheader("Live Temperature Monitoring")
    if cleaned.empty:
        st.info("No valid collected readings are available yet.")
    else:
        st.line_chart(cleaned.set_index("Timestamp")[["Milk_Temperature"]], use_container_width=True)
        st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with tabs[2]:
    st.subheader("Exploratory Data Analysis")
    labels = [
        ("Observations", eda["observations"]),
        ("Mean", format_metric(eda["mean"])),
        ("Median", format_metric(eda["median"])),
        ("Mode", format_metric(eda["mode"])),
        ("Minimum", format_metric(eda["minimum"])),
        ("Maximum", format_metric(eda["maximum"])),
        ("Standard deviation", format_metric(eda["standard_deviation"])),
        ("Variance", format_metric(eda["variance"])),
        ("Range", format_metric(eda["range"])),
        ("First quartile", format_metric(eda["q1"])),
        ("Third quartile", format_metric(eda["q3"])),
        ("IQR", format_metric(eda["iqr"])),
    ]
    stats_frame = pd.DataFrame(labels, columns=["Statistic", "Value"])
    st.dataframe(stats_frame, use_container_width=True, hide_index=True)
    st.write(
        f"Temperature change: **{format_metric(eda['temperature_change'])} °C**  \n"
        f"Overall cooling rate: **{format_metric(eda['cooling_rate_c_per_min'])} °C/min**"
    )

with tabs[3]:
    st.subheader("Statistical Visualizations")
    if cleaned.empty:
        st.info("Charts will appear after valid readings are collected.")
    else:
        with st.expander("Date and temperature filters", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            min_dt = cleaned["Timestamp"].min().to_pydatetime()
            max_dt = cleaned["Timestamp"].max().to_pydatetime()
            start_dt = c1.datetime_input("Start", min_dt)
            end_dt = c2.datetime_input("End", max_dt)
            temp_min = c3.number_input(
                "Minimum temperature (C)",
                value=float(cleaned["Milk_Temperature"].min()),
            )
            temp_max = c4.number_input(
                "Maximum temperature (C)",
                value=float(cleaned["Milk_Temperature"].max()),
            )
        start_ts = align_filter_timestamp(start_dt, cleaned["Timestamp"])
        end_ts = align_filter_timestamp(end_dt, cleaned["Timestamp"])
        filtered = cleaned[
            (cleaned["Timestamp"] >= start_ts)
            & (cleaned["Timestamp"] <= end_ts)
            & cleaned["Milk_Temperature"].between(temp_min, temp_max)
        ].copy()
        if filtered.empty:
            st.warning("No readings match the selected filters.")
        else:
            import matplotlib.pyplot as plt
            import visualization

            chart1, chart2 = st.columns(2)
            with chart1:
                fig, ax = plt.subplots(figsize=(8, 4))
                visualization.scatter_temperature(filtered, ax)
                st.pyplot(fig)
            with chart2:
                fig, ax = plt.subplots(figsize=(7, 4))
                visualization.box_plot(filtered, ax)
                st.pyplot(fig)

            chart3, chart4 = st.columns(2)
            with chart3:
                fig, ax = plt.subplots(figsize=(8, 4))
                visualization.line_chart(filtered, ax)
                st.pyplot(fig)
            with chart4:
                fig, ax = plt.subplots(figsize=(8, 4))
                visualization.histogram(filtered, ax)
                st.pyplot(fig)

            chart5, chart6 = st.columns(2)
            with chart5:
                fig, ax = plt.subplots(figsize=(7, 4))
                visualization.heatmap(filtered, ax)
                st.pyplot(fig)
            with chart6:
                window = st.slider("Rolling average window", 2, 50, 10)
                fig, ax = plt.subplots(figsize=(8, 4))
                visualization.rolling_average(filtered, window, ax)
                st.pyplot(fig)

            fig, ax = plt.subplots(figsize=(10, 4))
            visualization.statistics_bar_chart(filtered, ax)
            st.pyplot(fig)

with tabs[4]:
    st.subheader("Dataset Preview and Cleaning Summary")
    st.write(
        "The original CSV is preserved. Cleaning removes missing timestamps, "
        "missing/non-numeric temperatures, invalid sensor range values and exact duplicates "
        "only in memory."
    )
    c1, c2 = st.columns([2, 1])
    with c1:
        if cleaned.empty:
            st.info("Dataset is empty or contains no valid readings.")
        else:
            st.dataframe(cleaned, use_container_width=True, hide_index=True)
    with c2:
        st.json(cleaning_summary)
        if DATASET_PATH.exists():
            st.download_button(
                "⬇ Download original CSV",
                data=DATASET_PATH.read_bytes(),
                file_name="temperature_readings.csv",
                mime="text/csv",
            )

with tabs[5]:
    st.subheader("Experimental Case Comparison")
    st.write(
        "Comparisons require the two-column CSV to include actual case labels. "
        "No experimental result is simulated or generated."
    )
    st.info("The ESP32 CSV is two-column format: Timestamp and Milk_Temperature.")
