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

Progress is driven by **materials + logistics + risk**, not by passive resource generation.

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

## Station & Module Model (v1)

Stations are **infrastructure platforms**, not cities.

They convert materials, enable logistics, and project power, but do not generate raw resources on their own.

---

### Crew (v1)
- Stations use **crew**, not population
- Crew is a simple capacity-based resource
- Modules require crew to operate
- No births, deaths, or morale in v1

Stations start with a small crew capacity and must build habitat modules to expand.

---

### Power (v1)
- Power is a **budget**, not a stored resource
- Modules consume or produce power
- Exceeding power capacity blocks installs (v1 rule: cannot exceed budgets)

---

### Modules (v1 Philosophy)
Each module:
- Consumes or produces power (power delta)
- Requires crew
- Consumes station slot capacity
- Provides one primary benefit

Modules fall into categories:
- Infrastructure (power, storage, crew)
- Industry (refining, manufacturing)
- Logistics & Info (docking, scanning)
- Defense (shields, point defense)
- Commerce (trade hubs, taxes – later)

---

### Module Costs
- Modules do **not** consume raw ore directly
- Costs are paid in refined materials and parts
- This enforces logistics and refining gameplay

---

### Slots & Scale
- Stations have limited module slots
- Planets > Moons > Stations in capacity and defense (future)
- Stations are small, specialized, and expendable
- Planets are major economic and defensive hubs (future)

---

### Upgrades
- Upgrades improve efficiency, not behavior
- Same module, better output
- No extra slot cost

---

### Ships & Movement
Ship mobility tiers:
- Local (drones)
- System (non-FTL)
- Interstellar (FTL)

FTL gates allow non-FTL ships to travel between systems and act as strategic choke points.

---

## Resources & Materials (v1)

### Important Clarification
There is **no single “Ore” resource**.

Instead, resources are represented as **material types**.

### Material Categories
- **Raw materials (ores)**  
  e.g. `iron_ore`, `copper_ore`, later `nickel_ore`, `titanium_ore`
- **Refined materials**  
  e.g. `iron_bar`, `copper_bar`, `alloy_plate`, `glass_pane`
- **Manufactured parts**  
  e.g. `computer_chip`, `computer_screen`, `parts_basic` (names may evolve)

### Inventory Format (implemented)
Materials are stored in station inventories as:

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

Scan level

Modules (v1 – definitions + build queue)
Module Definitions (implemented)

Modules are data definitions with:

id / name / category

power delta

crew required

slot cost

build time (seconds)

material cost (from material registry)

effects (caps, scan level, defense, etc.)

Build Queue (Option A – implemented and working)

Builds are server-authoritative timed events.

Rules (implemented):

One build at a time per station

Costs are paid when queued (materials are spent immediately)

Budget checks are validated upfront (preview after completion)

A build schedules an event:

type = "build_module_complete"

time = sim_time + build_time

When the event fires, the module is installed (idempotent + budget-safe)

Order → Event → Outcome (implemented path):

Client requests build: POST /api/stations/{id}/build/module

Server validates ownership + rules and queues an event

Universe tick loop advances sim_time and processes due events

Completion event installs module into station modules list

Ships (v1 – event-based, planned)

Ships are timed event actors, not continuously simulated:

Mining Drone (extracts materials from bodies)

Courier (moves inventory between locations)

Patrol Skiff (abstract defense)

No per-tick ship simulation.

Universe Model (Implemented Core)
Universe State (implemented)

Universe is the root simulation object stored as a single JSON snapshot in SQLite.

Includes:

sim_time

stations

bodies

events

Implemented Entities

Station (player-owned)

CelestialBody (asteroid belts)

Material registry

Module registry

Event queue (module builds)

Planned Entities

Systems

Fleets / Ships

Factions

Contracts / Markets

Time & Simulation (Option A – implemented)
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

Persistence (v1 – implemented)

SQLite

Single authoritative universe snapshot

Autosave + crash-safe

last_update used for bounded catch-up

Multiplayer (v1)

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

✅ Milestone 2: Module Definitions + Build Queue (DONE)

Module definitions with material costs

Build queue stored as timed events

Materials spent on queue (not per tick)

Build completion installs module into station

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