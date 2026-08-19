# Passation — agent chef de projet technique

**Projet :** eXalt Onboarding Digital
**Rédigé le :** 28 juillet 2026, à la sortie de la sous-étape `T4`
**Mis à jour le :** 12 août 2026, à la sortie de la sous-étape **`T11`** — §1, §4, §5, §7, §8,
§9, §10 et §11 rectifiés **sur mesures**. **Cinq affirmations de ce document se sont révélées
fausses : voir §9.0.**
**Destinataire :** l'agent qui prend le relais **APRÈS la validation de la porte `G1`**, pour le LOT 2
**Interlocuteur unique :** Jonathan — technique et exploitation. Léa décide du produit.

Ce document dit **où en est le projet**, **ce qui a été fait et comment**, **les constantes à
connaître**, **les erreurs à ne plus commettre**, et **par où commencer**. Lis-le en entier
avant d'agir. Il remplace la passation d'ouverture du LOT 1.

---

# 1. En un coup d'œil

| | |
|---|---|
| Lots terminés | **LOT 0** verrouillé le 27/07/2026 (`DEC-438`), porte **`G0`** franchie · **LOT 1** verrouillé le 12/08/2026, porte **`G1`** franchie, tag **`v0.1.0`** |
| **Lot en cours** | **LOT 2 — Socle de données et isolation multi-entités**, ouvert le 18/08/2026 (`DEC-496`), porte `G2`, tag `v0.2.0`. Plan : [`fiche-lot-2.md`](docs/operations/fiche-lot-2.md), **12 sous-étapes** |
| Sous-étapes faites | **LOT 2 : `T1` à `T6` faites**, `T7` à `T12` non entamées · *LOT 1 : `T0` hors lot, `T1`→`T11`, complet* |
| **Prochaine action** | **`T7` — cercles, bureaux et appartenance aux cercles**, issues `#39` et `#41`, qu'elle **clôt toutes deux**. Trois index partiels du §25.1, dont un sur **deux** conditions. Voir §10 du compte rendu de `T6` |
| Stories `Done` | **LOT 2 : `US002`.** `US001` attend `T7`, `US003` attend `T6`, `US008` se clôt en `T12` · *LOT 1 : les huit* |
| Stories restantes | **LOT 2 : les huit**, `MVP-L02-US001` à `US008`, epic `#38`, issues `#39` à `#46` |
| Dépôt distant | `Jonathan2433/ONBOARDING_DIGITAL` — **privé, prouvé** par `gh api … --jq .private` → `true` |
| Branches | `main` et `develop`, **les deux protégées, et la CI y est BLOQUANTE**. Compte de commits : `git rev-list --left-right --count main...develop` — **ce document ne peut pas le tenir**, voir la note ci-dessous |
| Volumétrie | **fichiers suivis, Markdown, Python : `git ls-files \| sed 's/.*\\.//' \| sort \| uniq -c \| sort -rn`.** Aucun de ces comptes n'est affirmé ici — voir la note ci-dessous, `ECART-022` en a corrigé un de plus |
| Tests | **394** : **278 pytest** et **116 Vitest**. C'était 260 à la sortie du LOT 1 |
| Intégration continue | **11 contrôles** du cahier §23.1 sur chaque pull request, ~2 min 20. **Bloquante, prouvé trois fois** |
| **Images** | **3 images multiarchitecture** publiées dans GHCR privé. **Les DEUX architectures sont désormais NATIVES sur le même artefact publié** — `amd64` en CI depuis `T7`, `arm64` sur ce Mac depuis `T8`. `web` : **84,9 Mo** |
| Registres | **178 décisions** · **30 écarts** (5 ouverts, dont `ECART-012` **instruit**) · **41 questions** (34 ouvertes) · 34 risques |

> **Les nombres ci-dessus sont dérivés de la source, pas recopiés.** Quatre l'avaient été et
> étaient faux : `ECART-021` les corrige. Recompte-les avant de les réutiliser.
>
> **Deux nombres ont été retirés de ce tableau plutôt que corrigés : le compte de commits et le
> compte de lignes.** Tous deux ont été faux plusieurs fois, pour une raison structurelle et non
> par négligence — un document qui est lui-même commité se décrit dans son état **d'avant son
> propre commit**, et toute correction qu'on y apporte change le compte qu'il annonce. Un nombre
> qu'on ne peut pas tenir, on ne l'affirme pas : on donne la commande qui le calcule.
>
> **La façon dont ces nombres ont été traités est elle-même une leçon, et elle a fallu trois
> passes.** `T6` a d'abord retiré le seul compte de commits, et le compte de lignes est devenu faux
> au commit suivant — celui qui retirait l'autre : **une instance corrigée au lieu de la classe**.
> Puis `T7` a trouvé que le compte de fichiers YAML était faux lui aussi — « 4 YAML » là où il y en
> avait **6**, l'extension `.yaml` n'ayant pas été comptée — alors que ce document affirmait
> justement que le compte de fichiers, lui, était tenable. **La classe était encore plus large que
> `T6` ne l'avait cru.** Tous les comptes de fichiers sont donc retirés à leur tour, et remplacés
> par la commande qui les dérive. `ECART-022` consigne les cinq constats.
>
> Les autres grandeurs de ce tableau sont vérifiées exactes à la sortie de `T7`, et `make
> docs-check` couvre les séquences d'identifiants et les empreintes — mais **pas** les nombres
> cités en prose, qui restent à la charge du lecteur. **Ne rétablis aucun compte de fichiers sans
> poser d'abord le contrôle qui le dérive.**

**La plateforme démarre, répond, s'affiche, elle est empaquetée, et elle existe désormais en DEUX
environnements isolés.** `make up` lève les huit services du développement, `make up-recette` lève
les huit de la recette **sur les images publiées**, et les **sept** séparations du cahier §22.2 sont
prouvées sur l'état réel — 57 contrôles, 0 échec. L'API sert ses trois endpoints de santé à travers
Caddy en HTTPS dans les deux, la migration initiale s'applique dans les deux, les journaux sortent en
JSON corrélé, et la page de statut est servie sur `app.onboarding.localhost` et
`app.recette.onboarding.localhost`. Il n'existe **aucun écran métier** ni **aucune donnée métier**.

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
| **Que fait-on au LOT 2 ?** | **`docs/operations/fiche-lot-2.md`** — 12 sous-étapes, **`T1` barrée**. Découpage validé le 18/08/2026 |
| **Comment a-t-on fait `T1` à `T6` du LOT 2 ?** | **`docs/operations/compte-rendu-t{1,…,6}-lot-2.md`** — 22 défauts, dont **18 dans mon propre travail** |
| Que faisait-on au LOT 1 ? | `docs/operations/fiche-lot-1.md` — 12 sous-étapes, **les 12 barrées** |
| **Comment a-t-on fait `T1` à `T11` ?** | **`docs/operations/compte-rendu-t{0,…,11}-lot-1.md`** |
| **Que valide Jonathan à la porte ?** | **`docs/operations/checklist-validation-G1.md`** — 33 contrôles, et une démonstration guidée |
| **Comment EXPLOITE-t-on la plateforme ?** | **`docs/operations/exploitation-locale.md`** — toutes ses commandes ont été exécutées |
| Qu'a-t-on décidé depuis le début ? | `docs/decisions/registre-decisions.md` — **161 décisions**, et `make docs-check` en **dérive les totaux** |
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

## 4.7 `T5` — page de statut

La page est servie sur `app.onboarding.localhost`. Elle affiche les **trois** dépendances que
l'API sonde, la version du build, et **dit sur elle-même** que le worker, Mailpit et Caddy ne
sont pas sondés — plutôt que de laisser croire à un tableau de bord des huit services.
**Cinq états** et non trois : chargement, nominal, **dégradé**, erreur, hors connexion.

**Comment :** un 503 de `/health/ready` porte **la même forme JSON** qu'un 200. Le lire comme une
erreur réseau jetterait le diagnostic au moment où il devient utile — le client accepte donc 200
**et** 503 pour `ready`, 200 seul pour `version`. Le critère « affiche l'état réel » a été éprouvé
en **arrêtant réellement Redis** : 503, `redis indisponible`, motif `ConnectionError`.

**Et un contrôle qui n'existait pas :** `eslint-plugin-jsx-a11y`, motif déterminant de `DEC-451`,
n'avait jamais eu un seul fichier JSX à examiner — il n'existait aucun `.tsx` dans ce dépôt.
Éprouvé par témoin négatif, il examine et il **sait échouer**.

## 4.8 `T6` — intégration continue

**Le test le plus important du lot, et il exigeait de prouver l'échec.** Les 11 contrôles du
cahier §23.1 tournent sur chaque pull request en **~2 min 20**, découpés en deux tâches — la
qualité rend son verdict en une minute sans attendre Docker — et une **porte** unique qui conclut.

**Comment :** trois défauts introduits **un par un** dans une pull request jetable, chacun dans sa
propre poussée pour que l'échec soit attribuable. Lint, test, secret : trois exécutions rouges,
`mergeStateStatus: BLOCKED` dans les trois cas. Témoin positif indispensable : la même porte
laisse passer la branche de `T6`, `MERGEABLE` / `CLEAN`.

> **Piège de vocabulaire GitHub.** Le champ `mergeable` ne parle que des conflits et vaut
> `MERGEABLE` même sur une pull request refusée. C'est **`mergeStateStatus`** qui fait foi.

**Et deux défauts dormants réveillés** : le `Makefile` n'avait jamais tourné ailleurs que sur
macOS avec des volumes déjà peuplés. `make env` employait la forme BSD de `sed`, et `make up`
n'avait **jamais** fonctionné sur une machine propre. Voir §7.16.

## 4.9 `T7` — images multiarchitecture et publication GHCR

**Le dernier critère technique de la porte `G1`, et il exigeait de LANCER, pas de construire.** Les
trois images sont construites pour `linux/amd64` **et** `linux/arm64` en une **liste de manifestes
unique**, publiées dans GHCR privé, et **lancées sur les deux architectures** — 39 contrôles
fonctionnels, 0 échec.

**Comment :** en lisant, **dans** chaque conteneur, une valeur que l'autre architecture ne pourrait
pas produire — `uname -m` à `x86_64` ou `aarch64`. Un contrôle qui se contenterait de « le
conteneur a démarré » donnerait la même observation sur les deux, et ne prouverait rien.

**Deux risques clos d'un même geste.** `Dockerfile` `web` à **deux cibles nommées** (`DEC-479`) :
`developpement` garde le serveur Vite, `execution` sert l'artefact de `vite build` par Caddy. La
cible publiée passe de **1,02 Gio à 84,9 Mo**, et ni Node, ni Vite, ni ESLint n'y subsistent.
`ROAD-RSK-030` et `ROAD-RSK-031` sont clos.

**Et un gisement que le risque ne visait pas :** `docker history` a montré qu'un `RUN chown -R`
pesait **230 Mio** dans `web` et **143 Mio** dans `api` et `worker`. Une couche d'image
réenregistre le fichier **entier** dès qu'une métadonnée change : elle duplique l'arborescence dont
elle ne modifie que le propriétaire. `api` et `worker` perdent 29 % à ce seul titre.

**Trivy : mesuré avant d'être réglé.** `python:3.12-slim` porte **23 avis `HIGH`/`CRITICAL` dont
aucun n'a de correctif**. Bloquer sur `HIGH` aurait rendu la chaîne définitivement rouge sans
remède. La porte bloque donc sur `CRITICAL` **corrigeable** seulement, et rapporte le reste
visiblement (`DEC-482`). Second constat de la mesure : **nos couches n'ajoutent aucune
vulnérabilité**, les totaux sont exactement ceux des images de base.

> **Une réserve à connaître, et elle est dans la fiche §3.1.** `arm64` n'est prouvé **nativement**
> que sur une liste de manifestes construite localement, pas sur l'image publiée — le jeton `gh`
> n'a pas `read:packages`, et Jonathan a arbitré de ne pas l'ajouter. Sur l'image publiée, `amd64`
> est natif et `arm64` est **émulé**. Les deux empreintes sont nommées au compte rendu.

## 4.10 `T8` — environnement de recette isolé, sur les images publiées

**Les SEPT séparations du cahier §22.2, et la fiche n'en énumérait que six.** Le critère écrit dans
la fiche omettait « projet Docker distinct » — celle qui **produit** les volumes et le réseau
distincts, Compose les préfixant du nom de projet. C'est `ECART-023`, exactement la classe de
`ECART-018`. **Compte-les sur le cahier, jamais sur une fiche.**

**Comment :** chaque séparation est lue sur l'**état réel**, jamais sur un fichier `.env` — une
variable déclarée n'est pas une base servie, et `T7-8` l'avait montré. Deux séparations exigeaient
mieux qu'une comparaison de noms : la base et le bucket de l'autre environnement doivent être
**ABSENTS**, parce que deux noms distincts dans deux services qui partageraient un volume donneraient
la même observation. **57 contrôles, 0 échec, et le vérificateur compte les séparations examinées.**

**La recette exécute l'artefact PUBLIÉ, épinglé par empreinte** (`DEC-486`). Le fichier de base
déclare `build:` : sans garde-fou, une image absente ferait construire localement et la recette
exercerait un autre artefact **en paraissant saine**. `--no-build` rend l'échec bruyant — éprouvé
avant l'authentification : `unauthorized`, **0 conteneur démarré, 0 construction de repli**.

**La réserve `arm64` de la fiche §3.1 est LEVÉE.** Jonathan a élargi son jeton à `read:packages`
(`DEC-483`, qui renverse l'arbitrage de `T7`), la recette tire l'image publiée sur ce Mac, et
`uname -m` y rend **`aarch64` 3 fois sur 3**. Les deux architectures sont désormais natives **sur le
même artefact**.

**Et un constat que le critère ne visait pas.** Mon contrôle d'isolement réseau a échoué sur un
livrable conforme. Diagnostic avant correction : **publier un port perce l'isolement inter-réseaux
de Docker** — mesuré sur un **même conteneur**, `mailpit:8025` publié est joignable depuis la
recette, `mailpit:1025` non publié ne l'est pas. La règle `ACCEPT` d'un port publié précède les
règles `DOCKER-ISOLATION`. **Ce qui protège est la cinquième séparation, les secrets** : avec le mot
de passe de la recette, la base de dev **refuse**. `ROAD-RSK-034`, et vois §7.20.

---

## 4.11 `T9` — documentation d'exploitation locale

**Le critère disait « les procédures FONCTIONNENT depuis une machine propre ». Le mot qui commande
tout est « fonctionnent ».** Les 13 commandes `make` du document ont donc été exécutées une par une,
et les sorties citées sont réelles.

**Le démarrage à froid est véritable, et il l'est plus qu'en `T6` et `T8`.** Ces deux sous-étapes
avaient supprimé **un** volume. `T9` a détruit **tout** ce que la recette possédait — 6 volumes,
conteneurs, réseau — **et retiré les 3 images du cache local**. Une machine qui n'aurait jamais vu ce
projet est dans cet état exact. Remontée : **34 secondes**, 8/8 sains.

**Le développement n'a pas été touché**, sur arbitrage de Jonathan : détruire `dev` aurait supprimé
`caddy-data`, donc l'autorité approuvée dans son trousseau, et lui aurait coûté une réapprobation.

**Deux faits d'exploitation que seule l'exécution révèle :**

- **après un démarrage à froid, la migration n'est PAS appliquée.** Et `make migrate-status` sur une
  base non migrée affiche **rien** en sortant en **0** : une sortie vide ne veut pas dire « tout va
  bien », elle veut dire « rien n'est appliqué » ;
- **les 14 publications et les 12 volumes sont DÉRIVÉS** par commande dans le document, jamais
  recopiés. Toute liste recopiée est un `ECART-021` en puissance.

**Et trois cibles n'avaient jamais tourné.** `make destroy` — destructive et interactive — n'avait
jamais été lancée depuis son paramétrage en `T8` ; `make caddy-recreate` jamais sur la recette ; et
`make web-check` avait son origine en dur sur le développement. **Les trois ont été éprouvées, et
deux portaient un défaut.** Voir §7.21.

---

## 4.12 `T10` — design system et contrat API partagé

**Le critère disait « sans dépendance visuelle arbitraire », et c'était le seul endroit du lot où la
règle §6.5 — ne jamais inventer ce qui n'est pas décidé — était en jeu aussi directement.**

**Mesure d'abord :** le cahier §13.1 exige « la charte graphique » et « la police officielle » ;
**aucune des deux n'est dans le corpus**, aucun fichier de design n'est versionné, et le cahier ne
contient **aucune** couleur hexadécimale. Zéro occurrence.

**Le prototype, lui, NOMME sa palette** — `EXALT_BLUE = #5853FF`, `EXALT_DARK_BLUE = #2F2F9B`,
`EXALT_PINK = #FF2C9B`, `EXALT_YELLOW = #FFDA3E` — et cela corrobore littéralement le « dégradés
bleu, rose et violet » du §13.2. Deux sources concordantes, donc pas une invention. Arbitrage de
Jonathan sur quatre options.

**Et la mesure a CORRIGÉ le prototype, ce qui est le résultat le plus utile.** Le jaune rend **1,37**
de contraste sur fond clair, le bleu foncé **1,69** sur fond sombre : les couleurs de marque sont des
**surfaces** portant un texte apparié mesuré, pas des couleurs de texte libres. Le prototype ne
prévoyait du texte foncé que pour le jaune ; **le rose et le vert le réclament aussi**. Le reprendre
tel quel aurait reconduit deux défauts d'accessibilité.

**Le contrat : le sens de vérification est INVERSÉ, et c'est mesuré.** `components.schemas` du schéma
OpenAPI servi est **vide** — les routes rendent des dictionnaires sans modèle. Générer aurait produit
des types `unknown`, donc l'illusion d'un contrat typé. Un **manifeste JSON unique** déclare donc le
contrat, lu par TypeScript **et** par un contrôle Python qui vérifie que le schéma le respecte.

**Un constat produit par ce contrôle dès sa première exécution :** l'API ne documentait **pas** le
503 de `/health/ready`, que le frontend traite comme un état exploitable depuis `T5`.

**Et un événement extérieur qui ferme un risque.** `make audit` est passé de 1 avis toléré à 4 avis
hauts **sans que `T10` y soit pour rien** — vérifié sur un arbre créé avant `T10`, qui rend les mêmes
4. Ce sont des avis nouvellement publiés. Les deux sont corrigeables par montée de correctif, et
`brace-expansion@1.1.18` corrige au passage l'avis que `T6` avait mesuré **sans correctif
possible**. L'audit passe à **zéro avis, zéro tolérance** : `ROAD-RSK-032` est clos, `DEC-493`. Vois
§7.22.

---

## 4.13 Les décisions qui contraignent ton travail quotidien

Les 178 sont dans `docs/decisions/registre-decisions.md`. Celles que tu appliqueras :

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
| `DEC-470` | **Page et API sur une SEULE origine**, mandatée par Caddy. Ni CORS, ni proxy Vite |
| `DEC-471` | Testing Library sur **`jsdom`**. `restoreMocks` et `unstubGlobals` actifs |
| `DEC-472` | Le `Caddyfile` est monté **par son répertoire**, et `make up` **recharge** Caddy |
| `DEC-473` | **`.dockerignore`** : `node_modules`, `.venv`, caches, `.git`, `docs/prototype`, `.env` |
| `DEC-474` | Audit : **une seule tolérance nommée**, `GHSA-mh99-v99m-4gvg`. Tout autre avis bloque |
| `DEC-475` | Workflow en **2 tâches + 1 porte**. Actions épinglées **par empreinte de commit** |
| `DEC-476` | **CI obligatoire sur `develop` ET `main`**, contexte unique, `strict` actif |
| `DEC-477` | **`make up` en deux temps** : bucket MinIO créé AVANT que l'API doive être saine |
| `DEC-478` | **Multiarchitecture sur `develop` ET sur les tags.** Le cahier §23.2 et §23.3 divergeaient |
| `DEC-479` | Image `web` à **2 cibles nommées**, socle d'exécution **Caddy**, **port 5173 conservé**. Chaque surcouche **nomme sa cible**, `make images-check` échoue sinon. `chown -R` supprimé des 3 images |
| `DEC-480` | **Version et révision gravées** dans l'image par `ARG`→`ENV`, + **4 étiquettes OCI**. Compose les transmet à `api` **et** `worker` |
| `DEC-481` | Étiquettes : `sha-<empreinte>`, `develop`, version exacte. **Aucun `latest` publié** — plus strict que les conventions §4.1 |
| `DEC-482` | **Trivy bloque sur `CRITICAL` corrigeable seulement**, et rapporte le reste visiblement |

## 4.14 Les séquences d'identifiants — à respecter absolument

Un identifiant n'est **jamais** réutilisé, **jamais** renuméroté, et un trou n'est **jamais**
comblé.

| Séquence | Étendue | Prochain libre |
|---|---|---|
| `DEC-nnn` | `001`–`417` **réservés**, `418`–`510` en usage | **`DEC-511`** |
| `ECART-nnn` | `001`–`030` | **`ECART-031`** |
| `QO-nnn` | `072`–`117`, **5 trous** | **`QO-118`** |
| `ROAD-RSK-nnn` | `001`–`034` | **`ROAD-RSK-035`** |
| `DEP-nnn` | `001`–`017` | **`DEP-018`** |
| `CONT-nnn` | `001`–`029` | **`CONT-030`** |

Trous jamais comblés : `QO-075`, `QO-079`, `QO-080`, `QO-082`, `QO-090` (`ECART-011`).
**L'index à jour est dans [`docs/README.md`](docs/README.md) §4. Consulte-le avant de créer un
identifiant — et `make docs-check` échoue désormais si un marqueur ne correspond pas au maximum
réellement en usage. C'est ce contrôle qui aurait attrapé `ECART-021`.**

---

# 5. Constantes et variables à connaître

## 5.1 Outillage de la machine

| Élément | Valeur | Remarque |
|---|---|---|
| `gh` | **`~/.local/bin/gh`**, 2.96.0 | **Pas dans le `PATH`.** `export PATH="$HOME/.local/bin:$PATH"` |
| `uv` | **`~/.local/bin/uv`**, **0.11.32** | Posé en `T1`, archive officielle, **empreinte SHA-256 vérifiée** |
| Homebrew | `/opt/homebrew`, **inutilisable** | Appartient à `admin`. `test -w` échoue sur `bin` **et** `Cellar` |
| **Droits d'administration** | **AUCUN** | Mesuré le 29/07/2026 : `id -Gn` → `staff everyone localcounts…`, **pas de groupe `admin`**, et `sudo` répond « is not in the sudoers file ». Vois ci-dessous |
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
| db | `postgres:17.7@sha256:2006493727bd…` — **Debian, pas Alpine** : musl gère mal les locales. **Depuis `T1` du LOT 2, `POSTGRES_INITDB_ARGS` impose ICU `fr-FR`** (`DEC-497`) |
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

## 5.3 Les 52 cibles du `Makefile`, et le paramètre qui les commande

```text
Environnement   tools versions tree icloud-exclude icloud-verify install
Qualité         lint format format-check typecheck test test-unit test-integration check
                docs-check audit
Stack           env env-check up down destroy ps logs health ports minio-bucket
                stack-check persistence-test caddy-reload caddy-recreate
API             migrate migrate-status api-check alembic-check
                code-refresh code-check                           ← LOT 2, T1
Frontend        web-check test-frontend
Images          images-check images-build images-inspect images-verify images-push
                images-pin                                            ← T8
Recette (T8)    separations-check up-recette down-recette
                stack-check-recette recette-check
Nettoyage       clean clean-deps
Aide            help
```

> **DEPUIS `T8`, LES 15 CIBLES DE STACK SONT PARAMÉTRÉES PAR `ENVIRONNEMENT`**, dont `dev` est le
> défaut. `make up` reste `make up` ; `make up ENVIRONNEMENT=recette` lève la recette, et
> `make up-recette` en est l'alias. Les alias **délèguent** et ne portent aucune logique propre :
> deux copies d'une même recette divergent en silence, c'est `ECART-022` et `DEC-466`.
>
> **Un nom d'environnement fautif échoue à la LECTURE du `Makefile`**, avant toute action, et la
> liste des noms valides est **dérivée du disque** : `ENVIRONNEMENT=recete` répond
> « Environnements disponibles : dev recette ».
>
> `.env` sert le développement, `.env.recette` la recette — **déjà couvert par `.env.*` dans
> `.gitignore`, vérifié par `git check-ignore`**. Le modèle reste **unique**, `.env.example`, plus un
> **calque de différences versionné** par environnement : un second modèle de 79 variables
> divergerait.
>
> **`make separations-check` exige que les DEUX stacks tournent.** C'est une exception bornée à
> `DEC-440`, motivée : l'épreuve d'isolement réseau serait sans valeur si la cible était arrêtée.

`make check` = qualité complète. `make stack-check` = santé des 8 services + ports.
`make web-check` = la page vue **comme un navigateur la voit**, à travers Caddy en HTTPS.
`make caddy-reload` est appelée par `make up` : **Caddy ne surveille pas son fichier**, et sans
rechargement il sert une configuration périmée en paraissant sain (`DEC-472`, défaut `T5-2`).
`make docs-check` recalcule les 5 empreintes SHA-256 des documents immuables et **échoue si un
marqueur d'identifiant libre ne correspond pas au maximum en usage**. `make audit` tolère **un**
avis nommé, `DEC-474`. **`make help` est la source de vérité**, pas cette liste.

**Les quatre cibles d'images, et laquelle a besoin de Docker.** `images-check` est **statique** :
elle n'ouvre aucune connexion au démon, tourne dans la tâche « qualité » de la CI, et est incluse
dans `make check`. `images-build` construit les 3 images pour les 2 architectures **en local**,
`--load`, puis appelle `images-inspect` — manifestes, utilisateur non privilégié, étiquettes OCI,
plafonds de taille. `images-verify` **lance** les conteneurs. `images-push` publie, et n'est appelée
que par le workflow. **`env-check` compare `.env` à `.env.example`** et nomme les variables
manquantes : elle existe parce que `make env` est idempotent et ne réconcilie **rien** — trois
variables manquaient depuis `T3` et `T4` (`ECART-022`).

**`make caddy-recreate` est le remède au piège du §7.17.** Elle recrée le seul conteneur Caddy pour
lui faire re-résoudre son montage lié.

## 5.4 Variables de `.env.example` — **v1.2**, `ECART-006` et `ECART-022` clos

**79 variables, 79 noms distincts, aucun secret.** `T8` a ajouté `CADDY_SITE_APP` et `CADDY_SITE_API`. **7** valent `CHANGE_ME` (`ECART-019` : la chaîne
apparaît 9 fois, mais deux occurrences sont des commentaires — compte le motif
`^[A-Z_][A-Z0-9_]*=CHANGE_ME`).

> **`ECART-022` : le fichier annonçait 78 variables et déclarait `APP_REVISION` DEUX FOIS**, en
> blocs strictement identiques. Dans un fichier de configuration, deux déclarations d'une variable,
> c'est **la dernière qui gagne, en silence**, le jour où elles divergent.
>
> **Et un défaut plus sérieux, dormant depuis `T3` :** `make env` ne touche **jamais** un `.env`
> existant — c'est voulu, il porte des secrets engendrés. Une variable ajoutée au modèle **après**
> la première création du `.env` n'y arrive donc **jamais**. Le `.env` de cette machine comptait
> **74 affectations contre 78** : `APP_REVISION` (`T3`), `LOG_MAX_SIZE` et `LOG_MAX_FILES` (`T4`) y
> manquaient. **Lance `make env-check` en début de session** : c'est la parade, et elle nomme les
> manquantes.

`make env` **génère localement** `APP_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`,
`MINIO_ROOT_PASSWORD` sur 48 caractères, et un `MINIO_ROOT_USER` lisible. **Restent en
`CHANGE_ME`, et ce n'est pas un oubli** : `IMPORT_SOURCE_RETENTION_DAYS` (`QO-100`, bloquante,
LOT 9) et `UPTIME_KUMA_PUSH_URL` (LOT 13).

| Variable | Valeur par défaut |
|---|---|
| `APP_ENV` · `APP_VERSION` · `APP_REVISION` | `development` · `0.0.0-dev` · `inconnue`. **Gravées dans l'image depuis `T7`** (`DEC-480`), et Compose emploie des défauts explicites `${…:-…}` |
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
app.onboarding.localhost   → 127.0.0.1   page de statut, OPERATIONNELLE depuis T5
                                         + /health/* et /api/* mandates vers l'API (DEC-470)
api.onboarding.localhost   → 127.0.0.1   API, operationnelle depuis T3
```

macOS les résout **sans toucher à `/etc/hosts`** — vérifié, 0 occurrence dans le fichier.

**Depuis `T5`, la page et l'API partagent une origine** (`DEC-470`) : le bloc
`app.onboarding.localhost` mandate `/health/*` et `/api/*` vers `api:8000`, le reste vers
`web:5173`. Le frontend appelle donc `/health/ready` **en relatif**, sans CORS. Ne remets pas ce
montage en cause sans lire `DEC-470` : il existe pour que les cookies `Secure` et `SameSite` du
LOT 3 soient éprouvables.

> **✅ La racine de l'autorité interne de Caddy EST approuvée** depuis le 29/07/2026.
> `security verify-cert` sort en **0**, « certificate verification successful » — il sortait en
> **1**, `CSSMERR_TP_NOT_TRUSTED`, avant. `curl` **sans** `-k` aboutit désormais, la page répond
> 200, et elle a été **vue dans un vrai navigateur** : rendu complet, console sans erreur, cinq
> largeurs de recette sans débordement.
>
> **La commande qui figurait ici était fausse et ne pouvait pas fonctionner.** Elle employait
> `sudo` et le trousseau **système**, or Jonathan n'a **aucun droit d'administration** sur cette
> machine (§5.1). Le drapeau `-d` visait le magasin administrateur ; sans lui, `security` écrit
> dans le domaine **utilisateur**, et cela suffit. Si le volume `caddy-data` est un jour détruit,
> une nouvelle racine est engendrée et l'approbation doit être refaite — **c'est l'action de
> Jonathan**, elle demande son mot de passe **de session**, non celui d'un administrateur :
>
> ```bash
> docker cp onboarding-dev-caddy-1:/data/caddy/pki/authorities/local/root.crt /tmp/caddy-onboarding-root.crt && security add-trusted-cert -r trustRoot -k ~/Library/Keychains/login.keychain-db /tmp/caddy-onboarding-root.crt
> ```
>
> Couvre Safari, Chrome et Edge. **Pas Firefox**, qui gère son propre magasin. Mes contrôles
> restent en `curl -k` : ils ne doivent pas dépendre d'une action humaine.
>
> **C'est aussi pourquoi `make destroy` n'est pas anodin** : il supprime `caddy-data` avec le
> reste. Pour éprouver une machine propre, supprime le **seul** volume utile — c'est ce que `T6` a
> fait pour reproduire le défaut du bucket MinIO.

## 5.7 Contrainte mémoire

| Grandeur | Valeur mesurée |
|---|---|
| RAM machine | 16 Gio |
| **RAM allouée à Docker** | **7,75 Gio** |
| Les 8 services, **code applicatif en marche** | **483 à 494 Mio, 6,1 à 6,2 %** — deux mesures du 29/07/2026, sous-étape `T7`. C'était 389 Mio en `T5` |
| Pour mémoire, les mêmes au repos en `T2` | 146 Mio, 2 % — `api`, `worker` et `web` attendaient |
| Le service le plus sollicité | `api`, à **9,0 %** de sa limite de 1 024 Mio |
| Limites déclarées | 6 144 Mio au total, **effectivement appliquées** |
| Images | `web` **1,02 Gio** — `ROAD-RSK-030` **aggravé** · `api` et `worker` 662 Mio |
| Projet tiers `observatoire-ecom-studio` | **arrêté** par `docker compose stop`, volumes intacts |

**La marge est confortable pour UN environnement**, et c'est tout ce qui est prouvé. `DEC-440`
n'autorise qu'un environnement à la fois ; la mesure de deux stacks simultanées relève de `T8`,
et c'est là que `QO-085` pourra se clore.

**Remise en route du projet tiers, quand le LOT 1 sera fini :**

```bash
docker compose -p observatoire-ecom-studio start
```

## 5.8 Images, registre et étiquettes — les constantes de `T7`

**Elles n'existaient pas avant `T7`. Toutes sont déclarées dans le `Makefile`, en une seule source
de vérité, et le workflow n'en redéfinit aucune.**

| Constante | Valeur | Où, et pourquoi cette valeur |
|---|---|---|
| `REGISTRE_IMAGES` | `ghcr.io/jonathan2433/onboarding-digital` | `DEC-445`. **Minuscules obligatoires** : GHCR refuse une majuscule dans un nom de paquet, alors que le compte s'écrit `Jonathan2433` |
| `PLATEFORMES_IMAGES` | `linux/amd64,linux/arm64` | Cahier §22.3, littéralement : `arm64` pour le Mac M5, `amd64` pour un futur serveur x86 |
| `IMAGES_SPEC` | `api::130 worker::130 web:execution:35` | `<service>:<cible>:<plafond Mio>`. **Une liste littérale, et non trois familles de variables** : une variable Make n'est **pas** visible du shell d'une recette, et l'indirection `$${CIBLE_$$service}` y vaudrait la chaîne vide — `web` n'aurait jamais reçu `--target execution`, **en silence** |
| `VERSION_IMAGE` · `REVISION_IMAGE` | `0.0.0-dev` · `inconnue` | Défauts. La CI passe la version et l'empreinte du commit réels |
| `ETIQUETTE_LOCALE` | `onboarding-local` | Les listes de manifestes construites **localement**. Jamais poussées |

**Les plafonds portent sur la taille de CONTENU, pas sur l'usage disque, et c'est mesuré.** Une
image a **deux** tailles qui diffèrent d'un facteur quatre : `api` `arm64` pèse **115 Mo de contenu**
et **473 Mo sur disque**. `T2` et `T5` citaient la seconde, `docker images` la rapportant.

> **Pourquoi la première, et le motif est décisif :** l'usage disque **n'est pas comparable d'une
> plateforme à l'autre**. `docker image ls --tree` annonce **473 Mo** pour la variante `arm64` et
> **114 Mo** pour la variante `amd64` de la **même** image — seule la variante native est dépaquetée
> localement. Un plafond fondé sur cette grandeur passerait ou échouerait selon l'architecture de
> l'exécuteur. C'est le défaut `T7-6`, et il a produit un plafond **4,5 fois trop large**.

**Étiquettes publiées** — `DEC-481`, conventions §4.1 :

| Étiquette | Quand | Usage |
|---|---|---|
| `sha-<empreinte courte>` | **toujours** | traçabilité, diagnostic, rejeu |
| `develop` | poussée sur `develop` | recette locale **seulement** |
| version exacte, `0.1.0` | tag `v*` | **seule** référence autorisée en production |
| ~~`latest`~~ | **jamais** | `DEC-481`, plus strict que les conventions. `make images-check` échoue si le mot apparaît |

> **Les étiquettes locales de Compose, `onboarding-dev-web:latest`, sont hors de cette
> interdiction** : Compose les engendre pour toute image construite sans étiquette explicite, elles
> ne sont jamais poussées, et c'est exactement le cas que les conventions §4.1 tolèrent. Le contrôle
> les distingue, avec témoin dans les deux sens — la première version criait au loup sur
> `runs-on: ubuntu-latest`, qui est un **label d'exécuteur**.

**Deux plateformes de plus, à connaître :**

- **`linux/s390x`** est la **plateforme témoin** du vérificateur. Elle est volontairement absente de
  nos manifestes, et le contrôle **exige que son inspection échoue** : sans cela, un
  `docker image inspect --platform` qui réussirait pour n'importe quelle valeur donnerait la même
  observation qu'un manifeste correct ;
- **`ARM64-COW-BUG`** est un avertissement Redis, supprimé **uniquement** sur le double jetable du
  vérificateur. Voir §7.18 — ne le porte **jamais** dans Compose.

**Le magasin d'images containerd est un prérequis mesuré.** `docker info` doit rapporter
`io.containerd.snapshotter.v1` : sans lui, `docker buildx build --platform … --load` refuse de
charger une liste de manifestes. Vérifié le 29/07/2026 sur cette machine.

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
7. REFERMER l'issue  A LA MAIN : `Closes #N` ne marche pas depuis develop, voir §7.19
```

**L'étape 7 n'est pas une formalité et elle a été oubliée à la fusion de `T7`.** Le commentaire de
fermeture est aussi l'endroit où cocher les critères d'acceptation avec leurs preuves, ce que le
backlog §11 exige.

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

**80 défauts détectés à ce jour** : 7 au LOT 0, 3 en `T0`, **70 pendant `T1` à `T11` et après la porte**. Ils sont
tous consignés dans les comptes rendus de sous-étape.

## 7.0 La règle qui résume tout

> **Un contrôle qui ne peut pas échouer ne prouve rien. Un contrôle dont on ne lit pas le code
> de sortie ne prouve rien non plus. Un contrôle qui n'annonce pas combien d'éléments il a
> examinés peut toujours n'en avoir examiné qu'un. Et un contrôle dont l'échec produirait la
> même observation que le succès ne prouve rien, quel que soit le nombre d'éléments comptés.**

Les troisième et quatrième propositions sont l'apport de ce lot. Parades, toutes deux mécaniques :
**compter, et confronter le compte à un attendu** ; puis **se demander quelle valeur produirait
l'échec**.

La quatrième vient de `T5-6`. Mon contrôle annonçait « 7 modules sur 7 résolus » et avait bien
examiné 7 modules — mais il concluait sur un **code HTTP 200**, or Vite répond 200 avec
`index.html` pour tout chemin inconnu : un module absent aurait donné la même observation. La
parade du lot était respectée, et le contrôle ne prouvait rien. Corrigé en discriminant sur le
**type MIME**. Même mécanisme que `T2-5`, où un Mailpit vide et un volume effacé donnaient tous
deux `{"total":0}`.

**C'est le témoin négatif qui les révèle** : quand il **passe** alors qu'il devait échouer, ce
n'est pas le témoin qui est mauvais, c'est le contrôle qui ne discrimine pas.

**Cinquième proposition, apport de `T6` — elle ne porte plus sur les contrôles mais sur les
corrections :** avant d'appliquer un correctif, mesure **ce que le correctif casse**. Un avis de
sécurité désigne un problème, jamais une solution. En `T6`, forcer la version « corrigée » de
`brace-expansion` aurait neutralisé ESLint, donc `jsx-a11y`, donc le seul garde-fou
d'accessibilité du projet — pour un déni de service théorique dans une dépendance de
développement. Seul le fait d'installer la version et de l'appeler l'a montré.

**Sixième proposition, apport de `T7` — et elle attrape un contrôle que les cinq autres laissaient
passer :** un contrôle qui compare deux nombres doit prouver qu'ils mesurent **la même grandeur**.

Mon contrôle de plafond de taille pouvait échouer, on lisait son code, il annonçait combien
d'éléments il avait examinés, et l'échec aurait produit une observation différente du succès —
**les cinq propositions étaient respectées**. Et il ne prouvait rien : il comparait une **taille de
contenu** de 109 Mio à un plafond de 500 Mio calibré sur l'**usage disque**. Un facteur 4,5, donc un
plafond qui passait quoi qu'il arrive. La question qui manquait : *le nombre que j'affiche et le
seuil auquel je le compare mesurent-ils la même chose ?*

**Et un septième point, qui n'est pas une proposition mais un interdit.** En `T7` j'ai écrit une
**empreinte SHA-256 inventée** dans un workflow, comme « garde-fou secondaire » de l'installation
de Trivy. Aucune des six propositions ne l'attrape : le contrôle aurait « fonctionné ». Une valeur
plausible plutôt que mesurée, dans un contrôle de sécurité, **fabrique la preuve au lieu de la
produire**. N'écris jamais une empreinte, un compte ou une mesure que tu n'as pas relevée.

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

## 7.2 Les espaces dans le chemin — **4 occurrences, dont une en `T7`**

Le dépôt vit sous `~/Library/Mobile Documents/`. **`$(CURDIR)` contient une espace.**

| Où | Symptôme |
|---|---|
| `Makefile`, `--env-file $(ENV_FILE)` non cité | `couldn't find env file: /Users/.../Library/Mobile` |
| Scripts, `eval docker compose … "$@"` | `eval` redécoupe les arguments, un `sh -c '…'` explose |
| Shell ad hoc, `DC="docker compose --env-file $PWD/.env …"` | `code=127`, **la commande n'a jamais tourné** |
| **`T7`, le même `DC="…"` exactement** | `code=127`, et je venais de citer ce piège dans mon propre rapport |

```bash
# TOUJOURS citer :
docker compose --env-file "$PWD/.env" -f fichier.yml "$@"
# JAMAIS eval pour assembler une commande dont un argument est cité.
# Une FONCTION shell, jamais une variable :
dc() { docker compose --env-file "$PWD/.env" -f base.yml -f dev.yml "$@"; }
```

Dans les scripts, le montage retenu : `$COMPOSE_FILES` **non cité** — le découpage est voulu,
ces chemins n'ont pas d'espace — et `$env_file` **cité**. Le script **refuse de continuer** si un
chemin Compose contient une espace.

> **La parade que `T7` a retenue, et c'est la seule qui ne dépende pas de ta mémoire.** Ce piège a
> été commis quatre fois, dont deux fois par un agent qui l'avait lu le jour même. Les contrôles de
> `T7` sont donc écrits en **Python**, avec `subprocess.run([...])` et sans `shell=True` : les
> arguments sont passés tels quels, **aucune redécoupe n'a lieu**, et `returncode` ne peut pas être
> celui d'un autre maillon. Le piège n'y **existe pas**. Quand une classe d'erreur résiste à la
> vigilance, change d'outil au lieu de promettre d'être plus attentif.

## 7.3 Le code de sortie — **7 occurrences**, et la dernière est d'un autre type

```bash
sortie=$(commande 2>&1); code=$?          # correct... SAUF sous `set -e`
if commande | sed 's/x/y/'; then …        # teste sed, JAMAIS commande
echo "code=$?"   # apres un tuyau : c'est le code du DERNIER maillon
```

En `T4`, j'ai lu « build code=0 » alors que le build venait d'échouer : la stack est remontée
sur les **anciennes images** en affichant « 8 services sains ». En `zsh`, `${pipestatus[1]}`
donne le code du premier maillon.

> **`T7` a ajouté une sixième occurrence, et elle n'est PAS un tuyau.** Le journal de chaque étape
> GitHub Actions porte `shell: /usr/bin/bash -e {0}` : **`-e` est déjà actif, et `set -uo pipefail`
> ne le retire pas.** Un `commande ; code=$?` fait donc sortir bash **à l'échec de la commande, avant
> la lecture du code**. Mon étape échouait sans produire **une seule ligne de sortie**, alors que
> c'était un contrôle dont **l'échec de la commande était le résultat attendu** — prouver qu'un
> tirage anonyme du registre est refusé.
>
> ```bash
> # Dans une étape de workflow, pour une commande dont l'échec est ATTENDU :
> sortie=$(commande 2>&1) && code=0 || code=$?
> ```
>
> **Et cela dit la limite du remède du §7.2.** Écrire les contrôles en Python immunise le
> vérificateur ; les étapes d'un workflow restent du shell, avec un `-e` qu'on n'a pas écrit. Un
> remède structurel ne couvre que le périmètre où il s'applique, et il faut savoir dire où il
> s'arrête.

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

## 7.5 `zsh` ne découpe pas les variables en mots — **rejoué trois fois en une seule session**

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
| Vite sert le dev server sur toutes les interfaces | **Non**, défaut `localhost` → `server.host` à `0.0.0.0`, sinon injoignable en conteneur |
| Vite accepte n'importe quel en-tête `Host` | **Non**, Vite 8 installe un contrôle d'hôte dès que le serveur n'est pas lui-même en HTTPS → `server.allowedHosts` |
| Vite renvoie 404 sur un chemin inconnu | **Non**, il renvoie **200 + `index.html`** → discrimine sur le type MIME, jamais sur le code |
| `@testing-library/dom` vient avec `@testing-library/react` | **Non** depuis la v16, c'est un **pair** à installer explicitement |
| `pnpm` lit `auditConfig` dans `package.json` | **Non**, pnpm 11 lit ses réglages d'espace de travail dans **`pnpm-workspace.yaml`** — comme `storeDir` en `T1`. Même classe, autre clé |
| Une liste blanche Gitleaks est comparée à la ligne | **Non**, au **secret capturé** seul. Sans `regexTarget = "match"`, un motif écrit sur la ligne ne correspond à rien |
| `brace-expansion` 5.x remplace 1.x sans risque | **Non**, son export CommonJS est un **objet** portant `.expand`, non une fonction. `minimatch@3` casse |

**Inspecte les exports réels avant de les utiliser**, ne te fie pas à ta mémoire d'une API.

## 7.11 Vérifier ce que la documentation affirme

Ce lot a corrigé **huit** affirmations fausses du corpus, presque toutes des nombres non dérivés
de la source : le bandeau « LOT 1 non ouvert » après son ouverture (`ECART-017`), « 8 contrôles
de CI » là où le cahier en énumère **11** (`ECART-018`), « 9 placeholders `CHANGE_ME` » là où il y
en a **7** (`ECART-019`), les décisions de `T0` bornées à `DEC-447` au lieu de `DEC-449`, et les
quatre de `ECART-021` : **131 tests au lieu de 139** dans deux documents, « 30 tests » de masquage
non reproductible, les compteurs de commits et de lignes de ce document, et un **« prochain
identifiant libre : `DEC-451` »** dans le registre des décisions alors que `DEC-469` était en
usage — **19 décisions de retard**, donc une collision garantie pour qui s'y fierait.

Une affirmation fausse qui n'était pas un nombre, et celle-là a coûté du temps :
**`CLAUDE.md` §9.3 affirmait « `Caddyfile` inchangé : le mandatement existe déjà »**, alors
qu'aucune route n'y menait à l'API. Voir §9.0.

**Vérifie l'état réel par `git`, `gh` et les mesures. Et dérive les nombres de la source.**
`T6` doit poser en CI un contrôle qui les recalcule et échoue s'ils divergent — recommandation de
`ECART-021`, à joindre à celle de `ROAD-RSK-029` sur les cinq empreintes SHA-256.

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

**Depuis `T6`, ce n'est plus seulement une gêne locale : tout ce que tu écris tourne aussi sur un
exécuteur Linux.** Deux pièges mesurés le 29/07/2026 :

| Sur macOS | Sur Linux |
|---|---|
| `sed -i ''` fonctionne | **GNU sed échoue en code 2** : il lit le script comme un nom de fichier. Emploie `sed … > f.tmp && mv f.tmp f` |
| `app.onboarding.localhost` se résout | **`gaierror`, aucune adresse.** Linux ne résout pas les sous-domaines de `.localhost`. Le workflow pose deux lignes dans `/etc/hosts` |

Écris désormais du shell **portable**, et fais-le vérifier par la CI.

## 7.13 Ne jamais `grep` le prototype en entier

`V1.html` fait 2,83 Mo dont **2,64 Mo de Base64**. Travaille sur une version dépouillée, hors
du dépôt.

## 7.14 Ne jamais manipuler les identifiants de Jonathan

`git` et `gh` savent s'authentifier seuls. **N'extrais jamais le jeton du trousseau macOS**, et
**n'entre jamais d'identifiants à sa place** — `gh auth login`, mot de passe `sudo`, approbation
de la racine Caddy dans le trousseau sont **ses** actions.

## 7.15 Un service peut être sain et servir une configuration périmée

Trois pièges découverts en `T5`, tous les trois **silencieux** : rien n'échouait, tout paraissait
correct.

**1. Un bind mount de FICHIER unique épingle l'inode.** La plupart des éditeurs n'écrivent pas en
place : ils écrivent un temporaire puis renomment, ce qui produit un inode neuf. Le conteneur
continue de pointer vers l'ancien, désormais supprimé — `ls` affiche encore l'entrée, mais toute
ouverture répond « No such file or directory ». Mesure : le conteneur voyait un `Caddyfile` de
**1 573 octets** quand l'hôte en portait **2 844**, et Caddy servait donc une configuration
périmée **en étant `healthy`**, son API d'administration répondant très bien — sur l'ancienne
configuration.

```yaml
- ../caddy:/etc/caddy:ro      # le REPERTOIRE : le chemin est resolu a chaque ouverture
- ../caddy/Caddyfile:/etc/caddy/Caddyfile:ro   # le FICHIER : epingle l'inode, ne fais plus ca
```

**2. Compose ne recrée pas un conteneur quand seul le CONTENU du fichier monté change, et Caddy ne
surveille pas son fichier.** `make up` appelle donc `caddy-reload`. Si tu modifies le `Caddyfile`
et que rien ne change, c'est là qu'il faut regarder.

**3. Aucun `.dockerignore` n'existait avant `T5`.** `COPY apps/web ./apps/web` recopiait le
`node_modules` de l'**hôte** par-dessus celui de l'image. Non actif — les liens sont relatifs et
pointent vers le magasin du conteneur — mais l'hôte résout `darwin-arm64` là où l'image résout
`linux-arm64-musl`. Le défaut est resté invisible tant qu'aucune image n'avait besoin
d'**exécuter** le code copié.

**La leçon commune :** un healthcheck qui interroge un service ne dit rien de la **configuration**
que ce service a chargée. Compare toujours l'état chargé au fichier présent.

## 7.16 Ce qui n'a jamais tourné ailleurs n'est pas éprouvé

**Leçon centrale de `T6`, et elle vaut pour tout ce que tu écriras.** Le `Makefile` fonctionnait
depuis `T1` — sur **une** machine, sous macOS, avec des volumes **déjà peuplés**. La première
exécution sur un exécuteur neuf a révélé deux défauts qui n'étaient pas des régressions, mais des
**conditions jamais rencontrées** :

1. **`make env`** employait `sed -i ''`. GNU sed échoue. Toute la tâche « stack » cassait.
2. **`make up` n'avait jamais fonctionné sur une machine propre.** La sonde `ready` de l'API fait
   un `head_bucket` ; sans bucket elle répond 503, `api` n'est jamais sain, `up --wait` échoue. Or
   le bucket n'était créé qu'**après** cette attente. En local le volume `minio-data` survit à
   `make down`, et le bucket y était déjà : le défaut ne pouvait pas se montrer.

Le second aurait attendu **`T9`** pour se manifester, sur le critère « les procédures fonctionnent
depuis une machine propre » — et il aurait alors fallu comprendre pourquoi la stack ne démarre pas
chez quelqu'un d'autre. `DEC-477` le corrige, et **`T8` devra reproduire cet ordre** dans la
surcouche de recette.

**Pour éprouver une machine propre sans tout casser :** ne lance pas `make destroy`, qui
supprimerait `caddy-data` et l'approbation du certificat avec. Supprime le **seul** volume utile.

---

## 7.17 Monter le répertoire ne suffit pas : iCloud remplace aussi les répertoires

**Découvert en `T7`, et cela élargit le périmètre de `DEC-472`.** `make up` a échoué : le conteneur
`caddy` voyait un `/etc/caddy` **vide** alors que l'hôte portait bien son `Caddyfile`.

| Fait | Mesure du 29/07/2026 |
|---|---|
| Conteneur `caddy` créé à | **09:51:38** |
| `ctime` de `infra/caddy` **et** de `infra/caddy/Caddyfile` | **10:06:49**, 15 min plus tard |
| Action de session à 10:06:49 | **aucune** — même signature que le 27/07 à 23:30:28 |
| Conteneur **neuf** sur la même source | voyait le fichier sans peine, 2 844 octets |

**`T5` avait résolu le remplacement du FICHIER par un éditeur, en montant le répertoire. Cela ne
protège pas du remplacement du RÉPERTOIRE par iCloud** : un conteneur ne re-résout **pas** la source
d'un montage lié après sa création. Et pendant ce temps, les huit services étaient `healthy` et
Caddy servait la configuration chargée à 09:51.

```bash
make caddy-recreate   # le seul geste qui repare : le conteneur re-resout son montage
```

**`caddy-reload` compare désormais l'empreinte SHA-256 du `Caddyfile` vu par le conteneur à celle
de l'hôte**, et ne masque plus son erreur — elle annonçait « configuration invalide ou service
absent » là où le message réel était « no such file or directory ». Deuxième leçon, donc : le piège
du §7.6 était dans un contrôle que le projet avait lui-même écrit.

---

## 7.18 Diagnostiquer avant de corriger — `T7` y a perdu trois cycles

**Le défaut le plus coûteux de `T7`, et il n'était pas technique.** Ma sonde du worker échouait sous
émulation. J'ai corrigé **deux fois** sans avoir diagnostiqué :

| Tentative | Hypothèse | Résultat |
|---|---|---|
| 1 | une course : Redis pas encore prêt | j'ajoute une attente → échoue toujours |
| 2 | l'attente est trop courte | j'allonge à 120 s → « **JAMAIS en 120 s** » |
| 3 | **je fais dire au contrôle l'état de la dépendance qu'il démarre** | `exited code=1`, et le journal donne la cause en une ligne |

La cause : **sous QEMU, Redis détecte le bug copie-sur-écriture d'ARM64 et sort exprès**, pour ne pas
corrompre ses données. Aucune attente n'y pouvait rien. Trois cycles d'intégration continue — une
heure — pour un problème que le premier journal aurait nommé.

> **La leçon, sans jargon :** quand un contrôle échoue et que tu ne sais pas pourquoi, **la première
> correction à écrire est celle qui te le dira.** Un contrôle qui masque la cause de son échec ne
> coûte pas un message : il coûte des cycles entiers. C'est le §7.6 à l'échelle d'une sous-étape.

**Et une précaution sur le correctif retenu**, parce qu'on pourrait le généraliser à tort :
`--ignore-warnings ARM64-COW-BUG` **supprime un garde-fou contre la corruption de données**. Il est
posé sur le **double jetable** du vérificateur — sans donnée, `--save ""`, le temps d'un `PING` — et
**vérifié absent des fichiers Compose, 0 occurrence dans les YAML**. Le Redis du projet tourne
nativement sur `aarch64` et n'a jamais déclenché cet avertissement. **Ne le porte pas dans
`docker-compose.base.yml`** : ce serait exactement la classe de correctif que `T6-7` a appris à
mesurer avant d'appliquer.

---

## 7.19 `Closes #N` ne referme pas une issue depuis `develop`

**Constaté à la fusion de `T7`.** La pull request `#23` portait `Closes #7` ; après fusion, l'issue
`#7` était **toujours ouverte**.

GitHub n'applique le mot-clé que pour une fusion dans la branche **par défaut**, ici `main`. Or
**toutes** les fusions du LOT 1 vont dans `develop` : aucune ne referme son issue automatiquement.

```bash
gh issue close <n> --comment "…"   # a faire A LA MAIN, apres chaque fusion
```

Les sous-étapes précédentes le faisaient déjà sans que ce soit écrit. **C'est une routine à tenir
jusqu'à `T11`**, pas un incident — et le commentaire de fermeture est le bon endroit pour cocher les
critères d'acceptation avec leurs preuves, ce que le backlog §11 exige.

## 7.20 Un contrôle qui échoue sur un livrable conforme : ne l'affaiblis pas

**Découvert en `T8`, et c'est la leçon la plus utile de cette sous-étape.** Mon contrôle
d'isolement réseau exigeait que la base du développement soit injoignable depuis la recette. Il a
échoué. Le livrable était pourtant conforme au cahier.

**J'ai diagnostiqué avant de corriger** — leçon `T7-13` — et l'épreuve décisive a porté sur un
**même conteneur**, ce qui élimine toute cause propre à un service :

| Cible | Publié sur l'hôte ? | Depuis la recette |
|---|---|---|
| `dev mailpit 172.20.0.4:8025` | **oui** | **JOIGNABLE** |
| `dev mailpit 172.20.0.4:1025` | non | `TimeoutError` |

**Docker installe pour chaque port publié une règle `ACCEPT` dans la chaîne `FORWARD`, et elle
précède ses règles `DOCKER-ISOLATION`.** Le paquet est accepté avant que l'isolement n'ait la
parole. Le préfixe `127.0.0.1` de `DEC-460` protège du réseau local et du pare-feu de macOS ; il ne
protège **pas** d'un autre réseau Docker de la même machine.

**Le cahier §22.2 exige un « réseau distinct », pas l'inatteignabilité mutuelle.** Mon contrôle
exigeait donc plus que le critère. Trois réactions possibles, et une seule est bonne :

- le **supprimer** — on perd l'information ;
- l'**affaiblir** en le faisant porter sur les noms de réseau — il ne prouverait plus rien ;
- **le faire dire le vrai**, ce qui a été retenu.

> **La règle, sans jargon :** fais-lui **exiger** ce qui est exigible — noms, sous-réseaux, DNS, et
> les ports **non publiés** ; **rapporter visiblement** ce qui ne l'est pas, en le nommant ; et
> **exiger la barrière** qui rend le résiduel acceptable. Ici c'est la cinquième séparation : avec
> le mot de passe de la recette, la base de dev **refuse**. Une barrière qui rend un résiduel
> acceptable doit être un **contrôle**, jamais une affirmation.

C'est le parti de `DEC-482` pour Trivy, transposé. **Et le taire aurait été le pire choix** : le
contrôle aurait annoncé « 7 séparations prouvées » en laissant croire davantage que ce qui est vrai.

---

## 7.21 Un contrôle juste hier peut être faux aujourd'hui, et c'est toi qui l'as rendu faux

**Apport de `T9`, et les deux défauts qui l'ont produit sont instructifs parce qu'ils ne sont pas de
la négligence.**

| Défaut | Ce qu'il affirmait | Ce que la mesure dit |
|---|---|---|
| `make destroy`, écrite en `T2` | « détruire `caddy-data` obligera à réapprouver la racine dans le trousseau » | vrai pour `dev` — `verify-cert` code 0 — **faux pour la recette**, code 1, racine jamais approuvée |
| Contrôle de page, écrit en `T5` | l'index doit référencer `/src/main.tsx` | vrai du serveur Vite, **faux de l'artefact bâti**, qui référence `/assets/…js` |

**Les deux étaient JUSTES quand ils ont été écrits.** `T2` et `T5` ne connaissaient qu'un
environnement. C'est `T8`, en créant le second, qui les a rendus faux — sans que rien ne le signale,
parce qu'aucun contrôle ne les exerçait dans le nouvel environnement.

> **La règle, sans jargon :** quand une sous-étape ajoute un environnement, une cible de
> construction ou une plateforme, **relis les contrôles qui n'en connaissaient qu'un**. Un contrôle
> ne devient pas faux tout seul : il le devient quand le monde change autour de lui, et ce
> changement, c'est nous qui le faisons.

**Le remède est le même dans les deux cas, et c'est celui du §7.20 :** faire **mesurer** au lieu
d'affirmer. `destroy` interroge le trousseau et dit ce qu'elle a mesuré — ou dit **« indéterminé »**
quand elle ne peut pas mesurer, plutôt que de trancher. Le contrôle de page **identifie** la cible
servie, exige qu'elle soit l'une des deux formes connues, et **échoue** s'il n'en reconnaît aucune.

**Un avertissement faux est pire qu'une absence d'avertissement.** Celui de `destroy` portait sur la
cible la plus destructive du dépôt : annoncer une conséquence inexistante apprend à passer outre, si
bien que le jour où il porte sur `dev`, où la conséquence est réelle, il n'est plus lu.

**Et une troisième leçon, de méthode celle-là.** J'ai annoncé à Jonathan qu'un workflow ne s'était
pas déclenché. Il ne s'était pas déclenché **encore** : `gh run list --branch` rendait 0 pendant trois
minutes alors que les check-runs sur l'empreinte de tête montraient deux contrôles en cours. **Avant
d'annoncer qu'une chose est absente, demande-toi si ta sonde distingue « absent » de « pas encore
là ».** Même famille que `T2-1`, où un 429 masqué avait été lu comme une image inexistante.

---

## 7.22 Un résiduel accepté n'est pas un dossier clos

**Apport de `T10`, et il renverse une mesure de `T6` en un seul jour.**

`T6` avait accepté un avis de sécurité, `GHSA-mh99-v99m-4gvg`, avec un motif **mesuré et solide** :

- la dernière version publiée de la ligne 1.x de `brace-expansion` **était** `1.1.16` — aucun
  correctif n'existait dans cette ligne ;
- forcer la ligne 5 **cassait ESLint** : son export CommonJS est un objet portant `.expand`, non une
  fonction, là où `minimatch@3` appelle `expand(motif)`. Le « correctif » aurait neutralisé
  `eslint-plugin-jsx-a11y`, motif déterminant de `DEC-451`.

**Mesure du 30/07/2026 : la ligne 1.x a reçu `1.1.18`.** Ce que `T6` avait mesuré comme inexistant
existe. Un `pnpm update -r`, dans les plages déjà déclarées, sans forcer aucune version majeure.
Vérifié dans les deux sens — l'audit est vert **avec et sans** la tolérance — et rien n'est cassé.

> **La règle, sans jargon :** un risque accepté parce qu'« aucun correctif n'existe » décrit
> l'écosystème **à une date**. Réévalue-le, ne l'archive pas. Et **retire la tolérance dès qu'elle ne
> couvre plus rien** : une tolérance morte avalerait silencieusement une réapparition du même avis,
> donc elle est moins sûre que pas de tolérance du tout.

**`ROAD-RSK-033` est exactement dans cette situation** — 23 avis `HIGH`/`CRITICAL` de
`python:3.12-slim` « dont aucun n'a de correctif », mesuré en `T7`. À réexaminer avant le LOT 13, et
la même surprise est possible.

**Et une seconde leçon, sur la façon d'attribuer une régression.** Quand `make audit` est devenu
rouge en cours de sous-étape, la tentation était de chercher ce que `T10` avait cassé. La mesure
juste a été de créer un arbre de travail sur le commit **d'avant** et d'y relancer l'audit : mêmes
quatre avis. **Avant d'attribuer une régression à ton travail, mesure l'état d'avant** — `pnpm audit`
interroge une base qui change sans toi.

---

## 7.23 Un état DORMANT ne se voit pas dans ce qui tourne

**Apport du correctif postérieur à la porte `G1`, et il complète le §7.21.**

En `T8`, j'ai choisi la bande de ports de la recette après avoir mesuré que `8080` était **libre**.
La mesure employait `lsof -nP -iTCP -sTCP:LISTEN` : elle regardait **ce qui écoutait**.

Le projet tiers `observatoire-ecom-studio` **déclarait** `127.0.0.1:8080` depuis toujours. Il était
**arrêté** au moment de ma mesure — et **un conteneur arrêté déclare ses ports sans en occuper
aucun**. À sa relance : `Bind for 127.0.0.1:8080 failed: port is already allocated`.

**Et la mesure refaite correctement en a révélé un second, antérieur au projet** : `5432`, entre
`onboarding-dev` et `ticket_master`, arrêté depuis quatre semaines et donc jamais manifesté.

> **La règle, sans jargon :** ma mesure répondait à « ce port est-il occupé **maintenant** ? » quand
> la question était « ce port sera-t-il disponible **quand ce projet démarrera** ? ». **Quand tu
> mesures une ressource partagée, demande-toi qui la RÉCLAME, pas seulement qui la détient.** Un état
> dormant — conteneur arrêté, service désactivé, tâche planifiée qui n'a pas encore tourné — ne se
> voit pas dans l'état courant.

**Et une limite que ma première correction portait encore.** Le contrôle ne lisait que les conteneurs
existants. Or `make down` **supprime** les conteneurs : un environnement arrêté ne déclare plus rien,
et le contrôle était donc aveugle à lui — **il n'aurait pas attrapé le défaut qui l'a fait naître**,
puisque la recette n'existait pas encore comme conteneurs quand j'ai choisi ses ports. `make ports`
confronte désormais **deux sources** : les conteneurs existants **et** la configuration Compose
assemblée, qui ne demande aucun conteneur. `DEC-494`, `ECART-025`.

---

## 7.24 Deux règles justes séparément peuvent s'exclure, et un outil qui réussit ne prouve rien

**Apport du correctif de stratégie de fusion, et il tient deux leçons distinctes.**

**La première porte sur les documents.** Les conventions Git posaient, à onze lignes d'intervalle,
« historique linéaire requis » (ligne 94) et « `develop` → `main` : merge commit » (ligne 106).
**Aucune des deux n'est fausse** — la première sert la lisibilité de `develop`, la seconde la
traçabilité de `main`. Elles sont **incompatibles** : l'historique linéaire refuse tout merge commit.
Les deux ont été appliquées, si bien que la fusion s'est rabattue sur le squash, ce qui a coupé `main`
de l'histoire de `develop` — et **9 fichiers sont entrés en conflit alors que le contenu ne
divergeait pas**.

> **La règle, sans jargon :** relire une règle ne suffit pas, il faut **confronter les règles entre
> elles**. Et le défaut ne s'est manifesté qu'à la **seconde** fusion vers `main` : une contradiction
> peut rester invisible tant qu'une seule de ses branches a été exercée. C'est `ECART-023` élargi —
> un document dérivé ne fait pas que vieillir, il peut **prescrire l'impossible dès sa rédaction**.

**La seconde porte sur les outils, et c'est la quatrième proposition du §7.0 appliquée à `git`.** Ma
résolution en `git merge -X theirs` **a réussi** : code 0, aucun conflit signalé. Et elle avait gardé,
du côté abandonné, un fragment **non conflictuel** — le bloc `§3.1` de `fiche-lot-1.md` — **en plus**
de la version qui le remplaçait. Soit **41 lignes dupliquées**, et une réserve `arm64` réapparaissant
*après* le texte qui la lève.

**Le succès de la fusion et sa justesse sont deux grandeurs différentes.** « Aucun conflit » ne veut
pas dire « le résultat est celui que je veux » : les deux produisent exactement la même observation.
Le contrôle qui discrimine ne porte pas sur le verdict de l'outil mais sur son **résultat** —
l'arbre :

```bash
git rev-parse origin/main^{tree} origin/develop^{tree}   # doivent etre IDENTIQUES
git merge-base --is-ancestor origin/develop origin/main  # doit sortir en 0
git rev-parse origin/main^@ | wc -l                      # 2 = merge commit, 1 = squash
```

**Et c'est ce contrôle-là qui a attrapé le défaut.** Sans lui, cette fusion passait en paraissant
propre — comme `T2-5`, où un Mailpit vide et un volume effacé rendaient tous deux `{"total":0}`.

---

# 8. Ce qui reste ouvert

## 8.1 Écarts — 5 ouverts sur 22

| ID | Objet | Échéance |
|---|---|---|
| `ECART-005` | Schéma CSV définitif relève de `QO-096` | LOT 9 |
| `ECART-012` | `intercontrat` imposé à une direction générale | LOT 2, avant LOT 5 |
| `ECART-013` | Les 5 tâches communes du prototype ont des identifiants différents | LOT 7 |
| `ECART-014` | « Représentant de cercle » contre « Booster » | LOT 6 |
| `ECART-015` | Le prototype ne fournit ni descriptions de cercles ni liens internes | LOT 6 |

`ECART-023` est ouvert et clos en **`T8`** — la fiche énumérait six des sept séparations du cahier §22.2, et empruntait « Mailpit exclusif » aux LOTS 11 et 13.

`ECART-006` est **clos** en `T3`, et `ECART-022` en **`T7`** : `.env.example` est en **v1.1**,
77 variables, 77 noms distincts. `ECART-022` couvrait cinq constats d'une même classe — un nombre
ou une affirmation non dérivés de leur source — dont le plus sérieux n'était pas documentaire :
**`make env` ne réconcilie pas un `.env` existant**, et trois variables y manquaient depuis `T3` et
`T4`. `make env-check` est la parade, et elle est dans `make check`.

## 8.2 Questions ouvertes utiles à la suite du LOT 1

| ID | Objet | Quand |
|---|---|---|
| ~~`QO-085`~~ | **CLOSE en `T8`.** Deux stacks **simultanées** mesurées : **836,6 Mio pour seize services, 10,5 %** des 7 936 Mio. `DEC-440` reste en vigueur — mesurer la simultanéité ne l'autorise pas | close |
| `QO-111` | **Fournisseur de collation PostgreSQL.** Ne se change pas sans recréer le cluster | LOT 2 |
| `QO-112` | **Liste des extensions PostgreSQL.** `CREATE EXTENSION` exige des droits élevés | LOT 2 |
| `QO-113` | **Conservation calendaire des journaux.** `json-file` borne par la taille | LOT 13 |
| `QO-094` | Second référent technique — conditionne `DEC-429` | avant production |
| `QO-106` | 9 étiquettes GitHub par défaut subsistent | choix de Jonathan |
| `QO-114` | **Droits d'administration pour la production temporaire locale.** Jonathan n'en a aucun : `restic`, Uptime Kuma et les services au démarrage en réclament habituellement | **LOT 13, à instruire avant** |

## 8.3 Risques ouverts qui te concernent

| ID | Objet |
|---|---|
| `ROAD-RSK-026` | iCloud — **matérialisé**, résiduel accepté par `DEC-457`. `make icloud-verify` |
| `ROAD-RSK-029` | Un formateur peut réécrire les documents immuables. **Garde-fou posé en `T6`** : `make docs-check` recalcule les 5 empreintes à chaque pull request. Le risque reste ouvert — tout outil ajouté plus tard le rouvrirait — mais il est désormais **détecté** |
| ~~`ROAD-RSK-030`~~ | **CLOS en `T7`.** Image `web` de 1,02 Gio → **84,9 Mo**. Résiduel nommé : `uv` et `uvx`, **55,1 Mio**, restent dans `api` et `worker` — poids seulement, Trivy n'y trouve rien |
| ~~`ROAD-RSK-031`~~ | **CLOS en `T7`.** Deux cibles nommées. **`T8` doit encore SÉLECTIONNER `execution`** dans la surcouche de recette — `make images-check` échoue si elle ne nomme aucune cible |
| `ROAD-RSK-015` | Secret intégré au code — **mesure effective depuis `T6`** : Gitleaks sur chaque pull request, historique compris, avec des règles taillées sur les formats de ce projet |
| `ROAD-RSK-032` | Avis `GHSA-mh99-v99m-4gvg`, sévérité haute, dans une dépendance **de développement** de `jsx-a11y`. **Aucun correctif applicable** : la 1.x n'en a pas, et la 5.x casse le lint — mesuré. Tolérance nommée, `DEC-474` |
| `ROAD-RSK-033` | Les images publiées héritent des vulnérabilités de leurs bases : `python:3.12-slim` porte **23 avis `HIGH`/`CRITICAL` dont AUCUN corrigeable**. **Nos couches n'en ajoutent aucune.** Résiduel accepté par `DEC-482`, à réévaluer **avant le LOT 13** |
| `ROAD-RSK-034` | **Nouveau, et mesuré en `T8`.** **Publier un port perce l'isolement inter-réseaux de Docker** : la règle `ACCEPT` d'un port publié précède les règles `DOCKER-ISOLATION`. Les **7** ports publiés du développement sont joignables depuis la recette, et une connexion à sa base **aboutit**. Le cahier §22.2 exige un réseau **distinct**, ce qui est acquis — pas l'inatteignabilité. **La barrière effective est la cinquième séparation, les secrets**, et `make separations-check` en fait une **exigence** : avec le mot de passe de la recette, la base de dev **refuse**. Résiduel accepté au LOT 1, **à réévaluer avant le LOT 13**, où la production locale portera des données réelles |

## 8.4 Contenus en attente de relecture

Les 29 éléments `CONT-001` à `CONT-029` sont au statut **`à relire`**. **Aucun n'est publiable en
l'état.**

---

# 9. Par où commencer : la porte `G1` est instruite, elle attend la décision

## 9.0 Ce que les sous-étapes ont démenti, et ce qu'il faut en retenir

**Cinq fois, ce document a affirmé faux, et chaque fois c'était une affirmation jamais mesurée.** Les
cinq sont détaillées dans les comptes rendus de `T5` à `T7`. Et la liste s'est allongée de quatre
façons différentes, ce qui compte plus que le nombre :

- **`T8` a démenti la FICHE DU LOT** — six séparations énumérées là où le cahier en compte sept
  (`ECART-023`). **Tout document dérivé d'un autre vieillit, pas seulement cette passation.**
- **`T9` a démenti deux CONTRÔLES du dépôt.** Les deux étaient **justes quand ils ont été écrits** ;
  c'est `T8`, en créant un second environnement, qui les a rendus faux (`ECART-024`, §7.21).
- **`T10` a démenti une MESURE de `T6`**, en un jour : un avis de sécurité accepté parce qu'« aucun
  correctif n'existe » en avait reçu un (§7.22).
- **`T11` a démenti une lecture de `git`.** Après la fusion de `develop` dans `main`,
  `git rev-list --left-right --count` rendait `1 18` d'une syntaxe et `0 32` d'une autre, et **aucun
  des deux ne répondait à la question** : ce sont des artefacts de fusion en squash. Ce qui fait foi
  est l'**arbre**, identique des deux côtés. **Un compte de commits répond à une autre question que
  celle qu'on croit poser.**

**Vérifie avant de bâtir dessus — surtout quand ce document t'annonce que tu n'as rien à faire.**

## 9.1 Où en est exactement le lot

**Les douze sous-étapes sont faites, les huit stories sont livrées, et 33 contrôles de sortie sont à
zéro.** Il ne reste **aucun travail technique**.

**Ce qui reste est une décision de Jonathan**, et la [checklist](docs/operations/checklist-validation-G1.md)
lui est remise. Elle porte les sept critères avec leurs preuves, les neuf critères d'empêchement du
backlog §12, une **démonstration guidée** des six éléments de la roadmap, ce qui reste ouvert, et ce
que la pose du tag déclenchera.

## 9.2 Ce qui a suivi la validation, et ce qui reste

**Fait, et mesuré le 12/08/2026 :**

1. **☑ `develop` fusionnée dans `main`.** Il a fallu **deux** pull requests. La première, `#30`
   (`be65b53`), précédait les documents de `T11` **et a été squashée** — voir `ECART-026`. La
   seconde, `#35` (`4c25ed2`), est une **vraie fusion**. Mesuré : `main^{tree}` =
   `develop^{tree}` = `9bc9359`, **2 parents**, `develop` **ancêtre** de `main`, `main`↔`develop` à
   **3 / 0**, et la base de fusion remontée de `09ceb7c` à `e526e57`.
2. **☑ Tag annoté `v0.1.0` posé sur `main`**, sur `be65b53` — `DEC-428`. **Il n'a pas été déplacé
   vers `4c25ed2`** : arbitrage de Jonathan, et conventions §4, un tag posé ne se déplace jamais.
   **Conséquence à connaître : `v0.1.0` ne contient pas les documents de `T11`.**
3. **☑ `required_linear_history` retiré sur `main`**, conservé sur `develop` — `DEC-495`,
   `ECART-026`. Sans cela la porte `G2` aurait reconflicté à l'identique.

**Reste à faire, et ce sont des actions de Jonathan :**

4. **☐ Refermer l'epic `#1`.**
5. **☐ Relancer le projet Docker tiers** : `docker compose -p observatoire-ecom-studio start`.
   **Il collisionne sur `8080` avec la recette** (`ECART-025`) : les deux ne peuvent pas tourner en
   même temps, et `make ports` l'annonce désormais.
6. **☐ Ouvrir le LOT 2**, ce qui est une **décision à tracer** : `ROAD-003` et `ARB-BACK-003`
   exigent une validation explicite avant tout lot dépendant.

## 9.3 Les pièges de cette fin de lot

1. **☑ Le tag `v*` a déclenché `images.yml`, et le piège s'est réalisé comme annoncé.** Mesuré le
   12/08/2026 : exécution sur `ref=v0.1.0`, **succès**, et les images publiées portent désormais
   l'étiquette **`0.1.0`** — première version non `develop` du dépôt, aux côtés de `sha-be65b53`,
   `sha-e526e57` et `develop`. **Aucun `latest`**, `DEC-481` tenu. Le piège vaut toujours pour la
   porte suivante : dis-le à Jonathan **avant** de poser un tag, pas après.
2. **Ne mets PAS « Porte des images multiarchitecture » dans les contrôles requis.** `images.yml` ne
   s'exécute pas sur les pull requests — cahier §23.1 — donc ce contexte ne produirait jamais de
   statut et **bloquerait toute fusion pour toujours**, `enforce_admins` étant actif.
3. **Compare les ARBRES, pas les commits**, pour savoir si `main` porte bien le contenu de `develop`.
   Voir §9.0.
4. **Les cinq documents de cadrage restent immuables.** `make docs-check` recalcule leurs empreintes.
5. **Le LOT 2 EST ouvert** depuis le 18/08/2026 (`DEC-496`), **mais son plan attend validation** :
   `DEC-496` pose qu'aucune ligne de code n'est écrite avant que Jonathan ait validé le §3 de
   [`fiche-lot-2.md`](docs/operations/fiche-lot-2.md). **Les interdits du LOT 2 sont au §11 de cette
   fiche** — au premier chef : aucune table d'authentification, aucun écran, aucun type métier dans
   `packages/contracts` avant qu'une route l'expose. **Les LOTS 3 à 14 restent `Planned`.**

## 9.4 Ce qui reste ouvert et devra être dit à la porte

| Élément | Ce qu'il faut annoncer |
|---|---|
| `QO-115` | La **charte graphique** et la **police officielle** n'existent pas dans le corpus — le prototype référence pourtant « la charte EXALT », donc **elle existe et nous ne l'avons pas**. Les jetons de `T10` sont défendables mais restent une **approximation**. À instruire avant le LOT 4 |
| `ROAD-RSK-034` | Les ports publiés d'un environnement restent joignables depuis l'autre. Le cahier §22.2 exige un réseau **distinct**, ce qui est acquis ; la barrière effective est la **cinquième** séparation, les secrets. À réévaluer avant le LOT 13 |
| `ROAD-RSK-033` | 23 avis sans correctif dans `python:3.12-slim`. **`T10` a montré qu'un tel résiduel peut se corriger du jour au lendemain** : à réexaminer, pas à archiver |
| `QO-111`, `QO-112` | Collation et extensions PostgreSQL — **à trancher au LOT 2, avant la première table** |
| `QO-113` | Conservation calendaire des journaux, LOT 13 |
| `QO-114` | **Jonathan n'a aucun droit d'administration sur cette machine.** À instruire avant le LOT 13 |
| `ECART-005`, `012`–`015` | Cinq écarts ouverts, tous rattachés à un lot ultérieur |
| `CONT-001` à `CONT-029` | 29 contenus au statut **`à relire`**. Aucun n'est publiable en l'état |

## 9.5 Les 7 critères de sortie de la porte `G1`

| | Critère | État |
|:--:|---|---|
| ☑ | Tous les services démarrent sur le Mac M5 | `T2`, `T6`, `T8`, **et depuis une machine RÉELLEMENT propre en `T9`** — 0 volume, 0 image, remontée en 34 s |
| ☑ | **Les images multiarchitectures sont construites** | **`T7` — lancées sur les deux, et `arm64` NATIF sur l'image publiée depuis `T8`** |
| ☑ | Aucun secret réel n'est présent | **vérifié automatiquement** depuis `T6`, avec témoin. **Ni `T7` ni `T8` n'ont créé de secret de dépôt** |
| ☑ | Une migration Alembic vide ou initiale s'exécute | `T3`, rejouée à chaque pull request, **et sur une base créée de zéro en `T9`** |
| ☑ | Les logs possèdent un identifiant de corrélation | `T4`, **et le nom de l'en-tête est partagé et vérifié depuis `T10`** |
| ☑ | **La CI bloque une erreur de lint, de test et de secret** | **`T6`, prouvé trois fois** |
| ☑ | Jonathan valide le socle | **VALIDÉ le 12/08/2026** — [checklist](docs/operations/checklist-validation-G1.md) instruite, tag `v0.1.0` posé sur `main`, contenu de `develop` porté par `main` |

**LES SEPT CRITÈRES SONT ACQUIS. La porte `G1` est franchie, et le LOT 1 est verrouillé.** Les
huit stories sont livrées, les 33 contrôles de sortie de `T11` sont à zéro, le tag `v0.1.0` est posé
sur `main` (`DEC-428`), et `main` porte le contenu de `develop` — arbres identiques, `9bc9359`.

> **Ne mets PAS « Porte des images multiarchitecture » dans les contrôles requis** de la protection
> de branche. Le workflow `images.yml` ne s'exécute **pas** sur les pull requests — le cahier §23.1
> l'interdit. Exigé comme contexte, il ne produirait jamais de statut et **bloquerait toute fusion
> pour toujours**, y compris pour Jonathan, `enforce_admins` étant actif.

## 9.6 Ce que le LOT 1 ne doit toujours pas faire

Créer une table métier, un modèle SQLAlchemy métier ou un type métier dans
`packages/contracts` · implémenter une authentification, même partielle, même de test ·
introduire un contournement de l'authentification · charger une donnée de collaborateur ·
exposer PostgreSQL, Redis, MinIO ou Mailpit ailleurs que sur `127.0.0.1` · référencer une image
par `latest` seul · introduire Kubernetes, une PWA, un fonctionnement hors ligne, Entra ID,
Graph, Teams ou MFA · réutiliser une ligne du prototype historique.

# 10. Cartographie du dépôt

```text
.
├── CLAUDE.md                    ← ce document. AGENTS.md est un lien symbolique, NON VERSIONNÉ
├── README.md · CONTRIBUTING.md
├── Makefile                     ← 50 cibles, paramétrées par ENVIRONNEMENT (T8, DEC-485)
├── .env.example                 ← v1.2, 79 variables, aucun secret (ECART-022)
├── .dockerignore                ← DEC-473. node_modules, .venv, caches, .env
├── .gitleaks.toml               ← regles taillees sur les formats de CE projet (T6)
├── .node-version · .python-version
├── package.json · pnpm-workspace.yaml    ← pnpm épinglé, store hors iCloud
├── pyproject.toml               ← workspace uv, Ruff, mypy strict, pytest
├── tsconfig.base.json · eslint.config.js · .prettierrc.json · .prettierignore
├── apps/
│   ├── api/      app/{configuration,entities,health,shared}, alembic/, tests/, Dockerfile
│                 app/modeles.py         ← importe TOUS les modeles (LOT 2, T2)
│                 app/shared/modele.py   ← socle declaratif (LOT 2, T1, DEC-499)
│                 app/{entities,people,clients}/ ← 12 tables (LOT 2, T2 a T6)
│                 alembic/versions/      ← 0001 vide, 0002 ext., 0003 entites,
│                                          0004 person, 0005 appartenance,
│                                          0006 metiers, 0007 clients
│   ├── worker/   worker/{main,journal}.py, tests/, Dockerfile
│   └── web/      index.html, vite.config.ts
│                 Dockerfile              ← 2 CIBLES depuis T7 (DEC-479)
│                 Caddyfile.execution     ← sert l'artefact statique, port 5173
│       └── src/  main.tsx · App.tsx · FrontiereErreur.tsx · styles.css
│                 api/sante.ts          ← client des 2 endpoints, 200 ET 503
│                 pages/PageStatut.tsx  ← les 5 états
├── packages/
│   ├── observabilite/    journal JSON, masquage, corrélation (DEC-466)
│   ├── ui/               design system (T10) — jetons RELEVES du prototype et
│   │                     RECALCULES contre WCAG 2.2 AA (DEC-491)
│   │                     contraste.ts · jetons.ts · jetons.css · composants.css
│   │                     Bouton · Badge · Carte, 90 tests
│   └── contracts/        contrat API partagé (T10, DEC-492)
│                         contrat-api.json  ← SOURCE UNIQUE, lue par TS ET Python
├── infra/
│   ├── compose/  base + surcouches dev ET recette (T8)
│   │             la surcouche NOMME sa cible de construction (DEC-479)
│   │             differences-recette.env  ← calque VERSIONNÉ, aucun secret
│   ├── caddy/    Caddyfile — monté PAR SON RÉPERTOIRE (DEC-472), tls internal
│   └── scripts/  exclure-icloud · verifier-{ports,persistance,sante,page-statut}
│                  verifier-documentation.py  ← empreintes, sequences, ET
│                                                totaux DÉRIVÉS (T8, DEC-488)
│                  verifier-images.py         ← 6 sous-commandes, controles de T7
│                  verifier-separations.py    ← les 7 separations du cahier 22.2,
│                                                l'artefact en marche, l'archi,
│                                                Mailpit, QO-085          (T8)
│                  composer-env.py            ← modele + calque + secrets (T8)
│                  epingler-images.py         ← make images-pin           (T8)
│                  Tous en Python : le motif est en §7.2
└── docs/
    ├── product/ · architecture/     ← IMMUABLES
    ├── decisions/                   ← 178 décisions, 30 écarts
    └── operations/                  ← fiche-lot-1, comptes rendus T0 à T11, registres
                                        checklist-validation-G1.md  ← T11, la porte
                                        exploitation-locale.md  ← T9, toutes commandes exécutées
```

`.github/` porte les gabarits d'issue et de pull request, et **deux workflows** :

| Workflow | Déclencheurs | Contenu |
|---|---|---|
| **`ci.yml`** (`T6`) | pull request **et** poussée sur `develop`/`main` | 3 tâches, les 11 contrôles du cahier §23.1, et **la porte que la protection de branche exige** |
| **`images.yml`** (`T7`) | poussée sur `develop`, tags `v*`, **et `workflow_dispatch`** | 4 tâches : publier, lancer sur 2 architectures, Trivy, porte. **Jamais sur une pull request** — cahier §23.1. Sa porte n'est **pas** et ne doit **pas** devenir un contrôle requis : voir §9.4 |

---

# 11. Démarrage type d'une session

```bash
export PATH="$HOME/.local/bin:$PATH"
git switch develop && git pull
git log --oneline -5
git status -sb
gh issue list --milestone G1 --state all

make icloud-verify        # PAS une formalite : voir §7.1
make env-check            # .env contre .env.example : 3 variables manquaient (ECART-022)
make check                # qualite complete, docs-check ET images-check compris
make audit                # pip-audit et pnpm audit (DEC-474)
make up                   # les 8 services, ET recharge Caddy (DEC-472)
make stack-check          # sante + ports
make api-check            # les 3 endpoints
make web-check            # la page vue comme un navigateur la voit
make code-check           # LOT 2 : le conteneur execute-t-il le code du depot ?
make alembic-check        # une seule tete de migration
make test-integration     # 8 tests sur services reels

# Images, si tu y touches. `images-build` construit amd64 EN EMULATION : c'est lent.
make images-check         # statique, aucun Docker requis
make images-build         # 3 images x 2 architectures, en local, puis manifestes et tailles
make images-verify        # LANCE les conteneurs sur les 2 architectures

# RECETTE, depuis T8. Elle TIRE les images publiees : `docker login ghcr.io` requis.
make up-recette           # les 8 services de recette, sur les images PUBLIEES
make recette-check        # sante, ports, coherence du .env, puis les 7 separations
make separations-check    # EXIGE que les DEUX stacks tournent (exception a DEC-440)
make images-pin           # deplace le pointeur d'images sans commit, derive de la publication
make down-recette         # arret, volumes conserves
```

> **La recette ne demarre pas sans authentification au registre, et c'est voulu.** Si `make
> up-recette` repond `unauthorized`, ce n'est pas une panne : c'est le garde-fou de `DEC-486` qui
> refuse de se rabattre sur une construction locale. Le remede est un `docker login ghcr.io` de
> Jonathan — **son action** :
>
> ```bash
> ~/.local/bin/gh auth token | docker login ghcr.io -u Jonathan2433 --password-stdin
> ```
>
> **Et si `make up-recette` echoue une fois sur `dependency failed to start` apres un demarrage
> interrompu, rejoue-le** : c'est le defaut `T8-4`, diagnostique et non corrige. Compose evalue le
> verdict PERIME d'un conteneur laisse `unhealthy` au lieu d'attendre l'intervalle de sonde suivant.

**Et regarde l'integration continue**, qui existe depuis `T6` et qui **bloque** :

```bash
gh run list --limit 5
gh pr checks <numero>
```

Si Docker ne répond pas : `open -a Docker`, puis attendre. Il s'est arrêté seul une fois pendant
ce lot.

1. Lire ce document.
2. Lire [`docs/README.md`](docs/README.md) : quelle porte, quel prochain identifiant.
3. Lire [`fiche-lot-1.md`](docs/operations/fiche-lot-1.md) : la sous-étape en cours.
4. Lire le **compte rendu de la sous-étape précédente** — `T10` — pour savoir ce qui a été laissé
   ouvert. Son §3 dit ce qui n'est **pas** couvert et pourquoi, son §6 l'événement extérieur qui a
   fermé `ROAD-RSK-032`, son §7 les quatre défauts, et son §8 les six recommandations.
5. Lire [`exploitation-locale.md`](docs/operations/exploitation-locale.md) : lancement, arrêt,
   réinitialisation et **neuf symptômes de diagnostic réellement rencontrés**. Toutes ses commandes
   ont été exécutées.
5. Vérifier l'état réel par `git`, `gh` et les mesures, **pas par ce que la doc affirme**. §9.0
   donne un exemple récent où ce document se trompait sur l'architecture.
6. Exécuter **une** sous-étape, contrôler, rapporter, attendre la validation.

Contrôle d'hygiène utile à tout moment :

```bash
git ls-files | grep -Ei '\.(csv|env|pem|key|mp4|html)$'   # 2 attendus, voir ci-dessous
git ls-files | grep -c 'V1.html'                          # doit valoir 0
git status --short                                        # doit être vide
```

Le premier montre **deux** fichiers, et les deux sont légitimes : le CSV explicitement fictif, et
**`apps/web/index.html`**, point d'entrée imposé par Vite depuis `T5`. Le filtre visait le
prototype ; `.gitignore` ne vise que `docs/prototype/V1.html`, jamais `*.html`. **Toute troisième
entrée est une anomalie.**

---

# 12. Une dernière chose

Jonathan valide vite et lit sérieusement. Ce qui fonctionne avec lui :

- des rapports **denses mais courts**, avec les chiffres réels et non des approximations ;
- **signaler ses propres erreurs** dès que les contrôles les révèlent, sans les enjoliver. Les
  63 défauts sont documentés, y compris le trou de sécurité que j'avais laissé dans mon propre
  filtre de masquage, les **six** fois où j'ai conclu sur un code de sortie qui n'était pas celui
  que je croyais lire, et l'**empreinte SHA-256 inventée** que `T7` a écrite dans un workflow avant
  de la remplacer par la valeur mesurée. En `T5`, **cinq défauts sur huit étaient dans mes
  contrôles** ; en `T7`, **dix sur treize** — c'est la forme la plus insidieuse : on croit avoir
  prouvé. En `T6` **et** en `T7`, j'ai rejoué une leçon **écrite dans ce document** : un piège
  documenté n'est pas un piège désarmé. La parade de `T7` a été de **changer d'outil** plutôt que de
  promettre plus de vigilance ;
- distinguer nettement **ce qui est prouvé** de **ce qui est recommandé** ;
- dire ce qui **n'est pas** couvert, plutôt que de le laisser croire. La conservation de 30 jours
  des journaux n'est pas faite, et `QO-113` le dit ;
- lui donner à chaque fois la commande de fusion **et** celle de retour arrière ;
- ne rien pousser vers l'extérieur sans son accord ;
- **reformuler sans jargon** quand il dit ne pas comprendre une question. C'est arrivé deux fois,
  et les deux fois c'était ma question qui était mauvaise, pas sa lecture.

Le projet a une exigence de traçabilité inhabituellement élevée : 178 décisions, et un compte
rendu par sous-étape qui consigne jusqu'aux défauts de mes propres contrôles. Ce n'est pas de la
bureaucratie. C'est ce qui permettra, au LOT 9, de justifier chaque ligne rejetée d'un import de
données personnelles réelles — et, plus tôt, de ne pas refaire quatre fois la même erreur de
tuyau. **Tiens les registres à jour dans la même pull request que le travail — jamais après.**
