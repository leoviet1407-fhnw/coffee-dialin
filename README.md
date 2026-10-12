# PHIN Dial-in ([https://drive.google.com/file/d/1Ay8QxTo7vYY0t0jpf_nk3l4DjRRTTR7l/view?usp=sharing](https://www.figma.com/design/wAwisPu8mBdwfxbjY021eN/PHIN-Dial-in?node-id=1-307&t=Pj0qBKTYDaNcfAln-1))

> *PHIN Dial-in automates dialing in coffee: it logs each Phin or espresso brew, tells you the one change to make next, saves the recipe that works, and warns you before your beans run out.*

A web application branded for **PHIN Kafi** (Vietnamese coffee from Switzerland, [phinkafi.ch](https://phinkafi.ch), a team member's own brand), built around its coffees and two brew methods: the traditional **Phin filter** and the **espresso machine**.

> Web-based Applications · FHNW · HS26 · group project
> **Status: planning.** This README is the project plan. Implementation starts once the group has agreed on it.

---

## 1. Analysis

### The process we automate

Every bag of coffee and every brew method behaves differently. To get a good cup you adjust grind, dose, water and time over several attempts. This is called *dialing in*.

| Today (manual) | With PHIN Dial-in (automated) |
| --- | --- |
| Note the numbers in your head or on paper | Every brew is saved per coffee and method; dose and grind are prefilled from the last brew |
| Work out the ratio and check the time | Ratio is calculated and compared with the target for Phin (4–6 min) or espresso (25–30 s, ratio 1:2) |
| Guess what to change, often several things at once | One rule-based suggestion per brew, e.g. "sour and fast → grind finer" |
| Forget the recipe by the next bag | The balanced brew is saved as the recipe for that coffee and method |
| Notice the bag is empty when it is empty | Each brew subtracts its dose; a warning and a reorder link appear when about 3 brews are left |

### Users

| User | Situation | Need |
| --- | --- | --- |
| **Mia, home brewer** (primary) | Bought a PHIN starter set; brews Saigon Drip in the Phin filter most mornings. | Know what to change when the drip is too fast or the cup too bitter, and remember what worked. |
| **Jonas, espresso at home** (secondary) | Uses Da Lat Dawn in an espresso machine. | Get from a sour or bitter shot to a balanced one in fewer attempts. |
| **PHIN Kafi** (stakeholder) | Sells the coffees and filters. | Customers who succeed with the product and reorder on time. |

### Value

- **Fewer wasted brews:** one clear change per attempt instead of guessing.
- **Repeatable results:** the recipe that worked is saved per coffee and brew method.
- **Never run out:** the remaining stock is always visible, with a reorder link.
- **Learning:** every suggestion explains *why*, so users build intuition.

### Scope of the first version

| In scope | Out of scope |
| --- | --- |
| Coffees: add (from the PHIN range or "other"), view, edit, delete | Shop, cart, payments |
| Brews: log, list, delete, for **Phin filter** and **espresso** | Editing a brew (delete and log again instead) |
| Rule-based advice for the next brew | Machine learning or taste prediction |
| One saved recipe per coffee and method | Recipe history, public sharing |
| Simple stock: grams left per coffee, low-stock warning | Barcode scanning, multiple bags per coffee |
| JSON file storage | Moka pot, cold brew, milk recipes |
| *Later in the course:* user accounts, Docker | Native mobile apps |

### User stories

1. As Mia, I want to **add my coffee by picking it from the PHIN range** so that name, origin and bag size fill in automatically.
2. As Mia, I want to **log a Phin brew** and **immediately see what to change** next time.
3. As Jonas, I want to **log an espresso shot** and get advice suited to espresso.
4. As Mia, I want to **save the brew that tasted balanced as my recipe** so that I can repeat it tomorrow.
5. As Mia, I want to **see how much coffee is left** and be reminded to reorder before the bag runs out.

---

## 2. Design

### Workflow A: log a Phin brew and get advice

User: Mia · Goal: a balanced Phin coffee · Scope: one coffee, one brew at a time.

| Step | User action | Expected application response |
| --- | --- | --- |
| 1 | Open "Saigon Drip" and choose *Phin filter*. | Show the coffee, grams left, the saved recipe (if any), the brew log and the last advice. Dose and grind are prefilled. |
| 2 | Enter 18 g, 140 ml, 94 °C, drip time 3:10, taste *sour*; submit. | Validate the values and check that enough coffee is left. |
| 3 · success | Read the result. | Save the brew, subtract 18 g from stock, show ratio 1:7.8 and the advice: *"Sour and fast (3:10). Grind finer or press the screen a little firmer."* |
| 2a · alternative | Submit without a taste. | Show *"Taste: required"*, keep the other inputs, do not save. |
| 2b · alternative | Enter 18 g when only 6 g are left. | Refuse: *"Only 6 g left. Add a new bag first."* Nothing is saved or subtracted. |

### Workflow B: save the recipe

| Step | User action | Expected application response |
| --- | --- | --- |
| 1 | In the brew log, choose **Save as recipe** on a balanced brew. | Check that the brew belongs to this coffee and method and tasted balanced. |
| 2 · success | Read the confirmation. | The recipe card shows e.g. "18 g · 140 ml · 94 °C · 4:45 drip · grind 6". A later recipe for the same method replaces it. |
| 1a · alternative | Try to save a sour brew as the recipe. | Refuse: only a balanced brew can become the recipe. |

### Workflow C: running low

| Step | User action | Expected application response |
| --- | --- | --- |
| 1 | Log a brew that leaves 40 g (fewer than 3 brews at 18 g). | Show *"Running low: about 2 brews left"* with **Reorder on phinkafi.ch**. |
| 2 | Open a new bag and choose **New bag**. | Add the bag size to the grams left and update the roast date. |

### Screens

```
Coffees                                  Coffee detail
┌──────────────────────────────────┐     ┌────────────────────────────────────┐
│ ▓▓ PHIN  Coffees ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │     │ ← All coffees                      │
│ YOUR COFFEES                     │     │ SAIGON DRIP · 100% Robusta         │
│ ┌──────────┐┌──────────┐┌──────┐ │     │ 142 g left · about 7 brews [New bag]│
│ │HANOI HAZE││DA LAT    ││SAIGON│ │     │ [ Phin filter ] [ Espresso ]       │
│ │Arabica   ││DAWN      ││DRIP  │ │     │ ┌ Recipe ────────────────────────┐ │
│ │210 g left││⚠ 30 g    ││142 g │ │     │ │ 18 g · 140 ml · 94 °C · 4:45   │ │
│ └──────────┘└──────────┘└──────┘ │     │ └────────────────────────────────┘ │
│ ADD A COFFEE                     │     │ ┌ Log a brew ────────────────────┐ │
│ [Saigon Drip ▾] Roast date [   ] │     │ │ Dose Water Temp Drip Grind     │ │
│ [ ADD ]                          │     │ │ Taste ○sour ○balanced ○bitter  │ │
└──────────────────────────────────┘     │ └────────────────────────────────┘ │
                                         │ ▌Next brew: grind finer            │
                                         │ Brew log (table)  [Save as recipe] │
                                         └────────────────────────────────────┘
```

Interface patterns (from the app design class): *cards* to browse coffees, *tabs* to switch brew method, a *form* to log a brew, a *table* to compare brews, *detail cards* for the recipe and stock.

### Brand: PHIN Kafi look and feel

| Token | Value | Use |
| --- | --- | --- |
| `--phin-red` | `#B43824` | Header, primary buttons |
| `--phin-cream` | `#F7F4E5` | Text on red, light backgrounds |
| `--phin-ink` | `#020912` | Body text on cream |
| `--phin-slate` | `#2C3638` | Secondary buttons, table headers |
| `--phin-peach` | `#FFDFB8` | Advice panel, recipe card, low-stock warning |
| Heading font | **Figtree** 500, uppercase page titles | Google Fonts |
| Body font | **Anonymous Pro** (monospace) | Google Fonts; suits the numbers in the log |
| Shapes | Square corners, 2px outlines, pill-shaped badges | |
| Logo | PHIN logo in the header | Own brand |

Accessibility: cream on red has a 5.39:1 contrast ratio (passes WCAG AA). Use full-opacity cream for body text. Never use colour alone for taste or warnings; always add a text label.

### Domain model

```
Product 0..1 ──prefills── * Coffee 1 ──── * Brew
                             1
                             └──── 0..2 Recipe ────▶ 1 Brew   (max. one recipe per method)
```

| Entity | Fields |
| --- | --- |
| **Product** (seed, read-only) | id (e.g. `saigon-drip`), name, origin, roast_level, bag_size_g, shop_url |
| **Coffee** | id, product_id (optional), name, origin, roast_level, roast_date, bag_size_g, grams_left · *derived:* low_stock, brews_left, days_off_roast |
| **Brew** | id, coffee_id, method (`phin` / `espresso`), dose_g, grind_setting, taste, rating, notes, created_at · *Phin:* water_ml, water_temp_c, drip_time_s · *espresso:* yield_g, shot_time_s · *derived:* ratio, advice |
| **Recipe** | coffee_id, method, brew_id |

Seed products: **Hanoi Haze** (100% Arabica), **Da Lat Dawn** (Robusta & Arabica blend), **Saigon Drip** (100% Robusta).

### Brewing rules: what a good brew looks like

These are the targets the app checks and the fixes it suggests. They are well-established barista rules of thumb and PHIN's own Phin brew guide: a starting point that taste always overrides.

#### Espresso machine

| Variable | Target | Notes |
| --- | --- | --- |
| Dose | **18 g** (double basket, 16–20 g) | Match the basket size; keep the dose fixed while dialing in. |
| Ratio (yield ÷ dose) | **1:2**, i.e. 18 g in → **36 g out** | On target between 1:1.8 and 1:2.2. Ristretto (1:1–1:1.5) and lungo (1:2.5–1:3) are out of scope for v1. |
| Extraction time | **25–30 s** | Counted from pressing the button (pump start) to stopping the shot. |
| Water temperature | 90–96 °C, usually **93 °C** | Lower (90–92 °C) for dark roasts and Robusta-heavy coffees, higher (94–96 °C) for light Arabica. Only advised, not logged in v1. |
| Pressure | about 9 bar | Set by the machine; not logged. |
| Grind | Fine, like table salt to powdered sugar | The main lever for time. |

| What you see and taste | Likely cause | One fix for the next shot |
| --- | --- | --- |
| Under 25 s and sour, thin or watery | Under-extracted: water runs through too fast | **Grind finer** |
| Over 30 s and bitter, dry or harsh | Over-extracted: water runs through too slowly | **Grind coarser** |
| 25–30 s but sour | Not enough extraction for this coffee | **Longer yield** (e.g. 36 → 40 g, towards 1:2.2) |
| 25–30 s but bitter | Too much extraction for this coffee | **Shorter yield** (e.g. 36 → 32 g, towards 1:1.8) |
| 25–30 s, about 1:2 and balanced | Dialed in | **Save as recipe** |

#### Phin filter

Based on PHIN's brew guide at [phinkafi.ch](https://phinkafi.ch).

| Variable | Target | Notes |
| --- | --- | --- |
| Dose | **15–20 g**, about 2–3 tablespoons | Level the grounds and press lightly with the filter screen. |
| Grind | Medium-coarse | Coarser than espresso, finer than French press. Too fine clogs the filter. |
| Water temperature | **90–96 °C** | Just off the boil. |
| Bloom | **20–30 ml**, wait **20–30 s** | Wets the grounds so they release gas and extract evenly. |
| Main pour | **100–120 ml** more, then cover | Total water **120–150 ml**. |
| Ratio (water ÷ coffee) | about **1:7** (on target 1:6–1:8) | e.g. 18 g with 130 ml. Stronger for serving over condensed milk. |
| Drip time | **4–6 min** | From the main pour to the last drop. |

| What you see and taste | Likely cause | One fix for the next brew |
| --- | --- | --- |
| Done in under 4 min and sour or weak | Water runs through too fast | **Grind finer** or **press the screen a little firmer** |
| Over 6 min (or it stops dripping) and bitter | Too fine or pressed too hard; the filter clogs | **Grind coarser** or **press more lightly** |
| 4–6 min but sour or weak | Not enough extraction | **Hotter water** (up to 96 °C) or **a little more coffee** |
| 4–6 min but bitter | Too much extraction | **Cooler water** (around 90 °C) or **a little less coffee** |
| 4–6 min, about 1:7 and balanced | Dialed in | **Save as recipe** |

#### Rules for both methods

1. **Change one thing at a time**, otherwise you can't tell what helped.
2. **Time decides the lever:** when the time is off, change the grind (or the Phin press) first. When the time is on target, adjust the ratio or the temperature.
3. **Taste decides the direction:** sour → extract more; bitter → extract less.
4. **Taste beats numbers:** a balanced brew can be saved even if the time or ratio is slightly off target.
5. **Fresh beans:** coffee is best about 7–30 days after roasting. The app shows the days since roasting; very fresh or old beans may need a re-dial.

### Business rules

| # | Rule | Response |
| --- | --- | --- |
| R1 | Input ranges per method. **Phin:** dose 10–25 g, water 60–200 ml, temperature 85–100 °C, drip time 1–10 min. **Espresso:** dose 5–30 g, yield 5–120 g, time 5–120 s. Taste is sour / balanced / bitter; rating 1–5 (optional). | 422 |
| R2 | The roast date cannot be in the future. | 422 |
| R3 | Targets from the brewing rules above. **Espresso:** 25–30 s, ratio 1:2 (on target 1:1.8–1:2.2). **Phin:** drip 4–6 min, ratio about 1:7 (on target 1:6–1:8). Each brew response reports `time_status` (fast / ok / slow) and `ratio_status` (low / ok / high). | (in every brew response) |
| R4 | Advice follows the fix tables above: one suggestion per brew; time chooses the lever, taste chooses the direction; balanced → save as recipe. | (in every brew response) |
| R5 | Only a **balanced** brew of the **same coffee and method** can become the recipe; a new recipe replaces the old one. | 422 |
| R6 | **Stock:** logging a brew subtracts its dose from `grams_left`. A brew needing more than is left is refused and nothing changes. | 409 |
| R7 | **Low stock:** when `grams_left` is less than 3 × the last dose, the coffee is flagged `low_stock` and PHIN coffees show their reorder link. | (in coffee response) |
| R8 | Deleting a brew returns its dose to stock. Deleting a coffee deletes its brews and recipes. | 204 |

### API operations

Base path `/api`. FastAPI will generate the OpenAPI contract; we commit it to `contracts/` and keep it in sync with a test.

| Method | Path | Purpose | Success | Failures |
| --- | --- | --- | --- | --- |
| GET | `/products` | PHIN range to prefill "add coffee" | 200 | |
| GET | `/coffees` | List coffees with stock | 200 | |
| POST | `/coffees` | Add a coffee | 201 + `Location` | 422 |
| GET | `/coffees/{id}` | Read a coffee | 200 | 404 |
| PUT | `/coffees/{id}` | Edit a coffee, e.g. new bag | 200 | 404, 422 |
| DELETE | `/coffees/{id}` | Delete a coffee | 204 | 404 |
| GET | `/coffees/{id}/brews?method=phin` | Brew log with advice | 200 | 404 |
| POST | `/coffees/{id}/brews` | Log a brew, get advice | 201 + `Location` | 404, 409, 422 |
| DELETE | `/brews/{id}` | Delete a brew | 204 | 404 |
| GET | `/coffees/{id}/recipes` | Saved recipes (max. one per method) | 200 | 404 |
| PUT | `/coffees/{id}/recipes/{method}` | Save a brew as the recipe | 200 | 404, 422 |

#### Example: log a Phin brew

```http
POST /api/coffees/3/brews
Content-Type: application/json

{"method": "phin", "dose_g": 18, "water_ml": 140, "water_temp_c": 94,
 "drip_time_s": 190, "grind_setting": "7", "taste": "sour"}
```

```http
HTTP/1.1 201 Created
Location: /api/brews/12

{"id": 12, "coffee_id": 3, "method": "phin", "...": "...", "ratio": 7.8,
 "grams_left": 124,
 "advice": {"action": "grind_finer", "time_status": "fast",
            "message": "Sour and fast (3:10). Grind finer or press the screen a little firmer."}}
```

| Failure example | Response |
| --- | --- |
| `"water_temp_c": 110` | `422`: `water_temp_c` must be at most 100 |
| `"dose_g": 18` with 6 g left | `409`: "Only 6 g left. Add a new bag first." |
| Coffee 999 | `404`: "Coffee 999 was not found." |

---

## 3. Planned implementation

Three logical **layers** in one server **tier**, following the course's Station Bar example:

```
Browser (frontend/: HTML, CSS, JS, PHIN styling)  ──HTTP + JSON──▶  Uvicorn + FastAPI
                                                                    ├─ api.py       routes, status codes
                                                                    ├─ service.py   business rules R2, R5–R8
                                                                    │  └─ advice.py    advice R3–R4 (pure functions)
                                                                    ├─ models.py    Pydantic schemas (R1)
                                                                    └─ storage.py   JsonStore: seed.json → data.json
```

| Part | Choice | Reason |
| --- | --- | --- |
| Backend | Python, FastAPI, Pydantic, Uvicorn | Used in class; validation and OpenAPI come from the models. |
| Storage | JSON file, optional ORM (SQLAlchemy / SQLModel) | Matches the persistence class (19 Oct). |
| Frontend | Plain HTML, CSS, JavaScript, served by the same app | Matches the frontend class (9 Nov); no build step. |
| Tests | pytest + FastAPI `TestClient`; Postman collection | Every status code in the API table has a test. |
| Environment | GitHub Codespaces (`.devcontainer`) | Course setup; reproducible for the graders. |
| Later | User accounts (23 Nov), Dockerfile (30 Nov) | Follows the course schedule. |

---

## 4. Plan

### Fit with the course (assessment criteria)

| Criterion | Weight | How this project covers it |
| --- | --- | --- |
| Problem, value and scope | 15% | A real process (dialing in) with clear users, value and explicit scope. |
| Functionality and business rules | 25% | Full CRUD on coffees, brews with advice, recipe rules, stock rules (R6–R8). Validation (422) and state conflicts (409) are kept apart, as taught. |
| Architecture, API and data | 20% | Layered FastAPI backend, OpenAPI contract, related data (product → coffee → brews/recipes), JSON storage. |
| Testing and security | 15% | Tests for every success and failure case; user accounts in the security week. |
| Usability | 10% | Prefilled forms, one clear suggestion, inline errors, responsive layout, PHIN branding. |
| Documentation, reproducibility, collaboration | 15% | This README, Codespaces setup, seed data, contribution table, commits from every member. |

To keep it simple, both methods share one brew log, one recipe workflow and one advice structure; only the input fields and targets differ.

### Timeline (course schedule HS26)

| Week | Date | Work | Course milestone |
| --- | --- | --- | --- |
| CW42 | 12–18 Oct | Agree on this plan; sketches/prototype with PHIN branding; sample JSON | Catch up on the design milestone (05 Oct) |
| CW43 | 19–25 Oct | Models, JSON store, products, coffee + brew CRUD, stock rule, first tests | ORM & persistence class |
| CW44 | 26 Oct | Advice rules, recipes, low stock, OpenAPI contract | **Coaching: backend** |
| CW45–46 | 2–15 Nov | Frontend: coffee list, brew form and log, recipe and stock cards, PHIN styling | Frontend integration class (9 Nov) |
| CW47 | 16 Nov | Usability test with 2–3 people; fixes | **Coaching: integration** |
| CW48 | 23–29 Nov | User accounts, protected requests, tests | API security class |
| CW49 | 30 Nov – 6 Dec | Dockerfile; run from a clean checkout; finish README | Microservices & deployment class |
| CW50 | 07 Dec | Final review; record the presentation (max. 20 min) | **Coaching: submission readiness** |

### Optional extensions (only if time allows)

- **QR code on PHIN bags** linking to `…/#/add?product=saigon-drip`: the phone's own camera opens it, so the app needs no scanning code.
- Advice that also compares with the previous brew.
- Moving storage to an ORM.

### Team and responsibilities

| Member | Main responsibility | Contributions |
| --- | --- | --- |
| Pham Lac Viet Ha | Coordination, README, analysis, PHIN brand/UI, workflows, sketches, frontend | |
| Janusz Buhler | API contract, backend, advice rules, data/persistence, stock rules, tests, deployment | |

Both members review the whole project. Very unequal contributions may lead to individual grading.

### Open questions

1. Bag sizes of the PHIN coffees (250 g? 500 g?) and the product page links for the reorder button.
2. Grinder settings differ per grinder: is free text enough?
3. One personal account per user, or also a shared account (e.g. for a café)?

### Use of AI assistance

We drafted parts of this plan with an AI assistant (Claude). The group reviews every part and must be able to explain it.

## References

- Course material *Web-based Applications HS26*, FHNW (D. Montecchiari): teaching model, networks and APIs, app design, API design and lifecycle, API contracts and backend development.
- PHIN Kafi: brand, coffees and Phin brew guide, <https://phinkafi.ch>
- FastAPI documentation: <https://fastapi.tiangolo.com/>
- OpenAPI Specification 3.1: <https://spec.openapis.org/oas/latest.html>
