#!/usr/bin/env python3
"""Every Supplementary Table the manuscript cites must be accounted for.

A reader who follows the Data Availability statement goes looking for the
tables the paper cites. Some cited tables are deposited and some are held by
the authors, and the README is where the difference is documented.

So this does not ask whether the files exist. It asks whether every cited
table is either deposited or deliberately named as author-held, and it reads
the README for the second half of that because an undocumented absence and a
documented one are different things.

The manuscript itself is not part of the public release. Set
ARCTIC_MANUSCRIPT_DOCX to a copy of it, and ARCTIC_LIVE_TEXT_DIR to the
directory holding the live_text helper that strips tracked deletions; without
both, the check reports that it was skipped.

Exit 0 accounted for, 1 not, 3 unmeasured (including skipped).
"""
import os, pathlib, re, sys, zipfile
# Importing a sibling here writes __pycache__ INTO the deposit, and
# verify_deposit_accounted.py rejects bytecode in a citable archive. Running
# these scripts in place is the intended use, so the run must not leave
# residue behind, or the archive gate would fail merely because the verifiers
# had been run.
sys.dont_write_bytecode = True

HERE = pathlib.Path(__file__).resolve().parent
DEPOSIT = HERE.parent
REPO = DEPOSIT.parent
_DOCX_ENV = os.environ.get("ARCTIC_MANUSCRIPT_DOCX")
DOCX = pathlib.Path(_DOCX_ENV) if _DOCX_ENV else None
_LIVE_ENV = os.environ.get("ARCTIC_LIVE_TEXT_DIR")
LIVE_TEXT_DIR = pathlib.Path(_LIVE_ENV) if _LIVE_ENV else None
README = DEPOSIT / "supplementary" / "README.md"
SUPP = DEPOSIT / "supplementary"


def cited():
    sys.path.insert(0, str(LIVE_TEXT_DIR))
    import live_text
    raw = zipfile.ZipFile(DOCX).read("word/document.xml").decode("utf8")
    live = live_text.live_text(raw)
    return sorted({int(n) for n in re.findall(r"Supplementary Table (\d+)", live)})


def deposited():
    found = {}
    for f in SUPP.glob("supplementary_table_*"):
        m = re.search(r"supplementary_table_(\d+)_", f.name)
        if m:
            found.setdefault(int(m.group(1)), []).append(f.name)
    # Table 5 is the traceability file, which lives one level up under its own
    # name. The README says so; this reads the README rather than hardcoding it.
    txt = README.read_text()
    for m in re.finditer(r"Supplementary Table (\d+)\*\* — [^\n]*`\.\./([^`]+)`", txt):
        if (DEPOSIT / m.group(2)).is_file():
            found.setdefault(int(m.group(1)), []).append(m.group(2))
    return found


def author_held():
    txt = README.read_text()
    section = txt.split("## Not derivable, and why", 1)
    if len(section) < 2:
        return set()
    # a table that has "moved up" is no longer author-held, whatever the
    # section it is still described in
    out = set()
    for m in re.finditer(r"\*\*Supplementary Table (\d+)\*\* — (.{0,120})",
                         section[1], re.S):
        if "was listed here" in m.group(2):
            continue
        out.add(int(m.group(1)))
    return out


def self_test():
    assert re.findall(r"Supplementary Table (\d+)", "see Supplementary Table 7.") \
        == ["7"], "the citation pattern does not match"
    assert not re.findall(r"Supplementary Table (\d+)", "see Table 7"), \
        "the pattern matches a plain table"
    print("  self-test: PASS (citations parse, plain tables are not citations)")


def main():
    self_test()
    if DOCX is None or LIVE_TEXT_DIR is None:
        print("  skipped: the manuscript is not part of the public release "
              "(set ARCTIC_MANUSCRIPT_DOCX and ARCTIC_LIVE_TEXT_DIR to run this check).")
        return 3
    if not DOCX.is_file() or not README.is_file():
        print("  UNMEASURED: the manuscript or the supplementary README is not "
              "in this checkout, so nothing was compared.")
        return 3
    want, have, held = cited(), deposited(), author_held()
    print(f"  manuscript cites {len(want)}: {', '.join(map(str, want))}")
    print(f"  deposit holds    {len(have)}: {', '.join(map(str, sorted(have)))}")
    print(f"  author-held      {len(held)}: {', '.join(map(str, sorted(held)))}")

    faults = []
    for n in want:
        if n in have:
            continue
        if n in held:
            print(f"    Table {n}: not deposited, and the README says why")
            continue
        faults.append(f"Supplementary Table {n} is cited by the manuscript, is "
                      f"not in the deposit, and the README does not say why")
    for n in sorted(set(have) & held):
        faults.append(f"Supplementary Table {n} is deposited and the README "
                      f"still lists it as needing an author")
    for n in sorted(set(have) - set(want)):
        faults.append(f"Supplementary Table {n} is deposited and the "
                      f"manuscript never cites it")

    if not faults:
        print("\nPASS: every cited table is deposited or named as author-held.")
        return 0
    print(f"\nFAIL: {len(faults)} unaccounted table(s).")
    for f in faults:
        print(f"  {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
