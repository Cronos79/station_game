import time
import secrets
from pathlib import Path

from fastapi import FastAPI, Body, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from server.game.db import get_conn, init_db
from server.game.auth import hash_password, verify_password
from server.sim.universe import Universe, UniverseConfig
from server.sim.materials import MATERIALS

app = FastAPI()
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

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
    return {"ok": True, "universe": await universe.snapshot_async()}


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