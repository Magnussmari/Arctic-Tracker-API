# Verification scripts

These reproduce the numbers this paper reports, from the tables in
`../tables/`. They are the same scripts the authors run, copied here
rather than referenced, so the deposit does not depend on a repository
outliving it.

`verify_claims_offline.py` and `verify_trajectories_offline.py` need no
database: they read the Source Data in `../source_data.zip` after
`../rebuild_iucn.py` has restored the categories. The others need
`ARCTIC_DATABASE_URL` pointing at a PostgreSQL instance, and `ARCTIC_SCHEMA`
if you did not name your schema `arctic_v2`.
`../schema.sql` creates the tables; the CSVs in `../tables/` fill them.

**Two tables are not in this package and the scripts need them.**
`iucn_assessments` and `catch_records` are withheld for licence reasons,
so a database built from `tables/` alone cannot reproduce every number.
The scripts say which tables are empty and how to rebuild each one
rather than failing partway through — but you should know before you
start, because it is the difference between an incomplete deposit and a
broken one. This is the former, and it is a licence constraint rather
than a choice of ours. See `../identifiers/` and the top-level README.

`verify_manuscript_claims.py` prints every claim with the value the
paper states, the value the data gives, and a verdict.

- `verify_manuscript_claims.py` — recomputes every number the paper reports
- `verify_derived_truth.py` — re-reads the raw shards and compares on content digest
- `verify_source_truth.py` — compares curated tables against their source files
- `trajectory_report.py` — derives the status-trajectory tally under the stated rule
- `redlist_scale.py` — the single Red List scale the trajectory rule depends on
- `coverage_report.py` — fails if any table lacks a recorded verification decision
- `attribution_loss.py` — measures what a species-level count cannot see
- `verify_metamorphic.py` — asserts properties that hold without knowing the right answer: published values survive row permutation, counts are additive over a partition, filters are monotone, aggregates survive relabelling
- `verify_flag_invariants.py` — every flag named for a singular property is singular, or carries a written exemption saying what it actually means
- `verify_schema_applies.py` — ../schema.sql stands up the tables from nothing and still describes them
- `verify_deposit_roundtrip.py` — every CSV in ../tables/ loads back into the schema this package ships
- `run_all.py` — runs every check in this directory and reports pass, fail, crash or absent data separately, so a crash cannot read as a pass
- `stratify_trajectories.py` — the interval from listing to a species' first comparable assessment, which is what the observation window has to survive
- `window_sensitivity.py` — the sensitivity grid over observation window and baseline bound, computed and reported
- `verify_pipeline_record.py` — pipeline.json still describes the pipeline it was derived from, and re-renders both stage figures byte-for-byte to prove it
