import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id SERIAL PRIMARY KEY,
            temp REAL NOT NULL,
            humidity REAL NOT NULL,
            ts BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key VARCHAR(32) PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cur.execute("""
        INSERT INTO config (key, value) VALUES
            ('target_temp', '23.0'),
            ('target_hum', '50.0'),
            ('alert_percent', '2.0'),
            ('chat_id', '')
        ON CONFLICT (key) DO NOTHING
    """)
    conn.commit()
    cur.close()
    conn.close()


def insert_reading(temp, humidity, ts):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO readings (temp, humidity, ts) VALUES (%s, %s, %s)",
        (temp, humidity, ts),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_readings(hours=24):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT temp, humidity, ts FROM readings WHERE created_at > NOW() - INTERVAL '%s hours' ORDER BY ts ASC",
        (hours,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_config():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM config")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def set_config(key, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s",
        (key, value, value),
    )
    conn.commit()
    cur.close()
    conn.close()


def cleanup_old_readings():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM readings WHERE created_at < NOW() - INTERVAL '7 days'")
    conn.commit()
    cur.close()
    conn.close()
