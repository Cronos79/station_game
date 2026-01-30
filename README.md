# Station Game

A browser-based sci-fi station management game.

## Tech Stack
- Python + FastAPI (game server)
- SQLite (persistence)
- HTML + JavaScript (client)
- Server-authoritative simulation

## Current Features
- Server-side world ticking
- Station resources & rates
- Module building
- SQLite save/load

## Running Locally
```bash
uvicorn server.app:app --reload
