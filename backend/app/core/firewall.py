"""Semantic Firewall Engine — pure vector math, zero framework dependencies.

This module is completely agnostic of FastAPI, embedders, and storage layers.
It receives numpy arrays and a frozen ConfigState, returns structured results.
Portable across CLI tools, test harnesses, or alternative API wrappers.
"""
import logging
import math
import re
from collections.abc import Mapping
from typing import Any, Callable, TypedDict
import numpy as np

logger = logging.getLogger(__name__)

from app.core.models import ConfigState
from app.core.numerical import format_float


class ClauseResult(TypedDict):
    """Typed return value for SemanticFirewall.evaluate_clause().
    Ensures type-safety for all consumers (routes, tests, CLI tools)."""
    passed: bool
    breach_reason: str | None
    breach_details: dict | None
    trace: list[dict]
    last_activations: int
    last_cosine: float


def _cosine_reading(sim: float) -> dict[str, float]:
    """Similarity and angular distance, both native floats."""
    similarity = float(sim)
    return {"cosine_sim": similarity, "cosine_distance": float(1.0 - similarity)}


def _breach_reason(
    stage_name: str,
    details: dict,
    negative: bool,
    *,
    raw_passed: bool = True,
) -> str:
    if details.get("error") == "zero_norm":
        reason = "zero_norm"
    elif stage_name == "excitation" and not raw_passed:
        reason = "excitation_mass"
    else:
        reason = stage_name
    if negative:
        return f"negative:{reason}"
    return reason


_SHORT_QUERY_WORDS = 6


# Lightweight POS proxy — no external NLP dependency.
_CONTENT_WORD_RE = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ]{4,}$")
_VERB_SUFFIX_RE = re.compile(r"(ar|er|ir|ed|ing|ión|mente)$", re.IGNORECASE)


class SemanticFirewall:
    """Stateless firewall engine. All methods are static — no instance state."""

    # --- Early CPU discard (Phase 1) ---

    @staticmethod
    def calculate_raw_entropy(text: str) -> float:
        """Shannon entropy over raw character frequency (no normalization)."""
        if not text:
            return 0.0
        counts: dict[str, int] = {}
        for ch in text:
            counts[ch] = counts.get(ch, 0) + 1
        length = len(text)
        entropy = 0.0
        for count in counts.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    # --- Syntactic metrics (Phase 4.1) ---

    @staticmethod
    def query_length(text: str) -> int:
        """Token count L(q) — whitespace-split words."""
        stripped = text.strip()
        if not stripped:
            return 0
        return len(stripped.split())

    @staticmethod
    def lexical_density(text: str) -> float:
        """Proportion of content-bearing tokens (nouns/verbs proxy) over total words."""
        words = [w for w in text.split() if w]
        if not words:
            return 0.0
        content = 0
        for word in words:
            bare = re.sub(r"[^\wÁÉÍÓÚáéíóúÑñ]", "", word)
            if _CONTENT_WORD_RE.match(bare) or _VERB_SUFFIX_RE.search(bare):
                content += 1
        return content / len(words)

    # --- Dynamic mixing (Phase 4.2) ---

    @staticmethod
    def compute_alpha(text: str) -> float:
        """Sigmoid blend weight α(q) — favors dense similarity for complex queries.

        Uses syntactic proxy (L(q), Lex_d(q)) instead of a local perplexity model.
        """
        length = SemanticFirewall.query_length(text)
        density = SemanticFirewall.lexical_density(text)
        x = 0.45 * min(length / 20.0, 1.0) + 0.55 * density - 0.35
        return 1.0 / (1.0 + math.exp(-6.0 * x))

    @staticmethod
    def compute_epsilon(text: str, base_tolerance: float) -> float:
        """Exponential contraction of sparse excitation tolerance ε(q).

        Perplexity P(q) is approximated via length + lexical density proxy.
        """
        length = SemanticFirewall.query_length(text)
        density = SemanticFirewall.lexical_density(text)
        complexity = 0.5 * min(length / 20.0, 1.0) + 0.5 * density
        return base_tolerance * math.exp(-2.0 * complexity)

    @staticmethod
    def sparse_cosine_similarity(
        q_sparse: Mapping[int, float] | None,
        c_sparse: Mapping[int, float] | None,
    ) -> float:
        """Dot-product cosine over the union of sparse lexical keys."""
        if not q_sparse or not c_sparse:
            return 0.0
        common = set(q_sparse.keys()) & set(c_sparse.keys())
        if not common:
            return 0.0
        dot = sum(q_sparse[k] * c_sparse[k] for k in common)
        q_norm = math.sqrt(sum(v * v for v in q_sparse.values()))
        c_norm = math.sqrt(sum(v * v for v in c_sparse.values()))
        if q_norm == 0.0 or c_norm == 0.0:
            return 0.0
        return float(np.clip(dot / (q_norm * c_norm), -1.0, 1.0))

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
        """Burst Detection: Shannon Entropy of the Query Vector (Corpus-Independent)."""
        abs_q = np.abs(q_arr)
        p = abs_q / (np.sum(abs_q) + 1e-9)
        entropy = float(-np.sum(p * np.log2(p + 1e-9)))

        if entropy < cfg.global_noise_limit:
            return False, "noise", {"entropy": entropy, "limit": cfg.global_noise_limit}
        return True, "noise", {"entropy": entropy, "limit": cfg.global_noise_limit}

    @staticmethod
    def run_cosine_filter(
        q_arr: np.ndarray,
        c_arr: np.ndarray,
        cfg: ConfigState,
        hybrid_score: float | None = None,
        **_kw: Any,
    ) -> tuple[bool, str, dict]:
        """Cosine similarity gate using raw vectors or a precomputed hybrid score.

        Pass when cos(Q, C) >= tau_cos. Details carry cosine_distance = 1 - cos.
        A zero norm breaches before any downstream head runs.
        """
        if hybrid_score is not None:
            sim = float(np.clip(hybrid_score, -1.0, 1.0))
        else:
            query = np.asarray(q_arr, dtype=np.float64).ravel()
            corpus = np.asarray(c_arr, dtype=np.float64).ravel()
            q_norm = float(np.sqrt(np.dot(query, query)))
            c_norm = float(np.sqrt(np.dot(corpus, corpus)))
            if q_norm == 0.0 or c_norm == 0.0:
                logger.warning(
                    "Zero-norm vector in cosine filter (q_norm=%s, c_norm=%s)",
                    format_float(q_norm),
                    format_float(c_norm),
                )
                return False, "cosine", {**_cosine_reading(0.0), "error": "zero_norm"}
            raw = float(np.dot(query, corpus) / (q_norm * c_norm))
            sim = float(np.clip(raw, -1.0, 1.0))
        reading = _cosine_reading(sim)
        if sim < cfg.cosine_threshold:
            return False, "cosine", reading
        return True, "cosine", reading

    @staticmethod
    def run_excitation_filter(
        q_arr: np.ndarray,
        c_arr: np.ndarray,
        cfg: ConfigState,
        word_count: int = 0,
        epsilon_tolerance: float | None = None,
        **_kw: Any,
    ) -> tuple[bool, str, dict]:
        """Count coordinates inside the coarse delta tolerance.

        Short clauses (L(q) < 6) shrink ε by exp(-(6-L)/6). The mass threshold
        stays τ_coarse. A miss returns the caller to breach_reason excitation_mass.
        """
        base = float(epsilon_tolerance) if epsilon_tolerance is not None else float(cfg.noise_tolerance)
        tolerance = SemanticFirewall.coarse_epsilon(base, word_count)
        query = np.asarray(q_arr, dtype=np.float32).ravel()
        corpus = np.asarray(c_arr, dtype=np.float32).ravel()
        delta = np.abs(query - corpus)
        active = delta <= np.float32(tolerance)
        activations = int(np.count_nonzero(active))
        threshold = float(cfg.excitation_threshold)
        passed = activations >= threshold
        ratio = tolerance / base if base > 0.0 else 1.0
        return passed, "excitation", {
            "activations": activations,
            "threshold": threshold,
            "adaptive_applied": word_count < _SHORT_QUERY_WORDS,
            "adaptive_factor": float(ratio),
            "epsilon_tolerance": float(tolerance),
        }

    @staticmethod
    def coarse_epsilon(base_tolerance: float, word_count: int) -> float:
        """ε for a clause. Full tolerance at L(q) >= 6; exponential decay below."""
        base = float(base_tolerance)
        if word_count >= _SHORT_QUERY_WORDS:
            return base
        deficit = (_SHORT_QUERY_WORDS - word_count) / _SHORT_QUERY_WORDS
        return base * math.exp(-deficit)

    @staticmethod
    def run_sparse_short_circuit(
        q_sparse: Mapping[int, float] | None,
        c_sparse: Mapping[int, float] | None,
        cfg: ConfigState,
        query_text: str = "",
    ) -> tuple[bool, str, dict]:
        """Short-circuit: block immediately if sparse component alone fails threshold."""
        sim_sparse = SemanticFirewall.sparse_cosine_similarity(q_sparse, c_sparse)
        epsilon = SemanticFirewall.compute_epsilon(query_text, cfg.noise_tolerance)
        sparse_threshold = cfg.cosine_threshold * (1.0 - min(epsilon, 0.99))
        passed = sim_sparse >= sparse_threshold
        return passed, "sparse", {
            "sparse_sim": sim_sparse,
            "sparse_threshold": sparse_threshold,
            "epsilon": epsilon,
        }

    # --- Pipeline Engine ---

    @staticmethod
    def build_pipeline(cfg: ConfigState) -> list[tuple[int, str, "Callable"]]:
        """Build ordered list of (priority, name, function) sorted by config order."""
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
        *,
        query_text: str = "",
        q_sparse: Mapping[int, float] | None = None,
        c_sparse: Mapping[int, float] | None = None,
    ) -> ClauseResult:
        """Run the full ordered pipeline on a single clause's vectors.

        Hybrid scoring (Phase 4.3):
          Score = α(q)·Sim_dense + (1-α(q))·Sim_sparse
        Sparse short-circuit runs before the ordered pipeline when sparse vectors exist.
        """
        pipeline = SemanticFirewall.build_pipeline(cfg)
        trace: list[dict] = []
        last_activations = 0
        last_cosine = 0.0
        negative = cfg.firewall_mode == "negative"

        # Dense cosine for hybrid blend
        q_norm = np.linalg.norm(q_arr)
        c_norm = np.linalg.norm(c_arr)
        if q_norm == 0 or c_norm == 0:
            sim_dense = 0.0
        else:
            sim_dense = float(np.clip(np.dot(q_arr, c_arr) / (q_norm * c_norm), -1.0, 1.0))

        sim_sparse = SemanticFirewall.sparse_cosine_similarity(q_sparse, c_sparse)
        alpha_q = SemanticFirewall.compute_alpha(query_text) if query_text else 1.0
        if q_sparse is not None and c_sparse is not None:
            hybrid_score = alpha_q * sim_dense + (1.0 - alpha_q) * sim_sparse
        else:
            hybrid_score = None

        # Sparse short-circuit (Phase 4.3)
        if q_sparse is not None and c_sparse is not None:
            raw_passed, stage_name, details = SemanticFirewall.run_sparse_short_circuit(
                q_sparse, c_sparse, cfg, query_text=query_text,
            )
            effective_passed = raw_passed if not negative else not raw_passed
            trace.append({
                "stage": stage_name,
                "passed": effective_passed,
                "alpha": alpha_q,
                **details,
            })
            if not effective_passed:
                breach_reason = f"negative:{stage_name}" if negative else stage_name
                logger.info(
                    "SHORT_CIRCUIT layer=%s alpha=%s",
                    stage_name,
                    format_float(alpha_q),
                )
                return {
                    "passed": False,
                    "breach_reason": breach_reason,
                    "breach_details": details,
                    "trace": trace,
                    "last_activations": last_activations,
                    "last_cosine": last_cosine,
                }

        first_breach_reason = None
        first_breach_details = None

        for _order, stage_name, stage_fn in pipeline:
            extra: dict[str, Any] = {"word_count": word_count}
            if stage_name == "cosine" and hybrid_score is not None:
                extra["hybrid_score"] = hybrid_score

            raw_passed, _name, details = stage_fn(q_arr, c_arr, cfg, **extra)

            if negative and stage_name != "noise":
                effective_passed = not raw_passed
            else:
                effective_passed = raw_passed

            stage_trace = {"stage": stage_name, "passed": effective_passed, **details}
            if hybrid_score is not None and stage_name == "cosine":
                stage_trace["alpha"] = alpha_q
                stage_trace["sim_dense"] = sim_dense
                stage_trace["sim_sparse"] = sim_sparse
                stage_trace["hybrid_score"] = hybrid_score

            trace.append(stage_trace)

            if "activations" in details:
                last_activations = details["activations"]
            if "cosine_sim" in details:
                last_cosine = details["cosine_sim"]

            if not effective_passed:
                breach_reason = _breach_reason(
                    stage_name, details, negative, raw_passed=raw_passed
                )
                logger.info("SHORT_CIRCUIT layer=%s", breach_reason)
                return {
                    "passed": False,
                    "breach_reason": breach_reason,
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
