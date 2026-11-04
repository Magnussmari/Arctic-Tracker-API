# Arctic Tracker: analysis code

Code for *Trading for Conservation: Recorded Trade and Post-Listing Conservation
Status in CITES-Listed Arctic Species* (Tom Barry and Magnús Smári Smárason,
University of Akureyri).

It builds, curates, reconciles and analyses the Arctic Tracker corpus: 43
CITES-listed Arctic species, their CITES and CMS listings, 492,095 CITES trade
records (CITES Trade Database release v2025.1), illegal-trade seizure records
and the IUCN Red List assessment history. It also draws the paper's figures and
emits their Source Data.

- **Data, version of record:** Zenodo, https://doi.org/10.5281/zenodo.23578787
- **Live instance:** https://www.thearctic.is, updated continuously. It is
  for browsing and currency only; every result in the paper reproduces from
  the Zenodo snapshot, not from the live site.

This repository is a fresh tree with a single commit, so it carries no
history from earlier working repositories.

## What is here

| path | what it does |
|---|---|
| `ingest/` | loaders and reconciliation for the CITES, CMS, IUCN and NAMMCO sources |
| `visualizations/` | the figure generators and the scripts that emit Source Data |
| `deposit/` | the deposit builders, the journal figure builders, `load_deposit.sh` and `rebuild_iucn.py` |
| `deposit/verification/` | the verifiers a reader runs; several are copies of the `ingest/` gates, adapted to read the unpacked deposit instead of a database |
| `deposit/identifiers/` | IUCN assessment identifiers and catch-record identifiers |
| `schema.sql`, `migrations/` | the schema of record and the numbered migrations from `0010` |
| `requirements.lock.txt`, `Dockerfile` | the pinned environment that produced the reported numbers |

The loaders in `ingest/` document how the corpus was built from the raw CITES,
CMS, IUCN and NAMMCO sources. They need those source extracts and a database
role that can create schemas, so a reader starts from the Zenodo snapshot
instead, as below.

## Reproducing the paper

1. Download the deposit from Zenodo and unzip it in the repository root. It
   unpacks into `deposit/`, beside the code already there:

   ```sh
   unzip -n arctic-tracker-deposit-*.zip
   ```

   `-n` keeps the files this repository already has. Where the snapshot and the
   repository both carry a script, the repository's copy is the maintained one,
   so `deposit/MANIFEST.sha256.json`, which describes the snapshot, will not
   match those copies. The Zenodo record is the version of record.
2. Rebuild the Red List categories, which the deposit may not redistribute
   (needs a free IUCN API token; see `deposit/REBUILD-IUCN.md`):

   ```sh
   cd deposit && python3 rebuild_iucn.py
   ```

   Use this repository's `rebuild_iucn.py`, not the copy in the 1.0 snapshot.
   The snapshot's copy sends Python's default User-Agent, which IUCN's API now
   refuses with HTTP 403. This one asks once per species and waits out rate
   limits. It also names any assessment IUCN has withdrawn since the snapshot:
   one so far, which leaves 143 of 144 claims and every trajectory reproducible
   (see `deposit/REBUILD-IUCN.md`).

3. Recompute every reported value offline, with no database (from `deposit/`,
   or `make verify-offline` from the root):

   ```sh
   PYTHONDONTWRITEBYTECODE=1 python3 verification/verify_claims_offline.py
   PYTHONDONTWRITEBYTECODE=1 python3 verification/verify_trajectories_offline.py
   ```

   Both need step 2 first. Without an IUCN token they run their self-tests and
   stop with UNMEASURED rather than report numbers they could not compute.

4. Regenerate every Source Data file end to end, in the pinned environment.
   After steps 1 and 2, from the repository root:

   ```sh
   docker network create arctic
   docker run -d --name arctic-db --network arctic -e POSTGRES_DB=arctic \
       -e POSTGRES_PASSWORD=<choose one> -e POSTGRES_INITDB_ARGS=--locale=en_US.utf8 \
       postgres:17.5
   docker build -t arctic-tracker .
   export ARCTIC_DATABASE_URL=postgresql://postgres:<the password>@arctic-db:5432/arctic
   run() { docker run --rm --network arctic -e ARCTIC_DATABASE_URL arctic-tracker "$@"; }
   run bash deposit/load_deposit.sh                 # the snapshot: 22 tables
   run python deposit/load_iucn_categories.py       # the categories from step 2
   docker run --name arctic-run --network arctic -e ARCTIC_DATABASE_URL \
       arctic-tracker make reproduce
   docker cp arctic-run:/app/visualizations/source_data ./regenerated
   ```

   `regenerated/` then holds every figure's Source Data. Measured on
   4 November 2026 from a fresh PostgreSQL 17.5: all ten files are byte-identical
   to the deposit's `source_data.zip`, the six that carry categories after
   `rebuild_iucn.py` has restored them. With the one withdrawn assessment
   missing, `figure5_source_data.csv` lacks that one row's category.

   Without Docker: create `.venv` from `requirements.lock.txt`, load the database
   the same way, and run `make reproduce`. Rendering the figures as images needs
   a Chrome or Chromium browser for `kaleido`.

## What is not here, and why

**No data.** The corpus is deposited on Zenodo under its own DOI. This
repository holds the code that produces and checks it.

**No IUCN Red List categories.** IUCN's terms prohibit redistributing them,
including by archiving them in a public repository. `deposit/rebuild_iucn.py`
fetches them from IUCN's API using the deposited assessment identifiers. It then
checks the result against the recorded digest of the series the paper was
computed on.

**No credentials.** Database access is read from `ARCTIC_DATABASE_URL` in the
environment and is never committed.

## Licence and citation

The code is released under the MIT Licence (`LICENSE`). Derived aggregations,
the data dictionary and the documentation are released under CC BY 4.0
(`LICENSE-docs.md`).
Third-party source data remain under their originators' terms. To cite the
software, use `CITATION.cff`.
