// PHIN Dial-in frontend.
// Two pages driven by the URL hash: "#/" = coffee list, "#/coffees/3" = coffee detail.
// All data comes from the backend API; the browser stores nothing.

const app = document.getElementById("app");

// Form fields per brew method. The API checks the same ranges (422 if wrong).
const METHODS = {
  phin: {
    label: "Phin",
    targets: "Target: 4–6 min drip · about 1:7 · 90–96 °C",
    fields: [
      { name: "dose_g", label: "Dose (g)", hint: "15–20 g", type: "number", step: "0.1" },
      { name: "water_ml", label: "Water (ml)", hint: "120–150 ml total", type: "number", step: "1" },
      { name: "water_temp_c", label: "Temperature (°C)", hint: "90–96 °C", type: "number", step: "1" },
      { name: "drip_time", label: "Drip time (m:ss)", hint: "4–6 min", type: "text", placeholder: "4:30" },
      { name: "grind_setting", label: "Grind", hint: "medium-coarse", type: "text" },
    ],
    columns: ["Water", "Temp", "Drip"],
    cells: (b) => [`${b.water_ml} ml`, `${b.water_temp_c} °C`, mmss(b.drip_time_s)],
    recipe: (b) => `${b.dose_g} g · ${b.water_ml} ml · ${b.water_temp_c} °C · ${mmss(b.drip_time_s)} drip · grind ${b.grind_setting}`,
  },
  espresso: {
    label: "Espresso",
    targets: "Target: 1:2 ratio (18 g in → 36 g out) · 25–30 s",
    fields: [
      { name: "dose_g", label: "Dose (g)", hint: "16–20 g", type: "number", step: "0.1" },
      { name: "yield_g", label: "Yield (g)", hint: "about 2 × dose", type: "number", step: "0.1" },
      { name: "shot_time_s", label: "Shot time (s)", hint: "25–30 s", type: "number", step: "1" },
      { name: "grind_setting", label: "Grind", hint: "fine", type: "text" },
    ],
    columns: ["Yield", "Time"],
    cells: (b) => [`${b.yield_g} g`, `${b.shot_time_s} s`],
    recipe: (b) => `${b.dose_g} g in → ${b.yield_g} g out (1:${b.ratio.toFixed(1)}) · ${b.shot_time_s} s · grind ${b.grind_setting}`,
  },
};

const LABELS = {
  product_id: "PHIN coffee", name: "Name", origin: "Origin", roast_level: "Roast level", roast_date: "Roast date",
  bag_size_g: "Bag size", grams_left: "Grams left", dose_g: "Dose", water_ml: "Water", water_temp_c: "Temperature",
  drip_time_s: "Drip time", yield_g: "Yield", shot_time_s: "Shot time", grind_setting: "Grind", taste: "Taste",
  rating: "Rating", notes: "Notes",
};

// ---- API helper -------------------------------------------------------------------------

async function api(method, path, body) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(describeError(data.detail) || `Request failed (${res.status}).`);
  return data;
}

// 422 from FastAPI is a list of field errors; our own rules (404/409/422) send one sentence.
function describeError(detail) {
  if (!Array.isArray(detail)) return detail;
  return detail.map((e) => `${LABELS[e.loc.at(-1)] ?? e.loc.at(-1)}: ${e.msg}`).join(" · ");
}

// ---- small helpers ------------------------------------------------------------------------

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "onclick") node.addEventListener("click", v);
    else if (v !== false && v != null) node.setAttribute(k, v === true ? "" : v);
  }
  node.append(...children); // text is added as text, never as HTML (safe for user notes)
  return node;
}

function mount(id) {
  app.replaceChildren(document.getElementById(id).content.cloneNode(true));
}

function showError(form, message) {
  const box = form.querySelector(".form-error");
  box.textContent = message ?? "";
  box.hidden = !message;
}

function mmss(seconds) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function parseMmss(text) {
  const m = /^(\d{1,2}):([0-5]\d)$/.exec(text.trim());
  return m ? Number(m[1]) * 60 + Number(m[2]) : undefined;
}

const today = () => new Date().toISOString().slice(0, 10);

// Form values -> JSON body. Empty fields are left out so the API reports what is missing.
function formBody(form) {
  const body = {};
  for (const [key, raw] of new FormData(form)) {
    if (raw === "") continue;
    const input = form.elements[key];
    body[key] = input.type === "number" ? Number(raw) : raw;
  }
  return body;
}

// ---- page 1: coffee list ------------------------------------------------------------------

async function showList() {
  mount("tpl-list");
  document.title = "PHIN Dial-in";
  const [coffees, products] = await Promise.all([api("GET", "/coffees"), api("GET", "/products")]);

  document.getElementById("coffee-empty").hidden = coffees.length > 0;
  document.getElementById("coffee-list").replaceChildren(...coffees.map((c) =>
    el("li", { class: "card" },
      el("a", { href: `#/coffees/${c.id}` }, c.name),
      el("p", { class: "muted" }, `${c.origin} · ${c.days_off_roast} days since roasting`),
      el("p", { class: c.low_stock ? "stock-line low" : "stock-line" },
        `${c.low_stock ? "⚠ " : ""}${c.grams_left} g left · about ${c.brews_left} brews`),
      c.low_stock && c.shop_url ? el("a", { href: c.shop_url, target: "_blank", rel: "noopener" }, "Reorder on phinkafi.ch") : "",
    )));

  const form = document.getElementById("coffee-form");
  const select = document.getElementById("product-select");
  select.replaceChildren(
    ...products.map((p) => el("option", { value: p.id }, p.name)),
    el("option", { value: "" }, "Other…"),
  );
  form.roast_date.max = today();

  // Choosing a PHIN coffee prefills the bag size; "Other…" shows the extra fields.
  const sync = () => {
    const product = products.find((p) => p.id === select.value);
    document.getElementById("other-fields").hidden = Boolean(product);
    form.bag_size_g.value = product ? product.bag_size_g : "";
  };
  select.addEventListener("change", sync);
  sync();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = formBody(form);
    if (body.product_id) for (const k of ["name", "origin", "roast_level"]) delete body[k];
    try {
      const coffee = await api("POST", "/coffees", body);
      location.hash = `#/coffees/${coffee.id}`;
    } catch (err) {
      showError(form, err.message);
    }
  });
}

// ---- page 2: coffee detail ----------------------------------------------------------------

let currentMethod = "phin";

async function showDetail(id, method = currentMethod) {
  currentMethod = method;
  const [coffee, brews, recipes] = await Promise.all([
    api("GET", `/coffees/${id}`),
    api("GET", `/coffees/${id}/brews?method=${method}`),
    api("GET", `/coffees/${id}/recipes`),
  ]);
  mount("tpl-detail");
  const m = METHODS[method];

  document.title = `${coffee.name} · PHIN Dial-in`;
  document.getElementById("coffee-name").textContent = coffee.name;
  document.getElementById("coffee-meta").textContent =
    `${coffee.origin} · roasted ${coffee.roast_date} · ${coffee.days_off_roast} days since roasting`;

  // Stock and low-stock warning (R6, R7)
  document.getElementById("stock-text").textContent = `${coffee.grams_left} g left · about ${coffee.brews_left} brews`;
  const low = document.getElementById("low-stock");
  if (coffee.low_stock) {
    low.hidden = false;
    low.append(`⚠ Running low: about ${coffee.brews_left} brews left. `);
    if (coffee.shop_url) low.append(el("a", { href: coffee.shop_url, target: "_blank", rel: "noopener" }, "Reorder on phinkafi.ch"));
  }
  setupBagDialog(coffee);

  // Tabs
  for (const tab of app.querySelectorAll("[data-method]")) {
    tab.setAttribute("aria-selected", tab.dataset.method === method);
    tab.addEventListener("click", () => showDetail(id, tab.dataset.method));
  }

  // Recipe card
  const recipe = recipes.find((r) => r.method === method);
  const card = document.getElementById("recipe");
  card.classList.toggle("empty-recipe", !recipe);
  card.replaceChildren(
    el("h2", {}, `${m.label} recipe`),
    el("p", {}, recipe ? m.recipe(recipe.brew) : `No ${m.label} recipe yet. Save a brew that tastes balanced to keep it here.`),
  );

  // Brew form: fields for this method, prefilled from the last brew
  document.getElementById("targets").textContent = m.targets;
  const last = brews.at(-1);
  document.getElementById("method-fields").replaceChildren(...m.fields.map((f) =>
    el("label", {}, f.label,
      el("input", { name: f.name, type: f.type, step: f.step, placeholder: f.placeholder, maxlength: f.type === "text" ? 20 : null }),
      el("span", { class: "hint" }, f.hint))));
  const form = document.getElementById("brew-form");
  if (last) {
    form.dose_g.value = last.dose_g;
    form.grind_setting.value = last.grind_setting;
    if (method === "phin") form.water_temp_c.value = last.water_temp_c;
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = { method, ...formBody(form) };
    if (method === "phin") {
      body.drip_time_s = parseMmss(form.drip_time.value);
      delete body.drip_time;
      if (form.drip_time.value && body.drip_time_s === undefined) return showError(form, "Drip time: use m:ss, e.g. 4:30");
    }
    try {
      await api("POST", `/coffees/${id}/brews`, body);
      showDetail(id, method);
    } catch (err) {
      showError(form, err.message); // typed values stay in the form
    }
  });

  // Advice for the latest brew
  if (last) {
    document.getElementById("advice").hidden = false;
    document.getElementById("advice-text").textContent = last.advice.message;
  }

  renderLog(id, method, brews, recipe);
}

function renderLog(coffeeId, method, brews, recipe) {
  const m = METHODS[method];
  const table = document.getElementById("log");
  const empty = document.getElementById("log-empty");
  table.hidden = brews.length === 0;
  empty.hidden = brews.length > 0;
  empty.textContent = method === "phin"
    ? "No brews yet. Start with PHIN's guide: 18 g · 130 ml · 93 °C · 4–6 min."
    : "No shots yet. Start with 18 g in, 36 g out, 25–30 s.";

  table.tHead.replaceChildren(el("tr", {},
    ...["#", "Dose", ...m.columns, "Ratio", "Grind", "Taste", "Advice", ""].map((h) => el("th", {}, h))));
  table.tBodies[0].replaceChildren(...brews.map((b, i) => {
    const actions = el("td", { class: "actions" });
    if (recipe?.brew.id === b.id) actions.append(el("strong", {}, "✓ Recipe"));
    else if (b.taste === "balanced") {
      actions.append(el("button", { type: "button", onclick: () => saveRecipe(coffeeId, method, b.id) }, "Save as recipe"));
    }
    actions.append(el("button", { type: "button", class: "secondary", "aria-label": `Delete brew ${i + 1}`,
      onclick: () => deleteBrew(coffeeId, method, b) }, "Delete"));
    return el("tr", { class: recipe?.brew.id === b.id ? "is-recipe" : null },
      el("td", {}, String(i + 1)),
      el("td", {}, `${b.dose_g} g`),
      ...m.cells(b).map((c) => el("td", {}, c)),
      el("td", {}, `1:${b.ratio.toFixed(1)}`),
      el("td", {}, b.grind_setting),
      el("td", {}, el("span", { class: `taste ${b.taste}` }, b.taste)),
      el("td", { class: "muted" }, b.advice.message),
      actions);
  }));
}

function setupBagDialog(coffee) {
  const dialog = document.getElementById("bag-dialog");
  const form = document.getElementById("bag-form");
  const sum = () => {
    const add = Number(form.bag_size_g.value) || 0;
    document.getElementById("bag-sum").textContent =
      `${coffee.grams_left} g left + ${add} g → ${Math.round((coffee.grams_left + add) * 10) / 10} g left`;
  };
  document.getElementById("new-bag-btn").addEventListener("click", () => {
    form.bag_size_g.value = coffee.bag_size_g;
    form.roast_date.value = today();
    form.roast_date.max = today();
    showError(form, null);
    sum();
    dialog.showModal();
  });
  form.bag_size_g.addEventListener("input", sum);
  document.getElementById("bag-cancel").addEventListener("click", () => dialog.close());
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const bag = Number(form.bag_size_g.value);
    try {
      // New bag = PUT the coffee with more grams and the new roast date.
      await api("PUT", `/coffees/${coffee.id}`, {
        name: coffee.name, origin: coffee.origin, roast_level: coffee.roast_level,
        roast_date: form.roast_date.value, bag_size_g: bag,
        grams_left: Math.round((coffee.grams_left + bag) * 10) / 10,
      });
      dialog.close();
      showDetail(coffee.id);
    } catch (err) {
      showError(form, err.message);
    }
  });
}

async function saveRecipe(coffeeId, method, brewId) {
  try {
    await api("PUT", `/coffees/${coffeeId}/recipes/${method}`, { brew_id: brewId });
  } catch (err) {
    alert(err.message);
  }
  showDetail(coffeeId, method);
}

async function deleteBrew(coffeeId, method, brew) {
  if (!confirm(`Delete this brew? ${brew.dose_g} g are returned to stock.`)) return;
  try {
    await api("DELETE", `/brews/${brew.id}`);
  } catch (err) {
    alert(err.message);
  }
  showDetail(coffeeId, method);
}

// ---- routing --------------------------------------------------------------------------------

async function route() {
  const match = location.hash.match(/^#\/coffees\/(\d+)$/);
  try {
    if (match) await showDetail(Number(match[1]));
    else await showList();
  } catch (err) {
    // e.g. 404 "Coffee 999 was not found."
    app.replaceChildren(
      el("h1", {}, "We couldn't find this coffee."),
      el("p", {}, err.message),
      el("p", {}, el("a", { href: "#/" }, "← Back to your coffees")));
  }
}

window.addEventListener("hashchange", () => { currentMethod = "phin"; route(); });
route();
