"""HTTP interface: routes, status codes and headers.

Handlers stay thin: FastAPI has already validated the input against the
schemas; the handler calls the service and shapes the HTTP response.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from .schemas import (
    BrewCreate, Brew, Coffee, CoffeeCreate, CoffeeUpdate, ErrorMessage, Method, Product, Recipe, RecipeSave,
    RecordId,
)
from .service import DialInService


def get_service(request: Request) -> DialInService:
    return request.app.state.service


Service = Annotated[DialInService, Depends(get_service)]

NOT_FOUND = {404: {"model": ErrorMessage, "description": "No record with this ID."}}
INVALID = {422: {"description": "Invalid input, or valid input that breaks a business rule."}}
CONFLICT = {409: {"model": ErrorMessage, "description": "Not enough coffee left for this dose."}}

router = APIRouter(prefix="/api")


@router.get("/products", response_model=list[Product], tags=["products"])
def list_products(service: Service):
    return service.list_products()


# ---- coffees -------------------------------------------------------------------


@router.get("/coffees", response_model=list[Coffee], tags=["coffees"])
def list_coffees(service: Service):
    return service.list_coffees()


@router.post("/coffees", response_model=Coffee, status_code=201, responses=INVALID, tags=["coffees"])
def create_coffee(body: CoffeeCreate, response: Response, service: Service):
    coffee = service.create_coffee(body.model_dump())
    response.headers["Location"] = f"/api/coffees/{coffee['id']}"
    return coffee


@router.get("/coffees/{coffee_id}", response_model=Coffee, responses=NOT_FOUND, tags=["coffees"])
def read_coffee(coffee_id: RecordId, service: Service):
    return service.get_coffee(coffee_id)


@router.put("/coffees/{coffee_id}", response_model=Coffee, responses={**NOT_FOUND, **INVALID}, tags=["coffees"])
def update_coffee(coffee_id: RecordId, body: CoffeeUpdate, service: Service):
    return service.update_coffee(coffee_id, body.model_dump())


@router.delete("/coffees/{coffee_id}", status_code=204, responses=NOT_FOUND, tags=["coffees"])
def delete_coffee(coffee_id: RecordId, service: Service):
    service.delete_coffee(coffee_id)
    return Response(status_code=204)


# ---- brews -----------------------------------------------------------------------


@router.get("/coffees/{coffee_id}/brews", response_model=list[Brew], responses=NOT_FOUND, tags=["brews"])
def list_brews(coffee_id: RecordId, service: Service, method: Method | None = None):
    return service.list_brews(coffee_id, method.value if method else None)


@router.post(
    "/coffees/{coffee_id}/brews",
    response_model=Brew,
    status_code=201,
    responses={**NOT_FOUND, **CONFLICT, **INVALID},
    tags=["brews"],
    summary="Log a brew, subtract its dose from stock, get advice for the next one",
)
def add_brew(coffee_id: RecordId, body: BrewCreate, response: Response, service: Service):
    brew = service.add_brew(coffee_id, body.model_dump())
    response.headers["Location"] = f"/api/brews/{brew['id']}"
    return brew


@router.get("/brews/{brew_id}", response_model=Brew, responses=NOT_FOUND, tags=["brews"])
def read_brew(brew_id: RecordId, service: Service):
    return service.get_brew(brew_id)


@router.delete("/brews/{brew_id}", status_code=204, responses=NOT_FOUND, tags=["brews"],
               summary="Delete a brew and return its dose to stock")
def delete_brew(brew_id: RecordId, service: Service):
    service.delete_brew(brew_id)
    return Response(status_code=204)


# ---- recipes ---------------------------------------------------------------------


@router.get("/coffees/{coffee_id}/recipes", response_model=list[Recipe], responses=NOT_FOUND, tags=["recipes"])
def list_recipes(coffee_id: RecordId, service: Service):
    return service.list_recipes(coffee_id)


@router.put(
    "/coffees/{coffee_id}/recipes/{method}",
    response_model=Recipe,
    responses={**NOT_FOUND, **INVALID},
    tags=["recipes"],
    summary="Save a balanced brew as the recipe for this method (replaces the old one)",
)
def save_recipe(coffee_id: RecordId, method: Method, body: RecipeSave, service: Service):
    return service.save_recipe(coffee_id, method.value, body.brew_id)
