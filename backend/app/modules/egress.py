"""Compliance egress hold: no generation tokens to the client until unanimous pass.

Layer order (PDF): normalize homoglyphs, then DLP, INLP seam, reconstructed
numbers, then L04 AND on sentences. Ingress Noise/Cosine/Excitation is unchanged.

Default ``egress_profile`` is ``chat`` (today's live yield). CDE must set
``compliance``. Missing pyramid / pack on AND is fail-closed. Missing INLP
artefact is a documented skip, not a guessed τ.
"""
from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

EgressLayer = Literal["dlp", "homoglyph", "inlp", "numbers", "and"]
AndFn = Callable[[str, str | None], bool]
InlpFn = Callable[[str], bool | None]

EGRESS_CUT_MESSAGE = "[FIREWALL_AUDIT]\n[FW_BLOCK]\n[CONNECTION_TERMINATED]\n"
DEFAULT_INLP_ARTIFACT = (
    Path(__file__).resolve().parent.parent.parent / "calibration" / "geometry" / "inlp_lab.npz"
)

_PAN_WINDOW = re.compile(r"\d{13,19}")
_PAN_CANDIDATE = re.compile(r"(?:\d[ \-]?){13,19}")
_API_KEY = re.compile(
    r"(?:sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,})"
)
_AND_OVERRIDE: AndFn | None = None
_INLP_OVERRIDE: InlpFn | None = None


@dataclass(frozen=True)
class EgressVerdict:
    passed: bool
    layer: EgressLayer | None
    reason: str


def set_egress_overrides(*, and_fn: AndFn | None = None, inlp_fn: InlpFn | None = None) -> None:
    """Test seam. Pass None to restore production callables."""
    global _AND_OVERRIDE, _INLP_OVERRIDE
    _AND_OVERRIDE = and_fn
    _INLP_OVERRIDE = inlp_fn


def normalize_homoglyphs(text: str) -> str:
    """NFKC so fullwidth / compatibility digits become ASCII before DLP."""
    return unicodedata.normalize("NFKC", text or "")


def reconstruct_digits(text: str) -> str:
    """Digit stream after homoglyph normalization (newlines and spaces drop)."""
    return re.sub(r"\D", "", normalize_homoglyphs(text))


def split_response_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?;])\s+|\n+", text or "") if p.strip()]
    return parts or ([text.strip()] if text and text.strip() else [])


def redact_for_log(text: str) -> str:
    """Replace secrets with hash8 + last4. Never persist the raw value."""
    if not text:
        return text
    redacted = normalize_homoglyphs(text)
    secrets = [*_find_luhn_pans(redacted), *_find_regex_secrets(redacted)]
    compact = reconstruct_digits(redacted)
    for match in _PAN_WINDOW.finditer(compact):
        candidate = match.group(0)
        if luhn_ok(candidate) and candidate not in secrets:
            secrets.append(candidate)
    for secret in secrets:
        redacted = redacted.replace(secret, _token(secret))
        squeezed = re.sub(r"[\s\-]", "", redacted)
        compact_secret = re.sub(r"[\s\-]", "", secret)
        if compact_secret and compact_secret in squeezed:
            redacted = re.sub(
                r"(?:\d[\s\-]?){" + str(len(compact_secret)) + r"}",
                _token(compact_secret),
                redacted,
                count=1,
            )
    return redacted


def audit_held_response(
    text: str,
    *,
    pack_id: str | None = None,
    and_fn: AndFn | None = None,
    inlp_fn: InlpFn | None = None,
) -> EgressVerdict:
    """Unanimous pass or first failing layer. ``text`` is the full generation."""
    normalized = normalize_homoglyphs(text)
    dlp_hit = _dlp_hits(normalized)
    if dlp_hit:
        return EgressVerdict(passed=False, layer="dlp", reason=f"dlp:{_token(dlp_hit)}")

    inlp_cut = _run_inlp(normalized, inlp_fn=inlp_fn)
    if inlp_cut is True:
        return EgressVerdict(passed=False, layer="inlp", reason="inlp_energy")

    number_hit = _luhn_in_digit_stream(reconstruct_digits(normalized))
    if number_hit:
        return EgressVerdict(passed=False, layer="numbers", reason=f"numbers:{_token(number_hit)}")

    and_fn = and_fn if and_fn is not None else _AND_OVERRIDE
    for sentence in split_response_sentences(normalized):
        if not _run_and(sentence, pack_id, and_fn):
            return EgressVerdict(passed=False, layer="and", reason="and_membership")
    return EgressVerdict(passed=True, layer=None, reason="unanimous")


def _dlp_hits(text: str) -> str | None:
    pans = _find_luhn_pans(text)
    if pans:
        return pans[0]
    keys = _find_regex_secrets(text)
    if keys:
        return keys[0]
    return None


def luhn_ok(digits: str) -> bool:
    if not digits.isdigit() or not (13 <= len(digits) <= 19):
        return False
    total = 0
    reverse = digits[::-1]
    for i, ch in enumerate(reverse):
        n = ord(ch) - 48
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _find_luhn_pans(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _PAN_CANDIDATE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if luhn_ok(digits) and digits not in seen:
            seen.add(digits)
            found.append(digits)
    return found


def _find_regex_secrets(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _API_KEY.finditer(text):
        token = match.group(0)
        if token not in seen:
            seen.add(token)
            found.append(token)
    return found


def _luhn_in_digit_stream(digits: str) -> str | None:
    for length in range(16, 12, -1):
        for start in range(0, max(len(digits) - length + 1, 0)):
            window = digits[start : start + length]
            if luhn_ok(window):
                return window
    for length in (19, 18, 17, 13, 14, 15):
        for start in range(0, max(len(digits) - length + 1, 0)):
            window = digits[start : start + length]
            if luhn_ok(window):
                return window
    return None


def _run_and(sentence: str, pack_id: str | None, and_fn: AndFn | None) -> bool:
    if and_fn is not None:
        return bool(and_fn(sentence, pack_id))
    if not pack_id:
        logger.info("egress AND fail-closed: no pack_id")
        return False
    from app.modules.embedder import embedder
    from app.modules.geometry.multi_grain import evaluate_sentence

    try:
        verdict = evaluate_sentence(sentence, pack_id, embed_fn=embedder.embed)
    except Exception:
        logger.exception("egress AND failed closed")
        return False
    return bool(verdict.passed)


def _run_inlp(text: str, *, inlp_fn: InlpFn | None) -> bool | None:
    fn = inlp_fn if inlp_fn is not None else _INLP_OVERRIDE
    if fn is not None:
        return fn(text)
    path = DEFAULT_INLP_ARTIFACT
    if not path.exists():
        logger.info("egress INLP skip: no artefact at %s", path)
        return None
    from app.modules.embedder import embedder
    from app.modules.geometry.inlp import load_inlp, should_cut
    from app.modules.geometry.whitening import load_whitening

    try:
        model = load_inlp(path)
        vector = embedder.embed(text)
        dense = getattr(vector, "dense", vector)
        whitening_path = path.with_name("whitening_automotive.npz")
        if whitening_path.exists():
            from app.modules.geometry.whitening import whiten

            dense = whiten(dense, load_whitening(whitening_path))
        return should_cut(dense, model.tau, basis=model.basis)
    except Exception:
        logger.exception("egress INLP failed closed")
        return True


def _token(secret: str) -> str:
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:8]
    last4 = secret[-4:] if len(secret) >= 4 else secret
    return f"[redacted:{digest}:{last4}]"
