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
    