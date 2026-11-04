#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-15
"""Produce a citation-free rendering of the species narratives.

WHY THIS EXISTS
---------------
The 343 machine-drafted narrative sections carry parenthetical citations that
were never verified against sources. Sampling four at random found two that
resolve to no publication and two that resolve to real papers by the right
authors on the right species, attached to claims those papers do not make.

The narratives are already gated: none is served, none has been signed by a
reviewer, and no reported value derives from one. So nothing published is
affected. What remains is that the corpus ships with citation-shaped text that
cannot be relied on, and a reader opening the table has no way to tell which
citations are which.

Stripping them removes the liability without discarding the prose. The text keeps
whatever descriptive value it has; it simply stops making attribution claims it
cannot support. Restoring citations later is a matter of re-running the drafting
pipeline against a verified bibliography, which is the right way to get them.

WHAT IT HANDLES
---------------
Two citation forms, because the drafting model used both:

  parenthetical   "... in Siberian rivers (Zimmerman & Williams, 2000)."
  narrative       "... reproductive health Pavlová et al. (2016); and ..."

Removing only the parentheses from the second form leaves a dangling author name,
which is worse than leaving it alone. Both are removed whole.

Bare parentheticals that contain a year but no author — none were found in this
corpus, but the pattern allows for them — are left alone, because "(2002)" after
a treaty name is a date, not a reference.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/strip_narrative_citations.py
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/strip_narrative_citations.py --write
"""
from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).parent.parent
# supplementary/, not tables/. Everything in tables/ must load into the
# deposited schema, and V-14 refused this file within minutes of it being
# put there: it is a derived rendering of a table, not a table.
OUT = ROOT / "deposit" / "supplementary" / "species_narratives_no_citations.csv"
SCHEMA = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")

# Citations are removed as TOKENS, not as parenthetical groups.
#
# Removing whole parentheses fails on this corpus because some citations are
# malformed: five narratives contain an opening parenthesis that is never closed,
# so it swallows several sentences of prose and is finally closed by a later
# citation. One runs "(Haines et al. 2024." and continues for a full paragraph
# before ending at "Jantunen et al. 2015)". Deleting that group would delete the
# paragraph.
#
# So the author-year token itself is matched wherever it appears, inside
# parentheses or not, and the leftover punctuation is tidied afterwards.
AUTHOR = (r"[A-ZÁÉÍÓÚÝÐÞÆÖŠŽÑ][\w'’\-áéíóúýðþæöšžñ]*"
          r"(?:\s+(?:et\s+al\.?|&\s*[A-ZÁÉÍÓÚÝÐÞÆÖŠŽÑ][\w'’\-áéíóúýðþæöšžñ]*"
          r"|and\s+[A-ZÁÉÍÓÚÝÐÞÆÖŠŽÑ][\w'’\-áéíóúýðþæöšžñ]*))?")
# "Author et al., 2016" / "Author et al. (2016)" / "Author et al. 2016"
TOKEN = re.compile(AUTHOR + r",?\s*\(?(?:19|20)\d{2}[a-z]?\)?")

def strip(text: str) -> str:
    s = TOKEN.sub("", text)
    # Tidy what removal leaves: empty or orphaned parentheses, space before
    # punctuation, doubled separators, stranded conjunctions.
    s = re.sub(r"\(\s*[;,]?\s*\)", "", s)
    s = re.sub(r"\(\s*(?=[.;,])", "", s)
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r"([,;])\s*([,.;:])", r"\2", s)
    s = re.sub(r"\.\s*,", ".", s)
    # Repeated separators left by two adjacent citations, e.g. "pressures,,."
    s = re.sub(r"([,;])[\s,;]*\1", r"\1", s)
    s = re.sub(r"[,;]+(\s*[.])", r"\1", s)
    # A parenthesis left unbalanced by removal would be worse than the citation.
    if s.count("(") != s.count(")"):
        s = s.replace("(", "").replace(")", "")
    s = re.sub(r"[ \t]{2,}", " ", s)   # blank lines are the author's, not ours
    s = re.sub(r"(?m)^\s*(?:and|;)\s+", "", s)
    return s.strip()


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1
    write = "--write" in sys.argv

    conn = psycopg2.connect(url, connect_timeout=60)
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                select n.id, s.scientific_name, n.section, n.body
                  from {SCHEMA}.species_narratives n
                  join {SCHEMA}.species s on s.id = n.species_id
                 order by s.scientific_name, n.section, n.id""")
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        print("CANNOT RUN: species_narratives is empty, so a clean output would "
              "mean nothing.")
        return 2

    YEAR = re.compile(r"(?:19|20)\d{2}")
    cleaned, residual, shrunk = [], 0, 0
    for nid, sci, section, body in rows:
        body = body or ""
        s = strip(body)
        cleaned.append((nid, sci, section, s))
        if len(s) < len(body):
            shrunk += 1
        # Any year left inside parentheses means a citation form we did not model.
        if any(YEAR.search(m) for m in re.findall(r"\([^()]*\)", s)):
            residual += 1

    before = sum(len(r[3] or "") for r in rows)
    after = sum(len(c[3]) for c in cleaned)
    print(f"{len(rows)} narratives, {shrunk} contained a citation")
    print(f"characters {before:,} -> {after:,} ({100 * (before - after) / before:.1f}% removed)")
    print(f"narratives still containing a year inside parentheses: {residual}")

    if residual:
        print("\nThose are citation forms this script does not model. Reported "
              "rather than left silent: a partial strip is worse than none, "
              "because it looks complete.")
        return 1

    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "scientific_name", "section", "body_no_citations"])
            w.writerows(cleaned)
        print(f"\nwrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
    else:
        print("\nDry run. Pass --write to produce the deposit file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
