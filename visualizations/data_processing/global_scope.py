#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-10-06
"""One definition of "the species' current Red List status". One.

WHY THIS EXISTS
---------------
Three scripts resolved current status as `WHERE is_latest`, or as the last row
by year, with no condition on scope. `arctic_v2.iucn_assessments` carries
regional assessments beside global ones, and for twenty-one of the forty-three
focal species the most recent assessment is EUROPEAN. So `is_latest` picks the
European one, and the figure draws a regional category where a reader reads the
species' global status.

Two examples, from the deposited Source Data:

  Balaenoptera physalus  latest global assessment 2018; is_latest row 2023 Europe
  Balaenoptera musculus  latest global assessment 2018; is_latest row 2023 Europe

For both, the 2023 European category differs from the 2018 global one. A
pipeline that selects on is_latest alone therefore draws the European category
in a figure whose caption promises the global one, and two figures built with
and without the scope condition would disagree with each other. The cause is
one missing condition, so the condition is defined once, here.

THE RULE, which is the paper's own
----------------------------------
The post-listing trajectory analysis uses GLOBAL assessments only; Table 3 says
so and the Figure 4 caption says the European assessments are excluded by
design. Anything drawn as "the species' status" follows the same rule.

Global is scope_code NULL or '1'. IUCN's own vocabulary: 1 Global, 2 Europe, EU
the twenty-seven member states. The view leaves global NULL, which is how the
deposited identifier table records it, so both forms count.

A caller that wants a regional category must ask for it by scope explicitly and
must label it with the scope - see the app's src/lib/iucn-scope.ts, which exists
because "Europe" alone was printed over an EU-27 assessment.
"""

import csv
from pathlib import Path

import pandas as pd

# For SQL. Interpolated into a WHERE clause; no user input touches it.
# NOT sufficient on its own: see REGIONAL_IDS below. A query that needs "the
# species' current global category" calls latest_global_status() instead of
# writing `is_latest AND GLOBAL_SQL`, which returns nothing for a species whose
# is_latest assessment is European (measured 18 October 2026: four of ten
# figure7 rows and six of fifteen figure8 rows came back "Unknown").
GLOBAL_SQL = "(scope_code IS NULL OR scope_code = '1')"

# Eight assessments carry no scope in IUCN's record and are regional: five issue
# a category only a regional assessment can (NA, RE), three are labelled Europe
# or Mediterranean on IUCN's own page. A NULL scope_code reads them as global.
# The curated list is the one the tracker and make_fig3_fig10_source_data.py
# already drop; this module drops the same eight so every "global" in the
# figure pipeline is the same set. Without it, a scope-less European
# regional-only outcome reaches figure1 as a species' global status.
SCOPE_CORRECTIONS = (Path(__file__).resolve().parents[2]
                     / "species_data" / "curated" / "iucn_scope_corrections.csv")


def regional_ids():
    """Assessment ids the curated scope-correction list reads as regional."""
    with open(SCOPE_CORRECTIONS, newline="") as f:
        ids = {int(r["assessment_id"]) for r in csv.DictReader(f)}
    if not ids:
        raise SystemExit(f"{SCOPE_CORRECTIONS} is empty, so the regional "
                         f"assessments recorded without a scope would be read "
                         f"as global. Refusing rather than guessing.")
    return ids


def global_only(df, column="scope_code", ident="assessment_id"):
    """The global rows of a pandas frame of assessments, the eight corrected
    regional assessments excluded."""
    for c in (column, ident):
        if c not in df.columns:
            raise KeyError(
                f"{c!r} is not in this frame, so 'the global assessment' cannot "
                f"be selected and must not be guessed at. Add the column to the "
                f"query rather than dropping the condition.")
    scoped = df[column].isna() | (df[column].astype(str) == "1")
    regional = pd.to_numeric(df[ident], errors="coerce").isin(regional_ids())
    return df[scoped & ~regional]


def latest_global(df, species="species_id", year="year_published", ident="assessment_id"):
    """One row per species: its most recent GLOBAL assessment.

    Two global assessments in one year are resolved as the Methods state: the
    higher assessment identifier stands. Sorting on the year alone left the
    choice to an unstable sort, and on 2026-10-07 a regeneration drew one
    species' category from the lower of its two same-year assessments instead of
    the one the rule selects.
    """
    if ident not in df.columns:
        raise KeyError(
            f"{ident!r} is not in this frame, so a same-year tie between global "
            f"assessments cannot be resolved by the stated rule. Add it to the query.")
    g = global_only(df).assign(_id=lambda d: pd.to_numeric(d[ident], errors="coerce"))
    g = g.sort_values([year, "_id"], kind="mergesort")
    return g.groupby(species).tail(1).reset_index(drop=True).drop(columns="_id")


def latest_global_status(query, schema, species_ids=None):
    """{species_id: status} of each species' most recent GLOBAL assessment.

    The one call for a generator that needs a species' current category. It
    reads every assessment of the species and lets latest_global() choose, so
    the scope rule, the eight corrections and the same-year tie-break are the
    ones above and nowhere else.
    """
    sql = (f"SELECT species_id, status, year_published, assessment_id, scope_code "
           f"FROM {schema}.iucn_assessments")
    params = ()
    if species_ids is not None:
        sql += " WHERE species_id = ANY(%s::uuid[])"
        params = (list(species_ids),)
    df = pd.DataFrame(query(sql, params))
    if df.empty:
        return {}
    pick = latest_global(df)
    return dict(zip(pick["species_id"], pick["status"]))
