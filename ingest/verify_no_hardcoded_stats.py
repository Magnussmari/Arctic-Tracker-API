#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-14
"""V-22: a figure must not state a statistic it did not compute.

WHY THIS EXISTS
---------------
A statistic typed into a figure annotation as a string literal, for example

    f'{total:,.0f} items<br>93.3% of total<br>{count} incidents'

goes stale silently when the data changes. The figure regenerates, the Source
Data matches byte for byte, and the literal was never in the Source Data
because it was never computed. A literal cannot fail a determinism check: it is
the most deterministic thing in the file.

WHAT IT ASSERTS
---------------
No figure script contains a literal percentage or a literal thousands-separated
number inside display text — titles, annotations, hover templates, bar labels.
Such a number is either derived, in which case it should be an expression, or it
is stale, in which case it is already wrong.

Numbers in layout are ignored: coordinates, sizes, widths, opacities and axis
ranges are not claims about the data.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "visualizations" / "scripts"

# A number that asserts something: a percentage, or a thousands-separated count.
STAT = re.compile(r"\b\d{1,3}\.\d+%|\b\d{1,3}%|\b\d{1,3}(?:,\d{3})+\b")

# A first version of this required a display keyword (text=, title=, …) on the
# same line, and gave a FALSE GREEN on the exact defect it was written for: the
# 93.3% lived inside a list literal assigned to comparison_text, so its own line
# carried no keyword. Every string in the file is examined instead, and prose is
# told from machinery by what it looks like rather than by where it sits.
#
# A display string is one a human reads: it has words and spaces, or plotly's
# line break. SQL, format specifiers and colour codes do not qualify.
SQL = re.compile(r"\b(select|from|where|group by|order by|join)\b", re.I)

# Years and axis-style round numbers are not claims. 100% is a definition.
ALLOWED = {"100%", "0%"}
YEAR = re.compile(r"\b(19|20)\d{2}\b")


def is_display(s: str) -> bool:
    """Text a reader sees, as opposed to a query or a format string."""
    if SQL.search(s):
        return False
    return "<br>" in s or (" " in s.strip() and re.search(r"[A-Za-z]{3}", s))


def findings_for(path: Path) -> list[tuple[int, str, str]]:
    import io
    import tokenize

    text = path.read_text()
    out: list[tuple[int, str, str]] = []

    # Docstrings explain the code, including — as in this file — by quoting the
    # defect. Flagging them would make writing down what went wrong an error.
    doc_lines: set[int] = set()
    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)) and node.body:
                first = node.body[0]
                if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                        and isinstance(first.value.value, str)):
                    doc_lines |= set(range(first.lineno, first.end_lineno + 1))
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (SyntaxError, tokenize.TokenError, IndentationError) as exc:
        print(f"  NOT CHECKED: {path.name} does not parse ({type(exc).__name__})")
        return []

    # Python 3.12 split f-strings into FSTRING_START / FSTRING_MIDDLE / … , so a
    # scanner testing for tokenize.STRING sees no f-string at all. That is how
    # this gate passed twice on the defect it was built for: the 93.3% sits in an
    # f-string, beside the very interpolations that made the rest of the label
    # live. FSTRING_MIDDLE is exactly the literal text between interpolations,
    # which is precisely what must not contain a statistic.
    STRINGY = {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", -1)}
    for tok in toks:
        if tok.type not in STRINGY or tok.start[0] in doc_lines:
            continue
        if not is_display(tok.string):
            continue
        for m in STAT.finditer(tok.string):
            val = m.group(0)
            if val in ALLOWED or YEAR.fullmatch(val.replace(",", "")):
                continue
            # A literal that sits next to its own f-string interpolation is the
            # shape that produced this gate, but any literal statistic qualifies.
            out.append((tok.start[0], val, tok.string.strip()[:88].replace("\n", " ")))
    return out


def main() -> int:
    if not SCRIPTS.is_dir():
        print(f"V-22 CANNOT RUN: {SCRIPTS} is absent.")
        return 2
    scripts = sorted(SCRIPTS.glob("figure*.py"))
    if not scripts:
        # Silence must not pass: no scripts would mean nothing to check and a
        # free green.
        print("V-22 CANNOT RUN: no figure scripts found.")
        return 2

    all_findings: list[tuple[str, int, str, str]] = []
    for s in scripts:
        for line_no, tok, ctx in findings_for(s):
            all_findings.append((s.name, line_no, tok, ctx))

    print(f"V-22 hardcoded statistics: {len(scripts)} figure script(s) checked\n")

    # An allowed value that appears in no script is an exclusion nobody needs.
    # "100%" was one: carried since this gate was written, matching nothing.
    # Reported rather than removed automatically, because the right response to a
    # dead exclusion is to look at it, not to have a tool quietly delete rules.
    body = "".join(s.read_text(errors="ignore") for s in scripts)
    dead = [a for a in sorted(ALLOWED) if a not in body]
    if dead:
        print(f"  {len(dead)} allowed value(s) appear in no script: {', '.join(dead)}")


    if all_findings:
        print(f"V-22 FAIL: {len(all_findings)} literal statistic(s) in display text:\n")
        for name, line_no, tok, ctx in all_findings:
            print(f"  {name}:{line_no}  {tok}")
            print(f"      {ctx}")
        print("\nA number a figure states must be a number the figure computed.")
        print("Figure 7 asserted 93.3% beside two live values while its own data")
        print("said 83.6%, and a determinism check cannot see it: a literal is the")
        print("most reproducible thing in the file.")
        return 1

    print(f"V-22 PASS: no figure states a percentage or a thousands-separated "
          f"count that it did not compute.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
