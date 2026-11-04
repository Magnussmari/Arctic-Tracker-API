#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Reviewer tool: read gated content, record a signed verdict.

WHY THIS EXISTS
---------------
Gated content (narrative sections and reference bindings) is not servable until
a reviewer signs it. A gate with no key is not a workflow, so this tool gives a
reviewer a way to read gated content and record a verdict.

THE ROLE SEPARATION THAT MAKES THIS SAFE
-----------------------------------------
`arctic_app` cannot read unreviewed content and must not be able to. A reviewer
obviously must. Those are different jobs, so they are different roles:

    arctic_app       reads arctic_api only; sees signed content, never drafts
    arctic_reviewer  reads the drafts, and may INSERT reviews. Nothing else:
                     it cannot edit a narrative, cannot delete, cannot change a
                     binding, and cannot touch any fact table.
    arctic_admin     everything, used only by loaders

A reviewer approving text they can edit is not a review, so the reviewer role is
deliberately denied UPDATE on the content it signs.

WHAT THIS TOOL WILL NOT DO
--------------------------
- No bulk approve. Every verdict is recorded against one item with its own
  rationale. The whole defect being answered is 43 species of machine text
  marked reviewed by nobody; a --approve-all flag would recreate it in one line.
- No default rationale. The database requires 20 characters and this tool does
  not supply them on the reviewer's behalf.
- No model assistance in the verdict. A model may have drafted the text under
  review; it takes no part in deciding whether the text is sound.

Usage:
  ARCTIC_REVIEWER_URL=... python ingest/review_cli.py pending
  ARCTIC_REVIEWER_URL=... python ingest/review_cli.py show <narrative-id>
  ARCTIC_REVIEWER_URL=... python ingest/review_cli.py sign <narrative-id> \\
      --reviewer "<name>" --verdict approved --rationale "..."
"""
import argparse
import os
import sys
import textwrap

import psycopg2

SCHEMA = "arctic_v2"
MIN_RATIONALE = 20


def connect(readonly: bool = True):
    url = os.environ.get("ARCTIC_REVIEWER_URL")
    if not url:
        sys.exit("ARCTIC_REVIEWER_URL not set (set it in the environment; never hardcode it)")
    conn = psycopg2.connect(url, connect_timeout=20)
    if readonly:
        conn.set_session(readonly=True)
    return conn


def cmd_pending(args) -> int:
    """List what is waiting, grouped by species."""
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(f"""
            select s.scientific_name,
                   count(*) filter (where not exists (
                       select 1 from {SCHEMA}.narrative_review r
                        where r.narrative_id = n.id and r.verdict = 'approved')) as pending,
                   count(*) as total
              from {SCHEMA}.species_narratives n
              join {SCHEMA}.species s on s.id = n.species_id
             group by s.scientific_name
            having count(*) filter (where not exists (
                       select 1 from {SCHEMA}.narrative_review r
                        where r.narrative_id = n.id and r.verdict = 'approved')) > 0
             order by pending desc, s.scientific_name
             limit %s""", (args.limit,))
        rows = cur.fetchall()
        cur.execute(f"""
            select count(*) from {SCHEMA}.species_narratives n
             where not exists (select 1 from {SCHEMA}.narrative_review r
                                where r.narrative_id = n.id and r.verdict = 'approved')""")
        total_pending = cur.fetchone()[0]
    conn.close()

    print(f"{total_pending} narrative sections awaiting review\n")
    print(f"{'species':32}{'pending':>9}{'total':>7}")
    for name, pending, total in rows:
        print(f"{name:32}{pending:>9}{total:>7}")
    if len(rows) == args.limit:
        print(f"\n(showing {args.limit}; pass --limit for more)")
    return 0


def cmd_show(args) -> int:
    """Print one narrative in full, with everything needed to judge it."""
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(f"""
            select n.id, s.scientific_name, n.section, n.origin, n.citation_count,
                   n.body, n.source_artifact, n.source_sha256
              from {SCHEMA}.species_narratives n
              join {SCHEMA}.species s on s.id = n.species_id
             where n.id::text = %s or (s.scientific_name = %s and n.section = %s)""",
                    (args.identifier, args.identifier, args.section or ""))
        row = cur.fetchone()
        if not row:
            conn.close()
            sys.exit(f"no narrative matching {args.identifier!r}"
                     + (f" section {args.section!r}" if args.section else ""))
        nid, species, section, origin, citations, body, artifact, digest = row
        cur.execute(f"""select reviewer, verdict, rationale, reviewed_at
                          from {SCHEMA}.narrative_review where narrative_id = %s
                         order by reviewed_at""", (nid,))
        reviews = cur.fetchall()
    conn.close()

    print(f"id:        {nid}")
    print(f"species:   {species}")
    print(f"section:   {section}")
    print(f"origin:    {origin}   ({citations} embedded citations)")
    print(f"source:    {artifact}")
    print(f"sha256:    {digest[:16]}...")
    print("\n" + "-" * 76)
    print(textwrap.fill(body, 76))
    print("-" * 76)
    if citations:
        print(f"\nNOTE: {citations} author-year citations are embedded in this prose. None "
              f"carries a DOI or a resolvable link. Checking them is part of the review.")
    if reviews:
        print("\nexisting reviews:")
        for reviewer, verdict, rationale, when in reviews:
            print(f"  {when:%Y-%m-%d} {reviewer} -> {verdict}")
            print(textwrap.fill(rationale, 72, initial_indent="      ", subsequent_indent="      "))
    else:
        print("\nno reviews on file; this content is not servable")
    return 0


def cmd_sign(args) -> int:
    """Record one verdict, against one item, with a rationale."""
    rationale = args.rationale.strip()
    if len(rationale) < MIN_RATIONALE:
        sys.exit(f"rationale must be at least {MIN_RATIONALE} characters; "
                 f"got {len(rationale)}. State what you checked.")
    if not args.reviewer.strip():
        sys.exit("--reviewer must name a person")

    conn = connect(readonly=False)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(f"""select n.id, s.scientific_name, n.section
                                  from {SCHEMA}.species_narratives n
                                  join {SCHEMA}.species s on s.id = n.species_id
                                 where n.id::text = %s""", (args.narrative_id,))
                row = cur.fetchone()
                if not row:
                    sys.exit(f"no narrative with id {args.narrative_id}")
                nid, species, section = row
                cur.execute(f"""insert into {SCHEMA}.narrative_review
                                  (narrative_id, reviewer, verdict, rationale)
                                values (%s, %s, %s, %s)""",
                            (nid, args.reviewer.strip(), args.verdict, rationale))
                cur.execute(f"""select count(*) from {SCHEMA}.servable_species_narratives
                                 where id = %s""", (nid,))
                servable = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"recorded: {args.verdict} by {args.reviewer} on {species} / {section}")
    print(f"servable now: {'yes' if servable else 'no'}")
    if args.verdict == "approved" and not servable:
        print("  (another reviewer has rejected this item; a rejection overrides an approval)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("pending", help="list content awaiting review")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_pending)

    p = sub.add_parser("show", help="print one narrative in full")
    p.add_argument("identifier", help="narrative uuid, or a scientific name with --section")
    p.add_argument("--section")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("sign", help="record a verdict on one narrative")
    p.add_argument("narrative_id")
    p.add_argument("--reviewer", required=True, help="the person accountable for this verdict")
    p.add_argument("--verdict", required=True, choices=["approved", "rejected", "pending"])
    p.add_argument("--rationale", required=True,
                   help=f"what you checked, at least {MIN_RATIONALE} characters")
    p.set_defaults(func=cmd_sign)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
