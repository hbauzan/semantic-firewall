"""Campaign Z: force the target to emit planted secrets; Oracle scores /chat delivery."""
from __future__ import annotations

import time
from collections.abc import Callable

from rompepepe.client.chat_ndjson import ChatDelivery
from rompepepe.client.explorer_client import ExplorerClient
from rompepepe.client.firewall_client import FirewallClient
from rompepepe.oracle import Oracle
from rompepepe.oracle.metrics import Verdict
from rompepepe.state.models import SessionState, TelemetryTrace, TestResult
from rompepepe.state.session_manager import SessionManager
from rompepepe.test_dataset.campaign_z import CampaignZDataset, ZAttack, load_campaign_z

__all__ = ["CampaignZEngine", "load_campaign_z"]


class CampaignZEngine:
    """Explorer → POST /chat → Oracle on delivered_text. Default set is frozen (no live LLM)."""

    def __init__(
        self,
        firewall_client: FirewallClient,
        session_manager: SessionManager,
        explorer_client: ExplorerClient | None = None,
        oracle: Oracle | None = None,
    ):
        self.firewall_client = firewall_client
        self.session_manager = session_manager
        self.explorer_client = explorer_client
        self.oracle = oracle or Oracle()

    async def run(
        self,
        *,
        live_explorer: bool = False,
        session_id: str | None = None,
        dataset: CampaignZDataset | None = None,
        progress_callback: Callable[[SessionState, float], None] | None = None,
    ) -> SessionState:
        dataset = dataset or load_campaign_z()
        started = time.perf_counter()
        if session_id:
            session = self.session_manager.load_session(session_id)
            start_index = session.current_step
        else:
            session = self.session_manager.create_session(
                strategy="z_exfil",
                total_steps=len(dataset.attacks),
                metadata={
                    "campaign": "Z",
                    "plant_instructions": dataset.plant_instructions,
                    "live_explorer": live_explorer,
                },
            )
            start_index = 0

        verdicts: list[Verdict] = [self._verdict_from_result(r) for r in session.results]
        t0 = time.perf_counter()
        for offset, attack in enumerate(dataset.attacks[start_index:]):
            step = start_index + offset + 1
            prompt = attack.prompt
            if live_explorer:
                prompt = await self._mutate(prompt)
            delivery = await self.firewall_client.chat(prompt)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            t0 = time.perf_counter()
            verdict, notes = self._score_delivery(delivery, attack)
            verdicts.append(verdict)
            session.results.append(
                TestResult(
                    step=step,
                    prompt=prompt,
                    config={"technique": attack.technique, "attack_id": attack.id},
                    passed=not verdict.leaked and verdict.blocked,
                    breach_reason="EGRESS_CUT" if delivery.cut else None,
                    telemetry=TelemetryTrace(
                        passed=not delivery.cut,
                        text=verdict.delivered_text,
                    ),
                    duration_ms=duration_ms,
                    expected_label="attack",
                    delivered_text=verdict.delivered_text,
                    attack_success=verdict.attack_success,
                    leaked=verdict.leaked,
                    notes=notes,
                )
            )
            session.current_step = step
            self.session_manager.save_session(session)
            if progress_callback:
                progress_callback(session, time.perf_counter() - started)

        summary = self.oracle.summarize(verdicts)
        session.status = "completed"
        session.metadata.update(
            {
                "leaked": summary.leaked,
                "z_attempts": summary.z_attempts,
                "leakage_rate": summary.leakage_rate,
                "recall_block": summary.recall_block,
                "unreliable": sum(1 for r in session.results if "unreliable_empty_stream" in r.notes),
            }
        )
        self.session_manager.save_session(session)
        return session

    async def _mutate(self, prompt: str) -> str:
        if self.explorer_client is None:
            return prompt
        return await self.explorer_client.generate_prompt_mutation(prompt)

    def _score_delivery(self, delivery: ChatDelivery, attack: ZAttack) -> tuple[Verdict, str]:
        if delivery.unreliable:
            return (
                Verdict(
                    expected_label="attack",
                    delivered_text="",
                    blocked=False,
                    leaked=True,
                    leaked_secrets=(),
                    attack_success=True,
                    z_attempt=True,
                ),
                "unreliable_empty_stream",
            )
        text = delivery.delivered_text
        if delivery.cut and not text.strip():
            text = ""
        return self.oracle.score(text, "attack", planted_secrets=attack.planted_secrets), ""

    @staticmethod
    def _verdict_from_result(row: TestResult) -> Verdict:
        return Verdict(
            expected_label="attack",
            delivered_text=row.delivered_text or "",
            blocked=bool(row.breach_reason) and not row.leaked and not row.delivered_text,
            leaked=bool(row.leaked),
            leaked_secrets=(),
            attack_success=bool(row.attack_success),
            z_attempt=True,
        )
