# ESP32-Hygro Cloud Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend ESP32-Hygro firmware to publish sensor data via MQTT, and build a cloud backend (FastAPI on Render.com) that serves a responsive web dashboard, stores data in PostgreSQL, and sends out-of-range Telegram notifications.

**Architecture:** ESP32 publishes JSON readings to HiveMQ Cloud (free tier) via MQTT/TLS. A FastAPI backend subscribes to the same broker, stores readings in PostgreSQL, serves a Chart.js web dashboard with SSE live updates, and sends Telegram alerts when values exceed configured thresholds.

**Tech Stack:** MicroPython `umqtt.simple`, HiveMQ Cloud, FastAPI, Render.com, PostgreSQL, Chart.js, Tailwind CSS, python-telegram-bot

---

## File Structure

### New files (ESP32 firmware):

| File | Purpose |
|------|---------|
| `config.py` | WiFi/MQTT credentials, alert thresholds |
| `wifi_mqtt.py` | WiFi connection (WPS/SSID), MQTT publish with auto-reconnect |

### Modified files (ESP32 firmware):

| File | Purpose |
|------|---------|
| `main.py` | Add MQTT publish after sensor read; keep display working offline |

### New files (backend):

| File | Purpose |
|------|---------|
| `backend/requirements.txt` | Python dependencies |
| `backend/main.py` | FastAPI app: startup, MQTT subscriber, API routes |
| `backend/database.py` | PostgreSQL connection, table creation, queries |
| `backend/models.py` | Data models / SQL statements |
| `backend/mqtt_client.py` | MQTT subscription, message handler |
| `backend/telegram_bot.py` | Telegram bot: /start handler, alert sending |
| `backend/alert.py` | Alert logic: check thresholds, debounce |
| `backend/static/index.html` | Single-page web dashboard |
| `backend/static/app.js` | Chart.js graph, SSE, slider controls |
| `backend/static/app.css` | Minimal responsive styles (Tailwind via CDN) |
| `backend/render.yaml` | Render.com deployment config |

---

### Task 1: config.py — ESP32 Configuration

**Files:**
- Create: `config.py`

- [ ] **Step 1: Write config.py**

```python
WIFI_SSID = ""
WIFI_PASS = ""
MQTT_BROKER = "broker.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = ""
MQTT_PASS = ""
MQTT_TOPIC = "esp32-hygro/reading"
CLIENT_ID = "esp32-hygro-1"
TARGET_TEMP = 23.0
TARGET_HUM = 50.0
ALERT_PERCENT = 2.0
```

- [ ] **Step 2: Commit**

```bash
git add config.py
git commit -m "feat: add ESP32 config.py for WiFi/MQTT/alert settings"
```

---

### Task 2: wifi_mqtt.py — WiFi Connection and MQTT Publisher

**Files:**
- Create: `wifi_mqtt.py`

- [ ] **Step 1: Write wifi_mqtt.py**

```python
import time
import json
import network
from umqtt.simple import MQTTClient
import config

wlan = None
client = None
connected = False


def connect_wifi():
    global wlan, connected
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if config.WIFI_SSID:
        wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
    else:
        try:
            wlan.wps()
        except Exception:
            pass

    timeout = 20
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1

    connected = wlan.isconnected()
    return connected


def connect_mqtt():
    global client, connected
    if not wlan or not wlan.isconnected():
        connected = False
        return False

    try:
        client = MQTTClient(
            config.CLIENT_ID,
            config.MQTT_BROKER,
            port=config.MQTT_PORT,
            user=config.MQTT_USER,
            password=config.MQTT_PASS,
        )
        client.connect()
        connected = True
    except Exception:
        connected = False

    return connected


def publish(temp, humidity):
    global client, connected
    if not connected or not client:
        return False

    try:
        payload = json.dumps({
            "temp": round(temp, 1),
            "hum": round(humidity),
            "ts": int(time.time()),
        })
        client.publish(config.MQTT_TOPIC, payload)
        return True
    except Exception:
        connected = False
        return False


def reconnect():
    connect_wifi()
    connect_mqtt()
    return connected
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile wifi_mqtt.py`
Expected: no output (file is syntactically valid)

- [ ] **Step 3: Commit**

```bash
git add wifi_mqtt.py
git commit -m "feat: add WiFi/MQTT module for ESP32"
```

---

### Task 3: Update main.py — Add MQTT Publish

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update main.py**

Add MQTT publish call after each successful sensor read. Offline display continues to work regardless of network state.

```python
import time
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
from ringbuf import RingBuffer
from graph import render_graph
import wifi_mqtt

SAMPLE_INTERVAL_MS = 2000
LOG_INTERVAL_S = 300
GRAPH_TOGGLE_S = 10
BUFFER_SIZE = 288

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

display_ok = True
try:
    display = SSD1306_I2C(128, 64, i2c)
except Exception:
    display_ok = False

sensor = None
try:
    import ahtx0
    sensor = ahtx0.AHT10(i2c)
except Exception:
    pass

wifi_mqtt.connect_wifi()
wifi_mqtt.connect_mqtt()

buf = RingBuffer(BUFFER_SIZE)
buf.append(23.0, 50)
buf.append(24.0, 55)
last_log = 0
last_toggle = 0
last_mqtt_reconnect = 0
metric_shown = 0


while True:
    if not display_ok:
        time.sleep_ms(SAMPLE_INTERVAL_MS)
        continue

    now = time.time()
    temp = None
    hum = None
    if sensor:
        try:
            temp = sensor.temperature
            hum = sensor.relative_humidity
        except Exception:
            pass

    if temp is not None:
        wifi_mqtt.publish(temp, hum)

    if not wifi_mqtt.connected and now - last_mqtt_reconnect > 60:
        wifi_mqtt.reconnect()
        last_mqtt_reconnect = now

    if now - last_toggle >= GRAPH_TOGGLE_S:
        metric_shown = 1 - metric_shown
        last_toggle = now

    display.fill(0)

    if temp is not None:
        display.text(f"Now:{temp:.1f}C {hum:.0f}%", 0, 0)
        if len(buf) < 3 or now - last_log >= LOG_INTERVAL_S:
            buf.append(temp, hum)
            last_log = now
    else:
        display.text("ERR: sensor", 0, 0)

    data = buf.as_list()
    if len(data) >= 2:
        vmin, vmax = render_graph(display, data, metric_shown, 2, 10, 124, 44)
        if metric_shown == 0:
            display.text(f"24h: {vmin:.1f}-{vmax:.1f}C", 0, 56)
        else:
            display.text(f"24h: {vmin:.0f}-{vmax:.0f}%", 0, 56)

    display.show()
    time.sleep_ms(SAMPLE_INTERVAL_MS)
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile main.py`
Expected: note: imports `wifi_mqtt` which does not exist locally — acceptable (MicroPython import)

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add MQTT publish to main loop"
```

---

### Task 4: Backend — Database Layer

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`

- [ ] **Step 1: Write database.py**

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id SERIAL PRIMARY KEY,
            temp REAL NOT NULL,
            humidity REAL NOT NULL,
            ts BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key VARCHAR(32) PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cur.execute("""
        INSERT INTO config (key, value) VALUES
            ('target_temp', '23.0'),
            ('target_hum', '50.0'),
            ('alert_percent', '2.0'),
            ('chat_id', '')
        ON CONFLICT (key) DO NOTHING
    """)
    conn.commit()
    cur.close()
    conn.close()


def insert_reading(temp, humidity, ts):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO readings (temp, humidity, ts) VALUES (%s, %s, %s)",
        (temp, humidity, ts),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_readings(hours=24):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT temp, humidity, ts FROM readings WHERE created_at > NOW() - INTERVAL '%s hours' ORDER BY ts ASC",
        (hours,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_config():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM config")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def set_config(key, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
        (key, value, value),
    )
    conn.commit()
    cur.close()
    conn.close()


def cleanup_old_readings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM readings WHERE created_at < NOW() - INTERVAL '7 days'")
    conn.commit()
    cur.close()
    conn.close()
```

- [ ] **Step 2: Write models.py** (empty — all logic lives in database.py for simplicity)

```python
# All data access logic is in database.py
# This file exists as a placeholder for future model definitions
```

- [ ] **Step 3: Commit**

```bash
git add backend/database.py backend/models.py
git commit -m "feat: add PostgreSQL database layer"
```

---

### Task 5: Backend — MQTT Client + Alert Logic

**Files:**
- Create: `backend/mqtt_client.py`
- Create: `backend/alert.py`

- [ ] **Step 1: Write mqtt_client.py**

```python
import json
import os
import paho.mqtt.client as mqtt
import database
import alert

MQTT_BROKER = os.environ.get("MQTT_BROKER", "broker.hivemq.cloud")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USER = os.environ.get("MQTT_USER", "")
MQTT_PASS = os.environ.get("MQTT_PASS", "")
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "esp32-hygro/reading")

_callbacks = []


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        temp = data["temp"]
        humidity = data["hum"]
        ts = data["ts"]

        database.insert_reading(temp, humidity, ts)
        alert.check_and_notify(temp, humidity)

        for cb in _callbacks:
            cb(temp, humidity, ts)
    except Exception:
        pass


def start_mqtt():
    client = mqtt.Client()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    return client


def register_callback(cb):
    _callbacks.append(cb)
```

- [ ] **Step 2: Write alert.py**

```python
import time
import database
import telegram_bot

_last_alert = {}


def check_and_notify(temp, humidity):
    config = database.get_config()
    target_temp = float(config.get("target_temp", "23.0"))
    target_hum = float(config.get("target_hum", "50.0"))
    alert_pct = float(config.get("alert_percent", "2.0"))
    chat_id = config.get("chat_id", "")

    if not chat_id:
        return

    temp_range = target_temp * alert_pct / 100.0
    hum_range = target_hum * alert_pct / 100.0
    now = time.time()

    if abs(temp - target_temp) > temp_range:
        last = _last_alert.get("temp", 0)
        if now - last > 3600:
            msg = f"OUT OF RANGE - Temp: {temp:.1f}C (target: {target_temp:.1f}C +/-{alert_pct}%)"
            telegram_bot.send_message(chat_id, msg)
            _last_alert["temp"] = now

    if abs(humidity - target_hum) > hum_range:
        last = _last_alert.get("hum", 0)
        if now - last > 3600:
            msg = f"OUT OF RANGE - Humidity: {humidity:.0f}% (target: {target_hum:.0f}% +/-{alert_pct}%)"
            telegram_bot.send_message(chat_id, msg)
            _last_alert["hum"] = now
```

- [ ] **Step 3: Commit**

```bash
git add backend/mqtt_client.py backend/alert.py
git commit -m "feat: add MQTT subscriber and alert logic"
```

---

### Task 6: Backend — Telegram Bot

**Files:**
- Create: `backend/telegram_bot.py`

- [ ] **Step 1: Write telegram_bot.py**

```python
import os
import asyncio
from telegram import Bot
import database

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_bot = Bot(token=TOKEN) if TOKEN else None


async def handle_start(update, context):
    chat_id = str(update.effective_chat.id)
    database.set_config("chat_id", chat_id)
    await update.message.reply_text(
        "ESP32-Hygro alert notifications enabled! "
        "You will be notified when temperature or humidity goes out of range."
    )


def send_message(chat_id, text):
    if not _bot:
        return False
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_bot.send_message(chat_id=chat_id, text=text))
        loop.close()
        return True
    except Exception:
        return False
```

- [ ] **Step 2: Commit**

```bash
git add backend/telegram_bot.py
git commit -m "feat: add Telegram bot for alert notifications"
```

---

### Task 7: Web App — Dashboard HTML/JS/CSS

**Files:**
- Create: `backend/static/index.html`
- Create: `backend/static/app.js`
- Create: `backend/static/app.css`

- [ ] **Step 1: Write index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ESP32-Hygro</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="/static/app.css">
</head>
<body class="bg-gray-100 min-h-screen p-4 max-w-lg mx-auto">
  <h1 class="text-2xl font-bold mb-4">ESP32-Hygro</h1>

  <div id="current-values" class="bg-white rounded-xl shadow p-4 mb-4 text-center">
    <div class="text-3xl font-mono" id="temp-display">--.-°C</div>
    <div class="text-xl font-mono text-gray-600" id="hum-display">--%</div>
    <div class="text-sm mt-2" id="status-display">Waiting for data...</div>
  </div>

  <div class="bg-white rounded-xl shadow p-4 mb-4">
    <label class="block text-sm font-medium mb-1">Target Temperature: <span id="target-temp-label">23.0</span>°C</label>
    <input type="range" id="target-temp" min="10" max="40" step="0.5" class="w-full">

    <label class="block text-sm font-medium mb-1 mt-3">Target Humidity: <span id="target-hum-label">50</span>%</label>
    <input type="range" id="target-hum" min="20" max="90" step="1" class="w-full">

    <label class="block text-sm font-medium mb-1 mt-3">Alert Range: <span id="alert-percent-label">2.0</span>%</label>
    <input type="range" id="alert-percent" min="0.5" max="10" step="0.5" class="w-full">
  </div>

  <div class="bg-white rounded-xl shadow p-4 mb-4">
    <canvas id="chart"></canvas>
  </div>

  <div class="text-xs text-gray-500 text-center" id="live-status">Disconnected</div>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write app.js**

```javascript
const ctx = document.getElementById('chart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label: 'Temperature °C', data: [], borderColor: '#ef4444', fill: false, tension: 0.3, pointRadius: 0 },
      { label: 'Humidity %', data: [], borderColor: '#3b82f6', fill: false, tension: 0.3, pointRadius: 0, yAxisID: 'y1' },
    ],
  },
  options: {
    responsive: true,
    interaction: { mode: 'index', intersect: false },
    scales: {
      x: { display: true, ticks: { maxTicksLimit: 12 } },
      y: { position: 'left', title: { display: true, text: '°C' } },
      y1: { position: 'right', title: { display: true, text: '%' }, grid: { drawOnChartArea: false } },
    },
  },
});

function updateCurrent(temp, hum, targetTemp, targetHum, alertPct) {
  const tempEl = document.getElementById('temp-display');
  const humEl = document.getElementById('hum-display');
  tempEl.textContent = temp.toFixed(1) + '°C';
  humEl.textContent = Math.round(hum) + '%';

  const tRange = targetTemp * alertPct / 100;
  const hRange = targetHum * alertPct / 100;

  tempEl.className = 'text-3xl font-mono ' + (Math.abs(temp - targetTemp) > tRange ? 'text-red-600' : 'text-green-600');
  humEl.className = 'text-xl font-mono ' + (Math.abs(hum - targetHum) > hRange ? 'text-red-600' : 'text-green-600');
}

function updateConfig(config) {
  document.getElementById('target-temp').value = config.target_temp;
  document.getElementById('target-temp-label').textContent = config.target_temp;
  document.getElementById('target-hum').value = config.target_hum;
  document.getElementById('target-hum-label').textContent = config.target_hum;
  document.getElementById('alert-percent').value = config.alert_percent;
  document.getElementById('alert-percent-label').textContent = config.alert_percent;

  document.querySelectorAll('input[type="range"]').forEach(el => {
    el.addEventListener('change', () => {
      const key = el.id;
      const label = document.getElementById(key + '-label');
      if (label) label.textContent = el.value;
      const configKey = key.replace(/-/g, '_');
      const body = {};
      body[configKey] = el.value;
      fetch('/api/config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    });
  });
}

async function loadHistorical() {
  const resp = await fetch('/api/readings?hours=24');
  const readings = await resp.json();
  chart.data.labels = readings.map(r => new Date(r.ts * 1000).toLocaleTimeString());
  chart.data.datasets[0].data = readings.map(r => r.temp);
  chart.data.datasets[1].data = readings.map(r => r.humidity);
  chart.update();
}

async function loadConfig() {
  const resp = await fetch('/api/config');
  const config = await resp.json();
  updateConfig(config);
}

let lastData = null;
function connectSSE() {
  const evtSource = new EventSource('/api/live');
  evtSource.onmessage = (e) => {
    const data = JSON.parse(e.data);
    lastData = data;

    loadConfig().then(() => {
      const config = {
        target_temp: parseFloat(document.getElementById('target-temp').value),
        target_hum: parseFloat(document.getElementById('target-hum').value),
        alert_percent: parseFloat(document.getElementById('alert-percent').value),
      };
      updateCurrent(data.temp, data.humidity, config.target_temp, config.target_hum, config.alert_percent);
    });

    chart.data.labels.push(new Date(data.ts * 1000).toLocaleTimeString());
    chart.data.datasets[0].data.push(data.temp);
    chart.data.datasets[1].data.push(data.humidity);
    if (chart.data.labels.length > 288) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
      chart.data.datasets[1].data.shift();
    }
    chart.update('none');
    document.getElementById('live-status').textContent = 'Live';
  };
  evtSource.onerror = () => {
    document.getElementById('live-status').textContent = 'Reconnecting...';
  };
}

loadHistorical();
loadConfig();
connectSSE();
```

- [ ] **Step 3: Write app.css**

```css
/* Minimal extras beyond Tailwind */
input[type="range"] { accent-color: #3b82f6; }
```

- [ ] **Step 4: Commit**

```bash
git add backend/static/
git commit -m "feat: add responsive web dashboard with Chart.js and SSE"
```

---

### Task 8: Backend — FastAPI Main App

**Files:**
- Create: `backend/main.py`
- Create: `backend/requirements.txt`
- Create: `backend/render.yaml`

- [ ] **Step 1: Write main.py**

```python
import asyncio
import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import database
import mqtt_client
import telegram_bot
from telegram import Update
from telegram.ext import Application, CommandHandler

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

sse_queues = []


def broadcast(temp, humidity, ts):
    data = json.dumps({"temp": temp, "humidity": humidity, "ts": ts})
    for q in sse_queues[:]:
        try:
            q.put_nowait(data)
        except Exception:
            sse_queues.remove(q)


@app.on_event("startup")
async def startup():
    database.init_db()

    mqtt_client.register_callback(broadcast)
    mqtt_client.start_mqtt()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if token:
        tg_app = Application.builder().token(token).build()
        tg_app.add_handler(CommandHandler("start", telegram_bot.handle_start))
        asyncio.create_task(tg_app.start_polling())


@app.get("/")
async def index():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/readings")
async def get_readings(hours: int = 24):
    return database.get_readings(hours)


@app.get("/api/current")
async def get_current():
    readings = database.get_readings(1)
    if readings:
        r = readings[-1]
        config = database.get_config()
        target_temp = float(config.get("target_temp", "23.0"))
        target_hum = float(config.get("target_hum", "50.0"))
        alert_pct = float(config.get("alert_percent", "2.0"))
        temp_range = target_temp * alert_pct / 100.0
        hum_range = target_hum * alert_pct / 100.0
        return {
            "temp": r["temp"],
            "humidity": r["humidity"],
            "ts": r["ts"],
            "in_range_temp": abs(r["temp"] - target_temp) <= temp_range,
            "in_range_hum": abs(r["humidity"] - target_hum) <= hum_range,
        }
    return {}


@app.get("/api/config")
async def get_config():
    return database.get_config()


@app.post("/api/config")
async def update_config(request: Request):
    body = await request.json()
    for key, value in body.items():
        database.set_config(key, str(value))
    return {"ok": True}


@app.get("/api/live")
async def live_sse(request: Request):
    queue = asyncio.Queue()
    sse_queues.append(queue)

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                data = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {data}\n\n"
        except asyncio.TimeoutError:
            pass
        finally:
            if queue in sse_queues:
                sse_queues.remove(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 2: Write requirements.txt**

```
fastapi==0.115.0
uvicorn==0.30.0
paho-mqtt==2.1.0
psycopg2-binary==2.9.9
python-telegram-bot==21.0
sse-starlette==2.0.0
```

- [ ] **Step 3: Write render.yaml**

```yaml
services:
  - type: web
    name: esp32-hygro
    runtime: python
    region: frankfurt
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: esp32-hygro-db
          property: connectionString
      - key: MQTT_BROKER
        value: broker.hivemq.cloud
      - key: MQTT_USER
        sync: false
      - key: MQTT_PASS
        sync: false
      - key: TELEGRAM_BOT_TOKEN
        sync: false

databases:
  - name: esp32-hygro-db
    region: frankfurt
    plan: free
```

- [ ] **Step 4: Commit**

```bash
git add backend/main.py backend/requirements.txt backend/render.yaml
git commit -m "feat: add FastAPI main app with API routes and SSE"
```

---

### Task 9: README Update

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README.md with cloud features**

Add sections after existing content:

```markdown
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
   - Connect GitHub repo
   - Set environment variables: `MQTT_USER`, `MQTT_PASS`, `TELEGRAM_BOT_TOKEN`
   - Render auto-provisions PostgreSQL
4. Open the web app URL, send `/start` to your Telegram bot

### ESP32 Config

Edit `config.py` with your WiFi credentials, MQTT broker details, and alert thresholds:

```python
WIFI_SSID = "your-network"
WIFI_PASS = "your-password"
MQTT_USER = "hivemq-username"
MQTT_PASS = "hivemq-password"
TARGET_TEMP = 23.0
ALERT_PERCENT = 2.0
```

Upload `config.py` and `wifi_mqtt.py` along with the other files.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with cloud expansion setup"
```

---

### Task 10: Push and Tag

- [ ] **Step 1: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 2: Tag and push**

```bash
git tag v0.2.0
git push origin v0.2.0
```
