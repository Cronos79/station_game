import time
import json

from .db import init_db, get_conn
from .station import Station


class World:
    def __init__(self):
        init_db()
        self.station = Station("Alpha Station")
        self.last_update = time.time()

    def maybe_tick(self) -> None:
        now = time.time()
        dt = now - self.last_update
        self.last_update = now
        self.station.tick(dt)

    def ai_step(self) -> None:
        # run “big decisions” sometimes
        #for ai in self.ai_factions:
        #    ai.think(self)
        pass

    def tick_fixed(self, dt: float) -> None:
        # advance world by exactly dt seconds
        self.station.tick(dt)

    def snapshot(self) -> dict:
        return {
            "time": self.last_update,
            "station": self.station.snapshot(),
        }

    def new_station(self, name: str) -> None:
        self.station = Station(name)
        self.last_update = time.time()

    def save_station(self, user_id: int) -> int:
        state = json.dumps(self.station.to_dict())
        now = time.time()
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO stations (user_id, name, state_json, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, self.station.name, state, now),
            )
            return int(cur.lastrowid)

    def load_latest_station(self, user_id: int) -> bool:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT state_json FROM stations WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()

        if row is None:
            return False

        data = json.loads(row["state_json"])
        self.station = Station.from_dict(data)
        self.last_update = time.time()
        return True
