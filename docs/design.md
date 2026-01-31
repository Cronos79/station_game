# Station Game – Design (v1 Universe-First)

## Vision
A living, persistent universe that evolves over real time. Players and AI exist as entities inside the same simulation. A player’s station is **not** the center of the game; the universe is.

- Star systems contain planets, moons, asteroid belts, and orbital lanes.
- AI factions may live on planets/moons/stations or roam as fleets.
- Many bodies have no AI presence but contain **material resources**.
- Friendly / neutral / hostile relationships exist between factions.
- Players can trade, explore, mine, raid, or wage war.
- If a player station is destroyed, the universe continues.

---

## Non-Goals for v1 (Scope Control)
The following are intentionally excluded from v1:
- No real-time combat micro or tactics
- No per-second AI replay over long offline periods
- No player-controlled ship piloting
- No fully dynamic market pricing
- No sharding or multi-process simulation

---

## Core Gameplay Loop
**Scan → Extract → Move → Transform → Build → Defend / Expand**

Progress is driven by **materials + logistics + risk**,  
**not** by passive resource generation.

---

## Player Start
The player starts with a tiny station:
- minimal power
- minimal storage
- minimal defense
- limited build slots
- limited ship operations

Early gameplay focuses on survival and specialization:
- industrial builder
- trader / logistics
- explorer / salvager
- raider / mercenary (abstracted combat later)

---

## Resources & Materials (v1)

### Important Clarification
There is **no single “Ore” resource**.

Instead, resources are represented as **material types**.

### Material Categories
- **Raw materials (ores)**  
  e.g. `iron_ore`, `copper_ore`, later `nickel_ore`, `titanium_ore`
- **Refined materials**  
  e.g. `alloy_plate`
- **Manufactured parts**  
  e.g. `parts_basic`

### Current v1 Material Registry (implemented)
- Iron Ore
- Copper Ore
- Alloy Plate
- Basic Parts

Materials are stored in **station inventories** as:
json
"inventory": {
  "iron_ore": 5,
  "copper_ore": 2
}

Celestial Bodies (v1)

Bodies exist as data-only entities (no mining yet):

Planet

Moon

Asteroid Belt

Each body defines material availability weights, not quantities:

"materials": {
  "iron_ore": 0.7,
  "copper_ore": 0.2
}


This defines what can be found here, not how much is extracted.

Station Constraints (v1)

Constraints force meaningful decisions:

Power budget

Cargo capacity

Crew / habitat capacity

Docking / hangar capacity

Defense rating

Modules (v1 – definitions first)

Modules are definitions + costs before build logic.

Each module has:

material cost (using material registry)

build time

requirements (power, prerequisites)

maintenance (later)

Starter module definitions:

Solar Array

Battery Bank

Habitat Pod

Hydroponics

Water Recycler

Storage Bay

Docking Clamp

Basic Refinery

Workshop

Shield Emitter

Point Defense

Scanner Array

Ships (v1 – event-based)

Ships are timed event actors, not continuously simulated:

Mining Drone (extracts materials from bodies)

Courier (moves inventory between locations)

Patrol Skiff (abstract defense)

No per-tick ship simulation.

Universe Model (Implemented Core)

Universe is the root simulation object.

Implemented Entities

Station (player-owned)

CelestialBody (asteroid belts implemented)

Material registry

Universe state (JSON snapshot)

Planned Entities

Systems

Fleets / Ships

Factions

Event Queue

Contracts / Markets

Time & Simulation (Option A – Implemented)
Core Behavior

Fixed tick loop (1.0s)

Autosave every ~20s

Bounded catch-up on restart (max 300s)

Universe time (sim_time) always advances

Important Rule

Physical resources do NOT increase per tick.

Only these advance per tick:

simulation time

passive credits (optional / minimal)

scheduled events

All material gain happens via events (mining, trade, salvage).

Persistence (v1 – Implemented)

SQLite

Single authoritative universe snapshot

Autosave + crash-safe

last_update used for bounded catch-up

Multiplayer

Universe runs regardless of player activity

Players submit orders

Orders become events

No continuous player simulation

v1 Milestones (Updated)
✅ Milestone 1: Universe Skeleton (DONE)

Universe exists and advances time

Background tick loop + bounded catch-up

Persistent universe snapshot

Player station entity

Station inventory + credits

Material registry

Celestial bodies with material availability

🔜 Milestone 2: Module Definitions + Build Queue

Module definitions with material costs

Build queue stored as events

Materials spent on queue, not per tick

Build completion modifies station

🔜 Milestone 3: Mining & Logistics

Mining drone events

Material extraction from bodies

Courier movement between locations

🔜 Milestone 4: Trade

AI traders

Player trading

Simple pricing

🔜 Milestone 5: Risk

Abstract raids

Defense mitigation

Station damage/destruction

Design Principle (v1)

Nothing in v1 depends on per-tick material generation.
Everything meaningful happens via orders → events → outcomes.
