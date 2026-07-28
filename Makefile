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

.PHONY: help tools versions tree icloud-exclude icloud-verify install \
        lint format format-check typecheck test check clean clean-deps

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
	@bash infra/scripts/exclure-icloud.sh

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

check: versions tree icloud-verify format-check lint typecheck test ## Tout verifier
	@echo
	@echo "  Tous les controles sont passes."

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
