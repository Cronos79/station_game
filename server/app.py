import time
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse
from pathlib import Path

from server.game.world import World

app = FastAPI()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

WORLD = World()


@app.get("/", response_class=HTMLResponse)
def home():
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/hello")
def hello():
    return {"message": "Hello from Python!", "ok": True}


@app.get("/api/state")
def state():
    WORLD.maybe_tick()
    return WORLD.snapshot()


@app.post("/api/build/solar_array")
def build_solar_array():
    WORLD.maybe_tick()
    ok, reason = WORLD.station.build("solar_array")
    return {"ok": ok, "reason": reason, "station": WORLD.station.snapshot()}

@app.post("/api/new_station")
def new_station(payload: dict = Body(...)):
    name = payload.get("name", "New Station")
    WORLD.new_station(name)   # (we’ll add this helper)
    station_id = WORLD.save_station()
    return {"ok": True, "station_id": station_id, "station": WORLD.snapshot()}

@app.post("/api/save_station")
def save_station():
    WORLD.maybe_tick()
    station_id = WORLD.save_station()
    return {"ok": True, "station_id": station_id}

@app.get("/api/save_station")
def save_station_get():
    WORLD.maybe_tick()
    station_id = WORLD.save_station()
    return {"ok": True, "station_id": station_id, "via": "GET (temporary)"}

@app.get("/api/load_station")
def load_station():
    ok = WORLD.load_latest_station()
    return {"ok": ok, "station": WORLD.snapshot() if ok else None}

