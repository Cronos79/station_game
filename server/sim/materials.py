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
    # ores
    "ice": MaterialDef(id="ice", name="Ice", category="ore"),
    "iron_ore": MaterialDef(id="iron_ore", name="Iron Ore", category="ore"),
    "nickel_ore": MaterialDef(id="nickel_ore", name="Nickel Ore", category="ore"),
    "silicon_ore": MaterialDef(id="silicon_ore", name="Silicon Ore", category="ore"),
    "cobalt_ore": MaterialDef(id="cobalt_ore", name="Cobalt Ore", category="ore"),
    "silver_ore": MaterialDef(id="silver_ore", name="Silver Ore", category="ore"),
    "gold_ore": MaterialDef(id="gold_ore", name="Gold Ore", category="ore"),
    "copper_ore": MaterialDef(id="copper_ore", name="Copper Ore", category="ore"),
    "uranium_ore": MaterialDef(id="uranium_ore", name="Uranium Ore", category="ore"),
    "titanium_ore": MaterialDef(id="titanium_ore", name="Titanium Ore", category="ore"),

    # gases
    "hydrogen_gas": MaterialDef(id="hydrogen_gas", name="Hydrogen Gas", category="gas"),

    # refined
    "water": MaterialDef(id="water", name="Water", category="refined"),
    "iron_bar": MaterialDef(id="iron_bar", name="Iron Bar", category="refined"),
    "nickel_bar": MaterialDef(id="nickel_bar", name="Nickel Bar", category="refined"),
    "silicon_bar": MaterialDef(id="silicon_bar", name="Silicon Bar", category="refined"),
    "cobalt_bar": MaterialDef(id="cobalt_bar", name="Cobalt Bar", category="refined"),
    "silver_bar": MaterialDef(id="silver_bar", name="Silver Bar", category="refined"),
    "gold_bar": MaterialDef(id="gold_bar", name="Gold Bar", category="refined"),
    "copper_bar": MaterialDef(id="copper_bar", name="Copper Bar", category="refined"),
    "titanium_bar": MaterialDef(id="titanium_bar", name="Titanium Bar", category="refined"),    
    "glass_pane": MaterialDef(id="glass_pane", name="Glass Pane", category="refined"),
    "alloy_plate": MaterialDef(id="alloy_plate", name="Alloy Plate", category="refined"),

    "uranium": MaterialDef(id="uranium", name="Uranium", category="refined"),
    "hydrogen": MaterialDef(id="hydrogen", name="Hydrogen", category="refined"),

    # parts
    "copper_wire": MaterialDef(id="copper_wire", name="Copper Wire", category="parts"),
    "circuit_board": MaterialDef(id="circuit_board", name="Circuit Board", category="parts"),
    "computer_chip": MaterialDef(id="computer_chip", name="Computer Chip", category="parts"),
    "computer_screen": MaterialDef(id="computer_screen", name="Computer Screen", category="parts"), 
}


def is_valid_material(material_id: str) -> bool:
    return material_id in MATERIALS

def get_material(material_id: str) -> MaterialDef | None:
    return MATERIALS.get(material_id)
