sudo rmmod i2c_bcm2708
sudo modprobe i2c_bcm2708

echo '3f804000.i2c' > /sys/bus/platform/drivers/i2c-bcm2835/unbind
echo '3f804000.i2c' > /sys/bus/platform/drivers/i2c-bcm2835/bind


sudo pinctrl set 0 ip  # Set SCL as output
sudo pinctrl set 1 ip  # Set SDA as output
sudo pinctrl set 0 op  # Set SCL as output
sudo pinctrl set 1 op  # Set SDA as output

for i in {1..10}
do
    sudo pinctrl set 0 dl  # Drive SCL low
    sudo pinctrl set 1 dl  # Drive SDA low
    sudo pinctrl set 0 dh  # Drive SCL high
    sudo pinctrl set 1 dh  # Drive SDA high
done

sudo pinctrl set 0 dl  # Drive SCL low
sudo pinctrl set 1 dl  # Drive SDA low
