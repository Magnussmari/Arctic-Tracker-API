#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-22
"""Shared psycopg2 plumbing for figure-source regeneration (visualizations).

Reads ARCTIC_DATABASE_URL from the environment (never hardcoded).
"""
import os
import sys

import psycopg2


def get_conn():
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set ARCTIC_DATABASE_URL in the environment)")
    return psycopg2.connect(url)


def query(sql, params=None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()
