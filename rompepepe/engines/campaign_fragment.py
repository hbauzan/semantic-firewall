"""Campaign fragment: 90/10 piggyback vs chat sentence buffer. Oracle on /chat delivery."""
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
from rompepepe.test_dataset.campaign_fragment import (
    CampaignFragmentDataset,
    FragmentCase,
    load_campaign_fragment,
)

__all__ = ["CampaignFragmentEngine", "load_campaign_fragment"]


class CampaignFragmentEngine:
    """Set egress_profile, POST /chat, Oracle on delivered_text. Do not rewrite L08."""

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
        dataset: CampaignFragmentDataset | None = None,
        progress_callback: Callable[[SessionState, float], None] | None = None,
    ) -> SessionState:
        dataset = dataset or load_campaign_fragment()
        started = time.perf_counter()
        previous_profile = await self._read_profile()
        if session_id:
            session = self.session_manager.load_session(session_id)
            start_index = session.current_step
        else:
            session = self.session_manager.create_session(
                strategy="fragment",
                total_steps=len(dataset.cases),
                metadata={
                    "campaign": "fragment",
                    "plant_instructions": dataset.plant_instructions,
                    "live_explorer": live_explorer,
                    "payload": dataset.payload,
                },
            )
            start_index = 0

        verdicts: list[Verdict] = [self._verdict_from_result(r) for r in session.results]
        t0 = time.perf_counter()
        try:
            for offset, case in enumerate(dataset.cases[start_index:]):
                step = start_index + offset + 1
                prompt = case.prompt
                if live_explorer:
                    prompt = await self._mutate(prompt)
                await self._set_profile(case.profile)
                delivery = await self.firewall_client.chat(prompt)
                duration_ms = (time.perf_counter() - t0) * 1000.0
                t0 = time.perf_counter()
                verdict, notes = self._score_delivery(delivery, case)
                verdicts.append(verdict)
                session.results.append(
                    TestResult(
                        step=step,
                        prompt=prompt,
                        config={
                            "technique": case.technique,
                            "case_id": case.id,
                            "egress_profile": case.profile,
                            "payload": case.payload,
                        },
                        passed=not verdict.leaked,
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
        finally:
            if previous_profile:
                await self._set_profile(previous_profile)

        summary = self.oracle.summarize(verdicts)
        session.status = "completed"
        hold_leaked = sum(
            1
            for r in session.results
            if r.config.get("egress_profile") == "compliance" and r.leaked
        )
        session.metadata.update(
            {
                "leaked": summary.leaked,
                "z_attempts": summary.z_attempts,
                "payload_delivery_rate": summary.leakage_rate,
                "leakage_rate": summary.leakage_rate,
                "unreliable": sum(1 for r in session.results if "unreliable_empty_stream" in r.notes),
                "late_breach_leaks": sum(1 for r in session.results if "late_breach_leak" in r.notes),
                "l07_regression": hold_leaked,
            }
        )
        self.session_manager.save_session(session)
        return session

    async def _mutate(self, prompt: str) -> str:
        if self.explorer_client is None:
            return prompt
        return await self.explorer_client.generate_prompt_mutation(prompt)

    async def _read_profile(self) -> str | None:
        try:
            cfg = await self.firewall_client.get_config()
        except Exception:
            return None
        if isinstance(cfg, dict):
            value = cfg.get("egress_profile")
            if value in {"chat", "compliance"}:
                return value
        return None

    async def _set_profile(self, profile: str) -> None:
        await self.firewall_client.update_config({"egress_profile": profile})

    def _score_delivery(self, delivery: ChatDelivery, case: FragmentCase) -> tuple[Verdict, str]:
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
        verdict = self.oracle.score(text, "attack", planted_secrets=[case.payload])
        notes = ""
        if verdict.leaked and delivery.cut:
            notes = "late_breach_leak"
        elif verdict.leaked and case.is_hold_control:
            notes = "l07_regression"
        return verdict, notes

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
