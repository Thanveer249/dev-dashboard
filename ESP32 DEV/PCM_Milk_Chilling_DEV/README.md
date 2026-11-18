# Real-Time PCM-Based Milk Chilling DEV

This Python project collects real milk-temperature readings from an ESP32 and a DS18B20 sensor over Wi-Fi, stores them in a CSV file, cleans and analyzes the data, and shows an interactive Streamlit dashboard.

No temperature data is fabricated. The project writes nothing to the dataset unless the ESP32 returns a valid numeric reading.

## Project structure

```text
PCM_Milk_Chilling_DEV/
├── main.py
├── collect_data.py
├── preprocessing.py
├── analysis.py
├── visualization.py
├── dashboard.py
├── requirements.txt
├── README.md
├── dataset/
│   └── temperature_readings.csv
├── graphs/
└── utils/
    └── config.py
```

## Windows and VS Code setup

1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Open VS Code and install the Python extension.
3. Open the project folder in VS Code:

```powershell
cd "C:\code\DS code\ESP32 DEV\PCM_Milk_Chilling_DEV"
code .
```

4. Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, allow local scripts for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.venv\Scripts\Activate.ps1
```

5. Install packages:

```powershell
pip install -r requirements.txt
```

## ESP32 HTTP endpoint

On the Windows laptop:

1. Open Wi-Fi settings and connect to the ESP32 network `ESP32_MILK_MONITOR`.
2. Enter `Milk12345` as the Wi-Fi password.
3. Confirm the laptop receives a local address in the ESP32 network.
4. Verify `http://192.168.4.1/data` returns JSON containing `milk_temperature`.

No internet connection is required for collection.

```text
http://<ESP32-IP>/data
```

The AP address is `http://192.168.4.1/data`. Its response must be JSON:

```json
{"milk_temperature": 28.45}
```

A minimal Arduino sketch can use the following libraries and behavior:

```cpp
#include <WiFi.h>
#include <WebServer.h>
#include <OneWire.h>
#include <DallasTemperature.h>

const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
const byte SENSOR_PIN = 4;

WebServer server(80);
OneWire oneWire(SENSOR_PIN);
DallasTemperature sensors(&oneWire);

void setup() {
  Serial.begin(115200);
  sensors.begin();
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);

  server.on("/data", HTTP_GET, []() {
    sensors.requestTemperatures();
    float temperature = sensors.getTempCByIndex(0);
    if (temperature == DEVICE_DISCONNECTED_C || temperature < -55.0 || temperature > 125.0) {
      server.send(500, "application/json", "{\"error\":\"invalid_sensor_reading\"}");
      return;
    }
    String json = "{\"milk_temperature\":";
    json += String(temperature, 2);
    json += "}";
    server.send(200, "application/json", json);
  });

  server.begin();
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  server.handleClient();
}
```

Install **OneWire** and **DallasTemperature** in Arduino IDE/VS Code Arduino. The DS18B20 data pin should be GPIO 4, ground to GND, 3.3 V to VDD, and a 4.7 kΩ resistor between data and 3.3 V.

## Run the project

Open three terminals in VS Code as needed.

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Start collection

Default address and five-second interval:

```powershell
python main.py
```

Custom address, interval and experimental case:

```powershell
python main.py --ip 192.168.4.1 --interval 5
```

Press `Ctrl+C` to stop.

The collector automatically retries after network failures. It does not add fake readings, and invalid sensor values are rejected.

### Start the dashboard

```powershell
python -m streamlit run dashboard.py
```

Open the URL printed in the terminal, usually `http://localhost:8501`.

The dashboard sidebar can start and stop the collector. The ESP32 address defaults to `192.168.4.1`, and collection runs every 5 seconds. The dashboard reads the shared CSV while the collector appends valid readings in CSV append mode without deleting historical records.

## Data format

The CSV is:

```text
Timestamp,Milk_Temperature
2026-11-18T20:40:32+05:30,28.45
```

The original CSV is never deleted or cleaned in place. Cleaning occurs on a copy loaded by Pandas.

## Troubleshooting

- **Cannot reach ESP32:** verify that both devices use the same Wi-Fi network and enter the IP shown in the ESP32 serial monitor.
- **Invalid JSON:** open `http://<ESP32-IP>/data` in a browser and confirm the response is JSON.
- **Device is disconnected:** test the DS18B20 wiring and 4.7 kΩ pull-up resistor.
- **No rows in dashboard:** start collection and wait one interval. Invalid readings are intentionally omitted.
- **CSV locked or write error:** stop duplicate collector processes, then restart `python main.py`.
- **Missing module:** activate `.venv`, upgrade pip, and run `pip install -r requirements.txt`.
- **Port already in use:** run `streamlit run dashboard.py --server.port 8502`.
