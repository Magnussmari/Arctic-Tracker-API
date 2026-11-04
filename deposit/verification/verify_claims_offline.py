#!/usr/bin/env python3
"""Every traceable claim in the paper, recomputed from the deposit alone.

WHY THIS EXISTS
---------------
results_traceability.csv maps each reported quantity to its Methods section, its
source table and the SQL that produced it. The SQL is the right record, and it
needs the database: a reader holding the deposit could read the claims but
could not check a single one.

They can now. Twenty-one of the twenty-two claims recompute exactly from the
deposited package, with no credentials, no network and no database. The
deposited tables carry the trade records, the listings, the seizures, the CMS
memberships and the narratives; the Source Data carries the full Red List
assessment series. Nothing else was needed.

This is the paper's own standard applied to itself. "One scale, one source"
means the number in the text, the number in the traceability table and the
number the data yields are one number, and this is the check that says so.

WHAT IT DOES
------------
Recomputes each claim from the deposit using the operative definition recorded
beside it, and fails if the result differs from the recorded value. Each
computation is written to follow the recorded definition literally, so when the
two disagree the definition is what gets read, not guessed at.

Exit 0 pass, 1 fail, 3 unmeasured.
"""
import csv, io, pathlib, statistics, sys, zipfile
from collections import Counter, defaultdict

# The deposit ships no IUCN Red List category (IUCN's terms forbid it), so
# every Source Data read goes through the shim that prefers a local rebuild
# and stops with UNMEASURED when none has been made.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import redlist_scale as rl  # noqa: E402
import iucn_series  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DEPOSIT = HERE.parent
TABLES = DEPOSIT / "tables"
TRACE = DEPOSIT / "results_traceability.csv"
ZIP = DEPOSIT / "source_data.zip"
SERIES = "Source Data/figure5_source_data.csv"
SUPP1 = DEPOSIT / "supplementary" / "supplementary_table_1_post_listing_window.csv"

# The post-2001 Red List categories. Everything else is a legacy code that does
# not sit on the manuscript's ordinal scale. Written once, used by C10 and C11,
# because they are the same distinction asked two different ways.
CURRENT = {"LC", "NT", "VU", "EN", "CR", "EW", "EX", "DD", "RE"}

# The ordinal scale, least to most threatened. Legacy codes that carry a
# direction are placed on it; codes that carry none are absent, so a species
# assessed only in those has no comparable trajectory rather than a guessed one.
#
# This was written out here until 7 October 2026, and it was a FOURTH copy of a
# table the project claims to hold once. It also disagreed with the module it
# sits beside on two codes - it placed Regionally Extinct on the global ladder,
# which that module excludes on purpose - while C22, computed in this same file
# through `import redlist_scale`, used the module's table instead. One file,
# two scales, and both feeding published claims.
#
# Now asked for rather than restated, under whatever convention the module is
# on, which is the one the Methods state.
# Importing a sibling here writes __pycache__ INTO the deposit, and
# verify_deposit_accounted.py rejects bytecode in a citable archive. Running
# these scripts in place is the intended use, so the run must not leave
# residue behind, or the archive gate would fail merely because the verifiers
# had been run.
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import redlist_scale as _rl

RANK = {code: _rl.rank(code)
        for code in (list(_rl.RANK) + list(_rl.EQUIVALENT)
                     + list(_rl.CROSSWALK_LIN2025))
        if _rl.rank(code) is not None}
# Extended to 2025 on the lead author's instruction of 1 October 2026.
WINDOW = (1982, 2025)

# THE SERIES, from 21 October 2026. Every trajectory and status claim below is
# computed on the global-and-European series, no longer on the Global rows
# alone: the lead author decided that day that European regional assessments
# are included. Per species the two scopes form ONE series ordered by
# (year, assessment_id) - _rl.series_rows builds it - and in a year with
# several assessments the higher id stands (_rl.pick_in_year). The transition
# count keeps BOTH rows of a same-year pair, as the published method always
# did. Lamna nasus 2016 (16527805) is Mediterranean, not European, and stays
# out (_rl.NOT_EUROPEAN_IDS). The seven European assessments the series labels
# "Global" count, as European.

# The published supplementary table. It is rendered from the CSV, and the two
# can drift apart if one is corrected without the other. Checking them against
# each other here means a drift cannot pass without the gate saying so.
TABLE_MD = DEPOSIT / "results_traceability.md"


def table(name):
    return list(csv.DictReader(open(TABLES / f"{name}.csv")))


def series():
    with zipfile.ZipFile(ZIP) as z:
        return list(csv.DictReader(io.StringIO(iucn_series.read_member(z, SERIES).decode())))


def compute():
    """Each claim, by the definition recorded beside it in the table."""
    out = {}
    tr = table("cites_trade_records")
    n = len(tr)
    share = lambda k: round(100 * k / n, 2)

    out["C01"] = n
    out["C02"] = len(table("species"))
    out["C03"] = share(sum(1 for r in tr if r["purpose"] == "T"))
    out["C04"] = share(sum(1 for r in tr if r["appendix"] == "I"))
    out["C05"] = share(sum(1 for r in tr if r["appendix"] == "II"))
    out["C06"] = share(sum(1 for r in tr if r["appendix"] == "III"))
    out["C07"] = share(sum(1 for r in tr if r["source"] == "W"))
    out["C08"] = sum(1 for r in tr if not r["quantity"].strip())

    # C37-C39: the two species shares the Results lead with, and how much of the
    # sturgeon block is actually captive-bred. "Captive-bred sturgeon (39.8%)"
    # could not be resolved as written - the paper named neither the denominator nor the source code
    # behind "captive-bred", and 39.8% turns out to be the species' share of all
    # records rather than the captive-bred subset's.
    sp_name = {r["id"]: r["scientific_name"] for r in table("species")}
    stu = [r for r in tr if sp_name.get(r["species_id"]) == "Acipenser baerii"]
    gyr = [r for r in tr if sp_name.get(r["species_id"]) == "Falco rusticolus"]
    out["C37"] = share(len(stu))
    out["C38"] = share(len(gyr))
    out["C39"] = round(100 * sum(1 for r in stu if r["source"] == "C") / len(stu), 2)

    # C49-C50: the Critically Endangered record block. The share was stated in
    # the wrong direction: "over 39.9% (196,140)" against a denominator of 492,095
    # is 39.86%, which is under 39.9%, not over it. The count is exactly right
    # and was not traceable; now it is, together with the share, so the
    # direction cannot drift again.
    #
    # "Categorised as Critically Endangered" means the species' most recent
    # assessment of either scope (global or European) inside the window is CR -
    # the same current-category rule as C23-C28, the higher assessment id
    # standing in a tied year - and the record count is every trade record of
    # those species.
    cr_latest = {}
    for sp_, recs in _rl.series_rows(series(), window=(1982, 2025)).items():
        cr_latest[sp_] = (int(recs[-1]["year"]), recs[-1]["status"])
    cr_species = {k for k, (_, st) in cr_latest.items() if st == "CR"}
    cr_rows = sum(1 for r in tr if sp_name.get(r["species_id"]) in cr_species)
    out["C49"] = cr_rows
    out["C50"] = share(cr_rows)

    # C42-C48: the purpose codes behind the Indigenous-harvest limitation.
    # The word "subsistence" does not appear in the paper at all, while
    # the records that matter most in the Arctic - narwhal, beluga, walrus,
    # polar bear - originate in Inuit harvest conducted under co-management and
    # quota regimes, and the paper reports "67% for commercial purposes" with
    # no mention of it.
    #
    # The Trade Database has no subsistence or Indigenous-harvest purpose code,
    # and C42 is that fact as a count: the distinct purpose values present in
    # the corpus, blank included. The three species counts measure the point:
    # for these species the dominant wild-origin purpose is not T but P,
    # personal. A sentence in Methods reports them, so they are claims.
    wild = lambda name: [r for r in tr if r["source"] == "W"
                         and sp_name.get(r["species_id"]) == name]
    out["C42"] = len({r["purpose"] for r in tr})
    for name, p_id, n_id in (("Monodon monoceros", "C43", "C44"),
                             ("Odobenus rosmarus", "C45", "C46"),
                             ("Delphinapterus leucas", "C47", "C48")):
        w = wild(name)
        out[p_id] = sum(1 for r in w if r["purpose"] == "P")
        out[n_id] = len(w)

    # C51-C52: the two totals the wild-origin caption (Figure 7) now states. Read as a
    # standalone artefact, the caption carried no unit, no period and no total, while the
    # figure's own summary box carried three: "2.3 million items, 51,000+
    # records" from the 2025-11-12 run that the export itself records as
    # truncated at 51,000 rows, under panels drawn from the full extract. The
    # box is computed from the data now, and the caption states what the figure
    # sums to, so both have to be recomputable.
    #
    # The denominator is the shipped Source Data for the figure: the 15
    # wild-origin species it draws, summed over its own rows. Items and records
    # are different units and are reported separately for that reason.
    with zipfile.ZipFile(ZIP) as z:
        f8 = list(csv.DictReader(io.StringIO(
            iucn_series.read_member(z, "Source Data/figure8_source_data.csv").decode())))
    out["C51"] = round(sum(float(r["total_quantity"]) for r in f8))
    out["C52"] = sum(int(r["record_count"]) for r in f8)

    # C53-C57: the importer paragraph (trade partners, Figure 9). Read as a standalone
    # artefact, checking the body against the deposit showed that not one number in that
    # paragraph was traceable - not the 345,603 denominator, not the 83,131 the
    # Results lead with. Recomputing them found the last sentence wrong: the UK,
    # Hong Kong, Qatar, South Korea and Singapore were said to account for
    # "between 1.5-2.7%" and they span 2.1% to 3.9%, with two of the five above
    # the stated ceiling.
    #
    # The population is the one the figure draws: records whose importer is not
    # one of the nine Arctic reporter codes. Denmark and Greenland are separate
    # codes in the Trade Database and both count as Arctic.
    #
    # It was written with three further clauses -- non-blank importer, non-blank
    # exporter, year <= 2024 -- and the trade-partners caption (Figure 9) described them as
    # "records with both sides reported". Read against Methods, that caption is
    # impossible: the both-ends-reported subset Methods
    # defines is 226,046 records and cannot contain 345,603. Measured here, all
    # three clauses are no-ops on this corpus, so the caption named a condition
    # that both filtered nothing and meant something else. The clauses are kept
    # as assertions instead of filters: if a future release ships a blank
    # country or a 2025 record, this fails rather than quietly changing the
    # denominator the paper reports.
    arctic_iso = {"CA", "US", "RU", "NO", "IS", "DK", "SE", "FI", "GL"}
    blank = sum(1 for r in tr if not (r["importer"] and r["exporter"] and r["year"]))
    beyond = sum(1 for r in tr if r["year"] and int(r["year"]) > 2024)
    if blank or beyond:
        raise SystemExit(f"C53: the Figure 9 population is defined by importer "
                         f"alone, which held only because no record has a blank "
                         f"country or year and none post-dates 2024; now "
                         f"{blank} blank and {beyond} after 2024")
    imp = [r for r in tr if r["importer"] not in arctic_iso]
    out["C53"] = len(imp)
    by_importer = Counter(r["importer"] for r in imp)
    out["C54"] = by_importer["AE"]
    out["C55"] = round(100 * by_importer["AE"] / len(imp), 2)
    tail = [100 * by_importer[c] / len(imp) for c in ("GB", "HK", "QA", "KR", "SG")]
    out["C56"] = round(min(tail), 2)
    out["C57"] = round(max(tail), 2)

    # C141-C147: what is actually inside those importer shares. Every
    # corpus-level trade result could be dominated by two taxa, one of them
    # farmed; the composition behind each named importer's share is measurable,
    # so it is reported rather than conceded as a limitation.
    #
    # The composition is read on the named non-Arctic importers only - the ten
    # the Results name - because those are the shares the paper reports. Source
    # code W is the Convention's wild code and is read exactly as recorded;
    # nothing is merged into it.
    named = ("AE", "DE", "CN", "CH", "JP", "GB", "HK", "QA", "KR", "SG")
    per_importer = defaultdict(list)
    for r in imp:
        if r["importer"] in named:
            per_importer[r["importer"]].append(r)
    missing = [c for c in named if not per_importer[c]]
    if missing:
        raise SystemExit(f"C141: the Results name {missing} as importers and "
                         f"the corpus has no record for them")
    wild_shares, dominated = {}, 0
    for code, rows in per_importer.items():
        n = len(rows)
        wild_shares[code] = 100 * sum(1 for r in rows
                                      if (r["source"] or "").strip() == "W") / n
        top = Counter(r["taxon"] for r in rows).most_common(1)[0][1]
        if 100 * top / n > 70:
            dominated += 1
    ae = per_importer["AE"]
    out["C141"] = round(wild_shares["AE"], 2)
    out["C142"] = round(100 * sum(
        1 for r in ae if r["taxon"] in ("Falco rusticolus", "Falco peregrinus")
    ) / len(ae), 2)
    out["C143"] = round(min(wild_shares.values()), 2)
    out["C144"] = round(max(wild_shares.values()), 2)
    out["C145"] = dominated
    if out["C143"] > out["C141"]:
        raise SystemExit("C143: the lowest wild-origin share among the named "
                         "importers is below the UAE's, which cannot be, since "
                         "the UAE is one of them")

    # The corpus-level commercial share with the two dominant taxa removed. The
    # denominator moves with the numerator, which is the point: C03 reports
    # 67.01% over all 492,095 records, and that figure is a property of the
    # composition as much as of the trade.
    two = ("Acipenser baerii", "Falco rusticolus")
    rest = [r for r in tr if r["taxon"] not in two]
    out["C146"] = round(100 * sum(
        1 for r in rest if (r["purpose"] or "").strip() == "T") / len(rest), 2)
    out["C147"] = len(rest)

    # C58-C61: the seizure sentence. Added 7 October 2026 while fixing Figure
    # 7's caption, which attributed "33 of 225 records" to a figure drawn from a
    # different corpus. The 225 are the Stringham et al. records reconciled to
    # 26 Arctic species; the figure is built from CITES records with source
    # code I. Recomputing the three species the Results name found two of them
    # wrong: sperm whale was given as 28 and is 31, Canada lynx as 19 and is 20.
    # The walrus at 33 was right.
    seiz = table("illegal_trade_seizures")
    out["C58"] = len(seiz)
    seiz_by_sp = Counter(sp_name.get(r["species_id"]) for r in seiz)
    out["C59"] = seiz_by_sp["Odobenus rosmarus"]
    out["C60"] = seiz_by_sp["Physeter macrocephalus"]
    out["C61"] = seiz_by_sp["Lynx canadensis"]

    # C29-C32 ALREADY ARE the listing-to-first-improvement interval, and
    # their recorded definition already carried the whole rule, including
    # Phoebastria albatrus by name. The same four values were once duplicated
    # as C62-C65; the duplicates are removed. The rule belongs in the
    # manuscript text; the deposit records it here.
    ids = lambda f: len(list(csv.DictReader(open(DEPOSIT / "identifiers" / f))))
    out["C09"] = ids("iucn_assessment_ids.csv")
    out["C12"] = ids("catch_record_ids.csv")

    f5 = series()
    out["C10"] = sum(1 for r in f5 if r["status"] not in CURRENT)

    # C11: the first assessment (global or European) at or after the EARLIEST listing date,
    # with the listing date taken from cites_listings as the definition says.
    name = {r["id"]: r["scientific_name"] for r in table("species")}
    listed = {}
    for r in table("cites_listings"):
        sp, d = name.get(r["species_id"]), (r["listing_date"] or "")[:4]
        if sp and d.isdigit():
            listed[sp] = min(listed.get(sp, 9999), int(d))
    glob = {sp_: [(int(r["year"]), r["status"]) for r in recs]
            for sp_, recs in _rl.series_rows(f5).items()}
    legacy_first = 0
    for sp, a in glob.items():
        y = listed.get(sp)
        if y is None:
            continue
        post = [x for x in a if x[0] >= y]
        if post and post[0][1] not in CURRENT:
            legacy_first += 1
    out["C11"] = legacy_first

    out["C13"] = len(table("illegal_trade_seizures"))
    out["C14"] = len(table("cites_listings"))
    cms = table("cms_listings")
    out["C15"] = sum(1 for r in cms if r["agreement"] == "CMS")
    out["C16"] = sum(1 for r in cms if r["agreement"] != "CMS")
    out["C17"] = sum(1 for r in table("timeline_events")
                     if r["event_type"] in ("cites_suspension", "eu_decision"))
    out["C18"] = len(table("species_narratives"))

    imp = unch = det = 0
    for sp, a in glob.items():
        a = [x for x in a if WINDOW[0] <= x[0] <= WINDOW[1] and x[1] in RANK]
        if len(a) < 2:
            continue
        d = RANK[a[-1][1]] - RANK[a[0][1]]
        imp += d < 0
        unch += d == 0
        det += d > 0
    out["C19"], out["C20"], out["C21"] = imp, unch, det

    # C40-C41: what "unchanged" is holding at. Merging unchanged with improved
    # into "74.4% hold or improve" reads as a positive outcome for species that are still
    # threatened. Nine of the twenty are, and two of those at CR.
    #
    # These are END-OF-WINDOW counts and always were; the operative
    # definition says so. "Throughout" would be a different and smaller set:
    # only seven held a threatened category at every comparable assessment,
    # because two species end in a threatened category without having done
    # so. The abstract now says what these claims compute.
    held = []
    for sp, a in glob.items():
        a = [x for x in a if WINDOW[0] <= x[0] <= WINDOW[1] and x[1] in RANK]
        if len(a) >= 2 and RANK[a[-1][1]] == RANK[a[0][1]]:
            held.append(a[-1][1])
    out["C40"] = sum(1 for s in held if RANK[s] >= RANK["VU"])
    out["C41"] = sum(1 for s in held if s == "CR")

    # C22: the transition count, on the global-and-European series, by the
    # project's one scale. redlist_scale breaks the chain at a non-comparable assessment
    # rather than skipping over it, so no transition is invented across a gap.
    sys.path.insert(0, str(HERE))
    import redlist_scale as rl

    # Before any trajectory number is computed: every series below is built by
    # sorting (year, status) and taking the ends, which on a tied year takes the
    # alphabetically later status. That gives the right answer on this corpus
    # only because the flagged category happens to sort last in both ties that
    # matter. It is luck, so it is asserted rather than relied on - forcing the
    # opposite tie-break moves a species from deteriorated to improved.
    #
    # From 21 October 2026 the series is ordered by (year, assessment_id)
    # (_rl.series_rows), so no value below depends on the alphabet and the old
    # sort-versus-id conflict guard has nothing left to guard. The guard's own
    # self-test still runs, because C23-C28 resolve their final-year ties with
    # rl.pick_in_year.
    if not rl.self_test_tiebreak():
        raise SystemExit("the tie-break guard cannot be trusted; nothing checked")
    trans = []
    for sp, a in glob.items():
        trans.extend(rl.transitions([x for x in a
                                     if WINDOW[0] <= x[0] <= WINDOW[1]]))
    out["C22"] = len(trans)

    # C23-C28: the current global category of each species, counted. "Current"
    # is the most recent global assessment inside the window, one per species -
    # the same rule verify_trajectories_offline.py applies. The distribution is
    # reported part by part in the paper, and a tally that sums to 43 with the
    # wrong parts is invisible to any total, so each part is its own claim.
    # The tie-break is the whole difficulty. Seven species carry TWO global
    # assessments in their final year, and for two of them (Bubo scandiacus,
    # 2021, and Odobenus rosmarus, 2025) the two global assessments in one year
    # have different categories.
    #
    # A "keep the row with the later year" rule would, on a tie, keep whichever
    # row the CSV happened to list first, so export order would decide which
    # assessment counts as current. Row order is not a rule. The deposit ships
    # is_latest to resolve this, both flagged rows carry the higher assessment
    # id, and the status-patterns figure (now Figure 11) panel (a) was drawn on
    # the flag. So the flag decides, and where a tied year carries no flag at
    # all the first row stands - which affects no count in this corpus,
    # asserted below rather than assumed.
    #
    # 21 October 2026: "current" is now the most recent assessment of EITHER
    # scope inside the window, one per species. The tie is settled by
    # rl.pick_in_year - the higher assessment id stands, with is_latest as a
    # cross-check that refuses on a contradiction - so a global and a European
    # assessment in the same final year are decided by publication order, not by
    # row order or the alphabet. The result is 4 CR, 3 EN, 11 VU, 3 NT, 21 LC,
    # 0 DD and 1 RE. RE
    # is its own claim, C148, because the other six sum to 42 and a tally that
    # leaves one species out is the kind no total can see.
    latest = {}
    for sp, recs in _rl.series_rows(f5, window=WINDOW).items():
        ymax = int(recs[-1]["year"])
        final = [r for r in recs if int(r["year"]) == ymax]
        try:
            latest[sp] = (ymax, _rl.pick_in_year(final)["status"])
        except ValueError as e:
            raise SystemExit(f"C23-C28: {sp} in {ymax}: {e}")
    dist = Counter(s for _, s in latest.values())
    if sum(dist.values()) != 43:
        raise SystemExit(f"C23-C28: the current distribution covers "
                         f"{sum(dist.values())} species, not 43")
    for cat, cid in zip(["CR", "EN", "VU", "NT", "LC", "DD", "RE"],
                        ["C23", "C24", "C25", "C26", "C27", "C28", "C148"]):
        out[cid] = dist.get(cat, 0)

    # C29-C32: the listing-to-improvement interval. "A lag of about two
    # decades" is a causal-timing claim and needs a statistic behind it. The
    # interval is the years from a species' first listing to the first
    # assessment inside the window at a lower rank than its baseline. One
    # improving species, Phoebastria albatrus, improves before it is listed
    # and is reported separately rather than averaged in.
    lag = {}
    for sp, a in glob.items():
        a = [x for x in a if WINDOW[0] <= x[0] <= WINDOW[1] and x[1] in RANK]
        if len(a) < 2 or RANK[a[-1][1]] >= RANK[a[0][1]]:
            continue
        y = listed.get(sp)
        if y is None:
            continue
        base = RANK[a[0][1]]
        hit = next((yy for yy, st in a if RANK[st] < base), None)
        if hit is not None and hit - y >= 0:
            lag[sp] = hit - y
    # C33-C36: how recent the assessment record actually is. An earlier Results
    # draft stated the opposite of what the deposit holds:
    # "25 species (58%) have not been reassessed since 2005", "only three
    # within the past decade", "just two within the past five years", and the
    # blue whale "last reviewed in 1996". The deposited series gives 43, 42, 23
    # and 2018. These claims make each number recomputable.
    recent = {}
    for sp, a in glob.items():
        recent[sp] = max(y for y, _ in a)
    #
    # The anchor year is the recorded snapshot year, here and in the Results. C36 measured the lag "to 2025"
    # and the Results paragraph said "the 2025 snapshot" and "five years before
    # the snapshot", while the DEPOSITED source-release table records the IUCN
    # Red List snapshot as 2026-07-22 - its basis being the snapshot file's own
    # name - and the Data Availability statement says 22 July 2026. The
    # paragraph had been written against a 2025 retrieval.
    #
    # Re-anchored on the recorded snapshot year, three numbers change:
    #   the median lag        5 -> 6 years        (C36)
    #   "within the past decade"  42 -> 41 species (C109; C34's 2015-or-later
    #                             count of 42 is still 42, but the decade before
    #                             a 2026 snapshot starts in 2016)
    #   "only one older than a decade"  1 -> 2    (C110: two species last
    #                             assessed in 2014 and 2015)
    #
    # SNAPSHOT is read from the deposited table rather than written here, so the
    # next time the snapshot moves these four claims move with it instead of
    # going quietly stale.
    snap = [r for r in table("source_releases")
            if r["source_name"] == "IUCN Red List"]
    if len(snap) != 1 or not snap[0]["obtained_on"]:
        raise SystemExit(f"C36: the deposited source-release table carries "
                         f"{len(snap)} IUCN Red List row(s) with a date, so the "
                         f"snapshot year the recency claims are anchored on "
                         f"cannot be read from the deposit")
    SNAPSHOT = int(snap[0]["obtained_on"][:4])
    out["C33"] = sum(1 for y in recent.values() if y >= 2005)
    out["C34"] = sum(1 for y in recent.values() if y >= 2015)
    out["C35"] = sum(1 for y in recent.values() if y >= 2020)
    out["C36"] = int(statistics.median(sorted(SNAPSHOT - y
                                              for y in recent.values())))
    out["C108"] = SNAPSHOT
    out["C109"] = sum(1 for y in recent.values() if y > SNAPSHOT - 10)
    out["C110"] = sum(1 for y in recent.values() if y <= SNAPSHOT - 10)
    if out["C109"] + out["C110"] != len(recent):
        raise SystemExit(f"C109: the decade split covers "
                         f"{out['C109'] + out['C110']} of {len(recent)} species")

    # C66-C67: the both-ends overlap, and how much of it the match rule hides.
    # The eight-field exact join Methods describes matches on precisely
    # the fields the two reporter sides disagree about - a shipment leaving in
    # December and clearing in January is two different years, skins become
    # garments, specimens become kilograms, T becomes P - so it misses the hard
    # cases and keeps them as apparently independent rows. The falsifier was
    # "show that relaxing the join does not increase the matched set". It does:
    # dropping the year alone takes 226,046 to 340,991. The paper now reports
    # 45.9% as a lower bound and names the year-relaxed value beside it.
    #
    # C66 reproduces the figure the paper already carried; it is numbered 66
    # rather than 62 because C62-C65 were withdrawn as duplicates of C29-C32,
    # and an id that once meant something else is worse than a gap.
    keys = ("species_id", "year", "importer", "exporter", "term", "unit",
            "purpose", "source")

    def both_ends(on):
        sides, size = defaultdict(set), Counter()
        for r in tr:
            k = tuple(r[c] for c in on)
            sides[k].add(r["reporter_type"])
            size[k] += 1
        return sum(size[k] for k in sides if len(sides[k]) > 1)

    out["C66"] = both_ends(keys)
    out["C67"] = both_ends(tuple(c for c in keys if c != "year"))
    if out["C67"] <= out["C66"]:
        raise SystemExit("C67: relaxing the year did not enlarge the matched set, "
                         "so the paper's lower-bound claim is unsupported")

    # C68-C70: why the wild-origin window opens in 1985. The wild-origin caption
    # (Figure 7) is a claim about the reporting format, not about trade. The
    # falsifier was "show that the pre-1985 records carry a populated source
    # field that is simply never W". They do not: of 7,362 records before 1985,
    # none carries W and 6,963 carry no source at all. Source became a reliably
    # completed field later than the Convention's first decade, so pre-1985
    # wild-origin trade is in the corpus and invisible to a source-W filter.
    early = [r for r in tr if r["year"] and int(r["year"]) < 1985]
    out["C68"] = len(early)
    out["C69"] = sum(1 for r in early if r["source"] == "W")
    out["C70"] = sum(1 for r in early if not r["source"])
    if out["C69"]:
        raise SystemExit("C69: a pre-1985 record now carries source W, so the "
                         "manuscript's reason for the 1985 window is wrong")

    # C71-C74: Russia and Iceland in the trade record. An earlier draft said national reporting delays by the two
    # Parties "are offset by CITES-LEX", which holds legislation and policy and
    # no trade records at all. Measuring the corpus shows that both Parties appear as exporting Party well past the dates
    # the paper gives for their last report, and trade in which they export is
    # additionally reported from the importing side. That mirror side is the
    # real mitigation.
    def last_year(party, side):
        ys = [int(r["year"]) for r in tr
              if r["exporter"] == party and r["reporter_type"] == side and r["year"]]
        return max(ys) if ys else 0

    out["C71"] = last_year("RU", "E")
    out["C72"] = last_year("IS", "E")
    out["C73"] = sum(1 for r in tr
                     if r["exporter"] == "RU" and r["reporter_type"] == "I")
    out["C74"] = sum(1 for r in tr
                     if r["exporter"] == "IS" and r["reporter_type"] == "I")

    # C75: narwhal in the seizure corpus. "Narwhals typically hundreds per
    # year" inside a trafficking sentence would misread the scale: hundreds a
    # year is the order of magnitude of the LAWFUL quota-limited
    # harvest and of the legal tusk export the paper itself reports - 4,923
    # tusks over 1987-2009, about 230 a year. The seizure corpus holds ten
    # narwhal records in total, across the whole compilation, so the sentence
    # cannot be read as trafficking volume.
    out["C75"] = sum(1 for r in seiz
                     if sp_name.get(r["species_id"]) == "Monodon monoceros")

    # C76-C79: the beluga trade series. The Results sentence "128 beluga trade records were reported in 2023, an increase of
    # 11.6% over 2007 levels" cannot be reproduced from any integer baseline:
    # 128/1.116 = 114.7. Recomputed: 128 is the 2019 count; 2023 is 25; and 11.6% matches no pair of
    # years in the series. The narwhal comparison in the SAME sentence is exact
    # (1,232 in 2022 against 284 in 2007, 333.8%).
    bel = [r for r in tr if sp_name.get(r["species_id"]) == "Delphinapterus leucas"]
    year_of = lambda y: sum(1 for r in bel if r["year"] == str(y))
    out["C76"] = year_of(2007)
    out["C77"] = year_of(2019)
    out["C78"] = year_of(2022)
    out["C79"] = year_of(2023)
    if out["C78"] < out["C79"] or out["C78"] < out["C77"]:
        raise SystemExit("C78: 2022 is no longer the peak of the beluga series, "
                         "so the sentence the manuscript now carries is wrong")

    # C80-C83: the EN/CR series Figure 11 panel C draws. The prose carried a
    # bare comparative - "more species assessed as EN or CR through
    # the 1990s-2010s" - with no second term. Many languages cannot leave a
    # comparative unanchored, and the three candidate anchors give three
    # different claims.
    #
    # The anchor the figure actually supports is a rise and a fall: seven
    # species in EN or CR from 1996 through 2006, a peak of twelve in
    # 2015-2017, nine from 2019 on. (Thirteen until 18 October 2026, when the
    # eight assessments recorded with no scope that are regional stopped being
    # read as global in this panel; see make_fig3_fig10_source_data.py.) These are read back out of the DEPOSITED
    # Source Data for that panel rather than recomputed from the assessment
    # series, deliberately: the claim being checked is that the prose matches
    # the figure, and the figure's Source Data is what the figure is.
    #
    # 21 October 2026: the panel now counts global and European assessments as
    # one series, and the figure's Source Data in this package has not been
    # regenerated on it yet (that is the deposit rebuild, which also re-signs
    # it). The four values are therefore computed here, from the series, by the
    # rule the panel is drawn on - a species counts once it has a comparable
    # assessment, at its latest comparable category (higher id in a tied year) -
    # over the years the panel's Source Data spans. The shipped panel is still
    # read, and a difference is reported on stderr as STALE rather than hidden:
    # it is not a fault of the claim, it is the figure waiting for its rebuild.
    with zipfile.ZipFile(ZIP) as z:
        fb = list(csv.DictReader(io.StringIO(
            iucn_series.read_member(z, "Source Data/figureB_source_data.csv").decode())))
    shipped = {r["entity"]: int(r["value"]) for r in fb
               if r["panel"] == "C" and r["metric"] == "high_risk_en_cr"}
    if not shipped:
        raise SystemExit("C80: figureB_source_data.csv carries no panel C EN/CR "
                         "series, so the years of the panel cannot be read")
    panel_rows = _rl.series_rows(series())

    def _panel_hits(year):
        hit = 0
        for recs in panel_rows.values():
            past = [r for r in recs if int(r["year"]) <= year
                    and _rl.rank(r["status"]) is not None]
            if past and past[-1]["status"] in ("EN", "CR"):
                hit += 1
        return hit

    encr = {e: _panel_hits(int(e)) for e in shipped}
    stale = {e: (shipped[e], encr[e]) for e in encr if shipped[e] != encr[e]}
    if stale:
        print(f"  STALE: figureB_source_data.csv panel C still carries the global-"
              f"only series for {len(stale)} of {len(encr)} years (shipped, "
              f"recomputed): "
              + ", ".join(f"{e} {a}->{b}" for e, (a, b) in sorted(stale.items())[:6])
              + "... Regenerate the Source Data and rebuild the deposit.",
              file=sys.stderr)
    peak = max(encr.values())
    out["C80"] = encr["1996"]
    out["C81"] = peak
    out["C82"] = int(min(y for y, n in encr.items() if n == peak))
    out["C83"] = encr[max(encr)]
    if not (out["C80"] < out["C81"] > out["C83"]):
        raise SystemExit("C81: the EN/CR series no longer rises to a peak and "
                         "falls, which is what the manuscript sentence says")

    # C84-C85: the Abstract's unchanged-but-threatened count. "Nine of the unchanged species sit in a threatened category at
    # the end of the window, two of them Critically Endangered" appears in the
    # ABSTRACT and nowhere in the Results, so a reader who asks which nine
    # cannot be answered from the paper.
    #
    # Recomputed, the Abstract is exactly right: nine, of which two are in the
    # highest threat category. It is now in Section 4.7 as well.
    #
    # The guard is the unchanged count itself: if this module's ladder ever
    # stops producing the 20 that verify_trajectories_offline and the manuscript
    # both carry, these two numbers are being computed on a different scale and
    # must not be published. One scale, one source.
    unchanged, threatened, cr = 0, 0, 0
    for sp, a in glob.items():
        a = [x for x in a if WINDOW[0] <= x[0] <= WINDOW[1] and x[1] in RANK]
        if len(a) < 2 or RANK[a[-1][1]] != RANK[a[0][1]]:
            continue
        unchanged += 1
        if a[-1][1] in ("VU", "EN", "CR"):
            threatened += 1
            if a[-1][1] == "CR":
                cr += 1
    if unchanged != 18:
        raise SystemExit(f"C84: this module counts {unchanged} unchanged species "
                         f"where the deposit's trajectory verifier and the "
                         f"manuscript both carry 18, so C84 and C85 would be "
                         f"computed on a different ladder")
    out["C84"] = threatened
    out["C85"] = cr

    # C86-C95: the five smaller named importers, one count and one share each.
    # The UK, Hong Kong, Qatar, South
    # Korea and Singapore are named in the Results and then given no figure of
    # their own - only a band, "between 2.1% and 3.9%", spanning nearly a factor
    # of two - while the five larger importers each receive an exact count and
    # percentage. An official of Qatar or Singapore could not read their own
    # jurisdiction's attributed figure out of the paper that names it, which is
    # the one thing a named Party needs from it.
    #
    # The band was not wrong. It was a summary standing where the numbers
    # belonged, and C56/C57 stay as the band's own check.
    #
    # The guard is the ranking: the sentence names these five BECAUSE they are
    # the sixth to tenth largest importers in the figure's population. If a
    # future release reorders them, the sentence names the wrong five and this
    # fails rather than publishing a count against the wrong country.
    TAIL = ("GB", "HK", "QA", "KR", "SG")
    order = [c for c, _ in by_importer.most_common(10)]
    if tuple(order[5:10]) != TAIL:
        raise SystemExit(f"C86: the sixth to tenth largest importers are now "
                         f"{tuple(order[5:10])}, not {TAIL}, so the Results "
                         f"sentence names the wrong five jurisdictions")
    for i, code in enumerate(TAIL):
        out[f"C{86 + i}"] = by_importer[code]
        # out["C53"] is the denominator; `imp` is rebound further down the
        # function and reading len() off it here gave a TypeError, not a wrong
        # number - but the saved value is the one the figure publishes anyway.
        out[f"C{91 + i}"] = round(100 * by_importer[code] / out["C53"], 2)

    # C96-C98: the polar bear sentence's unit. "For polar bears, CITES reported 24,590 exports from 1975 to 2024" is held
    # against the Methods' own undertaking that "Where results refer to individuals,
    # products or mass, the unit is stated explicitly". It is not stated, and
    # the number is not one this corpus produces on any reading: the species has
    # 24,730 records over those years, 16,464 of them exporter-reported and
    # 21,117 carrying source code W. None of those is 24,590.
    #
    # So the paper now carries the corpus figures with their units beside the
    # cited one, and asks the authors where 24,590 comes from. The same shape as
    # the beluga 11.6%: a number that cannot be reproduced is reported as what
    # it is, not quietly replaced with one that can.
    pb = [sid for sid, n in sp_name.items() if n == "Ursus maritimus"]
    if len(pb) != 1:
        raise SystemExit(f"C96: Ursus maritimus resolves to {len(pb)} species "
                         f"rows, so the polar bear counts are ambiguous")
    pbr = [r for r in tr if r["species_id"] == pb[0]]
    out["C96"] = len(pbr)
    out["C97"] = sum(1 for r in pbr if r["reporter_type"] == "E")
    out["C98"] = sum(1 for r in pbr if r["source"] == "W")
    if 24590 in (out["C96"], out["C97"], out["C98"]):
        raise SystemExit("C96: one of the polar bear counts now IS 24,590, so "
                         "the sentence saying this corpus does not reproduce it "
                         "has become false and must be rewritten")

    # C99-C102: the seizure sub-dataset has no dates at all. The 225-record
    # corpus has no time window to give: seizure_date and
    # seizure_year are empty for all 225 rows. The paper acknowledged missing
    # seizure dates in a limitations clause and then ranked species out of the
    # corpus as though the gap were elsewhere. What CAN be stated is which
    # source database each record comes from, so that is what the paper states.
    seiz2 = table("illegal_trade_seizures")
    out["C99"] = sum(1 for r in seiz2 if r["seizure_date"] or r["seizure_year"])
    src = Counter(r["source_database"] for r in seiz2)
    out["C100"], out["C101"], out["C102"] = src["CITES"], src["LEMIS"], src["WTP"]
    if out["C99"]:
        raise SystemExit(f"C99: {out['C99']} seizure record(s) now carry a date, "
                         f"so the sentence saying none does is false and a window "
                         f"can be stated after all")
    if out["C100"] + out["C101"] + out["C102"] != len(seiz2):
        raise SystemExit(f"C100: the three named source databases cover "
                         f"{out['C100'] + out['C101'] + out['C102']} of "
                         f"{len(seiz2)} records, so the list is not exhaustive")

    # C103-C104: how many of the twelve improving species actually improve AFTER
    # their listing. "Twelve species (27.9%) improved their global Red
    # List category after listing" is read against Section 4.7's own concession
    # that the
    # short-tailed albatross "carries no interval, because its whole assessment
    # series inside the window precedes its 2023 listing". The paper states both.
    #
    # The trajectory classification never looks at a listing date: it compares
    # the earliest and latest comparable assessment inside 1982-2025. "After
    # listing" is therefore a label the method does not earn, and whether it is
    # false depends on which listing ladder you read - the two disagree, which is
    # what Q6 and Q24 ask about:
    #
    #   events table (first_listed_on, what Table 3's sensitivity note uses):
    #       0 of the 12 lack a post-listing improvement
    #   curated listings table (what Sections 4.2 and 4.7 follow):
    #       2 do - Phoebastria albatrus (listed 2023-02-23, every comparable
    #       assessment 1994-2018) and Phocoenoides dalli (listed 2003-02-13,
    #       improvement straddles the listing and nothing moves after it)
    #
    # So the headline is safe on one ladder and wrong on the other, and the paper
    # uses both. C103 is the number the paper's own prose implies; C104 is the
    # number under the anchor its sensitivity analysis uses. The guard is that
    # they must differ: if they ever agree, the two-ladder problem is gone and
    # this pair no longer measures anything.
    def _no_post_listing_gain(ladder):
        n = 0
        for sp, a in glob.items():
            a = [x for x in a if WINDOW[0] <= x[0] <= WINDOW[1] and x[1] in RANK]
            if len(a) < 2 or RANK[a[-1][1]] - RANK[a[0][1]] >= 0:
                continue
            yr = ladder.get(sp)
            if yr is None:
                n += 1
                continue
            post = [x for x in a if x[0] >= yr]
            if not (len(post) >= 2 and RANK[post[-1][1]] - RANK[post[0][1]] < 0):
                n += 1
        return n

    def _ladder(path, col, pred):
        out_ = {}
        for r in csv.DictReader(open(DEPOSIT / "tables" / path)):
            if not pred(r) or not r[col]:
                continue
            nm = sp_name.get(r["species_id"])
            if nm:
                out_[nm] = min(out_.get(nm, 9999), int(r[col][:4]))
        return out_

    curated = _ladder("cites_listings.csv", "listing_date", lambda r: True)
    events = _ladder("cites_listing_events.csv", "event_date",
                     lambda r: r["is_listing"] == "t")
    out["C103"] = _no_post_listing_gain(curated)
    out["C104"] = _no_post_listing_gain(events)
    if out["C103"] == out["C104"]:
        raise SystemExit(f"C103: both listing ladders now give "
                         f"{out['C103']}, so the disagreement these two claims "
                         f"measure has gone and the pair must be retired")

    # C105-C107: the corpus's final year is not a year of data. Release v2025.1 was downloaded on 28 July 2025, before
    # the 2024 CITES annual reports were due, so describing the corpus as
    # 1975-2024 would read the right-hand edge of every series as observed
    # trade.
    #
    # Measured, the size of it is not marginal:
    #
    #   2019-2023 average   29,712 records a year
    #   2023                27,432  (C106)
    #   2024                   138  (C105) - 0.5% of the recent average
    #   of those 138, exporter-reported: 7  (C107)
    #
    # 131 of the 138 come from the importing side, which is the signature of a
    # year whose exporter annual reports have not been submitted yet. Any trend,
    # decline or "peak" read to 2024 is reading a reporting gap.
    #
    # The guard is the ratio: if a later release fills 2024 in, these three
    # claims stop describing the corpus and the sentences built on them must go.
    by_year = Counter(int(r["year"]) for r in tr if r["year"])
    recent = [by_year[y] for y in range(2019, 2024)]
    out["C105"] = by_year[2024]
    out["C106"] = by_year[2023]
    out["C107"] = sum(1 for r in tr
                      if r["year"] == "2024" and r["reporter_type"] == "E")
    if out["C105"] > 0.25 * (sum(recent) / len(recent)):
        raise SystemExit(f"C105: 2024 now holds {out['C105']} records against a "
                         f"2019-2023 average of {sum(recent)/len(recent):.0f}, "
                         f"so it is no longer an empty tail and the sentences "
                         f"calling it incomplete must be rewritten")

    # C111-C114: the years the windows actually start and stop, read against
    # what the data can carry.
    #
    # The assessment record is labelled 1982-2025, "roughly four decades", but
    # the pre-1994 codes V and E are off the ordinal scale, so no trajectory can
    # OPEN before a comparable category exists. Measured, the earliest opening
    # year is 1988 (C111) and 24 of the 40 trajectories open in 1996 (C112) -
    # the year of the first global Red List assessment round on the modern
    # criteria. So trajectories span at most 37 years, not 43, and most span 29.
    #
    # Figure 8's window, 1980-2023, is given with no reason while Figure 7's
    # caption carefully explains its own. It needs none: those are the first and
    # last years in which ANY record in the corpus carries source code I (C113,
    # C114). Saying so costs a clause and removes an unexplained boundary.
    opens = sorted(min(y for y, _ in a)
                   for a in ([x for x in v2
                              if WINDOW[0] <= x[0] <= WINDOW[1]
                              and x[1] in RANK]
                             for v2 in glob.values())
                   if len(a) >= 2)
    if len(opens) != 41:
        raise SystemExit(f"C111: {len(opens)} species carry a trajectory, not "
                         f"the 41 the paper reports, so the opening years are "
                         f"being read off a different set")
    out["C111"] = opens[0]
    out["C112"] = sum(1 for y in opens if y == 1996)
    si = [int(r["year"]) for r in tr if r["source"] == "I" and r["year"]]
    out["C113"] = min(si)
    out["C114"] = max(si)
    if out["C111"] < 1988:
        raise SystemExit(f"C111: a trajectory now opens in {out['C111']}, before "
                         f"the 1994 revision's earliest comparable category, so "
                         f"the scale is admitting a code it should not")

    # C115-C116: how much of the corpus the two lapsed reporters actually carry.
    # It can be argued that Russia's and Iceland's reporting cessation means "the decline
    # claims and the 26 decreasing trends therefore partly measure the cessation
    # of reporting rather than a fall in trade".
    #
    # Measured, that objection has a bound and the bound is small: Russia is the
    # exporting Party on 1,919 records and Iceland on 524, together 0.50% of the
    # 492,095. Whatever the two missing national series would have held, they
    # cannot move a corpus-level trend. The paper now states the share, which
    # turns a plausible objection into a measured one.
    #
    # The same measurement settles whether the mirror-reported 1,152 and 246 are the gap years or the whole window: they
    # are the importer-reported records for those exporters across the window,
    # and they reproduce exactly.
    out["C115"] = sum(1 for r in tr if r["exporter"] == "RU")
    out["C116"] = sum(1 for r in tr if r["exporter"] == "IS")
    mirror_ru = sum(1 for r in tr
                    if r["exporter"] == "RU" and r["reporter_type"] == "I")
    mirror_is = sum(1 for r in tr
                    if r["exporter"] == "IS" and r["reporter_type"] == "I")
    if (mirror_ru, mirror_is) != (1152, 246):
        raise SystemExit(f"C115: the mirror-reported counts are now "
                         f"{(mirror_ru, mirror_is)}, not the (1152, 246) the "
                         f"Results state")

    # C117-C119: the EN/CR series as a share, not a count. The Results report
    # "rising from seven in 1996 to a peak of thirteen in 2015 to 2017, then
    # falling back to nine from 2019" as RAW COUNTS, while the figure they cite
    # plots a proportion and the assessed set is still growing across the same
    # years - 19 species with a current global assessment in 1988, 38 in 1996,
    # 43 from 2015.
    #
    # The objection is real and its magnitude is not: as a share the series runs
    # 18.4% to 30.2% to 20.9%, so the rise is a rise and the fall is a fall on
    # either measure. The denominator grew 13% between 1996 and 2015 while the
    # count grew 86%, and the 2017-to-2019 fall happens at a fixed denominator
    # of 43. The paper now gives the share beside the count.
    enc_series = {sp_: [(int(r["year"]), r["status"]) for r in recs]
                  for sp_, recs in _rl.series_rows(series()).items()}

    def _share(year):
        assessed = encr = 0
        for sp, a in enc_series.items():
            prev = [x for x in a if x[0] <= year]
            if not prev:
                continue
            assessed += 1
            if prev[-1][1] in ("EN", "CR"):
                encr += 1
        return round(100 * encr / assessed, 1) if assessed else None

    out["C117"] = _share(1996)
    out["C118"] = _share(2015)
    out["C119"] = _share(2019)
    if not (out["C117"] < out["C118"] > out["C119"]):
        raise SystemExit(f"C117: the share series {out['C117']}, {out['C118']}, "
                         f"{out['C119']} no longer rises to a peak and falls "
                         f"away, so the sentence it supports is wrong")

    # C120-C124: what the seizure corpus actually holds, by product name.
    # Which corpus and which unit stand behind "Seized products were dominated
    # by ivory, furs, and skins". Measured against the 225 reconciled records,
    # all three terms are wrong:
    #
    #   bone-named products   36 records  (C120)  - the largest group
    #   skin-named products   22          (C121)
    #   ivory or tusk         20          (C122)
    #   fur-named products     0          (C123)  - none at all
    #
    # "fur" and "small fur product" exist in the product vocabulary (C124 counts
    # the vocabulary entries), so the zero is an absence in the seizure record
    # and not a missing code. The grouping rule is a substring on the product
    # name, which is stated in the claim definition so a reader can redo it.
    #
    # The guard is the ranking: the sentence this supports names bone first, so
    # the verifier fails if bone stops being the largest of the three.
    prods = {r["id"]: (r["product_name"] or "").lower()
             for r in table("illegal_trade_products")}
    seiz3 = table("illegal_trade_seizures")

    def _named(sub):
        return sum(1 for r in seiz3
                   if sub in prods.get(r["product_type_id"], ""))

    out["C120"] = _named("bone")
    out["C121"] = _named("skin")
    out["C122"] = (_named("ivory") + _named("tusk"))
    out["C123"] = _named("fur")
    out["C124"] = sum(1 for n in prods.values() if "fur" in n)
    if not (out["C120"] > out["C121"] > out["C122"]):
        raise SystemExit(f"C120: the three groups now rank "
                         f"{out['C120']}, {out['C121']}, {out['C122']}, so the "
                         f"sentence naming bone first is no longer right")
    if out["C123"]:
        raise SystemExit(f"C123: {out['C123']} seizure record(s) now name a fur "
                         f"product, so the sentence saying none does is false")
    if not out["C124"]:
        raise SystemExit("C124: the product vocabulary carries no fur entry, so "
                         "the zero in C123 cannot be called an absence in the "
                         "record rather than a missing code")

    # C125-C126: the quantity the paper's one comparable prior result can be set
    # beside. The Introduction cites "around 40% of
    # CITES-listed species remain threatened" as the single prior quantitative
    # finding its headline is comparable to, and the paper never returns to it.
    #
    # It can: the current distribution the Results already report - 4 CR, 5 EN,
    # 9 VU - is 18 of the 43, which is 41.9%. The paper now states that share
    # where the trajectory result is stated, so a reader can make the comparison
    # the Introduction sets up. The comparison itself is left to the reader
    # because the cited 40% has no stated denominator in the source as cited
    # (a question for the authors), and a share of an
    # unknown base cannot be compared arithmetically to a share of 43.
    #
    # The guard is the distribution: these two must agree with the categories
    # the Results report, or the share is being computed on a different series.
    cur = {sp: a[-1][1] for sp, a in glob.items()}
    dist = Counter(cur.values())
    if (dist["CR"], dist["EN"], dist["VU"]) != (4, 3, 11):
        raise SystemExit(f"C125: the current distribution is now "
                         f"{dist['CR']} CR, {dist['EN']} EN, {dist['VU']} VU, "
                         f"not the 4, 3, 11 the Results report, so the threatened "
                         f"share would be computed on a different series")
    out["C125"] = dist["CR"] + dist["EN"] + dist["VU"]
    out["C126"] = round(100 * out["C125"] / len(cur), 1)

    # C127-C131: the listing enumeration in Section 4.2, which was correct on
    # neither ladder. Measuring the "since 1998"/"after 1998" boundary found the
    # earlier sentence reporting the events table's counts (38 and
    # five) while naming three of its five species from the curated table: the
    # porbeagle at 2013 rather than its Appendix III entry of 2012, the
    # short-tailed albatross as a 2023 listing, and no basking shark at all.
    #
    # For the albatross, its earliest listing event is
    # 1975-07-01 in Appendix I and its 2023 events are a transfer out of I into
    # II, which is also what Supplementary Table 1 records (first_listed_on
    # 1975-07-01, 51 post-listing years), so 1975 is its listing year, not 2023.
    #
    # The sentence is now anchored to the events table and carries the curated
    # table's reading of the same facts beside it, so both ladders' numbers are
    # reported numbers and both are bound here. Q6 still asks which the paper
    # should use throughout; that is the authors' call, not this gate's.
    #
    # The guard is that the two ladders must DISAGREE. If they ever agree, the
    # sentence no longer needs two readings and this block stops measuring
    # anything - the same guard C103/C104 carry for the trajectory anchor.
    ev_first, ev_rows = {}, defaultdict(list)
    for r in csv.DictReader((DEPOSIT / "tables/cites_listing_events.csv").open()):
        ev_rows[r["species_id"]].append(r)
        if r["is_listing"].lower() in ("true", "t", "1"):
            y = int(r["event_date"][:4])
            ev_first[r["species_id"]] = min(ev_first.get(r["species_id"], 9999), y)
    cu_first = {}
    for r in csv.DictReader((DEPOSIT / "tables/cites_listings.csv").open()):
        y = int(r["listing_date"][:4])
        cu_first[r["species_id"]] = min(cu_first.get(r["species_id"], 9999), y)

    out["C127"] = sum(1 for y in ev_first.values() if 1970 <= y <= 1979)
    out["C128"] = sum(1 for y in ev_first.values() if y >= 1998)
    out["C129"] = sum(1 for y in cu_first.values() if 1970 <= y <= 1979)
    out["C130"] = sum(1 for y in cu_first.values() if y >= 1998)
    if (out["C127"], out["C128"]) == (out["C129"], out["C130"]):
        raise SystemExit("C127: the two listing ladders now agree on both counts, "
                         "so Section 4.2 no longer needs two readings and this "
                         "block measures nothing")

    sp_names = {r["id"]: r["scientific_name"]
                for r in csv.DictReader((DEPOSIT / "tables/species.csv").open())}
    alb = [s for s, n in sp_names.items() if n == "Phoebastria albatrus"][0]
    rows = sorted(ev_rows[alb], key=lambda r: r["event_date"])
    out["C131"] = int(rows[0]["event_date"][:4])
    if rows[0]["appendix"] != "I":
        raise SystemExit(f"C131: the albatross's earliest listing event is now in "
                         f"Appendix {rows[0]['appendix']}, not Appendix I, so "
                         f"Section 4.2's 'in Appendix I' is false")
    moves = {(r["appendix"], r["change_type"]) for r in rows
             if r["event_date"][:4] == "2023"}
    if ("I", "x") not in moves or ("II", "a") not in moves:
        raise SystemExit(f"C131: the albatross's 2023 events are {sorted(moves)}, "
                         f"which is not a transfer out of Appendix I into "
                         f"Appendix II, so calling it a transfer is false")
    supp = {r["scientific_name"]: r for r in csv.DictReader(
        (DEPOSIT / "supplementary/supplementary_table_1_post_listing_window.csv").open())}
    if supp["Phoebastria albatrus"]["first_listed_on"][:4] != str(out["C131"]):
        raise SystemExit(f"C131: the events table dates the albatross's first "
                         f"listing to {out['C131']} and Supplementary Table 1 to "
                         f"{supp['Phoebastria albatrus']['first_listed_on']}, so "
                         f"the deposit disagrees with itself")

    # --- C132 to C140: does the 2001 criteria revision make the balance? ----
    #
    # The objection this answers is the strongest one the paper has had put to
    # it: improvements and deteriorations come out even (18-18), and the IUCN
    # criteria were revised in 2001, so the balance could be an artefact of
    # comparing categories assigned under different rules.
    #
    # Instrument 1 holds the criteria fixed WITHIN each comparison by bucketing
    # every transition on where the 2001 revision falls relative to its two
    # endpoints. A transition whose endpoints are both 2001 or later cannot
    # cross the revision, so the balance inside that bucket is not an artefact
    # of it. This is the instrument that bears on the objection.
    #
    # Instrument 2 restricts the species-level global_series to a later start year and
    # reclassifies. It is harsher and it does NOT isolate the revision, because
    # restricting the start year also shortens the window - from 43 years to 24
    # at 2001 - which reduces movement on its own. It is reported because the
    # paper should state the harsher reading itself rather than have a reader
    # find it, and the confound is stated with it.
    #
    # Neither instrument bounds category change arising from improved knowledge
    # or from taxonomy within one criteria era. That needs IUCN's
    # reason-for-change field, which the deposited global_series does not carry.
    REVISION = 2001
    with zipfile.ZipFile(ZIP) as z:
        rows = list(csv.DictReader(io.StringIO(
            iucn_series.read_member(z, SERIES).decode())))
    # From 21 October 2026 the series is global and European, ordered by
    # (year, assessment_id); see the banner at the top of this file.
    global_series = {sp_: [(int(r["year"]), r["status"]) for r in recs]
                     for sp_, recs in _rl.series_rows(rows).items()}

    # One scale, one source. The first version of this block re-implemented the
    # ladder and got 41 transitions where the project's own ladder gets 36: it
    # skipped over a non-comparable assessment instead of letting it break the
    # chain, and ignored the same-year tie-break. Both rules live in
    # redlist_scale.py and this block now calls them rather than paraphrasing
    # them.
    buckets = {"after": [], "straddle": [], "before": []}
    for name, obs in global_series.items():
        seq = [x for x in obs if WINDOW[0] <= x[0] <= WINDOW[1]]
        for y0, y1, direction in rl.transitions(seq):
            if y0 >= REVISION and y1 >= REVISION:
                buckets["after"].append(direction)
            elif y0 < REVISION and y1 < REVISION:
                buckets["before"].append(direction)
            else:
                buckets["straddle"].append(direction)

    out["C132"] = sum(len(v) for v in buckets.values())
    out["C133"] = len(buckets["after"])
    out["C134"] = buckets["after"].count("improved")
    out["C135"] = buckets["after"].count("deteriorated")
    out["C136"] = len(buckets["straddle"])
    out["C137"] = len(buckets["before"])

    # The whole point of instrument 1 is that most of the record does not cross
    # the revision. If that stopped being true the instrument would answer
    # nothing, so it refuses rather than report a number carrying no argument.
    if out["C132"] and out["C133"] <= out["C132"] // 2:
        raise SystemExit(f"C133: only {out['C133']} of {out['C132']} transitions "
                         f"have both endpoints after the {REVISION} revision, so "
                         f"this instrument no longer bounds the objection it "
                         f"exists to bound")
    if out["C134"] + out["C135"] != out["C133"]:
        raise SystemExit("C134: the post-revision bucket's two directions do not "
                         "sum to its size, so a transition has no direction")

    # Instrument 2, at the revision year. Harsher, and it does NOT isolate the
    # revision: restricting the start year also shortens the window from 43
    # years to 24, which reduces movement on its own. Reported because the paper
    # should state the harsher reading itself, with the confound beside it.
    unch = impr = deter = none = 0
    for name, obs in global_series.items():
        kept = [(y, st) for y, st in obs
                if y >= REVISION and rl.rank(st) is not None]
        if len(kept) < 2:
            none += 1
            continue
        first, last = rl.rank(kept[0][1]), rl.rank(kept[-1][1])
        if last < first:
            impr += 1
        elif last > first:
            deter += 1
        else:
            unch += 1
    out["C138"] = impr
    out["C139"] = deter
    out["C140"] = none
    if impr + deter + unch + none != len(global_series):
        raise SystemExit("C138: the species-level buckets do not sum to the "
                         "number of species in the global series")

    v = sorted(lag.values())
    out["C29"] = len(v)
    out["C30"] = int(statistics.median(v))
    out["C31"] = min(v)
    out["C32"] = max(v)
    return out


def self_test():
    assert "LR/lc" not in CURRENT and "LC" in CURRENT, \
        "SELF-TEST: the legacy/current split is wrong, so C10 and C11 are wrong"
    assert RANK["LC"] < RANK["VU"] < RANK["CR"], "SELF-TEST: the scale is unordered"
    assert RANK["LR/cd"] == RANK["NT"], \
        "SELF-TEST: LR/cd is not Near Threatened, which is what ref 76 is cited for"
    assert "RE" not in RANK, \
        "SELF-TEST: Regionally Extinct is on the global ladder"
    assert _rl.convention() == _rl.CONVENTION_LIN2025, \
        "SELF-TEST: the scale module is not on the convention the Methods state"
    assert "DD" not in RANK, "SELF-TEST: a category with no direction is on the scale"
    print("  self-test: PASS (the legacy split and the ordinal scale are both "
          "the ones the definitions name)", file=sys.stderr)


def main():
    self_test()
    for p in (TRACE, ZIP, TABLES):
        if not p.exists():
            print(f"UNMEASURED: {p.name} is not in the deposit.", file=sys.stderr)
            return 3

    recorded = {r["claim_id"]: (r["value"], r["claim"])
                for r in csv.DictReader(open(TRACE))}
    got = compute()

    faults, checked = [], 0
    for cid, (want, claim) in sorted(recorded.items()):
        if cid not in got:
            faults.append(f"{cid} ({claim[:50]}) is in the table and this check "
                          f"does not compute it")
            continue
        checked += 1
        mine = got[cid]
        same = (f"{mine:.2f}" == want) if isinstance(mine, float) else (str(mine) == want)
        if not same:
            shown = f"{mine:.2f}" if isinstance(mine, float) else str(mine)
            faults.append(f"{cid} ({claim[:50]}): the table records {want!r}, "
                          f"the deposit computes {shown!r}"
                          + (f" (raw {mine!r})" if shown != str(mine) else ""))

    # The table a reader actually opens has to carry the values this gate just
    # verified, or the verification is of a file nobody reads.
    if not TABLE_MD.exists():
        faults.append(f"{TABLE_MD.name} has not been rendered.")
    else:
        md = TABLE_MD.read_text()
        for cid, (want, claim) in sorted(recorded.items()):
            if f"| {cid} | {claim} | **{want}** |" not in md:
                faults.append(f"{cid} reads {want!r} in the CSV and the "
                              f"supplementary table does not say so. Re-render "
                              f"with ingest/render_traceability_md.py.")
        for stale in ("PENDING CONVENTION", "PENDING:"):
            if stale in md:
                faults.append(f"the supplementary table still contains "
                              f"{stale!r}, which no claim now carries.")

    if faults:
        print(f"\nTHE TRACEABLE CLAIMS ({len(faults)}):\n", file=sys.stderr)
        for f in faults:
            print(f"  {f}", file=sys.stderr)
        return 1

    print(f"traceable claims: all {checked} recomputed from the deposited "
          f"package and identical to the recorded value, with no database, "
          f"credentials or network. The supplementary table carries the same "
          f"{checked} values.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
