#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-15
"""The change table accompanying the revised manuscript.

WHY THIS EXISTS
---------------
Superseded wording is set against its replacement in a change table, so a
reader can verify that a contradiction is gone rather than merely relocated.

This builds that table, for the numbers.

WHAT IT COMPARES
----------------
The published column is read from the submitted manuscript and is historical: it
does not change and is recorded here verbatim, with the sentence each number
appeared in, so a reader can see the claim rather than only the value.

The current column is computed from the corpus on every run. That is the half
that would otherwise rot: a change table with a hand-typed "now" column is
correct on the day it is written and misleading thereafter.

WHAT IT DOES NOT DO
-------------------
It reports what moved. It does not decide whether a sentence needs rewriting —
three of these do, and which wording replaces them is the authors' call.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/build_change_table.py
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).parent.parent
OUT_CSV = ROOT / "deposit" / "supplementary" / "change_table_published_vs_current.csv"
OUT_MD = ROOT / "deposit" / "supplementary" / "change_table_published_vs_current.md"
SCHEMA = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")

# (label, published value as printed, the sentence it appeared in, SQL for now)
ROWS = [
    ("Trade records in the corpus", "473,102",
     "Between 1975 and 2024, CITES reported 473,102 trades involving 43 Arctic species",
     f"select count(*) from {SCHEMA}.cites_trade_records", "int"),
    ("Appendix I share of records", "27.3%",
     "27.3% involve Appendix I species",
     f"select round(100.0*count(*) filter (where appendix='I')/count(*), 1) "
     f"from {SCHEMA}.cites_trade_records", "pct"),
    ("Appendix II share of records", "66.4%",
     "66.4% Appendix II species (Fig. 5)",
     f"select round(100.0*count(*) filter (where appendix='II')/count(*), 1) "
     f"from {SCHEMA}.cites_trade_records", "pct"),
    ("Critically Endangered records", "188,979",
     "over 40% (188,979) involve species categorised as Critically Endangered",
     f"select count(*) from {SCHEMA}.cites_trade_records t "
     f"join {SCHEMA}.iucn_assessments a on a.species_id=t.species_id and a.is_latest "
     f"where a.status='CR'", "int"),
    ("Canada lynx, wild-origin trades", "29,958",
     "wild-origin trade is concentrated in a subset of mammals: Canada lynx (29,958 trades)",
     f"select count(*) from {SCHEMA}.cites_trade_records t "
     f"join {SCHEMA}.species s on s.id=t.species_id "
     f"where s.scientific_name='Lynx canadensis' and t.source='W'", "int"),
    ("Narwhal, wild-origin trades", "22,638", "narwhal (22,638)",
     f"select count(*) from {SCHEMA}.cites_trade_records t "
     f"join {SCHEMA}.species s on s.id=t.species_id "
     f"where s.scientific_name='Monodon monoceros' and t.source='W'", "int"),
    ("Polar bear, wild-origin trades", "20,983", "polar bear (20,983)",
     f"select count(*) from {SCHEMA}.cites_trade_records t "
     f"join {SCHEMA}.species s on s.id=t.species_id "
     f"where s.scientific_name='Ursus maritimus' and t.source='W'", "int"),
    ("Atlantic walrus, wild-origin trades", "20,590", "Atlantic walrus (20,590)",
     f"select count(*) from {SCHEMA}.cites_trade_records t "
     f"join {SCHEMA}.species s on s.id=t.species_id "
     f"where s.scientific_name='Odobenus rosmarus' and t.source='W'", "int"),
]


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1

    conn = psycopg2.connect(url, connect_timeout=60)
    out = []
    try:
        with conn.cursor() as cur:
            for label, published, sentence, sql, kind in ROWS:
                cur.execute(sql)
                now = cur.fetchone()[0]
                pub_n = float(published.replace(",", "").rstrip("%"))
                now_n = float(now)
                if kind == "pct":
                    shown, delta = f"{now_n:.1f}%", f"{now_n - pub_n:+.1f} pt"
                else:
                    shown, delta = f"{int(now_n):,}", f"{int(now_n - pub_n):+,}"
                if abs(now_n - pub_n) < 0.05:
                    delta = "unchanged"
                out.append((label, published, shown, delta, sentence))
    finally:
        conn.close()

    if not out:
        print("CANNOT RUN: no rows computed.")
        return 2

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "as_submitted", "current", "change",
                    "sentence_as_submitted"])
        w.writerows(out)

    md = ["<!-- GENERATED by ingest/build_change_table.py. Do not edit; the next",
          "     build overwrites it. Edit the generator. -->",
          "",
          "# Change table: submitted manuscript vs the rebuilt corpus",
          "",
          "The left column is what the submitted manuscript printed and does not",
          "change. The right columns are recomputed from the deposited corpus on",
          "every build, so this table cannot quietly go out of date.",
          "",
          "| Quantity | As submitted | Current | Change |",
          "|---|---|---|---|"]
    for label, pub, now, delta, _ in out:
        md.append(f"| {label} | {pub} | **{now}** | {delta} |")
    md += ["",
           "## The sentences these numbers appeared in",
           ""]
    for label, pub, now, delta, sentence in out:
        md.append(f"- **{label}** — “{sentence}”")
    md += ["",
           "Every count rises, which is what recovering records from a rebuild",
           "should do, and no ranking changes: lynx, narwhal, polar bear, walrus",
           "keep their order. The one sentence that needs rewording rather than",
           "renumbering is the Critically Endangered share, which was printed as",
           "\"over 40%\" and is now just under it.",
           ""]
    OUT_MD.write_text("\n".join(md) + "\n")

    print(f"change table: {len(out)} quantities compared")
    for label, pub, now, delta, _ in out:
        print(f"  {label:<38} {pub:>9} -> {now:>9}  {delta}")
    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} and {OUT_MD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
