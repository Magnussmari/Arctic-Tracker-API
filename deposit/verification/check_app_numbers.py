#!/usr/bin/env python3
"""Does the platform state the same numbers as the paper?

The paper and the platform describe one corpus. They are built from different
repositories and deployed on different days, so nothing except a check keeps
them saying the same thing. Measured 1 October 2026: the platform stated the
CITES trade total as 473,102 in seven places and 473,663 in an eighth, while
the deposit holds 492,095 and the manuscript states 492,095 nine times. The
gap, 18,993 records, is a stale mirror that no one had reason to look at.

The deposit is the source of record. This reads it, reads the platform's own
source, and reports every number the platform states that the deposit
contradicts.

Exit 0 agree, 1 disagree, 3 unmeasured (the platform checkout is not here).

Usage:
  python3 deposit/verification/check_app_numbers.py
  ARCTIC_PORTAL_REPO=/path/to/portal python3 .../check_app_numbers.py
"""
import os, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
DEPOSIT = HERE.parent
# The platform's source checkout, if the reader has one. There is no default:
# without it this check cannot measure anything and says so.
PORTAL = pathlib.Path(os.environ.get("ARCTIC_PORTAL_REPO", "/nonexistent"))

# What the deposit says, read from the deposit rather than typed here.
def from_deposit():
    facts = {}
    trade = DEPOSIT / "tables" / "cites_trade_records.csv"
    if trade.is_file():
        with trade.open("rb") as fh:
            facts["trade_records"] = sum(1 for _ in fh) - 1
    species = DEPOSIT / "tables" / "species.csv"
    if species.is_file():
        with species.open("rb") as fh:
            facts["species"] = sum(1 for _ in fh) - 1
    seiz = DEPOSIT / "tables" / "illegal_trade_seizures.csv"
    if seiz.is_file():
        with seiz.open("rb") as fh:
            facts["seizures"] = sum(1 for _ in fh) - 1
    return facts


# Each claim the platform can make, as a pattern over its own source, mapped to
# the deposited fact it must equal. The pattern captures the number with or
# without a thousands separator, because the platform writes it both ways.
CLAIMS = [
    ("trade_records", re.compile(r"(?<![#\w])(4\d{2},?\d{3})\b"),
     "the CITES trade total"),
]

# A dated release note states what the corpus was on that date. December 2025
# really did validate 473,102 records; the corpus grew afterwards. Rewriting
# that line to today's total would falsify a dated record, so a historical
# entry is exempt - but only where the surrounding block carries a date, and
# never for a value the running page uses.
HISTORICAL = re.compile(r"^\s*<li>.*\b(19|20)\d{2}\b", re.I)


def is_historical(path, lines, i):
    """True when line i sits under a dated heading in a release-notes page."""
    if "release-notes" not in path:
        return False
    if "=" in lines[i - 1] or "return" in lines[i - 1]:
        return False          # a value the page runs on, not a record of one
    for j in range(i - 2, max(-1, i - 60), -1):
        if re.search(r"<h2[^>]*>\s*[A-Z][a-z]+ (19|20)\d{2}", lines[j]):
            return True
    return False


# A six-digit number is only a claim about the corpus when its line is talking
# about the corpus. Without this, "#404040" in the theme file reads as a trade
# total that is 88,055 records out, and a check that cries wolf about a colour
# is a check people learn to skip.
CONTEXT = re.compile(r"trade|record|cites|transaction|dataset", re.I)

# Directories whose contents are not served. A stale number in a backup folder
# is not a claim to a reader, and counting it as one would train us to ignore
# the check.
SKIP = ("backup_old_", "node_modules", "/dist/", "/.next/", "__tests__")


def norm(s):
    return int(s.replace(",", ""))


def floor_claim_ok(got, want, line, end):
    """A number written "490,000+" claims a floor, not the count.

    It is true while the corpus is at or above it. It is only useful while it
    is also close: "400,000+" is technically true of 492,095 and tells a reader
    nothing, so a floor more than 5 per cent below the real figure still fails.
    """
    if not line[end:end + 1] == "+":
        return False
    return got <= want and (want - got) / want <= 0.05


def self_test():
    """Prove the scan can both find and miss before trusting a clean run."""
    assert norm("473,102") == 473102 and norm("473102") == 473102
    pat = CLAIMS[0][1]
    assert pat.search("total of 473,102 records"), "the pattern does not match"
    assert not pat.search("total of 43 species"), "the pattern matches anything"
    # the two defects this check was taught by
    assert not pat.search("getThemedColor('#e5e7eb', '#404040')"), \
        "a hex colour still reads as a trade total"
    assert not CONTEXT.search("const border = '#404040'"), \
        "a line with no corpus vocabulary still passes the context filter"
    assert CONTEXT.search("470,000+ trade transactions"), \
        "the context filter rejects a real claim"
    assert CONTEXT.search("src/hooks/useTradeRecordCount.ts"), \
        "the file name does not supply context, so the fallback is invisible"
    hist = ["<h2>December 2025</h2>", "<ul>", "<li>validated 473,102 records</li>"]
    assert is_historical("src/pages/release-notes.tsx", hist, 3), \
        "a dated release note is being treated as a current claim"
    assert not is_historical("src/pages/methodology.tsx", hist, 3), \
        "the historical exemption leaked outside the release-notes page"
    assert floor_claim_ok(490000, 492095, "490,000+ trade", 7), \
        "a close floor claim is rejected"
    assert not floor_claim_ok(400000, 492095, "400,000+ trade", 7), \
        "a stale floor claim is accepted"
    assert not floor_claim_ok(490000, 492095, "490,000 trade", 7), \
        "a plain number is treated as a floor"
    assert not floor_claim_ok(500000, 492095, "500,000+ trade", 7), \
        "a floor above the real count is accepted"
    live = ["<h2>December 2025</h2>", "x", "const { data = 473102 } = useX();"]
    assert not is_historical("src/pages/release-notes.tsx", live, 3), \
        "a value the page runs on was exempted as history"
    assert any(s in "src/pages/admin/backup_old_141125/x.tsx" for s in SKIP), \
        "the skip list does not cover the backup folder it was written for"
    print("  self-test: PASS (parses, matches, and skips what is not served)")


def main():
    self_test()
    facts = from_deposit()
    if not facts.get("trade_records"):
        print("  UNMEASURED: the deposited trade table is not in this checkout, "
              "so there is nothing to compare the platform against.")
        return 3
    if not PORTAL.is_dir():
        print(f"  UNMEASURED: {PORTAL} is not on this machine, so the platform's "
              f"own numbers were not read. Silence here is not agreement.")
        return 3

    print(f"  deposit: {facts['trade_records']:,} trade records"
          + (f", {facts['species']} species" if facts.get("species") else "")
          + (f", {facts['seizures']} seizures" if facts.get("seizures") else ""))

    faults, scanned, seen, accepted = [], 0, {}, set()
    for f in sorted((PORTAL / "src").rglob("*.ts*")):
        rel = str(f.relative_to(PORTAL))
        if any(s in "/" + rel for s in SKIP):
            continue
        scanned += 1
        text = f.read_text(errors="ignore")
        for key, pat, what in CLAIMS:
            want = facts.get(key)
            if want is None:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                # The file name counts as context too. useTradeRecordCount.ts
                # holds the fallback the whole platform falls back to, and its
                # two lines say only "return 473102" — no vocabulary at all.
                # Requiring it on the line alone made the check miss the one
                # number that matters most.
                if not (CONTEXT.search(line) or CONTEXT.search(rel)):
                    continue
                if is_historical(rel, text.splitlines(), i):
                    continue
                for m in pat.finditer(line):
                    got = norm(m.group(1))
                    seen.setdefault(got, []).append(f"{rel}:{i}")
                    if got == want:
                        continue
                    if floor_claim_ok(got, want, line, m.end()):
                        accepted.add(got)
                        continue
                    faults.append((rel, i, what, got, want))

    print(f"  platform: {scanned} source files read")
    if scanned == 0:
        print(f"  UNMEASURED: no platform source files under {PORTAL}, so there "
              f"was nothing to compare with the deposit.")
        return 3
    for n, where in sorted(seen.items()):
        if n == facts["trade_records"]:
            mark, note = "    ", ""
        elif n in accepted:
            mark, note = "    ", "  (a floor claim, and a current one)"
        else:
            mark, note = "  ! ", ""
        print(f"{mark}{n:,} stated in {len(where)} place(s): "
              f"{', '.join(where[:3])}{' ...' if len(where) > 3 else ''}{note}")

    if not faults:
        print("\nPASS: every total the platform states matches the deposit.")
        return 0
    print(f"\nFAIL: the platform states {len(faults)} number(s) the deposit "
          f"contradicts.")
    for rel, i, what, got, want in faults[:12]:
        print(f"  {rel}:{i}  {what}: states {got:,}, deposit holds {want:,} "
              f"(off by {abs(got - want):,})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
