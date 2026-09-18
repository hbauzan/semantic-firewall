"""Oracle package — scores delivered text for rompepepe campaigns."""

from rompepepe.oracle.metrics import ConfusionMatrix, Oracle, Verdict, metrics_from_results

__all__ = ["ConfusionMatrix", "Oracle", "Verdict", "metrics_from_results"]
