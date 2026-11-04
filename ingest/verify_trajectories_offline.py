#!/usr/bin/env python3
"""The paper's headline finding, recomputed from the deposit alone.

WHY THIS EXISTS
---------------
The trajectory split is what the paper is for: of the 43 CITES-listed Arctic
species, 40 carry a comparable Red List trajectory, and 20 of those are
unchanged, 12 improved and 8 deteriorated. Every other number in the paper
supports that one.

The whole series is in the deposit: figure5_source_data.csv inside
source_data.zip carries every assessment in the series for every species with
its year and category. So the finding is reproducible from the deposited
package with no credentials, no network and no database.

This check recomputes it and holds three things to each other: the deposit, the
traceability table, and the manuscript. If any one of them moves without the
others, it fails and says which.

THE SERIES, from 21 October 2026
--------------------------------
Everything above describes the paper as first submitted, when the trajectory was
computed on global assessments only. The lead author decided on 21 October 2026
that European regional assessments are included. Per species the Global and
Europe assessments now form ONE series ordered by (year, assessment_id), built
by redlist_scale.series_rows; in a year with several assessments the higher
assessment id stands (redlist_scale.pick_in_year), the transition count keeps
both rows of a same-year pair, and the Mediterranean porbeagle assessment
(redlist_scale.NOT_EUROPEAN_IDS) stays out. On that series 41 of the 43 species
carry a comparable trajectory: 18 unchanged, 13 improved, 10 deteriorated,
2 without one (roseroot and Stejneger's beaked whale), with 43 transitions
(22 improvements, 21 deteriorations).

Exit 0 pass, 1 fail, 3 unmeasured.
"""
import collections
import csv, io, os, pathlib, re, sys, zipfile
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
DEPOSIT = HERE.parent
REPO = DEPOSIT.parent
ZIP = DEPOSIT / "source_data.zip"
MEMBER = "Source Data/figure5_source_data.csv"
TRACE = DEPOSIT / "results_traceability.csv"
# The manuscript the numbers are held to: the 21 October 2026 text with the
# lead author's decision (global and European assessments) applied.
# The manuscript is not part of the public release. Set ARCTIC_MANUSCRIPT_DOCX
# to a copy of it and ARCTIC_LIVE_TEXT_DIR to the directory holding the
# live_text helper; without both, the manuscript comparison is skipped and the
# run says so.
_DOC_ENV = os.environ.get("ARCTIC_MANUSCRIPT_DOCX")
DOC = pathlib.Path(_DOC_ENV) if _DOC_ENV else None
_LIVE_ENV = os.environ.get("ARCTIC_LIVE_TEXT_DIR")
LIVE_TEXT_DIR = pathlib.Path(_LIVE_ENV) if _LIVE_ENV else None

# The IUCN ladder, least to most threatened. Pre-2001 codes that carry a
# direction are placed on it; the ones that do not (K, V, E, R, I, T, NR, DD,
# NA) are absent on purpose, so a species whose only assessments are those has
# no comparable trajectory rather than a guessed one.
#
# The ladder is not written out here: it is imported from redlist_scale.py,
# the one scale that the figure generators and the claims verifier also
# import, so no two copies can disagree. LR/cd is placed as the crosswalk the
# Methods cite (ref 76) places it, and RE is kept off the global ladder.
#
# The module is imported from beside this file, because a deposit that reaches
# back into the repository is only as durable as the repository; build_deposit.py
# copies redlist_scale.py in for exactly this reason, and the two copies are now
# the same file.
# Importing a sibling here writes __pycache__ INTO the deposit, and
# verify_deposit_accounted.py rejects bytecode in a citable archive. Running
# these scripts in place is the intended use, so the run must not leave
# residue behind, or the archive gate would fail merely because the verifiers
# had been run.
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import redlist_scale as _rl

# Every code the module can rank under the convention in force: the modern
# ladder, the 2001 renames, and whatever the selected crosswalk adds. Built by
# asking the module rather than by restating it, so this file cannot drift from
# it again.
RANK = {code: _rl.rank(code)
        for code in (list(_rl.RANK) + list(_rl.EQUIVALENT)
                     + list(_rl.CROSSWALK_LIN2025))
        if _rl.rank(code) is not None}

# Extended to 2025 on the lead author's instruction of 1 October 2026. It costs
# the split nothing, because every 2025 global assessment repeats the category
# its species already held; the one number it moves is the transition count.
WINDOW = (1982, 2025)
# SCOPE was "Global" until 21 October 2026; the series is now global and
# European, selected by redlist_scale.series_rows / in_series.


def trajectories():
    """(improved, unchanged, deteriorated, comparable, species without one)."""
    with zipfile.ZipFile(ZIP) as z:
        rows = list(csv.DictReader(io.StringIO(z.read(MEMBER).decode())))
    everyone = {r["scientific_name"] for r in rows}
    series = {sp: [(int(r["year"]), r["status"]) for r in recs
                   if r["status"] in RANK]
              for sp, recs in _rl.series_rows(rows, window=WINDOW).items()}

    imp = unch = det = 0
    comparable = []
    for sp, a in series.items():
        if len(a) < 2:
            continue
        d = RANK[a[-1][1]] - RANK[a[0][1]]
        comparable.append(sp)
        if d < 0:
            imp += 1
        elif d == 0:
            unch += 1
        else:
            det += 1
    return imp, unch, det, len(comparable), sorted(everyone - set(comparable))


# Sensitivity to the pre-1994 categories. V and E are excluded from the ladder
# because they were assessed under superseded criteria, not because they carry
# no direction. The Methods and Table 3 report what happens if V is read as VU
# and E as EN, so this gate recomputes it. On the global-and-European series
# that reading moves two species (the bowhead whale, deteriorated to improved,
# and the polar bear, deteriorated to unchanged) and changes the totals from
# 13 improved, 18 unchanged, 10 deteriorated and 2 without a trajectory to
# 14, 19, 8 and 2.
VE_MOVERS = {"Balaena mysticetus": ("deteriorated", "improved"),
             "Ursus maritimus": ("deteriorated", "unchanged")}
VE_ALT_SPLIT = (14, 19, 8, 2)      # improved, unchanged, deteriorated, unknown


def ve_sensitivity():
    """(published split, split with V=VU and E=EN, {species: (before, after)})."""
    with zipfile.ZipFile(ZIP) as z:
        rows = [r for r in csv.DictReader(io.StringIO(z.read(MEMBER).decode()))
                if _rl.in_series(r) and WINDOW[0] <= int(r["year"]) <= WINDOW[1]]
    everyone = {r["scientific_name"] for r in rows}

    def classify(extra):
        rank = dict(RANK)
        rank.update(extra)
        series = {sp: [(int(r["year"]), r["status"]) for r in recs
                       if r["status"] in rank]
                  for sp, recs in _rl.series_rows(rows).items()}
        out = {}
        for sp in everyone:
            a = series.get(sp, [])
            if len(a) < 2:
                out[sp] = "unknown"
                continue
            d = rank[a[-1][1]] - rank[a[0][1]]
            out[sp] = "improved" if d < 0 else ("deteriorated" if d > 0 else "unchanged")
        return out

    def split(c):
        n = Counter(c.values())
        return (n["improved"], n["unchanged"], n["deteriorated"], n["unknown"])

    base, alt = classify({}), classify({"V": 2, "E": 3})
    moved = {sp: (base[sp], alt[sp]) for sp in base if base[sp] != alt[sp]}
    return split(base), split(alt), moved


# The current category distribution (the most recent assessment per species)
# is a number the paper states, so it is recomputed here and tied to
# traceability claims C23 to C28. A wrong count can hide behind a correct
# total, because any distribution of 43 species sums to 43, so each category
# is checked on its own. One species' latest assessment of either scope is
# Regionally Extinct, so RE carries its own claim (C148).
CATEGORIES = ["CR", "EN", "VU", "NT", "LC", "DD", "RE"]
DIST_CLAIMS = dict(zip(CATEGORIES, ["C23", "C24", "C25", "C26", "C27", "C28", "C148"]))


def current_distribution():
    """Most recent assessment per species (global or European), counted by category.

    The tie-break is the part that matters, and this function had the same
    accidental one as verify_claims_offline.py until 6 October 2026: "keep the
    row with the later year", which on a tie keeps whichever row the CSV listed
    first. Seven species carry two global assessments in their final year, and
    for two of them the rows disagree on the category (one species in 2021, one
    in 2025). In both the row that
    came first is the one the deposit marks is_latest=False, so both verifiers
    reported a superseded assessment as current, and because they shared the
    same accident they agreed with each other and the disagreement was
    invisible. Two deposited verifiers agreeing on a wrong rule is worse than
    one being wrong.

    The rule lives in redlist_scale.pick_in_year: within a year the higher
    assessment id is the later publication and it stands, with is_latest as a
    cross-check where it exists. It is NOT the flag alone - the flag marks a
    species' current assessment, so it is absent from mid-series ties and
    cannot settle them. The two verifiers call the same function, which is what
    keeps them in step; sharing an accidental rule is what let them agree while
    both were wrong.
    """
    with zipfile.ZipFile(ZIP) as z:
        rows = list(csv.DictReader(io.StringIO(z.read(MEMBER).decode())))
    # Before anything is counted: the tie-break guard has to be seen working.
    # Series are ordered by (year, assessment_id), so no value here depends on
    # the alphabet; the final-year tie is settled by pick_in_year, which refuses
    # when is_latest contradicts the higher id.
    if not _rl.self_test_tiebreak():
        raise SystemExit("the tie-break guard cannot be trusted; nothing checked")
    latest = {}
    for who, recs in _rl.series_rows(rows, window=WINDOW).items():
        ymax = int(recs[-1]["year"])
        final = [r for r in recs if int(r["year"]) == ymax]
        latest[who] = (ymax, _rl.pick_in_year(final)["status"])
    return collections.Counter(s for _, s in latest.values())


def traced():
    out = {}
    for r in csv.DictReader(open(TRACE)):
        out[r["claim_id"]] = r["value"]
    return out


def self_test():
    """The ladder has to be able to tell the three verdicts apart."""
    assert RANK["LC"] < RANK["VU"] < RANK["CR"], "the ladder is not ordered"
    assert "DD" not in RANK and "K" not in RANK, \
        "a category with no direction is on the ladder"
    assert RANK["LR/lc"] == RANK["LC"], "the legacy least-concern code moved"
    # The two codes the project held two answers about. Asserted here so a
    # future edit to either table fails this gate rather than moving a number.
    assert RANK["LR/cd"] == RANK["NT"], \
        "LR/cd is not Near Threatened; the Methods cite a crosswalk that says it is"
    assert "RE" not in RANK, \
        "Regionally Extinct is on the global ladder; it is a regional outcome"
    assert _rl.convention() == _rl.CONVENTION_LIN2025, \
        ("the scale module is not on the convention the Methods state; this gate "
         "would recompute the paper's headline finding under a different scale")
    print("  self-test: PASS (the ladder is ordered, categories carrying no "
          "direction are off it, LR/cd reads as NT and RE is not on it)",
          file=sys.stderr)


def genuine_transitions():
    """Category transitions on the global-and-European series, by the one scale.

    Until 21 October 2026 this counted global assessments only and the manuscript
    reported 36 transitions (18 improvements, 18 deteriorations). The lead author
    then decided that European regional assessments are included: the Global and
    Europe assessments of a species form one series ordered by
    (year, assessment_id), both rows of a same-year pair stay in the sequence as
    the published method always counted them, and the Mediterranean porbeagle
    assessment stays out. redlist_scale.py is the one scale: a non-comparable
    assessment breaks the chain rather than being skipped over, so no transition
    is manufactured across a gap.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import redlist_scale as rl
    with zipfile.ZipFile(ZIP) as z:
        rows = list(csv.DictReader(io.StringIO(z.read(MEMBER).decode())))
    out = []
    for name, recs in rl.series_rows(rows, window=WINDOW).items():
        out.extend(rl.transitions([(int(r["year"]), r["status"]) for r in recs]))
    return out, sum(1 for t in out if t[-1] == "improved")


def main():
    self_test()
    if not ZIP.exists():
        print(f"UNMEASURED: {ZIP.name} is not in the deposit.", file=sys.stderr)
        return 3

    imp, unch, det, comparable, without = trajectories()
    trans, ups = genuine_transitions()
    faults = []

    t = traced()
    for claim, got, what in (("C19", imp, "improved"),
                             ("C20", unch, "unchanged"),
                             ("C21", det, "deteriorated")):
        want = t.get(claim, "")
        if want != str(got):
            faults.append(f"the traceability table has {claim} ({what}) as "
                          f"{want!r}; the deposit computes {got}")

    # --deposit-only compares the deposit with the traceability table and stops
    # there. The pass that writes the manuscript sentence calls it this way,
    # because the full check holds the manuscript to a sentence that pass has not
    # written yet: a gate that blocks the edit satisfying it is a circle, not a
    # check. After the pass runs, the full gate holds the three to each other.
    # The current distribution, claim by claim and then in the sentence.
    dist = current_distribution()
    if sum(dist.values()) != comparable + len(without):
        faults.append(f"the distribution covers {sum(dist.values())} species; "
                      f"the study set is {comparable + len(without)}")
    for cat in CATEGORIES:
        claim = DIST_CLAIMS[cat]
        want, got = t.get(claim, ""), dist.get(cat, 0)
        if want != str(got):
            faults.append(f"the traceability table has {claim} (current {cat}) "
                          f"as {want!r}; the deposit computes {got}")

    # The V/E sensitivity the Methods and Table 3 now report.
    ve_base, ve_alt, ve_moved = ve_sensitivity()
    if ve_base != (imp, unch, det, len(without)):
        faults.append(f"the V/E check recomputes the published split as "
                      f"{ve_base}, which is not {(imp, unch, det, len(without))}")
    if ve_alt != VE_ALT_SPLIT:
        faults.append(f"reading V as VU and E as EN is recorded as giving "
                      f"{VE_ALT_SPLIT} (improved, unchanged, deteriorated, "
                      f"unknown) on the global-and-European series; the deposit "
                      f"gives {ve_alt} against {ve_base} unread")
    if ve_moved != VE_MOVERS:
        faults.append(f"the species that move between classes when V and E are "
                      f"read as VU and EN are recorded as {sorted(VE_MOVERS)}; the deposit moves {sorted(ve_moved)} "
                      f"({ve_moved})")

    deposit_only = "--deposit-only" in sys.argv
    manuscript_compared = False
    if deposit_only:
        print("  note: --deposit-only, so the manuscript was not compared",
              file=sys.stderr)
    elif DOC is not None and LIVE_TEXT_DIR is not None and DOC.exists():
        manuscript_compared = True
        sys.path.insert(0, str(LIVE_TEXT_DIR))
        import live_text
        live = re.sub(r"\s+", " ", live_text.from_docx(DOC))
        total = comparable + len(without)
        pct = lambda k: f"{100 * k / total:.1f}"
        sentence = (f"Of {total} species, {imp} improved, {unch} were "
                    f"unchanged, {det} deteriorated and {len(without)} lack a "
                    f"comparable trajectory. Across {WINDOW[0]}\u2013{WINDOW[1]}, "
                    f"the record contains {ups} improving and "
                    f"{len(trans) - ups} deteriorating category transitions.")
        if sentence not in live:
            faults.append("the manuscript no longer states what the deposit "
                          f"computes. The deposit gives: {sentence}")

        # The transition count ANYWHERE in the paper, not only in that one
        # sentence. A count repeated in a caption or another section is held to
        # the deposit as well, since a check that looks for one sentence cannot
        # see the others.
        #
        # A number the paper repeats is a number that must be repaired
        # everywhere, so every count-of-transitions in the accepted text is
        # held to the deposit, caption and prose alike. The notes are stripped
        # first: a margin note quotes the number it is withdrawing.
        prose = re.sub(r"\s+", " ",
                       re.sub(r"\[(?:TOM|MINT|SET|TOM og MAGN\u00daS|TOM/MINT|TOM/SET)[^\]]*\]",
                              "", live))
        for m in re.finditer(r"(\d+)\s+(?:category |genuine )?transitions?", prose):
            if int(m.group(1)) != len(trans):
                faults.append(
                    f"the paper says {m.group(1)} transitions where the deposit "
                    f"computes {len(trans)}: ..."
                    + prose[max(0, m.start() - 70):m.end() + 40].strip() + "...")
        for m in re.finditer(r"the (\d+) counted in Section", prose):
            if int(m.group(1)) != len(trans):
                faults.append(
                    f"a cross-reference says {m.group(1)} where the deposit "
                    f"computes {len(trans)}: ..."
                    + prose[max(0, m.start() - 70):m.end() + 40].strip() + "...")
        if dist["DD"] != 0 or dist["RE"] != 1:
            faults.append(f"the manuscript's sentence names one Regionally "
                          f"Extinct species and none Data Deficient; the deposit "
                          f"gives {dist['RE']} RE and {dist['DD']} DD")
        stated = ("the current distribution includes "
                  + ", ".join(f"{dist[c]} {c}" for c in CATEGORIES[:3])
                  + f", {dist['NT']} NT and {dist['LC']} LC species, and one "
                  + "Regionally Extinct (RE)")
        if stated not in live:
            i = live.find("the current distribution includes")
            faults.append(
                "the manuscript's current distribution is not what the deposit "
                f"computes.\n      deposit: {stated}\n      paper  : "
                + (live[i:i + 120] if i >= 0 else "the sentence is absent"))

        # The two shares the Abstract and the Discussion carry, on the same base.
        hold = unch + imp
        for share, where in ((f"{100 * hold / total:.1f}%", "hold or improve"),
                             (f"{100 * imp / total:.1f}%", "improve outright")):
            if share not in live:
                faults.append(f"the manuscript does not state {share} anywhere, "
                              f"which is what the deposit gives for {where} of "
                              f"all {total} species")
    else:
        print("  skipped: the manuscript comparison (the manuscript is not part of "
              "the public release; set ARCTIC_MANUSCRIPT_DOCX and "
              "ARCTIC_LIVE_TEXT_DIR to run it). Only the deposit and the "
              "traceability table were compared.", file=sys.stderr)

    if len(without) != 2:
        faults.append(f"{len(without)} species have no comparable trajectory; "
                      f"the paper reports 2 ({', '.join(without)})")

    if faults:
        print(f"\nTHE HEADLINE FINDING ({len(faults)}):\n", file=sys.stderr)
        for f in faults:
            print(f"  {f}", file=sys.stderr)
        return 1

    print(f"transitions: {len(trans)} category transitions between "
          f"comparable global and European assessments ({ups} improvements, "
          f"{len(trans) - ups} deteriorations) in {WINDOW[0]}-{WINDOW[1]}")
    print(f"trajectories: {comparable} comparable, {unch} unchanged, {imp} "
          f"improved, {det} deteriorated, {len(without)} without a comparable "
          f"trajectory ({', '.join(without)}) — recomputed from the deposited "
          f"Source Data, with no database and no network, and matching "
          + ("both the traceability table and the manuscript" if manuscript_compared
             else "the traceability table (manuscript comparison skipped)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
