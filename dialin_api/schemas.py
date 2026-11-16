"""API data shapes (Pydantic). They are the contract with the frontend.

Input models check rule R1 (types, ranges, required fields). FastAPI rejects
invalid input with 422 before any of our own code runs. Output models describe
what the API returns; FastAPI also uses all of them to generate the OpenAPI docs.
"""

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

RecordId = Annotated[int, Field(gt=0)]


class RoastLevel(str, Enum):
    light = "light"
    medium = "medium"
    dark = "dark"


class Taste(str, Enum):
    sour = "sour"
    balanced = "balanced"
    bitter = "bitter"


class Method(str, Enum):
    phin = "phin"
    espresso = "espresso"


# ---- products ------------------------------------------------------------------


class Product(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    origin: str
    roast_level: RoastLevel
    bag_size_g: int
    shop_url: str


# ---- coffees -------------------------------------------------------------------


class CoffeeCreate(BaseModel):
    """Add a coffee. With product_id, missing fields are filled from the PHIN product."""

    model_config = ConfigDict(use_enum_values=True)  # store "light", not RoastLevel.light

    product_id: str | None = Field(default=None, examples=["saigon-drip"])
    name: str | None = Field(default=None, min_length=1, max_length=80)
    origin: str | None = Field(default=None, min_length=1, max_length=80)
    roast_level: RoastLevel | None = None
    roast_date: date
    bag_size_g: int | None = Field(default=None, ge=50, le=5000)
    grams_left: float | None = Field(default=None, ge=0, le=5000, description="Defaults to the bag size.")


class CoffeeUpdate(BaseModel):
    """Replace a coffee's details, e.g. after opening a new bag."""

    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(min_length=1, max_length=80)
    origin: str = Field(min_length=1, max_length=80)
    roast_level: RoastLevel
    roast_date: date
    bag_size_g: int = Field(ge=50, le=5000)
    grams_left: float = Field(ge=0, le=5000)


class Coffee(BaseModel):
    id: int
    product_id: str | None
    name: str
    origin: str
    roast_level: RoastLevel
    roast_date: date
    bag_size_g: int
    grams_left: float
    days_off_roast: int
    brews_left: int
    low_stock: bool
    shop_url: str | None


# ---- brews -----------------------------------------------------------------------


class BrewBase(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    grind_setting: str = Field(min_length=1, max_length=20, examples=["7"])
    taste: Taste
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str = Field(default="", max_length=500)


class PhinBrewCreate(BrewBase):
    method: Literal["phin"]
    dose_g: float = Field(ge=10, le=25, examples=[18])
    water_ml: float = Field(ge=60, le=200, examples=[140])
    water_temp_c: float = Field(ge=85, le=100, examples=[94])
    drip_time_s: int = Field(ge=60, le=600, description="Main pour to last drop, seconds.", examples=[270])


class EspressoBrewCreate(BrewBase):
    method: Literal["espresso"]
    dose_g: float = Field(ge=5, le=30, examples=[18])
    yield_g: float = Field(ge=5, le=120, examples=[36])
    shot_time_s: int = Field(ge=5, le=120, examples=[28])


# "method" decides which of the two shapes (and which ranges) apply.
BrewCreate = Annotated[PhinBrewCreate | EspressoBrewCreate, Field(discriminator="method")]


class Advice(BaseModel):
    action: str = Field(description="One change for the next brew, e.g. grind_finer, or keep.")
    message: str
    time_status: Literal["fast", "ok", "slow"]
    ratio_status: Literal["low", "ok", "high"]


class Brew(BaseModel):
    id: int
    coffee_id: int
    method: Method
    dose_g: float
    grind_setting: str
    taste: Taste
    rating: int | None
    notes: str
    created_at: datetime
    water_ml: float | None
    water_temp_c: float | None
    drip_time_s: int | None
    yield_g: float | None
    shot_time_s: int | None
    ratio: float = Field(description="Phin: water ÷ coffee. Espresso: yield ÷ dose.")
    advice: Advice
    grams_left: float = Field(description="Current stock of the coffee, in grams.")


# ---- recipes ---------------------------------------------------------------------


class RecipeSave(BaseModel):
    brew_id: RecordId


class Recipe(BaseModel):
    coffee_id: int
    method: Method
    brew: Brew


class ErrorMessage(BaseModel):
    detail: str
