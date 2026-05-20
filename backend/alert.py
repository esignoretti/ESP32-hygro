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
