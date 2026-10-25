"""Pure rules: ratio, time and ratio status, one piece of advice per brew (R3-R4). No I/O, no FastAPI."""

# (fast below, slow above) for time; (low below, high above) for ratio. README "Brewing rules".
TIME_TARGETS = {"phin": (240, 360), "espresso": (25, 30)}
RATIO_TARGETS = {"phin": (6, 8), "espresso": (1.8, 2.2)}

def brew_time(brew: dict) -> int:
    return brew["drip_time_s"] if brew["method"] == "phin" else brew["shot_time_s"]

def format_time(brew: dict) -> str:
    seconds = brew_time(brew)
    return f"{seconds // 60}:{seconds % 60:02d}" if brew["method"] == "phin" else f"{seconds} s"

def ratio(brew: dict) -> float:
    out = brew["water_ml"] if brew["method"] == "phin" else brew["yield_g"]
    return round(out / brew["dose_g"], 1)

def time_status(brew: dict) -> str:
    fast, slow = TIME_TARGETS[brew["method"]]
    seconds = brew_time(brew)
    return "fast" if seconds < fast else "slow" if seconds > slow else "ok"

def ratio_status(brew: dict) -> str:
    low, high = RATIO_TARGETS[brew["method"]]
    value = ratio(brew)
    return "low" if value < low else "high" if value > high else "ok"

def advise(brew: dict) -> dict:
    """Taste beats numbers; time chooses the lever; taste chooses the direction."""
    method, taste, time = brew["method"], brew["taste"], time_status(brew)
    phin = method == "phin"
    if taste == "balanced":
        action, fix = "save_recipe", "Save this brew as your recipe."
    elif time == "fast":
        action, fix = "grind_finer", "Grind finer or press the screen a little firmer." if phin else "Grind finer."
    elif time == "slow":
        action, fix = "grind_coarser", "Grind coarser or press more lightly." if phin else "Grind coarser."
    elif taste == "sour":
        if phin:
            action, fix = "hotter_water", "Try hotter water, up to 96 °C, or a little more coffee."
        else:
            action, fix = "longer_yield", f"Increase the yield, e.g. {brew['yield_g']:g} → {brew['yield_g'] + 4:g} g."
    elif phin:
        action, fix = "cooler_water", "Try cooler water, around 90 °C, or a little less coffee."
    else:
        action, fix = "shorter_yield", f"Shorten the yield, e.g. {brew['yield_g']:g} → {brew['yield_g'] - 4:g} g."
    speed = {"fast": "fast", "slow": "slow", "ok": "on time"}[time]
    joiner = ", " if time == "ok" else " and "
    message = f"{taste.capitalize()}{joiner}{speed} ({format_time(brew)}). {fix}"
    return {"action": action, "time_status": time, "ratio_status": ratio_status(brew), "message": message}
