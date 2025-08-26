#!/usr/bin/env python3
"""
Test script for MQTT Home Assistant integration
"""

import sys
import os
import time

# Add the gecko_controller module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gecko_controller.mqtt_client import GeckoMQTTClient

def test_mqtt():
    """Test the MQTT connection and publish test data"""
    print("Testing MQTT Home Assistant integration...")
    
    # Create MQTT client
    client = GeckoMQTTClient(
        broker="homeassistant.local",
        username="mqtt",
        password="mqtt",
        topic_prefix="gecko",
        device_id="gecko_controller_test"
    )
    
    print(f"Connecting to MQTT broker at homeassistant.local...")
    
    # Connect to broker
    if not client.connect():
        print("❌ Failed to connect to MQTT broker")
        print("Please check:")
        print("  1. homeassistant.local is reachable")
        print("  2. MQTT broker is running")
        print("  3. Username/password are correct")
        return False
    
    print("✅ Connected successfully!")
    print("⏳ Waiting for discovery messages to be published...")
    time.sleep(2)
    
    # Test data
    test_data = {
        "temperature": 28.5,
        "humidity": 65.0,
        "uva": 45.2,
        "uvb": 3.8,
        "uvc": 0.1,
        "light_status": True,
        "heat_status": False,
        "target_temperature": 30.0
    }
    
    print("\nPublishing test data:")
    for key, value in test_data.items():
        print(f"  {key}: {value}")
    
    if client.publish_data(test_data):
        print("\n✅ Data published successfully!")
        print("\n📱 Check Home Assistant:")
        print("  1. Go to Settings -> Devices & Services -> MQTT")
        print("  2. Look for 'Gecko Vivarium Controller'")
        print("  3. You should see 8 sensors with current values")
        print("\nSensor entities should appear as:")
        print("  - sensor.gecko_vivarium_controller_temperature")
        print("  - sensor.gecko_vivarium_controller_humidity")
        print("  - sensor.gecko_vivarium_controller_uva_level")
        print("  - sensor.gecko_vivarium_controller_uvb_level")
        print("  - sensor.gecko_vivarium_controller_uvc_level")
        print("  - sensor.gecko_vivarium_controller_light_status")
        print("  - sensor.gecko_vivarium_controller_heat_status")
        print("  - sensor.gecko_vivarium_controller_target_temperature")
    else:
        print("❌ Failed to publish data")
        return False
    
    # Disconnect
    client.disconnect()
    print("\n✅ Test completed successfully!")
    return True

if __name__ == "__main__":
    test_mqtt()