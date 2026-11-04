# Contributing

This repository is the analysis code for a published study. Its `main` branch
corresponds to the release cited in the paper, so it changes only for
corrections.

- **Found a problem reproducing a result?** Open an issue with the command you
  ran, the output, and the digest `deposit/rebuild_iucn.py` reported.
- **A correction to the code?** Open a pull request against `main` with a short
  description of what changes and why. The authors review every change.

Never commit credentials. Database access is read from `ARCTIC_DATABASE_URL` in
the environment.
