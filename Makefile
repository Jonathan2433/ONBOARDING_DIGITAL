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

.PHONY: help tools versions tree icloud-exclude icloud-verify install \
        lint format format-check typecheck test check clean clean-deps \
        env up down destroy ps logs health ports minio-bucket stack-check \
        persistence-test migrate migrate-status test-unit test-integration api-check \
        web-check caddy-reload docs-check audit alembic-check test-frontend

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

check: versions tree icloud-verify docs-check format-check lint typecheck test ## Tout verifier
	@echo
	@echo "  Tous les controles sont passes."

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

up: env ## Demarrer la stack de developpement : les 8 services
	@echo "==> Construction des images api, worker et web"
	$(DC_DEV) build
	@echo "==> Demarrage, avec attente de l'etat sain"
	$(DC_DEV) up --detach --wait
	@$(MAKE) --no-print-directory caddy-reload
	@$(MAKE) --no-print-directory minio-bucket
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
caddy-reload: ## Recharger la configuration de Caddy (idempotent)
	@$(DC_DEV) exec -T caddy caddy reload --config /etc/caddy/Caddyfile 2>/dev/null \
		&& echo "  ok        configuration Caddy rechargee depuis le fichier monte" \
		|| { echo "  ECHEC     rechargement de Caddy : configuration invalide ou service absent"; exit 1; }

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
