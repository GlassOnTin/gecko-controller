#!/usr/bin/env python3
# gecko_controller/web/app.py
from flask import Flask, render_template, jsonify, request
import os
import re
import csv
from datetime import datetime, timedelta
import pkg_resources
import shutil
import importlib.util
import sys
from typing import Dict, Any, Tuple
import time

app = Flask(__name__)
app.template_folder = pkg_resources.resource_filename('gecko_controller.web', 'templates')

CONFIG_FILE = '/etc/gecko-controller/config.py'
BACKUP_FILE = '/etc/gecko-controller/config.py.bak'
LOG_FILE = '/var/log/gecko-controller/readings.csv'

# Define all required fields and their types
REQUIRED_CONFIG = {
    # Display I2C
    'DISPLAY_ADDRESS': ('int', lambda x: 0 <= x <= 127),  # Valid I2C address range
    
    # GPIO Pins
    'LIGHT_RELAY': ('int', lambda x: 0 <= x <= 27),  # Valid GPIO range for RPi
    'HEAT_RELAY': ('int', lambda x: 0 <= x <= 27),
    'DISPLAY_RESET': ('int', lambda x: 0 <= x <= 27),
    
    # Temperature Settings
    'MIN_TEMP': ('float', lambda x: 10.0 <= x <= 40.0),  # Reasonable temp range
    'DAY_TEMP': ('float', lambda x: 15.0 <= x <= 40.0),
    'TEMP_TOLERANCE': ('float', lambda x: 0.1 <= x <= 5.0),
    
    # Time Settings
    'LIGHT_ON_TIME': ('time_str', lambda x: bool(re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', x))),
    'LIGHT_OFF_TIME': ('time_str', lambda x: bool(re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', x))),
    
    # UV Thresholds
    'UVA_THRESHOLDS': ('dict', lambda x: isinstance(x, dict) and 
                       all(k in x for k in ['low', 'high']) and 
                       all(isinstance(v, (int, float)) for v in x.values()) and 
                       0 <= x['low'] <= x['high'] <= 1000),
    'UVB_THRESHOLDS': ('dict', lambda x: isinstance(x, dict) and 
                       all(k in x for k in ['low', 'high']) and 
                       all(isinstance(v, (int, float)) for v in x.values()) and 
                       0 <= x['low'] <= x['high'] <= 100),
    
    # UV View Factor Correction
    'SENSOR_HEIGHT': ('float', lambda x: 0.0 <= x <= 1.0),
    'LAMP_DIST_FROM_BACK': ('float', lambda x: 0.0 <= x <= 1.0),
    'ENCLOSURE_HEIGHT': ('float', lambda x: 0.0 <= x <= 2.0),
    'SENSOR_ANGLE': ('float', lambda x: 0 <= x <= 360)
}

class ConfigValidationError(Exception):
    """Custom exception for config validation failures"""
    pass

def validate_config_module(module) -> bool:
    """Validate that all required fields are present and of correct type"""
    for field, (expected_type, validator) in REQUIRED_CONFIG.items():
        if not hasattr(module, field):
            raise ConfigValidationError(f"Missing required field: {field}")
            
        value = getattr(module, field)
        
        # Type validation
        if expected_type == 'int':
            if not isinstance(value, int):
                raise ConfigValidationError(f"Field {field} must be an integer")
        elif expected_type == 'float':
            if not isinstance(value, (int, float)):
                raise ConfigValidationError(f"Field {field} must be a number")
            value = float(value)
        elif expected_type == 'time_str':
            if not isinstance(value, str):
                raise ConfigValidationError(f"Field {field} must be a time string (HH:MM)")
        elif expected_type == 'dict':
            if not isinstance(value, dict):
                raise ConfigValidationError(f"Field {field} must be a dictionary")
                
        # Value validation
        if not validator(value):
            raise ConfigValidationError(f"Invalid value for {field}: {value}")
            
    # Additional validation: ensure DAY_TEMP > MIN_TEMP
    if module.DAY_TEMP <= module.MIN_TEMP:
        raise ConfigValidationError("DAY_TEMP must be greater than MIN_TEMP")
            
    return True

def create_config_content(config: Dict[str, Any]) -> str:
    """Generate config file content with comments"""
    lines = [
        "# Gecko Controller Configuration File",
        "# This file will be installed to /etc/gecko-controller/config.py",
        "# You can modify these values to customize your gecko enclosure settings",
        "# The service must be restarted after changes: sudo systemctl restart gecko-controller",
        "",
        "# Display I2C",
        f"DISPLAY_ADDRESS = {config['DISPLAY_ADDRESS']}",
        "",
        "# GPIO Pins",
        f"LIGHT_RELAY = {config['LIGHT_RELAY']}",
        f"HEAT_RELAY = {config['HEAT_RELAY']}",
        f"DISPLAY_RESET = {config['DISPLAY_RESET']}",
        "",
        "# Temperature Settings",
        f"MIN_TEMP = {config['MIN_TEMP']}",
        f"DAY_TEMP = {config['DAY_TEMP']}",
        f"TEMP_TOLERANCE = {config['TEMP_TOLERANCE']}",
        "",
        "# Time Settings",
        f'LIGHT_ON_TIME = "{config["LIGHT_ON_TIME"]}"',
        f'LIGHT_OFF_TIME = "{config["LIGHT_OFF_TIME"]}"',
        "",
        "# UV Thresholds # μW/cm²",
        f"UVA_THRESHOLDS = {config['UVA_THRESHOLDS']}",
        f"UVB_THRESHOLDS = {config['UVB_THRESHOLDS']}",
        "",
        "# UV View Factor Correction",
        f"SENSOR_HEIGHT = {config['SENSOR_HEIGHT']}",
        f"LAMP_DIST_FROM_BACK = {config['LAMP_DIST_FROM_BACK']}",
        f"ENCLOSURE_HEIGHT = {config['ENCLOSURE_HEIGHT']}",
        f"SENSOR_ANGLE = {config['SENSOR_ANGLE']}"
    ]
    return "\n".join(lines)

def load_config_module(config_path: str) -> Tuple[Any, bool]:
    """Load and validate a Python config module"""
    try:
        spec = importlib.util.spec_from_file_location("config", config_path)
        if spec is None or spec.loader is None:
            return None, False
            
        module = importlib.util.module_from_spec(spec)
        sys.modules["config"] = module  # This ensures proper importing
        spec.loader.exec_module(module)
        
        # Validate the loaded config
        validate_config_module(module)
        return module, True
    except Exception as e:
        print(f"Error loading config from {config_path}: {str(e)}")
        return None, False

def create_backup() -> bool:
    """Create a backup of the current config file"""
    try:
        shutil.copy2(CONFIG_FILE, BACKUP_FILE)
        return True
    except Exception as e:
        print(f"Failed to create backup: {str(e)}")
        return False

def restore_backup() -> bool:
    """Restore config from backup file"""
    try:
        if os.path.exists(BACKUP_FILE):
            shutil.copy2(BACKUP_FILE, CONFIG_FILE)
            return True
        return False
    except Exception as e:
        print(f"Failed to restore backup: {str(e)}")
        return False

def write_config(config: Dict[str, Any]) -> bool:
    """Write config back to file with backup and validation"""
    # Create backup first
    if not create_backup():
        raise ConfigValidationError("Failed to create backup, aborting config update")

    try:
        # Generate the new config file content
        content = create_config_content(config)
        
        # Write the new config file
        with open(CONFIG_FILE, 'w') as f:
            f.write(content)
            
        # Validate the new config
        module, success = load_config_module(CONFIG_FILE)
        if not success:
            raise ConfigValidationError("New config file failed validation")
            
        return True
        
    except Exception as e:
        # Restore backup if anything goes wrong
        restore_backup()
        raise ConfigValidationError(f"Failed to update config: {str(e)}")

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration with validation and rollback"""
    try:
        new_config = request.get_json()
        
        # Verify all required fields are present
        missing_fields = [field for field in REQUIRED_CONFIG.keys() if field not in new_config]
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Write and validate new config
        if write_config(new_config):
            # Wait briefly to ensure file is written
            time.sleep(0.5)
            # Restart the gecko-controller service to apply changes
            os.system('systemctl restart gecko-controller')
            return jsonify({'status': 'success'})
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to update configuration'
            }), 500
            
    except ConfigValidationError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/api/config/restore', methods=['POST'])
def restore_config():
    """Endpoint to restore config from backup"""
    try:
        if restore_backup():
            time.sleep(0.5)  # Wait briefly to ensure file is restored
            os.system('systemctl restart gecko-controller')
            return jsonify({'status': 'success'})
        return jsonify({
            'status': 'error',
            'message': 'No backup file found'
        }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def read_config() -> dict:
    """
    Read and validate the current configuration file.
    Returns a dictionary of configuration values or default values if the file cannot be read.
    """
    try:
        # Load and validate the config module
        module, success = load_config_module(CONFIG_FILE)
        
        if not success or module is None:
            raise ConfigValidationError("Failed to load configuration file")
            
        # Convert config module attributes to dictionary
        config = {}
        for field in REQUIRED_CONFIG.keys():
            value = getattr(module, field)
            
            # Handle special cases for formatting
            if field == 'DISPLAY_ADDRESS':
                # Convert integer to hex string format
                config[field] = f"0x{value:02x}"
            elif REQUIRED_CONFIG[field][0] == 'time_str':
                # Ensure time strings are in HH:MM format
                if isinstance(value, str):
                    try:
                        parsed_time = datetime.strptime(value, '%H:%M')
                        value = parsed_time.strftime('%H:%M')
                    except ValueError:
                        raise ConfigValidationError(f"Invalid time format for {field}: {value}")
                config[field] = value
            else:
                config[field] = value
            
        return config
        
    except Exception as e:
        print(f"Error reading config: {str(e)}")
        # Return default values as a fallback
        return {
            'DISPLAY_ADDRESS': '0x3c',  # Note: Now returning as hex string
            'LIGHT_RELAY': 17,
            'HEAT_RELAY': 18,
            'DISPLAY_RESET': 27,
            'MIN_TEMP': 20.0,
            'DAY_TEMP': 25.0,
            'TEMP_TOLERANCE': 0.5,
            'LIGHT_ON_TIME': '08:00',
            'LIGHT_OFF_TIME': '20:00',
            'UVA_THRESHOLDS': {'low': 100, 'high': 500},
            'UVB_THRESHOLDS': {'low': 10, 'high': 50},
            'SENSOR_HEIGHT': 0.15,
            'LAMP_DIST_FROM_BACK': 0.1,
            'ENCLOSURE_HEIGHT': 0.6,
            'SENSOR_ANGLE': 45
        }
        
def read_logs(hours=24):
    """Read the last N hours of log data"""
    data = {
        'timestamps': [],
        'temperature': [],
        'humidity': [],
        'uva': [],
        'uvb': [],
        'uvc': [],
        'light': [],
        'heat': []
    }
    
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with open(LOG_FILE, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    timestamp = datetime.strptime(row[0] + " " + row[1], '%Y-%m-%d %H:%M:%S.%f')
                                        
                    # Skip entries older than cutoff
                    if timestamp < cutoff_time:
                        continue
                        
                    data['timestamps'].append(timestamp.strftime('%H:%M'))  # Changed to hour:minute for cleaner display
                    data['temperature'].append(float(row[2]))
                    data['humidity'].append(float(row[3]))
                    data['uva'].append(float(row[4]))
                    data['uvb'].append(float(row[5]))
                    data['uvc'].append(float(row[6]))
                    data['light'].append(int(row[7]))
                    data['heat'].append(int(row[8]))
                except (ValueError, IndexError) as e:
                    print(f"Error parsing log entry: {e}")
                    continue
    except FileNotFoundError:
        print(f"Log file not found: {LOG_FILE}")
        pass
    except Exception as e:
        print(f"Error reading logs: {e}")
        pass
    
    return data

@app.route('/')
def index():
    """Render the main page"""
    config = read_config()
    return render_template('index.html', config=config)

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(read_config())

@app.route('/api/logs')
def get_logs():
    """Get log data"""
    hours = request.args.get('hours', default=24, type=int)
    print(f"/api/logs?hours={hours}")
    return jsonify(read_logs(hours))

def main():
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    main()