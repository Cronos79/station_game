import json
import time

from server.game.modules import MODULES

class Station:
    def __init__(self, name: str):
        self.name = name

        self.resources = {"credits": 100.0, "power": 50.0}

        # These are your "starting" rates before modules.
        self.base_rates = {"credits": 1.0, "power": -0.5}

        # Installed module ids
        self.modules: list[str] = []

        self.build_queue: list[dict] = []

        # Current computed rates (base + modules)
        self.rates = dict(self.base_rates)
        self.recompute_rates()

    def recompute_rates(self) -> None:
        self.rates = dict(self.base_rates)
        for module_id in self.modules:
            module = MODULES[module_id]
            for key, delta in module["rates"].items():
                self.rates[key] = self.rates.get(key, 0.0) + float(delta)

    def can_afford(self, cost: dict) -> bool:
        for key, amount in cost.items():
            if self.resources.get(key, 0.0) < float(amount):
                return False
        return True

    def pay_cost(self, cost: dict) -> None:
        for key, amount in cost.items():
            self.resources[key] = self.resources.get(key, 0.0) - float(amount)

    def install_module(self, module_id: str):
        self.modules.append(module_id)

        for res, delta in MODULES[module_id]["rates"].items():
            self.rates[res] = self.rates.get(res, 0) + delta

    def build(self, module_id: str) -> tuple[bool, str]:
        module = MODULES.get(module_id)
        if not module:
            return False, "unknown_module"

        # max per station
        count = self.modules.count(module_id)
        if count >= module.get("max_per_station", 999):
            return False, "max_reached"

        # check cost
        for res, cost in module["cost"].items():
            if self.resources.get(res, 0) < cost:
                return False, "not_enough_resources"

        # pay immediately
        for res, cost in module["cost"].items():
            self.resources[res] -= cost

        now = time.time()
        self.build_queue.append({
            "module_id": module_id,
            "started_at": now,
            "finish_at": now + module["build_time"],
        })

        return True, "queued"

    def tick(self, dt: float) -> None:
        for k, rate in self.rates.items():
            self.resources[k] = self.resources.get(k, 0.0) + rate * dt

        now = time.time()
        completed = []

        for job in self.build_queue:
            if now >= job["finish_at"]:
                completed.append(job)

        for job in completed:
            self.build_queue.remove(job)
            self.install_module(job["module_id"])

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "resources": self.resources,
            "rates": self.rates,
            "modules": list(self.modules),
            "build_queue": self.build_queue,
        }
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "resources": self.resources,
            "base_rates": getattr(self, "base_rates", None),
            "rates": self.rates,
            "modules": getattr(self, "modules", []),
        }
    
    @staticmethod
    def from_dict(data: dict) -> "Station":
        s = Station(data["name"])
        s.resources = data.get("resources", {"credits": 100.0, "power": 50.0})
        s.base_rates = data.get("base_rates", {"credits": 1.0, "power": -0.5})
        s.modules = data.get("modules", [])
        s.recompute_rates()
        return s
