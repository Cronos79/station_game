# server/sim/modules.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal

from server.sim.materials import is_valid_material


ModuleCategory = Literal["infrastructure", "industry", "logistics", "defense", "info"]


@dataclass(frozen=True)
class ModuleDef:
    """
    Pure data definition for a station module.

    Notes:
    - power_delta: positive means generates power, negative means consumes.
    - crew_required: how many crew must be available for it to operate.
    - slot_cost: how many station module slots it occupies (v1 always 1, but keep the field).
    - cost: material requirements paid up-front when queued/built.
    - build_time: seconds of sim_time until complete.
    """
    id: str
    name: str
    category: ModuleCategory

    power_delta: float
    crew_required: int
    slot_cost: int

    build_time: float
    cost: Dict[str, float]

    # "effects" are data-only placeholders for now (no code uses them yet)
    effects: Dict[str, float]


# ----------------------------
# v1 Module List (Data Only)
# ----------------------------

MODULES: Dict[str, ModuleDef] = {
    # --- Infrastructure ---
    "solar_array_1": ModuleDef(
        id="solar_array_1",
        name="Solar Array I",
        category="infrastructure",
        power_delta=+4.0,
        crew_required=0,
        slot_cost=1,
        build_time=60.0,
        cost={
            "iron_bar": 4.0,
            "copper_bar": 2.0,
            "glass_pane": 2.0,
        },
        effects={
            "power_cap": +4.0,
        },
    ),

    "habitat_pod_1": ModuleDef(
        id="habitat_pod_1",
        name="Habitat Pod I",
        category="infrastructure",
        power_delta=-1.0,
        crew_required=0,
        slot_cost=1,
        build_time=90.0,
        cost={
            "iron_bar": 4.0,
            "glass_pane": 2.0,
            "alloy_plate": 1.0,
        },
        effects={
            "crew_cap": +5.0,
        },
    ),

    "storage_bay_1": ModuleDef(
        id="storage_bay_1",
        name="Storage Bay I",
        category="infrastructure",
        power_delta=-1.0,
        crew_required=0,
        slot_cost=1,
        build_time=90.0,
        cost={
            "iron_bar": 6.0,
            "alloy_plate": 2.0,
        },
        effects={
            "cargo_cap": +50.0,
        },
    ),

    # --- Logistics / Info ---
    "docking_clamp_1": ModuleDef(
        id="docking_clamp_1",
        name="Docking Clamp I",
        category="logistics",
        power_delta=-1.0,
        crew_required=1,
        slot_cost=1,
        build_time=120.0,
        cost={
            "iron_bar": 4.0,
            "alloy_plate": 2.0,
            "computer_chip": 1.0,
        },
        effects={
            "dock_cap": +1.0,
        },
    ),

    "scanner_array_1": ModuleDef(
        id="scanner_array_1",
        name="Scanner Array I",
        category="info",
        power_delta=-2.0,
        crew_required=1,
        slot_cost=1,
        build_time=120.0,
        cost={
            "iron_bar": 2.0,
            "copper_bar": 2.0,
            "computer_chip": 2.0,
            "computer_screen": 1.0,
        },
        effects={
            "scan_level": +1.0,
        },
    ),

    # --- Industry ---
    "basic_refinery_1": ModuleDef(
        id="basic_refinery_1",
        name="Basic Refinery I",
        category="industry",
        power_delta=-3.0,
        crew_required=2,
        slot_cost=1,
        build_time=180.0,
        cost={
            "iron_bar": 6.0,
            "copper_bar": 2.0,
            "alloy_plate": 2.0,
            "computer_chip": 1.0,
        },
        effects={
            "refine_level": +1.0,
        },
    ),

    "workshop_1": ModuleDef(
        id="workshop_1",
        name="Workshop I",
        category="industry",
        power_delta=-3.0,
        crew_required=2,
        slot_cost=1,
        build_time=180.0,
        cost={
            "iron_bar": 4.0,
            "copper_bar": 2.0,
            "alloy_plate": 2.0,
            "computer_chip": 2.0,
            "computer_screen": 1.0,
        },
        effects={
            "manufacture_level": +1.0,
        },
    ),

    # --- Defense ---
    "shield_emitter_1": ModuleDef(
        id="shield_emitter_1",
        name="Shield Emitter I",
        category="defense",
        power_delta=-3.0,
        crew_required=1,
        slot_cost=1,
        build_time=180.0,
        cost={
            "alloy_plate": 4.0,
            "copper_bar": 2.0,
            "computer_chip": 2.0,
        },
        effects={
            "defense": +10.0,
        },
    ),

    "point_defense_1": ModuleDef(
        id="point_defense_1",
        name="Point Defense I",
        category="defense",
        power_delta=-2.0,
        crew_required=1,
        slot_cost=1,
        build_time=150.0,
        cost={
            "iron_bar": 4.0,
            "alloy_plate": 2.0,
            "computer_chip": 1.0,
        },
        effects={
            "defense": +6.0,
        },
    ),
}


def get_module(module_id: str) -> ModuleDef | None:
    return MODULES.get(module_id)


# ----------------------------
# Validation (fail loudly)
# ----------------------------

def _validate_modules() -> None:
    ids = set()
    for mid, m in MODULES.items():
        if mid != m.id:
            raise ValueError(f"Module key '{mid}' must match ModuleDef.id '{m.id}'")
        if m.id in ids:
            raise ValueError(f"Duplicate module id: {m.id}")
        ids.add(m.id)

        if m.crew_required < 0:
            raise ValueError(f"{m.id}: crew_required must be >= 0")
        if m.slot_cost <= 0:
            raise ValueError(f"{m.id}: slot_cost must be >= 1")
        if m.build_time <= 0:
            raise ValueError(f"{m.id}: build_time must be > 0")

        for mat_id, amt in m.cost.items():
            if not is_valid_material(mat_id):
                raise ValueError(f"{m.id}: unknown material id in cost: {mat_id}")
            if float(amt) <= 0:
                raise ValueError(f"{m.id}: cost {mat_id} must be > 0")


_validate_modules()
