"""Dial-in advice (README rules R3 and R4).

Pure functions: numbers and taste in, one suggestion out. No HTTP and no
database here, so the brewing rules can be read and tested on their own.

Both methods follow the same three rules:
  1. Change one thing at a time.
  2. Time decides the lever: when the time is off, change the grind first.
  3. Taste decides the direction: sour -> extract more, bitter -> extract less.
"""

ESPRESSO_TIME_S = (25, 30)  # shot time window
ESPRESSO_RATIO = (1.8, 2.2)  # yield ÷ dose, target 1:2
PHIN_TIME_S = (240, 360)  # 4-6 minutes from main pour to last drop
PHIN_RATIO = (6.0, 8.0)  # water ÷ coffee, target about 1:7
PHIN_MAX_TEMP_C, PHIN_COOL_TEMP_C = 96, 90


def status(value: float, low: float, high: float, words=("low", "ok", "high")) -> str:
    if value < low:
        return words[0]
    if value > high:
        return words[2]
    return words[1]


def mmss(seconds: int) -> str:
    return f"{seconds // 60}:{seconds % 60:02d}"


def espresso_advice(dose_g: float, yield_g: float, shot_time_s: int, taste: str) -> dict:
    ratio = round(yield_g / dose_g, 2)
    timing = status(shot_time_s, *ESPRESSO_TIME_S, words=("fast", "ok", "slow"))
    ratio_status = status(ratio, *ESPRESSO_RATIO)

    if taste == "balanced":
        action, message = "keep", "Balanced. Save this shot as your espresso recipe."
        if timing != "ok" or ratio_status != "ok":
            message = "Tastes balanced. Trust your taste and save it, even if the numbers are a little off."
    elif taste == "sour" and timing == "fast":
        action, message = "grind_finer", f"Sour and fast ({shot_time_s} s). Grind finer to slow the shot down."
    elif taste == "bitter" and timing == "slow":
        action, message = "grind_coarser", f"Bitter and slow ({shot_time_s} s). Grind coarser to speed the shot up."
    elif taste == "sour":
        target = round(yield_g + 4)
        action, message = "longer_yield", f"Sour but not fast. Pull a longer shot: about {target} g in the cup."
    else:  # bitter, not slow
        target = max(round(yield_g - 4), round(dose_g))
        action, message = "shorter_yield", f"Bitter but not slow. Stop the shot earlier: about {target} g in the cup."

    return {"ratio": ratio, "action": action, "message": message, "time_status": timing, "ratio_status": ratio_status}


def phin_advice(dose_g: float, water_ml: float, water_temp_c: float, drip_time_s: int, taste: str) -> dict:
    ratio = round(water_ml / dose_g, 2)
    timing = status(drip_time_s, *PHIN_TIME_S, words=("fast", "ok", "slow"))
    ratio_status = status(ratio, *PHIN_RATIO)
    t = mmss(drip_time_s)

    if taste == "balanced":
        action, message = "keep", "Balanced. Save this brew as your Phin recipe."
        if timing != "ok" or ratio_status != "ok":
            message = "Tastes balanced. Trust your taste and save it, even if the numbers are a little off."
    elif taste == "sour" and timing == "fast":
        action, message = "grind_finer", f"Sour and fast ({t}). Grind finer or press the screen a little firmer."
    elif taste == "bitter" and timing == "slow":
        action, message = "grind_coarser", f"Bitter and slow ({t}). Grind coarser or press more lightly."
    elif taste == "sour":
        if water_temp_c < PHIN_MAX_TEMP_C:
            action, message = "hotter_water", f"Sour but on time. Use hotter water: about {PHIN_MAX_TEMP_C} °C."
        else:
            action, message = "more_coffee", f"Sour but on time and hot. Use a little more coffee: about {round(dose_g + 1)} g."
    else:  # bitter, not slow
        if water_temp_c > PHIN_COOL_TEMP_C:
            action, message = "cooler_water", f"Bitter but not slow. Use cooler water: about {PHIN_COOL_TEMP_C} °C."
        else:
            action, message = "less_coffee", f"Bitter but not slow. Use a little less coffee: about {round(dose_g - 1)} g."

    return {"ratio": ratio, "action": action, "message": message, "time_status": timing, "ratio_status": ratio_status}
