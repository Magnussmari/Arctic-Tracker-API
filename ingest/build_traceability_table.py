#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Generate the Results-traceability table (Supplementary Table 5).

WHY THIS EXISTS
---------------
The manuscript carries a Results-traceability table mapping every quantitative
claim to (i) the Methods subsection defining the procedure, (ii) the source
dataset and sample size, (iii) the figure/panel with its provenance ID, and
(iv) the operative definition.

This generates that table. Every row carries the query that produces its
number, so a reader can re-derive any claim without reading the analysis code.

Claims whose value depends on a convention that is still an open question
(assessment scope, listing date, legacy category handling, reporter side) are
included and marked PENDING CONVENTION rather than given a number. Publishing a
number with an undocumented convention baked in is the failure the four
questions exist to prevent.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/build_traceability_table.py
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402
import redlist_scale as rl  # noqa: E402

# The Red List series, from 21 October 2026: global and European assessments as
# one series (the lead author's decision), the Mediterranean one excluded.
# redlist_scale.series_sql is the one definition of it, in SQL form.
SERIES_I = rl.series_sql("i")

ROOT = Path(__file__).parent.parent
OUT_CSV = ROOT / "deposit/results_traceability.csv"
# The supplementary table is rendered from the CSV by
# ingest/render_traceability_md.py. One artefact, one writer: when this file
# also wrote the Markdown, the CSV was corrected and the published table kept
# saying PENDING for three claims that had been answered.

# id, claim, methods section, source table, definition, SQL (None = pending)
CLAIMS = [
    ("C01", "Trade records for the 43 listed species, 1975 to 2024",
     "S3 (trade integration)", "cites_trade_records",
     "One CITES trade record is one line in the Trade Database.",
     "select count(*) from {s}.cites_trade_records"),
    ("C02", "Species in the study set",
     "S1 (species identification)", "species",
     "CITES-listed species with an Arctic distribution, curated.",
     "select count(*) from {s}.species"),
    ("C03", "Share of records for commercial purpose",
     "S3", "cites_trade_records",
     "purpose = 'T'. Denominator is ALL records including 1.65% with a blank purpose.",
     "select round(100.0*count(*) filter (where purpose='T')/count(*),2) from {s}.cites_trade_records"),
    ("C04", "Share of records involving Appendix I species",
     "S1, S3", "cites_trade_records",
     "appendix recorded ON THE TRADE RECORD, not the species' current listing.",
     "select round(100.0*count(*) filter (where appendix='I')/count(*),2) from {s}.cites_trade_records"),
    ("C05", "Share of records involving Appendix II species",
     "S1, S3", "cites_trade_records",
     "As C04. Note Appendix III is 5.32% and must be reported or the shares do not sum.",
     "select round(100.0*count(*) filter (where appendix='II')/count(*),2) from {s}.cites_trade_records"),
    ("C06", "Share of records involving Appendix III species",
     "S1, S3", "cites_trade_records", "As C04.",
     "select round(100.0*count(*) filter (where appendix='III')/count(*),2) from {s}.cites_trade_records"),
    ("C07", "Share of records that are wild-sourced",
     "S3", "cites_trade_records",
     "source = 'W'. The majority of the corpus (58.5%) is captive-bred, mostly farmed sturgeon.",
     "select round(100.0*count(*) filter (where source='W')/count(*),2) from {s}.cites_trade_records"),
    ("C08", "Records with a missing quantity",
     "S3", "cites_trade_records",
     "Quantity IS NULL. Reported because a per-dimension total silently drops such rows.",
     "select count(*) from {s}.cites_trade_records where quantity is null"),
    ("C09", "IUCN assessments in the series",
     "S2 (status compilation)", "iucn_assessments",
     "All assessments, all scopes, all vintages.",
     "select count(*) from {s}.iucn_assessments"),
    ("C10", "Assessments using a pre-2001 Red List category",
     "S2", "iucn_assessments",
     "Categories outside LC/NT/VU/EN/CR/EW/EX/DD/RE. Not on the manuscript's ordinal scale.",
     "select count(*) from {s}.iucn_assessments where status not in "
     "('LC','NT','VU','EN','CR','EW','EX','DD','RE')"),
    ("C11", "Species whose first post-listing assessment is a legacy category",
     "S2, S6", "iucn_assessments + cites_listings",
     "Baseline is the first assessment, global or European, at or after the EARLIEST listing date. "
     "Both conventions are stated here rather than assumed; under other conventions "
     "the value differs, which is the point of question 1 and 2.",
     "with fl as (select species_id, min(listing_date) f from {s}.cites_listings group by 1) "
     "select count(*) from (select s.id, (select i.status from {s}.iucn_assessments i "
     f"where i.species_id=s.id and {SERIES_I} and "
     "i.year_published >= extract(year from fl.f) order by i.year_published, i.assessment_id limit 1) bs "
     "from {s}.species s join fl on fl.species_id=s.id) x where bs is not null and "
     "bs not in ('LC','NT','VU','EN','CR','EW','EX','DD','RE')"),
    ("C12", "NAMMCO catch records",
     "S2", "catch_records", "All records as exported 11 June 2025.",
     "select count(*) from {s}.catch_records"),
    ("C13", "Illegal-trade seizure records attributable to a study species",
     "S3", "illegal_trade_seizures",
     "919 source rows decontaminated to those whose reported taxon matches the "
     "attributed species. Quantities are unitless in the source, so no total exists.",
     "select count(*) from {s}.illegal_trade_seizures"),
    ("C14", "CITES listings in force",
     "S1", "cites_listings",
     "All listing rows. is_current does not select one: 8 species carry several.",
     "select count(*) from {s}.cites_listings"),
    ("C15", "CMS listings, excluding daughter-agreement memberships",
     "S1", "cms_listings",
     "agreement = 'CMS'. Daughter agreements (ACCOBAMS etc) are memberships, not CMS listings.",
     "select count(*) from {s}.cms_listings where agreement='CMS'"),
    ("C16", "Daughter-agreement memberships",
     "S1", "cms_listings", "agreement <> 'CMS'. Carry no CMS appendix.",
     "select count(*) from {s}.cms_listings where agreement<>'CMS'"),
    ("C17", "Timeline events with no corroborating table in the deposit",
     "S7", "timeline_events",
     "cites_suspension and eu_decision. Curated assertions, flagged in the API.",
     "select count(*) from {s}.timeline_events where event_type in "
     "('cites_suspension','eu_decision')"),
    ("C18", "Narrative sections withheld pending expert review",
     "S5, S7", "species_narratives",
     "GATED. Machine-drafted, unservable until a named expert signs.",
     "select count(*) from {s}.species_narratives"),
    # Computed from the deposit, not from the database: the full assessment
    # series ships in source_data.zip, so these three are the rows a reviewer can
    # check without credentials. deposit/verification/ holds the computation and
    # the conventions it follows; DEPOSIT_COMPUTED keeps their values when this
    # generator runs, because the database cannot answer them more authoritatively
    # than the deposited table a reader actually has.
    ("C19", "Species whose post-listing trajectory improved",
     "S6 (scoring)", "source_data.zip:figure5_source_data.csv",
     "Earliest and most recent assessment, global or European regional, within "
     "1982-2025 (one series per species, ordered by year and assessment id; the "
     "Mediterranean porbeagle assessment 16527805 is excluded; from 21 October "
     "2026, the lead author's decision), placed on the "
     "ordinal scale; improved means the most recent category is less threatened "
     "than the earliest. Categories carrying no direction are off the scale.",
     None),
    ("C20", "Species whose post-listing trajectory was stable",
     "S6", "source_data.zip:figure5_source_data.csv",
     "Same comparison as C19; stable means the two categories are equal.", None),
    ("C21", "Species whose post-listing trajectory deteriorated",
     "S6", "source_data.zip:figure5_source_data.csv",
     "Same comparison as C19; deteriorated means the most recent category is more "
     "threatened than the earliest.", None),
    # C22 named an unreported quantity and was removed on 2026-10-01; the id is
    # reused on 2026-10-02 for one the paper does report and nothing carried.
    ("C22", "Category transitions between comparable global and European assessments",
     "S6", "source_data.zip:figure5_source_data.csv",
     "Consecutive comparable assessments, global or European, within 1982-2025 whose category "
     "differs, counted per species by deposit/verification/redlist_scale.py. A "
     "non-comparable assessment breaks the chain rather than being skipped, so "
     "no transition is manufactured across a gap. European regional assessments "
     "are counted since 21 October 2026 (the lead author's decision), in the "
     "order of year and assessment id, with both rows of a same-year pair kept as "
     "the published method counted them; the Mediterranean porbeagle assessment "
     "is not.",
     None),
    # C148 joined on 21 October 2026: once European assessments count, one
    # species' latest assessment is Regionally Extinct, so the six categories
    # C23 to C28 sum to 42 and the forty-third species needs its own claim.
    # Computed by deposit/verification/verify_claims_offline.py.
    ("C148", "Species whose current category, on the latest global or European assessment, is RE (Regionally Extinct)",
     "S6", "source_data.zip:figure5_source_data.csv",
     "Most recent assessment per species, global or European, within 1982-2025, "
     "counted by category; RE is the seventh part of the distribution C23 to C28 "
     "begin, so the seven counts sum to the 43 species in the study set.",
     None),
    # C141-C147: what is inside the Figure 8 importer shares. Carried without
    # SQL on purpose. A reader cannot check a composition claim on our word, so the
    # authority for them is deposit/verification/verify_claims_offline.py,
    # which recomputes each one from the deposited trade table with no
    # database and no credentials. Writing SQL here as well would put a second
    # computation of the same number behind a connection only we have.
    ("C141", "Wild-origin share of United Arab Emirates import records",
     "S3 (trade integration)", "cites_trade_records",
     "Composition of the shares Figure 8 reports, over the ten non-Arctic importers the Results name (AE, DE, CN, CH, JP, GB, HK, QA, KR, SG). Source code W is the Convention's wild code, read exactly as recorded and never merged with C, D or F. Dominated means the single largest taxon exceeds 70% of that importer's records. C146 and C147 move the denominator with the numerator by design: C03's 67.01% commercial share is over all 492,095 records, and the comparison is what shows how much of it is a property of the composition.", None),
    ("C142", "Gyrfalcon and peregrine share of United Arab Emirates import records",
     "S3 (trade integration)", "cites_trade_records",
     "Composition of the shares Figure 8 reports, over the ten non-Arctic importers the Results name (AE, DE, CN, CH, JP, GB, HK, QA, KR, SG). Source code W is the Convention's wild code, read exactly as recorded and never merged with C, D or F. Dominated means the single largest taxon exceeds 70% of that importer's records. C146 and C147 move the denominator with the numerator by design: C03's 67.01% commercial share is over all 492,095 records, and the comparison is what shows how much of it is a property of the composition.", None),
    ("C143", "Lowest wild-origin share among the ten named non-Arctic importers",
     "S3 (trade integration)", "cites_trade_records",
     "Composition of the shares Figure 8 reports, over the ten non-Arctic importers the Results name (AE, DE, CN, CH, JP, GB, HK, QA, KR, SG). Source code W is the Convention's wild code, read exactly as recorded and never merged with C, D or F. Dominated means the single largest taxon exceeds 70% of that importer's records. C146 and C147 move the denominator with the numerator by design: C03's 67.01% commercial share is over all 492,095 records, and the comparison is what shows how much of it is a property of the composition.", None),
    ("C144", "Highest wild-origin share among the ten named non-Arctic importers",
     "S3 (trade integration)", "cites_trade_records",
     "Composition of the shares Figure 8 reports, over the ten non-Arctic importers the Results name (AE, DE, CN, CH, JP, GB, HK, QA, KR, SG). Source code W is the Convention's wild code, read exactly as recorded and never merged with C, D or F. Dominated means the single largest taxon exceeds 70% of that importer's records. C146 and C147 move the denominator with the numerator by design: C03's 67.01% commercial share is over all 492,095 records, and the comparison is what shows how much of it is a property of the composition.", None),
    ("C145", "Named non-Arctic importers whose largest single taxon exceeds 70% of their records",
     "S3 (trade integration)", "cites_trade_records",
     "Composition of the shares Figure 8 reports, over the ten non-Arctic importers the Results name (AE, DE, CN, CH, JP, GB, HK, QA, KR, SG). Source code W is the Convention's wild code, read exactly as recorded and never merged with C, D or F. Dominated means the single largest taxon exceeds 70% of that importer's records. C146 and C147 move the denominator with the numerator by design: C03's 67.01% commercial share is over all 492,095 records, and the comparison is what shows how much of it is a property of the composition.", None),
    ("C146", "Share of records for commercial purpose, excluding Siberian sturgeon and gyrfalcon",
     "S3 (trade integration)", "cites_trade_records",
     "Composition of the shares Figure 8 reports, over the ten non-Arctic importers the Results name (AE, DE, CN, CH, JP, GB, HK, QA, KR, SG). Source code W is the Convention's wild code, read exactly as recorded and never merged with C, D or F. Dominated means the single largest taxon exceeds 70% of that importer's records. C146 and C147 move the denominator with the numerator by design: C03's 67.01% commercial share is over all 492,095 records, and the comparison is what shows how much of it is a property of the composition.", None),
    ("C147", "Records remaining after excluding Siberian sturgeon and gyrfalcon",
     "S3 (trade integration)", "cites_trade_records",
     "Composition of the shares Figure 8 reports, over the ten non-Arctic importers the Results name (AE, DE, CN, CH, JP, GB, HK, QA, KR, SG). Source code W is the Convention's wild code, read exactly as recorded and never merged with C, D or F. Dominated means the single largest taxon exceeds 70% of that importer's records. C146 and C147 move the denominator with the numerator by design: C03's 67.01% commercial share is over all 492,095 records, and the comparison is what shows how much of it is a property of the composition.", None),
]

# C22, "Post-uplisting decline in recorded trade, per named taxon", was removed
# on 2026-10-01. It was not a convention still to be settled; it was a row for a
# quantity the paper does not report. The manuscript contains no per-taxon claim
# that recorded trade fell after a listing, and it cannot: the revision's own
# definition of the outcome is the status trajectory, and R3-15 and R3-18 took
# out exactly the reading in which a post-listing movement is an effect of the
# listing. A traceability table maps reported quantities to their sources, so a
# row for an unreported one is not an open question but an invitation to ask for
# a number that exists nowhere in the text. Removing it is the decision; leaving
# it marked PENDING in a published supplementary table would have shipped an
# unresolved methodological choice to reviewers who never asked for the claim.


def refuse_to_truncate():
    """Stop if the published table holds claims this generator does not.

    CLAIMS holds fewer entries than results_traceability.csv, and this
    generator writes the CSV from CLAIMS alone, so an unguarded run would
    delete the claims it does not hold - the claim-to-Methods-to-source
    mapping the manuscript cites as Supplementary Table 5, and the table every
    offline verifier reads its expected values from.

    The other checks would not see that: verify_manifest_digests checks that
    the file matches its digest, verify_deposit_accounted checks that it is
    listed, and verify_claims_offline reads whatever rows it finds.

    This does not fix the gap - porting the deposit-computed claims into CLAIMS
    is a separate piece of work, and most of them have no SQL because the
    database is not where a reader checks them. It makes the gap loud instead
    of destructive: refusing names every claim that would be lost.
    """
    if not OUT_CSV.exists():
        return
    have = [r["claim_id"] for r in csv.DictReader(open(OUT_CSV))]
    known = {c[0] for c in CLAIMS}
    orphans = [c for c in have if c not in known]
    if orphans:
        sys.exit(f"REFUSING to write {OUT_CSV.name}: it carries "
                 f"{len(orphans)} claim(s) this generator does not know, and "
                 f"writing from CLAIMS alone would delete them -\n  "
                 + ", ".join(orphans) +
                 f"\n\nThose claims are computed by "
                 f"deposit/verification/verify_claims_offline.py. Add them to "
                 f"CLAIMS with sql=None so this generator carries them "
                 f"through, then run again. Do not delete this check to get "
                 f"past it: the table it protects is Supplementary Table 5 and "
                 f"every offline verifier reads its expected values from it.")


def deposit_values():
    """The values computed from the deposit, read back from the published CSV.

    These rows have no SQL because the database is not where a reader can check
    them. Their numbers come from deposit/verification/, which recomputes them
    from source_data.zip, and this generator's job is to carry them through
    unchanged rather than to blank them.
    """
    have = {r["claim_id"]: r["value"] for r in csv.DictReader(open(OUT_CSV))}
    missing = [c[0] for c in CLAIMS if c[5] is None and not have.get(c[0], "").strip()]
    if missing:
        sys.exit(f"{', '.join(missing)} are computed from the deposit and the "
                 f"existing {OUT_CSV.name} does not carry their values. Run "
                 f"deposit/verification/verify_claims_offline.py and fill them "
                 f"before regenerating, or this run would erase them.")
    return have


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", default="arctic_v2")
    args = ap.parse_args()

    # Before anything else, and before a database is needed: this generator
    # writes the whole file from CLAIMS, so it must not run while the published
    # table holds claims CLAIMS has never heard of.
    refuse_to_truncate()
    schema = validate_schema(args.schema)
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    rows = []
    conn = psycopg2.connect(url, connect_timeout=60)
    try:
        with conn.cursor() as cur:
            keep = deposit_values()
            for cid, claim, section, table, definition, sql in CLAIMS:
                if sql is None:
                    # Answered by the deposit, not by this connection. Refusing to
                    # overwrite it is the point: the number a reader can check must
                    # not be silently replaced by one only we can.
                    value = keep[cid]
                else:
                    cur.execute(sql.format(s=schema))
                    value = str(cur.fetchone()[0])
                rows.append({
                    "claim_id": cid,
                    "claim": claim,
                    "value": value,
                    "methods_section": section,
                    "source_table": table,
                    "operative_definition": definition,
                    "query": "" if sql is None else sql.format(s=schema),
                })
                print(f"  {cid}  {value:>22}  {claim[:52]}")
    finally:
        conn.close()

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} - {len(rows)} claims, every one valued.")
    print("  the supplementary table is rendered from this CSV by "
          "ingest/render_traceability_md.py, which needs no database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
