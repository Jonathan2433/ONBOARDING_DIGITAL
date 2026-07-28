# eXalt Onboarding Digital

Plateforme interne de découverte de l'organisation eXalt et d'onboarding des nouveaux
arrivants. Multi-entités dès le MVP, contenu initial pour Bordeaux.

- **Dépôt :** privé — `Jonathan2433/ONBOARDING_DIGITAL`
- **Décideurs :** Léa pour le produit et le métier ; Jonathan pour la technique et l'exploitation
- **Mode de réalisation :** lots successifs, avec validation explicite de Jonathan avant
  l'ouverture du lot suivant

---

## 1. État d'avancement

| Élément | Valeur |
|---|---|
| Dernier lot validé | **LOT 0 — Référentiel projet et préparation**, verrouillé le 27 juillet 2026 |
| Dernière porte franchie | **G0** — validée le 27 juillet 2026 (`DEC-438`) — [preuves](docs/operations/controles-sortie-lot-0.md) |
| **Lot en cours** | **LOT 1 — Monorepo, qualité et environnement local**, porte `G1`, tag `v0.1.0`. **Ouvert** le 27 juillet 2026 (`DEC-450`) — [plan](docs/operations/fiche-lot-1.md) |
| Sous-étape en cours | `T1` **faite** — squelette du monorepo, story `MVP-L01-US001`, issue [#2](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/2). Suivante : `T2`, stack Docker |
| Lots 2 à 14 | `Planned` — aucun travail anticipé autorisé |
| Passation | [`CLAUDE.md`](CLAUDE.md) — état, méthode et pièges de l'environnement |

Le LOT 1 a écrit les premières lignes de code du projet. À l'issue de `T1`, le dépôt porte le
**squelette exécutable** du monorepo — les sept répertoires du cahier §15.3, la chaîne de
qualité Python et TypeScript, et les versions épinglées — mais **aucune application** : ni
FastAPI, ni page web, ni stack Docker. Voir [`docs/README.md`](docs/README.md) §8 pour
l'avancement des douze sous-étapes.

### Démarrer sur une machine propre

```bash
make tools      # verifier que uv, node et pnpm sont disponibles
make install    # installer les dependances Python et JavaScript
make check      # tout verifier : versions, arborescence, iCloud, format, lint, types, tests
```

`make help` liste les quinze cibles disponibles.

---

## 2. Source de vérité

Les documents de cadrage validés se trouvent dans [`docs/`](docs/README.md).

Règle de préséance, en cas de contradiction :

1. le cahier des charges consolidé prévaut ;
2. une décision validée plus récente prévaut sur une décision plus ancienne ;
3. les annexes validées précisent les règles détaillées ;
4. aucune hypothèse ne remplace une décision explicite de Jonathan.

Toute proposition nouvelle est une **recommandation** jusqu'à validation explicite.

---

## 3. Architecture cible

Rappel des choix validés — aucun remplacement sans arbitrage explicite.

| Domaine | Choix validé |
|---|---|
| Frontend | React, TypeScript strict, Vite |
| API | Python, FastAPI |
| Base de données | PostgreSQL, SQLAlchemy, Alembic |
| Asynchrone | Redis, Dramatiq |
| Stockage objet | MinIO, compatible S3 |
| Reverse proxy | Caddy |
| E-mails hors production | Mailpit, en développement **et** en recette |
| Conteneurisation | Docker Compose |
| Images | `linux/arm64` et `linux/amd64`, publiées dans GHCR privé |
| Machine initiale | MacBook Pro Apple Silicon M5 |
| Environnements locaux | `onboarding-dev`, `onboarding-recette`, `onboarding-prod-local` |
| Versions épinglées | Python **3.12** · Node **24 LTS** · PostgreSQL **17** (`DEC-443`) |
| Monorepo | `pnpm` workspaces + workspace `uv`, orchestrés par le `Makefile` (`DEC-441`, `DEC-455`) |
| Qualité Python | Ruff, **mypy strict** (`DEC-442`), pytest |
| Qualité JS/TS | ESLint flat config avec `jsx-a11y`, Prettier, `tsc --noEmit` strict (`DEC-451`) |

Explicitement hors périmètre du MVP : PWA, fonctionnement hors ligne, Microsoft Entra ID,
Microsoft Graph, Teams, MFA, Kubernetes.

---

## 4. Règles non négociables

Ces règles sont issues des documents validés. Elles s'appliquent à chaque lot.

- aucun secret dans Git ;
- aucun fichier réel de collaborateurs, aucun CSV réel, aucune photo réelle versionnés ;
- aucune donnée métier durable dans `localStorage` ;
- aucune donnée ni image en Base64 dans PostgreSQL ou dans le code ;
- aucune règle de permission uniquement côté frontend : l'API est l'autorité finale ;
- isolation multi-entités respectée dès les fondations ;
- aucune création automatique de table en production ;
- aucun contournement du magic link ni de Mailpit en recette ;
- aucune image de production référencée par `latest` seul ;
- aucun code du prototype historique réutilisé ;
- aucune exigence `Must` ni story `P0` supprimée, fusionnée ou dégradée sans décision
  explicite et tracée.

---

## 5. Structure du dépôt

```text
.
├── README.md                  ← ce fichier
├── CLAUDE.md                  ← passation : état, méthode de travail, pièges de l'environnement
├── CONTRIBUTING.md            ← règles de contribution, définitions de Ready et de Done
├── Makefile                   ← point d'entrée unique des commandes (DEC-441)
├── .env.example               ← modèle de configuration, sans aucun secret
├── .gitignore                 ← barrière contre secrets et données réelles
├── .gitattributes             ← normalisation des fins de ligne
├── .editorconfig              ← normalisation dans l'éditeur
├── .node-version              ← 24.16   (DEC-443)
├── .python-version            ← 3.12    (DEC-443)
├── package.json               ← racine pnpm, pnpm épinglé par `packageManager`
├── pnpm-workspace.yaml        ← espaces de travail JS, store hors iCloud (DEC-439)
├── pyproject.toml             ← workspace uv, config Ruff, mypy strict, pytest (DEC-455)
├── tsconfig.base.json         ← TypeScript strict, partagé
├── eslint.config.js           ← ESLint flat config, dont jsx-a11y (DEC-451)
├── .prettierrc.json           ← Prettier
├── .prettierignore            ← Markdown exclu : protège les documents immuables (DEC-454)
├── .github/                   ← gabarits de pull request et d'issues
├── apps/
│   ├── api/                   ← API FastAPI          — squelette, application en T3
│   ├── worker/                ← worker Dramatiq      — squelette, démarrage en T3
│   └── web/                   ← frontend React/Vite  — outillage, page de statut en T5
├── packages/
│   ├── ui/                    ← design system        — coquille, tokens en T10
│   └── contracts/             ← contrat API partagé  — coquille, génération en T10
├── infra/
│   └── scripts/               ← exclure-icloud.sh (DEC-453). Compose et Caddy en T2
└── docs/
    ├── product/               ← cahier des charges, matrice des droits, roadmap, backlog
    │   └── contenus/          ← inventaire du prototype, parcours d'onboarding relevés
    ├── architecture/          ← modèle de données
    │   └── donnees/           ← schéma CSV, codes d'erreur, listes contrôlées, exemple fictif
    ├── decisions/             ← registre des décisions, registre des écarts
    ├── operations/            ← conventions, registres, politique de secrets, contrôles de sortie
    └── prototype/             ← prototype historique, non versionné, non réutilisable
```

Chaque espace de travail porte son propre `README.md` : rôle, commandes, et **ce qui y arrive
à quelle sous-étape**.

> **Ne pas remettre `node_modules` ni `.venv` dans la synchronisation iCloud.** Le dépôt
> réside dans iCloud Drive (`DEC-418`) ; ces répertoires en sont exclus par `DEC-439` et
> `DEC-453`. `pnpm install` efface le marquage, un `postinstall` le repose automatiquement, et
> `make icloud-verify` échoue s'il manque.

---

## 6. Prototype historique

Le fichier `docs/prototype/V1.html` est conservé sur disque à des fins d'historisation.
Il n'est **pas versionné** et ne constitue **pas** une base de code réutilisable.
Voir [`docs/prototype/README.md`](docs/prototype/README.md).

---

## 7. Configuration

La configuration passe exclusivement par des variables d'environnement. Le fichier `.env`
local n'est **jamais** versionné.

- [`.env.example`](.env.example) — modèle documenté en version 0.1, 74 variables, aucune valeur
  réelle. Chaque variable porte sa source documentaire et le lot où elle devient effective.
- [`docs/operations/politique-configuration-et-secrets.md`](docs/operations/politique-configuration-et-secrets.md)
  — séparation des trois environnements, garde-fous de démarrage, rotation, conduite à tenir en
  cas de fuite.

---

## 8. Suivi du projet

| Registre | Entrées |
|---|---:|
| [Décisions](docs/decisions/registre-decisions.md) | 125 |
| [Écarts](docs/decisions/registre-ecarts.md) | 18 — 6 ouverts, 10 clos, 2 acceptés |
| [Questions ouvertes](docs/operations/registre-questions-ouvertes.md) | 34 — 30 ouvertes |
| [Risques](docs/operations/registre-risques.md) | 29 |
| [Dépendances externes](docs/operations/registre-dependances-externes.md) | 17 |
| [Contenus inventoriés](docs/product/contenus/inventaire-prototype.md) | 29 |

Preuves de sortie du LOT 0 :
[contrôles](docs/operations/controles-sortie-lot-0.md) et
[checklist `G0`](docs/operations/checklist-validation-G0.md).
Arbitrages d'entrée du LOT 1 : [compte rendu `T0`](docs/operations/compte-rendu-t0-lot-1.md).
