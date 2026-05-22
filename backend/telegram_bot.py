import os
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


def send_message(chat_id, text):
    if not TOKEN:
        return False
    try:
        resp = requests.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
        })
        return resp.ok
    except Exception:
        return False


def process_update(data):
    if "message" not in data:
        return
    chat_id = str(data["message"]["chat"]["id"])
    text = data["message"].get("text", "")

    if text == "/start":
        import database
        database.set_config("chat_id", chat_id)
        send_message(chat_id, "ESP32-Hygro alert notifications enabled! You will be notified when temperature or humidity goes out of range.")
