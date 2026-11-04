#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-14
"""V-25: the deposit must describe what the pipeline currently produces.

WHY THIS EXISTS
---------------
The deposit is the version of record — the thing a reader is given and the thing
the manuscript describes. It is built by ingest/build_deposit.py from the
artefacts on disk, which means it is a snapshot, and a snapshot goes stale silently.

On 2026-08-14 six of the seven Source Data tables in `deposit/source_data.zip`
differed from the ones the pipeline had just produced. Two figures had been
corrected that day: Figure 1's appendix panel had been counting each species'
whole history under its current listing, and Figure 7 had been asserting a
hardcoded 93.3% where its own data said 83.6%. Both fixes landed in the working
tree. Neither reached the deposit, because nothing rebuilt it and nothing noticed.

Every other deposit gate passed throughout. V-14 loads the deposited CSVs into
the deposited schema and they load; V-19 runs the deposited scripts and they run;
the manifest digests match, because the manifest is built from the same stale
files. A snapshot is perfectly self-consistent. That is exactly what makes this
invisible: the deposit was internally correct and externally out of date.

WHAT IT ASSERTS
---------------
Every Source Data file inside the deposit is byte-identical to the live one it
was built from. Nothing about whether either is right — only that a reader
holding the deposit is holding the figures we currently believe in.

If this fails the fix is always the same: rebuild the deposit (ingest/build_deposit.py).
"""
from __future__ import annotations

import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).parent.parent
DEPOSIT_ZIP = ROOT / "deposit" / "source_data.zip"
LIVE = ROOT / "visualizations" / "source_data"


def main() -> int:
    if not DEPOSIT_ZIP.exists():
        print(f"V-25 CANNOT RUN: {DEPOSIT_ZIP.name} is absent. Rebuild the deposit (ingest/build_deposit.py).")
        return 2
    if not LIVE.is_dir():
        print(f"V-25 CANNOT RUN: {LIVE} is absent. Generate the figures first.")
        return 2

    stale: list[str] = []
    missing: list[str] = []
    orphan: list[str] = []
    examined = 0

    with zipfile.ZipFile(DEPOSIT_ZIP) as zf:
        deposited = {pathlib.Path(n).name: n
                     for n in zf.namelist() if n.endswith(".csv")}
        if not deposited:
            # Silence must not pass: an empty zip would compare nothing and
            # report that the deposit is current.
            print("V-25 CANNOT RUN: the deposit ships no Source Data CSVs at all.")
            return 2

        for name, member in sorted(deposited.items()):
            live_file = LIVE / name
            if not live_file.exists():
                orphan.append(name)
                continue
            examined += 1
            if zf.read(member) != live_file.read_bytes():
                stale.append(name)

    for live_file in sorted(LIVE.glob("*.csv")):
        if live_file.name not in deposited:
            missing.append(live_file.name)

    print(f"V-25 deposit currency: EXAMINED {examined} Source Data file(s) "
          f"against the live pipeline output")

    problems = (len(stale) + len(missing) + len(orphan))
    if problems:
        print(f"\nV-25 FAIL: the deposit does not match what the pipeline "
              f"produces ({problems} problem(s)):\n")
        for n in stale:
            print(f"  stale:   {n} differs from the live file")
        for n in missing:
            print(f"  absent:  {n} exists live but is not in the deposit")
        for n in orphan:
            print(f"  orphan:  {n} is deposited but no longer produced")
        print("\nEvery other deposit gate can pass on a stale deposit: a snapshot")
        print("is internally consistent with itself, manifest digests included.")
        print("Rebuild the deposit (ingest/build_deposit.py).")
        return 1

    if examined == 0:
        print("\nV-25 FAIL: nothing was compared, so this would pass for free.")
        return 1

    print(f"\nV-25 PASS: every deposited Source Data file is byte-identical to "
          f"the pipeline's current output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
