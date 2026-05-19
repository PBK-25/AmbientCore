# 🌡️ TempSensor Desktop Widget

A real-time desktop monitoring widget for **Windows 11** that reads live temperature and humidity from a Xiaomi BLE sensor and combines it with full PC hardware stats — all in a sleek dark-mode system tray widget.

> Built with Python · Bluetooth Low Energy · No cloud · No subscription · No data leaves your machine.

---

## 📸 What It Looks Like

```
┌─────────────────────────────────────┐
│   SYSTEM & CLIMATE MONITOR          │
├─────────────────────────────────────┤
│ ELECTRICAL CONNECTIONS              │
│   Temperature   26.4°C              │
│   Humidity      48%                 │
│   Battery       3107 mV (~100%)     │
├─────────────────────────────────────┤
│ CPU                                 │
│   Usage         14%                 │
│   Temperature   52.0°C              │
├─────────────────────────────────────┤
│ GPU (NVIDIA)                        │
│   Temperature   61°C                │
│   Usage         23%                 │
├─────────────────────────────────────┤
│ MEMORY (RAM)    Usage  42%          │
│ DISK (C:\)      Usage  68%          │
│ FANS            CPU Fan  1240 RPM   │
│                 Case Fan  890 RPM   │
└──────────────── ⚙ Settings ─────────┘
```

The **system tray icon** (near the Windows clock) permanently displays the room temperature on top and humidity on the bottom — no need to open the dashboard.

---

## ✨ Features

- **Live BLE sensor reading** — connects directly to your Xiaomi sensor over Bluetooth, no Mi Home app needed
- **Full PC stats** — CPU usage, GPU temp & usage (NVIDIA), RAM usage, disk usage
- **Deep hardware sensors** — CPU temperature, disk temperature, RAM temperature, and all fan speeds when [LibreHardwareMonitor](#librehardwaremonitor) is running
- **System tray icon** — always-on, shows temp & humidity drawn directly onto the tray icon
- **Configurable alarm system** — two-tier alert: yellow warning color + red critical color
- **Voice + beep alarm** — when room temp hits critical, plays beep tones and speaks *"Room temperature critical. Please shut down power now."* on a repeating loop using Windows built-in speech (no extra packages)
- **Persistent settings** — alarm thresholds saved to `config.json`, survive restarts
- **Auto-reconnect** — if Bluetooth drops, the widget reconnects automatically every 10 seconds

---

## 🛒 Microsoft Widget Board (Win + W)

> **Status: Roadmap / Future Version**

The current implementation is a **Python desktop app** that lives in the system tray. The Windows 11 Widget Board (`Win + W`) requires widgets to be built as **PWA (Progressive Web App)** packages submitted to the Microsoft Store.

A future version of this project will wrap the dashboard in a WebView2 / Electron shell and publish it to the Microsoft Store under the **PBK-25** developer account so it appears natively in `Win + W`.

**Tracking issue:** `#1 — Package as Win+W Widget`

---

## 🔧 Hardware Requirements

### Tested Sensor
| Property | Value |
|---|---|
| **Model** | Xiaomi Smart Temperature and Humidity Monitor |
| **Broadcast name** | `LYWSD03MMC` |
| **Protocol** | Bluetooth Low Energy (BLE 4.2) |
| **Data UUID** | `ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6` |
| **Data format** | 5 bytes: Temp (2B little-endian ÷100), Humidity (1B), Battery mV (2B little-endian) |
| **Battery** | CR2032 coin cell |
| **Range** | ~10 m line-of-sight |

### PC Requirements
- Windows 10 / 11 with Bluetooth 4.0+ adapter
- NVIDIA GPU (for GPU stats via `nvidia-smi`) — AMD/Intel show N/A
- [LibreHardwareMonitor](#librehardwaremonitor) (optional, for deep sensor data)

---

## 📦 Software Requirements

**Python 3.10 or newer** (tested on Python 3.13)

Install all dependencies with one command:

```powershell
pip install bleak pystray pillow psutil
```

| Package | Purpose |
|---|---|
| `bleak` | Bluetooth Low Energy communication |
| `pystray` | System tray icon |
| `pillow` | Drawing live values onto the tray icon |
| `psutil` | CPU usage, RAM, disk stats |

All other features use **Python standard library** only (`tkinter`, `subprocess`, `winsound`, `json`, `threading`, `asyncio`).

---

## 🚀 Installation & Setup

### 1. Clone the repository

```powershell
git clone https://github.com/PBK-25/TempSensor.git
cd TempSensor
```

### 2. Install dependencies

```powershell
pip install bleak pystray pillow psutil
```

### 3. Find your sensor's MAC address

Run the included scanner to discover all nearby BLE devices:

```powershell
python scanner.py
```

Look for a device named `LYWSD03MMC` in the output. Note its **Address** (e.g. `A4:C1:38:87:3F:10`).

### 4. Set your sensor address

Open `widget.py` and update line 13:

```python
TARGET_ADDRESS = "A4:C1:38:87:3F:10"   # ← replace with your address
```

### 5. Run the widget

```powershell
python widget.py
```

A dashboard window will appear. Click the **X** to minimize it to the system tray — the widget keeps running. Click the tray icon to bring the dashboard back.

---

## 🌡️ LibreHardwareMonitor

CPU temperature, disk temperature, RAM temperature, and fan speeds are **not available on Windows** through standard Python libraries. They require [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) — a free, open-source hardware monitoring tool that exposes sensor data via WMI.

### Setup (one-time)

1. Download the latest release from [github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases)
2. Extract the ZIP and run `LibreHardwareMonitor.exe`
3. In LHM: **Options → Run On Windows Startup** (recommended)
4. Restart `widget.py`

The widget automatically detects LHM and populates all sensor fields. You will see:
```
✓  LibreHardwareMonitor active — full sensor data
```
at the bottom of the dashboard.

---

## ⚙️ Alarm Settings

Click the **⚙ Settings** button in the dashboard to configure:

| Setting | Default | Behaviour |
|---|---|---|
| Room Temp Warning | **40 °C** | Value text turns **yellow** |
| Room Temp Critical | **50 °C** | Value text turns **red** + repeating voice alarm |
| GPU Temp Warning | **80 °C** | Value text turns **yellow** |
| CPU Usage Warning | **90 %** | Value text turns **yellow** |
| RAM Usage Warning | **85 %** | Value text turns **yellow** |
| Sound alarm | **On** | Beep tones + Windows TTS voice |

### Why 40 °C / 50 °C for electrical connections?

The sensor monitors ambient air temperature inside a confined cable management space. Industry guidance for electrical enclosures:
- **40 °C** — airflow is insufficient; inspect the setup
- **50 °C** — danger zone; power bricks and capacitors are being stressed; investigate immediately

---

## 🔌 Adding a Different BLE Temperature Sensor

This widget can be adapted to work with **any BLE temperature sensor** that sends notifications. Follow these steps:

### Step 1 — Discover the device

Run the scanner and note the device **name** and **MAC address**:

```powershell
python scanner.py
```

Update `widget.py`:
```python
TARGET_ADDRESS = "XX:XX:XX:XX:XX:XX"   # your new sensor's address
```

### Step 2 — Find the data characteristic UUID

Every BLE sensor exposes its data through a specific **UUID**. You need to discover which one your sensor uses.

**Option A — Use a BLE Explorer app**
Install **nRF Connect** (Android/iOS) or **BLE Scanner** and connect to your sensor. Look for a characteristic that sends **notifications** (it will have a **N** flag). Copy its full UUID.

**Option B — List all characteristics with Python**

Create a file `discover_uuids.py`:

```python
import asyncio
from bleak import BleakClient

TARGET = "XX:XX:XX:XX:XX:XX"   # your sensor address

async def main():
    async with BleakClient(TARGET) as c:
        for service in c.services:
            print(f"\nService: {service.uuid}")
            for char in service.characteristics:
                print(f"  Char: {char.uuid}  Props: {char.properties}")

asyncio.run(main())
```

Run it and look for a characteristic with `notify` in its properties. That is your `DATA_UUID`.

Update `widget.py`:
```python
DATA_UUID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"   # your UUID
```

### Step 3 — Decode the data bytes

Different sensors encode their data differently. You need to figure out how your sensor's bytes map to temperature and humidity values.

**Option A — Print raw bytes first**

Replace the `notification_handler` in `widget.py` temporarily:

```python
def _ble_notify(sender, raw):
    print(f"Raw bytes ({len(raw)}): {list(raw)} | hex: {raw.hex()}")
```

Run the widget, stand near the sensor, and watch the terminal output. You will see something like:
```
Raw bytes (5): [88, 7, 46, 11, 12] | hex: 0807462b0c
```

**Option B — Decode common formats**

| Format | Byte layout | Decode |
|---|---|---|
| **Xiaomi LYWSD03MMC** | `[T_lo, T_hi, H, B_lo, B_hi]` | `temp = int.from_bytes(data[0:2], 'little') / 100.0` |
| **Govee H5075** | 3-byte encoded | `temp = (int.from_bytes(data[0:3], 'big') / 1000) / 10` |
| **SHT31 / generic** | `[T_hi, T_lo, H_hi, H_lo]` | `temp = int.from_bytes(data[0:2], 'big') * 175 / 65535 - 45` |
| **ATC custom firmware** | See [ATC_MiThermometer](https://github.com/atc1441/ATC_MiThermometer) | Format depends on firmware version |

Once you know the format, update `_ble_notify` in `widget.py`:

```python
def _ble_notify(sender, raw):
    # Example for a sensor that sends temp as 2 big-endian bytes ÷ 10
    sensors["room_temp"] = int.from_bytes(raw[0:2], "big") / 10.0
    sensors["room_hum"]  = raw[2]
    # battery not available on this sensor
    sensors["room_batt"] = None
```

### Step 4 — Rename the label (optional)

In `widget.py`, find the section label and rename it to match your sensor's use case:

```python
s = _make_section(content, "SERVER ROOM TEMP", BLUE)   # was "ELECTRICAL CONNECTIONS"
```

### Tested Compatible Sensors

| Sensor | UUID | Notes |
|---|---|---|
| Xiaomi LYWSD03MMC | `ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6` | Stock firmware — direct connect |
| Xiaomi LYWSD03MMC (ATC firmware) | `00002a6e-0000-1000-8000-00805f9b34fb` | Passive broadcast, no pairing needed |
| Govee H5075 / H5074 | Advertisement data only | No notification UUID — passive scan required |
| Inkbird IBS-TH2 | `0000fff4-0000-1000-8000-00805f9b34fb` | Requires pairing |

---

## 📁 File Structure

```
TempSensor/
├── widget.py           # Main app — run this
├── scanner.py          # BLE device discovery tool
├── xiaomi_monitor.py   # Minimal terminal-only data reader
├── widget_Single.py    # Minimal BLE-only desktop widget (no PC stats)
├── config.json         # Auto-created on first run — stores alarm thresholds
└── README.md           # This file
```

---

## 🛣️ Roadmap

- [ ] **Win+W Widget** — package as PWA for the Microsoft Widget Board
- [ ] **Multi-sensor support** — monitor several rooms simultaneously
- [ ] **Data logging** — CSV export with timestamps
- [ ] **Historical graphs** — 24-hour temperature chart
- [ ] **AMD GPU support** — via `rocm-smi` or WMI
- [ ] **Dark/light theme toggle**

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push and open a Pull Request

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 👤 Author

**PBK-25**
GitHub: [github.com/PBK-25](https://github.com/PBK-25)

---

*Built because Xiaomi makes great sensors but no desktop software.*
