#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Build the Zenodo deposit package: exports, data dictionary, checksummed manifest.

WHY THIS EXISTS
---------------
The manuscript states that the code and the underlying dataset are deposited
as a tagged Zenodo release with a DOI. This script builds that package. It
produces everything that does not require a human account:

  - one CSV per table, from arctic_v2
  - a JSON data dictionary: every table, column, type, and provenance class
  - a SHA-256 manifest over every exported file
  - a README stating vintage, scope, licences and known limitations

What it deliberately does NOT do: mint a DOI, upload, or tag a release. Those
are outward-facing acts that belong to the authors, and inventing a DOI is the
exact failure this script exists to prevent.

After running this, the remaining steps are: review the package, upload to
Zenodo, mint the DOI, and cite it in the manuscript.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/build_deposit.py --schema arctic_v2
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT = ROOT / "deposit"

# Tables excluded from the deposit, with the reason stated in the README rather
# than omitted silently. IUCN's terms prohibit redistribution; NAMMCO grants
# no licence for it (checked at nammco.no/catch-database/, 7 Oct 2026).
EXCLUDED = {
    "iucn_assessments": (
        "IUCN Red List terms do not permit redistribution. The assessment "
        "identifier, publication year and scope of every withheld row are "
        "provided under identifiers/, so any reader with a free Red List "
        "account can retrieve each assessment by its identifier and reconstruct "
        "or check the table at source. The extraction is not shipped as a "
        "one-command tool inside this deposit; it lives in the code repository, "
        "where deposit/rebuild_iucn.py queries the Red List API directly and "
        "deposit/REBUILD-IUCN.md documents its use. Note that ingest/iucn_load.py is a loader, "
        "not an extractor: it replays a snapshot we may not redistribute, and "
        "is of no use here."
    ),
    "catch_records": (
        "NAMMCO publishes no licence or terms for the Catch Database, so no "
        "redistribution is granted. The catch_total column is the source's CATCH TOTAL for "
        "one row, in animals; the source lists national totals beside its area "
        "rows, so a sum over rows counts those animals twice. Record identifiers are "
        "provided under identifiers/. There is no extraction script: these "
        "catch figures were taken from the publicly browsable NAMMCO catch "
        "database by a scraper that was lost in an October 2025 repository "
        "cleanup. The values remain checkable at source using the identifiers "
        "and the access date; our route to them is not reproducible, and we "
        "state that rather than implying otherwise."
    ),
}


# The Zenodo record this package is published under, written by the authors'
# release step once the DOI has been reserved (that step is not part of the
# public release). Absent until then, and the README says so.
ZENODO = OUT / "zenodo.json"
NOT_UPLOADED = ("**This package has NOT been uploaded to Zenodo and has no DOI.** It is the\n"
                "artifact a DOI would point at. Minting the DOI is an author action.")


# Follows the Zenodo note in the README. Kept as a constant so the full build
# and the --zenodo paragraph rewrite emit the same text.
REPO_COPY_NOTE = ("\nThe copy in the code repository is maintained there and may differ from the\n"
                  "Zenodo 1.0 snapshot, which is the version of record.")


def zenodo_note() -> str:
    if not ZENODO.exists():
        return NOT_UPLOADED
    z = json.loads(ZENODO.read_text())
    note = (f"**This package is the Zenodo record https://doi.org/{z['version_doi']}** "
            f"(snapshot v{z['snapshot']}).")
    if z.get("concept_doi"):
        note += (f" The concept DOI https://doi.org/{z['concept_doi']} always resolves "
                 f"to the latest version.")
    return note


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()



def _source_data_index(files) -> str:
    """Map every Source Data file to the manuscript figure it belongs to.

    The pipeline's identifiers and the manuscript's figure numbers are two
    different numberings over the same figures, and figure_provenance.json is
    the record of which is which. Reading one as the other inverts the answer,
    so this is generated from that record rather than written by hand, and it
    states the two awkward cases out loud: the pipeline file that is bound to
    no manuscript figure, and the manuscript figures that have no pipeline.
    """
    import json as _json

    prov_path = ROOT / "visualizations/provenance/figure_provenance.json"
    prov = _json.loads(prov_path.read_text())
    fmap = prov.get("figure_map", [])
    by_id = {e["figure_id"]: e for e in fmap if e.get("figure_id")}
    present = {f.name.split("_")[0]: f.name for f in files}

    lines = [
        "# Source Data index",
        "",
        "NCOMMS-25-97285 · Trading for Conservation",
        "",
        "**The filenames are the pipeline's figure identifiers, not the "
        "manuscript's figure numbers.** They are two numberings over the same "
        "work and they do not agree: `figure3_source_data.csv` is the Source "
        "Data for manuscript **Figure 9**. Use this table, not the filename.",
        "",
        "| Manuscript figure | Source Data file | Caption |",
        "|:--|:--|:--|",
    ]
    for entry in sorted(fmap, key=lambda e: e.get("manuscript_number") or 99):
        fid = entry.get("figure_id")
        num = entry.get("manuscript_number")
        stub = (entry.get("manuscript_caption_stub") or "").replace("|", "/")
        if fid and fid in present:
            lines.append(f"| Figure {num} | `{present[fid]}` | {stub} |")
        else:
            # "no scripted pipeline" is not true of every unbound figure. Figures
            # 12 and 13 are DRAWN by deposited scripts and still have no Source Data,
            # because they plot no computed values - a finished state, not a gap.
            # The record says which it is; this reads it rather than printing
            # one sentence over both.
            why = ("none — plots no computed values"
                   if "plots no computed values" in (entry.get("binding_evidence") or "")
                   else "none — no scripted pipeline")
            lines.append(f"| Figure {num} | {why} | {stub} |")

    orphans = sorted(set(present) - set(by_id))
    lines += ["", "## Files bound to no manuscript figure", ""]
    if orphans:
        for o in orphans:
            lines.append(
                f"- `{present[o]}` — the `{o}` pipeline produces this, and no "
                f"manuscript figure is bound to it. It is included because the "
                f"pipeline emits it and removing it would make the archive "
                f"disagree with the byte-for-byte verification; it is not the "
                f"Source Data for manuscript Figure {o.replace('figure', '')}.")
    else:
        lines.append("- none: every file here is bound to a manuscript figure.")

    lines += [
        "",
        "## How these were produced",
        "",
        "Every value is regenerated from the deposited corpus by "
        "`visualizations/make_all_figures.py` and compared byte for byte "
        "against these files on each verification run. The bindings above come "
        "from `visualizations/provenance/figure_provenance.json`, which records "
        "the evidence for each one and who confirmed it.",
        "",
    ]
    return "\n".join(lines)


def _refuse_unless_withholding_holds(sd_zip):
    """Run the withholding verifier, and refuse if it fails.

    This writer rebuilds every member of the archive from
    visualizations/source_data/ - the PRE-withholding files. Run on its own, it
    would put the Red List categories (436 of them) back into the deposited zip
    and drop the assessment identifiers that stand in their place. A digest
    check cannot see that, because it only asks whether the digests match;
    verify_iucn_withheld.py catches all 436 in one run.

    So the writer runs it itself. A build that un-withholds fails at the
    build rather than at whoever reads the package next, and the archive that
    was there is put back.

    NOTE, and it is the whole route: visualizations/source_data/ holds the
    PRE-withholding files, because that is what the figure pipeline emits. So
    this writer ABORTING is the normal outcome of running it on its own, and
    the correct sequence is to run it and then run
    ingest/withhold_iucn_categories.py, which rewrites the deposited copies
    with the category replaced by its assessment identifier. A full
    build_deposit.py run does both.
    """
    import subprocess
    gate = ROOT / "deposit" / "verification" / "verify_iucn_withheld.py"
    if not gate.is_file():
        sys.exit(f"  ABORT: {gate} is not here, so this build cannot prove it "
                 f"did not republish a withheld category")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, str(gate)], cwd=ROOT,
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        # PUT THE OLD ONE BACK. The first version of this guard ran after the
        # writer had already overwritten the archive, so it aborted and left
        # the leaking file on disk - a check that names the damage and leaves
        # it there. The caller keeps a copy for exactly this.
        restored = ""
        keep = Path(str(sd_zip) + ".before")
        if keep.is_file():
            shutil.move(str(keep), str(sd_zip))
            restored = (" The previous archive has been put back, so the "
                        "deposit on disk is unchanged.")
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        sys.exit("  ABORT: the archive this build wrote carries withheld Red "
                 "List categories." + restored
                 + " This is the expected outcome of running the Source Data "
                   "writer alone: run ingest/withhold_iucn_categories.py after "
                   "it, which replaces each category with its assessment "
                   "identifier.\n    " + "\n    ".join(tail))
    Path(str(sd_zip) + ".before").unlink(missing_ok=True)
    print("  withholding verified: no Red List category in the deposit")


def _keep_signed_identifiers(sd_zip, before):
    """A member whose data did not change keeps the bytes it was signed with.

    Measured 18 October 2026, the first time the writer and the withholding
    transform ran in sequence since 6 October: the transform fills each row's
    assessment_id with the species' latest GLOBAL assessment, while the
    committed figure1, figure4, figure7 and figure8 files were computed on the
    is_latest assessment of any scope. Re-run, it re-pointed rows to an
    assessment other than the one whose category the file holds - in figure4 a
    row whose own scope column says Europe was given a global identifier. The
    signed archive carries the identifier of the assessment actually used.

    So, member by member: if every column other than assessment_id is identical
    to the signed archive, the signed member is kept byte for byte. A member
    whose data changed is taken as the transform wrote it, and its change is
    what the re-signing records.
    """
    import csv as _csv
    import io as _io
    import zipfile
    if not before.is_file():
        return
    with zipfile.ZipFile(before) as zb:
        old = {i.filename: zb.read(i.filename) for i in zb.infolist()}
    with zipfile.ZipFile(sd_zip) as zn:
        infos = zn.infolist()
        new = {i.filename: zn.read(i.filename) for i in infos}

    def body(raw):
        rows = list(_csv.DictReader(_io.StringIO(raw.decode("utf8"))))
        return [{k: v for k, v in r.items() if k != "assessment_id"} for r in rows]

    # "Data unchanged" has to include the column the archive withholds. Once
    # the category is replaced by a pointer, a member whose CATEGORY changed
    # reads identical to the signed one minus its identifiers, and this would
    # keep the identifiers of the assessment it no longer uses. For example,
    # when a figure moves from a species' 2023 European assessment to its 2018
    # global one, the row would keep the European assessment's identifier
    # beside a figure that draws the global category. So the pre-withholding
    # CSV is compared with the committed one; if it moved, the member is taken
    # as the transform wrote it.
    def source_moved(name):
        rel = f"visualizations/source_data/{Path(name).name}"
        r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT,
                           capture_output=True)
        if r.returncode != 0:
            return True
        return r.stdout != (ROOT / rel).read_bytes()

    import subprocess
    kept = []
    for name, raw in new.items():
        if (name.endswith(".csv") and name in old and old[name] != raw
                and body(old[name]) == body(raw) and not source_moved(name)):
            new[name] = old[name]
            kept.append(name)
    if not kept:
        return
    tmp = Path(str(sd_zip) + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for i in infos:
            z.writestr(i, new[i.filename])
    tmp.replace(sd_zip)
    for k in kept:
        print(f"  {k}: data unchanged, signed identifiers kept")


def build_source_data_zip():
    """Write deposit/source_data.zip from visualizations/source_data/.

    Lifted out of main() on 6 October 2026 so it can be run without a
    database. The reason is concrete: Figures 3 and 10 got a generator and
    Source Data that day (D265), the two new CSVs landed in
    visualizations/source_data/, and the only way to fold them into the
    package was a full build - which needs ARCTIC_DATABASE_URL and so could
    not happen offline. The package in the tree then carried seven figure
    files while nine existed, and the Data Availability statement pointed at
    it.

    One artefact, one writer: this is still the only code that writes the
    zip. The flag changes when it runs, not who writes it.
    """
    import zipfile
    sd_dir = ROOT / "visualizations" / "source_data"
    if sd_dir.exists():
        sd_zip = OUT / "source_data.zip"
        # Keep the archive that is there. The withholding guard below needs
        # something to put back when the build it just wrote would republish a
        # Red List category, and a guard with nothing to restore can only
        # report the damage.
        if sd_zip.is_file():
            shutil.copy2(sd_zip, str(sd_zip) + ".before")
        # A fixed timestamp keeps the archive byte-identical across rebuilds;
        # otherwise its digest changes every run and the manifest becomes noise.
        with zipfile.ZipFile(sd_zip, "w", zipfile.ZIP_DEFLATED) as z:
            files = sorted(f for f in sd_dir.glob("*.csv"))
            for f in files:
                info = zipfile.ZipInfo(f"Source Data/{f.name}", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, f.read_bytes())
            readme = (
                "Source Data for the figures of NCOMMS-25-97285.\n\n"
                "One labelled file per figure, in the zipped-folder form Nature\n"
                "Communications accepts as an alternative to a single workbook.\n\n"
                "Filenames use the pipeline's figure identifiers. The mapping to\n"
                "manuscript figure numbers is in the response letter and in\n"
                "visualizations/provenance/figure_provenance.json, because the two\n"
                "numberings are not the same and reading one as the other inverts\n"
                "the answer.\n\n"
                "Every value here is regenerated from the deposited corpus by\n"
                "visualizations/make_all_figures.py, and compared byte for byte\n"
                "against these files on every verification run.\n"
            )
            ri = zipfile.ZipInfo("Source Data/README.txt", date_time=(1980, 1, 1, 0, 0, 0))
            ri.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(ri, readme)

            # SOURCE_DATA_INDEX.md, which the Data Availability statement names.
            # Without it a reader of the deposit has no route from a filename
            # to a manuscript figure; and the filenames actively mislead,
            # because figure3_source_data.csv is manuscript Figure 9. Generated
            # from figure_provenance.json so it cannot drift from the bindings.
            index = _source_data_index(files)
            ii = zipfile.ZipInfo("Source Data/SOURCE_DATA_INDEX.md",
                                 date_time=(1980, 1, 1, 0, 0, 0))
            ii.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(ii, index)
        # 18 October 2026: the docstring of the guard below says "a full
        # build_deposit.py run does both" - writes the archive AND withholds the
        # categories - and nothing here did the second. So every run of this
        # writer aborted and put the old archive back, and the only route to a
        # new figure's Source Data was to bypass the guard. The transform runs
        # here, on the archive just written and before the guard reads it, and a
        # failure of either still restores the previous archive.
        import subprocess
        w = subprocess.run(
            [sys.executable, str(ROOT / "ingest" / "withhold_iucn_categories.py")],
            cwd=ROOT, capture_output=True, text=True,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if w.returncode != 0:
            keep = Path(str(sd_zip) + ".before")
            if keep.is_file():
                shutil.move(str(keep), str(sd_zip))
            sys.exit("  ABORT: withholding the Red List categories in the new "
                     "archive failed, and the previous archive has been put "
                     "back:\n    " + "\n    ".join(
                         (w.stdout + w.stderr).strip().splitlines()[-6:]))
        _keep_signed_identifiers(sd_zip, Path(str(sd_zip) + ".before"))
        _refuse_unless_withholding_holds(sd_zip)
        print(f"  source_data.zip: {len(files)} figure file(s), a README and "
              f"SOURCE_DATA_INDEX.md")
    else:
        print("  WARNING: no visualizations/source_data; Source Data package not built")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--schema", default="arctic_v2")
    ap.add_argument("--refresh-digests", action="store_true",
                    help="recompute the manifest digest and size for files "
                         "already listed in it, without a database. Adds and "
                         "removes nothing.")
    ap.add_argument("--register-static", action="store_true",
                    help="register manifest entries for the package's static "
                         "artefacts (documentation, verifier source) without a "
                         "database. Refuses anything that could carry data.")
    ap.add_argument("--source-data-only", action="store_true",
                    help="rebuild deposit/source_data.zip and its one manifest "
                         "entry, without a database. Everything else in the "
                         "deposit is left exactly as it is.")
    ap.add_argument("--zenodo", action="store_true",
                    help="write the Zenodo note from deposit/zenodo.json into the "
                         "built README and register both files in the manifest, "
                         "without a database. Nothing else changes.")
    args = ap.parse_args()

    if args.zenodo:
        # The DOI arrives after the package is built, and a full rebuild needs
        # the database. This touches the one README paragraph the full build
        # would write from the same function, so the two cannot disagree.
        if not ZENODO.exists():
            print("REFUSING: no deposit/zenodo.json (written by the authors' release "
                  "step, which is not part of the public release)",
                  file=sys.stderr)
            return 1
        readme = OUT / "README.md"
        text = readme.read_text()
        new, n = re.subn(r"((?:Built|The snapshot described here was built) [^\n]*\n\n)(.*?)(\n\n## Contents)",
                         lambda m: m.group(1) + zenodo_note() + REPO_COPY_NOTE + m.group(3),
                         text, count=1, flags=re.S)
        if n != 1:
            print("REFUSING: the README has no paragraph between 'Built' and "
                  "'## Contents' to replace", file=sys.stderr)
            return 1
        if "zenodo.json" not in new:
            new = new.replace("- `README.md` : this file",
                              "- `README.md` : this file\n- `zenodo.json` : the Zenodo "
                              "DOIs and snapshot version this package is published under", 1)
        readme.write_text(new)
        man_path = OUT / "MANIFEST.sha256.json"
        man = json.loads(man_path.read_text())
        for f in (readme, ZENODO):
            man[f.name] = {"bytes": f.stat().st_size, "sha256": sha256_file(f)}
            print(f"  manifest: {f.name} {man[f.name]['sha256'][:12]}")
        man_path.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
        print(f"  README: {zenodo_note()}")
        return 0

    if args.refresh_digests:
        # Recompute the recorded digest and size for files ALREADY listed in the
        # manifest, without a database and without touching any content.
        #
        # Why this exists, 6 October 2026: three deposited files were edited that
        # day - results_traceability.csv, results_traceability.md and
        # verification/verify_claims_offline.py, when claims C66 to C79 were
        # added - and the manifest went on recording their previous digests for
        # hours. Nothing noticed, because nothing checked: V-14 needs a database,
        # and verify_deposit_accounted compares the FILE LIST rather than the
        # digests, so a stale digest passed every gate in the set.
        #
        # This adds no entry and removes none - that is the full build's job, and
        # a flag that could add entries would let a file slip into the package
        # without the build that is supposed to put it there. It prints every
        # change, because a digest refresh that says nothing is indistinguishable
        # from laundering an edit nobody meant to make.
        man_path = OUT / "MANIFEST.sha256.json"
        if not man_path.exists():
            print("UNBUILDABLE: no MANIFEST.sha256.json to refresh.", file=sys.stderr)
            return 3
        man = json.loads(man_path.read_text())
        changed, missing = [], []
        for name, rec in sorted(man.items()):
            f = OUT / name
            if not f.exists():
                missing.append(name)
                continue
            digest, size = sha256_file(f), f.stat().st_size
            if digest != rec.get("sha256") or size != rec.get("bytes"):
                changed.append((name, rec.get("sha256", "")[:12], digest[:12]))
                man[name] = {"bytes": size, "sha256": digest}
        if missing:
            print(f"REFUSING: {len(missing)} manifest entry(ies) have no file on "
                  f"disk, so this is not a digest refresh but a missing build:",
                  file=sys.stderr)
            for n in missing:
                print(f"  {n}", file=sys.stderr)
            return 1
        if not changed:
            print("  manifest: every recorded digest already matches disk")
            return 0
        man_path.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
        print(f"  manifest: {len(changed)} digest(s) refreshed")
        for n, was, now in changed:
            print(f"    {n}: {was} -> {now}")
        return 0

    if args.register_static:
        # Register manifest entries for the package's STATIC artefacts: its
        # documentation and its verifier source. Nothing database-derived can
        # pass through here - the allowlist is by location and extension, so a
        # csv, a zip or anything under tables/ is refused by construction.
        #
        # This is the same bargain --source-data-only strikes: the build still
        # decides what the package contains, and the flag only lets the part of
        # the build that needs no database do its job. The earlier objection
        # stands and is what shapes this - "a flag that could add entries would
        # let a file slip into the package without the build that is supposed to
        # put it there" - so a flag that can add ONLY files the full build would
        # pick up by its own walk, and only ones that cannot carry data, does
        # not open that door.
        man_path = OUT / "MANIFEST.sha256.json"
        if not man_path.exists():
            print("UNBUILDABLE: no MANIFEST.sha256.json to register into.",
                  file=sys.stderr)
            return 3
        man = json.loads(man_path.read_text())
        added, refused = [], []
        for f in sorted(OUT.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(OUT).as_posix()
            if rel in man or rel == "MANIFEST.sha256.json":
                continue
            if rel.startswith("rebuilt/") or "__pycache__" in rel:
                continue
            # A journal figure counts as static when a top-level builder in the
            # package draws it (build_figureN_journal.py writes figures/figureN-*):
            # it is drawn from files already in the manifest, so it carries
            # nothing the package does not. Added 22 October 2026 for Figure 11.
            fig = re.match(r"figures/figure(\d+)-[^/]+-journal\.(svg|png)$", rel)
            static = (rel.endswith((".md", ".digest", ".txt"))
                      or (rel.startswith("verification/") and rel.endswith(".py"))
                      or ("/" not in rel and rel.endswith(".py"))
                      or bool(fig and (OUT / f"build_figure{fig.group(1)}_journal.py").exists()))
            if static:
                man[rel] = {"bytes": f.stat().st_size, "sha256": sha256_file(f)}
                added.append(rel)
            else:
                refused.append(rel)
        if refused:
            print(f"REFUSING: {len(refused)} unlisted file(s) are not static "
                  f"artefacts, so only the full build may add them:",
                  file=sys.stderr)
            for r in refused:
                print(f"  {r}", file=sys.stderr)
            return 1
        if not added:
            print("  manifest: every static artefact is already registered")
            return 0
        man_path.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
        print(f"  manifest: {len(added)} static artefact(s) registered")
        for a in added:
            print(f"    + {a}")
        return 0

    if args.source_data_only:
        build_source_data_zip()
        # The zip's digest lives in MANIFEST.sha256.json, so rebuilding the zip
        # without updating it would leave the package self-inconsistent and the
        # freshness check would be right to fail. Exactly ONE entry is touched,
        # and it is the entry for the file this run just wrote - that is a
        # record of what happened, not a laundered hand edit.
        man_path = OUT / "MANIFEST.sha256.json"
        if not man_path.exists():
            print("UNBUILDABLE: no MANIFEST.sha256.json to update; run the full "
                  "build.", file=sys.stderr)
            return 3
        man = json.loads(man_path.read_text())
        if "source_data.zip" not in man:
            print("UNBUILDABLE: the manifest does not list source_data.zip, so "
                  "this flag does not know where to record it.", file=sys.stderr)
            return 3
        z = OUT / "source_data.zip"
        before = man["source_data.zip"]["sha256"]
        man["source_data.zip"] = {"bytes": z.stat().st_size,
                                  "sha256": sha256_file(z)}
        man_path.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
        print(f"  manifest: source_data.zip {before[:12]} -> "
              f"{man['source_data.zip']['sha256'][:12]}")
        print("  nothing else in the deposit was read or written.")
        return 0

    schema = validate_schema(args.schema)
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    OUT.mkdir(exist_ok=True)
    (OUT / "tables").mkdir(exist_ok=True)
    # The build time is provenance and belongs in the package. It is also the
    # only thing left that stops two builds of the same data from being byte
    # identical, now that every table is exported in a deterministic order.
    # DEPOSIT_BUILT_UTC lets a reviewer pin it to the stamp we published and
    # reproduce the deposit exactly, digest for digest, rather than reproduce it
    # "apart from two timestamps" and have to take the rest on trust.
    stamp = os.environ.get("DEPOSIT_BUILT_UTC") or \
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp):
        raise SystemExit(
            f"DEPOSIT_BUILT_UTC={stamp!r} is not an ISO-8601 UTC stamp like "
            f"2026-09-01T14:38:16Z. Refusing rather than writing a malformed "
            f"build time into the package's own provenance.")

    conn = psycopg2.connect(url, connect_timeout=60)
    dictionary, manifest = {}, {}
    try:
        with conn.cursor() as cur:
            cur.execute(
                """select table_name from information_schema.tables
                    where table_schema = %s and table_type = 'BASE TABLE'
                    order by table_name""",
                (schema,),
            )
            tables = [t for (t,) in cur.fetchall()]

            for table in tables:
                cur.execute(
                    """select column_name, data_type, is_nullable
                         from information_schema.columns
                        where table_schema = %s and table_name = %s
                        order by ordinal_position""",
                    (schema, table),
                )
                cols = cur.fetchall()
                cur.execute(f"select count(*) from {schema}.{table}")
                n = cur.fetchone()[0]

                entry = {
                    "rows": n,
                    "columns": [
                        {"name": c, "type": t, "nullable": nl == "YES"} for c, t, nl in cols
                    ],
                }
                if table in EXCLUDED:
                    entry["exported"] = False
                    entry["exclusion_reason"] = EXCLUDED[table]
                    dictionary[table] = entry
                    print(f"  skipped  {table:<28} {n:>7} rows (not redistributable)")
                    continue

                path = OUT / "tables" / f"{table}.csv"
                names = [c for c, _, _ in cols]
                # COPY, not csv.writer over a SELECT.
                #
                # Reading rows into Python turns a PostgreSQL text[] into a
                # Python list, and csv.writer then writes it as a Python repr:
                # ['CITES', 'Appendix II'] instead of {CITES,"Appendix II"}.
                # The file looks fine and cannot be loaded back into the schema
                # it came from. Two of the twenty-two tables were affected, and
                # nothing noticed because nobody had ever tried to reload the
                # deposit — which is the one thing a reader does with it.
                #
                # COPY formats every type the way PostgreSQL parses it, so the
                # round trip is a property of the mechanism rather than of our
                # remembering which columns are arrays.
                # ORDER BY, because without it this deposit does not rebuild.
                #
                # A bare SELECT returns heap order, which PostgreSQL is free to
                # change and does — after a vacuum, an update, or a parallel
                # scan. Measured on 2026-09-01: rebuilding produced
                # cites_trade_records.csv at exactly 178,963,039 bytes both
                # times and a different SHA-256, because the same 492,095 rows
                # came back in a different order. The manifest's digests are
                # this deposit's integrity claim, so a rebuild that changes
                # every digest without changing any datum makes the freshness
                # checks report drift that is not drift, and makes it impossible
                # for a reviewer rebuilding from schema.sql to arrive at the
                # checksums we published.
                #
                # V-16 already asserts that published VALUES survive row
                # permutation, which is the right defence for the numbers. This
                # is the defence for the files.
                #
                # Primary key where there is one, every column otherwise: both
                # are total orders, so both are deterministic. Ordering by all
                # columns is the fallback rather than the rule because it is the
                # slower of the two on a 179 MB table.
                cur.execute(
                    """select a.attname
                         from pg_index i
                         join pg_attribute a
                           on a.attrelid = i.indrelid
                          and a.attnum = any(i.indkey)
                        where i.indrelid = %s::regclass and i.indisprimary
                        order by array_position(i.indkey, a.attnum)""",
                    (f"{schema}.{table}",),
                )
                pk = [r[0] for r in cur.fetchall()]
                order = ", ".join(f'"{c}"' for c in (pk or names))
                with open(path, "w", newline="", encoding="utf-8") as fh:
                    cur.copy_expert(
                        f"copy (select {', '.join(names)} from {schema}.{table} "
                        f"order by {order}) "
                        f"to stdout with csv header", fh)

                entry["exported"] = True
                entry["file"] = f"tables/{table}.csv"
                dictionary[table] = entry
                digest = sha256_file(path)
                manifest[f"tables/{table}.csv"] = {
                    "sha256": digest,
                    "bytes": path.stat().st_size,
                    "rows": n,
                }
                print(f"  exported {table:<28} {n:>7} rows  {digest[:16]}...")

            # Provenance classes, which are the deposit's distinguishing feature.
            cur.execute(
                f"""select table_name, column_name from information_schema.columns
                     where table_schema = %s and column_name = 'provenance_class'""",
                (schema,),
            )
            classed = [t for (t, _) in cur.fetchall()]
            provenance = {}
            for table in classed:
                cur.execute(
                    f"select provenance_class, count(*) from {schema}.{table} group by 1"
                )
                provenance[table] = dict(cur.fetchall())
        # ------------------------------------------------------------------
        # Identifiers for the withheld tables.
        #
        # The README tells a reader that the deposit "provides record
        # identifiers" for the two tables that may not be redistributed. The live
        # site carries no reproducibility weight, so the identifier files must
        # travel in the deposit itself.
        #
        # They are generated here from the database, so they are part of the
        # package and part of the manifest rather than a copy of a copy.
        # ------------------------------------------------------------------
        identifier_manifest = {}
        ident = OUT / "identifiers"
        ident.mkdir(parents=True, exist_ok=True)
        IDENTIFIERS = [
            (
                "iucn_assessment_ids.csv",
                "iucn_assessments",
                "select assessment_id, year_published, scope_code "
                f"from {schema}.iucn_assessments order by assessment_id",
            ),
            (
                "catch_record_ids.csv",
                "catch_records",
                # Species is joined in rather than exported as an opaque id: a reader
                # locating these rows in the public NAMMCO database needs the
                # scientific name, not our surrogate key. source_artifact and
                # source_occurrence are what tie a row back to the scraped file.
                #
                # catch_total is deliberately NOT selected. It is the withheld
                # value, not a locator: this table is excluded because "NAMMCO
                # terms do not permit redistribution", and the README tells the
                # reader the values remain checkable at source. Emitting the
                # catch figures in the identifiers file redistributed exactly
                # what the withholding withholds. The columns below locate each
                # record in the public NAMMCO database; the reader reads the
                # value there, as the deposit says they must.
                "select s.scientific_name, c.year, c.area, "
                "c.source_artifact, c.source_occurrence "
                f"from {schema}.catch_records c join {schema}.species s "
                "on s.id = c.species_id "
                "order by s.scientific_name, c.year, c.area, c.source_occurrence",
            ),
        ]
        for filename, table, sql in IDENTIFIERS:
            dest = ident / filename
            with conn.cursor() as cur, open(dest, "w", newline="") as fh:
                cur.copy_expert(f"copy ({sql}) to stdout with csv header", fh)
            rows = sum(1 for _ in open(dest)) - 1
            identifier_manifest[f"identifiers/{filename}"] = {
                "sha256": sha256_file(dest), "bytes": dest.stat().st_size, "rows": rows,
            }
            print(f"  identifiers/{filename}: {rows} rows for withheld table {table}")
    finally:
        conn.close()

    (OUT / "data_dictionary.json").write_text(
        json.dumps(
            {
                "_generated_by": "ingest/build_deposit.py — do not edit; the next "
                                 "make deposit overwrites this file",
                "schema": schema,
                "built_utc": stamp,
                "tables": dictionary,
                "provenance_classes": provenance,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    # (manifest written below, after the verification scripts are copied)

    exported = sum(1 for e in dictionary.values() if e.get("exported"))
    total_rows = sum(e["rows"] for e in dictionary.values() if e.get("exported"))

    # The contents list is derived from what was actually written, not typed.
    # Typed, it listed four of the seven things in the package: verification/,
    # supplementary/ and the traceability table were all absent from it while
    # sitting in the directory it described.
    _descr = {
        "tables/": f"{exported} tables, {total_rows} rows, one CSV each",
        "identifiers/": "record identifiers for the two tables withheld for "
                        "licence reasons, so a reader can rebuild or check them at source",
        "supplementary/": "the supplementary tables derivable from the corpus, "
                          "regenerated on every build",
        "verification/": "the scripts that reproduce this paper's numbers from "
                         "the tables above",
        "data_dictionary.json": "every table and column with type and provenance class",
        "MANIFEST.sha256.json": "SHA-256 and byte size for every file in this package",
        "results_traceability.csv": "Supplementary Table 5: claim to Methods to "
                                    "dataset to figure to definition",
        "results_traceability.md": "the same table, readable",
        "schema.sql": "the database schema these tables load into, generated from the database of record",
        "source_data.zip": "Source Data, one labelled file per figure, in the zipped-folder form the journal accepts",
        "README.md": "this file",
        "zenodo.json": "the Zenodo DOIs and snapshot version this package is published under",
        # Added 2026-09-01. These five were in the package and not in this map,
        # so the contents list ended with a line reading "UNDESCRIBED, and this
        # is a defect" and naming them. The line worked: it is why they are
        # described now. But it had been printing since the pipeline record was
        # deposited, and pipeline.json and figures/ are the evidence for R1-06,
        # which makes them the worst five things to leave unexplained to a
        # reviewer who downloads the package to check that answer.
        "pipeline.json": "the seven-step evaluation pipeline as a record: each "
                         "step's stage, data source, tool, human gate and the "
                         "audit questions it answers, carrying the SHA-256 of "
                         "the Supplementary Table 4 it was derived from",
        "figures/": "the two stage diagrams drawn from pipeline.json, SVG and "
                    "PNG. verification/verify_pipeline_record.py re-renders "
                    "them and compares byte for byte, so a stale diagram fails "
                    "rather than misleads",
        "build_pipeline_diagram.py": "draws the two figures above from "
                                     "pipeline.json; byte-deterministic, which "
                                     "is what makes that comparison possible",
        "load_deposit.sh": "loads every table in tables/ into a database built "
                           "from schema.sql, retrying until no further table "
                           "loads, because foreign keys make alphabetical "
                           "order fail",
        "sources/": "under curated/, the ten source files the curated tables "
                    "are built from. Each deposited table is compared against "
                    "the file here it came from by "
                    "verification/verify_source_truth.py",
    }
    _present = []
    for name, why in _descr.items():
        path = OUT / name.rstrip("/")
        if path.exists():
            _present.append(f"- `{name}` : {why}")
    _unlisted = sorted(
        f.name for f in OUT.iterdir()
        if f.name not in _descr and f"{f.name}/" not in _descr
    )
    if _unlisted:
        # Silence must not satisfy this either: something in the package that
        # the contents list cannot describe is a defect, not a footnote.
        _present.append(
            f"- **UNDESCRIBED, and this is a defect:** {', '.join(_unlisted)}")
    contents_block = "\n".join(_present)

    (OUT / "README.md").write_text(f"""# Arctic Tracker deposit package

<!-- GENERATED by ingest/build_deposit.py. Do not edit this file; the next
     deposit build overwrites it. Edit the generator. -->

The snapshot described here was built {stamp} from schema `{schema}`.

{zenodo_note()}{REPO_COPY_NOTE}

## Contents

{contents_block}

## Not redistributed, and why

{chr(10).join(f"- **{t}**: {r}" for t, r in EXCLUDED.items())}

For both, the deposit provides record identifiers under `identifiers/`. For the
IUCN assessments those identifiers let any reader with a free Red List account
retrieve each assessment and reconstruct the table at source; the extraction
code lives in the code repository, not in this deposit. For the NAMMCO catch
records there is no extraction route at all, for the reason given above; the
identifiers and access date let a reader check every value against the public
NAMMCO database, which is the level of verification available for them. No figure in the paper
depends on non-public data.

## Provenance classes

Every row carries one:

- **DERIVED**: computed from a hashed source file. Reproducible by replay.
- **CURATED**: entered by a named human, versioned in the repository.
- **GATED**: machine-proposed and not servable until a named expert signs it.

## Known limitations

- `cites_trade_records.quantity` was `numeric(10,2)` until 2026-07-29, which
  silently altered **64,956** records; **7,091 of those** — a subset, not a
  further group — were rounded to exactly zero, and a further 3 exceeded the
  declared range and were dropped outright. This export is taken after the fix;
  any earlier export of this dataset carries the defect.
  `verification/verify_manuscript_claims.py` recomputes all three figures on demand.
- Source verification covers nine tables, re-derived by code paths that do not
  reuse the loaders. V-5 reads five curated CSVs and the IUCN retrieval
  snapshot. V-5b re-derives `cites_trade_records` on full content digest from
  the raw shards, `illegal_trade_seizures` by applying the documented
  decontamination rule from its written statement, and `catch_records` by
  applying the documented NAMMCO parsing rules. `cites_listings`,
  `timeline_events` and `cms_listings` are covered by the idempotency check
  alone, which proves the loader is deterministic and not that it is correct.
  The two are different guarantees and we do not merge them.
- 66 of 520 timeline events have no corroborating table in this database and
  are flagged `is_corroborated = false`.
- Narrative prose and reference bindings are GATED and unreviewed, so they are
  present in the tables but not served by the application.
- **The narrative citations have no bibliography behind them, and where they
  do resolve they are misattributed.** The 343 machine-drafted sections carry
  parenthetical author-year citations in their prose; `references` holds 4
  records and `narrative_review` holds none, so not one section has been
  reviewed. This is why the narrative layer is gated rather than merely
  unreviewed, and it is the true scope of the identical-references defect
  reported against the deployed site.

  **Measured 31 August.** Every claim in these sections naming a CITES appendix or an
  IUCN Red List category was compared with the corresponding value in this
  deposit: 70 claims are checkable that way and 35 of them, exactly half,
  contradict it — five give the wrong appendix, thirty the wrong Red List
  category, and eleven species contradict themselves between their own
  sections. A further 127 sections carry malformed citation syntax. The check
  is deterministic and uses no model. The sections are therefore being
  regenerated from the verified corpus rather than reviewed, and
  `species_narratives_no_citations.csv` is deposited as the record of what the
  generator produced, not as material to cite.

  How many citations there are depends on how one parses them, and this file
  previously gave a single number (412) that no rule we can reconstruct
  produces. A strict pattern over `(Author, YEAR)` gives 445 instances and
  219 distinct author-year pairs; a looser one that splits multi-citation
  parentheses on semicolons gives 697 and 344. The bibliography is 4 records
  either way, which is the fact that matters.

  **Resolution was sampled, not assumed.** Four pairs drawn at random from
  the distinct set failed in two distinct ways. Two resolve to no publication
  at all (Zimmerman & Williams 2000 for Siberian sturgeon distribution;
  Ansmann et al. 2014 for lynx paw morphology, an author who publishes on
  dolphins). Two resolve to real papers, by the right authors, in the right
  years, on the right species — and are attached to claims those papers do
  not make: Aulich et al. 2019 is an acoustic migration study cited for fin
  whale length and mass, and states 22 m with no mass at all, against the
  narrative's "20 to 27 meters and 40 to 80 metric tons"; van Beest et al.
  2018 is movement ecology and disturbance modelling cited for harbour
  porpoise body measurements it does not report.

  The second mode is the one to note. A citation that resolves to a real
  paper about the right species passes a reference-existence audit
  completely; only reading the source catches it. Treat every citation in
  this table as unverified regardless of whether its DOI resolves.
- `source_releases` records which upstream release each part of the corpus came
  from, and `obtained_on_basis` records how each date is known. The CITES date
  is inferred from the modification times of the downloaded shards; the IUCN
  date is carried in the artifact itself. Those are not claims of equal
  strength and the column exists so a reader can tell them apart.
""")

    # The verification scripts: every headline number is reproduced by a script
    # deposited with the data, so a reader who downloads the package to check a
    # number finds the thing that checks it.
    #
    # Copied rather than referenced: a deposit that points at a git repository
    # is only as durable as that repository, and the whole point of a deposit is
    # that it outlives our infrastructure.
    verif = OUT / "verification"
    verif.mkdir(exist_ok=True)
    SCRIPTS = [
        ("verify_manuscript_claims.py", "recomputes every number the paper reports"),
        ("verify_derived_truth.py", "re-reads the raw shards and compares on content digest"),
        ("verify_source_truth.py", "compares curated tables against their source files"),
        ("trajectory_report.py", "derives the status-trajectory tally under the stated rule"),
        ("redlist_scale.py", "the single Red List scale the trajectory rule depends on"),
        ("coverage_report.py", "fails if any table lacks a recorded verification decision"),
        ("attribution_loss.py", "measures what a species-level count cannot see"),
        # Added 2026-08-13. A reader holding this package can run all four: the
        # first two need only the loaded tables, the third reads ../schema.sql,
        # and the fourth reads this deposit. The gates that are absent are absent
        # for a reason — they need the raw shards, the Species+ API, our figure
        # scripts, or a destructive reload, none of which travel in a deposit.
        ("verify_metamorphic.py",
         "asserts properties that hold without knowing the right answer: published "
         "values survive row permutation, counts are additive over a partition, "
         "filters are monotone, aggregates survive relabelling"),
        ("verify_flag_invariants.py",
         "every flag named for a singular property is singular, or carries a "
         "written exemption saying what it actually means"),
        # Added 2026-10-06. Bounds how much of the trajectory signal survives
        # the IUCN criteria revisions, with both instruments and the confound
        # in the second one named.
        ("sensitivity_criteria_eras.py",
         "bounds how much of the trajectory signal needs an assessment made "
         "under superseded IUCN criteria, by transitions that cannot cross a "
         "revision and by reclassifying from a later start year"),
        ("verify_schema_applies.py",
         "../schema.sql stands up the tables from nothing and still describes them"),
        ("verify_deposit_roundtrip.py",
         "every CSV in ../tables/ loads back into the schema this package ships"),
        # Added 2026-09-01. These four were in the deposit and not in this list,
        # so they were shipped and manifested but never maintained from a source:
        # editing them meant editing the deposit, which is the drift the check
        # below now refuses. run_all.py in particular is the entry point the
        # deposit README tells a reader to use.
        ("run_all.py",
         "runs every check in this directory and reports pass, fail, crash or "
         "absent data separately, so a crash cannot read as a pass"),
        ("stratify_trajectories.py",
         "the interval from listing to a species' first comparable assessment, "
         "which is what the observation window has to survive"),
        ("window_sensitivity.py",
         "the sensitivity grid over observation window and baseline bound, "
         "reported rather than promised"),
        ("verify_pipeline_record.py",
         "pipeline.json still describes the pipeline it was derived from, and "
         "re-renders both stage figures byte-for-byte to prove it"),
    ]
    here = Path(__file__).parent
    # db.py is imported by verify_flag_invariants and verify_source_truth. It was
    # not shipped, so both died with ModuleNotFoundError for anyone running the
    # deposit. A script shipped without its imports is not a shipped script.
    for dep in ("db.py",):
        if (here / dep).exists():
            (verif / dep).write_text((here / dep).read_text())

    # attribution_loss.py was shipped and its output was not, so the claim it
    # supports could not be checked from the deposit. verify_manuscript_claims
    # is deliberate about this -- it counts the missing report as a MISMATCH
    # rather than a skip, because "80 of 81 reproduce" with one silently
    # unverifiable is the failure that script exists to prevent -- and it was
    # the one mismatch in the run on 2026-09-02.
    #
    # The script's own fallback looks for ../../ingest/reports, which resolves
    # inside this repository and not inside a downloaded deposit, so the gap
    # only appeared where a reviewer would actually meet it.
    reports_src = here / "reports" / "attribution_loss.json"
    if reports_src.exists():
        (verif / "reports").mkdir(exist_ok=True)
        (verif / "reports" / "attribution_loss.json").write_bytes(
            reports_src.read_bytes())
    else:
        print("NOTE: ingest/reports/attribution_loss.json is absent, so the "
              "falcon attribution claim will not be checkable from the "
              "deposit. Run ingest/attribution_loss.py first.")
    # Copying is one-directional and silent, and on 2026-09-01 that was found to
    # be destructive. The deposit's verify_manuscript_claims.py and
    # verify_derived_truth.py had been fixed in place on 31 August — one of them
    # had been crashing before its first assertion — and ingest/ still held the
    # 13 and 15 August versions. Running this builder would have overwritten both
    # fixes with the older code and shipped a deposit whose "87 of 87 claims
    # reproduce" was false, without printing anything.
    #
    # The direction of truth is not knowable from here, so this refuses rather
    # than guesses. Editing the deposit copy in place is the natural thing to do
    # when a shipped script is broken, so the message says how to reconcile it
    # instead of treating it as an error.
    drifted = []
    for name, _ in SCRIPTS:
        src, dst = here / name, verif / name
        if src.exists() and dst.exists() and \
                src.read_bytes() != dst.read_bytes():
            drifted.append(name)
    if drifted:
        print(f"\nTHE DEPOSIT AND ITS SOURCE DISAGREE ({len(drifted)}):\n")
        for name in drifted:
            s, d = (here / name).stat().st_size, (verif / name).stat().st_size
            print(f"  {name}: ingest/ {s} bytes, deposit/verification/ {d} bytes")
        print("\nThis build would overwrite the deposit copy with the ingest one")
        print("and say nothing. If the deposit copy is the fixed one, which is")
        print("what happens when a shipped script is repaired in place, copy it")
        print("back to ingest/ first:")
        for name in drifted:
            print(f"  cp deposit/verification/{name} ingest/{name}")
        print("\nIf ingest/ is right, delete the deposit copy and re-run.")
        raise SystemExit(1)

    shipped = []
    for name, why in SCRIPTS:
        src = here / name
        if src.exists():
            (verif / name).write_text(src.read_text())
            shipped.append((name, why))
        else:
            print(f"  WARNING: {name} not found; the deposit will not contain it")

    (verif / "README.md").write_text(
        "# Verification scripts\n\n"
        "These reproduce the numbers this paper reports, from the tables in\n"
        "`../tables/`. They are the same scripts the authors run, copied here\n"
        "rather than referenced, so the deposit does not depend on a repository\n"
        "outliving it.\n\n"
        "Each needs `ARCTIC_DATABASE_URL` pointing at a PostgreSQL instance,\n"
        "and `ARCTIC_SCHEMA` if you did not name your schema `arctic_v2`.\n"
        "`../schema.sql` creates the tables; the CSVs in `../tables/` fill them.\n\n"
        "**Two tables are not in this package and the scripts need them.**\n"
        "`iucn_assessments` and `catch_records` are withheld for licence reasons,\n"
        "so a database built from `tables/` alone cannot reproduce every number.\n"
        "The scripts say which tables are empty and how to rebuild each one\n"
        "rather than failing partway through — but you should know before you\n"
        "start, because it is the difference between an incomplete deposit and a\n"
        "broken one. This is the former, and it is a licence constraint rather\n"
        "than a choice of ours. See `../identifiers/` and the top-level README.\n\n"
        "`verify_manuscript_claims.py` prints every claim with the value the\n"
        "paper states, the value the data gives, and a verdict.\n\n"
        + "".join(f"- `{n}` — {w}\n" for n, w in shipped))
    # Files only, and no __pycache__. Running the shipped scripts from inside the
    # deposit — which is exactly what a reader does — leaves a __pycache__
    # directory there, and this loop hashed it as if it were a file. Before it
    # crashed it had been quietly recording compiled caches as part of the
    # package, and the package's own manifest stopped describing it.
    # The name test above was doing nothing that is_file() did not already do,
    # because iterdir() does not descend. The compiled caches live INSIDE
    # verification/__pycache__/, so they were never seen, never manifested, and
    # never removed — two .pyc files shipped in a deposit whose manifest claimed
    # to cover every file in it. Purge them, then walk recursively so that
    # verification/reports/ is covered too.
    # Both kinds of residue a reader's run leaves behind: compiled bytecode, and
    # verification/reports/, which the shipped verify_manuscript_claims.py writes
    # next to itself. Neither is deposit content. Running the scripts in place is
    # the intended use, so this residue is expected — the failure is shipping a
    # copy of it, which is what happened.
    #
    # Purge __pycache__ anywhere under the deposit, not only under verification/.
    # build_pipeline_diagram.py sits at the deposit root, so running it leaves
    # deposit/__pycache__/, which the root-level iterdir() walk below would
    # neither purge nor manifest yet would still ship in the folder — the same
    # defect this block fixed for verification/, still open one directory up.
    # rebuilt/ holds the reader's reconstituted IUCN categories. Shipping our
    # copy of it would redistribute the Red List data the withholding exists to
    # keep out of the package, so the build removes it rather than manifest it.
    for junk in list(OUT.rglob("__pycache__")) + [verif / "reports",
                                                  OUT / "rebuilt"]:
        if junk.is_dir():
            shutil.rmtree(junk)
    for f in sorted(verif.rglob("*")):
        if not f.is_file():
            continue
        manifest[f"verification/{f.relative_to(verif)}"] = {
            "sha256": sha256_file(f), "bytes": f.stat().st_size,
        }

    # figures/ holds the two stage diagrams generated from pipeline.json by
    # deposit/build_pipeline_diagram.py. They are deposit content: the platform
    # inlines them on /pipeline and verify_pipeline_record.py re-renders them
    # byte-for-byte as its central assertion. They were added after this builder
    # was written and it did not know about them, so a rebuild silently dropped
    # all four from the manifest — leaving files served as part of the deposit
    # that the freshness check cannot see, which is the exact gap the manifest
    # exists to close.
    figs = OUT / "figures"
    if figs.is_dir():
        for f in sorted(figs.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                manifest[f"figures/{f.relative_to(figs)}"] = {
                    "sha256": sha256_file(f), "bytes": f.stat().st_size,
                }
        print(f"  figures/: {sum(1 for f in figs.rglob('*') if f.is_file())} "
              f"file(s) in the manifest")

    # The supplementary tables are built by ingest/build_supplementary.py and
    # folded in here so they carry digests like everything else. Files served as
    # part of the deposit but absent from the manifest are exactly what the
    # freshness check cannot see.
    # Source Data, in the shape Nature Communications asks for: "multiple
    # labelled files within a zipped folder", one per figure. Per-figure CSVs
    # sitting in a repository directory are not that package.
    build_source_data_zip()

    # The curated source files. V-5 re-reads these to prove the tables reproduce
    # them, and it was shipped without them: run from the deposit it said
    # "source file missing" and stopped, which is a script that cannot work for
    # the one reader it was shipped for. They are 176 KB, they are our own
    # curation, and they are already redistributed here in derived form.
    curated_src = ROOT / "species_data/curated"
    if curated_src.is_dir():
        curated_out = OUT / "sources" / "curated"
        curated_out.mkdir(parents=True, exist_ok=True)
        n_cur = 0
        for f in sorted(curated_src.glob("*.csv")):
            (curated_out / f.name).write_bytes(f.read_bytes())
            manifest[f"sources/curated/{f.name}"] = {
                "sha256": sha256_file(curated_out / f.name),
                "bytes": (curated_out / f.name).stat().st_size,
            }
            n_cur += 1
        print(f"  sources/curated/: {n_cur} file(s) so V-5 can run from the deposit")

    # The schema a reader builds from travels with the data. Without it the
    # deposit is 22 CSVs and no statement of what they are meant to load into.
    schema_src = ROOT / "schema.sql"
    if schema_src.exists():
        (OUT / "schema.sql").write_text(
            "-- Copied into the deposit by ingest/build_deposit.py.\n"
            "-- The repository copy is generated by pg_dump via `make schema`.\n"
            "-- Edit neither by hand.\n" + schema_src.read_text())
        print("  schema.sql copied into the deposit")
    else:
        print("  WARNING: no schema.sql; run 'make schema'")

    supp = OUT / "supplementary"
    if supp.exists():
        for f in sorted(supp.iterdir()):
            if f.is_file() and f.name != "__pycache__":
                manifest[f"supplementary/{f.name}"] = {
                    "sha256": sha256_file(f), "bytes": f.stat().st_size,
                }
        print(f"  supplementary/: {sum(1 for f in supp.iterdir() if f.is_file())} file(s) in the manifest")
    else:
        print("  WARNING: no supplementary/ directory; run ingest/build_supplementary.py first")

    manifest.update(identifier_manifest)
    # Everything in the package gets a digest except the manifest itself, which
    # cannot contain its own hash. README.md, data_dictionary.json and the
    # traceability table were shipping without one — and the traceability table
    # is Supplementary Table 5, a cited artefact. A file a reader downloads from
    # the deposit and cannot verify is the gap the manifest exists to close.
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.name != "MANIFEST.sha256.json":
            manifest[f.name] = {"sha256": sha256_file(f), "bytes": f.stat().st_size}

    manifest_path = OUT / "MANIFEST.sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    # Re-hash the package against the manifest just written. A manifest that does
    # not describe its own deposit is the one defect a checksum file exists to
    # make impossible, and it happened: README.md, data_dictionary.json and a
    # verification script were recorded at sizes and digests they no longer had.
    # The build now refuses to finish rather than emit a package whose own
    # checksums are wrong.
    drift = []
    for rel, entry in manifest.items():
        f = OUT / rel
        if not f.exists():
            drift.append(f"{rel}: in the manifest, absent from the deposit")
        elif "sha256" in entry and sha256_file(f) != entry["sha256"]:
            drift.append(f"{rel}: manifest {entry['bytes']} bytes, "
                         f"file {f.stat().st_size} bytes")
    # And the reverse. The README promises "a hash for every file in this
    # package"; enforce it, do not trust the purge above to be exhaustive. Any
    # file present in the deposit but missing from the manifest is a break of
    # that promise — this is exactly how two __pycache__/.pyc shipped unnoticed.
    for f in sorted(OUT.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(OUT).as_posix()
        if rel == "MANIFEST.sha256.json":
            continue
        if rel not in manifest:
            drift.append(f"{rel}: in the deposit, absent from the manifest")
    if drift:
        print(f"\nDEPOSIT NOT WRITTEN CORRECTLY: {len(drift)} file(s) do not match "
              f"the manifest that ships with them:")
        for d in drift:
            print(f"  {d}")
        return 1
    print(f"  verification/: {len(shipped)} script(s), all in the manifest")

    print(f"\ndeposit built at {OUT.relative_to(ROOT)}")
    print(f"  {exported} tables exported, {total_rows} rows")
    print(f"  {len(EXCLUDED)} tables withheld for licence reasons, documented in README")
    print("\nNOT DONE, and deliberately: no DOI minted, nothing uploaded, no release tagged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
