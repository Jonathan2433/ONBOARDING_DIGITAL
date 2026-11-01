# syntax=docker/dockerfile:1
#
# Image du frontend React et Vite — DEUX CIBLES NOMMEES.
#
# LOT 1, sous-etape T7, story MVP-L01-US006. Decision DEC-479.
#
#   developpement  serveur de developpement Vite, transformation a la demande,
#                  rechargement a chaud. Selectionnee par la surcouche dev.
#   execution      artefact statique produit par `vite build`, servi par Caddy.
#                  Selectionnee par la surcouche de recette en T8.
#
# POURQUOI DEUX CIBLES, ET NON UNE SEULE
#   ROAD-RSK-031 — la commande de l'image mono-etape etait le serveur de
#   DEVELOPPEMENT Vite, et `docker-compose.base.yml` la fait heriter a TOUTES les
#   surcouches. La recette aurait donc servi un artefact different de celui de la
#   production, ce qui vide la recette de sa valeur.
#
#   ROAD-RSK-030 — l'image mono-etape pesait 1,02 Gio parce qu'elle installait le
#   workspace pnpm COMPLET : ESLint et ses greffons, Prettier, Vitest, jsdom,
#   Testing Library, les types React. Une image d'execution n'en a aucun besoin.
#
# LE PORT 5173 EST CONSERVE PAR LES DEUX CIBLES, ET CE N'EST PAS COSMETIQUE
#   `infra/caddy/Caddyfile` porte `reverse_proxy web:5173`. Faire ecouter
#   l'artefact ailleurs obligerait a un Caddyfile par environnement, donc a
#   dupliquer le mandatement de meme origine de DEC-470 — la decision meme dont
#   depend l'epreuve des cookies Secure et SameSite du LOT 3. Un seul fichier,
#   deux cibles : T8 n'a qu'a choisir la cible.
#
# EPINGLAGE — DEC-443 et cahier des charges 23.3
#   Les deux bases sont referencees par tag de version ET par empreinte sha256.
#   `caddy:2.11-alpine` est DEJA employee par ce projet pour le mandataire
#   inverse : la reutiliser n'ajoute AUCUNE dependance externe, donc aucune
#   entree au registre des dependances.
#
# AUCUNE VARIABLE VITE_ N'EST INJECTEE A LA CONSTRUCTION, ET C'EST MESURE
#   Vite remplace les `import.meta.env.VITE_*` a la construction : une valeur
#   omise deviendrait `undefined` dans l'artefact, en silence. Mesure du
#   29/07/2026 : `apps/web/src` contient **0 occurrence** de `import.meta.env`.
#   `VITE_API_BASE_URL` n'y figure que dans deux commentaires, qui expliquent
#   precisement qu'elle n'a rien a y faire — la page appelle `/health/ready` en
#   relatif (DEC-470). Injecter une variable inutilisee laisserait croire a une
#   configuration qui n'existe pas. Le jour ou le LOT 4 en emploiera une, il
#   faudra ajouter l'ARG ici, et ce commentaire est la pour le dire.

# ============================================================================
#  socle — outillage commun aux deux cibles
# ============================================================================
FROM node:24.16-alpine@sha256:21f403ab171f2dc89bad4dd69d7721bfd15f084ccb46cdd225f31f2bc59b5c9a AS socle

ENV CI=true \
    PNPM_HOME=/pnpm \
    PATH="/pnpm:$PATH"

# pnpm est fourni par corepack, deja present dans l'image node. La version
# exacte est lue dans le champ packageManager de package.json, empreinte
# d'integrite comprise : aucun binaire tiers n'est telecharge a l'aveugle.
#
# /app ET /pnpm sont crees et donnes a `node` AVANT de changer d'utilisateur.
# C'est ce qui permet a l'installation de tourner non privilegiee, donc de se
# passer d'un `chown -R` final.
#
# LE `chown -R` SUPPRIME ICI PESAIT 230 Mio, MESURES.
#   `docker history` du 29/07/2026 sur l'image mono-etape :
#     RUN pnpm install --frozen-lockfile   ->  420 MB
#     RUN chown -R node:node /app          ->  230 MB
#   Un `chown -R` reecrit chaque inode, et une couche d'image enregistre le
#   fichier ENTIER des qu'un seul de ses metadonnees change. La couche
#   DUPLIQUE donc l'arborescence qu'elle ne fait que renommer. C'est 230 Mio
#   qui n'ont jamais rien apporte, et le meme piege existait dans les images
#   api et worker, pour 143 Mio chacune.
RUN corepack enable pnpm \
    && mkdir -p /app /pnpm \
    && chown node:node /app /pnpm

USER node
WORKDIR /app

# Verrou et manifestes d'abord, pour que la couche de dependances ne soit pas
# reconstruite a chaque modification du code.
COPY --chown=node:node package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY --chown=node:node apps/web/package.json ./apps/web/
COPY --chown=node:node packages/ui/package.json ./packages/ui/
COPY --chown=node:node packages/contracts/package.json ./packages/contracts/

# Le postinstall de la racine appelle infra/scripts/exclure-icloud.sh. Le
# script est ecrit en sh POSIX et sort en 0 hors macOS : il n'est donc pas
# necessaire de desactiver les scripts d'installation, ce qui aurait masque
# d'eventuels scripts legitimes plus tard dans le projet.
COPY --chown=node:node infra/scripts/exclure-icloud.sh ./infra/scripts/

# --frozen-lockfile : l'installation echoue si le verrou ne correspond pas aux
# manifestes, au lieu de le reecrire en silence.
#
# uid et gid sur le montage de cache : il est monte root par defaut, et
# l'installation tourne desormais sous `node`.
RUN --mount=type=cache,id=pnpm,target=/pnpm/store,uid=1000,gid=1000 \
    pnpm install --frozen-lockfile

COPY --chown=node:node tsconfig.base.json ./
COPY --chown=node:node packages ./packages
COPY --chown=node:node apps/web ./apps/web

# Vite cherche `vite.config.ts` dans le repertoire courant.
WORKDIR /app/apps/web

# ============================================================================
#  developpement — cible par defaut, comportement inchange depuis T5
# ============================================================================
FROM socle AS developpement

ARG APP_VERSION=0.0.0-dev
ARG APP_REVISION=inconnue

LABEL org.opencontainers.image.title="onboarding-digital/web" \
      org.opencontainers.image.description="Frontend React et Vite - cible de developpement" \
      org.opencontainers.image.source="https://github.com/Jonathan2433/ONBOARDING_DIGITAL" \
      org.opencontainers.image.licenses="UNLICENSED" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${APP_REVISION}"

# Documentaire : le port n'est PAS publie sur l'hote. Seul Caddy joint ce
# service, par le reseau interne (cahier §22.2, DEC-460). Les 7 publications
# de `make ports` restent inchangees.
EXPOSE 5173

# `node ./node_modules/vite/bin/vite.js` et non `pnpm run dev` : cela evite de
# faire dependre le demarrage du conteneur de corepack, qui peut vouloir
# telecharger pnpm a la premiere invocation sous l'utilisateur non privilegie.
# Un point d'entree qui depend du reseau n'est pas un point d'entree.
#
# L'ecoute et le port viennent de `vite.config.ts`, source unique : `host`
# 0.0.0.0 — un serveur lie a la boucle locale du conteneur ne serait joignable
# par personne — `strictPort` pour echouer bruyamment plutot que de glisser sur
# un autre port que Caddy ne mandate pas, et `allowedHosts` sans quoi Vite 8
# refuse l'en-tete `Host: app.onboarding.localhost`.
CMD ["node", "./node_modules/vite/bin/vite.js"]

# ============================================================================
#  constructeur — produit l'artefact statique. N'est jamais execute.
# ============================================================================
FROM socle AS constructeur

# `vite build` et non `pnpm run build` : meme motif que le CMD ci-dessus, et
# l'echec remonte directement.
RUN node ./node_modules/vite/bin/vite.js build

# L'artefact doit exister et ne pas etre vide. Si `vite build` changeait un jour
# de repertoire de sortie, le COPY de la cible d'execution copierait le vide et
# Caddy servirait 404 en paraissant sain : le defaut se verrait a l'execution,
# pas a la construction. Ce controle le ramene ici.
RUN test -s dist/index.html \
    && echo "  artefact : $(find dist -type f | wc -l) fichiers, index.html $(wc -c < dist/index.html) octets"

# ============================================================================
#  execution — l'artefact statique, servi par Caddy. AUCUN outillage.
# ============================================================================
FROM caddy:2.11-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648 AS execution

ARG APP_VERSION=0.0.0-dev
ARG APP_REVISION=inconnue

LABEL org.opencontainers.image.title="onboarding-digital/web" \
      org.opencontainers.image.description="Frontend React et Vite - artefact statique servi par Caddy" \
      org.opencontainers.image.source="https://github.com/Jonathan2433/ONBOARDING_DIGITAL" \
      org.opencontainers.image.licenses="UNLICENSED" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${APP_REVISION}"

# COUCHE APK EPINGLEE — meme classe que `perl-base` dans les images api/worker
# (DEC-581). Trouve en construisant T7 du LOT 11 : `images.yml` bloquait sur
# CRITICAL corrigeable (DEC-482) depuis le 30/10/2026 (cinq executions de
# suite, LOT 11 T1 a T5, jamais remarque car cette porte n'est pas un controle
# requis de PR, §9.4) — `CVE-2026-111497` sur `brotli-libs` 1.2.0-r0 de l'image
# `caddy:2.11-alpine` (Alpine 3.23.5), corrigee dans `1.2.1-r0` et DEJA publiee
# dans le depot `main` de cette version d'Alpine, mesure le 01/11/2026 sur les
# deux architectures avant d'ecrire cette ligne.
RUN apk add --no-cache brotli-libs=1.2.1-r0

# Utilisateur non privilegie. Le cahier 20.1 impose le moindre privilege, et
# l'image caddy officielle tourne root par defaut. Les deux repertoires XDG sont
# crees et donnes a l'utilisateur : Caddy y ecrit son etat, meme sans TLS, et
# refuserait de demarrer sinon.
ENV XDG_DATA_HOME=/var/lib/onboarding \
    XDG_CONFIG_HOME=/etc/onboarding
RUN adduser --disabled-password --gecos "" --uid 10001 onboarding \
    && install -d -o onboarding -g onboarding "$XDG_DATA_HOME" "$XDG_CONFIG_HOME"

COPY apps/web/Caddyfile.execution /etc/caddy/Caddyfile
COPY --from=constructeur /app/apps/web/dist /srv

USER onboarding

# Le meme port que la cible de developpement : `infra/caddy/Caddyfile` mandate
# `web:5173` et n'a pas a savoir quelle cible est en face. 5173 est au-dessus de
# 1024, donc joignable sans privilege.
EXPOSE 5173

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
