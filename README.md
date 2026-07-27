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
| Lot ouvert | **LOT 0 — Référentiel projet et préparation** |
| Porte de validation en cours | **G0** — « Jonathan confirme les documents et conventions » |
| Sous-étape en cours | S1 — dépôt, arborescence documentaire et barrières de sécurité |
| Lots suivants | `Planned` — aucun travail anticipé autorisé |

Aucun code applicatif n'existe encore : le LOT 0 est exclusivement documentaire et
décisionnel. Le monorepo (`apps/web`, `apps/api`, `apps/worker`, `packages/*`, `infra/`)
appartient au **LOT 1** et ne doit pas être amorcé avant validation de la porte `G0`.

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
├── .gitignore                 ← barrière contre secrets et données réelles
├── .gitattributes             ← normalisation des fins de ligne
└── docs/
    ├── product/               ← cahier des charges, matrice des droits, roadmap, backlog, contenus
    ├── architecture/          ← modèle de données, schéma CSV, décisions d'architecture
    ├── decisions/             ← registre des décisions, registre des écarts
    ├── operations/            ← conventions, registres risques / questions / dépendances, exploitation
    └── prototype/             ← prototype historique, non versionné, non réutilisable
```

Les répertoires applicatifs seront créés au LOT 1, après validation de `G0`.

---

## 6. Prototype historique

Le fichier `docs/prototype/V1.html` est conservé sur disque à des fins d'historisation.
Il n'est **pas versionné** et ne constitue **pas** une base de code réutilisable.
Voir [`docs/prototype/README.md`](docs/prototype/README.md).

---

## 7. Configuration

La configuration passe exclusivement par des variables d'environnement.
Le fichier `.env` local n'est jamais versionné ; un `.env.example` documenté et sans
aucune valeur réelle sera livré dans la sous-étape S5 du LOT 0.
