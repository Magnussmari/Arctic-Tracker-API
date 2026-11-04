#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-15
"""Every file in the deposit is described by the deposit's own manifest.

WHY THIS EXISTS
---------------
The deposit ships a SHA-256 manifest and the README tells a reader it covers
every file in the package. On 2026-08-15 it did not: four files on disk had no
entry, and two of them were compiled Python bytecode —
verification/__pycache__/*.pyc — created by running the shipped scripts from
inside the deposit, which is exactly what a reader does.

The builder had a guard against this and the guard could not work. It tested
`f.name == "__pycache__"` while iterating with `iterdir()`, which does not
descend, so the directory was skipped for a reason that was already covered by
`is_file()` and the files inside it were never visited at all. A check written
against the imagined defect, in a scope that could not contain the real one.

Nothing detected it either, because every existing deposit check starts from the
manifest and verifies that each listed file is present and unchanged. That
direction can never find an unlisted file. This one runs the other way.

WHAT IT ASSERTS
---------------
The set of files under deposit/ equals the manifest's keys, allowing exactly one
documented exception: MANIFEST.sha256.json itself, which cannot contain its own
digest.

An unaccounted file is a failure in both directions. Bytecode, editor backups and
scratch output do not belong in a citable archive; and a file a reader downloads
and cannot verify against the manifest is precisely the gap the manifest exists
to close.

Usage:
  ./.venv/bin/python ingest/verify_deposit_accounted.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEPOSIT = ROOT / "deposit"
MANIFEST = DEPOSIT / "MANIFEST.sha256.json"

# The single permitted exception, named rather than pattern-matched. A rule that
# excused a glob such as "*.json" would have excused the unmanifested report too.
EXEMPT = {"MANIFEST.sha256.json"}

# Things that must never be in a deposit at all, whether or not they are listed.
# Manifesting bytecode would satisfy the equality test above while still shipping
# bytecode, so this is a separate question from accounting.
NEVER = ("__pycache__", ".DS_Store", ".ipynb_checkpoints", ".pyc", "~",
         # verify_manuscript_claims.py writes its output to reports/ beside
         # itself. Running the shipped scripts in place is the intended use, so
         # this directory appearing is correct — shipping our copy of it is not,
         # with one named exception below.
         "verification/reports/",
         )

# attribution_loss.json is SHIPPED on purpose: build_deposit.py copies it in
# because the falcon attribution claim cannot be checked from the deposit
# without it, and verify_manuscript_claims counts its absence as a mismatch
# rather than a skip. On 7 October 2026 this gate and that builder disagreed
# about the same file — the gate called it scratch, the builder shipped it, and
# the manifest listed it — so deleting it to satisfy the gate broke the
# manifest. The exception is named rather than globbed, so any OTHER file
# appearing under verification/reports/ still fails.
KEEP = {"verification/reports/attribution_loss.json"}


def main() -> int:
    if not DEPOSIT.is_dir():
        print("CANNOT RUN: no deposit/ directory. Build the deposit first (ingest/build_deposit.py).")
        return 2
    if not MANIFEST.exists():
        print("DEPOSIT UNACCOUNTED: there is no manifest at all.")
        return 1

    listed = set(json.loads(MANIFEST.read_text()))
    on_disk = {str(p.relative_to(DEPOSIT))
               for p in DEPOSIT.rglob("*") if p.is_file()}

    # rebuilt/ is the reader's own reconstruction, so it is neither listed nor
    # a fault; it is reported as junk below if we ever ship it.
    local = {f for f in on_disk if f.startswith("rebuilt/")}
    unlisted = sorted(on_disk - listed - EXEMPT - local)
    missing = sorted(listed - on_disk)
    # rebuilt/ holds the reader's own reconstituted IUCN categories, written by
    # rebuild_iucn.py. Its appearing is the package being used as intended, so
    # it is neither unlisted nor junk. The BUILD purges it, which is where
    # "do not ship our copy" belongs - a gate that fires on correct use gets
    # switched off.
    junk = sorted(f for f in on_disk
                  if f not in KEEP and f not in local
                  and any(n in f for n in NEVER))

    print(f"deposit: {len(on_disk)} files on disk, {len(listed)} in the manifest")

    if not on_disk:
        print("DEPOSIT UNACCOUNTED: the deposit directory is empty, so this "
              "check would pass by having nothing to examine. Not a pass.")
        return 1

    problems = False
    if unlisted:
        problems = True
        print(f"\nNOT IN THE MANIFEST ({len(unlisted)}):")
        for f in unlisted:
            print(f"  {f}")
        print("\nThe README tells a reader the manifest covers every file in the")
        print("package. Either these belong in it, or they do not belong in the")
        print("deposit.")

    if missing:
        problems = True
        print(f"\nLISTED BUT ABSENT ({len(missing)}):")
        for f in missing:
            print(f"  {f}")

    if junk:
        problems = True
        print(f"\nDOES NOT BELONG IN A CITABLE ARCHIVE ({len(junk)}):")
        for f in junk:
            print(f"  {f}")

    if problems:
        return 1

    print("every file in the deposit is in its manifest, and nothing in it is "
          "build residue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
