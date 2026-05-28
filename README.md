# ESP32-Hygro

ESP32 hygrometer/thermometer with AHT10 sensor and SSD1306 OLED display running MicroPython. Shows live temperature/humidity and 24-hour sparkline graphs. Supports ESP32, ESP32-C3.

## Features

- Live readings: `23.5C   74%`
- 24-hour sparkline graphs (temp + humidity)
- Data logged every 5 minutes (288 samples = 24h)
- Range labels: `T:22.3-24.1C  H:45-68%`
- MQTT publishing to cloud backend (optional)
- Telegram notifications for out-of-range alerts

## Wiring

### ESP32 (full-size)

| ESP32 | AHT10 | GM009605 (SSD1306) |
|-------|-------|--------------------|
| 3.3V | VIN | VCC |
| GND | GND | GND |
| GPIO21 (SDA) | SDA | SDA |
| GPIO22 (SCL) | SCL | SCL |

### ESP32-C3 (compact)

| ESP32-C3 | AHT10 | 0.42" OLED (SSD1306) |
|----------|-------|----------------------|
| 3.3V | VIN | VCC |
| GND | GND | GND |
| GPIO5 (SDA) | SDA | SDA |
| GPIO6 (SCL) | SCL | SCL |

Both breakout boards have built-in pull-up resistors. No external components needed.

## Hardware Options

| Board | Display | I2C Pins | Firmware | Flash Offset |
|-------|---------|----------|----------|-------------|
| ESP32-D0WD-V3 | 128x64 OLED | GPIO21/22 | ESP32_GENERIC | 0x1000 |
| ESP32-C3 | 128x32 OLED | GPIO5/6 | ESP32_GENERIC_C3 | 0x0 |

## Files

| File | Description |
|------|-------------|
| `boot.py` | Empty — all init in main.py |
| `main.py` | Main loop: sensor read, logging, display, sparklines |
| `ahtx0.py` | AHT10 I2C driver (with timeout-safe busy wait) |
| `ssd1306.py` | SSD1306 OLED driver |
| `ringbuf.py` | Circular buffer (288 entries) |
| `graph.py` | Auto-scaling sparkline renderer |
| `config.py` | WiFi/MQTT credentials and alert thresholds (not tracked in git) |
| `wifi_mqtt.py` | WiFi connection and MQTT publish with auto-reconnect |

## Display Layout (128x32 OLED)

```
23.5C   74%         ← line 0: current values
████████ temp      ← line 1: temperature sparkline (8px tall)
████████ hum       ← line 2: humidity sparkline (8px tall)
T:22-24C H:45-68%  ← line 3: 24h range labels
```

## Deployment

### Flash MicroPython

**ESP32:**
```bash
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash 0x1000 ESP32_GENERIC-*.bin
```

**ESP32-C3:**
```bash
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash 0x0 ESP32_GENERIC_C3-*.bin
```

### Upload files

```bash
mpremote cp boot.py ringbuf.py graph.py ssd1306.py ahtx0.py main.py wifi_mqtt.py config.py :
```

### Run

Press RST or re-plug USB. The OLED will show:

- Live temperature/humidity on the first line
- Temperature and humidity 24h sparklines (8px tall each)
- Range labels: `T:22.3-24.1C  H:45-68%`

If no sensor is connected, shows `ERR: sensor` and seeds the graph with dummy data.

## Cloud Expansion

The firmware can publish sensor readings to a cloud backend via MQTT.

### Architecture

```
ESP32 ──MQTT──▶ HiveMQ Cloud ──MQTT──▶ FastAPI backend
                                        ├──▶ Web dashboard (Chart.js)
                                        ├──▶ Telegram notifications
                                        └──▶ PostgreSQL database
```

### Backend Setup

1. Register a free [HiveMQ Cloud](https://www.hivemq.com/mqtt-cloud-broker/) account
2. Create a Telegram bot via [@BotFather](https://t.me/botfather) and save the token
3. Deploy the `backend/` directory to [Render.com](https://render.com) as a web service:
   - Set Root Directory to `backend`
   - Set environment variables: `MQTT_USER`, `MQTT_PASS`, `TELEGRAM_BOT_TOKEN`
   - Render auto-provisions PostgreSQL
4. Register the Telegram webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<app>.onrender.com/api/telegram_webhook"
   ```
5. Open the web app URL, send `/start` to your Telegram bot

### ESP32 Config

Edit `config.py` with your WiFi credentials and MQTT broker details:

```python
WIFI_SSID = "your-network"
WIFI_PASS = "your-password"
MQTT_USER = "hivemq-username"
MQTT_PASS = "hivemq-password"
TARGET_TEMP = 23.0
ALERT_PERCENT = 2.0
```

## License

MIT
