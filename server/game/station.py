import json

from server.game.modules import MODULES

class Station:
    def __init__(self, name: str):
        self.name = name

        self.resources = {"credits": 100.0, "power": 50.0}

        # These are your "starting" rates before modules.
        self.base_rates = {"credits": 1.0, "power": -0.5}

        # Installed module ids
        self.modules: list[str] = []

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

    def build(self, module_id: str) -> tuple[bool, str]:
        if module_id not in MODULES:
            return False, "unknown_module"

        module = MODULES[module_id]

        # Optional uniqueness rule
        if module.get("unique", False) and module_id in self.modules:
            return False, "already_built"

        cost = module.get("cost", {})
        if not self.can_afford(cost):
            return False, "insufficient_resources"

        self.pay_cost(cost)
        self.modules.append(module_id)
        self.recompute_rates()
        return True, "built"

    def tick(self, dt: float) -> None:
        for k, rate in self.rates.items():
            self.resources[k] = self.resources.get(k, 0.0) + rate * dt

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "resources": self.resources,
            "rates": self.rates,
            "modules": list(self.modules),
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
