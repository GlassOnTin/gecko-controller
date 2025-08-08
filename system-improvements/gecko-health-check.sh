#!/bin/bash

# Gecko Controller Health Check Script
# This script checks the health of the gecko-controller service and takes action if needed

SERVICE_NAME="gecko-controller"
LOG_FILE="/var/log/gecko-health-check.log"
MAX_LOG_SIZE=10485760  # 10MB

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    
    # Rotate log if it gets too large
    if [ -f "$LOG_FILE" ] && [ $(stat -c%s "$LOG_FILE") -gt $MAX_LOG_SIZE ]; then
        mv "$LOG_FILE" "$LOG_FILE.old"
        touch "$LOG_FILE"
    fi
}

# Check if service is active
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    log_message "ERROR: $SERVICE_NAME is not active. Attempting restart..."
    systemctl restart "$SERVICE_NAME"
    sleep 5
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_message "SUCCESS: $SERVICE_NAME restarted successfully"
    else
        log_message "CRITICAL: Failed to restart $SERVICE_NAME"
        exit 1
    fi
fi

# Check for I2C errors in recent logs (last 5 minutes)
I2C_ERRORS=$(journalctl -u "$SERVICE_NAME" --since "5 minutes ago" 2>/dev/null | grep -c "I2C.*error")
if [ "$I2C_ERRORS" -gt 50 ]; then
    log_message "WARNING: High number of I2C errors detected ($I2C_ERRORS in last 5 minutes)"
    
    # Check if I2C bus is responsive
    if ! i2cdetect -y 1 &>/dev/null; then
        log_message "ERROR: I2C bus not responding. Restarting service..."
        systemctl restart "$SERVICE_NAME"
        sleep 5
        log_message "Service restarted due to I2C bus issues"
    fi
fi

# Check memory usage of the process
PID=$(systemctl show -p MainPID "$SERVICE_NAME" | cut -d= -f2)
if [ "$PID" != "0" ] && [ -n "$PID" ]; then
    MEM_USAGE=$(ps -o pmem= -p "$PID" 2>/dev/null | tr -d ' ')
    if [ -n "$MEM_USAGE" ]; then
        MEM_INT=${MEM_USAGE%.*}
        if [ "$MEM_INT" -gt 30 ]; then
            log_message "WARNING: High memory usage detected ($MEM_USAGE%)"
            if [ "$MEM_INT" -gt 50 ]; then
                log_message "CRITICAL: Memory usage exceeds 50%. Restarting service..."
                systemctl restart "$SERVICE_NAME"
                sleep 5
                log_message "Service restarted due to high memory usage"
            fi
        fi
    fi
fi

# Check if the web interface is responding (if applicable)
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 | grep -q "200\|301\|302"; then
    log_message "INFO: Web interface is responding"
else
    log_message "WARNING: Web interface not responding properly"
fi

# Log successful health check every hour only
MINUTE=$(date +%M)
if [ "$MINUTE" == "00" ]; then
    log_message "INFO: Health check passed"
fi

exit 0