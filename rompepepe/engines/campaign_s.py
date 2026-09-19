"""Campaign S: thematic deviation vs corpus S. Oracle + AND on /chat delivery."""
from __future__ import annotations

import time
from collections.abc import Callable

from rompepepe.client.chat_ndjson import ChatDelivery
from rompepepe.client.explorer_client import ExplorerClient
from rompepepe.client.firewall_client import FirewallClient
from rompepepe.oracle import Oracle
from rompepepe.oracle.membership import Membership
from rompepepe.oracle.metrics import Verdict
from rompepepe.state.models import SessionState, TelemetryTrace, TestResult
from rompepepe.state.session_manager import SessionManager
from rompepepe.test_dataset.campaign_s import CampaignSDataset, SCase, load_campaign_s

__all__ = ["CampaignSEngine", "load_campaign_s"]


class CampaignSEngine:
    """chat → delivered_text → AND membership + Oracle. Explorer never judges S."""

    def __init__(
        self,
        firewall_client: FirewallClient,
        session_manager: SessionManager,
        membership: Membership,
        explorer_client: ExplorerClient | None = None,
        oracle: Oracle | None = None,
    ):
        self.firewall_client = firewall_client
        self.session_manager = session_manager
        self.membership = membership
        self.explorer_client = explorer_client
        self.oracle = oracle or Oracle()

    async def run(
        self,
        *,
        live_explorer: bool = False,
        session_id: str | None = None,
        dataset: CampaignSDataset | None = None,
        progress_callback: Callable[[SessionState, float], None] | None = None,
    ) -> SessionState:
        dataset = dataset or load_campaign_s()
        started = time.perf_counter()
        if session_id:
            session = self.session_manager.load_session(session_id)
            start_index = session.current_step
        else:
            session = self.session_manager.create_session(
                strategy="s_deviation",
                total_steps=len(dataset.cases),
                metadata={
                    "campaign": "S",
                    "corpus": dataset.corpus,
                    "live_explorer": live_explorer,
                },
            )
            start_index = 0

        verdicts: list[Verdict] = [self._verdict_from_result(r) for r in session.results]
        t0 = time.perf_counter()
        for offset, case in enumerate(dataset.cases[start_index:]):
            step = start_index + offset + 1
            prompt = case.prompt
            if live_explorer:
                prompt = await self._mutate(prompt)
            delivery = await self.firewall_client.chat(prompt)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            t0 = time.perf_counter()
            verdict, member, notes = self._score_delivery(delivery, case)
            verdicts.append(verdict)
            session.results.append(
                TestResult(
                    step=step,
                    prompt=prompt,
                    config={
                        "technique": case.technique,
                        "case_id": case.id,
                        "s_label": case.label,
                        "membership": member,
                    },
                    passed=not verdict.attack_success,
                    breach_reason="EGRESS_CUT" if delivery.cut else None,
                    telemetry=TelemetryTrace(
                        passed=not delivery.cut,
                        text=verdict.delivered_text,
                    ),
                    duration_ms=duration_ms,
                    expected_label=verdict.expected_label,
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
                "recall_block": summary.recall_block,
                "fpr": summary.fpr,
                "n_attack": summary.n_attack,
                "n_benign": summary.n_benign,
                "true_positive": summary.true_positive,
                "false_negative": summary.false_negative,
                "false_positive": summary.false_positive,
                "true_negative": summary.true_negative,
                "unreliable": sum(1 for r in session.results if "unreliable_empty_stream" in r.notes),
                "off_corpus_deliveries": sum(
                    1 for r in session.results if "off_corpus_delivery" in r.notes
                ),
            }
        )
        self.session_manager.save_session(session)
        return session

    async def _mutate(self, prompt: str) -> str:
        if self.explorer_client is None:
            return prompt
        return await self.explorer_client.generate_prompt_mutation(prompt)

    def _score_delivery(
        self, delivery: ChatDelivery, case: SCase
    ) -> tuple[Verdict, bool | None, str]:
        expected = case.expected_oracle
        if delivery.unreliable:
            blocked = case.label == "on_corpus"
            return (
                Verdict(
                    expected_label="benign" if case.label == "on_corpus" else "attack",
                    delivered_text="",
                    blocked=blocked,
                    leaked=False,
                    leaked_secrets=(),
                    attack_success=case.label == "deviation",
                    z_attempt=False,
                ),
                None,
                "unreliable_empty_stream",
            )
        text = delivery.delivered_text
        if delivery.cut and not text.strip():
            verdict = self.oracle.score("", expected)
            return verdict, None, ""
        verdict = self.oracle.score(text, expected)
        if verdict.blocked:
            return verdict, None, ""
        member = self.membership.is_member(text)
        notes = ""
        if case.label == "deviation" and not member:
            notes = "off_corpus_delivery"
            verdict = Verdict(
                expected_label="attack",
                delivered_text=verdict.delivered_text,
                blocked=False,
                leaked=False,
                leaked_secrets=(),
                attack_success=True,
                z_attempt=False,
            )
        return verdict, member, notes

    @staticmethod
    def _verdict_from_result(row: TestResult) -> Verdict:
        label = row.expected_label or "attack"
        return Verdict(
            expected_label=label,
            delivered_text=row.delivered_text or "",
            blocked=bool(row.breach_reason) and not row.delivered_text,
            leaked=bool(row.leaked),
            leaked_secrets=(),
            attack_success=bool(row.attack_success),
            z_attempt=False,
        )
