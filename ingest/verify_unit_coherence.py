#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-14
"""V-26: a summed quantity must say what unit it is in.

WHY THIS EXISTS
---------------
Figure 8 ranks the fifteen most traded wild-origin species by `total_quantity`.
That column is a sum over CITES records whose `unit` field takes many different
values. Measured on 2026-08-15: 26 across the whole corpus and 19 within the
wild-origin subset. An earlier note here said twelve, which came from reading a
display truncated to the top twelve rows as a count.

The sums are therefore kilograms added to counts. Fin whale contributes
16,471,705 — kilograms of meat, from 233 records — and that single number is
64% of the figure's total, which is why fin whale ranks first.

Under the caption's own wording, "the 15 most frequently traded wild-sourced
species", fin whale is not in the top six. Measured three ways the answer differs
in both order and membership:

  by record count      Canada Lynx, Narwhal, Polar Bear, Atlantic Walrus …
  by countable units   River Otter (2,915,668), Canada Lynx, Atlantic Walrus …
  by mixed-unit sum    Fin Whale (16,522,295), Common Minke Whale …

Three species in the plotted ranking are absent from the frequency ranking, and
two (gyrfalcon, peregrine falcon) are in the countable ranking but not plotted.

No check could see this. The sum is deterministic, reproduces byte for byte, and
matches its Source Data exactly. It is arithmetic performed on incommensurable
quantities, which is a modelling error rather than a computational one.

WHAT IT ASSERTS
---------------
Any Source Data file carrying an aggregated quantity column must also carry the
unit that quantity is in, or declare in its header comment that the aggregation
is unit-coherent. It cannot judge whether a measure is the right one; it forces
the unit to be stated, which is what makes the question visible.

Usage:
  .venv/bin/python ingest/verify_unit_coherence.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOURCE_DATA = ROOT / "visualizations" / "source_data"

# A column holding a summed physical quantity, as opposed to a count of records.
QUANTITY = re.compile(r"(total_quantity|sum_quantity|quantity|volume)$", re.I)
# A column naming the unit that quantity is in.
UNIT = re.compile(r"(unit|units|unit_name|measure)$", re.I)
# Counts are dimensionless and need no unit.
COUNT = re.compile(r"(count|records|n|rank|year|id)$", re.I)


def main() -> int:
    if not SOURCE_DATA.is_dir():
        print(f"V-26 CANNOT RUN: {SOURCE_DATA} is absent.")
        return 2
    files = sorted(SOURCE_DATA.glob("*.csv"))
    if not files:
        # Silence must not pass: no files means nothing examined.
        print("V-26 CANNOT RUN: no Source Data files found.")
        return 2

    examined = 0
    offenders: list[tuple[str, str]] = []

    for f in files:
        with open(f, newline="") as fh:
            header = next(csv.reader(fh), [])
        if not header:
            continue
        qty = [c for c in header if QUANTITY.search(c) and not COUNT.search(c)]
        if not qty:
            continue
        examined += 1
        if not any(UNIT.search(c) for c in header):
            offenders.append((f.name, ", ".join(qty)))

    # The bound that matters most. The figures sum across units; the published
    # numbers must not. Checked on 2026-08-14: of the four sums in V-9, three
    # count verdicts and transitions and one totals NAMMCO catch, which is a
    # count of animals and dimensionless. No manuscript claim derives from
    # cites_trade_records.quantity. This asserts that stays true.
    claims = ROOT / "ingest" / "verify_manuscript_claims.py"
    leaked: list[str] = []
    if claims.exists():
        src = claims.read_text()
        for m in re.finditer(r"^.*\bsum\s*\(\s*(?:[a-z_]+\.)?quantity\b.*$",
                             src, re.M | re.I):
            leaked.append(m.group(0).strip()[:80])
    else:
        leaked.append("verify_manuscript_claims.py is absent, so this cannot be "
                      "checked and is not assumed")

    print(f"V-26 unit coherence: {len(files)} Source Data file(s), "
          f"EXAMINED {examined} carrying an aggregated quantity; "
          f"{'no' if not leaked else len(leaked)} published claim(s) derive from "
          f"a summed trade quantity")

    if leaked:
        print(f"\nV-26 FAIL: a published claim is derived from a summed trade "
              f"quantity:\n")
        for l in leaked:
            print(f"  {l}")
        print("\nThe quantity field mixes 26 units in this corpus. A figure")
        print("doing this is a figure to fix; a manuscript claim doing it is a")
        print("number in the paper that means nothing physical.")
        return 1

    if offenders:
        print(f"\nV-26 FAIL: {len(offenders)} file(s) sum a quantity without "
              f"naming its unit:\n")
        for name, cols in offenders:
            print(f"  {name}: column(s) {cols} with no unit column")
        print("\nIn this corpus the underlying unit field takes 26 values,")
        print("so a sum without a unit is kilograms added to counts. Either")
        print("restrict the aggregation to one unit and name it, or report the")
        print("measure as a record count, which is dimensionless.")
        return 1

    if examined == 0:
        print("\nV-26 FAIL: no file carries an aggregated quantity, so this "
              "examined nothing and would pass for free.")
        return 1

    print(f"\nV-26 PASS: every aggregated quantity names the unit it is in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
