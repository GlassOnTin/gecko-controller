#!/usr/bin/env python3
"""
Fix MQTT binary sensors by clearing old configs and republishing
"""

import paho.mqtt.client as mqtt
import time

def fix_binary_sensors():
    """Clear old sensor configs for light/heat status"""
    print("Fixing MQTT binary sensor configuration...")
    
    # Connect to broker
    client = mqtt.Client()
    client.username_pw_set("mqtt", "mqtt")
    
    try:
        client.connect("homeassistant.local", 1883, 60)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    
    # Clear old sensor configurations (wrong type)
    old_configs = [
        "homeassistant/sensor/gecko_controller/light_status/config",
        "homeassistant/sensor/gecko_controller/heat_status/config"
    ]
    
    for topic in old_configs:
        result = client.publish(topic, "", retain=True)
        if result.rc == 0:
            print(f"✓ Cleared old config: {topic}")
        else:
            print(f"✗ Failed to clear: {topic}")
        time.sleep(0.1)
    
    client.disconnect()
    print("\n✅ Old configurations cleared!")
    print("The service will create new binary_sensor configurations on restart")

if __name__ == "__main__":
    fix_binary_sensors()