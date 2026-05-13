import json
from pathlib import Path


def load_travel_request(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Request file not found: {file_path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)