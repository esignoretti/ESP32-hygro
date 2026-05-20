import time
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
from ringbuf import RingBuffer
from graph import render_graph

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

buf = RingBuffer(BUFFER_SIZE)
buf.append(23.0, 50)
buf.append(24.0, 55)
last_log = 0
last_toggle = 0
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
