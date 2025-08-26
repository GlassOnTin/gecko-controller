#!/usr/bin/env python3
"""
Clean up the test MQTT device from Home Assistant
"""

import paho.mqtt.client as mqtt
import time

def cleanup_test_device():
    """Remove the test device discovery configurations"""
    print("Removing test MQTT device from Home Assistant...")
    
    # Connect to broker
    client = mqtt.Client()
    client.username_pw_set("mqtt", "mqtt")
    
    try:
        client.connect("homeassistant.local", 1883, 60)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    
    # List of test device sensors to remove
    test_sensors = [
        "temperature", "humidity", "uva", "uvb", "uvc",
        "light_status", "heat_status", "target_temperature"
    ]
    
    # Clear each discovery topic by publishing empty retained message
    for sensor in test_sensors:
        topic = f"homeassistant/sensor/gecko_controller_test/{sensor}/config"
        result = client.publish(topic, "", retain=True)
        if result.rc == 0:
            print(f"✓ Cleared {sensor}")
        else:
            print(f"✗ Failed to clear {sensor}")
        time.sleep(0.1)
    
    # Also clear any state topics
    for sensor in test_sensors:
        topic = f"gecko/gecko_controller_test/{sensor}/state"
        client.publish(topic, "", retain=True)
    
    client.disconnect()
    print("\n✅ Test device removed!")
    print("You may need to restart Home Assistant or reload the MQTT integration")
    print("The production 'gecko_controller' device should remain active")

if __name__ == "__main__":
    cleanup_test_device()