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
