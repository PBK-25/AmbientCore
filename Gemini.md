I have a Xiaomi Smart Temperature and Humidity Monitor

I want a way to keep it connected to my computer and show the values real time

While Xiaomi makes fantastic and affordable temperature sensors, they don't provide an official desktop app for them—they are strictly designed to live inside the Mi Home mobile app.

However, because these monitors broadcast their data using standard Bluetooth Low Energy (BLE), you can absolutely bypass the app and read the real-time data directly from your computer, provided your PC has Bluetooth.

Here are the most reliable ways to set this up, ranging from a quick browser trick to a full smart-home dashboard.

Method 1: The Web Browser (Quickest & Easiest)
You don't need to install any software for this method. Modern web browsers (like Google Chrome and Microsoft Edge) have a built-in feature called Web Bluetooth that can talk to nearby devices.

How it works:

Turn on your PC's Bluetooth.

Open a Chromium-based browser (Chrome or Edge) and visit the community-built Telink Web Flasher tool. (Note: This tool is often used by enthusiasts to flash custom firmware, but it works perfectly as a passive, real-time monitor).

Click Connect and select your Xiaomi monitor from the pairing menu (it will likely show up as LYWSD03MMC or similar).

Once connected, the page will display your real-time temperature, humidity, and battery percentage right in your browser.

Method 2: Python Scripting (Best for Logging & Custom Projects)
If you are comfortable with coding and want to save the data to a spreadsheet or build your own custom widget, Python is the way to go.

How it works:

You can write a lightweight script using a Python Bluetooth library like bleak, or use pre-made open-source scripts like MiTemperature2 from GitHub.

The script runs in your terminal or command prompt, passively "listening" to the Bluetooth signals your Xiaomi monitor constantly broadcasts in the background.

It will print the exact temperature and humidity to your screen every few seconds without needing to pair the device.

Method 3: Home Assistant (Best for a Permanent Dashboard)
If your ultimate goal is to have a beautiful, permanent dashboard on your computer monitor with graphs tracking the temperature over time, you should look into Home Assistant.

How it works:

You install Home Assistant on your PC (usually via a Virtual Machine or Docker).

Home Assistant has a native, built-in "Xiaomi BLE" integration.

As long as your PC's Bluetooth is on, Home Assistant will automatically discover the sensor and generate a live, customizable dashboard showing current metrics and historical climate graphs.

Method 4: Android Emulator (The "Official" Workaround)
If you really just want the exact Mi Home interface you see on your phone, you can simulate a mobile environment on your PC.

How it works:

Download an Android emulator like BlueStacks, or use the Windows Subsystem for Android if you are on Windows 11.

Install the Mi Home app from the Google Play Store inside the emulator.

Caveat: Bluetooth pass-through from a PC to an Android emulator can sometimes be finicky, so this method can require some trial and error.

Which of these routes sounds like the best fit for your setup? If you'd like, I can write a starter Python script for you or walk you through the browser method step-by-step!

Method 2: Python Scripting (Best for Logging & Custom Projects)

If you are comfortable with coding and want to save the data to a spreadsheet or build your own custom widget, Python is the way to go.



How it works:

You can write a lightweight script using a Python Bluetooth library like bleak, or use pre-made open-source scripts like MiTemperature2 from GitHub.

The script runs in your terminal or command prompt, passively "listening" to the Bluetooth signals your Xiaomi monitor constantly broadcasts in the background.

It will print the exact temperature and humidity to your screen every few seconds without needing to pair the device.



I like this approach

can you guide me step by step to do it ?

This is a fantastic choice. Building your own script gives you total control over the data, and using Python with the bleak library is incredibly satisfying once it clicks.

Before we start, a quick point of clarification: because the stock Xiaomi firmware encrypts its background "passive" broadcasts, doing a true passive listen requires extracting a hidden decryption key from the Mi Home app. To skip that headache, the script below will instead connect directly to the sensor's live data stream. It is much easier to set up and requires zero hacking.

Here is exactly how to do it, step by step.

Step 1: Install Python and the bleak Library
You will need Python installed on your computer. If you don't have it, download it from python.org (make sure to check the box that says "Add Python to PATH" during installation).

Once Python is ready, open your terminal (macOS/Linux) or Command Prompt/PowerShell (Windows) and install the Bluetooth library by running:

Bash
pip install bleak
Step 2: Create the Python Script
Create a new folder for your project, open your favorite text editor or IDE (like VS Code, Notepad, or TextEdit), and paste the following code. Save the file as xiaomi_monitor.py.

Python
import asyncio
from bleak import BleakScanner, BleakClient

# The specific Bluetooth characteristic UUID for the Xiaomi LYWSD03MMC
DATA_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"

def notification_handler(sender, data):
    """
    Decodes the raw byte data sent by the sensor.
    The sensor sends exactly 5 bytes of data (e.g., 88 07 34 39 0B).
    """
    # Bytes 0 & 1: Temperature (Little Endian format)
    temp_int = int.from_bytes(data[0:2], byteorder='little')
    temperature = temp_int / 100.0
    
    # Byte 2: Humidity percentage
    humidity = data[2]
    
    # Bytes 3 & 4: Battery voltage in millivolts
    batt_mv = int.from_bytes(data[3:5], byteorder='little')
    
    print(f"Live Data -> Temperature: {temperature}°C | Humidity: {humidity}% | Battery: {batt_mv}mV")

async def main():
    print("Scanning for Xiaomi Monitor (LYWSD03MMC)...")
    devices = await BleakScanner.discover(timeout=5.0)
    
    target_address = None
    for device in devices:
        # The sensor usually broadcasts its name as 'LYWSD03MMC'
        if device.name and "LYWSD03MMC" in device.name:
            target_address = device.address
            print(f"Found sensor! Address: {target_address}")
            break
            
    if not target_address:
        print("Sensor not found. Make sure Bluetooth is on and the sensor is close by.")
        return

    print(f"Connecting to {target_address}...")
    try:
        async with BleakClient(target_address) as client:
            print("Connected successfully! Waiting for sensor readings (press Ctrl+C to stop)...\n")
            
            # Subscribe to the sensor's live data stream
            await client.start_notify(DATA_UUID, notification_handler)
            
            # Keep the script running to listen to incoming data
            while True:
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    # Run the asynchronous loop
    asyncio.run(main())
Step 3: Run the Script
Make sure your computer's Bluetooth is turned on. Navigate to the folder where you saved the script in your terminal, and run it:

Bash
python xiaomi_monitor.py
How the Script Works (The Geeky Details)
The Scan: The script first tells your computer's Bluetooth radio to look for any device broadcasting the name LYWSD03MMC. (Note: On Windows/Linux, the address it finds will be a MAC address like A4:C1:38.... On macOS, Apple hides MAC addresses for privacy, so it will print a long UUID instead. The script handles both seamlessly).

The Subscription: Once connected, it targets the specific "UUID" (ebe0ccc1...) that Xiaomi uses to stream environmental data. It tells the sensor, "Send me an alert every time the temperature or humidity changes."

The Translation: The sensor doesn't send plain text; it sends hex bytes. A temperature of 19.28°C is sent as 88 07. The notification_handler function catches these bytes, reverses them (a concept called Little Endian), divides by 100, and prints human-readable numbers straight to your screen.

PS C:\Users\kalre\OneDrive\Desktop\TempSensor> python xiaomi_monitor.py

Scanning for Xiaomi Monitor (LYWSD03MMC)...

Sensor not found. Make sure Bluetooth is on and the sensor is close by.

PS C:\Users\kalre\OneDrive\Desktop\TempSensor> 

Don't worry, this is the most common hurdle when working with BLE (Bluetooth Low Energy) devices! If the script ran but couldn't find the sensor, it means your computer's Bluetooth radio is working, but it simply didn't see the specific name LYWSD03MMC broadcasting during that 5-second window.

Here are the most likely reasons this is happening and how to fix them.

1. Disconnect from the Mi Home App (Most Common)
Bluetooth Low Energy typically only allows a sensor to have one active connection at a time.

If your Xiaomi sensor is currently connected to the Mi Home app on your phone, it will stop broadcasting its availability to other devices.

The Fix: Turn off Bluetooth on your phone temporarily, or force-close the Mi Home app, and try running the script again.

2. The Sensor is Broadcasting a Different Name
Depending on the firmware version (or if it was ever flashed with custom firmware), the sensor might not be broadcasting the exact string "LYWSD03MMC". Sometimes it broadcasts as MiKettle, ATC_XXXX, or even a blank name.

Let's find out exactly what your computer is seeing. Create a new file called scanner.py in the same folder, paste this diagnostic code, and run it:

Python
import asyncio
from bleak import BleakScanner

async def main():
    print("Scanning for ALL nearby Bluetooth devices for 10 seconds...")
    # Increased timeout to 10 seconds to catch slow broadcasters
    devices = await BleakScanner.discover(timeout=10.0)
    
    print("\n--- Devices Found ---")
    for d in devices:
        # Print everything the PC can see
        print(f"Name: {d.name} | Address: {d.address} | Signal Strength: {d.rssi} dBm")
    print("---------------------\n")

if __name__ == "__main__":
    asyncio.run(main())
Run this with python scanner.py. Look through the list it prints. You are looking for a device with a strong signal strength (closer to 0 is better, e.g., -50 dBm is very close, -90 dBm is far away). If you see it broadcasting a slightly different name, you can just change "LYWSD03MMC" in the original script to match whatever name it is actually using.

3. Increase the Scan Timeout
Sometimes, these battery-powered sensors go to "sleep" and only broadcast their presence every 5 to 10 seconds to save power. If our original script only scanned for 5 seconds, it might have just missed the broadcast window.

In your original xiaomi_monitor.py script, find this line:

Python
devices = await BleakScanner.discover(timeout=5.0)
Change the 5.0 to 15.0, save the file, and try running it again.

4. Windows Bluetooth Pairing Quirk
Usually, you do not need to pair BLE devices in Windows for Python to see them. However, Windows 11 sometimes aggressively filters out "unpaired" devices.

Open your standard Windows Bluetooth settings.

Click Add device.

See if the LYWSD03MMC shows up in the standard Windows list. If it does, click it to pair it, and then try running the Python script again.

PS C:\Users\kalre\OneDrive\Desktop\TempSensor> python scanner.py

Scanning for ALL nearby Bluetooth devices for 10 seconds...



--- Devices Found ---

Traceback (most recent call last):

  File "C:\Users\kalre\OneDrive\Desktop\TempSensor\scanner.py", line 16, in <module>

    asyncio.run(main())

    ~~~~~~~~~~~^^^^^^^^

  File "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3568.0_x64__qbz5n2kfra8p0\Lib\asyncio\runners.py", line 195, in run

    return runner.run(main)

           ~~~~~~~~~~^^^^^^

  File "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3568.0_x64__qbz5n2kfra8p0\Lib\asyncio\runners.py", line 118, in run

    return self._loop.run_until_complete(task)

           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^

  File "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3568.0_x64__qbz5n2kfra8p0\Lib\asyncio\base_events.py", line 725, in run_until_complete

    return future.result()

           ~~~~~~~~~~~~~^^

  File "C:\Users\kalre\OneDrive\Desktop\TempSensor\scanner.py", line 12, in main

    print(f"Name: {d.name} | Address: {d.address} | Signal Strength: {d.rssi} dBm")

                                                                      ^^^^^^

AttributeError: 'BLEDevice' object has no attribute 'rssi'

PS C:\Users\kalre\OneDrive\Desktop\TempSensor> 

Ah, I apologize for that! That is entirely my fault.

The bleak library recently updated how it handles Bluetooth data. It moved the signal strength (rssi) out of the main device object and into a separate "Advertisement Data" object.

Let's fix that script so it uses the modern, updated method to grab both the device name and its signal strength.

The Corrected Scanner Script
Replace the code in your scanner.py file with this updated version:

Python
import asyncio
from bleak import BleakScanner

async def main():
    print("Scanning for ALL nearby Bluetooth devices for 10 seconds...")
    
    # Adding 'return_adv=True' tells bleak to capture the extra advertisement data (like RSSI)
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
    
    print("\n--- Devices Found ---")
    
    # With return_adv=True, 'devices' is now a dictionary where we get the device AND its ad data
    for address, (device, adv_data) in devices.items():
        name = device.name or "Unknown"
        rssi = adv_data.rssi
        print(f"Name: {name} | Address: {address} | Signal Strength: {rssi} dBm")
        
    print("---------------------\n")

if __name__ == "__main__":
    asyncio.run(main())
What to do next:
Run python scanner.py again.

It should successfully print out a list of everything your PC can see.

Look for anything named LYWSD03MMC, MiKettle, ATC_XXXX, or even a blank name with a very strong signal (e.g., -40 dBm to -60 dBm).

Once you spot your sensor's name or address in that list, we can drop it straight into the main monitor script.

PS C:\Users\kalre\OneDrive\Desktop\TempSensor> python scanner.py

Scanning for ALL nearby Bluetooth devices for 10 seconds...



--- Devices Found ---

Name: Unknown | Address: 05:CD:4F:7F:38:39 | Signal Strength: -55 dBm

Name: Unknown | Address: 54:00:AF:C4:0F:37 | Signal Strength: -67 dBm

Name: Unknown | Address: D0:D0:03:EC:DA:07 | Signal Strength: -85 dBm

Name: Unknown | Address: FA:ED:FC:A7:4F:AA | Signal Strength: -59 dBm

Name: Unknown | Address: 2B:5E:6F:3F:23:B7 | Signal Strength: -55 dBm

Name: Unknown | Address: 54:F7:9F:B8:69:EE | Signal Strength: -84 dBm

Name: Unknown | Address: 38:CA:84:8C:3B:A8 | Signal Strength: -97 dBm

Name: Unknown | Address: 74:D3:38:F2:BF:2B | Signal Strength: -93 dBm

Name: Unknown | Address: 55:DF:59:76:27:DD | Signal Strength: -99 dBm

Name: Unknown | Address: 59:DB:A0:CB:5C:06 | Signal Strength: -92 dBm

Name: Unknown | Address: 18:36:FF:6A:47:F1 | Signal Strength: -59 dBm

Name: Unknown | Address: 6B:F5:A1:64:46:B5 | Signal Strength: -96 dBm

Name: Unknown | Address: F7:24:A2:29:FD:1C | Signal Strength: -96 dBm

Name: Unknown | Address: E5:C6:8E:35:30:35 | Signal Strength: -99 dBm

Name: Unknown | Address: AC:C0:48:3B:EC:2C | Signal Strength: -53 dBm

Name: Unknown | Address: D5:74:15:7F:55:3A | Signal Strength: -70 dBm

Name: Unknown | Address: F8:F7:94:97:A2:8D | Signal Strength: -88 dBm

Name: Unknown | Address: 62:A2:06:64:57:3D | Signal Strength: -102 dBm

Name: LYWSD03MMC | Address: A4:C1:38:87:3F:10 | Signal Strength: -45 dBm

Name: Unknown | Address: FA:E3:FB:61:F2:A0 | Signal Strength: -94 dBm

---------------------



PS C:\Users\kalre\OneDrive\Desktop\TempSensor> 

Bingo! We found it.

Here is the exact line from your output:
Name: LYWSD03MMC | Address: A4:C1:38:87:3F:10 | Signal Strength: -45 dBm

A signal strength of -45 dBm is fantastic; it means the sensor is very close to your PC and communicating loudly and clearly.

Now that we know its exact, permanent MAC address (A4:C1:38:87:3F:10), we can make our main script infinitely better. Instead of forcing the script to "scan and guess" every time you run it, we can hardcode the address so it connects instantly.

The Final Step: The Direct-Connect Script
Open your original xiaomi_monitor.py file, delete everything inside, and paste this streamlined version.

Python
import asyncio
from bleak import BleakClient

# The exact MAC address of your specific sensor
TARGET_ADDRESS = "A4:C1:38:87:3F:10"

# The specific Bluetooth characteristic UUID for the Xiaomi LYWSD03MMC
DATA_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"

def notification_handler(sender, data):
    """
    Decodes the raw byte data sent by the sensor.
    The sensor sends exactly 5 bytes of data (e.g., 88 07 34 39 0B).
    """
    # Bytes 0 & 1: Temperature (Little Endian format)
    temp_int = int.from_bytes(data[0:2], byteorder='little')
    temperature = temp_int / 100.0
    
    # Byte 2: Humidity percentage
    humidity = data[2]
    
    # Bytes 3 & 4: Battery voltage in millivolts
    batt_mv = int.from_bytes(data[3:5], byteorder='little')
    
    print(f"Live Data -> Temperature: {temperature}°C | Humidity: {humidity}% | Battery: {batt_mv}mV")

async def main():
    print(f"Connecting directly to {TARGET_ADDRESS}...")
    try:
        # Connect directly using the MAC address (no scanning required!)
        async with BleakClient(TARGET_ADDRESS) as client:
            print("Connected successfully! Waiting for sensor readings (press Ctrl+C to stop)...\n")
            
            # Subscribe to the sensor's live data stream
            await client.start_notify(DATA_UUID, notification_handler)
            
            # Keep the script running to listen to incoming data
            while True:
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"Failed to connect: {e}")
        print("Tip: If it fails, make sure the Mi Home app is closed on your phone!")

if __name__ == "__main__":
    # Run the asynchronous loop
    asyncio.run(main())
Run it!
Go back to your terminal and run:

Bash
python xiaomi_monitor.py
Because we are skipping the scanning phase, it should jump straight to "Connecting..." and, within a few seconds, start printing your live room temperature and humidity to the screen. Every time the temperature changes on the physical screen of the device, it will instantly pop up in your terminal.

oh wow

it is working and this was very simple and fast thank you



PS C:\Users\kalre\OneDrive\Desktop\TempSensor> python xiaomi_monitor.py

Connecting directly to A4:C1:38:87:3F:10...

Connected successfully! Waiting for sensor readings (press Ctrl+C to stop)...



Live Data -> Temperature: 25.93°C | Humidity: 46% | Battery: 3107mV

Live Data -> Temperature: 25.91°C | Humidity: 46% | Battery: 3107mV

Live Data -> Temperature: 25.94°C | Humidity: 46% | Battery: 3107mV

Live Data -> Temperature: 25.94°C | Humidity: 46% | Battery: 3107mV

That is awesome! Seeing those live numbers pop up in the terminal for the first time is a great feeling. You're officially reading raw Bluetooth packets directly from the hardware.

Notice how the battery voltage is 3107mV? That translates to roughly 3.1 Volts, meaning your CR2032 coin battery is nice and full (a dead battery drops closer to 2.5V-2.7V).

Now that you have a stable pipeline of real-time data flowing into your computer, what would you like to do with it next? We can modify the script to log these readings into a Excel/CSV file with timestamps, or we could look into making a tiny pop-up window widget for your desktop.

Yes I would like to make a tiny pop-up window widget

Building a desktop widget is incredibly rewarding. To do this, we need to bridge the gap between two worlds: the background Bluetooth task (listening to your sensor) and the graphical user interface (drawing the window on your screen).

Because these two tasks run at different speeds, we will use Python's built-in tkinter for the user interface, and run your Bluetooth code in a separate "background thread."

Here is the complete, ready-to-run code to create a sleek, "always-on-top" dark-mode widget.

The Desktop Widget Script
Create a new file called widget.py in your project folder, paste the code below, and run it with python widget.py.

(Note: It is using the exact MAC address you found earlier, so it will connect instantly).

Python
import asyncio
import threading
import tkinter as tk
from bleak import BleakClient

# Your specific sensor
TARGET_ADDRESS = "A4:C1:38:87:3F:10"
DATA_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"

# Global variables to pass data between the Bluetooth thread and the GUI
latest_temp = "Loading..."
latest_hum = "--"

def notification_handler(sender, data):
    """Decodes the sensor data and updates the global variables."""
    global latest_temp, latest_hum
    temp_int = int.from_bytes(data[0:2], byteorder='little')
    
    # Format the numbers nicely
    latest_temp = f"{temp_int / 100.0:.1f}°C"
    latest_hum = f"{data[2]}%"

async def ble_task():
    """The background task that constantly listens to the sensor."""
    try:
        async with BleakClient(TARGET_ADDRESS) as client:
            await client.start_notify(DATA_UUID, notification_handler)
            # Keep listening forever
            while True:
                await asyncio.sleep(1)
    except Exception as e:
        global latest_temp
        latest_temp = "Connection Lost"
        print(f"BLE Error: {e}")

def start_ble_thread():
    """Wrapper to run the asynchronous BLE task in a separate thread."""
    asyncio.run(ble_task())

# ==========================================
# GUI SETUP (Tkinter)
# ==========================================

# Create the main window
root = tk.Tk()
root.title("Room Climate")
root.geometry("180x80")          # Set a tiny window size
root.attributes('-topmost', True) # Keep the widget on top of all other windows
root.configure(bg='#1e1e1e')      # Dark mode background color

# Define custom fonts
LARGE_FONT = ("Helvetica", 20, "bold")
SMALL_FONT = ("Helvetica", 11)

# Create the text labels (blue for temp, green for humidity)
temp_label = tk.Label(root, text=latest_temp, font=LARGE_FONT, fg="#4fc3f7", bg="#1e1e1e")
temp_label.pack(pady=(10, 0)) # Add a little padding at the top

hum_label = tk.Label(root, text=f"Humidity: {latest_hum}", font=SMALL_FONT, fg="#a5d6a7", bg="#1e1e1e")
hum_label.pack()

def update_gui():
    """Refreshes the GUI with the latest data from the Bluetooth thread."""
    temp_label.config(text=latest_temp)
    
    if latest_hum != "--":
        hum_label.config(text=f"Humidity: {latest_hum}")
        
    # Tell Tkinter to run this function again in 1000 milliseconds (1 second)
    root.after(1000, update_gui)

# 1. Start the Bluetooth background thread (Daemon=True means it closes when you close the app)
threading.Thread(target=start_ble_thread, daemon=True).start()

# 2. Start the GUI refresh loop
update_gui()

# 3. Launch the window
root.mainloop()
What This Script Does
Always on Top: root.attributes('-topmost', True) ensures your widget floats above your web browser, code editor, or whatever else you are working on.

Daemon Threads: By setting daemon=True on the background thread, it guarantees that when you click the "X" to close the graphical window, the Python script fully stops and releases your Bluetooth connection cleanly.

Decoupled Architecture: Tkinter handles drawing the window, while Bleak silently updates the variables in the background. Every 1 second, the UI simply peeks at those variables and updates the screen.

and how to start it ?

To start your new desktop widget, you will run it through your terminal just like you did with the previous scripts.

Here is exactly how to open and launch it:

Step 1: Save the Code
Make sure you have copied the widget code from the previous message and saved it inside your project folder (C:\Users\kalre\OneDrive\Desktop\TempSensor) with the exact name widget.py.

Step 2: Run the Command
Open your PowerShell or Command Prompt terminal to your project folder and run:

PowerShell
python widget.py
What to Expect When It Starts:
A small, dark-mode window (180x80 pixels) will pop up on your screen.

For the first few seconds, it will say "Loading..." while your PC reaches out to connect to the sensor.

Once the connection is established and the sensor broadcasts its next update, the text will turn bright blue and show your live temperature, with the humidity listed in green below it.

Because of the "always-on-top" setting, you can drag that tiny window anywhere on your screen (like a corner of your monitor), and it will stay floating on top of your web browser, games, or work files while you use your PC.

How to Close It:
Whenever you want to stop the widget, simply click the standard "X" button in the top corner of the small pop-up window. The script will automatically shut down the background Bluetooth connection and close cleanly.

Lets modify this and make it more

I have l-connect 3 software

which monitors my PC stats

GPU, CPU and all

I think it is connected via blutooth because I have to have a blutooth dongle attached to my pc at all times to make it show values but I may be wrong

can we include these as well in the widget

and for the widget

is it possible to make it in the task bar near the clock and date ? and show by defult the temprature sensor values and once clickec the widget will open ?

First, a quick hardware mystery solved! The dongle you have attached to your PC for L-Connect 3 is actually a proprietary 2.4GHz wireless receiver (the Lian Li L-Wireless Sync), not standard Bluetooth. Lian Li uses this closed radio frequency to talk to your fans and screens securely.

Because it's a closed system, we can't easily intercept it—but the good news is, we don't need to. Python can completely bypass L-Connect 3 and ask Windows for your CPU and GPU stats directly.

We can absolutely upgrade your widget to sit in the system tray (near the clock), monitor your PC stats, and hide/show when clicked.

Step 1: Install the New Libraries
To read PC stats and build a system tray icon, we need a few extra Python packages. Open your terminal and run:

PowerShell
pip install psutil GPUtil pystray pillow
Note: psutil checks your CPU, GPUtil checks your GPU (works best with Nvidia), and pystray alongside pillow handles the taskbar icon.

Step 2: The Ultimate Taskbar Widget Script
Replace the code in your widget.py file with this upgraded version.

How it works now:

When you run it, the window will appear. If you click the "X", it no longer closes the app—it minimizes it to your system tray.

A small icon will appear near your Windows clock.

By default, if you hover your mouse over that tray icon, a tooltip will pop up showing: Room: 25.9°C | GPU: 45.0°C.

If you click the tray icon, the full dashboard window opens back up.

Python
import asyncio
import threading
import tkinter as tk
import psutil
import GPUtil
import pystray
from PIL import Image
from bleak import BleakClient
import sys

# --- Configuration ---
TARGET_ADDRESS = "A4:C1:38:87:3F:10"
DATA_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"

# Global Variables
latest_temp = "Wait..."
latest_hum = "--"
tray_icon = None

# ==========================================
# 1. BLUETOOTH SENSOR LOGIC
# ==========================================
def notification_handler(sender, data):
    global latest_temp, latest_hum
    temp_int = int.from_bytes(data[0:2], byteorder='little')
    latest_temp = f"{temp_int / 100.0:.1f}°C"
    latest_hum = f"{data[2]}%"

async def ble_task():
    try:
        async with BleakClient(TARGET_ADDRESS) as client:
            await client.start_notify(DATA_UUID, notification_handler)
            while True:
                await asyncio.sleep(1)
    except Exception as e:
        global latest_temp
        latest_temp = "BLE Error"

def start_ble_thread():
    asyncio.run(ble_task())

# ==========================================
# 2. PC STATS LOGIC
# ==========================================
def get_pc_stats():
    """Fetches CPU usage and GPU temperature."""
    cpu_usage = psutil.cpu_percent()
    gpus = GPUtil.getGPUs()
    # If a compatible GPU is found, get temp. Otherwise return N/A.
    gpu_temp = f"{gpus[0].temperature}°C" if gpus else "N/A"
    return cpu_usage, gpu_temp

# ==========================================
# 3. GUI SETUP (Tkinter)
# ==========================================
root = tk.Tk()
root.title("System & Climate")
root.geometry("200x130")
root.attributes('-topmost', True)
root.configure(bg='#1e1e1e')

# Instead of closing the app when 'X' is clicked, hide it to the tray
root.protocol('WM_DELETE_WINDOW', lambda: root.withdraw())

# Fonts
LARGE_FONT = ("Helvetica", 16, "bold")
SMALL_FONT = ("Helvetica", 10)

# Labels
temp_label = tk.Label(root, text=latest_temp, font=LARGE_FONT, fg="#4fc3f7", bg="#1e1e1e")
temp_label.pack(pady=(5, 0))

hum_label = tk.Label(root, text=f"Humidity: {latest_hum}", font=SMALL_FONT, fg="#a5d6a7", bg="#1e1e1e")
hum_label.pack()

cpu_label = tk.Label(root, text="CPU: --%", font=SMALL_FONT, fg="#ffb74d", bg="#1e1e1e")
cpu_label.pack(pady=(5,0))

gpu_label = tk.Label(root, text="GPU: --°C", font=SMALL_FONT, fg="#ef5350", bg="#1e1e1e")
gpu_label.pack()

def update_gui():
    """Refreshes the GUI and the Taskbar Icon Tooltip."""
    cpu_usage, gpu_temp = get_pc_stats()
    
    # Update Window Text
    temp_label.config(text=latest_temp)
    if latest_hum != "--":
        hum_label.config(text=f"Humidity: {latest_hum}")
    
    cpu_label.config(text=f"CPU Usage: {cpu_usage}%")
    gpu_label.config(text=f"GPU Temp: {gpu_temp}")
    
    # Update System Tray Hover Text
    if tray_icon:
        tray_icon.title = f"Room: {latest_temp} | GPU: {gpu_temp}"
        
    root.after(1000, update_gui)

# ==========================================
# 4. SYSTEM TRAY LOGIC (Pystray)
# ==========================================
def show_window(icon, item):
    """Unhides the window when the tray icon is clicked."""
    root.after(0, root.deiconify)

def exit_app(icon, item):
    """Fully kills the app."""
    icon.stop()
    root.destroy()
    sys.exit()

def setup_tray():
    global tray_icon
    # Create a simple blue square icon for the system tray
    image = Image.new('RGB', (64, 64), color='#4fc3f7')
    
    # Create right-click menu
    menu = pystray.Menu(
        pystray.MenuItem('Open Dashboard', show_window, default=True),
        pystray.MenuItem('Exit', exit_app)
    )
    
    tray_icon = pystray.Icon("Climate", image, "Initializing...", menu)
    tray_icon.run()

# ==========================================
# START EVERYTHING
# ==========================================
# Start background threads
threading.Thread(target=start_ble_thread, daemon=True).start()
threading.Thread(target=setup_tray, daemon=True).start()

# Start main loop
update_gui()
root.mainloop()
How to Use It
Run python widget.py.

The UI will appear with your Xiaomi room data, plus your CPU usage and GPU temperature.

Click the "X" on the window. It will disappear, but the script keeps running.

Look in your Windows Taskbar (you might need to click the ^ arrow to see hidden icons). You will see a small blue square.

Hover over the square to instantly see your room and GPU temp without clicking anything.

Click the square to bring the dashboard back to the center of your screen.

Python script to read GPU temperatures
This video walks through how the GPUtil library operates under the hood to pull accurate temperature readings from your graphics card.

PS C:\Users\kalre\OneDrive\Desktop\TempSensor> python widget.py

Traceback (most recent call last):

  File "C:\Users\kalre\OneDrive\Desktop\TempSensor\widget.py", line 5, in <module>

    import GPUtil

  File "C:\Users\kalre\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages\GPUtil\__init__.py", line 33, in <module>

    from .GPUtil import GPU, getGPUs, getAvailable, getAvailability, getFirstAvailable, showUtilization, __version__

  File "C:\Users\kalre\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages\GPUtil\GPUtil.py", line 34, in <module>

    from distutils import spawn

ModuleNotFoundError: No module named 'distutils'

PS C:\Users\kalre\OneDrive\Desktop\TempSensor> 

Ah, you have run into a classic Python version clash!

Here is exactly what happened: You are using a brand new version of Python (3.13). However, starting in Python 3.12, the developers permanently removed an old foundational tool called distutils. The GPUtil library hasn't been updated in years, so it is still blindly searching for that deleted tool and crashing your script before it even starts.

Instead of trying to fix a broken library, we are going to drop GPUtil entirely. Assuming you have an NVIDIA graphics card, Windows actually has a built-in monitoring tool called nvidia-smi that Python can talk directly to behind the scenes. This is much cleaner and doesn't require any outdated third-party downloads.

The Fix
You do not need to install anything new. Just replace the code in your widget.py file with this updated version:

Python
import asyncio
import threading
import tkinter as tk
import psutil
import pystray
import subprocess
from PIL import Image
from bleak import BleakClient
import sys

# --- Configuration ---
TARGET_ADDRESS = "A4:C1:38:87:3F:10"
DATA_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"

# Global Variables
latest_temp = "Wait..."
latest_hum = "--"
tray_icon = None

# ==========================================
# 1. BLUETOOTH SENSOR LOGIC
# ==========================================
def notification_handler(sender, data):
    global latest_temp, latest_hum
    temp_int = int.from_bytes(data[0:2], byteorder='little')
    latest_temp = f"{temp_int / 100.0:.1f}°C"
    latest_hum = f"{data[2]}%"

async def ble_task():
    try:
        async with BleakClient(TARGET_ADDRESS) as client:
            await client.start_notify(DATA_UUID, notification_handler)
            while True:
                await asyncio.sleep(1)
    except Exception as e:
        global latest_temp
        latest_temp = "BLE Error"

def start_ble_thread():
    asyncio.run(ble_task())

# ==========================================
# 2. PC STATS LOGIC (Fixed for Python 3.13)
# ==========================================
def get_pc_stats():
    """Fetches CPU usage and GPU temperature natively without GPUtil."""
    cpu_usage = psutil.cpu_percent()
    
    try:
        # Ask Windows for the NVIDIA GPU temp directly in the background
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW # Prevents a black cmd box from flashing
        )
        gpu_temp = f"{result.stdout.strip()}°C"
    except Exception:
        gpu_temp = "N/A" # Fallback if you are using AMD or Intel integrated graphics
        
    return cpu_usage, gpu_temp

# ==========================================
# 3. GUI SETUP (Tkinter)
# ==========================================
root = tk.Tk()
root.title("System & Climate")
root.geometry("200x130")
root.attributes('-topmost', True)
root.configure(bg='#1e1e1e')

# Hide to tray instead of closing
root.protocol('WM_DELETE_WINDOW', lambda: root.withdraw())

# Fonts
LARGE_FONT = ("Helvetica", 16, "bold")
SMALL_FONT = ("Helvetica", 10)

# Labels
temp_label = tk.Label(root, text=latest_temp, font=LARGE_FONT, fg="#4fc3f7", bg="#1e1e1e")
temp_label.pack(pady=(5, 0))

hum_label = tk.Label(root, text=f"Humidity: {latest_hum}", font=SMALL_FONT, fg="#a5d6a7", bg="#1e1e1e")
hum_label.pack()

cpu_label = tk.Label(root, text="CPU: --%", font=SMALL_FONT, fg="#ffb74d", bg="#1e1e1e")
cpu_label.pack(pady=(5,0))

gpu_label = tk.Label(root, text="GPU: --°C", font=SMALL_FONT, fg="#ef5350", bg="#1e1e1e")
gpu_label.pack()

def update_gui():
    """Refreshes the GUI and the Taskbar Icon Tooltip."""
    cpu_usage, gpu_temp = get_pc_stats()
    
    # Update Window Text
    temp_label.config(text=latest_temp)
    if latest_hum != "--":
        hum_label.config(text=f"Humidity: {latest_hum}")
    
    cpu_label.config(text=f"CPU: {cpu_usage}%")
    
    if gpu_temp and gpu_temp != "°C":
        gpu_label.config(text=f"GPU: {gpu_temp}")
    else:
        gpu_label.config(text="GPU: N/A")
    
    # Update System Tray Hover Text
    if tray_icon:
        tray_icon.title = f"Room: {latest_temp} | GPU: {gpu_temp}"
        
    root.after(1000, update_gui)

# ==========================================
# 4. SYSTEM TRAY LOGIC (Pystray)
# ==========================================
def show_window(icon, item):
    """Unhides the window when the tray icon is clicked."""
    root.after(0, root.deiconify)

def exit_app(icon, item):
    """Fully kills the app."""
    icon.stop()
    root.destroy()
    sys.exit()

def setup_tray():
    global tray_icon
    image = Image.new('RGB', (64, 64), color='#4fc3f7')
    
    menu = pystray.Menu(
        pystray.MenuItem('Open Dashboard', show_window, default=True),
        pystray.MenuItem('Exit', exit_app)
    )
    
    tray_icon = pystray.Icon("Climate", image, "Initializing...", menu)
    tray_icon.run()

# ==========================================
# START EVERYTHING
# ==========================================
threading.Thread(target=start_ble_thread, daemon=True).start()
threading.Thread(target=setup_tray, daemon=True).start()

update_gui()
root.mainloop()
Run python widget.py again. It should bypass the broken library completely and correctly load your real-time stats alongside your room environment!

Python Read GPU Temp Tutorial
This video demonstrates the older GPUtil method, which is useful to reference if you ever find yourself working in older Python 3.9/3.10 environments where the library still functions normally.

Let the widget show the following when clicked on

* CPU Temprature

* CPU Usage

* GPU temprature

* GPU usage

* Ram Temprature

* Ram Usage

* Disk Temprature

* Disk Usage

* Fan Speeds (each fan in the pc, its name and its speed)

* Mi Temprator sensor values listed as Electrical Connection Temp and Humidity

This widget will show in the task bar by defult and the values are the electrical connection Temp on top and humidity on buttom (Small foot print)

once this is clicked - will show the dashboard of all the values in a very nicly desisgned dashboard

also, I need to add setting for alarms for any value threashold which will make the number value change color from any color to RED

So reserve red for alarm

Also, we will make a sound alarm threshold that the alarm will only sound when the temprature exceed a certin number. all this in the widget setting

To build a professional, multi-functional dashboard that lives in your system tray and monitors everything from your hardware to your Xiaomi sensor, we need to shift from a simple script to a modular Python application.

Because you have extensive monitoring requirements, we will use psutil (for system stats) and the standard tkinter library for the interface.

The Architecture Plan
The "Tray" App (The Mini Footprint): A small icon in the taskbar showing Temp and Humidity.

The Dashboard (The Full UI): A window that opens upon clicking, organized by tabs or sections for CPU, GPU, RAM, Disk, and Fans.

Alarm System: A background thread constantly comparing values against user-defined thresholds, changing text to RED and triggering a system beep (\a) if limits are crossed.

Implementation Guide
To handle this, you will need to organize your code into a main class structure.

1. Monitoring All Hardware
Using psutil, you can access almost all system sensors.

CPU/RAM/Disk: Use psutil.cpu_percent(), psutil.virtual_memory().percent, and psutil.disk_usage('C:\\').

Fans & Temps: Use psutil.sensors_temperatures() and psutil.sensors_fans().

Note: psutil support depends on your motherboard's driver reporting to Windows. If it returns empty, you may need a helper like OpenHardwareMonitor (which exposes data via WMI/WMI-query).

2. Threshold Logic and Alarm
You should create a configuration dictionary to store your limits. The update loop will look like this:

Python
# Alarm Logic Example
THRESHOLD_TEMP = 80  # Celsius

def check_alarms(value, label_widget):
    if value > THRESHOLD_TEMP:
        label_widget.config(fg="red")  # Change color to RED
        print("\a")                    # Trigger system beep
    else:
        label_widget.config(fg="white") # Default color
3. Designing the Dashboard
Use the tkinter.ttk.Notebook widget to create a tabbed interface. This keeps the "small footprint" goal intact by hiding all the "heavy" data behind tabs like "System Stats" and "Room Sensors."

Key Components to Include
Feature	Library/Method
System Tray	pystray (handles the icon in the taskbar)
Hardware Stats	psutil (all-in-one system monitoring)
GUI	tkinter + ttk (for the tabbed dashboard)
Sound Alarm	winsound.Beep(frequency, duration) (Windows specific)
Refinement Checklist for Your Development
Settings Persistence: Since you want an "alarm threshold" setting, you should use a config.json file. This way, your thresholds aren't lost when you close the app.

Performance: Do not poll hardware sensors faster than once per second. Sensors like disk usage or fan speeds can be "heavy" to read; reading them 60 times a second will slow down your PC.

GPU Monitoring: As we discovered, some libraries are outdated. If psutil doesn't pick up your GPU sensors, use subprocess to call nvidia-smi as we did in the previous step, as it is the most reliable way to get NVIDIA stats on modern Python versions.

Next Steps
Would you like me to provide a template for the "Tabbed Dashboard" structure so you can start adding the layout for your CPU, GPU, RAM, and Disk sections? This will give you the framework to plug in each specific sensor reading.

Ok, for temprature alarm, what do you think is the best threashold

Context: I have clustered all my computer electrical wire connections in one small confined space in my desk to wire managment

so now I have all my equipment (2 monitors, PC, The desk motor, and an extension with 3 power points and 2 USBs all connected to a phillips 5 power point extension cord which in turn is connected to single wall socket)

I now my power draw is low, since my PSU is 850W and desk motor is not alwyas on (only when I want to adjust desk height) and not sure how much my monitors are drawing

and for the 3 points are not used regulary but mainly for charging phone or small devices

thats why I have added to temprature sensor to see if there is any problems with this set up

Setting an alarm for your wire management "cluster" is a smart move. Because you are measuring the ambient air temperature inside a confined space rather than the temperature of a specific wire's conductor, you need to set your thresholds carefully to avoid "false alarms" while still catching real heat buildup.

Recommended Thresholds
Since your sensor is likely measuring the air temperature inside the desk enclosure, here is how you should tier your alarms:

Warning (Yellow Alert): 40°C (104°F)

Reasoning: As noted by industry standards for electrical enclosures, the "safe" operating range is generally below 35–40°C. If your enclosure hits 40°C, it means your heat management (airflow) is insufficient for the equipment inside. This isn't a fire risk yet, but it is an "efficiency risk" that will shorten the lifespan of your power bricks and electronics.

Critical (RED Alert + Sound Alarm): 50°C (122°F)

Reasoning: If the air temperature in your wire cluster reaches 50°C, you are entering a danger zone. At this temperature, the internal components (like the capacitors inside your power bricks) are being severely stressed. This is the point where you should immediately investigate the setup, check for the "burnt plastic" smell, and ensure nothing is physically touching a heat source.

Important Safety Tips for Your "Cluster"
Since you are grouping power sources, keep these three physical rules in mind to keep that temperature low:

Avoid the "Coil Effect": Never coil up excess length of power cords. When a cable is coiled, it acts like an induction heater, especially under load. Keep cables as straight as possible, even if they are bundled together.

Airflow is King: Even a tiny amount of passive ventilation helps. If your desk enclosure is a "box," drill a few holes near the top and bottom to create a convection current. Heat rises; let it escape.

Check for "Hot Spots": The air temperature sensor is great, but once a week, touch the power bricks and the extension cord plug. If any of them are too hot to hold for a few seconds, you have a high-resistance connection or an overloaded device. That is a fire hazard regardless of what your sensor says.

Implementing the Alarm in Python
In your widget.py, you can add a simple check in your update_gui function to trigger the Windows system beep. Here is a snippet to add:

Python
import winsound # Add this at the top

# Inside your update_gui function:
def update_gui():
    # ... existing code ...
    
    # Check for Temp Alarm
    # Assuming latest_temp is a string like "25.9°C", we convert it to a float
    try:
        current_temp = float(latest_temp.replace('°C', ''))
        if current_temp >= 50.0:
            temp_label.config(fg="red") # Make the text RED
            winsound.Beep(1000, 500)    # Trigger a 1000Hz tone for 0.5 seconds
        else:
            temp_label.config(fg="#4fc3f7") # Revert to blue
    except:
        pass
    
    root.after(1000, update_gui)
By keeping your alert at 50°C, you provide yourself enough "headroom" to avoid constant beeping on a hot summer day, while still being warned well before you reach the 60°C+ limits where PVC insulation begins to soften.

Electrical Wire Temperature Ratings Explained

This video explains the standard temperature ratings for common electrical wiring and why maintaining these limits is critical for fire safety.