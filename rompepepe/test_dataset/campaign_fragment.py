"""Campaign fragment / piggyback cases vs the chat sentence buffer."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_JSON_PATH = Path(__file__).with_name("campaign_fragment.json")

EgressProfile = Literal["chat", "compliance"]


@dataclass(frozen=True)
class FragmentCase:
    id: str
    technique: str
    profile: EgressProfile
    prompt: str
    payload: str

    @property
    def is_hold_control(self) -> bool:
        return self.profile == "compliance"


@dataclass(frozen=True)
class CampaignFragmentDataset:
    payload: str
    plant_instructions: str
    cases: tuple[FragmentCase, ...]

    @property
    def chat_cases(self) -> tuple[FragmentCase, ...]:
        return tuple(c for c in self.cases if c.profile == "chat")

    @property
    def hold_controls(self) -> tuple[FragmentCase, ...]:
        return tuple(c for c in self.cases if c.is_hold_control)


def load_campaign_fragment() -> CampaignFragmentDataset:
    with _JSON_PATH.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    payload = str(raw["payload"]["pan"])
    cases = tuple(
        FragmentCase(
            id=str(row["id"]),
            technique=str(row["technique"]),
            profile=row["profile"],
            prompt=str(row["prompt"]).format(pan=payload),
            payload=payload,
        )
        for row in raw["cases"]
    )
    return CampaignFragmentDataset(
        payload=payload,
        plant_instructions=str(raw["plant_instructions"]),
        cases=cases,
    )
