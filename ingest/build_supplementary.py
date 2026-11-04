#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-12
"""Emit the supplementary tables that are derivable from the corpus.

WHY THIS EXISTS
---------------
The manuscript cites nine supplementary tables. Exactly one existed as a file:
results_traceability, which is Supplementary Table 5. The other eight were
described in prose only (for example, "the audit questions have been promoted
out of the figure inset into a dedicated numbered table"); this builds them.

Four of them are pure derivations from the frozen corpus and had no reason to be
waiting on a person. They are generated here, so they exist, so they change when
the corpus changes, and so nobody hand-maintains a copy that drifts.

The rest genuinely need an author, and this script says so by name rather than
emitting a stub that looks finished. A placeholder table is worse than an absent
one: it survives review.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/build_supplementary.py
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT = ROOT / "deposit" / "supplementary"

# Tables this script cannot produce, and the reason. Named individually so the
# gap is a list rather than an absence.
AUTHOR_DEPENDENT = {
    2: "The seven audit questions must be reproduced verbatim. The wording is "
       "the instrument itself and does not exist in the database; it comes from "
       "the authors' questionnaire.",
    3: "Step-to-stage mapping is an editorial statement about the Methods, not a "
       "derivation. It is written in the manuscript text and belongs there.",
    4: "Step-to-question mapping requires the outcome-tier / adoption-tier "
       "partition of Q1-Q7, which is a judgement only a subject author can "
       "make.",
    7: "The LLM toolchain table needs vendor build strings and access dates that "
       "are author-held values, not corpus values.",
}


def rows_to_csv(path: Path, header: list[str], rows: list[tuple]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return len(rows)


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1
    schema = validate_schema(os.environ.get("ARCTIC_SCHEMA", "arctic_v2"))
    S = schema

    conn = psycopg2.connect(url, connect_timeout=60)
    built: list[tuple[int, str, int]] = []
    try:
        with conn, conn.cursor() as cur:
            # --- Supplementary Table 1 -------------------------------------
            # Per-species post-listing window and baseline assessment year.
            # The baseline is the assessment in force at the listing, so the
            # ordering ties on assessment_id: 22 of 43 species have more than
            # one assessment in the same year, and without the tiebreak this
            # table would depend on what the database happened to return.
            #
            # Only 10 of the 43 have any assessment predating their listing —
            # most were listed before the Red List existed in a comparable form.
            # An empty cell would read as missing data, so the reason is stated
            # in its own column. That absence is a finding about the study
            # design, not a gap in the table.
            cur.execute(f"""
                with first_listing as (
                    select species_id, min(event_date) as listed_on
                    from {S}.cites_listing_events
                    where change_type = 'a'
                    group by species_id
                ),
                baseline as (
                    select distinct on (a.species_id)
                           a.species_id, a.year_published, a.status, a.assessment_id
                    from {S}.iucn_assessments a
                    join first_listing f on f.species_id = a.species_id
                    where a.year_published <= extract(year from f.listed_on)
                    order by a.species_id, a.year_published desc, a.assessment_id desc
                )
                select s.scientific_name,
                       f.listed_on,
                       b.year_published,
                       b.status,
                       b.assessment_id,
                       extract(year from current_date)::int - extract(year from f.listed_on)::int,
                       case when b.species_id is not null then ''
                            else 'no assessment predates the listing: the species was '
                                 'listed before any Red List assessment exists for it' end
                from {S}.species s
                join first_listing f on f.species_id = s.id
                left join baseline b on b.species_id = s.id
                order by s.scientific_name
            """)
            n = rows_to_csv(
                OUT / "supplementary_table_1_post_listing_window.csv",
                ["scientific_name", "first_listed_on", "baseline_assessment_year",
                 "baseline_status", "baseline_assessment_id", "post_listing_years",
                 "baseline_absent_because"],
                cur.fetchall())
            built.append((1, "Per-species post-listing window and baseline assessment", n))

            # --- Supplementary Table 6 -------------------------------------
            # The alternative reporter side. CITES records are reported by both
            # importer and exporter and the two do not agree; the paper's series
            # uses one side, so the other is given in full rather than described.
            cur.execute(f"""
                select s.scientific_name, t.year, t.reporter_type,
                       count(*) as records,
                       count(distinct t.importer) as importers,
                       count(distinct t.exporter) as exporters
                from {S}.cites_trade_records t
                join {S}.species s on s.id = t.species_id
                group by s.scientific_name, t.year, t.reporter_type
                order by s.scientific_name, t.year, t.reporter_type
            """)
            n = rows_to_csv(
                OUT / "supplementary_table_6_reporter_side_series.csv",
                ["scientific_name", "year", "reporter_type", "records",
                 "distinct_importers", "distinct_exporters"],
                cur.fetchall())
            built.append((6, "Post-listing series on both reporter sides", n))

            # --- Supplementary Table 8 -------------------------------------
            # Focal-set reconciliation: the listed-species count against the 43.
            cur.execute(f"""
                select l.appendix,
                       count(distinct l.species_id) as species,
                       count(distinct case when sp.id is not null then l.species_id end) as in_focal_set
                from {S}.cites_listings l
                left join {S}.species sp on sp.id = l.species_id
                where l.is_current
                group by l.appendix
                order by l.appendix
            """)
            rows = cur.fetchall()
            cur.execute(f"select count(*) from {S}.species")
            total = cur.fetchone()[0]
            # Species, not rows: one species can carry several population-level
            # split listings, and the published tally counts species.
            cur.execute(f"select count(distinct species_id) from {S}.split_listings")
            split = cur.fetchone()[0]
            rows = list(rows) + [("TOTAL", total, total), ("split-listed", split, split)]
            n = rows_to_csv(
                OUT / "supplementary_table_8_focal_set_reconciliation.csv",
                ["appendix", "species_with_current_listing", "species_in_focal_set"],
                rows)
            built.append((8, "Focal-set reconciliation by appendix", n))

            # --- Supplementary Table 9 -------------------------------------
            # Post-listing quantity series, per unit dimension. Quantities in
            # different units are not addable, so a single total would be a
            # category error; the series is reported per dimension.
            cur.execute(f"""
                select coalesce(nullif(t.unit, ''), '(count of specimens)') as unit,
                       t.year,
                       count(*) as records,
                       sum(t.quantity) as total_quantity,
                       count(distinct t.species_id) as species
                from {S}.cites_trade_records t
                where t.quantity is not null
                group by 1, 2
                order by 1, 2
            """)
            n = rows_to_csv(
                OUT / "supplementary_table_9_quantity_by_unit_dimension.csv",
                ["unit", "year", "records", "total_quantity", "species"],
                cur.fetchall())
            built.append((9, "Post-listing quantity series per unit dimension", n))
    finally:
        conn.close()

    readme = [
        "# Supplementary tables",
        "",
        "Generated from the frozen corpus by `ingest/build_supplementary.py`.",
        "They are derived on every build rather than hand-maintained, so a change",
        "in the corpus changes them and cannot leave a stale copy behind.",
        "",
        "## Derived here",
        "",
    ]
    for num, title, n in built:
        readme.append(f"- **Supplementary Table {num}** — {title} ({n} rows)")
    readme += [
        "",
        "## Also in this directory",
        "",
        "- **`change_table_published_vs_current.csv` / `.md`** — every",
        "  claim-bearing number in the submitted manuscript beside its value in",
        "  the rebuilt corpus, with the sentence it appeared in. The published",
        "  column is historical; the current column is recomputed on every build.",
        "  Produced by ingest/build_change_table.py.",
        "- **`species_narratives_no_citations.csv`** — the 343 machine-drafted",
        "  species narratives with their citations removed. The narratives are",
        "  gated: none has been signed by a reviewer, none is served, and no",
        "  reported value derives from one. Their citations were never verified,",
        "  and sampling found both references that resolve to nothing and",
        "  references that resolve to real papers attached to claims those papers",
        "  do not make — the second kind passes a reference-existence check, so",
        "  only reading the source catches it. This rendering keeps the prose and",
        "  drops the attribution. Produced by ingest/strip_narrative_citations.py;",
        "  the original text remains in `../tables/species_narratives.csv`.",
        "",
        "## Elsewhere in the deposit",
        "",
        "- **Supplementary Table 5** — results traceability: `../results_traceability.csv`",
        "",
        "## Not derivable, and why",
        "",
        "These need an author. They are named rather than stubbed: a placeholder",
        "table looks finished and survives review, which is worse than an absence.",
        "",
    ]
    for num in sorted(AUTHOR_DEPENDENT):
        readme.append(f"- **Supplementary Table {num}** — {AUTHOR_DEPENDENT[num]}")
    (OUT / "README.md").write_text("\n".join(readme) + "\n")

    print(f"supplementary/: {len(built)} table(s) derived")
    for num, title, n in built:
        print(f"  Table {num}: {n:>6} rows  {title}")
    print(f"  {len(AUTHOR_DEPENDENT)} table(s) need an author: "
          f"{', '.join(str(n) for n in sorted(AUTHOR_DEPENDENT))}")
    print("  Table 5 is results_traceability, already in the deposit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
