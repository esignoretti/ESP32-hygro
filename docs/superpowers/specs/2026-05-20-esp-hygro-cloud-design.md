# ESP32-Hygro Cloud: MQTT, Web App & Telegram Notifications

## Overview

Extend the ESP32-Hygro firmware to publish sensor readings via MQTT, and build a cloud backend that serves a responsive web dashboard and sends out-of-range alerts via Telegram bot.

## Architecture

```
ESP32 ──MQTT──▶ HiveMQ Cloud ──MQTT──▶ FastAPI backend (render.com)
                 (free tier)            │
                                        ├──▶ Web app (Chart.js + SSE)
                                        ├──▶ Telegram bot (push notifications)
                                        └──▶ PostgreSQL (render.com free)
```

### MQTT — why

The ESP32 can directly publish to a public MQTT broker (no static IP or port forwarding needed). The backend subscribes to the same broker. This is simpler than HTTP from the ESP32 (which would need TLS certificates, retry logic, etc.) and allows multiple subscribers (web app + potential future MQTT clients).

### Components

| Component | Host | Free tier limit | Notes |
|-----------|------|-----------------|-------|
| MQTT broker | HiveMQ Cloud | 10 connections, 1 GB/month | TLS on port 8883 |
| Backend | Render.com | 750 hours/month, 512 MB RAM, shared CPU | FastAPI + uvicorn |
| Database | Render.com PostgreSQL | 1 GB storage | Single connection |
| Telegram bot | python-telegram-bot | Unlimited, free | Bot registered via @BotFather |
| Web app | Served by FastAPI | — | Static HTML/JS, Chart.js via CDN |

## ESP32 Firmware Changes

### New file: `config.py`

WiFi credentials, MQTT broker config, alert thresholds.

```python
WIFI_SSID = ""
WIFI_PASS = ""
MQTT_BROKER = "broker.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = ""
MQTT_PASS = ""
MQTT_TOPIC = "esp32-hygro/reading"
TARGET_TEMP = 23.0
TARGET_HUM = 50.0
ALERT_PERCENT = 2.0
```

### New file: `wifi_mqtt.py`

- Connect to WiFi (WPS first attempt if AP supports it, fallback to SSID/password)
- Connect to MQTT broker with TLS
- Publish readings as JSON over MQTT
- Auto-reconnect on connection loss

### Modified file: `main.py`

- On startup: connect WiFi, then connect MQTT (continue without MQTT if it fails)
- In the main loop: after reading sensor, publish via MQTT
- Display continues to work offline (sensor + OLED unaffected by network issues)

### MQTT Payload

```json
{
  "temp": 23.4,
  "hum": 52,
  "ts": 1716249600
}
```

Published ~every 2 seconds (same as sensor read interval). The backend filters/logs appropriately.

## Backend (FastAPI on Render.com)

### Dependencies

- `fastapi`, `uvicorn`
- `paho-mqtt` — MQTT subscriber client
- `psycopg2-binary` — PostgreSQL driver
- `python-telegram-bot` — Telegram alerts
- `asyncio` + `sse-starlette` — Server-Sent Events for live updates

### Startup Sequence

1. Connect to PostgreSQL (create tables if not exist)
2. Subscribe to MQTT topic
3. Register Telegram bot webhook (or poll)
4. Serve web app static files
5. Start SSE endpoint for live data

### Database Schema

```sql
CREATE TABLE readings (
    id SERIAL PRIMARY KEY,
    temp REAL NOT NULL,
    humidity REAL NOT NULL,
    ts BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE config (
    key VARCHAR(32) PRIMARY KEY,
    value TEXT NOT NULL
);

-- Default config values
INSERT INTO config (key, value) VALUES
    ('target_temp', '23.0'),
    ('target_hum', '50.0'),
    ('alert_percent', '2.0'),
    ('chat_id', '');
```

Data retention: readings older than 7 days are deleted periodically.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/readings?hours=24` | Historical readings |
| GET | `/api/current` | Latest reading + alert status |
| GET | `/api/config` | Current target + range settings |
| POST | `/api/config` | Update settings |
| GET | `/api/live` | SSE stream for real-time updates |

### Telegram Bot

- Bot token configured via environment variable `TELEGRAM_BOT_TOKEN`
- Chat ID stored in the `config` table (user sends `/start` to the bot to register)
- Alert logic: when a reading arrives, compute `temp_range = target * alert_percent / 100`. If `abs(reading - target) > temp_range`, send notification
- Debounce: no duplicate alerts within 60 minutes for the same metric
- Alert format: `⚠️ OUT OF RANGE — Temp: 24.8°C (target: 23.0°C ±2%)`

### Data Cleanup

A background task runs every hour: `DELETE FROM readings WHERE created_at < NOW() - INTERVAL '7 days'`

## Web App

### Tech Stack

- Single page HTML (served by FastAPI as static files)
- Chart.js (CDN) for the 24h temperature/humidity graph
- Tailwind CSS (CDN) for responsive layout
- SSE for real-time chart updates

### Layout (mobile-first)

```
┌─────────────────────┐
│ 23.4°C    52%       │  ← current values (green/yellow/red)
│ [====slider====]    │  ← target temp slider
│ [====slider====]    │  ← alert % slider
│ ┌─────────────────┐ │
│ │    temperature  │ │  ← Chart.js line graph
│ │  ╱╲    ╱╲╱╲    │ │     temp + humidity lines
│ │ ╱  ╲  ╱    ╲   │ │     last 24 hours
│ │╱    ╲╱      ╲  │ │
│ └─────────────────┘ │
│ Status: Connected    │
└─────────────────────┘
```

- Temperature in green if in range, yellow if ±1% of boundary, red if out of range
- Target and alert % sliders update via `POST /api/config` on change
- Graph auto-updates via SSE when new data arrives

## Deployment

### ESP32

1. Flash MicroPython firmware
2. Upload all `.py` files including `config.py` and `wifi_mqtt.py`
3. Edit `config.py` with real WiFi credentials and MQTT credentials
4. Reset

### Infrastructure Setup (one-time)

1. Register HiveMQ Cloud free account → create cluster → note broker URL/port/credentials
2. Register Telegram bot via @BotFather → save token
3. Deploy FastAPI backend to Render.com:
   - Connect GitHub repo with backend code
   - Set environment variables: `DATABASE_URL`, `MQTT_*`, `TELEGRAM_BOT_TOKEN`
   - Render auto-provisions PostgreSQL
4. Open web app URL, send `/start` to Telegram bot to register chat ID

## Future Considerations

- Configurable alert debounce interval via web app
- Historical data export (CSV)
- Multiple ESP32 devices
- Battery-powered deep sleep mode (less frequent MQTT publishes)
- NTFY.sh as alternative notification channel
