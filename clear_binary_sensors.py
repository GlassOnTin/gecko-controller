#!/usr/bin/env python3
"""
Clear old binary sensor configs to update names and device classes
"""

import paho.mqtt.client as mqtt
import time

def clear_binary_sensors():
    """Clear binary sensor configs for renaming"""
    print("Clearing binary sensor configurations for update...")
    
    # Connect to broker
    client = mqtt.Client()
    client.username_pw_set("mqtt", "mqtt")
    
    try:
        client.connect("homeassistant.local", 1883, 60)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    
    # Clear binary sensor configurations to force re-creation with new names
    configs_to_clear = [
        "homeassistant/binary_sensor/gecko_controller/light_status/config",
        "homeassistant/binary_sensor/gecko_controller/heat_status/config"
    ]
    
    for topic in configs_to_clear:
        result = client.publish(topic, "", retain=True)
        if result.rc == 0:
            print(f"✓ Cleared: {topic}")
        else:
            print(f"✗ Failed to clear: {topic}")
        time.sleep(0.1)
    
    client.disconnect()
    print("\n✅ Configurations cleared!")
    print("Restart the service to create updated configurations")

if __name__ == "__main__":
    clear_binary_sensors()