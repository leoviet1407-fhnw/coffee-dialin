"""The brewing rules (README R3/R4) on their own, without HTTP or a database."""

import pytest

from dialin_api.advice import espresso_advice, mmss, phin_advice


@pytest.mark.parametrize(
    ("taste", "shot_time_s", "action"),
    [
        ("sour", 20, "grind_finer"),
        ("sour", 28, "longer_yield"),
        ("bitter", 35, "grind_coarser"),
        ("bitter", 28, "shorter_yield"),
        ("balanced", 28, "keep"),
        ("balanced", 40, "keep"),  # taste beats numbers
    ],
)
def test_espresso_actions(taste, shot_time_s, action):
    assert espresso_advice(18, 36, shot_time_s, taste)["action"] == action


@pytest.mark.parametrize(("shot_time_s", "expected"), [(24, "fast"), (25, "ok"), (30, "ok"), (31, "slow")])
def test_espresso_time_window_is_25_to_30_seconds(shot_time_s, expected):
    assert espresso_advice(18, 36, shot_time_s, "balanced")["time_status"] == expected


@pytest.mark.parametrize(("yield_g", "expected"), [(31, "low"), (32.4, "ok"), (39.6, "ok"), (40, "high")])
def test_espresso_ratio_window_is_1_8_to_2_2(yield_g, expected):
    assert espresso_advice(18, yield_g, 28, "balanced")["ratio_status"] == expected


@pytest.mark.parametrize(
    ("taste", "temp", "drip_time_s", "action"),
    [
        ("sour", 94, 190, "grind_finer"),
        ("bitter", 94, 400, "grind_coarser"),
        ("sour", 92, 290, "hotter_water"),
        ("sour", 96, 290, "more_coffee"),
        ("bitter", 94, 290, "cooler_water"),
        ("bitter", 90, 290, "less_coffee"),
        ("balanced", 93, 290, "keep"),
    ],
)
def test_phin_actions(taste, temp, drip_time_s, action):
    assert phin_advice(18, 130, temp, drip_time_s, taste)["action"] == action


def test_phin_ratio_and_time_status():
    result = phin_advice(18, 130, 93, 290, "balanced")
    assert result["ratio"] == 7.22
    assert result["ratio_status"] == "ok"
    assert result["time_status"] == "ok"
    assert phin_advice(18, 160, 93, 380, "balanced")["ratio_status"] == "high"


def test_messages_explain_the_reason():
    assert "3:10" in phin_advice(18, 140, 94, 190, "sour")["message"]
    assert "about 40 g" in espresso_advice(18, 36, 28, "sour")["message"]
    assert "about 18 g" in espresso_advice(18, 20, 28, "bitter")["message"]  # never below the dose


def test_mmss():
    assert mmss(190) == "3:10"
    assert mmss(65) == "1:05"
