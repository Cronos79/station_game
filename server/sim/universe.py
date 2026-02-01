# server/sim/universe.py
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from server.game.db import get_conn
from server.sim.entities import Station
from server.sim.materials import is_valid_material
from server.sim.modules import get_module


@dataclass
class UniverseConfig:
    tick_dt: float = 1.0        # sim seconds per tick
    autosave_dt: float = 20.0   # save every N sim seconds
    catchup_max: float = 300.0  # max offline seconds to simulate


class Universe:
    """
    Universe stored as a single JSON blob in universe_state (Option 1).
    This class keeps an in-memory copy (self.state) and periodically saves it.
    """

    BASE_STATION_STATS = {
        "slot_cap": 4.0,
        "power_cap": 8.0,   # built-in starter reactor
        "crew_cap": 5.0,    # built-in starter crew capacity
        "cargo_cap": 25.0,
        "dock_cap": 0.0,
        "defense": 0.0,
        "scan_level": 0.0,
    }

    def __init__(self, cfg: UniverseConfig | None = None):
        self.cfg = cfg or UniverseConfig()

        self.state: Dict[str, Any] = {
            "version": 1,
            "sim_time": 0.0,
            "stations": [],
            "bodies": [],
            "events": [],
        }

        self.last_update_real: float = time.time()

        # Background task control
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

        # Autosave tracking (in sim time)
        self._last_autosave_sim: float = 0.0

        # Simple lock so tick/save and API reads don't fight
        self._lock = asyncio.Lock()

    # ----------------------------
    # Station derived stats + budgets
    # ----------------------------

    def compute_station_stats(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """
        Derived station stats from base + installed module effects.

        Returns:
        - caps: totals after module effects
        - usage: power_used, crew_used, slots_used
        - modules: module ids
        """
        stats = dict(self.BASE_STATION_STATS)

        power_used = 0.0
        crew_used = 0.0
        slots_used = 0.0

        module_ids = station.get("modules") or []
        if not isinstance(module_ids, list):
            module_ids = []

        for mid in module_ids:
            m = get_module(str(mid))
            if not m:
                continue  # ignore unknown module ids for now

            # Apply effects (power_cap, crew_cap, cargo_cap, defense, etc.)
            for k, v in (m.effects or {}).items():
                stats[k] = float(stats.get(k, 0.0)) + float(v)

            # Track usage (what it costs to keep it running)
            if m.power_delta < 0:
                power_used += -float(m.power_delta)  # consumption
            crew_used += float(m.crew_required)
            slots_used += float(m.slot_cost)

        return {
            "caps": stats,
            "usage": {
                "power_used": power_used,
                "crew_used": crew_used,
                "slots_used": slots_used,
            },
            "modules": [str(x) for x in module_ids],
        }

    def _find_station_mut(self, station_id: int) -> Dict[str, Any]:
        """Find the *actual* station dict inside self.state (mutable reference)."""
        for s in self.state.get("stations", []):
            if int(s.get("id", -1)) == int(station_id):
                return s
        raise ValueError(f"station_not_found: {station_id}")

    def _preview_stats_after_add(self, station: Dict[str, Any], module_id: str) -> Dict[str, Any]:
        """Return derived stats *as if* module_id were added to station.modules. Does not mutate."""
        temp = dict(station)
        modules = list(temp.get("modules") or [])
        modules.append(module_id)
        temp["modules"] = modules
        return self.compute_station_stats(temp)

    def _budget_problems(self, derived: Dict[str, Any]) -> list[str]:
        """Return a list of human-readable budget problems. Empty list means OK."""
        caps = derived.get("caps", {}) or {}
        usage = derived.get("usage", {}) or {}

        def f(x: Any) -> float:
            try:
                return float(x)
            except Exception:
                return 0.0

        problems: list[str] = []

        slots_used = f(usage.get("slots_used"))
        slots_cap = f(caps.get("slot_cap"))
        if slots_used > slots_cap + 1e-9:
            problems.append(f"Slots: {slots_used:.2f} / {slots_cap:.2f}")

        crew_used = f(usage.get("crew_used"))
        crew_cap = f(caps.get("crew_cap"))
        if crew_used > crew_cap + 1e-9:
            problems.append(f"Crew: {crew_used:.2f} / {crew_cap:.2f}")

        power_used = f(usage.get("power_used"))
        power_cap = f(caps.get("power_cap"))
        if power_used > power_cap + 1e-9:
            problems.append(f"Power: {power_used:.2f} / {power_cap:.2f}")

        return problems

    def _install_module_nolock(self, station_id: int, module_id: str) -> None:
        """
        Install module into station (NO LOCK).
        Idempotent. Re-checks budgets for safety.
        """
        module_id = str(module_id).strip()
        if not module_id:
            return

        if not get_module(module_id):
            return

        station = self._find_station_mut(station_id)

        mods = station.get("modules")
        if not isinstance(mods, list):
            mods = []
            station["modules"] = mods

        if module_id in mods:
            return

        preview = self._preview_stats_after_add(station, module_id)
        problems = self._budget_problems(preview)
        if problems:
            return

        mods.append(module_id)

    async def add_module_to_station(self, station_id: int, module_id: str) -> None:
        """
        Debug/instant install (still validated server-side).
        """
        module_id = str(module_id).strip()
        if not module_id:
            raise ValueError("module_id_required")
        if not get_module(module_id):
            raise ValueError(f"module_not_found: {module_id}")

        async with self._lock:
            station = self._find_station_mut(station_id)
            mods = station.get("modules")
            if not isinstance(mods, list):
                station["modules"] = []
                mods = station["modules"]

            if module_id in mods:
                raise ValueError(f"module_already_installed: {module_id}")

            derived_preview = self._preview_stats_after_add(station, module_id)
            problems = self._budget_problems(derived_preview)
            if problems:
                raise ValueError("over_budget: " + "; ".join(problems))

            self._install_module_nolock(station_id, module_id)
            self.save()

    async def remove_module_from_station(self, station_id: int, module_id: str) -> None:
        module_id = str(module_id).strip()
        async with self._lock:
            station = self._find_station_mut(station_id)

            mods = station.get("modules")
            if not isinstance(mods, list):
                station["modules"] = []
                raise ValueError(f"module_not_installed: {module_id}")

            if module_id not in mods:
                raise ValueError(f"module_not_installed: {module_id}")

            mods.remove(module_id)
            self.save()

    # ----------------------------
    # Econ
    # ----------------------------

    def _try_spend(self, inventory: Dict[str, float], cost: Dict[str, float]) -> bool:
        """Return True and subtract items if inventory covers cost; else False."""
        for item, amount in cost.items():
            have = float(inventory.get(item, 0.0))
            if have < float(amount):
                return False

        for item, amount in cost.items():
            inventory[item] = float(inventory.get(item, 0.0)) - float(amount)
            if inventory[item] <= 1e-9:
                del inventory[item]

        return True

    def _clean_inventory(self, inv: Dict[str, float]) -> None:
        """
        Remove invalid materials and normalize amounts to floats.
        Keeps saves clean if you ever typo an id.
        """
        bad_keys = [k for k in inv.keys() if not is_valid_material(str(k))]
        for k in bad_keys:
            del inv[k]

        for k in list(inv.keys()):
            inv[k] = float(inv[k])
            if inv[k] <= 1e-9:
                del inv[k]

    # ----------------------------
    # bodies
    # ----------------------------

    async def ensure_bootstrap_world(self) -> None:
        """Ensure the universe has at least a starter system layout. Safe to call multiple times."""
        async with self._lock:
            if self.state.get("bodies"):
                return

            from server.sim.bodies import Body

            bodies = [
                Body(
                    id=1,
                    system="Sol",
                    name="Sol - Inner Belt",
                    type="asteroid_belt",
                    x=25.0,
                    y=5.0,
                    materials={"iron_ore": 0.7, "copper_ore": 0.2},
                ),
                Body(
                    id=2,
                    system="Sol",
                    name="Sol - Outer Belt",
                    type="asteroid_belt",
                    x=-40.0,
                    y=10.0,
                    materials={"iron_ore": 0.5, "copper_ore": 0.1},
                ),
            ]

            self.state["bodies"] = [b.to_dict() for b in bodies]
            self.save()

    # ----------------------------
    # Entities
    # ----------------------------

    async def ensure_player_station(self, user_id: int, username: str) -> int:
        async with self._lock:
            stations = self.state.get("stations", [])

            # 1) If station exists, migrate missing fields and return it
            for s in stations:
                if s.get("owner_user_id") == user_id:
                    changed = False

                    if "inventory" not in s or not isinstance(s.get("inventory"), dict):
                        s["inventory"] = {}
                        changed = True

                    self._clean_inventory(s["inventory"])

                    if "credits" not in s:
                        s["credits"] = 0.0
                        changed = True

                    if "modules" not in s or not isinstance(s.get("modules"), list):
                        s["modules"] = []
                        changed = True

                    if changed:
                        self.save()

                    return int(s["id"])

            # 2) Otherwise create a new station
            next_id = 1
            if stations:
                next_id = max(int(s["id"]) for s in stations) + 1

            st = Station(
                id=next_id,
                name=f"{username}'s Station",
                owner_user_id=user_id,
                system="Sol",
                x=0.0,
                y=0.0,
                credits=1000.0,
                inventory={"iron_ore": 5.0, "copper_ore": 2.0},
                modules=[],
            )

            stations.append(st.to_dict())
            self.state["stations"] = stations
            self.save()

            return st.id

    # ----------------------------
    # Events (v1) - single system
    # ----------------------------

    def _get_events_mut(self) -> list[Dict[str, Any]]:
        """Return the actual mutable events list in self.state, ensuring it exists."""
        ev = self.state.get("events")
        if not isinstance(ev, list):
            ev = []
            self.state["events"] = ev
        return ev

    def _next_event_id(self) -> int:
        """Simple monotonically increasing event id (scan max; fine for v1)."""
        ev = self._get_events_mut()
        if not ev:
            return 1
        best = 0
        for e in ev:
            try:
                best = max(best, int(e.get("id", 0)))
            except Exception:
                pass
        return best + 1

    def enqueue_event(self, when_sim: float, type_: str, data: Dict[str, Any]) -> int:
        """
        Add an event to the universe at sim time 'when_sim'.
        Events are kept ordered by time.
        """
        eid = self._next_event_id()
        e = {
            "id": int(eid),
            "time": float(when_sim),
            "type": str(type_),
            "data": dict(data or {}),
        }
        ev = self._get_events_mut()
        ev.append(e)
        ev.sort(key=lambda x: float(x.get("time", 0.0)))
        return int(eid)

    def _station_has_pending_build(self, station_id: int) -> bool:
        """One-build-at-a-time rule (pending build completion event exists)."""
        for e in self._get_events_mut():
            if str(e.get("type", "")) != "build_module_complete":
                continue
            data = e.get("data") or {}
            if not isinstance(data, dict):
                continue
            if int(data.get("station_id", -1)) == int(station_id):
                return True
        return False

    def _process_one_event(self, e: Dict[str, Any]) -> None:
        et = str(e.get("type", ""))
        data = e.get("data") or {}
        if not isinstance(data, dict):
            data = {}

        # Both event types ultimately install a module
        if et in ("build_module_complete", "install_module"):
            station_id = int(data.get("station_id", -1))
            module_id = str(data.get("module_id", "")).strip()
            if station_id <= 0 or not module_id:
                return

            # install module (idempotent + budget safe)
            self._install_module_nolock(station_id, module_id)
            return

        # Unknown event types: ignore for now
        return
        
    def _process_due_events(self) -> int:
        """
        Process all events with time <= current sim_time.
        Returns how many events were processed.
        """
        sim_time = float(self.state.get("sim_time", 0.0))
        ev = self._get_events_mut()
        if not ev:
            return 0

        processed: list[Dict[str, Any]] = []
        while ev and float(ev[0].get("time", 0.0)) <= sim_time + 1e-9:
            processed.append(ev.pop(0))

        for e in processed:
            try:
                self._process_one_event(e)
            except Exception:
                # For v1: swallow errors to avoid killing the sim loop
                pass

        return len(processed)

    # ----------------------------
    # Build queue (v1)
    # ----------------------------

    async def queue_build_module(self, station_id: int, module_id: str) -> Dict[str, Any]:
        """
        Queue a module build:
        - one build at a time per station
        - validate module exists
        - validate not already installed
        - validate budgets AFTER completion (preview)
        - validate inventory has cost and spend immediately
        - schedule build_module_complete event at sim_time + build_time

        Returns: { event_id, finishes_at }
        """
        module_id = str(module_id).strip()
        if not module_id:
            raise ValueError("module_id_required")

        m = get_module(module_id)
        if not m:
            raise ValueError(f"module_not_found: {module_id}")

        async with self._lock:
            station = self._find_station_mut(station_id)

            mods = station.get("modules")
            if not isinstance(mods, list):
                mods = []
                station["modules"] = mods

            if module_id in mods:
                raise ValueError(f"module_already_installed: {module_id}")

            if self._station_has_pending_build(station_id):
                raise ValueError("build_in_progress")

            # budget preview (after install)
            derived_preview = self._preview_stats_after_add(station, module_id)
            problems = self._budget_problems(derived_preview)
            if problems:
                raise ValueError("over_budget: " + "; ".join(problems))

            inv = station.get("inventory")
            if not isinstance(inv, dict):
                inv = {}
                station["inventory"] = inv

            self._clean_inventory(inv)

            cost = m.cost or {}
            if cost:
                if not self._try_spend(inv, {str(k): float(v) for k, v in cost.items()}):
                    raise ValueError("insufficient_materials")

            sim_time = float(self.state.get("sim_time", 0.0))
            finishes_at = sim_time + float(m.build_time)

            event_id = self.enqueue_event(
                finishes_at,
                "build_module_complete",
                {"station_id": int(station_id), "module_id": module_id},
            )

            self.save()
            return {"event_id": int(event_id), "finishes_at": float(finishes_at)}

    # ----------------------------
    # DB persistence
    # ----------------------------

    def load(self) -> None:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT state_json, last_update FROM universe_state WHERE id=1"
            ).fetchone()

        if row is None:
            raise RuntimeError("universe_state row missing (id=1). Did init_db() run?")

        self.state = json.loads(row["state_json"])
        self.last_update_real = float(row["last_update"])
        self._last_autosave_sim = float(self.state.get("sim_time", 0.0))

    def save(self) -> None:
        now = time.time()
        with get_conn() as conn:
            conn.execute(
                "UPDATE universe_state SET state_json=?, last_update=? WHERE id=1",
                (json.dumps(self.state), now),
            )
        self.last_update_real = now

    # ----------------------------
    # Simulation
    # ----------------------------

    def advance(self, dt: float) -> None:
        """Advance simulation time by dt seconds."""
        if dt <= 0:
            return

        self.state["sim_time"] = float(self.state.get("sim_time", 0.0)) + float(dt)

        # Passive income (tiny, just to prove economy)
        for s in self.state.get("stations", []):
            if s.get("owner_user_id") is not None:
                s["credits"] = float(s.get("credits", 0.0)) + 0.1 * float(dt)

        # Process any events that are now due
        self._process_due_events()

    def snapshot(self) -> Dict[str, Any]:
        """Safe snapshot for API responses."""
        return json.loads(json.dumps(self.state))

    # ----------------------------
    # Tick loop (Option A)
    # ----------------------------

    async def start(self) -> None:
        """Start the background tick loop (bounded catch-up first)."""
        await self._bounded_catchup()
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the tick loop and save once."""
        self._stop.set()
        if self._task:
            await self._task
            self._task = None

        async with self._lock:
            self.save()

    async def _bounded_catchup(self) -> None:
        """If server was offline, simulate up to catchup_max seconds."""
        now = time.time()
        offline = max(0.0, now - self.last_update_real)
        catchup = min(offline, self.cfg.catchup_max)

        if catchup <= 0:
            return

        steps = int(catchup // self.cfg.tick_dt)
        remainder = catchup - steps * self.cfg.tick_dt

        async with self._lock:
            for _ in range(steps):
                self.advance(self.cfg.tick_dt)
            if remainder > 1e-6:
                self.advance(remainder)

            self.save()
            self._last_autosave_sim = float(self.state.get("sim_time", 0.0))

    async def _run_loop(self) -> None:
        """
        Real-time tick loop.
        Every tick_dt real seconds:
          - advance sim by tick_dt
          - autosave every autosave_dt sim seconds
        """
        next_wall = time.time()
        while not self._stop.is_set():
            next_wall += self.cfg.tick_dt
            sleep_for = max(0.0, next_wall - time.time())

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=sleep_for)
                break
            except asyncio.TimeoutError:
                pass

            async with self._lock:
                self.advance(self.cfg.tick_dt)

                sim_time = float(self.state.get("sim_time", 0.0))
                if (sim_time - self._last_autosave_sim) >= self.cfg.autosave_dt:
                    self.save()
                    self._last_autosave_sim = sim_time

    async def snapshot_async(self) -> Dict[str, Any]:
        async with self._lock:
            return self.snapshot()
