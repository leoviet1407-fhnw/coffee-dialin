"""Database tables (ORM models).

Each class is one table; each attribute is one column. Relationships let us
write coffee.brews instead of a manual SQL JOIN.

    products 1 ──< coffees 1 ──< brews
                       1
                       └──< recipes >── 1 brews     (one recipe per coffee and method)
"""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Product(Base):
    """The PHIN range. Read-only seed data used to prefill "Add a coffee"."""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # e.g. "saigon-drip"
    name: Mapped[str] = mapped_column(String(80))
    origin: Mapped[str] = mapped_column(String(80))
    roast_level: Mapped[str] = mapped_column(String(10))
    bag_size_g: Mapped[int] = mapped_column(Integer)
    shop_url: Mapped[str] = mapped_column(String(200))


class Coffee(Base):
    """One bag of coffee the user is brewing, with its remaining stock."""

    __tablename__ = "coffees"
    __table_args__ = (CheckConstraint("grams_left >= 0", name="grams_left_not_negative"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(80))
    origin: Mapped[str] = mapped_column(String(80))
    roast_level: Mapped[str] = mapped_column(String(10))
    roast_date: Mapped[date] = mapped_column(Date)
    bag_size_g: Mapped[int] = mapped_column(Integer)
    grams_left: Mapped[float] = mapped_column(Float)

    product: Mapped[Product | None] = relationship()
    # cascade + passive_deletes: deleting a coffee deletes its brews and recipes,
    # enforced by the database itself (ON DELETE CASCADE below).
    brews: Mapped[list["Brew"]] = relationship(
        back_populates="coffee", cascade="all, delete-orphan", passive_deletes=True, order_by="Brew.id"
    )
    recipes: Mapped[list["Recipe"]] = relationship(
        back_populates="coffee", cascade="all, delete-orphan", passive_deletes=True
    )


class Brew(Base):
    """One Phin brew or espresso shot.

    Both methods share one table. Columns that only one method uses are NULL
    for the other (single-table design: simple queries, one brew log).
    """

    __tablename__ = "brews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coffee_id: Mapped[int] = mapped_column(ForeignKey("coffees.id", ondelete="CASCADE"), index=True)
    method: Mapped[str] = mapped_column(String(10))  # "phin" or "espresso"
    dose_g: Mapped[float] = mapped_column(Float)
    grind_setting: Mapped[str] = mapped_column(String(20))
    taste: Mapped[str] = mapped_column(String(10))  # "sour", "balanced" or "bitter"
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)

    # Phin filter only
    water_ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    drip_time_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Espresso only
    yield_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    shot_time_s: Mapped[int | None] = mapped_column(Integer, nullable=True)

    coffee: Mapped[Coffee] = relationship(back_populates="brews")


class Recipe(Base):
    """The saved, dialed-in brew for one coffee and one method."""

    __tablename__ = "recipes"
    # At most one recipe per coffee and method; saving a new one replaces it.
    __table_args__ = (UniqueConstraint("coffee_id", "method", name="one_recipe_per_method"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coffee_id: Mapped[int] = mapped_column(ForeignKey("coffees.id", ondelete="CASCADE"))
    method: Mapped[str] = mapped_column(String(10))
    # Deleting the brew behind a recipe also removes the recipe.
    brew_id: Mapped[int] = mapped_column(ForeignKey("brews.id", ondelete="CASCADE"))

    coffee: Mapped[Coffee] = relationship(back_populates="recipes")
    brew: Mapped[Brew] = relationship()
