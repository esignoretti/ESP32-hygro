import json
import os
import sys
import paho.mqtt.client as mqtt

MQTT_BROKER = os.environ.get("MQTT_BROKER", "broker.hivemq.cloud")
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

        import database
        database.insert_reading(temp, humidity, ts)

        import alert
        alert.check_and_notify(temp, humidity)

        for cb in _callbacks:
            cb(temp, humidity, ts)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"MQTT invalid message: {e}", flush=True)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        print(f"MQTT connected, subscribed to {MQTT_TOPIC}", flush=True)
    else:
        print(f"MQTT connection failed with code {rc}", flush=True)


def start_mqtt():
    global _client
    if not MQTT_BROKER:
        print("MQTT_BROKER not set, skipping MQTT", flush=True)
        return

    client = mqtt.Client()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_message = on_message
    client.on_connect = on_connect
    client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    _client = client
    print("MQTT client started (async)", flush=True)


def register_callback(cb):
    _callbacks.append(cb)
