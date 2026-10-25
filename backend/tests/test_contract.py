"""The committed contract must match the running API (re-export with scripts/export_openapi.py)."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from coffee_api.api import create_app

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "coffee-dialin.openapi.json"

def test_contract_is_in_sync(tmp_path):
    served = TestClient(create_app(tmp_path / "data.json")).get("/openapi.json").json()
    assert served == json.loads(CONTRACT.read_text(encoding="utf-8"))

def test_errors_use_error_model():
    assert "HTTPValidationError" not in CONTRACT.read_text(encoding="utf-8")
