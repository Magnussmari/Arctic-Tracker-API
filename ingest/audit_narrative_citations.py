#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-28
"""Audit the citations embedded in species narrative prose.

The `arctic.species` table carries eight free-text narrative fields that render
on the public species pages. Each was machine-generated and each contains inline
author-year citations. Those citations live in prose, NOT in the `references`
table, so:

  - they carry no DOI, no title, and no link;
  - they were never covered by the H1 reference repair (which fixed
    `profile_references`, a different and much smaller surface);
  - nothing binds them to the species the page is about, which is exactly the
    failure mode that produced the wrong-species references R1 caught.

This audit quantifies that surface. It does NOT attempt to judge whether a given
citation is correct: that requires resolving each one against Crossref and a
species-relevance check, which is the repair, not the measurement. Conflating
the two would repeat the mistake of letting a machine grade its own output.

Read-only by construction.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/audit_narrative_citations.py \
      [--schema arctic] [--json OUT.json]
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

import psycopg2

# The narrative fields. Named explicitly rather than discovered, so that a new
# column cannot silently escape the audit or silently join it.
NARRATIVE_FIELDS = [
    "description",
    "habitat_description",
    "movement_patterns",
    "use_and_trade",
    "threats_overview",
    "conservation_overview",
    "population_size",
    "population_trend",
]

# Author-year citations as they actually appear in this corpus. Handles the
# unicode hyphens (U+2010/U+2011) and accented names present in the data, plus
# "A & B, 2019" and "A et al., 2019" forms. Validated against the raw
# parenthetical spans before use; see --show-samples.
NAME = r"[A-Z][A-Za-zÀ-ÿ‐‑’'-]+"
CITATION = re.compile(
    rf"({NAME}(?:\s+(?:&|and)\s+{NAME})?(?:\s+et\s+al\.?)?),?\s*(\d{{4}})"
)

# A year outside this range is almost certainly not a citation (a listing date,
# a population figure, a quantity). Bounds are generous on purpose.
YEAR_MIN, YEAR_MAX = 1850, 2026


def _ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        sys.exit(f"invalid identifier: {name!r}")
    return f'"{name}"'


def extract(text: str) -> set[tuple[str, str]]:
    """Return the distinct (author, year) citations in one narrative field."""
    if not text:
        return set()
    found = set()
    for m in CITATION.finditer(text):
        year = int(m.group(2))
        if YEAR_MIN <= year <= YEAR_MAX:
            found.add((m.group(1).strip(), m.group(2)))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", default="arctic")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--show-samples", type=int, default=0,
                    help="print N species with their raw parentheticals, to eyeball extraction quality")
    args = ap.parse_args()

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")
    try:
        conn = psycopg2.connect(url, connect_timeout=15)
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"connect failed: {type(exc).__name__}: {exc}")
    conn.set_session(readonly=True)
    cur = conn.cursor()

    schema = _ident(args.schema)
    fields = ", ".join(_ident(f) for f in NARRATIVE_FIELDS)
    cur.execute(
        f"select scientific_name, common_name, manual_review, reviewed_by, review_date, {fields} "
        f"from {schema}.species order by scientific_name"
    )
    rows = cur.fetchall()

    per_species = {}
    global_counter = Counter()
    unreviewed = []
    for row in rows:
        name, common, manual_review, reviewed_by, review_date = row[:5]
        texts = row[5:]
        by_field = {}
        species_cites = set()
        for field, text in zip(NARRATIVE_FIELDS, texts):
            cites = extract(text)
            by_field[field] = {
                "chars": len(text or ""),
                "citations": sorted(f"{a} {y}" for a, y in cites),
            }
            species_cites |= cites
        global_counter.update(species_cites)
        reviewed = bool(reviewed_by) or (manual_review or "").lower() in {"yes", "true", "done"}
        if not reviewed:
            unreviewed.append(name)
        per_species[name] = {
            "common_name": common,
            "manual_review": manual_review,
            "reviewed_by": reviewed_by,
            "review_date": review_date.isoformat() if review_date else None,
            "reviewed": reviewed,
            "distinct_citations": len(species_cites),
            "narrative_chars": sum(v["chars"] for v in by_field.values()),
            "fields": by_field,
        }

    # How much of this surface is backed by an actual reference row?
    cur.execute(f"select count(*) from {schema}.references")
    ref_rows = cur.fetchone()[0]

    total_pairs = sum(v["distinct_citations"] for v in per_species.values())
    report = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schema": args.schema,
        "species": len(rows),
        "narrative_fields": NARRATIVE_FIELDS,
        "distinct_citations_global": len(global_counter),
        "species_citation_pairs": total_pairs,
        "mean_citations_per_species": round(total_pairs / len(rows), 2) if rows else 0,
        "reference_table_rows": ref_rows,
        "species_never_reviewed": unreviewed,
        "unreviewed_count": len(unreviewed),
        "single_source_species": sorted(
            n for n, v in per_species.items() if v["distinct_citations"] == 1
        ),
        "zero_citation_species": sorted(
            n for n, v in per_species.items() if v["distinct_citations"] == 0
        ),
        "per_species": per_species,
    }

    print(f"species: {report['species']}")
    print(f"narrative fields per species: {len(NARRATIVE_FIELDS)}")
    print(f"distinct in-prose citations: {report['distinct_citations_global']}")
    print(f"species-citation pairs: {total_pairs} (mean {report['mean_citations_per_species']}/species)")
    print(f"rows in {args.schema}.references: {ref_rows}")
    print(f"\nNEVER REVIEWED BY A HUMAN: {len(unreviewed)} of {len(rows)} species")
    if report["single_source_species"]:
        print(f"\nSINGLE-SOURCE narratives ({len(report['single_source_species'])} species, "
              f"entire narrative rests on one citation):")
        for n in report["single_source_species"]:
            print(f"  {n}")
    if report["zero_citation_species"]:
        print(f"\nZERO-CITATION narratives ({len(report['zero_citation_species'])} species):")
        for n in report["zero_citation_species"]:
            print(f"  {n}")

    if args.show_samples:
        print("\n--- extraction samples (raw parentheticals vs extracted) ---")
        for name in list(per_species)[: args.show_samples]:
            cur.execute(
                f"select threats_overview from {schema}.species where scientific_name = %s", (name,)
            )
            txt = cur.fetchone()[0] or ""
            print(f"\n{name}")
            raw_parens = re.findall(r"\(([^)]{0,110})\)", txt)[:3]
            print(f"  raw:       {raw_parens}")
            print(f"  extracted: {sorted(f'{a} {y}' for a, y in extract(txt))}")

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=1, sort_keys=True)
        print(f"\nwrote {args.json_out}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
