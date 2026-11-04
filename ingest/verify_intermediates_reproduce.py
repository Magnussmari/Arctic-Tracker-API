#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-15
"""V-29: every figure intermediate must reproduce byte for byte when re-run.

WHY THIS EXISTS
---------------
A regeneration of an intermediate such as data/processed/iucn_historic_timeline.json
should be a no-op. Serialising a Python set of strings straight to JSON (for
example `list({a["status"] for a in rows})`) breaks that, because Python
randomises string-set iteration per process, so the file would differ between
runs on the same data.

The figure gate cannot see this: it compares Source Data, which is downstream
of sorting in the Source Data writers. The intermediates sit between the
database and that sort, so this check regenerates them twice and compares.

WHAT IT ASSERTS
---------------
Each intermediate is generated twice in a row and the two digests match. Nothing
about correctness: an intermediate can be perfectly reproducible and wrong. It
asserts only that the pipeline gives the same answer twice, which the paper
claims when it says every figure is computed deterministically from the Stage 1
corpus.

Each artefact is put back byte for byte afterwards, whatever the outcome. The
committed intermediates are the frozen inputs the published figures were drawn
from; regenerating them from the live database is a test, not a release. On
2026-10-07 a suite run left all four rewritten from the current database (a
bowhead priority and the analysis date among them), and only a dirty tree said so.

Timestamps are excluded before hashing, because a generated_date that changes
daily is a legitimate difference and would make this gate cry wolf until it was
ignored.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/verify_intermediates_reproduce.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PY = str(ROOT / ".venv" / "bin" / "python")
DP = ROOT / "visualizations" / "data_processing"

# generator -> the artefact it writes
INTERMEDIATES = [
    ("generate_iucn_timeline_pg.py", "data/processed/iucn_historic_timeline.json"),
    ("export_cites_effectiveness_pg.py", "data/raw/1_DATA_cites_effectiveness.json"),
    ("analyze_iwt_seizures_pg.py", "data/exports/iwt_seizures_analysis.json"),
    ("analyze_wild_origin_trade_pg.py", "data/exports/wild_origin_trade_analysis.json"),
]

# Fields that legitimately differ between two runs seconds apart.
VOLATILE = re.compile(r"(generated|built|analysis|created|run)_?(date|utc|at|on)?$", re.I)


def stable_digest(path: Path) -> str:
    """Digest with volatile top-level metadata removed."""
    try:
        data = json.loads(path.read_text())
    except (ValueError, OSError):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    # Recursive, not top-level. 1_DATA_cites_effectiveness.json carries its
    # analysis_date inside "metadata", so a top-level strip left it in the
    # digest and a run crossing midnight would have failed for the wrong
    # reason — the gate would have been right by luck until the one night it
    # was not.
    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if not VOLATILE.match(k)}
        if isinstance(node, list):
            return [strip(x) for x in node]
        return node

    data = strip(data)
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main() -> int:
    if not os.environ.get("ARCTIC_DATABASE_URL"):
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1

    unstable: list[str] = []
    broken: list[str] = []
    examined = 0

    # The frozen artefacts, kept so the gate leaves the tree as it found it.
    originals = {rel: (ROOT / rel).read_bytes() if (ROOT / rel).exists() else None
                 for _, rel in INTERMEDIATES}
    try:
        examined = _regenerate_twice(unstable, broken)
    finally:
        for rel, body in originals.items():
            art = ROOT / rel
            if body is None:
                art.unlink(missing_ok=True)
            else:
                art.write_bytes(body)
    not_restored = [rel for rel, body in originals.items()
                    if body is not None and (ROOT / rel).read_bytes() != body]
    if not_restored:
        broken.append(f"could not put back {', '.join(not_restored)}")
    return _report(examined, unstable, broken)


def _regenerate_twice(unstable: list[str], broken: list[str]) -> int:
    examined = 0
    for generator, rel in INTERMEDIATES:
        gen = DP / generator
        art = ROOT / rel
        if not gen.exists():
            broken.append(f"{generator} is absent, so {rel} cannot be re-derived")
            continue

        digests = []
        for _ in range(2):
            r = subprocess.run([PY, str(gen)], capture_output=True, text=True,
                               cwd=str(ROOT), timeout=900)
            if r.returncode != 0:
                broken.append(f"{generator} exited {r.returncode}: "
                              f"{(r.stderr or r.stdout).strip().splitlines()[-1][:90]}")
                break
            if not art.exists():
                broken.append(f"{generator} ran but did not write {rel}")
                break
            digests.append(stable_digest(art))
        else:
            examined += 1
            if digests[0] != digests[1]:
                unstable.append(f"{rel}: {digests[0][:16]} then {digests[1][:16]}")
            else:
                print(f"  reproduces  {rel}  ({digests[0][:16]})")
    return examined


def _report(examined: int, unstable: list[str], broken: list[str]) -> int:
    print(f"\nV-29 intermediate reproducibility: EXAMINED {examined} of "
          f"{len(INTERMEDIATES)} intermediate(s), generated twice each")

    if broken or unstable:
        print("\nV-29 FAIL:")
        for b in broken:
            print(f"  {b}")
        for u in unstable:
            print(f"  DOES NOT REPRODUCE  {u}")
        if unstable:
            print("\nThe usual cause is a set or dict serialised without sorting:")
            print("Python randomises string-set iteration per process, so the file")
            print("differs on the same machine from the same data. Downstream checks")
            print("miss it when the Source Data writers sort their own output.")
        return 1

    if examined == 0:
        print("V-29 FAIL: nothing was regenerated, so this would pass for free.")
        return 1

    print(f"V-29 PASS: every intermediate gives the same answer twice. This does "
          f"not establish that any of them is the right answer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
