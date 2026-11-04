#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-27
"""Species-bound logged retrieval layer (SPEC-REFERENCE-PROVENANCE-FIX v1.0, ISC-2/3/11).

Replaces the old undocumented manual Scite Assistant procedure with a coded,
logged retrieval where the species binomial is a REQUIRED conjunct of every
query. This is the fix for the theme-drift root cause: the old per-section
retrieval matched the section theme keyword ("movement patterns", "climate
change") and, for thin-literature species, pulled off-domain papers. Here the
species can never be dropped from the query, and every candidate is captured
with full provenance for the frozen, Zenodo-citable snapshot.

The actual Scite call is injected (`search_fn`) so this module is deterministic
and unit-testable, and the production Scite API client slots in without changing
the query/provenance logic. Nothing here writes to a database.

"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable

# The 11 conservation-profile sections, with the theme terms that refine (never
# replace) the species conjunct. These theme words are exactly what leaked in
# the incident; here they can only ever narrow a species-scoped query.
SECTION_THEMES: dict[str, list[str]] = {
    "description": ["morphology", "identification"],
    "habitat": ["habitat", "ecology"],
    "population_size": ["population size", "abundance"],
    "population_trend": ["population trend", "decline", "increase"],
    "generation_length": ["generation length", "age at maturity"],
    "movement_patterns": ["movement", "migration"],
    "subpopulations": ["subpopulation", "stock", "management unit"],
    "distribution_range": ["distribution", "range"],
    "threats": ["threats", "climate change", "bycatch"],
    "use_and_trade": ["trade", "harvest", "CITES"],
    "conservation": ["conservation", "management", "protection"],
}


class QueryScopeError(ValueError):
    """Raised if a query would be emitted without a species identity term."""


@dataclass(frozen=True)
class RetrievalCandidate:
    species_scientific: str
    section: str
    query_text: str
    title: str | None
    doi: str | None
    retrieved_at: str          # ISO8601, passed in (caller stamps; keeps this pure)
    retrieval_tool: str
    retrieval_model: str
    tool_version: str
    response_sha256: str | None = None
    extra: dict = field(default_factory=dict)


def build_query(species_scientific: str, section: str, common_names: list[str] | None = None) -> str:
    """Build ONE Scite query with the species as a required conjunct.

    Shape: ("<binomial>" OR "<common>"...) AND (<theme> OR <theme>...)
    The species group is mandatory; the theme group only refines it. A theme-only
    query (the incident's failure shape) is structurally impossible here.
    """
    sci = species_scientific.strip()
    if not sci:
        raise QueryScopeError("no species binomial given; refusing to emit a theme-only query")
    species_terms = [f'"{sci}"'] + [f'"{c.strip()}"' for c in (common_names or []) if c and c.strip()]
    species_group = "(" + " OR ".join(species_terms) + ")"
    themes = SECTION_THEMES.get(section)
    if themes is None:
        raise KeyError(f"unknown section {section!r}; expected one of {list(SECTION_THEMES)}")
    theme_group = "(" + " OR ".join(f'"{t}"' if " " in t else t for t in themes) + ")"
    return f"{species_group} AND {theme_group}"


def assert_species_bound(query_text: str, species_scientific: str) -> None:
    """Guard: a query is only allowed to run if it names the species. Used by the
    retrieval driver and by tests to prove no theme-only query can ever be issued."""
    if f'"{species_scientific.strip()}"' not in query_text:
        raise QueryScopeError(f"query does not bind the species {species_scientific!r}: {query_text}")


def retrieve_species(
    *,
    species_scientific: str,
    common_names: list[str] | None,
    search_fn: Callable[[str], list[dict]],
    retrieved_at: str,
    retrieval_tool: str = "scite",
    retrieval_model: str = "unset",
    tool_version: str = "unset",
    sections: list[str] | None = None,
) -> list[RetrievalCandidate]:
    """Run species-bound retrieval across the sections. `search_fn(query)->[{title,doi,...}]`
    is injected (the real Scite API client in prod, a stub in tests). Every query is
    asserted species-bound before it runs; every result is captured as a provenance row."""
    out: list[RetrievalCandidate] = []
    for section in (sections or list(SECTION_THEMES)):
        query = build_query(species_scientific, section, common_names)
        assert_species_bound(query, species_scientific)  # cannot run an unbound query
        for hit in search_fn(query) or []:
            out.append(RetrievalCandidate(
                species_scientific=species_scientific,
                section=section,
                query_text=query,
                title=hit.get("title"),
                doi=hit.get("doi"),
                retrieved_at=retrieved_at,
                retrieval_tool=retrieval_tool,
                retrieval_model=retrieval_model,
                tool_version=tool_version,
                response_sha256=hit.get("response_sha256"),
                extra={k: v for k, v in hit.items() if k not in {"title", "doi", "response_sha256"}},
            ))
    return out


def candidate_as_row(c: RetrievalCandidate) -> dict:
    """Flatten to a dict matching arctic.reference_candidates columns."""
    return asdict(c)
