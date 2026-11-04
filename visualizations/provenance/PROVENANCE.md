# Figure Provenance & Regeneration — Arctic Tracker (H5)

**Date:** 2026-07-22 · **Machine manifest:** `figure_provenance.json`
**One command:** `./.venv/bin/python visualizations/make_all_figures.py` (set ARCTIC_DATABASE_URL in the environment)
**Verify:** `... make_all_figures.py --check` (byte-exact Source-Data equivalence; G5 gate).

## The chain

Every manuscript figure traces: **arctic table/query → psycopg2 generator →
intermediate JSON → figure script → HTML/PNG + frozen numeric Source-Data CSV**.
`--check` regenerates the Source-Data CSVs from the live sovereign DB and
byte-diffs against the committed ones — a reviewer with DB access re-runs the
pipeline and gets identical numbers.

| Fig | Script | arctic source | Source-Data |
|---|---|---|---|
| 1 | `scripts/figure1_publication.py` | species, cites_listings, iucn_assessments, cites_trade_records, cms_listings, catch_records | `figure1_source_data.csv` |
| 2 | `scripts/figure2_trade_enforcement.py` | same intermediate as fig 1 | `figure2_source_data.csv` |
| 3 | `scripts/figure3_trade_partners.py` (retargeted to psycopg2) | cites_trade_records (direct aggregate) | `figure3_source_data.csv` |
| 4 | `scripts/figure4_conservation_trends.py` | iucn_assessments, species | `figure4_source_data.csv` |
| 5 | `scripts/figure5_status_heatmap.py` | same as fig 4 | `figure5_source_data.csv` |
| 7 | `scripts/figure7_iwt_seizures.py` | cites_trade_records `source='I'` (FULL) | `figure7_source_data.csv` |
| 8 | `scripts/figure8_wild_origin_trade.py` | cites_trade_records `source='W'` (FULL) | `figure8_source_data.csv` |
| 6, 9 | — | **no scripted pipeline exists** — supplied by the authors | — |

## Documented divergences from the *published* figures

Regeneration is faithful to the live sovereign DB. Where that differs from
what was published, the cause is documented, not hidden
(frozen originals: `provenance/frozen_intermediates/`, md5-manifested):

1. **Fig 7 — truncation defect (corrected).** The 2025-11-12 export consumed
   one unpaginated supabase page: 1,000 of 2,606 `source='I'` records. Ranks
   below #1 were wrong (e.g. walrus seizures — #3 by quantity — absent).
   Regenerated on the full 2,606 records.
2. **Fig 8 — truncation defect (corrected).** The export hit its own 50k
   safety cap: 51,000 of 137,304 `source='W'` records. **The published #1
   (minke whale, 2.76M) is wrong; the full-data #1 is fin whale at 16.5M** —
   the truncated run never saw those records. Regenerated on full data.
3. **Fig 1/2 — IUCN vintage + corruption repair.** Published statuses reflect
   the Sep-2025 extract and pre-repair corruption (e.g. one species shown
   several categories below its current one). Regenerated values reflect the Nov-2025 validated IUCN
   rebuild + the 2026-07-22 H2 `is_latest` repair. 3 species renamed since
   (Antigone→Grus, Nyctea→Bubo, B. h. leucopareia→Branta hutchinsii).
4. **Fig 4/5 — `is_latest` flags** reflect the H2 repair (frozen file carries
   the corrupt flags). Severity/trend logic ported verbatim.
5. **Effectiveness `trade_trend` + `data_quality_score`** are a *frozen legacy
   artifact*: their source (the `article_summary_table` computation) was lost
   with the Supabase-era schema. Values are frozen per-species in
   `legacy_frozen_fields.csv` and flagged for the authors — recomputing the
   trend semantics is a domain call, not an automated one. Figures 1/2 use
   `trade_trend` for annotation; all other consumed fields regenerate exactly
   (verified 43/43 on names/taxonomy, 40/40 trade species on counts/wild/mode).
6. **Catch aggregates** in the effectiveness intermediate diverge by vintage
   (the frozen JSON predates the 2025-06-11 NAMMCO reload); figures 1/2 do
   not consume them.
7. **Top-exporter tie-breaks**: 3 species (Eubalaena japonica, Hyperoodon
   ampullatus, Phoebastria albatrus) regenerate a different mode-exporter on
   ties; the stated rule (mode, deterministic order) is now authoritative.

## Colour-vision safety

Fig 1 uses the IUCN Red List standard colour scale (CR red → LC green), the
conventional mapping for status figures, with status labels printed on marks
(redundant encoding). Fig 4/5 heatmaps annotate each cell with the status
code — colour is never the sole channel. Fig 3/7/8 use single-hue sequential
scales (`#2E5266` family), safe under all CVD types. Full palette audit:
`provenance/colour_safety.md`.
