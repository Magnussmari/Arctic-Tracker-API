#!/usr/bin/env python3
"""V-7: every flag named for a singular thing is singular, or is documented.

WHY THIS GATE EXISTS
--------------------
Five of the defects found in this dataset are one defect wearing five hats:

  iucn_assessments.is_latest   not unique per species per SCOPE
  cites_listings.is_current    flagged on every row for 8 species
  cms_listings (agreement)     CMS and daughter agreements share a table
  cites_trade_records          reporter side omitted from a GROUP BY
  common_names.is_main         (this one is fine, and the gate proves it)

In each case a column named for a singular thing ("the latest", "the current",
"the main") did not uniquely identify one row over the partition that anyone
actually cared about, and code downstream assumed it did. Nothing failed. The
page rendered, the query returned, the number looked plausible.

A human sweep found these five. A human sweep will not find the sixth, because
the sixth will be added by someone who has not read this file. So the property
is asserted here instead.

HOW IT WORKS
------------
For every boolean column whose name suggests singularity (is_latest, is_current,
is_main, is_primary and so on) in a table that has a species_id, the gate counts
how many rows carry the flag per species. It then requires one of:

  a) exactly one flagged row per species, the property the name implies, OR
  b) an entry in EXEMPTIONS naming the real partition and the reason.

An exemption is not a suppression. It is a written statement of what the flag
actually means, and the gate still checks that the stated partition holds. A
flag that is neither unique nor exempt fails the run.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/verify_flag_invariants.py --schema arctic_v2
"""
import argparse
import os
import sys
from pathlib import Path

import psycopg2

# Importing a sibling here writes __pycache__ INTO the deposit, and
# verify_deposit_accounted.py rejects bytecode in a citable archive. Running
# these scripts in place is the intended use, so the run must not leave
# residue behind, or the archive gate would fail merely because the verifiers
# had been run.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402

# Column-name fragments that promise "there is one of these".
SINGULAR_HINTS = ("is_latest", "is_current", "is_main", "is_primary", "is_default")

# Flags that are legitimately not unique per species, each with the partition
# that IS unique and why. The gate verifies the stated partition rather than
# taking the exemption on trust.
#
# Adding an entry here is a deliberate act that requires writing down what the
# flag means. That is the point: the defects happened because nobody had to.
EXEMPTIONS = {
    ("cites_listing_events", "is_current"): {
        # NOT a defect, unlike every other entry here. In Species+, is_current
        # means "this event is still in force", and several events per species
        # legitimately are: the standing listing, plus every Party reservation
        # never withdrawn. Norway and Japan have held reservations against the
        # minke whale's Appendix I listing since 1986; Iceland entered its own
        # on both appendices in 2000. All are current, alongside the listing.
        #
        # partition is None because no partition can satisfy "exactly one
        # flagged row": most historical events are not current, so any finer
        # grouping produces partitions with zero. Tried species+change_type+
        # party (161 violations) then adding appendix (178). The flag is simply
        # not a selector, and the exemption records that.
        #
        # Requiring one flagged row per species here would mean discarding the
        # fact that two whaling nations have never accepted the listing, which
        # is precisely what this paper exists to surface.
        "partition": None,
        "reason": (
            "Means 'still in force', not 'the current listing'. Multiple events per "
            "species are simultaneously current: one standing listing plus any number "
            "of unwithdrawn Party reservations. Consumers must filter on is_listing "
            "to get appendix state and must never read is_current alone as selecting "
            "a single row."
        ),
    },
    ("iucn_assessments", "is_latest"): {
        # It IS unique per species. That is exactly the problem: an assessment is
        # scoped, so the correct partition is species AND scope, and uniqueness
        # over the wrong partition is what makes the defect invisible. The first
        # version of this registry called it "non-unique" and the gate caught
        # that as a stale exemption, which is the gate working.
        "partition": ("species_id",),
        "must_not_be_unique_over": ("species_id", "coalesce(scope_code, '1')"),
        "reason": (
            "Inherited from the source and NOT scope-aware. Flagged on the newest "
            "assessment by year regardless of scope, so for 17 of 43 species it sits "
            "on a European regional row while the global assessment carries no flag. "
            "A 2025-09-08 migration would have flagged per species per scope and was "
            "never applied. Exposed unchanged in arctic_api so the defect stays "
            "visible; consumers must use the computed is_latest_in_scope instead."
        ),
    },
    ("cites_listings", "is_current"): {
        "partition": None,
        "reason": (
            "Does not discriminate. Eight species carry several rows and EVERY row is "
            "flagged, so selecting on it returns whichever row the plan produced first "
            "and the dates behind those rows span up to 27 years. Consumers must use "
            "the computed first_listed_on / is_first_listing instead."
        ),
    },
    ("split_listings", "is_current"): {
        "partition": ("species_id", "population_identifier"),
        "reason": (
            "Unique per species per POPULATION, not per species, which is the whole "
            "point of a split listing. Balaenoptera acutorostrata is Appendix I except "
            "the West Greenland population, which is Appendix II, and both halves are "
            "concurrently in force."
        ),
    },
}


def singular_boolean_columns(cur, schema):
    """Boolean columns whose name promises uniqueness, in tables keyed by species."""
    cur.execute(
        """
        select c.table_name, c.column_name
          from information_schema.columns c
         where c.table_schema = %s
           and c.data_type = 'boolean'
           and exists (
                 select 1 from information_schema.columns k
                  where k.table_schema = c.table_schema
                    and k.table_name = c.table_name
                    and k.column_name = 'species_id')
         order by c.table_name, c.column_name
        """,
        (schema,),
    )
    return [
        (t, col)
        for (t, col) in cur.fetchall()
        if any(hint in col for hint in SINGULAR_HINTS)
    ]


def offenders(cur, schema, table, column, partition):
    """Species (or partition tuples) carrying a count other than exactly one."""
    keys = ", ".join(partition)
    cur.execute(
        f"""
        select count(*) from (
          select {keys}, count(*) filter (where {column}) as n
            from {schema}.{table}
           group by {keys}
          having count(*) filter (where {column}) <> 1
        ) x
        """
    )
    return cur.fetchone()[0]


# Partitions that are supposed to determine a single answer, with the columns
# whose disagreement makes that impossible. V-7's flag check passes when a flag
# is unique over its partition; it cannot see two rows in the SAME partition
# holding different VALUES, which is the same defect one level deeper.
#
# Three species carry two global IUCN assessments in the same year with
# different categories, so "the current status" depends on a tie-break, and
# two independent implementations can pick differently unless one rule is
# stated.
VALUE_CONFLICTS = {
    ("iucn_assessments", "status"): {
        "partition": ("species_id", "year_published", "coalesce(scope_code, '1')"),
        "expected": 3,
        "reason": (
            "Branta ruficollis 2015, Bubo scandiacus 2021 and Odobenus rosmarus "
            "2025 each have two global assessments in one year with different "
            "categories. Both are what the IUCN published; the data encodes no "
            "precedence. The API resolves the tie with a documented rule (the "
            "higher assessment id stands) and states it."
        ),
    },
}


def value_conflicts(cur, schema, table, column, partition):
    """Groups in a determining partition that hold more than one distinct value."""
    keys = ", ".join(partition)
    cur.execute(
        f"""
        select count(*) from (
          select {keys} from {schema}.{table}
           group by {keys}
          having count(distinct {column}) > 1
        ) x
        """
    )
    return cur.fetchone()[0]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--schema", default="arctic_v2")
    args = ap.parse_args()

    schema = validate_schema(args.schema)
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    failures, notes = [], []
    conn = psycopg2.connect(url, connect_timeout=30)
    try:
        with conn.cursor() as cur:
            columns = singular_boolean_columns(cur, schema)
            if not columns:
                sys.exit(f"FAIL: no singular-sounding boolean columns found in {schema}; "
                         f"the gate is not looking at anything and would pass vacuously")

            print(f"V-7 flag invariants, schema {schema}")
            print(f"checking {len(columns)} singular-sounding boolean column(s)\n")

            for table, column in columns:
                key = (table, column)
                exemption = EXEMPTIONS.get(key)

                if exemption is None:
                    bad = offenders(cur, schema, table, column, ("species_id",))
                    if bad:
                        failures.append(
                            f"{table}.{column}: {bad} species do not have exactly one "
                            f"flagged row. Either fix the data, or add an EXEMPTIONS "
                            f"entry stating what the flag actually means."
                        )
                        print(f"  FAIL  {table}.{column}: {bad} species not unique")
                    else:
                        print(f"  ok    {table}.{column}: unique per species")
                    continue

                # A flag may be unique over one partition and still wrong, because
                # the partition anyone cares about is a different one. Where an
                # exemption names that correct partition, assert the flag still
                # FAILS it: if it starts passing, the source was fixed and both the
                # exemption and its workaround are now lying to the reader.
                wrong = exemption.get("must_not_be_unique_over")
                if wrong is not None:
                    still_broken = offenders(cur, schema, table, column, wrong)
                    if still_broken == 0:
                        failures.append(
                            f"{table}.{column}: exemption says it is not unique per "
                            f"{'+'.join(wrong)}, but it now is. The source was corrected. "
                            f"Remove the exemption and the computed workaround."
                        )
                        print(f"  FAIL  {table}.{column}: exemption is now stale")
                    else:
                        notes.append(
                            f"{table}.{column}: unique per {'+'.join(exemption['partition'])} "
                            f"but wrong; {still_broken} group(s) violate the correct "
                            f"partition {'+'.join(wrong)}"
                        )
                        print(f"  noted {table}.{column}: unique over the wrong partition")
                    continue

                partition = exemption["partition"]
                if partition is None:
                    # Documented as not uniquely identifying anything. Assert that it
                    # really is still broken, so a silent upstream fix does not leave a
                    # stale exemption in place telling future readers a falsehood.
                    bad = offenders(cur, schema, table, column, ("species_id",))
                    if bad == 0:
                        failures.append(
                            f"{table}.{column}: exempted as non-unique, but it is now "
                            f"unique per species. The source may have been corrected. "
                            f"Remove the exemption and the workaround that depends on it."
                        )
                        print(f"  FAIL  {table}.{column}: exemption is now stale")
                    else:
                        notes.append(f"{table}.{column}: known non-unique ({bad} species)")
                        print(f"  noted {table}.{column}: documented defect, {bad} species")
                else:
                    bad = offenders(cur, schema, table, column, partition)
                    if bad:
                        failures.append(
                            f"{table}.{column}: exempted as unique per "
                            f"{'+'.join(partition)}, but {bad} group(s) violate that too."
                        )
                        print(f"  FAIL  {table}.{column}: stated partition does not hold")
                    else:
                        print(f"  ok    {table}.{column}: unique per {'+'.join(partition)}")

            # Value conflicts: two rows in a determining partition disagreeing.
            for (table, column), spec in VALUE_CONFLICTS.items():
                found = value_conflicts(cur, schema, table, column, spec["partition"])
                if found != spec["expected"]:
                    failures.append(
                        f"{table}.{column}: {found} conflicting group(s) over "
                        f"{'+'.join(spec['partition'])}, registry expects "
                        f"{spec['expected']}. A new conflict appeared or one was "
                        f"resolved; update VALUE_CONFLICTS deliberately."
                    )
                    print(f"  FAIL  {table}.{column}: {found} conflicts, expected {spec['expected']}")
                else:
                    notes.append(
                        f"{table}.{column}: {found} group(s) hold conflicting values "
                        f"over {'+'.join(spec['partition'])}"
                    )
                    print(f"  noted {table}.{column}: {found} value conflict(s), as registered")

            # Every exemption must correspond to a column that still exists, or the
            # registry is describing a schema that no longer exists.
            present = set(columns)
            for key in EXEMPTIONS:
                if key not in present:
                    failures.append(
                        f"{key[0]}.{key[1]}: EXEMPTIONS entry for a column that does not "
                        f"exist in {schema}. Remove it."
                    )
    finally:
        conn.close()

    print()
    for note in notes:
        print(f"documented defect carried forward: {note}")
    if failures:
        print(f"\nV-7 FAIL, {len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nV-7 PASS, {len(columns)} flag(s) checked, {len(notes)} documented defect(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
