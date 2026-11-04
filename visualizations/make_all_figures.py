#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""make_all_figures — regenerate every manuscript figure from the sovereign DB.

Pipeline per run:
  1. Regenerate the 4 intermediate JSONs from `arctic` via the psycopg2
     generators in data_processing/ (cites_effectiveness, iucn_timeline,
     iwt_seizures, wild_origin_trade).
  2. Run the 7 figure scripts (figs 1-5, 7, 8) against those intermediates.
  3. Write per-figure numeric Source-Data CSVs (visualizations/source_data/).

--check mode: does all of the above into a scratch location and diffs the
Source-Data CSVs against the committed frozen ones. Byte equality = the whole
chain (DB → intermediate → figure numbers) is deterministic and reproducible.
Divergences vs the ORIGINAL published figures (the 2025-09/2025-11 supabase
runs) are computed against provenance/frozen_intermediates/ and written to
provenance/divergence_report.md — those are DOCUMENTED (figs 7/8 truncation
defects, H2 is_latest repair, catch vintage), not silently absorbed.

Figs 6 (climate correlation) and 9 are out of scope: no scripted pipeline
exists; they are supplied by the authors (see provenance/PROVENANCE.md).
"""
import argparse
import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
import os as _os
SCHEMA = _os.environ.get("ARCTIC_SCHEMA", "arctic_v2")

VIZ = Path(__file__).parent
ROOT = VIZ.parent
# The interpreter the steps run under: $PY if set (the Dockerfile sets it),
# else the project .venv, else the interpreter running this script.
PY = (Path(_os.environ["PY"]) if _os.environ.get("PY")
      else ROOT / ".venv/bin/python" if (ROOT / ".venv/bin/python").exists()
      else Path(sys.executable))
DP = VIZ / "data_processing"
SCRIPTS = VIZ / "scripts"
SOURCE_DATA = VIZ / "source_data"
PROV = VIZ / "provenance"

sys.path.insert(0, str(DP))
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(VIZ))

GENERATORS = [
    DP / "export_cites_effectiveness_pg.py",
    DP / "generate_iucn_timeline_pg.py",
    DP / "analyze_iwt_seizures_pg.py",
    DP / "analyze_wild_origin_trade_pg.py",
]

FIGURE_SCRIPTS = [
    ("figure1", "figure1_publication.py"),
    ("figure2", "figure2_trade_enforcement.py"),
    ("figure3", "figure3_trade_partners.py"),
    ("figure4", "figure4_conservation_trends.py"),
    ("figure5", "figure5_status_heatmap.py"),
    ("figure7", "figure7_iwt_seizures.py"),
    ("figure8", "figure8_wild_origin_trade.py"),
]


def run(cmd, **kw):
    r = subprocess.run([str(PY), *[str(c) for c in cmd]], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"FAILED: {cmd}")
    return r


def regenerate_intermediates():
    for g in GENERATORS:
        print(f"== {g.name}")
        run([g])


def run_figure_scripts():
    for name, script in FIGURE_SCRIPTS:
        print(f"== {name} ({script})")
        run([SCRIPTS / script])


def write_source_data(outdir: Path):
    # Hoisted: figure 2's panels (b) and (c) query the records too, and they
    # are written before figure 3's block where this used to be imported.
    from pg_common import query
    """Flatten each figure's displayed numbers to CSV."""
    outdir.mkdir(parents=True, exist_ok=True)

    # figs 1/2: per-species fields the scripts consume
    d = json.load(open(ROOT / "data/raw/1_DATA_cites_effectiveness.json"))
    rows = sorted(d["species_analyses"], key=lambda s: s["scientific_name"])
    with open(outdir / "figure1_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scientific_name", "common_name", "iucn_status", "cites_appendix",
                    "trade_records_count", "wild_origin_count",
                    "most_recorded_trade_use", "trade_trend"])
        for sp in rows:
            w.writerow([sp["scientific_name"], sp.get("common_name"), sp.get("iucn_status"),
                        sp.get("cites_appendix"), sp.get("trade_records_count"),
                        sp.get("wild_origin_count"), sp.get("most_recorded_trade_use"),
                        sp.get("trade_trend")])
    # Figure 2 was a byte copy of figure 1's table. Both scripts read the same
    # intermediate, but Source Data must carry the numbers a figure DISPLAYS, and
    # figure 2 displays three panel aggregates that the per-species table never
    # shows. A reader checking the appendix totals against figure1's CSV would
    # find them absent and conclude the figure was unsupported.
    with open(outdir / "figure2_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["panel", "category", "value_label", "trade_records"])
        top10 = sorted(rows, key=lambda s: -(s.get("trade_records_count") or 0))[:10]
        for sp in top10:
            w.writerow(["a_top10_species", sp["scientific_name"],
                        sp.get("common_name"), sp.get("trade_records_count")])
        # Panels (b) and (c) are RECORD-LEVEL and are counted off the records,
        # not off the per-species table. The species table carries one CURRENT
        # appendix and one MODAL purpose per species, and attributing a
        # species' whole record total to those two buckets answers a different
        # question from the one the panel titles ask. Measured 7 October 2026:
        # it put "Commercial" at 405,381 where the corpus holds 329,770, the
        # 67% the paper reports in 4.5, and it moved about 4,000 records
        # between Appendix I and II against the shares C04 to C06 verify.
        appendix, purpose = defaultdict(int), defaultdict(int)
        for r in query(f"SELECT appendix, purpose FROM {SCHEMA}.cites_trade_records"):
            appendix[r["appendix"] or "N"] += 1
            purpose[r["purpose"] or ""] += 1
        for panel, totals in (("b_by_appendix", appendix), ("c_by_purpose", purpose)):
            for cat, n in sorted(totals.items(), key=lambda x: -x[1]):
                w.writerow([panel, cat or "(blank)", cat or "(blank)", n])

    # fig3: top-10 non-arctic importers + top-5 arctic partners
    ARCTIC = {"CA", "US", "RU", "NO", "IS", "DK", "SE", "FI", "GL"}
    pairs = query(f"""SELECT importer, exporter, count(*) n FROM {SCHEMA}.cites_trade_records
                     WHERE year <= 2024 AND importer IS NOT NULL AND importer <> ''
                       AND exporter IS NOT NULL AND exporter <> ''
                     GROUP BY importer, exporter""")
    totals = defaultdict(int)
    partners = defaultdict(lambda: defaultdict(int))
    for r in pairs:
        totals[r["importer"]] += r["n"]
        if r["exporter"] in ARCTIC:
            partners[r["importer"]][r["exporter"]] += r["n"]
    top10 = sorted(((c, n) for c, n in totals.items() if c not in ARCTIC), key=lambda x: -x[1])[:10]
    with open(outdir / "figure3_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["importer", "total_import_records", "partner_rank", "arctic_partner", "records"])
        for c, n in top10:
            for rank, (p, pn) in enumerate(sorted(partners[c].items(), key=lambda x: -x[1])[:5], 1):
                w.writerow([c, n, rank, p, pn])

    # figs 4/5: timeline per-species per-scope current status + changes
    t_json = json.load(open(ROOT / "data/processed/iucn_historic_timeline.json"))
    with open(outdir / "figure4_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scientific_name", "scope", "first_year", "latest_year",
                    "total_assessments", "status_changes", "current_status"])
        for sp in sorted(t_json["species_timelines"], key=lambda s: s["scientific_name"]):
            for scope, st in sorted(sp["scope_timelines"].items()):
                w.writerow([sp["scientific_name"], scope, st["first_year"], st["latest_year"],
                            st["total_assessments"], st["status_changes"], st["current_status"]])
    # Figure 5 was a byte copy of figure 4's table, and the two do not show the
    # same thing. Figure 4 summarises per species per scope; figure 5 plots one
    # cell per species per year, merging scopes. A byte copy would give a
    # species its global summary row while the figure plots a regional cell for
    # it, so the Source Data would contradict its own figure and hide the scope.
    with open(outdir / "figure5_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scientific_name", "common_name", "year", "status",
                    "scope", "is_latest", "assessment_id"])
        for sp in sorted(t_json["species_timelines"], key=lambda s: s["scientific_name"]):
            for scope, st in sorted(sp["scope_timelines"].items()):
                for a in sorted(st.get("assessments", []), key=lambda x: x["year"]):
                    w.writerow([sp["scientific_name"], sp.get("common_name"),
                                a["year"], a["status"], scope,
                                a.get("is_latest"), a.get("assessment_id")])

    # fig7
    i = json.load(open(ROOT / "data/exports/iwt_seizures_analysis.json"))
    with open(outdir / "figure7_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "scientific_name", "total_quantity", "seizure_count",
                    "iucn_status", "cites_appendix"])
        for rank, s in enumerate(i["top_10_species"], 1):
            w.writerow([rank, s["scientific_name"], s["total_quantity"], s["seizure_count"],
                        s["iucn_status"], s["cites_appendix"]])

    # Manuscript Figures 3 and 10, which had no Source Data at all until
    # 6 October 2026. The Data Availability statement declared that as a gap in
    # the deposit; both are derivable from the two files this function already
    # reads, so it was twenty lines rather than a missing measurement. The
    # identifiers are letters because the pipeline's numbering and the
    # manuscript's already disagree, and two more numbers would deepen that.
    # The generator asserts every number those two captions publish before it
    # writes anything, so it fails rather than shipping a disagreement.
    import make_fig3_fig10_source_data as fig3_fig10
    fig3_fig10.self_test()
    fig3_fig10.write(outdir)

    # Manuscript Figure 5, CITES reservations by state, which the co-author added
    # on 18 October 2026. Every cell it draws is in the deposited Species+ event
    # history; the generator asserts all twenty before it writes.
    import make_figC_reservations_source_data as figC
    table = figC.rows()
    figC.self_test(table)
    with open(outdir / "figureC_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state_column", "cites_party", "scientific_name", "common_name",
                    "appendix", "coverage", "species_plus_note"])
        w.writerows(table)

    # fig8
    w8 = json.load(open(ROOT / "data/exports/wild_origin_trade_analysis.json"))
    with open(outdir / "figure8_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "scientific_name", "total_quantity", "record_count",
                    "iucn_status", "cites_appendix"])
        for rank, s in enumerate(w8["top_15_species"], 1):
            w.writerow([rank, s["scientific_name"], s["total_quantity"], s["record_count"],
                        s["iucn_status"], s["cites_appendix"]])


def _reference_tables():
    """name -> bytes of the Source Data each regenerated file is compared with.

    In the maintainers' tree that is visualizations/source_data/. In the public
    release it is the Zenodo snapshot unpacked into deposit/: deposit/rebuilt/
    for the files whose category column rebuild_iucn.py has restored, and
    source_data.zip for the rest. A file whose only reference still carries the
    withheld marker cannot be compared and is reported as not compared.
    """
    import zipfile
    refs, withheld = {}, []
    if SOURCE_DATA.is_dir():
        for f in SOURCE_DATA.glob("figure*_source_data.csv"):
            refs[f.name] = f.read_bytes()
    rebuilt = ROOT / "deposit" / "rebuilt"
    zpath = ROOT / "deposit" / "source_data.zip"
    if zpath.exists():
        with zipfile.ZipFile(zpath) as zf:
            for member in zf.namelist():
                name = Path(member).name
                if not (name.startswith("figure") and name.endswith("_source_data.csv")):
                    continue
                if name in refs:
                    continue
                if (rebuilt / name).exists():
                    refs[name] = (rebuilt / name).read_bytes()
                    continue
                data = zf.read(member)
                if "withheld".encode() in data:
                    withheld.append(name)
                else:
                    refs[name] = data
    return refs, withheld


def check():
    """Regenerate into scratch and compare the Source Data byte for byte."""
    import tempfile
    refs, withheld = _reference_tables()
    regenerate_intermediates()
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td)
        write_source_data(scratch)
        ok, compared = True, 0
        for name in sorted(refs):
            new = scratch / name
            if not new.exists():
                print(f"  FAIL {name}: not regenerated")
                ok = False
                continue
            compared += 1
            if refs[name] != new.read_bytes():
                print(f"  FAIL {name}: source data CHANGED")
                ok = False
            else:
                print(f"  PASS {name}")
        for name in sorted(withheld):
            print(f"  NOT COMPARED {name}: its category column is withheld; "
                  f"run deposit/rebuild_iucn.py first")
    if compared == 0:
        print("Source-data equivalence: NOTHING COMPARED - unpack the Zenodo "
              "snapshot into deposit/ first (see README)")
        sys.exit(3)
    verdict = "GREEN" if ok and not withheld else "FAIL" if not ok else "PARTIAL"
    print(f"Source-data equivalence: {verdict} ({compared} compared, "
          f"{len(withheld)} not compared)")
    sys.exit(0 if verdict == "GREEN" else 1)


def _require_working_driver() -> None:
    """Fail with the actual problem rather than a low-level loader error.

    A python3 outside the project's virtual environment may carry a psycopg2
    linked against a PostgreSQL client library that is not installed, and the
    resulting ImportError names a missing shared library. The real problem is
    the interpreter, and the message should say so.
    """
    try:
        import psycopg2  # noqa: F401
    except ImportError as exc:
        import sys
        from pathlib import Path as _P
        venv = _P(__file__).resolve().parent.parent / ".venv" / "bin" / "python"
        hint = f"\n\nRun this with the project interpreter instead:\n  {venv} {' '.join(sys.argv)}" if venv.exists() else ""
        raise SystemExit(
            f"psycopg2 will not import under {sys.executable}: {exc}{hint}"
        ) from exc


def stamp_provenance():
    """Record which commit produced these figures, from the run that produced them.

    figure_provenance.json is hand-maintained, which is why it goes stale by
    default rather than by accident. On 2026-08-12 it was 109 commits behind and
    was found by someone reading it. On 2026-08-15 V-23 caught it again twelve
    hours after being written, because two commits had changed the pipeline since
    the last stamp.

    A record that has to be updated by remembering will eventually not be. So the
    run that builds the figures writes it: the commit named here is, by
    construction, the code that produced the artefacts on disk beside it.

    V-23 stays as the backstop for the case this cannot cover — figures built
    from a dirty tree, or from a checkout whose HEAD moved afterwards.
    """
    import json
    import subprocess
    from datetime import date

    prov = PROV / "figure_provenance.json"
    if not prov.exists():
        print("  (no provenance record to stamp)")
        return
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                              capture_output=True, text=True, timeout=30)
        dirty = subprocess.run(["git", "status", "--porcelain",
                                "visualizations/scripts",
                                "visualizations/data_processing"],
                               cwd=str(ROOT), capture_output=True, text=True, timeout=30)
    except Exception as exc:  # noqa: BLE001
        print(f"  (could not read git to stamp provenance: {exc})")
        return
    if head.returncode != 0:
        print("  (not a git checkout; provenance commit left as it was)")
        return

    d = json.loads(prov.read_text())
    was = d.get("commit", "")
    d["commit"] = head.stdout.strip()
    d["generated"] = date.today().isoformat()

    # The commit alone cannot be right. Figure-code changes are committed AFTER
    # the figures are built, so a stamp taken at build time names the parent of
    # the commit that contains the change, and a check comparing them fires
    # every single time. That is what happened on 2026-08-15: the auto-stamp was
    # added to stop V-23 going stale and made it fire on every run instead.
    #
    # A digest of the pipeline source has no such ordering problem. It describes
    # what the code WAS when the figures were built, which is the question, and
    # it is exact regardless of when anything is committed.
    import hashlib
    h = hashlib.sha256()
    for f in sorted(list((VIZ / "scripts").glob("*.py"))
                    + list((VIZ / "data_processing").glob("*.py"))):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    d["pipeline_source_sha256"] = h.hexdigest()
    # An uncommitted change to the pipeline means the recorded commit does not
    # describe what just ran. Say so in the record rather than implying it does.
    if dirty.stdout.strip():
        d["commit_caveat"] = ("Figure code had uncommitted changes when these "
                              "figures were built, so the commit above names the "
                              "nearest ancestor rather than the exact source.")
        print("  provenance stamped, with a caveat: figure code is uncommitted")
    else:
        d.pop("commit_caveat", None)
        if was[:12] != d["commit"][:12]:
            print(f"  provenance stamped: {was[:12] or 'none'} -> {d['commit'][:12]}")
    prov.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def main():
    _require_working_driver()
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify regeneration reproduces committed Source-Data (gate mode)")
    ap.add_argument("--skip-figures", action="store_true",
                    help="only regenerate intermediates + source data")
    args = ap.parse_args()
    if args.check:
        check()
        return
    regenerate_intermediates()
    if not args.skip_figures:
        run_figure_scripts()
    write_source_data(SOURCE_DATA)
    stamp_provenance()
    print("\nAll figures regenerated from the sovereign DB. Source-Data in", SOURCE_DATA)


if __name__ == "__main__":
    main()
