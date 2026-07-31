"""Test dataset package for rompepepe."""
import json
from pathlib import Path

def load_seed_corpus() -> dict:
    json_path = Path(__file__).parent / "seed_corpus.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)
