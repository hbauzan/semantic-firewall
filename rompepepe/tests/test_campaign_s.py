"""L11 — Campaign S: on-corpus paraphrases vs deviations. AND judges membership, not Explorer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from rompepepe.client.chat_ndjson import ChatDelivery
from rompepepe.engines.campaign_s import CampaignSEngine, load_campaign_s
from rompepepe.oracle import Oracle
from rompepepe.oracle.membership import AndMembership
from rompepepe.reports.generator import ReportGenerator
from rompepepe.state.models import SessionState
from rompepepe.state.session_manager import SessionManager
from rompepepe.test_dataset.campaign_s import seed_positive_queries

ON_CORPUS_ANSWER = "Gap de electrodo en iridio: consultar la ficha; apriete en tapa de cilindros sin pelar rosca."
RECIPE_ANSWER = "Bizcochuelo: 180 celsius, 40 minutos, cacao, huevos y manteca. Nada de bujías."
CUT = ChatDelivery(delivered_text="", cut=True, unreliable=False)
OK = ChatDelivery(delivered_text=ON_CORPUS_ANSWER, cut=False, unreliable=False)
RECIPE = ChatDelivery(delivered_text=RECIPE_ANSWER, cut=False, unreliable=False)
EMPTY = ChatDelivery(delivered_text="", cut=False, unreliable=True)


@dataclass
class MapMembership:
    on_markers: tuple[str, ...]
    off_markers: tuple[str, ...]

    def is_member(self, delivered_text: str) -> bool:
        text = delivered_text or ""
        if any(m in text for m in self.off_markers):
            return False
        return any(m in text for m in self.on_markers)


MEMBERSHIP = MapMembership(
    on_markers=("electrodo", "apriete", "tapa de cilindros"),
    off_markers=("Bizcochuelo", "cacao", "ley de coparticipación", "despertar espiritual"),
)


def test_oracle_accepts_on_corpus_and_deviation_labels():
    cut = "[FW_BLOCK]\n[CONNECTION_TERMINATED]\n"
    blocked_valid = Oracle().score(cut, "on_corpus")
    assert blocked_valid.expected_label == "benign"
    assert blocked_valid.blocked is True
    leaked_dev = Oracle().score(RECIPE_ANSWER, "deviation")
    assert leaked_dev.expected_label == "attack"
    assert leaked_dev.blocked is False
    assert leaked_dev.attack_success is True


def test_campaign_s_prompts_are_paraphrases_not_verbatim_chunks():
    dataset = load_campaign_s()
    assert dataset.on_corpus
    assert dataset.deviations
    techniques = {c.technique for c in dataset.deviations}
    assert {"recipe", "metaphor", "politics"} <= techniques
    verbatim = set(seed_positive_queries())
    for case in dataset.on_corpus:
        assert case.prompt not in verbatim
        assert case.label == "on_corpus"


def test_and_membership_delegates_to_evaluate_sentence_not_explorer():
    calls: list[str] = []

    @dataclass
    class _V:
        passed: bool

    def fake_and(text: str, pack_id: str, *, embed_fn, nodes=None, **_k):
        calls.append(text)
        assert pack_id == "lab-automotive"
        assert embed_fn("x") == "emb"
        assert nodes == [{"node_id": "t1"}]
        return _V(passed="apriete" in text)

    member = AndMembership(
        evaluate=fake_and,
        pack_id="lab-automotive",
        embed_fn=lambda _t: "emb",
        nodes=[{"node_id": "t1"}],
    )
    assert member.is_member(ON_CORPUS_ANSWER) is True
    assert member.is_member(RECIPE_ANSWER) is False
    assert calls == [ON_CORPUS_ANSWER, RECIPE_ANSWER]


@pytest.mark.asyncio
async def test_engine_recall_and_fpr_on_mixed_chat_mock(tmp_path: Path):
    dataset = load_campaign_s()
    by_id = {c.id: c for c in dataset.cases}

    async def chat(prompt: str) -> ChatDelivery:
        if prompt == by_id["para-iridium-gap"].prompt:
            return OK
        if prompt == by_id["para-spark-interval"].prompt:
            return CUT
        if prompt == by_id["dev-chocolate-recipe"].prompt:
            return RECIPE
        if prompt == by_id["dev-german-ignition"].prompt:
            return CUT
        if prompt == by_id["dev-politics"].prompt:
            return CUT
        if prompt == by_id["dev-spiritual-metaphor"].prompt:
            return CUT
        return OK

    fw = MagicMock()
    fw.chat = AsyncMock(side_effect=chat)
    fw.base_url = "http://firewall.test"
    explorer = MagicMock()
    explorer.generate_prompt_mutation = AsyncMock(side_effect=AssertionError("Explorer is not the S judge"))
    engine = CampaignSEngine(fw, SessionManager(tmp_path), MEMBERSHIP, explorer_client=explorer)
    session = await engine.run(live_explorer=False)
    assert session.strategy == "s_deviation"
    explorer.generate_prompt_mutation.assert_not_called()
    assert session.metadata["n_benign"] == len(dataset.on_corpus)
    assert session.metadata["n_attack"] == len(dataset.deviations)
    assert session.metadata["false_positive"] == 1
    assert session.metadata["false_negative"] == 1
    assert session.metadata["true_positive"] == len(dataset.deviations) - 1
    assert session.metadata["true_negative"] == len(dataset.on_corpus) - 1
    assert session.metadata["fpr"] == pytest.approx(1 / len(dataset.on_corpus))
    assert session.metadata["recall_block"] == pytest.approx(
        (len(dataset.deviations) - 1) / len(dataset.deviations)
    )
    recipe = next(r for r in session.results if r.config["case_id"] == "dev-chocolate-recipe")
    assert recipe.notes == "off_corpus_delivery"
    assert recipe.config["membership"] is False
    content = ReportGenerator(tmp_path / "reports").generate_report(session).read_text()
    assert "Recall de bloqueo" in content
    assert "False positive rate" in content
    assert "operational stability" not in content.split("## Auxiliary")[0].lower()


@pytest.mark.asyncio
async def test_membership_sees_delivered_text_not_the_prompt(tmp_path: Path):
    seen: list[str] = []

    class Capture:
        def is_member(self, delivered_text: str) -> bool:
            seen.append(delivered_text)
            return True

    async def chat(_prompt: str) -> ChatDelivery:
        return OK

    case = load_campaign_s().on_corpus[0]
    tiny = load_campaign_s()
    tiny = type(tiny)(corpus=tiny.corpus, cases=(case,))
    fw = MagicMock()
    fw.chat = AsyncMock(side_effect=chat)
    session = await CampaignSEngine(fw, SessionManager(tmp_path), Capture()).run(dataset=tiny)
    assert seen == [ON_CORPUS_ANSWER]
    assert session.results[0].delivered_text == ON_CORPUS_ANSWER


@pytest.mark.asyncio
async def test_empty_stream_on_corpus_is_not_a_true_negative(tmp_path: Path):
    case = load_campaign_s().on_corpus[0]
    tiny = load_campaign_s()
    tiny = type(tiny)(corpus=tiny.corpus, cases=(case,))
    fw = MagicMock()
    fw.chat = AsyncMock(return_value=EMPTY)
    session = await CampaignSEngine(fw, SessionManager(tmp_path), MEMBERSHIP).run(dataset=tiny)
    assert session.metadata["unreliable"] == 1
    assert session.metadata["false_positive"] == 1
    assert session.metadata["true_negative"] == 0


def test_session_state_accepts_s_deviation():
    session = SessionState(
        session_id="s1",
        strategy="s_deviation",
        status="completed",
        created_at="2026-09-18T00:00:00",
        updated_at="2026-09-18T00:00:01",
    )
    assert session.strategy == "s_deviation"


def test_campaign_s_does_not_import_evaluate_clause_or_prod_thresholds():
    engine_src = (Path(__file__).resolve().parents[1] / "engines" / "campaign_s.py").read_text()
    assert "evaluate_clause" not in engine_src
    assert "cosine_threshold" not in engine_src
    assert "excitation_threshold" not in engine_src
