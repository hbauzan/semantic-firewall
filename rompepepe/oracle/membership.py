"""S-membership of delivered text. Lab AND (L04), not an Explorer LLM judge."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class Membership(Protocol):
    def is_member(self, delivered_text: str) -> bool:
        """True iff delivered text is in corpus S (micro ∩ meso ∩ lexical)."""


EvaluateSentence = Callable[..., Any]


@dataclass(frozen=True)
class AndMembership:
    """Adapter over `evaluate_sentence`. Inject the function; do not import embedders here."""

    evaluate: EvaluateSentence
    pack_id: str
    embed_fn: Callable[[str], Any]
    nodes: Sequence[Mapping[str, Any]] | None = None
    db_path: str | None = None
    whitening: Any = None
    config: Any = None

    def is_member(self, delivered_text: str) -> bool:
        text = (delivered_text or "").strip()
        if not text:
            return False
        kwargs: dict[str, Any] = {"embed_fn": self.embed_fn}
        if self.nodes is not None:
            kwargs["nodes"] = self.nodes
        if self.db_path is not None:
            kwargs["db_path"] = self.db_path
        if self.whitening is not None:
            kwargs["whitening"] = self.whitening
        if self.config is not None:
            kwargs["config"] = self.config
        verdict = self.evaluate(text, self.pack_id, **kwargs)
        return bool(getattr(verdict, "passed", False))
