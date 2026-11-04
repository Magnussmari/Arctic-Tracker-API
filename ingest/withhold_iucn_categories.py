#!/usr/bin/env python3
"""Replace every IUCN Red List category in the deposit with a pointer to it.

IUCN's Terms and Conditions of Use prohibit redistributing Red List Data
"by means including ... archiving in a public data repository", whole or in
part, alone or combined with other data, including within Derivative Works,
without IUCN's prior written permission. A category value is Red List Data.

An assessment identifier is not. It is a pointer into IUCN's own published
record, and IUCN publishes the category at that pointer. So the deposit ships
the identifier and REBUILD-IUCN.md, and a reader reconstitutes the corpus from
the source under their own acceptance of IUCN's terms. The deposit also ships
the SHA-256 of the reconstituted file, so a reader can prove they rebuilt the
same corpus the paper was computed on without IUCN data ever passing
through us.

A second thing falls out of this, measured rather than intended. Two deposited
files carried a category for the same assessment and disagreed on 23 of them -
fifteen of those where timeline_events said "LC" and figure5_source_data.csv
said CR, K, V, E, T or DD. After this transform only the identifier is shipped,
so the two files cannot disagree about a category: neither one states one.
"One scale, one source" stops being a rule someone has to remember and becomes
a property of the package.

Run from the repository root:

    PYTHONDONTWRITEBYTECODE=1 python3 ingest/withhold_iucn_categories.py

Then refresh the manifest and run the gate:

    python3 ingest/build_deposit.py --refresh-digests
    cd deposit && PYTHONDONTWRITEBYTECODE=1 \
        python3 verification/verify_iucn_withheld.py
"""
import argparse
import csv
import hashlib
import io
import pathlib
import shutil
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "deposit" / "verification"))
import redlist_scale as rl  # noqa: E402  the one definition of the series

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEPOSIT = ROOT / "deposit"
ZIP = DEPOSIT / "source_data.zip"
SERIES = "Source Data/figure5_source_data.csv"
WITHHELD = "⟨withheld: see REBUILD-IUCN.md⟩"

# Only an actual Red List category is Red List Data. "N/A", "NA" and "NR" are
# this corpus's own markers for "no assessment of this kind exists", and
# withholding them would hide our own bookkeeping behind IUCN's terms.
CATEGORIES = {
    "EX", "EW", "CR", "EN", "VU", "NT", "LC", "DD", "NE",
    "LR/cd", "LR/lc", "LR/nt", "LR",
    "E", "V", "R", "K", "T", "I", "CT", "RE", "Ex", "Ex?",
    "CR(PE)", "CR(PEW)",
}


IDENT = DEPOSIT / "identifiers" / "iucn_assessment_ids.csv"


def read_series():
    """The name+year+id series, from whichever copy still carries the binding.

    On a first run that is figure5_source_data.csv inside the archive. After
    the first run the category there is withheld, so the species-bound
    identifier table is the source and the script stays idempotent instead of
    silently losing the binding on a second run.
    """
    if IDENT.exists():
        with IDENT.open(newline="", encoding="utf8") as fh:
            rows = list(csv.DictReader(fh))
        if rows and "scientific_name" in rows[0] and "assessment_id" in rows[0]:
            return [{"scientific_name": r["scientific_name"],
                     "year": r["year_published"],
                     "status": "",
                     "assessment_id": r["assessment_id"],
                     "scope": r.get("scope", ""),
                     "is_latest": r.get("is_latest", "")} for r in rows]
    with zipfile.ZipFile(ZIP) as zf:
        raw = zf.read(SERIES).decode("utf8")
    rows = list(csv.DictReader(io.StringIO(raw)))
    for need in ("scientific_name", "year", "status", "assessment_id", "scope"):
        if need not in rows[0]:
            raise SystemExit(f"  ABORT: {SERIES} has no {need!r} column")
    return rows


def build_binding(series):
    """name|year -> assessment_id.

    Where one species-year carries several assessments they differ by scope,
    and the paper's scale is the global one, so a global assessment wins. Only
    a species-year with several *global* assessments stays unresolvable, and
    the gate reports those rather than guessing.
    """
    by_key = {}
    for r in series:
        by_key.setdefault((r["scientific_name"], r["year"]), []).append(r)
    out = {}
    for (name, year), rows in by_key.items():
        glob = [r for r in rows if (r.get("scope") or "").strip() == "Global"]
        pick = glob or rows
        ids = sorted({r["assessment_id"] for r in pick})
        # 25 species-years carry two assessments published in the same year -
        # IUCN republishes an assessment, and both are real records. Naming
        # both is truer than naming neither: the reader can resolve either and
        # see for themselves that they agree.
        out[f"{name}|{year}"] = ";".join(ids)
    return out


def species_names():
    """species_id -> scientific_name, for the deposited table copy."""
    path = DEPOSIT / "tables" / "species.csv"
    with path.open(newline="", encoding="utf8") as fh:
        return {r["id"]: r["scientific_name"] for r in csv.DictReader(fh)}


NAMES = None


def latest_in_series(series):
    """scientific_name -> the identifier of its latest assessment of the series.

    For Figure 11 (figureB) panel A only, from 21 October 2026: Global and
    Europe assessments as one series, 1982-2025, newest year and within a year
    the higher assessment id, the Mediterranean assessment outside it. The
    corrected-regional list is NOT applied here: the seven European ones count.
    """
    best = {}
    for r in series:
        if not rl.in_series(r):
            continue
        y = int(r["year"]) if str(r["year"]).strip().isdigit() else -1
        if not 1982 <= y <= 2025:
            continue
        key = (y, int(r["assessment_id"]))
        name = r["scientific_name"]
        if name not in best or key > best[name][0]:
            best[name] = (key, str(r["assessment_id"]))
    return {k: v[1] for k, v in best.items()}


def latest_assessment(series):
    """scientific_name -> the identifier of its latest global assessment.

    Every figure but figure5 reports one category per species, so one
    identifier per species is what those rows need. It is chosen by the rule
    the figure generators use (visualizations/data_processing/global_scope.py):
    global scope, the eight regional assessments in
    species_data/curated/iucn_scope_corrections.csv excluded, newest year, and
    within a year the higher assessment id, as the Methods state.

    Until 18 October 2026 this preferred the is_latest flag and broke a
    same-year tie by row order, so for the blue whale (2018) and the North
    Atlantic right whale (2020) it bound the lower of two same-year ids while
    the generator draws the higher. The categories agree; the identifier is
    what a reader resolves, so it must be the one actually used.
    """
    with open(ROOT / "species_data" / "curated" / "iucn_scope_corrections.csv",
              newline="", encoding="utf8") as fh:
        regional = {r["assessment_id"].strip() for r in csv.DictReader(fh)}
    best = {}
    for r in series:
        name = r["scientific_name"]
        if (r.get("scope") or "Global") not in ("", "Global"):
            continue
        aid = str(r["assessment_id"]).strip()
        if aid in regional or not aid.isdigit():
            continue
        year = int(r["year"]) if str(r["year"]).strip().isdigit() else -1
        key = (year, int(aid))
        if name not in best or key > best[name][0]:
            best[name] = (key, aid)
    return {k: v[1] for k, v in best.items()}


SCOPES = pathlib.Path(__file__).resolve().parent / "data" / "iucn_scope_codes.csv"


def scope_codes():
    """{assessment_id: scope_code}. Blank is global, as the view holds it."""
    if not SCOPES.is_file():
        raise SystemExit(f"  ABORT: {SCOPES} is not here, so the identifier "
                         f"table would be written without the scope code")
    with SCOPES.open(newline="", encoding="utf8") as fh:
        return {r["assessment_id"].strip(): r["scope_code"].strip()
                for r in csv.DictReader(fh)}


def write_identifier_table(series):
    """Species-bound identifiers: everything but the category itself.

    The previous identifiers/iucn_assessment_ids.csv held 370 ids with no
    species, so no row of the corpus could be resolved through it. These
    columns are IUCN's own identifiers and metadata, not Red List Data.
    """
    out = DEPOSIT / "identifiers" / "iucn_assessment_ids.csv"
    # scope_code as well as scope. The description is LOSSY: code 2 is the
    # Europe region and code EU is the twenty-seven member states, and the view
    # describes both as "Europe". Writing only the description publishes a
    # category at a scope it was not assessed at. The first version of this
    # writer dropped the code while adding the species names, which is a trade
    # and not an upgrade. See ingest/data/README-iucn_scope_codes.md.
    codes = scope_codes()
    fields = ["scientific_name", "year_published", "assessment_id", "scope",
              "scope_code", "is_latest", "redlist_url"]
    rows = []
    for r in sorted(series, key=lambda r: (r["scientific_name"], r["year"])):
        aid = str(r["assessment_id"])
        if aid not in codes:
            raise SystemExit(f"  ABORT: assessment {aid} has no scope code in "
                             f"{SCOPES}; a regional assessment published as "
                             f"'Europe' alone names a geography it may not have "
                             f"been assessed at")
        code = codes[aid]
        described = (r.get("scope") or "").strip()
        if (code == "") != (described in ("", "Global")):
            raise SystemExit(f"  ABORT: assessment {aid} is described as "
                             f"{described!r} and coded {code!r}; the two "
                             f"disagree about whether it is global")
        rows.append({
            "scientific_name": r["scientific_name"],
            "year_published": r["year"],
            "assessment_id": r["assessment_id"],
            "scope": r.get("scope", ""),
            "scope_code": code,
            "is_latest": r.get("is_latest", ""),
            "redlist_url": f"https://www.iucnredlist.org/assessment/{r['assessment_id']}",
        })
    with out.open("w", newline="", encoding="utf8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


DIGEST_FILE = DEPOSIT / "REBUILD-IUCN.digest"


def reconstituted_digest():
    """The SHA-256 a reader's rebuilt figure5_source_data.csv must match.

    Taken on the file while it still carries the category, so a reader can
    prove their rebuild reproduces the corpus the paper was computed on. Once
    recorded it is never recomputed: recomputing it from a withheld file would
    publish the digest of a file nobody can rebuild.
    """
    if DIGEST_FILE.exists():
        return DIGEST_FILE.read_text(encoding="utf8").split()[0], True
    with zipfile.ZipFile(ZIP) as zf:
        return hashlib.sha256(zf.read(SERIES)).hexdigest(), False


# (path, category column, identifier column, which rows are assessment rows)
LOOSE_TARGETS = [
    ("sources/curated/timeline_events.csv", "status", "iucn_assessment_id",
     lambda r: r.get("event_type") == "iucn_assessment"),
    ("tables/timeline_events.csv", "status", "iucn_assessment_id",
     lambda r: r.get("event_type") == "iucn_assessment"),
    ("supplementary/supplementary_table_1_post_listing_window.csv",
     "baseline_status", "baseline_assessment_id", lambda r: True),
]


def key_for(rel, row):
    if "timeline_events" not in rel:
        return ""
    name = (row.get("scientific_name") or "").strip()
    if not name:
        # tables/timeline_events.csv carries species_id, not the name.
        name = NAMES.get((row.get("species_id") or "").strip(), "")
    return f"{name}|{row.get('year','')}"


def withhold_rows(rows, fields, cat_col, id_col, is_assessment, binding, rel):
    if id_col not in fields:
        fields.insert(fields.index(cat_col) + 1, id_col)
    n = unbound = 0
    for row in rows:
        row.setdefault(id_col, "")
        if not is_assessment(row):
            continue
        val = (row.get(cat_col) or "").strip()
        if not val or val == WITHHELD or val not in CATEGORIES:
            continue
        row[cat_col] = WITHHELD
        if not (row.get(id_col) or "").strip():
            aid = binding.get(key_for(rel, row), "")
            if aid:
                row[id_col] = aid
            else:
                unbound += 1
        n += 1
    return n, unbound


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    global NAMES
    NAMES = species_names()
    series = read_series()
    binding = build_binding(series)
    digest, recorded = reconstituted_digest()
    print(f"  series: {len(series)} assessment rows, "
          f"{len(binding)} unambiguous name+year bindings")
    print(f"  reconstituted {SERIES} must hash to sha256:{digest}"
          + ("  (recorded earlier)" if recorded else "  (recorded now)"))

    total = 0
    for rel, cat_col, id_col, pred in LOOSE_TARGETS:
        path = DEPOSIT / rel
        if not path.exists():
            raise SystemExit(f"  ABORT: {rel} is not in the deposit")
        with path.open(newline="", encoding="utf8") as fh:
            reader = csv.DictReader(fh)
            fields = list(reader.fieldnames)
            rows = list(reader)
        if cat_col not in fields:
            raise SystemExit(f"  ABORT: {rel} has no {cat_col!r} column")
        n, unbound = withhold_rows(rows, fields, cat_col, id_col, pred, binding, rel)
        print(f"  {rel}: {n} withheld"
              + (f", {unbound} with no resolvable identifier" if unbound else ""))
        total += n
        if args.dry_run:
            continue
        tmp = path.with_suffix(".csv.tmp")
        with tmp.open("w", newline="", encoding="utf8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for row in rows:
                w.writerow({k: row.get(k, "") for k in fields})
        tmp.replace(path)

    # The Source Data archive. Every figure keeps every column that is ours
    # and loses the one column that is IUCN's. The targets are named rather
    # than sniffed, because figure2's "category" column holds a species name
    # and figure4's "status_changes" holds a count - a heuristic would withhold
    # both and corrupt two figures to satisfy a licence that does not cover
    # either.
    #
    # (member, category column, how a row names its species, long-format marker)
    ARCHIVE_TARGETS = [
        ("Source Data/figure1_source_data.csv", "iucn_status", "scientific_name", None),
        ("Source Data/figure4_source_data.csv", "current_status", "scientific_name", None),
        ("Source Data/figure5_source_data.csv", "status", "scientific_name", None),
        ("Source Data/figure7_source_data.csv", "iucn_status", "scientific_name", None),
        ("Source Data/figure8_source_data.csv", "iucn_status", "scientific_name", None),
        ("Source Data/figureB_source_data.csv", "value", "entity",
         ("metric", "latest_category")),
    ]
    latest = latest_assessment(series)
    latest_ser = latest_in_series(series)
    rewritten = {}
    for member, cat_col, name_col, marker in ARCHIVE_TARGETS:
        with zipfile.ZipFile(ZIP) as zf:
            if member not in zf.namelist():
                raise SystemExit(f"  ABORT: {member} is not in the archive")
            rows = list(csv.DictReader(io.StringIO(zf.read(member).decode("utf8"))))
        if not rows:
            continue
        fields = list(rows[0].keys())
        if cat_col not in fields:
            raise SystemExit(f"  ABORT: {member} has no {cat_col!r} column")
        # figure5 is the per-assessment series and binds on name+year; every
        # other figure reports the latest assessment and binds on name alone.
        per_year = "figure5" in member
        id_col = "assessment_id"
        if id_col not in fields:
            fields.insert(fields.index(cat_col) + 1, id_col)
        n = unbound = 0
        for row in rows:
            row.setdefault(id_col, "")
            if marker and (row.get(marker[0]) or "").strip() != marker[1]:
                continue
            val = (row.get(cat_col) or "").strip()
            if not val or val == WITHHELD or val not in CATEGORIES:
                continue
            row[cat_col] = WITHHELD
            if not (row.get(id_col) or "").strip():
                name = (row.get(name_col) or "").strip()
                aid = (binding.get(f"{name}|{row.get('year','')}") if per_year
                       else (latest_ser if "figureB" in member else latest).get(name)) or ""
                if aid:
                    row[id_col] = aid
                else:
                    unbound += 1
            n += 1
        print(f"  {member}: {n} withheld"
              + (f", {unbound} with no resolvable identifier" if unbound else ""))
        total += n
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
        rewritten[member] = buf.getvalue().encode("utf8")

    if not args.dry_run:
        if not DIGEST_FILE.exists():
            DIGEST_FILE.write_text(
                f"{digest}  Source Data/figure5_source_data.csv (reconstituted)\n",
                encoding="utf8")
        backup = ZIP.with_suffix(".zip.bak")
        shutil.copy2(ZIP, backup)
        tmp = ZIP.with_suffix(".zip.tmp")
        with zipfile.ZipFile(backup) as zin, \
             zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                zout.writestr(info, rewritten.get(info.filename,
                                                  zin.read(info.filename)))
        tmp.replace(ZIP)
        backup.unlink()
        wrote = write_identifier_table(series)
        print(f"  identifiers/iucn_assessment_ids.csv: {wrote} species-bound rows")

    print(f"\n  {total} category value(s) "
          + ("would be " if args.dry_run else "")
          + "replaced by a pointer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
