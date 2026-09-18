"""Chat-profile output accumulator. Delimiters: `.` `;` `?` newline.

This is not the ingress prompt splitter (wider punctuation, drops short
fragments). A frozen sentence includes its delimiter. The tail without a
delimiter is flushed at upstream done.

A PAN split by newline is two sentences here. The first half **can** be
emitted if it passes the per-sentence gate — that is why L07 hold exists.
Do not mix compliance hold into this buffer.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

CHAT_DELIMITERS = frozenset(".?;\n")
EvalFn = Callable[[str], bool]


@dataclass
class SentenceBuffer:
    _buf: str = field(default="", init=False)

    def push(self, delta: str) -> list[str]:
        if not delta:
            return []
        self._buf += delta
        frozen: list[str] = []
        while True:
            idx = _first_delimiter(self._buf)
            if idx is None:
                return frozen
            frozen.append(self._buf[: idx + 1])
            self._buf = self._buf[idx + 1 :]

    def flush_tail(self) -> str:
        tail, self._buf = self._buf, ""
        return tail

    @property
    def pending(self) -> str:
        return self._buf


def drain(text: str) -> list[str]:
    """Apply the live buffer to a finished string (frozen sentences + tail)."""
    buf = SentenceBuffer()
    parts = buf.push(text)
    tail = buf.flush_tail()
    if tail:
        parts.append(tail)
    return parts


def gated_emit(pieces: Sequence[str], eval_fn: EvalFn) -> tuple[list[str], bool]:
    """Push deltas in order. Stop before emitting a failing sentence.

    Returns ``(emitted, passed)``. ``passed`` is False if any eval failed;
    already-emitted sentences stay in ``emitted``.
    """
    buf = SentenceBuffer()
    emitted: list[str] = []
    for piece in pieces:
        for sentence in buf.push(piece):
            if not eval_fn(sentence):
                return emitted, False
            emitted.append(sentence)
    tail = buf.flush_tail()
    if tail:
        if not eval_fn(tail):
            return emitted, False
        emitted.append(tail)
    return emitted, True


def _first_delimiter(text: str) -> int | None:
    for index, char in enumerate(text):
        if char in CHAT_DELIMITERS:
            return index
    return None
