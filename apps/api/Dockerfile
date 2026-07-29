# syntax=docker/dockerfile:1
#
# Image de l'API FastAPI.
#
# LOT 1, sous-etape T2, story MVP-L01-US002.
# LOT 1, sous-etape T7, story MVP-L01-US006 — injection de version (DEC-480),
#   labels OCI, et suppression du `chown -R` final.
#
# EPINGLAGE — DEC-443 et cahier des charges 23.3
#   Les bases sont referencees par tag de version ET par empreinte sha256.
#   Aucune reference a `latest`, seule ou non. L'empreinte va au-dela de
#   l'interdiction du cahier : elle rend l'image bit pour bit reproductible.
#
# CONTEXTE DE CONSTRUCTION
#   La racine du depot, et non apps/api : les dependances sont resolues par le
#   workspace uv declare a la racine (DEC-455), dont uv.lock est le verrou.
#   Construire depuis apps/api priverait uv de son verrou.

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
    UV_CACHE_DIR=/home/onboarding/.cache/uv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=uv /uv /uvx /usr/local/bin/

# Utilisateur non privilegie, cree AVANT toute copie. Le cahier 20.1 impose le
# moindre privilege ; un processus applicatif n'a aucune raison d'etre root.
#
# LE `chown -R` FINAL EST SUPPRIME, ET IL PESAIT 143 Mio. MESURE.
#   `docker history` du 29/07/2026 sur l'image de T2 :
#     RUN uv sync --frozen --no-dev --no-install-workspace   ->  143 MB
#     RUN useradd ... && chown -R onboarding:onboarding ...   ->  143 MB
#   Un `chown -R` reecrit chaque inode, et une couche d'image reenregistre le
#   fichier ENTIER des qu'un seul de ses metadonnees change : la couche
#   DUPLIQUE donc l'arborescence dont elle ne change que le proprietaire.
#   Creer l'utilisateur d'abord, donner les deux repertoires a la creation, puis
#   copier avec --chown, produit le meme resultat sans la seconde copie.
RUN useradd --create-home --uid 10001 onboarding \
    && install -d -o onboarding -g onboarding /app /opt/venv

USER onboarding
WORKDIR /app

# Le verrou et les manifestes d'abord : la couche de dependances n'est
# reconstruite que s'ils changent, pas a chaque modification du code.
# Les trois membres du workspace sont necessaires : le pyproject.toml racine
# declare une dependance sur chacun d'eux.
COPY --chown=onboarding:onboarding pyproject.toml uv.lock ./
COPY --chown=onboarding:onboarding apps/api/pyproject.toml ./apps/api/
COPY --chown=onboarding:onboarding apps/worker/pyproject.toml ./apps/worker/
# Le troisieme membre du workspace uv, ajoute en T4 : sans lui, `uv sync`
# repond « Failed to determine installation plan », le verrou mentionnant un
# membre absent du contexte de construction.
COPY --chown=onboarding:onboarding packages/observabilite/pyproject.toml ./packages/observabilite/

# uid et gid sur le montage de cache : il est monte root par defaut, et
# l'installation tourne desormais sous `onboarding`.
RUN --mount=type=cache,target=/home/onboarding/.cache/uv,uid=10001,gid=10001 \
    uv sync --frozen --no-dev --no-install-workspace

COPY --chown=onboarding:onboarding apps/api ./apps/api
COPY --chown=onboarding:onboarding apps/worker ./apps/worker
COPY --chown=onboarding:onboarding packages/observabilite ./packages/observabilite

RUN --mount=type=cache,target=/home/onboarding/.cache/uv,uid=10001,gid=10001 \
    uv sync --frozen --no-dev

# IDENTITE DU BUILD — DEC-480, cahier 18.7, `.env.example` sections 1 et 15.
#
# Jusqu'a T7, `/health/version` renvoyait les valeurs par DEFAUT de
# `settings.py` — `0.0.0-dev` et `inconnue` — parce que ni le Dockerfile ni
# Compose ne transmettaient ces variables. Le critere de `MVP-L01-US003`, « la
# version correspond au build », n'etait donc pas satisfait : il etait seulement
# non contredit, faute de build identifie.
#
# Les valeurs par defaut restent celles de `.env.example` : une image construite
# a la main sans arguments continue de dire honnetement qu'elle ne connait pas sa
# revision, plutot que d'afficher un numero faux.
#
# Une variable d'environnement d'execution — celle que Compose injecte — prime
# sur cet ENV. C'est voulu : l'image porte l'identite de SA construction, et
# l'environnement peut la surcharger.
ARG APP_VERSION=0.0.0-dev
ARG APP_REVISION=inconnue
ENV APP_VERSION=${APP_VERSION} \
    APP_REVISION=${APP_REVISION}

LABEL org.opencontainers.image.title="onboarding-digital/api" \
      org.opencontainers.image.description="API FastAPI - eXalt Onboarding Digital" \
      org.opencontainers.image.source="https://github.com/Jonathan2433/ONBOARDING_DIGITAL" \
      org.opencontainers.image.licenses="UNLICENSED" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${APP_REVISION}"

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
