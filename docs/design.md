# Station Game – Design (v1 Universe-First)

## Vision
A living, persistent universe that evolves over real time. Players and AI exist as entities inside the same simulation. A player’s station is not the center of the game; the universe is.

- Star systems contain planets, moons, asteroid belts, and orbital lanes.
- AI factions may live on planets/moons/stations or roam as fleets.
- Many bodies have no AI presence but have resources that can be mined or salvaged.
- Friendly/neutral/hostile relationships exist between factions.
- Players can trade, explore, mine, raid, or wage war.
- If a player station is destroyed, the universe continues.

## Non-goals for v1 (Important)
The following are intentionally excluded from v1 to preserve scope:
- No real-time combat micro or tactics
- No per-second AI replay over long offline periods
- No player-controlled ship piloting
- No fully dynamic market pricing
- No sharding or multi-process simulation

These may be revisited in later versions once the universe simulation is stable.


## Core Gameplay Loop
**Scan → Extract → Move → Transform → Build → Defend/Expand**

Progress is primarily based on **materials + logistics + risk**, not passive credits.

## Player Start
The player starts with a tiny station with:
- low cargo capacity
- minimal power generation
- minimal defense
- limited build slots
- limited ability to operate ships

The early game is about survival and specialization:
- miner/industrial builder
- trader/logistics runner
- explorer/salvager
- raider/mercenary (later, abstract combat first)

## Resources (v1 target set)
Keep the set small and expandable:
- Power (generation/consumption budget; not a “stored” resource beyond buffers)
- Water
- Food
- Ore (raw)
- Alloys (refined construction material)
- Parts (manufactured components)

Optional later:
Fuel, Electronics, Medicine, Ammo, Rare/Exotic minerals, Research.

## Station Constraints (v1)
Pick constraints that force meaningful choices:
- Power budget
- Cargo capacity
- Crew/habitat capacity
- Docking/hangar capacity
- Threat/Defense rating

## Modules (v1 starter list)
Each module has:
- material cost (not just credits)
- build time
- maintenance/upkeep (later)
- requirements (power, crew, prerequisites)

Starter modules:
- Solar Array (Power +)
- Battery Bank (Buffer +)
- Habitat Pod (Crew cap +)
- Hydroponics (Food +, Power -)
- Water Recycler (Water +, Power -)
- Storage Bay (Cargo +)
- Docking Clamp (Trade/ship ops +)
- Basic Refinery (Ore → Alloys)
- Workshop (Alloys → Parts)
- Shield Emitter (Defense +, Power -)
- Point Defense (Defense +, Ammo later)
- Scanner Array (Exploration +)

## Ships (v1)
Ships are timed-event actors with cargo and travel time:
- Mining Drone: Extracts ore from a body over time (needs target site).
- Courier: Moves goods between locations (trade/logistics).
- Patrol Skiff: Basic defense/escort (abstract combat initially).

## Universe Model
Universe is the root simulation object.

Entities:
- System
- CelestialBody (planet/moon/asteroid belt) with resource nodes
- Station (player or AI controlled)
- Fleet/Ship (moves, mines, trades, raids)
- Faction (relationships, doctrine)
- Market/Contracts (later)
- EventQueue (build completion, arrival, raid resolution)

## Time & Simulation (Option A: Fixed Tick + Bounded Catch-up)

Goal: The universe feels alive, but the server never “replays” huge offline periods at full fidelity.

### Option A Summary
- **Fixed tick loop** advances the universe in real time (e.g. 1.0s).
- The server **autosaves snapshots** periodically (e.g. every 10–30s) and on important events.
- On restart, the universe performs a **bounded catch-up** (e.g. max 5 minutes), then resumes real-time ticking.
- AI decisions are **coarse + capped** during catch-up to avoid spikes.

### Definitions
- `tick_dt`: fixed sim step (start with 1.0s; can go 0.25s later).
- `ai_dt`: AI “think” cadence (start 10s).
- `catchup_max`: maximum offline time to simulate on boot (start 300s = 5 minutes).
- `autosave_dt`: how often we write to DB (start 15–30s).

### Startup / Restart Behavior
When the server starts:
1) Load `universe_state` from DB (including `last_update`).
2) Compute offline time: `offline = now - last_update`.
3) Apply **bounded catch-up**:
   - `catchup = min(offline, catchup_max)`
   - Advance the simulation by `catchup` using the same fixed tick step.
4) Resume background ticking at real time.

**Key rule:** We never try to faithfully simulate 24 hours of AI “thinking”. We only advance the sim state and process events; AI decisions are throttled.

### What runs every tick?
Each tick (fixed dt):
1) **Continuous resources:** `resource += rate * dt` (cheap, linear)
2) **Process timestamped events** whose `time <= now_sim` (build completes, arrivals, etc.)
3) **Apply queued order effects** (player/AI submitted “orders”)
4) **AI think step** runs only when due (every `ai_dt`) and is capped per tick.

### AI Catch-up Policy (very important)
During bounded catch-up:
- We may run **0 or very few** AI thinks.
- We apply a strict budget like:
  - max `N` AI decisions per catch-up tick, or
  - max total AI work time (future: time budget).
- Any “missed” AI thinking is simply skipped. The universe still advances via rates + events.

This keeps boot time predictable even with hundreds of AI factions.

### Persistence
- Autosave every `autosave_dt` seconds OR after important state changes.
- Persist:
  - `last_update` (sim time)
  - entities (stations, ships, nodes…)
  - pending events / queues
- SQLite is fine for single-host v1.

## AI Doctrines (v1)
Simple rule-based AI first:
- Trader: prioritizes cargo + docking + courier routes
- Miner/Industrial: prioritizes mining + refinery + storage
- Raider: prioritizes patrol/defense and opportunistic raids (later)
- Explorer/Salvager: prioritizes scanners and roaming

AI should appear “alive” but must be compute-bounded.

## Multiplayer
- Real players can log in occasionally.
- Universe runs regardless of player activity.
- Player actions submit “orders” to the simulation (build, trade, launch ship, etc.).

## Persistence (v1)
SQLite is acceptable for local/single-host server.
- Universe state persists (last_update + entity snapshots)
- Save on important events + periodic autosave
- Single authoritative server process writes to DB
- Store universe `last_update` and enforce `catchup_max` on boot to avoid long replays.

## v1 Milestones
### Milestone 1: Universe skeleton
- Universe exists and advances time
- A few AI stations exist and gain/consume resources
- Player station exists as a normal entity
- UI shows local snapshot
- Server background tick loop (Option A) + bounded catch-up on restart
- Autosave snapshot timer

### Milestone 2: Orders + build queue (materials + time)
- Build queue uses materials (pay on queue)
- Build completes as an event and modifies station

### Milestone 3: Mining + logistics
- Mining drone extracts ore from a resource node
- Courier moves cargo between stations/bodies

### Milestone 4: Trade (simple)
- AI traders move goods
- Player can trade with friendly stations

### Milestone 5: Risk (abstract)
- Hostile factions can raid
- Defense mitigates losses
- Stations can be damaged/destroyed
