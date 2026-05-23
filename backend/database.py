import os
import sys
from urllib.parse import urlparse, unquote

DB = None


def _parse_url(url):
    try:
        parsed = urlparse(url)
        return {
            "user": unquote(parsed.username),
            "password": unquote(parsed.password),
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip("/"),
        }
    except Exception:
        return None


def _connect():
    global DB
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("DATABASE_URL not set, running without database", flush=True)
        return None

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        params = _parse_url(url)
        if not params:
            print(f"Cannot parse DATABASE_URL", flush=True)
            return None
        DB = psycopg2.connect(**params, cursor_factory=RealDictCursor)
        print("Database connected", flush=True)
        return DB
    except Exception as e:
        print(f"Database connection error: {e}", flush=True)
        return None


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


def _ensure_db():
    global DB
    if DB is not None:
        try:
            cur = DB.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return DB
        except Exception:
            DB = None
    return _connect()


def _exec(query, params=None, fetch=False, commit=False):
    db = _ensure_db()
    if not db:
        return [] if fetch else None
    try:
        cur = db.cursor()
        cur.execute(query, params or ())
        if fetch:
            rows = cur.fetchall()
            cur.close()
            return rows
        if commit:
            db.commit()
        cur.close()
    except Exception as e:
        print(f"DB error: {e}", flush=True)
        try:
            db.rollback()
        except Exception:
            pass
    return [] if fetch else None


def init_db():
    _exec("CREATE TABLE IF NOT EXISTS readings (id SERIAL PRIMARY KEY, temp REAL NOT NULL, humidity REAL NOT NULL, ts BIGINT NOT NULL, created_at TIMESTAMP DEFAULT NOW())", commit=True)
    _exec("CREATE TABLE IF NOT EXISTS config (key VARCHAR(32) PRIMARY KEY, value TEXT NOT NULL)", commit=True)
    _exec("INSERT INTO config (key, value) VALUES ('target_temp','23.0'),('target_hum','50.0'),('alert_percent','2.0'),('chat_id','') ON CONFLICT (key) DO NOTHING", commit=True)


def insert_reading(temp, humidity, ts):
    _exec("INSERT INTO readings (temp, humidity, ts) VALUES (%s,%s,%s)", (temp, humidity, ts), commit=True)


def get_readings(hours=24):
    return _exec("SELECT temp,humidity,ts FROM readings WHERE created_at > NOW() - %s::INTERVAL ORDER BY ts ASC", (f"{hours} hours",), fetch=True)


def get_config():
    rows = _exec("SELECT key,value FROM config", fetch=True)
    if not rows:
        return {}
    try:
        return {r["key"]: r["value"] for r in rows}
    except TypeError:
        return {r[0]: r[1] for r in rows}


def set_config(key, value):
    _exec("INSERT INTO config (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=%s", (key, value, value), commit=True)
