import asyncio
import ctypes
import csv
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
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

if getattr(sys, "frozen", False):
    _DIR    = os.path.dirname(sys.executable)
    _BUNDLE = sys._MEIPASS
else:
    _DIR    = os.path.dirname(os.path.abspath(__file__))
    _BUNDLE = _DIR

CONFIG_FILE = os.path.join(_DIR,    "config.json")
ICON_PATH   = os.path.join(_BUNDLE, "icon.ico")
LOG_DIR     = _DIR

DEFAULT_CFG = {
    "room_warn":      40.0,
    "room_critical":  50.0,
    "gpu_warn":       80.0,
    "cpu_usage_warn": 90.0,
    "ram_warn":       85.0,
    "sound_alarm":    True,
    "theme":          "dark",
}

# ── Theme ──────────────────────────────────────────────────────────────────────
_DARK = {
    "BG":     "#1e1e1e",
    "PANEL":  "#252526",
    "BORDER": "#3c3c3c",
    "DIM":    "#6e6e6e",
    "WHITE":  "#d4d4d4",
    "BLUE":   "#4fc3f7",
    "GREEN":  "#a5d6a7",
    "ORANGE": "#ffb74d",
    "RED":    "#ef5350",
    "YELLOW": "#ffd54f",
}
_LIGHT = {
    "BG":     "#f5f5f5",
    "PANEL":  "#e8e8e8",
    "BORDER": "#bdbdbd",
    "DIM":    "#757575",
    "WHITE":  "#212121",
    "BLUE":   "#0288d1",
    "GREEN":  "#388e3c",
    "ORANGE": "#e64a19",
    "RED":    "#c62828",
    "YELLOW": "#f57f17",
}

BG = PANEL = BORDER = DIM = WHITE = BLUE = GREEN = ORANGE = RED = YELLOW = ""

def _load_theme():
    global BG, PANEL, BORDER, DIM, WHITE, BLUE, GREEN, ORANGE, RED, YELLOW
    t  = _DARK if cfg.get("theme", "dark") == "dark" else _LIGHT
    BG     = t["BG"]
    PANEL  = t["PANEL"]
    BORDER = t["BORDER"]
    DIM    = t["DIM"]
    WHITE  = t["WHITE"]
    BLUE   = t["BLUE"]
    GREEN  = t["GREEN"]
    ORANGE = t["ORANGE"]
    RED    = t["RED"]
    YELLOW = t["YELLOW"]

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
_load_theme()

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

# ── CSV logging ────────────────────────────────────────────────────────────────
_LOG_FIELDS = [
    "timestamp", "room_temp", "room_hum", "room_batt_mv",
    "cpu_usage", "cpu_temp", "gpu_temp", "gpu_usage",
    "ram_usage", "disk_usage",
]
_24h_buffer = []   # list of (datetime, float) for room_temp
_24h_lock   = threading.Lock()


def _fmt(v):
    if v is None:
        return ""
    return f"{v:.2f}" if isinstance(v, float) else str(v)


def _log_reading():
    if sensors["room_temp"] is None:
        return
    now      = datetime.now()
    log_path = os.path.join(LOG_DIR, f"AmbientCore_{now.strftime('%Y-%m-%d')}.csv")
    new_file = not os.path.exists(log_path)

    row = {
        "timestamp":    now.strftime("%Y-%m-%d %H:%M:%S"),
        "room_temp":    _fmt(sensors["room_temp"]),
        "room_hum":     _fmt(sensors["room_hum"]),
        "room_batt_mv": _fmt(sensors["room_batt"]),
        "cpu_usage":    _fmt(sensors["cpu_usage"]),
        "cpu_temp":     _fmt(sensors["cpu_temp"]),
        "gpu_temp":     _fmt(sensors["gpu_temp"]),
        "gpu_usage":    _fmt(sensors["gpu_usage"]),
        "ram_usage":    _fmt(sensors["ram_usage"]),
        "disk_usage":   _fmt(sensors["disk_usage"]),
    }
    try:
        with open(log_path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=_LOG_FIELDS)
            if new_file:
                w.writeheader()
            w.writerow(row)
    except Exception:
        pass

    cutoff = now - timedelta(hours=24)
    with _24h_lock:
        _24h_buffer.append((now, sensors["room_temp"]))
        while _24h_buffer and _24h_buffer[0][0] < cutoff:
            _24h_buffer.pop(0)


def _load_csv_history():
    """Read yesterday + today CSV files; return sorted list of (datetime, float) tuples."""
    now    = datetime.now()
    cutoff = now - timedelta(hours=24)
    results = []
    for delta in (1, 0):
        day  = now - timedelta(days=delta)
        path = os.path.join(LOG_DIR, f"AmbientCore_{day.strftime('%Y-%m-%d')}.csv")
        if not os.path.exists(path):
            continue
        try:
            with open(path, newline="") as f:
                for row in csv.DictReader(f):
                    try:
                        ts = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
                        t  = float(row["room_temp"])
                        if ts >= cutoff:
                            results.append((ts, t))
                    except (ValueError, KeyError):
                        pass
        except Exception:
            pass
    return sorted(results)


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

    if "cpu_temp" not in out and cpu_core_temps:
        out["cpu_temp"] = round(max(cpu_core_temps), 1)

    return out

# ── Stats thread ───────────────────────────────────────────────────────────────
def run_stats():
    lhm_countdown = 0

    while True:
        sensors["cpu_usage"] = psutil.cpu_percent(interval=1)
        sensors["ram_usage"] = psutil.virtual_memory().percent
        try:
            sensors["disk_usage"] = psutil.disk_usage("C:\\").percent
        except Exception:
            sensors["disk_usage"] = None

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

        lhm_countdown -= 1
        if lhm_countdown <= 0:
            lhm_data = _query_lhm()
            if lhm_data:
                parsed = _parse_lhm(lhm_data)
                for key in ("cpu_temp", "disk_temp", "ram_temp", "fans"):
                    if key in parsed:
                        sensors[key] = parsed[key]
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
                lhm_countdown = 10

# ── Alarm ──────────────────────────────────────────────────────────────────────
def _tts(text):
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

        _tts("Room temperature critical. Please shut down power now.")

        if not _alarm_active:
            return

        for _ in range(3):
            if not _alarm_active:
                return
            try:
                winsound.Beep(1000, 350)
            except Exception:
                pass
            time.sleep(0.12)

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

# ── Tray icon ──────────────────────────────────────────────────────────────────
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
        pystray.MenuItem(
            "24h Graph",
            lambda i, it: root.after(0, lambda: _open_graph(root)),
        ),
        pystray.MenuItem("Exit", lambda i, it: root.after(0, _exit_app)),
    )
    tray_obj = pystray.Icon("AmbientCore", _tray_image(), "Connecting…", menu)
    tray_obj.run()

def _show_dashboard():
    root.deiconify()
    if os.path.exists(ICON_PATH):
        root.iconbitmap(ICON_PATH)
    root.lift()
    root.focus_force()

def _exit_app():
    _clear_alarm()
    if tray_obj:
        tray_obj.stop()
    root.destroy()
    sys.exit(0)

# ── GUI helpers ────────────────────────────────────────────────────────────────
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

# ── 24-hour graph window ───────────────────────────────────────────────────────
_mpl      = None
_graph_win = None   # single-instance guard

def _ensure_mpl():
    global _mpl
    if _mpl is not None:
        return _mpl
    try:
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.dates as mdates
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        _mpl = (matplotlib, mdates, Figure, FigureCanvasTkAgg)
        return _mpl
    except ImportError:
        return None

def _open_graph(master):
    """Open the graph window, or raise/focus the existing one."""
    global _graph_win
    if _graph_win is not None:
        try:
            if _graph_win.w.winfo_exists():
                _graph_win.w.lift()
                _graph_win.w.focus_force()
                return
        except Exception:
            pass
    _graph_win = GraphWindow(master)

class GraphWindow:
    def __init__(self, master):
        self.w = tk.Toplevel(master)
        self.w.title("24h Temperature — Room Sensor")
        self.w.geometry("760x440")
        self.w.configure(bg=BG)
        self.w.resizable(True, True)
        self.w.attributes("-topmost", True)
        if os.path.exists(ICON_PATH):
            self.w.iconbitmap(ICON_PATH)
        self._after_id = None
        self._build()
        self.w.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        mpl_result = _ensure_mpl()
        if mpl_result is None:
            tk.Label(
                self.w,
                text=(
                    "matplotlib is not installed.\n\n"
                    "Run in terminal:\n"
                    "    pip install matplotlib\n\n"
                    "Then restart AmbientCore."
                ),
                font=("Segoe UI", 11), fg=RED, bg=BG, justify="center",
            ).pack(expand=True)
            return

        _, _, Figure, FigureCanvasTkAgg = mpl_result
        is_dark = cfg.get("theme", "dark") == "dark"
        fig_bg  = "#1e1e1e" if is_dark else "#f5f5f5"
        ax_bg   = "#252526" if is_dark else "#e8e8e8"

        self.fig = Figure(figsize=(7.6, 4.1), dpi=100, facecolor=fig_bg)
        self.ax  = self.fig.add_subplot(111, facecolor=ax_bg)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.w)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(8, 0))

        bar = tk.Frame(self.w, bg=BG)
        bar.pack(fill="x", padx=8, pady=(4, 6))
        tk.Button(
            bar, text="Open Log Folder",
            font=("Segoe UI", 9), bg=PANEL, fg=WHITE,
            relief="flat", activebackground=BORDER, activeforeground=WHITE,
            padx=8, pady=3, cursor="hand2",
            command=lambda: subprocess.Popen(["explorer", LOG_DIR]),
        ).pack(side="left")
        self.refresh_lbl = tk.Label(bar, text="", font=("Segoe UI", 8), fg=DIM, bg=BG)
        self.refresh_lbl.pack(side="right")

        self._schedule_refresh()

    def _redraw(self):
        _, mdates, _, _ = _ensure_mpl()
        is_dark = cfg.get("theme", "dark") == "dark"
        txt_col = "#d4d4d4" if is_dark else "#212121"
        line_c  = "#4fc3f7" if is_dark else "#0288d1"
        fill_c  = "#4fc3f7" if is_dark else "#0288d1"
        grid_c  = "#3c3c3c" if is_dark else "#bdbdbd"
        ax_bg   = "#252526" if is_dark else "#e8e8e8"

        ax = self.ax
        ax.clear()
        ax.set_facecolor(ax_bg)

        # Merge CSV history with in-memory buffer; deduplicate by minute
        csv_data = _load_csv_history()
        with _24h_lock:
            buf = list(_24h_buffer)

        seen = {}
        for ts, v in csv_data + buf:
            seen[ts.replace(second=0, microsecond=0)] = (ts, v)
        merged = sorted(seen.values())

        if len(merged) >= 2:
            xs = [p[0] for p in merged]
            ys = [p[1] for p in merged]
            ax.plot(xs, ys, color=line_c, linewidth=1.5, zorder=3)
            ax.fill_between(xs, ys, alpha=0.15, color=fill_c, zorder=2)
            ax.annotate(
                f"{ys[-1]:.1f}°C",
                xy=(xs[-1], ys[-1]),
                xytext=(-44, 8), textcoords="offset points",
                color=line_c, fontsize=9, fontweight="bold",
            )
        elif len(merged) == 1:
            xs = [p[0] for p in merged]
            ys = [p[1] for p in merged]
            ax.scatter(xs, ys, color=line_c, zorder=3, s=20)

        ax.axhline(
            cfg["room_warn"], color="#ffd54f", linewidth=1, linestyle="--",
            label=f"Warning {cfg['room_warn']:.0f}°C", zorder=4,
        )
        ax.axhline(
            cfg["room_critical"], color="#ef5350", linewidth=1, linestyle="--",
            label=f"Critical {cfg['room_critical']:.0f}°C", zorder=4,
        )

        now = datetime.now()
        ax.set_xlim(now - timedelta(hours=24), now)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        ax.tick_params(colors=txt_col, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(grid_c)
        ax.set_ylabel("Room Temperature (°C)", color=txt_col, fontsize=9)
        ax.grid(True, color=grid_c, linewidth=0.5, alpha=0.7, zorder=1)
        ax.legend(fontsize=8, facecolor=ax_bg, edgecolor=grid_c, labelcolor=txt_col)

        if not merged:
            ax.text(
                0.5, 0.5, "No data yet — waiting for sensor readings",
                transform=ax.transAxes, ha="center", va="center",
                color=txt_col, fontsize=10,
            )

        self.fig.tight_layout()
        self.canvas.draw()
        self.refresh_lbl.config(text=f"Updated {datetime.now().strftime('%H:%M:%S')}")

    def _schedule_refresh(self):
        self._redraw()
        self._after_id = self.w.after(60_000, self._schedule_refresh)

    def _on_close(self):
        global _graph_win
        if self._after_id:
            self.w.after_cancel(self._after_id)
        _graph_win = None
        self.w.destroy()


# ── Dashboard ──────────────────────────────────────────────────────────────────
class Dashboard:
    def __init__(self, master):
        self.root      = master
        self._tick_id  = None
        self._log_cnt  = 0
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

        s = _make_section(content, "ELECTRICAL CONNECTIONS", BLUE)
        self.e_temp = _make_row(s, "Temperature", BLUE)
        self.e_hum  = _make_row(s, "Humidity",    GREEN)
        self.e_batt = _make_row(s, "Battery",     DIM)

        s = _make_section(content, "CPU", ORANGE)
        self.cpu_usage = _make_row(s, "Usage",       ORANGE)
        self.cpu_temp  = _make_row(s, "Temperature", ORANGE)

        s = _make_section(content, "GPU (NVIDIA)", RED)
        self.gpu_temp  = _make_row(s, "Temperature", RED)
        self.gpu_usage = _make_row(s, "Usage",       RED)

        s = _make_section(content, "MEMORY (RAM)", GREEN)
        self.ram_usage = _make_row(s, "Usage",       GREEN)
        self.ram_temp  = _make_row(s, "Temperature", DIM)

        s = _make_section(content, "DISK  (C:\\)", YELLOW)
        self.disk_usage = _make_row(s, "Usage",       YELLOW)
        self.disk_temp  = _make_row(s, "Temperature", DIM)

        self.fan_body = _make_section(content, "FANS", DIM)
        self.fan_rows = {}

        self.lhm_lbl = tk.Label(
            content, text="", font=("Segoe UI", 8), fg=DIM, bg=BG,
            wraplength=370, justify="left",
        )
        self.lhm_lbl.pack(anchor="w", pady=(10, 0))

        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=12, pady=(4, 10))
        self.status_lbl = tk.Label(bar, text="Connecting…",
                                   font=("Segoe UI", 8), fg=DIM, bg=BG)
        self.status_lbl.pack(side="left")
        tk.Button(
            bar, text="Graph", font=("Segoe UI", 9),
            bg=PANEL, fg=WHITE, relief="flat",
            activebackground=BORDER, activeforeground=WHITE,
            padx=8, pady=3, cursor="hand2",
            command=lambda: _open_graph(self.root),
        ).pack(side="right", padx=(4, 0))
        tk.Button(
            bar, text="⚙  Settings", font=("Segoe UI", 9),
            bg=PANEL, fg=WHITE, relief="flat",
            activebackground=BORDER, activeforeground=WHITE,
            padx=8, pady=3, cursor="hand2",
            command=lambda: SettingsWindow(self.root, self),
        ).pack(side="right")

    def _tick(self):
        self._refresh()
        _refresh_tray()
        self._log_cnt += 1
        if self._log_cnt >= 30:
            _log_reading()
            self._log_cnt = 0
        self._tick_id = self.root.after(1000, self._tick)

    def rebuild(self):
        """Destroy all widgets, reload theme, and recreate everything."""
        if self._tick_id:
            self.root.after_cancel(self._tick_id)
            self._tick_id = None
        for w in self.root.winfo_children():
            w.destroy()
        _load_theme()
        self.root.configure(bg=BG)
        self._build()
        self._tick()

    def _refresh(self):
        s = sensors

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

        gt = s["gpu_temp"]
        self.gpu_temp.config(
            text=f"{gt:.0f}°C" if gt is not None else "N/A",
            fg=_alarm_color(gt, RED, "gpu_warn") if gt is not None else DIM,
        )
        gu = s["gpu_usage"]
        self.gpu_usage.config(text=f"{gu:.0f}%" if gu is not None else "N/A")

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

        du = s["disk_usage"]
        self.disk_usage.config(text=f"{du:.0f}%" if du is not None else "---")
        disk_t = s["disk_temp"]
        self.disk_temp.config(
            text=f"{disk_t:.0f}°C" if disk_t is not None else "N/A",
            fg=WHITE if disk_t is not None else DIM,
        )

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
    def __init__(self, parent, dashboard=None):
        self._dashboard = dashboard
        self.w = tk.Toplevel(parent)
        self.w.title("Settings")
        self.w.geometry("340x470")
        self.w.configure(bg=BG)
        self.w.attributes("-topmost", True)
        self.w.resizable(False, False)
        if os.path.exists(ICON_PATH):
            self.w.iconbitmap(ICON_PATH)
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

        # Theme
        tk.Frame(self.w, bg=BORDER, height=1).pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(self.w, text="THEME",
                 font=("Segoe UI", 10, "bold"), fg=BLUE, bg=BG).pack(pady=(0, 4))
        theme_row = tk.Frame(self.w, bg=BG)
        theme_row.pack(pady=(0, 4))
        self.theme_var = tk.StringVar(value=cfg.get("theme", "dark"))
        for label, val in (("Dark", "dark"), ("Light", "light")):
            tk.Radiobutton(
                theme_row, text=label, variable=self.theme_var, value=val,
                font=("Segoe UI", 9), fg=WHITE, bg=BG,
                selectcolor=PANEL, activebackground=BG, activeforeground=WHITE,
            ).pack(side="left", padx=20)

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
        theme_changed = cfg.get("theme", "dark") != self.theme_var.get()
        cfg.update(vals)
        cfg["sound_alarm"] = self.sound_var.get()
        cfg["theme"]       = self.theme_var.get()
        save_cfg()
        self.w.destroy()
        if theme_changed and self._dashboard:
            self._dashboard.rebuild()


# ── First-run setup (only triggers when running as a compiled .exe) ────────────
def _first_run_setup():
    import winreg as _wr
    import ctypes

    marker = os.path.join(_DIR, ".setup_done")
    if os.path.exists(marker):
        return

    resp = ctypes.windll.user32.MessageBoxW(
        0,
        "Welcome to AmbientCore!\n\n"
        "Would you like to:\n"
        "  • Start AmbientCore automatically with Windows\n"
        "  • Add a shortcut to your Desktop\n",
        "AmbientCore Setup",
        0x00000024,
    )
    if resp == 6:
        cmd = f'"{sys.executable}"'
        try:
            key = _wr.OpenKey(
                _wr.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, _wr.KEY_SET_VALUE,
            )
            _wr.SetValueEx(key, "AmbientCore", 0, _wr.REG_SZ, cmd)
            _wr.CloseKey(key)
        except Exception:
            pass

        try:
            key2 = _wr.OpenKey(
                _wr.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            )
            desktop = os.path.expandvars(_wr.QueryValueEx(key2, "Desktop")[0])
            _wr.CloseKey(key2)
        except Exception:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")

        lnk  = os.path.join(desktop, "AmbientCore.lnk")
        icon = os.path.join(_BUNDLE, "icon.ico")
        vbs  = (
            'Set sh = WScript.CreateObject("WScript.Shell")\n'
            f'Set lnk = sh.CreateShortcut("{lnk}")\n'
            f'lnk.TargetPath = "{sys.executable}"\n'
            f'lnk.WorkingDirectory = "{_DIR}"\n'
            f'lnk.IconLocation = "{icon}"\n'
            'lnk.Description = "AmbientCore - Environment & Hardware Monitor"\n'
            "lnk.Save\n"
        )
        vbs_path = os.path.join(_DIR, "_tmp.vbs")
        try:
            with open(vbs_path, "w") as f:
                f.write(vbs)
            subprocess.run(
                ["cscript", "//nologo", vbs_path],
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )
        finally:
            if os.path.exists(vbs_path):
                os.remove(vbs_path)

    open(marker, "w").close()


# ── Entry point ────────────────────────────────────────────────────────────────

# Tell Windows this is a standalone app so it uses our icon in the taskbar
# instead of grouping the window under python.exe
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AmbientCore.Widget.1")
except Exception:
    pass

root = tk.Tk()
if os.path.exists(ICON_PATH):
    root.iconbitmap(ICON_PATH)
root.withdraw()

if getattr(sys, "frozen", False):
    _first_run_setup()

dashboard = Dashboard(root)
root.deiconify()
if os.path.exists(ICON_PATH):
    root.iconbitmap(ICON_PATH)

threading.Thread(target=run_ble,   daemon=True).start()
threading.Thread(target=run_stats, daemon=True).start()
threading.Thread(target=run_tray,  daemon=True).start()

root.mainloop()
