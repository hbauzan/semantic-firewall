"""Lomo vs oficio: text rules only. Does not load BGE-M3."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from calibration.dimension_probe.generate import default_prisma_json, load_prisma_chunks
from calibration.dimension_probe.lomo import classify_lomo, split_oficio
from calibration.dimension_probe.run import (
    _compare_envelopes,
    _compare_hypothesis,
    _envelope_report,
    _paint_groups,
)
from calibration.dimension_probe.metrics import (
    dim_spans,
    envelope_bounds,
    relative_slack,
    rows_inside_strict,
)

_INDEX = (
    "Iluminación exterior. . . . . . . . . . . . 6-1 "
    "Sistema de infoentretenimiento . . . . . . . . . 7-1 "
    "Radio . . . . . . . . . . . . . . . . . . . . . . . . . 7-9 "
    "Índice . . . . . . . . . . . . . . . . . . . . i-1"
)

_LEGAL_LOMO = (
    "Las informaciones y descripciones de los equipamientos, contenidos en esta Guía, "
    "están basadas en un vehículo completamente equipado con los optativos disponibles "
    "en la fecha de publicación señalada en el lomo."
)

_LEGAL_FACTURA = (
    "Todos los Concesionarios disponen de Manual de Ventas con informaciones vigentes. "
    "La factura emitida por el Concesionario identifica los componentes instalados "
    "originariamente. Esa factura y el Manual de Ventas rigen la garantía ofrecida "
    "por General Motors de Argentina S.R.L."
)

_COVER = (
    "MY15.5_Prisma_52101249_ESP_20141117_V0.1\n"
    "Black plate (1,1)\n"
    "Chevrolet Onix Sedan Owner Manual (GMSA-Localizing-Mercosur-8071828) "
    "- 2015 - crc - 11/5/14\n"
    "Black plate (2,1)\n"
    "Chevrolet Onix Sedan Owner Manual (GMSA-Localizing-Mercosur-8071828)"
)

_RADIO_CH7 = (
    "Sistema de infoentretenimiento 7-9\n"
    "Radio AM-FM. Pulse [telephone] en el menú de inicio. "
    "Si el teléfono Bluetooth no estuviera conectado al sistema de "
    "infoentretenimiento, la función no estará disponible."
)

_RADIO_EQ = (
    "Modo EQ (Ecualizador): Seleccione el estilo de sonido (Manual—Pop—Rock). "
    "Ajustes del tono en el menú de FM/AM del sistema de infoentretenimiento."
)

_OIL = (
    "Compruebe el nivel de aceite del motor antes de recurrir a la asistencia "
    "de un concesionario. Consulte Aceite del motor en la página 10-11."
)

_COOLANT = (
    "Cuidado del vehículo 10-15. Refrigerante del motor. "
    "Cambio del líquido refrigerante del motor. Cerrar el capó."
)

_FOB = (
    "Control remoto de radio K Desbloquear todas las puertas. "
    "Q Bloquear todas las puertas y la tapa del baúl."
)

_XREF_DOOR = (
    "Sacar la llave de la cerradura del encendido. Consulte "
    "“Configuración del vehículo” en Infoentretenimiento en la página 7-1. "
    "Peligro: no desbloquee la puerta mientras conduzca."
)

_GAS_STATION = (
    "Apague los teléfonos móviles. Siga las instrucciones de funcionamiento "
    "y seguridad de la estación de servicio al recargar."
)

_TIRE_PLUS_FOOTER = (
    "presión de los neumáticos que se indica. 60 psi (420 kPa) "
    "MY15.5_Prisma_52101249_ESP_20141117_V0.1 "
    "Black plate (12,1) Chevrolet Onix Sedan Owner Manual "
    "(GMSA-Localizing-Mercosur-8071828) - 2015 - crc - 11/5/14"
)

_CLIENTE = (
    "Información del cliente 13-1\n"
    "Oficinas de asistencia Chevrolet. Centro de Contactos con Clientes GM."
)


def test_index_dotted_leaders_are_lomo() -> None:
    tag = classify_lomo(_INDEX)
    assert tag is not None
    assert tag.reason == "indice"


def test_legal_spine_and_gm_warranty_are_lomo() -> None:
    assert classify_lomo(_LEGAL_LOMO).reason == "legal"
    assert classify_lomo(_LEGAL_FACTURA).reason == "legal"
    assert classify_lomo(_CLIENTE).reason == "legal"


def test_cover_boilerplate_is_lomo() -> None:
    assert classify_lomo(_COVER).reason == "cubierta"


def test_radio_chapter_and_eq_are_lomo() -> None:
    assert classify_lomo(_RADIO_CH7).reason == "radio"
    assert classify_lomo(_RADIO_EQ).reason == "radio"


def test_taller_oil_and_coolant_stay_oficio() -> None:
    assert classify_lomo(_OIL) is None
    assert classify_lomo(_COOLANT) is None


def test_key_fob_is_not_stereo() -> None:
    assert classify_lomo(_FOB) is None


def test_infotainment_xref_on_a_door_page_stays_oficio() -> None:
    assert classify_lomo(_XREF_DOOR) is None


def test_gas_station_is_not_radio() -> None:
    assert classify_lomo(_GAS_STATION) is None


def test_tire_psi_with_running_header_is_not_cover() -> None:
    assert classify_lomo(_TIRE_PLUS_FOOTER) is None


def test_split_oficio_is_auditable() -> None:
    chunks = [
        {"index": 0, "id": "a", "text": _LEGAL_LOMO},
        {"index": 1, "id": "b", "text": _OIL},
        {"index": 2, "id": "c", "text": _INDEX},
        {"index": 3, "id": "d", "text": _RADIO_CH7},
    ]
    split = split_oficio(chunks)
    assert split.n_raw == 4
    assert split.n_oficio == 1
    assert split.keep[0]["id"] == "b"
    assert split.keep_indices == (1,)
    assert split.counts["legal"] == 1
    assert split.counts["indice"] == 1
    assert split.counts["radio"] == 1
    reasons = {d.reason for d in split.drop}
    assert reasons == {"legal", "indice", "radio"}
    assert all(d.preview for d in split.drop)


def test_oficio_envelope_rejects_torta_that_raw_book_admits() -> None:
    """dim1: radio +0.039 lifts the ceiling; torta +0.027 sneaks into the book."""
    oficio = np.array([[0.0, 0.00], [0.1, 0.02], [0.05, 0.01]], dtype=np.float32)
    radio = np.array([[0.05, 0.039]], dtype=np.float32)
    raw = np.vstack([oficio, radio])
    torta = np.array([[0.05, 0.027]], dtype=np.float32)
    lo_r, hi_r = envelope_bounds(raw)
    lo_o, hi_o = envelope_bounds(oficio)
    slack_r = relative_slack(dim_spans(raw), 5.0)
    slack_o = relative_slack(dim_spans(oficio), 5.0)
    assert rows_inside_strict(torta, lo_r, hi_r, slack_r) == 1.0
    assert rows_inside_strict(torta, lo_o, hi_o, slack_o) == 0.0


def test_paint_groups_slices_prisma_without_changing_probe_families() -> None:
    prisma = np.array([[0.0, 0.0], [1.0, 0.1], [0.2, 0.9]], dtype=np.float32)
    torta = np.array([[5.0, 0.0]], dtype=np.float32)
    groups = _paint_groups({"prisma_chunk": prisma, "piggy_clause_torta": torta}, (0, 1))
    assert groups["prisma_oficio"].shape == (2, 2)
    assert groups["prisma_lomo"].shape == (1, 2)
    assert np.allclose(groups["piggy_clause_torta"], torta)
    raw = _envelope_report(groups, "prisma_chunk")
    oficio = _envelope_report(groups, "prisma_oficio")
    cmp = _compare_envelopes(raw, oficio)
    assert cmp["median_span_oficio"] <= cmp["median_span_raw"]
    hypo = _compare_hypothesis(raw, oficio)
    assert hypo["oficio_span_mas_chico_que_libro"] is True
    assert hypo["lomo_no_define_el_candado_oficio"] is True


def test_real_prisma_export_drops_lomo_keeps_oil_if_present() -> None:
    path = default_prisma_json()
    if not path.is_file():
        pytest.skip("no local prisma export")
    chunks = load_prisma_chunks(path)
    split = split_oficio(chunks)
    assert split.n_raw == 903
    assert 80 <= split.counts.get("indice", 0) <= 200
    assert split.counts.get("radio", 0) >= 20
    assert split.counts.get("legal", 0) >= 3
    assert 500 <= split.n_oficio < split.n_raw
    first = classify_lomo(chunks[0]["text"])
    assert first is not None and first.reason == "legal"
    oil = next(c for c in chunks if "aceite del motor" in c["text"].lower() and c["text"].count(". . .") < 3)
    assert classify_lomo(oil["text"]) is None
