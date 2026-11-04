#!/usr/bin/env python3
# @orchestrator: Magnus Smárason | smarason.is  @created: 2026-10-06
"""V-36: every recorded digest in the deposit's manifest matches the file on disk.

WHY THIS EXISTS
---------------
Nothing checked this, and on 6 October 2026 it cost hours of false confidence.
Three deposited files were edited that day - results_traceability.csv,
results_traceability.md and verification/verify_claims_offline.py, when the
claims C66 to C79 were added - and the manifest went on recording their previous
digests while every gate in the set passed.

It passed because the two checks that look at the manifest look past this:

  * V-14 (verify_deposit_roundtrip) reads the manifest but needs
    ARCTIC_DATABASE_URL, so it cannot run offline and in practice does not run;
  * verify_deposit_accounted compares the FILE LIST - every file on disk is in
    the manifest and nothing in the manifest is residue - and a stale digest
    passes it, because the file is present and listed.

So the package could claim a checksum for content it no longer had, which is the
one promise a checksummed manifest exists to make. The paper's Data Availability
statement says every headline figure "is verifiable against its manifest
checksum".

A digest check needs no database and no network: the manifest and the files are
the whole input. That it was missing is the finding; that it is cheap is why.

FIELD OF VIEW
-------------
The self-test proves the check can fail, by corrupting one byte of a temporary
file against its own recorded digest, and proves it passes when they agree.
A test proves nothing until it has proven its own field of view.

Exit 0 = every digest matches, 1 = a mismatch, 3 = unmeasured.
"""
import hashlib
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEPOSIT = ROOT / "deposit"
MANIFEST = DEPOSIT / "MANIFEST.sha256.json"
# The manifest cannot contain its own digest. Declared rather than skipped
# silently, which is the same reasoning verify_deposit_accounted records.
EXEMPT = {"MANIFEST.sha256.json"}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compare(manifest: dict, base: pathlib.Path):
    """-> (checked, mismatches, absent). Mismatch = digest or size disagrees."""
    checked, mismatches, absent = 0, [], []
    for name, rec in sorted(manifest.items()):
        if name in EXEMPT:
            continue
        f = base / name
        if not f.exists():
            absent.append(name)
            continue
        checked += 1
        digest, size = sha256_file(f), f.stat().st_size
        if digest != rec.get("sha256"):
            mismatches.append((name, "digest", rec.get("sha256", "")[:12],
                               digest[:12]))
        elif size != rec.get("bytes"):
            mismatches.append((name, "size", str(rec.get("bytes")), str(size)))
    return checked, mismatches, absent


def self_test() -> bool:
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d)
        f = base / "table.csv"
        f.write_text("a,b\n1,2\n")
        man = {"table.csv": {"bytes": f.stat().st_size, "sha256": sha256_file(f)}}
        checked, bad, absent = compare(man, base)
        if checked != 1 or bad or absent:
            print("SELF-TEST FAIL: an agreeing digest was reported as a mismatch")
            return False
        f.write_text("a,b\n1,3\n")          # same length, one byte different
        checked, bad, absent = compare(man, base)
        if len(bad) != 1 or bad[0][1] != "digest":
            print("SELF-TEST FAIL: a changed byte did not fire")
            return False
        man["ghost.csv"] = {"bytes": 1, "sha256": "0" * 64}
        checked, bad, absent = compare(man, base)
        if absent != ["ghost.csv"]:
            print("SELF-TEST FAIL: a listed file with nothing on disk was not seen")
            return False
    print("  self-test: PASS (an agreeing digest passes, one changed byte at the "
          "same length fires, and a listed file with no file on disk is reported)",
          file=sys.stderr)
    return True


def main() -> int:
    if not self_test():
        print("refusing to report from a checker that cannot see defects")
        return 2
    if not MANIFEST.exists():
        print(f"UNMEASURED: {MANIFEST.name} is not in the deposit.", file=sys.stderr)
        return 3

    manifest = json.loads(MANIFEST.read_text())
    checked, mismatches, absent = compare(manifest, DEPOSIT)

    print(f"V-36 manifest digests: EXAMINED {checked} of {len(manifest)} entry(ies)")

    if absent:
        print(f"\nV-36 FAIL: {len(absent)} entry(ies) have no file on disk:\n",
              file=sys.stderr)
        for name in absent:
            print(f"  {name}", file=sys.stderr)
    if mismatches:
        print(f"\nV-36 FAIL: {len(mismatches)} file(s) do not match the digest the "
              f"package publishes for them:\n", file=sys.stderr)
        for name, kind, was, now in mismatches:
            print(f"  {name}: recorded {kind} {was}, on disk {now}", file=sys.stderr)
        print("\nThe Data Availability statement says every headline figure is\n"
              "verifiable against its manifest checksum. Refresh with\n"
              "  python ingest/build_deposit.py --refresh-digests\n"
              "after checking that each change is one you meant to make.",
              file=sys.stderr)
    if absent or mismatches:
        return 1

    print("every file the manifest lists is on disk and matches the digest and "
          "size recorded for it. This does not establish that any of them is "
          "the right content, only that the package does not lie about what it "
          "holds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
