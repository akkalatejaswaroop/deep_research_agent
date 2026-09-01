"""Seed controlled notes into the sandbox vault for REX tests B / C / F.

Usage: python rex_tests/seed_vault.py --mode B|C|F [--tag <label>]
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_VAULT = Path(os.environ.get("REX_TEST_VAULT", str(ROOT / "rex_test_vault")))
os.environ["REX_VAULT_PATH"] = str(TEST_VAULT)
sys.path.insert(0, str(ROOT / "backend"))

from agents import memory_agent as ma  # noqa: E402


def make_id(code: str, key: str) -> str:
    h = hashlib.sha256(key.encode()).hexdigest()[:21].upper()
    h = h.replace("I", "J").replace("L", "M").replace("O", "P")
    return f"{code}-01J8Y{h[:21]}"


def base_fm(note_type, title, conf, tags, extra=None):
    code = ma._CODE_MAP[note_type]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    fm = {
        "id": make_id(code, title),
        "type": note_type,
        "title": title,
        "status": "active",
        "confidence": conf,
        "created": now,
        "updated": now,
        "version": 1,
        "source_count": 1,
        "agent": "memory",
        "tags": tags,
    }
    if extra:
        fm.update(extra)
    return fm


def seed(note_type, title, body, conf=0.75, tags=None, extra=None):
    fm = base_fm(note_type, title, conf, tags or [], extra)
    res = ma.create_note(note_type, fm, body, run_id="rextest-seed")
    return res


def mode_B():
    """Test B: one directly-relevant cluster (oversized, to force budget truncation)
    plus one deliberately irrelevant note."""
    out = {"relevant": [], "irrelevant": None}
    src = seed(
        "source",
        "Cathode durability study of layered sodium-ion cells",
        "# Source Note\n\nURL: https://example-journals.org/sodium-cathode-durability\n\n"
        "Peer-reviewed study measuring capacity retention of layered oxide sodium-ion "
        "cathodes across 500-2000 cycles at 25C and 45C, including impedance growth data.",
        tags=["source", "sodium-ion"],
        extra={"url": "https://example-journals.org/sodium-cathode-durability",
               "provenance": "peer-reviewed", "authors": "Test Seed",
               "publication": "Journal of Test Seeding", "year": 2026, "doi": "",
               "source_type": "paper", "retrieved": time.strftime("%Y-%m-%d"),
               "access_note": "seeded for REX test B"},
    )
    out["source"] = src.get("id")
    src_link = f"[[{src.get('id')}]]"
    facts = [
        ("Prussian blue analogue cathodes dissolve iron at elevated charge voltages",
         "Prussian blue analogue sodium cathodes release Fe ions into carbonate electrolytes "
         "when charged above 3.9 volts, and the dissolved iron plates onto the counter "
         "electrode, according to ICP-MS measurements in the seeded study.", 0.82,
         ["sodium-ion", "cathode-durability"]),
        ("Tunnel-type Na cathodes resist strain because their open frames flex during sodiation",
         "The tunnel-structured sodium insertion material accommodates ion entry by elastic "
         "frame distortion rather than brittle phase change, so its crystallites survive "
         "repeated swelling cycles far better than layered analogues.", 0.78,
         ["sodium-ion", "cathode-durability"]),
        ("Dry-room dew point below minus 40C preserves sodium electrode adhesion",
         "Assembly halls held at very low humidity kept the binder matrix from premature "
         "gelling, doubling peel strength of freshly calendered sodium electrodes versus "
         "the humid baseline line.", 0.72, ["sodium-ion", "manufacturing"]),
        ("Sodium cells tolerate deep winter discharge better than lithium counterparts",
         "Field telemetry from cold-region storage sites showed the sodium chemistry "
         "delivering usable power at minus 20 Celsius where reference lithium racks had "
         "already curtailed output.", 0.7, ["sodium-ion", "field-performance"]),
        ("Spent sodium stacks yield nickel and manganese feedstock via mild acid leaching",
         "Recyclers recovered battery-grade transition-metal salts from end-of-life sodium "
         "cells using dilute organic acids at near-ambient temperature, avoiding pyrometal "
         "furnaces entirely.", 0.67, ["sodium-ion", "recycling"]),
        ("Sodium electrolyte formulations with ether cosolvents pass 60-day float tests",
         "Adding glyme-based cosolvent stabilized the sodium interphase during long float "
         "periods; impedance rose under ten percent across a two-month bench trial.",
         0.64, ["sodium-ion", "electrolyte"]),
        ("Grid pilot installed in 2025 logged 98 percent round-trip efficiency over summer peak shaving",
         "The megawatt-scale sodium demonstrator recorded seasonal efficiency just under 99 "
         "percent while performing daily peak-shaving duty for the regional utility.",
         0.69, ["sodium-ion", "grid-pilot"]),
        ("Machine-vision inspection catches sodium electrode coating defects before roll pressing",
         "An inline camera system flagged pinholes and streaks on coated sodium foils early "
         "enough to re-slurry the batch, cutting scrap rates by a third.",
         0.65, ["sodium-ion", "quality-control"]),
    ]
    for i, (title, body, conf, tags) in enumerate(facts):
        r = seed("claim", title,
                 f"# {title}\n\n{body}\n\nEvidence: {src_link}\n",
                 conf=conf, tags=tags,
                 extra={"claim_class": "interpretation", "evidence_strength": "moderate",
                        "supporting_sources": [src_link], "contradicting_sources": []})
        out["relevant"].append(r.get("id"))
    irr = seed(
        "concept",
        "Byzantine manuscript pigment degradation patterns",
        "# Byzantine manuscript pigment degradation patterns\n\nAnalysis of ultramarine and "
        "lead-tin yellow pigments in twelfth-century Byzantine manuscripts shows distinctive "
        "oxidation patterns driven by monastery humidity cycles rather than light exposure.\n\n"
        "Orphan justification: deliberate negative-control seed for REX test B — must stay "
        "topically unrelated to all research questions.",
        conf=0.6, tags=["art-history", "pigments", "orphan-intentional"])
    out["irrelevant"] = irr.get("id")
    return out


def mode_C():
    """Test C: one narrow seeded claim to be duplicated / updated / contradicted."""
    src = seed(
        "source",
        "Solid-state EV pack trial report Q2",
        "# Source Note\n\nURL: https://example-labs.org/ssb-pack-trial\n\nFleet trial report "
        "covering solid-state battery pack prototypes in two electric vans over six months.",
        tags=["source", "solid-state"],
        extra={"url": "https://example-labs.org/ssb-pack-trial", "provenance": "industry",
               "authors": "Test Seed", "publication": "SSB Pack Trials", "year": 2026,
               "doi": "", "source_type": "report",
               "retrieved": time.strftime("%Y-%m-%d"),
               "access_note": "seeded for REX test C"},
    )
    src_link = f"[[{src.get('id')}]]"
    clm = seed(
        "claim",
        "Solid-state EV pack prototype achieved 420 Wh/kg pack-level energy density",
        "# Solid-state EV pack prototype achieved 420 Wh/kg pack-level energy density\n\n"
        "The six-month van fleet trial reported pack-level energy density of 420 Wh/kg with "
        "under 5 percent fade over 300 cycles.\n\nEvidence: "
        f"{src_link}\n",
        conf=0.8, tags=["solid-state", "ev-packs"],
        extra={"claim_class": "fact", "evidence_strength": "strong",
               "supporting_sources": [src_link], "contradicting_sources": []})
    return {"claim": clm.get("id"), "source": src.get("id")}


def mode_F():
    """Test F: 10 related fact notes, deliberately mixed confidence, spread over
    fake runs, all HOT/WARM tier."""
    ids = []
    confs = [0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.95]
    titles = [
        "Quantum dot LED external quantum efficiency reached 20 percent in 2024 devices",
        "Quantum dot displays achieve Rec.2020 coverage above 90 percent",
        "CdSe quantum dot synthesis yield improved to 85 percent with new precursors",
        "InP quantum dot LEDs reach 12 percent EQX without cadmium",
        "Quantum dot lifetime T50 exceeded 40000 hours in blue emitters",
        "Perovskite quantum dots show halide migration under bias stress",
        "Quantum dot color conversion patterning reaches 1000 ppi resolution",
        "Room-temperature quantum dot sintering avoids ligand loss",
        "Quantum dot solar cells hit certified 18 percent efficiency",
        "Blue quantum dot emission narrowed to 22 nm FWHM in production panels",
    ]
    for i, (t, c) in enumerate(zip(titles, confs)):
        body = (f"# {t}\n\nMeasured result reported by lab {i}: {t.lower()} under standard "
                f"test conditions, reproduced across two device batches with uncertainty "
                f"under 5 percent relative.\n")
        r = seed("fact", t, body, conf=c, tags=["quantum-dot-display"],
                 extra={"run_refs": [f"RUN-seedF{i:02d}"]})
        ids.append(r.get("id"))
    return {"cluster": ids, "confidences": confs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["B", "C", "F"])
    args = ap.parse_args()
    fn = {"B": mode_B, "C": mode_C, "F": mode_F}[args.mode]
    out = fn()
    print(json.dumps(out, indent=2))
    (TEST_VAULT.parent / "rex_test_evidence" / f"seed_{args.mode}.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
