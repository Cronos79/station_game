import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "game.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")

        # --- Auth ---
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at REAL NOT NULL
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # --- Prototype legacy (v0) ---
        conn.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            state_json TEXT NOT NULL,
            updated_at REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # --- Universe v1 ---
        conn.execute("""
        CREATE TABLE IF NOT EXISTS universe_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state_json TEXT NOT NULL,
            last_update REAL NOT NULL
        )
        """)

        # Ensure universe_state has its singleton row (id=1)
        row = conn.execute("SELECT id FROM universe_state WHERE id=1").fetchone()
        if row is None:
            default_state = {
                "version": 1,
                "sim_time": 0.0,
                "stations": [],
                "events": []
            }
            conn.execute(
                "INSERT INTO universe_state (id, state_json, last_update) VALUES (1, ?, ?)",
                (json.dumps(default_state), time.time())
            )
