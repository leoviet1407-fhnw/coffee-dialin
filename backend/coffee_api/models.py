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
