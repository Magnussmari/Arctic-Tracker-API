#!/usr/bin/env python3
"""Load the rebuilt IUCN Red List categories into a database built from this deposit.

The deposit ships iucn_assessments empty, because IUCN's terms forbid
redistributing Red List categories. load_deposit.sh therefore leaves the table
empty, and the figure pipeline (`make reproduce`) needs it filled. This script
fills it from two inputs a reader already holds after the rebuild step:

  identifiers/iucn_assessment_ids.csv   species, year, assessment id, scope,
                                        is_latest: the rows as the paper used them
  rebuilt/iucn_categories.json          {assessment_id: category}, written by
                                        rebuild_iucn.py from IUCN's own API

Row ids are uuid5 over the species id and the assessment id, the same rule the
project's own loader uses, so the table is identical to the one the paper was
computed on wherever the categories are.

An assessment IUCN has withdrawn since the snapshot has no category to load. It
is named and left out rather than guessed; pass one you obtained from IUCN with
--add ID=CODE, as for rebuild_iucn.py.

    ARCTIC_DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db> \\
        python3 deposit/load_iucn_categories.py

Exit 0 when every identifier has a category, 1 when some were left out, 3 when
it could not run.
"""
import argparse
import csv
import hashlib
import json
import os
import pathlib
import sys
import uuid

HERE = pathlib.Path(__file__).resolve().parent
IDENT = HERE / "identifiers" / "iucn_assessment_ids.csv"
CATEGORIES = HERE / "rebuilt" / "iucn_categories.json"
UUID_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
LOADER_VERSION = "load_iucn_categories 1.0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default=os.environ.get("ARCTIC_SCHEMA", "arctic_v2"))
    ap.add_argument("--categories", default=str(CATEGORIES))
    ap.add_argument("--add", action="append", default=[], metavar="ID=CODE")
    args = ap.parse_args()

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("  ARCTIC_DATABASE_URL is not set", file=sys.stderr)
        return 3
    cat_path = pathlib.Path(args.categories)
    if not cat_path.exists():
        print(f"  {cat_path} is missing: run rebuild_iucn.py first", file=sys.stderr)
        return 3
    categories = json.loads(cat_path.read_text(encoding="utf8"))
    for pair in args.add:
        aid, _, code = pair.partition("=")
        categories[aid.strip()] = code.strip()

    import psycopg2

    rows = list(csv.DictReader(IDENT.open(newline="", encoding="utf8")))
    ident_sha = hashlib.sha256(IDENT.read_bytes()).hexdigest()
    source = "identifiers/iucn_assessment_ids.csv + IUCN Red List API (rebuild_iucn.py)"

    conn = psycopg2.connect(url)
    loaded, left_out = 0, []
    with conn, conn.cursor() as cur:
        cur.execute(f"SELECT scientific_name, id FROM {args.schema}.species")
        species = dict(cur.fetchall())
        cur.execute(f"DELETE FROM {args.schema}.iucn_assessments")
        for r in rows:
            aid = r["assessment_id"].strip()
            code = categories.get(aid, "")
            if not code:
                left_out.append(r)
                continue
            sid = species.get(r["scientific_name"])
            if sid is None:
                print(f"  {r['scientific_name']} is not in the species table",
                      file=sys.stderr)
                return 3
            cur.execute(
                f"INSERT INTO {args.schema}.iucn_assessments (id, species_id, "
                f"year_published, is_latest, status, url, assessment_id, "
                f"scope_code, scope_description, source_artifact, source_sha256, "
                f"provenance_class, loader_version) VALUES "
                f"(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'DERIVED',%s)",
                (str(uuid.uuid5(UUID_NS, f"iucn_assessments:{sid}:{aid}")), sid,
                 int(r["year_published"]), r["is_latest"] == "True", code,
                 r["redlist_url"], int(aid), r["scope_code"] or None,
                 r["scope"] or None, source, ident_sha, LOADER_VERSION))
            loaded += 1
    conn.close()

    print(f"  loaded {loaded} of {len(rows)} assessments into "
          f"{args.schema}.iucn_assessments")
    if left_out:
        print("  left out, no category (withdrawn by IUCN since the snapshot; "
              "see REBUILD-IUCN.md):", file=sys.stderr)
        for r in left_out:
            print(f"    {r['scientific_name']}, {r['year_published']}, "
                  f"{r['scope'] or 'Global'}: assessment {r['assessment_id']}",
                  file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
