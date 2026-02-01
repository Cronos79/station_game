import time
import secrets
from pathlib import Path

from fastapi import FastAPI, Body, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from server.game.db import get_conn, init_db
from server.game.auth import hash_password, verify_password
from server.sim.universe import Universe, UniverseConfig
from server.sim.materials import MATERIALS
from server.sim.modules import MODULES
from server.sim.modules import MODULES, get_module

from fastapi.staticfiles import StaticFiles

app = FastAPI()
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

SESSION_COOKIE = "station_session"

universe = Universe(UniverseConfig(tick_dt=1.0, autosave_dt=20.0, catchup_max=300.0))

@app.on_event("startup")
async def on_startup():
    init_db()
    universe.load()
    await universe.start()
    await universe.ensure_bootstrap_world()
    print("🚀 Server starting up (universe ticking)")


@app.on_event("shutdown")
async def on_shutdown():
    await universe.stop()
    print("🛑 Server shutting down cleanly")


def get_user_id_from_request(request: Request) -> int | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE token=?",
            (token,),
        ).fetchone()
    return int(row["user_id"]) if row else None


# -------- Pages --------

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return (WEB_DIR / "login.html").read_text(encoding="utf-8")


@app.get("/register", response_class=HTMLResponse)
def register_page():
    return (WEB_DIR / "register.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse("/login")
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


# -------- Auth API --------

@app.post("/api/register")
def api_register(payload: dict = Body(...)):
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="username_and_password_required")

    pw_hash = hash_password(password)
    now = time.time()

    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, pw_hash, now),
            )
            user_id = int(cur.lastrowid)
    except Exception:
        raise HTTPException(status_code=400, detail="username_taken")

    return {"ok": True, "user_id": user_id}


@app.post("/api/login")
def api_login(response: Response, payload: dict = Body(...)):
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="username_and_password_required")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username=?",
            (username,),
        ).fetchone()

    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    user_id = int(row["id"])
    token = secrets.token_urlsafe(32)
    now = time.time()

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, now),
        )

    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@app.post("/api/logout")
def api_logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with get_conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/me")
def api_me(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return {"ok": True, "user_id": None}

    with get_conn() as conn:
        row = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()

    return {"ok": True, "user_id": user_id, "username": row["username"] if row else None}

@app.get("/api/universe")
async def api_universe():
    snap = await universe.snapshot_async()

    # Attach derived station stats (server-side view)
    for s in snap.get("stations", []):
        s["derived"] = universe.compute_station_stats(s)

    return {"ok": True, "universe": snap}

@app.post("/api/universe/advance")
def api_universe_advance(payload: dict = Body(...)):
    # Debug endpoint for now.
    # Example body: { "dt": 5 }
    dt = float(payload.get("dt", 1.0))
    if dt < 0:
        raise HTTPException(status_code=400, detail="dt_must_be_non_negative")

    universe.advance(dt)
    universe.save()
    return {"ok": True, "universe": universe.snapshot()}

@app.post("/api/universe/ensure_player_station")
async def api_ensure_player_station(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    with get_conn() as conn:
        row = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()

    username = row["username"] if row else "Player"
    station_id = await universe.ensure_player_station(user_id, username)

    return {"ok": True, "station_id": station_id}

@app.get("/api/my/stations")
async def api_my_stations(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    snap = await universe.snapshot_async()
    mine = [
        s for s in snap.get("stations", [])
        if int(s.get("owner_user_id") or -1) == int(user_id)
    ]

    for s in mine:
        s["derived"] = universe.compute_station_stats(s)

    return {"ok": True, "stations": mine}

@app.get("/api/materials")
def api_materials():
    return {
        "ok": True,
        "materials": [
            {"id": m.id, "name": m.name, "category": m.category}
            for m in MATERIALS.values()
        ]
    }

@app.get("/api/bodies")
async def api_bodies():
    snap = await universe.snapshot_async()
    return {"ok": True, "bodies": snap.get("bodies", [])}

@app.get("/api/modules")
def api_modules():
    return {
        "ok": True,
        "modules": [
            {
                "id": m.id,
                "name": m.name,
                "category": m.category,
                "power_delta": m.power_delta,
                "crew_required": m.crew_required,
                "slot_cost": m.slot_cost,
                "build_time": m.build_time,
                "cost": m.cost,
                "effects": m.effects,
            }
            for m in MODULES.values()
        ],
    }

@app.post("/api/stations/{station_id}/build/module")
async def api_build_module(station_id: int, payload: dict = Body(...), request: Request = None):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    module_id = str(payload.get("module_id") or "").strip()
    if not module_id:
        raise HTTPException(status_code=400, detail="module_id_required")

    # Ownership check
    snap = await universe.snapshot_async()
    st = next((x for x in snap.get("stations", []) if int(x.get("id", -1)) == int(station_id)), None)
    if not st:
        raise HTTPException(status_code=404, detail="station_not_found")
    if int(st.get("owner_user_id", -1)) != int(user_id):
        raise HTTPException(status_code=403, detail="not_station_owner")

    try:
        event_id = await universe.queue_build_module(station_id, module_id)
    except ValueError as e:
        msg = str(e)

        if msg.startswith("module_not_found") or msg.startswith("station_not_found"):
            raise HTTPException(status_code=404, detail=msg)

        if msg in ("module_id_required",):
            raise HTTPException(status_code=400, detail=msg)

        # these are normal validation errors
        raise HTTPException(status_code=400, detail=msg)

    # Return some timing info for UI
    now_sim = float(universe.state.get("sim_time", 0.0))
    m = get_module(module_id)
    finishes_at = now_sim + float(m.build_time) if m else None

    return {"ok": True, "event_id": event_id, "finishes_at": finishes_at}


@app.post("/api/debug/stations/{station_id}/modules/add")
async def api_debug_add_module(station_id: int, payload: dict = Body(...), request: Request = None):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    module_id = str(payload.get("module_id") or "").strip()
    if not module_id:
        raise HTTPException(status_code=400, detail="module_id_required")

    snap = await universe.snapshot_async()
    st = next((x for x in snap.get("stations", []) if int(x.get("id", -1)) == station_id), None)
    if not st or int(st.get("owner_user_id", -1)) != int(user_id):
        raise HTTPException(status_code=403, detail="not_station_owner")
    
    try:
        await universe.add_module_to_station(station_id, module_id)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("station_not_found") or msg.startswith("module_not_found"):
            raise HTTPException(status_code=404, detail=msg)
        else:
            raise HTTPException(status_code=400, detail=msg)
    return {"ok": True}

@app.post("/api/debug/stations/{station_id}/modules/remove")
async def api_debug_remove_module(station_id: int, payload: dict = Body(...), request: Request = None):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    module_id = str(payload.get("module_id") or "").strip()
    if not module_id:
        raise HTTPException(status_code=400, detail="module_id_required")

    try:
        await universe.remove_module_from_station(station_id, module_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"ok": True}

@app.post("/api/debug/events/install_module")
async def api_debug_event_install_module(payload: dict = Body(...), request: Request = None):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    station_id = int(payload.get("station_id") or 0)
    module_id = str(payload.get("module_id") or "").strip()
    delay = float(payload.get("delay") or 5.0)

    if station_id <= 0:
        raise HTTPException(status_code=400, detail="station_id_required")
    if not module_id:
        raise HTTPException(status_code=400, detail="module_id_required")
    if delay < 0:
        raise HTTPException(status_code=400, detail="delay_must_be_non_negative")

    # Ownership check (so you can't schedule events for other people)
    snap = await universe.snapshot_async()
    st = next((x for x in snap.get("stations", []) if int(x.get("id", -1)) == station_id), None)
    if not st or int(st.get("owner_user_id", -1)) != int(user_id):
        raise HTTPException(status_code=403, detail="not_station_owner")

    now_sim = float(universe.state.get("sim_time", 0.0))
    fire_at = now_sim + delay

    # IMPORTANT: Universe.enqueue_event is not async; protect with lock here.
    async with universe._lock:
        eid = universe.enqueue_event(
            fire_at,
            "install_module",
            {"station_id": station_id, "module_id": module_id},
        )
        universe.save()

    return {"ok": True, "event_id": eid, "fires_at": fire_at}

@app.post("/api/debug/stations/{station_id}/grant")
async def api_debug_grant(station_id: int, payload: dict = Body(...), request: Request = None):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    material_id = str(payload.get("material_id") or "").strip()
    amount = float(payload.get("amount", 0))

    if not material_id or amount <= 0:
        raise HTTPException(status_code=400, detail="material_id_and_positive_amount_required")

    snap = await universe.snapshot_async()
    st = next((x for x in snap.get("stations", []) if int(x.get("id", -1)) == int(station_id)), None)
    if not st:
        raise HTTPException(status_code=404, detail="station_not_found")
    if int(st.get("owner_user_id", -1)) != int(user_id):
        raise HTTPException(status_code=403, detail="not_station_owner")

    async with universe._lock:
        s = universe._find_station_mut(station_id)
        inv = s.get("inventory")
        if not isinstance(inv, dict):
            inv = {}
            s["inventory"] = inv
        inv[material_id] = float(inv.get(material_id, 0.0)) + float(amount)
        universe.save()

    return {"ok": True}

