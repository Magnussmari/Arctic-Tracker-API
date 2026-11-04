# Figures

`make_all_figures.py` regenerates the figure pipeline from the database named by
`ARCTIC_DATABASE_URL`. From the repository root, `make reproduce` runs it.

1. **Intermediates.** The generators in `data_processing/` (the `*_pg.py` files)
   read the corpus and write four intermediate JSON files: CITES trade against
   listing, the IUCN timeline, illegal-trade seizures and wild-origin trade.
2. **Figures.** The scripts in `scripts/` draw figures 1–5, 7 and 8 from those
   intermediates.
3. **Source Data.** Each figure's numbers are written as a CSV table.

`make check-figures` runs the same chain into a scratch location and compares the
Source Data byte for byte with the recorded tables.

The journal versions of Figures 8, 11, 12 and 13 are drawn by the
`build_figure*_journal.py` scripts in `deposit/`.

`provenance/` records where each figure's numbers come from, and where they
differ from the figures in the first submission and why (`PROVENANCE.md`).

The Source Data tables are not in this repository, because some carry
per-species IUCN Red List categories, which may not be redistributed. The scripts
that produce them are.
