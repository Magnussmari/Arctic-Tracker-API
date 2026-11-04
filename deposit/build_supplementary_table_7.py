#!/usr/bin/env python3
"""Supplementary Table 7, the LLM toolchain, built from the pipeline record.

The deposit's README listed this table as one that could not be derived,
because it "needs vendor build strings and access dates that are author-held
mint values, not corpus values". That was true until 1 October 2026, when the
values were recovered from the project's own operational record and written
into pipeline.json. Nothing is author-held any more, so the table is derived
like the others.

It is built from pipeline.json rather than typed so that the table, the
Methods box and Figure 13 cannot disagree: all three read the same record.

Two columns will stay empty, by design. Neither vendor
publishes a build string for the model actually served, so "version" names the
product and its documented basis instead of a number. An empty cell here is a
measurement, not an omission, and the table says which.

Usage:
  python3 deposit/build_supplementary_table_7.py
"""
import csv, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "pipeline.json"
OUT = HERE / "supplementary" / "supplementary_table_7_ai_toolchain.csv"

HEADER = ["step", "step_title", "role", "vendor", "product", "version_basis",
          "access_dates", "configuration", "human_gate", "produces_reported_value"]


def plain(s):
    """Strip the record's markdown emphasis; it is a table cell, not prose."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s or "")
    s = re.sub(r"`(.+?)`", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


# Vendor is not in the record, because the record names products. The mapping
# is stated here, once, and asserted against the product string so a renamed
# product cannot carry the wrong vendor silently.
VENDORS = {"Scite": "scite.ai", "Gemini": "Google"}


def vendor_for(product):
    for key, who in VENDORS.items():
        if key.lower() in product.lower():
            return who
    return ""


def split_tool(ai_tool):
    """'**Scite Assistant** (scite.ai) - source discovery' -> product, role.

    The parenthesised vendor is dropped from the product: it has its own
    column, and printing it twice makes the row read as two different things.
    """
    t = re.sub(r"\s*\((?:[a-z0-9.-]+\.[a-z]{2,})\)", "", plain(ai_tool))
    if "—" in t:
        product, role = t.split("—", 1)
    elif ";" in t:
        product, role = t.split(";", 1)
    else:
        product, role = t, ""
    return product.strip(" ."), role.strip(" .")


def dates_from(record):
    m = re.search(r"between (\d{4}-\d{2}-\d{2}) and (\d{4}-\d{2}-\d{2})", record)
    if m:
        return f"{m.group(1)} to {m.group(2)}"
    m = re.search(r"v2 dated (\d{1,2} \w+ \d{4})", record)
    return f"prompt v2 dated {m.group(1)}" if m else ""


def version_from(record, product):
    # The model is read from what the retained outputs record, not asserted:
    # this column once said "documented as GPT-4 based" from one planning
    # document, while the operational record names o3-mini in its output files.
    m = re.search(r"retained v2 outputs? on ([\w. -]+?)\.(?:\s|$)", record)
    if m:
        return (f"no build string published by the vendor; retained output "
                f"records {m.group(1)}")
    if "exposes no build string" in record:
        return f"no build string published by the vendor; served as {product}"
    return ""


def config_from(record):
    bits = []
    for pat, label in [(r"temperature ([\d.]+)", "temperature {}"),
                       (r"maximum output (\d+) tokens", "max output {} tokens"),
                       # A lazy \S+? followed by [.,;] stops at the FIRST
                       # period, which is inside these names rather than after
                       # them: "Unified_Species_JSON_Prompt.md," became
                       # "Unified_Species_JSON_Prompt" and "parser unified_v1.0."
                       # became "unified_v1". Both landed in the deposited
                       # provenance table, whose whole job is to name artefacts
                       # exactly. The terminator must therefore be sentence
                       # punctuation - a period at the END of the token, before
                       # a space or the end of the record - and not any period.
                       (r"system prompt (\S+?)(?=[.,;](?:\s|$))",
                        "system prompt {}"),
                       (r"parser (\S+?)(?=[.,](?:\s|$))", "parser {}"),
                       (r"[Pp]rompt versions? ([^.]+?)[,.]", "prompt versions {}")]:
        m = re.search(pat, record)
        if m:
            bits.append(label.format(m.group(1)))
    return "; ".join(bits)


def rows_from(rec):
    out = []
    for s in rec["steps"]:
        tool = plain(s["ai_tool"])
        if tool.lower().startswith("none"):
            continue                    # no model in the path at all
        product, role = split_tool(s["ai_tool"])
        record = plain(s.get("tool_record", ""))
        generative = bool(vendor_for(product))
        version = version_from(record, product)
        dates = dates_from(record)
        config = config_from(record)
        if not generative:
            # a model is in the path but the record names no product, so every
            # vendor column is "not recorded" rather than blank: a blank cell
            # reads as "nothing to say" and this is "we did not capture it"
            version = dates = config = "not recorded"
        out.append((
            s["id"],
            plain(s["title"]),
            role or ("summarises verified metrics; scoring is author-applied"
                     if "author-applied" in s["ai_tool"] else ""),
            vendor_for(product),
            product if generative else "",
            version,
            dates,
            config,
            s["gate"],
            "no",                       # the wall: no model produces a reported value
        ))
    return out


def self_test():
    assert split_tool("**Scite Assistant** (scite.ai) — source discovery") == \
        ("Scite Assistant", "source discovery"), split_tool(
            "**Scite Assistant** (scite.ai) — source discovery")
    assert vendor_for("Gemini 2.5 Pro") == "Google"
    assert vendor_for("No model") == "", "an unknown product was given a vendor"
    assert dates_from("structured between 2024-05-21 and 2025-06-12.") == \
        "2024-05-21 to 2025-06-12"
    assert dates_from("nothing here") == "", "a date was invented"
    assert "temperature 0.2" in config_from(
        "Google AI Studio, temperature 0.2, maximum output 8192 tokens,")
    assert config_from("") == "", "configuration was invented from nothing"
    assert version_from("retained v2 outputs on o3-mini and o4-mini. Prompt", "Scite") == \
        "no build string published by the vendor; retained output records o3-mini and o4-mini"
    assert "GPT-4" not in version_from("no build string for the served model", "Scite")
    assert version_from("exposes no build string for", "Gemini 2.5 Pro").startswith(
        "no build string"), "the absent version is not reported as absent"
    print("  self-test: PASS (parses, and invents nothing from an empty record)",
          file=sys.stderr)


def main():
    self_test()
    rec = json.loads(SRC.read_text())
    rows = rows_from(rec)
    if not rows:
        print("  ABORT: the pipeline record names no AI step", file=sys.stderr)
        return 1
    for r in rows:
        if "MINT" in "".join(map(str, r)):
            print(f"  ABORT: {r[0]} still carries an unminted placeholder",
                  file=sys.stderr)
            return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(rows)
    print(f"  wrote {OUT.name}: {len(rows)} rows, {len(HEADER)} columns",
          file=sys.stderr)
    for r in rows:
        print(f"    {r[0]}  {r[4] or r[2]:34.34s} {r[6] or '(no dates recorded)'}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
