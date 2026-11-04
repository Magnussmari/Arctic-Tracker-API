# Rebuilding the IUCN Red List categories

This deposit carries no IUCN Red List category. It carries IUCN's own
assessment identifiers, and this file tells you how to turn them back into the
corpus the paper was computed on.

## Why

The IUCN Red List Terms and Conditions of Use state that

> All forms of reposting, and any … redistribution of IUCN Red List Data in
> their original format, either whole or in part, alone or combined with other
> data, including within Derivative Works, are strictly prohibited without the
> prior written permission of IUCN. Users may not repost or redistribute …
> including … archiving in a public data repository …

A Red List category is Red List Data, and a public repository is exactly where
this deposit lives. An assessment identifier is not Red List Data: it is a
pointer into IUCN's own published record, and IUCN publishes the category at
that pointer.

So the category reaches you from IUCN, under your own acceptance of their
terms, and not from us. Nothing about the paper's procedure is withheld. What
changes is the first step: you fetch, then everything else in this package runs
as it always did.

This is not only the lawful arrangement, it is the better one. Your corpus is
then traceable to the assessments rather than to our copy of them, and if IUCN
has reassessed a species since we did, you will see that rather than inherit
our snapshot silently.

## What ships instead

`identifiers/iucn_assessment_ids.csv` — 370 rows, one per assessment:

| column | meaning |
|---|---|
| `scientific_name` | the species, as this corpus names it |
| `year_published` | IUCN's publication year for that assessment |
| `assessment_id` | IUCN's own assessment identifier |
| `scope` | `Global`, or a regional scope such as `Europe` |
| `is_latest` | whether this corpus treats it as the species' latest assessment |
| `redlist_url` | IUCN's permalink for the assessment |

Every withheld cell in the Source Data carries the `assessment_id` that fills
it. Twenty-five species-years hold two assessments published in the same year,
because IUCN republishes; those rows name both identifiers, separated by `;`,
and either resolves to the same category.

## How

```sh
export IUCN_API_TOKEN=...            # request one at https://api.iucnredlist.org
cd deposit
python3 rebuild_iucn.py
```

The script reads the identifier table, fetches each assessment from IUCN's
API v4, writes the restored files into `deposit/rebuilt/`, and caches the
category map in `deposit/rebuilt/iucn_categories.json` so a second run needs
no network. If you already hold a map of `{assessment_id: category}` you can
skip the fetch:

```sh
python3 rebuild_iucn.py --from-json your_categories.json
```

Nothing in `rebuilt/` is part of this deposit, and nothing there may be
redistributed — it is your copy, under your terms with IUCN.

## How you know you rebuilt the right thing

`REBUILD-IUCN.digest` records the SHA-256 of
`Source Data/figure5_source_data.csv` as the paper was computed on it.
`rebuild_iucn.py` checks your reconstituted copy against it and says MATCH or
MISMATCH. A match proves, byte for byte, that you hold the same corpus,
without IUCN data ever having passed through us.

All six withheld Source Data files rebuild byte-exactly from the identifiers;
the digest is recorded for the per-assessment series because every other file
derives from it.

A mismatch is not necessarily an error on your side. IUCN reassess and
republish, so a later fetch can legitimately differ. If that happens, report
the digest you obtained alongside any number you recompute — that is more
useful than silence either way.

## Then the verifiers

The deposit's verifiers read Source Data through
`verification/iucn_series.py`, which prefers your rebuilt copy. Before the
rebuild they stop with `UNMEASURED` and point here. After it:

```sh
cd deposit
PYTHONDONTWRITEBYTECODE=1 python3 verification/verify_claims_offline.py
PYTHONDONTWRITEBYTECODE=1 python3 verification/verify_trajectories_offline.py
```

Both then recompute the paper's claims from the package alone, with no
database and no credentials.

## One thing to know about `is_latest`

In this corpus `is_latest` marks the most recent assessment of **any** scope,
not the most recent global one. For 17 of the 43 species that most recent
assessment is a European regional assessment published in 2023 or 2025,
including *Ursus maritimus*. No figure takes its category from that flag. The
Source Data files `figure1`, `figure7` and `figure8` carry, for each species,
its most recent **global** assessment: `scope == "Global"` in the identifier
table, the eight assessments listed in
`species_data/curated/iucn_scope_corrections.csv` excluded because IUCN records
them without a scope although they are regional, and, where two global
assessments share a year, the higher `assessment_id`. The `assessment_id` in
each of those rows is that assessment. Those names are pipeline identifiers:
`figure7` is manuscript Figure 8, `figure8` is manuscript Figure 7, and
`figure1` is bound to no manuscript figure (see `SOURCE_DATA_INDEX.md` inside `source_data.zip`).
Since 21 October 2026 the running text, Figure 4 and every trajectory
statistic use global and European assessments as one series: `scope` is
`Global` or `Europe` in the identifier table, ordered by year and assessment id,
and the one Mediterranean assessment (16527805, *Lamna nasus* 2016) is left out.

## Assessments withdrawn since the snapshot

IUCN withdraws and replaces assessments, and a withdrawn assessment no longer
has a category in the API. As of 4 November 2026, one of the 370 assessments
the paper used has gone: *Ziphius cavirostris*, 2012, Global, assessment
2785108. The taxon record now lists 2008, 2020 and 2023 for the species, but
not 2012.

`rebuild_iucn.py` names every such assessment rather than guessing its
category. Without it the rebuilt series cannot match `REBUILD-IUCN.digest`.
Measured on 4 November 2026 with the other 369 categories:

- every trajectory statistic and all 43 category transitions reproduce;
- 143 of the 144 traceable claims reproduce. C10, the count of assessments
  using a pre-2001 category, comes out one higher, because the missing category
  is not counted as a modern one.

With the 2012 category supplied (`--add 2785108=<code>`), the series matches
the digest and all 144 claims reproduce.

The script asks IUCN once per species (43 calls, not 370), sends its own
User-Agent, which the API requires, and waits out rate limits. The copy in the
1.0 Zenodo snapshot does neither and fails with HTTP 403. Use the copy in the
code repository.
