"""Database connection: one SQLite file, opened through SQLAlchemy.

SQLite stores the whole database in a single file (data/dialin.db), so there is
no database server to install. SQLAlchemy is the ORM: it maps the Python
classes in models.py to tables and turns our Python code into SQL.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Parent class of every table in models.py."""


def make_engine(url: str) -> Engine:
    # check_same_thread=False: FastAPI may run a request in a different thread
    # than the one that opened the connection; each request still gets its own session.
    options = {"connect_args": {"check_same_thread": False}}
    if ":memory:" in url:
        # An in-memory database exists only inside one connection, so all sessions must share it.
        options["poolclass"] = StaticPool
    engine = create_engine(url, **options)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        # SQLite ignores FOREIGN KEY rules unless this is switched on per connection.
        # We need it so that deleting a coffee also deletes its brews (ON DELETE CASCADE).
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    return engine


def make_session_factory(engine: Engine) -> sessionmaker:
    # expire_on_commit=False: objects stay readable after commit, so the API can
    # turn them into JSON without another database round trip.
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_tables(engine: Engine) -> None:
    from . import models  # noqa: F401  (registers the tables on Base)

    Base.metadata.create_all(engine)
