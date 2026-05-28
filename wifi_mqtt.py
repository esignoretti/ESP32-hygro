import time
import json
import network
from umqtt.simple import MQTTClient
try:
    import config
except ImportError:
    class _Config:
        WIFI_SSID = ""
        WIFI_PASS = ""
        MQTT_BROKER = ""
        MQTT_PORT = 8883
        MQTT_USER = ""
        MQTT_PASS = ""
        MQTT_TOPIC = "esp32-hygro/reading"
        CLIENT_ID = "esp32-hygro"
        TARGET_TEMP = 23.0
        TARGET_HUM = 50.0
        ALERT_PERCENT = 2.0
    config = _Config()

wlan = None
client = None
connected = False
wifi_started = False
wifi_retry_after = 0


def _best_bssid(ssid):
    for n in wlan.scan():
        s = n[0].decode() if isinstance(n[0], bytes) else n[0]
        if s == ssid:
            return n[1]
    return None


def connect_wifi():
    global wlan, wifi_started, wifi_retry_after

    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

    if wlan.isconnected():
        return True

    if not config.WIFI_SSID:
        return False

    if not wifi_started:
        bssid = _best_bssid(config.WIFI_SSID)
        if bssid:
            wlan.connect(config.WIFI_SSID, config.WIFI_PASS, bssid=bssid)
        else:
            wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
        wifi_started = True
        wifi_retry_after = time.time() + 10
    elif time.time() >= wifi_retry_after and wlan.status() != 1001:
        wlan.disconnect()
        time.sleep(1)
        bssid = _best_bssid(config.WIFI_SSID)
        if bssid:
            wlan.connect(config.WIFI_SSID, config.WIFI_PASS, bssid=bssid)
        else:
            wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
        wifi_retry_after = time.time() + 10

    return wlan.isconnected()


def connect_mqtt():
    global client, connected
    if not wlan or not wlan.isconnected():
        return False

    try:
        client = MQTTClient(
            config.CLIENT_ID,
            config.MQTT_BROKER,
            port=config.MQTT_PORT,
            user=config.MQTT_USER,
            password=config.MQTT_PASS,
            ssl=True,
            ssl_params={"server_hostname": config.MQTT_BROKER},
        )
        client.connect()
        connected = True
        return True
    except Exception:
        connected = False
        return False


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


def ping():
    global connected
    if not client:
        connected = False
        return False
    try:
        client.ping()
        return True
    except Exception:
        connected = False
        return False


def reconnect():
    connect_wifi()
    connect_mqtt()
    return connected
