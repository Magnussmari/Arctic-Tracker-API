#!/usr/bin/env python3
"""V-8: what the verification gates actually cover, and what they do not.

WHY THIS EXISTS
---------------
A coverage statement written by hand can describe a smaller thing than it
appears to. For example, V-5 checks five tables and 207 rows (0.04% of the
corpus), none of them tables the manuscript draws a number from; a summary such
as "the database matches the source files" would overstate it. This gate makes
coverage a computed value that fails when it drifts.

WHAT THIS GATE DOES
-------------------
1. Reads the tables actually present in the schema.
2. Compares them against the declared coverage map below.
3. FAILS if a table exists that no one has classified. A new table added without
   a coverage decision is the exact mechanism by which the paper's reproducibility
   claim would silently become false again.
4. Prints the sentence the Methods should contain, computed rather than written,
   so the manuscript and the database cannot disagree.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not verify any data. It verifies that our statements about verification
are accurate. A table listed as STRUCTURAL_ONLY here is not thereby validated;
it is labelled as unvalidated.

Usage:
  ARCTIC_DATABASE_URL=... ./.venv/bin/python ingest/coverage_report.py
  ARCTIC_DATABASE_URL=... ./.venv/bin/python ingest/coverage_report.py --self-test
  ARCTIC_DATABASE_URL=... ./.venv/bin/python ingest/coverage_report.py --methods-sentence
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2

# Importing a sibling here writes __pycache__ INTO the deposit, and
# verify_deposit_accounted.py rejects bytecode in a citable archive. Running
# these scripts in place is the intended use, so the run must not leave
# residue behind, or the archive gate would fail merely because the verifiers
# had been run.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import validate_schema  # noqa: E402


# Tables whose contents are compared against an independent read of their source.
# This is the only class that supports a reproducibility claim about VALUES.
SOURCE_VERIFIED = {
    "species": "V-5 (curated CSV)",
    "countries": "V-5 (curated CSV)",
    "glossary_terms": "V-5 (curated CSV)",
    "illegal_trade_products": "V-5 (curated CSV)",
    "subpopulations": "V-5 (curated CSV)",
    "cites_trade_records": "V-5b (raw shard re-read, count + content digest)",
    "iucn_assessments": "V-5b (raw shard re-read, count + status match)",
}

# Tables covered only by gates that check STRUCTURE or CHANGE, never values
# against source. V-4 proves a reload is deterministic. V-6 proves every
# row-count difference is explained. V-7 proves flags mean what they are named.
# None of the three can see a value that was wrong on the way in and has stayed
# wrong consistently since; this file records that limit.
STRUCTURAL_ONLY = {
    "catch_records": "The Selenium scraper that produced the NAMMCO CSVs was lost in an October 2025 cleanup, so the extraction cannot be re-run. Since 2026-08-13 V-5b re-derives the table from those CSVs using the documented parsing rules, independently of the loader: 958 rows, every species-year group, catch totals agreeing at 277,663.",
    "cites_listings": "Listing dates were ambiguous for 8 species; fixed in the read layer, not source-verified.",
    "cms_listings": "CMS listings and daughter agreements shared one table; split in the read layer.",
    "timeline_events": "Curator-asserted events; a curator's assertion is not a table-checked fact.",
    "illegal_trade_seizures": "694 of 919 source rows were misattributed and are excluded by the documented decontamination rule. Since 2026-08-13 V-5b applies that rule independently of the loader and confirms both the selection (225 kept, per species across 26 species) and the content of every retained row against the source file.",
    "common_names": "Descriptive only. No manuscript number depends on it.",
    "management_areas": "Descriptive only. No manuscript number depends on it.",
    "split_listings": "Derived from cites_listings; correctness pinned by application tests, not by a source gate.",
    "references": "Reference provenance repaired under migration 0010; not source-digested.",
    "profile_references": "Join table. Integrity enforced by foreign keys.",
    "species_narratives": "Machine-drafted prose. Withheld from serving until reviewed; enters no number.",
    "conservation_profiles": "Machine-drafted prose. Withheld from serving until reviewed; enters no number.",
    "cites_listing_events": (
        "Full CITES event history from Species+, listings and reservations "
        "distinguished by change_type. Verified against the official record by "
        "V-12 on every run, which is stronger than a source digest: it compares "
        "against the authority rather than against our own copy of it."
    ),
    "species_media": (
        "Photographs resolved from iNaturalist. Each row carries the source URL and a "
        "SHA-256 of the stored bytes, so an image can be checked against what we saved, "
        "but the remote source is mutable and cannot be re-verified as a frozen artifact. "
        "Enters no manuscript number."
    ),
}

# Human sign-off tables. These are the one class that cannot be regenerated from
# any source, which is why the teardown refuses to touch them.
HUMAN_RECORD = {
    "narrative_review": "Human review verdicts. Irreplaceable; never reloaded.",
    "profile_review": "Human review verdicts. Irreplaceable; never reloaded.",
    "source_releases": (
        "Which upstream release each part of the corpus came from, and how the "
        "date is known. Curator-asserted and deliberately so: the CITES date is "
        "inferred from shard modification times and no download receipt exists, "
        "so there is no artifact to digest it against. Reloading the corpus "
        "would not regenerate it — a copy or a restore would destroy the mtimes "
        "it rests on, which is precisely why it is stored."),
}

# Views in the base schema, not tables. Excluded from coverage accounting.
KNOWN_VIEWS = {"servable_species_narratives", "servable_profile_references"}


def observed_tables(schema: str) -> set[str]:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")
    schema = validate_schema(schema)
    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """select table_name from information_schema.tables
                   where table_schema = %s and table_type = 'BASE TABLE'""",
                (schema,),
            )
            return {r[0] for r in cur.fetchall()}


def classify(present: set[str]) -> tuple[dict, set[str], set[str]]:
    declared = set(SOURCE_VERIFIED) | set(STRUCTURAL_ONLY) | set(HUMAN_RECORD)
    undeclared = present - declared - KNOWN_VIEWS
    missing = declared - present
    return declared, undeclared, missing


def report(schema: str) -> int:
    present = observed_tables(schema)
    _, undeclared, missing = classify(present)

    sv = sorted(t for t in SOURCE_VERIFIED if t in present)
    so = sorted(t for t in STRUCTURAL_ONLY if t in present)
    hr = sorted(t for t in HUMAN_RECORD if t in present)

    print(f"V-8 verification coverage, schema {schema}")
    print(f"  {len(present)} base tables present\n")

    print(f"SOURCE-VERIFIED ({len(sv)}) — values compared against an independent read of source")
    for t in sv:
        print(f"  ok    {t}: {SOURCE_VERIFIED[t]}")

    print(f"\nSTRUCTURAL ONLY ({len(so)}) — NOT value-verified against source")
    for t in so:
        print(f"  note  {t}: {STRUCTURAL_ONLY[t]}")

    print(f"\nHUMAN RECORD ({len(hr)}) — cannot be regenerated from any source")
    for t in hr:
        print(f"  keep  {t}: {HUMAN_RECORD[t]}")

    failed = False
    if undeclared:
        failed = True
        print(f"\nFAIL: {len(undeclared)} table(s) exist with no coverage decision:")
        for t in sorted(undeclared):
            print(f"  ??    {t}")
        print("  Add each to SOURCE_VERIFIED, STRUCTURAL_ONLY or HUMAN_RECORD.")
        print("  An undeclared table is how a reproducibility claim silently becomes false.")
    if missing:
        print(f"\nnote: {len(missing)} declared table(s) are absent from the schema:")
        for t in sorted(missing):
            print(f"  --    {t}")

    pct = 100.0 * len(sv) / max(len(present), 1)
    print(f"\n{'-' * 64}")
    print(f"Source-verified: {len(sv)} of {len(present)} tables ({pct:.1f}%)")
    print("V-8 FAIL" if failed else "V-8 PASS")
    return 1 if failed else 0


def methods_sentence(schema: str) -> int:
    """The claim the Methods may make, computed from the schema rather than written."""
    present = observed_tables(schema)
    sv = sorted(t for t in SOURCE_VERIFIED if t in present)
    so = sorted(t for t in STRUCTURAL_ONLY if t in present)
    print(
        f"Of the {len(present)} tables in the analytical corpus, {len(sv)} are verified "
        f"against an independent read of their source files ({', '.join(sv)}), including "
        f"both tables from which the manuscript's quantitative results derive. The "
        f"remaining {len(so)} are covered by determinism, reconciliation and flag-invariant "
        f"checks but are not value-verified against source, and we identify them as such "
        f"rather than describing the corpus as uniformly validated."
    )
    return 0


def self_test() -> int:
    """Prove the gate can see the thing it claims to detect, before trusting a pass.

    A coverage checker that cannot detect an undeclared table would report a
    clean bill of health on a schema it has never actually examined. So we seed
    a table name that is definitely not declared and require it to be caught.
    """
    print("V-8 self-test: can this gate detect an undeclared table?")
    seeded = {"__seeded_undeclared_table__"} | set(SOURCE_VERIFIED)
    _, undeclared, _ = classify(seeded)
    if "__seeded_undeclared_table__" not in undeclared:
        print("  FAIL: seeded undeclared table was NOT detected.")
        print("  The gate cannot detect undeclared tables, so its PASS is not informative.")
        return 1
    print("  ok: seeded undeclared table was detected")

    clean = set(SOURCE_VERIFIED) | set(STRUCTURAL_ONLY) | set(HUMAN_RECORD)
    _, undeclared_clean, _ = classify(clean)
    if undeclared_clean:
        print(f"  FAIL: a fully-declared set was flagged anyway: {undeclared_clean}")
        return 1
    print("  ok: a fully-declared set produces no false positive")
    print("V-8 self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", default="arctic_v2")
    ap.add_argument("--self-test", action="store_true", help="prove the gate is not blind, then exit")
    ap.add_argument("--methods-sentence", action="store_true", help="print the computed coverage claim")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.methods_sentence:
        return methods_sentence(args.schema)

    # The self-test always runs first. A gate that has not proven its own field
    # of view invalidates its own result, so a self-test failure short-circuits.
    if self_test() != 0:
        print("\nself-test failed; refusing to report coverage")
        return 1
    print()
    return report(args.schema)


if __name__ == "__main__":
    raise SystemExit(main())
