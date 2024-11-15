#!/usr/bin/env python3
# gecko_controller/web/app.py
from flask import Flask, render_template, jsonify, request
import os
import re
import csv
from datetime import datetime
import pkg_resources

app = Flask(__name__)
app.template_folder = pkg_resources.resource_filename('gecko_controller.web', 'templates')

CONFIG_FILE = '/etc/gecko-controller/config.py'
LOG_FILE = '/var/log/gecko-controller/readings.log'

def read_config():
    """Read and parse the config file"""
    config = {}
    with open(CONFIG_FILE, 'r') as f:
        content = f.read()
        # Extract key-value pairs using regex
        pairs = re.findall(r'(\w+)\s*=\s*([^#\n]+)', content)
        for key, value in pairs:
            # Clean up the value
            value = value.strip().strip('"\'')
            try:
                # Try to evaluate as Python literal
                import ast
                config[key] = ast.literal_eval(value)
            except:
                # If not a literal, store as string
                config[key] = value
    return config

def write_config(config):
    """Write config back to file"""
    # Read existing file to preserve comments and structure
    with open(CONFIG_FILE, 'r') as f:
        lines = f.readlines()

    # Update values while preserving structure
    new_lines = []
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0].strip()
            if key in config:
                value = config[key]
                if isinstance(value, str) and not key.endswith('_THRESHOLDS'):
                    value = f'"{value}"'
                new_lines.append(f'{key} = {value}\n')
        else:
            new_lines.append(line)

    # Write back to file
    with open(CONFIG_FILE, 'w') as f:
        f.writelines(new_lines)

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
        with open(LOG_FILE, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    print(row[0],row[1])
                    timestamp = datetime.strptime(row[0] + "." + row[1], '%Y-%m-%d %H:%M:%S.%f')
                    data['timestamps'].append(timestamp.strftime('%Y-%m-%d %H:%M'))
                    data['temperature'].append(float(row[2]))
                    data['humidity'].append(float(row[3]))
                    data['uva'].append(float(row[4]))
                    data['uvb'].append(float(row[5]))
                    data['uvc'].append(float(row[6]))
                    data['light'].append(int(row[7]))
                    data['heat'].append(int(row[8]))
                except (ValueError, IndexError) as e:
                    print(e)
                    continue
    except FileNotFoundError:
        print(f"{LOG_FILE} not found")
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

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        new_config = request.get_json()
        write_config(new_config)
        # Restart the gecko-controller service to apply changes
        os.system('systemctl restart gecko-controller')
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/logs')
def get_logs():
    """Get log data"""
    hours = request.args.get('hours', default=24, type=int)
    return jsonify(read_logs(hours))

def main():
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    main()