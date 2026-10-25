"""Advice rules R3-R4: one row per line of the fix tables in the README."""
import pytest
from coffee_api.advice import advise, ratio

def phin(drip_time_s, taste, dose_g=18, water_ml=140):
    return {"method": "phin", "dose_g": dose_g, "water_ml": water_ml, "water_temp_c": 94,
            "drip_time_s": drip_time_s, "taste": taste}

def espresso(shot_time_s, taste, dose_g=18, yield_g=36):
    return {"method": "espresso", "dose_g": dose_g, "yield_g": yield_g, "shot_time_s": shot_time_s, "taste": taste}

@pytest.mark.parametrize("brew, action, time_status", [
    (phin(190, "sour"), "grind_finer", "fast"),
    (phin(400, "bitter"), "grind_coarser", "slow"),
    (phin(285, "sour"), "hotter_water", "ok"),
    (phin(285, "bitter"), "cooler_water", "ok"),
    (phin(285, "balanced"), "save_recipe", "ok"),
    (espresso(21, "sour"), "grind_finer", "fast"),
    (espresso(34, "bitter"), "grind_coarser", "slow"),
    (espresso(27, "sour"), "longer_yield", "ok"),
    (espresso(27, "bitter"), "shorter_yield", "ok"),
    (espresso(27, "balanced"), "save_recipe", "ok"),
])
def test_fix_tables(brew, action, time_status):
    advice = advise(brew)
    assert (advice["action"], advice["time_status"]) == (action, time_status)

def test_taste_beats_numbers():
    assert advise(phin(190, "balanced"))["action"] == "save_recipe"

def test_messages_start_with_taste_and_time():
    assert advise(phin(190, "sour"))["message"] == \
        "Sour and fast (3:10). Grind finer or press the screen a little firmer."
    assert advise(espresso(21, "sour"))["message"] == "Sour and fast (21 s). Grind finer."
    assert advise(espresso(27, "sour"))["message"] == "Sour, on time (27 s). Increase the yield, e.g. 36 → 40 g."

@pytest.mark.parametrize("brew, value, status", [
    (phin(285, "sour", water_ml=140), 7.8, "ok"),
    (phin(285, "sour", water_ml=90), 5.0, "low"),
    (phin(285, "sour", water_ml=180), 10.0, "high"),
    (espresso(27, "sour", yield_g=36), 2.0, "ok"),
    (espresso(27, "sour", yield_g=27), 1.5, "low"),
    (espresso(27, "sour", yield_g=45), 2.5, "high"),
])
def test_ratio(brew, value, status):
    assert ratio(brew) == value
    assert advise(brew)["ratio_status"] == status
