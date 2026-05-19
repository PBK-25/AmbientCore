# AmbientCore

> Always-on Windows 11 tray widget that unifies live BLE environment sensors with full PC hardware monitoring — dark mode, voice alarms, zero cloud.

Built with Python · Bluetooth Low Energy · No cloud · No subscription · No data leaves your machine.

---

## What It Does

AmbientCore sits quietly in your Windows system tray and gives you two things at a glance:

- **Your environment** — live temperature and humidity from a Bluetooth sensor (tested with Xiaomi LYWSD03MMC, adaptable to any BLE sensor)
- **Your hardware** — CPU, GPU, RAM, disk, and fan data pulled directly from your PC

Click the tray icon to open the full dark-mode dashboard. Close the dashboard and it keeps running in the background.

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

The **system tray icon** near the Windows clock shows the room temperature on top and humidity below — no need to open the dashboard for a quick check.

---

## Features

- **Live BLE sensor** — reads directly from your Bluetooth sensor, no vendor app needed
- **Full PC stats** — CPU usage, GPU temperature & usage (NVIDIA), RAM usage, disk usage
- **Deep hardware sensors** — CPU temp, disk temp, RAM temp, and fan speeds when [LibreHardwareMonitor](#librehardwaremonitor-for-deep-sensor-data) is running
- **System tray icon** — always-on, live values drawn directly onto the icon graphic
- **Two-tier alarm system** — configurable warning (yellow) and critical (red) thresholds for every sensor
- **Voice + beep alarm** — on critical room temperature, plays repeating beep tones followed by a spoken alert using Windows built-in speech synthesis
- **Persistent settings** — alarm thresholds survive restarts via `config.json`
- **Auto-reconnect** — recovers automatically if Bluetooth drops

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
- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) — optional, enables CPU temp, disk temp, RAM temp, and fan speeds

---

## Installation

### 1. Clone

```powershell
git clone https://github.com/PBK-25/AmbientCore.git
cd AmbientCore
```

### 2. Install dependencies

```powershell
pip install bleak pystray pillow psutil
```

| Package | Purpose |
|---|---|
| `bleak` | Bluetooth Low Energy |
| `pystray` | System tray icon |
| `pillow` | Drawing values onto the tray icon |
| `psutil` | CPU, RAM, disk stats |

Everything else (`tkinter`, `winsound`, `subprocess`, `asyncio`) is Python standard library.

### 3. Find your sensor's address

```powershell
python scanner.py
```

Look for your device in the list. Note its **Address** (e.g. `A4:C1:38:87:3F:10`).

### 4. Set your sensor address

Open `widget.py` and update line 13:

```python
TARGET_ADDRESS = "A4:C1:38:87:3F:10"   # ← your sensor's address
```

### 5. Run

```powershell
python widget.py
```

---

## LibreHardwareMonitor — for Deep Sensor Data

CPU temperature, disk temperature, RAM temperature, and fan speeds are not exposed by Windows through standard APIs. [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) bridges that gap by publishing all sensor data via WMI, which AmbientCore queries automatically.

**Setup (one-time):**

1. Download the latest release from the [LHM releases page](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases)
2. Extract and run `LibreHardwareMonitor.exe`
3. Optional: **Options → Run On Windows Startup**
4. Restart `widget.py`

When LHM is active, the dashboard footer shows:
```
✓  LibreHardwareMonitor active — full sensor data
```

---

## Alarm Settings

Open **⚙ Settings** in the dashboard to configure:

| Threshold | Default | Effect |
|---|---|---|
| Room Temp — Warning | 40 °C | Text turns yellow |
| Room Temp — Critical | 50 °C | Text turns red + repeating voice alarm |
| GPU Temp — Warning | 80 °C | Text turns yellow |
| CPU Usage — Warning | 90 % | Text turns yellow |
| RAM Usage — Warning | 85 % | Text turns yellow |

**Alarm pattern:** three beep tones → *"Room temperature critical. Please shut down power now."* → three beep tones → 8-second pause → repeats until temperature drops below critical.

> **Why 40 / 50 °C?** These thresholds are designed for monitoring ambient air inside a confined cable management space. 40 °C signals poor airflow; 50 °C means components are under thermal stress and should be investigated immediately.

---

## Adding a Different BLE Sensor

AmbientCore works with any BLE sensor that sends data via notifications. Here is how to adapt it to a new device.

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

Look for a characteristic with `notify` in its properties. Update `widget.py`:

```python
DATA_UUID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Step 3 — Decode the bytes

Temporarily replace `_ble_notify` in `widget.py` to print raw bytes:

```python
def _ble_notify(sender, raw):
    print(f"Raw ({len(raw)} bytes): {list(raw)}  hex: {raw.hex()}")
```

Run the widget and watch the output while the sensor updates. Once you know the byte layout, decode it:

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
├── scanner.py          # BLE device discovery
├── xiaomi_monitor.py   # Minimal terminal-only reader
├── widget_Single.py    # Minimal BLE-only widget (no PC stats)
├── config.json         # Auto-created — stores alarm thresholds
└── README.md
```

---

## Roadmap

- [ ] Win+W Widget Board support (PWA / Microsoft Store)
- [ ] Multi-sensor support — monitor several rooms at once
- [ ] CSV data logging with timestamps
- [ ] 24-hour temperature graph
- [ ] AMD GPU support via WMI
- [ ] Light theme option

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
