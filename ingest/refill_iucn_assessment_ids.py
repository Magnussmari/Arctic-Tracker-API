#!/usr/bin/env python3
"""Refill the assessment_id column each withheld figure needs to be rebuilt.

The first withholding pass bound every per-species figure to the latest GLOBAL
assessment. That was wrong for nine species: in this corpus "latest" means the
most recent assessment of any scope, and for nine Arctic cetaceans that is a
2023 European regional assessment. Binding them to the global record would have
made the rebuild quietly produce a different figure from the published one. The
divergence would have looked like a rebuild bug and hidden the real finding,
which is that figures 1, 7 and 8 carry regional categories where the prose
reports global status.

So the identifier is written with the rule the figure actually uses, and the
rule is named per file. Run from the repository root.
"""
import csv
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
IDENT = DEPOSIT / "identifiers" / "iucn_assessment_ids.csv"
WITHHELD = "⟨withheld: see REBUILD-IUCN.md⟩"

RULES = {
    "Source Data/figure1_source_data.csv":
        ("iucn_status", "scientific_name", None, "latest_any"),
    "Source Data/figure4_source_data.csv":
        ("current_status", "scientific_name", None, "latest_in_scope"),
    "Source Data/figure7_source_data.csv":
        ("iucn_status", "scientific_name", None, "latest_any"),
    "Source Data/figure8_source_data.csv":
        ("iucn_status", "scientific_name", None, "latest_any"),
    "Source Data/figureB_source_data.csv":
        ("value", "entity", ("metric", "latest_category"), "latest_series"),
}


def newest(cands):
    best = None
    for r in cands:
        flag = str(r.get("is_latest", "")).strip().lower() in ("true", "1", "yes")
        year = int(r["year_published"]) if r["year_published"].strip().isdigit() else -1
        if best is None or (flag, year) > best[:2]:
            best = (flag, year, r["assessment_id"])
    return best[2] if best else ""


def main():
    with IDENT.open(newline="", encoding="utf8") as fh:
        rows_ident = list(csv.DictReader(fh))
    by_name, by_scope = {}, {}
    for r in rows_ident:
        by_name.setdefault(r["scientific_name"], []).append(r)
        by_scope.setdefault((r["scientific_name"], r.get("scope", "")), []).append(r)
    latest_any = {k: newest(v) for k, v in by_name.items()}
    latest_global = {
        k: newest([r for r in v if (r.get("scope") or "Global") in ("", "Global")])
        for k, v in by_name.items()
    }
    latest_scope = {k: newest(v) for k, v in by_scope.items()}

    # Figure 11 (figureB) panel A: the latest assessment of the global-and-
    # European series, 1982-2025, the higher assessment id standing in a tied
    # year, the Mediterranean one outside it (21 October 2026).
    def newest_in_series(cands):
        best = None
        for r in cands:
            if not rl.in_series({"scope": r.get("scope"), "assessment_id": r["assessment_id"]}):
                continue
            y = r["year_published"].strip()
            if not y.isdigit() or not 1982 <= int(y) <= 2025:
                continue
            if best is None or (int(y), int(r["assessment_id"])) > best[:2]:
                best = (int(y), int(r["assessment_id"]), r["assessment_id"])
        return best[2] if best else ""
    latest_series = {k: newest_in_series(v) for k, v in by_name.items()}

    rewritten, changed = {}, 0
    with zipfile.ZipFile(ZIP) as zf:
        names = zf.namelist()
        for member, (cat_col, name_col, marker, rule) in RULES.items():
            if member not in names:
                continue
            rows = list(csv.DictReader(io.StringIO(zf.read(member).decode("utf8"))))
            if not rows:
                continue
            fields = list(rows[0].keys())
            if "assessment_id" not in fields:
                fields.insert(fields.index(cat_col) + 1, "assessment_id")
            n = 0
            for row in rows:
                if marker and (row.get(marker[0]) or "").strip() != marker[1]:
                    continue
                if (row.get(cat_col) or "").strip() != WITHHELD:
                    continue
                name = (row.get(name_col) or "").strip()
                if rule == "latest_in_scope":
                    aid = latest_scope.get((name, row.get("scope", "")), "")
                elif rule == "latest_global":
                    aid = latest_global.get(name, "")
                elif rule == "latest_series":
                    aid = latest_series.get(name, "")
                else:
                    aid = latest_any.get(name, "")
                if aid and row.get("assessment_id") != aid:
                    row["assessment_id"] = aid
                    n += 1
            print(f"  {member}: {n} identifier(s) rewritten under rule {rule!r}")
            changed += n
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=fields)
            w.writeheader()
            for row in rows:
                w.writerow({k: row.get(k, "") for k in fields})
            rewritten[member] = buf.getvalue().encode("utf8")

    backup = ZIP.with_suffix(".zip.bak")
    shutil.copy2(ZIP, backup)
    tmp = ZIP.with_suffix(".zip.tmp")
    with zipfile.ZipFile(backup) as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                zout.writestr(info, rewritten.get(info.filename,
                                                  zin.read(info.filename)))
    tmp.replace(ZIP)
    backup.unlink()
    print(f"\n  {changed} identifier(s) rewritten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
