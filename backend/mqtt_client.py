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
