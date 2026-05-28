import time
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import wifi_mqtt
import config

SAMPLE_INTERVAL_MS = 2000
SHOW_TEMP_SECS = 5
SHOW_HUM_SECS = 5

i2c = I2C(0, scl=Pin(6), sda=Pin(5), freq=400000)

display_ok = True
try:
    display = SSD1306_I2C(72, 40, i2c)
    display.fill(0)
    display.text("ABrobot", 10, 16)
    display.show()
except Exception:
    display_ok = False

sensor = None
try:
    import ahtx0
    sensor = ahtx0.AHT10(i2c)
except Exception:
    pass

last_mqtt_ping = 0
last_mqtt_retry = 0
last_swap = 0
alert_scroll_x = 72
show_temp = True


while True:
    if not display_ok:
        time.sleep_ms(SAMPLE_INTERVAL_MS)
        continue

    now = time.time()

    wifi_mqtt.connect_wifi()
    if not wifi_mqtt.connected and now - last_mqtt_retry >= 30:
        wifi_mqtt.connect_mqtt()
        last_mqtt_retry = now

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

    if wifi_mqtt.connected and now - last_mqtt_ping >= 20:
        if not wifi_mqtt.ping():
            wifi_mqtt.connected = False
        last_mqtt_ping = now

    if now - last_swap >= (SHOW_TEMP_SECS if show_temp else SHOW_HUM_SECS):
        show_temp = not show_temp
        last_swap = now

    temp_range = config.TARGET_TEMP * config.ALERT_PERCENT / 100.0
    hum_range = config.TARGET_HUM * config.ALERT_PERCENT / 100.0

    display.fill(0)

    if temp is None:
        display.text("no sensor", 10, 16)
    elif show_temp:
        label = f"{temp:.1f}C"
        x = (72 - len(label) * 8) // 2
        display.text(label, x, 12)
    else:
        label = f"{hum:.0f}%"
        x = (72 - len(label) * 8) // 2
        display.text(label, x, 12)

    alerts = []
    if temp is not None and abs(temp - config.TARGET_TEMP) > temp_range:
        alerts.append("T out of range!")
    if hum is not None and abs(hum - config.TARGET_HUM) > hum_range:
        alerts.append("H out of range!")
    if alerts:
        msg = "  ".join(alerts) + "  "
        alert_scroll_x -= 3
        if alert_scroll_x < -len(msg) * 8:
            alert_scroll_x = 72
        display.text(msg, alert_scroll_x, 32)

    display.show()
    time.sleep_ms(100)
