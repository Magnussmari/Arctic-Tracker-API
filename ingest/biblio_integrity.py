#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-27
"""Bibliographic-integrity validator (SPEC-REFERENCE-PROVENANCE-FIX v1.0, ISC-5).

Deterministic external confirmation of a stored binding's bibliographic record.
For a given (DOI, stored title) this asks Crossref whether the DOI resolves and
whether the title Crossref holds for that DOI matches the title we stored. This
catches two distinct failure modes the lexical gate cannot:

  1. LLM-parser corruption   the stored title was mangled during flattening.
  2. Real-DOI-wrong-pairing   a valid DOI was bound to the wrong stored title.

This module is NOT in the gate authority path. It is a deterministic external
check (Crossref REST, read-only) that supplements the lexical gate. No LLM is
involved. Network access is confined to the public Crossref API and every
failure mode degrades gracefully to `resolves=False` rather than raising.

The title-normalization and matching logic (`normalize_title`, `title_overlap`,
`titles_match`) is pure and side-effect free, and is what the unit tests cover
with mocked responses. No test in this repo hits the network.

"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass

try:
    import requests
except ImportError:  # requests is optional at import time; only the live call needs it
    requests = None  # type: ignore

CROSSREF_WORKS = "https://api.crossref.org/works/{doi}"
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")
# User-Agent per Crossref etiquette. Set CONTACT_EMAIL in the environment to add
# a mailto, which routes requests onto Crossref's polite pool. Read-only GET,
# one work at a time.
USER_AGENT = (
    "ArcticTracker/2.0 (research; +https://doi.org/10.5281/zenodo.23578786"
    + (f"; mailto:{CONTACT_EMAIL}" if CONTACT_EMAIL else "") + ")"
)
DEFAULT_TIMEOUT = 15.0

_TAG = re.compile(r"<[^>]+>")
_NONWORD = re.compile(r"[^a-z0-9\s]+")
_WS = re.compile(r"\s+")

# Frequent title stopwords carry no bibliographic identity; dropping them keeps
# the overlap metric from rewarding matches on "the/of/and/in" alone.
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "of", "and", "or", "in", "on", "at", "to", "for",
        "with", "from", "by", "as", "is", "are", "be", "into", "over",
    }
)

# Matching threshold, justified:
# We use a token-containment metric (intersection over the smaller token set),
# not raw Jaccard. Crossref titles and stored titles legitimately differ by a
# trailing subtitle, a series suffix, or a dropped parenthetical, which deflates
# Jaccard even for a true match. Containment asks the narrower question that
# actually matters for identity: "are (almost) all of the significant words of
# the shorter title present in the longer one?" A genuine same-paper pair sits
# near 1.0; an unrelated pair (the incident failure mode: red-panda title bound
# under a sturgeon DOI) sits far below. 0.70 leaves headroom for one or two
# token differences on short titles while still rejecting a different paper.
MATCH_THRESHOLD = 0.70


@dataclass(frozen=True)
class BiblioResult:
    doi: str
    resolves: bool          # DOI returned a Crossref record
    crossref_title: str | None
    title_match: bool       # normalized token containment >= MATCH_THRESHOLD
    status: str             # human-readable outcome / error detail
    overlap: float = 0.0    # the measured containment score (for auditing)


def normalize_title(text: str | None) -> list[str]:
    """Lowercase, strip HTML tags, ASCII-fold, drop punctuation and stopwords.

    Returns the list of significant tokens. Pure and deterministic.
    """
    if not text:
        return []
    s = _TAG.sub(" ", text)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = _NONWORD.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return [t for t in s.split(" ") if t and t not in _STOPWORDS]


def title_overlap(a: str | None, b: str | None) -> float:
    """Token containment: |A ∩ B| / min(|A|, |B|). 0.0 when either side is empty.

    Containment (not Jaccard) so a legitimate subtitle/suffix difference does not
    sink a true match. See MATCH_THRESHOLD rationale above.
    """
    ta, tb = set(normalize_title(a)), set(normalize_title(b))
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / min(len(ta), len(tb))


def titles_match(a: str | None, b: str | None, threshold: float = MATCH_THRESHOLD) -> bool:
    """True when normalized token containment meets the pre-registered threshold."""
    return title_overlap(a, b) >= threshold


def _extract_crossref_title(payload: dict) -> str | None:
    """Pull the primary title string out of a Crossref /works response body."""
    msg = payload.get("message") or {}
    titles = msg.get("title") or []
    if isinstance(titles, list) and titles:
        return titles[0]
    if isinstance(titles, str) and titles:
        return titles
    return None


def check_reference(
    doi: str | None,
    stored_title: str | None,
    *,
    session=None,
    timeout: float = DEFAULT_TIMEOUT,
) -> BiblioResult:
    """Resolve a DOI via Crossref and compare its title to the stored title.

    Read-only, single GET, graceful failure. Any network error, timeout, non-200,
    or missing title collapses to `resolves=False` with the reason in `status`.
    A missing/blank DOI short-circuits without a network call.
    """
    clean_doi = (doi or "").strip()
    if not clean_doi:
        return BiblioResult("", False, None, False, "no-doi", 0.0)

    if requests is None:
        return BiblioResult(clean_doi, False, None, False, "requests-unavailable", 0.0)

    getter = (session or requests).get
    url = CROSSREF_WORKS.format(doi=clean_doi)
    try:
        resp = getter(
            url,
            headers={"User-Agent": USER_AGENT},
            params={"mailto": CONTACT_EMAIL} if CONTACT_EMAIL else None,
            timeout=timeout,
        )
    except Exception as exc:  # network down, timeout, DNS, TLS, etc.
        return BiblioResult(clean_doi, False, None, False, f"request-error: {exc}", 0.0)

    if resp.status_code == 404:
        return BiblioResult(clean_doi, False, None, False, "doi-not-found", 0.0)
    if resp.status_code != 200:
        return BiblioResult(clean_doi, False, None, False, f"http-{resp.status_code}", 0.0)

    try:
        payload = resp.json()
    except Exception as exc:
        return BiblioResult(clean_doi, False, None, False, f"bad-json: {exc}", 0.0)

    crossref_title = _extract_crossref_title(payload)
    if not crossref_title:
        return BiblioResult(clean_doi, True, None, False, "resolved-no-title", 0.0)

    ov = title_overlap(stored_title, crossref_title)
    match = ov >= MATCH_THRESHOLD
    status = "match" if match else "title-mismatch"
    return BiblioResult(clean_doi, True, crossref_title, match, status, round(ov, 3))
