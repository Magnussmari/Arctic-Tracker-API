#!/usr/bin/env python3
"""The one Red List scale. Every trajectory number in this project comes from here.

WHY THIS MODULE EXISTS
----------------------
Earlier versions of this repository had five scripts ranking IUCN categories,
carrying three different scales:

  figure4_conservation_trends.py   'K': 1,  # Legacy insufficiently known (treat as LC)
  generate_all_article_statistics.py   K absent -> .get(status, 0) -> 0
  generate_article_statistics.py       K absent -> 0
  generate_iucn_historic_timeline.py   K absent -> 0
  data_processing/generate_iucn_timeline_pg.py   K absent -> 0

The two implementations disagreed on the direction of change for 30 of 43
species. In one, "Insufficiently Known" meant Least Concern; in the other it
meant worse than Least Concern. Neither is defensible and no reader could tell
which produced a given number.

THE DECISION (D10, 2026-08-10)
------------------------------
Legacy categories are NOT mapped onto the modern scale. Species whose baseline
is a non-comparable legacy category are excluded from trajectory analysis and
the exclusion is reported.

This implements the manuscript's own stated rule:

    Non-genuine changes (revised taxonomy, new data, criteria revision,
    improved knowledge) are recorded separately and excluded.

It is also the discipline standard. The Red List Index counts only *genuine*
status changes; IUCN codes 'criteria revision' as an explicitly non-genuine
reason for a category change, and the accepted remedy for older assessments is
back-casting, that is retrospective re-assessment under current criteria by
specialists (Butchart et al. 2004, 2007). We cannot back-cast: that requires
the assessors, not a script. So we exclude, and we say how many.

THE THREE RULES
---------------
1. COMPARABLE RANKS are the 2001-system threat categories only:
       LC < NT < VU < EN < CR   (plus EW, EX above CR)
   A change between two of these is a candidate genuine change.

2. NOMENCLATURE EQUIVALENCES are not changes at all. The 2001 revision renamed
   the Lower Risk subcategories; the species did not move.
       LR/lc == LC        LR/nt == NT
   A step from LR/lc to LC is recorded as *unchanged*, not as an improvement
   and not as a deterioration. This is the only legacy handling permitted, and
   it is permitted because it is a rename rather than a re-evaluation.

3. NON-COMPARABLE categories cannot begin or end a trajectory:
       K, T, NR, NA, N/A   knowledge states or unresolved threat levels,
                           not risk ranks. K is the modern DD.
       V, E                pre-1994 criteria. Superficially VU and EN, but
                           assigned under criteria the 1994 revision replaced.
                           Treating them as equivalent is exactly the criteria
                           revision the Methods exclude.
       LR/cd               discontinued in 2001 with no modern equivalent.
       DD, RE              DD is a knowledge state. RE is a regional outcome
                           and is not on the global threat scale.

WHAT THIS COSTS
---------------
It reduces the number of species that can carry a trajectory. That is the
correct outcome. The alternative reported a larger number by counting an
assessor's improved knowledge as a species' recovery, and by treating a 1994
criteria change as a real-world change. A smaller comparable denominator is
preferred to a larger one built on non-comparable baselines.
"""
from __future__ import annotations

# Comparable 2001-system ranks. Higher is more threatened.
RANK = {"LC": 0, "NT": 1, "VU": 2, "EN": 3, "CR": 4, "EW": 5, "EX": 6}

# Pure renames from the 2001 revision. The species did not move.
EQUIVALENT = {"LR/lc": "LC", "LR/nt": "NT"}

# Everything else, with the reason it cannot enter a trajectory.
NON_COMPARABLE = {
    "K":     "Insufficiently Known: a knowledge state, the modern DD, not a risk rank",
    "T":     "Threatened, unresolved between VU/EN/CR",
    "NR":    "Not Recorded: never assessed",
    "NA":    "Not Applicable",
    "N/A":   "Not assessed",
    "V":     "pre-1994 Vulnerable, assigned under criteria the 1994 revision replaced",
    "E":     "pre-1994 Endangered, assigned under criteria the 1994 revision replaced",
    "LR/cd": "Lower Risk conservation dependent, discontinued in 2001 with no equivalent",
    "DD":    "Data Deficient: a knowledge state, not a risk rank",
    "RE":    "Regionally Extinct: a regional outcome, not on the global threat scale",
}


# ---------------------------------------------------------------------------
# CONVENTION SWITCH (added 2026-09-27, at the lead author's request)
#
# The Lin et al. (2025) / Morton et al. (2022) crosswalk. Both quotes are
# verbatim:
#
#   Lin et al. 2025, Conservation Biology 39(6), doi:10.1111/cobi.70103,
#   Figure 2 caption: "possibly extinct and possibly extinct in the wild were
#   treated as critically endangered; not threatened, low risk, lower risk or
#   conservation dependent, and low risk or near threatened were treated as near
#   threatened; and low risk or least concern was treated as least concern".
#
#   Morton et al. 2022, Current Biology 32(5), doi:10.1016/j.cub.2022.01.011,
#   STAR Methods: "We converted pre-2000 codes (lr/cd/nt) and removed all other
#   older notations (such as 'rare' or 'CT', commercially threatened) ... 'lr'
#   (least concern), 'cd' (near-threatened) and 'nt' (near-threatened)."
#
# MEASURED against our 43 species (global scope) before implementing:
#   LR/cd    7 assessments, 7 species   -> the only row that moves anything
#   LR/lc   22 assessments, 12 species  -> already a rename under D10 rule 2
#   LR/nt    2 assessments,  2 species  -> already a rename under D10 rule 2
#   PE      10 assessments,  1 species  -> already on the category the
#                                          crosswalk assigns PE
#   bare LR  0 assessments              -> the one point where the two sources
#                                          contradict each other (Lin: NT,
#                                          Morton: LC) is moot in our data
#   K/V/E/T/NR/NA/N/A/DD/RE             -> "all other older notations", which
#                                          Morton removes exactly as D10 does
#
# So the crosswalk is one rule wide here: LR/cd -> NT. Everything else it names
# is either already implemented or absent.
#
# WHAT THE SWITCH DOES NOT CARRY. Lin's crosswalk lives in a caption that ends:
# "Changes unrelated to population improvement or worsening (not genuine
# changes) were excluded". Lin counted 1,511 species with a GENUINE status
# change out of 163,040, and report that only 5-33% of annual category changes
# are genuine at all. We hold no reason-for-change field, so that filter is not
# implementable here (checked: arctic_v2.iucn_assessments has no such column;
# the only `change_type` in the database belongs to cites_listing_events).
# This is stated in Methods rather than silently omitted, because LR/cd's
# removal in 2001 is itself a classification change and would be non-genuine
# under Lin's own rule.
CONVENTION_D10 = "d10"          # legacy categories excluded
CONVENTION_LIN2025 = "lin2025"  # the Lin/Morton crosswalk: LR/cd treated as NT

CROSSWALK_LIN2025 = {"LR/cd": "NT"}

# WHY THE DEFAULT IS THE CROSSWALK
# --------------------------------
# The paper states the crosswalk in Methods. With D10 as the default, every
# caller that did not ask for the crosswalk would produce a number the paper
# does not report, silently and with no gate able to see it. Two consequences:
#
#   * This file exists in two copies: ingest/redlist_scale.py, which
#     build_deposit.py copies from and the figure generators import, and
#     deposit/verification/redlist_scale.py. They must stay identical. The
#     convention decides the headline split (12/20/8 under the crosswalk,
#     8/23/7 under D10), so a change made to one copy only would be reverted
#     by the next deposit rebuild.
#
#   * verify_claims_offline.py imports this module, so the transition count
#     (C22) and the species split in the same manuscript sentence are computed
#     under one convention. The crosswalk gives 36 transitions and D10 gives
#     34. The two extra transitions belong to species whose 1996 assessment
#     uses LR/cd and whose next assessment is on the modern scale; one of them
#     is a deterioration that places its species among the eight.
#
# So the default is the convention the paper states. Forgetting to choose
# gives the published number; D10 is what you opt into, which is what the
# sensitivity analyses do. RE is untouched by this: the crosswalk says nothing
# about it and a regional outcome is still not on the global threat scale.
_convention = CONVENTION_LIN2025


def set_convention(name: str) -> None:
    """Choose the mapping convention. D10 is now the one you opt into."""
    global _convention
    if name not in (CONVENTION_D10, CONVENTION_LIN2025):
        raise ValueError(f"unknown convention {name!r}")
    _convention = name


def convention() -> str:
    return _convention


def normalise(status: str | None, convention: str | None = None) -> str | None:
    """Map a raw status to a comparable category, or None if non-comparable."""
    if not status:
        return None
    s = status.strip()
    if (convention or _convention) == CONVENTION_LIN2025:
        s = CROSSWALK_LIN2025.get(s, s)
    s = EQUIVALENT.get(s, s)
    return s if s in RANK else None


def rank(status: str | None, convention: str | None = None) -> int | None:
    """Ordinal rank of a status, or None when it cannot be ranked."""
    n = normalise(status, convention)
    return RANK[n] if n is not None else None


def comparable(status: str | None) -> bool:
    return rank(status) is not None


def reason_excluded(status: str | None) -> str:
    if status is None:
        return "no status recorded"
    return NON_COMPARABLE.get(status.strip(), f"unrecognised category {status!r}")


def classify(first: str | None, last: str | None) -> str:
    """'improved' | 'deteriorated' | 'unchanged' | 'excluded'.

    Excluded whenever either endpoint is non-comparable: a trajectory needs two
    comparable ends, and half a comparison is not a weaker result, it is a
    different question.
    """
    a, b = rank(first), rank(last)
    if a is None or b is None:
        return "excluded"
    if b < a:
        return "improved"
    if b > a:
        return "deteriorated"
    return "unchanged"


def transitions(sequence):
    """Genuine transitions in a chronological [(year, status), ...] sequence.

    Consecutive comparable assessments only. A non-comparable assessment breaks
    the chain rather than being skipped over: pretending a 1988 'K' and a 2004
    'LC' are adjacent manufactures a transition that no assessor made.
    """
    out = []
    prev_year = prev_rank = None
    for year, status in sequence:
        r = rank(status)
        if r is None:
            prev_year = prev_rank = None
            continue
        if prev_rank is not None and r != prev_rank:
            out.append((prev_year, year,
                        "improved" if r < prev_rank else "deteriorated"))
        prev_year, prev_rank = year, r
    return out


# ---------------------------------------------------------------------------
# THE TIE-BREAK (added 2026-10-06)
#
# A species can carry TWO assessments in the SAME year. Twenty-two (species,
# year) groups in this corpus do, and in three of them the rows disagree on the
# category: Bubo scandiacus (2021), Odobenus rosmarus (2025) and Branta
# ruficollis (2015) each have two global assessments in one year with
# different categories.
#
# Without a stated rule, call sites could resolve such a tie differently:
#
#   * a "first row in the CSV" rule lets export order decide which assessment
#     is current;
#   * sorting (year, status) tuples and taking the ends takes the
#     alphabetically LATER status on a tie.
#
# THE RULE IS THE ASSESSMENT ID: within a year, the higher id is the later
# published assessment and it stands. is_latest is a CROSS-CHECK, not the rule
# - it marks a species' current assessment and so exists only on final-year
# rows, which is why it cannot settle a mid-series tie at all. A rule of
# "is_latest, otherwise the first row" would be row order under another name
# for every mid-series tie. The id rule needs no fallback: every tie has
# distinct ids.
#
# In this corpus the id rule, the flag where present, and the alphabetical sort
# pick the same row in all three conflicts, so the trajectory split does not
# depend on the rule. The current-category distribution does depend on it, and
# is computed with it. The transition count keeps both rows of a same-year
# pair: transitions() receives both, so each pair adds a step to the
# assessment this rule sets aside (36 transitions with both rows, 31 with one
# row per year, on the global series).
#
# tie_conflicts() is the guard: it reports every tie where the id rule and the
# alphabetical sort would disagree, so a corpus where they differ fails
# loudly instead of changing a published trajectory in silence.


def pick_in_year(rows):
    """The one assessment that stands, from rows sharing a year.

    `rows` are mappings with 'status' and 'assessment_id'. The higher id is the
    later publication and wins. Where is_latest is present it must agree, and a
    disagreement refuses rather than choosing.
    """
    rows = list(rows)
    if not rows:
        raise ValueError("no rows to choose between")
    if any(not str(r.get("assessment_id", "")).strip() for r in rows):
        raise ValueError("an assessment carries no id, so the tie cannot be "
                         "broken by publication order")
    pick = max(rows, key=lambda r: int(r["assessment_id"]))
    flagged = [r for r in rows if str(r.get("is_latest")) == "True"]
    if len(flagged) > 1:
        raise ValueError(f"{len(flagged)} assessments flagged is_latest in one "
                         f"year; the flag cannot cross-check the tie")
    if flagged and flagged[0]["status"] != pick["status"]:
        raise ValueError(
            f"the highest assessment id in this year gives "
            f"{pick['status']} and is_latest marks {flagged[0]['status']}; "
            f"two records of which assessment is current disagree")
    return pick


# ---------------------------------------------------------------------------
# THE SERIES (decided by the lead author, 21 October 2026)
#
# Until that day every trajectory and status number in the paper was computed on
# the GLOBAL assessments only. The decision: European regional assessments are
# included. For each species the Global and Europe assessments form ONE series,
# ordered by (year, assessment_id); in a year with several assessments the
# higher id stands (pick_in_year above), while the transition count keeps BOTH
# rows of a same-year pair, as the published method always did.
#
# Eight assessments are labelled "Global" in the series because IUCN records
# them without a scope (species_data/curated/iucn_scope_corrections.csv). Seven
# are European and so now count, as European. One is Mediterranean, Lamna nasus
# 2016 (assessment 16527805), and is excluded: it is regional but not European.
# The assessment identifier is deposited (identifiers/), so naming it here
# withholds nothing. The same exclusion is derivable from the curated file
# (species_data/curated/iucn_scope_corrections.csv).

SERIES_SCOPES = ("Global", "Europe")
NOT_EUROPEAN_IDS = frozenset({"16527805"})


def in_series(row) -> bool:
    """True if this assessment belongs to the global-and-European series."""
    return ((row.get("scope") or "Global") in SERIES_SCOPES
            and str(row["assessment_id"]).strip() not in NOT_EUROPEAN_IDS)


def series_sql(alias: str = "") -> str:
    """The same series as a SQL predicate on arctic_v2.iucn_assessments.

    For the database-backed checks, so they select exactly what in_series
    selects: scope code 1 or null (global, which includes the eight assessments
    recorded without a scope), 2 or EU (Europe), and not the Mediterranean one.
    """
    p = f"{alias}." if alias else ""
    ids = ", ".join(sorted(NOT_EUROPEAN_IDS))
    return (f"coalesce({p}scope_code, '1') in ('1', '2', 'EU') "
            f"and coalesce({p}assessment_id, 0) not in ({ids})")


def series_rows(rows, window=None):
    """{species: [row, ...]} for the global-and-European series.

    Each species' rows are in (year, assessment_id) order and a same-year pair
    keeps both rows, so transitions() sees the sequence the published method
    counted. `window` is an inclusive (first, last) year pair, or None.
    """
    out = {}
    for r in rows:
        if not in_series(r):
            continue
        y = int(r["year"])
        if window and not (window[0] <= y <= window[1]):
            continue
        out.setdefault(r["scientific_name"], []).append(r)
    for v in out.values():
        v.sort(key=lambda r: (int(r["year"]), int(r["assessment_id"])))
    return out


def tie_conflicts(rows, scope="Global", window=None):
    """Ties where the alphabetical sort and the id rule would disagree.

    `rows` are mappings with 'scientific_name', 'year', 'status', 'scope',
    'assessment_id' and optionally 'is_latest'. Returns one
    (species, year, sorted_pick, id_pick) per year in which a species has two
    or more assessments with differing categories AND the two rules choose
    differently. An empty list means every value built by sorting (year,
    status) and taking the ends is independent of the alphabet.
    """
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        if scope is not None and r.get("scope") != scope:
            continue
        y = int(r["year"])
        if window and not (window[0] <= y <= window[1]):
            continue
        groups[(r["scientific_name"], y)].append(r)
    out = []
    for (sp, y), g in sorted(groups.items()):
        if len(g) < 2 or len({r["status"] for r in g}) < 2:
            continue
        ordered = max(r["status"] for r in g)      # what a (year, status) sort takes
        chosen = pick_in_year(g)["status"]
        if ordered != chosen:
            out.append((sp, y, ordered, chosen))
    return out


def self_test_tiebreak() -> bool:
    """The guard has to be seen firing, and seen staying quiet.

    Case 1 is this corpus's shape: the later-published category also sorts
    last, so the two rules agree and nothing is reported. Case 2 is the same tie with the later publication on
    the alphabetically EARLIER category, which is what would silently flip a
    trajectory; the guard must report it. Case 3 is a tie whose rows agree,
    which is not a conflict. Case 4 is the cross-check: an is_latest flag that
    contradicts the ids refuses rather than picking. Case 5 is a mid-series tie with
    NO flag, which must still resolve by id rather than by row order.
    """
    def row(sp, y, st, i, latest=None):
        d = {"scientific_name": sp, "year": str(y), "status": st,
             "scope": "Global", "assessment_id": str(i)}
        if latest is not None:
            d["is_latest"] = "True" if latest else "False"
        return d
    lucky = [row("A", 2021, "LC", 100, False), row("A", 2021, "VU", 200, True)]
    unlucky = [row("B", 2021, "VU", 100, False), row("B", 2021, "LC", 200, True)]
    agreeing = [row("C", 2020, "EN", 100), row("C", 2020, "EN", 200)]
    midseries = [row("E", 2015, "NT", 900001), row("E", 2015, "VU", 900002)]
    if tie_conflicts(lucky) != []:
        return False
    if tie_conflicts(unlucky) != [("B", 2021, "VU", "LC")]:
        return False
    if tie_conflicts(agreeing) != []:
        return False
    if pick_in_year(midseries)["status"] != "VU":
        return False
    for bad in ([row("D", 2020, "LC", 100, True), row("D", 2020, "VU", 200, True)],
                [row("D", 2020, "LC", 300, True), row("D", 2020, "VU", 400, False)]):
        try:
            pick_in_year(bad)
        except ValueError:
            pass
        else:
            return False
    return True


if __name__ == "__main__":
    print("tie-break self-test:",
          "PASS (an unlucky tie is reported; a lucky one, an agreeing one and a "
          "flagless mid-series tie are not; a double or contradicting flag refuses)"
          if self_test_tiebreak() else "FAIL")
