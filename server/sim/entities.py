# server/sim/entities.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class Station:
    """
    A Station is an entity in the universe.
    We keep it tiny for v1: identity + location + owner.
    """
    id: int
    name: str
    owner_user_id: Optional[int]  # None means AI/NPC-owned later
    system: str
    x: float
    y: float
    credits: float
    # materials stored as a dict (material_id -> amount)
    inventory: Dict[str, float]
    modules: list[str]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-friendly dict. (dataclasses.asdict does this for us.)
        """
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Station":
        """
        Build a Station from a dict loaded from JSON.
        """
        inv = d.get("inventory")
        if not isinstance(inv, dict):
            inv = {}
        # Make sure values are floats (JSON might store ints)
        inv2 = {str(k): float(v) for k, v in inv.items()}

        mods = d.get("modules")
        if not isinstance(mods, list):
            mods = []
        mods2 = [str(x) for x in mods]

        return Station(
            id=int(d["id"]),
            name=str(d["name"]),
            owner_user_id=int(d["owner_user_id"]) if d.get("owner_user_id") is not None else None,
            system=str(d["system"]),
            x=float(d["x"]),
            y=float(d["y"]),
            credits=float(d.get("credits", 0.0)),
            inventory=inv2,
            modules=mods2,
        )
