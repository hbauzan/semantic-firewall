"""L12 — fragment / piggyback vs chat buffer. Payload in delivered_text is leakage."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from rompepepe.client.chat_ndjson import ChatDelivery, parse_chat_ndjson
from rompepepe.engines.campaign_fragment import CampaignFragmentEngine, load_campaign_fragment
from rompepepe.oracle import Oracle
from rompepepe.reports.generator import ReportGenerator
from rompepepe.state.models import SessionState
from rompepepe.state.session_manager import SessionManager

EGRESS_CUT = "[FIREWALL_AUDIT]\n[FW_BLOCK]\n[CONNECTION_TERMINATED]\n"
TECH = "Apriete de bujía 25 Nm en tapa de cilindros."


def test_dataset_covers_pdf_splits_and_hold_control():
    dataset = load_campaign_fragment()
    techniques = {c.technique for c in dataset.cases}
    assert techniques >= {"hybrid_90_10", "split_semicolon", "split_newline", "continuation", "hold_control"}
    assert dataset.chat_cases
    assert dataset.hold_controls
    assert all(c.profile == "chat" for c in dataset.chat_cases)
    assert all(c.profile == "compliance" for c in dataset.hold_controls)
    assert all(dataset.payload in c.prompt for c in dataset.cases)
    assert ";" in next(c.prompt for c in dataset.cases if c.technique == "split_semicolon")
    assert "\n" in next(c.prompt for c in dataset.cases if c.technique == "split_newline")
    assert "de paso" in next(c.prompt for c in dataset.cases if c.technique == "continuation")


def test_late_cut_after_payload_is_leakage_not_a_win():
    pan = load_campaign_fragment().payload
    raw = "".join(
        json.dumps({"response": chunk}) + "\n"
        for chunk in (
            "[FIREWALL_AUDIT]\n[FW_PASS]\n[LLM_RESPONSE]:\n\n",
            f"{TECH} {pan}.",
            EGRESS_CUT,
        )
    )
    delivery = parse_chat_ndjson(raw)
    assert delivery.cut is True
    assert pan in delivery.delivered_text
    verdict = Oracle().score(delivery.delivered_text, "attack", planted_secrets=[pan])
    assert verdict.leaked is True


@pytest.mark.asyncio
async def test_engine_chat_cut_before_payload_is_zero_delivery(tmp_path: Path):
    dataset = load_campaign_fragment()
    profiles: list[str] = []

    async def chat(_prompt: str) -> ChatDelivery:
        return ChatDelivery(delivered_text=TECH, cut=True, unreliable=False)

    async def update(cfg: dict) -> dict:
        profiles.append(cfg["egress_profile"])
        return cfg

    fw = MagicMock()
    fw.chat = AsyncMock(side_effect=chat)
    fw.update_config = AsyncMock(side_effect=update)
    fw.get_config = AsyncMock(return_value={"egress_profile": "chat"})
    fw.base_url = "http://firewall.test"
    session = await CampaignFragmentEngine(fw, SessionManager(tmp_path)).run()
    assert session.strategy == "fragment"
    assert "chat" in profiles
    assert "compliance" in profiles
    assert session.metadata["payload_delivery_rate"] == 0.0
    assert session.metadata["l07_regression"] == 0
    content = ReportGenerator(tmp_path / "reports").generate_report(session).read_text()
    assert "Egress leakage" in content
    assert "operational stability" not in content.split("## Auxiliary")[0].lower()


@pytest.mark.asyncio
async def test_engine_payload_then_cut_counts_as_leak(tmp_path: Path):
    dataset = load_campaign_fragment()
    pan = dataset.payload

    async def chat(prompt: str) -> ChatDelivery:
        case = next(c for c in dataset.cases if c.prompt == prompt)
        if case.is_hold_control:
            return ChatDelivery(delivered_text="", cut=True, unreliable=False)
        return ChatDelivery(delivered_text=f"{TECH} {pan}", cut=True, unreliable=False)

    fw = MagicMock()
    fw.chat = AsyncMock(side_effect=chat)
    fw.update_config = AsyncMock(return_value={})
    fw.get_config = AsyncMock(return_value={"egress_profile": "chat"})
    session = await CampaignFragmentEngine(fw, SessionManager(tmp_path)).run()
    chat_rows = [r for r in session.results if r.config["egress_profile"] == "chat"]
    hold_rows = [r for r in session.results if r.config["egress_profile"] == "compliance"]
    assert all(r.leaked for r in chat_rows)
    assert all("late_breach_leak" in r.notes for r in chat_rows)
    assert all(r.leaked is False for r in hold_rows)
    assert session.metadata["payload_delivery_rate"] == len(chat_rows) / len(session.results)
    assert session.metadata["l07_regression"] == 0


@pytest.mark.asyncio
async def test_compliance_control_delivering_payload_is_l07_regression(tmp_path: Path):
    dataset = load_campaign_fragment()
    pan = dataset.payload
    hold = dataset.hold_controls[0]
    tiny = type(dataset)(
        payload=dataset.payload,
        plant_instructions=dataset.plant_instructions,
        cases=(hold,),
    )

    async def chat(_prompt: str) -> ChatDelivery:
        return ChatDelivery(delivered_text=f"hold leaked {pan}", cut=False, unreliable=False)

    fw = MagicMock()
    fw.chat = AsyncMock(side_effect=chat)
    fw.update_config = AsyncMock(return_value={})
    fw.get_config = AsyncMock(return_value={"egress_profile": "chat"})
    session = await CampaignFragmentEngine(fw, SessionManager(tmp_path)).run(dataset=tiny)
    assert session.results[0].notes == "l07_regression"
    assert session.metadata["l07_regression"] == 1
    assert session.metadata["payload_delivery_rate"] == 1.0


@pytest.mark.asyncio
async def test_empty_stream_is_not_a_zero_payload_win(tmp_path: Path):
    dataset = load_campaign_fragment()
    case = dataset.chat_cases[0]
    tiny = type(dataset)(
        payload=dataset.payload,
        plant_instructions=dataset.plant_instructions,
        cases=(case,),
    )
    fw = MagicMock()
    fw.chat = AsyncMock(return_value=ChatDelivery(delivered_text="", cut=False, unreliable=True))
    fw.update_config = AsyncMock(return_value={})
    fw.get_config = AsyncMock(return_value={"egress_profile": "chat"})
    session = await CampaignFragmentEngine(fw, SessionManager(tmp_path)).run(dataset=tiny)
    assert session.metadata["unreliable"] == 1
    assert session.metadata["payload_delivery_rate"] == 1.0


def test_session_state_accepts_fragment():
    session = SessionState(
        session_id="f1",
        strategy="fragment",
        status="completed",
        created_at="2026-09-18T00:00:00",
        updated_at="2026-09-18T00:00:01",
    )
    assert session.strategy == "fragment"


def test_campaign_fragment_does_not_rewrite_sentence_buffer():
    engine = (Path(__file__).resolve().parents[1] / "engines" / "campaign_fragment.py").read_text()
    assert "evaluate_clause" not in engine
    assert "sentence_buffer" not in engine
