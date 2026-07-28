# Passation — agent chef de projet technique

**Projet :** eXalt Onboarding Digital
**Rédigé le :** 28 juillet 2026, à la sortie de la sous-étape `T4`
**Destinataire :** l'agent qui prend le relais pour **poursuivre le LOT 1 à partir de `T5`**
**Interlocuteur unique :** Jonathan — technique et exploitation. Léa décide du produit.

Ce document dit **où en est le projet**, **ce qui a été fait et comment**, **les constantes à
connaître**, **les erreurs à ne plus commettre**, et **par où commencer**. Lis-le en entier
avant d'agir. Il remplace la passation d'ouverture du LOT 1.

---

# 1. En un coup d'œil

| | |
|---|---|
| Lots terminés | **LOT 0** verrouillé le 27/07/2026 (`DEC-438`), porte **`G0`** franchie |
| **Lot en cours** | **LOT 1 — Monorepo, qualité et environnement local**, porte `G1`, tag `v0.1.0` |
| Sous-étapes faites | **`T0`** hors lot · **`T1`** · **`T2`** · **`T3`** · **`T4`** — les cinq validées par Jonathan |
| **Prochaine action** | **`T5`** — frontend Vite, page de statut. Stories `MVP-L01-US002` et `US003`, issues [#3](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/3) et [#4](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/4) |
| Stories `Done` | **4 sur 8** : `US001`, `US002`, `US003`, `US004`. Issues `#2` à `#5` closes |
| Stories restantes | `US005` CI · `US006` images GHCR · `US007` design system (`P1`) · `US008` documentation |
| Dépôt distant | `Jonathan2433/ONBOARDING_DIGITAL` — **privé, prouvé** par `gh api … --jq .private` → `true` |
| Branches | `main` 13 commits · `develop` **19 commits**, en avance de **6**. **Les deux protégées** |
| Volumétrie | **128 fichiers suivis** — 51 Markdown, 31 Python, 7 TypeScript — **30 487 lignes** |
| Tests | **139** : 131 unitaires, 8 d'intégration sur services réels |
| Registres | **137 décisions** · 19 écarts (5 ouverts) · 37 questions (33 ouvertes) · 30 risques |

**La plateforme démarre et répond.** `make up` lève les huit services, l'API sert ses trois
endpoints de santé à travers Caddy en HTTPS, la migration initiale s'applique, et les journaux
sortent en JSON corrélé. Il n'existe **aucun écran** ni **aucune donnée métier**.

**Le régime de contribution est contraignant.** `main` et `develop` sont protégées avec
`enforce_admins` : **aucun commit direct**, y compris documentaire, y compris pour Jonathan.
Toute modification passe par une branche et une pull request vers `develop`.

---

# 2. Les règles qui ne se négocient pas

1. **Un lot à la fois.** Seul le lot ouvert par Jonathan peut être réalisé (`ROAD-003`,
   `ARB-BACK-003`, `BACKLOG-006`). Le LOT 1 est ouvert. **Le LOT 2 ne l'est pas** : n'écris pas
   une ligne qui lui appartienne — ni table, ni modèle SQLAlchemy métier, ni type métier dans
   `packages/contracts`.
2. **Aucun secret dans Git.** Ni fichier, ni message de commit, ni titre de branche, ni
   description de pull request.
3. **Aucune donnée réelle de collaborateur versionnée.** Aucun CSV réel, aucune photo.
4. **Aucune ligne de code du prototype réutilisée.** `docs/prototype/V1.html` est une référence
   d'intention, pas une base de code.
5. **L'API est l'autorité finale** sur les permissions. Jamais le frontend seul.
6. **Aucun contournement de l'authentification**, à aucun moment, même en développement.
7. **Aucune exigence `Must` ni story `P0`** supprimée, fusionnée ou dégradée sans décision
   explicite et tracée.
8. **Toute proposition nouvelle est une recommandation** jusqu'à validation de Jonathan.
9. **Ne repose jamais une question déjà tranchée.** Lis avant de demander.
10. **Ne déclare jamais une sous-étape terminée sans preuve.** Contrôles exécutés, sorties
    réelles montrées, critères vérifiés un par un.

Liste complète : [`README.md`](README.md) §4 et [`CONTRIBUTING.md`](CONTRIBUTING.md) §7.
Interdictions propres au LOT 1 : [`fiche-lot-1.md`](docs/operations/fiche-lot-1.md) §11.

---

# 3. Où est la vérité

| Question | Document |
|---|---|
| Que doit faire le produit ? | `docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md` — **prévaut sur tout** |
| Qui a le droit de faire quoi ? | `docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md` |
| Comment sont structurées les données ? | `docs/architecture/MODELE_DONNEES_EXALT.md` |
| Dans quel ordre construit-on ? | `docs/product/ROADMAP_MVP_V1_V2_EXALT.md` |
| Quelle est l'unité de travail ? | `docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md` |
| **Que fait-on au LOT 1 ?** | **`docs/operations/fiche-lot-1.md`** — 12 sous-étapes, 5 barrées |
| **Comment a-t-on fait `T1` à `T4` ?** | **`docs/operations/compte-rendu-t{0,1,2,3,4}-lot-1.md`** |
| Qu'a-t-on décidé depuis le début ? | `docs/decisions/registre-decisions.md` — **137 décisions** |
| Comment travaille-t-on ? | `CONTRIBUTING.md` et `docs/operations/conventions-git-et-versions.md` |

Les cinq documents de cadrage sont **immuables**. Intégrité prouvée par empreinte SHA-256 dans
`docs/operations/integrite-et-conformite-documents.md`. **Ne les modifie pas** — et vois §7.9,
un formateur a failli les réécrire.

Règle de préséance : le cahier prévaut ; une décision plus récente prévaut sur une plus
ancienne ; les annexes précisent le détail ; **aucune hypothèse ne remplace une décision
explicite de Jonathan**.

---

# 4. Ce qui a été livré, et comment

## 4.1 LOT 0 — référentiel documentaire

Sept stories, huit sous-étapes. 5 documents de cadrage versionnés avec preuve d'intégrité,
`CONTRIBUTING.md`, 5 registres, `.env.example`, schéma CSV, inventaire du prototype.

## 4.2 `T0` — prérequis et arbitrages, hors lot

3 prérequis bloquants levés, 7 choix techniques tranchés, traçabilité GitHub posée par `gh`.
Détail : [`compte-rendu-t0-lot-1.md`](docs/operations/compte-rendu-t0-lot-1.md).

## 4.3 `T1` — squelette du monorepo

Les **sept répertoires** du cahier §15.3, chacun avec son `README.md`. Workspaces `pnpm` **et**
`uv`. Ruff, mypy strict, pytest, ESLint avec `jsx-a11y`, Prettier, `tsc --noEmit` strict, Vitest.
`Makefile` comme point d'entrée unique.

**Comment :** chaque maillon de la chaîne a reçu un **défaut réel** pour vérifier qu'il sait
échouer — **10 témoins négatifs sur 10**. Un contrôle qui ne peut pas échouer ne prouve rien.

## 4.4 `T2` — stack Docker locale

`make up` construit, démarre et attend l'état sain des **huit services**. Compose en base +
surcouche, projet `onboarding-dev`. **8 images toutes épinglées par empreinte `sha256`**, toutes
vérifiées `linux/amd64` **et** `linux/arm64`. 6 volumes nommés. 7 publications **toutes sur
127.0.0.1**. HTTPS local par autorité interne Caddy.

**Comment :** `make persistence-test` relève cinq empreintes, arrête, redémarre, compare. Le
témoin négatif a été **réellement exécuté** — volume `redis-data` supprimé, contrôle en échec.

## 4.5 `T3` — API, santé, migration

Les **11 garde-fous** de démarrage du cahier §20.3. Les trois endpoints du §18.7. Format
d'erreur unique du §18.3. Migration `0001_initial`, **volontairement vide** (`DEC-463`). Worker
Dramatiq avec les **7 files** du §16.4.

**Comment :** `ready` a été éprouvé en **arrêtant réellement Redis** — 503, `redis
indisponible`, motif `ConnectionError`, PostgreSQL et MinIO toujours disponibles. Chaque
garde-fou a **deux** tests : celui qui l'enfreint, et le témoin qui le respecte. Les sept
contrôles de production sont éprouvés **en forçant `APP_ENV=production`**, plus un test qui
prouve qu'ils **ne s'appliquent pas** en développement.

## 4.6 `T4` — journalisation JSON corrélée

Les **dix champs** du §28.1 dans les journaux réels des conteneurs. Corrélation en **requête et
en job** : elle traverse Caddy, revient dans la réponse, et **voyage dans le message Dramatiq**.
**Trois barrières** de masquage du §28.2. Rotation `json-file` sur les huit services.

**Comment :** un **paquet Python partagé**, `packages/observabilite`, plutôt que du code
dupliqué — deux filtres de masquage finissent par diverger, et le jour où l'un oublie un motif
la fuite est silencieuse.

## 4.7 Les décisions qui contraignent ton travail quotidien

Les 137 sont dans `docs/decisions/registre-decisions.md`. Celles que tu appliqueras :

| ID | Décision |
|---|---|
| `DEC-418` | Le dépôt réside dans iCloud Drive. Risque accepté, **matérialisé une fois**, voir §7.1 |
| `DEC-427`, `DEC-429` | Branche + PR obligatoires. `main` et `develop` protégées, **0 approbation** |
| `DEC-428` | **`v0.1.0` à `G1`**, tag annoté sur `main` |
| `DEC-439`, `DEC-453`, `DEC-457` | `node_modules`, `.venv` et caches exclus d'iCloud. **Non durable** : vois §7.1 |
| `DEC-440` | **Un seul environnement à la fois.** Limites mémoire par service |
| `DEC-441`, `DEC-455` | `pnpm` workspaces **et** workspace `uv` unique. Le `Makefile` orchestre |
| `DEC-442` | **`mypy` strict** |
| `DEC-443`, `DEC-458` | Versions épinglées, **empreinte `sha256` partout**, aucun `latest` |
| `DEC-444` | Compose base + surcouches, `COMPOSE_PROJECT_NAME` distinct |
| `DEC-445` | `ghcr.io/jonathan2433/onboarding-digital/{api,web,worker}` |
| `DEC-446` | Caddy `tls internal` sur `app.` et `api.onboarding.localhost` |
| `DEC-447` | **Volumes nommés exclusivement.** Bind mount de configuration en lecture seule toléré |
| `DEC-451` | **ESLint** flat config + **Prettier**. `jsx-a11y` est le motif déterminant |
| `DEC-452` | « Exécutable » à `T1` = chaîne d'outils, pas application qui écoute |
| `DEC-454` | **Le Markdown est exclu de tout formatage automatique.** Vois §7.9 |
| `DEC-456` | Outillage posé par archive officielle, **empreinte SHA-256 vérifiée** |
| `DEC-459` | Healthcheck `api` sur `/health/ready`, `worker` sur ping du courtier |
| `DEC-460` | **Publications de ports sur `127.0.0.1` uniquement.** `make ports` le vérifie |
| `DEC-461` | `make env` génère 5 secrets locaux, en laisse 2 en `CHANGE_ME` |
| `DEC-462` | **API synchrone.** `uvicorn --factory`, configuration sur `app.state` |
| `DEC-463` | **Migration `0001_initial` vide.** Extensions au LOT 2, `QO-112` |
| `DEC-464` | Le garde-fou `CHANGE_ME` porte sur les variables que l'API **déclare** |
| `DEC-466` | Journalisation et masquage dans **`packages/observabilite`**, partagé |
| `DEC-467` | Rotation par le pilote `json-file`. **La conservation 30 jours n'est PAS couverte** |
| `DEC-468` | `resultat` prend **trois** valeurs : `succes`, `refus`, `echec` |
| `DEC-469` | **Jamais journalisés** : chaîne de requête, arguments de job, traces, accès uvicorn |

## 4.8 Les séquences d'identifiants — à respecter absolument

Un identifiant n'est **jamais** réutilisé, **jamais** renuméroté, et un trou n'est **jamais**
comblé.

| Séquence | Étendue | Prochain libre |
|---|---|---|
| `DEC-nnn` | `001`–`417` **réservés**, `418`–`469` en usage | **`DEC-470`** |
| `ECART-nnn` | `001`–`019` | **`ECART-020`** |
| `QO-nnn` | `072`–`113`, **5 trous** | **`QO-114`** |
| `ROAD-RSK-nnn` | `001`–`030` | **`ROAD-RSK-031`** |
| `DEP-nnn` | `001`–`017` | **`DEP-018`** |
| `CONT-nnn` | `001`–`029` | **`CONT-030`** |

Trous jamais comblés : `QO-075`, `QO-079`, `QO-080`, `QO-082`, `QO-090` (`ECART-011`).
**L'index à jour est dans [`docs/README.md`](docs/README.md) §4. Consulte-le avant de créer un
identifiant.**

---

# 5. Constantes et variables à connaître

## 5.1 Outillage de la machine

| Élément | Valeur | Remarque |
|---|---|---|
| `gh` | **`~/.local/bin/gh`**, 2.96.0 | **Pas dans le `PATH`.** `export PATH="$HOME/.local/bin:$PATH"` |
| `uv` | **`~/.local/bin/uv`**, **0.11.32** | Posé en `T1`, archive officielle, **empreinte SHA-256 vérifiée** |
| Homebrew | `/opt/homebrew`, **inutilisable** | Appartient à `admin`. `test -w` échoue sur `bin` **et** `Cellar` |
| Node / npm | **v24.16.0** / 11.13.0 | Via `nvm` |
| `pnpm` | **11.17.0**, par `corepack` | Épinglé par `packageManager` **avec empreinte d'intégrité** |
| Python | **3.12.13**, géré par `uv` | Le Python système 3.9.6 n'est **jamais** utilisé |
| Docker | 29.5.3, Compose **v5.1.4** | Pas de clé `version:`. **7,75 Gio alloués** |
| `make` | GNU Make **3.81** | Pas de `.ONESHELL`, pas de `$(file …)` |

## 5.2 Versions épinglées et images

Épinglage `majeur.mineur` dans les fichiers de version, **empreinte `sha256` dans les
`Dockerfile` et dans Compose**. **Aucune référence à `latest`**, contrôlée à chaque sous-étape.

| Rôle | Référence |
|---|---|
| db | `postgres:17.7@sha256:2006493727bd…` — **Debian, pas Alpine** : musl gère mal les locales |
| redis | `redis:8.4-alpine@sha256:bd4a0d37e7cd…` |
| minio | `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z@sha256:14cea493d9a3…` |
| mailpit | `ghcr.io/axllent/mailpit:v1.30@sha256:7f33095f80e9…` |
| caddy | `caddy:2.11-alpine@sha256:5f5c8640aae0…` |
| api, worker | `python:3.12-slim@sha256:57cd7c3a7a27…` — **slim, pas Alpine** : roues absentes en musl |
| web | `node:24.16-alpine@sha256:21f403ab171f…` |
| construction | `ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96…` |

> **Docker Hub applique une limite de débit anonyme.** Elle a fait échouer une inspection en
> `T2`. MinIO vient de **quay.io**, Mailpit de **ghcr.io** : leurs registres de publication, non
> limités. Si une inspection d'image échoue, **lis l'erreur** avant de conclure à une absence.

## 5.3 Les 31 cibles du `Makefile`

```text
Environnement   tools versions tree icloud-exclude icloud-verify install
Qualité         lint format format-check typecheck test test-unit test-integration check
Stack           env up down destroy ps logs health ports minio-bucket stack-check
                persistence-test
API             migrate migrate-status api-check
Nettoyage       clean clean-deps
Aide            help
```

`make check` = qualité complète. `make stack-check` = santé des 8 services + ports.
**`make help` est la source de vérité**, pas cette liste.

## 5.4 Variables de `.env.example` — **v1.0**, `ECART-006` clos

**78 variables, aucun secret.** **7** valent `CHANGE_ME` (`ECART-019` : la chaîne apparaît 9
fois, mais deux occurrences sont des commentaires — compte le motif
`^[A-Z_][A-Z0-9_]*=CHANGE_ME`).

`make env` **génère localement** `APP_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`,
`MINIO_ROOT_PASSWORD` sur 48 caractères, et un `MINIO_ROOT_USER` lisible. **Restent en
`CHANGE_ME`, et ce n'est pas un oubli** : `IMPORT_SOURCE_RETENTION_DAYS` (`QO-100`, bloquante,
LOT 9) et `UPTIME_KUMA_PUSH_URL` (LOT 13).

| Variable | Valeur par défaut |
|---|---|
| `APP_ENV` · `APP_VERSION` · `APP_REVISION` | `development` · `0.0.0-dev` · `inconnue` |
| `API_PREFIX` · `API_DOCS_ENABLED` | `/api/v1` · `true` — **`false` obligatoire en production** |
| `LOG_FORMAT` · `LOG_LEVEL` | **`json` obligatoire** · `info` |
| `LOG_RETENTION_DAYS` · `LOG_MAX_SIZE` · `LOG_MAX_FILES` | `30` (non consommée, `QO-113`) · `10m` · `5` |
| `POSTGRES_HOST` · `PORT` · `DB` · `HOST_PORT` | `db` · `5432` · `onboarding_dev` · `5432` |
| `REDIS_HOST` · `PORT` · `HOST_PORT` | `redis` · `6379` · `6379` |
| `MINIO_ENDPOINT` · `BUCKET` · `HOST_PORT` · `CONSOLE_HOST_PORT` | `minio:9000` · `onboarding-dev-media` · `9000` · `9001` |
| `SMTP_HOST` · `PORT` · `MAILPIT_HOST_PORT` | `mailpit` · `1025` · `8025` |
| `CADDY_HTTP_HOST_PORT` · `HTTPS_HOST_PORT` | `80` · `443` |
| `DRAMATIQ_QUEUES` | `default,emails,imports,media,exports,maintenance,security` |
| `DB_AUTO_CREATE` · `SESSION_COOKIE_SECURE` · `CSRF_PROTECTION_ENABLED` | `false` · `true` · `true` |
| `VITE_API_BASE_URL` | `/api/v1` |

## 5.5 Les 11 garde-fous de démarrage — **implémentés et testés**

`apps/api/app/configuration/settings.py`. **4 dans tous les environnements** : variable
obligatoire absente, `CHANGE_ME` résiduel, valeur typée invalide, `LOG_FORMAT` ≠ `json`.
**7 en production seule** : `APP_SECRET_KEY` d'au moins 32 caractères, `EMAIL_PROVIDER` ≠
`mailpit`, `API_DOCS_ENABLED=false`, `SESSION_COOKIE_SECURE=true`,
`CSRF_PROTECTION_ENABLED=true`, `DB_AUTO_CREATE=false`, `PUBLIC_BASE_URL` en `https://`.

**Le message nomme la variable, jamais sa valeur.** Un test l'éprouve.

## 5.6 Hôtes locaux et HTTPS

```text
app.onboarding.localhost   → 127.0.0.1   (frontend, 502 jusqu'à T5)
api.onboarding.localhost   → 127.0.0.1   (API, opérationnelle)
```

macOS les résout **sans toucher à `/etc/hosts`** — vérifié, 0 occurrence dans le fichier.

> **⚠️ La racine de l'autorité interne de Caddy n'est PAS approuvée dans le trousseau macOS.**
> Tous les contrôles passent par `curl -k`. **C'est l'action de Jonathan**, elle demande son mot
> de passe. En `T5`, la page s'affichera dans un navigateur : l'avertissement de certificat
> deviendra visible. **Demande-lui avant de préparer la démonstration.**

## 5.7 Contrainte mémoire

| Grandeur | Valeur mesurée |
|---|---|
| RAM machine | 16 Gio |
| **RAM allouée à Docker** | **7,75 Gio** |
| Les 8 services au repos | **146 Mio, 2 %** — mais `web` est encore un placeholder |
| Limites déclarées | 6 144 Mio au total, **effectivement appliquées** |
| Projet tiers `observatoire-ecom-studio` | **arrêté** par `docker compose stop`, volumes intacts |

**Remise en route du projet tiers, quand le LOT 1 sera fini :**

```bash
docker compose -p observatoire-ecom-studio start
```

---

# 6. La méthode de travail

## 6.1 La boucle

```text
1. Annoncer          ce qui va être modifié, pourquoi, les risques, le point de retour
2. Exécuter          une seule sous-étape, jamais deux
3. Contrôler         en lecture seule, après modification, avec témoins
4. Rapporter         au format imposé, avec les sorties réelles
5. Attendre          la validation explicite de Jonathan
6. Fusionner         une pull request par sous-étape, squash
```

## 6.2 Le format de rapport imposé

```text
État du lot · Sous-étape en cours · Travail réalisé · Contrôles exécutés · Résultats
Décisions ajoutées ou modifiées · Risques et écarts · Questions ouvertes
Validation demandée à Jonathan
```

Termine par la **commande de fusion** et celle de **retour arrière** :

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```

**Vérifie toujours `git status -sb` avant d'annoncer un point de retour.**

## 6.3 Les questions à Jonathan

Utilise **l'outil de question** : 2 à 4 options, la recommandée en premier avec
« (Recommandé) », et une description qui explique la **conséquence**.

**Jonathan a répondu « je ne comprends pas la question » deux fois pendant ce lot.** La cause
était la même : la question employait un vocabulaire technique sans dire ce qui changeait pour
lui. Quand cela arrive, **reformule sans jargon, explique ce que chaque option engage
concrètement, et dis qui décide de quoi.** N'insiste pas sur la formulation initiale.

Ne l'interroge que si la réponse change réellement le travail. S'il demande qu'un point reste en
suspens, **adapte la conception** pour qu'il reste ouvert sans bloquer, et ouvre une question au
registre. C'est ce qui a produit `DEC-434`, `QO-111`, `QO-112` et `QO-113`.

## 6.4 Générer plutôt que transcrire

Pour tout volume — 44 tâches, 68 codes d'erreur, 8 issues, 8 empreintes d'images — **génère
depuis la source par script** au lieu de recopier.

## 6.5 Ne jamais inventer ce qui n'est pas décidé

**C'est la règle la plus utilisée de ce lot.** Trois fois, la fiche annonçait un contenu que le
corpus ne définissait pas. Trois fois, la bonne réponse a été d'ouvrir une question :

- les **extensions PostgreSQL** de `0001_initial` : aucun document n'en nomme une seule →
  migration vide, `QO-112` ;
- le **fournisseur de collation** PostgreSQL : le modèle §26.1 le laisse ouvert → valeurs par
  défaut, `QO-111` ;
- la **conservation calendaire** des journaux : le pilote Docker ne sait pas le faire → dit
  explicitement, `QO-113`.

**Une hypothèse déguisée en décision est pire qu'une case vide.**

---

# 7. Les erreurs à ne plus commettre

**34 défauts détectés à ce jour** : 7 au LOT 0, 3 en `T0`, **24 pendant `T1` à `T4`**. Ils sont
tous consignés dans les comptes rendus de sous-étape.

## 7.0 La règle qui résume tout

> **Un contrôle qui ne peut pas échouer ne prouve rien. Un contrôle dont on ne lit pas le code
> de sortie ne prouve rien non plus. Un contrôle qui n'annonce pas combien d'éléments il a
> examinés peut toujours n'en avoir examiné qu'un.**

La troisième proposition est l'apport de ce lot. La parade est mécanique : **compter, et
confronter le compte à un attendu.**

## 7.1 iCloud : le risque s'est matérialisé

`ROAD-RSK-026` n'est plus théorique. Chronologie sur horodatages d'inode :

| Moment | Fait |
|---|---|
| 27/07 **17:21:19** | Création d'un **`node_modules 2`** — copie de conflit iCloud, 178 Mio, 11 066 fichiers |
| 27/07 **23:30:28** | Changement de métadonnées sur les deux, **sans aucune action de session** |
| 28/07 matin | La **copie** portait l'attribut d'exclusion, l'**original** l'avait perdu |

**L'attribut d'exclusion n'est pas durable.** `make icloud-verify` l'a détecté — pas une
inspection manuelle. Risque résiduel **accepté** par `DEC-457`.

```bash
make icloud-verify   # en DEBUT DE SESSION, ce n'est pas une formalite
```

Le motif `* [0-9]` est exclu dans `.gitignore`, `.prettierignore`, Ruff et ESLint, et
`icloud-verify` **échoue** s'il trouve une telle copie.

## 7.2 Les espaces dans le chemin — **3 occurrences**

Le dépôt vit sous `~/Library/Mobile Documents/`. **`$(CURDIR)` contient une espace.**

| Où | Symptôme |
|---|---|
| `Makefile`, `--env-file $(ENV_FILE)` non cité | `couldn't find env file: /Users/.../Library/Mobile` |
| Scripts, `eval docker compose … "$@"` | `eval` redécoupe les arguments, un `sh -c '…'` explose |
| Shell ad hoc, `DC="docker compose --env-file $PWD/.env …"` | `code=127`, **la commande n'a jamais tourné** |

```bash
# TOUJOURS citer :
docker compose --env-file "$PWD/.env" -f fichier.yml "$@"
# JAMAIS eval pour assembler une commande dont un argument est cité.
```

Dans les scripts, le montage retenu : `$COMPOSE_FILES` **non cité** — le découpage est voulu,
ces chemins n'ont pas d'espace — et `$env_file` **cité**. Le script **refuse de continuer** si un
chemin Compose contient une espace.

## 7.3 Le code de sortie d'un tuyau — **4 occurrences**

```bash
sortie=$(commande 2>&1); code=$?          # correct
if commande | sed 's/x/y/'; then …        # teste sed, JAMAIS commande
echo "code=$?"   # apres un tuyau : c'est le code du DERNIER maillon
```

En `T4`, j'ai lu « build code=0 » alors que le build venait d'échouer : la stack est remontée
sur les **anciennes images** en affichant « 8 services sains ». En `zsh`, `${pipestatus[1]}`
donne le code du premier maillon.

## 7.4 Les contrôles qui sous-couvrent — **3 occurrences**

| Contrôle | Ce qu'il annonçait | Ce qu'il avait examiné |
|---|---|---|
| `make ports` | « aucune exposition hors de 127.0.0.1 » | **5 publications sur 7** |
| Persistance | « les 5 volumes ont survécu » | **1 empreinte sur 5** |
| Témoin Mailpit | « identique » | `{"total":0}` — **un volume effacé aurait donné la même valeur** |

Causes : un découpage qui ne gardait que la première correspondance ; un `docker compose exec`
qui **consommait l'entrée standard** dans une boucle `while read` ; un témoin dont la valeur
initiale était indistinguable de l'échec.

```bash
# Lire un fichier dans une boucle qui lance des commandes : descripteur 3
while IFS= read -r ligne <&3; do commande </dev/null; done 3< "$fichier"
# Puis COMPARER le nombre examine au nombre attendu, et echouer sinon.
```

## 7.5 `zsh` ne découpe pas les variables en mots

```bash
CIBLES="a b c"
for d in $CIBLES; do …   # UNE seule iteration en zsh, sur "a b c"
```

En `T1`, cela a créé un répertoire portant huit noms concaténés. Le `Makefile` force
`SHELL := /bin/bash` pour cette raison. Ailleurs : boucle `while read` sur un document en ligne,
**et comptage des itérations**.

## 7.6 `2>/dev/null` masque les erreurs qu'il faut lire

Ma sonde d'empreintes d'images signalait `caddy:2-alpine` **ABSENT**. Le registre renvoyait
**429 Too Many Requests**. J'aurais conclu qu'une image officielle n'existe pas.

**Ne supprime jamais l'erreur d'un contrôle dont tu vas interpréter le silence.**

## 7.7 Un livrable difficile à tester est un livrable qu'on ne teste pas

Deux défauts en `T3`, tous deux corrigés **pour rendre les tests possibles**, et qui ont produit
un meilleur code :

- `app/main.py` finissait par `application = creer_application()` : importer le module lisait
  l'environnement, et la **collecte** des tests échouait → `uvicorn --factory` ;
- les routes lisaient un cache global : impossible de tester « `ready` répond 503 » sans arrêter
  des services → configuration portée par `app.state`.

## 7.8 Un test faux — 3 occurrences

- un test qui **court-circuite le point d'entrée réel** ne prouve pas ce qu'il croit ;
- un test qui cherche `court` échoue sur le libellé légitime « plus **court**e que 32
  caracteres », pas sur une fuite ;
- un test de filtre de sécurité doit énumérer **les formes réellement produites par ce projet**,
  pas des exemples de documentation. C'est ainsi qu'a été trouvé le trou de `T4-1` :
  `redis://:motdepasse@` — le format exact de `url_redis()` — **passait à travers le filtre**.

## 7.9 Un formateur a failli réécrire les documents immuables

Mesuré, exclusion neutralisée : **Prettier réécrivait les cinq documents de cadrage**, ajoutant
**54 661 octets** au seul cahier des charges, soit **+21,7 %**. Ruff voyait **41 Markdown** au
lieu de 4 fichiers Python.

La preuve d'intégrité SHA-256 — élément de la porte `G0` — aurait été invalidée **sans qu'aucun
contrôle existant ne le signale**, le contenu restant sémantiquement identique.

**Le Markdown est exclu de tout formatage automatique** (`DEC-454`). `ROAD-RSK-029` reste ouvert :
tout outil ajouté plus tard rouvrirait le risque. **Recommandation pour `T6` : un contrôle de CI
qui recalcule les cinq empreintes et échoue si l'une diffère.**

## 7.10 Les outils changent, la documentation vieillit

| Ce que je croyais | Ce qui est |
|---|---|
| `store-dir` se déclare dans `.npmrc` | **pnpm 11 ne lit plus ces clés depuis `.npmrc`** → `pnpm-workspace.yaml` |
| `reactHooks.configs['recommended-latest']` est en flat config | Il est en `eslintrc`, **ESLint 10 le refuse** → `configs.flat.recommended` |
| `defineConfig` de `vite` connaît la clé `test` | **Non**, avec Vitest 4 → `vitest/config` |
| `bash` est disponible dans une image Node | **Non**, `node:alpine` n'a que `sh` |
| L'image MinIO contient `grep` | **Non** → `mc stat`, pas `mc ls \| grep` |

**Inspecte les exports réels avant de les utiliser**, ne te fie pas à ta mémoire d'une API.

## 7.11 Vérifier ce que la documentation affirme

Ce lot a corrigé **quatre** affirmations fausses du corpus, toutes des nombres non dérivés de la
source : le bandeau « LOT 1 non ouvert » après son ouverture (`ECART-017`), « 8 contrôles de
CI » là où le cahier en énumère **11** (`ECART-018`), « 9 placeholders `CHANGE_ME` » là où il y
en a **7** (`ECART-019`), et les décisions de `T0` bornées à `DEC-447` au lieu de `DEC-449`.

**Vérifie l'état réel par `git`, `gh` et les mesures. Et dérive les nombres de la source.**

## 7.12 Outils macOS différents de GNU

| N'existe pas | Utiliser |
|---|---|
| `cat -A` | `cat -vet` |
| `grep -P` | `grep -E` ou Python |
| `timeout` | rien d'équivalent |
| `sed -i` sans argument | `sed -i ''` |

`grep` est ici **`ugrep`**, qui échoue avec « exceeds complexity limits » sur certains motifs.
**Passe par Python** pour les extractions non triviales. Le système de fichiers est **insensible
à la casse** : tout renommage ne différant que par la casse exige deux temps.

## 7.13 Ne jamais `grep` le prototype en entier

`V1.html` fait 2,83 Mo dont **2,64 Mo de Base64**. Travaille sur une version dépouillée, hors
du dépôt.

## 7.14 Ne jamais manipuler les identifiants de Jonathan

`git` et `gh` savent s'authentifier seuls. **N'extrais jamais le jeton du trousseau macOS**, et
**n'entre jamais d'identifiants à sa place** — `gh auth login`, mot de passe `sudo`, approbation
de la racine Caddy dans le trousseau sont **ses** actions.

---

# 8. Ce qui reste ouvert

## 8.1 Écarts — 5 ouverts sur 19

| ID | Objet | Échéance |
|---|---|---|
| `ECART-005` | Schéma CSV définitif relève de `QO-096` | LOT 9 |
| `ECART-012` | `intercontrat` imposé à une direction générale | LOT 2, avant LOT 5 |
| `ECART-013` | Les 5 tâches communes du prototype ont des identifiants différents | LOT 7 |
| `ECART-014` | « Représentant de cercle » contre « Booster » | LOT 6 |
| `ECART-015` | Le prototype ne fournit ni descriptions de cercles ni liens internes | LOT 6 |

`ECART-006` est **clos** en `T3` : `.env.example` est en v1.0.

## 8.2 Questions ouvertes utiles à la suite du LOT 1

| ID | Objet | Quand |
|---|---|---|
| `QO-085` | RAM et disque du Mac M5 | **Mesure après `T5`**, quand `web` travaillera vraiment |
| `QO-111` | **Fournisseur de collation PostgreSQL.** Ne se change pas sans recréer le cluster | LOT 2 |
| `QO-112` | **Liste des extensions PostgreSQL.** `CREATE EXTENSION` exige des droits élevés | LOT 2 |
| `QO-113` | **Conservation calendaire des journaux.** `json-file` borne par la taille | LOT 13 |
| `QO-094` | Second référent technique — conditionne `DEC-429` | avant production |
| `QO-106` | 9 étiquettes GitHub par défaut subsistent | choix de Jonathan |

## 8.3 Risques ouverts qui te concernent

| ID | Objet |
|---|---|
| `ROAD-RSK-026` | iCloud — **matérialisé**, résiduel accepté par `DEC-457`. `make icloud-verify` |
| `ROAD-RSK-029` | Un formateur peut réécrire les documents immuables. **Garde-fou de CI à poser en `T6`** |
| `ROAD-RSK-030` | Image `web` de **924 Mio** : elle embarque ESLint, Prettier, Vitest. **À corriger en `T7`** par un `Dockerfile` multi-étapes |
| `ROAD-RSK-015` | Secret intégré au code — la mesure devient effective en `T6` avec Gitleaks |

## 8.4 Contenus en attente de relecture

Les 29 éléments `CONT-001` à `CONT-029` sont au statut **`à relire`**. **Aucun n'est publiable en
l'état.**

---

# 9. Par où commencer : `T5`

## 9.1 Objet

**Frontend Vite : page de statut consommant les healthchecks.** Stories `MVP-L01-US002` et
`MVP-L01-US003`, issues `#3` et `#4` — **déjà closes**, `T5` complète leur démonstration.

**Critère de la fiche §3 :** « La page affiche l'état réel des services et la version ;
TypeScript strict sans erreur. »

**Critère du backlog, `US002` :** la démonstration attendue par la roadmap comprend une « page
web de statut ».

## 9.2 Ce qui est déjà là

| Élément | État |
|---|---|
| `/health/ready` | Répond 200 avec les **trois dépendances détaillées**, 503 si l'une manque |
| `/health/version` | Répond `version`, `revision`, `environnement` |
| `apps/web` | Outillage seul : React 19, Vite 8, Vitest 4, TypeScript 7, `tsconfig` strict |
| `VITE_API_BASE_URL` | `/api/v1` dans `.env.example` |
| Caddy | `app.onboarding.localhost` → `web:5173`. **502 aujourd'hui** |
| Service `web` | Démarre, healthcheck sur la résolution de Vite. `CMD` encore `sleep infinity` |

## 9.3 Ce que `T5` doit produire, à mon avis

**C'est une recommandation, pas une décision.** Vérifie-la contre la fiche et le backlog.

- `index.html`, `src/main.tsx`, `src/App.tsx`, `src/pages/StatusPage.tsx` ;
- un appel aux **deux** endpoints, avec les trois états exigés par le cahier §17.4 et la fiche
  §6 : **chargement**, **erreur**, **hors connexion** ;
- le `CMD` du `Dockerfile` web passe de `sleep infinity` à `vite --host`, et le healthcheck
  Compose devient un vrai appel HTTP — comme `DEC-459` l'a fait pour `api` en `T3` ;
- tests **Vitest et Testing Library** sur les trois états ;
- `Caddyfile` inchangé : le mandatement existe déjà.

## 9.4 Les pièges propres à `T5`

1. **La racine Caddy n'est pas approuvée.** La page s'affichera avec un avertissement de
   certificat. **Demande à Jonathan de l'approuver avant la démonstration** — c'est son mot de
   passe, pas ton action.
2. **`VITE_API_BASE_URL` vaut `/api/v1`**, un chemin relatif. Les endpoints de santé sont
   **hors** de ce préfixe, volontairement (`DEC-465`). La page doit appeler `/health/ready`, pas
   `/api/v1/health/ready`.
3. **`web` n'écoute pas encore.** Tant que le `CMD` reste `sleep infinity`, Caddy renverra 502
   quoi que tu écrives dans `src/`.
4. **`ROAD-RSK-030`** : ne cherche pas à réduire l'image web ici, c'est `T7`.
5. **Aucun écran métier.** Une page de statut n'est pas un portail. Le LOT 4 possède la
   navigation.

## 9.5 Les 7 critères de sortie de la porte `G1`

| | Critère | État |
|:--:|---|---|
| ☑ | Tous les services démarrent sur le Mac M5 | **fait en `T2`** |
| ☐ | Les images multiarchitectures sont construites | `T7` |
| ☑ | **Aucun secret réel n'est présent** | contrôlé à chaque sous-étape |
| ☑ | Une migration Alembic vide ou initiale s'exécute | **fait en `T3`** |
| ☑ | Les logs possèdent un identifiant de corrélation | **fait en `T4`** |
| ☐ | **La CI bloque volontairement une erreur de lint, de test et de secret** | **`T6`, le test le plus important du lot** |
| ☐ | Jonathan valide le socle | `T11` |

À la validation, le tag **`v0.1.0`** est posé sur `main` (`DEC-428`).

## 9.6 Ce que le LOT 1 ne doit toujours pas faire

Créer une table métier, un modèle SQLAlchemy métier ou un type métier dans
`packages/contracts` · implémenter une authentification, même partielle, même de test ·
introduire un contournement de l'authentification · charger une donnée de collaborateur ·
exposer PostgreSQL, Redis, MinIO ou Mailpit ailleurs que sur `127.0.0.1` · référencer une image
par `latest` seul · introduire Kubernetes, une PWA, un fonctionnement hors ligne, Entra ID,
Graph, Teams ou MFA · réutiliser une ligne du prototype historique.

---

# 10. Cartographie du dépôt

```text
.
├── CLAUDE.md                    ← ce document. AGENTS.md est un lien symbolique, NON VERSIONNÉ
├── README.md · CONTRIBUTING.md
├── Makefile                     ← 31 cibles, point d'entrée unique (DEC-441)
├── .env.example                 ← v1.0, 78 variables, aucun secret
├── .node-version · .python-version
├── package.json · pnpm-workspace.yaml    ← pnpm épinglé, store hors iCloud
├── pyproject.toml               ← workspace uv, Ruff, mypy strict, pytest
├── tsconfig.base.json · eslint.config.js · .prettierrc.json · .prettierignore
├── apps/
│   ├── api/      app/{configuration,health,shared}, alembic/, tests/, Dockerfile
│   ├── worker/   worker/{main,journal}.py, tests/, Dockerfile
│   └── web/      src/, vite.config.ts, Dockerfile      ← page de statut en T5
├── packages/
│   ├── observabilite/    journal JSON, masquage, corrélation (DEC-466)
│   ├── ui/               design system        ← tokens en T10
│   └── contracts/        contrat API partagé  ← génération en T10
├── infra/
│   ├── compose/  base + surcouche dev        ← surcouche recette en T8
│   ├── caddy/    Caddyfile, tls internal
│   └── scripts/  exclure-icloud · verifier-{ports,persistance,sante}
└── docs/
    ├── product/ · architecture/     ← IMMUABLES
    ├── decisions/                   ← 137 décisions, 19 écarts
    └── operations/                  ← fiche-lot-1, comptes rendus T0 à T4, registres
```

`.github/workflows/` n'existe pas encore : c'est `T6`.

---

# 11. Démarrage type d'une session

```bash
export PATH="$HOME/.local/bin:$PATH"
git switch develop && git pull
git log --oneline -5
git status -sb
gh issue list --milestone G1 --state all

make icloud-verify        # PAS une formalite : voir §7.1
make check                # qualite complete
make up                   # les 8 services
make stack-check          # sante + ports
make api-check            # les 3 endpoints
make test-integration     # 8 tests sur services reels
```

Si Docker ne répond pas : `open -a Docker`, puis attendre. Il s'est arrêté seul une fois pendant
ce lot.

1. Lire ce document.
2. Lire [`docs/README.md`](docs/README.md) : quelle porte, quel prochain identifiant.
3. Lire [`fiche-lot-1.md`](docs/operations/fiche-lot-1.md) : la sous-étape en cours.
4. Lire le **compte rendu de la sous-étape précédente** — `T4` — pour savoir ce qui a été laissé
   ouvert.
5. Vérifier l'état réel par `git`, `gh` et les mesures, **pas par ce que la doc affirme**.
6. Exécuter **une** sous-étape, contrôler, rapporter, attendre la validation.

Contrôle d'hygiène utile à tout moment :

```bash
git ls-files | grep -Ei '\.(csv|env|pem|key|mp4|html)$'   # doit ne montrer que le CSV fictif
git ls-files | grep -c 'V1.html'                          # doit valoir 0
git status --short                                        # doit être vide
```

---

# 12. Une dernière chose

Jonathan valide vite et lit sérieusement. Ce qui fonctionne avec lui :

- des rapports **denses mais courts**, avec les chiffres réels et non des approximations ;
- **signaler ses propres erreurs** dès que les contrôles les révèlent, sans les enjoliver. Les
  34 défauts sont documentés, y compris le trou de sécurité que j'avais laissé dans mon propre
  filtre de masquage, et les quatre fois où j'ai lu le code de sortie d'un `grep` en croyant lire
  celui d'une commande ;
- distinguer nettement **ce qui est prouvé** de **ce qui est recommandé** ;
- dire ce qui **n'est pas** couvert, plutôt que de le laisser croire. La conservation de 30 jours
  des journaux n'est pas faite, et `QO-113` le dit ;
- lui donner à chaque fois la commande de fusion **et** celle de retour arrière ;
- ne rien pousser vers l'extérieur sans son accord ;
- **reformuler sans jargon** quand il dit ne pas comprendre une question. C'est arrivé deux fois,
  et les deux fois c'était ma question qui était mauvaise, pas sa lecture.

Le projet a une exigence de traçabilité inhabituellement élevée : 137 décisions, et un compte
rendu par sous-étape qui consigne jusqu'aux défauts de mes propres contrôles. Ce n'est pas de la
bureaucratie. C'est ce qui permettra, au LOT 9, de justifier chaque ligne rejetée d'un import de
données personnelles réelles — et, plus tôt, de ne pas refaire quatre fois la même erreur de
tuyau. **Tiens les registres à jour dans la même pull request que le travail — jamais après.**
