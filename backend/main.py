import asyncio
import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import database
import mqtt_client
import telegram_bot
from telegram import Update
from telegram.ext import Application, CommandHandler

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

sse_queues = []


def broadcast(temp, humidity, ts):
    data = json.dumps({"temp": temp, "humidity": humidity, "ts": ts})
    for q in sse_queues[:]:
        try:
            q.put_nowait(data)
        except Exception:
            sse_queues.remove(q)


@app.on_event("startup")
async def startup():
    database.init_db()

    mqtt_client.register_callback(broadcast)
    mqtt_client.start_mqtt()

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if token:
        try:
            tg_app = Application.builder().token(token).build()
            tg_app.add_handler(CommandHandler("start", telegram_bot.handle_start))
            asyncio.create_task(tg_app.start_polling())
        except Exception:
            pass


@app.get("/")
async def index():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/readings")
async def get_readings(hours: int = 24):
    return database.get_readings(hours)


@app.get("/api/current")
async def get_current():
    readings = database.get_readings(1)
    if readings:
        r = readings[-1]
        config = database.get_config()
        target_temp = float(config.get("target_temp", "23.0"))
        target_hum = float(config.get("target_hum", "50.0"))
        alert_pct = float(config.get("alert_percent", "2.0"))
        temp_range = target_temp * alert_pct / 100.0
        hum_range = target_hum * alert_pct / 100.0
        return {
            "temp": r["temp"],
            "humidity": r["humidity"],
            "ts": r["ts"],
            "in_range_temp": abs(r["temp"] - target_temp) <= temp_range,
            "in_range_hum": abs(r["humidity"] - target_hum) <= hum_range,
        }
    return {}


@app.get("/api/config")
async def get_config():
    return database.get_config()


@app.post("/api/config")
async def update_config(request: Request):
    body = await request.json()
    for key, value in body.items():
        database.set_config(key, str(value))
    return {"ok": True}


@app.get("/api/live")
async def live_sse(request: Request):
    queue = asyncio.Queue()
    sse_queues.append(queue)

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():
                    break
                data = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {data}\n\n"
        except asyncio.TimeoutError:
            pass
        finally:
            if queue in sse_queues:
                sse_queues.remove(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
