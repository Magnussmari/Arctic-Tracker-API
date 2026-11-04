#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-10-01
"""Sign files ADDED to the deposit, without re-freezing the version of record.

WHY THIS EXISTS
---------------
check_deposit_clean reports unsigned files in the deposit and says, correctly,
that a file which belongs there has to be signed, "which means rebuilding the
manifest deliberately rather than letting a file arrive by running something".

The only tool for that was ingest/build_deposit.py, and it re-exports every
table from the live database. The database has moved since the snapshot was
frozen: the manifest records 2,606 seizure-source records consumed and the
corpus holds 2,642 today. Running the full build to add a LICENSE file would
therefore have silently re-frozen the paper's version of record on today's data,
changing the binding of every reported number, as a side effect of a licensing
fix. That is the opposite of what a version of record is for.

So this adds, and only adds. It refuses if a file that is already signed has
changed on disk, because that is a re-freeze wearing an addition's clothes, and
it refuses to touch deposit/tables/ at all: a table change is a real rebuild and
has to be one.

WHAT A READER SEES
------------------
The manifest gains the new entries, and deposit/ADDITIONS.json gains a record
naming the date, the files and the reason. A reviewer comparing two manifests
can see exactly what was added after the freeze and what was not touched, rather
than being handed a wholly new set of digests and asked to trust that only one
thing moved.

The record lives in its own file rather than under a `_additions` key inside the
manifest, and that is not a preference. Twenty-odd readers across three
repositories treat every manifest key as a path to a file, and the app's
sync-deposit script refused outright when a metadata key appeared there. The
manifest is a map from path to digest and stays one; ADDITIONS.json is a file
like any other and is signed like any other.
"""
import csv, hashlib, json, os, pathlib, sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
DEPOSIT = HERE.parent / "deposit"
MANIFEST = DEPOSIT / "MANIFEST.sha256.json"
ADDITIONS = DEPOSIT / "ADDITIONS.json"
FROZEN_PREFIX = "tables/"

# NEVER signed, whatever is named. deposit/rebuilt/ holds what a READER produces
# by running rebuild_iucn.py against their own IUCN licence: the Red List
# categories this deposit exists to withhold. On 6 October this signer swept six
# of them into the manifest as ordinary additions, because they are files in the
# deposit directory and nothing said otherwise. A signed file is deposit content,
# and deposit content carrying a withheld category is the one thing that must
# never ship. They are gitignored, which kept them out of history and would not
# have kept them out of a zip of this directory.
NEVER_SIGN = ("rebuilt/",)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def entry(path):
    """One manifest entry: bytes, sha256, and for a CSV its row count.

    build_deposit.py records `rows` for every table it exports, and the app's
    deposit-freshness test holds the manifest to it: a CSV entry without a row
    count is a manifest that was REWRITTEN rather than re-signed, which is the
    shape a hand-edited manifest has. This signer did not record it, so every
    CSV it added failed that test - two of them on 6 October, the IUCN
    assessment identifiers and the timeline events.

    The row count is read off the file, so adding it to an existing entry
    changes no digest and re-freezes nothing.
    """
    e = {"bytes": path.stat().st_size, "sha256": digest(path)}
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf8") as fh:
            e["rows"] = max(0, sum(1 for _ in csv.reader(fh)) - 1)
    return e


def walk(root):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel == MANIFEST.name or "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        yield rel, p


def self_test():
    """Prove the two refusals fire before trusting a run that does not refuse."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        (d / "a.txt").write_text("one")
        man = {"a.txt": {"bytes": 3, "sha256": digest(d / "a.txt")}}
        changed, added, frozen = classify(d, man)
        assert not changed and not added, "SELF-TEST: a clean deposit looked dirty"
        (d / "a.txt").write_text("TWO")
        changed, added, frozen = classify(d, man)
        assert changed == ["a.txt"], f"SELF-TEST: a changed signed file was not seen ({changed})"
        (d / "tables").mkdir()
        (d / "tables" / "x.csv").write_text("id\n1\n")
        (d / "new.txt").write_text("hello")
        changed, added, frozen = classify(d, man)
        assert added == ["new.txt"], f"SELF-TEST: the addition was not seen ({added})"
        assert frozen == ["tables/x.csv"], \
            f"SELF-TEST: a new file under tables/ was not refused ({frozen})"
    print("  self-test: PASS (changed, added and frozen-area files are each seen)",
          file=sys.stderr)


def classify(root, manifest):
    changed, added, frozen = [], [], []
    for rel, p in walk(root):
        if any(rel.startswith(x) for x in NEVER_SIGN):
            continue
        if rel in manifest:
            if digest(p) != manifest[rel]["sha256"]:
                changed.append(rel)
        elif rel.startswith(FROZEN_PREFIX):
            frozen.append(rel)
        else:
            added.append(rel)
    return changed, added, frozen


def main():
    self_test()
    reason = os.environ.get("DEPOSIT_ADDITION_REASON", "").strip()
    if not reason:
        print("  ABORT: set DEPOSIT_ADDITION_REASON to one sentence saying why these "
              "files belong in the deposit. An unexplained addition to a version of "
              "record is indistinguishable from drift.", file=sys.stderr)
        return 2
    if not MANIFEST.exists():
        print(f"  ABORT: {MANIFEST} is not here", file=sys.stderr)
        return 2
    # NEVER SIGN A LEAKING DEPOSIT. On 6 October this signer put its name on a
    # source_data.zip that had just been rebuilt from the pre-withholding files
    # and carried 436 Red List categories. Signing is the act that makes a file
    # deposit content, so it is the right place to ask whether the content may
    # be deposited at all.
    import subprocess
    gate = DEPOSIT / "verification" / "verify_iucn_withheld.py"
    if not gate.is_file():
        print(f"  ABORT: {gate} is not here, so this cannot sign anything "
              f"without asserting a withholding it did not check",
              file=sys.stderr)
        return 2
    r = subprocess.run([sys.executable, str(gate)], cwd=DEPOSIT.parent,
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()[-5:]
        print("  ABORT: the deposit carries withheld Red List categories; "
              "nothing is signed.\n    " + "\n    ".join(tail), file=sys.stderr)
        return 1
    print("  withholding verified before signing")

    manifest = json.loads(MANIFEST.read_text())
    stray = [k for k in manifest if k.startswith("_")]
    if stray:
        print(f"  ABORT: the manifest carries non-path keys {stray}. Readers across "
              f"three repositories treat every key as a file; metadata belongs in "
              f"{ADDITIONS.name}.", file=sys.stderr)
        return 2
    entries = dict(manifest)

    changed, added, frozen = classify(DEPOSIT, entries)

    # A signed file that changed is refused by default. It can be re-signed only
    # by being named, one path at a time, in DEPOSIT_RESIGN: naming it is the
    # deliberate act check_deposit_clean asks for, and anything NOT named still
    # stops the run. A table is never eligible, whatever is named.
    allowed = {x.strip() for x in os.environ.get("DEPOSIT_RESIGN", "").split(",")
               if x.strip()}
    bad_allow = sorted(x for x in allowed if x.startswith(FROZEN_PREFIX))
    if bad_allow:
        print(f"  ABORT: DEPOSIT_RESIGN names {bad_allow}, which are corpus. A table "
              f"is re-signed by rebuilding the deposit, never by naming it here.",
              file=sys.stderr)
        return 2
    unknown = sorted(x for x in allowed if x not in changed)
    if unknown:
        print(f"  ABORT: DEPOSIT_RESIGN names {unknown}, which did not change. "
              f"Naming a file that did not move means the run was aimed at a "
              f"different state than the one on disk.", file=sys.stderr)
        return 2
    resigned = [r for r in changed if r in allowed]
    changed = [r for r in changed if r not in allowed]

    # RETIRED: a signed path whose file is gone. Added 18 October 2026, when
    # the manuscript's new Figure 5 renumbered the journal figures and their
    # builders were renamed with git mv. This signer only ever added, so the
    # old names stayed in the manifest pointing at nothing, and the digest
    # verifier is right to fail on that. A path leaves the manifest only by
    # being named in DEPOSIT_RETIRE, only if its file is really absent, never
    # under tables/, and the removal is recorded beside the additions. An
    # absent signed file that is NOT named still stops the run.
    retire = sorted({x.strip() for x in os.environ.get("DEPOSIT_RETIRE", "").split(",")
                     if x.strip()})
    gone = sorted(k for k in entries if not (DEPOSIT / k).exists()
                  and not any(k.startswith(x) for x in NEVER_SIGN))
    bad = [x for x in retire if x.startswith(FROZEN_PREFIX) or x not in gone]
    if bad:
        print(f"  ABORT: DEPOSIT_RETIRE names {bad}, which are corpus, unsigned, or "
              f"still on disk. Only a signed file that is gone can be retired.",
              file=sys.stderr)
        return 2
    unnamed = [k for k in gone if k not in retire]
    if unnamed:
        print("  ABORT: these signed files are gone from disk and are not named in "
              "DEPOSIT_RETIRE, so the manifest would go on vouching for them:",
              file=sys.stderr)
        for r in unnamed:
            print(f"    {r}", file=sys.stderr)
        return 1

    if changed:
        print("  ABORT: these files are already signed and have changed on disk. "
              "That is a re-freeze, not an addition, and it has to go through "
              "ingest/build_deposit.py deliberately:", file=sys.stderr)
        for r in changed:
            print(f"    {r}", file=sys.stderr)
        return 1
    if frozen:
        print(f"  ABORT: unsigned files under {FROZEN_PREFIX}. A table is corpus, not "
              f"an addition; adding one here would let the snapshot grow without a "
              f"rebuild:", file=sys.stderr)
        for r in frozen:
            print(f"    {r}", file=sys.stderr)
        return 1
    if not added and not resigned and not retire:
        print("  nothing to add: every file in the deposit is already signed")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # The record is written BEFORE the manifest, so its own digest is signed with
    # everything else in the same pass. A record of a signing that is not itself
    # signed is a note, not provenance.
    history = json.loads(ADDITIONS.read_text()) if ADDITIONS.exists() else []
    record = {"date": stamp, "reason": reason, "added": added, "resigned": resigned}
    if retire:
        record["retired"] = retire
    history.append(record)
    ADDITIONS.write_text(json.dumps(history, indent=2) + "\n")
    if ADDITIONS.name not in added and ADDITIONS.name not in entries:
        added.append(ADDITIONS.name)
    elif ADDITIONS.name in entries and ADDITIONS.name not in resigned:
        resigned.append(ADDITIONS.name)

    for rel in retire:
        del manifest[rel]
    for rel in added + resigned:
        p = DEPOSIT / rel
        manifest[rel] = entry(p)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"  signed {len(added)} addition(s) and re-signed {len(resigned)} named "
          f"file(s); no table touched:", file=sys.stderr)
    for rel in added:
        print(f"    added     {rel}", file=sys.stderr)
    for rel in resigned:
        print(f"    re-signed {rel}", file=sys.stderr)
    for rel in retire:
        print(f"    retired   {rel}", file=sys.stderr)
    print(f"  recorded in ADDITIONS.json at {stamp}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
