# DC-DC Converter Filtering in Isolated Power Supplies

## Built-in Filtering

### What the DC-DC Converter Provides:

1. **Output Capacitors**: Usually 10-100µF
   - Smooths the rectified output
   - Reduces ripple to ~50-100mV typically
   - Good for steady-state operation

2. **High-Frequency Filtering**: 
   - The transformer naturally blocks DC transients
   - Switching frequency (~1-2 MHz) is filtered out
   - Small ceramic caps (0.1µF) on output for HF noise

3. **Isolation Barrier**:
   - Completely breaks ground loops
   - Prevents conducted EMI below ~100 kHz
   - No direct path for relay switching transients

## What It DOESN'T Filter Well:

### Input Side Disturbances:
```
Relay switches → Pi power dips → DC-DC input drops → Output follows (with delay)
                                                    └→ ~1-10ms response time
```

The isolated DC-DC will still show:
- **Load transients**: If input voltage sags 10%, output sags too (after delay)
- **Ripple**: Typically 50-100mV ripple at switching frequency
- **Limited bandwidth**: Can't filter fast transients (<1ms)

## Realistic Protection Level:

### For Your I2C Issues:
✅ **Excellent for**: Ground loops, conducted EMI, voltage spikes on ground
⚠️ **Moderate for**: Power supply dips (helps but doesn't eliminate)
❌ **Poor for**: Radiated EMI (need shielding), very fast transients (<1µs)

## Additional Filtering Recommended:

### On the Isolated Side (After Pololu Board):
```
VISO ──┬──[FB]──┬──────→ To I2C devices VCC
       │        │
      ===      ===
      C1       C2
       │        │
      GND      GND

Where:
- FB = Ferrite bead (optional but helpful)
- C1 = 100µF electrolytic (bulk storage)
- C2 = 0.1µF ceramic (HF bypass)
```

### For Your Relay Issues Specifically:

The main problem is likely **ground bounce** when relays switch:
```
Without isolator:
Relay coil dumps energy → Ground bounces 0.5-2V → I2C logic thresholds violated

With isolator:
Relay coil dumps energy → Ground bounces → [ISOLATION] → I2C ground stable
```

## Real-World Performance:

**Pololu ISO1640 board** filtering specs (typical):
- Output ripple: ~50mV p-p
- Transient response: ~100µs
- Load regulation: ±5%
- Line regulation: ±2%

**This is sufficient for I2C devices** because:
- I2C is relatively slow (100-400 kHz)
- Digital logic has noise margins (0.3-0.7V typically)
- Sensors have internal regulators/filtering

## Testing Filtering Effectiveness:

```bash
# Before installing isolator:
# Run this during relay switching
i2cdetect -y 1  # Will show devices disappearing

# After installing isolator:
i2cdetect -y 1  # Devices should remain stable
```

## Do You Need Extra Filtering?

For your setup, probably not initially. Try the Pololu board alone first.

Add extra filtering only if you still see issues:
1. **Still getting I2C errors?** → Add 100µF cap on isolated power
2. **OLED flickering?** → Add ferrite bead + caps
3. **Sensor readings jumpy?** → Check for radiated EMI (needs shielding)

## Bottom Line:

The Pololu board provides:
- ✅ Good enough filtering for most I2C issues
- ✅ Excellent ground isolation (main problem solver)
- ✅ Adequate power filtering for digital circuits
- ⚠️ Not audiophile-grade power (but you don't need that)

The isolation itself is 90% of the solution. The filtering is the other 10%.