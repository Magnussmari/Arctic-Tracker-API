#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-11
"""Load the corrected CITES event history into arctic_v2.cites_listing_events.

Reads ingest/reports/speciesplus_listings.json, produced by
ingest/speciesplus_listings.py from the official UNEP-WCMC database.

Listings and reservations are distinguished by Species+ change_type:
  a = addition, x = deletion   -> a listing event
  r = reservation, w = withdrawal -> not a listing

The old cites_listings table conflated them and was short by 40 events across
25 of 40 species. It is left in place for the reconciliation gate; this table
supersedes it for analysis.
"""
from __future__ import annotations
import hashlib, json, os, sys
from datetime import datetime
from pathlib import Path
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "ingest/reports/speciesplus_listings.json"
LOADER = "listing_events_load/1.0"
LISTING = {"a", "x"}


def parse_date(s):
    if not s:
        return None
    for f in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set")
    data = json.loads(SRC.read_text())
    digest = hashlib.sha256(SRC.read_bytes()).hexdigest()

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("select scientific_name, id from arctic_v2.species")
    ids = dict(cur.fetchall())

    # DO NOT deduplicate identical-looking events. Falco peregrinus carries FOUR
    # Appendix I additions on 1975-07-01, all with no party and no note, and
    # they are the four subspecies listings rendered at species level.
    # Collapsing them would destroy three real events, and V-12 checks the
    # count against the authority. Identical-looking is not identical when the distinguishing
    # field is one we did not capture.
    rows, unknown = [], []
    for name, v in data.items():
        sid = ids.get(name)
        if not sid:
            unknown.append(name)
            continue
        for e in v["events"]:
            ct = (e.get("change_type") or "").lower()
            rows.append((sid, parse_date(e.get("date")), e.get("appendix"), ct,
                         ct in LISTING, e.get("party"), e.get("is_current"),
                         e.get("note"), v.get("taxon_concept_id"),
                         "speciesplus.net/api/v1/taxon_concepts", digest, LOADER))

    # An advisory lock, because delete-then-insert is not safe under
    # concurrency and on 2026-08-12 two overlapping runs left 580 rows where 290
    # belong: the second transaction's delete saw nothing to remove, then both
    # inserted. V-12 caught it within the minute by comparing against Species+,
    # but the corpus was wrong in the meantime and nothing in this loader would
    # have prevented a third copy.
    cur.execute("select pg_advisory_xact_lock(%s)", (hash("cites_listing_events") % (2**31),))
    cur.execute("delete from arctic_v2.cites_listing_events")
    cur.executemany(
        """insert into arctic_v2.cites_listing_events
           (species_id, event_date, appendix, change_type, is_listing, party,
            is_current, note, source_taxon_id, source_artifact, source_sha256,
            loader_version)
           values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", rows)
    conn.commit()

    cur.execute("select count(*), count(*) filter (where is_listing) from arctic_v2.cites_listing_events")
    tot, lst = cur.fetchone()
    cur.execute("select count(distinct species_id) from arctic_v2.cites_listing_events")
    nsp, = cur.fetchone()
    print(f"loaded {tot} events for {nsp} species: {lst} listings, {tot-lst} reservations")
    if unknown:
        print("no species row for:", ", ".join(unknown))
    # the check that would have caught the original defect
    cur.execute("""select count(*) from arctic_v2.cites_listing_events
                   where is_listing and change_type not in ('a','x')""")
    bad, = cur.fetchone()
    if bad:
        print(f"FAIL: {bad} rows marked as listings with a reservation change_type")
        return 1
    if lst == 0 or tot == lst:
        print("FAIL: one bucket is empty; the classifier is wrong, not the data")
        return 1
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
