#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-11
"""Rebuild CITES listing history from Species+, separating listings from reservations.

WHY
---
Our cites_listings table holds 62 rows for 43 species and conflates two different
kinds of event. Verified examples found on 2026-08-11:

  - the 2000-04-02 rows on Balaenoptera physalus, B. borealis and Megaptera
    novaeangliae are ICELAND'S RESERVATIONS on re-accession, not listings
  - the 1996-06-10 row on Falco rusticolus is SAUDI ARABIA'S RESERVATION
  - Falco rusticolus is missing App II (1975, via Falconidae spp.), the 1979
    uplisting to App I, and the 1981 population split entirely

A reservation is a Party declining to be bound. It does not move a species
between appendices. Treating one as a listing corrupts both the listing-date
covariate and the appendix covariate, and four of our five checked species had
a real appendix change that our table did not contain.

Species+ is the official UNEP-WCMC/CITES database and distinguishes them:
change_type is 'ADDITION', 'DELETION', 'RESERVATION', 'RESERVATION_WITHDRAWAL'
or 'TRANSFER'. This reads that field rather than guessing from a note.

Usage:
  ./.venv/bin/python ingest/speciesplus_listings.py            # fetch + report
  ./.venv/bin/python ingest/speciesplus_listings.py --diff     # compare to ours
"""
from __future__ import annotations
import argparse, json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ingest/reports/speciesplus_listings.json"
API = "https://speciesplus.net/api/v1/taxon_concepts"
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")
UA = {"User-Agent": "ArcticTracker/2.0 (research; +https://doi.org/10.5281/zenodo.23578786"
      + (f"; mailto:{CONTACT_EMAIL}" if CONTACT_EMAIL else "") + ")"}
PAUSE = 0.8

# Species+ returns SINGLE-LETTER change types, not words:
#   a = addition        r = reservation
#   w = reservation withdrawal    x = deletion
# The first version of this script filtered on {"ADDITION","DELETION","TRANSFER"},
# matched nothing, and classified all 273 events as reservations without failing.
# Verified against the live API: {'a': 98, 'r': 107, 'w': 67, 'x': 1}.
LISTING_EVENTS = {"a", "x"}
RESERVATION_EVENTS = {"r", "w"}


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))


# CITES knows three of our species only under other names. Species+ returns
# nothing for the modern binomial, which is exactly why the alias map exists.
CITES_NAME = {
    "Branta hutchinsii": "Branta canadensis leucopareia",
    "Bubo scandiacus": "Nyctea scandiaca",
    "Grus canadensis": "Antigone canadensis",
}


def find_id(name):
    name = CITES_NAME.get(name, name)
    # The search parameter is taxon_concept_query. "name" is ignored and
    # silently returns the first 25 concepts alphabetically, which is how a
    # wrong parameter looks exactly like a failed lookup.
    q = f"{API}?" + urllib.parse.urlencode({"taxon_concept_query": name})
    try:
        d = get(q)
    except Exception as exc:
        print(f"  !! {name}: {exc}")
        return None
    for tc in d.get("taxon_concepts") or []:
        if (tc.get("full_name") or "").lower() == name.lower() and tc.get("rank") in (None, "SPECIES"):
            return tc.get("id")
    for tc in d.get("taxon_concepts") or []:
        if (tc.get("full_name") or "").lower() == name.lower():
            return tc.get("id")
    return None


def self_test() -> bool:
    """Prove the lookup works before trusting a run of it.

    The first version of this script passed `name=` to the search endpoint.
    Species+ ignores unknown parameters and returns the first 25 concepts
    alphabetically, so every lookup "succeeded" and every name failed to match.
    43 of 43 species came back not-found and the script exited 0. A wrong
    parameter is indistinguishable from a missing species unless you seed a
    known answer.
    """
    known = {"Odobenus rosmarus": 9179, "Falco rusticolus": 7821}
    for name, expect in known.items():
        got = find_id(name)
        time.sleep(PAUSE)
        if got != expect:
            print(f"SELF-TEST FAIL: {name} resolved to {got}, expected {expect}")
            return False
    print(f"self-test: {len(known)} known ids resolve correctly\n")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--species-file", default=str(ROOT / "ingest/reports/our43.txt"))
    args = ap.parse_args()
    names = [l.strip() for l in open(args.species_file) if l.strip()]

    if not self_test():
        print("refusing to run: a lookup that cannot find a known species")
        return 2

    result, missing = {}, []
    for n in names:
        tid = find_id(n); time.sleep(PAUSE)
        if not tid:
            missing.append(n); print(f"  --   {n}: not found"); continue
        try:
            d = get(f"{API}/{tid}")["taxon_concept"]
        except Exception as exc:
            print(f"  !! {n}: {exc}"); missing.append(n); continue
        time.sleep(PAUSE)
        ev = []
        for L in d.get("cites_listings") or []:
            ev.append({
                "date": L.get("effective_at_formatted"),
                "appendix": L.get("species_listing_name"),
                "change_type": L.get("change_type"),
                "party": L.get("party_full_name"),
                "is_current": L.get("is_current"),
                "note": L.get("full_note_en") or L.get("short_note_en") or L.get("auto_note"),
            })
        listings = [e for e in ev if (e["change_type"] or "").lower() in LISTING_EVENTS]
        reserv = [e for e in ev if (e["change_type"] or "").lower() in RESERVATION_EVENTS]
        unknown = [e for e in ev if (e["change_type"] or "").lower()
                   not in LISTING_EVENTS | RESERVATION_EVENTS]
        if unknown:
            print(f"       !! {len(unknown)} unclassified change_type(s): "
                  f"{sorted({e['change_type'] for e in unknown})}")
        result[n] = {"taxon_concept_id": tid, "events": ev,
                     "listing_events": listings, "reservation_events": reserv}
        print(f"  ok   {n:34} {len(listings):>2} listing, {len(reserv):>2} reservation")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1))
    tl = sum(len(v["listing_events"]) for v in result.values())
    tr = sum(len(v["reservation_events"]) for v in result.values())
    if len(missing) > len(names) // 4:
        print(f"\nFAIL: {len(missing)} of {len(names)} not found. That is too many to be")
        print("real; suspect the query rather than the species list.")
    print(f"\n{len(result)} species resolved, {len(missing)} not found")
    print(f"{tl} genuine listing events, {tr} reservation events")
    if tl == 0 or tr == 0:
        print("FAIL: one bucket is empty, which means the classifier is wrong,")
        print("not that the data is one-sided.")
        return 1
    print(f"our cites_listings table holds 62 rows in total, which cannot be right")
    print(f"-> {OUT}")
    if missing:
        print("not found:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
