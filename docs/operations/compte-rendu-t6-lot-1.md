# Compte rendu — sous-étape `T6` du LOT 1

**Exécutée le :** 29 juillet 2026
**Objet :** intégration continue GitHub Actions — les 11 contrôles du cahier §23.1, dont **trois échecs volontaires prouvés**
**Story :** `MVP-L01-US005`, issue [#6](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/6)
**Fondement :** cahier §23.1 à §23.5 ; roadmap LOT 1, critères de sortie ; conventions Git §2 ; `ROAD-RSK-029`, `ROAD-RSK-015`, `ECART-018`, `ECART-021`
**Décisions produites :** `DEC-474` à `DEC-477`
**Risque ouvert :** `ROAD-RSK-032` · **Question ouverte :** `QO-114`

---

## 1. Critère de sortie, et ce qui le prouve

> « Les 11 contrôles sont exécutés ; le pipeline passe ; et il **échoue effectivement** sur une
> erreur de lint, une erreur de test et un secret introduits volontairement. » — fiche §3
>
> « La CI **bloque** volontairement une erreur de lint, de test et de secret. » — roadmap,
> critère de sortie du LOT 1

**C'était le test le plus important du lot, parce qu'il exigeait de prouver l'échec et non le
succès.** Un pipeline vert ne démontre rien : il faut montrer qu'il sait devenir rouge, et que le
rouge **empêche** de fusionner.

| Volet | Preuve | Résultat |
|---|---|---|
| Les 11 contrôles sont exécutés | Énumérés dans le workflow et nommés dans les étapes | **11/11** |
| Le pipeline passe | Exécution [30433268640](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/actions/runs/30433268640) | **vert** |
| Il échoue sur une erreur de **lint** | Exécution [30433558925](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/actions/runs/30433558925), étape `10. 2 · Lint` | **rouge**, fusion `BLOCKED` |
| Il échoue sur une erreur de **test** | Exécution [30433745189](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/actions/runs/30433745189), étape `12. 4 · Tests unitaires` | **rouge**, fusion `BLOCKED` |
| Il échoue sur un **secret** | Exécution [30433971315](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/actions/runs/30433971315), étape `14. 9 · Detection de secrets` | **rouge**, fusion `BLOCKED` |

**Chaque défaut a été introduit seul**, le précédent retiré, pour que l'échec soit attribuable à
un contrôle précis et non à un cumul. Le tout dans une pull request jetable, `#19`, fermée sans
fusion et sa branche supprimée — sur arbitrage de Jonathan entre trois façons de le prouver.

**Le témoin positif est ce qui rend les trois échecs concluants :** la même porte, sur la branche
de `T6`, laisse la pull request `MERGEABLE` / `CLEAN`. Elle distingue donc un succès d'un échec.

> **Une précision de vocabulaire GitHub qui compte.** Le champ `mergeable` ne dit rien de la
> porte : il ne parle que de l'absence de conflit, et vaut `MERGEABLE` même sur une pull request
> refusée. C'est **`mergeStateStatus`** qui fait foi, et il vaut `BLOCKED` dans les trois cas.
> Conclure sur `mergeable` aurait produit un contrôle menteur de plus.

Le secret du troisième témoin était **engendré au hasard, à usage unique, employé nulle part**, et
la branche qui le portait est supprimée.

---

## 2. Ce qui a été livré

| Emplacement | Contenu |
|---|---|
| `.github/workflows/ci.yml` | Trois tâches : **qualité**, **stack**, **porte**. Les 11 contrôles y sont **énumérés**, pas comptés |
| `.gitleaks.toml` | Règles propres au projet, en plus des règles par défaut. Liste blanche **étroite** |
| `infra/scripts/verifier-documentation.py` | Empreintes des documents immuables **et** cohérence des séquences d'identifiants |
| `Makefile` | 4 cibles : `docs-check`, `audit`, `alembic-check`, `test-frontend`. **37 cibles** au total |
| `pnpm-workspace.yaml` | `auditConfig.ignoreGhsas` — une tolérance nommée, motivée par la mesure |
| `pyproject.toml`, `uv.lock` | `pip-audit` ajouté aux dépendances de développement |
| Protection de `develop` et `main` | Contrôle requis **« Porte de l integration continue »**, `strict` actif |

### 2.1 Les onze contrôles, et où chacun s'exécute

| # | Contrôle du cahier §23.1 | Commande | Tâche |
|---:|---|---|---|
| 1 | formatage | `make format-check` | qualité |
| 2 | lint | `make lint` | qualité |
| 3 | typage | `make typecheck` | qualité |
| 4 | tests unitaires | `make test-unit` | qualité |
| 5 | tests d'intégration PostgreSQL | `make test-integration` | stack |
| 6 | tests API | `make api-check` | stack |
| 7 | tests frontend | `make test-frontend` | qualité |
| 8 | contrôle Alembic | `make migrate` + `make alembic-check` | stack |
| 9 | détection de secrets | Gitleaks 8.30.1 | qualité |
| 10 | audit de dépendances | `make audit` | qualité |
| 11 | construction des images | `make up` | stack |

**Deux contrôles s'y ajoutent**, recommandés par le lot et devenus effectifs ici :
`make docs-check` recalcule les **cinq empreintes SHA-256** des documents immuables
(`ROAD-RSK-029`) et confronte les marqueurs « prochain identifiant libre » au **maximum
réellement en usage** (`ECART-021`). Le second a servi dès sa première utilisation : il a refusé
la présente sous-étape tant que l'index de `docs/README.md` n'était pas à jour.

### 2.2 Le `Makefile` est resté le point d'entrée, et c'était l'intention de `T1`

Aucune commande d'outil n'est écrite en dur dans le workflow, à la seule exception de Gitleaks,
qui n'existe pas en local. Le pipeline appelle des cibles `make`, et **tout ce qu'il exécute est
reproductible à l'identique sur la machine de Jonathan**. C'est ce que le commentaire de `T1`
annonçait — « deviendra celui de la CI en `T6` » — et ce qui a permis de trouver deux défauts en
local plutôt qu'en poussant à l'aveugle.

### 2.3 Ce que `T6` n'a pas fait, et ne devait pas faire

Aucune publication dans GHCR — c'est `T7`, et le `GITHUB_TOKEN` en lecture seule suffisait ici.
**Aucun secret de dépôt n'a été créé.** Aucune analyse d'image par Trivy : elle porte sur des
images publiées, donc `T7`. Aucun déploiement : le cahier §23.1 est explicite, « aucun
déploiement ne part d'une pull request ».

---

## 3. Ce qui n'est PAS couvert par la CI, et il faut le dire

1. **`make persistence-test`** — la survie des volumes à un redémarrage. Elle est éprouvée à
   chaque sous-étape en local, elle ne figure pas parmi les onze contrôles du cahier, et elle
   coûterait deux cycles complets de la stack à chaque pull request.
2. **`pnpm peers check`** — hors des onze, et il échouerait sur `eslint-plugin-jsx-a11y`, dont
   `T5` a prouvé par témoin qu'il fonctionne malgré une déclaration de compatibilité ESLint
   périmée. L'ajouter serait ajouter une fausse alarme permanente.
3. **Les nombres cités en prose** — « 139 tests », « 33 330 lignes ». `docs-check` vérifie les
   marqueurs d'identifiants et les empreintes, pas la narration : ces nombres changent à chaque
   commit, et un contrôle qui échouerait sur la description d'un document par lui-même finirait
   désactivé. La parade reste humaine.
4. **La mesure de deux environnements simultanés** — `QO-085`, qui relève de `T8`.

---

## 4. Durée et consommation

| Tâche | Durée | Contenu |
|---|---:|---|
| Qualité et sécurité | **1 min 08** | 7 contrôles, sans aucun service |
| Stack réelle | **1 min 57** | 8 services construits et démarrés, 4 contrôles |
| Porte | 5 s | récapitulatif et verdict |
| **De bout en bout** | **~2 min 20** | les deux tâches en parallèle |

Le découpage en deux tâches n'est donc pas décoratif : le retour qualité arrive en une minute,
sans attendre la construction des images. Aucun cache de dépendances JavaScript n'a été mis en
place à ce stade — une piste d'optimisation si la consommation de minutes devenait un sujet.

---

## 5. Contrôles exécutés, et leurs témoins

**Neuf témoins négatifs, tous concluants.** Trois sont les échecs volontaires exigés ; les six
autres éprouvent les contrôles que `T6` a lui-même ajoutés.

| Maillon | Défaut injecté ou action réelle | Résultat |
|---|---|---|
| Lint en CI | import inutilisé, Ruff F401 | rouge, `BLOCKED` |
| Tests en CI | assertion faussée | rouge, `BLOCKED` |
| Détection de secrets en CI | secret plausible dans un document Markdown | rouge, `BLOCKED` |
| Empreintes des documents immuables | une empreinte de **référence** faussée d'un caractère | échec, écart affiché |
| Cohérence des séquences | marqueur porté à `ROAD-RSK-099` | échec, écart nommé |
| Audit de dépendances | identifiant d'avis bidon à la place du vrai | l'audit rééchoue |
| Gitleaks, couverture réelle | **5 secrets plausibles plantés** aux formats du projet | **5/5 attrapés** |
| `make up` sur machine propre | volume MinIO supprimé | échec reproduit, puis corrigé |
| Majuscule de l'énumération | correction retirée | le nouveau test échoue |

Le septième mérite d'être détaillé, parce qu'il applique la leçon de `T4-1`. Les cinq formes
plantées étaient celles que **ce projet produit réellement** : `APP_SECRET_KEY`,
`POSTGRES_PASSWORD` et `REDIS_PASSWORD` avec des valeurs de 48 et 32 caractères comme `make env`
en engendre, une URL `postgresql://onboarding:…@db:5432/…` et une URL **`redis://:…@redis:6379/0`
sans nom d'utilisateur** — exactement le format qui avait trompé le filtre de masquage en `T4`.
Les cinq sont détectées. En sens inverse, le dépôt réel et ses 21 commits ne produisent **aucune**
détection.

---

## 6. Défauts détectés pendant `T6`

**Huit défauts. Trois étaient dans mes propres contrôles ou ma propre configuration**, deux
dormaient dans le `Makefile` depuis `T2`, un est un piège d'environnement, un est une erreur de
raisonnement évitée par la mesure, et un est un défaut de rédaction visible seulement à l'écran.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T6-1` | `make env` employait **`sed -i ''`**, la forme BSD de macOS. GNU sed lit alors le script comme un nom de fichier et sort en **code 2** : « can't read s|^APP_SECRET_KEY… ». Mesuré sur GNU sed 4.9 | **Défaut dormant depuis `T2`**, invisible tant que le `Makefile` n'avait jamais tourné sur Linux. Il cassait toute la tâche « stack » | Forme portable, `sed … > fichier.tmp && mv`. Vérifiée sur macOS aussi : 5 variables renseignées, 2 `CHANGE_ME` volontaires, aucun temporaire laissé. C'est le piège documenté en `CLAUDE.md` §7.12 |
| `T6-2` | **`make up` n'avait jamais fonctionné sur une machine sans volume MinIO préexistant.** La sonde `ready` fait un `head_bucket` ; sans bucket elle répond 503, `api` n'est jamais sain, et `up --wait` échoue. Or le bucket n'était créé qu'**après** cette attente | **Le défaut le plus important de la sous-étape.** Il aurait fait échouer le critère de `T9`, « les procédures fonctionnent depuis une machine propre ». Invisible en local, le volume survivant à `make down` | Démarrage en deux temps, `DEC-477`. Reproduit localement en supprimant le **seul** volume MinIO — `caddy-data` préservé pour ne pas invalider l'approbation de la racine dans le trousseau — puis corrigé et revérifié depuis le même état |
| `T6-3` | **Linux ne résout pas les sous-domaines de `.localhost`**, contrairement à macOS. Mesuré dans un conteneur Linux réel : `gaierror, No address associated with hostname`, alors que `localhost` seul se résout | **Piège d'environnement.** `api-check` et `web-check` auraient échoué faute de résolution de nom, et non par défaut du livrable — le diagnostic aurait pu coûter cher | Deux lignes dans `/etc/hosts` de l'exécuteur, **suivies d'un `getent` qui échoue si la résolution ne marche pas** : l'étape ne se contente pas d'écrire |
| `T6-4` | Mon contrôle de cohérence des séquences annonçait un écart sur `ROAD-RSK` : maximum en usage `024` alors que `031` existe. Mon extracteur ne lisait que les identifiants en **première colonne de tableau**, or les risques `025` à `031` sont documentés en **titres de section** | **Faux positif de mon propre contrôle.** Un contrôle qui échoue pour une raison de mise en forme finit désactivé, donc ne prouve rien | Les deux formes déclaratives sont reconnues. Les mentions en **prose** restent ignorées — la fiche de `ECART-021` cite `DEC-451`, et un relevé naïf l'aurait comptée |
| `T6-5` | J'ai déclaré `auditConfig` dans **`package.json`** : sans effet, `pnpm audit` continuait de sortir en 1. **pnpm 11 lit ses réglages d'espace de travail depuis `pnpm-workspace.yaml`** | **Leçon `T1-3` rejouée**, alors qu'elle est écrite dans ma propre passation §7.10 pour `storeDir` et `engineStrict`. La classe ne s'est pas refermée, elle s'est déplacée d'une clé à l'autre | Réglage porté dans `pnpm-workspace.yaml`. La sortie affiche « 1 high (**1 ignored**) » : la tolérance est visible, non silencieuse |
| `T6-6` | Mes règles Gitleaks laissaient passer **neuf faux positifs** que leurs listes blanches auraient dû écarter. Cause : une liste blanche de règle est comparée par défaut au **secret capturé**, jamais à la ligne — mes motifs, écrits sur l'URL entière, ne pouvaient correspondre à rien | **Configuration inopérante**, détectée parce que j'ai mesuré au lieu de pousser | `regexTarget = "match"`, et des exceptions distinctes pour les gabarits d'interpolation `{…}` et les valeurs de test. Puis les deux sens éprouvés |
| `T6-7` | J'ai failli corriger `GHSA-mh99-v99m-4gvg` en forçant `brace-expansion@5.0.8`. **Mesure : son export CommonJS est un objet portant `.expand`, non une fonction appelable**, alors que `minimatch@3.1.5` fait `expand(motif)` | **Erreur de raisonnement évitée par la mesure.** Le « correctif évident » aurait remplacé un déni de service théorique par la neutralisation **certaine** d'ESLint, donc de `jsx-a11y`, motif déterminant de `DEC-451` | Tolérance nommée et étroite, `DEC-474`, avec `ROAD-RSK-032` pour ne pas l'oublier et un déclencheur de réévaluation |
| `T6-8` | La page de statut affichait « L'API sonde trois dépendances. **le** worker Dramatiq, Mailpit et Caddy… » — minuscule après un point | **Défaut de rédaction visible seulement à l'écran.** Le test de `T5` cherchait `toContain('worker Dramatiq')`, ce qui passe quelle que soit la grammaire : **un test insensible au défaut ne le trouve jamais** | Majuscule initiale, et un test qui vérifie la phrase entière. Éprouvé : sans la correction, le nouveau test échoue |

### 6.1 Ce que ces huit défauts enseignent

**`T6-1` et `T6-2` disent la même chose et c'est la leçon centrale de cette sous-étape :** un
outillage qui n'a jamais tourné que sur une seule machine, dans un seul état, n'est pas éprouvé.
Le `Makefile` fonctionnait depuis `T1` — sur macOS, avec des volumes déjà peuplés. Les deux
premiers défauts n'étaient pas des régressions : c'étaient des **conditions jamais rencontrées**.
L'intégration continue les a révélées en une seule exécution, et c'est précisément ce qu'on
attendait d'elle. `T6-2` aurait autrement attendu `T9` pour se manifester, sur le critère
« depuis une machine propre » — et là il aurait fallu comprendre pourquoi la stack ne démarre pas
chez quelqu'un d'autre.

**`T6-5` est le plus humiliant, et le plus instructif sur la nature de ces classes de défauts.**
La leçon était écrite noir sur blanc dans ma passation, pour une autre clé du même fichier, et je
l'ai quand même rejouée. Un piège documenté n'est pas un piège désarmé : il faut se demander
**à chaque réglage** où l'outil le lit vraiment, et le vérifier.

**`T6-7` ajoute une nuance à la règle du lot.** Jusqu'ici la discipline portait sur les contrôles :
peuvent-ils échouer, discriminent-ils, combien d'éléments ont-ils examinés. `T6-7` porte sur les
**corrections** : la remédiation évidente d'un problème réel peut être pire que le problème. Le
seul moyen de le savoir était d'installer la version prétendument corrective et de l'appeler.

> **La règle du lot, augmentée d'une cinquième proposition :**
> avant d'appliquer un correctif, mesurer **ce que le correctif casse**. Un avis de sécurité
> désigne un problème, jamais une solution.

---

## 7. État à la sortie de `T6`

| | |
|---|---|
| Sous-étape | **`T6` terminée.** Story `MVP-L01-US005` prête pour validation, issue `#6` à refermer à la fusion |
| Décisions | `DEC-474` à `DEC-477`. Prochaine libre : **`DEC-478`** |
| Écarts | Aucun nouveau. Prochain libre : `ECART-022` |
| Risques | **`ROAD-RSK-032` ouvert**, résiduel accepté. Prochain libre : **`ROAD-RSK-033`** |
| Questions | **`QO-114` ouverte** — droits d'administration pour le LOT 13. Prochaine libre : `QO-115` |
| Tests | **166** — 139 pytest (131 unitaires, 8 d'intégration) et 27 Vitest |
| Cibles `Makefile` | **37** |
| Protection des branches | `develop` **et** `main` : contrôle requis, `strict`, `enforce_admins`, 0 approbation |
| `make check` · `stack-check` · `api-check` · `web-check` · `test-integration` · `docs-check` · `audit` · `alembic-check` | Tous **code 0** |

### Les 7 critères de la porte `G1`

| | Critère | État |
|:--:|---|---|
| ☑ | Tous les services démarrent sur le Mac M5 | `T2`, et **aussi sur une machine propre** depuis `T6` |
| ☐ | Les images multiarchitectures sont construites | **`T7`** — construites en CI depuis `T6`, mais ni multiarchitecture ni publiées |
| ☑ | Aucun secret réel n'est présent | **désormais vérifié automatiquement**, avec témoin |
| ☑ | Une migration Alembic vide ou initiale s'exécute | `T3`, et rejouée à chaque pull request |
| ☑ | Les logs possèdent un identifiant de corrélation | `T4` |
| ☑ | **La CI bloque volontairement une erreur de lint, de test et de secret** | **`T6`, prouvé trois fois** |
| ☐ | Jonathan valide le socle | `T11` |

**La démonstration attendue par la roadmap est satisfaite à 6 sur 6.** Les quatre critères
d'empêchement du backlog §12 devenus applicables au LOT 1 le sont également, dont « aucun secret
ni donnée réelle versionné — désormais vérifié **automatiquement** par Gitleaks ».

### Ce qui attend `T7`

Images multiarchitecture `linux/amd64` et `linux/arm64`, publiées dans GHCR privé. Story
`MVP-L01-US006`, issue `#7`. Quatre éléments de `T6` y entrent directement :

- le workflow **construit déjà** les images, il reste à les construire pour deux architectures et
  à les publier — ce qui demandera les **premières permissions d'écriture** du projet
  (`packages: write`) et, cette fois, un jeton ;
- **`ROAD-RSK-030`** — image `web` de **1,02 Gio** — et **`ROAD-RSK-031`** — elle exécute le
  serveur de développement — se traitent tous deux par le `Dockerfile` multi-étapes de `T7` ;
- **Trivy** y devient pertinent, les images étant publiées ;
- `DEC-477` impose un ordre de démarrage que la surcouche de recette de `T8` devra reproduire.
