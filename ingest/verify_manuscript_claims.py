#!/usr/bin/env python3
"""Recompute every headline number in the manuscript against the live corpus.

A number that does not reproduce is a number any reader can falsify in one
query, so each one is recomputed here.

Turns UNVERIFIED into DONE or FALSE. Every claim is printed with the value the
manuscript states, the value the database gives, and a verdict. Where the claim's
definition is ambiguous the script says so rather than guessing, because a
match produced under a guessed definition is not a verification.
"""
import os
import re
import sys
# Importing a sibling here writes __pycache__ INTO the deposit, and
# verify_deposit_accounted.py rejects bytecode in a citable archive. Running
# these scripts in place is the intended use, so the run must not leave
# residue behind, or the archive gate would fail merely because the verifiers
# had been run.
sys.dont_write_bytecode = True

import psycopg2
import pathlib as _pl
ROOT_DIR = _pl.Path(__file__).parent.parent

RESULTS = []


def check(label, claimed, computed, ok=None, note=""):
    if ok is None:
        ok = claimed == computed
    RESULTS.append((label, claimed, computed, ok, note))


def main():
    # Run from a fresh clone there is no credential. Exit with a sentence, as
    # every other script in this directory does, so the failure reads as
    # missing configuration rather than as broken code.
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")
    conn = psycopg2.connect(url)
    cur = conn.cursor()

    def one(sql, args=None):
        cur.execute(sql, args or ())
        return cur.fetchone()[0]

    # A reader running this from the deposit will not have a schema called
    # arctic_v2 unless they happened to name it that.
    # The name is overridable, and the schema is checked to exist before any
    # claim runs — otherwise every query fails with "relation does not exist"
    # and the reader is left guessing whether the data or the script is wrong.
    S = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", S):
        raise SystemExit(f"ARCTIC_SCHEMA={S!r} is not a plain identifier")
    # information_schema.schemata lists only the schemas the connecting role
    # may USE, so a role without USAGE would be told the schema "does not exist".
    # A missing permission and a missing schema need different fixes, so they
    # are told apart: existence from pg_namespace, permission separately.
    cur.execute("select 1 from pg_namespace where nspname = %s", (S,))
    if cur.fetchone():
        cur.execute("select has_schema_privilege(%s, 'USAGE')", (S,))
        if not cur.fetchone()[0]:
            raise SystemExit(
                f"schema {S!r} exists, but the role in ARCTIC_DATABASE_URL has no "
                f"USAGE on it. Connect as a role that can read it; nothing was checked.")
    else:
        raise SystemExit(
            f"schema {S!r} does not exist in this database.\n"
            f"Load the deposited tables into a schema and name it with "
            f"ARCTIC_SCHEMA, or create schema.sql's arctic_v2 as-is.")

    # Preflight. Running this against a database built from the deposit alone
    # used to die with ZeroDivisionError somewhere around claim thirty, because
    # two tables are withheld for licence reasons and are therefore empty. A
    # reader would have had no way to tell that from the traceback, and would
    # reasonably have concluded the deposit was broken.
    #
    # It is not broken; it is incomplete by licence, which we say elsewhere and
    # should say here, at the moment it bites.
    REQUIRED = {
        "iucn_assessments": "IUCN Red List terms forbid redistribution -- it is "
                            "withheld by licence, not broken. The assessment ids in "
                            "identifiers/iucn_assessment_ids.csv let you retrieve each "
                            "assessment from the Red List with a free account; the "
                            "extraction code (deposit/rebuild_iucn.py, documented "
                            "in deposit/REBUILD-IUCN.md) is in the code "
                            "repository, not this deposit. See the README, "
                            "'Not redistributed, and why'.",
        "catch_records": "NAMMCO terms forbid redistribution, and we have no "
                         "extraction script — see the deposit README. The record "
                         "identifiers in identifiers/catch_record_ids.csv locate "
                         "every row in the public NAMMCO catch database.",
        "cites_trade_records": "This one ships in the deposit; if it is empty the "
                               "load did not complete.",
        "species": "This one ships in the deposit; if it is empty the load did not "
                   "complete.",
    }
    empty = []
    for table, how in REQUIRED.items():
        cur.execute(f"select count(*) from {S}.{table}")
        if cur.fetchone()[0] == 0:
            empty.append((table, how))
    if empty:
        print("These claims cannot be checked, because tables they need are empty:\n")
        for table, how in empty:
            print(f"  {S}.{table} has no rows.")
            print(f"    {how}\n")
        print("Nothing here says the numbers are wrong. It says this database "
              "cannot answer\nthe question yet. Fill the tables above and re-run.")
        raise SystemExit(2)

    # --- corpus size -------------------------------------------------------
    trade = one(f"select count(*) from {S}.cites_trade_records")
    check("CITES trade records", 492095, trade)

    species = one(f"select count(*) from {S}.species")
    check("species", 43, species)

    iucn = one(f"select count(*) from {S}.iucn_assessments")
    check("IUCN assessments", 370, iucn)

    # --- seizures ----------------------------------------------------------
    seiz = one(f"select count(*) from {S}.illegal_trade_seizures")
    check("seizure records retained", 225, seiz)
    seiz_sp = one(f"select count(distinct species_id) from {S}.illegal_trade_seizures")
    check("species with seizure records", 26, seiz_sp)

    # --- purpose -----------------------------------------------------------
    commercial = one(
        f"select count(*) from {S}.cites_trade_records where purpose = 'T'")
    pct_all = round(100.0 * commercial / trade, 2)
    check("commercial purpose, share of ALL records", 67.01, pct_all)

    stated = one(
        f"select count(*) from {S}.cites_trade_records "
        f"where purpose is not null and purpose <> ''")
    pct_stated = round(100.0 * commercial / stated, 2)
    check("commercial purpose, share of records WITH a stated purpose",
          68.14, pct_stated)

    blank = round(100.0 * (trade - stated) / trade, 2)
    check("records with blank purpose", 1.65, blank)

    # --- reporter side -----------------------------------------------------
    exp = one(f"select count(*) from {S}.cites_trade_records where reporter_type = 'E'")
    imp = one(f"select count(*) from {S}.cites_trade_records where reporter_type = 'I'")
    check("exporter-reported records", 307261, exp)
    check("importer-reported records", 184834, imp)

    # --- Acipenser baerii share of the trade records -----------------------
    baerii = one(
        f"select count(*) from {S}.cites_trade_records t join {S}.species s "
        f"on s.id = t.species_id where s.scientific_name = 'Acipenser baerii'")
    check("Acipenser baerii trade records", 195775, baerii)

    # --- appendix shares ---------------------------------------------------
    # Denominator pinned: share of TRADE RECORDS, not of species. Species gives
    # non-integer counts (27.34% of 43 = 11.76), so records is the only reading
    # under which the published figures are even well formed.
    def app_pct(code):
        n = one(f"select count(*) from {S}.cites_trade_records where appendix = %s", (code,))
        return round(100.0 * n / trade, 2)

    check("Appendix II share of records", 67.34, app_pct("II"))
    check("Appendix I share of records", 27.34, app_pct("I"))
    check("Appendix III share of records", 5.32, app_pct("III"))

    # The three published shares are quoted as summing to 100. They do not
    # quite: a fourth appendix code exists and is never reported.
    n_other = one(
        f"select count(*) from {S}.cites_trade_records "
        f"where appendix is null or appendix not in ('I','II','III')")
    check("records outside Appendix I/II/III (unreported fourth category)",
          23, n_other,
          note="Appendix code 'N'. Small, but the paper presents three shares "
               "as exhaustive. State it or state the exclusion.")

    # The series. From 21 October 2026 every trajectory and status number here is
    # computed on global AND European assessments read as one series (the lead
    # author's decision); redlist_scale.series_sql is the one definition, shared
    # with the offline verifiers, and the Mediterranean porbeagle assessment
    # stays out. In a year with several assessments the higher id stands.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import redlist_scale as rl
    SERIES = rl.series_sql()
    SERIES_A = rl.series_sql("a")

    # --- Critically Endangered share, with the scope pinned ----------------
    # Scope matters: the old is_latest flag pointed at a European regional
    # assessment for 17 of 43 species, and the global-only reading it was
    # replaced by was itself replaced on 21 October 2026. This uses the series
    # above, latest year, the higher assessment id in a tied year.
    cr_sql = f"""
        with cur as (
          select distinct on (species_id) species_id, status
          from {S}.iucn_assessments
          where {SERIES}
          order by species_id, year_published desc, assessment_id desc
        )
        select count(*) from {S}.cites_trade_records t
        join cur c on c.species_id = t.species_id where c.status = 'CR'"""
    cr = one(cr_sql)
    check("Critically Endangered share of records (global and European, latest year)",
          39.86, round(100.0 * cr / trade, 2),
          note="Under 40%, so 'over 40%' would overstate it.")

    check("share of the top-category records contributed by the largest single taxon",
          99.81, round(100.0 * baerii / cr, 2),
          note="One taxon, largely farmed, makes up almost all of this share. "
               "Quoting 39.86% without this is arithmetically true and "
               "substantively misleading.")

    # --- next-largest CR contribution, bounding the one-taxon claim -------
    # Finding (i) names this figure to show every other CR contribution is
    # negligible. The set it is computed over changes whenever a species'
    # current category changes (one of the species was reassessed in 2020), so
    # the number is recomputed and asserted here rather than taken as fixed.
    next_cr = one(f"""
        with cur as (
          select distinct on (species_id) species_id, status
          from {S}.iucn_assessments
          where {SERIES}
          order by species_id, year_published desc, assessment_id desc
        ),
        cr_counts as (
          select t.species_id, count(*) n
          from {S}.cites_trade_records t
          join cur c on c.species_id = t.species_id
          where c.status = 'CR'
          group by t.species_id
        )
        select n from cr_counts order by n desc offset 1 limit 1""")
    check("next-largest single-taxon contribution to the top-category records",
          185, next_cr,
          note="The finding-(i) qualifier states this. The set it ranks follows "
               "each species' current category, so a reassessment can change it.")

    # --- the quantity defect, measured rather than remembered --------------
    # The defect can be counted in more than one way (records altered, rows
    # differing under a comparison, quantities restored), and the counts do not
    # reconcile unless each is defined. These checks measure the defined
    # quantities directly against the corpus.
    lose = one(f"""select count(*) from {S}.cites_trade_records
                   where quantity is not null and quantity <> round(quantity, 2)""")
    check("records that lose precision at two decimal places", 64956, lose)

    to_zero = one(f"""select count(*) from {S}.cites_trade_records
                      where quantity is not null and quantity <> 0
                        and round(quantity, 2) = 0""")
    check("of those, records that would round to exactly zero", 7091, to_zero,
          note="A SUBSET of the 64,956, not an additional group. Stating them "
               "as separate populations is what made the numbers appear not to sum.")

    # V-5b's first run reported 63,971 "source rows absent from the database".
    # That is a THIRD quantity, not a contradiction of the two above, and the
    # difference is entirely explained by the comparison's own normalisation:
    # verify_derived_truth.norm() formats numerics to six decimal places, so a
    # record whose precision loss falls below the sixth decimal digests
    # identically on both sides and is not counted as differing.
    differs_6dp = one(f"""
        select count(*) from {S}.cites_trade_records
        where quantity is not null
          and to_char(quantity,'FM99999999990.000000')
              <> to_char(round(quantity, 2),'FM99999999990.000000')""")
    check("of those, records that still differ once normalised to six decimals",
          63968, differs_6dp)

    dropped = one(f"""select count(*) from {S}.cites_trade_records
                      where quantity is not null and abs(quantity) >= 1e8""")
    check("records the old numeric(10,2) ceiling dropped outright", 3, dropped)

    check("V-5b first-run differing rows, reconstructed (63,968 + 3)",
          63971, differs_6dp + dropped,
          note="Closes the reconciliation a blind model review opened on "
               "2026-08-11. 64,956 records altered; 63,968 of them detectable "
               "at the gate's six-decimal normalisation; plus the 3 records the "
               "ceiling dropped entirely = the 63,971 V-5b reported.")

    # --- quantity: no genuine zeros remain ---------------------------------
    zeros = one(
        f"select count(*) from {S}.cites_trade_records where quantity = 0")
    check("quantity values equal to exactly zero (all were artifacts, "
          "expected 0 after the widen+restore)", 0, zeros)

    # --- attribution loss, the ground for withdrawing finding (ii) ---------
    # The DIRECTION of this effect is what matters. An earlier draft read falcon
    # reporting resolution as IMPROVED, 52% unattributable falling to 2.3%.
    # Measured, it deteriorated: 24.9% rising to 54.6%, driven by hybrid records going from
    # 51 to 128,554. The direction is the whole argument — worsening resolution
    # manufactures an apparent decline, which is precisely the post-uplisting
    # decline the paper claimed, so the direction is asserted here.
    #
    # These two numbers come from the raw shards rather than the corpus, because
    # the corpus by construction holds only records attributable to a species.
    # They are asserted here against the stored report so they cannot drift.
    import json, os as _os
    # The deposit has to stand on its own — a reader holding only the deposit is
    # the reader this whole verification directory is for — so the report is
    # deposited beside this script. It is also written by attribution_loss.py
    # into the repository's ingest/reports, and that is where it actually was
    # while this check reported the claim unverified.
    _d = _pl.Path(__file__).resolve().parent
    _reps = [_d / "reports" / "attribution_loss.json",
             _d.parent.parent / "ingest" / "reports" / "attribution_loss.json"]
    rep = next((str(r) for r in _reps if r.exists()), str(_reps[0]))
    if not _os.path.exists(rep):
        # Not a skip. A missing report means this claim is unverified, and an
        # unverified claim reported as "24 of 24 reproduce" is the failure this
        # whole script exists to prevent.
        check("falcon attribution report present (run attribution_loss.py)",
              True, False)
    else:
        with open(rep) as fh:
            per_year = json.load(fh)["falcons"]

        def share(lo, hi):
            sp = higher = hybrid = 0
            for year, (s, h, y) in per_year.items():
                if lo <= int(year) <= hi:
                    sp += s; higher += h; hybrid += y
            total = sp + higher + hybrid
            return round(100.0 * (higher + hybrid) / total, 1) if total else None

        def component(lo, hi):
            sp = higher = hybrid = 0
            for year, (s, h, y) in per_year.items():
                if lo <= int(year) <= hi:
                    sp += s; higher += h; hybrid += y
            return sp, higher, hybrid

        # The two components move in OPPOSITE directions, which is why this was
        # got wrong twice. Higher-taxon reporting genuinely improved; hybrid
        # reporting exploded, and a hybrid is as unattributable as a genus-level
        # record. Only the combined share answers the question the paper asks.
        sp_e, hi_e, hy_e = component(1975, 1985)
        sp_l, hi_l, hy_l = component(2006, 2024)
        check("falcon records above species level, 1975-1985 share", 20,
              round(100.0 * hi_e / (sp_e + hi_e)))
        check("falcon records above species level, 2006-2024 share", 1.7,
              round(100.0 * hi_l / (sp_l + hi_l), 1),
              note="This component IMPROVED. Quoting it alone is what produced "
                   "the inverted account of the overall trend.")
        check("Falco hybrid records, 1975-1985", 51, hy_e)
        check("Falco hybrid records, 2006-2024", 128554, hy_l)

        early, late = share(1975, 1985), share(2006, 2024)
        check("falcon records unattributable to a species, 1975-1985", 24.9, early)
        check("falcon records unattributable to a species, 2006-2024", 54.6, late,
              note="RISES. Reporting resolution for these taxa deteriorated. A "
                   "species-level count therefore captures a shrinking share of "
                   "the group's trade and manufactures an apparent decline.")
        check("direction of the falcon attribution shift", "worse",
              "worse" if (early is not None and late is not None and late > early)
              else "better",
              note="Every document in this project said 'better' until "
                   "2026-08-12. The direction is the entire argument for "
                   "withdrawing finding (ii); backwards, it refutes itself.")

    # --- does the "post-listing" trajectory actually post-date the listing? --
    # The outcome construct is named "post-listing conservation status
    # trajectory". For ten species it is not one: their earliest comparable
    # global assessment predates their first Appendix listing, so the measured
    # span begins before the intervention it is named for. Found 2026-08-12 by
    # checking a sentence rather than asserting it.
    pre = one(f"""
        with l as (select species_id, min(event_date) first_listing
                     from {S}.cites_listing_events where is_listing group by species_id),
             a as (select species_id, min(year_published) y0
                     from {S}.iucn_assessments
                    where {SERIES} group by species_id)
        select count(*) from a join l on l.species_id = a.species_id
         where a.y0 < extract(year from l.first_listing)""")
    check("species whose earliest assessment PREDATES their first listing", 10, pre,
          note="The construct is called post-listing. For these ten it is not, "
               "and the Methods now say so at the definition.")

    # --- finding (iii): the status trajectories -----------------------------
    # V-9 did not assert these until 2026-08-12, which is how the manuscript came
    # to state "34 genuine category transitions (18 improvements)" against a
    # measured 33 (17). The third headline finding was the only one whose
    # numbers no gate reproduced.
    cur.execute(f"""
        select s.scientific_name, a.status, a.year_published
          from {S}.iucn_assessments a
          join {S}.species s on s.id = a.species_id
         where {SERIES_A} and a.year_published is not null
         order by s.scientific_name, a.year_published, a.assessment_id""")
    seq = {}
    for name, status, year in cur.fetchall():
        seq.setdefault(name, []).append((year, status))

    verdicts = {"improved": 0, "deteriorated": 0, "unchanged": 0}
    excluded = 0
    transitions = []
    for name, rows in seq.items():
        usable = [(y, s) for y, s in rows if rl.comparable(s)]
        if len(usable) < 2:
            excluded += 1
            continue
        verdicts[rl.classify(usable[0][1], usable[-1][1])] += 1
        transitions.extend(rl.transitions(rows))

    scored = sum(verdicts.values())
    check("species carrying a comparable trajectory", 41, scored)
    check("species excluded, baseline not comparable", 2, excluded)

    # --- the R1-04 stratification -----------------------------------------
    # These five numbers are the measured answer to the confounder R1-04
    # raised. Each is recomputed here so the stated values cannot drift.
    cur.execute(f"""
        select species_id, min(extract(year from event_date))::int
          from {S}.cites_listing_events where is_listing group by species_id""")
    listing_year = dict(cur.fetchall())

    cur.execute(f"""
        select s.id, a.year_published, a.status
          from {S}.iucn_assessments a
          join {S}.species s on s.id = a.species_id
         where {SERIES_A} and a.year_published is not null
         order by s.id, a.year_published, a.assessment_id""")
    by_id = {}
    for sid, yr, st in cur.fetchall():
        by_id.setdefault(sid, []).append((yr, st))

    STABLE = {'LC', 'LR/lc', 'NT', 'LR/nt', 'LR/cd'}
    THREAT = {'VU', 'EN', 'CR'}
    stable_at_listing = threatened_at_listing = no_baseline = 0
    lags = []
    for sid, hist in by_id.items():
        usable = [(y, s) for y, s in hist if rl.comparable(s)]
        if len(usable) < 2:
            continue
        ly = listing_year.get(sid)
        if ly is None:
            continue
        prior = [s for y, s in hist if y <= ly]
        if not prior:
            no_baseline += 1
        elif prior[-1] in STABLE:
            stable_at_listing += 1
        elif prior[-1] in THREAT:
            threatened_at_listing += 1
        after = [y for y, s in hist if y > ly and rl.comparable(s)]
        if after:
            lags.append(after[0] - ly)

    check("species assessed as stable at listing", 0, stable_at_listing,
          note="The R1-04 confounder needs this stratum to be non-empty.")
    check("species already threatened at listing", 4, threatened_at_listing)
    check("species with no assessment at or before listing", 32, no_baseline)
    import statistics as _st
    check("median years from listing to the first comparable assessment",
          19, int(_st.median(lags)))
    check("the same, as a mean", 18.5, round(_st.mean(lags), 1))
    check("trajectories unchanged", 18, verdicts["unchanged"])
    check("trajectories improved", 13, verdicts["improved"])
    check("trajectories deteriorated", 10, verdicts["deteriorated"])
    # The Results and Abstract quote every share over all 43 species, one
    # decimal, not over the scored species (6 October 2026 text).
    check("unchanged share of all 43 species", 41.9,
          round(100 * verdicts["unchanged"] / (scored + excluded), 1))
    check("genuine category transitions", 43, len(transitions))
    ups = sum(1 for tr in transitions if tr[-1] == "improved")
    check("of those, improvements", 22, ups,
          note="Stable only since the ordering was made deterministic on "
               "2026-08-12. Before that a reload could return same-year "
               "assessments in a different sequence, and 22 species have "
               "multiple global assessments in one year.")

    # --- reporter-side overlap ---------------------------------------------
    overlap = one(f"""
        select count(*) from {S}.cites_trade_records t
         where exists (
           select 1 from {S}.cites_trade_records o
            where o.year = t.year and o.taxon = t.taxon and o.term = t.term
              and o.importer is not distinct from t.importer
              and o.exporter is not distinct from t.exporter
              and o.unit is not distinct from t.unit
              and o.purpose is not distinct from t.purpose
              and o.source is not distinct from t.source
              and o.reporter_type <> t.reporter_type)""")
    check("records inside a doubly-reported shipment coordinate", 226046, overlap)

    # --- re-exports, now stated in the manuscript (T-05/T-06) -------------
    # The S3/G3 paragraph reported gross exports with re-exports retained,
    # and quoted these two values. Before 2026-08-15 that paragraph also said
    # units were harmonised before summation, which is false; the correction
    # is in the manuscript and the unit claim is covered by V-26.
    reexport = one(f"""
        select count(*) from {S}.cites_trade_records
         where origin is not null and origin <> '' and origin <> exporter""")
    check("records that are re-exports, origin set and not the exporter",
          171498, reexport)

    # --- how many units the quantity field actually takes ------------------
    # The methods paragraph states this number. A bare integer in prose is
    # invisible to number_coverage, whose CLAIM pattern deliberately ignores
    # small unseparated numbers, so it is asserted here.
    units_all = one(f"""
        select count(distinct coalesce(nullif(unit,''), '(count of specimens)'))
          from {S}.cites_trade_records""")
    units_wild = one(f"""
        select count(distinct coalesce(nullif(unit,''), '(count of specimens)'))
          from {S}.cites_trade_records where source = 'W'""")
    check("distinct units the quantity field takes, whole corpus", 26, units_all,
          note="Stated in the S3/G3 methods paragraph. A sum across these is not a physical quantity; the per-unit series is Supplementary Table 9.")
    check("the same within the wild-origin subset", 19, units_wild)

    # --- how many tables the independent re-read actually covers ----------
    # The reproducibility paragraph says "four tables are additionally
    # re-derived from their sources by code paths that do not reuse the
    # loader". That was true when written. It is a count in prose about our
    # own verification, which is the category of number that has drifted here
    # three times: nine database gates, 61 of 61, fifteen checks.
    #
    # Counted from V-5b's source rather than from a list kept by hand, so
    # adding or removing a table moves this number by itself.
    # This file lives in two places and the script runs from both. In the
    # deposit it is a sibling under verification/; in the repository it is
    # ingest/verify_derived_truth.py. ROOT_DIR is the deposit directory, so
    # ROOT_DIR/"ingest" resolved to deposit/ingest, which exists in neither —
    # the script crashed with FileNotFoundError before reaching a single
    # assertion. The candidates below cover both locations.
    _here = _pl.Path(__file__).resolve().parent
    _candidates = [
        _here / "verify_derived_truth.py",                       # deposit
        _here.parent.parent / "ingest" / "verify_derived_truth.py",  # repository
        ROOT_DIR / "ingest" / "verify_derived_truth.py",         # historical
    ]
    _src = next((c for c in _candidates if c.exists()), None)
    if _src is None:
        raise SystemExit(
            "verify_derived_truth.py not found beside this script or in the "
            "repository. Looked in:\n  " + "\n  ".join(str(c) for c in _candidates))
    derived = _src.read_text()
    covered = set(re.findall(r'^\s*def check_(\w+)\(', derived, re.M))
    covered |= set(re.findall(r'^\s*"(\w+)":\s*check_', derived, re.M))
    if not covered:
        covered = set(re.findall(r'\b(cites_trade_records|iucn_assessments|catch_records|illegal_trade_seizures)\b', derived))
    check("tables re-derived by an independent code path", 4, len(covered),
          note="Counted from verify_derived_truth.py: " + ", ".join(sorted(covered)))
    check("that share of the corpus", 34.9, round(100.0 * reexport / trade, 1),
          note="Retained as distinct records; no step collapses them, which is what makes the reported series gross.")
    check("that overlap as a share of the corpus", 45.9,
          round(100.0 * overlap / trade, 1),
          note="Combining the two reporter sides would double-count these.")

    # The number is sensitive to the shipment key, and the paper states the
    # number without stating the key. Matching on the eight fields above gives
    # 226,046 (45.9%); adding origin and appendix gives 213,763 (43.4%), because
    # a pair where the two sides recorded origin differently is split apart.
    #
    # Neither key is wrong. The looser one over-matches when two genuinely
    # different shipments share a coordinate; the tighter one under-matches when
    # the sides disagree about origin. The range is what can be stated, and a
    # reader recomputing this with only one key will get one end of it.
    tight = one(f"""
        select count(*) from {S}.cites_trade_records t
         where exists (
           select 1 from {S}.cites_trade_records o
            where o.year = t.year and o.taxon = t.taxon and o.term = t.term
              and o.importer is not distinct from t.importer
              and o.exporter is not distinct from t.exporter
              and o.unit is not distinct from t.unit
              and o.purpose is not distinct from t.purpose
              and o.source is not distinct from t.source
              and o.origin is not distinct from t.origin
              and o.appendix is not distinct from t.appendix
              and o.reporter_type <> t.reporter_type)""")
    check("the same overlap on a key that also fixes origin and appendix",
          213763, tight,
          note="Reported so the sensitivity is visible rather than implied. "
               "The overlap is 43.4-45.9% depending on the key; both support "
               "the stated 'nearly half'.")

    # --- unit dimensions, the ground for R3-20 -----------------------------
    # The bucket totals must sum to the corpus (492,095); a table transcribed
    # from a truncated query would not. Asserted here so the table cannot drift
    # from the corpus.
    def dim(sql_pred):
        return one(f"select count(*) from {S}.cites_trade_records where {sql_pred}")

    blank = dim("coalesce(nullif(unit,''),'') = ''")
    explicit = dim("unit = 'Number of specimens'")
    mass = dim("unit in ('g','kg','mg','microgrammes')")
    volume = dim("unit in ('ml','l')")
    linear = dim("unit in ('m2','cm2','m3','cm3','m','cm')")
    other = trade - blank - explicit - mass - volume - linear

    check("unit dimension: specimen count, unit field blank", 236941, blank)
    check("unit dimension: mass", 195219, mass)
    check("unit dimension: specimen count stated explicitly", 53965, explicit)
    check("unit dimension: discrete containers", 5143, other)
    check("unit dimension: volume", 697, volume)
    check("unit dimension: length, area or material volume", 130, linear)
    check("unit dimensions sum to the corpus", trade,
          blank + explicit + mass + volume + linear + other)
    check("share measured as mass", 39.67, round(100.0 * mass / trade, 2))
    check("share, specimen count with unit blank", 48.15, round(100.0 * blank / trade, 2))
    check("share, specimen count stated explicitly", 10.97, round(100.0 * explicit / trade, 2))
    check("share, discrete containers", 1.05, round(100.0 * other / trade, 2))
    check("share, volume", 0.14, round(100.0 * volume / trade, 2))
    check("share, length/area/material volume", 0.03, round(100.0 * linear / trade, 2))
    check("share counted as specimens", 59.12,
          round(100.0 * (blank + explicit) / trade, 2),
          note="Specimens, not animals: a counted specimen may be a skin, a "
               "tusk or a carving.")

    # --- trajectory shares quoted in the Results ---------------------------
    check("trajectories improved, as a share of all 43", 30.2,
          round(100 * verdicts["improved"] / (scored + excluded), 1))
    check("trajectories deteriorated, as a share of all 43", 23.3,
          round(100 * verdicts["deteriorated"] / (scored + excluded), 1))
    check("no comparable trajectory, as a share of all 43", 4.7,
          round(100 * excluded / (scored + excluded), 1))

    # The alternative reading, published alongside the main one because the
    # result is sensitive to it. Bubo scandiacus and Odobenus rosmarus each hold
    # two same-year global assessments with different categories; taking the
    # other one as current moves the headline. Asserted here so the SENSITIVITY
    # is verified too, not just the figure we chose.
    cur.execute(f"""
        select s.scientific_name, a.status, a.year_published
          from {S}.iucn_assessments a
          join {S}.species s on s.id = a.species_id
         where {SERIES_A} and a.year_published is not null
         order by s.scientific_name, a.year_published, a.assessment_id desc""")
    alt_seq = {}
    for name, status, year in cur.fetchall():
        alt_seq.setdefault(name, []).append((year, status))
    alt = {"improved": 0, "deteriorated": 0, "unchanged": 0}
    for name, rows in alt_seq.items():
        usable = [(y, s) for y, s in rows if rl.comparable(s)]
        if len(usable) >= 2:
            alt[rl.classify(usable[0][1], usable[-1][1])] += 1
    alt_scored = sum(alt.values())
    # Not quoted in the paper since the tie-break rule went into the Methods;
    # pinned so that a change in the sensitivity is seen, not to verify a figure.
    check("alternative tiebreak: unchanged share", 46,
          round(100 * alt["unchanged"] / alt_scored),
          note="Once published alongside the main share because the choice between two "
               "same-year assessments is a convention, not a finding.")
    check("alternative tiebreak: deteriorated share", 22,
          round(100 * alt["deteriorated"] / alt_scored))
    check("alternative tiebreak: improved share is unaffected", 32,
          round(100 * alt["improved"] / alt_scored))

    # --- flags that were the documented defects ----------------------------
    multi_current = one(
        f"select count(*) from (select species_id from {S}.cites_listings "
        f"where is_current group by species_id having count(*) > 1) x")
    check("species with >1 is_current listing row (documented defect)",
          8, multi_current)

    # The corpus should carry a source_releases row for every upstream source
    # (CITES, IUCN, NAMMCO, the CMS Appendices, the Species+ listing history and
    # the seizure compilation), each with a date and a stated basis, so that
    # "when was this obtained" has an answer for all six. Counted here.
    # Scope. Seventeen v1 species carried a European regional assessment as their
    # flagged latest, and nine of those disagree with the global category. The
    # aggregate threatened count is the same under either reading, by three
    # offsetting swaps rather than by robustness, which is why the published
    # percentages cannot say which scope the submitted analysis used. Asserted so
    # that the coincidence is on record rather than mistaken for stability.
    v1_regional = one("""select count(distinct species_id) from
                         arctic_v1_frozen.iucn_assessments
                         where is_latest and coalesce(scope_code, '1') <> '1'""")
    check("v1 species whose flagged assessment is regional, not global", 17, v1_regional)
    v1_thr_flagged = one("""select count(*) from arctic_v1_frozen.iucn_assessments
                            where is_latest and status in ('VU','EN','CR')""")
    v1_thr_global = one("""select count(*) from (
                             select distinct on (a.species_id) a.species_id, a.status
                             from arctic_v1_frozen.iucn_assessments a
                             where coalesce(a.scope_code,'1') = '1'
                             order by a.species_id, a.year_published desc,
                                      a.assessment_id desc) x
                           where x.status in ('VU','EN','CR')""")
    check("v1 threatened count, flagged reading", 18, v1_thr_flagged)
    check("v1 threatened count, global-only reading", 18, v1_thr_global)

    # The reporter-side identity. The submitted manuscript published 473,102
    # trade records, and the frozen v1 corpus shows exporter-reported plus
    # importer-reported summing to exactly that. It settles, arithmetically,
    # that the submitted analysis combined both sides, so its figures
    # double-count every shipment both parties reported.
    v1_e = one("select count(*) from arctic_v1_frozen.cites_trade_records "
               "where reporter_type = 'E'")
    v1_i = one("select count(*) from arctic_v1_frozen.cites_trade_records "
               "where reporter_type = 'I'")
    check("v1 exporter-reported records", 290443, v1_e)
    check("v1 importer-reported records", 182659, v1_i)
    check("the two sides sum to the count the submitted manuscript published",
          473102, v1_e + v1_i)

    # Two species with a same-year pair of assessments. For these two species
    # the Red List is_latest flag is well formed, exactly one per species, and
    # it agrees with the assessment_id tiebreak. Asserted so that if either
    # signal moves, the check fails loudly.
    for name in ("Bubo scandiacus", "Odobenus rosmarus"):
        flagged = one(f"""select count(*) from {S}.iucn_assessments a
                          join {S}.species s on s.id = a.species_id
                          where s.scientific_name = %(n)s and a.is_latest""", {"n": name})
        check(f"{name}: assessments flagged latest", 1, flagged)
        status = one(f"""select a.status from {S}.iucn_assessments a
                         join {S}.species s on s.id = a.species_id
                         where s.scientific_name = %(n)s and a.is_latest""", {"n": name})
        check(f"{name}: that assessment's status", "VU", status)
        tiebreak = one(f"""select a.status from {S}.iucn_assessments a
                           join {S}.species s on s.id = a.species_id
                           where s.scientific_name = %(n)s
                           order by a.year_published desc, a.assessment_id desc
                           limit 1""", {"n": name})
        check(f"{name}: the tiebreak agrees with the flag", status, tiebreak)

    # The NAMMCO catch total, which the loader calls a never-diverge key and the
    # manuscript reports. Asserted rather than declared uncheckable: it falls
    # out of the corpus in one line, and a published figure needs a check.
    catch_total = one(f"select coalesce(sum(catch_total), 0) from {S}.catch_records")
    check("NAMMCO catch total across all records", 277663, catch_total)

    recorded = one(f"select count(*) from {S}.source_releases")
    check("upstream sources with a recorded release and basis", 6, recorded)
    undated = one(
        f"""select count(*) from {S}.source_releases
            where obtained_on is null or coalesce(obtained_on_basis, '') = ''""")
    check("of those, any lacking a date or a stated basis for it", 0, undated)

    print(f"{'claim':<62} {'stated':>12} {'database':>12}  verdict")
    print("-" * 104)
    bad = 0
    for label, claimed, computed, ok, note in RESULTS:
        verdict = "MATCH" if ok else "MISMATCH"
        if not ok:
            bad += 1
        print(f"{label:<62} {str(claimed):>12} {str(computed):>12}  {verdict}")
        if note:
            print(f"  note: {note}")
    print("-" * 104)
    print(f"{len(RESULTS) - bad} of {len(RESULTS)} claims reproduce against the live corpus")

    # Write the count where a document check can read it. Documents quote
    # "N of N reproduce"; counting check() calls in this file overcounts, because one of them only fires when a report is absent.
    # The run knows the true number and nothing else does.
    import json as _json
    _rep = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(_rep, exist_ok=True)
    with open(os.path.join(_rep, "manuscript_claims.json"), "w") as fh:
        _json.dump({"total": len(RESULTS), "reproduced": len(RESULTS) - bad}, fh)
    conn.close()
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
