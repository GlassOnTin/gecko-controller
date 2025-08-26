#!/usr/bin/env python3
"""
MQTT Home Assistant Auto-Discovery Module for Gecko Controller
Publishes sensor data to Home Assistant via MQTT with automatic discovery
"""

import json
import time
import logging
import threading
from typing import Dict, Optional, Any
import paho.mqtt.client as mqtt

class GeckoMQTTClient:
    def __init__(self, 
                 broker: str = "homeassistant.local",
                 port: int = 1883,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 topic_prefix: str = "gecko",
                 device_id: str = "gecko_controller"):
        """
        Initialize MQTT client with Home Assistant auto-discovery
        
        Args:
            broker: MQTT broker hostname/IP
            port: MQTT broker port
            username: MQTT username (optional)
            password: MQTT password (optional)
            topic_prefix: Topic prefix for state topics
            device_id: Unique device identifier
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix
        self.device_id = device_id
        
        # MQTT client setup
        self.client = mqtt.Client(client_id=f"{device_id}_client")
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        # Connection state
        self.connected = False
        self.connect_lock = threading.Lock()
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Device info for Home Assistant
        self.device_info = {
            "identifiers": [device_id],
            "name": "Gecko Vivarium Controller",
            "model": "Gecko Controller v1",
            "manufacturer": "DIY",
            "sw_version": "1.0.0"
        }
        
        # Binary sensor configurations (for on/off states)
        self.binary_sensors = {
            "light_status": {
                "name": "Light Relay",
                "device_class": "power",
                "icon": "mdi:lightbulb"
            },
            "heat_status": {
                "name": "Heat Relay",
                "device_class": "power",
                "icon": "mdi:radiator"
            }
        }
        
        # Regular sensor configurations (for measurements)
        self.sensors = {
            "temperature": {
                "name": "Vivarium Temperature",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "icon": "mdi:thermometer",
                "value_template": "{{ value }}",
                "state_class": "measurement"
            },
            "humidity": {
                "name": "Vivarium Humidity",
                "device_class": "humidity",
                "unit_of_measurement": "%",
                "icon": "mdi:water-percent",
                "value_template": "{{ value }}",
                "state_class": "measurement"
            },
            "uva": {
                "name": "UVA Level",
                "unit_of_measurement": "μW/cm²",
                "icon": "mdi:sun-wireless",
                "value_template": "{{ value }}",
                "state_class": "measurement"
            },
            "uvb": {
                "name": "UVB Level",
                "unit_of_measurement": "μW/cm²",
                "icon": "mdi:sun-wireless-outline",
                "value_template": "{{ value }}",
                "state_class": "measurement"
            },
            "uvc": {
                "name": "UVC Level",
                "unit_of_measurement": "μW/cm²",
                "icon": "mdi:radioactive",
                "value_template": "{{ value }}",
                "state_class": "measurement"
            },
            "target_temperature": {
                "name": "Target Temperature",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "icon": "mdi:thermometer-lines",
                "value_template": "{{ value }}",
                "state_class": "measurement"
            }
        }
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when client connects to broker"""
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            self.connected = True
            # Publish discovery messages after connection
            self._publish_discovery()
        else:
            self.logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when client disconnects from broker"""
        self.logger.warning(f"Disconnected from MQTT broker. Return code: {rc}")
        self.connected = False
        if rc != 0:
            # Unexpected disconnection, try to reconnect
            self._reconnect()
    
    def _reconnect(self):
        """Attempt to reconnect to broker"""
        max_retries = 5
        retry_delay = 5
        
        for i in range(max_retries):
            try:
                self.logger.info(f"Attempting to reconnect... ({i+1}/{max_retries})")
                self.client.reconnect()
                return
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")
                if i < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error("Maximum reconnection attempts reached")
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()  # Start background thread for network operations
            
            # Wait for connection (up to 10 seconds)
            for _ in range(10):
                if self.connected:
                    return True
                time.sleep(1)
            
            self.logger.error("Connection timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
        self.logger.info("Disconnected from MQTT broker")
    
    def _publish_discovery(self):
        """Publish Home Assistant MQTT discovery messages"""
        try:
            # Publish regular sensors
            for sensor_id, config in self.sensors.items():
                discovery_topic = f"homeassistant/sensor/{self.device_id}/{sensor_id}/config"
                state_topic = f"{self.topic_prefix}/{self.device_id}/{sensor_id}/state"
                
                payload = {
                    "name": config["name"],
                    "state_topic": state_topic,
                    "unique_id": f"{self.device_id}_{sensor_id}",
                    "device": self.device_info
                }
                
                # Add optional fields if present
                for field in ["device_class", "unit_of_measurement", "icon", 
                             "value_template", "state_class"]:
                    if field in config:
                        payload[field] = config[field]
                
                # Publish discovery message with retain flag
                result = self.client.publish(
                    discovery_topic,
                    json.dumps(payload),
                    qos=1,
                    retain=True
                )
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.debug(f"Published discovery for sensor {sensor_id}")
                else:
                    self.logger.error(f"Failed to publish discovery for sensor {sensor_id}")
                
                # Small delay between discovery messages
                time.sleep(0.1)
            
            # Publish binary sensors
            for sensor_id, config in self.binary_sensors.items():
                discovery_topic = f"homeassistant/binary_sensor/{self.device_id}/{sensor_id}/config"
                state_topic = f"{self.topic_prefix}/{self.device_id}/{sensor_id}/state"
                
                payload = {
                    "name": config["name"],
                    "state_topic": state_topic,
                    "unique_id": f"{self.device_id}_{sensor_id}",
                    "device": self.device_info,
                    "payload_on": "ON",
                    "payload_off": "OFF"
                }
                
                # Add optional fields if present
                for field in ["device_class", "icon"]:
                    if field in config:
                        payload[field] = config[field]
                
                # Publish discovery message with retain flag
                result = self.client.publish(
                    discovery_topic,
                    json.dumps(payload),
                    qos=1,
                    retain=True
                )
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.debug(f"Published discovery for binary_sensor {sensor_id}")
                else:
                    self.logger.error(f"Failed to publish discovery for binary_sensor {sensor_id}")
                
                # Small delay between discovery messages
                time.sleep(0.1)
                
            self.logger.info("Home Assistant discovery messages published")
            
        except Exception as e:
            self.logger.error(f"Error publishing discovery messages: {e}")
    
    def publish_data(self, data: Dict[str, Any]):
        """
        Publish sensor data to MQTT
        
        Args:
            data: Dictionary containing sensor readings
                  Expected keys: temperature, humidity, uva, uvb, uvc,
                                light_status, heat_status, target_temperature
        """
        if not self.connected:
            self.logger.warning("Not connected to MQTT broker, skipping publish")
            return False
        
        try:
            published_count = 0
            
            # Publish regular sensor values
            for key, value in data.items():
                if key in self.sensors and value is not None:
                    state_topic = f"{self.topic_prefix}/{self.device_id}/{key}/state"
                    
                    # Format value based on type
                    if isinstance(value, bool):
                        payload = "1" if value else "0"
                    elif isinstance(value, float):
                        payload = f"{value:.2f}"
                    else:
                        payload = str(value)
                    
                    result = self.client.publish(state_topic, payload, qos=1)
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        published_count += 1
                        self.logger.debug(f"Published {key}: {payload}")
                    else:
                        self.logger.error(f"Failed to publish {key}")
            
            # Publish binary sensor values
            for key, value in data.items():
                if key in self.binary_sensors and value is not None:
                    state_topic = f"{self.topic_prefix}/{self.device_id}/{key}/state"
                    
                    # Format binary value as ON/OFF
                    payload = "ON" if value else "OFF"
                    
                    result = self.client.publish(state_topic, payload, qos=1)
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        published_count += 1
                        self.logger.debug(f"Published {key}: {payload}")
                    else:
                        self.logger.error(f"Failed to publish {key}")
            
            self.logger.debug(f"Published {published_count} sensor values")
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing data: {e}")
            return False
    
    def publish_availability(self, available: bool = True):
        """
        Publish availability status
        
        Args:
            available: True if device is online, False if offline
        """
        if self.connected:
            availability_topic = f"{self.topic_prefix}/{self.device_id}/availability"
            status = "online" if available else "offline"
            self.client.publish(availability_topic, status, qos=1, retain=True)


def main():
    """Test the MQTT client with sample data"""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize client
    client = GeckoMQTTClient(
        broker="homeassistant.local",
        username="mqtt",
        password="mqtt"
    )
    
    # Connect to broker
    if client.connect():
        print("Connected successfully!")
        
        # Publish test data
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
        
        # Publish data every 10 seconds
        try:
            while True:
                client.publish_data(test_data)
                print(f"Published data: {test_data}")
                time.sleep(10)
                
                # Vary test data slightly
                test_data["temperature"] += 0.1
                test_data["humidity"] -= 0.2
                
        except KeyboardInterrupt:
            print("\nShutting down...")
            client.disconnect()
    else:
        print("Failed to connect to MQTT broker")


if __name__ == "__main__":
    main()