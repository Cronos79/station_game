# Station Game – Design (v1 Universe-First)

## Vision
A living, persistent universe that evolves over real time. Players and AI exist as entities inside the same simulation. A player’s station is not the center of the game; the universe is.

- Star systems contain planets, moons, asteroid belts, and orbital lanes.
- AI factions may live on planets/moons/stations or roam as fleets.
- Many bodies have no AI presence but have resources that can be mined or salvaged.
- Friendly/neutral/hostile relationships exist between factions.
- Players can trade, explore, mine, raid, or wage war.
- If a player station is destroyed, the universe continues.

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

## Time & Simulation
We avoid per-second “replay” over long offline time.

Three layers:
1) **Continuous simulation**: resources updated via `resources += rates * dt` (O(N)).
2) **Discrete events**: build completions, arrivals, etc. processed by timestamps (O(E)).
3) **AI decisions**: coarse cadence and capped catch-up work to prevent spikes.

Cadences (initial targets):
- Sim tick: 0.25–1.0s (server background loop)
- AI think: every 5–30s depending on cost
- Catch-up: process resources/events exactly; cap AI decisions per catch-up window

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

## v1 Milestones
### Milestone 1: Universe skeleton
- Universe exists and advances time
- A few AI stations exist and gain/consume resources
- Player station exists as a normal entity
- UI shows local snapshot

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
