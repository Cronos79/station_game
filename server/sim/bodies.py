# server/sim/bodies.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class Body:
    """
    A celestial body or resource site in a system.
    materials = relative availability weights (not amounts).
    Example: {"iron_ore": 0.7, "copper_ore": 0.2}
    """
    id: int
    system: str
    name: str
    type: str  # "planet", "moon", "asteroid_belt"
    x: float
    y: float
    materials: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
