#!/usr/bin/env python3
"""Measure what our species-level counts cannot see.

WHY
---
Our extraction filters the CITES download to 47 names: 43 accepted binomials
plus four aliases. That is correct as far as it goes, because CITES normalises
the Taxon column to the accepted name, so synonym-reported trade already
surfaces under the binomial (verified species by species against Species+ on
2026-08-11).

What it CANNOT see is trade the reporting Party attributed above species level,
or to a hybrid. Those records are real, they concern our taxa, and no query on a
binomial returns them. They are not ours to add: a `Cetacea spp.` record may be
any cetacean. But they are ours to MEASURE, because their share changes over
time and that change manufactures trends.

For the two falcons, records reported above species level fell from 52% of the
total in 1975-1985 to 2.3% in 2006-2024. A species-level count therefore rises
even where the underlying trade is flat.

WHAT THIS PRODUCES
------------------
Per group and per year: species-level records, higher-taxon records that could
conceal the group, hybrid records, and the resulting attribution share. That is
the denominator a resolution-corrected series needs.

It reads the RAW download, not our database, because the point is to see what
the database excluded by construction.
"""
from __future__ import annotations
import csv, glob, json, os, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "species_data/cites_trade/Trade_database_download_v2025.1"
OUT = ROOT / "ingest/reports/attribution_loss.json"

# Groups where a higher taxon or hybrid category can conceal one of our species.
# Keyed by the genus/family our species sit in.
GROUPS = {
    "falcons":    {"genera": {"Falco"},
                   "higher": {"Falconidae spp.", "Falconiformes spp.", "Falco spp."},
                   "hybrid": {"Falco hybrid"}},
    "sturgeon":   {"genera": {"Acipenser"},
                   "higher": {"Acipenseriformes spp.", "Acipenseridae spp.", "Acipenser spp."},
                   "hybrid": set()},   # named crosses handled dynamically
    "cetaceans":  {"genera": {"Balaenoptera","Balaena","Megaptera","Physeter","Orcinus",
                              "Globicephala","Delphinapterus","Monodon","Phocoena",
                              "Phocoenoides","Lagenorhynchus","Hyperoodon","Mesoplodon",
                              "Berardius","Ziphius","Eubalaena","Eschrichtius"},
                   "higher": {"Cetacea spp.","Balaenopteridae spp.","Balaenoptera spp.",
                              "Balaena spp.","Eubalaena spp.","Globicephala spp.",
                              "Phocoena spp.","Hyperoodon spp.","Mesoplodon spp.",
                              "Berardius spp.","Ziphius spp.","Physeter spp.",
                              "Lagenorhynchus spp."},
                   "hybrid": set()},
    "bears":      {"genera": {"Ursus"}, "higher": {"Ursidae spp.","Ursus spp."},
                   "hybrid": {"Ursus hybrid"}},
    "owls":       {"genera": {"Bubo","Asio"},
                   "higher": {"Strigiformes spp.","Strigidae spp.","Bubo spp.","Asio spp."},
                   "hybrid": {"Bubo hybrid"}},
    "walrus":     {"genera": {"Odobenus"}, "higher": {"Odobenidae spp.","Odobenus spp."},
                   "hybrid": set()},
}

def main() -> int:
    ours = set()
    if len(sys.argv) > 1:
        ours = {l.strip() for l in open(sys.argv[1]) if l.strip()}
    else:
        sys.exit("usage: attribution_loss.py <file with our 43 species names>")

    # dynamic hybrids: any name in one of our genera containing ' x ' or 'hybrid'
    per = {g: collections.defaultdict(lambda: [0,0,0]) for g in GROUPS}   # year -> [sp, higher, hybrid]
    for f in sorted(glob.glob(str(RAW / "trade_db_*.csv"))):
        with open(f, newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                t = (r.get("Taxon") or "").strip()
                y = r.get("Year")
                if not (t and y and y.isdigit()):
                    continue
                y = int(y); gen = t.split()[0]
                for g, spec in GROUPS.items():
                    if t in ours and gen in spec["genera"]:
                        per[g][y][0] += 1
                    elif t in spec["higher"]:
                        per[g][y][1] += 1
                    elif gen in spec["genera"] and (" x " in t or "hybrid" in t.lower()):
                        per[g][y][2] += 1

    out = {}
    print(f"{'group':11} {'window':11} {'species':>9} {'higher':>8} {'hybrid':>8} {'unattributable':>15}")
    for g in GROUPS:
        out[g] = {str(y): v for y, v in sorted(per[g].items())}
        for lo, hi, lab in [(1975,1985,"1975-1985"),(1986,1995,"1986-1995"),
                            (1996,2005,"1996-2005"),(2006,2024,"2006-2024")]:
            s = sum(v[0] for y,v in per[g].items() if lo<=y<=hi)
            h = sum(v[1] for y,v in per[g].items() if lo<=y<=hi)
            x = sum(v[2] for y,v in per[g].items() if lo<=y<=hi)
            tot = s+h+x
            if tot:
                print(f"{g:11} {lab:11} {s:>9,} {h:>8,} {x:>8,} {100*(h+x)/tot:>14.1f}%")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"\nper-year detail -> {OUT}")
    print("\nThese records are NOT added to species counts: a higher-taxon record")
    print("cannot be attributed to a species. They are the measured denominator")
    print("for a resolution-corrected series.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
