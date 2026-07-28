# syntax=docker/dockerfile:1
#
# Image de l'API FastAPI.
#
# LOT 1, sous-etape T2, story MVP-L01-US002.
#
# EPINGLAGE — DEC-443 et cahier des charges 23.3
#   Les bases sont referencees par tag de version ET par empreinte sha256.
#   Aucune reference a `latest`, seul ou non. L'empreinte va au-dela de
#   l'interdiction du cahier : elle rend l'image bit pour bit reproductible.
#
# CONTEXTE DE CONSTRUCTION
#   La racine du depot, et non apps/api : les dependances sont resolues par le
#   workspace uv declare a la racine (DEC-455), dont uv.lock est le verrou.
#   Construire depuis apps/api priverait uv de son verrou.
#
# ETAT A T2
#   Aucun code applicatif. L'image prouve que ses dependances se resolvent et
#   que le paquet `app` est importable. L'application FastAPI, les trois
#   healthchecks et le point d'entree uvicorn arrivent en T3.

FROM ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c AS uv

FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

# Debian slim et non Alpine : de nombreuses roues Python n'existent pas en
# musl, ce qui forcerait une compilation depuis les sources a chaque
# installation. psycopg et les dependances du LOT 2 en beneficieront.

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /app

# Le verrou et les manifestes d'abord : la couche de dependances n'est
# reconstruite que s'ils changent, pas a chaque modification du code.
# Les deux membres du workspace sont necessaires : le pyproject.toml racine
# declare une dependance sur chacun d'eux.
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml ./apps/api/
COPY apps/worker/pyproject.toml ./apps/worker/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace

COPY apps/api ./apps/api
COPY apps/worker ./apps/worker

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Utilisateur non privilegie. Le cahier 20.1 impose le moindre privilege ;
# un processus applicatif n'a aucune raison d'etre root.
RUN useradd --create-home --uid 10001 onboarding \
    && chown -R onboarding:onboarding /app /opt/venv
USER onboarding

EXPOSE 8000

# `--factory` : uvicorn appelle `creer_application()` lui-meme. L'application
# n'est PAS construite a l'import du module, sinon importer `app.main` lirait
# l'environnement et la collecte des tests echouerait faute de variables.
#
# Si la configuration est invalide, `ConfigurationInvalide` remonte ici et le
# conteneur s'arrete en nommant la variable fautive : c'est le refus de demarrer
# qu'exige le cahier §20.3. Un demarrage en mode degrade serait pire.
#
# 0.0.0.0 dans le conteneur uniquement : le service n'est pas publie sur l'hote,
# seul Caddy le joint par le reseau interne (cahier §22.2).
CMD ["uvicorn", "app.main:creer_application", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
