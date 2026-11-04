#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
# SCALE-EXEMPT: STATUS_SEVERITY here is display ORDERING only, as the comment
# above it already says. The improvement/deterioration decision in this file
# goes through redlist_scale.rank, which is the one table.
"""IUCN historic timeline regeneration — psycopg2 port (figs 4, 5).

Logic preserved verbatim from article_update_package/generate_iucn_historic_timeline.py
(severity ranking, per-scope timelines, trend computation, quirk: unranked
historical codes default severity 0 so e.g. NR→LC reads as 'worsening').

Known intended divergence from the frozen 2025-11 JSON: `is_latest` flags now
reflect the H2 repair (2026-07-22) — the frozen file carries the corrupt flags.
Everything else must match exactly.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pg_common import query

ROOT = Path(__file__).parent.parent.parent
OUT = ROOT / "data/processed/iucn_historic_timeline.json"

# D10 (2026-08-11): trend direction comes from ingest/redlist_scale.py.
# This dict is retained ONLY for display ordering. It must not be used to
# decide whether a species improved or deteriorated: every legacy category is
# absent from it, so .get(status, 0) silently placed 'K' below Least Concern.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "ingest"))
import redlist_scale as _rl

# The manuscript's corpus is arctic_v2. Three of these generators read the
# pre-rebuild `arctic` schema instead, which is why Figure 2 was titled
# "473,102 trade records" while the manuscript reports 492,095. One name,
# overridable, so the figures and the claims cannot describe different data.
import os as _os


def _run_date() -> str:
    """The date this file was actually produced.

    These fields were hardcoded to "2026-07-22" and were still saying so on
    2026-08-15, in files regenerated minutes earlier from a different corpus.
    A provenance date that never moves is worse than an absent one: a reader
    has no reason to distrust it.

    V-29 strips these before comparing digests, so a live date does not make
    the intermediates look unreproducible.
    """
    import datetime as _dt
    return _dt.date.today().isoformat()
SCHEMA = _os.environ.get("ARCTIC_SCHEMA", "arctic_v2")

STATUS_SEVERITY = {
    'EX': 7, 'EW': 6, 'CR': 5, 'EN': 4, 'VU': 3, 'NT': 2, 'LC': 1, 'DD': 0, 'RE': 6,
}
STATUS_NAMES = {
    'EX': 'Extinct', 'EW': 'Extinct in the Wild', 'CR': 'Critically Endangered',
    'EN': 'Endangered', 'VU': 'Vulnerable', 'NT': 'Near Threatened',
    'LC': 'Least Concern', 'DD': 'Data Deficient', 'RE': 'Regionally Extinct',
}


def build():
    species = query(f"SELECT id, scientific_name, common_name FROM {SCHEMA}.species ORDER BY common_name")
    assessments = query(f"""SELECT species_id, assessment_id, status, year_published, is_latest,
                                  scope_code, scope_description
                           FROM {SCHEMA}.iucn_assessments
                          ORDER BY species_id, year_published, assessment_id""")
    # PostgreSQL returns rows in whatever order it likes without an ORDER BY, and
    # this query had none. Three consecutive regenerations on 2026-08-15 produced
    # three different digests of the timeline JSON.
    #
    # Nothing plotted moved: current_status and status_changes were identical
    # across all three runs, and the figure gate passed correctly because the
    # Source Data writers sort their own output. What varied was the order of the
    # assessment list inside each species, which is an artefact a reader diffing
    # two builds would see and reasonably distrust.
    #
    # assessment_id is the tiebreak because 22 species hold multiple global
    # assessments published in the same year — the same reason V-9's trajectory
    # query carries it.
    by_species = defaultdict(list)
    for a in assessments:
        by_species[a["species_id"]].append(a)

    timelines = []
    for sp in species:
        rows = by_species.get(sp["id"], [])
        if not rows:
            continue
        rows = sorted(rows, key=lambda a: (a["year_published"], a.get("scope_description") or "Global"))
        by_scope = defaultdict(list)
        for a in rows:
            by_scope[a.get("scope_description") or "Global"].append(a)

        scope_timelines = {}
        for scope, scope_rows in by_scope.items():
            timeline = []
            prev = None
            for a in scope_rows:
                status, year = a["status"], a["year_published"]
                trend = "stable"
                if prev:
                    ps, cs = _rl.rank(prev), _rl.rank(status)
                    if ps is None or cs is None:
                        trend = 'not comparable'
                        ps = cs = 0
                    if cs > ps:
                        trend = "worsening"
                    elif cs < ps:
                        trend = "improving"
                timeline.append({
                    "year": year, "status": status,
                    "status_name": STATUS_NAMES.get(status, status),
                    "assessment_id": a.get("assessment_id"),
                    "is_latest": a.get("is_latest", False),
                    "trend": trend,
                    "change_from_previous": f"{prev} → {status}" if prev else "Initial assessment",
                })
                prev = status
            scope_timelines[scope] = {
                "assessments": timeline,
                "first_year": timeline[0]["year"] if timeline else None,
                "latest_year": timeline[-1]["year"] if timeline else None,
                "total_assessments": len(timeline),
                "status_changes": sum(1 for t in timeline if t["trend"] != "stable"),
                "current_status": timeline[-1]["status"] if timeline else None,
                "current_status_name": timeline[-1]["status_name"] if timeline else None,
            }

        all_years = [a["year_published"] for a in rows]
        # sorted(), not list(). A set of strings iterates in an order that
        # Python randomises per process, so serialising one straight to JSON
        # made this file differ on every single run: three consecutive
        # regenerations on 2026-08-15 gave three digests. Nothing plotted
        # moved — current_status and status_changes were identical across all
        # three — but an intermediate that never reproduces is one a reader
        # diffing two builds would reasonably distrust.
        all_statuses = sorted({a["status"] for a in rows})
        timelines.append({
            "species_id": sp["id"],
            "scientific_name": sp["scientific_name"],
            "common_name": sp["common_name"],
            "scope_timelines": scope_timelines,
            "summary": {
                "scopes_tracked": list(scope_timelines.keys()),
                "first_assessment_year": min(all_years) if all_years else None,
                "latest_assessment_year": max(all_years) if all_years else None,
                "total_assessments": len(rows),
                "all_statuses_recorded": all_statuses,
            },
        })

    # overall summary (mirrors analyze_overall_trends)
    current_dist = defaultdict(int)
    trend_counts = {"improving": 0, "worsening": 0, "stable": 0}
    most_assessed = []
    earliest = min((t["summary"]["first_assessment_year"] for t in timelines), default=None)
    latest = max((t["summary"]["latest_assessment_year"] for t in timelines), default=None)
    for t in timelines:
        for scope, st in t["scope_timelines"].items():
            current_dist[st["current_status"]] += 1
            asmts = st["assessments"]
            if asmts:
                fs = STATUS_SEVERITY.get(asmts[0]["status"], 0)
                ls = STATUS_SEVERITY.get(asmts[-1]["status"], 0)
                if ls > fs:
                    trend_counts["worsening"] += 1
                elif ls < fs:
                    trend_counts["improving"] += 1
                else:
                    trend_counts["stable"] += 1
        most_assessed.append({
            "species": t["common_name"],
            "scientific_name": t["scientific_name"],
            "total_assessments": t["summary"]["total_assessments"],
            "scopes": t["summary"]["scopes_tracked"],
        })
    most_assessed.sort(key=lambda x: -x["total_assessments"])

    return {
        "generated_date": _run_date(),
        "summary": {
            "total_species_analyzed": len(timelines),
            "current_status_distribution": dict(current_dist),
            "trend_analysis": trend_counts,
            "most_assessed_species": most_assessed[:10],
            "assessment_year_range": {"earliest": earliest, "latest": latest},
        },
        "species_timelines": timelines,
    }


def main():
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    print(f"timeline: {data['summary']['total_species_analyzed']} species -> {OUT}")


if __name__ == "__main__":
    main()
