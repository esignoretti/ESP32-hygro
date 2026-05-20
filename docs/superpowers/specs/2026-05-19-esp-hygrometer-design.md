# ESP-12F Hygrometer & Thermometer with 24h Graph

## Overview

A temperature and humidity measurement device using ESP-12F (NodeMCU), AHT10 sensor, and SSD1306 OLED display. MicroPython firmware. Shows live readings and scrolls through 24-hour graph history.

## Hardware

### Components

| Component | Notes |
|---|---|
| ESP-12F (NodeMCU dev board) | Built-in USB-UART + 3.3V regulator |
| AHT10 | Temp/humidity sensor, I2C address 0x38 |
| GM009605 OLED 128x64 | SSD1306 driver, I2C address 0x3C |

### Wiring (Single I2C Bus)

| ESP-12F Pin | Connection |
|---|---|
| 3.3V | AHT10 VIN, SSD1306 VCC |
| GND | AHT10 GND, SSD1306 GND |
| GPIO4 (D2) | AHT10 SDA, SSD1306 SDA |
| GPIO5 (D1) | AHT10 SCL, SSD1306 SCL |

No pull-up resistors needed — both breakout boards include them.

### Power

USB power via NodeMCU's micro-USB port. Future battery expansion possible.

## Software

### Framework

MicroPython running on the ESP-12F.

### Files

- **`boot.py`** — Initialize I2C bus (GPIO4=SDA, GPIO5=SCL, 400kHz)
- **`main.py`** — Main application loop:
  1. Init AHT10 and SSD1306
  2. Read sensor every ~2 seconds
  3. Store reading in ring buffer (288 entries = 24h at 5-min resolution)
  4. Update OLED display

### Display Layout (128x64)

```
┌──────────────────────┐
│ 23.5°C    74%        │  ← line 0: current values
│  ┌────────────────┐   │
│  │   temperature   │   │  ← lines 1-6: graph area
│  │  ╱╲    ╱╲╱╲    │   │     toggles temp/humidity
│  │ ╱  ╲  ╱    ╲   │   │     every 10 seconds
│  │╱    ╲╱      ╲  │   │
│  └────────────────┘   │
│ 24h graph | T+10s     │  ← line 7: status
└──────────────────────┘
```

### Data Logging

- Ring buffer in RAM: 288 entries of (temp, humidity) tuples
- Each entry taken ~5 minutes apart (configurable)
- Rounding down: 24h × 60min / 5min = 288 samples
- Oldest entries overwritten when full
- Graph scales dynamically to min/max of visible data
- RAM-only: data lost on power cycle (acceptable for this project)
- Display refreshes every ~2s with latest sensor value; only logged to ring buffer every ~5min

### Graph Rendering (SSD1306 framebuffer)

- 48px height × 128px width available for graph (lines 1-6 on a 8-line 8px-high font layout, using 6×8 = 48px)
- Actually: SSD1306 is 128x64, 8px font = 8 rows. Row 0 = current values. Row 7 = status. Rows 1-6 = 48px for graph.
- Draw axes, plot points scaled to min/max range, connect with lines
- Flicker-free: use framebuffer, blit full frame at once

### Error Handling

| Failure | Behavior |
|---|---|
| AHT10 I2C timeout | Show "ERR: sensor" on display, retry next cycle |
| I2C init failure | Soft reboot after 5s |
| OLED init failure | Continue measuring, serial output only |

## Sampling & Update Cycle

| Parameter | Value |
|---|---|
| Sensor read interval | ~2 seconds |
| Data log interval | ~5 minutes |
| Graph toggle interval | 10 seconds |
| Graph history | 24 hours (288 samples) |

## Future Considerations

- Deep sleep + battery power
- Wi-Fi upload to MQTT/Home Assistant
- Denser sampling (support depends on use case)
