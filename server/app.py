import time
import secrets
import asyncio
from pathlib import Path

from fastapi import FastAPI, Body, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from server.game.db import get_conn
from server.game.auth import hash_password, verify_password
from server.game.world import World

app = FastAPI()

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

SESSION_COOKIE = "station_session"

WORLD_BY_USER: dict[int, World] = {}

RUNNING = True

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


def get_world(user_id: int) -> World:
    w = WORLD_BY_USER.get(user_id)
    if w is None:
        w = World()
        w.load_latest_station(user_id)  # ok if none exists
        WORLD_BY_USER[user_id] = w
    return w


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

# -------- Game API --------

@app.get("/api/state")
def api_state(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    w = get_world(user_id)
    w.maybe_tick()
    return w.snapshot()


@app.post("/api/new_station")
def api_new_station(request: Request, payload: dict = Body(...)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    name = (payload.get("name") or "New Station").strip()

    w = get_world(user_id)
    w.new_station(name)
    station_id = w.save_station(user_id)
    return {"ok": True, "station_id": station_id, "station": w.snapshot()}


@app.post("/api/save_station")
def api_save_station(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    w = get_world(user_id)
    w.maybe_tick()
    station_id = w.save_station(user_id)
    return {"ok": True, "station_id": station_id}


@app.get("/api/load_station")
def api_load_station(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    w = get_world(user_id)
    ok = w.load_latest_station(user_id)
    return {"ok": ok, "station": w.snapshot() if ok else None}


@app.post("/api/build/solar_array")
def api_build_solar_array(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="not_logged_in")

    w = get_world(user_id)
    w.maybe_tick()
    ok, reason = w.station.build("solar_array")
    return {"ok": ok, "reason": reason, "station": w.station.snapshot()}

@app.on_event("startup")
async def on_startup():
    global RUNNING
    RUNNING = True
    print("🚀 Server starting up")
    asyncio.create_task(game_loop())

@app.on_event("shutdown")
def on_shutdown():
    global RUNNING
    RUNNING = False
    print("🛑 Server shutting down cleanly")

async def game_loop():
    """
    Runs server-side ticks so AI + build queues progress even if nobody is polling.
    """
    sim_step = 0.25  # seconds; start simple (4 ticks/sec)
    ai_step = 2.0    # seconds; AI decisions less frequent

    ai_accum = 0.0

    while RUNNING:
        # tick all loaded worlds
        for w in WORLD_BY_USER.values():
            w.tick_fixed(sim_step)      # simulation step (resources, queues)
            # w.ai_step(ai_step)        # optional: AI decision step (later)

        ai_accum += sim_step
        if ai_accum >= ai_step:
            ai_accum = 0.0
            for w in WORLD_BY_USER.values():
                w.ai_step()  # you'll implement later (NPC actions)

        await asyncio.sleep(sim_step)


