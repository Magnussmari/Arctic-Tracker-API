#!/usr/bin/env python3
"""Source Data for manuscript Figure 5, CITES reservations held by Arctic states.

WHY THIS EXISTS
---------------
Figure 5 joined the manuscript on 18 October 2026, drawn by the co-author from
the CITES country profiles. Every cell it shows is also in the deposit: the
Species+ event history in deposit/tables/cites_listing_events.csv carries each
reservation with its Party, appendix, whether it is current, and the stock note
that makes some of them partial. So the figure needs no new source. It needs the
twenty lines that read what the deposit already holds, and an assertion that
what they read is what the figure draws.

The identifier is a LETTER for the reason make_fig3_fig10_source_data.py gives:
the pipeline's numbering and the manuscript's are two numberings, and a letter
cannot be misread as either.

WHAT IT COUNTS
--------------
A reservation is counted per (Party, species) and placed in the appendix the
species is listed in. The common minke whale is split-listed: Iceland holds an
Appendix I reservation on every stock except West Greenland and an Appendix II
reservation on the West Greenland stock. That is two Species+ events and one
species, and the figure draws it once, in Appendix I. Counting events instead of
species gives Iceland 15 and matches nothing.

Partial means the reservation's own note limits it to some stocks and the
remaining stocks are not covered by another reservation of the same Party.
The minke notes ("Except stock of west Greenland") are not partial in that
sense, because the West Greenland stock is Appendix II and Iceland reserves it
there; Norway's are, and the figure draws Norway's minke as full because its
West Greenland stock is not an Appendix I population at all.

ONE THING THE FIGURE NAMES DIFFERENTLY FROM ITS SOURCE
------------------------------------------------------
Species+ enters the porbeagle reservation for the Party "Denmark". The figure's
column says Greenland. Denmark is the CITES Party for Greenland, and the
reservation is the one the manuscript has always attributed to Denmark and
Greenland; the generator records the Party as Species+ names it and the column
as the figure names it, so neither is silently rewritten.

Exit 0 pass, 1 fail.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

VIZ = Path(__file__).resolve().parent
ROOT = VIZ.parent
EVENTS = ROOT / "deposit/tables/cites_listing_events.csv"
SPECIES = ROOT / "deposit/tables/species.csv"

# Column as the figure names it -> Party as Species+ names it.
STATES = [("Iceland", "Iceland"), ("Norway", "Norway"), ("Greenland", "Denmark"),
          ("Finland", "Finland"), ("Sweden", "Sweden")]
# The other three Arctic states, which the figure omits because they hold none.
OTHERS = ["Canada", "United States of America", "Russian Federation"]

# Stock notes that restrict a reservation to some stocks with no other
# reservation of the same Party covering the rest.
PARTIAL_NOTES = ("Reservation not applicable to stocks", "Stocks in (A)")


def current_reservations():
    names = {}
    with open(SPECIES, newline="") as f:
        for r in csv.DictReader(f):
            names[r["id"]] = (r["scientific_name"], r["common_name"])
    out = defaultdict(list)
    with open(EVENTS, newline="") as f:
        for r in csv.DictReader(f):
            if r["change_type"] != "r" or r["is_current"] != "t":
                continue
            sci, common = names[r["species_id"]]
            out[(r["party"], sci)].append((r["appendix"], r["note"], common))
    return out


def rows():
    res = current_reservations()
    table = []
    for column, party in STATES + [(p, p) for p in OTHERS]:
        for (p, sci), events in sorted(res.items()):
            if p != party:
                continue
            apps = sorted({a for a, _, _ in events})
            appendix = "I" if "I" in apps else apps[0]
            notes = [n for _, n, _ in events if n]
            partial = any(n.startswith(PARTIAL_NOTES) for n in notes)
            table.append((column, party, sci, events[0][2], appendix,
                          "partial" if partial else "full", "; ".join(notes)))
    return table


def self_test(table):
    by = defaultdict(lambda: {"I": 0, "II": 0})
    for column, _, _, _, app, _, _ in table:
        by[column][app] += 1
    want = {"Iceland": (7, 7), "Norway": (4, 1), "Greenland": (0, 1),
            "Finland": (0, 0), "Sweden": (0, 0)}
    for column, (i, ii) in want.items():
        got = (by[column]["I"], by[column]["II"])
        assert got == (i, ii), f"SELF-TEST: {column} I/II is {got}, the figure draws {(i, ii)}"
    for p in OTHERS:
        assert sum(by[p].values()) == 0, f"SELF-TEST: {p} holds {dict(by[p])}; the figure omits it as holding none"
    partial = sorted((c, s) for c, _, s, _, _, k, _ in table if k == "partial")
    assert partial == [("Norway", "Balaenoptera borealis"), ("Norway", "Balaenoptera physalus")], \
        f"SELF-TEST: the figure's two hollow circles are Norway's fin and sei whales, got {partial}"
    print("  self-test: PASS (Iceland 14 = 7 + 7, Norway 5 = 4 + 1 with fin and sei "
          "partial, Greenland 1, Finland 0, Sweden 0; Canada, USA and Russia hold none)")


def main():
    table = rows()
    self_test(table)
    out = VIZ / "source_data" / "figureC_source_data.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state_column", "cites_party", "scientific_name", "common_name",
                    "appendix", "coverage", "species_plus_note"])
        w.writerows(table)
    print(f"  wrote {out.relative_to(ROOT)} ({len(table)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
