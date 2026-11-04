#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-15
"""Is Figure 10's data derivable from the corpus? (analysis, not a gate)

WHAT THIS IS, AND IS NOT
------------------------
This is analysis for an authors' decision: manuscript Figure 10 had no scripted
pipeline, and the choice was whether to add one or to state in the paper that
it is unscripted, as the paper does for the cartographic and schematic figures.

It is NOT the Figure 10 pipeline, and running it does not create one. It does not
render a figure, does not write into deposit/, and is not wired into any suite.
It changes nothing about the provenance record, which states that the published
Figure 10 had no pipeline artefact matched to it. This only answers a prior question — CAN the figure be scripted? — by
computing the three panels' data from the corpus and checking the result against
what the manuscript already says about Figure 10.

WHAT FIGURE 10 IS
-----------------
From the submitted manuscript: "Conservation status patterns among CITES-listed
Arctic species (1982-2023). A) the most recent IUCN Red List category assigned to
each species; B) the number of Red List category changes between 1982-2023; and
C) trajectory illustrating change."

All three are IUCN-assessment quantities, and the corpus holds every assessment.
Panels A and B are direct queries; panel C is the trajectory classification the
D10 scale module already defines and V-10 already exercises.

THE CHECK ON ITSELF
-------------------
The manuscript states Figure 10 shows "limited movement overall" and "slightly
more improvements than deteriorations". If this computation is measuring the same
thing the figure measures, panel C must reproduce that: more unchanged than
anything else, and improved > deteriorated by a little. If it does not, this
script is measuring the wrong thing and its numbers should not be trusted — the
seed-a-known-positive discipline, applied to an analysis.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/analysis_figure10_derivability.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import redlist_scale as R  # noqa: E402

WINDOW = (1982, 2023)  # the caption's own range
SCHEMA = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1
    import psycopg2
    conn = psycopg2.connect(url, connect_timeout=60)
    cur = conn.cursor()

    # Panel A: the latest GLOBAL category per species.
    #
    # NOT `where is_latest`. The is_latest flag points at a 2023 Europe-scope
    # assessment for 17 of the 43 species, so a naive is_latest query returns a
    # regional category for them (for the gray whale and several great whales
    # the European category differs from the global one). The trajectory
    # pipeline avoids this by filtering coalesce(scope_code,'1')='1'; this must
    # match it, and measures the corpus the manuscript speaks about.
    # distinct on with an is_latest tie-break, NOT max(year) with an arbitrary
    # pick. Snowy Owl (2021) and Walrus (2025) each carry two global
    # assessments in one year with different categories, and only one of each
    # pair is the current one (is_latest). Taking the max year and letting row
    # order choose within it would pick the wrong row for those two species.
    # This is the same tie-break V-31 uses; the two must agree.
    cur.execute(f"""
        select distinct on (s.id) s.scientific_name, a.status
          from {SCHEMA}.iucn_assessments a
          join {SCHEMA}.species s on s.id = a.species_id
         where a.scope_code is null
         order by s.id, a.year_published desc, a.is_latest desc""")
    latest = [(name, st) for name, st in cur.fetchall()]
    panel_a = Counter(st for _, st in latest)
    regional_latest: list[tuple[str, str]] = []  # none, by construction: global only

    # Panels B and C: per-species chronological sequence within the window.
    # One row per (species, year): where a year carries two global assessments
    # (one species has two in 2021, in different categories), keep the is_latest one, so the trajectory is
    # built on the same status panel A uses.
    cur.execute(f"""
        select distinct on (s.id, a.year_published)
               s.scientific_name, a.year_published, a.status
          from {SCHEMA}.iucn_assessments a
          join {SCHEMA}.species s on s.id = a.species_id
         where a.scope_code is null
           and a.year_published between %s and %s
         order by s.id, a.year_published, a.is_latest desc""", WINDOW)
    seq: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for name, yr, st in cur.fetchall():
        seq[name].append((yr, st))
    conn.close()

    panel_b = {name: len(R.transitions(pairs)) for name, pairs in seq.items()}
    panel_c: dict[str, str] = {}
    for name, pairs in seq.items():
        comp = [st for _, st in pairs if R.normalise(st) is not None]
        panel_c[name] = (R.classify(comp[0], comp[-1]) if len(comp) >= 2
                         else "single assessment")
    c = Counter(panel_c.values())

    print(f"Figure 10 data, recomputed from {SCHEMA} over {WINDOW[0]}-{WINDOW[1]}, "
          f"GLOBAL scope only")
    print("\nPanel A — latest GLOBAL Red List category per species "
          f"({len(latest)} species):")
    for cat, n in sorted(panel_a.items(), key=lambda x: -x[1]):
        print(f"  {cat:>4}  {n}")
    print("  (global scope: a naive is_latest query would show 17 species at "
          "their 2023 Europe status instead)")

    print(f"\nPanel B — Red List category changes per species "
          f"({len(seq)} species with an assessment in window):")
    for k, n in sorted(Counter(panel_b.values()).items()):
        print(f"  {k} change(s): {n} species")
    print(f"  most-changed: "
          f"{', '.join(f'{n} ({k})' for n, k in sorted(panel_b.items(), key=lambda x: -x[1])[:4])}")

    print(f"\nPanel C — trajectory, first vs last comparable category:")
    for k in ("improved", "unchanged", "deteriorated", "single assessment"):
        if c.get(k):
            print(f"  {k:>18}  {c[k]}")

    # The self-check: does panel C reproduce the manuscript's stated finding?
    improved, deteriorated = c.get("improved", 0), c.get("deteriorated", 0)
    unchanged = c.get("unchanged", 0)
    moved = improved + deteriorated
    limited_movement = unchanged >= moved
    slightly_more_improved = 0 < (improved - deteriorated) <= 3
    print("\nSelf-check against the manuscript's own words about Figure 10:")
    print(f"  'limited movement overall'                -> "
          f"{unchanged} unchanged vs {moved} moved: "
          f"{'reproduced' if limited_movement else 'NOT reproduced'}")
    print(f"  'slightly more improvements than deteriorations' -> "
          f"{improved} vs {deteriorated}: "
          f"{'reproduced' if slightly_more_improved else 'NOT reproduced'}")

    if not (limited_movement and slightly_more_improved):
        print("\nThe recomputation does NOT match the manuscript's description, so "
              "this analysis is measuring something other than what the figure "
              "shows. Do not use these numbers to argue Figure 10 is derivable "
              "until the mismatch is understood.")
        return 1

    print("\nBoth reproduced: Figure 10's three panels are computable from the "
          "corpus and the trajectory panel agrees with the paper's own claim. "
          "Scripting it is therefore a real option, not a blank. Whether to add "
          "the script or state the figure is unscripted remains the authors'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
