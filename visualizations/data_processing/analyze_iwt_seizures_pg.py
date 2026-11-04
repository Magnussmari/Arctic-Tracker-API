#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""IWT seizures analysis — psycopg2 port (fig 7), FULL DATA.

DEFECT FIXED vs the frozen 2025-11-12 JSON: the supabase original consumed one
unpaginated page (1,000 of 2,606 source='I' records) — ranks below #1 were
wrong (e.g. walrus seizures missing from the top ranks). This port reads ALL
records. Output schema is identical; numbers are the corrected full-data values.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pg_common import query
from global_scope import latest_global_status

# The manuscript's corpus is arctic_v2. Three of these generators read the
# pre-rebuild `arctic` schema instead, which is why Figure 2 was titled
# "473,102 trade records" while the manuscript reports 492,095. One name,
# overridable, so the figures and the claims cannot describe different data.
import os as _os


def _run_date() -> str:
    """The date this file was actually produced.

    These fields were hardcoded to "2026-07-22" and were still saying so on
    2026-08-15, in files regenerated minutes earlier from a different corpus.
    A provenance date that never moves is worse than an absent one: a reader
    has no reason to distrust it.

    V-29 strips these before comparing digests, so a live date does not make
    the intermediates look unreproducible.
    """
    import datetime as _dt
    return _dt.date.today().isoformat()
SCHEMA = _os.environ.get("ARCTIC_SCHEMA", "arctic_v2")

ROOT = Path(__file__).parent.parent.parent
OUT = ROOT / "data/exports/iwt_seizures_analysis.json"


def main():
    records = query(f"""SELECT species_id, taxon, term, quantity, year, purpose, importer, exporter, appendix
                       FROM {SCHEMA}.cites_trade_records WHERE source = 'I'
                       ORDER BY species_id, record_id""")  # fixed order: deterministic float accumulation
    species_data = defaultdict(lambda: {
        "taxon": "", "total_quantity": 0.0, "record_count": 0,
        "terms": Counter(), "purposes": Counter(), "years": [], "appendices": Counter(),
    })
    for r in records:
        d = species_data[r["species_id"]]
        d["taxon"] = r["taxon"]
        d["total_quantity"] += float(r.get("quantity") or 0)
        d["record_count"] += 1
        d["terms"][r.get("term") or "unknown"] += 1
        d["purposes"][r.get("purpose") or "unknown"] += 1
        d["years"].append(r.get("year"))
        d["appendices"][r.get("appendix") or "unknown"] += 1

    top = sorted(species_data.items(), key=lambda x: x[1]["total_quantity"], reverse=True)[:10]
    ids = [sid for sid, _ in top]
    # Latest GLOBAL category, from the one definition in global_scope.py.
    # `WHERE is_latest AND <global>` would be empty for every species whose
    # is_latest assessment is European, and `is_latest` alone would draw the
    # European category (for the fin whale it differs from the global one).
    # The manuscript caption says "latest global IUCN Red List category".
    iucn = latest_global_status(query, SCHEMA, ids)
    cites = {r["species_id"]: r["appendix"] for r in query(
        f"SELECT species_id, appendix FROM {SCHEMA}.cites_listings WHERE is_current AND species_id = ANY(%s::uuid[])", (ids,))}
    names = {r["id"]: r for r in query(
        f"SELECT id, scientific_name, common_name FROM {SCHEMA}.species WHERE id = ANY(%s::uuid[])", (ids,))}

    out = []
    for sid, d in top:
        info = names.get(sid, {})
        out.append({
            "species_id": sid,
            "scientific_name": info.get("scientific_name", d["taxon"]),
            "common_name": info.get("common_name", ""),
            "total_quantity": d["total_quantity"],
            "seizure_count": d["record_count"],
            "iucn_status": iucn.get(sid, "Unknown"),
            "cites_appendix": cites.get(sid, "Unknown"),
            "top_products": dict(d["terms"].most_common(3)),
            "top_purposes": dict(d["purposes"].most_common(3)),
            "appendix_distribution": dict(d["appendices"]),
            "year_range": f"{min(y for y in d['years'] if y)}-{max(y for y in d['years'] if y)}" if any(d["years"]) else "N/A",
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({
            "total_seizure_records": len(records),
            "top_10_species": out,
            "analysis_date": _run_date(),
            "data_source": "CITES Trade Database (source=I, FULL extract — fixes 1000-row truncation of 2025-11-12 run)",
        }, f, indent=2, sort_keys=True)
    print(f"iwt: {len(records)} records, top={out[0]['scientific_name']} -> {OUT}")


if __name__ == "__main__":
    main()
