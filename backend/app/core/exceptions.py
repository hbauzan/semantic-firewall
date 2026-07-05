"""Structured security exceptions for the semantic firewall."""


class BurstDetectionBreach(Exception):
    """Raised when raw prompt entropy falls below the configured floor (GCG / burst)."""

    breach_type = "BURST_DETECTION_BREACH"

    def __init__(self, clause: str, entropy: float, limit: float) -> None:
        self.clause = clause
        self.entropy = entropy
        self.limit = limit
        super().__init__(
            f"BURST_DETECTION_BREACH: entropy={entropy:.4f} < limit={limit:.4f}"
        )
