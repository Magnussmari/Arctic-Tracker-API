#!/usr/bin/env bash
# Run all retargeted ingests against the scratch schema, then prove idempotency.
# Usage: run_all_ingests.sh [--verify] [--target-schema NAME]
#   --verify  run every loader TWICE and assert count+content-hash unchanged,
#             then reconcile the scratch schema against the live arctic schema.
set -uo pipefail
cd "$(dirname "$0")/.."
PY="./.venv/bin/python"
SCHEMA="arctic_sprint"
VERIFY=0
for arg in "$@"; do
  case "$arg" in
    --verify) VERIFY=1 ;;
    --target-schema=*) SCHEMA="${arg#*=}" ;;
  esac
done

if [ -z "${ARCTIC_DATABASE_URL:-}" ]; then
  echo "ARCTIC_DATABASE_URL not set (set it in the environment, never hardcode)" >&2
  exit 2
fi

run_all() {
  echo "== cites (raw v2025.1 canonical refresh path) =="
  "$PY" ingest/cites_load.py --source raw --target-schema "$SCHEMA" || return 1
  echo "== nammco =="
  "$PY" ingest/nammco_load.py --target-schema "$SCHEMA" || return 1
  echo "== illegal_trade =="
  "$PY" ingest/illegal_trade_load.py --target-schema "$SCHEMA" || return 1
  echo "== iucn (snapshot replay) =="
  "$PY" ingest/iucn_load.py --target-schema "$SCHEMA" || return 1
}

snapshot_state() {
  # Business-column hash only: ids are deterministic uuid5 in scratch but
  # legacy random in live; created_at/updated_at default now() per run.
  "$PY" ingest/table_hashes.py "$SCHEMA"
}

if [ "$VERIFY" = "1" ]; then
  echo "== run 1 =="
  run_all || { echo "G4 FAIL: first run errored"; exit 1; }
  snapshot_state > /tmp/ingest_run1.txt
  echo "== run 2 (idempotency) =="
  run_all || { echo "G4 FAIL: second run errored"; exit 1; }
  snapshot_state > /tmp/ingest_run2.txt
  if ! diff -u /tmp/ingest_run1.txt /tmp/ingest_run2.txt; then
    echo "G4 FAIL: not idempotent (state changed between runs)"
    exit 1
  fi
  echo "idempotency: PASS (count + content hash unchanged)"
  echo "== reconcile scratch vs live arctic =="
  if [ -f ingest/verify_against_live.py ]; then
    "$PY" ingest/verify_against_live.py "$SCHEMA" || { echo "G4 FAIL: scratch does not reproduce live baseline"; exit 1; }
  else
    echo "skipped: live-baseline comparison (maintainers' check, not part of this repository)"
    echo "PARTIAL: idempotency passed; the live-baseline comparison did not run"
    exit 3
  fi
else
  run_all
fi
