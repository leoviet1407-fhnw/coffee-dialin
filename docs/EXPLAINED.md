# How PHIN Dial-in works

A walk through the code: what each part does, how one request travels through it, and why the database is built the way it is. Read it next to the code.

## 1. The big picture

```
Browser (frontend/)                         Server: one Python process (Uvicorn + FastAPI)
┌──────────────────────┐   HTTP + JSON   ┌────────────────────────────────────────────────┐
│ index.html  structure│ ──────────────▶ │ api.py      HTTP interface: routes, status codes│
│ styles.css  PHIN look│                 │ schemas.py  shapes + validation of the JSON (R1)│
│ app.js      fetch()  │ ◀────────────── │ service.py  business rules (R2, R5–R8)          │
└──────────────────────┘                 │ advice.py   brewing rules (R3, R4)               │
                                         │ models.py   tables (SQLAlchemy ORM)              │
                                         │ db.py       connection to SQLite                 │
                                         └──────────────────────┬─────────────────────────┘
                                                                │ SQL
                                                        data/dialin.db (SQLite file)
```

- **Layers** (how the code is split by responsibility): HTTP interface → application logic → data access. This is the same split as the course's Station Bar example (`api.py` → `BarService` → `JsonStore`).
- **Tiers** (where it runs): the browser is the client tier; the server tier is one process that runs all backend layers.

| File | What it does |
| --- | --- |
| `dialin_api/main.py` | `create_app()` wires everything: opens the database, creates the tables, seeds data, creates the service, registers routes, maps errors to status codes, serves the frontend. |
| `dialin_api/api.py` | One function per endpoint. Gets validated input, calls the service, sets status and `Location` header. No rules here. |
| `dialin_api/schemas.py` | Pydantic models: what JSON the API accepts and returns. Ranges like "dose 10–25 g for Phin" live here. FastAPI uses them for validation **and** for the OpenAPI docs at `/docs`. |
| `dialin_api/service.py` | `DialInService`: the business rules. Stock, recipes, prefill from PHIN products, roast date check. Raises `NotFound`, `RuleViolation`, `Conflict`. |
| `dialin_api/advice.py` | Pure functions that turn one brew into one suggestion. No database, no HTTP, easy to test. |
| `dialin_api/models.py` | The four tables as Python classes. |
| `dialin_api/db.py` | Creates the SQLAlchemy engine for SQLite and switches on foreign keys. |
| `dialin_api/seed.py` | The PHIN range (always) and two demo coffees (only into an empty database). |
| `frontend/` | Static files. `app.js` calls the API with `fetch()` and draws the two pages. |
| `tests/` | 45 automatic checks: every rule and every status code. |
| `contracts/dialin-api.openapi.json` | The API contract, generated from the code; a test fails if it is out of date. |

## 2. One request, step by step

**Mia logs a Phin brew:** `POST /api/coffees/1/brews` with `{"method": "phin", "dose_g": 18, "water_ml": 140, "water_temp_c": 94, "drip_time_s": 190, "grind_setting": "7", "taste": "sour"}`.

1. **Browser** (`app.js`, `showDetail` → form submit): reads the form, turns "3:10" into `190` seconds, sends the JSON with `fetch`.
2. **Routing** (`api.py`, `add_brew`): FastAPI matches `POST /coffees/{coffee_id}/brews`, puts `1` into `coffee_id`.
3. **Validation** (`schemas.py`, `BrewCreate`): `"method": "phin"` selects `PhinBrewCreate` (a *discriminated union*), so the Phin ranges apply. `water_temp_c: 110` would stop here with **422** and our code would never run.
4. **Dependency injection** (`api.py`, `Service = Annotated[..., Depends(get_service)]`): FastAPI hands the handler the one `DialInService` created in `main.py`.
5. **Business rules** (`service.py`, `add_brew`): inside one database transaction, load coffee 1 (**404** if missing), check `18 g ≤ grams_left` (**409** if not), subtract 18 g, insert the brew.
6. **Database** (`models.py` + SQLAlchemy): on leaving the `with self.sessions.begin()` block, SQLAlchemy sends `UPDATE coffees SET grams_left=…` and `INSERT INTO brews …` and commits both together.
7. **Advice** (`advice.py`, `phin_advice`): ratio 140 ÷ 18 = 7.78 (ok), 190 s < 240 s (fast) + sour → `grind_finer`.
8. **Response** (`api.py`): **201 Created**, header `Location: /api/brews/5`, body = the brew + ratio + advice + new `grams_left`.
9. **Browser**: redraws the page; the advice box shows "Sour and fast (3:10). Grind finer or press the screen a little firmer."

## 3. The database technology

### What we use

| Part | Technology | In one sentence |
| --- | --- | --- |
| Database | **SQLite** | A full SQL database stored in one file (`data/dialin.db`); no server to install or run. |
| Access from Python | **SQLAlchemy 2** (ORM) | Maps Python classes to tables and writes the SQL for us. |
| Validation | **Pydantic** | Checks the JSON *before* anything touches the database. |

**ORM** = Object-Relational Mapping: we work with Python objects (`coffee.grams_left -= 18`, `coffee.brews`) and SQLAlchemy translates that into SQL (`UPDATE coffees …`, `SELECT … FROM brews WHERE coffee_id = 1`).

### Why SQLite and not the JSON file from class, or PostgreSQL?

| Option | Good | Problem for us |
| --- | --- | --- |
| JSON file (course week 6) | Simple, readable | We would have to write relations, uniqueness, "delete the brews of a deleted coffee" and safe concurrent writes ourselves. |
| **SQLite + SQLAlchemy** ✔ | Real tables, keys, constraints and transactions; one file; works in Codespaces with no setup; tests use a fresh file each | Only one writer at a time: fine for one user or a small team, not for thousands of users. |
| PostgreSQL | Many users, production-grade | Needs a separate server (Docker or cloud) just to start the app. |

Switching later is a one-line change: set `DIALIN_DATABASE_URL=postgresql://…`. The models stay the same, because SQLAlchemy hides the database differences.

### The tables

```
products 1 ──< coffees 1 ──< brews
                  1
                  └──< recipes >── 1 brews      (max. one recipe per coffee and method)
```

| Table | Key columns | Notes |
| --- | --- | --- |
| `products` | `id` (text, e.g. `saigon-drip`) | The PHIN range; seeded on every start. |
| `coffees` | `id`, `product_id` → products | `grams_left` is the stock. `CHECK (grams_left >= 0)`. |
| `brews` | `id`, `coffee_id` → coffees | Phin **and** espresso in one table; Phin-only columns (`water_ml`, `water_temp_c`, `drip_time_s`) are `NULL` for espresso and the other way round. Index on `coffee_id` for fast brew logs. |
| `recipes` | `id`, `coffee_id`, `brew_id` | `UNIQUE (coffee_id, method)` = at most one recipe per method. |

The exact SQL that SQLAlchemy generated, from `sqlite3 data/dialin.db .schema`:

```sql
CREATE TABLE brews (
  id INTEGER NOT NULL, coffee_id INTEGER NOT NULL, method VARCHAR(10) NOT NULL,
  dose_g FLOAT NOT NULL, grind_setting VARCHAR(20) NOT NULL, taste VARCHAR(10) NOT NULL,
  rating INTEGER, notes VARCHAR(500) NOT NULL, created_at DATETIME NOT NULL,
  water_ml FLOAT, water_temp_c FLOAT, drip_time_s INTEGER, yield_g FLOAT, shot_time_s INTEGER,
  PRIMARY KEY (id),
  FOREIGN KEY(coffee_id) REFERENCES coffees (id) ON DELETE CASCADE
);
CREATE TABLE recipes (
  id INTEGER NOT NULL, coffee_id INTEGER NOT NULL, method VARCHAR(10) NOT NULL, brew_id INTEGER NOT NULL,
  PRIMARY KEY (id),
  CONSTRAINT one_recipe_per_method UNIQUE (coffee_id, method),
  FOREIGN KEY(coffee_id) REFERENCES coffees (id) ON DELETE CASCADE,
  FOREIGN KEY(brew_id) REFERENCES brews (id) ON DELETE CASCADE
);
```

### Design decisions you should be able to defend

1. **One `brews` table for both methods** (single-table design). One brew log, one query, one delete. The price is a few `NULL` columns. The alternative (separate `phin_brews` / `espresso_brews` tables) would need two queries for "all brews of a coffee".
2. **Derived values are computed, not stored**: ratio, advice, `brews_left`, `low_stock`, `days_off_roast`. They can never disagree with the stored numbers. Changing a brewing rule changes the advice for old brews too.
3. **The database guards the data, not only Python**:
   - `ON DELETE CASCADE`: deleting a coffee deletes its brews and recipes; deleting a brew deletes a recipe pointing at it (rule R8).
   - `UNIQUE (coffee_id, method)`: two recipes for the same method are impossible even with a bug in Python.
   - `CHECK (grams_left >= 0)`: stock can never go negative.
   - SQLite only enforces foreign keys when `PRAGMA foreign_keys = ON` is sent per connection; `db.py` does that.
4. **Transactions**: every change runs in `with self.sessions.begin():`. If a rule raises an error halfway, everything is rolled back. Example: "not enough coffee" leaves both stock and brew log untouched (tested in `test_not_enough_coffee_is_409_and_changes_nothing`).
5. **One session per request**: each service method opens its own session (its own unit of work) and closes it at the end. No data leaks between requests.

### Look inside the database yourself

```bash
sqlite3 data/dialin.db
```

Then, inside sqlite3: `.tables`, `.schema brews`, `SELECT id, name, grams_left FROM coffees;`, `.quit`. In VS Code or Codespaces the "SQLite Viewer" extension (already in `.devcontainer`) opens the file as a table.

To start again with demo data, stop the server and delete `data/dialin.db`.

### Known limits (good to mention honestly)

- **No migrations yet**: `create_all()` creates missing tables but does not change existing ones. After changing `models.py`, delete `data/dialin.db`. The professional tool for this is **Alembic**.
- **No users yet**: everyone sees all coffees. Accounts follow in the API security week (23 Nov): a `users` table and a `user_id` column on `coffees`.

## 4. Validation, rules and status codes

The course distinguishes "does the input match the schema?" from "is this change allowed now?". Here is where each check lives:

| Check | Where | Status |
| --- | --- | --- |
| Wrong type, missing field, out of range (R1) | `schemas.py`, automatically by FastAPI | **422** (list of field errors) |
| Roast date in the future (R2), unknown product, recipe not balanced / other coffee / other method (R5) | `service.py` → `RuleViolation` | **422** (one sentence) |
| Not enough coffee for the dose (R6) | `service.py` → `Conflict` | **409** |
| Coffee or brew does not exist | `service.py` → `NotFound` | **404** |
| Created | `api.py` | **201** + `Location` header |
| Deleted | `api.py` | **204** (no body) |

`main.py` turns the three exception types into these status codes, so the service never has to know about HTTP.

## 5. The advice engine (`advice.py`)

Both methods follow the README's brewing rules: **time decides the lever, taste decides the direction, one change per brew.**

| Method | Measures | Window | Main fixes |
| --- | --- | --- | --- |
| Espresso | ratio = yield ÷ dose; shot time | 1:1.8–1:2.2; 25–30 s | sour+fast → finer · bitter+slow → coarser · sour on time → longer yield · bitter on time → shorter yield |
| Phin | ratio = water ÷ coffee; drip time | 1:6–1:8; 4–6 min | sour+fast → finer/press firmer · bitter+slow → coarser/press lighter · sour on time → hotter water (max 96 °C) · bitter on time → cooler water (90 °C) |

Balanced always means "keep it and save it as the recipe": taste beats numbers.

## 6. The frontend (`frontend/`)

- **Two pages**, switched by the URL hash: `#/` (coffee list) and `#/coffees/3` (detail). `route()` in `app.js` reads the hash; the HTML for each page is a `<template>` in `index.html`.
- **All data comes from the API** with `fetch()`; nothing is stored in the browser.
- **Errors**: `describeError()` turns FastAPI's 422 list into "Taste: Field required · Yield: …" and shows it next to the form. The typed values stay.
- **Safety**: every text from the database is inserted as text (`node.append(...)`), never as HTML, so a note like `<script>` cannot run.
- **Prefill**: the next brew starts with the last dose and grind, because usually only one thing changes.
- **New bag**: a `<dialog>` that sends `PUT /api/coffees/{id}` with the old grams plus the new bag.

## 7. Tests

```bash
pytest
```

- `tests/test_advice.py`: the brewing rules alone (time windows, ratio windows, every advice branch).
- `tests/test_api.py`: real HTTP requests against a fresh SQLite file per test: every status code, stock, cascade deletes, recipe rules, restart persistence.
- `tests/test_contract.py`: the committed OpenAPI contract matches the code.

## 8. Questions you may get in coaching (with short answers)

- **Why an ORM?** It maps tables to classes, writes safe SQL (no SQL injection, because values are sent as parameters) and lets us change the database engine later without rewriting queries.
- **What happens if two brews are logged at the same moment?** SQLite serialises writes; each brew runs in its own transaction, so stock is updated correctly one after the other.
- **Where is the dose subtracted, and why there?** In `service.add_brew`, inside the transaction that also inserts the brew, so both happen or neither does.
- **Why is the ratio not a column?** It is always `water ÷ dose` or `yield ÷ dose`; storing it would allow inconsistencies.
- **What is dependency injection here?** `main.py` creates one `DialInService` with its session factory; FastAPI's `Depends(get_service)` hands it to each handler. Tests create the app with a temporary database instead: same code, different collaborator.
- **How would you add user accounts?** A `users` table, `coffees.user_id` as a foreign key, and every service query filtered by the logged-in user.
