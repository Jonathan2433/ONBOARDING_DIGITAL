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

# ---------------------------------------------------------------------------
#  T8 — TOUTES LES CIBLES DE STACK SONT PARAMETREES PAR L'ENVIRONNEMENT.
#
#      make up                          le developpement, par defaut
#      make up ENVIRONNEMENT=recette    la recette
#      make up-recette                  alias equivalent, plus court
#
#  POURQUOI PARAMETRER PLUTOT QUE DUPLIQUER. La solution paresseuse aurait ete
#  d'ecrire quinze cibles `*-recette` portant chacune une copie de la recette de
#  son homologue. Deux copies d'une meme logique divergent, et la divergence est
#  silencieuse : c'est le motif de DEC-466 pour le masquage, celui de ECART-022
#  pour les modeles de configuration, et celui que T7 §2.3 a suivi en NE
#  dupliquant pas le Caddyfile. Les seuls alias `*-recette` de ce fichier
#  delèguent — ils ne portent aucune logique propre.
#
#  LE RISQUE DE CE CHOIX EST LA REGRESSION SUR `dev`, et il est nomme. Ces
#  quinze cibles n'avaient jamais tourne que dans un seul etat. C'est exactement
#  la classe des defauts T6-1 et T6-2 : `make env` employait la forme BSD de
#  `sed` et `make up` n'avait jamais fonctionne sur une machine propre, faute
#  d'avoir jamais tourne ailleurs. La parade a ete de RELEVER les codes de sortie
#  des onze controles AVANT la premiere modification, et de les confronter apres.
# ---------------------------------------------------------------------------
ENVIRONNEMENT ?= dev

SURCOUCHE_COMPOSE := $(COMPOSE_DIR)/docker-compose.$(ENVIRONNEMENT).yml

# UN NOM D'ENVIRONNEMENT FAUTIF DOIT ECHOUER TOUT DE SUITE, ET LE DIRE.
# Sans ce garde-fou, `make up ENVIRONNEMENT=recete` passerait a Compose un `-f`
# vers un fichier absent, et l'erreur parlerait d'un chemin, pas d'une faute de
# frappe. Le controle est evalue a la lecture du Makefile, donc avant toute
# action : rien ne peut avoir demarre a moitie.
ifeq ($(wildcard $(SURCOUCHE_COMPOSE)),)
$(error ENVIRONNEMENT=$(ENVIRONNEMENT) inconnu : $(SURCOUCHE_COMPOSE) n'existe pas. \
Environnements disponibles : $(patsubst $(COMPOSE_DIR)/docker-compose.%.yml,%, \
$(filter-out $(COMPOSE_DIR)/docker-compose.base.yml, \
$(wildcard $(COMPOSE_DIR)/docker-compose.*.yml))))
endif

# Le developpement garde `.env` tout court : le suffixe ne serait qu'une gene
# pour l'environnement employe cent fois par jour, et tout le corpus le nomme
# ainsi depuis T2. Les autres environnements prennent `.env.<nom>`, deja couvert
# par `.env.*` dans .gitignore — VERIFIE par `git check-ignore`, non suppose.
ifeq ($(ENVIRONNEMENT),dev)
SUFFIXE_ENV :=
else
SUFFIXE_ENV := .$(ENVIRONNEMENT)
endif
ENV_FILE := $(CURDIR)/.env$(SUFFIXE_ENV)

# Le calque de differences, s'il existe. Le developpement n'en a pas : c'est lui
# que `.env.example` decrit.
CALQUE_ENV := $(wildcard $(COMPOSE_DIR)/differences-$(ENVIRONNEMENT).env)

COMPOSE_FILES_NUS := $(COMPOSE_DIR)/docker-compose.base.yml $(SURCOUCHE_COMPOSE)
COMPOSE_FILES     := -f $(COMPOSE_DIR)/docker-compose.base.yml -f $(SURCOUCHE_COMPOSE)
DC                := docker compose --env-file "$(ENV_FILE)" $(COMPOSE_FILES)

# LE DEVELOPPEMENT CONSTRUIT, LA RECETTE TIRE — ET REFUSE DE CONSTRUIRE.
#
# La surcouche de recette epingle les images publiees par empreinte, mais le
# fichier de base declare aussi `build:` pour les trois services applicatifs.
# Compose accepte les deux ensemble : si l'image tiree manquait, `up`
# CONSTRUIRAIT localement et la recette exercerait un artefact different de
# celui que la production deploiera — en paraissant parfaitement saine. DEC-478
# dit l'inverse : « une recette qui exerce un autre artefact ne recette rien ».
#
# `--no-build` transforme donc ce detournement silencieux en echec bruyant.
ifeq ($(ENVIRONNEMENT),dev)
PREPARER_IMAGES := build
DRAPEAUX_UP     :=
else
PREPARER_IMAGES := pull
DRAPEAUX_UP     := --no-build
endif

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
        web-check caddy-reload caddy-recreate docs-check sources-check sources-temoin \
        audit alembic-check test-frontend docs-temoin \
        images-check images-build images-inspect images-verify images-push \
        images-pin separations-check \
        domaines-provision magic-link-check admin-local admin-check \
        sessions-check sessions-temoin csrf-check \
        up-recette down-recette stack-check-recette recette-check \
        demo-init demo-check demo-info demo-reset

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
	copies=$$(find . \( -name '* [0-9]' -o -name '* [0-9][0-9]' \
		-o -name '* [0-9].*' -o -name '* [0-9][0-9].*' \) \
		-not -path './.git/*' -not -path '*/node_modules/*' \
		-not -path './.venv/*' -not -path '*/__pycache__/*' 2>/dev/null); \
	if [ -n "$$copies" ]; then \
		n=$$(echo "$$copies" | wc -l | tr -d ' '); \
		echo "  COPIE DE CONFLIT iCLOUD detectee — $$n :"; \
		echo "$$copies" | sed 's/^/      /'; \
		echo "      -> iCloud a duplique un fichier ou un repertoire. ROAD-RSK-026."; \
		echo "      -> COMPARE le contenu avant de supprimer : le 23/08/2026 les"; \
		echo "         115 copies etaient identiques a l'octet, mais en T11 iCloud"; \
		echo "         avait mis un contenu ANTERIEUR dans l'original (§7.31)."; \
		manque=1; \
	else \
		echo "  ok       aucune copie de conflit iCloud (toutes profondeurs)"; \
	fi; \
	aveugles=; examines=0; \
	for t in 'node_modules 2' 'modeles 2.py' 'fiche 12.md' 'a 2.cpython-312.pyc'; do \
		examines=$$((examines + 1)); \
		git check-ignore -q "$$t" || aveugles="$$aveugles [$$t]"; \
	done; \
	if [ -n "$$aveugles" ]; then \
		echo "  MOTIF .gitignore AVEUGLE a :$$aveugles"; \
		echo "      -> un nom non ignore entre dans un commit par « git add -A »."; \
		echo "         Le 23/08/2026, « * [0-9] » seul — ecrit contre un REPERTOIRE,"; \
		echo "         donc sans extension — a laisse passer 115 fichiers."; \
		manque=1; \
	else \
		echo "  ok       .gitignore ignore les $$examines formes de copie de conflit"; \
	fi; \
	python3 infra/scripts/verifier-reversion-icloud.py || manque=1; \
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

# Existe a cause de ECART-054 : `docs-check` etait exact pour les six registres et
# AVEUGLE a la passation, si bien que `CLAUDE.md` a annonce `DEC-541` libre alors que
# `DEC-565` etait en usage -- une collision d'identifiant garantie pour qui s'y fierait.
# Le controle a ete etendu ; ce temoin prouve qu'il MORD. Il travaille sur des copies
# en repertoire temporaire et ne touche jamais le depot.
docs-temoin: ## Temoin negatif du controle de documentation et de la passation
	@python3 infra/scripts/temoin-documentation.py

# Existe a cause de T1 du LOT 5 : le module `apps/api/app/media/` a ete ecrit et
# teste, `make check` est sorti en 0, et `git add -A` ne l'a PAS ajoute -- la
# ligne `media/` de .gitignore, ecrite au LOT 0 contre les medias DEPOSES, vaut a
# toute profondeur et attrapait le module du meme nom. Classe §7.34 : un motif
# ecrit contre un exemple ne couvre que cet exemple. Le controle est dans `make
# check` ET NOMME DANS `ci.yml`, et non dans `icloud-verify`, parce que le moment
# ou il faut le savoir est la PULL REQUEST, pas le debut de session.
#
# ATTENTION : `ci.yml` N'INVOQUE PAS `make check`. Il appelle les cibles UNE PAR
# UNE -- trente-huit invocations. Une cible ajoutee a `make check` n'entre donc
# PAS dans l'integration continue. C'est le defaut T1-5 : j'avais mesure sur un
# grep qui matchait `make check` dans un COMMENTAIRE du workflow.
parametres-check: ## Verifier qu'aucun parametre lie ne sert deux types de colonne differents
	@$(UV) run python infra/scripts/verifier-parametres-lies.py

parametres-temoin: ## Temoin du controle des parametres lies — il doit MORDRE et se TAIRE
	@$(UV) run python infra/scripts/verifier-parametres-lies.py --temoin

sources-check: ## Verifier qu'aucun fichier source du disque n'est ignore par git
	@python3 infra/scripts/verifier-sources-suivies.py

sources-temoin: ## Temoin negatif du controle des sources suivies
	@python3 infra/scripts/verifier-sources-suivies.py --temoin

# Controle 10 des onze du cahier 23.1. La tolerance d'un avis nomme est declaree
# dans pnpm-workspace.yaml, avec son motif mesure : voir DEC-474.
audit: ## Auditer les dependances Python (pip-audit) et JavaScript (pnpm audit)
	@echo "==> pip-audit"
	$(UV) run pip-audit --progress-spinner off
	@echo "==> pnpm audit"
	$(PNPM) audit

check: versions tree icloud-verify docs-check sources-check sources-temoin parametres-check parametres-temoin images-check recette-modele-check sessions-temoin cadre-check cadre-temoin format-check lint typecheck test ## Tout verifier
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

# T8 — LE TRAVAIL EST PASSE DU SHELL A PYTHON, et pour trois raisons mesurees.
#
# La version de T2 etait `cp` puis cinq substitutions `sed`. Elle suffisait pour
# UN environnement et une valeur en dur, `MINIO_ROOT_USER=onboarding-dev-admin`.
# T8 doit engendrer un SECOND fichier avec une vingtaine de valeurs differentes,
# et le shell y devient dangereux :
#
#   1. LE DELIMITEUR DE `sed`. La forme employee etait `s|^NOM=.*|NOM=valeur|`.
#      Une valeur contenant `|` casse la substitution ; une valeur contenant `&`
#      est reinjectee par sed comme la chaine appariee. Le calque de recette
#      porte deja une URL.
#   2. LA PORTABILITE. `sed -i ''` de BSD fait echouer GNU sed, qui lit le script
#      comme un nom de fichier — mesure du 29/07/2026, GNU sed 4.9, code 2. C'est
#      le defaut T6-1 : cette cible est appelee par `make up`, donc par
#      l'integration continue sur un executeur Linux, ou la forme BSD cassait
#      TOUTE la tache. Le script Python ne modifie jamais en place.
#   3. UNE SUBSTITUTION SUR UN NOM ABSENT NE FAIT RIEN, EN SILENCE. `sed` sort en
#      0 sans rien changer. Un calque nommant `POSTGRES_DBB` aurait donc laisse la
#      recette partager la base du developpement, et la separation 2 sur 7 aurait
#      ete perdue sans un mot. `composer-env.py` REFUSE de continuer dans ce cas —
#      et il l'a effectivement attrape pendant l'ecriture de T8, sur CADDY_SITE_APP
#      et CADDY_SITE_API, que j'avais mises au calque sans les declarer au modele.
#
# Le chemin de CREATION est desormais eprouve, ce qu'il n'avait jamais ete sur
# cette machine : `.env` existait depuis T2, donc la cible n'y faisait rien.
# Quatre temoins negatifs : idempotence, nom inconnu, doublon, ligne malformee.
env: ## Creer le fichier d'environnement, avec des secrets locaux engendres
	@python3 infra/scripts/composer-env.py \
		--modele .env.example \
		--cible "$(ENV_FILE)" \
		--environnement $(ENVIRONNEMENT) \
		$(if $(CALQUE_ENV),--calque $(CALQUE_ENV),)
	@$(MAKE) --no-print-directory env-check ENVIRONNEMENT=$(ENVIRONNEMENT)

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
# T8 — LE FICHIER EXAMINE SUIT L'ENVIRONNEMENT, et il devait le suivre. Il y a
# desormais deux fichiers d'environnement ; un controle qui n'aurait regarde que
# `.env` aurait laisse `.env.recette` deriver exactement comme ECART-022 l'a
# montre, c'est-a-dire en silence et pendant deux sous-etapes.
env-check: ## Verifier que le fichier d'environnement declare toutes les variables du modele
	@python3 infra/scripts/verifier-images.py environnement --fichier ".env$(SUFFIXE_ENV)"

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
#
# T8 — CET ORDRE EST CONSERVE A L'IDENTIQUE POUR LA RECETTE, et c'est le point.
# Le volume `minio-data` de la recette n'existe pas au premier demarrage : la
# condition qui a fait echouer l'executeur neuf le 29/07/2026 est exactement
# celle du premier `make up-recette`. Eprouve, et pas seulement herite.
up: env ## Demarrer la stack : les 8 services (ENVIRONNEMENT=dev par defaut)
	@echo "==> Images de $(ENVIRONNEMENT) : $(PREPARER_IMAGES)"
	$(DC) $(PREPARER_IMAGES)
	@echo "==> Demarrage des services d'infrastructure"
	$(DC) up --detach --wait $(DRAPEAUX_UP) db redis minio mailpit
	@$(MAKE) --no-print-directory minio-bucket ENVIRONNEMENT=$(ENVIRONNEMENT)
	@$(MAKE) --no-print-directory roles-provision ENVIRONNEMENT=$(ENVIRONNEMENT)
	@echo "==> Demarrage des services applicatifs"
	$(DC) up --detach --wait $(DRAPEAUX_UP)
	@$(MAKE) --no-print-directory caddy-reload ENVIRONNEMENT=$(ENVIRONNEMENT)
	@echo
	@$(MAKE) --no-print-directory health ENVIRONNEMENT=$(ENVIRONNEMENT)
	@$(MAKE) --no-print-directory ports ENVIRONNEMENT=$(ENVIRONNEMENT)

down: ## Arreter la stack. LES VOLUMES SONT CONSERVES
	$(DC) down

# LE NOM DU PROJET EST LU DANS LE FICHIER D'ENVIRONNEMENT, jamais ecrit en dur.
# La version de T2 annoncait « les volumes de onboarding-dev » : sur la recette,
# elle aurait donc demande a Jonathan de confirmer la destruction d'un projet qui
# n'est pas celui qu'elle allait detruire. Un message de confirmation qui nomme le
# mauvais objet est pire qu'une absence de message.
# T9 — CE MESSAGE DIT DESORMAIS LE VRAI, ET IL NE L'A PAS TOUJOURS DIT.
#
# La version de T8 annoncait, quel que soit l'environnement : « Sa perte
# obligera a reapprouver la racine dans le trousseau macOS, ce qui demande le mot
# de passe de Jonathan. » Mesure du 29/07/2026, sur les deux racines :
#
#     dev      empreinte c9a952a9...  security verify-cert -> code 0  APPROUVEE
#     recette  empreinte fb8fbc2d...  security verify-cert -> code 1  non approuvee
#
# L'avertissement etait donc FAUX pour la recette, dont la racine n'a jamais ete
# approuvee. Un avertissement qui annonce une consequence inexistante est pire
# qu'une absence d'avertissement : sur la cible la plus destructive du depot, il
# apprend a l'operateur a passer outre. Et le jour ou il porte sur `dev`, ou la
# consequence est reelle, il ne sera plus lu.
#
# La correction n'est pas de reformuler : c'est de MESURER. La cible extrait la
# racine du conteneur et interroge le trousseau. Quand elle ne peut pas mesurer —
# conteneur arrete, ou `security` absent hors macOS — elle dit qu'elle ne sait
# pas, plutot que d'affirmer l'un ou l'autre.
#
# Elle enumere aussi les volumes REELLEMENT presents, derives du moteur : « y
# compris caddy-data » etait une affirmation de plus, vraie mais non verifiee.
destroy: ## Arreter la stack ET SUPPRIMER LES VOLUMES (destructif)
	@projet=$$(grep -E '^COMPOSE_PROJECT_NAME=' "$(ENV_FILE)" | cut -d= -f2); \
	volumes=$$(docker volume ls --filter "label=com.docker.compose.project=$$projet" \
		--format '{{.Name}}' | sort | tr '\n' ' '); \
	nb=$$(printf '%s' "$$volumes" | wc -w | tr -d ' '); \
	echo "  Cette cible supprime les $$nb volume(s) de donnees de $$projet :"; \
	for v in $$volumes; do echo "      $$v"; done; \
	racine=$$(mktemp); \
	if docker cp "$$projet-caddy-1:/data/caddy/pki/authorities/local/root.crt" "$$racine" \
			>/dev/null 2>&1 && command -v security >/dev/null 2>&1; then \
		if security verify-cert -c "$$racine" >/dev/null 2>&1; then \
			echo "  ATTENTION : l'autorite de certification de CET environnement est"; \
			echo "  APPROUVEE dans le trousseau macOS -- mesure a l'instant. La detruire"; \
			echo "  obligera Jonathan a reapprouver la racine, avec son mot de passe de"; \
			echo "  session. Voir CLAUDE.md 5.6 pour la commande."; \
		else \
			echo "  L'autorite de certification de cet environnement n'est PAS approuvee"; \
			echo "  dans le trousseau -- mesure a l'instant. Sa perte n'a donc aucun cout"; \
			echo "  pour toi : un navigateur avertissait deja sur cet environnement."; \
		fi; \
	else \
		echo "  Etat du trousseau INDETERMINE : le conteneur caddy est arrete, ou"; \
		echo "  l'outil securite du systeme est indisponible. Si cet environnement est"; \
		echo "  celui dont tu as approuve la racine, sa perte te la fera reapprouver."; \
	fi; \
	rm -f "$$racine"; \
	printf "  Taper exactement DETRUIRE pour confirmer : "; \
	read reponse; [ "$$reponse" = "DETRUIRE" ] || { echo "  annule"; exit 1; }
	$(DC) down --volumes

ps: ## Etat des conteneurs
	@$(DC) ps

logs: ## Suivre les journaux de la stack
	@$(DC) logs --follow --tail 80

minio-bucket: ## Creer le bucket MinIO (idempotent, ARB-ROAD-002)
	@bucket=$$(grep -E '^MINIO_BUCKET=' "$(ENV_FILE)" | cut -d= -f2); \
	$(DC) exec -T minio sh -c \
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
	sortie=$$($(DC) exec -T caddy sha256sum /etc/caddy/Caddyfile 2>&1); \
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
	sortie=$$($(DC) exec -T caddy caddy reload --config /etc/caddy/Caddyfile 2>&1); \
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
	$(DC) up --detach --force-recreate --no-deps caddy
	@$(MAKE) --no-print-directory caddy-reload ENVIRONNEMENT=$(ENVIRONNEMENT)

health: ## Verifier que les 8 services sont sains (echoue sinon)
	@manque=0; \
	for s in $(SERVICES); do \
		cid=$$($(DC) ps -q $$s 2>/dev/null); \
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

# DEUX CONTROLES, ET ILS NE MESURENT PAS LA MEME CHOSE.
#
#   verifier-ports.sh        les publications de CET environnement sont-elles
#                            toutes liees a 127.0.0.1, et les declarees
#                            concordent-elles avec les reelles ? (T2, DEC-460)
#
#   verifier-collisions-     deux conteneurs de la MACHINE reclament-ils le meme
#   ports.py                 port d'hote, CONTENEURS ARRETES COMPRIS ?
#
# Le second a ete pose apres la porte G1, et il est ne d'un defaut reel : la
# bande de ports de la recette avait ete choisie apres avoir mesure ce qui
# ECOUTAIT, alors qu'un conteneur ARRETE declare ses ports sans en occuper aucun.
# Le projet tiers `observatoire-ecom-studio` reclamait deja 8080 et n'a pas pu
# demarrer. La mesure etait juste a sa date ; la methode etait incomplete.
ports: ## Verifier les publications de l'environnement ET les collisions de la machine
	@sh infra/scripts/verifier-ports.sh "$(ENV_FILE)" $(COMPOSE_FILES_NUS)
	@python3 infra/scripts/verifier-collisions-ports.py

stack-check: health ports ## Controler la stack : sante des 8 services et publication des ports

# --workdir : alembic.ini reside dans apps/api, et `script_location` y est
# relatif. Lance depuis /app, alembic repond « No 'script_location' key found ».
# LOT 2, T1 : `migrate` RAFRAICHIT puis VERIFIE le code embarque avant d'agir.
#
# `apps/api` n'est PAS monte en bind : le code est cuit dans l'image. Une
# migration ecrite sur l'hote et non reconstruite est INVISIBLE du conteneur, et
# `alembic upgrade head` repond « deja a jour » en sortant en 0. Le defaut s'est
# produit reellement le 18/08/2026 : la migration 0002 existait, `make migrate`
# a rendu `0001 (head)`, succes apparent, rien d'applique.
#
# C'est le meme mecanisme que le defaut T5-2 du LOT 1 -- Caddy servant une
# configuration perimee en etant `healthy` -- et le meme parti que `DEC-472` :
# `make up` appelle `caddy-reload` parce qu'attendre du service qu'il se
# rafraichisse seul ne marche pas.
#
# Le controle APRES le rafraichissement n'est pas redondant : un `build` qui
# n'aurait pas pris produirait exactement la meme observation qu'un `build`
# reussi. C'est la quatrieme proposition du §7.0.
# LE RAFRAICHISSEMENT DU CODE NE VAUT QUE POUR LE DEVELOPPEMENT
#
#   `code-refresh` reconstruit `api` et `worker` pour qu'ils portent le code du
#   depot. C'est juste en developpement, ou l'image est construite localement.
#
#   **EN RECETTE, C'EST UNE ERREUR, ET ELLE EST BRUYANTE.** La surcouche reference
#   ses images **par empreinte** (`DEC-486`), et `docker compose build` refuse :
#   « build tag cannot contain a digest ». Surtout, reconstruire localement
#   DEFERAIT le principe meme de la recette -- elle doit executer l'artefact
#   PUBLIE, ce que `--no-build` garde par ailleurs.
#
#   Le defaut date de `T1` du LOT 2, quand `code-refresh` a ete ajoute a `migrate`
#   alors qu'un seul environnement existait. C'est le §7.21 : un controle juste
#   hier, rendu faux par un environnement que nous avons ajoute nous-memes -- et
#   il n'est apparu qu'en executant reellement la recette, §7.16.
migrate: ## Appliquer les migrations Alembic (rafraichit le code embarque en DEV)
	@if [ "$(ENVIRONNEMENT)" = "dev" ]; then \
		$(MAKE) --no-print-directory code-refresh ENVIRONNEMENT=$(ENVIRONNEMENT); \
		$(MAKE) --no-print-directory code-check ENVIRONNEMENT=$(ENVIRONNEMENT); \
	else \
		echo "==> $(ENVIRONNEMENT) : aucun rafraichissement, l'image est PUBLIEE et epinglee"; \
	fi
	$(DC) exec -T --workdir /app/apps/api api alembic upgrade head
	@$(MAKE) --no-print-directory migrate-status ENVIRONNEMENT=$(ENVIRONNEMENT)
	@$(MAKE) --no-print-directory domaines-provision ENVIRONNEMENT=$(ENVIRONNEMENT)

# `--wait` n'est pas un confort : `up --detach` rend la main des que le conteneur
# est DEMARRE, pas des qu'il est SAIN. Sans l'attente, la CI enchainerait
# `api-check` sur une API en cours de demarrage, et l'echec serait intermittent
# donc penible a attribuer. Un defaut qui ne se produit qu'une fois sur trois
# coute plus cher qu'un defaut franc.
code-refresh: ## Reconstruire et recreer api, worker ET web pour qu'ils portent le code du depot
	@echo "==> Reconstruction de api, worker et web (le code est cuit dans les images)"
	@#  **`web` A ETE AJOUTE EN `T3` DU LOT 4, ET SON ABSENCE A COUTE CHER.**
	@#  Cette cible ne reconstruisait que `api` et `worker`. Le conteneur `web`
	@#  n'est rafraichi que par `make up`, et comme la routine de sous-etape
	@#  emploie `code-refresh`, le frontend servi est reste celui du LOT 1
	@#  pendant TOUT le LOT 3 et les deux premieres sous-etapes du LOT 4 :
	@#  9 fichiers dans le conteneur contre 24 dans le depot, mesure.
	@#  `make ecrans-check` passait quand meme, parce qu'il verifiait que les
	@#  huit chemins rendent `text/html` avec le point de montage -- ce que le
	@#  repli SPA fait pour N'IMPORTE QUEL chemin. §7.0, quatrieme proposition.
	@$(DC) build api worker web
	@$(DC) up --detach --wait --no-deps api worker web

code-check: ## Verifier que le conteneur execute le code du depot, par empreinte
	@python3 infra/scripts/verifier-code-embarque.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

# LOT 2, T9. Deux controles que les sous-etapes precedentes ne portaient pas :
# le COMPTE des relations historisees, derive du modele §25.2 lui-meme, et
# l'absence de colonne nullable dans une cle d'exclusion — defaut `T8-1`.
historisation-check: ## Verifier les 7 relations historisees du modele 25.2
	@python3 infra/scripts/verifier-historisation.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

isolation-check: ## Verifier l isolation inter-entites du modele 2.5 et 25.3
	@python3 infra/scripts/verifier-isolation.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

isolation-temoin: ## Temoin negatif : le controle d isolation sait-il echouer ?
	@python3 infra/scripts/verifier-isolation.py --temoin \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

roles-provision: ## Approvisionner les deux roles du moindre privilege (QO-116, idempotent)
	@python3 infra/scripts/provisionner-roles.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

# APPELEE PAR `make migrate`, ET NON PAR `make up`, et le motif est l'ordre :
# elle ECRIT dans `allowed_email_domain`, donc elle exige une base migree. A
# l'endroit ou `make up` appelle `roles-provision`, aucune migration n'a tourne.
# Un appel qui « sauterait » quand la table manque produirait un succes
# silencieux, ce que le §7.0 interdit.
domaines-provision: ## Poser le domaine e-mail initial du cahier 7.2 (DEC-523, idempotent)
	@python3 infra/scripts/provisionner-domaines.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

# CREE OU DEVERROUILLE. Elle ne touche JAMAIS un mot de passe existant sans
# `--reinitialiser`, et le mot de passe engendre est affiche UNE SEULE FOIS.
# C'est la parade au risque nomme au §7 de la fiche du LOT 3 : « le verrouillage
# administrateur bloque Jonathan lui-meme ».
#   make admin-local ADRESSE=jonathan@exalt-company.com
#   make admin-local ADRESSE=... REINITIALISER=1
admin-local: ## Creer ou deverrouiller un compte administrateur (ADRESSE=... , DEC-527)
	@test -n "$(ADRESSE)" || { \
		echo "  ECHEC : ADRESSE est obligatoire."; \
		echo "          make admin-local ADRESSE=jonathan@exalt-company.com"; \
		exit 1; }
	@$(UV) run python infra/scripts/provisionner-administrateur.py \
		--env-file "$(ENV_FILE)" --adresse "$(ADRESSE)" \
		$(if $(REINITIALISER),--reinitialiser,) $(COMPOSE_FILES_NUS)

secrets-check: ## Verifier qu aucune colonne ne peut porter un secret en clair (10.2, 10.3)
	@python3 infra/scripts/verifier-secrets-en-clair.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

privileges-check: ## Verifier le moindre privilege PostgreSQL (QO-116) — DDL REFUSE au role d execution
	@python3 infra/scripts/verifier-privileges.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

migrations-check: ## Prouver qu une base VIDE se construit uniquement par migrations
	@python3 infra/scripts/verifier-migrations.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

recette-modele-check: ## Classer les 25 controles de recette du modele 30
	@python3 infra/scripts/verifier-recette-modele.py

jeu-de-donnees: ## Ensemencer la base avec le jeu fictif (25 entites, 5000 profils)
	@uv run python infra/scripts/engendrer-jeu-de-donnees.py \
		--env-file "$(ENV_FILE)" $(ARGS)

# ---------------------------------------------------------------------------
#  Demonstration client — exclusivement sur le developpement local.
#
#  Le jeu volumetrique et le decor narratif ont deux responsabilites distinctes :
#  `jeu-de-donnees` fournit la masse et les cas limites ; le second script rend
#  huit profils stables et racontables sans modifier la fabrique de recette.
# ---------------------------------------------------------------------------

demo-init: ## Preparer la demo client complete sur une base locale vide
	@test "$(ENVIRONNEMENT)" = "dev" || { echo "  REFUS    demo-init est reserve a ENVIRONNEMENT=dev"; exit 1; }
	@$(MAKE) --no-print-directory up ENVIRONNEMENT=dev
	@$(MAKE) --no-print-directory migrate ENVIRONNEMENT=dev
	@$(MAKE) --no-print-directory jeu-de-donnees ENVIRONNEMENT=dev
	@$(UV) run python infra/scripts/preparer-demo-client.py enrichir --env-file "$(ENV_FILE)"
	@$(MAKE) --no-print-directory code-refresh ENVIRONNEMENT=dev
	@$(MAKE) --no-print-directory code-check ENVIRONNEMENT=dev | tail -1
	@$(MAKE) --no-print-directory admin-local \
		ADRESSE=demo.client@exemple.test REINITIALISER=1 ENVIRONNEMENT=dev
	@$(MAKE) --no-print-directory demo-check ENVIRONNEMENT=dev
	@$(MAKE) --no-print-directory demo-info ENVIRONNEMENT=dev

demo-check: ## Verifier les personas, le compte et les invariants de la demo
	@test "$(ENVIRONNEMENT)" = "dev" || { echo "  REFUS    demo-check est reserve a ENVIRONNEMENT=dev"; exit 1; }
	@$(UV) run python infra/scripts/preparer-demo-client.py verifier --env-file "$(ENV_FILE)"

demo-info: ## Afficher les adresses et le parcours de la demonstration client
	@test "$(ENVIRONNEMENT)" = "dev" || { echo "  REFUS    demo-info est reserve a ENVIRONNEMENT=dev"; exit 1; }
	@echo
	@echo "  Demonstration client"
	@echo "    connexion      https://$${CADDY_SITE_APP:-app.onboarding.localhost}/connexion/administrateur"
	@echo "    compte         demo.client@exemple.test"
	@echo "    portail        https://$${CADDY_SITE_APP:-app.onboarding.localhost}/"
	@echo "    Bordeaux       https://$${CADDY_SITE_APP:-app.onboarding.localhost}/entites/BORDEA00/trombinoscope"
	@echo "    recherche      Alice, puis alice"
	@echo "    profil vedette Alice Martin"
	@echo
	@echo "  Le mot de passe n'est jamais stocke. La cible demo-init l'affiche et le renouvelle."
	@echo "  Conducteur : docs/demo/guide-presentation-client.md"

demo-reset: ## Vider uniquement les donnees applicatives de la demo locale
	@test "$(ENVIRONNEMENT)" = "dev" || { echo "  REFUS    demo-reset est reserve a ENVIRONNEMENT=dev"; exit 1; }
	@$(UV) run python infra/scripts/preparer-demo-client.py reinitialiser \
		--env-file "$(ENV_FILE)" --confirmation EFFACER-LA-DEMO

migrate-status: ## Afficher la revision appliquee
	@$(DC) exec -T --workdir /app/apps/api api alembic current

# Controle 8 des onze du cahier 23.1, et il verifie autre chose que `migrate` :
# qu'il existe EXACTEMENT UNE tete de migration. Deux tetes signifient une
# chaine divergente — deux branches ayant chacune ajoute une revision sur le
# meme parent. `alembic upgrade head` echouerait alors avec « The script
# directory has multiple heads », mais seulement le jour ou quelqu'un migre.
# Mieux vaut l'apprendre en integration continue.
alembic-check: ## Verifier qu'il existe exactement une tete de migration
	@sortie=$$($(DC) exec -T --workdir /app/apps/api api alembic heads 2>&1); \
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
#
# T9 — L'ORIGINE EST DERIVEE DU FICHIER D'ENVIRONNEMENT, jamais ecrite en dur.
# Elle assemble l'hote servi par Caddy et son port HTTPS publie, et n'ajoute le
# port que s'il n'est pas 443 : une URL en `:443` serait valide mais illisible, et
# une URL sans port ne joindrait pas la recette, publiee sur 8443.
web-check: ## Controler la page de statut telle qu'un navigateur la voit
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	sh infra/scripts/verifier-page-statut.sh "$$origine"

# L'ORIGINE EST DERIVEE DU FICHIER D'ENVIRONNEMENT, comme pour `web-check` :
# l'ecrire en dur ferait porter ce controle sur le developpement alors qu'il
# tournerait sur la recette. C'etait le defaut de `web-check` avant `T9`.
csrf-check: ## Prouver qu une ecriture sans protection est refusee, et l idempotence (US005)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-csrf.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

compte-de-service: ## Creer un compte de service et lui delivrer un jeton (NOM, PROPRIETAIRE, SCOPES)
	@if [ -z "$(NOM)" ] || [ -z "$(PROPRIETAIRE)" ] || [ -z "$(SCOPES)" ]; then \
		echo "  Usage : make compte-de-service NOM=<nom> PROPRIETAIRE=<adresse> SCOPES=<a:b,c:d> [JOURS=90] [ENTITE=<code>]"; \
		echo "  Scopes du cahier 22 : people:read people:import media:process email:send reports:generate"; \
		exit 2; \
	fi
	@$(UV) run python infra/scripts/provisionner-compte-de-service.py \
		--nom "$(NOM)" --proprietaire "$(PROPRIETAIRE)" --scopes "$(SCOPES)" \
		$(if $(JOURS),--jours $(JOURS),) $(if $(ENTITE),--entite $(ENTITE),)

residu-check: ## Lancer la suite d integration et PROUVER qu elle ne laisse rien derriere
	@$(UV) run python infra/scripts/verifier-residu.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

evenements-check: ## Prouver que les 7 evenements du 10.6 sont traces, sans rien de sensible (US008)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-evenements.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

ecrans-check: ## Prouver que les 8 ecrans sont servis, sans couleur hors jetons ni stockage
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-ecrans.py --base "$$origine"

service-check: ## Prouver qu un jeton hors scope est refuse, que l expiration agit, et l audit (US007)
	@$(UV) run python infra/scripts/verifier-comptes-de-service.py \
		--env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

apercu: ## Regarder le portail dans un navigateur : rafraichit le code, pose un decor de demonstration, imprime l'adresse
	@#  **CETTE CIBLE EXISTE PARCE QUE LE FRONTEND SERVI N'EST PAS CELUI DU
	@#  DEPOT TANT QU'ON NE L'A PAS RECONSTRUIT.** Le conteneur `web` n'a AUCUN
	@#  montage : le code est cuit dans l'image. C'est ce qui a fait vivre le
	@#  frontend du LOT 1 pendant un mois -- `ECART-042`.
	@#
	@#  Le decor est FICTIF et porte un marqueur : `make apercu-fin` le retire.
	@$(MAKE) --no-print-directory code-refresh ENVIRONNEMENT=$(ENVIRONNEMENT)
	@$(MAKE) --no-print-directory code-check ENVIRONNEMENT=$(ENVIRONNEMENT) | tail -1
	@python3 infra/scripts/poser-decor-apercu.py --env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

apercu-fin: ## Retirer le decor de demonstration pose par `make apercu`
	@python3 infra/scripts/poser-decor-apercu.py --retirer --env-file "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

cadre-check: ## Prouver le cadre applicatif : jetons resolus, layouts, routes internes (LOT 4, T3)
	@#  STATIQUE : il n'ouvre aucune connexion, il est donc dans `make check`.
	@#  Le debordement REEL exige un moteur de rendu -- LOT 12, Playwright.
	@python3 infra/scripts/verifier-cadre.py

cadre-temoin: ## Eprouver `cadre-check` lui-meme : il DOIT echouer
	@sortie=$$(python3 infra/scripts/verifier-cadre.py --temoin 2>&1) && code=0 || code=$$?; \
	if [ "$$code" = "0" ]; then \
		echo "  ECHEC    le temoin est PASSE : le controle ne discrimine pas"; \
		exit 1; \
	fi; \
	attendus=0; \
	echo "$$sortie" | grep -q 'NON DEFINIE' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'aucune route de mise en page' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q "N'EST PAS chargee" && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'MOT POUR MOT dans le cahier' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q "sa cible n'est PAS focusable" && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'ne coexistent jamais' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'SANS .:focus-visible' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'la carte precede la liste' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'soit DECORATIVE' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'repli(s) fautif(s)' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q "pas une simple NAVIGATION" && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'predicat de visibilite est DUPLIQUE' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'roles sont ECRITS dans le frontend' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'SUCCES est atteignable depuis un' && attendus=$$((attendus + 1)); \
	echo "$$sortie" | grep -q 'NON EMPLOYES par un ecran' && attendus=$$((attendus + 1)); \
	if [ "$$attendus" != "15" ]; then \
		echo "  ECHEC    le temoin echoue, mais pas pour les 15 raisons attendues ($$attendus/15)"; \
		echo "$$sortie" | sed 's/^/           /'; \
		exit 1; \
	fi; \
	echo; \
	echo "  Temoin de \`cadre-check\` — §7.25, un temoin doit NOMMER ce qu'il attend"; \
	echo "    ok       code=$$code, et les QUINZE motifs attendus sont nommes :"; \
	echo "             une propriete non definie par une feuille chargee"; \
	echo "             l'absence de route de mise en page sous CHEMINS.entite"; \
	echo "             la feuille des composants non chargee alors qu'ils sont employes"; \
	echo "             un libelle de rubrique absent du cahier mot pour mot"; \
	echo "             une cible de lien d'evitement non focusable"; \
	echo "             les deux reperes de navigation qui pourraient coexister"; \
	echo "             un element interactif sans regle :focus-visible"; \
	echo "             la carte qui precederait la liste dans le DOM"; \
	echo "             une carte qui ne serait pas decorative"; \
	echo "             un repli qui ne serait pas un \`<details>\`/\`<summary>\`"; \
	echo "             un selecteur d'entite qui porterait de l'ECRITURE"; \
	echo "             un predicat de visibilite duplique dans un composant"; \
	echo "             un role d'administration ecrit en litteral dans le frontend"; \
	echo "             un etat de succes atteignable depuis un \`catch\` (cahier 17.2)"; \
	echo "             un composant exporte qu'aucun ecran n'emploie (critere T11)"; \
	echo; \
	echo "  --> le controle discrimine"

framework-check: ## Prouver la page Framework : trois familles de cartes (LOT 6, US001)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-framework.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

entites-check: ## Prouver que la page nationale ne propose QUE des entites actives (LOT 4, US001)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-entites.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

# LOT 5, T2. Il EXIGE que le conteneur porte le code du depot : lance
# `make code-refresh && make code-check` d'abord, sinon il eprouve un autre
# artefact en paraissant sain (§7.28).
#
# SON CONTROLE LE PLUS UTILE EST UN TEMOIN, PAS UN REFUS. Ma premiere version de
# la route typait `taille` en `Literal[25, 50, 100]` ; un parametre d'URL arrive
# en CHAINE, et Pydantic refuse « 25 » contre un Literal d'entiers. La route
# refusait donc les TROIS tailles valides, et les huit epreuves de refus
# passaient toutes -- elles demandaient un refus et l'obtenaient, pour la
# mauvaise raison. Defaut T2-3.
trombinoscope-check: ## Prouver que le trombinoscope est pagine et ne rend QUE des profils publies (LOT 5, US001)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-trombinoscope.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

# LOT 5, T4. Comme le precedent, il EXIGE que le conteneur porte le code du depot.
#
# SON CONTROLE LE PLUS UTILE RELIE LA FICHE A LA LISTE : il prend l'identifiant
# que le TROMBINOSCOPE rend, verifie que sa fiche est servie, puis prend un
# profil que la liste EXCLUT et verifie que sa fiche est refusee. Sans ce lien,
# une fiche accessible pour un profil masque rendrait le filtre de la liste
# decoratif, et aucun controle de la liste seule ne le verrait.
profil-check: ## Prouver que la fiche ne masque rien, sert la MINIATURE, et qu'un DSM n'ecrit QUE dans son perimetre (LOT 5, US004, US005 et US006)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-profil.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

permissions-check: ## Prouver que le changement d'entite recharge les droits sans en transferer (LOT 4, US002)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-permissions.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

onboarding-check: ## Prouver l'asymetrie DSM/ESM, le cycle de vie complet et ECART-066 sur la pile reelle (LOT 7, T14, US003, US008)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-administration-onboarding.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

accueil-check: ## Prouver la grille a deux visages du DSM, ARB-DROIT-003 et le classement temporel sur la pile reelle (LOT 8, T13, US002, US003, US004)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-accueil-evenements.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

revocation-check: ## Prouver que le depart revoque immediatement, et que la session ne repond plus (US006)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-revocation.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

debit-check: ## Prouver que les limites du 20.2 produisent les resultats attendus (US001, US003)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-debit.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

sessions-check: ## Prouver les trois attributs du cookie et l absence de jeton cote navigateur (US004)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-sessions.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

# LE TEMOIN N'EXIGE AUCUNE STACK : il eprouve le controle des sources dans les
# DEUX sens — un usage reel doit etre vu, un commentaire ne doit pas l'etre.
# Il est donc dans `make check`, la ou la stack n'est pas garantie.
sessions-temoin: ## Temoin : le controle de stockage navigateur sait-il ECHOUER ? (7.25)
	@$(UV) run python infra/scripts/verifier-sessions.py --temoin

admin-check: ## Prouver que le verrouillage administrateur se declenche ET se leve (US003)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	$(UV) run python infra/scripts/verifier-connexion-admin.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

magic-link-check: ## Prouver que la reponse au magic link est IDENTIQUE, connue ou non (US001)
	@hote=$$(grep -E '^CADDY_SITE_APP=' "$(ENV_FILE)" | cut -d= -f2); \
	port=$$(grep -E '^CADDY_HTTPS_HOST_PORT=' "$(ENV_FILE)" | cut -d= -f2); \
	if [ "$$port" = "443" ]; then origine="https://$$hote"; else origine="https://$$hote:$$port"; fi; \
	python3 infra/scripts/verifier-magic-link.py \
		--env-file "$(ENV_FILE)" --base "$$origine" $(COMPOSE_FILES_NUS)

test-unit: ## Tests sans dependance externe
	$(UV) run pytest -m "not integration"

test-integration: ## Tests exigeant la stack REELLE. Echoue si elle est absente
	@$(MAKE) --no-print-directory health ENVIRONNEMENT=$(ENVIRONNEMENT) >/dev/null 2>&1 || { \
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
	@$(DC) down >/dev/null 2>&1
	@echo "==> Redemarrage"
	@$(DC) up --detach --wait >/dev/null 2>&1
	@echo "==> Comparaison"
	@sh infra/scripts/verifier-persistance.sh compare "$(ENV_FILE)" $(COMPOSE_FILES_NUS)

# ---------------------------------------------------------------------------
#  Environnement de recette isole (T8, MVP-L01-US002)
# ---------------------------------------------------------------------------

# LES SEPT SEPARATIONS DU CAHIER 22.2, VERIFIEES SUR L'ETAT REEL.
#
# Ce controle exige que les DEUX environnements soient joignables : il compare
# les projets, les bases, les buckets, les volumes, les secrets, les reseaux et
# les ports. Il ne lit pas les fichiers .env pour conclure — une variable
# declaree n'est pas une base servie.
separations-check: ## Prouver les 7 separations du cahier 22.2 entre dev et recette
	@python3 infra/scripts/verifier-separations.py

# EPINGLER LA RECETTE SUR LA DERNIERE PUBLICATION REUSSIE, SANS COMMIT.
#
# Les empreintes par defaut de `docker-compose.recette.yml` sont celles d'un
# build donne, et elles vieillissent. Cette cible les DERIVE de la source — les
# journaux de la tache `publier` du workflow, qui les tient elle-meme du
# --metadata-file de buildx — et les ecrit dans le fichier d'environnement de la
# recette. Elle n'invente rien et ne transcrit rien de memoire : c'est l'interdit
# de T7-9.
#
# Figer un nouveau pointeur DURABLEMENT reste un commit sur la surcouche, et
# c'est voulu : changer l'artefact que l'on recette est un acte delibere.
images-pin: ## Epingler la recette sur la derniere publication reussie (sans commit)
	@python3 infra/scripts/epingler-images.py --fichier-env ".env.recette"

# ---------------------------------------------------------------------------
#  Alias de commodite. Ils DELEGUENT et ne portent aucune logique propre : une
#  seconde copie d'une recette divergerait de la premiere, en silence.
# ---------------------------------------------------------------------------
up-recette: ## Demarrer la recette (alias de up ENVIRONNEMENT=recette)
	@$(MAKE) --no-print-directory up ENVIRONNEMENT=recette

down-recette: ## Arreter la recette, volumes conserves
	@$(MAKE) --no-print-directory down ENVIRONNEMENT=recette

stack-check-recette: ## Sante et ports de la recette
	@$(MAKE) --no-print-directory stack-check ENVIRONNEMENT=recette

# LE CONTROLE COMPLET DE LA RECETTE, dans l'ordre ou il a du sens : la stack est
# saine, son environnement est coherent avec le modele, puis les sept
# separations sont prouvees contre le developpement.
recette-check: ## Controler la recette de bout en bout, separations comprises
	@$(MAKE) --no-print-directory stack-check ENVIRONNEMENT=recette
	@$(MAKE) --no-print-directory env-check ENVIRONNEMENT=recette
	@$(MAKE) --no-print-directory separations-check

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
