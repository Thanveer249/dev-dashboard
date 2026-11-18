"""Collect temperature readings from an ESP32 and append them safely to CSV."""

from __future__ import annotations

import argparse
import csv
import math
import signal
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from utils.config import (
    COLUMNS,
    DATASET_PATH,
    DEFAULT_ESP32_ENDPOINT,
    DEFAULT_INTERVAL_SECONDS,
    MAX_VALID_TEMPERATURE_C,
    MIN_VALID_TEMPERATURE_C,
    REQUEST_TIMEOUT_SECONDS,
)


class ESP32Collector:
    def __init__(
        self,
        endpoint: str = DEFAULT_ESP32_ENDPOINT,
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
        dataset_path: Path = DATASET_PATH,
        experiment_case: str = "Unlabelled",
    ) -> None:
        self.endpoint = endpoint
        self.interval_seconds = max(0.1, float(interval_seconds))
        self.dataset_path = Path(dataset_path)
        self.experiment_case = experiment_case
        self.stop_event = threading.Event()
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

    def fetch_reading(self) -> Optional[float]:
        try:
            response = requests.get(self.endpoint, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ESP32 connection error: {exc}")
            return None

        try:
            payload = response.json()
        except requests.JSONDecodeError as exc:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Invalid JSON response: {exc}")
            return None

        if "milk_temperature" not in payload:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Response missing milk_temperature")
            return None

        try:
            temperature = float(payload["milk_temperature"])
        except (TypeError, ValueError):
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Sensor returned a non-numeric value")
            return None

        if not math.isfinite(temperature):
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Sensor returned a non-finite value")
            return None
        if not MIN_VALID_TEMPERATURE_C <= temperature <= MAX_VALID_TEMPERATURE_C:
            print(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
                f"Invalid temperature {temperature:.2f} C"
            )
            return None
        return temperature

    def append_reading(self, temperature: float) -> None:
        timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        row = [timestamp, temperature]
        try:
            # Open in append mode; this preserves every existing dataset record.
            with open(self.dataset_path, "a", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                if self.dataset_path.stat().st_size == 0:
                    writer.writerow(COLUMNS)
                writer.writerow(row)
                csv_file.flush()
        except (OSError, csv.Error) as exc:
            raise RuntimeError(f"CSV write error: {exc}") from exc

    def run(self) -> None:
        print(f"Starting ESP32 collection from {self.endpoint}", flush=True)
        print(f"Saving to {self.dataset_path}", flush=True)
        print("Press Ctrl+C to stop.", flush=True)

        while not self.stop_event.is_set():
            try:
                temperature = self.fetch_reading()
                if temperature is not None:
                    self.append_reading(temperature)
                    print(
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
                        f"{temperature:.2f} C saved",
                        flush=True,
                    )
                else:
                    print(
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
                        "No reading saved; retrying.",
                        flush=True,
                    )
            except RuntimeError as exc:
                print(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {exc}",
                    flush=True,
                )
            self.stop_event.wait(self.interval_seconds)

    def stop(self) -> None:
        self.stop_event.set()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect ESP32 DS18B20 milk temperatures.")
    parser.add_argument("--ip", default="192.168.4.1", help="ESP32 IP address")
    parser.add_argument("--endpoint", default=None, help="Full HTTP endpoint, overrides --ip")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS)
    parser.add_argument(
        "--case",
        default="Unlabelled",
        choices=[
            "Unlabelled",
            "Case A: Without PCM",
            "Case B: PCM only",
            "Case C: PCM with evaporative sleeve",
            "Case D: PCM with sleeve and agitation",
        ],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    endpoint = args.endpoint or f"http://{args.ip}/data"
    collector = ESP32Collector(endpoint, args.interval, DATASET_PATH, args.case)

    def handle_stop(_signum, _frame) -> None:
        collector.stop()

    signal.signal(signal.SIGINT, handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_stop)
    collector.run()


if __name__ == "__main__":
    main()
