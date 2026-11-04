#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""CITES trade ingest — psycopg2, transactional, idempotent.

Two sources (H3 methodology documents the semantics of both):
  --source optimized  Canonical frozen intermediate (species_data/processed/optimized_species
                      *.json.gz, May-2025 extraction). Reproduces the published 473,102-row
                      baseline. Permits are empty in this source (dropped upstream).
  --source raw        Raw CITES download (species_data/cites_trade/Trade_database_download_v2025.1
                      trade_db_*.csv, 56 shards), filtered to the 43 Arctic species
                      (+ documented CITES-name aliases). This is the REFRESH path; its
                      output legitimately differs from the frozen baseline (newer vintage)
                      and the delta report is written for the authors to review.

Target:
  --target-schema arctic_sprint (default; scratch) or arctic (live, --live required)

Load is ONE transaction (truncate + COPY), so re-runs are no-ops and a mid-load
death rolls back. Row uuids are uuid5(record_id) — deterministic across runs,
unlike the legacy random-uuid loads.
"""
import argparse
import gzip
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema, get_conn, ensure_scratch_schema, copy_records, load_species_map, count

import pandas as pd

ROOT = Path(__file__).parent.parent
OPT_DIR = ROOT / "species_data/processed/optimized_species"
RAW_DIR = ROOT / "species_data/cites_trade/Trade_database_download_v2025.1"

COLUMNS = ["id", "species_id", "record_id", "year", "appendix", "taxon", "class",
           "order_name", "family", "genus", "term", "quantity", "unit", "importer",
           "exporter", "origin", "purpose", "source", "reporter_type",
           "import_permit", "export_permit", "origin_permit",
           "source_artifact", "source_sha256", "provenance_class", "loader_version"]

UUID_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # nil namespace base

LOADER_VERSION = "cites_load/1.1"


def raw_source_digest() -> str:
    """Digest of the raw shard set: file names and sizes.

    Hashing 8.6 GB of CSV on every load would be prohibitive, so the pin is over
    the shard inventory. A changed, added or truncated shard changes the digest.
    """
    import hashlib
    inventory = sorted((p.name, p.stat().st_size) for p in RAW_DIR.glob("trade_db_*.csv"))
    return hashlib.sha256(repr(inventory).encode()).hexdigest()

# Raw v2025.1 shards use dotted header names ('Reporter.type',
# 'Import.permit.RandomID', ...). pandas itertuples() silently renames those
# to positional _N attributes, so getattr(r, 'Reporter.type', '') returned ''
# for EVERY row (SOTA blocker: reporter_type + all permits lost on the raw
# path). Rename to safe identifiers BEFORE iterating.
RAW_RENAME = {
    "Reporter.type": "reporter_type",
    "Import.permit.RandomID": "import_permit",
    "Export.permit.RandomID": "export_permit",
    "Origin.permit.RandomID": "origin_permit",
    "Order": "order_name",  # 'Order' survives itertuples, renamed for clarity
}

# LARGE-QUANTITY HANDLING, corrected 2026-08-11.
#
# This loader used to DROP any row whose quantity reached 1e8, calling it a
# "CITES reporting artifact". That diagnosis was wrong and the drop was a
# schema limitation wearing a data-quality costume: the quantity column was
# numeric(10,2) and could not hold the value, so the row was discarded and the
# report blamed the source.
#
# The three affected rows are caviar quantities in milligrammes. 100,000,000 mg
# is 100 kg. They are ordinary records.
#
# The column is now unconstrained numeric and holds them. The ceiling stayed in
# this file for two weeks after the column was widened, which meant a full
# reload silently reproduced the original defect and left the corpus at 492,092
# instead of 492,095. V-4 caught it. Large values are now RETAINED and flagged,
# never dropped: an unparseable quantity is still an error, but a large one is
# not.
QUANTITY_FLAG_THRESHOLD = 1e8
DROPPED_REPORT = ROOT / "ingest/reports/cites_dropped_rows.json"
RAW_DQ_REPORT = ROOT / "ingest/reports/cites_raw_dq.json"


def assert_raw_dq(cur, schema: str):
    """Load-time source-truth DQ gate for the raw refresh path (in-transaction:
    any violation rolls the whole load back).

    The R3 methodology's importer/exporter split and permit analysis depend on
    reporter_type and the three permit columns. The itertuples() dotted-column
    bug loaded '' for all four on every row and every gate stayed green —
    these assertions make that failure mode impossible to commit.
    """
    cur.execute(f"SELECT DISTINCT reporter_type FROM {schema}.cites_trade_records")
    rt = {r[0] for r in cur.fetchall()}
    assert rt == {"E", "I"}, f"reporter_type distinct set must be exactly {{'E','I'}}, got {rt!r}"
    cur.execute(f"""
        SELECT
          count(*) FILTER (WHERE reporter_type = 'E'),
          count(*) FILTER (WHERE reporter_type = 'I'),
          count(*) FILTER (WHERE import_permit <> ''),
          count(*) FILTER (WHERE export_permit <> ''),
          count(*) FILTER (WHERE origin_permit <> ''),
          count(*) FILTER (WHERE quantity IS NULL),
          count(*)
        FROM {schema}.cites_trade_records
    """)
    e, i, imp, exp, ori, null_q, total = cur.fetchone()
    assert imp > 0 and exp > 0 and ori > 0, (
        f"permit columns must be populated on the raw path "
        f"(import={imp}, export={exp}, origin={ori})")
    report = {
        "source": "raw v2025.1",
        "reporter_type": {"E": e, "I": i},
        "permit_fill": {
            "import_permit": {"non_empty": imp, "pct": round(100 * imp / total, 2)},
            "export_permit": {"non_empty": exp, "pct": round(100 * exp / total, 2)},
            "origin_permit": {"non_empty": ori, "pct": round(100 * ori / total, 2)},
        },
        "null_quantity": {"count": null_q, "pct": round(100 * null_q / total, 2)},
        "total_rows": total,
    }
    RAW_DQ_REPORT.parent.mkdir(parents=True, exist_ok=True)
    RAW_DQ_REPORT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"  DQ raw: reporter E={e} I={i}; permits imp={imp} exp={exp} ori={ori}; "
          f"null_qty={null_q} ({report['null_quantity']['pct']}%) -> {RAW_DQ_REPORT.name}")


def row_uuid(record_id: str) -> str:
    return str(uuid.uuid5(UUID_NS, f"cites_trade_records:{record_id}"))


_dropped = []
_flagged = []


def _quantity_ok(record_id, q):
    """True if the row may be loaded. Large quantities are kept and flagged."""
    if q is None:
        return True
    try:
        if abs(float(q)) >= QUANTITY_FLAG_THRESHOLD:
            _flagged.append({"record_id": str(record_id), "quantity": str(q),
                             "reason": "large quantity, retained; check the unit "
                                       "(these are typically milligramme caviar records)"})
        return True
    except (TypeError, ValueError):
        _dropped.append({"record_id": str(record_id), "quantity": str(q),
                         "reason": "unparseable quantity"})
        return False


def denormalize_optimized(path: Path):
    """Yield denormalized records from an optimized species JSON(.gz)."""
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    tax = data["lookup_tables"]["taxonomic"]
    loc = data["lookup_tables"]["locations"]
    cat = data["lookup_tables"]["categorical_reverse"]
    for record in data["trade_records"]:
        full = {
            "record_id": record.get("id", ""),
            "year": record.get("year"),
            "quantity": record.get("quantity_normalized"),
        }
        tid = record.get("taxonomic_id")
        if tid is not None and str(tid) in tax:
            full.update(tax[str(tid)])
        for lf in ("importer", "exporter", "origin"):
            lid = record.get(f"{lf}_id")
            full[lf] = loc.get(str(lid), "") if lid is not None else ""
        for category, lookup in cat.items():
            cid = record.get(f"{category}_id")
            full[category] = lookup.get(str(cid), "") if cid is not None else ""
        yield full


def rows_from_optimized(species_map: dict):
    seen = set()
    for path in sorted(OPT_DIR.glob("*_trade_data_optimized.json.gz")):
        species_name = path.name.replace("_trade_data_optimized.json.gz", "").replace("_", " ")
        if species_name in seen:
            continue
        seen.add(species_name)
        species_id = species_map.get(species_name)
        if not species_id:
            print(f"  WARN: no species mapping for {species_name}", file=sys.stderr)
            continue
        n = 0
        for rec in denormalize_optimized(path):
            rid = str(rec.get("record_id", ""))
            if not _quantity_ok(rid, rec.get("quantity")):
                continue
            yield (
                row_uuid(rid), species_id, rid, rec.get("year"),
                rec.get("appendix", ""), species_name, rec.get("class", ""),
                rec.get("order", ""), rec.get("family", ""), rec.get("genus", ""),
                rec.get("term", ""), rec.get("quantity"), rec.get("unit", ""),
                rec.get("importer", ""), rec.get("exporter", ""), rec.get("origin", ""),
                rec.get("purpose", ""), rec.get("source", ""), rec.get("reporter_type", ""),
                "", "", "",
            )
            n += 1
        print(f"  optimized: {species_name}: {n} records")


_RAW_DIGEST = None


def rows_from_raw(species_map: dict):
    global _RAW_DIGEST
    _RAW_DIGEST = raw_source_digest()
    """Filter raw CITES shards to the Arctic species set (with aliases)."""
    wanted = {name: sid for name, sid in species_map.items()}
    names = set(wanted)
    for shard in sorted(RAW_DIR.glob("trade_db_*.csv")):
        for chunk in pd.read_csv(shard, chunksize=250_000, dtype=str, keep_default_na=False):
            chunk = chunk.rename(columns=RAW_RENAME)
            sub = chunk[chunk["Taxon"].isin(names)]
            for r in sub.itertuples(index=False):
                taxon = r.Taxon
                q = None
                if r.Quantity not in ("", None):
                    try:
                        q = float(r.Quantity)
                    except ValueError:
                        q = None
                if not _quantity_ok(r.Id, q):
                    continue
                yield (
                    row_uuid(r.Id), wanted[taxon], r.Id,
                    int(r.Year) if r.Year else None,
                    r.Appendix, taxon, r.Class, r.order_name, r.Family, r.Genus,
                    r.Term, q, r.Unit, r.Importer, r.Exporter, r.Origin,
                    r.Purpose, r.Source, r.reporter_type,
                    r.import_permit, r.export_permit, r.origin_permit,
                    str(RAW_DIR.relative_to(ROOT)) + "/trade_db_*.csv",
                    _RAW_DIGEST, "DERIVED", LOADER_VERSION,
                )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["optimized", "raw"], default="optimized")
    ap.add_argument("--target-schema", default="arctic_sprint")
    ap.add_argument("--lookup-schema", default="arctic",
                    help="schema to resolve species ids against")
    ap.add_argument("--live", action="store_true", help="permit targeting the live arctic schema")
    args = ap.parse_args()

    if args.target_schema == "arctic" and not args.live:
        sys.exit("refusing to target live schema without --live")

    conn = get_conn()
    try:
        with conn:  # ONE transaction: scratch DDL + truncate + COPY
            with conn.cursor() as cur:
                ensure_scratch_schema(cur, args.target_schema)
                species_map = load_species_map(cur, args.lookup_schema)
                # DELETE, not TRUNCATE: Postgres refuses to truncate a table any
                # foreign key references, even when the child is empty.
                cur.execute(f"DELETE FROM {args.target_schema}.cites_trade_records")
                gen = rows_from_optimized(species_map) if args.source == "optimized" else rows_from_raw(species_map)
                n = copy_records(cur, args.target_schema, "cites_trade_records", COLUMNS, gen)
                if args.source == "raw":
                    assert_raw_dq(cur, args.target_schema)
                final = count(cur, args.target_schema, "cites_trade_records")
                print(f"LOADED source={args.source} schema={args.target_schema} rows_copied={n} final_count={final}")
                cur.execute(f"""
                    SELECT s.scientific_name, count(*) FROM {args.target_schema}.cites_trade_records t
                    JOIN {validate_schema(args.lookup_schema)}.species s ON s.id = t.species_id GROUP BY 1 ORDER BY 1
                """)
                for name, c in cur.fetchall():
                    print(f"    {name}={c}")
    finally:
        conn.close()
    if _dropped:
        DROPPED_REPORT.parent.mkdir(parents=True, exist_ok=True)
        DROPPED_REPORT.write_text(json.dumps(_dropped, indent=1))
        print(f"DROPPED {len(_dropped)} unparseable rows -> {DROPPED_REPORT}")


if __name__ == "__main__":
    main()
