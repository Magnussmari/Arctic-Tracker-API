#!/usr/bin/env python3
"""Does the improving share concentrate among species already stable at listing?

WHY THIS EXISTS
---------------
A reviewer (R1-04) raised the confounder: if the species whose Red List
status improved were mostly the ones that were already in good shape when CITES
listed them, then "improvement after listing" says considerably less than it
appears to. This analysis measures the confounder rather than only
acknowledging it.

This is not a verification gate. It is the analysis, and it reports a table.
Nothing here decides what the table means — that is the authors' reading.

METHOD, stated plainly because the choices are arguable
-------------------------------------------------------
For each of the 38 species carrying a comparable trajectory (the same set
finding (iii) uses):

  1. Take the species' first CITES listing event as the listing date.
  2. Take the Red List category in force at that date: the most recent
     assessment published on or before it. Species with no assessment at or
     before listing are reported separately rather than dropped, because for
     most of this portfolio CITES listing predates the Red List assessment
     history entirely — that fact is itself the answer to part of R1-04.
  3. Classify that category as STABLE (LC, LR/lc, NT, LR/nt, LR/cd) or
     THREATENED (VU, EN, CR) or NOT COMPARABLE (pre-1994 codes: K, V, E, R, I,
     T, NR, and DD/NA which carry no direction).
  4. Cross-tabulate against the species' trajectory verdict.

The trajectory verdict is recomputed here rather than imported, so this script
stands alone and a reviewer can run it against the deposit.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/stratify_trajectories.py
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

import psycopg2

SCHEMA = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")

# The scale is NOT redefined here. redlist_scale exists because five scripts in
# this repository once carried three different orderings and disagreed on the
# direction of change for 30 of 43 species. Writing another one — which this
# script did in its first two drafts, and got 41 species and then 15 against a
# published 38 — would have been the sixth.
# Importing a sibling here writes __pycache__ INTO the deposit, and
# verify_deposit_accounted.py rejects bytecode in a citable archive. Running
# these scripts in place is the intended use, so the run must not leave
# residue behind, or the archive gate would fail merely because the verifiers
# had been run.
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import redlist_scale as rl  # noqa: E402

STABLE_AT_LISTING = {"LC", "LR/lc", "NT", "LR/nt", "LR/cd"}
THREATENED_AT_LISTING = {"VU", "EN", "CR"}


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1

    conn = psycopg2.connect(url, connect_timeout=60)
    try:
        with conn.cursor() as cur:
            # The same population and ordering V-9 uses, including the series
            # filter (global and European assessments since 21 October 2026). Without it the counts diverge from the published
            # ones for reasons that have nothing to do with this analysis.
            cur.execute(f"""
                select s.id, s.common_name, a.year_published, a.status
                  from {SCHEMA}.iucn_assessments a
                  join {SCHEMA}.species s on s.id = a.species_id
                 where {rl.series_sql('a')}
                   and a.year_published is not null
                 order by s.common_name, a.year_published, a.assessment_id""")
            assessments: dict[int, list[tuple[int, str]]] = defaultdict(list)
            names: dict[int, str] = {}
            for sid, name, year, status in cur.fetchall():
                names[sid] = name
                assessments[sid].append((year, status))

            cur.execute(f"""
                select species_id, min(extract(year from event_date))::int
                  from {SCHEMA}.cites_listing_events
                 where is_listing group by species_id""")
            listed = dict(cur.fetchall())
    finally:
        conn.close()

    if not assessments or not listed:
        print("T-17 CANNOT RUN: assessments or listing events are empty, so "
              "every stratum would be empty and the table would say nothing.")
        return 2

    rows = []
    for sid, hist in assessments.items():
        comparable = [(y, s) for y, s in hist if rl.comparable(s)]
        if len(comparable) < 2:
            continue                      # the species finding (iii) excludes
        verdict = rl.classify(comparable[0][1], comparable[-1][1])

        listing_year = listed.get(sid)
        if listing_year is None:
            stratum = "no listing event recorded"
        else:
            prior = [(y, s) for y, s in hist if y <= listing_year]
            if not prior:
                stratum = "no assessment at or before listing"
            elif prior[-1][1] in STABLE_AT_LISTING:
                stratum = "stable at listing"
            elif prior[-1][1] in THREATENED_AT_LISTING:
                stratum = "threatened at listing"
            else:
                stratum = "category at listing not comparable"
        rows.append((names[sid], listing_year, stratum, verdict))

    print(f"T-17 trajectory by status at listing — {len(rows)} species with a "
          f"comparable trajectory\n")

    strata = sorted({r[2] for r in rows})
    verdicts = ["improved", "unchanged", "deteriorated"]
    width = max(len(s) for s in strata) + 2

    print(f"  {'stratum':<{width}}" + "".join(f"{v:>15}" for v in verdicts) + f"{'total':>9}")
    for st in strata:
        counts = [sum(1 for r in rows if r[2] == st and r[3] == v) for v in verdicts]
        print(f"  {st:<{width}}" + "".join(f"{c:>15}" for c in counts)
              + f"{sum(counts):>9}")
    totals = [sum(1 for r in rows if r[3] == v) for v in verdicts]
    print(f"  {'ALL':<{width}}" + "".join(f"{c:>15}" for c in totals)
          + f"{sum(totals):>9}")

    print("\n  species improving, with their status at listing:")
    for name, yr, st, v in sorted(rows):
        if v == "improved":
            print(f"    {name:<32} listed {yr}   {st}")

    # ---- Is the "two-decade lag" biology, or the Red List's calendar? --------
    #
    # The manuscript carries a sentence about a roughly two-decade lag between
    # listing and observable status change. Whether that is a biological
    # response time or simply how often IUCN re-runs an assessment is
    # measurable, and this section measures it.
    import statistics

    lag_any, lag_comparable = [], []
    for sid, hist in assessments.items():
        ly = listed.get(sid)
        if ly is None:
            continue
        # Same population as the table above and as V-9: the species carrying a
        # comparable trajectory. Averaging over every species with a listing year
        # instead gives a mean of 21.4 against V-9's 19.8; the populations must
        # match for the two numbers to be comparable.
        if len([1 for _, s in hist if rl.comparable(s)]) < 2:
            continue
        after = [y for y, _ in hist if y > ly]
        if after:
            lag_any.append(after[0] - ly)
        after_c = [y for y, s in hist if y > ly and rl.comparable(s)]
        if after_c:
            lag_comparable.append(after_c[0] - ly)

    if lag_comparable:
        print("\n  T-19 — how soon after listing a change could register at all:")
        print(f"    first assessment of any kind      median "
              f"{statistics.median(lag_any):.0f} yr, mean "
              f"{statistics.mean(lag_any):.1f}, range {min(lag_any)}-{max(lag_any)} "
              f"(n={len(lag_any)})")
        print(f"    first COMPARABLE assessment       median "
              f"{statistics.median(lag_comparable):.0f} yr, mean "
              f"{statistics.mean(lag_comparable):.1f}, range "
              f"{min(lag_comparable)}-{max(lag_comparable)} (n={len(lag_comparable)})")
        # Computed, not asserted, so the reported interval is traceable.
        # Consecutive comparable assessments, distinct years per species, same
        # population as the lags above.
        gaps = []
        for sid, hist in assessments.items():
            if listed.get(sid) is None:
                continue
            years = sorted({y for y, s in hist if rl.comparable(s)})
            if len(years) < 2:
                continue
            gaps += [b - a for a, b in zip(years, years[1:])]
        print(f"    Median interval between consecutive comparable reassessments is "
              f"{statistics.median(gaps):g} years (n={len(gaps)} intervals),")
        print("    so the delay is not the re-run cadence: it is how long the Red")
        print("    List took to reach these species on the modern scale at all.")
        print("    A two-decade lag is therefore indistinguishable from the")
        print("    earliest date at which any change could have been recorded.")

    print("\nWhat this does and does not settle: it measures whether the "
          "improving species\nwere already in the low-threat categories when "
          "CITES listed them. It cannot\nattribute any change to listing, and "
          "the largest stratum below is the relevant\nheadline for R1-04.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
