"""Strategy B: Closed-Loop Adaptive Exploration (Evolutionary Fuzzing Engine).

Synthesizes and mutates prompts in real-time based on firewall telemetry feedback to locate exact semantic boundaries.
"""
import asyncio
from datetime import datetime
import logging
import time
from typing import Any, Callable

from rompepepe.client.explorer_client import ExplorerClient, TokenQuotaExhaustedError
from rompepepe.client.firewall_client import FirewallClient
from rompepepe.state.models import BoundaryTrace, SessionState, TestResult, TelemetryTrace
from rompepepe.state.session_manager import SessionManager
from rompepepe.test_dataset import load_seed_corpus

logger = logging.getLogger(__name__)


class AdaptiveFuzzingEngine:
    def __init__(
        self,
        firewall_client: FirewallClient,
        explorer_client: ExplorerClient,
        session_manager: SessionManager,
    ):
        self.firewall_client = firewall_client
        self.explorer_client = explorer_client
        self.session_manager = session_manager

    async def estimate_preflight(self, iterations: int) -> dict[str, Any]:
        # Latency sampling: 1 firewall audit + 1 explorer prompt synthesis
        t0 = time.perf_counter()
        try:
            await self.firewall_client.audit("Sample test query")
            fw_latency = time.perf_counter() - t0
        except Exception:
            fw_latency = 0.05

        t0 = time.perf_counter()
        try:
            await self.explorer_client.generate_prompt_mutation("Sample test query")
            exp_latency = time.perf_counter() - t0
        except Exception:
            exp_latency = 0.5

        total_per_step = fw_latency + exp_latency
        total_seconds = total_per_step * iterations

        return {
            "iterations": iterations,
            "avg_fw_latency_sec": fw_latency,
            "avg_explorer_latency_sec": exp_latency,
            "total_per_step_sec": total_per_step,
            "estimated_seconds": total_seconds,
            "formatted_eta": f"~{int(total_seconds // 60)}m {int(total_seconds % 60)}s",
        }

    async def run(
        self,
        iterations: int = 50,
        seed_prompts: list[str] | None = None,
        session_id: str | None = None,
        progress_callback: Callable[[SessionState, float], None] | None = None,
    ) -> SessionState:
        # Load corpus references via API if available
        corpus_references = []
        try:
            packs = await self.firewall_client.get_packs()
            for pack in packs:
                if isinstance(pack, dict) and "filename" in pack:
                    corpus_references.append(str(pack["filename"]))
        except Exception as e:
            logger.warning(f"Could not fetch corpus packs: {e}")

        # Default seeds adapted dynamically to LanceDB packs
        if not seed_prompts:
            from rompepepe.test_dataset import build_adapted_corpus
            seed_prompts = await build_adapted_corpus(self.firewall_client)

        if session_id:
            session = self.session_manager.load_session(session_id)
            session.status = "running"
        else:
            try:
                initial_config = await self.firewall_client.get_config()
            except Exception:
                initial_config = {}

            session = self.session_manager.create_session(
                strategy="adaptive_fuzzing",
                total_steps=iterations,
                initial_target_config=initial_config,
            )

        start_time = time.time()
        start_step = session.current_step

        current_prompt = seed_prompts[start_step % len(seed_prompts)]
        last_telemetry: dict[str, Any] | None = None
        previous_result: TestResult | None = None

        if session.results:
            previous_result = session.results[-1]
            last_telemetry = previous_result.telemetry.model_dump()

        for step in range(start_step + 1, iterations + 1):
            t0 = time.perf_counter()

            # 1. Synthesize / mutate prompt via Explorer LLM with quota retry & backoff
            if step > 1 and last_telemetry:
                mutated_prompt = None
                max_quota_retries = 3
                for attempt in range(1, max_quota_retries + 1):
                    try:
                        mutated_prompt = await self.explorer_client.generate_prompt_mutation(
                            base_prompt=current_prompt,
                            telemetry_feedback=last_telemetry,
                            corpus_references=corpus_references,
                        )
                        break
                    except TokenQuotaExhaustedError as q_err:
                        if attempt < max_quota_retries:
                            wait_sec = attempt * 3.0
                            logger.warning(f"[Quota Limit Attempt {attempt}/{max_quota_retries}] Retrying in {wait_sec}s...")
                            await asyncio.sleep(wait_sec)
                        else:
                            logger.error(f"[!] Token quota limit exhausted after {max_quota_retries} attempts: {q_err}")
                            session.status = "paused"
                            session.metadata["quota_exhausted"] = True
                            session.metadata["pause_reason"] = (
                                f"Token quota / rate limit exhausted for explorer provider '{self.explorer_client.provider}' "
                                f"(Model: '{self.explorer_client.model}') after {max_quota_retries} retries."
                            )
                            self.session_manager.save_session(session)
                            print(f"\n\n[!] Execution paused due to token quota exhaustion at step {session.current_step}/{session.total_steps}.")
                            print(f"[+] Session state cleanly saved. You can resume anytime from the menu.")
                            return session
                if not mutated_prompt:
                    mutated_prompt = current_prompt
            else:
                mutated_prompt = current_prompt

            # 2. Audit mutated prompt against Firewall REST API
            telemetry = None
            duration_ms = 0.0
            for retry in range(3):
                try:
                    current_config = await self.firewall_client.get_config()
                    telemetry = await self.firewall_client.audit(mutated_prompt)
                    duration_ms = (time.perf_counter() - t0) * 1000.0
                    break
                except Exception as e:
                    duration_ms = (time.perf_counter() - t0) * 1000.0
                    if "429" in str(e) and retry < 2:
                        await asyncio.sleep(1.0 * (retry + 1))
                    else:
                        telemetry = TelemetryTrace(passed=False, breach_reason=f"HTTP Error: {e}", text="HTTP Error")

            result = TestResult(
                step=step,
                prompt=mutated_prompt,
                config=current_config if 'current_config' in locals() else {},
                passed=telemetry.passed if telemetry else False,
                breach_reason=telemetry.breach_reason if telemetry else "Error",
                telemetry=telemetry or TelemetryTrace(passed=False, breach_reason="HTTP Error"),
                duration_ms=duration_ms,
            )

            # 3. Detect Boundary Transition Point
            if previous_result and (previous_result.passed != result.passed):
                result.is_boundary_transition = True
                boundary = BoundaryTrace(
                    step_a=previous_result.step,
                    step_b=result.step,
                    prompt_a=previous_result.prompt,
                    prompt_b=result.prompt,
                    passed_a=previous_result.passed,
                    passed_b=result.passed,
                    cosine_a=previous_result.telemetry.cosine_delta,
                    cosine_b=result.telemetry.cosine_delta,
                    mutation_description=(
                        f"State flip: {previous_result.passed} -> {result.passed} "
                        f"(Reason: {result.breach_reason})"
                    ),
                    timestamp=datetime.now().isoformat(),
                )
                session.boundary_traces.append(boundary)

            session.results.append(result)
            session.current_step = step

            # Save state & prepare next loop
            last_telemetry = result.telemetry.model_dump()
            previous_result = result
            current_prompt = mutated_prompt

            if step % 5 == 0 or step == iterations:
                self.session_manager.save_session(session)

            if progress_callback:
                elapsed = time.time() - start_time
                progress_callback(session, elapsed)

        session.status = "completed"
        self.session_manager.save_session(session)
        return session
