from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset"
DATASET_DIR.mkdir(parents=True, exist_ok=True)
GRAPHS_DIR = PROJECT_ROOT / "graphs"
GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

DATASET_PATH = DATASET_DIR / "temperature_readings.csv"
DEFAULT_ESP32_IP = os.getenv("ESP32_IP", "192.168.4.1")
DEFAULT_ESP32_ENDPOINT = f"http://{DEFAULT_ESP32_IP}/data"
DEFAULT_INTERVAL_SECONDS = float(os.getenv("COLLECTION_INTERVAL", "5"))
REQUEST_TIMEOUT_SECONDS = 5
MIN_VALID_TEMPERATURE_C = -55.0
MAX_VALID_TEMPERATURE_C = 125.0
COLUMNS = ["Timestamp", "Milk_Temperature"]
