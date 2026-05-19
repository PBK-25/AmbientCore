import asyncio
import threading
import tkinter as tk
from tkinter import messagebox
import psutil
import pystray
import subprocess
import json
import os
import sys
import time
import winsound
from PIL import Image, ImageDraw, ImageFont
from bleak import BleakClient

# ── Constants ──────────────────────────────────────────────────────────────────
TARGET_ADDRESS = "A4:C1:38:87:3F:10"
DATA_UUID      = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"
CONFIG_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CFG = {
    "room_warn":      40.0,
    "room_critical":  50.0,
    "gpu_warn":       80.0,
    "cpu_usage_warn": 90.0,
    "ram_warn":       85.0,
    "sound_alarm":    True,
}

BG     = "#1e1e1e"
PANEL  = "#252526"
BORDER = "#3c3c3c"
DIM    = "#6e6e6e"
WHITE  = "#d4d4d4"
BLUE   = "#4fc3f7"
GREEN  = "#a5d6a7"
ORANGE = "#ffb74d"
RED    = "#ef5350"
YELLOW = "#ffd54f"

# ── Config ─────────────────────────────────────────────────────────────────────
def load_cfg():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                stored = json.load(f)
            out = DEFAULT_CFG.copy()
            out.update(stored)
            return out
        except Exception:
            pass
    return DEFAULT_CFG.copy()

def save_cfg():
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

cfg = load_cfg()

# ── Shared sensor state ────────────────────────────────────────────────────────
sensors = {
    "room_temp":  None,
    "room_hum":   None,
    "room_batt":  None,
    "cpu_usage":  None,
    "cpu_temp":   None,
    "gpu_temp":   None,
    "gpu_usage":  None,
    "ram_usage":  None,
    "ram_temp":   None,
    "disk_usage": None,
    "disk_temp":  None,
    "fans":       {},
    "lhm_active": False,
}

_alarm_active = False
tray_obj      = None

# ── BLE thread ─────────────────────────────────────────────────────────────────
def _ble_notify(sender, raw):
    sensors["room_temp"] = int.from_bytes(raw[0:2], "little") / 100.0
    sensors["room_hum"]  = raw[2]
    if len(raw) >= 5:
        sensors["room_batt"] = int.from_bytes(raw[3:5], "little")

async def _ble_loop():
    while True:
        try:
            async with BleakClient(TARGET_ADDRESS) as c:
                await c.start_notify(DATA_UUID, _ble_notify)
                while True:
                    await asyncio.sleep(1)
        except Exception:
            sensors["room_temp"] = None
            await asyncio.sleep(10)

def run_ble():
    asyncio.run(_ble_loop())

# ── LibreHardwareMonitor WMI query ─────────────────────────────────────────────
# LHM must be running for this to return data.
# Download free from: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor
_LHM_PS = (
    "try {"
    "  $s = Get-WmiObject -Namespace root\\LibreHardwareMonitor -Class Sensor -EA Stop;"
    "  $s | Select-Object Name,Value,SensorType | ConvertTo-Json -Compress"
    "} catch { '' }"
)

def _query_lhm():
    try:
        r = subprocess.run(
            ["powershell", "-NonInteractive", "-Command", _LHM_PS],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        txt = r.stdout.strip()
        if not txt:
            return None
        raw = json.loads(txt)
        return [raw] if isinstance(raw, dict) else raw
    except Exception:
        return None

def _parse_lhm(items):
    out = {"fans": {}}
    cpu_core_temps = []

    for item in items:
        name  = (item.get("Name") or "").strip()
        stype = (item.get("SensorType") or "").strip()
        val   = item.get("Value")
        if val is None:
            continue
        nl = name.lower()

        if stype == "Temperature":
            if "cpu package" in nl:
                out["cpu_temp"] = round(float(val), 1)
            elif "cpu" in nl and "core" in nl:
                cpu_core_temps.append(float(val))
            if "gpu core" in nl:
                out["gpu_temp"] = round(float(val), 1)
            if any(x in nl for x in ("ssd", "hdd", "nvme", "drive", "disk", "storage")):
                out.setdefault("disk_temp", round(float(val), 1))
            if any(x in nl for x in ("memory", "dram", "dimm")):
                out.setdefault("ram_temp", round(float(val), 1))

        elif stype == "Fan":
            rpm = int(float(val))
            if rpm > 0:
                out["fans"][name] = rpm

    # Fall back to hottest core if package sensor not found
    if "cpu_temp" not in out and cpu_core_temps:
        out["cpu_temp"] = round(max(cpu_core_temps), 1)

    return out

# ── Stats thread ───────────────────────────────────────────────────────────────
def run_stats():
    lhm_countdown = 0

    while True:
        # CPU usage + RAM + Disk — always available via psutil
        sensors["cpu_usage"] = psutil.cpu_percent(interval=1)
        sensors["ram_usage"] = psutil.virtual_memory().percent
        try:
            sensors["disk_usage"] = psutil.disk_usage("C:\\").percent
        except Exception:
            sensors["disk_usage"] = None

        # GPU via nvidia-smi
        try:
            r = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=temperature.gpu,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if r.returncode == 0 and r.stdout.strip():
                parts = r.stdout.strip().split(",")
                sensors["gpu_temp"]  = float(parts[0].strip())
                sensors["gpu_usage"] = float(parts[1].strip())
            else:
                sensors["gpu_temp"] = sensors["gpu_usage"] = None
        except Exception:
            sensors["gpu_temp"] = sensors["gpu_usage"] = None

        # LibreHardwareMonitor — poll every ~3 s to keep overhead low
        lhm_countdown -= 1
        if lhm_countdown <= 0:
            lhm_data = _query_lhm()
            if lhm_data:
                parsed = _parse_lhm(lhm_data)
                for key in ("cpu_temp", "disk_temp", "ram_temp", "fans"):
                    if key in parsed:
                        sensors[key] = parsed[key]
                # Use LHM GPU temp if nvidia-smi gave nothing
                if sensors["gpu_temp"] is None and "gpu_temp" in parsed:
                    sensors["gpu_temp"] = parsed["gpu_temp"]
                sensors["lhm_active"] = True
                lhm_countdown = 3
            else:
                sensors["cpu_temp"]   = None
                sensors["disk_temp"]  = None
                sensors["ram_temp"]   = None
                sensors["fans"]       = {}
                sensors["lhm_active"] = False
                lhm_countdown = 10  # back off when LHM is not running

# ── Alarm — continuous beep + voice loop ───────────────────────────────────────
_alarm_active = False

def _tts(text):
    """Speak text via Windows built-in speech synthesis. No extra packages needed."""
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Speak('{text}')"
    )
    try:
        subprocess.run(
            ["powershell", "-NonInteractive", "-Command", ps],
            capture_output=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass

def _alarm_worker():
    global _alarm_active
    while _alarm_active:
        # Beep Beep Beep
        for _ in range(3):
            if not _alarm_active:
                return
            try:
                winsound.Beep(1000, 350)
            except Exception:
                pass
            time.sleep(0.12)

        if not _alarm_active:
            return

        # Voice announcement
        _tts("Room temperature critical. Please shut down power now.")

        if not _alarm_active:
            return

        # Beep Beep Beep
        for _ in range(3):
            if not _alarm_active:
                return
            try:
                winsound.Beep(1000, 350)
            except Exception:
                pass
            time.sleep(0.12)

        # 8-second pause before repeating — check flag every 100 ms so it stops fast
        for _ in range(80):
            if not _alarm_active:
                return
            time.sleep(0.1)

def _trigger_alarm():
    global _alarm_active
    if not _alarm_active:
        _alarm_active = True
        threading.Thread(target=_alarm_worker, daemon=True).start()

def _clear_alarm():
    global _alarm_active
    _alarm_active = False

# ── Tray icon — draws live temp + humidity on the icon ─────────────────────────
def _tray_image():
    img  = Image.new("RGBA", (64, 64), (30, 30, 30, 255))
    draw = ImageDraw.Draw(img)
    try:
        fnt_big = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
        fnt_sm  = ImageFont.truetype("C:/Windows/Fonts/arial.ttf",   16)
    except Exception:
        fnt_big = fnt_sm = ImageFont.load_default()

    t = sensors["room_temp"]
    h = sensors["room_hum"]
    draw.text((32, 17), f"{t:.0f}°" if t is not None else "---",
              fill=(79, 195, 247), font=fnt_big, anchor="mm")
    draw.text((32, 47), f"{h}%" if h is not None else "--",
              fill=(165, 214, 167), font=fnt_sm, anchor="mm")
    return img

def _refresh_tray():
    if tray_obj is None:
        return
    tray_obj.icon = _tray_image()
    t = sensors["room_temp"]
    h = sensors["room_hum"]
    tray_obj.title = (
        f"{t:.1f}°C  ·  {h}%"
        if t is not None and h is not None
        else "Connecting…"
    )

def run_tray():
    global tray_obj
    menu = pystray.Menu(
        pystray.MenuItem(
            "Open Dashboard",
            lambda i, it: root.after(0, _show_dashboard),
            default=True,
        ),
        pystray.MenuItem("Exit", lambda i, it: root.after(0, _exit_app)),
    )
    tray_obj = pystray.Icon("ClimateMonitor", _tray_image(), "Connecting…", menu)
    tray_obj.run()

def _show_dashboard():
    root.deiconify()
    root.lift()
    root.focus_force()

def _exit_app():
    _clear_alarm()
    if tray_obj:
        tray_obj.stop()
    root.destroy()
    sys.exit(0)

# ── Shared GUI helpers ─────────────────────────────────────────────────────────
def _alarm_color(val, default, warn_key, crit_key=None):
    if val is None or warn_key not in cfg:
        return default
    if crit_key and val >= cfg[crit_key]:
        return RED
    if val >= cfg[warn_key]:
        return YELLOW
    return default

def _make_section(parent, title, accent):
    frame = tk.Frame(parent, bg=BG)
    frame.pack(fill="x", pady=(8, 0))
    tk.Frame(frame, bg=accent, height=2).pack(fill="x")
    tk.Label(frame, text=title, font=("Segoe UI", 8, "bold"),
             fg=accent, bg=BG).pack(anchor="w", pady=(2, 0))
    body = tk.Frame(frame, bg=BG)
    body.pack(fill="x")
    return body

def _make_row(parent, label_text, default_color):
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x", pady=1)
    tk.Label(row, text=label_text, font=("Segoe UI", 9),
             fg=DIM, bg=BG, width=16, anchor="w").pack(side="left")
    lbl = tk.Label(row, text="---", font=("Segoe UI", 9, "bold"),
                   fg=default_color, bg=BG, anchor="w")
    lbl.pack(side="left")
    return lbl

# ── Dashboard ──────────────────────────────────────────────────────────────────
class Dashboard:
    def __init__(self, master):
        self.root = master
        master.title("System & Climate Monitor")
        master.geometry("400x680")
        master.configure(bg=BG)
        master.resizable(False, False)
        master.attributes("-topmost", True)
        master.protocol("WM_DELETE_WINDOW", master.withdraw)
        self._build()
        self._tick()

    def _build(self):
        tk.Label(self.root, text="SYSTEM & CLIMATE MONITOR",
                 font=("Segoe UI", 11, "bold"), fg=BLUE, bg=BG).pack(pady=(12, 2))
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=12, pady=4)

        content = tk.Frame(self.root, bg=BG)
        content.pack(fill="both", expand=True, padx=12)

        # Electrical Connections — Xiaomi sensor
        s = _make_section(content, "ELECTRICAL CONNECTIONS", BLUE)
        self.e_temp = _make_row(s, "Temperature", BLUE)
        self.e_hum  = _make_row(s, "Humidity",    GREEN)
        self.e_batt = _make_row(s, "Battery",     DIM)

        # CPU
        s = _make_section(content, "CPU", ORANGE)
        self.cpu_usage = _make_row(s, "Usage",       ORANGE)
        self.cpu_temp  = _make_row(s, "Temperature", ORANGE)

        # GPU
        s = _make_section(content, "GPU (NVIDIA)", RED)
        self.gpu_temp  = _make_row(s, "Temperature", RED)
        self.gpu_usage = _make_row(s, "Usage",       RED)

        # RAM
        s = _make_section(content, "MEMORY (RAM)", GREEN)
        self.ram_usage = _make_row(s, "Usage",       GREEN)
        self.ram_temp  = _make_row(s, "Temperature", DIM)

        # Disk
        s = _make_section(content, "DISK  (C:\\)", YELLOW)
        self.disk_usage = _make_row(s, "Usage",       YELLOW)
        self.disk_temp  = _make_row(s, "Temperature", DIM)

        # Fans
        self.fan_body = _make_section(content, "FANS", DIM)
        self.fan_rows = {}

        # LHM status notice (always visible, text changes)
        self.lhm_lbl = tk.Label(
            content,
            text="",
            font=("Segoe UI", 8), fg=DIM, bg=BG,
            wraplength=370, justify="left",
        )
        self.lhm_lbl.pack(anchor="w", pady=(10, 0))

        # Status bar + settings button
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=12, pady=(4, 10))
        self.status_lbl = tk.Label(bar, text="Connecting…",
                                   font=("Segoe UI", 8), fg=DIM, bg=BG)
        self.status_lbl.pack(side="left")
        tk.Button(bar, text="⚙  Settings", font=("Segoe UI", 9),
                  bg=PANEL, fg=WHITE, relief="flat",
                  activebackground=BORDER, activeforeground=WHITE,
                  padx=8, pady=3, cursor="hand2",
                  command=lambda: SettingsWindow(self.root)).pack(side="right")

    def _tick(self):
        self._refresh()
        _refresh_tray()
        self.root.after(1000, self._tick)

    def _refresh(self):
        s = sensors

        # ── Electrical Connections ──
        room_t = s["room_temp"]
        room_h = s["room_hum"]
        room_b = s["room_batt"]

        if room_t is not None:
            tc = _alarm_color(room_t, BLUE, "room_warn", "room_critical")
            self.e_temp.config(text=f"{room_t:.1f}°C", fg=tc)
            self.status_lbl.config(text="● Connected", fg=GREEN)
            if room_t >= cfg["room_critical"] and cfg.get("sound_alarm", True):
                _trigger_alarm()
            else:
                _clear_alarm()
        else:
            self.e_temp.config(text="Reconnecting…", fg=DIM)
            self.status_lbl.config(text="● Reconnecting", fg=DIM)
            _clear_alarm()

        self.e_hum.config(text=f"{room_h}%" if room_h is not None else "---")
        if room_b is not None:
            pct = max(0, min(100, int((room_b - 2500) / 600 * 100)))
            self.e_batt.config(text=f"{room_b} mV  (~{pct}%)")

        # ── CPU ──
        cu = s["cpu_usage"]
        self.cpu_usage.config(
            text=f"{cu:.0f}%" if cu is not None else "---",
            fg=_alarm_color(cu, ORANGE, "cpu_usage_warn"),
        )
        ct = s["cpu_temp"]
        self.cpu_temp.config(
            text=f"{ct:.1f}°C" if ct is not None else "N/A",
            fg=ORANGE if ct is not None else DIM,
        )

        # ── GPU ──
        gt = s["gpu_temp"]
        self.gpu_temp.config(
            text=f"{gt:.0f}°C" if gt is not None else "N/A",
            fg=_alarm_color(gt, RED, "gpu_warn") if gt is not None else DIM,
        )
        gu = s["gpu_usage"]
        self.gpu_usage.config(text=f"{gu:.0f}%" if gu is not None else "N/A")

        # ── RAM ──
        ru = s["ram_usage"]
        self.ram_usage.config(
            text=f"{ru:.0f}%" if ru is not None else "---",
            fg=_alarm_color(ru, GREEN, "ram_warn"),
        )
        ram_t = s["ram_temp"]
        self.ram_temp.config(
            text=f"{ram_t:.1f}°C" if ram_t is not None else "N/A",
            fg=WHITE if ram_t is not None else DIM,
        )

        # ── Disk ──
        du = s["disk_usage"]
        self.disk_usage.config(text=f"{du:.0f}%" if du is not None else "---")
        disk_t = s["disk_temp"]
        self.disk_temp.config(
            text=f"{disk_t:.0f}°C" if disk_t is not None else "N/A",
            fg=WHITE if disk_t is not None else DIM,
        )

        # ── Fans ──
        fans = s["fans"]
        for name in list(self.fan_rows):
            if name not in fans and name != "__none__":
                self.fan_rows[name][0].destroy()
                del self.fan_rows[name]

        if fans:
            if "__none__" in self.fan_rows:
                self.fan_rows["__none__"][0].destroy()
                del self.fan_rows["__none__"]
            for name, rpm in fans.items():
                if name not in self.fan_rows:
                    f = tk.Frame(self.fan_body, bg=BG)
                    f.pack(fill="x", pady=1)
                    tk.Label(f, text=name[:16], font=("Segoe UI", 9),
                             fg=DIM, bg=BG, width=16, anchor="w").pack(side="left")
                    lbl = tk.Label(f, text=f"{rpm} RPM",
                                   font=("Segoe UI", 9, "bold"), fg=WHITE, bg=BG)
                    lbl.pack(side="left")
                    self.fan_rows[name] = (f, lbl)
                else:
                    self.fan_rows[name][1].config(text=f"{rpm} RPM")
        else:
            if "__none__" not in self.fan_rows:
                f = tk.Frame(self.fan_body, bg=BG)
                f.pack(fill="x", pady=1)
                lbl = tk.Label(f, text="N/A  (requires LibreHardwareMonitor)",
                               font=("Segoe UI", 9), fg=DIM, bg=BG)
                lbl.pack(anchor="w")
                self.fan_rows["__none__"] = (f, lbl)

        # ── LHM notice ──
        if s["lhm_active"]:
            self.lhm_lbl.config(
                text="✓  LibreHardwareMonitor active — full sensor data",
                fg="#3c7a3c",
            )
        else:
            self.lhm_lbl.config(
                text=(
                    "ℹ  CPU / RAM / Disk temps and fan speeds require LibreHardwareMonitor.\n"
                    "    Download free from github.com/LibreHardwareMonitor — just run it."
                ),
                fg="#6a6a9a",
            )


# ── Settings window ────────────────────────────────────────────────────────────
class SettingsWindow:
    def __init__(self, parent):
        self.w = tk.Toplevel(parent)
        self.w.title("Alarm Settings")
        self.w.geometry("340x390")
        self.w.configure(bg=BG)
        self.w.attributes("-topmost", True)
        self.w.resizable(False, False)
        self.w.grab_set()
        self._build()

    def _build(self):
        tk.Label(self.w, text="ALARM THRESHOLDS",
                 font=("Segoe UI", 10, "bold"), fg=BLUE, bg=BG).pack(pady=(12, 4))
        tk.Frame(self.w, bg=BORDER, height=1).pack(fill="x", padx=14, pady=4)

        fields = [
            ("Room Temp — Warning (°C)",  "room_warn",      YELLOW),
            ("Room Temp — Critical (°C)", "room_critical",  RED),
            ("GPU Temp — Warning (°C)",   "gpu_warn",       RED),
            ("CPU Usage — Warning (%)",   "cpu_usage_warn", ORANGE),
            ("RAM Usage — Warning (%)",   "ram_warn",       GREEN),
        ]
        self.vars = {}
        for label, key, color in fields:
            row = tk.Frame(self.w, bg=BG)
            row.pack(fill="x", padx=16, pady=5)
            tk.Label(row, text=label, font=("Segoe UI", 9),
                     fg=color, bg=BG, width=28, anchor="w").pack(side="left")
            v = tk.StringVar(value=str(cfg[key]))
            tk.Entry(row, textvariable=v, width=7,
                     bg=PANEL, fg=WHITE, insertbackground=WHITE,
                     relief="flat").pack(side="left", padx=4)
            self.vars[key] = v

        self.sound_var = tk.BooleanVar(value=cfg.get("sound_alarm", True))
        tk.Checkbutton(
            self.w,
            text="Enable voice + beep alarm at Critical temp",
            variable=self.sound_var,
            font=("Segoe UI", 9), fg=WHITE, bg=BG,
            selectcolor=PANEL, activebackground=BG, activeforeground=WHITE,
        ).pack(anchor="w", padx=16, pady=(8, 0))

        tk.Label(self.w,
                 text="Warning → yellow   │   Critical → red + repeating voice alarm",
                 font=("Segoe UI", 8), fg=DIM, bg=BG).pack(pady=(4, 0))

        tk.Button(self.w, text="Save", font=("Segoe UI", 9, "bold"),
                  bg=BLUE, fg="#000", relief="flat", padx=16, pady=4,
                  cursor="hand2", command=self._save).pack(pady=(14, 8))

    def _save(self):
        try:
            vals = {k: float(v.get()) for k, v in self.vars.items()}
        except ValueError:
            messagebox.showerror("Invalid Input", "All values must be numbers.", parent=self.w)
            return
        if vals["room_warn"] >= vals["room_critical"]:
            messagebox.showerror(
                "Invalid Input", "Warning must be less than Critical.", parent=self.w
            )
            return
        cfg.update(vals)
        cfg["sound_alarm"] = self.sound_var.get()
        save_cfg()
        self.w.destroy()


# ── Entry point ────────────────────────────────────────────────────────────────
root = tk.Tk()
root.withdraw()

dashboard = Dashboard(root)
root.deiconify()

threading.Thread(target=run_ble,   daemon=True).start()
threading.Thread(target=run_stats, daemon=True).start()
threading.Thread(target=run_tray,  daemon=True).start()

root.mainloop()
