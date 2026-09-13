"""Generate bundled demo PDF corpora for Etapa 3/5 (automotive + medical)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo_corpus"

CORPORA: dict[str, str] = {
    "automotive_maintenance.pdf": """
Vehicle Maintenance Reference — Passenger Cars

Tire pressure monitoring is critical for safety and fuel economy. The rear axle
nominal PSI for most sedans is between 32 and 35 PSI when tires are cold.
Always check pressure before long trips. Nitrogen-filled tires may hold pressure
longer but still require seasonal adjustment. Replace valve stems when corroded.

Brake pad inspection should occur every 12,000 miles. Listen for squealing or
grinding. Hydraulic fluid must be DOT 3 or DOT 4 as specified in the owner manual.
Flush brake fluid every two years to prevent moisture contamination.

Coolant system maintenance includes thermostat testing, radiator hose inspection,
and water pump gasket checks. Use the manufacturer-recommended coolant mix ratio.
Overheating often traces to a failed thermostat or clogged radiator fins.

Transmission service intervals vary: automatic transmissions need fluid changes
every 60,000 miles under severe duty. Manual gear oil should match viscosity
specifications. Differential bearings require proper lubrication during overhaul.

Suspension components — springs, dampers, alignment camber and caster — affect
tire wear and steering response. Inspect control arms and bushings during
alignment service. Steering rack boots must remain intact to exclude debris.

Electrical systems: alternator output, battery cold-cranking amps, starter draw,
and fuse continuity. Oxygen sensor readings influence fuel trim; replace sensors
at recommended intervals. Diagnostic protocols use OBD-II voltage and resistance
checks before replacing modules.
""",
    "medical_hypertension.pdf": """
Clinical Hypertension Management Guide

Hypertension is sustained blood pressure at or above 130/80 mmHg in adults.
Initial evaluation includes repeated office measurements, home monitoring logs,
and assessment of cardiovascular risk factors. Lifestyle modification is first-line:
sodium reduction, DASH diet, weight management, and regular aerobic exercise.

Pharmacologic therapy may begin with thiazide diuretics, ACE inhibitors, ARBs,
or calcium channel blockers depending on comorbidities. Diabetic patients often
benefit from ACE inhibitors or ARBs for renal protection. Monitor potassium and
creatinine when initiating RAAS blockade.

Resistant hypertension requires review of adherence, white-coat effect, and
secondary causes such as renal artery stenosis or primary aldosteronism. Ambulatory
blood pressure monitoring clarifies nocturnal dipping patterns. Target organ
damage screening includes urinalysis, echocardiography, and retinal exam.

Patient education covers medication timing, avoiding NSAID interactions, and
recognizing symptoms of hypotension. Emergency referral is indicated for
hypertensive crisis with end-organ damage. Follow-up visits should document
home readings and adjust therapy incrementally.

Special populations: pregnant patients need methyldopa or labetalol rather than
ACE inhibitors. Elderly patients may tolerate higher systolic targets to reduce
fall risk. Chronic kidney disease stages influence agent selection and dose
titration schedules.
""",
}


# Helvetica is WinAnsi; map common Unicode punctuation so extraction stays readable.
_WINANSI = str.maketrans({
    "\u2014": "\x97",  # em dash
    "\u2013": "\x96",  # en dash
    "\u2018": "\x91",
    "\u2019": "\x92",
    "\u201c": "\x93",
    "\u201d": "\x94",
    "\u2026": "\x85",
    "\u00a0": " ",
})


def _pdf_escape(text: str) -> str:
    """Escape a string for a PDF literal `(...)` in WinAnsi/Helvetica."""
    out: list[str] = []
    for ch in text.translate(_WINANSI):
        code = ord(ch)
        if ch in "\\()":
            out.append("\\" + ch)
        elif code < 32 or code > 126:
            if code > 255:
                ch = "-"
                code = ord(ch)
                out.append(ch)
            else:
                out.append(f"\\{code:03o}")
        else:
            out.append(ch)
    return "".join(out)


def _paginate_lines(body: str) -> list[list[str]]:
    """Paginate at 90-char wraps, 14pt leading, US Letter."""
    paragraphs = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
    pages: list[list[str]] = []
    current: list[str] = []
    y = 72
    for para in paragraphs:
        if y > 700 and current:
            pages.append(current)
            current = []
            y = 72
        chunks = [para[i : i + 90] for i in range(0, len(para), 90)]
        for line in chunks:
            if y > 720 and current:
                pages.append(current)
                current = []
                y = 72
            current.append(line)
            y += 14
        y += 10
    if current:
        pages.append(current)
    return pages or [[""]]


def build_text_pdf(body: str) -> bytes:
    """Build a simple Helvetica text PDF without copyleft PDF libraries."""
    pages = _paginate_lines(body)
    objects: list[bytes] = [b""]  # 1-indexed

    def add_object(payload: bytes) -> int:
        objects.append(payload)
        return len(objects) - 1

    add_object(b"<< /Type /Catalog /Pages 2 0 R >>")  # 1
    add_object(b"")  # 2 placeholder for Pages
    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_ids: list[int] = []
    for lines in pages:
        content_ops = ["BT", "/F1 11 Tf", "14 TL", "72 720 Td"]
        for i, line in enumerate(lines):
            if i:
                content_ops.append("T*")
            content_ops.append(f"({_pdf_escape(line)}) Tj")
        content_ops.append("ET")
        stream = "\n".join(content_ops).encode("latin-1")
        content_id = add_object(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
        page_ids.append(
            add_object(
                (
                    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                    f"/Contents {content_id} 0 R >>"
                ).encode("ascii")
            )
        )

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    parts = [header]
    offsets = [0]
    pos = len(header)
    for obj_id, payload in enumerate(objects[1:], start=1):
        offsets.append(pos)
        entry = f"{obj_id} 0 obj\n".encode("ascii") + payload + b"\nendobj\n"
        parts.append(entry)
        pos += len(entry)
    xref_pos = pos
    xref = [f"xref\n0 {len(objects)}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer\n<< /Size {len(objects)} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode("ascii")
    return b"".join(parts + xref + [trailer])


def _write_pdf(filename: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / filename
    path.write_bytes(build_text_pdf(body))
    print(f"Wrote {path}")


def main() -> None:
    for name, text in CORPORA.items():
        _write_pdf(name, text)


if __name__ == "__main__":
    main()
