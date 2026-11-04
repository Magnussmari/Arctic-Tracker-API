# The environment that produced the reported numbers.
#
# Pinned against what actually ran, measured 2026-08-31 rather than recalled:
#   Python           3.13.1   (the interpreter that generated requirements.lock.txt)
#   PostgreSQL       17.5     (server_version on the database of record; the
#                             image installs the pgdg 17 client series, whose
#                             point release tracks the repository and is not
#                             pinned to the server's — client and server are
#                             wire-compatible across it)
#   Collation        en_US.utf8, ctype en_US.utf8
#
# The collation matters and is not decoration: PostgreSQL string ordering is
# collation-dependent, so a different collation regroups results and can move a
# reported number without any code change.
#
# Build:  docker build -t arctic-tracker .
# Run:    docker run --rm -e ARCTIC_DATABASE_URL="$ARCTIC_DATABASE_URL" \
#                    arctic-tracker make reproduce

FROM python:3.13.1-slim-bookworm

# libpq for psycopg2, and the v17 client so pg_dump/psql match the server of
# record rather than whatever the base image happens to carry.
RUN apt-get update && apt-get install --no-install-recommends -y \
        ca-certificates curl gnupg make locales \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] \
        http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client-17 libpq5 \
        chromium git \
    && rm -rf /var/lib/apt/lists/* \
    # Generate the locale rather than only naming it: an uninstalled locale
    # falls back to C, and collation changes results.
    && sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen \
    && locale-gen en_US.UTF-8

ENV PYTHONDONTWRITEBYTECODE=1 \
    PY=/usr/local/bin/python \
    BROWSER_PATH=/usr/bin/chromium \
    PYTHONUNBUFFERED=1 \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    LC_COLLATE=en_US.UTF-8 \
    LC_CTYPE=en_US.UTF-8

WORKDIR /app

# Dependencies before source, so editing a script does not reinstall 70 pinned
# packages. --require-hashes is deliberately not set: the lockfile pins versions
# but carries no hashes.
COPY requirements.lock.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.lock.txt

COPY . .

# No credential is baked in. ARCTIC_DATABASE_URL is passed at run time from the
# environment; a database URL in an image layer is a leaked
# credential that survives every later deletion.
CMD ["make", "reproduce"]
