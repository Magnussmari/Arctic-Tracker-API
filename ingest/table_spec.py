#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""Shared table/column spec + canonical content hashing for ingest verification.

Two hash purposes:
1. LIVE COMPARISON (bizhash): scratch vs live `arctic` schema. Documented
   legacy quirks are normalized via SQL column EXPRESSIONS:
   - catch_records.catch_total: the Supabase-era loader wrote NULL where the
     NAMMCO CSV reports an explicit 0 catch. The sprint loader is faithful to
     source (keeps 0, plus maps the '*No reported catches' sentinel to 0).
     nullif() normalizes the legacy quirk for comparison only; the restoration
     is pinned as a hard enrichment expectation in the maintainers' live comparison.
   - catch_records.area / quota: never populated by the legacy load (all NULL
     in live); excluded from the live-comparison hash; enrichment pinned.

2. SOURCE TRUTH (source_hash): independent derivation from the source CSV/
   snapshot, hashed with the SAME canonical serializer as the DB side — a
   loader that zeroed quantity or swapped importer/exporter cannot pass.

Hashing is SHA-256 over a canonical per-row serialization (MD5 is collision-
broken; whole-row ::text is non-canonical). Rows are ordered by all business
columns (fully deterministic: any two rows identical on every business column
serialize identically, so their relative order cannot affect the hash).
"""
import hashlib
from decimal import Decimal, ROUND_HALF_UP

# Postgres numeric rounds half-away-from-zero; Python Decimal defaults to
# half-even. Canonicalize with HALF_UP so source-side and DB-side serializations
# agree (found 2026-07-22: 4 rows at exact .xx5 quantities diverged silently).

# column expression -> canonical type: TEXT | INT | BOOL | NUM2 | UUID
TABLES = {
    "cites_trade_records": {
        "species_id": "UUID", "record_id": "TEXT", "year": "INT",
        "appendix": "TEXT", "taxon": "TEXT", "class": "TEXT",
        "order_name": "TEXT", "family": "TEXT", "genus": "TEXT",
        "term": "TEXT", "quantity": "NUM2", "unit": "TEXT",
        "importer": "TEXT", "exporter": "TEXT", "origin": "TEXT",
        "purpose": "TEXT", "source": "TEXT", "reporter_type": "TEXT",
        "import_permit": "TEXT", "export_permit": "TEXT", "origin_permit": "TEXT",
    },
    "catch_records": {
        "species_id": "UUID", "year": "INT", "area": "TEXT",
        "catch_total": "INT", "quota": "INT",
        "source": "TEXT", "country_id": "UUID", "data_source": "TEXT",
    },
    "illegal_trade_seizures": {
        "species_id": "UUID", "source_database": "TEXT",
        "product_type_id": "UUID", "product_category": "TEXT",
        "reported_taxon_name": "TEXT", "gbif_id": "TEXT",
        "db_taxa_name_clean": "TEXT", "data_source": "TEXT",
    },
    "iucn_assessments": {
        "species_id": "UUID", "year_published": "INT", "is_latest": "BOOL",
        "possibly_extinct": "BOOL", "possibly_extinct_in_wild": "BOOL",
        "status": "TEXT", "url": "TEXT", "assessment_id": "INT",
        "scope_code": "TEXT", "scope_description": "TEXT",
    },
}

# Live-comparison overrides: SQL expression used INSTEAD of the bare column
# (normalizes documented legacy quirks — live comparison only, never source
# truth). Type is unchanged.
LIVE_NORMALIZE = {
    ("catch_records", "catch_total"): "nullif(catch_total, 0)",
}

# Columns excluded from LIVE comparison only (never populated by the legacy
# load — all NULL in live; sprint populates them from the same CSV vintage;
# their enrichment is pinned as hard expectations in the maintainers' live
# comparison).
LIVE_EXCLUDE = {
    ("catch_records", "area"),
    ("catch_records", "quota"),
}


def canon(ctype, v):
    """Canonical string for a value of a given type (None -> '<NULL>')."""
    if v is None:
        return "<NULL>"
    if ctype == "BOOL":
        if isinstance(v, str):
            if v in ("True", "true"):
                return "true"
            if v in ("False", "false"):
                return "false"
            raise ValueError(f"uncanonical bool {v!r}")
        return "true" if v else "false"
    if ctype == "INT":
        return str(int(v))
    if ctype == "NUM2":
        return str(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return str(v)


def row_string(coltypes, values):
    return "|".join(canon(t, v) for t, v in zip(coltypes, values))


def hash_rows(coltypes, rows):
    """SHA-256 over sorted canonical row strings (order-independent)."""
    h = hashlib.sha256()
    n = 0
    for s in sorted(row_string(coltypes, r) for r in rows):
        h.update(s.encode("utf-8"))
        h.update(b"\n")
        n += 1
    return h.hexdigest(), n


def _expr(table, col, live_compare):
    if live_compare and (table, col) in LIVE_NORMALIZE:
        return LIVE_NORMALIZE[(table, col)]
    return f'"{col}"'


def bizhash(cur, schema, table, live_compare=False):
    """SHA-256 content hash of a DB table's business columns."""
    spec = TABLES[table]
    cols = [c for c in spec if not (live_compare and (table, c) in LIVE_EXCLUDE)]
    collist = ", ".join(_expr(table, c, live_compare) for c in cols)
    order = ", ".join(_expr(table, c, live_compare) for c in cols)
    cur.execute(f'SELECT {collist} FROM "{schema}"."{table}" ORDER BY {order}')
    coltypes = [spec[c] for c in cols]
    return hash_rows(coltypes, cur.fetchall())
