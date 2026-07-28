# Fiche de lot — LOT 1 : Monorepo, qualité et environnement local

> **✅ LE LOT 1 EST OUVERT** depuis le 27 juillet 2026, décision `DEC-450`.
> Cette fiche a d'abord été un plan préparé, produit après la validation de la porte `G0`
> (`DEC-438`). Les 3 prérequis bloquants du §9.1 et les 7 choix techniques du §9.2 sont levés
> et tranchés en sous-étape `T0` : les conditions de `ROAD-003`, `ARB-BACK-003` et
> `BACKLOG-006` sont réunies, et les stories `MVP-L01-US001` à `US008` peuvent passer à
> `Ready` puis `In progress`.
>
> Les **LOTS 2 à 14 restent `Planned`** : aucune de leurs stories ne peut être entamée.
>
> *Le bandeau de non-ouverture qui figurait ici jusqu'au 27/07/2026 était devenu faux après
> `DEC-450`. Corrigé au titre de `ECART-017`.*

**Porte de validation :** `G1` — « Stack, CI et images validées »
**Tag posé à la validation :** `v0.1.0` (`DEC-428`)
**Dépendance :** LOT 0 validé le 27 juillet 2026 ✅
**Fondement :** roadmap LOT 1 ; backlog `EPIC MVP-L01` ; cahier des charges §15 à §18, §22, §23, §28
**Structure imposée :** backlog §10, « Préparation opérationnelle de chaque lot », dix points

---

## 1. Objectif et périmètre

### 1.1 Objectif littéral

> « Obtenir une plateforme vide mais exécutable localement sur le MacBook Pro M5, avec une
> chaîne de qualité opérationnelle. » — roadmap, LOT 1

### 1.2 Périmètre inclus

| Élément | Source |
|---|---|
| Monorepo : `/apps/web`, `/apps/api`, `/apps/worker`, `/packages/ui`, `/packages/contracts`, `/infra`, `/docs` | Roadmap LOT 1, cahier §15.3 |
| React, TypeScript strict, Vite | Cahier §17.1 |
| FastAPI, SQLAlchemy, Alembic | Cahier §15.1, §16.2 |
| PostgreSQL, Redis, MinIO, Dramatiq, Caddy, Mailpit | Cahier §15.1, §15.4 |
| Docker Compose pour développement **et recette** | Roadmap LOT 1, cahier §22.2 |
| Images `linux/arm64` et `linux/amd64` | Cahier §22.3 |
| Healthchecks `live`, `ready`, `version` | Cahier §18.7 |
| Logs JSON avec corrélation | Cahier §28.1 |
| CI : **11 contrôles**, énumérés au §4.3 ci-dessous | Cahier §23.1 |
| Publication de premières images techniques dans GHCR privé | Roadmap LOT 1 |

### 1.3 Périmètre exclu

**Littéral** (roadmap LOT 1, « Hors périmètre ») : écrans métier, authentification
fonctionnelle, données collaborateurs, déploiement général.

**Déduit du séquencement**, pour éviter toute dérive :

| Exclu | Lot propriétaire |
|---|---|
| Modèles SQLAlchemy métier, contraintes, historisation, isolation | LOT 2 |
| Magic links, sessions, cookies, CSRF, limitation de débit | LOT 3 |
| Toute page métier : portail national, trombinoscope, Framework | LOT 4 et suivants |
| Chaîne média complète : quarantaine, variantes, validation MIME réelle | LOT 11 |
| Outbox, files Dramatiq réellement exploitées, tâches planifiées | LOT 11 |
| Production temporaire locale, sauvegardes, restic, Uptime Kuma | LOT 13 |

> **Nuance sur MinIO.** `ARB-ROAD-002` impose d'**amorcer** le stockage MinIO dès le LOT 1. Le
> service doit donc démarrer et être sain. La chaîne média — états, empreintes, quarantaine,
> variantes — reste au LOT 11. Amorcer n'est pas implémenter.

> **Nuance sur Dramatiq.** Le worker doit démarrer et être sain, et les 7 files validées
> peuvent être déclarées. La persistance des jobs, l'outbox transactionnelle et l'idempotence
> appartiennent au LOT 11 (`MVP-L11-US001`, `US002`).

---

## 2. Stories sélectionnées et ordre interne

8 stories : **7 `P0`** et **1 `P1`**. Aucune n'est de taille `XL`, donc aucun découpage n'est
imposé par `ARB-BACK-002`.

| Ordre | ID | Prio | Taille | Résultat attendu | Dépendances |
|---:|---|:--:|:--:|---|---|
| 1 | `MVP-L01-US001` | P0 | M | Initialiser le monorepo avec les applications et packages validés | LOT 0 |
| 2 | `MVP-L01-US002` | P0 | L | Démarrer la stack Docker locale complète sur le Mac M5 | US001 |
| 3 | `MVP-L01-US003` | P0 | M | Exposer les endpoints de santé `live`, `ready` et `version` | US002 |
| 4 | `MVP-L01-US004` | P0 | M | Produire des logs JSON corrélés | US002 |
| 5 | `MVP-L01-US008` | P0 | M | Documenter lancement, arrêt, réinitialisation et diagnostic local | US002 |
| 6 | `MVP-L01-US005` | P0 | L | Mettre en place la CI de qualité et sécurité | US001 |
| 7 | `MVP-L01-US006` | P0 | L | Construire et publier des images ARM64/AMD64 dans GHCR privé | US005 |
| 8 | `MVP-L01-US007` | **P1** | M | Créer le socle du design system et du contrat API | US001 |

### 2.1 Justification de l'ordre

Les dépendances déclarées au backlog forment deux branches parallèles à partir de `US001` :
la branche d'exécution locale (`US002` → `US003`, `US004`, `US008`) et la branche
d'industrialisation (`US005` → `US006`). `US007`, seule story `P1`, est placée en dernier :
c'est la seule qui puisse faire l'objet d'un arbitrage de report sans empêcher la porte.

`US008` est volontairement traitée **avant** la CI : documenter le lancement pendant qu'on
vient de l'éprouver produit une documentation juste. Documenter après, de mémoire, produit une
documentation fausse.

---

## 3. Sous-étapes proposées

Une sous-étape, un contrôle, une validation. Même discipline que le LOT 0.

| Sous-étape | Objet | Stories | Critère de validation |
|---|---|---|---|
| ~~**T0**~~ | Prérequis et arbitrages techniques. **Aucune écriture.** ✅ **Faite le 27/07/2026, hors lot** | — | ✅ Jonathan a répondu aux 3 prérequis bloquants et aux 7 choix techniques. Voir [`compte-rendu-t0-lot-1.md`](compte-rendu-t0-lot-1.md) |
| ~~**T1**~~ | Squelette du monorepo, outillage, versions épinglées. ✅ **Faite le 27/07/2026** | `US001` | ✅ Les 7 répertoires existent ; lint, formatage, typage et tests s'exécutent sans erreur, et **chacun des 10 maillons sait échouer** — témoins négatifs vérifiés. Décisions `DEC-451` à `DEC-456` |
| ~~**T2**~~ | Docker Compose développement : les 8 services démarrent et sont sains. ✅ **Faite le 28/07/2026** | `US002` | ✅ `make up` démarre tout ; les 8 services sont `healthy` ; `make persistence-test` prouve la survie des 5 volumes, **et échoue quand un volume est réellement supprimé**. Décisions `DEC-458` à `DEC-461` |
| ~~**T3**~~ | API FastAPI minimale, 3 healthchecks, migration Alembic initiale. ✅ **Faite le 28/07/2026** | `US003` | ✅ Les 3 endpoints répondent à travers Caddy ; `ready` sonde réellement les 3 dépendances et **répond 503 quand Redis est arrêté pour de vrai** ; la migration s'applique sur base vide, se rejoue, et s'annule. `DEC-462` à `DEC-465` |
| ~~**T4**~~ | Journalisation JSON corrélée, API et worker. ✅ **Faite le 28/07/2026** | `US004` | ✅ Les 10 champs du cahier §28.1 dans les journaux **réels** des conteneurs ; corrélation en requête **et** en job, propagée à travers Caddy ; **3 barrières** de masquage, 30 tests ; rotation sur les 8 services. `DEC-466` à `DEC-469` |
| **T5** | Frontend Vite : page de statut consommant les healthchecks | `US002`, `US003` | La page affiche l'état réel des services et la version ; TypeScript strict sans erreur |
| **T6** | CI GitHub Actions : **11 contrôles** du cahier §23.1, dont **3 échecs volontaires prouvés** | `US005` | Les 11 contrôles sont exécutés ; le pipeline passe ; et il **échoue effectivement** sur une erreur de lint, une erreur de test et un secret introduits volontairement |
| **T7** | Images multiarchitecture et publication GHCR privé | `US006` | Une même version immuable fonctionne sur `arm64` et `amd64` ; l'accès au registre est authentifié ; aucune référence à `latest` seul |
| **T8** | Environnement de recette isolé | `US002` | Volumes, base, bucket, réseau, ports et secrets distincts du développement ; Mailpit exclusif |
| **T9** | Documentation d'exploitation locale | `US008` | Les procédures fonctionnent **depuis une machine propre** ; ports, volumes et commandes de diagnostic identifiés |
| **T10** | Design system minimal et contrat API partagé | `US007` (`P1`) | Tokens et composants de base sans dépendance visuelle arbitraire ; contrat généré et partagé |
| **T11** | Contrôles de sortie et préparation de la porte `G1` | — | Les 7 critères de sortie sont prouvés ; checklist remise à Jonathan |

---

## 4. Fichiers et modules probablement affectés

Le LOT 1 **crée**. Il ne modifie du LOT 0 que les registres, l'index et le `README`.

### 4.1 Créations attendues

```text
apps/
├── api/
│   ├── app/
│   │   ├── main.py                    ← application FastAPI, montage des routes de santé
│   │   ├── configuration/             ← lecture et validation de la configuration
│   │   │   └── settings.py            ← garde-fous de démarrage du cahier §20.3
│   │   ├── shared/
│   │   │   ├── logging.py             ← journalisation JSON, correlation_id
│   │   │   ├── errors.py              ← format d'erreur du cahier §18.3
│   │   │   └── database.py            ← session SQLAlchemy
│   │   └── health/                    ← live, ready, version
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/0001_initial.py   ← extensions seules, AUCUNE table métier
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── worker/
│   ├── worker/main.py                 ← démarrage Dramatiq, déclaration des 7 files
│   ├── tests/
│   └── Dockerfile
└── web/
    ├── src/{main.tsx,App.tsx,pages/StatusPage.tsx}
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json                  ← TypeScript strict
    └── Dockerfile

packages/
├── ui/                                ← tokens et composants de base (T10)
└── contracts/                         ← contrat API partagé (T10)

infra/
├── compose/
│   ├── docker-compose.dev.yml
│   ├── docker-compose.recette.yml
│   └── docker-compose.base.yml
├── caddy/Caddyfile
├── postgres/init/
└── minio/

.github/workflows/
├── ci.yml                             ← 11 contrôles du cahier §23.1
└── images.yml                         ← Buildx multiarchitecture, GHCR

Makefile                               ← la « commande documentée » de la démonstration
```

### 4.2 Modifications du LOT 0

| Fichier | Nature de la modification |
|---|---|
| `.env.example` | Passage de v0.1 à v1.0, complété par les variables réellement nécessaires. **Clôt `ECART-006`** |
| `.gitignore` | Ajouts éventuels liés à l'outillage retenu |
| `README.md`, `docs/README.md` | Avancement, structure, porte courante |
| `docs/decisions/registre-decisions.md` | Décisions `DEC-439` et suivantes |
| `docs/decisions/registre-ecarts.md` | Clôture de `ECART-006` et `ECART-010` |
| `docs/operations/registre-questions-ouvertes.md` | Clôture de `QO-107`, `QO-108`, `QO-109` ; éléments de réponse à `QO-085` et `QO-086` |
| `docs/operations/registre-risques.md` | Réévaluation de `ROAD-RSK-015`, `026`, `027` |
| `docs/operations/exploitation-locale.md` | **Création** (T9) |

Les cinq documents de cadrage validés restent **immuables**. Leurs empreintes SHA-256 doivent
être vérifiées à la sortie du lot.

---

## 5. Migrations prévues

**Une seule migration, volontairement minimale.**

| Migration | Contenu | Justification |
|---|---|---|
| `0001_initial` | Extensions PostgreSQL strictement nécessaires. **Aucune table métier.** | Modèle §28, étape 1 de l'ordre recommandé. La roadmap n'exige au LOT 1 qu'« une migration Alembic vide ou initiale s'exécute » |

Contrôles obligatoires, modèle §28 :

- application sur une **base vide** ;
- rejeu depuis l'état précédent ;
- `downgrade` puis `upgrade` compatible ;
- **aucune création automatique de table** : `DB_AUTO_CREATE=false`. Attention à la source —
  le cahier §16.2 énonce le **principe**, « aucune création automatique de tables **en
  production** », et ne contient nulle part la chaîne `DB_AUTO_CREATE` ; ce nom de variable
  vient de [`.env.example`](../../.env.example) L104, produit au LOT 0. Le LOT 1 applique la
  contrainte **dans tous les environnements**, ce qui est plus strict que le cahier et
  correspond à la valeur par défaut déjà livrée ;
- exécution sur **PostgreSQL réel**, jamais SQLite.

Toute table métier créée dans ce lot serait une anticipation du LOT 2 et devrait être refusée.

---

## 6. Tests à écrire

| Catégorie | Contenu | Story |
|---|---|---|
| Unitaires API | Lecture et validation de la configuration ; **les 11 garde-fous de démarrage** de [`politique-configuration-et-secrets.md`](politique-configuration-et-secrets.md) §6 refusent bien de démarrer — **4 applicables à tous les environnements** (variable obligatoire absente, `CHANGE_ME_*` résiduel, valeur typée invalide, `LOG_FORMAT` autre que `json`) et **7 propres à `APP_ENV=production`**, à éprouver en forçant cette valeur en test | `US002` |
| Intégration PostgreSQL réel | Connexion, application de la migration, rejeu. **Aucune dépendance à SQLite** | `US003` |
| API | Les 3 healthchecks ; `ready` en échec quand une dépendance est absente ; format d'erreur du cahier §18.3 avec identifiant de corrélation | `US003` |
| Journalisation | Présence du `correlation_id` en requête **et** en job ; **absence de secret, de jeton et de magic link** dans la sortie | `US004` |
| Frontend | Vitest et Testing Library sur la page de statut ; état de chargement, état d'erreur, état hors connexion | `US002` |
| CI, échecs volontaires | Une erreur de lint, une erreur de test et un secret introduits volontairement **doivent bloquer** le pipeline | `US005` |
| Images | La même version immuable démarre sur `arm64` et sur `amd64` | `US006` |
| Reprise | Arrêt puis redémarrage de la stack **sans perte de volume** | `US002` |

Le test de la CI est le plus important du lot : la roadmap exige que « la CI bloque
volontairement une erreur de lint, de test et de secret ». Il faut donc **prouver l'échec**, pas
seulement le succès. C'est la leçon du défaut n°7 du LOT 0 : un contrôle qui ne peut pas
échouer ne prouve rien.

---

## 7. Démonstration attendue

Littéralement, roadmap LOT 1 :

| # | Élément à démontrer |
|---:|---|
| 1 | Lancement complet **avec une commande documentée** |
| 2 | Page web de statut |
| 3 | API répondant aux trois healthchecks |
| 4 | PostgreSQL, Redis, MinIO, worker et Mailpit **sains** |
| 5 | Arrêt et redémarrage **sans perte des volumes** |
| 6 | Pipeline CI réussi |

À quoi s'ajoute, par les critères de sortie : la construction des images multiarchitectures, et
la démonstration que la CI **bloque** une erreur de lint, de test et de secret.

---

## 8. Risques propres au lot

| Risque | Impact sur ce lot | Traitement |
|---|---|---|
| `ROAD-RSK-026` Dépôt et volumes dans iCloud Drive | ~~Bloquant avant T2.~~ **Traité en `T0`.** Le périmètre réel s'est révélé plus étroit : les volumes nommés sont déjà hors iCloud | `DEC-447` volumes nommés exclusivement, `DEC-439` exclusion de `node_modules` et du cache. `QO-109` close |
| `ROAD-RSK-027` ~~16 Gio~~ **7,75 Gio** de mémoire allouée à Docker | **Plus contraint qu'estimé.** Docker ne dispose que de la moitié des 16 Gio, et un projet tiers en occupait 25 % | `DEC-440` : un seul environnement à la fois, limites mémoire par service, projet tiers arrêté pendant le lot. `T8` prouve la **séparation**, pas la simultanéité |
| `ROAD-RSK-015` Secret intégré au code | La mesure devient effective en T6 avec Gitleaks | Jusqu'à T6, contrôles manuels de chaque commit |
| `ROAD-RSK-011` Lot technique sans résultat visible | Moyen | La page de statut de T5 est la réponse : elle rend le socle démontrable |
| `ROAD-RSK-002` Réouverture d'un lot validé | Moyen | Le LOT 1 fixe l'outillage de tout le projet : un mauvais choix en T1 coûte cher plus tard |
| ~~Nouveau~~ **Traité** | Le premier commit de code déclenche le circuit branche + PR (`DEC-427`) et la protection de `main` (`DEC-429`) | Prérequis traités en `T0`, avant l'ouverture. `main` et `develop` sont protégées avec `enforce_admins`, rejet du push direct **prouvé** par `GH006`. Le circuit s'applique désormais à **toute** modification, y compris documentaire |

---

## 9. Décisions encore nécessaires

### 9.1 Prérequis bloquants, hérités du LOT 0

> **✅ Les 3 prérequis sont levés** en sous-étape `T0`, le 27 juillet 2026, **avant l'ouverture
> du lot**. Voir [`compte-rendu-t0-lot-1.md`](compte-rendu-t0-lot-1.md).

| # | Prérequis | Références | Pourquoi bloquant | État |
|---:|---|---|---|---|
| 1 | Mettre en place la traçabilité GitHub : 13 étiquettes, 15 milestones, protection de `main`. `gh` n'est pas installé et aucun connecteur GitHub n'est disponible | `ECART-010`, `QO-107`, `QO-108` | `DEC-427` fait entrer le circuit PR en vigueur dès le premier commit de code. Sans protection ni issues, `BACKLOG-010` n'est pas respecté | **Levé.** `gh` 2.96.0 installé hors Homebrew, authentifié par Jonathan. 13 étiquettes, 15 milestones, epic `#1`, stories `#2`–`#9`. `main` et `develop` protégées, `enforce_admins` actif, **rejet du push direct prouvé** (`GH006`). `DEC-449`. `ECART-010`, `QO-107` et `QO-108` clos |
| 2 | Décider des atténuations iCloud pour les volumes Docker et les dépendances | `QO-109`, `ROAD-RSK-026` | Un volume PostgreSQL créé dans un dossier synchronisé est un risque de corruption. Déplacer après coup coûte plus cher | **Levé.** Mesure : les volumes nommés sont déjà hors iCloud, l'image disque de la VM Docker résidant sous `~/Library/Containers/`. Restaient `node_modules` et le cache. `DEC-439`, `DEC-447`. `QO-109` close |
| 3 | Arbitrer l'exécution non simultanée des environnements | `ROAD-RSK-027`, `QO-085` | Détermine la conception des fichiers Compose et des limites mémoire | **Levé.** Docker ne dispose que de **7,75 Gio**, dont un quart occupé par un projet tiers. Un seul environnement à la fois ; projet tiers arrêté pendant le lot. `DEC-440`. `ROAD-RSK-027` réécrit |

### 9.2 Choix techniques non tranchés par les documents validés

Aucun document du corpus ne les fixe. Ils ont été présentés en **`T0`** avec une recommandation
argumentée. **Les 7 sont tranchés et validés** par Jonathan le 27 juillet 2026.

| # | Choix | Contrainte connue | Décision retenue |
|---:|---|---|---|
| 1 | Gestionnaire de paquets JavaScript et outillage monorepo | Aucune dépendance essentielle à un CDN public (roadmap §2.3) | **`pnpm` workspaces**, store hors iCloud, aucun orchestrateur de tâches — `DEC-441` |
| 2 | `mypy` **ou** `pyright` | Le cahier §23.5 cite les deux sans trancher | **`mypy` strict**, dans l'environnement `uv` — `DEC-442` |
| 3 | Versions épinglées de Python, Node et PostgreSQL | Interdiction de `latest` seul en production (cahier §23.3) | **Python 3.12 · Node 24 LTS · PostgreSQL 17**, épinglage par empreinte `sha256` — `DEC-443` |
| 4 | Organisation des fichiers Compose pour trois environnements | Volumes, bases, buckets, réseaux, ports et secrets distincts (cahier §22.2) | **Base + surcouches**, `COMPOSE_PROJECT_NAME` distinct par environnement — `DEC-444` |
| 5 | Nommage et étiquetage des images GHCR | Version exacte et empreinte de commit obligatoires (`DEC-428`) | **`ghcr.io/jonathan2433/onboarding-digital/{api,web,worker}`** — `DEC-445` |
| 6 | HTTPS local par Caddy | Aucun domaine public nécessaire en phase locale (cahier §22.2) | **`tls internal`** sur `app.` et `api.onboarding.localhost` — `DEC-446` |
| 7 | Emplacement physique des volumes Docker | Dépend du prérequis 2 | **Volumes nommés exclusivement**, aucun bind mount de donnée d'état — `DEC-447` |

Le cahier §23.5 propose par ailleurs `uv`, Ruff, Pytest, pytest-cov, Alembic, Gitleaks,
pip-audit, Trivy, Vitest, Playwright et axe comme **outils candidats**. Je les retiendrai sauf
objection, ces choix étant déjà inscrits au cadrage.

### 9.3 Questions ouvertes qui trouveront des éléments de réponse dans ce lot

| Question | Apport attendu du LOT 1 |
|---|---|
| `QO-085` RAM et disque du Mac M5 | Mesure réelle en charge, une fois les 8 services démarrés |
| ~~`QO-086`~~ Docker Desktop ou moteur alternatif | **Close en `T0`** : Docker Desktop 29.5.3, Compose v5.1.4, pilote `overlayfs`, `aarch64`, **7,75 Gio alloués**. Aucun moteur alternatif |
| `QO-084` PostgreSQL RLS immédiat ou différé | À trancher au LOT 2, mais la migration initiale peut préparer le terrain |

---

## 10. Checklist de validation de la porte `G1`

Les 7 critères littéraux de la roadmap, LOT 1.

| | Critère de sortie |
|:--:|---|
| ☐ | Tous les services démarrent sur le Mac M5 |
| ☐ | Les images multiarchitectures sont construites |
| ☐ | **Aucun secret réel n'est présent** |
| ☐ | Une migration Alembic vide ou initiale s'exécute |
| ☐ | Les logs possèdent un identifiant de corrélation |
| ☐ | **La CI bloque volontairement une erreur de lint, de test et de secret** |
| ☐ | Jonathan valide le socle |

Complétés par les 9 critères d'empêchement du backlog §12, dont quatre étaient « sans objet »
au LOT 0 et **deviennent applicables ici** :

| | Critère devenant applicable |
|:--:|---|
| ☐ | Une migration fonctionne sur une base propre |
| ☐ | Aucun secret ni donnée réelle versionné — désormais vérifié **automatiquement** par Gitleaks |
| ☐ | La documentation minimale d'exploitation existe et fonctionne depuis une machine propre |
| ☐ | La démonstration correspond aux critères de la roadmap |

Restent « sans objet » au LOT 1 : les permissions critiques et le comportement mobile ou
clavier essentiel, l'authentification et les écrans métier n'appartenant pas à ce lot.

À la validation de `G1`, le tag `v0.1.0` est posé sur `main` (`DEC-428`).

---

## 11. Ce que ce lot ne doit pas faire

Rappel des interdictions les plus susceptibles d'être enfreintes dans un lot d'amorçage :

- créer une table métier, un modèle SQLAlchemy métier ou une migration de contenu ;
- implémenter une authentification, même partielle, même de test ;
- introduire un mécanisme de contournement de l'authentification ;
- charger la moindre donnée de collaborateur, réelle ou non ;
- exposer publiquement PostgreSQL, Redis, MinIO ou Mailpit ;
- référencer une image par `latest` seul ;
- placer un secret dans un fichier versionné, un message de commit ou une description de PR ;
- installer une dépendance non prévue sans justification tracée ;
- introduire Kubernetes, une PWA ou un fonctionnement hors ligne ;
- réutiliser une ligne de code du prototype historique.
