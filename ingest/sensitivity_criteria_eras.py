#!/usr/bin/env python3
"""How much of the trajectory signal needs an assessment made under superseded
IUCN criteria.

Written 6 October 2026 to answer this objection:

    "The paper's only outcome measure is Red List category change, and the paper
     concedes it cannot separate genuine status change from change arising from
     revised criteria, improved knowledge or taxonomy - the exact distinction
     IUCN requires before category change is read as a conservation signal.
     Stated plainly, this removes the contribution: the headline 46.5/27.9/18.6
     split and the 18-against-18 transition balance may be substantially an
     artefact of assessment practice over four decades spanning the 1994 and
     2001 criteria revisions. No sensitivity analysis bounds how much of the
     signal survives."

The last sentence was true. This bounds it, and the answer is not one-sided, so
both instruments are reported and the confound in the second one is named.

INSTRUMENT 1 - transitions that cannot cross a revision. A transition is a step
between two consecutive comparable assessments. If both are dated 2001 or later,
no criteria revision lies between them, so the step cannot be an artefact of one.
This is the instrument that answers the question as asked, because it holds the
criteria fixed WITHIN each comparison.

INSTRUMENT 2 - species reclassified on modern assessments alone. Restricting
every species' series to assessments dated 2001 or later and re-running the
earliest-against-latest classification. This answers a different and harsher
question - how much of the SPECIES-level result needs the older assessments -
and it carries a confound that must be stated: it also shortens the window from
43 years to 24, which reduces movement mechanically and independently of criteria.

Exit 0 when both instruments compute, 1 when the deposited inputs cannot support
them, 3 unmeasured. Nothing here is a claim in the manuscript yet; if a
sensitivity paragraph is adopted, these numbers become traceability claims and
this file becomes their query.
"""
import collections
import csv
import io
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import redlist_scale as rl  # noqa: E402
# The deposit ships no IUCN category, so the series is read through the shim
# that prefers a local rebuild. Without it this script read the withheld file,
# computed zeros in every bucket and still printed its self-test as PASS -
# silence is not a pass, and a measurement of nothing is not a measurement.
sys.path.insert(0, str(HERE.parent / "deposit" / "verification"))
import iucn_series  # noqa: E402

DEPOSIT = (HERE.parent / "deposit") if (HERE.parent / "deposit").is_dir() else HERE.parent
ZIP = DEPOSIT / "source_data.zip"
MEMBER = "Source Data/figure5_source_data.csv"
WINDOW = (1982, 2025)
# The two criteria revisions. 1994 introduced the quantitative criteria,
# 2001 the version the modern categories are assessed under.
REVISIONS = (1994, 2001)


def series():
    with zipfile.ZipFile(ZIP) as z:
        rows = list(csv.DictReader(io.StringIO(
            iucn_series.read_member(z, MEMBER).decode())))
    # From 21 October 2026 the series is global and European, ordered by
    # (year, assessment_id): the lead author's decision, built by
    # redlist_scale.series_rows so every verifier selects the same rows.
    return {sp: [(int(r["year"]), r["status"]) for r in recs]
            for sp, recs in rl.series_rows(rows).items()}


def transitions_by_era(glob):
    """Every in-window transition, split by whether a revision lies inside it."""
    buckets = collections.defaultdict(list)
    for sp, a in glob.items():
        inside = [x for x in a if WINDOW[0] <= x[0] <= WINDOW[1]]
        for y0, y1, direction in rl.transitions(inside):
            for cut in REVISIONS:
                key = ("after", cut) if y0 >= cut else \
                      ("straddles", cut) if y1 >= cut else ("before", cut)
                buckets[key].append((sp, y0, y1, direction))
    return buckets


def classify_from(glob, lo):
    """Earliest against latest comparable assessment, restricted to year >= lo."""
    c = collections.Counter()
    for sp, a in glob.items():
        inside = [x for x in a
                  if lo <= x[0] <= WINDOW[1] and rl.rank(x[1]) is not None]
        if len(inside) < 2:
            c["no trajectory"] += 1
            continue
        d = rl.rank(inside[-1][1]) - rl.rank(inside[0][1])
        c["improved" if d < 0 else "deteriorated" if d > 0 else "unchanged"] += 1
    return c


def self_test():
    """The instruments must separate what they claim to separate."""
    # A transition whose endpoints straddle 2001 must not be counted as "after".
    straddle = rl.transitions([(1996, "VU"), (2008, "NT")])
    assert len(straddle) == 1 and straddle[0][0] == 1996, \
        "SELF-TEST: transitions() no longer reports the opening year"
    # Restricting a series must be able to remove a trajectory entirely.
    only_old = classify_from({"x": [(1990, "VU"), (1996, "NT")]}, 2001)
    assert only_old["no trajectory"] == 1, \
        "SELF-TEST: restricting the series does not drop a pre-cut pair"
    # And must be able to keep one.
    kept = classify_from({"x": [(2004, "VU"), (2019, "NT")]}, 2001)
    assert kept["improved"] == 1, "SELF-TEST: a post-cut improvement is lost"
    print("  self-test: PASS (a straddling pair is not an after-pair, and "
          "restricting the series both drops and keeps trajectories)")


def main():
    if not ZIP.exists():
        print(f"UNMEASURED: {ZIP} is not here")
        return 3
    self_test()
    glob = series()
    if len(glob) != 43:
        print(f"the deposited series covers {len(glob)} species, not 43")
        return 1

    buckets = transitions_by_era(glob)
    total = sum(len(v) for k, v in buckets.items() if k[1] == REVISIONS[1])
    print()
    print("INSTRUMENT 1 - transitions, by where the 2001 revision falls")
    print(f"  {'bucket':24} {'n':>4} {'improved':>9} {'deteriorated':>13}")
    for name in ("after", "straddles", "before"):
        rows = buckets[(name, 2001)]
        c = collections.Counter(d for *_, d in rows)
        label = {"after": "both endpoints 2001+",
                 "straddles": "straddles 2001",
                 "before": "both before 2001"}[name]
        print(f"  {label:24} {len(rows):>4} {c['improved']:>9} "
              f"{c['deteriorated']:>13}")
    print(f"  {'all in-window':24} {total:>4}")
    after94 = buckets[("after", 1994)]
    c94 = collections.Counter(d for *_, d in after94)
    print(f"  (both endpoints 1994+:   {len(after94)}, improved "
          f"{c94['improved']}, deteriorated {c94['deteriorated']})")

    print()
    print("INSTRUMENT 2 - species reclassified from a later start year")
    print(f"  {'series restricted to':24} {'unch':>5} {'impr':>5} {'deter':>6} "
          f"{'none':>5}")
    for lo in (WINDOW[0], 1994, 2001):
        c = classify_from(glob, lo)
        print(f"  {str(lo) + '-2025':24} {c['unchanged']:>5} {c['improved']:>5} "
              f"{c['deteriorated']:>6} {c['no trajectory']:>5}")
    print("  NOTE: restricting the start year also shortens the window, from 43 "
          "years to 24 at 2001, which reduces movement independently of any "
          "criteria change. Instrument 1 is the one that holds criteria fixed "
          "within each comparison; this one does not and must not be read as if "
          "it did.")
    print()
    print("What neither instrument bounds: category change arising from improved "
          "knowledge or from taxonomy within one criteria era. That needs IUCN's "
          "reason-for-change field, which the deposited assessment series does "
          "not carry, and the manuscript says so.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
