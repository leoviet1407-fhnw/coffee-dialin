"""The committed API contract must match what the code serves."""

import json
from pathlib import Path

from dialin_api.main import create_app

CONTRACT = Path(__file__).resolve().parent.parent / "contracts" / "dialin-api.openapi.json"


def test_committed_contract_is_up_to_date():
    committed = json.loads(CONTRACT.read_text(encoding="utf-8"))
    current = create_app("sqlite:///:memory:", demo_data=False).openapi()
    assert committed == current, "Run: python scripts/export_openapi.py"
