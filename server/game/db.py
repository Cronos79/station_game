import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "game.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            state_json TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """)
