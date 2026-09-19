"""Campaign S cases: on-corpus paraphrases vs thematic deviations. No verbatim chunks."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_JSON_PATH = Path(__file__).with_name("campaign_s.json")
_SEED_PATH = Path(__file__).with_name("seed_corpus.json")


@dataclass(frozen=True)
class SCase:
    id: str
    label: str
    technique: str
    prompt: str

    @property
    def expected_oracle(self) -> str:
        return "on_corpus" if self.label == "on_corpus" else "deviation"


@dataclass(frozen=True)
class CampaignSDataset:
    corpus: str
    cases: tuple[SCase, ...]

    @property
    def on_corpus(self) -> tuple[SCase, ...]:
        return tuple(c for c in self.cases if c.label == "on_corpus")

    @property
    def deviations(self) -> tuple[SCase, ...]:
        return tuple(c for c in self.cases if c.label == "deviation")


def load_campaign_s() -> CampaignSDataset:
    with _JSON_PATH.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    cases = tuple(
        SCase(
            id=str(row["id"]),
            label=str(row["label"]),
            technique=str(row["technique"]),
            prompt=str(row["prompt"]),
        )
        for row in raw["cases"]
    )
    return CampaignSDataset(corpus=str(raw["corpus"]), cases=cases)


def seed_positive_queries() -> tuple[str, ...]:
    with _SEED_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return tuple(str(q) for q in data.get("positive_queries", []))
