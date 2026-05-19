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