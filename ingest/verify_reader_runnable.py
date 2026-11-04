#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-14
"""V-19: every script we ship must run for someone who has only the deposit.

WHY THIS EXISTS
---------------
On 2026-08-13 four verification scripts were added to the deposit with the claim
that a reader holding only that package could run them. Nobody tried it. Three of
the four were broken:

  - one imported a module that was not shipped (ModuleNotFoundError);
  - one computed the deposit path as ROOT/deposit, which is right from the
    repository and wrong from inside the deposit;
  - one hardcoded the schema name, so it would check our database or none.

The fourth worked. That ratio is the reason this exists: the promise was made in
a commit message and a README, and neither can fail.

WHAT IT ASSERTS
---------------
That every shipped script RUNS. Not that it passes: pointed at a deposit-only
database, several will legitimately report that they cannot complete, because two
tables are withheld for licence reasons and are therefore empty. Reporting that
clearly is correct behaviour and is what a reader needs.

The failure this catches is a Python traceback — an import that is not there, a
path that does not resolve, a schema name that does not exist. A script that
reaches a verdict is working as shipped. A script that dies before reaching one
was never really shipped.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/verify_reader_runnable.py
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

import psycopg2

ROOT = pathlib.Path(__file__).parent.parent
DEPOSIT = ROOT / "deposit"
PY = ROOT / ".venv" / "bin" / "python"
PROBE = "arctic_reader_probe"

# The signature of a script that did not survive being shipped.
CRASH = re.compile(
    r"Traceback \(most recent call last\)|"
    r"ModuleNotFoundError|ImportError|"
    r"FileNotFoundError|IsADirectoryError|NotADirectoryError|"
    r"UndefinedTable|UndefinedColumn|InvalidSchemaName|"
    r"NameError|AttributeError|TypeError|KeyError")


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1

    verif = DEPOSIT / "verification"
    schema_sql = DEPOSIT / "schema.sql"
    tables = DEPOSIT / "tables"
    for f in (verif, schema_sql, tables):
        if not f.exists():
            print(f"V-19 FAIL: the deposit has no {f.name}. Rebuild the deposit (ingest/build_deposit.py).")
            return 1

    # Modules the scripts import are shipped so the scripts work; they are not
    # themselves things a reader runs, and judging them by whether they print a
    # verdict would be judging a header file for having no output.
    MODULES = {"db.py", "redlist_scale.py"}
    scripts = sorted(p for p in verif.glob("*.py") if p.name not in MODULES)
    if not scripts:
        # Silence must not satisfy this: an empty verification directory would
        # otherwise run nothing and report that everything works.
        print("V-19 FAIL: the deposit ships no verification scripts at all.")
        return 1

    conn = psycopg2.connect(url, connect_timeout=60)
    conn.autocommit = True
    results: list[tuple[str, bool, str]] = []
    try:
        with conn.cursor() as cur:
            cur.execute(f"drop schema if exists {PROBE} cascade")
            probe_sql = re.sub(r"\barctic_v2\b", PROBE, schema_sql.read_text())
            cur.execute(probe_sql)
            cur.execute("set session_replication_role = replica")
            for csv_file in sorted(tables.glob("*.csv")):
                with open(csv_file) as fh:
                    header = fh.readline().strip()
                    fh.seek(0)
                    cur.copy_expert(
                        f"copy {PROBE}.{csv_file.stem} ({header}) "
                        f"from stdin with csv header", fh)
            cur.execute("set session_replication_role = origin")

        env = dict(os.environ)
        env["ARCTIC_SCHEMA"] = PROBE
        for script in scripts:
            # Only pass flags the script actually declares. attribution_loss.py
            # takes a positional path, so handing it --schema made it try to
            # open a file called "--schema" — a crash caused by this gate rather
            # than by the script, which would have been a false accusation.
            source = script.read_text()
            args = [str(PY), script.name]
            if "--schema" in source:
                args += ["--schema", PROBE]
            # The 4.2 GB shard re-read is not what is under test here, and it
            # pushes the whole gate past ten minutes, which is how a check stops
            # being run.
            if "--skip-trade" in source:
                args.append("--skip-trade")
            try:
                r = subprocess.run(
                    args, cwd=str(verif), capture_output=True, text=True,
                    timeout=900, env=env)
                output = (r.stdout or "") + (r.stderr or "")
            except subprocess.TimeoutExpired:
                results.append((script.name, False, "timed out"))
                continue
            needs_input = re.search(r"usage: \S+ <", output)
            if needs_input and not CRASH.search(output.replace(needs_input.group(0), "")):
                results.append((script.name, True,
                                "needs an argument; prints its usage rather than crashing"))
                continue
            # The exit code is evidence this gate was throwing away. A script
            # that dies on an unhandled exception exits 1 with a traceback, but
            # one that exits non-zero while printing nothing at all is equally
            # useless to a reader and matched no pattern here. V-18 called this
            # oracle weak and was right about the substance if not the label.
            if r.returncode not in (0, 1, 2, 3) or (
                    r.returncode != 0 and not output.strip()):
                results.append((script.name, False,
                                f"exited {r.returncode} with "
                                f"{'no output at all' if not output.strip() else 'an unexpected code'}"))
                continue
            crash = CRASH.search(output)
            if crash:
                line = next((l.strip() for l in reversed(output.splitlines())
                             if l.strip()), "")
                results.append((script.name, False, f"{crash.group(0)}: {line[:70]}"))
            else:
                # Look from the end: these scripts print a table first and their
                # conclusion last, so the first matching line was a column header.
                verdict = next(
                    (l.strip() for l in reversed(output.splitlines())
                     if re.search(r"\b(PASS(ED)?|FAIL(ED)?|CANNOT RUN|NOT RUN)\b"
                                  r"|\d+ of \d+|cannot be checked", l)),
                    "ran, but printed no line stating an outcome")
                results.append((script.name, True, verdict[:78]))
    finally:
        with conn.cursor() as cur:
            cur.execute(f"drop schema if exists {PROBE} cascade")
        conn.close()

    ok = [r for r in results if r[1]]
    broken = [r for r in results if not r[1]]

    print(f"V-19 reader runnability: {len(results)} shipped script(s), run against a "
          f"database built from the deposit alone\n")
    for name, good, detail in results:
        print(f"  {'runs   ' if good else 'BROKEN '} {name:32s} {detail}")

    if broken:
        print(f"\nV-19 FAIL: {len(broken)} shipped script(s) do not run for a reader.")
        print("Reaching a verdict is the bar, not passing. These did not reach one.")
        return 1

    print(f"\nV-19 PASS: all {len(ok)} shipped scripts run and reach a verdict. "
          f"Several report that they cannot complete, which is correct: the deposit "
          f"withholds two tables for licence reasons and says so.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
