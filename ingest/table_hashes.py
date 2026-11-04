#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""Print count + business-column content hash per ingested table in a schema.

Used by run_all_ingests.sh for run-to-run idempotency proof. Business columns
only (ids are uuid5-deterministic in scratch but legacy random in live;
created_at/updated_at default now() per run).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import get_conn
from table_spec import TABLES, bizhash


def main():
    schema = sys.argv[1] if len(sys.argv) > 1 else "arctic_sprint"
    conn = get_conn()
    with conn.cursor() as cur:
        for table in TABLES:
            cur.execute(f"SELECT count(*) FROM {schema}.{table}")
            n = cur.fetchone()[0]
            h, _ = bizhash(cur, schema, table)
            print(f"{table}|{n}|{h}")
    conn.close()


if __name__ == "__main__":
    main()
