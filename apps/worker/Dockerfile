# syntax=docker/dockerfile:1
#
# Image du worker Dramatiq.
#
# LOT 1, sous-etape T2, story MVP-L01-US002.
# LOT 1, sous-etape T7, story MVP-L01-US006 — injection de version (DEC-480),
#   labels OCI, et suppression du `chown -R` final.
#
# Meme socle, meme epinglage et meme contexte de construction que l'image de
# l'API : voir apps/api/Dockerfile pour le detail des motifs, notamment celui de
# la suppression du `chown -R`, qui pesait 143 Mio mesures ici aussi.

FROM ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c AS uv

FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea


# CORRECTIF DE SECURITE PRIS DANS DEBIAN, ET IL EST EPINGLE
#
#   `perl-base` 5.40.1-6 porte `CVE-2026-13221`, **CRITICAL**, et le correctif
#   `5.40.1-6+deb13u1` EXISTE dans `trixie/main` -- mesure du 14/09/2026,
#   `apt-cache policy` le donne comme candidat. Il n'est dans AUCUNE image
#   amont : `python:3.12-slim` n'a pas ete reconstruit depuis sa publication, et
#   les deux architectures portent encore la version vulnerable.
#
#   `DEC-482` bloque la porte des images sur un `CRITICAL` **corrigeable**. Le
#   correctif etant disponible, la porte a RAISON, et la reponse fidele est de le
#   prendre -- non d'affaiblir la porte (§7.20).
#
#   LA VERSION EST EPINGLEE, et c'est ce qui rend cette couche acceptable dans un
#   depot ou tout l'est : la construction reste reproductible tant que cette
#   version est au depot, et le jour ou Debian la retire, le build CASSE
#   BRUYAMMENT au lieu de deriver en silence. C'est le parti du §7.21 -- mieux
#   vaut un echec qui nomme sa cause qu'une derive que personne ne voit.
RUN apt-get update \
 && apt-get install --no-install-recommends -y perl-base=5.40.1-6+deb13u1 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/home/onboarding/.cache/uv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=uv /uv /uvx /usr/local/bin/

RUN useradd --create-home --uid 10001 onboarding \
    && install -d -o onboarding -g onboarding /app /opt/venv

USER onboarding
WORKDIR /app

COPY --chown=onboarding:onboarding pyproject.toml uv.lock ./
COPY --chown=onboarding:onboarding apps/api/pyproject.toml ./apps/api/
COPY --chown=onboarding:onboarding apps/worker/pyproject.toml ./apps/worker/
# Le troisieme membre du workspace uv, ajoute en T4 : sans lui, `uv sync`
# repond « Failed to determine installation plan », le verrou mentionnant un
# membre absent du contexte de construction.
COPY --chown=onboarding:onboarding packages/observabilite/pyproject.toml ./packages/observabilite/

RUN --mount=type=cache,target=/home/onboarding/.cache/uv,uid=10001,gid=10001 \
    uv sync --frozen --no-dev --no-install-workspace

COPY --chown=onboarding:onboarding apps/api ./apps/api
COPY --chown=onboarding:onboarding apps/worker ./apps/worker
COPY --chown=onboarding:onboarding packages/observabilite ./packages/observabilite

RUN --mount=type=cache,target=/home/onboarding/.cache/uv,uid=10001,gid=10001 \
    uv sync --frozen --no-dev

# IDENTITE DU BUILD — DEC-480. Le worker n'expose aucun endpoint, mais il ecrit
# `APP_VERSION` dans le champ `version` des dix champs du cahier 28.1 :
# `worker/main.py` le lit par `os.environ.get("APP_VERSION", "0.0.0-dev")`. Sans
# injection, chaque ligne de journal du worker affirmerait `0.0.0-dev`, quelle
# que soit l'image reellement en cours d'execution — et un journal qui se trompe
# de version rend le diagnostic de production impossible.
ARG APP_VERSION=0.0.0-dev
ARG APP_REVISION=inconnue
ENV APP_VERSION=${APP_VERSION} \
    APP_REVISION=${APP_REVISION}

LABEL org.opencontainers.image.title="onboarding-digital/worker" \
      org.opencontainers.image.description="Worker Dramatiq - eXalt Onboarding Digital" \
      org.opencontainers.image.source="https://github.com/Jonathan2433/ONBOARDING_DIGITAL" \
      org.opencontainers.image.licenses="UNLICENSED" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${APP_REVISION}"

# Le nombre de fils vient de WORKER_CONCURRENCY (`.env.example`), avec 2 par
# defaut. Un seul processus : la machine ne dispose que de 7,75 Gio pour Docker
# (DEC-440), et le parallelisme utile viendra du LOT 11.
CMD ["sh", "-c", "dramatiq worker.main --processes 1 --threads ${WORKER_CONCURRENCY:-2}"]
