"""Test dataset package for rompepepe with auto-adaptation to active LanceDB corpus packs.
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_seed_corpus() -> dict[str, Any]:
    json_path = Path(__file__).parent / "seed_corpus.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


async def build_adapted_corpus(firewall_client: Any) -> list[str]:
    """Dynamically fetches active packs from LanceDB via REST API (/corpus/packs)
    and constructs a domain-aware test query dataset.
    """
    seed_data = load_seed_corpus()
    queries = (
        seed_data.get("positive_queries", [])
        + seed_data.get("negative_queries", [])
        + seed_data.get("boundary_blended_queries", [])
        + seed_data.get("edge_case_queries", [])
    )

    try:
        packs = await firewall_client.get_packs()
        if not packs:
            logger.info("No active corpus packs found in LanceDB via API. Using static seed corpus.")
            return queries

        pack_names = [p.get("filename", "") for p in packs if isinstance(p, dict)]
        logger.info(f"Detected {len(pack_names)} active corpus pack(s) in LanceDB: {pack_names}")

        # Check if backend has calibration datasets available
        backend_dir = Path(__file__).resolve().parents[2] / "backend" / "calibration" / "datasets"
        dynamic_queries = []

        if backend_dir.exists():
            for dataset_file in backend_dir.glob("*.json"):
                try:
                    with open(dataset_file, "r", encoding="utf-8") as f:
                        ds_data = json.load(f)
                    c_file = ds_data.get("corpus_file", "")
                    if any(p in c_file or c_file in p for p in pack_names):
                        for q_item in ds_data.get("queries", []):
                            txt = q_item.get("text")
                            if txt:
                                dynamic_queries.append(txt)
                except Exception as e:
                    logger.warning(f"Could not load calibration dataset {dataset_file}: {e}")

        if dynamic_queries:
            logger.info(f"Loaded {len(dynamic_queries)} domain-matched queries from LanceDB corpus calibration datasets.")
            return dynamic_queries + queries[:10]  # Combine domain-matched with boundary distractor queries

    except Exception as e:
        logger.warning(f"Could not adapt dataset to LanceDB packs via API: {e}")

    return queries
