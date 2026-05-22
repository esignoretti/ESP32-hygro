import os
import re

DB = None
COLUMNS = ["id", "temp", "humidity", "ts", "created_at"]
CONFIG_COLUMNS = ["key", "value"]


def _parse_url(url):
    m = re.match(r"postgres(?:ql)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", url)
    if not m:
        return None
    return {"user": m.group(1), "password": m.group(2), "host": m.group(3), "port": int(m.group(4)), "database": m.group(5)}


def _connect():
    global DB
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return None
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        params = _parse_url(url)
        if params:
            DB = psycopg2.connect(**params, cursor_factory=RealDictCursor)
            return DB
    except Exception:
        pass
    return None


def _rows(cur):
    try:
        return cur.fetchall()
    except Exception:
        return []


def init_db():
    db = _connect()
    if not db:
        return
    try:
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS readings (id SERIAL PRIMARY KEY, temp REAL NOT NULL, humidity REAL NOT NULL, ts BIGINT NOT NULL, created_at TIMESTAMP DEFAULT NOW())")
        cur.execute("CREATE TABLE IF NOT EXISTS config (key VARCHAR(32) PRIMARY KEY, value TEXT NOT NULL)")
        cur.execute("INSERT INTO config (key, value) VALUES ('target_temp','23.0'),('target_hum','50.0'),('alert_percent','2.0'),('chat_id','') ON CONFLICT (key) DO NOTHING")
        db.commit()
        cur.close()
    except Exception as e:
        print(f"DB init error: {e}", flush=True)


def insert_reading(temp, humidity, ts):
    if not DB:
        return
    try:
        cur = DB.cursor()
        cur.execute("INSERT INTO readings (temp, humidity, ts) VALUES (%s,%s,%s)", (temp, humidity, ts))
        DB.commit()
        cur.close()
    except Exception:
        try:
            DB.rollback()
        except Exception:
            pass


def get_readings(hours=24):
    if not DB:
        return []
    try:
        cur = DB.cursor()
        cur.execute("SELECT temp,humidity,ts FROM readings WHERE created_at > NOW() - INTERVAL %s HOURS ORDER BY ts ASC", (hours,))
        return cur.fetchall()
    except Exception:
        return []


def get_config():
    if not DB:
        return {}
    try:
        cur = DB.cursor()
        cur.execute("SELECT key,value FROM config")
        return {r["key"]: r["value"] for r in _rows(cur)}
    except Exception:
        return {}


def set_config(key, value):
    if not DB:
        return
    try:
        cur = DB.cursor()
        cur.execute("INSERT INTO config (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=%s", (key, value, value))
        DB.commit()
        cur.close()
    except Exception:
        try:
            DB.rollback()
        except Exception:
            pass
