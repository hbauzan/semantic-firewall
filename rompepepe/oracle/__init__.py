"""Oracle package — scores delivered text for rompepepe campaigns."""

from rompepepe.oracle.membership import AndMembership
from rompepepe.oracle.metrics import ConfusionMatrix, Oracle, Verdict, metrics_from_results

__all__ = ["AndMembership", "ConfusionMatrix", "Oracle", "Verdict", "metrics_from_results"]
