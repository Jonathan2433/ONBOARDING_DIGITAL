# syntax=docker/dockerfile:1
#
# Image du worker Dramatiq.
#
# LOT 1, sous-etape T2, story MVP-L01-US002.
#
# Meme socle, meme epinglage et meme contexte de construction que l'image de
# l'API : voir apps/api/Dockerfile pour le detail des motifs.
#
# ETAT A T2
#   Aucun code applicatif. Le demarrage Dramatiq et la declaration des sept
#   files validees arrivent en T3 et T4 ; la persistance des jobs, l'outbox
#   transactionnelle et l'idempotence relevent du LOT 11.

FROM ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c AS uv

FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml ./apps/api/
COPY apps/worker/pyproject.toml ./apps/worker/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace

COPY apps/api ./apps/api
COPY apps/worker ./apps/worker

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 onboarding \
    && chown -R onboarding:onboarding /app /opt/venv
USER onboarding

# T2 : voir apps/api/Dockerfile. Le healthcheck du fichier Compose verifie que
# le paquet `worker` est importable. T3 remplacera cette commande par dramatiq.
CMD ["sleep", "infinity"]
