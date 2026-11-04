#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-27
"""Reference-relevance gate (SPEC-REFERENCE-PROVENANCE-FIX v1.0, ISC-4).

Deterministic + human authority ONLY. No LLM in this path (answers a
reviewer's objection to LLMs validating LLM output). A candidate reference may become a LIVE binding
only if a non-LLM judge passes it:

  ACCEPT  lexical-binomial   exact scientific binomial in title/abstract
  ACCEPT  lexical-common     a registered common name in title/abstract
  ACCEPT  allowlist          human-signed per-DOI exception (recorded rationale)
  REVIEW  genus-only         bare genus match but NOT the binomial -> human queue
                             (this is the Falco rusticolus vs peregrinus trap;
                             genus is NEVER a live accept)
  REJECT  no-species-signal  nothing matched

REVIEW and REJECT are both "not live". Only ACCEPT authorizes a live binding.
A separate model judge (elsewhere) may only ORDER the REVIEW queue; it never
promotes to ACCEPT here.

"""
from __future__ import annotations

import re
from dataclasses import dataclass

_TAG = re.compile(r"<[^>]+>")
_WORD = re.compile(r"[a-z]+")


def _norm(text: str | None) -> str:
    return _TAG.sub("", (text or "")).lower()


@dataclass(frozen=True)
class GateResult:
    decision: str   # ACCEPT | REVIEW | REJECT
    method: str     # lexical-binomial | lexical-common | allowlist | genus-only | no-species-signal
    reason: str

    @property
    def is_live(self) -> bool:
        return self.decision == "ACCEPT"


def gate_reference(
    *,
    title: str | None,
    doi: str | None,
    species_scientific: str,
    common_names: list[str] | None = None,
    abstract: str | None = None,
    allowlist_dois: set[str] | None = None,
) -> GateResult:
    """Decide whether one candidate reference may bind LIVE to one species.

    Deterministic and side-effect free. `abstract` is optional extra haystack.
    """
    hay = f"{_norm(title)} {_norm(abstract)}"
    sci = species_scientific.strip().lower()
    genus = sci.split()[0] if sci else ""
    commons = [c.strip().lower() for c in (common_names or []) if c and c.strip()]
    allow = {d.strip().lower() for d in (allowlist_dois or set()) if d}

    # Human-signed allowlist first (records a verified exception, e.g. a study
    # whose title names no species). Requires a recorded rationale upstream.
    if doi and doi.strip().lower() in allow:
        return GateResult("ACCEPT", "allowlist", f"DOI {doi} on human-signed allowlist")

    # Exact binomial (the only automatic species-identity signal we trust).
    if sci and sci in hay:
        return GateResult("ACCEPT", "lexical-binomial", f"binomial '{sci}' present")

    # Registered common name.
    for cn in commons:
        if cn and cn in hay:
            return GateResult("ACCEPT", "lexical-common", f"common name '{cn}' present")

    # Bare genus but not the binomial -> congener risk, never a live accept.
    if genus and re.search(rf"\b{re.escape(genus)}\b", hay):
        return GateResult(
            "REVIEW", "genus-only",
            f"genus '{genus}' present but not the binomial/common name; congener risk, human review",
        )

    return GateResult("REJECT", "no-species-signal", "no species identity signal in title/abstract")
