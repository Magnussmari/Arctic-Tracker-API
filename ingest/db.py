#!/usr/bin/env python3
"""Shared psycopg2 plumbing for the sovereign ingest pipeline.

Connection: ARCTIC_DATABASE_URL env var (never hardcode credentials). The
loader role is arctic_admin (RLS-bypassing superuser) — the RLS-blind
arctic_app role cannot see the tables. Single-tenant model.

Every load runs in ONE transaction (atomic per table): a mid-load death rolls
back to the prior good state.
"""
import json
import os
import re
import sys
import hashlib
import psycopg2
import psycopg2.extras

_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_ALIASES = None


def validate_schema(schema: str) -> str:
    """Allowlist-validate a --target-schema argv value (kills SQL injection:
    all schema/table identifiers in this pipeline are otherwise static)."""
    if not _SCHEMA_RE.match(schema or ""):
        sys.exit(f"invalid target schema {schema!r}: must match ^[a-z_][a-z0-9_]*$")
    return schema


def load_aliases() -> dict:
    """Frozen CITES-name alias map (ingest/aliases.json, test-pinned)."""
    global _ALIASES
    if _ALIASES is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aliases.json")
        with open(p, encoding="utf-8") as f:
            _ALIASES = json.load(f)["cites_aliases"]
    return _ALIASES


def get_conn():
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set ARCTIC_DATABASE_URL in the environment; never hardcode it)")
    return psycopg2.connect(url)


def ensure_scratch_schema(cur, schema: str):
    """Create a scratch schema mirroring arctic's structure (no data)."""
    validate_schema(schema)
    if schema == "arctic":
        return
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'arctic'")
    for (tablename,) in cur.fetchall():
        cur.execute(
            f'CREATE TABLE IF NOT EXISTS "{schema}"."{tablename}" (LIKE arctic."{tablename}" INCLUDING ALL)'
        )


def content_hash(cur, schema: str, table: str, order_col: str = "id") -> str:
    """MD5 over all rows (stable order) for before/after idempotency proof."""
    cur.execute(f"""
        SELECT md5(string_agg(t.rowhash, '' ORDER BY t.rowhash))
        FROM (SELECT md5({table}::text) AS rowhash FROM {schema}.{table} ORDER BY {order_col}) t
    """)
    return cur.fetchone()[0]


def count(cur, schema: str, table: str) -> int:
    cur.execute(f"SELECT count(*) FROM {schema}.{table}")
    return cur.fetchone()[0]


def copy_records(cur, schema: str, table: str, columns: list, rows) -> int:
    """Bulk-load rows (iterable of tuples) via COPY inside the current txn."""
    from io import StringIO
    buf = StringIO()
    n = 0
    for row in rows:
        buf.write("\t".join("\\N" if v is None else str(v).replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r") for v in row))
        buf.write("\n")
        n += 1
    buf.seek(0)
    cols = ", ".join(columns)
    cur.copy_expert(f"COPY {schema}.{table} ({cols}) FROM STDIN WITH (FORMAT text, NULL '\\N')", buf)
    return n


def load_species_map(cur, schema: str = "arctic") -> dict:
    """scientific_name -> species uuid, with known taxonomic aliases.

    `schema` selects which species table to resolve against so the same loader
    can target the v2 rebuild; it is allowlist-validated because it reaches SQL.
    """
    schema = validate_schema(schema)
    cur.execute(f"SELECT id, scientific_name FROM {schema}.species")
    m = {name: str(sid) for sid, name in cur.fetchall()}
    # CITES-name aliases observed in the trade data (H3 methodology documents
    # these; frozen in ingest/aliases.json, test-pinned).
    for src, dst in load_aliases().items():
        if dst in m:
            m[src] = m[dst]
    return m


def md5_file(path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
