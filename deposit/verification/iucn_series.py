#!/usr/bin/env python3
"""Read a Source Data member, restoring IUCN categories from a local rebuild.

The deposit ships no Red List category: IUCN's terms prohibit redistributing
them, so what ships is the assessment identifier and REBUILD-IUCN.md. Every
number in the paper is still recomputable from the deposit - but the first step
is the reader's own fetch from IUCN, under the reader's own acceptance of
IUCN's terms, and rebuild_iucn.py performs it.

A verifier therefore reads the archive through this module. Before the rebuild
it stops with UNMEASURED and says what to run; after the rebuild it sees the
file the paper was computed on, byte for byte, as REBUILD-IUCN.digest attests.

Silence is not a pass: returning the withheld file to a verifier would make it
compute zeros and report a mismatch that is an artefact of the licence, not of
the data.
"""
import pathlib
import sys

DEPOSIT = pathlib.Path(__file__).resolve().parent.parent
REBUILT = DEPOSIT / "rebuilt"
WITHHELD = "⟨withheld: see REBUILD-IUCN.md⟩"

MESSAGE = (
    "UNMEASURED: {member} carries withheld IUCN Red List categories.\n"
    "  The deposit may not redistribute them (IUCN Terms and Conditions of\n"
    "  Use). Rebuild them from the deposited assessment identifiers first:\n"
    "\n"
    "      python3 rebuild_iucn.py            # needs an IUCN API token\n"
    "\n"
    "  See REBUILD-IUCN.md. The rebuild writes deposit/rebuilt/ and checks\n"
    "  itself against REBUILD-IUCN.digest, so a successful rebuild is the\n"
    "  same corpus this paper was computed on."
)


def read_member(zipobj, member):
    """Bytes of a Source Data member, preferring a rebuilt copy if one exists."""
    local = REBUILT / pathlib.PurePosixPath(member).name
    if local.exists():
        return local.read_bytes()
    raw = zipobj.read(member)
    if WITHHELD.encode("utf8") in raw:
        print(MESSAGE.format(member=member), file=sys.stderr)
        raise SystemExit(3)
    return raw
