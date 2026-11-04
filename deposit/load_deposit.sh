#!/usr/bin/env bash
# Build a database from this deposit.
#
# WHY THIS EXISTS
# ---------------
# The verification README said "schema.sql creates the tables; the CSVs in
# tables/ fill them", which is true and is not enough. The tables carry foreign
# keys, so they load in a dependency order, and nothing here stated it. Loading
# them the obvious way — alphabetically — fails on 8 of the 22, including
# cites_trade_records, because cites_listings and the rest reach species before
# species exists. A reviewer following the README in the obvious order gets
# fourteen tables and eight errors, and would reasonably conclude the deposit is
# broken. It is not: all 22 load, in two passes.
#
# Rather than publish an order that goes stale the next time a foreign key is
# added, this retries: load whatever loads, then try the rest, until a pass
# achieves nothing. That is order-independent and needs no dependency graph.
#
# Two tables stay empty and that is a licence constraint, not a failure:
# iucn_assessments and catch_records are not redistributable. See identifiers/
# for the record IDs and the top-level README for how to rebuild each.
#
# Verified on 2026-09-01 against a virgin PostgreSQL 17, and again on 2026-10-23
# after the IUCN withholding added a column: schema.sql applies with
# no errors, 22 of 22 tables load in two passes, 492,095 trade records,
# 225 seizures, 43 species.
#
# Usage:
#   ARCTIC_DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<dbname> ./load_deposit.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
: "${ARCTIC_DATABASE_URL:?set ARCTIC_DATABASE_URL to the database to build}"
SCHEMA="${ARCTIC_SCHEMA:-arctic_v2}"

command -v psql >/dev/null || { echo "psql not found; install the PostgreSQL client"; exit 1; }

echo "==> schema"
psql "$ARCTIC_DATABASE_URL" -v ON_ERROR_STOP=1 -q -f "$HERE/schema.sql"
echo "    applied $HERE/schema.sql"

# schema.sql describes the database of record. The deposit differs from it in
# one column on purpose: IUCN's terms forbid redistributing a Red List
# category, so ingest/withhold_iucn_categories.py replaces each category in
# tables/timeline_events.csv with a pointer to the assessment and adds the
# column that holds it. Without this the file does not load ("extra data after
# last expected column") and a reader gets 21 tables of 22.
psql "$ARCTIC_DATABASE_URL" -v ON_ERROR_STOP=1 -q -c \
  "alter table $SCHEMA.timeline_events add column if not exists iucn_assessment_id text"

echo "==> tables"
remaining=("$HERE"/tables/*.csv)
pass=0
while [ ${#remaining[@]} -gt 0 ]; do
  pass=$((pass + 1))
  loaded=0
  still=()
  for f in "${remaining[@]}"; do
    t="$(basename "$f" .csv)"
    # By name, not position: the added column sits mid-file but last in the table.
    cols="$(head -1 "$f" | tr -d '\r')"
    if psql "$ARCTIC_DATABASE_URL" -q \
        -c "\copy $SCHEMA.$t ($cols) from '$f' with (format csv, header true)" >/dev/null 2>&1; then
      loaded=$((loaded + 1))
    else
      still+=("$f")
    fi
  done
  echo "    pass $pass: $loaded table(s)"
  if [ "$loaded" -eq 0 ]; then break; fi
  remaining=("${still[@]:-}")
  [ -z "${remaining[0]:-}" ] && remaining=()
done

if [ ${#remaining[@]} -gt 0 ] && [ -n "${remaining[0]:-}" ]; then
  echo
  echo "did not load:"
  for f in "${remaining[@]}"; do echo "  $(basename "$f")"; done
  echo
  echo "A pass that loads nothing means what is left does not depend on load"
  echo "order. Read the error by running the \\copy for one of them by hand."
  exit 1
fi

echo "==> what is in it"
psql "$ARCTIC_DATABASE_URL" -tA -c "
  select '    ' || relname || ' ' || n_live_tup
    from pg_stat_user_tables
   where schemaname = '$SCHEMA' and n_live_tup > 0
   order by n_live_tup desc limit 6"

echo
echo "iucn_assessments and catch_records are empty by licence, not by failure."
echo "Now: ARCTIC_DATABASE_URL=... ./verification/verify_manuscript_claims.py"
