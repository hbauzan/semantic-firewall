"""Recorte lomo vs oficio. Texto solamente. Lab. No evaluate_clause.

El PDF es un libro. El candado de la tesis es el oficio (taller), no el lomo
(radio / legal / índice / cubiertas). Cada drop lleva un reason auditable.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

LOMO_REASONS: tuple[str, ...] = ("indice", "legal", "cubierta", "radio")

_DOT_LEADER = re.compile(r"(?:\.\s*){6,}")
_RADIO_HEADER = re.compile(
    r"(?:sistema de\s+)?infoentretenimiento\s+7-\d+",
    re.I,
)
_CLIENTE_HEADER = re.compile(r"informaci[oó]n del cliente\s+13-\d+", re.I)
_BOILER = re.compile(
    r"MY15\.5_Prisma\S*"
    r"|Black plate\s*\([^)]+\)"
    r"|Chevrolet Onix Sedan Owner Manual[^.\n]*"
    r"|GMSA-Localizing-Mercosur-\d+"
    r"|2015\s*-\s*crc\s*-\s*[\d/]+",
    re.I,
)

_LEGAL_PHRASES: tuple[str, ...] = (
    "publicación señalada en el lomo",
    "publicacion senalada en el lomo",
    "no se permite reproduc",
    "reservamos el derecho",
    "garantía ofrecida por general motors",
    "garantia ofrecida por general motors",
    "manual de ventas",
    "centro de contactos",
    "oficinas de asistencia",
)

_RADIO_SUBJECT: tuple[str, ...] = (
    "radio am-fm",
    "radio am",
    "radio fm",
    "ecualizador",
    "antena de mástil",
    "antena de mastil",
    "emisora",
    "reproductor",
    "bluetooth",
    "mylink",
    "infoentretenimiento",
    "manos libres",
    "archivos de música",
    "archivos de musica",
    "a2dp",
)

_OFICIO_CORE: tuple[str, ...] = (
    "aceite del motor",
    "refrigerante",
    "pastillas",
    "bujía",
    "bujia",
    "torque",
    "cerradura",
    "desbloquear",
    "estacionamiento",
    "estación de servicio",
    "estacion de servicio",
    "depósito de combustible",
    "deposito de combustible",
    "indicador de combustible",
    "filtro de aire",
    "capó",
    "holgura",
    "helada",
    "carretera",
)

_OFICIO_MEASURE: tuple[str, ...] = (
    "psi",
    "kpa",
    "aceite del motor",
    "refrigerante del motor",
    "líquido de frenos",
    "liquido de frenos",
    "bujía",
    "bujia",
    "neumático",
    "neumatico",
)

_FOB_MARKERS: tuple[str, ...] = (
    "control remoto de radio",
    "control remoto",
)


@dataclass(frozen=True)
class LomoTag:
    reason: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class DroppedChunk:
    index: int
    id: object
    reason: str
    reasons: tuple[str, ...]
    preview: str


@dataclass(frozen=True)
class OficioSplit:
    keep: tuple[dict, ...]
    drop: tuple[DroppedChunk, ...]
    counts: dict[str, int]
    n_raw: int
    n_oficio: int
    keep_indices: tuple[int, ...]


def _fold(text: str) -> str:
    return " ".join(text.lower().split())


def _preview(text: str, n: int = 180) -> str:
    return " ".join(text.split())[:n]


def _has_any(hay: str, needles: tuple[str, ...]) -> bool:
    return any(n in hay for n in needles)


def _count_subj(hay: str, needles: tuple[str, ...]) -> int:
    return sum(1 for n in needles if n in hay)


def _stripped_body(text: str) -> str:
    return " ".join(_BOILER.sub(" ", text).split())


def _is_index(text: str, low: str) -> bool:
    if text.count(". . .") >= 6 or len(_DOT_LEADER.findall(text)) >= 6:
        return True
    if "índice" in low or "indice" in low:
        return text.count(". . .") >= 3
    return False


def _is_legal(low: str, measure: bool) -> bool:
    if _has_any(low, _LEGAL_PHRASES):
        return True
    if _CLIENTE_HEADER.search(low) and not measure:
        return True
    return False


def _is_cover(text: str, low: str, measure: bool) -> bool:
    if measure:
        return False
    black = low.count("black plate")
    my15 = low.count("my15.5_prisma")
    body = _stripped_body(text)
    if len(body) <= 80 and (black or my15):
        return True
    if black >= 2 and len(body) <= 160:
        return True
    return False


def _xref_or_display(low: str) -> bool:
    if "consulte" in low and "infoentreten" in low and "página 7" in low:
        return True
    if "consulte" in low and "infoentreten" in low and "pagina 7" in low:
        return True
    if "vehículos no equipados con mylink" in low or "vehiculos no equipados con mylink" in low:
        return True
    if "se mostrará en el sistema de infoentretenimiento" in low:
        return True
    if "se mostrara en el sistema de infoentretenimiento" in low:
        return True
    return False


def _is_fob(low: str) -> bool:
    return _has_any(low, _FOB_MARKERS) and (
        "desbloquear" in low or "bloquear" in low or "puertas" in low
    )


def _is_radio(low: str, measure: bool, oficio_core: bool) -> bool:
    if _RADIO_HEADER.search(low):
        return True
    if _is_fob(low):
        return False
    score = _count_subj(low, _RADIO_SUBJECT)
    if score < 2:
        return False
    if measure:
        return False
    if oficio_core and _xref_or_display(low):
        return False
    if oficio_core and score <= 2 and _xref_or_display(low):
        return False
    if oficio_core and score <= 2 and "página 7" in low:
        return False
    return True


def classify_lomo(text: str) -> LomoTag | None:
    """None = oficio: esa fila pinta el sobre recortado."""
    if not text or not text.strip():
        return LomoTag("cubierta", ("cubierta",))
    low = _fold(text)
    measure = _has_any(low, _OFICIO_MEASURE)
    oficio_core = measure or _has_any(low, _OFICIO_CORE)
    found: list[str] = []
    if _is_index(text, low):
        found.append("indice")
    if _is_legal(low, measure):
        found.append("legal")
    if _is_cover(text, low, measure):
        found.append("cubierta")
    if _is_radio(low, measure, oficio_core):
        found.append("radio")
    if not found:
        return None
    primary = next(r for r in LOMO_REASONS if r in found)
    return LomoTag(primary, tuple(found))


def prisma_bucket_indices(chunks: list[dict]) -> dict[str, tuple[int, ...]]:
    """Row index in prisma_chunk order → oficio | indice | legal | cubierta | radio."""
    buckets: dict[str, list[int]] = {r: [] for r in LOMO_REASONS}
    buckets["oficio"] = []
    for i, chunk in enumerate(chunks):
        tag = classify_lomo(str(chunk.get("text") or ""))
        key = "oficio" if tag is None else tag.reason
        buckets[key].append(i)
    return {k: tuple(v) for k, v in buckets.items()}


def split_oficio(chunks: list[dict]) -> OficioSplit:
    keep: list[dict] = []
    drop: list[DroppedChunk] = []
    keep_idx: list[int] = []
    counts: Counter[str] = Counter()
    for i, chunk in enumerate(chunks):
        tag = classify_lomo(str(chunk.get("text") or ""))
        if tag is None:
            keep.append(chunk)
            keep_idx.append(i)
            continue
        counts[tag.reason] += 1
        drop.append(
            DroppedChunk(
                index=int(chunk.get("index", i)),
                id=chunk.get("id", i),
                reason=tag.reason,
                reasons=tag.reasons,
                preview=_preview(str(chunk.get("text") or "")),
            )
        )
    return OficioSplit(
        keep=tuple(keep),
        drop=tuple(drop),
        counts=dict(counts),
        n_raw=len(chunks),
        n_oficio=len(keep),
        keep_indices=tuple(keep_idx),
    )
