#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-27
"""Full 43-species gated reference audit (SPEC-REFERENCE-PROVENANCE-FIX v1.0, ISC-1/6).

Runs the deterministic species-relevance gate (`ingest.reference_gate`) against
EVERY reference in every processed conservation-profile file, using a common-name
map assembled from the standardization report, the prompt headers, and the
common name embedded in each processed file. Emits a per-species supplementary
audit table (worst-first) plus totals to `reports/reference-gate-audit-43.md`,
and prints the totals.

SCOPE: this is a deterministic SCREENING pass, not a proof of correctness.
  - ACCEPT means an exact binomial or a registered common name is present in the
    title. It does NOT prove the paper is about this species in substance.
  - REVIEW/REJECT means no lexical species signal was found in the stored title.
    That is a candidate flagged for Crossref + human check, NOT a proven-wrong
    binding. Recall is bounded by common-name coverage: a real paper that names
    the species only in its abstract or by a synonym we did not register will be
    under-counted here. The gate is intentionally conservative (genus-only never
    accepts) so it errs toward REVIEW, not toward false ACCEPT.

Read-only. No network, no DB. Deterministic and re-runnable.

"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ingest.reference_gate import gate_reference

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "species_data" / "scite" / "processed"
PROMPTS_DIR = ROOT / "species_data" / "scite" / "prompts" / "species"
REPORT_MD = ROOT / "species_data" / "scite" / "SPECIES_JSON_STANDARDIZATION_REPORT.md"
OUT_MD = ROOT / "reports" / "reference-gate-audit-43.md"

# Human-signed allowlist carried over from the canary set: the one verified
# narwhal telemetry study whose title names no species (Movement Ecology 2023).
ALLOWLIST_DOIS = {"10.1186/s40462-023-00397-y"}

_PROMPT_HEADER = re.compile(r"^#\s*Conservation Profile Prompt:\s*(.+?)\s*\(([^)]+)\)")
_REPORT_ROW = re.compile(r"`([A-Z][a-z]+_[a-z_]+)\.json`.*?[-|]\s*([A-Za-z][^|\n]+?)\s*(?:✅)?\s*$")


def _split_common(raw: str) -> list[str]:
    """Split a display common name into candidate lexical forms.

    'Killer Whale (Orca)' -> ['killer whale', 'orca']; 'Beluga' -> ['beluga'].
    Slash alternatives are split too. Whole phrases are kept (the gate does a
    contiguous substring match), never single generic words invented by us.
    """
    out: list[str] = []
    # pull parenthetical alternates first, then strip them from the base
    for alt in re.findall(r"\(([^)]+)\)", raw):
        out.append(alt)
    base = re.sub(r"\([^)]*\)", " ", raw)
    for part in re.split(r"[/,]", base):
        p = part.strip()
        if p:
            out.append(p)
    seen, uniq = set(), []
    for c in out:
        k = c.strip().lower()
        if k and k not in seen:
            seen.add(k)
            uniq.append(c.strip())
    return uniq


def build_common_name_map() -> dict[str, list[str]]:
    """Merge common names from prompt headers + standardization report + processed files.

    Keyed by scientific binomial (as stored in the processed file). Every source
    is additive; more registered names means higher recall for the screen.
    """
    cmap: dict[str, set[str]] = {}

    def add(binomial: str, names: list[str]) -> None:
        if not binomial:
            return
        key = binomial.strip()
        cmap.setdefault(key, set())
        for n in names:
            for form in _split_common(n):
                cmap[key].add(form)

    # Source 1: prompt headers "Binomial (Common Name)"
    if PROMPTS_DIR.is_dir():
        for f in sorted(PROMPTS_DIR.glob("*_conservation_profile.md")):
            try:
                first = f.read_text(encoding="utf-8").splitlines()[0]
            except (OSError, IndexError):
                continue
            m = _PROMPT_HEADER.match(first)
            if m:
                add(m.group(1), [m.group(2)])

    # Source 2: standardization report rows (filename stem -> common name)
    if REPORT_MD.is_file():
        for line in REPORT_MD.read_text(encoding="utf-8").splitlines():
            m = _REPORT_ROW.search(line)
            if m:
                binomial = m.group(1).replace("_", " ")
                add(binomial, [m.group(2)])

    # Source 3: the common name embedded in each processed file (strongest, authored per species)
    for f in sorted(PROCESSED_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sd = (d or {}).get("species_data") or {}
        sci = sd.get("scientific_name")
        cn = sd.get("common_name")
        if sci and cn:
            add(sci, [cn])

    return {k: sorted(v) for k, v in cmap.items()}


def audit() -> dict:
    cmap = build_common_name_map()
    per_species = []
    totals = {"candidates": 0, "ACCEPT": 0, "REVIEW": 0, "REJECT": 0}

    for f in sorted(PROCESSED_DIR.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        sd = (d or {}).get("species_data") or {}
        sci = sd.get("scientific_name") or f.stem.replace("_", " ")
        refs = (d or {}).get("references") or []
        commons = cmap.get(sci, [])

        counts = {"ACCEPT": 0, "REVIEW": 0, "REJECT": 0}
        for ref in refs:
            res = gate_reference(
                title=ref.get("title"),
                doi=ref.get("doi"),
                species_scientific=sci,
                common_names=commons,
                allowlist_dois=ALLOWLIST_DOIS,
            )
            counts[res.decision] += 1

        n = len(refs)
        per_species.append({
            "species": sci,
            "common": commons[0] if commons else "",
            "candidates": n,
            "ACCEPT": counts["ACCEPT"],
            "REVIEW": counts["REVIEW"],
            "REJECT": counts["REJECT"],
            "accept_rate": (counts["ACCEPT"] / n) if n else 0.0,
        })
        totals["candidates"] += n
        for k in ("ACCEPT", "REVIEW", "REJECT"):
            totals[k] += counts[k]

    # worst-first: lowest accept-rate first, then most rejected, then most candidates
    per_species.sort(key=lambda r: (r["accept_rate"], -r["REJECT"], -r["candidates"]))
    catastrophic = [r for r in per_species if r["candidates"] > 0 and r["ACCEPT"] == 0]
    return {"per_species": per_species, "totals": totals, "catastrophic": catastrophic,
            "species_count": len(per_species)}


def render_markdown(result: dict) -> str:
    t = result["totals"]
    rows = result["per_species"]
    cat = result["catastrophic"]
    lines = []
    lines.append("<!--")
    lines.append("@artifact      Supplementary audit table — 43-species gated reference screen (ISC-1/6)")
    lines.append("@orchestrator  Magnus Smárason | smarason.is")
    lines.append("@created       2026-07-27")
    lines.append("-->")
    lines.append("")
    lines.append("# Reference-Gate Audit — all 43 species")
    lines.append("")
    lines.append("Deterministic species-relevance screen of every stored reference in the 43 processed "
                 "conservation-profile files, using `ingest.reference_gate.gate_reference` (SPEC-REFERENCE-"
                 "PROVENANCE-FIX v1.0, ISC-4). Re-runnable: `.venv/bin/python -m ingest.audit_all_references`.")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"- Species audited: **{result['species_count']}**")
    lines.append(f"- Candidate references: **{t['candidates']}**")
    lines.append(f"- ACCEPT (live-eligible, lexical species signal present): **{t['ACCEPT']}** "
                 f"({_pct(t['ACCEPT'], t['candidates'])})")
    lines.append(f"- REVIEW (genus-only / congener risk -> human queue): **{t['REVIEW']}** "
                 f"({_pct(t['REVIEW'], t['candidates'])})")
    lines.append(f"- REJECT (no species signal in stored title): **{t['REJECT']}** "
                 f"({_pct(t['REJECT'], t['candidates'])})")
    lines.append(f"- Catastrophic all-REJECT species (0 ACCEPT): **{len(cat)}**")
    lines.append("")
    lines.append("## CAVEAT (read before citing these numbers)")
    lines.append("")
    lines.append("This is a **deterministic screening**, not a verdict of correctness.")
    lines.append("")
    lines.append("- **ACCEPT** means the stored title contains the exact binomial or a registered common "
                 "name. It does not prove the paper is substantively about this species.")
    lines.append("- **REVIEW / REJECT** means no lexical species signal was found in the stored title. "
                 "These are candidates that **need Crossref resolution (ISC-5) plus a human check**, "
                 "**not** bindings proven wrong. A genuine paper that names the species only in its "
                 "abstract, or under an unregistered synonym, is under-counted here.")
    lines.append("- **Recall is bounded by common-name coverage.** The map is built from the "
                 "standardization report, the prompt headers, and each file's embedded common name. "
                 "Gaps in that map lower ACCEPT counts without implying a bad binding.")
    lines.append("- The gate is deliberately conservative: **bare genus never ACCEPTs** (it routes to "
                 "REVIEW), which is what defeats the *Falco* / *Balaenoptera* / *Eubalaena* congener "
                 "false-positive. It errs toward REVIEW, never toward a false live binding.")
    lines.append("")
    lines.append("## Catastrophic all-REJECT species")
    lines.append("")
    if cat:
        lines.append("Species where **zero** stored references carry any lexical species signal. These are "
                     "the theme-drift casualties (retrieval matched a section keyword, not the species) "
                     "and are the first-priority human re-curation targets.")
        lines.append("")
        lines.append("| Species | Common name | Candidates | REJECT | REVIEW |")
        lines.append("|---|---|---:|---:|---:|")
        for r in sorted(cat, key=lambda r: -r["candidates"]):
            lines.append(f"| *{r['species']}* | {r['common']} | {r['candidates']} | "
                         f"{r['REJECT']} | {r['REVIEW']} |")
    else:
        lines.append("None.")
    lines.append("")
    lines.append("## Per-species (worst-first)")
    lines.append("")
    lines.append("| Species | Common name | Candidates | ACCEPT | REVIEW | REJECT | Accept % |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        lines.append(f"| *{r['species']}* | {r['common']} | {r['candidates']} | {r['ACCEPT']} | "
                     f"{r['REVIEW']} | {r['REJECT']} | {_pct(r['ACCEPT'], r['candidates'])} |")
    lines.append("")
    return "\n".join(lines)


def _pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


def main() -> None:
    result = audit()
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(result), encoding="utf-8")
    t = result["totals"]
    print(f"Species audited      : {result['species_count']}")
    print(f"Candidate references : {t['candidates']}")
    print(f"  ACCEPT             : {t['ACCEPT']} ({_pct(t['ACCEPT'], t['candidates'])})")
    print(f"  REVIEW             : {t['REVIEW']} ({_pct(t['REVIEW'], t['candidates'])})")
    print(f"  REJECT             : {t['REJECT']} ({_pct(t['REJECT'], t['candidates'])})")
    print(f"Catastrophic all-REJECT species: {len(result['catastrophic'])}")
    for r in sorted(result["catastrophic"], key=lambda r: -r["candidates"]):
        print(f"    - {r['species']} ({r['common']}): {r['candidates']} refs, all REJECT/REVIEW")
    print(f"Report written       : {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
