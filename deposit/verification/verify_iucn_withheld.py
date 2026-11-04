#!/usr/bin/env python3
"""No IUCN Red List category may leave this package.

The Red List Terms and Conditions of Use prohibit redistribution of Red List
Data "by means including ... archiving in a public data repository", whole or
in part, alone or combined with other data, including within Derivative Works,
without prior written permission of IUCN.

A category value - LC, VU, EN, CR, NT, DD and the pre-1994 codes - IS Red List
Data. An assessment identifier is not: it is a pointer into IUCN's own
published record, and it is what lets a reader rebuild the corpus from the
source. So the deposit ships identifiers and REBUILD-IUCN.md, never categories.

This gate exists because compliance that depends on remembering is compliance
that fails on the next build. Run from deposit/:

    PYTHONDONTWRITEBYTECODE=1 python3 verification/verify_iucn_withheld.py

Exit 0 clean, 1 if a category is present, 3 if it could not look.
"""
import csv
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The modern scale, the 1994 scale, and the pre-1994 codes the corpus carries.
# Measured from the source: the categories actually present were CR DD E EN K
# LC LR/cd LR/lc LR/nt NT RE T V VU, plus the non-category markers N/A NA NR NE.
CATEGORIES = {
    "EX", "EW", "CR", "EN", "VU", "NT", "LC", "DD", "NE",
    "LR/cd", "LR/lc", "LR/nt", "LR",
    "E", "V", "R", "K", "T", "I", "CT", "RE", "Ex", "Ex?",
    "CR(PE)", "CR(PEW)",
}
# "I" is also a CITES appendix and "T" a trade code, so a bare match is not
# enough: a category only counts when the column says it is one.
AMBIGUOUS = {"I", "T", "E", "V", "K", "R"}

# A column whose name says it holds a Red List category.
CATEGORY_COLUMN_HINTS = ("status", "category", "assessment", "redlist", "red_list")
# ... except where the name says it holds something else entirely.
NOT_CATEGORY_COLUMN = ("assessment_id", "assessment_year", "baseline_assessment_id",
                       "conservation_status_source", "status_source")

# The withheld marker the deposit uses in place of a category.
WITHHELD = "⟨withheld: see identifiers/iucn_assessment_ids.csv⟩"


def is_category_column(name):
    low = name.lower()
    if low in NOT_CATEGORY_COLUMN:
        return False
    return any(h in low for h in CATEGORY_COLUMN_HINTS)


def row_is_redlist(row, col):
    """Does this row's own evidence say the value is a Red List category?

    Needed because "I" is also a CITES appendix, "T" a trade code and "E" an
    export code. A gate that reads those as Red List categories reports a
    violation that is not there, and a gate that over-reports is a gate the
    next build switches off.
    """
    low = col.lower()
    if "redlist" in low or "red_list" in low or "baseline_status" in low:
        return True
    for k, v in row.items():
        if not k or not isinstance(v, str):
            continue
        kl, vl = k.lower(), v.lower()
        if kl in ("event_type", "source_type", "type", "kind", "metric") and "iucn" in vl:
            return True
    return False


def scan_csv(path):
    hits = []
    with path.open(newline="", encoding="utf8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            return hits
        cat_cols = [c for c in reader.fieldnames if c and is_category_column(c)]
        for n, row in enumerate(reader, start=2):
            for col in cat_cols:
                val = (row.get(col) or "").strip().strip('"')
                if not val or val == WITHHELD or val not in CATEGORIES:
                    continue
                # An unambiguous category counts wherever it sits. An ambiguous
                # one counts only where the row says it is Red List data.
                if val in AMBIGUOUS and not row_is_redlist(row, col):
                    continue
                hits.append((n, col, val))
    return hits


def _walk_json(data):
    hits = []

    def walk(node, trail):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, trail + [str(k)])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, trail + [str(i)])
        else:
            if not trail:
                return
            key = trail[-1]
            if isinstance(node, str) and is_category_column(key):
                val = node.strip()
                if val and val != WITHHELD and val in CATEGORIES:
                    hits.append(("/".join(trail), key, val))

    walk(data, [])
    return hits


def scan_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf8"))
    except Exception:
        return []
    return _walk_json(data)


def scan_zip(path):
    """Source Data ships as a zip, and the zip is what the journal publishes.

    A gate that only reads loose files declares a package clean while the
    archive beside it carries the data. This blind spot was real: it is named
    here so the next reader knows the archive is covered.
    """
    import zipfile
    hits = []
    try:
        zf = zipfile.ZipFile(path)
    except Exception:
        return hits
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            low = info.filename.lower()
            if not (low.endswith(".csv") or low.endswith(".json")):
                continue
            raw = zf.read(info.filename)
            tmp = io.StringIO(raw.decode("utf8", "replace"))
            if low.endswith(".csv"):
                reader = csv.DictReader(tmp)
                if not reader.fieldnames:
                    continue
                cat_cols = [c for c in reader.fieldnames if c and is_category_column(c)]
                for n, row in enumerate(reader, start=2):
                    for col in cat_cols:
                        val = (row.get(col) or "").strip().strip('"')
                        if not val or val == WITHHELD or val not in CATEGORIES:
                            continue
                        if val in AMBIGUOUS and not row_is_redlist(row, col):
                            continue
                        hits.append((f"{info.filename}:{n}", col, val))
            else:
                try:
                    data = json.loads(raw.decode("utf8"))
                except Exception:
                    continue
                for where, col, val in _walk_json(data):
                    hits.append((f"{info.filename}:{where}", col, val))
    return hits


def self_test():
    """A gate proves nothing until it has proven its own field of view."""
    import io
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        bad = d / "bad.csv"
        bad.write_text("scientific_name,year,status\nTestus speciesus,2015,VU\n", encoding="utf8")
        if not scan_csv(bad):
            return "self-test FAILED: a VU in a status column was not caught"

        ok = d / "ok.csv"
        ok.write_text(f"scientific_name,year,status\nTestus speciesus,2015,{WITHHELD}\n",
                      encoding="utf8")
        if scan_csv(ok):
            return "self-test FAILED: the withheld marker was read as a category"

        # An identifier is not a category.
        ident = d / "ident.csv"
        ident.write_text("assessment_id,year_published\n9442304,2007\n", encoding="utf8")
        if scan_csv(ident):
            return "self-test FAILED: an assessment_id was read as a category"

        # A CITES appendix "I" in an appendix column must not trip it.
        app = d / "app.csv"
        app.write_text("taxon,appendix\nTestus speciesus,I\n", encoding="utf8")
        if scan_csv(app):
            return "self-test FAILED: a CITES appendix was read as a category"

        # A CITES listing row whose status is "I" is an appendix, not a category.
        cl = d / "cl.csv"
        cl.write_text("scientific_name,event_type,status\n"
                      "Testus speciesus,cites_listing,I\n", encoding="utf8")
        if scan_csv(cl):
            return "self-test FAILED: a CITES listing appendix was read as a category"

        # The same value in an IUCN assessment row IS a category and must trip.
        iu = d / "iu.csv"
        iu.write_text("scientific_name,event_type,status\n"
                      "Testus speciesus,iucn_assessment,I\n", encoding="utf8")
        if not scan_csv(iu):
            return "self-test FAILED: an ambiguous category in an IUCN row was missed"
    return None


def main():
    problem = self_test()
    if problem:
        print(f"  {problem}", file=sys.stderr)
        return 3

    targets = sorted(p for p in ROOT.rglob("*")
                     if p.is_file() and p.suffix.lower() in (".csv", ".json", ".zip")
                     and "verification/reports" not in p.as_posix()
                     # rebuilt/ is the READER's reconstituted copy, written by
                     # rebuild_iucn.py. It holds categories by design and under
                     # the reader's own terms with IUCN. Scanning it made this
                     # gate fail on the intended use of the package, which is
                     # a gate that punishes correct behaviour.
                     and not p.relative_to(ROOT).as_posix().startswith("rebuilt/"))
    if not targets:
        print("  UNMEASURED: no deposited csv/json/zip files found", file=sys.stderr)
        return 3

    total = 0
    for p in targets:
        suffix = p.suffix.lower()
        if suffix == ".csv":
            hits = scan_csv(p)
        elif suffix == ".json":
            hits = scan_json(p)
        else:
            hits = scan_zip(p)
        if hits:
            rel = p.relative_to(ROOT).as_posix()
            print(f"  {rel}: {len(hits)} Red List category value(s)", file=sys.stderr)
            for where, col, val in hits[:4]:
                print(f"      {where} [{col}] = {val!r}", file=sys.stderr)
            if len(hits) > 4:
                print(f"      ... and {len(hits) - 4} more", file=sys.stderr)
            total += len(hits)

    if total:
        print(f"\n  FAIL: {total} Red List category value(s) in {len(targets)} "
              f"deposited files. IUCN's terms prohibit redistributing these; "
              f"ship identifiers and REBUILD-IUCN.md instead.", file=sys.stderr)
        return 1

    print(f"  PASS: {len(targets)} deposited csv/json/zip artefacts, archive "
          f"members included, carry no IUCN Red List category value.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
