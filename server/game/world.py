import time, json
from .db import init_db, get_conn
from .station import Station

class World:
    def __init__(self):
        self.station = Station("Alpha Station")
        self.last_update = time.time()
        init_db()

    def maybe_tick(self) -> None:
        now = time.time()
        dt = now - self.last_update
        self.last_update = now
        self.station.tick(dt)

    def snapshot(self) -> dict:
        return {
            "time": self.last_update,
            "station": self.station.snapshot(),
        }
    
    def save_station(self) -> int:
        state = json.dumps(self.station.to_dict())
        now = time.time()
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO stations (name, state_json, updated_at) VALUES (?, ?, ?)",
                (self.station.name, state, now),
            )
            return int(cur.lastrowid)

    def load_latest_station(self) -> bool:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id, state_json FROM stations ORDER BY id DESC LIMIT 1"
            ).fetchone()

        if row is None:
            return False

        data = json.loads(row["state_json"])
        self.station = Station.from_dict(data)
        self.last_update = time.time()
        return True
    
    def new_station(self, name: str) -> None:
        self.station = Station(name)
        self.last_update = time.time()

