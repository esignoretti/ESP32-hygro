import json
import os
import paho.mqtt.client as mqtt
import database
import alert

MQTT_BROKER = os.environ.get("MQTT_BROKER", "580bc15dbdc94a9686c52d5a825dd4c3.s1.eu.hivemq.cloud")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USER = os.environ.get("MQTT_USER", "")
MQTT_PASS = os.environ.get("MQTT_PASS", "")
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "esp32-hygro/reading")

_callbacks = []
_client = None


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


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)


def start_mqtt():
    global _client
    try:
        client = mqtt.Client()
        if MQTT_USER:
            client.username_pw_set(MQTT_USER, MQTT_PASS)
        client.tls_set()
        client.on_message = on_message
        client.on_connect = on_connect
        client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        _client = client
    except Exception:
        pass


def register_callback(cb):
    _callbacks.append(cb)
