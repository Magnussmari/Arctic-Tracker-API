#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-10
"""Resolve one licensed photograph per species from iNaturalist, once.

WHY THIS EXISTS
---------------
The v1 site called the iNaturalist API while rendering a species page. Three
problems followed from that, and this loader is the answer to all three.

  SPEED       A network round trip per page view. Resolved once here, stored,
              and served from our own origin, a species page does no external
              I/O at all.
  FRAGILITY   A rate limit or an outage became a broken image on a live page a
              reviewer was reading.
  LICENCE     iNaturalist's default is all rights reserved. Displaying a
              photograph without checking its licence is a copyright problem,
              not a styling one, and roughly a fifth of our species are in that
              category.

So: resolve, check the licence, record the photographer's credit verbatim,
store the bytes with a digest, and mark the row displayable only when the
licence permits it AND a credit exists. The read-surface view filters on that
flag, so an unlicensed image cannot reach a page even if a caller asks.

MATCHING
--------
Species are matched on exact scientific name against the taxa search, checking
several results rather than trusting the first: a plain search for
`Acipenser baerii` ranks another sturgeon above it. A non-exact match is
recorded with match_exact = false and is NOT displayed, because a confidently
wrong photograph is worse than no photograph. That is the same rule the seizure
records follow.

Usage:
  ARCTIC_DATABASE_URL=... ./.venv/bin/python ingest/inaturalist_media_load.py \
      --target-schema arctic_v2 --media-dir <app>/public/media/species
  ... --dry-run    resolve and report, write nothing
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import validate_schema  # noqa: E402

LOADER_VERSION = "inaturalist_media_load/1.1"
API = "https://api.inaturalist.org/v1/taxa"
OBS = "https://api.inaturalist.org/v1/observations"
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")
UA = {"User-Agent": "ArcticTracker/2.0 (research; +https://doi.org/10.5281/zenodo.23578786"
      + (f"; mailto:{CONTACT_EMAIL}" if CONTACT_EMAIL else "") + ")"}

# Licences under which we may display the photograph with attribution.
# Absent from this set, including a null licence code, means do not display.
# ND (no derivatives) is permitted: we display the image unmodified.
DISPLAYABLE = {"cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa", "cc-by-nc-nd", "cc-by-nd"}

# Courtesy pause between API calls. iNaturalist asks for at most 1/second and
# we are in no hurry: this runs once, not per page view.
PAUSE = 0.7


def resolve(name: str) -> tuple[dict | None, bool]:
    """Find the taxon for this scientific name.

    Returns (taxon, exact). `exact` is True when the taxon's accepted name is
    the name we asked for. It is False when we matched through a synonym: our
    name is the one CITES uses and iNaturalist has since moved the species to
    another accepted name. Grus canadensis is the case in this corpus — it is
    Antigone canadensis there, and the strict matcher recorded it as "no exact
    taxonomic match", which is not what a reader understands by that phrase.

    A synonym match is not a wrong animal. It is recorded, and matched_name
    carries the accepted name so the page can say which taxon the photograph is
    filed under.
    """
    url = f"{API}?" + urllib.parse.urlencode(
        {"q": name, "rank": "species", "per_page": 10})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            results = json.load(r).get("results") or []
    except Exception as exc:                       # network, JSON, HTTP
        print(f"  !! {name}: {exc}")
        return None, False
    for taxon in results:
        if (taxon.get("name") or "").lower() == name.lower():
            return taxon, True
    # Synonym: iNaturalist reports which term the search hit. Accept it only
    # when that term is exactly our name, never on a fuzzy ranking.
    for taxon in results:
        if (taxon.get("matched_term") or "").lower() == name.lower():
            return taxon, False
    return None, False


def licensed_photo(taxon_id: int) -> dict | None:
    """A research-grade observation photograph we are allowed to display.

    WHY THIS EXISTS
    ---------------
    v1.0 read `taxon.default_photo` and stopped. iNaturalist's default photo is
    all rights reserved for most taxa, so thirteen of the forty-three species
    ended with nothing, and the site told readers that "most have only an
    all-rights-reserved photograph". Checked against the source on 2026-08-31,
    that was false: every one of those thirteen has licensed photographs, from
    18 research-grade observations for Acipenser baerii to 58,039 for Antigone
    canadensis. The constraint was never the licence. It was that we looked at
    exactly one photograph per species.

    Research-grade only, because a community-confirmed identification is the
    same standard the rest of this corpus applies to an attributed record.
    """
    url = f"{OBS}?" + urllib.parse.urlencode({
        "taxon_id": taxon_id,
        "photo_license": "cc0,cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa,cc-by-nc-nd,cc-by-nd",
        "photos": "true",
        "quality_grade": "research",
        "order_by": "votes",
        "per_page": 1,
    })
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            results = json.load(r).get("results") or []
    except Exception as exc:
        print(f"  !! licensed-photo lookup failed for taxon {taxon_id}: {exc}")
        return None
    for obs in results:
        for photo in obs.get("photos") or []:
            if photo.get("license_code") in DISPLAYABLE and photo.get("attribution"):
                return photo
    return None


def clean_attribution(value: str | None) -> str | None:
    """Collapse whitespace in a credit, and change nothing else.

    iNaturalist returned "(c) \nJörg Mazur, algunos derechos reservados
    (CC BY-SA)" for Mesoplodon stejnegeri — a newline straight after "(c)",
    which rendered on the page as a credit reading "(c)" and nothing more. The
    photographer lost their name to a line break.

    Whitespace only. The wording, the language and the punctuation are the
    source's and stay the source's, including when the source answers in
    Spanish. This corpus records credits verbatim; a credit nobody can read is
    not verbatim, it is broken.
    """
    if value is None:
        return None
    collapsed = " ".join(value.split())
    return collapsed or None


def fetch_bytes(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
            return r.read()
    except Exception as exc:
        print(f"  !! image download failed: {exc}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--media-dir", help="write image files here (skipped if omitted)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    schema = validate_schema(args.target_schema)

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    media_dir = Path(args.media_dir) if args.media_dir else None
    if media_dir and not args.dry_run:
        media_dir.mkdir(parents=True, exist_ok=True)

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute(f"select id, scientific_name from {schema}.species order by scientific_name")
    species = cur.fetchall()

    stats = {"displayable": 0, "unlicensed": 0, "unmatched": 0, "nophoto": 0}
    rows = []

    for sid, name in species:
        taxon, exact = resolve(name)
        time.sleep(PAUSE)
        if not taxon:
            stats["unmatched"] += 1
            print(f"  --   {name}: no match, not even through a synonym")
            rows.append((sid, "inaturalist", None, None, None, None, False,
                         None, None, None, None, False, None, None))
            continue

        photo = taxon.get("default_photo") or {}
        lic = photo.get("license_code")
        attribution = clean_attribution(photo.get("attribution"))

        # The default photo is usually all rights reserved. That is a fact about
        # which photograph iNaturalist happens to feature, not about whether a
        # licensed photograph of the species exists.
        if not (lic in DISPLAYABLE and attribution):
            fallback = licensed_photo(taxon["id"])
            time.sleep(PAUSE)
            if fallback:
                photo = fallback
                lic = photo.get("license_code")
                attribution = clean_attribution(photo.get("attribution"))
                print(f"  ..   {name}: default photo unusable, took a licensed "
                      f"research-grade observation instead")
        src_url = photo.get("medium_url") or photo.get("url")

        if not src_url:
            stats["nophoto"] += 1
            print(f"  --   {name}: taxon {taxon['id']}, no photo")
            rows.append((sid, "inaturalist", taxon["id"], None, lic, attribution,
                         False, None, None, None, taxon.get("name"), exact, None, None))
            continue

        displayable = bool(lic and lic in DISPLAYABLE and attribution)
        local_path = sha = None

        if displayable and media_dir and not args.dry_run:
            data = fetch_bytes(src_url)
            if data:
                sha = hashlib.sha256(data).hexdigest()
                ext = ".jpg" if ".jp" in src_url.lower() else Path(
                    urllib.parse.urlparse(src_url).path).suffix or ".jpg"
                fname = name.replace(" ", "_") + ext
                (media_dir / fname).write_bytes(data)
                local_path = f"/media/species/{fname}"
            else:
                displayable = False

        if displayable:
            stats["displayable"] += 1
            print(f"  ok   {name}: {lic}")
        else:
            stats["unlicensed"] += 1
            print(f"  no   {name}: licence={lic!r} -> not displayed")

        rows.append((sid, "inaturalist", taxon["id"], str(photo.get("id")), lic,
                     attribution, displayable, src_url, local_path, sha,
                     taxon.get("name"), exact, src_url, sha))

    if args.dry_run:
        print("\n(dry run, nothing written)")
    else:
        cur.execute(f"delete from {schema}.species_media where source = 'inaturalist'")
        cur.executemany(
            f"""insert into {schema}.species_media
                (species_id, source, source_taxon_id, source_photo_id, license_code,
                 attribution, is_displayable, original_url, local_path, content_sha256,
                 matched_name, match_exact, loader_version, source_artifact, source_sha256)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'{LOADER_VERSION}',%s,%s)""",
            rows)
        conn.commit()

    total = len(species)
    print(f"\n{stats['displayable']} of {total} species have a displayable, "
          f"attributed photograph")
    print(f"  {stats['unlicensed']} licence does not permit display (or no credit)")
    print(f"  {stats['nophoto']} matched but no photograph")
    print(f"  {stats['unmatched']} no name match at all")
    print("\nEvery non-displayable case is recorded rather than dropped, so the "
          "site can say what is missing and why.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
