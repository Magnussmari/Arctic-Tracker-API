#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""Illegal-trade seizure ingest — psycopg2, transactional, idempotent.

Source: illegal_trade/arctic_illegal_trade_records.csv (919 records), the Arctic
subset of Stringham et al. 2021 (Data in Brief, S2352340921008076) — a manual
OpenDatabases scrape (CITES/LEMIS/WTP), vintage documented in H7. No SLA on
updates; the raw extraction is NOT re-run by this sprint (documented non-goal).

Decontamination filter (generalized 2026-07-22, SOTA blocker):
The original scrape matched records at genus/family/keyword level, so the
`arctic_species_id` attribution is wrong for any record whose
`db_taxa_name_clean` is not the attributed species. The 2025-10-02 hotfix
(HOTFIX_polar_bear_contamination.sql) fixed this for Ursus maritimus only
(177 records dropped: 174 genus-match + 3 different-genus), leaving the SAME
bug uncorrected for every other genus (Lynx, Falco, Buteo, Acipenser, Bubo,
Balaenoptera, Orcinus, ...). This loader generalizes the hotfix rule to ALL
species:

  KEEP iff db_taxa_name_clean (lowercased) is
    (a) exactly the attributed species' binomial, or
    (b) a trinomen whose binomial is the attributed species (subspecies), or
    (c) a documented alias in ILLEGAL_TRADE_ALIASES (frozen, test-pinned).
  DROP otherwise, with per-genus evidence in
  ingest/reports/illegal_trade_decontamination.json.

This deliberately DIVERGES from the live 742-row baseline (which carries the
residual contamination). The corrected count and per-genus evidence are reported
for the authors; the maintainers' live-comparison check asserts the corrected
output against an independent source-CSV derivation, not against the
known-flawed live table.

Row uuids are uuid5(species_id|db_taxa_name_clean|gbif_id|source_database|idx)
— deterministic across runs. One transaction (truncate + COPY + assertions).
"""
import argparse
import csv
import json
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema, get_conn, ensure_scratch_schema, copy_records, count, sha256_file

ROOT = Path(__file__).parent.parent
SOURCE_CSV = ROOT / "illegal_trade/arctic_illegal_trade_records.csv"
DECON_REPORT = ROOT / "ingest/reports/illegal_trade_decontamination.json"

UUID_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

# Documented taxonomic aliases accepted as legitimate attributions (frozen —
# a test pins this map; additions require a documented justification).
ILLEGAL_TRADE_ALIASES = {
    "bubo scandiaca": "Bubo scandiacus",        # gender-variant synonym
    "physeter catodon": "Physeter macrocephalus",  # junior synonym
    "lynx lynx canadensis": "Lynx canadensis",  # subspecies-of-linx treatment
}

COLUMNS = ["id", "species_id", "source_database", "original_record_id",
           "seizure_date", "seizure_year", "seizure_location",
           "product_type_id", "product_category", "quantity", "unit",
           "reported_taxon_name", "gbif_id", "db_taxa_name_clean", "data_source"] + ["source_artifact", "source_sha256", "provenance_class", "loader_version"]


def row_uuid(parts) -> str:
    return str(uuid.uuid5(UUID_NS, "illegal_trade_seizures:" + "|".join(parts)))


def classify(clean: str, target: str):
    """Return 'keep' or a drop-reason category for an attribution."""
    if clean == target:
        return "keep"
    tokens = clean.split()
    if len(tokens) > 2 and " ".join(tokens[:2]) == target:
        return "keep"  # subspecies of the attributed species
    alias_target = ILLEGAL_TRADE_ALIASES.get(clean)
    if alias_target and alias_target.lower() == target:
        return "keep"
    if len(tokens) == 1 and tokens[0] == target.split()[0]:
        return "genus-only record (no binomial)"
    if tokens and tokens[0] == target.split()[0]:
        return "congeneric species (genus-match, not the Arctic species)"
    return "different-genus attribution (keyword/family-level match)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-schema", default="arctic_sprint")
    ap.add_argument("--lookup-schema", default="arctic",
                    help="schema to resolve species and product ids against")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.target_schema == "arctic" and not args.live:
        sys.exit("refusing to target live schema without --live")

    source_sha = sha256_file(SOURCE_CSV)
    conn = get_conn()
    dropped = []
    drop_summary = defaultdict(Counter)
    rejects = []
    kept = 0
    try:
        with conn:
            with conn.cursor() as cur:
                ensure_scratch_schema(cur, args.target_schema)
                cur.execute(f"SELECT id, product_code FROM {validate_schema(args.lookup_schema)}.illegal_trade_products")
                products = {code: str(pid) for pid, code in cur.fetchall()}
                cur.execute(f"SELECT id, scientific_name FROM {validate_schema(args.lookup_schema)}.species")
                species_names = {str(i): n for i, n in cur.fetchall()}
                # The source CSV carries species ids from --lookup-schema. When the
                # target is a rebuilt schema those uuids do not exist there, so
                # translate via scientific_name. Identity map when the two match.
                cur.execute(f"SELECT scientific_name, id FROM {validate_schema(args.target_schema)}.species")
                target_ids = {n: str(i) for n, i in cur.fetchall()}
                species_remap = {old: target_ids[name] for old, name in species_names.items()
                                 if name in target_ids}
                cur.execute(f"SELECT product_code, id FROM {validate_schema(args.target_schema)}.illegal_trade_products")
                target_products = {code: str(pid) for code, pid in cur.fetchall()}

                def gen():
                    nonlocal kept
                    with open(SOURCE_CSV, newline="", encoding="utf-8") as f:
                        for idx, row in enumerate(csv.DictReader(f)):
                            sid = row["arctic_species_id"].strip()
                            clean = row["db_taxa_name_clean"].strip()
                            target = (species_names.get(sid) or "").lower()
                            verdict = classify(clean.lower(), target)
                            if verdict != "keep":
                                dropped.append({"db": row["db"], "db_taxa_name_clean": clean,
                                                "attributed_species": target, "reason": verdict})
                                drop_summary[target][verdict] += 1
                                continue
                            ptype = products.get(row["standardized_use_id"].strip())
                            if ptype:
                                # products maps code -> lookup-schema id; the code
                                # is the stable key, so re-resolve against the target.
                                code = next((c for c, pid in products.items() if pid == ptype), None)
                                ptype = target_products.get(code, ptype) if code else ptype
                            if not ptype:
                                rejects.append({"db": row["db"], "db_taxa_name_clean": clean,
                                                "standardized_use_id": row["standardized_use_id"],
                                                "reason": "no product mapping"})
                                continue
                            kept += 1
                            yield (
                                row_uuid([species_remap.get(sid, sid), clean, row["gbif_id"].strip(),
                                          row["db"].strip().upper(), str(idx)]),
                                species_remap.get(sid, sid),
                                row["db"].strip().upper(), None,
                                None, None, None,
                                ptype, row["main_category"].strip(), None, None,
                                row["db_taxa_name"].strip(), row["gbif_id"].strip(),
                                clean, "Stringham et al. 2021",
                                # Provenance travels with every row; the NOT NULL
                                # constraints in v2 make a load without it impossible.
                                str(SOURCE_CSV.relative_to(ROOT)), source_sha,
                                "DERIVED", "illegal_trade_load/1.1",
                            )

                # DELETE, not TRUNCATE: Postgres refuses to truncate a table any
                # foreign key references, even when the child is empty.
                cur.execute(f"DELETE FROM {args.target_schema}.illegal_trade_seizures")
                n = copy_records(cur, args.target_schema, "illegal_trade_seizures", COLUMNS, gen())
                # Post-load DQ assertion: every loaded row must satisfy the keep rule.
                cur.execute(f"""
                    SELECT count(*) FROM {args.target_schema}.illegal_trade_seizures t
                    JOIN {validate_schema(args.lookup_schema)}.species s ON s.id = t.species_id
                    WHERE lower(t.db_taxa_name_clean) <> lower(s.scientific_name)
                      AND lower(split_part(t.db_taxa_name_clean, ' ', 1) || ' ' ||
                                split_part(t.db_taxa_name_clean, ' ', 2)) <> lower(s.scientific_name)
                      AND lower(t.db_taxa_name_clean) NOT IN ({','.join(repr(a) for a in ILLEGAL_TRADE_ALIASES)})
                """)
                bad = cur.fetchone()[0]
                assert bad == 0, f"{bad} loaded rows violate the decontamination keep-rule"
                assert not rejects, f"{len(rejects)} kept rows have no product mapping: {rejects[:5]}"
                final = count(cur, args.target_schema, "illegal_trade_seizures")
                cur.execute(f"""SELECT source_database, count(*) FROM {args.target_schema}.illegal_trade_seizures
                                GROUP BY 1 ORDER BY 1""")
                by_db = dict(cur.fetchall())
                print(f"LOADED illegal_trade schema={args.target_schema} rows_copied={n} "
                      f"final_count={final} by_db={by_db} source_sha256={source_sha[:12]}…")
    finally:
        conn.close()
    total_dropped = len(dropped)
    DECON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DECON_REPORT.write_text(json.dumps({
        "source_csv": str(SOURCE_CSV.relative_to(ROOT)),
        "source_sha256": source_sha,
        "rule": "keep iff db_taxa_name_clean == attributed binomial, a subspecies of it, "
                "or a documented alias (ILLEGAL_TRADE_ALIASES in illegal_trade_load.py)",
        "total_source_rows": total_dropped + kept + len(rejects),
        "kept": kept,
        "dropped": total_dropped,
        "dropped_by_attributed_species": {k: dict(v) for k, v in sorted(drop_summary.items())},
        "rows": dropped,
    }, indent=1) + "\n")
    print(f"DECONTAMINATED {total_dropped} rows across {len(drop_summary)} genera -> {DECON_REPORT}")
    for sp, reasons in sorted(drop_summary.items()):
        print(f"    {sp}: {sum(reasons.values())} ({', '.join(f'{v} {k}' for k, v in reasons.items())})")


if __name__ == "__main__":
    main()
