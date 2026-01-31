# Station Game

A browser-based sci-fi **station management and universe simulation** game.

The game is built around a **persistent, server-authoritative universe** that continues to evolve whether or not players are logged in. Player stations exist *inside* the universe — they are not the center of it.

---

## Core Idea

- One living universe
- Time always advances
- Player actions become **orders**
- Orders resolve as **events**
- Materials and progress come from actions, not idle ticking

---

## Tech Stack

- **Python + FastAPI** — game server & API
- **SQLite** — persistent universe state
- **HTML + JavaScript** — browser client
- **Server-authoritative simulation** with bounded catch-up

---

## Current Features (Implemented)

### Universe & Simulation
- Persistent universe state stored as a single snapshot
- Fixed tick simulation loop
- Bounded catch-up on server restart
- Periodic autosave
- Server continues running with or without players

### Entities
- Player stations as universe entities
- Celestial bodies (asteroid belts) with material availability
- Material registry (canonical material definitions)

### Economy & Data Model
- Station credits
- Station material inventories (multiple material types)
- No per-tick material generation
- All meaningful progress is event-based

### API
- Authentication (register / login / sessions)
- Universe snapshot endpoint
- Materials registry endpoint
- Celestial bodies endpoint
- Player station creation

---

## Explicit Non-Features (Yet)

These are **intentionally not implemented yet**:
- No mining logic
- No trade system
- No build queue
- No ships or fleets
- No combat or damage
- No AI factions

These will be added incrementally.

---

## Design Philosophy

- **Data first**: define systems before mechanics
- **Events over ticks**: outcomes happen at discrete times
- **Deterministic simulation**: predictable, debuggable, persistent
- **Small steps**: v1 focuses on correctness and structure, not content scale

---

## Running Locally

### Requirements
- Python 3.11+
- Virtual environment recommended

### Install & Run
bash
uvicorn server.app:app --reload

Server will start at:

http:://127.0.0.1:8000

---

## Project Status

### 🚧 Active development (v1)

Current focus:

Module definitions

Build costs & build queue

Event-based construction

Mining & logistics (later)

---

## License

TBD