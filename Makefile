# ============================================================================
#  eXalt Onboarding Digital - Makefile
#
#  LOT 1, sous-etape T1, story MVP-L01-US001.
#
#  Ce fichier est la « commande documentee » attendue par la roadmap, et il
#  tient le role d'orchestrateur de taches du monorepo : DEC-441 ecarte
#  explicitement Turborepo et Nx. Il deviendra le point d'entree unique de la
#  CI en sous-etape T6.
#
#  Toutes les cibles sont sures a rejouer.
# ============================================================================

# bash, et non le shell interactif de l'utilisateur. En zsh, `$(VARIABLE)`
# n'est PAS decoupee en mots : les boucles `for` ci-dessous ne parcourraient
# qu'un seul element, et les controles afficheraient « conforme » sans avoir
# rien verifie. Ce piege a deja produit un controle menteur sur ce projet.
SHELL := /bin/bash

.DEFAULT_GOAL := help

# uv est installe dans ~/.local/bin, qui n'est pas dans le PATH par defaut
# de cette machine. Homebrew y est inutilisable : /opt/homebrew appartient a
# l'utilisateur `admin`.
export PATH := $(HOME)/.local/bin:$(PATH)

UV   := uv
PNPM := pnpm

# Versions epinglees par DEC-443.
NODE_ATTENDU   := v24.16
PYTHON_ATTENDU := 3.12

# Repertoires exclus de la synchronisation iCloud (DEC-439). Le depot reside
# sous ~/Library/Mobile Documents/ : ces repertoires, eux, ne doivent pas
# etre synchronises.
ICLOUD_EXCLUS := \
	node_modules \
	apps/web/node_modules \
	packages/ui/node_modules \
	packages/contracts/node_modules \
	.venv \
	.ruff_cache \
	.mypy_cache \
	.pytest_cache

# Les sept repertoires imposes par le cahier des charges 15.3.
REPERTOIRES := apps/web apps/api apps/worker packages/ui packages/contracts infra docs

# ---------------------------------------------------------------------------
#  Compose (DEC-444). Le fichier de base ne se lance jamais seul : il est
#  toujours assemble avec une surcouche d'environnement.
#
#  --env-file est donne en chemin absolu : les fichiers -f resident dans
#  infra/compose/, ce qui deplace le repertoire de projet de Compose. Un
#  chemin relatif serait resolu depuis un endroit inattendu.
# ---------------------------------------------------------------------------
#  ATTENTION AUX ESPACES. Le depot reside sous ~/Library/Mobile Documents/ :
#  $(CURDIR) contient une espace. Toute expansion de ENV_FILE doit etre citee,
#  faute de quoi docker compose recoit « /Users/.../Library/Mobile » et
#  repond « couldn't find env file ». Ce piege a deja fait echouer les cibles
#  health et minio-bucket pendant cette sous-etape.
COMPOSE_DIR   := infra/compose
ENV_FILE      := $(CURDIR)/.env
COMPOSE_FILES_NUS := $(COMPOSE_DIR)/docker-compose.base.yml \
                     $(COMPOSE_DIR)/docker-compose.dev.yml
COMPOSE_FILES     := -f $(COMPOSE_DIR)/docker-compose.base.yml \
                     -f $(COMPOSE_DIR)/docker-compose.dev.yml
DC_DEV        := docker compose --env-file "$(ENV_FILE)" $(COMPOSE_FILES)

# Les huit services attendus sains (cahier 15.4).
SERVICES := db redis minio mailpit caddy api worker web

# ---------------------------------------------------------------------------
#  Images multiarchitecture et publication GHCR (T7, DEC-478 a DEC-481)
# ---------------------------------------------------------------------------
#  Depot GHCR impose par DEC-445. Minuscules : GHCR n'accepte pas de majuscule
#  dans un nom de paquet, alors que le compte GitHub s'ecrit `Jonathan2433`.
REGISTRE_IMAGES := ghcr.io/jonathan2433/onboarding-digital

#  Les deux architectures du cahier 22.3, litteralement : « linux/arm64 pour le
#  Mac M5 » et « linux/amd64 pour un futur serveur x86 ».
PLATEFORMES_IMAGES := linux/amd64,linux/arm64

#  LES TROIS IMAGES APPLICATIVES, EN UNE SEULE SOURCE DE VERITE.
#
#  Format : <service>:<cible ou vide>:<plafond en Mio>
#
#  Une liste litterale et non trois familles de variables `CIBLE_x` /
#  `PLAFOND_x` : une variable Make n'est PAS visible du shell d'une recette, et
#  l'indirection `$${CIBLE_$$service}` y aurait valu la chaine vide — donc `web`
#  n'aurait jamais recu `--target execution`, silencieusement. Le contourner
#  demandait `eval`, que la passation §7.2 proscrit pour de bonnes raisons.
#  Un decoupage de chaine dans le shell n'a aucun de ces deux defauts.
#
#  `web` publie sa cible `execution`, jamais la cible de developpement : c'est
#  tout l'objet de DEC-479.
#
#  PLAFONDS DE TAILLE, en Mio, pour la variante PUBLIEE de chaque image.
#  Demandes par ROAD-RSK-030 : « faire echouer la construction si l'image
#  d'execution depasse un plafond declare. Un controle de taille qui n'echoue
#  pas ne sert a rien. »
#
#  QUELLE GRANDEUR EST MESUREE, ET POURQUOI CE N'EST PAS CELLE DE T2 ET T5.
#  Une image a DEUX tailles, et elles diffèrent d'un facteur quatre :
#
#    taille de CONTENU     ce que le registre stocke et transfere. Mesure du
#                          29/07/2026 pour `api` arm64 : 115 Mo.
#    usage DISQUE          l'arborescence depaquetee. Meme image : 473 Mo.
#                          C'est cette grandeur que citent T2 et T5 — 662 Mo
#                          avant T7 — parce que `docker images` la rapporte.
#
#  Les plafonds portent sur la taille de CONTENU, pour deux motifs mesures :
#
#    1. c'est la grandeur que ROAD-RSK-030 visait reellement — « publiee deux
#       fois, telechargee a chaque deploiement, analysee par Trivy » ;
#    2. l'usage disque N'EST PAS COMPARABLE d'une plateforme a l'autre. Mesure :
#       `docker image ls --tree` annonce 473 Mo pour la variante arm64 et 114 Mo
#       pour la variante amd64 de la MEME image — parce que seule la variante
#       native est depaquetee sur cette machine. Un plafond fonde sur cette
#       grandeur passerait ou echouerait selon l'architecture de l'executeur.
#
#  Mesures du 29/07/2026, taille de contenu par plateforme :
#    api 114-115 Mo, worker 114-115 Mo, web execution 22-23 Mo.
#  Marges retenues : ~18 % pour api et worker, un facteur 1,5 pour web, dont la
#  petite taille absolue rend une marge en pourcentage trop serree.
IMAGES_SPEC := api::130 worker::130 web:execution:35

#  Identite du build. En local, les valeurs de .env font foi ; l'integration
#  continue passe la version et l'empreinte du commit reels.
VERSION_IMAGE  ?= 0.0.0-dev
REVISION_IMAGE ?= inconnue

#  Etiquette locale des images multiarchitectures construites par images-build.
#  Elle n'est jamais poussee : c'est la liste de manifestes eprouvee sur cette
#  machine, distincte de celle que publie l'integration continue.
ETIQUETTE_LOCALE := onboarding-local

.PHONY: help tools versions tree icloud-exclude icloud-verify install \
        lint format format-check typecheck test check clean clean-deps \
        env env-check up down destroy ps logs health ports minio-bucket stack-check \
        persistence-test migrate migrate-status test-unit test-integration api-check \
        web-check caddy-reload caddy-recreate docs-check audit alembic-check test-frontend \
        images-check images-build images-inspect images-verify images-push

# ---------------------------------------------------------------------------

help: ## Afficher cette aide
	@echo "eXalt Onboarding Digital - cibles disponibles :"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo

# ---------------------------------------------------------------------------
#  Prerequis et conformite de l'environnement
# ---------------------------------------------------------------------------

tools: ## Verifier que uv, node et pnpm sont disponibles
	@manque=0; \
	for outil in $(UV) node $(PNPM); do \
		if command -v "$$outil" >/dev/null 2>&1; then \
			echo "  ok       $$outil  ($$(command -v $$outil))"; \
		else \
			echo "  ABSENT   $$outil"; manque=1; \
		fi; \
	done; \
	if [ $$manque -ne 0 ]; then \
		echo; \
		echo "  uv   : archive officielle astral-sh/uv, empreinte SHA-256 verifiee,"; \
		echo "         installee dans ~/.local/bin. Homebrew est inutilisable ici."; \
		echo "  pnpm : corepack enable pnpm  (version epinglee par le champ"; \
		echo "         packageManager de package.json)."; \
	fi; \
	exit $$manque

versions: ## Verifier les versions epinglees par DEC-443
	@ecart=0; \
	n=$$(node --version 2>/dev/null); \
	case "$$n" in \
		$(NODE_ATTENDU)*) echo "  ok       node    $$n";; \
		*) echo "  ECART    node    $$n, attendu $(NODE_ATTENDU).x (DEC-443)"; ecart=1;; \
	esac; \
	p=$$($(UV) run python --version 2>/dev/null | awk '{print $$2}'); \
	case "$$p" in \
		$(PYTHON_ATTENDU).*) echo "  ok       python  $$p";; \
		*) echo "  ECART    python  $$p, attendu $(PYTHON_ATTENDU).x (DEC-443)"; ecart=1;; \
	esac; \
	echo "  info     pnpm    $$($(PNPM) --version 2>/dev/null)"; \
	exit $$ecart

tree: ## Verifier la presence des 7 repertoires du cahier 15.3
	@manque=0; \
	for d in $(REPERTOIRES); do \
		if [ -d "$$d" ]; then echo "  ok       $$d"; else echo "  MANQUANT $$d"; manque=1; fi; \
	done; \
	exit $$manque

# ---------------------------------------------------------------------------
#  Atténuations iCloud (DEC-439, DEC-447)
# ---------------------------------------------------------------------------

icloud-exclude: ## Exclure dependances et caches de la synchronisation iCloud
	@sh infra/scripts/exclure-icloud.sh

icloud-verify: ## Verifier que l'exclusion iCloud est bien posee (echoue sinon)
	@manque=0; \
	for d in $(ICLOUD_EXCLUS); do \
		if [ ! -d "$$d" ]; then echo "  absent   $$d"; continue; fi; \
		v=$$(xattr -p 'com.apple.fileprovider.ignore#P' "$$d" 2>/dev/null); \
		if [ "$$v" = "1" ]; then echo "  ok       $$d"; else echo "  NON EXCLU $$d"; manque=1; fi; \
	done; \
	s=$$($(PNPM) store path 2>/dev/null); \
	case "$$s" in \
		*"Mobile Documents"*) echo "  DANS iCLOUD  store pnpm : $$s"; manque=1;; \
		"") echo "  store pnpm introuvable"; manque=1;; \
		*) echo "  ok       store pnpm hors iCloud : $$s";; \
	esac; \
	copies=$$(find . -maxdepth 3 \( -name '* [0-9]' -o -name '* [0-9][0-9]' \) \
		-not -path './.git/*' -not -path './node_modules/*' 2>/dev/null); \
	if [ -n "$$copies" ]; then \
		echo "  COPIE DE CONFLIT iCLOUD detectee :"; \
		echo "$$copies" | sed 's/^/      /'; \
		echo "      -> iCloud a duplique un repertoire. Voir ROAD-RSK-026."; \
		manque=1; \
	else \
		echo "  ok       aucune copie de conflit iCloud"; \
	fi; \
	exit $$manque

# ---------------------------------------------------------------------------
#  Installation
# ---------------------------------------------------------------------------

install: icloud-exclude ## Installer les dependances Python et JavaScript
	$(UV) sync
	$(PNPM) install
	@$(MAKE) --no-print-directory icloud-exclude
	@$(MAKE) --no-print-directory icloud-verify

# ---------------------------------------------------------------------------
#  Chaine de qualite
# ---------------------------------------------------------------------------

lint: ## Lint Python (Ruff) et JavaScript/TypeScript (ESLint)
	@echo "==> Ruff"
	$(UV) run ruff check .
	@echo "==> ESLint"
	$(PNPM) run lint

format: ## Reformater le code (Ruff et Prettier)
	$(UV) run ruff format .
	$(PNPM) run format

format-check: ## Verifier le formatage sans rien modifier
	@echo "==> Ruff format"
	$(UV) run ruff format --check .
	@echo "==> Prettier"
	$(PNPM) run format:check

typecheck: ## Verifier les types (mypy strict, tsc --noEmit)
	@echo "==> mypy (strict, DEC-442)"
	$(UV) run mypy
	@echo "==> tsc --noEmit (TypeScript strict)"
	$(PNPM) run typecheck

test: ## Executer les tests (pytest et Vitest)
	@echo "==> pytest"
	$(UV) run pytest
	@echo "==> Vitest"
	$(PNPM) run test

# Controle 7 des onze du cahier 23.1, « tests frontend ». Cible distincte parce
# que l'integration continue l'execute SANS la stack Docker, alors que `make
# test` lance aussi les 8 tests d'integration, qui exigent des services reels.
test-frontend: ## Tests frontend seuls (Vitest, sans dependance externe)
	$(PNPM) run test

# Rend effectives les deux recommandations du lot : ROAD-RSK-029, un formateur
# peut reecrire les documents immuables sans qu'aucun controle ne le signale, et
# ECART-021, quatre nombres du corpus n'etaient pas derives de leur source.
docs-check: ## Verifier l'integrite des documents immuables et les sequences d'identifiants
	@python3 infra/scripts/verifier-documentation.py

# Controle 10 des onze du cahier 23.1. La tolerance d'un avis nomme est declaree
# dans pnpm-workspace.yaml, avec son motif mesure : voir DEC-474.
audit: ## Auditer les dependances Python (pip-audit) et JavaScript (pnpm audit)
	@echo "==> pip-audit"
	$(UV) run pip-audit --progress-spinner off
	@echo "==> pnpm audit"
	$(PNPM) audit

check: versions tree icloud-verify docs-check images-check format-check lint typecheck test ## Tout verifier
	@echo
	@echo "  Tous les controles sont passes."

# ---------------------------------------------------------------------------
#  Images multiarchitecture et publication GHCR — T7, story MVP-L01-US006
#
#  LE MAKEFILE RESTE LE POINT D'ENTREE UNIQUE, y compris pour la publication.
#  Aucune commande buildx n'est ecrite en dur dans le workflow : ce que
#  l'integration continue execute, Jonathan peut le rejouer a l'identique ici.
#  C'est ce que T1 annoncait et ce que T6 a tenu.
# ---------------------------------------------------------------------------

# Controles STATIQUES : aucun demon Docker requis, donc executables dans la
# tache « qualite » de la CI, qui ne demarre aucun service. Inclus dans
# `make check`.
images-check: ## Controles statiques des images : epinglage, etiquettes, cibles
	@python3 infra/scripts/verifier-images.py statique

# Construction LOCALE des trois images pour les deux architectures, chargees dans
# le magasin local, puis controlees.
#
# `--load` avec deux plateformes exige le magasin d'images containerd. Verifie le
# 29/07/2026 sur cette machine : le snapshotter est `io.containerd.snapshotter.v1`
# et la liste de manifestes est bien produite. Sans lui, buildx refuserait.
#
# La construction `linux/amd64` sur ce Mac `arm64` passe par l'emulation, donc
# elle est LENTE. C'est le prix de la preuve locale, et la duree est mesuree.
images-build: ## Construire les 3 images en multiarchitecture, en local, et les controler
	@rep="$${TMPDIR:-/tmp}/onboarding-images-t7"; mkdir -p "$$rep"; \
	construites=0; attendues=0; \
	for spec in $(IMAGES_SPEC); do \
		attendues=$$((attendues + 1)); \
		service=$${spec%%:*}; reste=$${spec#*:}; cible=$${reste%%:*}; \
		echo; \
		echo "==> $$service — plateformes $(PLATEFORMES_IMAGES)$${cible:+, cible $$cible}"; \
		debut=$$(date +%s); \
		docker buildx build \
			--platform $(PLATEFORMES_IMAGES) \
			$${cible:+--target} $$cible \
			--build-arg APP_VERSION=$(VERSION_IMAGE) \
			--build-arg APP_REVISION=$(REVISION_IMAGE) \
			--metadata-file "$$rep/$$service.json" \
			--load \
			-t $(ETIQUETTE_LOCALE)/$$service:multiarch \
			-f apps/$$service/Dockerfile . ; \
		code=$$?; \
		if [ $$code -ne 0 ]; then echo "  ECHEC construction de $$service, code $$code"; continue; fi; \
		construites=$$((construites + 1)); \
		echo "  duree de construction : $$(( $$(date +%s) - debut )) s"; \
	done; \
	echo; \
	echo "  images attendues : $$attendues   construites : $$construites"; \
	if [ "$$construites" -ne "$$attendues" ]; then exit 1; fi
	@$(MAKE) --no-print-directory images-inspect

# Manifeste et taille de chaque image construite. Separee de `images-build` pour
# etre rejouable sans reconstruire.
images-inspect: ## Controler manifestes et tailles des images locales multiarchitecture
	@rep="$${TMPDIR:-/tmp}/onboarding-images-t7"; echec=0; examinees=0; attendues=0; \
	for spec in $(IMAGES_SPEC); do \
		attendues=$$((attendues + 1)); \
		service=$${spec%%:*}; reste=$${spec#*:}; plafond=$${reste##*:}; \
		python3 infra/scripts/verifier-images.py manifeste \
			$(ETIQUETTE_LOCALE)/$$service:multiarch --metadonnees "$$rep/$$service.json" || echec=1; \
		python3 infra/scripts/verifier-images.py taille \
			$(ETIQUETTE_LOCALE)/$$service:multiarch $$service $$plafond || echec=1; \
		examinees=$$((examinees + 1)); \
	done; \
	echo; \
	echo "  images attendues : $$attendues   examinees : $$examinees"; \
	if [ "$$examinees" -ne "$$attendues" ]; then exit 1; fi; \
	exit $$echec

# Controle FONCTIONNEL : les conteneurs sont LANCES, sur les deux architectures.
# Le critere de la fiche §3 dit « fonctionne », pas « est construite » : une image
# amd64 qui se construit mais ne demarre pas ne satisfait rien.
#
# Le temoin de la cible de DEVELOPPEMENT est indispensable : il prouve que le
# detecteur de `/@vite/client` sait trouver le motif. Sans lui, « 0 occurrence »
# serait indistinguable d'une expression reguliere fausse — defaut T5-7.
images-verify: ## Lancer les 3 images sur les 2 architectures et prouver qu'elles fonctionnent
	@echec=0; examinees=0; attendues=0; \
	for spec in $(IMAGES_SPEC); do \
		attendues=$$((attendues + 1)); \
		service=$${spec%%:*}; reste=$${spec#*:}; cible=$${reste%%:*}; \
		python3 infra/scripts/verifier-images.py fonctionnel \
			$$service $(ETIQUETTE_LOCALE)/$$service:multiarch \
			--version "$(VERSION_IMAGE)" --revision "$(REVISION_IMAGE)" \
			$${cible:+--cible} $$cible || echec=1; \
		examinees=$$((examinees + 1)); \
	done; \
	echo; \
	echo "==> TEMOIN POSITIF : la cible de DEVELOPPEMENT doit, elle, porter /@vite/client"; \
	python3 infra/scripts/verifier-images.py fonctionnel \
		web onboarding-dev-web:latest --cible developpement \
		--plateforme linux/arm64 || echec=1; \
	echo; \
	echo "  services attendus : $$attendues   examines : $$examinees"; \
	if [ "$$examinees" -ne "$$attendues" ]; then exit 1; fi; \
	exit $$echec

# Publication dans GHCR. Appelee par le workflow images.yml, jamais a la main :
# elle exige une authentification au registre, que le GITHUB_TOKEN du workflow
# fournit (`packages: write`). Aucun secret de depot n'est necessaire.
#
# ETIQUETTES est fourni par l'appelant, separe par des espaces. `latest` n'y
# figure jamais : arbitrage de Jonathan, plus strict que les conventions §4.1.
# `images-check` echoue si le mot apparait dans un workflow.
images-push: ## Publier les 3 images multiarchitecture dans GHCR (CI, ETIQUETTES=...)
	@test -n "$(ETIQUETTES)" || { echo "  ECHEC : ETIQUETTES est vide"; exit 1; }
	@rep="$${TMPDIR:-/tmp}/onboarding-images-t7"; mkdir -p "$$rep"; \
	: > "$$rep/empreintes.txt"; \
	publiees=0; attendues=0; \
	for spec in $(IMAGES_SPEC); do \
		attendues=$$((attendues + 1)); \
		service=$${spec%%:*}; reste=$${spec#*:}; cible=$${reste%%:*}; \
		args=""; \
		for etiquette in $(ETIQUETTES); do \
			args="$$args -t $(REGISTRE_IMAGES)/$$service:$$etiquette"; \
		done; \
		echo; \
		echo "==> publication de $$service, etiquettes : $(ETIQUETTES)"; \
		debut=$$(date +%s); \
		docker buildx build \
			--platform $(PLATEFORMES_IMAGES) \
			$${cible:+--target} $$cible \
			--build-arg APP_VERSION=$(VERSION_IMAGE) \
			--build-arg APP_REVISION=$(REVISION_IMAGE) \
			--metadata-file "$$rep/$$service-publie.json" \
			--push $$args \
			-f apps/$$service/Dockerfile . ; \
		code=$$?; \
		if [ $$code -ne 0 ]; then echo "  ECHEC publication de $$service, code $$code"; continue; fi; \
		publiees=$$((publiees + 1)); \
		echo "  duree : $$(( $$(date +%s) - debut )) s"; \
		empreinte=$$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['containerimage.digest'])" "$$rep/$$service-publie.json"); \
		echo "  empreinte de la liste de manifestes : $$empreinte"; \
		printf '%s %s\n' "$$service" "$$empreinte" >> "$$rep/empreintes.txt"; \
	done; \
	echo; \
	echo "  images attendues : $$attendues   publiees : $$publiees"; \
	if [ "$$publiees" -ne "$$attendues" ]; then exit 1; fi

# ---------------------------------------------------------------------------
#  Stack Docker locale (T2)
# ---------------------------------------------------------------------------

# `sed` PORTABLE, et ce n'est pas un detail de style. La forme BSD `sed -i ''`
# de macOS fait echouer GNU sed, qui lit le script comme un nom de fichier :
# mesure du 29/07/2026 sur GNU sed 4.9, « can't read s|^APP_SECRET_KEY... »,
# code 2. Cette cible est appelee par `make up`, donc par l'integration
# continue sur un executeur Linux : la forme BSD y cassait toute la tache.
# Le fichier temporaire est couvert par `.env.*` dans .gitignore.
env: ## Creer .env depuis .env.example, avec des secrets locaux generes
	@if [ -f "$(ENV_FILE)" ]; then \
		echo "  $(ENV_FILE) existe deja : inchange"; \
	else \
		cp .env.example "$(ENV_FILE)"; \
		for v in APP_SECRET_KEY POSTGRES_PASSWORD REDIS_PASSWORD MINIO_ROOT_PASSWORD; do \
			s=$$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 48); \
			sed "s|^$$v=CHANGE_ME.*|$$v=$$s|" "$(ENV_FILE)" > "$(ENV_FILE).tmp" \
				&& mv "$(ENV_FILE).tmp" "$(ENV_FILE)"; \
		done; \
		sed "s|^MINIO_ROOT_USER=CHANGE_ME.*|MINIO_ROOT_USER=onboarding-dev-admin|" "$(ENV_FILE)" > "$(ENV_FILE).tmp" \
			&& mv "$(ENV_FILE).tmp" "$(ENV_FILE)"; \
		echo "  $(ENV_FILE) cree depuis .env.example"; \
		echo "  4 secrets engendres aleatoirement sur 48 caracteres, et un"; \
		echo "  MINIO_ROOT_USER lisible : cinq variables renseignees en tout"; \
		echo "  .env n'est PAS versionne : .gitignore le refuse (verifie)"; \
		echo; \
		echo "  RESTENT volontairement en CHANGE_ME, et ce n'est pas un oubli :"; \
		echo "    IMPORT_SOURCE_RETENTION_DAYS  -> sa valeur releve de QO-100, bloquante"; \
		echo "    UPTIME_KUMA_PUSH_URL          -> supervision externe, LOT 13"; \
	fi
	@$(MAKE) --no-print-directory env-check

# T7, ECART-022 — LA PARADE A UN DEFAUT QUE `make env` NE PEUT PAS CORRIGER.
#
# `make env` est idempotent : si .env existe, il n'y touche pas. C'est voulu, le
# fichier porte des secrets locaux engendres. Mais la consequence l'etait moins :
# une variable ajoutee a .env.example APRES la premiere creation du .env n'y
# arrive JAMAIS.
#
# Mesure du 29/07/2026 : le .env de cette machine comptait 74 affectations contre
# 78 dans le modele. Manquaient APP_REVISION, ajoutee en T3, et LOG_MAX_SIZE et
# LOG_MAX_FILES, ajoutees en T4 — trois variables absentes depuis deux et une
# sous-etapes.
#
# EFFETS REELS, MESURES ET DIFFERENTS L'UN DE L'AUTRE :
#   - Compose substituait une chaine VIDE a $${APP_REVISION}, faute de defaut ;
#   - LOG_MAX_SIZE et LOG_MAX_FILES ont un defaut dans Compose : la rotation de
#     T4 fonctionnait donc par le DEFAUT, pas par .env. Ce qui est correct, mais
#     n'est pas ce que le compte rendu de T4 laissait entendre.
#
# Ce controle compte les deux fichiers et NOMME les manquantes. Il ne modifie
# rien : ajouter automatiquement des lignes a un fichier de secrets serait pire
# que le defaut.
env-check: ## Verifier que .env declare toutes les variables de .env.example
	@python3 infra/scripts/verifier-images.py environnement

# DEMARRAGE EN DEUX TEMPS, et l'ordre n'est pas cosmetique.
#
# La sonde `ready` de l'API fait un `head_bucket` sur le bucket MinIO. Tant que
# le bucket n'existe pas, elle repond 503, donc le conteneur `api` n'est jamais
# `healthy`, donc `up --wait` echoue sur « dependency failed to start ».
#
# Ce defaut n'a jamais paru en local : le volume `minio-data` survit a
# `make down`, et le bucket y etait donc deja. Il s'est montre au PREMIER
# demarrage sur une machine neuve — l'executeur d'integration continue, le
# 29/07/2026 — et il aurait fait echouer le critere de T9, « les procedures
# fonctionnent depuis une machine propre ». Reproduit localement en supprimant
# le seul volume minio : `minio indisponible, motif=RuntimeError`.
#
# Le bucket est donc cree APRES que MinIO soit sain, mais AVANT que l'API ne
# doive l'etre.
up: env ## Demarrer la stack de developpement : les 8 services
	@echo "==> Construction des images api, worker et web"
	$(DC_DEV) build
	@echo "==> Demarrage des services d'infrastructure"
	$(DC_DEV) up --detach --wait db redis minio mailpit
	@$(MAKE) --no-print-directory minio-bucket
	@echo "==> Demarrage des services applicatifs"
	$(DC_DEV) up --detach --wait
	@$(MAKE) --no-print-directory caddy-reload
	@echo
	@$(MAKE) --no-print-directory health
	@$(MAKE) --no-print-directory ports

down: ## Arreter la stack. LES VOLUMES SONT CONSERVES
	$(DC_DEV) down

destroy: ## Arreter la stack ET SUPPRIMER LES VOLUMES (destructif)
	@echo "  Cette cible supprime les volumes de donnees de onboarding-dev,"
	@echo "  y compris caddy-data, qui porte l'autorite de certification interne."
	@echo "  Sa perte obligera a reapprouver la racine dans le trousseau macOS,"
	@echo "  ce qui demande le mot de passe de Jonathan."
	@printf "  Taper exactement DETRUIRE pour confirmer : "
	@read reponse; [ "$$reponse" = "DETRUIRE" ] || { echo "  annule"; exit 1; }
	$(DC_DEV) down --volumes

ps: ## Etat des conteneurs
	@$(DC_DEV) ps

logs: ## Suivre les journaux de la stack
	@$(DC_DEV) logs --follow --tail 80

minio-bucket: ## Creer le bucket MinIO (idempotent, ARB-ROAD-002)
	@bucket=$$(grep -E '^MINIO_BUCKET=' "$(ENV_FILE)" | cut -d= -f2); \
	$(DC_DEV) exec -T minio sh -c \
		"mc alias set local http://127.0.0.1:9000 \"\$$MINIO_ROOT_USER\" \"\$$MINIO_ROOT_PASSWORD\" >/dev/null \
		 && mc mb --ignore-existing local/$$bucket >/dev/null \
		 && mc stat local/$$bucket >/dev/null" \
		&& echo "  ok        bucket MinIO $$bucket present" \
		|| { echo "  ECHEC     bucket MinIO $$bucket"; exit 1; }
	@# `mc stat` et non `mc ls | grep` : l'image MinIO ne fournit pas grep.
	@# stat sort en erreur si le bucket est absent, ce qui rend le controle
	@# capable d'echouer reellement.

# Caddy NE SURVEILLE PAS son fichier de configuration, et Compose ne recree pas
# le conteneur quand seul le CONTENU du fichier monte change. Sans ce
# rechargement, une modification du Caddyfile reste sans effet et la stack sert
# une configuration perimee en paraissant parfaitement saine — defaut trouve en
# T5. `caddy reload` est idempotent : il ne fait rien si rien n'a change.
#
# T7 — DEUX CORRECTIONS, apres un echec reel le 29/07/2026.
#
# 1. L'ERREUR N'EST PLUS MASQUEE. La version de T5 ecrivait `2>/dev/null` et
#    concluait « configuration invalide ou service absent ». Le message reel
#    etait « open /etc/caddy/Caddyfile: no such file or directory », soit une
#    cause entierement differente. C'est le piege de la passation §7.6 : ne
#    jamais supprimer l'erreur d'un controle dont on va interpreter le silence.
#
# 2. LE CONTROLE COMPARE DESORMAIS CE QUE LE CONTENEUR VOIT A CE QUE L'HOTE
#    PORTE. Motif mesure : le conteneur caddy, cree a 09:51:38, voyait un
#    /etc/caddy VIDE alors que l'hote portait bien le fichier. Les inodes de
#    `infra/caddy` et de son Caddyfile avaient change a 10:06:49, sans aucune
#    action de session — la signature de ROAD-RSK-026. Monter le REPERTOIRE
#    (DEC-472) protege du remplacement du FICHIER par un editeur ; cela ne
#    protege pas du remplacement du REPERTOIRE par iCloud, car un conteneur ne
#    re-resout pas la source d'un montage apres sa creation. Et pendant ce
#    temps, Caddy restait `healthy` : son API d'administration repondait sur la
#    configuration chargee au demarrage.
caddy-reload: ## Recharger la configuration de Caddy (idempotent, et compare hote/conteneur)
	@empreinte_hote=$$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" infra/caddy/Caddyfile); \
	sortie=$$($(DC_DEV) exec -T caddy sha256sum /etc/caddy/Caddyfile 2>&1); \
	code=$$?; \
	if [ $$code -ne 0 ]; then \
		echo "  ECHEC     le conteneur caddy ne voit PAS /etc/caddy/Caddyfile"; \
		printf '%s\n' "$$sortie" | sed 's/^/              /'; \
		echo "              Cause la plus probable : le conteneur est epingle a un inode"; \
		echo "              de repertoire perime. iCloud remplace les inodes sans action"; \
		echo "              de session (ROAD-RSK-026), et un conteneur ne re-resout pas"; \
		echo "              la source d'un montage lie apres sa creation."; \
		echo "              Remede :  make caddy-recreate"; \
		exit 1; \
	fi; \
	empreinte_conteneur=$$(printf '%s' "$$sortie" | cut -d' ' -f1); \
	if [ "$$empreinte_hote" != "$$empreinte_conteneur" ]; then \
		echo "  ECHEC     le conteneur voit un Caddyfile DIFFERENT de celui de l'hote"; \
		echo "              hote      $$empreinte_hote"; \
		echo "              conteneur $$empreinte_conteneur"; \
		echo "              Remede :  make caddy-recreate"; \
		exit 1; \
	fi; \
	echo "  ok        le conteneur voit le MEME Caddyfile que l'hote ($$(printf '%s' "$$empreinte_hote" | cut -c1-16)...)"; \
	sortie=$$($(DC_DEV) exec -T caddy caddy reload --config /etc/caddy/Caddyfile 2>&1); \
	code=$$?; \
	if [ $$code -ne 0 ]; then \
		echo "  ECHEC     rechargement de Caddy, code $$code :"; \
		printf '%s\n' "$$sortie" | sed 's/^/              /'; \
		exit 1; \
	fi; \
	echo "  ok        configuration Caddy rechargee depuis le fichier monte"

# Remede au defaut ci-dessus. Recreer le conteneur lui fait RE-RESOUDRE la
# source de son montage lie : c'est le seul geste qui repare un inode perime.
# --no-deps : ne touche pas aux sept autres services, qui n'ont rien a se voir
# redemarrer pour un probleme de montage propre a Caddy.
caddy-recreate: ## Recreer le conteneur Caddy (repare un montage lie perime)
	$(DC_DEV) up --detach --force-recreate --no-deps caddy
	@$(MAKE) --no-print-directory caddy-reload

health: ## Verifier que les 8 services sont sains (echoue sinon)
	@manque=0; \
	for s in $(SERVICES); do \
		cid=$$($(DC_DEV) ps -q $$s 2>/dev/null); \
		if [ -z "$$cid" ]; then echo "  ABSENT    $$s"; manque=1; continue; fi; \
		etat=$$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}sans-healthcheck{{end}}' "$$cid"); \
		if [ "$$etat" = "healthy" ]; then \
			echo "  sain      $$s"; \
		else \
			echo "  PAS SAIN  $$s ($$etat)"; manque=1; \
		fi; \
	done; \
	if [ $$manque -eq 0 ]; then echo "  --> les 8 services sont sains"; fi; \
	exit $$manque

ports: ## Verifier qu'aucun service n'ecoute ailleurs que sur la boucle locale
	@sh infra/scripts/verifier-ports.sh "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

stack-check: health ports ## Controler la stack : sante des 8 services et publication des ports

# --workdir : alembic.ini reside dans apps/api, et `script_location` y est
# relatif. Lance depuis /app, alembic repond « No 'script_location' key found ».
migrate: ## Appliquer les migrations Alembic sur la base de developpement
	$(DC_DEV) exec -T --workdir /app/apps/api api alembic upgrade head
	@$(MAKE) --no-print-directory migrate-status

migrate-status: ## Afficher la revision appliquee
	@$(DC_DEV) exec -T --workdir /app/apps/api api alembic current

# Controle 8 des onze du cahier 23.1, et il verifie autre chose que `migrate` :
# qu'il existe EXACTEMENT UNE tete de migration. Deux tetes signifient une
# chaine divergente — deux branches ayant chacune ajoute une revision sur le
# meme parent. `alembic upgrade head` echouerait alors avec « The script
# directory has multiple heads », mais seulement le jour ou quelqu'un migre.
# Mieux vaut l'apprendre en integration continue.
alembic-check: ## Verifier qu'il existe exactement une tete de migration
	@sortie=$$($(DC_DEV) exec -T --workdir /app/apps/api api alembic heads 2>&1); \
	code=$$?; \
	if [ $$code -ne 0 ]; then \
		echo "  ECHEC     alembic heads a echoue :"; echo "$$sortie"; exit 1; \
	fi; \
	n=$$(printf '%s\n' "$$sortie" | grep -c '(head)'); \
	printf '%s\n' "$$sortie" | sed 's/^/    /'; \
	echo "  tetes attendues : 1   trouvees : $$n"; \
	if [ "$$n" -ne 1 ]; then \
		echo "  ECHEC     chaine de migration divergente ou vide"; exit 1; \
	fi; \
	echo "  --> une seule tete de migration, la chaine est lineaire"

api-check: ## Interroger les trois endpoints de sante et lire leurs codes
	@sh infra/scripts/verifier-sante.sh "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

# Ce controle passe par Caddy en HTTPS, depuis l'hote : c'est le chemin d'un
# navigateur, et le seul qui eprouve le mandatement de meme origine (DEC-470).
web-check: ## Controler la page de statut telle qu'un navigateur la voit
	@sh infra/scripts/verifier-page-statut.sh

test-unit: ## Tests sans dependance externe
	$(UV) run pytest -m "not integration"

test-integration: ## Tests exigeant la stack REELLE. Echoue si elle est absente
	@$(MAKE) --no-print-directory health >/dev/null 2>&1 || { \
		echo "  ECHEC : la stack n'est pas saine. Lancer make up."; \
		echo "          Ces tests ne doivent PAS etre ignores en silence :"; \
		echo "          un test ignore n'est pas un test qui passe."; \
		exit 1; }
	$(UV) run pytest -m integration
	@# Un test ignore ne prouve rien : on verifie qu'il en a bien execute.
	@n=$$($(UV) run pytest -m integration -q 2>/dev/null | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+'); \
	if [ -z "$$n" ] || [ "$$n" -eq 0 ]; then \
		echo "  ECHEC : aucun test d'integration execute, le controle ne prouve rien"; exit 1; \
	else echo "  $$n tests d'integration reellement executes"; fi

persistence-test: ## Prouver que les volumes survivent a un arret/redemarrage
	@echo "==> Releve des empreintes avant arret"
	@sh infra/scripts/verifier-persistance.sh capture "$(ENV_FILE)" $(COMPOSE_FILES_NUS)
	@echo "==> Arret, volumes conserves"
	@$(DC_DEV) down >/dev/null 2>&1
	@echo "==> Redemarrage"
	@$(DC_DEV) up --detach --wait >/dev/null 2>&1
	@echo "==> Comparaison"
	@sh infra/scripts/verifier-persistance.sh compare "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

# ---------------------------------------------------------------------------
#  Nettoyage
# ---------------------------------------------------------------------------

clean: ## Supprimer les caches et artefacts de construction
	rm -rf .ruff_cache .mypy_cache .pytest_cache
	rm -rf apps/web/dist packages/ui/dist packages/contracts/dist coverage
	find . -name '__pycache__' -type d -prune -not -path './.git/*' -exec rm -rf {} +
	@$(MAKE) --no-print-directory icloud-exclude

clean-deps: clean ## Supprimer aussi les dependances installees (reinstallation requise)
	rm -rf $(ICLOUD_EXCLUS)
	@$(MAKE) --no-print-directory icloud-exclude
