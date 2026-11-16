"""Application logic: the business rules of the README, independent of HTTP.

Every method opens its own database session. Changes run inside
`with self.sessions.begin()`: SQLAlchemy commits when the block ends normally
and rolls everything back if a rule raises an exception, so a refused brew can
never leave half-changed stock behind.

The API layer turns the exceptions below into status codes:
NotFound -> 404, RuleViolation -> 422, Conflict -> 409.
"""

from collections.abc import Callable
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from .advice import espresso_advice, phin_advice
from .models import Brew, Coffee, Product, Recipe

DEFAULT_DOSE_G = 18  # used for "brews left" before the first brew is logged
LOW_STOCK_BREWS = 3  # R7: low stock when fewer than 3 brews are left


class NotFound(Exception):
    pass


class RuleViolation(Exception):
    """Valid input that breaks a business rule (e.g. a roast date in the future)."""


class Conflict(Exception):
    """The request is not possible in the current state (e.g. not enough coffee left)."""


def grams(value: float) -> str:
    return f"{value:g} g"


class DialInService:
    def __init__(self, sessions: sessionmaker, today: Callable[[], date] = date.today):
        self.sessions = sessions
        self.today = today

    # ---- products ----------------------------------------------------------------

    def list_products(self) -> list[Product]:
        with self.sessions() as s:
            return list(s.scalars(select(Product).order_by(Product.name)))

    # ---- coffees -------------------------------------------------------------------

    def list_coffees(self) -> list[dict]:
        with self.sessions() as s:
            coffees = s.scalars(
                select(Coffee).options(selectinload(Coffee.brews), selectinload(Coffee.product)).order_by(Coffee.id)
            )
            return [self._coffee_out(c) for c in coffees]

    def get_coffee(self, coffee_id: int) -> dict:
        with self.sessions() as s:
            return self._coffee_out(self._coffee(s, coffee_id))

    def create_coffee(self, fields: dict) -> dict:
        self._check_roast_date(fields["roast_date"])
        with self.sessions.begin() as s:
            if fields.get("product_id"):
                product = s.get(Product, fields["product_id"])
                if product is None:
                    raise RuleViolation(f"Unknown PHIN coffee: {fields['product_id']}.")
                # Prefill: anything the user left empty comes from the PHIN product.
                for key in ("name", "origin", "roast_level", "bag_size_g"):
                    if fields.get(key) is None:
                        fields[key] = getattr(product, key)
            missing = [k for k in ("name", "origin", "roast_level", "bag_size_g") if fields.get(k) is None]
            if missing:
                raise RuleViolation("Choose a PHIN coffee or fill in: " + ", ".join(missing) + ".")
            if fields.get("grams_left") is None:
                fields["grams_left"] = fields["bag_size_g"]
            coffee = Coffee(**fields)
            s.add(coffee)
            s.flush()  # sends the INSERT now, so coffee.id is known
            return self._coffee_out(coffee)

    def update_coffee(self, coffee_id: int, fields: dict) -> dict:
        self._check_roast_date(fields["roast_date"])
        with self.sessions.begin() as s:
            coffee = self._coffee(s, coffee_id)
            for key, value in fields.items():
                setattr(coffee, key, value)
            return self._coffee_out(coffee)

    def delete_coffee(self, coffee_id: int) -> None:
        """R8: the database deletes the coffee's brews and recipes too (ON DELETE CASCADE)."""
        with self.sessions.begin() as s:
            s.delete(self._coffee(s, coffee_id))

    # ---- brews -----------------------------------------------------------------------

    def list_brews(self, coffee_id: int, method: str | None = None) -> list[dict]:
        with self.sessions() as s:
            coffee = self._coffee(s, coffee_id)
            return [self._brew_out(b, coffee) for b in coffee.brews if method is None or b.method == method]

    def get_brew(self, brew_id: int) -> dict:
        with self.sessions() as s:
            brew = self._brew(s, brew_id)
            return self._brew_out(brew, brew.coffee)

    def add_brew(self, coffee_id: int, fields: dict) -> dict:
        with self.sessions.begin() as s:
            coffee = self._coffee(s, coffee_id)
            # R6: a brew uses its dose from the bag; refuse if there is not enough left.
            if fields["dose_g"] > coffee.grams_left:
                raise Conflict(f"Only {grams(coffee.grams_left)} left. Add a new bag first.")
            coffee.grams_left = round(coffee.grams_left - fields["dose_g"], 1)
            brew = Brew(coffee=coffee, created_at=datetime.now().astimezone().replace(microsecond=0), **fields)
            s.add(brew)
            s.flush()
            return self._brew_out(brew, coffee)

    def delete_brew(self, brew_id: int) -> None:
        """R8: the dose goes back to stock; a recipe pointing at this brew is removed by the database."""
        with self.sessions.begin() as s:
            brew = self._brew(s, brew_id)
            brew.coffee.grams_left = round(brew.coffee.grams_left + brew.dose_g, 1)
            s.delete(brew)

    # ---- recipes ---------------------------------------------------------------------

    def list_recipes(self, coffee_id: int) -> list[dict]:
        with self.sessions() as s:
            coffee = self._coffee(s, coffee_id)
            return [self._recipe_out(r, coffee) for r in sorted(coffee.recipes, key=lambda r: r.method)]

    def save_recipe(self, coffee_id: int, method: str, brew_id: int) -> dict:
        """R5: only a balanced brew of the same coffee and method; replaces the old recipe."""
        with self.sessions.begin() as s:
            coffee = self._coffee(s, coffee_id)
            brew = self._brew(s, brew_id)
            if brew.coffee_id != coffee_id:
                raise RuleViolation(f"Brew {brew_id} belongs to a different coffee.")
            if brew.method != method:
                raise RuleViolation(f"Brew {brew_id} is a {brew.method} brew, not {method}.")
            if brew.taste != "balanced":
                raise RuleViolation("Only a brew that tasted balanced can become the recipe.")
            recipe = s.scalar(select(Recipe).where(Recipe.coffee_id == coffee_id, Recipe.method == method))
            if recipe is None:
                recipe = Recipe(coffee=coffee, method=method, brew=brew)
                s.add(recipe)
            else:
                recipe.brew = brew
            s.flush()
            return self._recipe_out(recipe, coffee)

    # ---- helpers -----------------------------------------------------------------------

    def _check_roast_date(self, roast_date: date) -> None:
        if roast_date > self.today():
            raise RuleViolation("The roast date cannot be in the future.")

    @staticmethod
    def _coffee(s: Session, coffee_id: int) -> Coffee:
        coffee = s.get(Coffee, coffee_id)
        if coffee is None:
            raise NotFound(f"Coffee {coffee_id} was not found.")
        return coffee

    @staticmethod
    def _brew(s: Session, brew_id: int) -> Brew:
        brew = s.get(Brew, brew_id)
        if brew is None:
            raise NotFound(f"Brew {brew_id} was not found.")
        return brew

    def _coffee_out(self, c: Coffee) -> dict:
        """Stored columns plus the derived values the frontend needs (R7)."""
        last_dose = c.brews[-1].dose_g if c.brews else DEFAULT_DOSE_G
        return {
            "id": c.id,
            "product_id": c.product_id,
            "name": c.name,
            "origin": c.origin,
            "roast_level": c.roast_level,
            "roast_date": c.roast_date,
            "bag_size_g": c.bag_size_g,
            "grams_left": c.grams_left,
            "days_off_roast": (self.today() - c.roast_date).days,
            "brews_left": int(c.grams_left // last_dose),
            "low_stock": c.grams_left < LOW_STOCK_BREWS * last_dose,
            "shop_url": c.product.shop_url if c.product else None,
        }

    @staticmethod
    def _brew_out(b: Brew, coffee: Coffee) -> dict:
        if b.method == "phin":
            advice = phin_advice(b.dose_g, b.water_ml, b.water_temp_c, b.drip_time_s, b.taste)
        else:
            advice = espresso_advice(b.dose_g, b.yield_g, b.shot_time_s, b.taste)
        ratio = advice.pop("ratio")
        fields = ("id", "coffee_id", "method", "dose_g", "grind_setting", "taste", "rating", "notes", "created_at",
                  "water_ml", "water_temp_c", "drip_time_s", "yield_g", "shot_time_s")
        return {**{f: getattr(b, f) for f in fields}, "ratio": ratio, "advice": advice, "grams_left": coffee.grams_left}

    def _recipe_out(self, r: Recipe, coffee: Coffee) -> dict:
        return {"coffee_id": r.coffee_id, "method": r.method, "brew": self._brew_out(r.brew, coffee)}
