# server/sim/materials.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class MaterialDef:
    """
    Definition of a material type (not an amount).
    This is 'what is iron_ore?' not 'how much iron_ore do I have?'.
    """
    id: str
    name: str
    category: str  # e.g. "ore", "refined", "parts"


# Your game's "canonical" material list for v1.
# Single source of truth: everywhere else should refer to these IDs.
MATERIALS: Dict[str, MaterialDef] = {
    "iron_ore": MaterialDef(id="iron_ore", name="Iron Ore", category="ore"),
    "copper_ore": MaterialDef(id="copper_ore", name="Copper Ore", category="ore"),

    # examples for later
    "alloy_plate": MaterialDef(id="alloy_plate", name="Alloy Plate", category="refined"),
    "parts_basic": MaterialDef(id="parts_basic", name="Basic Parts", category="parts"),
}


def is_valid_material(material_id: str) -> bool:
    return material_id in MATERIALS
