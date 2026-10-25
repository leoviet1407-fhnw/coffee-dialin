"""Input/output shapes: Pydantic schemas and input ranges (R1). Rules that need stored data live in the service."""
from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

Method = Literal["phin", "espresso"]
Taste = Literal["sour", "balanced", "bitter"]

class InputModel(BaseModel):
    # Clients cannot send server-owned fields such as id, grams_left or ratio.
    model_config = ConfigDict(extra="forbid")

class Error(BaseModel):
    code: str
    message: str

class Product(BaseModel):
    id: str
    name: str
    origin: str
    roast_level: str
    bag_size_g: int
    shop_url: str

class CoffeeInput(InputModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"product_id": "saigon-drip", "roast_date": "2026-10-10"}]})
    product_id: str | None = Field(None, description="PHIN product; fills missing name, origin, roast level and bag size.")
    name: str | None = Field(None, min_length=1)
    origin: str | None = None
    roast_level: str | None = None
    roast_date: date
    bag_size_g: int | None = Field(None, ge=50, le=5000)

class CoffeeUpdate(CoffeeInput):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"product_id": "saigon-drip", "roast_date": "2026-10-20", "bag_size_g": 250, "grams_left": 250}]})
    grams_left: float = Field(ge=0)

class Coffee(BaseModel):
    id: int
    product_id: str | None
    name: str
    origin: str | None
    roast_level: str | None
    roast_date: date
    bag_size_g: int
    grams_left: float
    low_stock: bool = Field(description="True when fewer than 3 brews (at the last dose) are left.")
    brews_left: int | None
    days_off_roast: int
    reorder_url: str | None = Field(description="Shop link, only for low-stock PHIN coffees.")

class BrewFields(BaseModel):
    grind_setting: str | None = Field(None, max_length=20, description="Free text, grinder settings differ.")
    taste: Taste
    rating: int | None = Field(None, ge=1, le=5)
    notes: str | None = Field(None, max_length=500)

class PhinFields(BrewFields):
    method: Literal["phin"]
    dose_g: float = Field(ge=10, le=25)
    water_ml: int = Field(ge=60, le=200)
    water_temp_c: int = Field(ge=85, le=100)
    drip_time_s: int = Field(ge=60, le=600, description="From the main pour to the last drop.")

class EspressoFields(BrewFields):
    method: Literal["espresso"]
    dose_g: float = Field(ge=5, le=30)
    yield_g: float = Field(ge=5, le=120)
    shot_time_s: int = Field(ge=5, le=120)

class PhinBrewInput(PhinFields, InputModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [
        {"method": "phin", "dose_g": 18, "water_ml": 140, "water_temp_c": 94, "drip_time_s": 190,
         "grind_setting": "7", "taste": "sour"}]})

class EspressoBrewInput(EspressoFields, InputModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [
        {"method": "espresso", "dose_g": 18, "yield_g": 36, "shot_time_s": 27, "grind_setting": "2.5",
         "taste": "balanced", "rating": 5}]})

BrewInput = Annotated[PhinBrewInput | EspressoBrewInput, Field(discriminator="method")]

class Advice(BaseModel):
    action: Literal["save_recipe", "grind_finer", "grind_coarser", "hotter_water", "cooler_water",
                    "longer_yield", "shorter_yield"]
    time_status: Literal["fast", "ok", "slow"]
    ratio_status: Literal["low", "ok", "high"]
    message: str

class BrewResult(BaseModel):
    id: int
    coffee_id: int
    created_at: datetime
    ratio: float = Field(description="Water ÷ dose (Phin) or yield ÷ dose (espresso), one decimal.")
    grams_left: float = Field(description="Coffee left right after this brew.")
    advice: Advice

class PhinBrew(PhinFields, BrewResult):
    pass

class EspressoBrew(EspressoFields, BrewResult):
    pass

Brew = Annotated[PhinBrew | EspressoBrew, Field(discriminator="method")]

class RecipeInput(InputModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{"brew_id": 2}]})
    brew_id: int = Field(ge=1)

class Recipe(BaseModel):
    coffee_id: int
    method: Method
    brew_id: int
    brew: Brew
