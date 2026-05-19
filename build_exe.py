"""
AmbientCore — EXE builder.

Run once with:  python build_exe.py

Requires PyInstaller:  pip install pyinstaller

Output:  dist\AmbientCore\AmbientCore.exe   (fast-start, self-contained folder)

After building, run AmbientCore.exe once — it will ask if you want to add it
to Windows startup and create a desktop shortcut automatically.
"""

import os
import sys
import subprocess
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH  = os.path.join(SCRIPT_DIR, "icon.ico")
DIST_DIR   = os.path.join(SCRIPT_DIR, "dist", "AmbientCore")
EXE_PATH   = os.path.join(DIST_DIR, "AmbientCore.exe")


def ensure_icon():
    if not os.path.exists(ICON_PATH):
        print("  Generating icon.ico ...")
        from install import create_icon
        create_icon()


def build():
    print()
    print("  AmbientCore - Building EXE")
    print("  " + "-" * 36)

    ensure_icon()

    # Check PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("\n  PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    print("  Running PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name",           "AmbientCore",
        "--windowed",                           # no console window
        "--icon",           ICON_PATH,
        "--add-data",       f"{ICON_PATH};.",   # bundle icon.ico inside the exe folder
        "--noconfirm",                          # overwrite dist without asking
        "--clean",                              # fresh build
        # Explicit hidden imports bleak needs on Windows
        "--hidden-import",  "bleak",
        "--hidden-import",  "bleak.backends.winrt",
        "--hidden-import",  "bleak.backends.winrt.scanner",
        "--hidden-import",  "bleak.backends.winrt.client",
        "--hidden-import",  "bleak.backends.winrt.utils",
        "--hidden-import",  "bleak.backends.characteristic",
        "--hidden-import",  "bleak.backends.descriptor",
        "--hidden-import",  "bleak.backends.service",
        "--hidden-import",  "pystray._win32",
        "--hidden-import",  "PIL._tkinter_finder",
        os.path.join(SCRIPT_DIR, "widget.py"),
    ]

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)

    if result.returncode != 0:
        print("\n  Build FAILED. See output above.")
        return

    print()
    print("  Build complete!")
    print(f"  EXE location:  {EXE_PATH}")
    print()

    # Copy config.json if it exists so settings carry over
    cfg_src = os.path.join(SCRIPT_DIR, "config.json")
    cfg_dst = os.path.join(DIST_DIR, "config.json")
    if os.path.exists(cfg_src) and not os.path.exists(cfg_dst):
        shutil.copy(cfg_src, cfg_dst)
        print("  Copied config.json to dist folder.")

    print()
    ans = input("  Launch AmbientCore.exe now? [Y/n]: ").strip().lower()
    if ans != "n":
        subprocess.Popen([EXE_PATH])
        print("  Launched.")
    print()


if __name__ == "__main__":
    build()
