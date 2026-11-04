#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-14
"""V-24: every figure must describe the corpus the manuscript describes.

WHY THIS EXISTS
---------------
Figure 2 shipped for weeks with the subtitle "473,102 trade records" while the
manuscript reported 492,095, because the figure generators read the pre-rebuild
schema. That was fixed by making the schema explicit.

It then happened again, within the hour, to me. Testing a different gate I
exported ARCTIC_SCHEMA=arctic, regenerated one intermediate, and later rebuilt a
single figure. The result mixed two corpora inside one image: panel (c) queried
the manuscript's corpus directly while the subtitle came from the stale
intermediate, so the figure said 473,102 at the top and 492,095 in its own bars.

Nothing failed. Both numbers are real, both are reproducible, and a determinism
check compares a figure against its own last output rather than against the
corpus. The only reason it was caught is that the figure was looked at.

WHAT IT ASSERTS
---------------
Every count a rendered figure states about the corpus as a whole equals the
corpus. Concretely: any figure artefact quoting "N trade records" must quote the
live row count of the trade table.

This is narrow on purpose. It cannot tell whether a figure is right. It tells you
whether two artefacts that claim to describe one dataset are describing one
dataset, which is the property that failed twice in one day.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/verify_figure_corpus.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).parent.parent
PRODUCTION = ROOT / "visualizations" / "production"
SCHEMA = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")

# "492,095 total trade records", "473,102 trade records", and the escaped forms
# plotly writes into HTML.
CORPUS_CLAIM = re.compile(r"([\d]{1,3}(?:,\d{3})+)\s*(?:total\s+)?trade records", re.I)


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1
    if not PRODUCTION.is_dir():
        print(f"V-24 CANNOT RUN: {PRODUCTION} is absent. Generate the figures first.")
        return 2

    conn = psycopg2.connect(url, connect_timeout=60)
    try:
        with conn.cursor() as cur:
            cur.execute(f"select count(*) from {SCHEMA}.cites_trade_records")
            corpus = cur.fetchone()[0]
    finally:
        conn.close()

    artefacts = sorted(PRODUCTION.glob("figure*.html"))
    if not artefacts:
        # Silence must not pass: no figures means nothing examined, and a green
        # here would say the figures agree with the corpus when there are none.
        print("V-24 CANNOT RUN: no rendered figures found.")
        return 2

    examined = 0
    wrong: list[tuple[str, str]] = []
    silent: list[str] = []

    for art in artefacts:
        text = art.read_text(errors="ignore")
        claims = set(CORPUS_CLAIM.findall(text))
        if not claims:
            silent.append(art.name)
            continue
        for c in sorted(claims):
            examined += 1
            if int(c.replace(",", "")) != corpus:
                wrong.append((art.name, c))

    print(f"V-24 figure corpus: {SCHEMA}.cites_trade_records holds {corpus:,} rows.")
    print(f"  EXAMINED {examined} corpus claim(s) across "
          f"{len(artefacts) - len(silent)} of {len(artefacts)} figure(s); "
          f"{len(silent)} state no corpus total")

    if wrong:
        print(f"\nV-24 FAIL: {len(wrong)} figure claim(s) describe a different corpus:\n")
        for name, c in wrong:
            print(f"  {name}: states {c} trade records, corpus holds {corpus:,}")
        print("\nA figure and the manuscript must describe one dataset. Regenerate")
        print("every figure from one schema — a single stale intermediate is enough")
        print("to put two corpora inside one image.")
        return 1

    if examined == 0:
        print("\nV-24 FAIL: no figure states a corpus total, so this examined "
              "nothing and would pass for free.")
        return 1

    print(f"\nV-24 PASS: every corpus total stated by a figure matches the corpus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
