"""Semantic Firewall Engine — pure vector math, zero framework dependencies.

This module is completely agnostic of FastAPI, embedders, and storage layers.
It receives numpy arrays and a frozen ConfigState, returns structured results.
Portable across CLI tools, test harnesses, or alternative API wrappers.
"""
import logging
import re
from typing import Any
import numpy as np

logger = logging.getLogger(__name__)

from app.core.models import ConfigState


class SemanticFirewall:
    """Stateless firewall engine. All methods are static — no instance state."""

    # --- Segmentation ---

    @staticmethod
    def segment(text: str) -> list[str]:
        """Language-agnostic structural segmentation with overflow chunking.

        1. Split on universal punctuation (no language-specific words).
        2. Discard fragments <= 4 chars.
        3. Force-split any clause > 20 words into 15-word sub-chunks.
        """
        raw = [c.strip() for c in re.split(r'[.!?;:\n\-\|«»\u201c\u201d]+', text) if len(c.strip()) > 4]
        if not raw:
            raw = [text]

        clauses: list[str] = []
        for rc in raw:
            words = rc.split()
            if len(words) > 20:
                for i in range(0, len(words), 15):
                    sub = " ".join(words[i:i + 15])
                    if len(sub.strip()) > 4:
                        clauses.append(sub.strip())
            else:
                clauses.append(rc)

        return clauses if clauses else [text]

    # --- Individual Filters ---
    # Each returns: (passed: bool, stage_name: str, details: dict)

    @staticmethod
    def run_noise_filter(
        q_arr: np.ndarray, c_arr: np.ndarray, cfg: ConfigState, **_kw: Any
    ) -> tuple[bool, str, dict]:
        """Global delta sanity check across all dimensions."""
        avg_delta = float(np.mean(np.abs(q_arr - c_arr)))
        if avg_delta > cfg.global_noise_limit:
            return False, "noise", {"avg_delta": avg_delta, "limit": cfg.global_noise_limit}
        return True, "noise", {"avg_delta": avg_delta}

    @staticmethod
    def run_cosine_filter(
        q_arr: np.ndarray, c_arr: np.ndarray, cfg: ConfigState, **_kw: Any
    ) -> tuple[bool, str, dict]:
        """Cosine similarity gate using raw vectors."""
        q_norm = np.linalg.norm(q_arr)
        c_norm = np.linalg.norm(c_arr)
        if q_norm == 0 or c_norm == 0:
            logger.warning("Zero-norm vector in cosine filter (q_norm=%.4f, c_norm=%.4f)", q_norm, c_norm)
            return False, "cosine", {"cosine_sim": 0.0, "error": "zero_norm"}
        raw = np.dot(q_arr, c_arr) / (q_norm * c_norm)
        sim = float(np.clip(raw, -1.0, 1.0))
        if sim < cfg.cosine_threshold:
            return False, "cosine", {"cosine_sim": sim}
        return True, "cosine", {"cosine_sim": sim}

    @staticmethod
    def run_excitation_filter(
        q_arr: np.ndarray, c_arr: np.ndarray, cfg: ConfigState, word_count: int = 0, **_kw: Any
    ) -> tuple[bool, str, dict]:
        """Dimensional resonance count with adaptive threshold for short clauses."""
        delta = np.abs(q_arr - c_arr)
        activations = int(np.sum(delta <= cfg.noise_tolerance))
        is_short = word_count < 6
        factor = cfg.adaptive_factor if is_short else 1.0
        threshold = float(cfg.excitation_threshold) * factor
        passed = activations >= threshold
        return passed, "excitation", {
            "activations": activations,
            "threshold": threshold,
            "adaptive_applied": is_short,
            "adaptive_factor": factor,
        }

    # --- Pipeline Engine ---

    @staticmethod
    def build_pipeline(cfg: ConfigState) -> list[tuple[int, str, callable]]:
        """Build ordered list of (priority, name, function) sorted by config order.
        Disabled filters are excluded from the pipeline."""
        stages = []
        if cfg.cosine_enabled:
            stages.append((cfg.cosine_order, "cosine", SemanticFirewall.run_cosine_filter))
        if cfg.excitation_enabled:
            stages.append((cfg.excitation_order, "excitation", SemanticFirewall.run_excitation_filter))
        if cfg.noise_enabled:
            stages.append((cfg.noise_order, "noise", SemanticFirewall.run_noise_filter))
        return sorted(stages, key=lambda x: x[0])

    @staticmethod
    def evaluate_clause(
        q_arr: np.ndarray,
        c_arr: np.ndarray,
        cfg: ConfigState,
        word_count: int = 0,
    ) -> dict:
        """Run the full ordered pipeline on a single clause's vectors.

        Returns:
            {
                "passed": bool,
                "breach_reason": str | None,
                "breach_details": dict | None,
                "trace": [{"stage": str, "passed": bool, ...}, ...],
                "last_activations": int,
                "last_cosine": float,
            }
        """
        pipeline = SemanticFirewall.build_pipeline(cfg)
        trace: list[dict] = []
        last_activations = 0
        last_cosine = 0.0

        for _order, stage_name, stage_fn in pipeline:
            passed, _name, details = stage_fn(
                q_arr, c_arr, cfg, word_count=word_count
            )
            trace.append({"stage": stage_name, "passed": passed, **details})

            if passed:
                if "activations" in details:
                    last_activations = details["activations"]
                if "cosine_sim" in details:
                    last_cosine = details["cosine_sim"]
            else:
                return {
                    "passed": False,
                    "breach_reason": stage_name,
                    "breach_details": details,
                    "trace": trace,
                    "last_activations": last_activations,
                    "last_cosine": last_cosine,
                }

        return {
            "passed": True,
            "breach_reason": None,
            "breach_details": None,
            "trace": trace,
            "last_activations": last_activations,
            "last_cosine": last_cosine,
        }
