#!/usr/bin/env python3
# gecko_controller/web/app.py
from flask import Flask, render_template, jsonify, request, send_from_directory
import os
import re
import csv
import sys
import time
import shutil
import stat
from datetime import datetime, timedelta
from pathlib import Path
import importlib.util
from typing import Dict, Any, Tuple
from typing import Tuple, Optional
import logging

def get_app_paths():
    """Determine the correct paths for templates and static files"""
    # In your main() function
    os.makedirs('/etc/gecko-controller', mode=0o755, exist_ok=True)
    os.makedirs('/var/log/gecko-controller', mode=0o755, exist_ok=True)

    # Check if we're running from the development directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dev_template_dir = os.path.join(current_dir, 'templates')
    dev_static_dir = os.path.join(current_dir, 'static')
    
    # Check if development directories exist
    if os.path.isdir(dev_template_dir) and os.path.isdir(dev_static_dir):
        return dev_template_dir, dev_static_dir
    
    # Fall back to installed package location
    try:
        import pkg_resources
        template_dir = pkg_resources.resource_filename('gecko_controller.web', 'templates')
        static_dir = pkg_resources.resource_filename('gecko_controller.web', 'static')
        return template_dir, static_dir
    except ImportError:
        # If all else fails, return the development paths anyway
        return dev_template_dir, dev_static_dir

# Initialize Flask app with correct paths
template_dir, static_dir = get_app_paths()
app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)

# Rest of your existing code remains the same...
CONFIG_FILE = '/etc/gecko-controller/config.py'
BACKUP_FILE = '/etc/gecko-controller/config.py.bak'
LOG_FILE = '/var/log/gecko-controller/readings.csv'

# Add some debugging information at startup
@app.before_first_request
def log_startup_info():
    app.logger.info(f'Current working directory: {os.getcwd()}')
    app.logger.info(f'Template folder: {app.template_folder}')
    app.logger.info(f'Static folder: {app.static_folder}')
    app.logger.info(f'Template folder exists: {os.path.exists(app.template_folder)}')
    app.logger.info(f'Static folder exists: {os.path.exists(app.static_folder)}')

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

class ConfigError(Exception):
    """Base exception for configuration errors"""
    pass

class ConfigPermissionError(ConfigError):
    """Raised when there are permission issues with config files"""
    pass

class ConfigBackupError(ConfigError):
    """Raised when backup operations fail"""
    pass

def check_file_permissions(path: str) -> Tuple[bool, Optional[str]]:
    """
    Check if we have read/write permissions for a file or its parent directory if it doesn't exist
    Returns: (has_permission, error_message)
    """
    try:
        path_obj = Path(path)
        
        # If file exists, check its permissions
        if path_obj.exists():
            # Check if we can read and write
            readable = os.access(path, os.R_OK)
            writable = os.access(path, os.W_OK)
            if not (readable and writable):
                return False, f"Insufficient permissions for {path}. Current permissions: {stat.filemode(path_obj.stat().st_mode)}"
                
        # If file doesn't exist, check parent directory permissions
        else:
            parent = path_obj.parent
            if not parent.exists():
                return False, f"Parent directory {parent} does not exist"
            if not os.access(parent, os.W_OK):
                return False, f"Cannot write to parent directory {parent}"
                
        return True, None
        
    except Exception as e:
        return False, f"Error checking permissions: {str(e)}"

def create_backup(config_file: str, backup_file: str, logger: logging.Logger) -> bool:
    """
    Create a backup of the config file with proper permission checking
    
    Args:
        config_file: Path to the main config file
        backup_file: Path to the backup location
        logger: Logger instance for recording operations
        
    Returns:
        bool: True if backup was successful
    
    Raises:
        ConfigPermissionError: If permission issues prevent backup
        ConfigBackupError: If backup fails for other reasons
    """
    try:
        # Check if source config exists
        if not os.path.exists(config_file):
            raise ConfigBackupError(f"Config file {config_file} does not exist")
            
        # Check permissions on source and destination
        src_ok, src_error = check_file_permissions(config_file)
        if not src_ok:
            raise ConfigPermissionError(f"Source file permission error: {src_error}")
            
        dst_ok, dst_error = check_file_permissions(backup_file)
        if not dst_ok:
            raise ConfigPermissionError(f"Destination file permission error: {dst_error}")
            
        # Create parent directory for backup if it doesn't exist
        backup_dir = os.path.dirname(backup_file)
        if not os.path.exists(backup_dir):
            try:
                os.makedirs(backup_dir, mode=0o755, exist_ok=True)
            except Exception as e:
                raise ConfigPermissionError(f"Failed to create backup directory: {str(e)}")
        
        # Perform the backup
        shutil.copy2(config_file, backup_file)
        
        # Verify the backup
        if not os.path.exists(backup_file):
            raise ConfigBackupError("Backup file was not created")
            
        # Ensure backup is readable
        if not os.access(backup_file, os.R_OK):
            raise ConfigPermissionError("Created backup file is not readable")
            
        logger.info(f"Successfully created backup at {backup_file}")
        return True
        
    except (ConfigPermissionError, ConfigBackupError) as e:
        logger.error(str(e))
        raise
    except Exception as e:
        msg = f"Unexpected error during backup: {str(e)}"
        logger.error(msg)
        raise ConfigBackupError(msg)

def restore_backup(config_file: str, backup_file: str, logger: logging.Logger) -> bool:
    """
    Restore config from backup with proper permission checking
    
    Args:
        config_file: Path to the main config file
        backup_file: Path to the backup location
        logger: Logger instance for recording operations
        
    Returns:
        bool: True if restoration was successful
    
    Raises:
        ConfigPermissionError: If permission issues prevent restoration
        ConfigBackupError: If restoration fails for other reasons
    """
    try:
        # Check if backup exists
        if not os.path.exists(backup_file):
            raise ConfigBackupError("No backup file found")
            
        # Check permissions
        src_ok, src_error = check_file_permissions(backup_file)
        if not src_ok:
            raise ConfigPermissionError(f"Backup file permission error: {src_error}")
            
        dst_ok, dst_error = check_file_permissions(config_file)
        if not dst_ok:
            raise ConfigPermissionError(f"Config file permission error: {dst_error}")
            
        # Perform the restoration
        shutil.copy2(backup_file, config_file)
        
        # Verify the restoration
        if not os.path.exists(config_file):
            raise ConfigBackupError("Config file was not restored")
            
        # Ensure restored file is readable
        if not os.access(config_file, os.R_OK):
            raise ConfigPermissionError("Restored config file is not readable")
            
        logger.info(f"Successfully restored config from {backup_file}")
        return True
        
    except (ConfigPermissionError, ConfigBackupError) as e:
        logger.error(str(e))
        raise
    except Exception as e:
        msg = f"Unexpected error during restoration: {str(e)}"
        logger.error(msg)
        raise ConfigBackupError(msg)

def write_config(config: Dict[str, Any], logger: Optional[logging.Logger] = None) -> bool:
    """
    Write config to file with atomic operation and validation
    
    Args:
        config: Dictionary containing configuration values
        logger: Optional logger instance for recording operations
    
    Returns:
        bool: True if write was successful
    
    Raises:
        ConfigPermissionError: If permission issues prevent writing
        ConfigValidationError: If the new config is invalid
    """
    # Use a null logger if none provided
    if logger is None:
        logger = logging.getLogger('null')
        logger.addHandler(logging.NullHandler())

    try:
        # First validate the new config values before writing anything
        for field, (expected_type, validator) in REQUIRED_CONFIG.items():
            if field not in config:
                raise ConfigValidationError(f"Missing required field: {field}")
                
            value = config[field]
            
            # Perform type checking
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
                    
            # Perform value validation
            if not validator(value):
                raise ConfigValidationError(f"Invalid value for {field}: {value}")
        
        # Check special case: DAY_TEMP > MIN_TEMP
        if config['DAY_TEMP'] <= config['MIN_TEMP']:
            raise ConfigValidationError("DAY_TEMP must be greater than MIN_TEMP")
            
        # Check permissions on config file
        ok, error = check_file_permissions(CONFIG_FILE)
        if not ok:
            raise ConfigPermissionError(f"Config file permission error: {error}")
            
        # Generate the new config content
        content = create_config_content(config)
        
        # Write to a temporary file first (atomic operation)
        temp_file = f"{CONFIG_FILE}.tmp"
        try:
            with open(temp_file, 'w') as f:
                f.write(content)
                # Ensure content is written to disk
                f.flush()
                os.fsync(f.fileno())
                
            # Set permissions on temp file to match intended config file
            os.chmod(temp_file, 0o644)
            
            # Atomically replace the old config with the new one
            os.replace(temp_file, CONFIG_FILE)
            
        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
            raise ConfigError(f"Failed to write config: {str(e)}")
            
        # Validate the newly written config
        module, success = load_config_module(CONFIG_FILE)
        if not success or module is None:
            raise ConfigValidationError("New config file failed validation after writing")
            
        logger.info("Successfully wrote and validated new configuration")
        return True
        
    except (ConfigValidationError, ConfigPermissionError) as e:
        logger.error(str(e))
        raise
    except Exception as e:
        msg = f"Unexpected error writing config: {str(e)}"
        logger.error(msg)
        raise ConfigError(msg)

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
        
        # Create backup first
        try:
            create_backup(CONFIG_FILE, BACKUP_FILE, app.logger)
        except ConfigPermissionError as e:
            return jsonify({
                'status': 'error',
                'message': f'Permission error: {str(e)}'
            }), 403
        except ConfigBackupError as e:
            return jsonify({
                'status': 'error',
                'message': f'Backup error: {str(e)}'
            }), 500
            
        # Write and validate new config
        try:
            if write_config(new_config, app.logger):
                time.sleep(0.5)
                os.system('systemctl restart gecko-controller')
                return jsonify({'status': 'success'})
        except ConfigValidationError as e:
            # Try to restore from backup
            try:
                restore_backup(CONFIG_FILE, BACKUP_FILE, app.logger)
                return jsonify({
                    'status': 'error',
                    'message': f'Config validation failed and restored from backup: {str(e)}'
                }), 400
            except (ConfigPermissionError, ConfigBackupError) as restore_error:
                return jsonify({
                    'status': 'error',
                    'message': f'Config validation failed and backup restoration also failed: {str(restore_error)}'
                }), 500
        except Exception as e:
            # Try to restore from backup
            try:
                restore_backup(CONFIG_FILE, BACKUP_FILE, app.logger)
                return jsonify({
                    'status': 'error',
                    'message': f'Config update failed and restored from backup: {str(e)}'
                }), 500
            except (ConfigPermissionError, ConfigBackupError) as restore_error:
                return jsonify({
                    'status': 'error',
                    'message': f'Config update failed and backup restoration also failed: {str(restore_error)}'
                }), 500
                
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500

@app.route('/api/config/restore', methods=['POST'])
def restore_config_endpoint():
    """
    Endpoint to restore config from backup with comprehensive validation and error handling
    
    Returns:
        JSON response indicating success or detailed error information
        HTTP status codes:
        - 200: Success
        - 403: Permission denied
        - 404: Backup not found
        - 500: Server error or validation failure
    """
    try:
        # First verify backup exists and is readable
        if not os.path.exists(BACKUP_FILE):
            return jsonify({
                'status': 'error',
                'message': 'No backup file found'
            }), 404

        # Pre-validate backup content before attempting restore
        module, success = load_config_module(BACKUP_FILE)
        if not success or module is None:
            return jsonify({
                'status': 'error',
                'message': 'Backup file failed validation, cannot restore'
            }), 500

        try:
            # Attempt to restore using the improved restore_backup function
            if restore_backup(CONFIG_FILE, BACKUP_FILE, app.logger):
                # Double check the restored config
                restored_module, restored_success = load_config_module(CONFIG_FILE)
                if not restored_success or restored_module is None:
                    # If validation fails after restore, try to recover
                    app.logger.error("Restored config failed validation")
                    return jsonify({
                        'status': 'error',
                        'message': 'Restored config failed validation'
                    }), 500

                # Brief pause to ensure file operations are complete
                time.sleep(0.5)
                
                try:
                    # Attempt to restart the service
                    result = os.system('systemctl restart gecko-controller')
                    if result != 0:
                        app.logger.warning("Service restart failed but config was restored")
                        return jsonify({
                            'status': 'partial',
                            'message': 'Config restored but service restart failed'
                        }), 500
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Configuration restored and service restarted'
                    })
                    
                except Exception as service_error:
                    app.logger.error(f"Service restart error: {str(service_error)}")
                    return jsonify({
                        'status': 'partial',
                        'message': 'Config restored but service restart failed'
                    }), 500

        except ConfigPermissionError as e:
            app.logger.error(f"Permission error during restore: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Permission denied: {str(e)}'
            }), 403
            
        except ConfigBackupError as e:
            app.logger.error(f"Backup error during restore: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Backup error: {str(e)}'
            }), 500
                
    except Exception as e:
        app.logger.error(f"Unexpected error in restore endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500

def get_service_status():
    """Helper function to check gecko-controller service status"""
    try:
        result = os.system('systemctl is-active --quiet gecko-controller')
        return result == 0
    except:
        return False

# Optional: Add a status endpoint to check service health
@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current service and config status"""
    try:
        config_exists = os.path.exists(CONFIG_FILE)
        backup_exists = os.path.exists(BACKUP_FILE)
        service_running = get_service_status()
        
        # Try to validate current config
        config_valid = False
        if config_exists:
            module, success = load_config_module(CONFIG_FILE)
            config_valid = success and module is not None
            
        return jsonify({
            'status': 'ok',
            'details': {
                'config_exists': config_exists,
                'config_valid': config_valid,
                'backup_exists': backup_exists,
                'service_running': service_running,
                'config_path': CONFIG_FILE,
                'backup_path': BACKUP_FILE
            }
        })
        
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
        
        # Create a list to store full timestamps and data
        entries = []
        
        with open(LOG_FILE, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    # Create full timestamp object for proper sorting
                    timestamp = datetime.strptime(row[0] + "." + row[1], '%Y-%m-%d %H:%M:%S.%f')
                    
                    # Skip entries older than cutoff
                    if timestamp < cutoff_time:
                        continue
                        
                    entries.append({
                        'timestamp': timestamp,
                        'display_time': timestamp.strftime('%H:%M'),
                        'temperature': float(row[2]),
                        'humidity': float(row[3]),
                        'uva': float(row[4]),
                        'uvb': float(row[5]),
                        'uvc': float(row[6]),
                        'light': int(row[7]),
                        'heat': int(row[8])
                    })
                    
                except (ValueError, IndexError) as e:
                    print(f"Error parsing log entry: {e}")
                    continue
                    
        # Sort entries by timestamp
        entries.sort(key=lambda x: x['timestamp'])
        
        # Fill the data arrays with sorted values
        for entry in entries:
            data['timestamps'].append(entry['display_time'])
            data['temperature'].append(entry['temperature'])
            data['humidity'].append(entry['humidity'])
            data['uva'].append(entry['uva'])
            data['uvb'].append(entry['uvb'])
            data['uvc'].append(entry['uvc'])
            data['light'].append(entry['light'])
            data['heat'].append(entry['heat'])
            
    except FileNotFoundError:
        print(f"Log file not found: {LOG_FILE}")
    except Exception as e:
        print(f"Error reading logs: {e}")
        
    return data

@app.route('/static/<path:path>')
def send_static(path):
    app.logger.debug(f'Static file requested: {path}')
    try:
        full_path = os.path.join(app.static_folder, path)
        app.logger.debug(f'Full path: {full_path}')
        app.logger.debug(f'File exists: {os.path.exists(full_path)}')
        return send_from_directory(app.static_folder, path)
    except Exception as e:
        app.logger.error(f'Error serving static file {path}: {str(e)}')
        return str(e), 404

@app.route('/')
def index():
    """Render the main page"""
    try:
        app.logger.debug('Index route accessed')
        app.logger.debug(f'Static folder: {app.static_folder}')
        app.logger.debug(f'Template folder: {app.template_folder}')
        config = read_config()
        app.logger.debug(f'Config loaded: {config}')
        return render_template('index.html', config=config)
    except Exception as e:
        app.logger.error(f'Error rendering index: {str(e)}')
        return str(e), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    app.logger.debug('/api/config accessed')
    return jsonify(read_config())


@app.route('/api/logs')
def get_logs():
    """Get log data"""
    app.logger.debug('/api/logs accessed')
    hours = request.args.get('hours', default=24, type=int)
    print(f"Received log request for past {hours} hours")
            
    data = read_logs(hours)
    print(f"Returning {len(data['timestamps'])} data points")
            
    return jsonify(data)
    
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response
    
def main():
    app.logger.info('Starting Flask application...')
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    main()
