import os
import re
import sys

DB = None


def _parse_url(url):
    m = re.match(r"postgres(?:ql)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", url)
    if not m:
        return None
    return {"user": m.group(1), "password": m.group(2), "host": m.group(3), "port": int(m.group(4)), "database": m.group(5)}


def _connect():
    global DB
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("DATABASE_URL not set, running without database", flush=True)
        return None

    import psycopg2
    from psycopg2.extras import RealDictCursor
    params = _parse_url(url)
    if not params:
        print(f"Cannot parse DATABASE_URL: {url[:30]}...", flush=True)
        return None
    DB = psycopg2.connect(**params, cursor_factory=RealDictCursor)
    print("Database connected", flush=True)
    return DB


def init_db():
    db = _connect()
    if not db:
        return
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS readings (id SERIAL PRIMARY KEY, temp REAL NOT NULL, humidity REAL NOT NULL, ts BIGINT NOT NULL, created_at TIMESTAMP DEFAULT NOW())")
    cur.execute("CREATE TABLE IF NOT EXISTS config (key VARCHAR(32) PRIMARY KEY, value TEXT NOT NULL)")
    cur.execute("INSERT INTO config (key, value) VALUES ('target_temp','23.0'),('target_hum','50.0'),('alert_percent','2.0'),('chat_id','') ON CONFLICT (key) DO NOTHING")
    db.commit()
    cur.close()


def insert_reading(temp, humidity, ts):
    if not DB:
        return
    cur = DB.cursor()
    cur.execute("INSERT INTO readings (temp, humidity, ts) VALUES (%s,%s,%s)", (temp, humidity, ts))
    DB.commit()
    cur.close()


def get_readings(hours=24):
    if not DB:
        return []
    cur = DB.cursor()
    cur.execute("SELECT temp,humidity,ts FROM readings WHERE created_at > NOW() - INTERVAL %s HOURS ORDER BY ts ASC", (hours,))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_config():
    if not DB:
        return {}
    cur = DB.cursor()
    cur.execute("SELECT key,value FROM config")
    rows = cur.fetchall()
    cur.close()
    return {r["key"]: r["value"] for r in rows}


def set_config(key, value):
    if not DB:
        return
    cur = DB.cursor()
    cur.execute("INSERT INTO config (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=%s", (key, value, value))
    DB.commit()
    cur.close()
