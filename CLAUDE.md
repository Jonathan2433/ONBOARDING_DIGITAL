# Passation — agent chef de projet technique

**Projet :** eXalt Onboarding Digital
**Rédigé le :** 27 juillet 2026, à l'ouverture du LOT 1
**Destinataire :** l'agent qui prend le relais pour **réaliser le LOT 1**
**Interlocuteur unique :** Jonathan — technique et exploitation. Léa décide du produit.

Ce document dit **où en est le projet**, **ce qui a été fait et comment**, **les constantes à
connaître**, **les erreurs à ne plus commettre**, et **par où commencer**. Lis-le en entier
avant d'agir. Il remplace la passation de clôture du LOT 0.

---

# 1. En un coup d'œil

| | |
|---|---|
| Lots terminés | **LOT 0** verrouillé le 27/07/2026 (`DEC-438`), porte **`G0`** franchie |
| Sous-étape `T0` | **Terminée hors lot.** 3 prérequis levés, 7 choix techniques tranchés |
| **Lot en cours** | **LOT 1 — Monorepo, qualité et environnement local**, porte `G1`, tag `v0.1.0` |
| **État du LOT 1** | **OUVERT** par Jonathan le 27/07/2026 (`DEC-450`) |
| **Prochaine action** | **`T1`** — squelette du monorepo, story `MVP-L01-US001`, issue [#2](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/2) |
| Code applicatif | **Aucun à ce jour.** Le LOT 1 écrit les premières lignes |
| Dépôt distant | `Jonathan2433/ONBOARDING_DIGITAL` — **privé, prouvé** par `gh api … --jq .private` → `true` |
| Branches | `main` 13 commits · `develop` 14 commits, en avance de 1. **Les deux protégées** |
| Volumétrie | 46 fichiers suivis, 41 Markdown, ~18 070 lignes |

**Le régime de contribution a changé.** `main` et `develop` sont protégées avec
`enforce_admins` : **aucun commit direct n'est possible**, y compris documentaire, y compris
pour Jonathan. Toute modification passe par une branche et une pull request vers `develop`.

---

# 2. Les règles qui ne se négocient pas

Elles viennent des documents validés, pas de moi.

1. **Un lot à la fois.** Seul le lot explicitement ouvert par Jonathan peut être réalisé
   (`ROAD-003`, `ARB-BACK-003`, `BACKLOG-006`). Le LOT 1 est ouvert. **Le LOT 2 ne l'est pas** :
   n'écris pas une ligne qui lui appartienne.
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
10. **Ne déclare jamais un lot terminé sans preuve.** Contrôles exécutés, sorties réelles
    montrées, critères de sortie vérifiés un par un.

Liste complète des interdictions : [`README.md`](README.md) §4 et
[`CONTRIBUTING.md`](CONTRIBUTING.md) §7. Interdictions propres au LOT 1 :
[`fiche-lot-1.md`](docs/operations/fiche-lot-1.md) §11.

---

# 3. Où est la vérité

| Question | Document |
|---|---|
| Que doit faire le produit ? | `docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md` — **prévaut sur tout** |
| Qui a le droit de faire quoi ? | `docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md` |
| Comment sont structurées les données ? | `docs/architecture/MODELE_DONNEES_EXALT.md` |
| Dans quel ordre construit-on ? | `docs/product/ROADMAP_MVP_V1_V2_EXALT.md` |
| Quelle est l'unité de travail ? | `docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md` |
| **Que fait-on au LOT 1 ?** | **`docs/operations/fiche-lot-1.md`** — plan en 12 sous-étapes |
| **Qu'a-t-on décidé en `T0` ?** | **`docs/operations/compte-rendu-t0-lot-1.md`** |
| Qu'a-t-on décidé depuis le début ? | `docs/decisions/registre-decisions.md` — **117 décisions** |
| Comment travaille-t-on ? | `CONTRIBUTING.md` et `docs/operations/conventions-git-et-versions.md` |

Les cinq documents de cadrage sont **immuables**. Intégrité prouvée par empreinte SHA-256 dans
`docs/operations/integrite-et-conformite-documents.md`. **Ne les modifie pas.** Toute évolution
suit la procédure du cahier §35.

Règle de préséance : le cahier prévaut ; une décision plus récente prévaut sur une plus
ancienne ; les annexes précisent le détail ; **aucune hypothèse ne remplace une décision
explicite de Jonathan**.

---

# 4. Ce qui a été livré

## 4.1 LOT 0 — référentiel documentaire

Sept stories, huit sous-étapes, un commit par sous-étape. 5 documents de cadrage versionnés avec
preuve d'intégrité, `CONTRIBUTING.md` et conventions Git, 5 registres, `.env.example` à
74 variables, schéma CSV `1.0-initiale` (19 champs logiques, 68 codes d'erreur), inventaire du
prototype (29 contenus, 44 tâches d'onboarding relevées).

## 4.2 `T0` — prérequis et arbitrages techniques

Exécutée **hors lot**, sans écriture de code. Elle a levé les 3 prérequis bloquants et tranché
les 7 choix techniques que la fiche laissait ouverts. Détail complet et preuves :
[`compte-rendu-t0-lot-1.md`](docs/operations/compte-rendu-t0-lot-1.md).

> **Pourquoi hors lot.** La fiche exigeait en §9.1 que les prérequis soient réglés « avant
> l'ouverture du lot », mais plaçait en §3 la sous-étape qui les résout **dans** le lot.
> Contradiction levée en traitant `T0` comme une porte d'entrée : elle n'écrit rien, donc son
> exécution hors lot n'enfreint ni `ROAD-003`, ni `ARB-BACK-003`, ni `BACKLOG-006`.

## 4.3 Traçabilité GitHub — posée et prouvée

| Élément | État |
|---|---|
| 13 étiquettes prescrites | **Créées**, conformes en nom **et** couleur |
| 15 milestones `G0`–`G14` | **Créées**, `G0` **fermée** |
| Epic du LOT 1 | Issue **#1** |
| 8 stories du LOT 1 | Issues **#2** à **#9**, toutes sur `G1`, 7 `p0` + 1 `p1` |
| Protection `main` et `develop` | **Posée**, `enforce_admins` actif, **rejet du push direct prouvé** (`GH006`) |
| Issues des LOTS 2 à 14 | **Non créées** — 104 restantes, à créer lot par lot |
| Contrôles d'intégration obligatoires | **Aucun** — à ajouter en `T6`, quand la CI existera |

## 4.4 Les séquences d'identifiants — à respecter absolument

Un identifiant n'est **jamais** réutilisé, **jamais** renuméroté, et un trou n'est **jamais**
comblé.

| Séquence | Étendue | Prochain libre |
|---|---|---|
| `DEC-nnn` décisions | `001`–`417` **réservés**, `418`–`450` en usage | **`DEC-451`** |
| `ECART-nnn` écarts | `001`–`016` | **`ECART-017`** |
| `QO-nnn` questions | `072`–`110`, **5 trous** | **`QO-111`** |
| `ROAD-RSK-nnn` risques | `001`–`028` | **`ROAD-RSK-029`** |
| `DEP-nnn` dépendances | `001`–`017` | **`DEP-018`** |
| `CONT-nnn` contenus | `001`–`029` | **`CONT-030`** |
| `RIGHTS` / `DATA` / `ROAD` / `BACKLOG` | figées au cadrage | `026` / `019` / `013` / `011` |
| `ARB-DROIT / ARB-DATA / ARB-ROAD / ARB-BACK` | `-001`–`-005` chacun | `-006` |

Trous conservés, jamais comblés : `QO-075`, `QO-079`, `QO-080`, `QO-082`, `QO-090`
(`ECART-011`). Plage `DEC-001`–`DEC-417` réservée pour un import ultérieur (`DEC-422`).

**L'index à jour est dans [`docs/README.md`](docs/README.md) §4. Consulte-le avant de créer un
identifiant.**

## 4.5 Les décisions qui contraignent ton travail quotidien

Les 117 sont dans `docs/decisions/registre-decisions.md`. Celles que tu appliqueras au LOT 1 :

| ID | Décision |
|---|---|
| `DEC-418` | Le dépôt réside dans iCloud Drive. Risque accepté, atténué par `DEC-439` et `DEC-447` |
| `DEC-420` | `V1.html` conservé dans `docs/prototype/`, **exclu du suivi Git** |
| `DEC-427` | Circuit branche + pull request dès le premier commit de code du LOT 1 |
| `DEC-428` | Versions jalonnées sur les portes : **`v0.1.0` à `G1`** … `v1.0.0` à `G14` |
| `DEC-429` | `main` protégée : PR obligatoire, **zéro approbation** — GitHub interdit l'auto-approbation (`QO-094`) |
| **`DEC-439`** | **`node_modules` et cache de paquets exclus d'iCloud** ; store `pnpm` hors dossier synchronisé ; le dépôt reste dans iCloud |
| **`DEC-440`** | **Un seul environnement à la fois.** Limites mémoire par service. Projet tiers arrêté pendant le LOT 1 |
| **`DEC-441`** | **`pnpm` workspaces.** Ni Turborepo, ni Nx : le `Makefile` tient ce rôle |
| **`DEC-442`** | **`mypy` strict**, dans l'environnement `uv`. Pas `pyright` |
| **`DEC-443`** | **Python 3.12 · Node 24 LTS · PostgreSQL 17.** Épinglage `majeur.mineur` + **empreinte `sha256`** dans les `Dockerfile` |
| **`DEC-444`** | **Compose base + surcouches**, `COMPOSE_PROJECT_NAME` distinct par environnement |
| **`DEC-445`** | **`ghcr.io/jonathan2433/onboarding-digital/{api,web,worker}`** |
| **`DEC-446`** | **Caddy `tls internal`** sur `app.` et `api.onboarding.localhost` |
| **`DEC-447`** | **Volumes nommés exclusivement.** Aucun bind mount de donnée d'état |
| **`DEC-449`** | Traçabilité GitHub posée par `gh`. Remplace `DEC-448` |
| **`DEC-450`** | **Ouverture du LOT 1** |

---

# 5. Constantes et variables à connaître

Tout ce qui suit est **décidé**. Ne le change pas sans arbitrage tracé.

## 5.1 Outillage de la machine

| Élément | Valeur | Remarque |
|---|---|---|
| `gh` | **`~/.local/bin/gh`**, version 2.96.0 | **Pas dans le `PATH`.** Préfixe par `export PATH="$HOME/.local/bin:$PATH"` |
| Homebrew | `/opt/homebrew`, **inutilisable** | Appartient à l'utilisateur `admin`, pas à `jonathan.dupau`. `brew install` échoue. Le correctif `sudo chown` exige le mot de passe de Jonathan |
| Docker | 29.5.3, Compose **v5.1.4** | Compose v5 : pas de clé `version:`, `include:` disponible |
| Node / npm | v24.16.0 / 11.13.0 | `pnpm` **pas encore installé** — à poser en `T1` |
| Python système | 3.9.6 | **N'y touche pas.** `uv` gèrera Python 3.12 |
| `uv` | **pas installé** | À poser en `T1` |

## 5.2 Versions épinglées (`DEC-443`)

```text
Python      3.12
Node        24 LTS
PostgreSQL  17
```

Épinglage `majeur.mineur` dans les fichiers de version, **empreinte `sha256`** dans les
`Dockerfile`. Le cahier §23.3 interdit `latest` seul ; l'épinglage par empreinte va au-delà.

## 5.3 Images GHCR (`DEC-445`)

```text
ghcr.io/jonathan2433/onboarding-digital/api
ghcr.io/jonathan2433/onboarding-digital/web
ghcr.io/jonathan2433/onboarding-digital/worker
```

Étiquettes : `:0.1.0` (**seule** référence de déploiement), `:sha-<court>`, `:develop` pour la
recette. Labels OCI `revision`, `version`, `source` obligatoires. Consommation **par empreinte**
en production temporaire. Architectures `linux/arm64` **et** `linux/amd64` (cahier §22.3).

## 5.4 Environnements Compose (`DEC-444`, cahier §22.2)

```text
onboarding-dev
onboarding-recette
onboarding-prod-local
```

Sept séparations exigées par le cahier : projet Docker, base PostgreSQL, bucket MinIO, volumes,
secrets, réseau, ports. Le `COMPOSE_PROJECT_NAME` en couvre automatiquement deux — volumes et
réseaux ; les cinq autres sont à distinguer explicitement.

## 5.5 Hôtes locaux (`DEC-446`)

```text
app.onboarding.localhost
api.onboarding.localhost
```

macOS résout `.localhost` vers 127.0.0.1 **sans toucher à `/etc/hosts`**. La racine de
l'autorité interne de Caddy devra être approuvée une fois dans le trousseau macOS — **c'est une
action de Jonathan, elle demande son mot de passe.**

## 5.6 Variables de `.env.example` v0.1

74 variables, aucun secret, 9 placeholders `CHANGE_ME_*`. Les principales :

| Variable | Valeur par défaut |
|---|---|
| `APP_ENV` | `development` |
| `PUBLIC_BASE_URL` | `https://localhost` |
| `LOG_FORMAT` / `LOG_LEVEL` | `json` / `info` |
| `POSTGRES_HOST` / `PORT` / `DB` | `db` / `5432` / `onboarding_dev` |
| `REDIS_HOST` / `PORT` | `redis` / `6379` |
| `MINIO_ENDPOINT` / `BUCKET` / `REGION` | `minio:9000` / `onboarding-dev-media` / `eu-west-1` |
| `MINIO_HOST_PORT` / `CONSOLE` | `9000` / `9001` |
| `SMTP_HOST` / `PORT` · `MAILPIT_HOST_PORT` | `mailpit` / `1025` · `8025` |
| `CADDY_HTTP_HOST_PORT` / `HTTPS` | `80` / `443` |
| `VITE_API_BASE_URL` | `/api/v1` |
| `ALLOWED_EMAIL_DOMAINS` | `exalt-company.com` |
| `DB_AUTO_CREATE` | `false` |

`ECART-006` : `.env.example` est en **v0.1** et doit passer en **v1.0 au LOT 1**, complété par
les variables réellement nécessaires. `IMPORT_SOURCE_RETENTION_DAYS` reste en `CHANGE_ME` :
sa valeur relève de `QO-100`, bloquante.

## 5.7 Les 11 garde-fous de démarrage

`docs/operations/politique-configuration-et-secrets.md` §6. **4 dans tous les environnements** :
variable obligatoire absente, `CHANGE_ME_*` résiduel, valeur typée invalide, `LOG_FORMAT` autre
que `json`. **7 en production seule** : `APP_SECRET_KEY`, `EMAIL_PROVIDER` ≠ `mailpit`,
`API_DOCS_ENABLED=false`, `SESSION_COOKIE_SECURE=true`, `CSRF_PROTECTION_ENABLED=true`,
`DB_AUTO_CREATE=false`, `PUBLIC_BASE_URL` en `https://`.

Les 7 derniers s'éprouvent en **forçant `APP_ENV=production`** dans le test.

## 5.8 Contrainte mémoire — le chiffre qui compte

| Grandeur | Valeur mesurée |
|---|---|
| RAM machine | 16 Gio |
| **RAM allouée à Docker Desktop** | **7,75 Gio** — la moitié |
| Occupée par le projet tiers `observatoire-ecom-studio` | **~1,93 Gio**, 5 conteneurs, dont 1,77 Gio pour son worker |
| **Marge réelle pour les 8 services du LOT 1** | **~5,8 Gio**, ~7,7 Gio si le projet tiers est arrêté |

`ROAD-RSK-027` a été réécrit sur ces mesures. **Vérifie l'état du projet tiers avant `T2`, et
demande à Jonathan avant de l'arrêter — il ne nous appartient pas.**

## 5.9 Issues et milestone du LOT 1

| Issue | Story | Prio | Sous-étape |
|---|---|:--:|---|
| [#1](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/1) | **EPIC** `MVP-L01` | — | — |
| [#2](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/2) | `MVP-L01-US001` monorepo | `P0` | **`T1`** |
| [#3](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/3) | `MVP-L01-US002` stack Docker | `P0` | `T2`, `T5`, `T8` |
| [#4](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/4) | `MVP-L01-US003` healthchecks | `P0` | `T3`, `T5` |
| [#5](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/5) | `MVP-L01-US004` logs JSON | `P0` | `T4` |
| [#6](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/6) | `MVP-L01-US005` CI | `P0` | `T6` |
| [#7](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/7) | `MVP-L01-US006` images GHCR | `P0` | `T7` |
| [#8](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/8) | `MVP-L01-US007` design system | **`P1`** | `T10` |
| [#9](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/9) | `MVP-L01-US008` documentation | `P0` | `T9` |

Milestone : **`G1`**. Étiquettes disponibles : `mvp` `v1` `v2` · `p0` `p1` `p2` · `frontend`
`backend` `data` `infra` `security` `a11y` `content`.

## 5.10 Circuit Git

```text
feat/l01-us001-squelette-monorepo ──► develop ──► main ──► tag v0.1.0
```

Nommage : `<type>/l<NN>-us<NNN>-<resume-kebab-case>`. Types : `feat` `fix` `docs` `chore`
`refactor` `test` `perf` `ci` `build` `revert`.

Fusion **branche → `develop` : squash**. **`develop` → `main` : merge commit**, à la validation
de la porte.

```bash
git switch develop && git pull
git switch -c feat/l01-us001-squelette-monorepo
```

---

# 6. La méthode de travail

## 6.1 La boucle

```text
1. Annoncer          ce qui va être modifié, pourquoi, les risques, le point de retour
2. Exécuter          une seule sous-étape, jamais deux
3. Contrôler         en lecture seule, après modification
4. Rapporter         au format imposé, avec les sorties réelles
5. Attendre          la validation explicite de Jonathan
6. Fusionner         une pull request par sous-étape, squash
```

**Ne jamais enchaîner deux sous-étapes sans validation.** Jonathan valide par un message court.

## 6.2 Le format de rapport imposé

```text
État du lot
Sous-étape en cours
Travail réalisé
Contrôles exécutés
Résultats
Décisions ajoutées ou modifiées
Risques et écarts
Questions ouvertes
Validation demandée à Jonathan
```

Termine par la **commande de fusion** et la **commande de retour arrière**. Depuis que les
branches sont protégées, le retour arrière d'une sous-étape publiée n'est plus
`git reset --hard` mais :

```bash
~/.local/bin/gh pr close <n> --delete-branch
```

**Vérifie toujours `git status -sb` avant d'annoncer un point de retour** : `reset --hard` ne
vaut que pour un commit non poussé.

## 6.3 Les questions à Jonathan

Utilise **l'outil de question** plutôt que du texte libre : 2 à 4 options, la recommandée en
premier avec la mention « (Recommandé) », et une description qui explique la **conséquence** de
chaque option.

Ne l'interroge que si la réponse change réellement le travail. S'il demande qu'un point **reste
en suspens**, ne force pas de choix : **adapte la conception** pour que le point reste ouvert
sans bloquer. C'est ce qui a produit `DEC-434`.

## 6.4 Générer plutôt que transcrire

Pour tout volume — 44 tâches, 68 codes d'erreur, 8 issues — **génère depuis la source par
script** au lieu de recopier. Les 8 issues du LOT 1 ont été produites ainsi : fidélité 8/8 au
mot près, apostrophes typographiques préservées, zéro erreur de recopie.

## 6.5 Ne jamais inventer ce qui n'est pas décidé

Le catalogue des métiers n'est énuméré nulle part → « à établir avec l'ESM ».
`IMPORT_SOURCE_RETENTION_DAYS` reste en `CHANGE_ME` car sa valeur relève de `QO-100`.
**Une hypothèse déguisée en décision est pire qu'une case vide.**

---

# 7. Les erreurs à ne plus commettre

Dix défauts ont été détectés à ce jour : **sept au LOT 0**
([`controles-sortie-lot-0.md`](docs/operations/controles-sortie-lot-0.md) §7) et **trois en `T0`**
([`compte-rendu-t0-lot-1.md`](docs/operations/compte-rendu-t0-lot-1.md) §3.2).

**Cinq d'entre eux étaient des contrôles faux, pas des livrables faux.** C'est le cas le plus
dangereux : le livrable est bon, mais on croit l'avoir prouvé alors qu'on n'a rien prouvé.

## 7.1 La règle qui résume tout

> **Un contrôle qui ne peut pas échouer ne prouve rien. Un contrôle dont on ne lit pas le code
> de sortie ne prouve rien non plus.**

Tout contrôle de sécurité s'accompagne d'un **témoin positif** — un motif dont tu sais qu'il
existe — **et d'un témoin négatif**. Si le témoin positif ne remonte rien, c'est ton contrôle
qui est cassé, pas le dépôt qui est propre.

## 7.2 `zsh` ne découpe pas les variables en mots

Le piège le plus dangereux du projet. En `zsh`, `$VAR` n'est pas soumis au découpage en mots.

```bash
COMMITS=$(git rev-list --all)
git grep -i 'motif' $COMMITS      # ← UN seul argument : ne marche pas
```

Combiné à `2>/dev/null`, l'erreur était invisible et le contrôle « aucun secret dans
l'historique » affichait OK **sans rien vérifier**.

```bash
for c in $(git rev-list --all); do git grep -i 'motif' "$c"; done   # ← correct
```

Utilise une boucle explicite, un tableau, ou `${=VAR}`. Pour itérer sur des données
structurées, préfère `while IFS='|' read -r a b c; do … done <<'EOF'`.

## 7.3 Le code de sortie d'un pipeline est celui du dernier maillon

**Je suis tombé dedans en `T0`, sur le contrôle de protection de branche** — défaut `T0-1` :

```bash
if git push origin main | sed 's/^/  /'; then echo "ACCEPTE"; fi   # ← teste sed, jamais git
```

Le serveur avait renvoyé `GH006` et refusé le push ; mon contrôle affichait « ACCEPTÉ ».
**Capture la sortie dans une variable et teste le code de sortie directement :**

```bash
sortie=$(git push origin main 2>&1); code=$?
[ $code -ne 0 ] && echo "refuse"
```

En `zsh`, `${pipestatus[1]}` donne le code du premier maillon.

## 7.4 Vérifier le texte, pas seulement les identifiants

En S4 du LOT 0, les contrôles comptaient les identifiants : 99/99, tout au vert. En étendant au
**texte**, **16 libellés sur 89** différaient de la source par un caractère : apostrophe droite
`'` au lieu de l'apostrophe typographique **`’` (U+2019)**.

Les documents sources emploient systématiquement `’`. Si tu recopies, **vérifie avec `grep -F`**
contre la source.

## 7.5 Vérifier ce que la documentation affirme

Trois affirmations de la documentation se sont révélées fausses à la prise en charge :

- « les 11 commits sont locaux » → ils étaient **poussés** depuis 74 secondes (`ECART-016`) ;
- la fiche attribuait `DB_AUTO_CREATE` au cahier → le cahier **ne contient pas** cette chaîne ;
- la fiche annonçait 7 garde-fous → il y en a **11**, et elle retenait les mauvais.

**Vérifie l'état réel par `git`, `gh` et les mesures, jamais par ce que la doc affirme.**

## 7.6 Le système de fichiers est insensible à la casse

`DOCS` et `docs` désignent le **même** dossier. Tout renommage ne différant que par la casse
exige deux temps : `mv DOCS __tmp__ && mv __tmp__ docs`.

## 7.7 Outils macOS différents de GNU

| N'existe pas | Utiliser |
|---|---|
| `cat -A` | `cat -vet` |
| `grep -P` | `grep -E` ou Python |
| `timeout` | rien d'équivalent, ou `gtimeout` si installé |

`grep` est ici **`ugrep`**, qui échoue avec « exceeds complexity limits » sur des motifs comme
`.{0,60}(a|b|c).{0,60}`. **Passe par Python** pour les extractions non triviales.

## 7.8 Ne jamais `grep` le prototype en entier

`V1.html` fait 2,83 Mo dont **2,64 Mo de Base64**, qui produisent des correspondances fortuites.

```bash
sed -E 's/data:image\/[a-z]+;base64,[A-Za-z0-9+\/=]+/<B64>/g' docs/prototype/V1.html > /tmp/propre.html
```

Le fichier tombe à 194 566 caractères analysables. **Travaille toujours sur la version
dépouillée, hors du dépôt.**

## 7.9 Attention au BOM

Un BOM `EF BB BF` s'était glissé en tête de `.env.example`. Dans un `.env`, cela corrompt la
première entrée selon l'outil qui lit.

```bash
head -c 3 fichier | od -An -tx1 | tr -d ' \n' | grep -q '^efbbbf' && echo "BOM present"
```

## 7.10 Ne jamais manipuler les identifiants de Jonathan

`git` et `gh` savent s'authentifier seuls. **N'extrais jamais le jeton du trousseau macOS**
pour appeler une API, et **n'entre jamais d'identifiants à sa place** — `gh auth login`, mot de
passe `sudo`, approbation de certificat dans le trousseau sont ses actions, pas les tiennes.

---

# 8. Ce qui reste ouvert

## 8.1 Écarts ouverts — 6 sur 16

| ID | Objet | Échéance |
|---|---|---|
| `ECART-005` | Schéma CSV initial livré ; le définitif relève de `QO-096` | LOT 9 |
| **`ECART-006`** | **`.env.example` en v0.1, à porter en v1.0** | **LOT 1** |
| `ECART-012` | `intercontrat` imposé à une direction générale : cohérent techniquement, trompeur à l'écran | LOT 2, avant LOT 5 |
| `ECART-013` | Les 5 tâches communes du prototype ont des identifiants différents. **Reprendre cette numérotation ferait échouer `MVP-L07-US007`** | LOT 7 |
| `ECART-014` | Le prototype dit « Représentant de cercle », les documents disent « Booster » | LOT 6 |
| `ECART-015` | Le prototype ne fournit **ni** descriptions de cercles **ni** liens internes | LOT 6 |

`ECART-009` et `ECART-011` sont **acceptés**. `ECART-001` à `004`, `007`, `008`, `010`, `016`
sont **clos**.

## 8.2 Questions ouvertes utiles au LOT 1

30 ouvertes sur 34. Celles qui te concernent :

| ID | Objet | Apport attendu du LOT 1 |
|---|---|---|
| `QO-085` | RAM et disque du Mac M5 | **Mesure en charge** une fois les 8 services démarrés. Éléments déjà versés |
| `QO-084` | PostgreSQL RLS immédiat ou différé | À trancher au LOT 2, la migration initiale peut préparer le terrain |
| `QO-106` | Familles d'étiquettes complémentaires GitHub | Non prescrites, choix de Jonathan |
| `QO-094` | Second référent technique | Conditionne `DEC-429` |

`QO-086`, `QO-107`, `QO-108`, `QO-109` ont été **closes en `T0`**.

## 8.3 Points en attente de décision de Jonathan

- Les **9 étiquettes GitHub par défaut** (`bug`, `enhancement`, `good first issue`…) subsistent.
- Les **104 issues** des LOTS 2 à 14 ne sont pas créées.

## 8.4 Contenus en attente de relecture

Les 29 éléments `CONT-001` à `CONT-029` sont au statut **`à relire`**. Propriétaires : Léa
(produit), Tess (éditorial), Diane (parcours). **Aucun n'est publiable en l'état.**

---

# 9. Le LOT 1 — par où commencer

## 9.1 Objectif, repris littéralement de la roadmap

> « Obtenir une plateforme vide mais exécutable localement sur le MacBook Pro M5, avec une
> chaîne de qualité opérationnelle. »

## 9.2 Les 11 sous-étapes restantes

`T0` est faite. Reste `T1` à `T11`, une par pull request.

| Sous-étape | Objet | Story |
|---|---|---|
| **`T1`** | **Squelette du monorepo, outillage, versions épinglées** | `US001` |
| `T2` | Compose développement : les 8 services démarrent et sont sains | `US002` |
| `T3` | API FastAPI minimale, 3 healthchecks, migration Alembic initiale | `US003` |
| `T4` | Journalisation JSON corrélée, API et worker | `US004` |
| `T5` | Frontend Vite : page de statut consommant les healthchecks | `US002`, `US003` |
| `T6` | CI GitHub Actions : 8 contrôles, dont **3 échecs volontaires prouvés** | `US005` |
| `T7` | Images multiarchitecture et publication GHCR privé | `US006` |
| `T8` | Environnement de recette isolé | `US002` |
| `T9` | Documentation d'exploitation locale | `US008` |
| `T10` | Design system minimal et contrat API partagé | `US007` (`P1`) |
| `T11` | Contrôles de sortie et préparation de la porte `G1` | — |

**`T8` ne cherche pas la coexistence** de deux stacks : la mémoire ne le permet pas. Il prouve
la **séparation** par démarrages **successifs** — le cahier §22.2 exige des ressources
distinctes, jamais la simultanéité.

## 9.3 Ce que `T1` doit produire

Arborescence de la roadmap, cahier §15.3 :

```text
apps/web  apps/api  apps/worker  packages/ui  packages/contracts  infra  docs
```

Plus : `pnpm-workspace.yaml`, `Makefile`, la configuration Ruff, `mypy`, TypeScript strict, et
les versions épinglées. **Critère de validation :** l'arborescence des 7 répertoires existe, et
lint, formatage et typage s'exécutent **à vide sans erreur**.

Avant tout `pnpm install`, applique `DEC-439` : store `pnpm` hors du dossier synchronisé et
exclusion de `node_modules` d'iCloud. **C'est plus facile avant qu'après.**

## 9.4 Le test le plus important du lot

`T6`. La roadmap exige que « la CI bloque volontairement une erreur de lint, de test et de
secret ». **Il faut prouver l'échec, pas seulement le succès.**

## 9.5 Les 7 critères de sortie de la porte `G1`

| | Critère |
|:--:|---|
| ☐ | Tous les services démarrent sur le Mac M5 |
| ☐ | Les images multiarchitectures sont construites |
| ☐ | **Aucun secret réel n'est présent** |
| ☐ | Une migration Alembic vide ou initiale s'exécute |
| ☐ | Les logs possèdent un identifiant de corrélation |
| ☐ | **La CI bloque volontairement une erreur de lint, de test et de secret** |
| ☐ | Jonathan valide le socle |

À la validation, le tag **`v0.1.0`** est posé sur `main` (`DEC-428`).

## 9.6 Ce que le LOT 1 ne doit pas faire

- créer une table métier, un modèle SQLAlchemy métier ou une migration de contenu — **la seule
  migration est `0001_initial`, extensions PostgreSQL seules** ;
- implémenter une authentification, même partielle, même de test ;
- introduire un mécanisme de contournement de l'authentification ;
- charger la moindre donnée de collaborateur, réelle ou non ;
- exposer publiquement PostgreSQL, Redis, MinIO ou Mailpit ;
- référencer une image par `latest` seul ;
- introduire Kubernetes, une PWA, un fonctionnement hors ligne, Entra ID, Graph, Teams ou MFA ;
- réutiliser une ligne de code du prototype historique.

---

# 10. Cartographie du dépôt

```text
.
├── CLAUDE.md                    ← ce document
├── AGENTS.md                    → lien symbolique vers CLAUDE.md, NON VERSIONNÉ
├── README.md                    ← état d'avancement, règles, structure
├── CONTRIBUTING.md              ← circuit de contribution, Ready et Done
├── .env.example                 ← 74 variables, aucun secret
├── .gitattributes               ← normalisation des fins de ligne, LF
├── .gitignore                   ← barrière : secrets, CSV, médias, volumes
├── .github/                     ← gabarits PR et issues
└── docs/
    ├── README.md                ← INDEX : documents, séquences d'ID, portes, avancement
    ├── product/                 ← cahier, matrice, roadmap, backlog  [IMMUABLES]
    │   └── contenus/            ← inventaire prototype, parcours relevés, exclusions
    ├── architecture/            ← modèle de données  [IMMUABLE]
    │   └── donnees/             ← schéma CSV, codes d'erreur, listes, exemple fictif
    ├── decisions/               ← registre des décisions, registre des écarts
    ├── operations/              ← conventions, registres, secrets, contrôles,
    │                              fiche-lot-1.md, compte-rendu-t0-lot-1.md
    └── prototype/               ← V1.html, NON VERSIONNÉ
```

Le LOT 1 ajoutera `apps/`, `packages/`, `infra/`, `Makefile` et `.github/workflows/`.

---

# 11. Démarrage type d'une session

```bash
export PATH="$HOME/.local/bin:$PATH"
git switch develop && git pull
git log --oneline -5
git status -sb
gh issue list --milestone G1
make icloud-verify        # depuis T1 : iCloud a deja duplique node_modules une fois
```

> **`make icloud-verify` en début de session n'est pas une formalité.** Le 27/07/2026, iCloud
> a produit une copie de conflit `node_modules 2` de 11 066 fichiers et effacé l'attribut
> d'exclusion de l'original, en moins de sept heures et sans aucune action de session. C'est
> ce contrôle qui l'a détecté. Risque résiduel accepté par `DEC-457` ; incident détaillé dans
> [`compte-rendu-t1-lot-1.md`](docs/operations/compte-rendu-t1-lot-1.md) §4 et
> `ROAD-RSK-026`.

1. Lire ce document.
2. Lire [`docs/README.md`](docs/README.md) : quelle porte, quel prochain identifiant.
3. Lire [`fiche-lot-1.md`](docs/operations/fiche-lot-1.md) : la sous-étape en cours.
4. Vérifier l'état réel du dépôt par `git` et `gh`, **pas par ce que la doc affirme**.
5. Exécuter **une** sous-étape, contrôler, rapporter, attendre la validation.

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
- **signaler ses propres erreurs** dès que les contrôles les révèlent, sans les enjoliver — les
  dix défauts sont tous documentés, y compris celui qui rendait un contrôle de sécurité
  inopérant et celui qui affichait « ACCEPTÉ » sur un push refusé ;
- distinguer nettement **ce qui est prouvé** de **ce qui est recommandé** ;
- lui donner à chaque fois la commande de fusion **et** celle de retour arrière ;
- ne rien pousser vers l'extérieur sans son accord.

Le projet a une exigence de traçabilité inhabituellement élevée : 117 décisions pour un lot
documentaire et une sous-étape d'arbitrage. Ce n'est pas de la bureaucratie, c'est ce qui
permettra, au LOT 9, de justifier chaque ligne rejetée d'un import de données personnelles
réelles. **Tiens les registres à jour dans la même pull request que le travail — jamais après.**
