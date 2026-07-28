# syntax=docker/dockerfile:1
#
# Image du frontend React et Vite.
#
# LOT 1, sous-etape T2, story MVP-L01-US002.
#
# EPINGLAGE — DEC-443 et cahier des charges 23.3
#   Base referencee par tag de version ET par empreinte sha256. Aucune
#   reference a `latest`.
#
# CONTEXTE DE CONSTRUCTION
#   La racine du depot : pnpm-lock.yaml et pnpm-workspace.yaml y resident, et
#   apps/web depend des paquets packages/ui et packages/contracts.
#
# ETAT A T2
#   Outillage seul. Il n'existe ni index.html, ni point d'entree React : ils
#   appartiennent a T5, avec la page de statut. L'image prouve que les
#   dependances du workspace s'installent depuis le verrou.

FROM node:24.16-alpine@sha256:21f403ab171f2dc89bad4dd69d7721bfd15f084ccb46cdd225f31f2bc59b5c9a

ENV CI=true \
    PNPM_HOME=/pnpm \
    PATH="/pnpm:$PATH"

# pnpm est fourni par corepack, deja present dans l'image node. La version
# exacte est lue dans le champ packageManager de package.json, empreinte
# d'integrite comprise : aucun binaire tiers n'est telecharge a l'aveugle.
RUN corepack enable pnpm

WORKDIR /app

# Verrou et manifestes d'abord, pour que la couche de dependances ne soit pas
# reconstruite a chaque modification du code.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/ui/package.json ./packages/ui/
COPY packages/contracts/package.json ./packages/contracts/

# --frozen-lockfile : l'installation echoue si le verrou ne correspond pas aux
# manifestes, au lieu de le reecrire en silence.
#
# Le postinstall de la racine appelle infra/scripts/exclure-icloud.sh. Le
# script est ecrit en sh POSIX et sort en 0 hors macOS : il n'est donc pas
# necessaire de desactiver les scripts d'installation, ce qui aurait masque
# d'eventuels scripts legitimes plus tard dans le projet.
COPY infra/scripts/exclure-icloud.sh ./infra/scripts/
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile

COPY tsconfig.base.json ./
COPY packages ./packages
COPY apps/web ./apps/web

# node:alpine fournit deja un utilisateur `node` non privilegie (uid 1000).
RUN chown -R node:node /app
USER node

# T2 : le conteneur reste debout pour prouver que l'image se construit et que
# les dependances du workspace sont installees. Le healthcheck, declare dans le
# fichier Compose, verifie que Vite est resolvable — un controle qui echoue si
# l'installation est incomplete.
# T5 remplacera cette commande par le serveur Vite.
CMD ["sleep", "infinity"]
