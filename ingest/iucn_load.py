#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""IUCN assessment ingest — psycopg2, transactional, idempotent.

Source: species_data/iucn/iucn_assessments_snapshot_2026-07-22.csv — a frozen
snapshot of the live `arctic.iucn_assessments` (370 rows), exported 2026-07-22.
The live table was itself built from the IUCN Red List API (validated, 2025-11
vintage); deposit/rebuild_iucn.py and deposit/REBUILD-IUCN.md document how to
rebuild the assessments from the API.

This loader is the deterministic replay path (G4). The snapshot is checksum-
pinned: EXPECTED_SNAPSHOT_SHA256 must match or the load hard-fails before
touching the database — a corrupted or swapped snapshot can never silently
produce a green load. The H2 refresh path re-runs the validated API rebuild,
produces a NEW snapshot, and any divergence vs the frozen signed baseline
(iucn_status_set, iucn_latest_hash — the two allowlisted keys) is documented
before/after.

Row uuids are uuid5(species_id|assessment_id) — deterministic. One transaction
(truncate + COPY + invariant assertions), so a violated invariant rolls the
whole load back.
"""
import argparse
import pathlib
import csv
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema, get_conn, ensure_scratch_schema, copy_records, count, sha256_file

ROOT = Path(__file__).parent.parent
SNAPSHOT = ROOT / "species_data/iucn/iucn_assessments_snapshot_2026-07-22.csv"

# sha256 of the committed replay snapshot (pin updated only with a new,
# documented snapshot vintage — recorded in the run manifest).
EXPECTED_SNAPSHOT_SHA256 = "8302ab75c25d20ca28003f16d2038e24698800415ded048b213c1b620e9e54ef"

UUID_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

COLUMNS = ["id", "species_id", "year_published", "is_latest", "possibly_extinct",
           "possibly_extinct_in_wild", "status", "url", "assessment_id",
           "scope_code", "scope_description"] + ["source_artifact", "source_sha256", "provenance_class", "loader_version"]


def parse_bool(v, field, aid):
    """Strict bool parse — anything outside {'True','False'} is a data error,
    not a silent False (the old `== 'True'` mapped 'true'/'1'/'t' to False)."""
    if v == "True":
        return True
    if v == "False":
        return False
    raise ValueError(f"iucn snapshot: unparseable bool {v!r} in {field} (assessment_id={aid})")


def assert_latest_invariants(cur, schema):
    """Exactly one is_latest per species, and it must be the newest assessment
    (tie-break: max assessment_id). Runs in-transaction: violation = rollback."""
    cur.execute(f"""
        WITH flagged AS (
            SELECT species_id, count(*) FILTER (WHERE is_latest) AS n_latest,
                   max(year_published) AS max_year
            FROM {schema}.iucn_assessments GROUP BY species_id
        ),
        bad_count AS (SELECT species_id FROM flagged WHERE n_latest <> 1),
        bad_pick AS (
            SELECT a.species_id FROM {schema}.iucn_assessments a
            WHERE a.is_latest AND (a.year_published, a.assessment_id) < (
                SELECT max(b.year_published),
                       max(b.assessment_id) FILTER (WHERE b.year_published = (
                           SELECT max(c.year_published) FROM {schema}.iucn_assessments c
                           WHERE c.species_id = a.species_id))
                FROM {schema}.iucn_assessments b WHERE b.species_id = a.species_id)
        )
        SELECT (SELECT count(*) FROM bad_count), (SELECT count(*) FROM bad_pick)
    """)
    n_bad_count, n_bad_pick = cur.fetchone()
    assert n_bad_count == 0, f"{n_bad_count} species without exactly one is_latest flag"
    assert n_bad_pick == 0, f"{n_bad_pick} species whose is_latest is not the newest assessment"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-schema", default="arctic_sprint")
    ap.add_argument("--lookup-schema", default="arctic",
                    help="schema whose species table the snapshot's species_id values belong to; "
                         "ids are remapped by scientific_name when it differs from --target-schema")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    # OFF BY DEFAULT, deliberately. Applying it changes a published number
    # (the right whale's trajectory, 12/20/8 to 12/19/9), and that is the
    # authors' decision on how regional assessments recorded without a scope
    # are read. The snapshot stays as IUCN's export gave it; the
    # correction is a curated layer over it, applied on load so a rebuild
    # reproduces it, and each corrected row says so in its provenance.
    ap.add_argument("--apply-scope-corrections", action="store_true",
                    help="mark the assessments in species_data/curated/"
                         "iucn_scope_corrections.csv with the regional scope their "
                         "evidence shows (default: load the snapshot as exported)")
    args = ap.parse_args()
    if args.target_schema == "arctic" and not args.live:
        sys.exit("refusing to target live schema without --live")

    snapshot_sha = sha256_file(args.snapshot)
    if snapshot_sha != EXPECTED_SNAPSHOT_SHA256:
        sys.exit(f"IUCN snapshot checksum mismatch: {args.snapshot} sha256={snapshot_sha} "
                 f"!= pinned {EXPECTED_SNAPSHOT_SHA256}. Refusing to load — commit and pin "
                 f"a new snapshot vintage deliberately, never silently.")

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                ensure_scratch_schema(cur, args.target_schema)

                # The snapshot carries species_id values from --lookup-schema.
                # When loading into a rebuilt schema those uuids do not exist,
                # so translate via scientific_name. Identity map when the two
                # schemas are the same.
                cur.execute(f"SELECT id, scientific_name FROM {validate_schema(args.lookup_schema)}.species")
                by_old = {str(i): n for i, n in cur.fetchall()}
                cur.execute(f"SELECT scientific_name, id FROM {validate_schema(args.target_schema)}.species")
                by_name = {n: str(i) for n, i in cur.fetchall()}
                remap = {}
                for old_id, name in by_old.items():
                    new_id = by_name.get(name)
                    if new_id:
                        remap[old_id] = new_id
                unmapped = set()

                def gen():
                    with open(args.snapshot, newline="", encoding="utf-8") as f:
                        for row in csv.DictReader(f):
                            sid = remap.get(row["species_id"])
                            if sid is None:
                                unmapped.add(row["species_id"])
                                continue
                            aid = row["assessment_id"]
                            yield (
                                str(uuid.uuid5(UUID_NS, f"iucn_assessments:{sid}:{aid}")),
                                sid,
                                int(row["year_published"]) if row["year_published"] else None,
                                parse_bool(row["is_latest"], "is_latest", aid),
                                parse_bool(row["possibly_extinct"], "possibly_extinct", aid),
                                parse_bool(row["possibly_extinct_in_wild"], "possibly_extinct_in_wild", aid),
                                row["status"], row["url"] or None,
                                int(aid) if aid else None,
                                row["scope_code"] or None, row["scope_description"] or None,
                                # Provenance travels with every row; the NOT NULL
                                # constraints in v2 make a load without it impossible.
                                str(args.snapshot), snapshot_sha, "DERIVED",
                                "iucn_load/1.1",
                            )

                # DELETE, not TRUNCATE: Postgres refuses to truncate a table any
                # foreign key references, even when the child is empty.
                cur.execute(f"DELETE FROM {args.target_schema}.iucn_assessments")
                n = copy_records(cur, args.target_schema, "iucn_assessments", COLUMNS, gen())
                if args.apply_scope_corrections:
                    corrections = pathlib.Path(__file__).resolve().parent.parent / \
                        "species_data" / "curated" / "iucn_scope_corrections.csv"
                    with open(corrections, newline="", encoding="utf-8") as f:
                        fixes = list(csv.DictReader(f))
                    for fx in fixes:
                        cur.execute(
                            f"UPDATE {args.target_schema}.iucn_assessments "
                            f"SET scope_code = %s, scope_description = %s, "
                            f"provenance_class = 'CURATED', "
                            f"source_artifact = source_artifact || ' + ' || %s "
                            f"WHERE assessment_id = %s AND scope_code IS NULL",
                            (fx["corrected_scope_code"], fx["corrected_scope_description"],
                             str(corrections.relative_to(corrections.parent.parent.parent)),
                             int(fx["assessment_id"])))
                        if cur.rowcount != 1:
                            sys.exit(f"FAIL: scope correction for assessment "
                                     f"{fx['assessment_id']} matched {cur.rowcount} rows, "
                                     f"not 1; refusing to load a partial correction")
                    print(f"APPLIED {len(fixes)} curated scope corrections from {corrections.name}")
                assert_latest_invariants(cur, args.target_schema)
                final = count(cur, args.target_schema, "iucn_assessments")
                cur.execute(f"SELECT count(*) FILTER (WHERE is_latest) FROM {args.target_schema}.iucn_assessments")
                latest = cur.fetchone()[0]
                print(f"LOADED iucn schema={args.target_schema} rows_copied={n} final_count={final} "
                      f"is_latest={latest} snapshot_sha256={snapshot_sha[:12]}…")
                if unmapped:
                    # Never silent: an unmappable species means rows were dropped.
                    sys.exit(f"FAIL: {len(unmapped)} species_id values in the snapshot have no "
                             f"counterpart in {args.target_schema}.species; rows were dropped")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
