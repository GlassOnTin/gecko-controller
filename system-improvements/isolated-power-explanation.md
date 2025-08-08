# How the Pololu ISO1640 Board Provides Isolated Power

## The Magic: Integrated Isolated DC-DC Converter

The Pololu board includes a small isolated DC-DC converter (likely a chip like the TI DCR010505 or similar) that works like this:

### How Isolated DC-DC Converters Work:

```
Input Side                 Transformer                Output Side
(From Pi)                  (Isolation)                (To Sensors)
                              
3.3V/5V ──→ [Oscillator] ──→ ≈≈≈≈≈ ──→ [Rectifier] ──→ 3.3V/5V Isolated
              (1-2 MHz)      Tiny ferrite              (Filtered DC)
                             core transformer
```

1. **Input Stage**: Takes your Pi's 3.3V or 5V power
2. **Oscillator**: Converts DC to high-frequency AC (~1-2 MHz)
3. **Transformer**: Tiny ferrite core transformer provides galvanic isolation
4. **Rectifier**: Converts back to DC on isolated side
5. **Output**: Clean, isolated 3.3V or 5V for your sensors

## Power Connections:

```
Single Power Source (Raspberry Pi)
           │
           ├──→ Pi's own circuits
           │
           └──→ Pololu Board VDD1 input
                      │
                      ├──→ ISO1640 chip (Pi side)
                      │
                      └──→ DC-DC Converter
                               │
                               └──→ Isolated output (VISO)
                                         │
                                         ├──→ ISO1640 chip (isolated side)
                                         └──→ Your 4 I2C devices
```

## Current Limitations:

The Pololu board typically provides:
- **Input**: 3.3V or 5V from Pi (jumper selectable)
- **Output**: ~100-150mA isolated power (check specific model)

Your I2C devices power consumption (estimated):
- OLED display (0x3C): ~20-30mA active
- SHT31 sensor (0x44): ~1mA
- Unknown device (0x68): ~5-10mA (if RTC/sensor)
- LED/Mux (0x74): ~10-50mA (depends on LEDs)
- **Total**: ~40-90mA typical (well within limits)

## Why This Isolation Matters:

### Without Isolation:
```
Relay switches → Voltage spike/dip on power rail → Affects all I2C devices
             └→ Ground current surge → Corrupts I2C signals
```

### With Isolation:
```
Relay switches → Voltage spike on Pi power → [ISOLATION BARRIER] → Clean power to sensors
             └→ Ground current surge → [NO PATH] → I2C signals protected
```

## Practical Wiring:

You only need to connect:
```bash
# From Raspberry Pi:
- 3.3V from Pin 1 or 17 → VDD1 on Pololu board
- GND from Pin 6, 9, etc → GND1 on Pololu board
- SDA from Pin 3 → SDA1 on Pololu board
- SCL from Pin 5 → SCL1 on Pololu board

# To your I2C devices:
- VISO from Pololu → VCC of all 4 devices
- GNDI from Pololu → GND of all 4 devices
- SDA2 from Pololu → SDA of all 4 devices
- SCL2 from Pololu → SCL of all 4 devices
```

## Power Budget Check:

To verify your devices won't exceed the isolated power limit:
```bash
# Check current system power usage
vcgencmd measure_volts
vcgencmd get_throttled

# If throttled=0x0, power supply is adequate
```

## Alternative if Power Not Enough:

If your I2C devices need more than ~150mA (unlikely):
1. Use Pololu board for I2C isolation only
2. Add a separate isolated DC-DC module (e.g., ROE-0505S, ~$10)
3. Or use a second USB power supply with USB isolator

But for your 4 devices, the Pololu board's integrated power should be plenty!