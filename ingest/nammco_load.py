#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""NAMMCO catch ingest — psycopg2, transactional, idempotent.

Source: species_data/nammco/*_catches_2025-06-11.csv (18 marine-mammal species,
Selenium scrape of NAMMCO catch database, 2025-06-11 vintage — H7 documents
coverage bounds; the scraper itself was lost in the Oct-2025 repo cleanup).
Target: catch_records. One transaction (truncate + COPY). Re-runs are no-ops.

Verification anchor: catch_total_sum must equal the frozen baseline (277,663)
when run against the same CSV vintage — it is a never-diverge key in the
reconciliation gate.

Data-quality rules (documented in H7 + table_spec.py):
- Year/season values: the FIRST 4-digit year is taken ("2004/2005" -> 2004).
  Rows with no 4-digit year are skipped and reported (nammco_skipped_rows.json).
- No-catch sentinels: '*No reported catches' is an explicit zero report and is
  loaded as 0. 'N/A' and '' mean UNKNOWN (no data reported), loaded as NULL —
  unknown is not zero. Sentinel counts are reported in the run manifest.
- num() validates with a strict regex; malformed numerics load as NULL with a
  logged warning (a multi-dot value like '1.5.2' previously crashed the load).
- Row ids are uuid5 of the natural key (species_id|year|area|country|source)
  plus a per-key occurrence index — deterministic across runs; duplicate
  natural keys (2 documented double-reports) are counted in the manifest.
- Rows whose species is not in the Arctic species map are skipped AND
  reported (previously silently dropped).
"""
import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema, get_conn, ensure_scratch_schema, copy_records, load_species_map, count, sha256_file

ROOT = Path(__file__).parent.parent
NAMMCO_DIR = ROOT / "species_data/nammco"
SKIPPED_REPORT = ROOT / "ingest/reports/nammco_skipped_rows.json"

CATCH_SUM_EXPECTED = 277_663  # frozen signed baseline (never-diverge key)

COLUMNS = ["species_id", "year", "area", "catch_total", "quota", "source",
           "country_id", "data_source"]

_NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
ZERO_SENTINELS = {"*no reported catches"}       # explicit zero report -> 0
NULL_SENTINELS = {"n/a", "no quota", "none", "-"}  # documented unknown/absent -> NULL

_skipped = []
_bad_numerics = []
_unmapped = []
_comments = []
_blank_rows = 0
_sentinel_zeros = 0
_sentinel_nulls = collections.Counter()


def num(v, context):
    """Parse a NAMMCO numeric; documented sentinels -> NULL (counted);
    anything else malformed -> NULL-with-log."""
    v = (v or "").strip().replace(",", "")
    if not v:
        return None
    if v.lower() in NULL_SENTINELS:
        _sentinel_nulls[context.get("column", "?") + ":" + v] += 1
        return None
    if _NUM_RE.match(v):
        return int(float(v))
    _bad_numerics.append({"value": v, **context})
    return None


def rows_from_csvs(cur, lookup_schema: str = "arctic"):
    global _sentinel_zeros, _blank_rows
    # country name -> id (catch_records.country_id)
    cur.execute(f"SELECT id, country_name, country_code FROM {validate_schema(lookup_schema)}.countries")
    cmap = {}
    for cid, name, code in cur.fetchall():
        if name:
            cmap[name.lower()] = str(cid)
        if code:
            cmap[code.lower()] = str(cid)
    species_map = load_species_map(cur, lookup_schema)
    n_files = 0
    key_occurrence = collections.Counter()
    duplicates = 0
    for path in sorted(NAMMCO_DIR.glob("*_catches_2025-06-11.csv")):
        n_files += 1
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                sci = (row.get("SPECIES (SCIENTIFIC NAME)") or "").strip()
                first_val = next((v or "").strip() for v in row.values())
                if first_val.startswith("#"):
                    # Scraper comment lines — e.g. "# No catch records found
                    # for Balaenoptera musculus" documents an EMPTY species.
                    _comments.append({"file": path.name, "comment": first_val})
                    continue
                if not sci and not any((v or "").strip() for v in row.values()):
                    _blank_rows += 1
                    continue  # trailing blank line in the export
                species_id = species_map.get(sci)
                if not species_id:
                    _unmapped.append({"species": sci, "file": path.name,
                                      "year_or_season": (row.get("YEAR OR SEASON") or "").strip()})
                    continue
                year_raw = (row.get("YEAR OR SEASON") or "").strip()
                # The original load took the FIRST 4-digit year of season/range
                # values ("2004/2005" -> 2004, "1992-1995" -> 1992). Rows with
                # NO 4-digit year are skipped with a log (H7).
                year = None
                toks = [t for t in year_raw.replace("/", " ").replace("-", " ").split() if t.isdigit() and len(t) == 4]
                if toks:
                    year = int(toks[0])
                else:
                    _skipped.append({"species": sci, "year_or_season": year_raw,
                                     "area": (row.get("AREA OR STOCK") or "").strip(),
                                     "reason": "no parseable year"})
                    continue
                catch_raw = (row.get("CATCH TOTAL") or "").strip()
                ctx = {"species": sci, "year": year, "file": path.name}
                if catch_raw.lower() in ZERO_SENTINELS:
                    catch = 0
                    _sentinel_zeros += 1
                else:
                    catch = num(catch_raw, {**ctx, "column": "catch_total"})
                quota = num(row.get("QUOTA (IF APPLICABLE)"), {**ctx, "column": "quota"})
                country = (row.get("COUNTRY") or "").strip().lower()
                if country and country not in cmap:
                    _bad_numerics.append({"value": country, "column": "country (unmapped)", **ctx})
                area = (row.get("AREA OR STOCK") or "").strip()
                natkey = f"{species_id}|{year}|{area}|{country}|NAMMCO"
                key_occurrence[natkey] += 1
                occ = key_occurrence[natkey]
                if occ > 1:
                    duplicates += 1
                yield (
                    species_id, year, area, catch, quota,
                    "NAMMCO", cmap.get(country), "NAMMCO",
                )
    print(f"  nammco csv files: {n_files}; duplicate natural keys: {duplicates}")
    return {"files": n_files, "duplicates": duplicates}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-schema", default="arctic_sprint")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    if args.target_schema == "arctic" and not args.live:
        sys.exit("refusing to target live schema without --live")

    input_hashes = {p.name: sha256_file(p)
                    for p in sorted(NAMMCO_DIR.glob("*_catches_2025-06-11.csv"))}

    conn = get_conn()
    stats = {}
    try:
        with conn:
            with conn.cursor() as cur:
                ensure_scratch_schema(cur, args.target_schema)
                # DELETE, not TRUNCATE: Postgres refuses to truncate a table any
                # foreign key references, even when the child is empty.
                cur.execute(f"DELETE FROM {args.target_schema}.catch_records")
                n = copy_records(cur, args.target_schema, "catch_records", COLUMNS, rows_from_csvs(cur))
                final = count(cur, args.target_schema, "catch_records")
                cur.execute(f"SELECT coalesce(sum(catch_total),0), "
                            f"count(*) FILTER (WHERE catch_total = 0), "
                            f"count(*) FILTER (WHERE catch_total IS NULL), "
                            f"count(area), count(quota) FROM {args.target_schema}.catch_records")
                total, zeros, nulls, areas, quotas = cur.fetchone()
                # Never-diverge anchor: frozen baseline sum must hold for this vintage.
                assert total == CATCH_SUM_EXPECTED, (
                    f"catch_total_sum {total} != frozen baseline {CATCH_SUM_EXPECTED} — "
                    f"source vintage changed or loader corrupted the parse")
                stats = {"rows_copied": n, "final_count": final, "catch_total_sum": total,
                         "explicit_zeros": zeros, "null_catch": nulls,
                         "sentinel_zeros_mapped": _sentinel_zeros,
                         "area_populated": areas, "quota_populated": quotas}
                print(f"LOADED nammco schema={args.target_schema} rows_copied={n} final_count={final} "
                      f"catch_total_sum={total} zeros={zeros} (sentinel-mapped={_sentinel_zeros}) "
                      f"nulls={nulls} area={areas} quota={quotas}")
    finally:
        conn.close()
    SKIPPED_REPORT.parent.mkdir(parents=True, exist_ok=True)
    SKIPPED_REPORT.write_text(json.dumps({
        "no_parseable_year": _skipped,
        "unmapped_species": _unmapped,
        "malformed_values_loaded_null": _bad_numerics,
        "blank_rows_skipped": _blank_rows,
        "scraper_comments": _comments,
        "documented_null_sentinels": dict(_sentinel_nulls),
    }, indent=1) + "\n")
    print(f"SKIPPED {len(_skipped)} no-year + {len(_unmapped)} unmapped-species + "
          f"{len(_bad_numerics)} malformed -> {SKIPPED_REPORT}")
    return {"input_hashes": input_hashes, **stats}


if __name__ == "__main__":
    main()
