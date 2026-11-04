# Arctic Tracker: reproduction entry points.
#
# Every target that reads the corpus needs ARCTIC_DATABASE_URL, pointing at a
# PostgreSQL 17 database loaded from the Zenodo snapshot with
# deposit/load_deposit.sh. Credentials come from the environment only.
#
# $(PY) is quoted at every use, so the repository can live under a path that
# contains spaces or parentheses.

# The project interpreter. The Dockerfile sets PY to the image's own Python,
# where the pinned packages are installed and there is no .venv.
PY ?= $(CURDIR)/.venv/bin/python
SHELL := /bin/bash

.PHONY: help reproduce figures check-figures verify-offline supplementary lock

help:
	@echo "make reproduce       regenerate every Source Data file from the snapshot"
	@echo "make check-figures   regenerate into scratch and compare byte for byte"
	@echo "make verify-offline  recompute the paper's claims and trajectories, no database"
	@echo "make supplementary   derive the supplementary tables from the corpus"
	@echo "make lock            refresh requirements.lock.txt from this interpreter"
	@echo
	@echo "reproduce, check-figures and supplementary need ARCTIC_DATABASE_URL"
	@echo "(see deposit/load_deposit.sh). verify-offline needs the unpacked deposit"
	@echo "and the rebuilt IUCN categories (see deposit/REBUILD-IUCN.md)."

$(PY):
	@echo "No project interpreter at $(PY)."
	@echo "Create it with: python3 -m venv .venv && .venv/bin/pip install -r requirements.lock.txt"
	@echo "or set PY to an interpreter that has them."
	@exit 1

NEED_DB = @test -n "$$ARCTIC_DATABASE_URL" || { echo "ARCTIC_DATABASE_URL is not set: load the snapshot with deposit/load_deposit.sh and point it there"; exit 1; }

# Regenerates the intermediate exports from the corpus, runs the figure
# scripts, and writes each figure's Source Data table.
reproduce: $(PY)
	$(NEED_DB)
	"$(PY)" visualizations/make_all_figures.py

figures: reproduce

# Determinism: rerun the whole chain into a scratch location and compare the
# Source Data byte for byte against the recorded tables.
check-figures: $(PY)
	$(NEED_DB)
	"$(PY)" visualizations/make_all_figures.py --check

# The deposit's own verifiers, from deposit/: every traceable claim and every
# category trajectory, recomputed from the Source Data with no database.
verify-offline: $(PY)
	cd deposit && PYTHONDONTWRITEBYTECODE=1 "$(PY)" verification/verify_claims_offline.py
	cd deposit && PYTHONDONTWRITEBYTECODE=1 "$(PY)" verification/verify_trajectories_offline.py

# Four of the nine supplementary tables are derived from the corpus rather than
# maintained by hand.
supplementary: $(PY)
	$(NEED_DB)
	"$(PY)" ingest/build_supplementary.py
	"$(PY)" ingest/strip_narrative_citations.py --write
	"$(PY)" ingest/build_change_table.py

# The lockfile records what the interpreter that produced the reported numbers
# had installed. It is regenerated, not edited.
lock: $(PY)
	"$(PY)" -m pip freeze --exclude-editable > requirements.lock.txt
	@echo "requirements.lock.txt: $$(grep -c '==' requirements.lock.txt) exact pins"
