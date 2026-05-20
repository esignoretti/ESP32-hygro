# ESP32-Hygro

ESP32 hygrometer/thermometer with AHT10 sensor and SSD1306 OLED display running MicroPython. Shows live temperature/humidity and a scrolling 24-hour graph.

## Features

- Live readings: `Now: 23.5C 74%`
- 24-hour graph, toggles between temperature and humidity every 10s
- Data logged every 5 minutes (288 samples = 24h)
- Status bar shows min-max range for the last 24h
- Fits 128x64 OLED (GM009605 / SSD1306)

## Wiring

| ESP32 | AHT10 | GM009605 (SSD1306) |
|-------|-------|--------------------|
| 3.3V | VIN | VCC |
| GND | GND | GND |
| GPIO21 (SDA) | SDA | SDA |
| GPIO22 (SCL) | SCL | SCL |

Both breakout boards have built-in pull-up resistors. No external components needed.

## Requirements

- ESP32 board (tested on ESP32-D0WD-V3, 4MB flash)
- AHT10 temperature/humidity sensor
- GM009605 OLED 128x64 (SSD1306 driver)
- MicroPython v1.28.0+

## Files

| File | Description |
|------|-------------|
| `boot.py` | Empty — all init in main.py |
| `main.py` | Main loop: sensor read, logging, display, graph |
| `ahtx0.py` | AHT10 I2C driver (with timeout-safe busy wait) |
| `ssd1306.py` | SSD1306 OLED driver |
| `ringbuf.py` | Circular buffer (288 entries) |
| `graph.py` | Auto-scaling line graph renderer |

## Deployment

### Flash MicroPython

```bash
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash 0x1000 ESP32_GENERIC-*.bin
```

### Upload files

Using Thonny, rshell, ampy, or mpremote:

```bash
mpremote cp boot.py ringbuf.py graph.py ssd1306.py ahtx0.py main.py :
```

Or via Thonny: open each file → File → Save Copy To → MicroPython device.

### Run

Press RST or re-plug USB. The OLED will show:

- Live temperature/humidity on the first line
- 24h temperature or humidity graph (toggles every 10s)
- Range labels: `24h: 22.3-24.1C` or `24h: 45-68%`

If no sensor is connected, shows `ERR: sensor` and seeds the graph with dummy data.

## License

MIT
