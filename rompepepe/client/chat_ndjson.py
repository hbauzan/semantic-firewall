"""Parse POST /chat NDJSON into the text the user actually saw.

The HUD prefixes a `[FIREWALL_AUDIT] [FW_PASS]` banner. That banner is not
generation. Feeding it to the Oracle would trip `[FIREWALL_AUDIT]` as a cut
and lie that nothing leaked.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

CUT_MARKERS = (
    "[FW_BLOCK]",
    "[CONNECTION_TERMINATED]",
)
PASS_MARKERS = (
    "[FW_PASS]",
    "[LLM_RESPONSE]:",
)


@dataclass(frozen=True)
class ChatDelivery:
    """User-visible generation from `/chat`, minus pass-banner and cut blobs."""

    delivered_text: str
    cut: bool
    unreliable: bool


def parse_chat_ndjson(raw: str | bytes | Iterable[str]) -> ChatDelivery:
    parts: list[str] = []
    cut = False
    for obj in _iter_objects(raw):
        text = _extract_text(obj)
        if not text:
            continue
        if _is_pass_banner(text):
            continue
        if _is_cut_blob(text):
            cut = True
            continue
        parts.append(text)
    delivered = "".join(parts)
    unreliable = (not cut) and (not delivered.strip())
    return ChatDelivery(delivered_text=delivered, cut=cut, unreliable=unreliable)


def _iter_objects(raw: str | bytes | Iterable[str]):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        lines = raw.splitlines()
    else:
        lines = list(raw)
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def _extract_text(obj: dict) -> str:
    for key in ("response", "text"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _is_pass_banner(text: str) -> bool:
    if any(marker in text for marker in CUT_MARKERS):
        return False
    return any(marker in text for marker in PASS_MARKERS)


def _is_cut_blob(text: str) -> bool:
    return any(marker in text for marker in CUT_MARKERS)
