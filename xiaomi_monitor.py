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