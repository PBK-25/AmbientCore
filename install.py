"""
AmbientCore — One-time setup script.

Run this once with:  python install.py

It will:
  1. Generate the app icon  (icon.ico)
  2. Add AmbientCore to Windows startup (no admin rights needed)
  3. Create a desktop shortcut
  4. Offer to launch the widget now
"""

import os
import sys
import winreg
import subprocess
from PIL import Image, ImageDraw

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
WIDGET_PATH = os.path.join(SCRIPT_DIR, "widget.py")
ICON_PATH   = os.path.join(SCRIPT_DIR, "icon.ico")
APP_NAME    = "AmbientCore"

# ── 1. Icon generation ─────────────────────────────────────────────────────────
def _draw_frame(size):
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s    = size

    # Dark rounded background
    pad = max(1, s // 16)
    draw.rounded_rectangle(
        [pad, pad, s - pad, s - pad],
        radius=s // 5,
        fill=(22, 22, 30, 255),
        outline=(79, 195, 247, 220),
        width=max(1, s // 20),
    )

    # Thermometer stem
    cx       = s // 2
    stem_w   = max(2, s // 8)
    stem_top = s // 5
    stem_bot = s * 13 // 20
    draw.rounded_rectangle(
        [cx - stem_w // 2, stem_top, cx + stem_w // 2, stem_bot],
        radius=stem_w // 2,
        fill=(79, 195, 247, 255),
    )

    # Thermometer bulb
    bulb_r = max(3, s // 6)
    bulb_cy = stem_bot + bulb_r - max(1, s // 16)
    draw.ellipse(
        [cx - bulb_r, bulb_cy - bulb_r, cx + bulb_r, bulb_cy + bulb_r],
        fill=(79, 195, 247, 255),
    )

    # Humidity droplet (top-right area, only visible at larger sizes)
    if s >= 48:
        dx = cx + s // 5
        dy = s // 4
        dr = max(2, s // 12)
        draw.ellipse(
            [dx - dr, dy, dx + dr, dy + dr * 2],
            fill=(165, 214, 167, 200),
        )
        # droplet tip
        draw.polygon(
            [(dx, dy - dr), (dx - dr, dy + dr // 2), (dx + dr, dy + dr // 2)],
            fill=(165, 214, 167, 200),
        )

    return img


def create_icon():
    # Draw at 256x256 then let PIL produce all required sizes
    base   = _draw_frame(256).convert("RGBA")
    sizes  = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(ICON_PATH, format="ICO", sizes=sizes)
    print(f"  [OK] Icon created -> {ICON_PATH}")


# ── 2. Windows startup registration ───────────────────────────────────────────
def _pythonw():
    """Return path to pythonw.exe (no console window on startup)."""
    candidate = sys.executable.replace("python.exe", "pythonw.exe")
    return candidate if os.path.exists(candidate) else sys.executable


def add_startup():
    cmd = f'"{_pythonw()}" "{WIDGET_PATH}"'
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(key)
    print(f"  [OK] Startup entry added (HKCU\\...\\Run\\{APP_NAME})")


def remove_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print(f"  [OK] Startup entry removed.")
    except FileNotFoundError:
        print("  [--] No startup entry found.")


# ── 3. Desktop shortcut ────────────────────────────────────────────────────────
def _get_desktop():
    """Use the registry to find the real Desktop path (handles OneDrive redirection)."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        path = os.path.expandvars(winreg.QueryValueEx(key, "Desktop")[0])
        winreg.CloseKey(key)
        return path
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Desktop")

def create_shortcut(target_path=None, is_exe=False):
    desktop = _get_desktop()
    lnk     = os.path.join(desktop, f"{APP_NAME}.lnk")
    if is_exe and target_path:
        target  = target_path
        args    = ""
        workdir = os.path.dirname(target_path)
    else:
        target  = _pythonw()
        args    = f'"{WIDGET_PATH}"'
        workdir = SCRIPT_DIR
    # Use Chr(34) for quotes inside VBScript strings to avoid escaping issues
    quoted_args = f'Chr(34) & "{args.strip(chr(34))}" & Chr(34)' if args else '""'
    vbs = (
        'Set sh = WScript.CreateObject("WScript.Shell")\n'
        f'Set lnk = sh.CreateShortcut("{lnk}")\n'
        f'lnk.TargetPath = "{target}"\n'
        f'lnk.Arguments = {quoted_args}\n'
        f'lnk.WorkingDirectory = "{workdir}"\n'
        f'lnk.IconLocation = "{ICON_PATH}"\n'
        f'lnk.Description = "AmbientCore - Environment & Hardware Monitor"\n'
        "lnk.Save\n"
    )
    vbs_path = os.path.join(SCRIPT_DIR, "_tmp_shortcut.vbs")
    with open(vbs_path, "w") as f:
        f.write(vbs)
    subprocess.run(
        ["cscript", "//nologo", vbs_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    os.remove(vbs_path)
    print(f"  [OK] Desktop shortcut -> {lnk}")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AmbientCore setup")
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the startup entry",
    )
    args = parser.parse_args()

    print()
    print("  AmbientCore Setup")
    print("  " + "-" * 36)

    if args.uninstall:
        remove_startup()
        print("\n  AmbientCore removed from startup.")
    else:
        create_icon()
        add_startup()
        create_shortcut()
        print()
        print("  Done! AmbientCore will now start automatically with Windows.")
        print("  A shortcut has been added to your Desktop.")
        print()
        ans = input("  Launch AmbientCore now? [Y/n]: ").strip().lower()
        if ans != "n":
            subprocess.Popen([_pythonw(), WIDGET_PATH])
            print("  Widget launched.")
    print()
