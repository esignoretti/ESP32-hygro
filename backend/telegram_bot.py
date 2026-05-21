import os
import asyncio
from telegram import Bot
import database

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_bot = Bot(token=TOKEN) if TOKEN else None


async def handle_start(update, context):
    chat_id = str(update.effective_chat.id)
    print(f"Telegram /start from chat_id={chat_id}", flush=True)
    database.set_config("chat_id", chat_id)
    await update.message.reply_text(
        "ESP32-Hygro alert notifications enabled! "
        "You will be notified when temperature or humidity goes out of range."
    )
    print(f"Telegram /start replied to {chat_id}", flush=True)


def send_message(chat_id, text):
    if not _bot:
        return False
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_bot.send_message(chat_id=chat_id, text=text))
        loop.close()
        return True
    except Exception:
        return False
