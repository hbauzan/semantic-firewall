"""Generate bundled demo PDF corpora for Etapa 3/5 (automotive + medical)."""
from __future__ import annotations

import fitz
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


def _write_pdf(filename: str, body: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / filename
    doc = fitz.open()
    paragraphs = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
    page = doc.new_page(width=612, height=792)
    y = 72
    for para in paragraphs:
        if y > 700:
            page = doc.new_page(width=612, height=792)
            y = 72
        chunks = [para[i : i + 90] for i in range(0, len(para), 90)]
        for line in chunks:
            if y > 720:
                page = doc.new_page(width=612, height=792)
                y = 72
            page.insert_text((72, y), line, fontsize=11)
            y += 14
        y += 10
    doc.save(path)
    doc.close()
    print(f"Wrote {path}")


def main() -> None:
    for name, text in CORPORA.items():
        _write_pdf(name, text)


if __name__ == "__main__":
    main()
