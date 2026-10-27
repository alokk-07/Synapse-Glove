# 🌐 Synapse Glove: Biomedical Signal Acquisition & DSP Platform

**Synapse Glove** is an untethered, wearable biomedical signal acquisition and tactile probing system engineered for an academic **Signals and Systems** framework. By mounting an optical photoplethysmography (PPG) pulse sensor directly onto the index fingertip, it turns the human hand into a mobile medical diagnostic tool capable of spot-checking arterial pulse waves at various physiological pressure points.

The system features an **ESP32 microcontroller node**, a real-time **3-Stage SciPy Digital Signal Processing (DSP) Engine**, and a high-end **Swiss Minimalist / Neumorphic Telemetry Dashboard** running at 60 FPS.

---

## 🏗️ System Architecture (MVC Pattern)

```
Synapse Glove/
│
├── synapse_glove_esp32.ino        # ESP32 C++ Firmware (250 Hz Timer ADC + WebSocket)
├── requirements.txt               # Python Dependencies
├── .gitignore                     # Git ignore rules
├── README.md                      # Complete Project Documentation
│
├── app/
│   ├── main.py                    # Application Entrypoint & Static Server
│   │
│   ├── models/                    # [MODEL LAYER]
│   │   ├── dsp_pipeline.py        # 3-Stage Real-Time SciPy IIR Filter (HP, Notch, LP)
│   │   ├── signal_metrics.py      # Heart Rate (BPM), Real-time SNR (dB), SQI & Fs Monitor
│   │   └── signal_simulator.py    # Morphological PPG Simulator (for testing without hardware)
│   │
│   ├── controllers/               # [CONTROLLER LAYER]
│   │   ├── stream_controller.py   # WebSocket Broker, DSP Routing & Broadcast Hub
│   │   └── routes.py              # REST API & WebSocket Endpoint Handlers
│   │
│   └── views/                     # [VIEW LAYER - Swiss Neumorphic UI]
│       ├── index.html             # Neumorphic Layout & Oscilloscope Card
│       ├── css/
│       │   └── style.css          # Neumorphic Box Shadows, CRT Glowing Traces, Fonts
│       └── js/
│           ├── canvas_wave.js     # 60 FPS HTML5 Canvas Oscilloscope with Phosphor Glow
│           ├── ui_controls.js     # Sliders, Mode Toggles, and Metric Handlers
│           └── app.js             # Client WebSocket Bridge & Event Orchestrator
```

---

## 🧮 Digital Signal Processing (DSP) Pipeline

| Stage | Filter Type | Cutoff / Parameters | Purpose |
| :--- | :--- | :--- | :--- |
| **Stage 1 (X)** | 2nd-Order Butterworth High-Pass (SOS) | $f_c = 0.5\text{ Hz}$ | Strips respiration drift, finger contact pressure changes, and DC baseline wander. |
| **Stage 2 (Y)** | Digital IIR Notch Filter | $f_0 = 50.0\text{ Hz},\ Q = 30$ | Surgically removes 50 Hz AC electrical grid hum without altering cardiac harmonics. |
| **Stage 3 (Z)** | 4th-Order Butterworth Low-Pass (SOS) | $f_c = 40.0\text{ Hz}$ | Eliminates high-frequency muscle micro-tremor noise (EMG) and optical jitter. |

*Note: Second-Order Sections (`sos`) and initial condition state preservation (`zi`) are utilized to guarantee zero boundary discontinuities between streaming chunks.*

---

## 🚀 Quickstart Guide

### 1. Install Python Dependencies
Ensure you have Python 3.9+ installed:
```powershell
# Create a virtual environment (optional but recommended)
python -m venv .venv
.\.venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Start the FastAPI DSP Backend
```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your web browser and navigate to:
```
http://localhost:8000
```
> The dashboard will immediately start streaming in **Simulator Mode**! You can adjust the $X, Y, Z$ sliders, observe the glowing green pulse trace, and inspect the real-time metrics before touching any hardware.

---

## ⚡ ESP32 Firmware Setup

1. Open `synapse_glove_esp32.ino` in the **Arduino IDE**.
2. Install the **WebSockets** library:
   * Go to `Sketch` ➔ `Include Library` ➔ `Manage Libraries...`
   * Search for **`WebSockets` by Markus Sattler** and click **Install**.
3. Select your board:
   * `Tools` ➔ `Board` ➔ `ESP32 Arduino` ➔ `ESP32 Dev Module`.
4. Configure Wi-Fi & Laptop IP:
   * Set `WIFI_SSID` and `WIFI_PASSWORD` to your local 2.4 GHz Wi-Fi network.
   * Run `ipconfig` on your laptop to find its local IPv4 address (e.g. `192.168.1.100`).
   * Set `SERVER_HOST` to your laptop's IP address.
5. Plug the ESP32 into your laptop via USB and click **Upload**.
6. Open the Arduino Serial Monitor at **115200 baud** to confirm connection.

---

## 🔌 Hardware Wiring & Assembly Guide

### Pin Connections

| Pulse Sensor Pin | ESP32 Pin | Function |
| :--- | :--- | :--- |
| **VCC (+)** (Red wire) | **3V3** | 3.3V Power Rail |
| **GND (-)** (Black wire) | **GND** | Ground Reference |
| **Signal (S)** (Yellow/White wire) | **GPIO 34** (ADC1) | Analog Pulse Voltage |

### Power Wiring (2x AAA Battery Pack)

```
[ Battery (+) Red Wire ] ────► [ Slide Switch ] ────► [ 5V / VIN Pin ]
[ Battery (-) Black Wire] ──────────────────────────► [ GND Pin ]
```

> **Important Electrical Note regarding 2x AAA (3.0V):**
> 2x AAA batteries provide 3.0V nominal. When Wi-Fi initiates, high current spikes can cause the voltage to dip, which may trigger the ESP32 brownout detector.
> * **During initial testing/viva:** Power the ESP32 via USB cable while streaming data wirelessly over Wi-Fi.
> * **For untethered battery use:** Wire a miniature 5V step-up (boost) converter between the battery pack and the ESP32 `VIN` pin to maintain a steady 5V supply.
