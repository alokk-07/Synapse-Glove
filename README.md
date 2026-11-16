# 🌐 Synapse Glove: Biomedical Signal Acquisition & DSP Platform

**Synapse Glove** is an untethered, wearable biomedical signal acquisition and tactile probing system engineered for an academic **Signals and Systems** framework. By mounting an optical photoplethysmography (PPG) pulse sensor directly onto the index fingertip, it turns the human hand into a mobile medical diagnostic tool capable of spot-checking arterial pulse waves across various physiological pressure points (radial, brachial, and carotid arteries).

The system features a **zero-hardcoded ESP32 microcontroller wearable node**, an asynchronous **FastAPI + SciPy Digital Signal Processing (DSP) telemetry backend** with Zeroconf/mDNS service broadcasting, and a high-performance **Swiss Neumorphic Telemetry Dashboard** rendering glowing pulse traces at 60 FPS on an HTML5 canvas.

---

## ⚡ What's New & Upgraded (Current Updates)

- **Zero-Hardcode Wi-Fi Provisioning (`WiFiManager`)**: No hardcoded Wi-Fi SSIDs or passwords. On boot, if no stored network is found, the ESP32 automatically launches an on-demand captive portal AP (`SynapseGlove-Setup` at `192.168.4.1`) for web-based Wi-Fi configuration and optional server IP fallback.
- **Dynamic Server Discovery (`mDNS / Zeroconf`)**: The Python backend broadcasts its presence via `_synapse._tcp.local.`. The ESP32 discovers the host workstation's dynamic IP address and WebSocket port over multicast DNS automatically—eliminating manual IP updates across DHCP environments.
- **PlatformIO Unified Toolchain**: Full development workflow migrated to PlatformIO (`platformio.ini`) with automated library management (`WebSockets`, `WiFiManager`, `ArduinoJson`), one-click builds, and flashing.
- **Continuous State-Preserved IIR Filtering**: 3-stage SciPy DSP filter pipeline with Second-Order Sections (`sos`) and initial condition state preservation (`zi`) ensuring clean, artifact-free continuous streaming across chunk boundaries.
- **Automatic Fallback Simulator**: Seamless transition between real ESP32 hardware streaming and a morphologically accurate synthetic PPG generator (systolic peak, dicrotic notch, baseline wander, 50 Hz powerline hum, and EMG noise) for immediate verification without physical hardware connected.
- **Comprehensive Documentation**: Complete academic engineering report generator script (`generate_docs.py`) generating publication-grade Word documentation (`Synapse_Glove_Project_Documentation.docx`).

---

## 🏗️ System Architecture (MVC Pattern)

```
Synapse-Glove/
├── platformio.ini                        # PlatformIO project configuration & dependency manager
├── requirements.txt                      # Python backend dependencies (FastAPI, SciPy, Zeroconf, etc.)
├── run_command.txt                       # Quick command cheat sheet
├── generate_docs.py                      # Academic technical documentation generator (.docx)
├── Synapse_Glove_Project_Documentation.docx # Generated comprehensive engineering documentation
├── README.md                             # Project overview & operational manual
│
├── synapse_glove_esp32/
│   └── synapse_glove_esp32.ino           # ESP32 C++ firmware (250 Hz ADC, WiFiManager, mDNS, WebSocket)
│
└── app/                                  # Full-Stack MVC Telemetry Server
    ├── __init__.py
    ├── main.py                           # FastAPI application entrypoint & static asset server
    │
    ├── models/                           # [MODEL LAYER: Signal Processing & Math Engine]
    │   ├── __init__.py
    │   ├── dsp_pipeline.py               # 3-Stage real-time SciPy IIR filter (HP, Notch, LP with state preservation)
    │   ├── signal_metrics.py             # Feature extraction: BPM (peak detection), SNR (dB), SQI (%), actual Fs
    │   └── signal_simulator.py           # Morphological synthetic PPG generator with biological noise models
    │
    ├── controllers/                      # [CONTROLLER LAYER: Networking & Routing]
    │   ├── __init__.py
    │   ├── stream_controller.py          # WebSocket broker, DSP coordinator & client broadcast manager
    │   ├── routes.py                     # REST endpoints (/api/status, /api/filter-settings) & WebSocket routes
    │   └── mdns_broadcaster.py           # Zeroconf / mDNS service advertiser (_synapse._tcp)
    │
    └── views/                            # [VIEW LAYER: Swiss Neumorphic Web Interface]
        ├── index.html                    # Neumorphic layout, oscilloscope container & metric cards
        ├── css/
        │   └── style.css                 # Neumorphic soft shadows, glowing CRT phosphor styling, responsive grid
        └── js/
            ├── canvas_wave.js            # 60 FPS HTML5 canvas oscilloscope with grid and phosphor glow
            ├── ui_controls.js            # Real-time sliders (X, Y, Z cutoffs), toggles, metric update DOM handlers
            └── app.js                    # Dual WebSocket bridge, auto-reconnect engine & telemetry dispatcher
```

---

## 🧮 Digital Signal Processing (DSP) Pipeline

The signals acquired by the fingertip optical sensor pass through a sequential 3-stage discrete-time filter cascade running at $F_s = 250\text{ Hz}$:

```
  [Raw PPG ADC: GPIO 34] 
            │ (250 Hz, 12-bit)
            ▼
┌───────────────────────────────────────┐
│ Stage 1 (X): High-Pass Filter         │ ➔ 2nd-Order Butterworth SOS (fc = 0.50 Hz)
│ Purpose: Eliminates respiration &     │   Strips DC baseline drift and movement offsets
│ contact pressure baseline wander      │
└───────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│ Stage 2 (Y): Digital IIR Notch Filter │ ➔ IIR Notch Filter (f0 = 50.0 Hz, Q = 30)
│ Purpose: Surgically removes 50 Hz AC  │   Removes powerline hum without corrupting
│ electromagnetic interference          │   cardiac harmonic frequencies
└───────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│ Stage 3 (Z): Low-Pass Filter          │ ➔ 4th-Order Butterworth SOS (fc = 40.0 Hz)
│ Purpose: Attenuates high-frequency    │   Eliminates optical jitter and EMG micro-tremors
│ muscular tremor noise & thermal jitter│
└───────────────────────────────────────┘
            │
            ▼
[Clean Arterial PPG Waveform] ──► Peak Detection (BPM) + SNR (dB) + 60 FPS Canvas
```

### Filter Parameter Summary

| Filter Stage | Topology | Default Parameters | Dynamic UI Range | Target Artifact / Noise Removed |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1 (X)** | 2nd-Order Butterworth High-Pass | $f_c = 0.50\text{ Hz}$ (SOS) | $0.05\text{ Hz} - 3.00\text{ Hz}$ | Respiration drift, finger contact pressure shifts, DC offset |
| **Stage 2 (Y)** | Discrete IIR Digital Notch | $f_0 = 50.0\text{ Hz},\ Q = 30$ | $45.0\text{ Hz} - 65.0\text{ Hz}$ | 50 Hz mains electrical interference |
| **Stage 3 (Z)** | 4th-Order Butterworth Low-Pass | $f_c = 40.0\text{ Hz}$ (SOS) | $5.0\text{ Hz} - 80.0\text{ Hz}$ | High-frequency EMG muscle tremors, photodiode thermal noise |

> **State Preservation (`zi`):** The filters use `scipy.signal.sosfilt` with initial state vectors (`sosfilt_zi`) and `lfilter_zi` for the notch filter. This preserves filter memory between 5-sample WebSocket packets and prevents boundary discontinuity spikes.

---

## 📊 Real-Time Metrics & Feature Extraction

The Model layer extracts real-time physiological and diagnostic indicators computed over a rolling 4-second time window:

1. **Heart Rate (BPM)**: Peak-detection algorithm using `scipy.signal.find_peaks` on systolic upstrokes with adaptive prominence thresholding and inter-beat interval ($RR$) median filtering bounded to 40–171 BPM.
2. **Signal-to-Noise Ratio (SNR)**: Computed in decibels ($\text{dB}$) by comparing the variance of the filtered arterial signal against the noise residual ($\text{raw} - \text{filtered}$).
3. **Signal Quality Index (SQI)**: Percentage score evaluating waveform morphology, peak consistency, and baseline stability.
4. **Effective Sampling Rate ($F_s$)**: Live hardware throughput counter measuring actual samples received per second.

---

## 🚀 Quickstart & Setup Guide

### Prerequisites
- **Python 3.9+**
- **VS Code** with the **PlatformIO IDE** extension installed (or Arduino IDE 2.x)
- ESP32 Development Board (ESP32-WROOM-32) + Analog Pulse Sensor

---

### Step 1: Install Python Backend Dependencies

```powershell
# Open terminal in project root: Synapse-Glove
# Create and activate virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

### Step 2: Start the FastAPI DSP Backend

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Binds to `0.0.0.0:8000` so devices on the local Wi-Fi network can communicate with the server.
- The `MDNSBroadcaster` immediately announces the server as `_synapse._tcp.local.` on the local network.
- Open your browser at:
  ```
  http://localhost:8000
  ```
- **Instant Simulator Mode:** If the ESP32 is not connected, the backend automatically runs in synthetic PPG mode. You can test slider adjustments, inspect the oscilloscope trace, and verify the UI immediately.

---

### Step 3: Flash ESP32 Firmware (PlatformIO)

1. Open the project folder `Synapse-Glove` in **VS Code**.
2. Connect your ESP32 to your PC via a micro-USB data cable.
3. In VS Code, open the PlatformIO sidebar or bottom status bar:
   - Click **Build** (`✓`) to compile.
   - Click **Upload** (`→`) to flash the firmware.
   - Or run from terminal:
     ```powershell
     pio run -t upload
     ```
4. Open the PlatformIO **Serial Monitor** (plug icon or `pio device monitor`) at **115200 baud**.

---

### Step 4: First-Time Wi-Fi & Dynamic Server Setup

Thanks to **zero-hardcoding**, you don't edit Wi-Fi credentials in source code:

1. **Connect to Captive AP**: On first boot (or when changing networks), the ESP32 broadcasts a Wi-Fi Access Point named **`SynapseGlove-Setup`**.
2. **Open Setup Portal**: Connect your phone or laptop to `SynapseGlove-Setup`. The captive portal will appear automatically (or open `http://192.168.4.1` in your browser).
3. **Configure Wi-Fi**:
   - Tap **Configure WiFi**.
   - Select your Wi-Fi network (or mobile hotspot) and enter the password.
   - *(Optional)* If your local network blocks mDNS, enter your workstation's IP in the **Laptop IP (optional fallback)** field.
   - Click **Save**.
4. **Auto-Discovery & Streaming**:
   - The ESP32 connects to Wi-Fi, queries mDNS for `_synapse._tcp`, locates your laptop's backend, and connects to `ws://<laptop-ip>:8000/ws/esp32`.
   - The dashboard top status pill will turn **Green** and display **`HARDWARE LIVE`**.

---

## 🔌 Hardware Wiring & Pinout

### Pulse Sensor to ESP32 Pin Mapping

| Pulse Sensor Pin | Wire Color | ESP32 Pin | Technical Description |
| :--- | :--- | :--- | :--- |
| **VCC (+)** | Red | **3V3** | 3.3V Regulated Power Output |
| **GND (-)** | Black | **GND** | System Common Ground |
| **Signal (S)** | Purple / Yellow / White | **GPIO 34** (ADC1_CH6) | Low-noise input-only analog pin (ADC1) |

> [!IMPORTANT]
> **Use ADC1 Exclusively:** On the ESP32, **ADC2 is hardware-disabled** whenever the Wi-Fi radio is actively transmitting. GPIO 34 belongs to **ADC1**, guaranteeing uninterrupted continuous analog sampling alongside high-throughput Wi-Fi streaming.

### Power Supply Options

```
Option A: Tethered USB (Bench / Viva Testing)
[ Laptop USB Port ] ────(Micro-USB Cable)────► [ ESP32 Micro-USB Port ]

Option B: Portable Untethered Wearable (2x AAA / Battery)
[ Battery (+) ] ────► [ Slide Switch ] ────► [ 5V Step-Up Boost ] ────► [ ESP32 VIN / 5V ]
[ Battery (-) ] ───────────────────────────────────────────────────────► [ ESP32 GND ]
```

*Note: ESP32 Wi-Fi bursts draw up to 250 mA peak current. When running on small batteries, a 5V boost regulator or high-discharge 3.7V LiPo with LDO is recommended to prevent brownout resets.*

---

## 📡 API & WebSocket Reference

### WebSocket Channels

| Endpoint | Protocol | Direction | Description |
| :--- | :--- | :--- | :--- |
| `/ws/esp32` | WebSocket (JSON) | ESP32 ➔ Server | Batched raw ADC telemetry: `{"samples": [v1,v2,v3,v4,v5], "t": millis}` |
| `/ws/stream` | WebSocket (JSON) | Server ⇄ Web UI | 60 FPS processed waveform streaming, filter state sync, and real-time metrics |

### REST Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the Swiss Neumorphic Web Dashboard |
| `GET` | `/api/status` | Returns system health, hardware connection status, and active filter configuration |
| `POST` | `/api/filter-settings` | Updates $f_c$ high-pass, notch frequency, and low-pass cutoffs dynamically |
| `POST` | `/api/mode` | Toggles between live hardware mode and forced synthetic simulator mode |

---

## 📑 Generating Academic Documentation (.docx)

The repository contains an automated engineering report builder:

```powershell
python generate_docs.py
```

This compiles `Synapse_Glove_Project_Documentation.docx`, complete with formal academic formatting:
- Academic context, course learning outcomes, and Signals & Systems alignment.
- Mathematical derivations (Bilinear Transform, SOS transfer functions, Difference Equations).
- Comprehensive hardware schematic and assembly instructions.
- Full software architecture diagrams and source code explanations.
- Viva voce interview Q&A and laboratory evaluation guide.

---

## 🛠️ Troubleshooting & Diagnostic Tips

| Symptom | Probable Cause | Recommended Resolution |
| :--- | :--- | :--- |
| **ESP32 does not connect to backend** | mDNS blocked across public/campus Wi-Fi subnets | Connect both PC and ESP32 to a mobile phone hotspot, or enter the PC's IP (`ipconfig`) in the captive portal fallback field. |
| **Dashboard stuck on "SIMULATOR"** | Hardware not streaming or Wi-Fi disconnected | Click the **ESP32 LIVE** button in the header; ensure the onboard ESP32 LED (GPIO 2) is illuminated, indicating active WebSocket connection. |
| **Noisy or flatlined signal** | Sensor contact pressure too loose or too tight | Place the optical sensor lightly against the finger pulp with minimal pressure; avoid occluding capillary blood flow. |
| **ESP32 continuously resets** | Brownout detector triggered by current surge | Power ESP32 via a USB 3.0 port or 5V 1A+ dedicated power supply during Wi-Fi transmission. |
| **Port 8000 already in use** | Stray uvicorn background process | Run `Get-Process python` in PowerShell and terminate the stale process before restarting uvicorn. |
