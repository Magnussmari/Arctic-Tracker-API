#!/usr/bin/env python3
"""Rebuild the IUCN Red List categories this deposit does not redistribute.

Why the deposit does not carry them
-----------------------------------
IUCN's Terms and Conditions of Use prohibit redistributing Red List Data
"by means including ... archiving in a public data repository", whole or in
part, alone or combined with other data, including within Derivative Works,
without IUCN's prior written permission. A Red List category is Red List Data.

So this deposit ships what is ours and what is a pointer: the species, the
years, the scopes, and IUCN's own assessment identifiers. The category comes
from IUCN, to you, under your own acceptance of their terms. Nothing about the
paper's numbers is withheld - the procedure that produces them is here in full,
and this script is the first step of it.

What this script guarantees
---------------------------
REBUILD-IUCN.digest records the SHA-256 of figure5_source_data.csv as the
paper was computed on it. After a successful rebuild this script checks your
reconstituted copy against that digest. A match proves you hold the same
corpus, byte for byte - so the deposit's verifiers then measure the paper's
claims on exactly the data the paper used, without IUCN data ever having
passed through us.

Usage
-----
    export IUCN_API_TOKEN=...        # https://api.iucnredlist.org
    python3 rebuild_iucn.py

    python3 rebuild_iucn.py --from-json cached.json   # {assessment_id: code}

Exit 0 on a rebuild whose digest matches, 1 on a mismatch, 2 on a fetch
failure, 3 if it could not look.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

DEPOSIT = pathlib.Path(__file__).resolve().parent
ZIP = DEPOSIT / "source_data.zip"
IDENT = DEPOSIT / "identifiers" / "iucn_assessment_ids.csv"
DIGEST_FILE = DEPOSIT / "REBUILD-IUCN.digest"
REBUILT = DEPOSIT / "rebuilt"
SERIES = "Source Data/figure5_source_data.csv"
WITHHELD = "⟨withheld: see REBUILD-IUCN.md⟩"
# Regional but not European (Lamna nasus 2016, Mediterranean): outside the series.
# The same constant is redlist_scale.NOT_EUROPEAN_IDS in verification/; the
# repository check response/check_figure11_source_data.py asserts they agree.
NOT_EUROPEAN = frozenset({"16527805"})
SERIES_WINDOW = (1982, 2025)
API = "https://api.iucnredlist.org/api/v4/assessment/{aid}"
TAXON_API = "https://api.iucnredlist.org/api/v4/taxa/scientific_name"

# member -> (category column, species column, long-format marker, binding rule)
#
# The rule differs per file and it is written down here because it is not
# obvious from the files: figure5 is the per-assessment series and binds on
# species and year; figure4 reports one category per species AND scope;
# figures 1, 7 and 8 report, as published, the latest assessment of ANY scope,
# which is why nine of figure 1's forty-three cells carry a European regional
# category. figureB's panel A (manuscript Figure 11) reports the latest
# assessment of the global-and-European series, which is how it is bound since
# 21 October 2026: Global and Europe together, ordered by year and assessment id,
# inside 1982-2025, without the one Mediterranean assessment (NOT_EUROPEAN).
TARGETS = {
    "Source Data/figure1_source_data.csv": ("iucn_status", "scientific_name", None, "latest_any"),
    "Source Data/figure4_source_data.csv": ("current_status", "scientific_name", None, "latest_in_scope"),
    "Source Data/figure5_source_data.csv": ("status", "scientific_name", None, "per_year"),
    "Source Data/figure7_source_data.csv": ("iucn_status", "scientific_name", None, "latest_any"),
    "Source Data/figure8_source_data.csv": ("iucn_status", "scientific_name", None, "latest_any"),
    "Source Data/figureB_source_data.csv": ("value", "entity",
                                            ("metric", "latest_category"), "latest_series"),
}


USER_AGENT = "ArcticTracker-rebuild/1.0 (+https://doi.org/10.5281/zenodo.23578787)"


def identifiers():
    with IDENT.open(newline="", encoding="utf8") as fh:
        return list(csv.DictReader(fh))


def _get(url, token):
    """One API call, with rate limits and server hiccups waited out.

    Returns the parsed body, or the HTTP status code when IUCN answers with a
    refusal that waiting will not change (404, 401, 403).
    """
    req = urllib.request.Request(url, headers={
        "Authorization": token, "Accept": "application/json",
        # IUCN's API refuses Python's default User-Agent with 403.
        "User-Agent": USER_AGENT})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 5:
                retry_after = exc.headers.get("Retry-After") or ""
                wait = (int(retry_after) if retry_after.isdigit() else 0) or 5 * 2 ** attempt
                print(f"  HTTP {exc.code}, retrying in {wait} s", file=sys.stderr)
                time.sleep(wait)
                continue
            return exc.code
    return 429


def fetch_all(rows, token, pause=0.5):
    """assessment_id -> category code, from IUCN's own API.

    One call per species (43, not 370): the taxon record lists every published
    assessment with its category. An identifier the taxon record does not list
    is asked for on its own; if IUCN answers 404 there too, the assessment has
    been withdrawn from the Red List since the snapshot and is returned in the
    second value rather than guessed.
    """
    out, withdrawn = {}, []
    by_name = {}
    for r in rows:
        if r["assessment_id"].strip():
            by_name.setdefault(r["scientific_name"].strip(), []).append(r)
    for n, (name, wanted) in enumerate(sorted(by_name.items()), start=1):
        genus, species = name.split(" ", 1)
        body = _get(TAXON_API + "?" + urllib.parse.urlencode(
            {"genus_name": genus, "species_name": species}), token)
        if isinstance(body, int):
            print(f"  {name}: HTTP {body}", file=sys.stderr)
            return None, []
        listed = {str(a.get("assessment_id")): a.get("red_list_category_code") or ""
                  for a in body.get("assessments", [])}
        for r in wanted:
            aid = r["assessment_id"].strip()
            if listed.get(aid):
                out[aid] = listed[aid]
                continue
            one = _get(API.format(aid=aid), token)
            if one == 404:
                withdrawn.append((name, r["year_published"], r.get("scope", ""), aid))
                continue
            if isinstance(one, int):
                print(f"  {aid}: HTTP {one}", file=sys.stderr)
                return None, []
            code = ((one.get("red_list_category") or {}).get("code")
                    or one.get("category") or "")
            if not code:
                print(f"  {aid}: the response carries no category code",
                      file=sys.stderr)
                return None, []
            out[aid] = code
        if n % 10 == 0:
            print(f"  fetched {n}/{len(by_name)} species")
        time.sleep(pause)
    return out, withdrawn


def restore(categories, zip_path=None, out_dir=None):
    """Write the rebuilt members. Returns ({member: sha256}, {member: [unreproduced]})."""
    zip_path = zip_path or ZIP
    out_dir = out_dir or REBUILT
    out_dir.mkdir(exist_ok=True)

    rows_ident = identifiers()

    def newest(cands):
        best = None
        for r in cands:
            flag = str(r.get("is_latest", "")).strip().lower() in ("true", "1", "yes")
            year = int(r["year_published"]) if r["year_published"].strip().isdigit() else -1
            if best is None or (flag, year) > best[:2]:
                best = (flag, year, r["assessment_id"])
        return best[2] if best else ""

    per_year = {f"{r['scientific_name']}|{r['year_published']}": r["assessment_id"]
                for r in rows_ident}
    by_name = {}
    by_name_scope = {}
    for r in rows_ident:
        by_name.setdefault(r["scientific_name"], []).append(r)
        by_name_scope.setdefault((r["scientific_name"], (r.get("scope") or "")), []).append(r)
    latest_any = {k: newest(v) for k, v in by_name.items()}
    latest_global = {k: newest([r for r in v if (r.get("scope") or "Global") in ("", "Global")])
                     for k, v in by_name.items()}

    def newest_in_series(cands):
        best = None
        for r in cands:
            if (r.get("scope") or "Global") not in ("", "Global", "Europe"):
                continue
            aid = r["assessment_id"].strip()
            y = r["year_published"].strip()
            if aid in NOT_EUROPEAN or not aid.isdigit() or not y.isdigit():
                continue
            if not SERIES_WINDOW[0] <= int(y) <= SERIES_WINDOW[1]:
                continue
            if best is None or (int(y), int(aid)) > best[:2]:
                best = (int(y), int(aid), aid)
        return best[2] if best else ""
    latest_series = {k: newest_in_series(v) for k, v in by_name.items()}
    latest_scope = {k: newest(v) for k, v in by_name_scope.items()}

    digests, unreproduced = {}, {}
    with zipfile.ZipFile(zip_path) as zf:
        for member, (cat_col, name_col, marker, rule) in TARGETS.items():
            if member not in zf.namelist():
                continue
            rows = list(csv.DictReader(io.StringIO(zf.read(member).decode("utf8"))))
            if not rows:
                continue
            fields = list(rows[0].keys())
            missing = []
            for row in rows:
                if marker and (row.get(marker[0]) or "").strip() != marker[1]:
                    continue
                if (row.get(cat_col) or "").strip() != WITHHELD:
                    continue
                name = (row.get(name_col) or "").strip()
                aid = (row.get("assessment_id") or "").strip()
                if not aid:
                    if rule == "per_year":
                        aid = per_year.get(f"{name}|{row.get('year','')}", "")
                    elif rule == "latest_in_scope":
                        aid = latest_scope.get((name, (row.get("scope") or "")), "")
                    elif rule == "latest_global":
                        aid = latest_global.get(name, "")
                    elif rule == "latest_series":
                        aid = latest_series.get(name, "")
                    else:
                        aid = latest_any.get(name, "")
                code = ""
                for one in aid.split(";"):
                    code = categories.get(one.strip(), "")
                    if code:
                        break
                if not code:
                    missing.append(name or "(unnamed row)")
                    continue
                row[cat_col] = code
            # The rebuilt file carries the columns the original had, so a
            # digest comparison is a comparison of content and not of layout.
            keep = [f for f in fields if f != "assessment_id" or member == SERIES]
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=keep)
            w.writeheader()
            for row in rows:
                w.writerow({k: row.get(k, "") for k in keep})
            payload = buf.getvalue().encode("utf8")
            name = pathlib.PurePosixPath(member).name
            (out_dir / name).write_bytes(payload)
            digests[member] = hashlib.sha256(payload).hexdigest()
            unreproduced[member] = missing
            print(f"  rebuilt {name}"
                  + (f" - {len(missing)} row(s) with no category: "
                     f"{', '.join(sorted(set(missing))[:4])}" if missing else ""))
    return digests, unreproduced


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-json", help="cached {assessment_id: category} map")
    ap.add_argument("--out", help="write the rebuilt files here instead")
    ap.add_argument("--add", action="append", default=[], metavar="ID=CODE",
                    help="a category you obtained from IUCN for an assessment "
                         "their API no longer serves; may be repeated")
    args = ap.parse_args()

    if not ZIP.exists() or not IDENT.exists():
        print("  UNMEASURED: source_data.zip or the identifier table is missing",
              file=sys.stderr)
        return 3
    ids = {r["assessment_id"] for r in identifiers() if r["assessment_id"].strip()}
    print(f"  {len(ids)} assessment identifier(s) in {IDENT.name}")

    withdrawn = []
    if args.from_json:
        categories = json.loads(pathlib.Path(args.from_json).read_text(encoding="utf8"))
        print(f"  {len(categories)} category code(s) read from "
              f"{args.from_json}")
    else:
        token = os.environ.get("IUCN_API_TOKEN")
        if not token:
            print("  IUCN_API_TOKEN is not set. Request one at "
                  "https://api.iucnredlist.org and export it, or pass a cached "
                  "map with --from-json. See REBUILD-IUCN.md.", file=sys.stderr)
            return 3
        categories, withdrawn = fetch_all(identifiers(), token)
        if categories is None:
            print("  the fetch did not complete; nothing was written",
                  file=sys.stderr)
            return 2
        cache = DEPOSIT / "rebuilt" / "iucn_categories.json"
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps(categories, indent=0), encoding="utf8")
        print(f"  cached {len(categories)} code(s) in {cache}")

    for pair in args.add:
        aid, _, code = pair.partition("=")
        categories[aid.strip()] = code.strip()
    withdrawn = [w for w in withdrawn if w[3] not in categories]
    if withdrawn:
        print(f"\n  IUCN no longer publishes {len(withdrawn)} assessment(s) the "
              f"paper used. They were withdrawn from the Red List after the "
              f"snapshot was made, so their categories cannot be fetched:",
              file=sys.stderr)
        for name, year, scope, aid in withdrawn:
            print(f"    {name}, {year}, {scope or 'Global'}: assessment {aid}",
                  file=sys.stderr)
        print("  If you obtain a category from IUCN, pass it with "
              "--add ID=CODE. See REBUILD-IUCN.md.", file=sys.stderr)

    out_dir = pathlib.Path(args.out) if args.out else REBUILT
    digests, _ = restore(categories, out_dir=out_dir)

    want = DIGEST_FILE.read_text(encoding="utf8").split()[0]
    got = digests.get(SERIES)
    if got is None:
        print("  UNMEASURED: the series was not rebuilt", file=sys.stderr)
        return 3
    if got != want and withdrawn:
        print(f"\n  MISMATCH: the rebuilt series hashes to\n    {got}\n"
              f"  and differs from the paper's. The {len(withdrawn)} withdrawn "
              f"assessment(s) above are missing from it, which on its own "
              f"changes the series. The verifiers report which claims depend "
              f"on them.", file=sys.stderr)
        return 1
    if got != want:
        print(f"\n  MISMATCH: the rebuilt series hashes to\n    {got}\n"
              f"  and the paper was computed on\n    {want}\n"
              f"  The categories you fetched are not the ones the paper used. "
              f"IUCN reassess and republish, so a later fetch can legitimately "
              f"differ; report the digest you obtained alongside any number you "
              f"recompute.", file=sys.stderr)
        return 1
    print(f"\n  MATCH: the rebuilt series hashes to sha256:{got}, which is the "
          f"corpus this paper was computed on. The deposit's verifiers will "
          f"now measure against it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
