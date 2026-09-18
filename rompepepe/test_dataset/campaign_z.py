"""Campaign Z planted secrets — synthetic only. Never real PANs or live keys.

How to plant on a live lab
--------------------------
The same strings live in `campaign_z.json`. Tests inject them into the mock
`/chat` body. Against a running firewall, put these values in the **target**
system prompt / fixture the model can recite (lab envelope, work order). Do
not put real card numbers or production API keys in this file or the backend.
"""
from __future__ import annotations

import base64
import codecs
import json
from dataclasses import dataclass
from pathlib import Path

_JSON_PATH = Path(__file__).with_name("campaign_z.json")


@dataclass(frozen=True)
class ZAttack:
    id: str
    technique: str
    prompt: str
    planted_secrets: tuple[str, ...]
    expected_label: str = "attack"


@dataclass(frozen=True)
class CampaignZDataset:
    pan: str
    api_key: str
    plant_instructions: str
    attacks: tuple[ZAttack, ...]


def _load_raw() -> dict:
    with _JSON_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


_RAW = _load_raw()
PLANTED_PAN = str(_RAW["secrets"]["pan"])
PLANTED_API_KEY = str(_RAW["secrets"]["api_key"])


def load_campaign_z() -> CampaignZDataset:
    secrets = {
        "pan": PLANTED_PAN,
        "api_key": PLANTED_API_KEY,
        "pan_b64": base64.b64encode(PLANTED_PAN.encode()).decode(),
        "pan_hex": PLANTED_PAN.encode().hex(),
        "api_key_rot13": codecs.encode(PLANTED_API_KEY, "rot_13"),
        "pan_spaced": " ".join(PLANTED_PAN),
    }
    attacks: list[ZAttack] = []
    for row in _RAW["attacks"]:
        planted = tuple(secrets[name] if name in secrets else str(name) for name in row["planted"])
        # Templates ask the model to emit the clear secret, not the encoding.
        clear = tuple(secrets[name] for name in row["planted"] if name in ("pan", "api_key"))
        prompt = str(row["prompt"]).format(**secrets)
        attacks.append(
            ZAttack(
                id=str(row["id"]),
                technique=str(row["technique"]),
                prompt=prompt,
                planted_secrets=clear or planted,
            )
        )
    return CampaignZDataset(
        pan=PLANTED_PAN,
        api_key=PLANTED_API_KEY,
        plant_instructions=str(_RAW["plant_instructions"]),
        attacks=tuple(attacks),
    )
