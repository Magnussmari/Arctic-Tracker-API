#!/usr/bin/env python3
"""Run every verification in this directory and report what actually happened.

WHY THIS EXISTS
---------------
The deposit README says "every shipped script has been run against a database
built from the deposit alone". This entry point executes the whole set so that
the statement is checked by a run rather than by hand invocation of each script.

Running the set together exposed one defect in two files:
verify_manuscript_claims.py and verify_derived_truth.py treated Path(__file__).parent.parent as the
repository root when it is the deposit directory, so one crashed with
FileNotFoundError or under-counted its checks, and the other reported sources as
absent that were present. A crash and a wrong number look identical from outside
unless the scripts are run.

A script that fails because data it needs is legitimately absent is reported as
such and does not fail the run: a clone carries the code and not the 172 MB of
tables, and the report says so. A script that crashes always
fails, because a crash is never a legitimate outcome.

Usage:
  ARCTIC_DATABASE_URL=... python3 deposit/verification/run_all.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# db.py is a helper, not a verification. attribution_loss.py and the report
# generators take arguments and write artefacts rather than asserting.
# Excluded only if it CANNOT FAIL. A script that returns non-zero on a logical
# defect is a gate and belongs in the run; one that only derives and prints is a
# report and does not.
#
# coverage_report.py was on this list and should never have been. It is V-8, it
# returns 1 in four places, and it carries its own self-test asking "can this
# gate detect an undeclared table?" -- its whole job is to fail when a table
# exists that no verification decision covers, which makes it the gate that
# catches gaps in the other gates. Without it this entry point could report
# "9 passed, 0 failed" with V-8 never run.
#
# The other three stay, measured rather than assumed: trajectory_report.py is
# V-10 but returns 1 nowhere, redlist_scale.py is the scale the trajectory rule
# reads, and attribution_loss.py needs a species-list argument.
NOT_VERIFICATIONS = {"db.py", "run_all.py", "attribution_loss.py",
                     "trajectory_report.py", "redlist_scale.py"}

# Absent input is a different outcome from a broken check. These are the phrases
# the scripts themselves use when the data is not beside them.
MISSING_DATA = re.compile(
    r"not found at|source .* absent|no .* source files found|"
    r"could not find the deposit|ARCTIC_DATABASE_URL is not set", re.I)


def main() -> int:
    scripts = sorted(p for p in HERE.glob("*.py")
                     if p.name not in NOT_VERIFICATIONS)
    if not scripts:
        print("no verification scripts found beside this one")
        return 2

    if not os.environ.get("ARCTIC_DATABASE_URL"):
        print("ARCTIC_DATABASE_URL is not set; every check would report the "
              "same missing input and the run would say nothing.\n")
        # Which role, not just which variable. Run with a read-only role, most
        # checks fail with "permission denied"; run with an example connection
        # string that still carries a "<password>" placeholder, the error is an
        # invalid port. Neither error names the thing that is wrong. Set
        # ARCTIC_DATABASE_URL in the environment to a real credential. The suite needs more than read access because
        # verify_schema_applies and verify_deposit_roundtrip create a scratch
        # database and load the deposit into it.
        print("It must be a role that owns the database: two of these checks")
        print("CREATE DATABASE, and the rest read every table in the arctic_v2")
        print("schema. A read-only credential fails as 'permission denied',")
        print("which reads like a broken check rather than a wrong credential.\n")
        # What a reader restoring the deposit needs is the privilege to grant
        # themselves against their own restore.
        print("If you are restoring this deposit yourself: load schema.sql and")
        print("the tables into a database you own, and point ARCTIC_DATABASE_URL")
        print("at a role that owns it. The checks need CREATE DATABASE and read")
        print("access to every table in the schema; nothing here writes to your")
        print("data.")
        return 2

    passed, absent, failed, crashed = [], [], [], []
    width = max(len(p.stem) for p in scripts)

    for s in scripts:
        r = subprocess.run([sys.executable, str(s)], capture_output=True,
                           text=True, timeout=900)
        out = (r.stdout or "") + (r.stderr or "")
        tail = next((l for l in reversed(out.splitlines()) if l.strip()), "")
        if "Traceback (most recent call last)" in out:
            crashed.append((s.stem, next(
                (l for l in reversed(out.splitlines())
                 if re.match(r"^\w*(Error|Exception)", l)), tail)))
            state = "CRASH"
        elif r.returncode == 0:
            passed.append(s.stem)
            state = "PASS"
        elif r.returncode == 3 or MISSING_DATA.search(out):
            # Exit 3 is every script's "could not measure" (UNMEASURED,
            # skipped): an absent input, never a pass and never a failure.
            absent.append((s.stem, tail))
            state = "NO DATA"
        else:
            failed.append((s.stem, tail))
            state = "FAIL"
        print(f"  {s.stem:<{width}}  {state:<8} {tail[:72]}")

    print(f"\n{len(passed)} passed, {len(absent)} could not run for want of "
          f"data, {len(failed)} failed, {len(crashed)} crashed")

    for label, items in (("CRASHED", crashed), ("FAILED", failed)):
        if items:
            print(f"\n{label}:")
            for name, why in items:
                print(f"  {name}: {why[:100]}")

    if absent:
        print("\nCould not run for want of data (a clone carries the code, not "
              "the 172 MB of tables):")
        for name, why in absent:
            print(f"  {name}: {why[:100]}")

    if crashed or failed:
        print("\nA crash and a wrong number look the same from outside if "
              "nobody runs the thing.")
        return 1

    # SILENCE IS NOT A PASS.
    # Every check can report "could not run for want of data" -- a clone carries
    # the code, not the 172 MB of tables -- and with nothing crashed and nothing
    # failed this would return 0. A reader, or a CI job, reads 0 as "the deposit
    # verifies". It means the opposite: nothing was verified at all, and the
    # exit code was reporting the absence of bad news rather than the presence
    # of good news.
    if passed and absent:
        print(f"\nPARTIAL: {len(passed)} passed and {len(absent)} could not run. "
              "Exit 3: a partial run is not a full pass.")
        return 3

    if not passed:
        print("\nNOTHING RAN. Every check was skipped for want of data, so this")
        print("run proves nothing about the deposit. Exit 3 rather than 0: a")
        print("suite that verified nothing must not be readable as a pass.")
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
