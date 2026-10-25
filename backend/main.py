"""Wiring: build the app on a data file. Run from backend/: python -m uvicorn main:app --reload"""
import os
from pathlib import Path
from coffee_api.api import create_app

app = create_app(Path(os.environ.get("COFFEE_DATA_FILE", Path(__file__).with_name("data.json"))))
