"""Application logic: business rules R2, R5-R8. This module has no HTTP or FastAPI dependencies."""
from datetime import date, datetime, timezone
from math import floor
from .advice import advise, ratio
from .storage import JsonStore

DEFAULT_DOSE_G = 18

class CoffeeError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

class CoffeeService:
    def __init__(self, store: JsonStore):
        self.store = store

    @staticmethod
    def find(rows: list[dict], record_id, label: str) -> dict:
        for row in rows:
            if row["id"] == record_id:
                return row
        raise CoffeeError("not_found", f"{label} {record_id} was not found.")

    @staticmethod
    def coffee_fields(data: dict, fields: dict) -> dict:
        """R2 and product prefill: check the input against stored data and complete it."""
        if fields["roast_date"] > date.today():
            raise CoffeeError("invalid_input", "roast_date cannot be in the future.")
        if fields["product_id"] is not None:
            product = next((p for p in data["products"] if p["id"] == fields["product_id"]), None)
            if product is None:
                raise CoffeeError("invalid_input", f"Product '{fields['product_id']}' does not exist.")
            for key in ("name", "origin", "roast_level", "bag_size_g"):
                if fields[key] is None:
                    fields[key] = product[key]
        elif fields["name"] is None or fields["bag_size_g"] is None:
            raise CoffeeError("invalid_input", "name and bag_size_g are required without a product_id.")
        return {**fields, "roast_date": fields["roast_date"].isoformat()}

    @staticmethod
    def coffee_view(data: dict, coffee: dict) -> dict:
        """R7: add the derived stock fields to a stored coffee."""
        brews = [b for b in data["brews"] if b["coffee_id"] == coffee["id"]]
        last_dose = max(brews, key=lambda b: b["id"])["dose_g"] if brews else DEFAULT_DOSE_G
        low_stock = coffee["grams_left"] < 3 * last_dose
        product = next((p for p in data["products"] if p["id"] == coffee["product_id"]), None)
        return {
            **coffee,
            "low_stock": low_stock,
            "brews_left": floor(coffee["grams_left"] / last_dose),
            "days_off_roast": (date.today() - date.fromisoformat(coffee["roast_date"])).days,
            "reorder_url": product["shop_url"] if low_stock and product else None,
        }

    @staticmethod
    def brew_view(brew: dict) -> dict:
        """R3-R4: ratio and advice are computed on every read, never stored."""
        return {**brew, "ratio": ratio(brew), "advice": advise(brew)}

    def list_products(self) -> list[dict]:
        with self.store.lock:
            return self.store.load()["products"]

    def list_coffees(self) -> list[dict]:
        with self.store.lock:
            data = self.store.load()
            return [self.coffee_view(data, c) for c in data["coffees"]]

    def get_coffee(self, coffee_id: int) -> dict:
        with self.store.lock:
            data = self.store.load()
            return self.coffee_view(data, self.find(data["coffees"], coffee_id, "Coffee"))

    def create_coffee(self, fields: dict) -> dict:
        with self.store.lock:
            data = self.store.load()
            fields = self.coffee_fields(data, fields)
            coffee = {"id": data["next_coffee_id"], **fields, "grams_left": fields["bag_size_g"]}
            data["next_coffee_id"] += 1
            data["coffees"].append(coffee)
            self.store.save(data)
            return self.coffee_view(data, coffee)

    def replace_coffee(self, coffee_id: int, fields: dict) -> dict:
        with self.store.lock:
            data = self.store.load()
            coffee = self.find(data["coffees"], coffee_id, "Coffee")
            coffee.update(self.coffee_fields(data, fields))
            self.store.save(data)
            return self.coffee_view(data, coffee)

    def delete_coffee(self, coffee_id: int) -> None:
        """R8: a coffee takes its brews and recipes with it."""
        with self.store.lock:
            data = self.store.load()
            coffee = self.find(data["coffees"], coffee_id, "Coffee")
            data["coffees"].remove(coffee)
            data["brews"] = [b for b in data["brews"] if b["coffee_id"] != coffee_id]
            data["recipes"] = [r for r in data["recipes"] if r["coffee_id"] != coffee_id]
            self.store.save(data)

    def list_brews(self, coffee_id: int, method: str | None) -> list[dict]:
        with self.store.lock:
            data = self.store.load()
            self.find(data["coffees"], coffee_id, "Coffee")
            brews = [b for b in data["brews"]
                     if b["coffee_id"] == coffee_id and (method is None or b["method"] == method)]
            return [self.brew_view(b) for b in sorted(brews, key=lambda b: b["id"], reverse=True)]

    def log_brew(self, coffee_id: int, fields: dict) -> dict:
        """R6: a brew uses its dose from stock; if there is not enough, nothing is saved."""
        with self.store.lock:
            data = self.store.load()
            coffee = self.find(data["coffees"], coffee_id, "Coffee")
            if fields["dose_g"] > coffee["grams_left"]:
                raise CoffeeError("conflict", f"Only {coffee['grams_left']:g} g left. Add a new bag first.")
            coffee["grams_left"] = round(coffee["grams_left"] - fields["dose_g"], 1)
            brew = {"id": data["next_brew_id"], "coffee_id": coffee_id, **fields,
                    "grams_left": coffee["grams_left"],
                    "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}
            data["next_brew_id"] += 1
            data["brews"].append(brew)
            self.store.save(data)
            return self.brew_view(brew)

    def delete_brew(self, brew_id: int) -> None:
        """R8: the dose goes back to stock and a recipe built on this brew is removed."""
        with self.store.lock:
            data = self.store.load()
            brew = self.find(data["brews"], brew_id, "Brew")
            coffee = self.find(data["coffees"], brew["coffee_id"], "Coffee")
            coffee["grams_left"] = round(coffee["grams_left"] + brew["dose_g"], 1)
            data["brews"].remove(brew)
            data["recipes"] = [r for r in data["recipes"] if r["brew_id"] != brew_id]
            self.store.save(data)

    def recipe_view(self, data: dict, recipe: dict) -> dict:
        return {**recipe, "brew": self.brew_view(self.find(data["brews"], recipe["brew_id"], "Brew"))}

    def list_recipes(self, coffee_id: int) -> list[dict]:
        with self.store.lock:
            data = self.store.load()
            self.find(data["coffees"], coffee_id, "Coffee")
            return [self.recipe_view(data, r) for r in data["recipes"] if r["coffee_id"] == coffee_id]

    def save_recipe(self, coffee_id: int, method: str, brew_id: int) -> dict:
        """R5: only a balanced brew of this coffee and method; replaces the recipe for that method."""
        with self.store.lock:
            data = self.store.load()
            self.find(data["coffees"], coffee_id, "Coffee")
            brew = self.find(data["brews"], brew_id, "Brew")
            if brew["coffee_id"] != coffee_id or brew["method"] != method:
                raise CoffeeError("invalid_input", f"Brew {brew_id} is not a {method} brew of coffee {coffee_id}.")
            if brew["taste"] != "balanced":
                raise CoffeeError("invalid_input", "Only a balanced brew can become the recipe.")
            data["recipes"] = [r for r in data["recipes"]
                               if not (r["coffee_id"] == coffee_id and r["method"] == method)]
            recipe = {"coffee_id": coffee_id, "method": method, "brew_id": brew_id}
            data["recipes"].append(recipe)
            self.store.save(data)
            return self.recipe_view(data, recipe)
