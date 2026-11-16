"""Application setup: connect the database, service, routes and frontend.

Run with:  uvicorn dialin_api.main:app --reload
"""

import os
from collections.abc import Callable
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .db import create_tables, make_engine, make_session_factory
from .seed import seed_demo, seed_products
from .service import Conflict, DialInService, NotFound, RuleViolation

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = f"sqlite:///{ROOT / 'data' / 'dialin.db'}"
FRONTEND_DIR = ROOT / "frontend"


def create_app(
    database_url: str | None = None,
    demo_data: bool | None = None,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    database_url = database_url or os.environ.get("DIALIN_DATABASE_URL", DEFAULT_DB)
    if demo_data is None:
        demo_data = os.environ.get("DIALIN_DEMO_DATA", "1") == "1"

    app = FastAPI(
        title="PHIN Dial-in API",
        version="0.1.0",
        description="Log Phin and espresso brews, get one piece of advice per brew, save the recipe that works, "
        "and keep track of the coffee left in the bag.",
    )

    # 1. Database: create data/ and the tables if needed, then seed.
    if database_url.startswith("sqlite:///") and ":memory:" not in database_url:
        Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = make_engine(database_url)
    create_tables(engine)
    sessions = make_session_factory(engine)
    seed_products(sessions)
    if demo_data:
        seed_demo(sessions, today())

    # 2. Service: created once and handed to every request (dependency injection, see api.get_service).
    app.state.service = DialInService(sessions, today=today)
    app.include_router(router)

    # 3. Turn service exceptions into HTTP status codes.
    def error(status_code: int):
        def handler(_request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})

        return handler

    app.add_exception_handler(NotFound, error(404))
    app.add_exception_handler(RuleViolation, error(422))
    app.add_exception_handler(Conflict, error(409))

    # 4. Frontend: mounted last so /api, /docs and /openapi.json keep priority.
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app


app = create_app()
