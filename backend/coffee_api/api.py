"""HTTP interface: routes, status codes, Location headers and error mapping. Rules live in the service."""
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, FastAPI, Path as PathParameter, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from .models import (Brew, BrewInput, Coffee, CoffeeInput, CoffeeUpdate, Error, Method, Product,
                     Recipe, RecipeInput)
from .service import CoffeeError, CoffeeService
from .storage import JsonStore

RecordId = Annotated[int, PathParameter(ge=1)]
ERRORS = {
    404: {"model": Error, "description": "Resource not found"},
    409: {"model": Error, "description": "Conflict with current state"},
    422: {"model": Error, "description": "Invalid input"},
}
LOCATION = {"Location": {"description": "Relative URL of the created resource", "schema": {"type": "string"}}}

def errors(*codes: int) -> dict:
    return {code: ERRORS[code] for code in codes}

def create_app(data_file: Path) -> FastAPI:
    app = FastAPI(title="PHIN Dial-in API", version="0.2.0",
                  description="Log Phin and espresso brews, get one piece of advice per brew, "
                              "save the recipe that works and track the coffee left. Milestone 2 backend.")
    app.state.service = CoffeeService(JsonStore(data_file))

    def get_service(request: Request) -> CoffeeService:
        return request.app.state.service

    Service = Annotated[CoffeeService, Depends(get_service)]
    api = APIRouter(prefix="/api")

    @app.exception_handler(CoffeeError)
    async def business_error(request: Request, error: CoffeeError):
        status = {"invalid_input": 422, "not_found": 404, "conflict": 409}[error.code]
        return JSONResponse(status_code=status, content={"code": error.code, "message": error.message})

    @app.exception_handler(RequestValidationError)
    async def input_error(request: Request, error: RequestValidationError):
        messages = [".".join(str(part) for part in e["loc"]) + ": " + e["msg"] for e in error.errors()]
        return JSONResponse(status_code=422, content={"code": "invalid_input", "message": "; ".join(messages)})

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(error.status_code, "http_error")
        return JSONResponse(status_code=error.status_code, headers=error.headers,
                            content={"code": code, "message": str(error.detail)})

    @api.get("/products", response_model=list[Product], tags=["Products"], operation_id="listProducts")
    def list_products(service: Service):
        return service.list_products()

    @api.get("/coffees", response_model=list[Coffee], tags=["Coffees"], operation_id="listCoffees")
    def list_coffees(service: Service):
        return service.list_coffees()

    @api.post("/coffees", response_model=Coffee, status_code=201, tags=["Coffees"],
              operation_id="createCoffee", responses={**errors(422), 201: {"headers": LOCATION}})
    def create_coffee(body: CoffeeInput, response: Response, service: Service):
        coffee = service.create_coffee(body.model_dump())
        response.headers["Location"] = f"/api/coffees/{coffee['id']}"
        return coffee

    @api.get("/coffees/{coffee_id}", response_model=Coffee, tags=["Coffees"],
             operation_id="readCoffee", responses=errors(404, 422))
    def read_coffee(coffee_id: RecordId, service: Service):
        return service.get_coffee(coffee_id)

    @api.put("/coffees/{coffee_id}", response_model=Coffee, tags=["Coffees"],
             operation_id="replaceCoffee", responses=errors(404, 422))
    def replace_coffee(coffee_id: RecordId, body: CoffeeUpdate, service: Service):
        return service.replace_coffee(coffee_id, body.model_dump())

    @api.delete("/coffees/{coffee_id}", status_code=204, response_class=Response, tags=["Coffees"],
                operation_id="deleteCoffee", responses=errors(404, 422))
    def delete_coffee(coffee_id: RecordId, service: Service):
        service.delete_coffee(coffee_id)
        return Response(status_code=204)

    @api.get("/coffees/{coffee_id}/brews", response_model=list[Brew], tags=["Brews"],
             operation_id="listBrews", responses=errors(404, 422))
    def list_brews(coffee_id: RecordId, service: Service,
                   method: Annotated[Method | None, Query(description="Only brews of this method.")] = None):
        return service.list_brews(coffee_id, method)

    @api.post("/coffees/{coffee_id}/brews", response_model=Brew, status_code=201, tags=["Brews"],
              operation_id="logBrew", responses={**errors(404, 409, 422), 201: {"headers": LOCATION}})
    def log_brew(coffee_id: RecordId, body: BrewInput, response: Response, service: Service):
        brew = service.log_brew(coffee_id, body.model_dump())
        response.headers["Location"] = f"/api/brews/{brew['id']}"
        return brew

    @api.delete("/brews/{brew_id}", status_code=204, response_class=Response, tags=["Brews"],
                operation_id="deleteBrew", responses=errors(404, 422))
    def delete_brew(brew_id: RecordId, service: Service):
        service.delete_brew(brew_id)
        return Response(status_code=204)

    @api.get("/coffees/{coffee_id}/recipes", response_model=list[Recipe], tags=["Recipes"],
             operation_id="listRecipes", responses=errors(404, 422))
    def list_recipes(coffee_id: RecordId, service: Service):
        return service.list_recipes(coffee_id)

    @api.put("/coffees/{coffee_id}/recipes/{method}", response_model=Recipe, tags=["Recipes"],
             operation_id="saveRecipe", responses=errors(404, 422))
    def save_recipe(coffee_id: RecordId, method: Method, body: RecipeInput, service: Service):
        return service.save_recipe(coffee_id, method, body.brew_id)

    app.include_router(api)
    return app
