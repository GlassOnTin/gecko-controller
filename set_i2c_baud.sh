#!/bin/bash

# Check if script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

CONFIG_FILE="/boot/firmware/config.txt"
BACKUP_FILE="/boot/firmware/config.txt.backup"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE does not exist"
    exit 1
fi

# Create backup
cp "$CONFIG_FILE" "$BACKUP_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to create backup file"
    exit 1
fi

# Create temporary file
TMP_FILE=$(mktemp)

# Process the file
while IFS= read -r line || [ -n "$line" ]; do
    # Check if line contains i2c_arm_baudrate
    if echo "$line" | grep -q "i2c_arm_baudrate="; then
        # Replace existing baud rate with 10000
        echo "$line" | sed 's/i2c_arm_baudrate=[0-9]*/i2c_arm_baudrate=10000/' >> "$TMP_FILE"
    else
        echo "$line" >> "$TMP_FILE"
    fi
done < "$CONFIG_FILE"

# Copy temporary file to original location
mv "$TMP_FILE" "$CONFIG_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to update config file"
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    rm "$TMP_FILE"
    exit 1
fi

# Set proper permissions
chmod 755 "$CONFIG_FILE"

echo "Successfully updated I2C baud rate to 10000"
echo "Original config file backed up to $BACKUP_FILE"
echo "Please reboot for changes to take effect"
