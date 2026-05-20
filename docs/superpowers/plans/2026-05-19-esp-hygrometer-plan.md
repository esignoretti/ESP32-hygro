# ESP-12F Hygrometer & Thermometer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a MicroPython firmware that reads AHT10 temp/humidity, logs 24h history in RAM, and displays live readings + scrolling graph on SSD1306 OLED.

**Architecture:** Single I2C bus (GPIO4=SDA, GPIO5=SCL) shared by AHT10 (addr 0x38) and SSD1306 (addr 0x3C). Four files: boot.py (I2C init), ringbuf.py (circular buffer), graph.py (OLED graph rendering), main.py (application loop).

**Tech Stack:** MicroPython on ESP-12F (NodeMCU), AHT10 sensor, GM009605 OLED (SSD1306 driver)

**Files:**

| File | Purpose |
|---|---|
| `boot.py` | I2C bus init (GPIO4=SDA, GPIO5=SCL, 400kHz) |
| `ringbuf.py` | Ring buffer: 288 entries of (temp, humidity) tuples |
| `graph.py` | Graph renderer: plots data series on SSD1306 framebuffer |
| `main.py` | Main loop: read sensor → log → update display |

---

### Task 1: boot.py — I2C Bus Initialization

**Files:**
- Create: `boot.py`

- [ ] **Step 1: Write boot.py**

```python
import time
from machine import Pin, I2C

try:
    i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
except Exception:
    time.sleep(5)
    import machine
    machine.reset()
```

- [ ] **Step 2: Verify the file syntax**

Run: `python3 -m py_compile boot.py`
Expected: no output (file is syntactically valid Python 3)

- [ ] **Step 3: Commit**

```bash
git add boot.py
git commit -m "feat: add boot.py with I2C init on GPIO4/GPIO5"
```

---

### Task 2: ringbuf.py — Ring Buffer Module

**Files:**
- Create: `ringbuf.py`

- [ ] **Step 1: Write ringbuf.py**

```python
class RingBuffer:
    def __init__(self, capacity):
        self._buf = [None] * capacity
        self._cap = capacity
        self._head = 0
        self._full = False

    def append(self, temp, humidity):
        self._buf[self._head] = (temp, humidity)
        self._head = (self._head + 1) % self._cap
        if self._head == 0:
            self._full = True

    def __len__(self):
        return self._cap if self._full else self._head

    def __getitem__(self, idx):
        if idx < 0 or idx >= len(self):
            raise IndexError
        if self._full:
            idx = (self._head + idx) % self._cap
        return self._buf[idx]

    def as_list(self):
        n = len(self)
        if n == 0:
            return []
        if self._full:
            return self._buf[self._head:] + self._buf[:self._head]
        return self._buf[:n]
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile ringbuf.py`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add ringbuf.py
git commit -m "feat: add ring buffer module for 24h data logging"
```

---

### Task 3: graph.py — Graph Rendering Module

**Files:**
- Create: `graph.py`

- [ ] **Step 1: Write graph.py**

```python
def auto_scale(values):
    if not values:
        return 0, 1
    mn = min(values)
    mx = max(values)
    if mx == mn:
        mn -= 1
        mx += 1
    return mn, mx


def render_graph(display, data, metric, x, y, w, h):
    values = [d[metric] for d in data]
    if len(values) < 2:
        display.text("-- no data --", x + 4, y + h // 2 - 4)
        return

    vmin, vmax = auto_scale(values)
    vrange = vmax - vmin
    if vrange == 0:
        vrange = 1

    step_x = (w - 2) / (len(values) - 1) if len(values) > 1 else 1

    for i in range(len(values) - 1):
        x1 = int(x + 1 + i * step_x)
        x2 = int(x + 1 + (i + 1) * step_x)
        y1 = int(y + h - 1 - ((values[i] - vmin) / vrange) * (h - 2))
        y2 = int(y + h - 1 - ((values[i + 1] - vmin) / vrange) * (h - 2))
        display.line(x1, y1, x2, y2, 1)

    label = "T" if metric == 0 else "H"
    display.text(f"{label}:{vmin:.0f}-{vmax:.0f}", x + 2, y + h - 10)
```

Note: `metric == 0` means temperature (first element of tuple), `metric == 1` means humidity (second element).

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile graph.py`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add graph.py
git commit -m "feat: add graph rendering module for OLED"
```

---

### Task 4: main.py — Main Application Loop

**Files:**
- Create: `main.py`

This is the core loop. It assumes:
- `boot.py` has created `i2c` as a module-level global
- `ahtx0.py` driver will be uploaded to the device (available in MicroPython package repos)
- `ssd1306.py` driver is included in the MicroPython firmware or uploaded separately

- [ ] **Step 1: Write main.py**

```python
import time
import boot
from machine import Pin
from ssd1306 import SSD1306_I2C
from ringbuf import RingBuffer
from graph import render_graph

SAMPLE_INTERVAL_MS = 2000
LOG_INTERVAL_S = 300
GRAPH_TOGGLE_S = 10
BUFFER_SIZE = 288

display = SSD1306_I2C(128, 64, boot.i2c)

aht_ok = True
try:
    import ahtx0
    sensor = ahtx0.AHT10(boot.i2c)
except Exception:
    aht_ok = False
    sensor = None

buf = RingBuffer(BUFFER_SIZE)
last_log = 0
last_toggle = 0
metric_shown = 0

def read_temp_humidity():
    if sensor is None:
        return None, None
    try:
        temp = sensor.temperature
        hum = sensor.relative_humidity
        return temp, hum
    except Exception:
        return None, None

def draw_current_values(display, temp, hum, aht_ok):
    display.fill_rect(0, 0, 128, 8, 0)
    if aht_ok and temp is not None:
        display.text(f"{temp:.1f}C  {hum:.0f}%", 0, 0)
    else:
        display.text("ERR: sensor", 0, 0)

def draw_status_line(display, temp, hum, aht_ok, graph_metric):
    label = "T" if graph_metric == 0 else "H"
    if aht_ok and temp is not None:
        status = f"Now:{temp:.1f}C {hum:.0f}% | G:{label}"
    else:
        status = f"G:{label}"
    display.fill_rect(0, 56, 128, 8, 0)
    display.text(status, 0, 56)

def draw_graph(display, data, metric):
    display.fill_rect(0, 8, 128, 48, 0)
    render_graph(display, data, metric, 2, 10, 124, 44)

while True:
    temp, hum = read_temp_humidity()
    now = time.time()
    if now - last_log >= LOG_INTERVAL_S and aht_ok and temp is not None:
        buf.append(temp, hum)
        last_log = now

    if now - last_toggle >= GRAPH_TOGGLE_S:
        metric_shown = 1 - metric_shown
        last_toggle = now

    display.fill(0)

    draw_current_values(display, temp, hum, aht_ok)

    if len(buf) > 1:
        draw_graph(display, buf.as_list(), metric_shown)

    draw_status_line(display, temp, hum, aht_ok, metric_shown)

    display.show()

    time.sleep_ms(SAMPLE_INTERVAL_MS)
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile main.py`
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add main application loop with sensor read and OLED display"
```

---

### Task 5: Wiring Diagram (Documentation)

**Files:**
- Modify: `docs/superpowers/specs/2026-05-19-esp-hygrometer-design.md` (wiring section is already there)

No code changes needed. The wiring table in the spec is sufficient.

- [ ] **Step 1: Verify the wiring table is still accurate**

Already documented in spec:
| ESP-12F Pin | Connection |
|---|---|
| 3.3V | AHT10 VIN, SSD1306 VCC |
| GND | AHT10 GND, SSD1306 GND |
| GPIO4 (D2) | AHT10 SDA, SSD1306 SDA |
| GPIO5 (D1) | AHT10 SCL, SSD1306 SCL |

- [ ] **Step 2: Commit (if any doc changes needed)**

```bash
git add docs/superpowers/specs/2026-05-19-esp-hygrometer-design.md
git commit -m "docs: finalize wiring and design spec"
```

---

### Task 6: Deployment Guide

**Files:**
- Create: `DEPLOY.md`

- [ ] **Step 1: Write DEPLOY.md**

```markdown
# Deployment Guide

## Prerequisites

- NodeMCU ESP-12F with MicroPython firmware installed
  (flash with esptool if not already done)
- AHT10 sensor + GM009605 OLED (SSD1306 driver) wired per wiring table
- `rshell` or `ampy` or Thonny for file upload

## Dependencies

Upload these MicroPython libraries to the device:

- `ssd1306.py` — included in most MicroPython builds; if not, get from
  https://github.com/micropython/micropython-lib
- `ahtx0.py` — from https://github.com/tvdev/micropython-ahtx0

## Upload Files

```bash
# Using rshell
rshell cp boot.py /pyboard/boot.py
rshell cp ringbuf.py /pyboard/ringbuf.py
rshell cp graph.py /pyboard/graph.py
rshell cp main.py /pyboard/main.py
rshell cp ahtx0.py /pyboard/ahtx0.py
rshell cp ssd1306.py /pyboard/ssd1306.py

# Or using ampy
ampy --port /dev/ttyUSB0 put boot.py
ampy --port /dev/ttyUSB0 put ringbuf.py
ampy --port /dev/ttyUSB0 put graph.py
ampy --port /dev/ttyUSB0 put main.py
ampy --port /dev/ttyUSB0 put ahtx0.py
ampy --port /dev/ttyUSB0 put ssd1306.py
```

## Verify

Reset the device (or press RST). The OLED should show:
1. "ERR: sensor" briefly
2. Then live temperature and humidity update every 2 seconds
3. Graph fills in over time as data accumulates
```

- [ ] **Step 2: Commit**

```bash
git add DEPLOY.md
git commit -m "docs: add deployment guide with upload instructions"
```
