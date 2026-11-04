#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-14
"""V-21: a scored component that never varies is not scoring anything.

WHY THIS EXISTS
---------------
The CITES-effectiveness score is built from five components. One of them is
computed like this:

    df["population_score"] = df["population_trend"].map(
        {"increasing": 30, "stable": 25, "unknown": 15, "decreasing": 0}
    ).fillna(15)

`population_trend` in the source schema holds 43 values averaging 430 characters
— free prose of the form "the population trend is often classified as stable
across many areas; however, certain local populations face considerable threats".

None of the 43 equals "increasing", "stable", "unknown" or "decreasing". The map
returns NaN for every species and fillna assigns 15 to every species. A component
documented as worth up to 30 points contributes exactly 15 points to all 43, which
is the same as not existing — except that it looks like a measurement.

Nothing caught this. The score is a number, it is reproducible, it is byte-stable
across runs, and every gate that compares it against a frozen copy passes. It is
deterministically meaningless.

The same prose column is the only candidate source for the manuscript's
unexplained "69.8%", which is recorded separately for the authors. They
are the same defect seen from two directions: a text field being read as if it
were a category.

WHAT IT ASSERTS
---------------
Every named component of a derived score takes more than one distinct value
across the corpus. This is a weak property deliberately — it cannot tell a good
score from a bad one, only a live component from a dead one — but it is exactly
the property that was false here, and it is cheap.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/verify_score_components.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
INTERMEDIATE = ROOT / "data" / "raw"   # where the generator actually writes

# The components the effectiveness score is assembled from, named as the
# generator names them.
COMPONENTS = ["population_score", "trade_trend_score", "iucn_score",
              "cites_score", "data_quality_bonus"]


def load_rows() -> list[dict]:
    """The generated intermediate, whichever name it currently carries."""
    candidates = sorted(INTERMEDIATE.glob("*effectiveness*.json"))
    for path in candidates:
        try:
            data = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        rows = (data if isinstance(data, list)
                else data.get("species_analyses") or data.get("species")
                or data.get("data"))
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            print(f"  reading {path.relative_to(ROOT)}")
            return rows
    return []


def main() -> int:
    rows = load_rows()
    if not rows:
        # Silence must not pass: with no intermediate on disk there is nothing to
        # examine, and reporting success would be the exact failure this catches.
        print("V-21 CANNOT RUN: no effectiveness intermediate found. "
              "Run 'make figures' (or visualizations/make_all_figures.py) first.")
        return 2

    present = [c for c in COMPONENTS if c in rows[0]]
    missing = [c for c in COMPONENTS if c not in rows[0]]
    if not present:
        print(f"V-21 CANNOT RUN: the intermediate has none of the component "
              f"columns {COMPONENTS}. Either the score was restructured or this "
              f"gate is reading the wrong artefact; both need a person.")
        return 2

    print(f"V-21 score components: {len(rows)} species, "
          f"{len(present)} of {len(COMPONENTS)} components present\n")

    dead = []
    for comp in present:
        values = {r.get(comp) for r in rows}
        status = "varies" if len(values) > 1 else "CONSTANT"
        sample = sorted(str(v) for v in values)[:4]
        print(f"  {status:9s} {comp:22s} {len(values)} distinct value(s): "
              f"{', '.join(sample)}{' …' if len(values) > 4 else ''}")
        if len(values) <= 1:
            dead.append((comp, next(iter(values))))

    if missing:
        print(f"\n  not present in the intermediate: {', '.join(missing)}")

    if dead:
        print(f"\nV-21 FAIL: {len(dead)} component(s) take the same value for every "
              f"species:")
        for comp, value in dead:
            print(f"  {comp} = {value} for all {len(rows)} species")
        print("A component that never varies contributes nothing to the ranking it")
        print("appears in. Either the field it reads is not the field it expects —")
        print("mapping prose against category keys returns NaN and falls back to a")
        print("constant — or the component should be removed and the score's stated")
        print("range corrected.")
        return 1

    print(f"\nV-21 PASS: every component of the effectiveness score varies across "
          f"the corpus. This does not establish that any of them is the right "
          f"measure, only that none is dead.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
