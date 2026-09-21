"""IEEE 754 full-mantissa text for coordinates and telemetry."""


def format_float(val: float) -> str:
    """Render a float so the text round-trips every float64 bit."""
    return f"{float(val):.17g}"
