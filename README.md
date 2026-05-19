# AmbientCore

> Always-on Windows 11 tray widget that unifies live BLE environment sensors with full PC hardware monitoring — dark mode, voice alarms, zero cloud.

Built with Python · Bluetooth Low Energy · No cloud · No subscription · No data leaves your machine.

---

## What It Does

AmbientCore sits quietly in your Windows system tray and gives you two things at a glance:

- **Your environment** — live temperature and humidity from a Bluetooth sensor (tested with Xiaomi LYWSD03MMC, adaptable to any BLE sensor)
- **Your hardware** — CPU, GPU, RAM, disk, and fan data pulled directly from your PC

Click the tray icon to open the full dark-mode dashboard. Close the dashboard and it keeps running in the background. AmbientCore can start automatically with Windows and requires no terminal once installed.

---

## What It Looks Like

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

The **system tray icon** near the Windows clock shows room temperature on top and humidity below — drawn live onto the icon itself, no need to open the dashboard for a quick check.

---

## Features

- **Live BLE sensor** — reads directly from your Bluetooth sensor over BLE, no vendor app needed
- **Full PC stats** — CPU usage, GPU temperature & usage (NVIDIA), RAM usage, disk usage
- **Deep hardware sensors** — CPU temp, disk temp, RAM temp, and fan speeds when [LibreHardwareMonitor](#librehardwaremonitor--for-deep-sensor-data) is running
- **Custom app icon** — thermometer + humidity droplet icon at 7 sizes (16–256 px), shown in the taskbar, title bar, and desktop shortcut
- **System tray icon** — always-on, live values drawn directly onto the icon graphic
- **Two-tier alarm system** — configurable warning (yellow) and critical (red) thresholds per sensor
- **Repeating voice + beep alarm** — on critical room temperature: three beep tones → spoken alert via Windows built-in speech → three beep tones → 8-second pause → repeats until temperature drops
- **CSV data logging** — all sensor readings written to daily CSV files (`AmbientCore_YYYY-MM-DD.csv`) every 30 seconds, stored next to the app
- **24-hour temperature graph** — matplotlib chart showing the last 24 hours of room temperature with warning/critical threshold lines; opens from the dashboard or tray menu; auto-refreshes every 60 seconds
- **Light theme** — switch between dark and light colour schemes from Settings; takes effect instantly without restarting
- **Persistent settings** — alarm thresholds and theme saved to `config.json`, survive restarts
- **Auto-reconnect** — recovers automatically if Bluetooth drops, retries every 10 seconds
- **Windows startup** — optional auto-start with Windows via registry (no admin rights needed)
- **Standalone EXE** — can be compiled to a self-contained executable with no Python requirement

---

## Hardware Requirements

### Tested Sensor — Xiaomi LYWSD03MMC

| Property | Value |
|---|---|
| **Model** | Xiaomi Smart Temperature and Humidity Monitor |
| **Broadcast name** | `LYWSD03MMC` |
| **Protocol** | Bluetooth Low Energy (BLE 4.2) |
| **Data UUID** | `ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6` |
| **Data format** | 5 bytes — Temp (2B little-endian ÷100), Humidity (1B), Battery mV (2B little-endian) |
| **Battery** | CR2032 coin cell |

### PC Requirements

- Windows 10 / 11 with Bluetooth 4.0+ adapter
- NVIDIA GPU for GPU stats via `nvidia-smi` (AMD/Intel show N/A)
- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) — optional, unlocks CPU temp, disk temp, RAM temp, and fan speeds

---

## Installation

### Option A — Python (recommended for development)

**1. Clone**
```powershell
git clone https://github.com/PBK-25/AmbientCore.git
cd AmbientCore
```

**2. Install dependencies**
```powershell
pip install bleak pystray pillow psutil matplotlib
```

| Package | Purpose |
|---|---|
| `bleak` | Bluetooth Low Energy |
| `pystray` | System tray icon |
| `pillow` | Drawing live values onto the tray icon + icon generation |
| `psutil` | CPU, RAM, disk stats |
| `matplotlib` | 24-hour temperature graph |

Everything else (`tkinter`, `winsound`, `subprocess`, `asyncio`, `csv`) is Python standard library.

**3. Find your sensor's MAC address**
```powershell
python scanner.py
```
Look for your device in the list and note its **Address** (e.g. `A4:C1:38:87:3F:10`).

**4. Set your sensor address**

Open `widget.py` and update line 17:
```python
TARGET_ADDRESS = "A4:C1:38:87:3F:10"   # ← your sensor's address
```

**5. Run the one-time setup** (generates icon, adds to startup, creates desktop shortcut)
```powershell
python install.py
```

**6. Run**
```powershell
python widget.py
```

> From now on use the Desktop shortcut or let Windows start it automatically on boot.

---

### Option B — Standalone EXE (no Python required to run)

**1. Build the exe** (only needs to be done once, requires Python + PyInstaller)
```powershell
pip install pyinstaller
python build_exe.py
```

Output: `dist\AmbientCore\AmbientCore.exe`

**2. Run the exe**

Double-click `AmbientCore.exe`. On first launch, a dialog asks if you want to add it to Windows startup and create a desktop shortcut — click **Yes** and it sets itself up automatically.

> You can share the entire `dist\AmbientCore\` folder with anyone on Windows — no Python installation needed.

---

## LibreHardwareMonitor — for Deep Sensor Data

CPU temperature, disk temperature, RAM temperature, and fan speeds are **not exposed by Windows** through standard Python APIs (`psutil` sensor support is Linux-only). [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) bridges that gap by publishing all sensor data via WMI, which AmbientCore queries automatically when it detects LHM is running.

**Setup (one-time):**

1. Download the latest release from the [LHM releases page](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases)
2. Extract and run `LibreHardwareMonitor.exe`
3. Recommended: **Options → Run On Windows Startup**
4. Restart AmbientCore

When LHM is active, the dashboard footer shows:
```
✓  LibreHardwareMonitor active — full sensor data
```
When it is not running, the footer shows a reminder with a link.

---

## Alarm Settings

Click **⚙ Settings** in the dashboard to configure:

| Threshold | Default | Effect |
|---|---|---|
| Room Temp — Warning | 40 °C | Value turns **yellow** |
| Room Temp — Critical | 50 °C | Value turns **red** + repeating voice alarm |
| GPU Temp — Warning | 80 °C | Value turns **yellow** |
| CPU Usage — Warning | 90 % | Value turns **yellow** |
| RAM Usage — Warning | 85 % | Value turns **yellow** |

**Alarm pattern (repeats until temp drops):**
```
Beep Beep Beep  →  "Room temperature critical. Please shut down power now."  →  Beep Beep Beep  →  8s pause  →  ...
```

Voice uses Windows' built-in speech synthesis — no extra packages or internet required.

> **Why 40 / 50 °C?** These defaults are designed for monitoring ambient air inside a confined cable management space. 40 °C signals poor airflow; 50 °C means power bricks and capacitors are under thermal stress and the setup should be investigated immediately.

---

## Adding a Different BLE Sensor

AmbientCore works with any BLE sensor that sends data via notifications. Here is how to adapt it.

### Step 1 — Discover the device

```powershell
python scanner.py
```

Update `widget.py`:
```python
TARGET_ADDRESS = "XX:XX:XX:XX:XX:XX"
```

### Step 2 — Find the data UUID

**Option A — Mobile app**
Use **nRF Connect** (Android/iOS) or **BLE Scanner**. Connect to your sensor and look for a characteristic with an **N** (Notify) flag. That UUID is what you need.

**Option B — Python script**
```python
import asyncio
from bleak import BleakClient

TARGET = "XX:XX:XX:XX:XX:XX"

async def main():
    async with BleakClient(TARGET) as c:
        for service in c.services:
            print(f"\nService: {service.uuid}")
            for char in service.characteristics:
                print(f"  Char: {char.uuid}  Props: {char.properties}")

asyncio.run(main())
```

Update `widget.py`:
```python
DATA_UUID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Step 3 — Decode the bytes

Temporarily replace `_ble_notify` in `widget.py` to print raw bytes:
```python
def _ble_notify(sender, raw):
    print(f"Raw ({len(raw)} bytes): {list(raw)}  hex: {raw.hex()}")
```

Once you know the byte layout, update the decoder:
```python
# Example — 2-byte big-endian temperature ÷ 10, 1-byte humidity
def _ble_notify(sender, raw):
    sensors["room_temp"] = int.from_bytes(raw[0:2], "big") / 10.0
    sensors["room_hum"]  = raw[2]
    sensors["room_batt"] = None
```

### Common sensor byte formats

| Sensor | Byte layout | Decode |
|---|---|---|
| **Xiaomi LYWSD03MMC** | `[T_lo, T_hi, H, B_lo, B_hi]` | `int.from_bytes(data[0:2], 'little') / 100.0` |
| **Xiaomi LYWSD03MMC (ATC firmware)** | UUID `00002a6e-…` | `int.from_bytes(data[0:2], 'big') / 100.0` |
| **Govee H5075 / H5074** | Advertisement data | Passive scan only — no notify UUID |
| **Inkbird IBS-TH2** | UUID `0000fff4-…` | Requires pairing first |
| **SHT31 / generic SHT sensor** | `[T_hi, T_lo, H_hi, H_lo]` | `int.from_bytes(data[0:2], 'big') * 175 / 65535 - 45` |

### Step 4 — Rename the section label (optional)

```python
s = _make_section(content, "SERVER ROOM", BLUE)   # rename from "ELECTRICAL CONNECTIONS"
```

---

## File Structure

```
AmbientCore/
├── widget.py           # Main app — run this
├── install.py          # One-time setup: icon + startup + desktop shortcut
├── build_exe.py        # Builds a standalone AmbientCore.exe via PyInstaller
├── icon.ico            # App icon (7 sizes: 16–256 px)
├── scanner.py          # BLE device discovery utility
├── xiaomi_monitor.py   # Minimal terminal-only data reader
├── widget_Single.py    # Minimal BLE-only widget (no PC stats)
└── README.md
```

> `config.json` and `dist/` are excluded from the repo via `.gitignore` — they are generated locally.

---

## Removing from Startup

```powershell
python install.py --uninstall
```

---

## CSV Data Logging

AmbientCore writes all sensor readings to a daily CSV file every 30 seconds:

```
AmbientCore_2026-05-20.csv
```

Columns: `timestamp, room_temp, room_hum, room_batt_mv, cpu_usage, cpu_temp, gpu_temp, gpu_usage, ram_usage, disk_usage`

Files are stored in the same folder as the app (or exe). Click **Open Log Folder** in the graph window to open that location directly in Explorer.

---

## 24-Hour Temperature Graph

Click **Graph** in the dashboard bottom bar (or **24h Graph** in the tray menu) to open a matplotlib chart of the last 24 hours of room temperature. The chart:

- Merges on-disk CSV history with the current session's in-memory buffer
- Shows dashed warning and critical threshold lines
- Auto-refreshes every 60 seconds
- Adapts colours to the active dark/light theme

---

## Light Theme

Open **⚙ Settings** and choose **Dark** or **Light** under the Theme section. The dashboard rebuilds instantly — no restart required.

---

## Roadmap

- [ ] Win+W Widget Board support (PWA / Microsoft Store)
- [ ] Multi-sensor support — monitor several rooms at once
- [ ] AMD GPU support via WMI

---

## Contributing

Pull requests are welcome. For major changes please open an issue first.

```bash
git checkout -b feature/my-feature
git commit -m "Add my feature"
# open a pull request
```

---

## License

**AmbientCore Non-Commercial License**

Free to use, copy, modify, and share for **personal and non-commercial purposes**.
Commercial use of any kind requires prior written permission from the author.

See [`LICENSE`](LICENSE) for the full terms.

---

*Made by [PBK-25](https://github.com/PBK-25)*
