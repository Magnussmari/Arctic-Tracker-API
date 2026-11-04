#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-11
"""V-12: the listing table must match the official CITES event history.

A table can be faithfully loaded from the project's own file and still be
wrong if the file is. The earlier cites_listings table was short by 40 listing
events across 25 of 40 species and stored Party reservations as listings, which
only a comparison against the authority can detect.

This gate compares arctic_v2.cites_listing_events against the Species+ snapshot,
per species, on both counts. It fails on any divergence.

It self-tests first: it seeds a species with a deliberately wrong count and
requires detection, because a comparison that silently matches nothing looks
exactly like a clean bill of health. That failure mode occurred three times in
this project on 11 August alone.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "ingest/reports/speciesplus_listings.json"
LISTING = {"a", "x"}


def compare(expected: dict, actual: dict):
    """expected/actual: species -> (listings, reservations). Returns divergences."""
    out = []
    for sp, (el, er) in expected.items():
        al, ar = actual.get(sp, (None, None))
        if (al, ar) != (el, er):
            out.append((sp, (el, er), (al, ar)))
    for sp in actual:
        if sp not in expected:
            out.append((sp, None, actual[sp]))
    return out


def self_test() -> bool:
    exp = {"A": (3, 5), "B": (1, 0)}
    if not compare(exp, {"A": (2, 5), "B": (1, 0)}):
        print("SELF-TEST FAIL: a wrong count was not detected"); return False
    if not compare(exp, {"A": (3, 5)}):
        print("SELF-TEST FAIL: a missing species was not detected"); return False
    if compare(exp, dict(exp)):
        print("SELF-TEST FAIL: identical inputs reported a divergence"); return False
    print("self-test: wrong count, missing species and clean case all behave\n")
    return True


def main() -> int:
    if not self_test():
        return 2
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set")
    if not SRC.exists():
        print(f"no Species+ snapshot at {SRC}; run ingest/speciesplus_listings.py")
        return 2

    data = json.loads(SRC.read_text())
    expected = {n: (len(v["listing_events"]), len(v["reservation_events"]))
                for n, v in data.items()}

    conn = psycopg2.connect(url); cur = conn.cursor()
    cur.execute("""select s.scientific_name,
                          count(*) filter (where e.is_listing),
                          count(*) filter (where not e.is_listing)
                   from arctic_v2.cites_listing_events e
                   join arctic_v2.species s on s.id = e.species_id
                   group by 1""")
    actual = {n: (a, b) for n, a, b in cur.fetchall()}
    conn.close()

    if not actual:
        print("FAIL: the table is empty. That is a load failure, not agreement.")
        return 1

    div = compare(expected, actual)
    print(f"V-12 listing events, {len(expected)} species in the Species+ snapshot")
    if div:
        print(f"\nFAIL: {len(div)} species diverge from the official record\n")
        for sp, e, a in div[:15]:
            print(f"  {sp:32} expected {e}  actual {a}")
        return 1
    tot = sum(l for l, _ in expected.values())
    print(f"V-12 PASS: {tot} listing events match Species+ exactly, "
          f"reservations counted separately")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
