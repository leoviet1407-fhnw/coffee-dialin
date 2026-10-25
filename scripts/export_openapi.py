"""Write the OpenAPI contract: python scripts/export_openapi.py (run after every API change)."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from coffee_api.api import create_app  # noqa: E402

CONTRACT = ROOT / "contracts" / "coffee-dialin.openapi.json"

def main():
    with tempfile.TemporaryDirectory() as folder:
        document = create_app(Path(folder) / "data.json").openapi()
    text = json.dumps(document, indent=2, ensure_ascii=False)
    if "HTTPValidationError" in text:
        sys.exit("The contract still references HTTPValidationError; 422s must use Error.")
    CONTRACT.parent.mkdir(exist_ok=True)
    CONTRACT.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {CONTRACT.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
