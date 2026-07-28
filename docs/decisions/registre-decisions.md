# Registre des décisions

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Dernière mise à jour :** 28 juillet 2026, sous-étape `T5` du LOT 1
**Règles de tenue :** [README.md](README.md)

Ce registre est la vue unique des décisions du projet. Il **reprend** sans les altérer les
85 décisions et arbitrages présents dans les documents validés, et **ajoute** les décisions
prises pendant la réalisation à partir de `DEC-418`.

| Origine | Nombre | Statut |
|---|---:|---|
| Décisions de droits `RIGHTS` | 25 | Validées le 25/07/2026 |
| Décisions de modèle `DATA` | 18 | Validées le 25/07/2026 |
| Décisions de roadmap `ROAD` | 12 | Validées le 25/07/2026 |
| Décisions de backlog `BACKLOG` | 10 | Validées le 25/07/2026 |
| Arbitrages `ARB-*` | 20 | Validés le 25/07/2026 |
| **Total repris** | **85** | |
| Décisions de réalisation `DEC-418+` | 21 | Validées le 27/07/2026 |
| Arbitrages techniques `DEC-439+`, sous-étape `T0` | 10 | Validés le 27/07/2026 |
| Mise en place GitHub `DEC-449` | 1 | Validée le 27/07/2026. **Remplace `DEC-448`** |
| Ouverture du LOT 1 `DEC-450` | 1 | Validée le 27/07/2026 |
| Réalisation du LOT 1 `DEC-451+`, sous-étape `T1` | 7 | Validées les 27 et 28/07/2026 |
| Réalisation du LOT 1 `DEC-458+`, sous-étape `T2` | 4 | Validées le 28/07/2026 |
| Réalisation du LOT 1 `DEC-462+`, sous-étape `T3` | 4 | Validées le 28/07/2026 |
| Réalisation du LOT 1 `DEC-466+`, sous-étape `T4` | 4 | Validées le 28/07/2026 |
| Réalisation du LOT 1 `DEC-470+`, sous-étape `T5` | 4 | Soumises le 28/07/2026 |
| **Total** | **141** | |

---

# 1. Décisions de réalisation — `DEC-418` et suivantes

Toutes validées par Jonathan le 27 juillet 2026, lot 0, sous-étapes S1 à S8.

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-418` | Le dépôt local réside dans le dossier iCloud Drive du projet, `~/Library/Mobile Documents/com~apple~CloudDocs/CODE/ONBOARDING_DIGITAL`. | Choix de Jonathan après exposition du risque. Emplacement de travail habituel. | Validée |
| `DEC-419` | Le dépôt distant est `Jonathan2433/ONBOARDING_DIGITAL`, privé, sur le compte personnel de Jonathan. | Dépôt déjà créé par Jonathan. Caractère privé confirmé par lui le 27/07/2026. | Validée |
| `DEC-420` | Le prototype `V1.html` est conservé dans `docs/prototype/` pour historisation, et **exclu du suivi Git**. | Historisation souhaitée, mais le fichier contient des données personnelles réelles et un mot de passe en clair. Le versionner rendrait la porte `G0` invalidable. | Validée |
| `DEC-421` | Le dossier documentaire est nommé `docs` en minuscules, avec les sous-dossiers `product`, `architecture`, `decisions`, `operations`, plus `prototype`. | Exigence littérale de la roadmap. Le système de fichiers étant insensible à la casse, `DOCS` a été renommé en deux temps. | Validée |
| `DEC-422` | Les 85 décisions et arbitrages consolidés font foi comme registre décisionnel. La plage `DEC-001` à `DEC-417` est **réservée** pour un import ultérieur sans conflit. Les décisions de réalisation démarrent à `DEC-418`. | La table `DEC-001..417` n'est présente dans aucun document du corpus (`ECART-004`). Cette formulation préserve les deux issues possibles. | Validée |
| `DEC-423` | Jonathan valide le cahier des charges v1.0 le 27/07/2026, **sans modification du fichier**. Le statut faisant foi est celui de ce registre et de l'index `docs/README.md`. | Valider n'est pas une évolution de contenu : le cahier §35 n'exige donc aucun changement de version. L'immuabilité du fichier préserve la preuve d'intégrité par empreinte SHA-256. | Validée |
| `DEC-424` | L'identité Git personnelle `jonathan.dupau24@gmail.com` est conservée pour ce dépôt. | Le dépôt appartient au compte personnel de Jonathan : la cohérence est défendable. `ECART-009` clos en risque accepté. | Validée |
| `DEC-425` | Répartition documentaire : `docs/product/` reçoit le cahier des charges, la matrice des droits, la roadmap et le backlog ; `docs/architecture/` reçoit le modèle de données. | `product/` porte le quoi et le quand, `architecture/` porte le comment technique. La matrice est d'abord un arbitrage métier. | Validée |
| `DEC-426` | Les cinq documents validés conservent leur nom d'origine en majuscules. Les documents produits par le projet utilisent le kebab-case minuscule. | Préserve la traçabilité avec le prompt de cadrage et les références croisées internes. | Validée |
| `DEC-427` | Le circuit branche + pull request s'applique à partir du **premier commit de code du LOT 1**. Les sous-étapes documentaires du LOT 0 restent en commits directs sur `main`, chacune validée explicitement par Jonathan. | Au LOT 0 aucune intégration continue n'existe : une pull request n'y vérifierait rien automatiquement. La revue est portée par la validation de sous-étape. | Validée |
| `DEC-428` | Versionnement sémantique préfixé `v`, jalonné sur les portes : `v0.1.0` à `G1` … `v0.13.0` à `G13`, puis **`v1.0.0` à l'ouverture générale `G14`**. `G0` ne produit aucun tag. `PATCH` pour une correction sur un lot validé. | Le numéro mineur devient un indicateur d'avancement. `v1.0.0` signale sans ambiguïté le premier logiciel réellement ouvert à tous. La production temporaire n'est pas la production générale. | Validée |
| `DEC-429` | `main` est protégée : pull request obligatoire, **zéro approbation requise**, rejet des push directs et forcés. Les contrôles d'intégration deviendront bloquants au LOT 1. | GitHub interdit d'approuver sa propre pull request. Exiger une approbation bloquerait toute fusion tant que Jonathan est l'unique relecteur — objet de `QO-094`. | Validée |
| `DEC-430` | Les 12 risques du cahier des charges §33, jusqu'ici sans identifiant, deviennent `ROAD-RSK-013` à `ROAD-RSK-024`, sans modification de leur libellé. Les risques nouveaux démarrent à `ROAD-RSK-025`. | Un registre sans identifiant est inexploitable et non référençable dans une pull request. Une seule séquence de risques pour tout le projet. | Validée |
| `DEC-431` | Création des séquences `ECART-nnn` pour les écarts et `DEP-nnn` pour les dépendances externes. | `MVP-L00-US006` exige un registre de dépendances portant responsable, échéance, impact, statut et caractère bloquant. Une dépendance n'est ni une question ni un risque. | Validée |

| `DEC-432` | Le CSV collaborateurs utilise le séparateur `;` et l'encodage UTF-8. La virgule est tolérée si elle est détectée de façon non ambiguë, et le séparateur retenu est consigné au rapport d'import. Un BOM est retiré à la lecture et jamais propagé. | Les noms et présentations contiennent des virgules, pas des points-virgules : le besoin de guillemets et donc le risque de saisie diminuent. C'est aussi le format produit nativement par Excel en locale française. | Validée |
| `DEC-433` | Le CSV porte un champ `autorisation_photo` à trois valeurs `oui`, `non`, `inconnu`, avec **`inconnu` par défaut**. Sans autorisation active, aucune photo n'est publiée et l'avatar neutre est utilisé. | Le cahier §21.2 exige une autorisation explicite. `non` et `inconnu` produisent le même affichage mais se distinguent au registre, distinction nécessaire au traitement de `QO-098`. | Validée |
| `DEC-434` | Le schéma du CSV définit des **champs logiques** `F01` à `F19`, indépendants de tout intitulé de colonne. Les en-têtes du fichier réel sont associées à ces champs par un **profil de correspondance versionné**, enregistré avec le lot d'import aux côtés de l'empreinte et du séparateur. | La nomenclature des en-têtes est en suspens (`QO-110`), la source de données n'étant pas connue. Ce découplage est de toute façon nécessaire : les en-têtes du fichier réel ne correspondront pas à des intitulés inventés à l'avance. | Validée |
| `DEC-435` | Imputation des anomalies portant sur plusieurs lignes. **Doublon d'identifiant** : la première occurrence du fichier est retenue, les suivantes seules sont rejetées. **Conflit d'attribution métier** — Booster, responsables de bureau : toutes les lignes du groupe sont rejetées, aucune n'est retenue. **Homonymie** : les deux lignes attendent une décision. **Rapprochement de client** : seule la ligne portant la variante non reconnue est signalée. | Sans ces règles, une ligne correcte serait rejetée par ricochet. Désigner un Booster par l'ordre d'apparition dans un fichier serait une décision métier arbitraire ; conserver la première occurrence d'un e-mail est en revanche déterministe et tracé. | Validée |

| `DEC-436` | Création de la séquence `CONT-nnn` pour les éléments de contenu éditorial inventoriés. Chaque élément porte un identifiant stable, un propriétaire de relecture et un statut parmi `à relire`, `validé`, `à réécrire`, `écarté`. | L'inventaire du prototype doit être référençable story par story au LOT 6 et au LOT 7. Sans identifiant, un contenu relu ne peut pas être relié à sa validation ni à sa publication. Même motif que `DEC-431` pour les écarts et les dépendances. | Validée |

| `DEC-437` | La story `MVP-L00-US005`, priorité `P1`, est **validée au statut `à relire`**. Les 29 contenus inventoriés sont tracés et attribués à Léa, Tess et Diane ; leur relecture est portée au LOT 6, story `MVP-L06-US007`. La porte `G0` peut être franchie sans attendre cette relecture. | Option (a) retenue par Jonathan le 27/07/2026, parmi les trois possibles. La relecture dépend de trois personnes et n'est pas réalisable dans le LOT 0. La priorité `P1` autorise cet arbitrage explicite (`ARB-BACK-001`), et l'exigence n'est pas perdue puisque chaque élément porte un propriétaire et un statut. | Validée |

| `DEC-438` | **Jonathan valide la porte `G0` le 27 juillet 2026.** Le LOT 0 est terminé et **verrouillé**. Les 105 décisions du registre, les conventions Git et de versions, le schéma CSV `1.0-initiale`, la politique de configuration et de secrets, et l'état des 5 registres deviennent la référence opposable du projet. | Cinquième critère de sortie du LOT 0 satisfait. Les quatre autres étaient prouvés par les contrôles de la sous-étape S8. Conformément à `ROAD-003` et `ARB-BACK-003`, le plan du LOT 1 peut désormais être préparé, mais aucun travail du LOT 1 ne commence avant son ouverture explicite. | Validée |

## 1.1 Arbitrages techniques du LOT 1 — sous-étape `T0`

Validés par Jonathan le 27 juillet 2026, **avant l'ouverture du LOT 1**. `T0` ne produit aucun
code : elle lève les 3 prérequis de la [fiche du LOT 1](../operations/fiche-lot-1.md) §9.1 et
tranche les 7 choix techniques de §9.2, qu'aucun document validé ne fixait.

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-439` | Les répertoires `node_modules/` et le cache de paquets sont **exclus de la synchronisation iCloud**. Le dépôt lui-même **reste** dans iCloud Drive. Le store `pnpm` est placé hors du dossier synchronisé. | Mesure du 27/07/2026 : les volumes Docker nommés résident déjà dans l'image disque de la VM, sous `~/Library/Containers/`, **hors iCloud**. Le risque `ROAD-RSK-026` ne portait donc réellement que sur les dépendances. Exclure les seuls artefacts lourds préserve `DEC-418` sans la rouvrir. Clôt `QO-109`. | Validée |
| `DEC-440` | Les trois environnements ne sont **jamais exécutés simultanément**. Des limites mémoire sont fixées par service. Le projet tiers `observatoire-ecom-studio` est **arrêté pendant la durée du LOT 1**. | Mesure du 27/07/2026 : Docker Desktop ne dispose que de **7,75 Gio** sur les 16 Gio de la machine, et le projet tiers en consommait **~1,93 Gio**, soit 25 % du budget, dont 1,77 Gio pour son seul worker. Le cahier §22.2 exige des ressources **distinctes** entre environnements, il n'exige nulle part leur simultanéité. Voir `ROAD-RSK-027` réécrit. | Validée |
| `DEC-441` | Le monorepo JavaScript utilise **`pnpm` workspaces**. Aucun orchestrateur de tâches — ni Turborepo, ni Nx — n'est introduit au LOT 1 : le `Makefile` tient ce rôle. | Store partagé et arborescence non aplatie : nettement moins de fichiers à exclure d'iCloud, et dépendances fantômes impossibles dans un monorepo à 5 paquets. Cohérent avec `DEC-439`, qui sort le store du dossier synchronisé. Un orchestrateur apporterait un cache dont le socle n'a pas encore l'usage. | Validée |
| `DEC-442` | Le vérificateur de types Python est **`mypy`, en mode strict**. | Le cahier §23.5 cite `mypy` **ou** `pyright` sans trancher. `mypy` s'installe dans le même environnement `uv` que le reste de l'API : une seule chaîne d'outils, un seul verrouillage de versions, comportement identique en local et en intégration continue. `pyright` imposerait Node dans le job Python et dans l'image API. SQLAlchemy 2.x étant nativement typé, aucun greffon n'est requis. | Validée |
| `DEC-443` | Versions épinglées du socle : **Python 3.12**, **Node 24 LTS**, **PostgreSQL 17**. L'épinglage se fait en `majeur.mineur` dans les fichiers de version et **par empreinte `sha256`** dans les `Dockerfile`. | Maturité de l'écosystème FastAPI, SQLAlchemy et Dramatiq pour Python 3.12. Node 24 correspond à la version installée (24.16.0) et évite d'entretenir deux chaînes. PostgreSQL 17 par prudence sur un socle qui portera 14 lots (`ROAD-RSK-002`). L'épinglage par empreinte va au-delà de l'interdiction de `latest` seul du cahier §23.3. | Validée |
| `DEC-444` | Les fichiers Compose sont organisés en un `docker-compose.base.yml` assemblé par surcouches `.dev.yml` et `.recette.yml`, avec un `COMPOSE_PROJECT_NAME` distinct par environnement : `onboarding-dev`, `onboarding-recette`, `onboarding-prod-local`. | Noms littéraux du cahier §22.2. Le nom de projet sépare automatiquement volumes et réseaux ; base, bucket, ports et `--env-file` sont distingués explicitement. Les 7 séparations exigées par §22.2 sont ainsi couvertes sans duplication de définition. | Validée |
| `DEC-445` | Les images sont publiées sous **`ghcr.io/jonathan2433/onboarding-digital/{api,web,worker}`**, étiquetées `:0.1.0` (version exacte, **seule** référence de déploiement), `:sha-<court>` et `:develop` pour la recette. Labels OCI `revision`, `version` et `source` obligatoires ; consommation **par empreinte** en production temporaire. | GHCR impose des chemins en minuscules alors que le dépôt s'appelle `ONBOARDING_DIGITAL` : le tiret est retenu contre l'underscore, plus conforme aux usages OCI. Conforme à `DEC-428` et aux conventions §4.1. | Validée |
| `DEC-446` | Le HTTPS local est assuré par **Caddy en `tls internal`**, sur les hôtes `app.onboarding.localhost` et `api.onboarding.localhost`. | macOS résout `.localhost` vers 127.0.0.1 sans modifier `/etc/hosts`, et l'autorité interne de Caddy évite toute dépendance externe — conforme au cahier §22.2, « aucun domaine public n'est nécessaire ». Motif déterminant : les cookies `Secure` et `SameSite` du LOT 3 ne peuvent pas être éprouvés en HTTP clair ; les découvrir après la porte `G1` serait le scénario de réouverture de `ROAD-RSK-002`. La racine Caddy devra être approuvée une fois dans le trousseau macOS. | Validée |
| `DEC-447` | Les données d'état utilisent **exclusivement des volumes Docker nommés**. **Aucun bind mount** de donnée d'état vers le dépôt : ni `./data`, ni `./volumes`, ni `./backups`. Les bind mounts de code source pour le rechargement à chaud restent autorisés. | Les volumes nommés résident dans l'image disque de la VM, hors iCloud, sans aucune action. Un bind mount de données dans le dépôt est précisément le geste qui ramènerait `ROAD-RSK-026` sur des fichiers de base ouverts en écriture. | Validée |
| `DEC-448` | La traçabilité GitHub — branche `develop`, protection de `main` et de `develop`, 13 étiquettes prescrites, 15 milestones, epic et stories du LOT 1 — est mise en place **par Jonathan dans l'interface GitHub**. | `gh` n'est pas installé et aucun connecteur GitHub n'est disponible en session : la vérification a été refaite le 27/07/2026 et confirme le constat de `ECART-010`. La protection de branche n'est de toute façon posable que par le propriétaire du dépôt. Répond à `QO-108`. La mise en place effective clora `ECART-010` et `QO-107`. | Validée |

## 1.2 Mise en place effective de la traçabilité GitHub

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-449` | **Remplace `DEC-448`.** La traçabilité GitHub n'a pas été posée dans l'interface web comme `DEC-448` le prévoyait, mais **par `gh` en ligne de commande**, selon le partage de rôles suivant : Jonathan a créé la branche `develop` et **authentifié `gh` lui-même** ; l'agent a installé le binaire et exécuté les créations. `gh` **2.96.0** est installé dans **`~/.local/bin/gh`**, hors Homebrew — `/opt/homebrew` appartient à l'utilisateur `admin` et `brew install` échoue faute de droits, le correctif `sudo chown` exigeant un mot de passe. Le binaire provient de la publication officielle `cli/cli`, **empreinte SHA-256 vérifiée** contre celle publiée par le projet. Livré : 13 étiquettes, 15 milestones avec `G0` fermée, l'epic `#1` et les 8 stories `#2` à `#9`, et la protection de `main` **et** `develop`. | `DEC-448` décrivait une intention, pas ce qui a eu lieu. Les conventions interdisent de modifier une décision validée en silence : elle est remplacée par une nouvelle décision qui la référence (`CONTRIBUTING.md` §8). La ligne que l'agent n'a pas franchie est l'authentification : il n'entre pas d'identifiants à la place de Jonathan et n'extrait pas le jeton du trousseau macOS. | Validée |

**Protection appliquée à `main` et `develop`**, conforme à `DEC-429` :

| Réglage | Valeur appliquée |
|---|---|
| Pull request obligatoire | Activée |
| Approbations requises | **0** — GitHub interdit l'auto-approbation, `QO-094` |
| `enforce_admins` | **Activé** — sans quoi le propriétaire contournerait la règle et le contrôle ne prouverait rien |
| Push forcés, suppressions | Rejetés |
| Historique linéaire, résolution des conversations | Exigés |
| Contrôles d'intégration obligatoires | **Aucun pour l'instant** — à ajouter en `T6`, quand la CI existera |

**Preuve d'effectivité**, et non simple constat de réglage : une tentative de push direct d'un
commit vide sur `main` puis sur `develop` a été **rejetée** par le serveur avec
`GH006 — Protected branch update failed … Changes must be made through a pull request`. Témoin
positif : le même push vers une branche neuve non protégée a **réussi**, ce qui établit que le
test sait distinguer un succès d'un échec.

**Conséquence de régime, applicable immédiatement.** `enforce_admins` vaut aussi pour Jonathan :
plus aucun commit direct sur `main` ni `develop`, **y compris documentaire**. `DEC-427` ne
faisait entrer le circuit en vigueur qu'au premier commit de code du LOT 1 ; il s'applique en
pratique dès maintenant, ce qui est plus strict et va dans le sens du cadrage.

## 1.3 Ouverture du LOT 1

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-450` | **Jonathan ouvre le LOT 1 — « Monorepo, qualité et environnement local »** le 27 juillet 2026. Les stories `MVP-L01-US001` à `US008` peuvent passer à `Ready` puis `In progress`. Le travail démarre à la sous-étape **`T1`**, story `MVP-L01-US001`, issue `#2`. Les LOTS 2 à 14 restent `Planned` : aucune de leurs stories ne peut être entamée. | Les 3 prérequis bloquants de la fiche §9.1 sont levés et prouvés, les 7 choix techniques de §9.2 sont tranchés (`DEC-439` à `DEC-447`), et la traçabilité GitHub est en place avec protection effective des branches (`DEC-449`). Les conditions de `ROAD-003`, `ARB-BACK-003` et `BACKLOG-006` sont donc réunies. | Validée |

**Conséquences immédiates**

- `DEC-427` prend effet au premier commit de code : **branche + pull request obligatoires**. En
  pratique le régime s'applique déjà à tout, `enforce_admins` étant actif depuis `DEC-449`.
- La porte `G1` devient la porte courante. Le tag `v0.1.0` sera posé sur `main` à sa validation
  (`DEC-428`).
- `ECART-006` — `.env.example` en v0.1 — doit être clos dans ce lot.

## 1.4 Réalisation du LOT 1 — sous-étape `T1`

Décisions prises pendant la réalisation du squelette du monorepo, story
`MVP-L01-US001`, issue `#2`. Les six sont validées par Jonathan le 27 juillet 2026.

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-451` | Le lint et le formatage JavaScript et TypeScript sont assurés par **ESLint** en « flat config » et **Prettier**, `eslint-config-prettier` désactivant les règles en conflit. La vérification de types reste à `tsc --noEmit`, avec la configuration stricte de `tsconfig.base.json`. | Aucun document du corpus ne tranchait : le cahier §17.1 et §23.5 ne nomment aucun linter JavaScript. Motif déterminant : **`eslint-plugin-jsx-a11y`**, sans équivalent de profondeur ailleurs, alors que le cahier §14 fait de l'accessibilité une exigence dure auditée au LOT 12. Découvrir au LOT 12 qu'on ne peut pas la linter serait le scénario de réouverture de `ROAD-RSK-002`. | Validée |
| `DEC-452` | Le critère « les répertoires sont **exécutables** » de `MVP-L01-US001` s'entend, à `T1`, comme : chaque espace de travail s'installe, se lint, se type-vérifie et exécute au moins un test réel, avec un code de sortie 0. **Aucune application n'écoute de port** à ce stade. | Le critère du backlog et celui de la fiche §3 — « lint, formatage et typage s'exécutent **à vide** sans erreur » — ne disent pas la même chose. Cette lecture est la seule compatible avec le fait que `T3` possède l'API, `T5` le frontend et `T2` la stack Docker. La retenir évite de vider trois sous-étapes de leur substance. | Validée |
| `DEC-453` | L'exclusion iCloud de `DEC-439` est mise en œuvre par l'attribut étendu **`com.apple.fileprovider.ignore#P = 1`**, posé par [`infra/scripts/exclure-icloud.sh`](../../infra/scripts/exclure-icloud.sh), appelé **à la fois** par `make icloud-exclude` et par le `postinstall` de `package.json`. La cible `make icloud-verify` échoue si un répertoire n'est pas marqué. | Mesure du 27/07/2026 : **`pnpm install` supprime et recrée les `node_modules`**, ce qui efface l'attribut ; `uv` réutilise le `.venv` et le préserve. Une cible de `Makefile` seule n'aurait protégé que les installations lancées par `make`. **Ce qui est prouvé** : l'attribut est posé, relu, et son absence détectée. **Ce qui ne l'est pas** : le respect effectif par iCloud — convention documentée par Apple, qu'aucun outil de cette machine ne permet de vérifier. `brctl` ne couvre pas les chemins CloudDocs et renvoie 0 sur erreur. **L'attribut n'est pas durable** : voir l'incident du 27/07 consigné en `ROAD-RSK-026`. La cible `icloud-verify` détecte aussi les copies de conflit iCloud. | Validée |
| `DEC-454` | **Le Markdown est exclu de tout formatage automatique**, aussi bien de Ruff (`extend-exclude`) que de Prettier (`.prettierignore`). | Mesure du 27/07/2026 : sans cette exclusion, Prettier **réécrivait les cinq documents de cadrage immuables**, ajoutant 54 661 octets au seul cahier des charges, soit +21,7 %. La preuve d'intégrité SHA-256 de [`integrite-et-conformite-documents.md`](../operations/integrite-et-conformite-documents.md) — et avec elle la porte `G0` — en aurait été invalidée. Ruff formate lui aussi les blocs de code embarqués dans le Markdown : il voyait 41 documents au lieu de 4 fichiers Python. Voir `ROAD-RSK-029`. | Validée |
| `DEC-455` | Les deux projets Python sont réunis dans un **workspace `uv` unique déclaré à la racine**, membres `apps/api` et `apps/worker`, avec un seul `uv.lock`, un seul `.venv` et une seule configuration Ruff, mypy et pytest portée par le `pyproject.toml` racine. | Symétrique de `pnpm-workspace.yaml` côté JavaScript, et cohérent avec `DEC-441`. Un seul environnement virtuel signifie un seul répertoire à soustraire à iCloud, un seul verrou à auditer en CI, et une seule source pour les règles de qualité. Les fichiers `tests/__init__.py` ont été écartés : ils créaient deux paquets homonymes `tests` que mypy et pytest refusent tous les deux. | Validée |
| `DEC-456` | Outillage posé à `T1` : **`uv` 0.11.32** depuis l'archive officielle `astral-sh/uv`, **empreinte SHA-256 vérifiée**, installée dans `~/.local/bin` ; **`pnpm` 11.17.0** par `corepack`, épinglé par le champ `packageManager` **avec empreinte d'intégrité** ; **CPython 3.12.13** géré par `uv`. Les bibliothèques du cahier §17.1 sans usage avant le LOT 4 — React Router, TanStack Query, React Hook Form, Zod, Radix UI — **ne sont pas installées**. | Même procédure que `gh` en `T0` (`DEC-449`) : Homebrew reste inutilisable, `/opt/homebrew` appartenant à l'utilisateur `admin`. `corepack` était déjà présent avec Node 24 : aucun binaire tiers supplémentaire n'a été téléchargé pour `pnpm`. Le Python système 3.9.6 n'est pas touché. Installer cinq bibliothèques sans usage ajouterait une surface d'audit de dépendances sans contrepartie, alors que le LOT 1 met justement `pip-audit` et Trivy en place. | Validée |

**Décision prise le 28 juillet 2026, après matérialisation du risque `ROAD-RSK-026`**

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-457` | **`DEC-453` est maintenue en l'état** après l'incident iCloud du 27/07/2026 : marquage par attribut étendu, reposé automatiquement par le `postinstall`, contrôlé par `make icloud-verify` exécuté en début de session et intégré à `make check`. **`DEC-418` n'est pas rouverte** et `node_modules` reste dans l'arborescence synchronisée. La copie de conflit `node_modules 2` est supprimée. **Le risque résiduel est accepté en connaissance de cause** : une nouvelle copie de conflit peut réapparaître ; le vérificateur la détectera, il ne l'empêchera pas. | Jonathan a tranché sur présentation des mesures, entre trois issues : maintenir le marquage avec vérificateur, sortir physiquement `node_modules` et `.venv` de l'arborescence par liens symboliques, ou rouvrir l'emplacement du dépôt. La deuxième option est provable là où l'attribut ne l'est pas, mais pnpm remplace parfois un lien symbolique par un vrai répertoire à l'installation — elle déplacerait le risque sans le supprimer, au prix d'une demi-sous-étape avant `T2`. La troisième dépasse le périmètre du LOT 1 et relève du confort de travail de Jonathan. L'essentiel du volume — 338 Mio de store `pnpm`, de cache et de Python gérés par `uv` — est déjà hors dépôt par construction. | Validée |

**Ce que `T1` a délibérément écarté**

- `storeDir` et `engineStrict` dans un `.npmrc` : **pnpm 11 ne lit plus ces clés depuis
  `.npmrc`**. Vérifié le 27/07/2026, `pnpm config get store-dir` y renvoyait `undefined` et
  pnpm retombait silencieusement sur son défaut. Les réglages sont dans `pnpm-workspace.yaml`.
- `--passWithNoTests` sur `packages/ui` et `packages/contracts` : une suite vide qui « passe »
  est le contrôle qui ne peut pas échouer. Un test réel a été écrit dans chaque paquet.
- `QO-085` recevra sa mesure en charge une fois les 8 services démarrés.

*Ce bloc figurait par erreur à la fin de la section 1, après le tableau de `T4`, et son marqueur
« prochain identifiant libre » y annonçait `DEC-451` alors que `DEC-469` était en usage —
19 décisions de retard. Replacé dans sa sous-étape au titre de `ECART-021`.*

## 1.5 Réalisation du LOT 1 — sous-étape `T2`

Décisions prises pendant la mise en place de la stack Docker de développement, story
`MVP-L01-US002`, issue `#3`. Validées par Jonathan le 28 juillet 2026.

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-458` | **Versions et registres des images non fixés par `DEC-443`** : Redis **8.4-alpine**, MinIO **`RELEASE.2025-09-07T16-13-09Z`** servi depuis **quay.io**, Mailpit **v1.30** servi depuis **ghcr.io**, Caddy **2.11-alpine**. PostgreSQL 17.7 en image **Debian** et non Alpine ; Python 3.12 en **`slim`** et non Alpine. Les huit images sont référencées par tag **et** empreinte `sha256`, toutes vérifiées `linux/amd64` **et** `linux/arm64`. | `DEC-443` n'épinglait que Python, Node et PostgreSQL : les quatre autres versions n'étaient fixées par aucun document. **PostgreSQL en Debian** parce qu'Alpine repose sur musl, dont la gestion des locales est réduite : ce socle portera un trombinoscope de noms français accentués et les index de recherche du cahier §26.1, et la collation ne se change pas sans recréer le cluster. **Python en `slim`** parce que de nombreuses roues n'existent pas en musl, ce qui forcerait une compilation depuis les sources. **quay.io et ghcr.io** parce que ce sont les registres de publication de MinIO et de Mailpit, et que la limite de débit anonyme de Docker Hub a réellement fait échouer une inspection pendant cette sous-étape (défaut `T2-1`). | Validée |
| `DEC-459` | À `T2`, le healthcheck de `api`, `worker` et `web` porte sur le **processus et l'image**, non sur un appel HTTP : il vérifie que le paquet applicatif est importable, ou que Vite est résolvable. Les endpoints `/health/live`, `/health/ready` et `/health/version`, avec la vérification effective de PostgreSQL, Redis et MinIO, relèvent entièrement de `T3`. | Le critère de `T2` exige que les trois services soient sains, alors que `T3` livre l'application : à `T2`, il n'y a rien à sonder en HTTP. Arbitrage de Jonathan entre cette lecture et l'avance d'une API minimale. Retenue parce qu'elle ne vide ni `T3` ni `T5` de leur substance, et parce que le contrôle reste **capable d'échouer** — une image cassée ou une installation incomplète le font sortir en erreur. | Validée |
| `DEC-460` | Toutes les publications de ports sont liées **explicitement à `127.0.0.1`**. Le contrôle `make ports` compare les publications **déclarées** dans la configuration Compose et les publications **réelles** du moteur, et **échoue si les deux nombres ne concordent pas**. | Le cahier §22.2 pose que PostgreSQL, Redis, MinIO et Mailpit ne sont jamais exposés publiquement. Sans préfixe explicite, Docker publie sur **toutes** les interfaces et contourne le pare-feu de macOS : le défaut est silencieux. La comparaison des deux vues vient du défaut `T2-4`, où le contrôle affirmait « aucune exposition » en n'ayant examiné que 5 publications sur 7. | Validée |
| `DEC-461` | `make env` crée le `.env` local depuis `.env.example` et **génère aléatoirement 5 secrets de services locaux** sur 48 caractères — `APP_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `MINIO_ROOT_PASSWORD` — plus un identifiant MinIO lisible. **`IMPORT_SOURCE_RETENTION_DAYS` et `UPTIME_KUMA_PUSH_URL` restent en `CHANGE_ME`**, et la cible le dit explicitement. | `.env` n'est pas versionné : générer des secrets forts localement n'enfreint aucune règle et supprime la tentation d'un mot de passe faible réutilisé. Les deux variables laissées en `CHANGE_ME` ne sont pas des oublis : la première relève de `QO-100`, bloquante, la seconde d'une supervision externe du LOT 13. Les afficher à la création évite qu'un futur contributeur les remplisse au hasard. | Validée |

## 1.6 Réalisation du LOT 1 — sous-étape `T3`

Décisions prises pendant la mise en place de l'API, des trois healthchecks et de la migration
initiale, story `MVP-L01-US003`, issue `#4`. Validées par Jonathan le 28 juillet 2026.

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-462` | L'API est **synchrone** : SQLAlchemy en mode classique et FastAPI servant les routes par son pool de fils. L'application n'est **pas** construite à l'import : `uvicorn` est lancé avec **`--factory`**, et la configuration est portée par **`app.state`**, non par un cache global. | Aucun document n'impose l'asynchrone, et le cahier §25.1 dimensionne le produit pour environ 500 collaborateurs : le pool de fils suffit très largement. Le mode synchrone évite la double chaîne de pilotes, les sessions asynchrones et les pièges de mélange que le LOT 2 paierait cher. **La fabrique et `app.state` viennent d'un défaut réel** : la première version se terminait par `application = creer_application()`, ce qui faisait échouer la simple collecte des tests, et les routes lisaient un cache global, ce qui rendait intestable le cas « `ready` doit répondre 503 ». Un livrable difficile à tester est un livrable qu'on finit par ne pas tester. | Validée |
| `DEC-463` | **La migration `0001_initial` est vide.** Elle n'active aucune extension PostgreSQL. La liste des extensions sera établie au **LOT 2**, avec les tables et les index de recherche. Question ouverte `QO-112`. | La fiche §5 annonçait « les extensions strictement nécessaires », mais **aucun document du corpus n'en nomme une seule** — zéro occurrence de `pg_trgm`, `unaccent`, `citext`, `pgcrypto`, `uuid-ossp` dans le cahier comme dans le modèle, témoin positif du même filtre à quatre occurrences de `SQLAlchemy`. Le modèle §3 impose des UUID, mais `gen_random_uuid()` est intégré à PostgreSQL depuis la version 13 ; le modèle §26.1 laisse la recherche tolérante explicitement ouverte, et ses index arrivent à la migration 16. La roadmap autorise littéralement « une migration Alembic **vide ou initiale** ». Choisir une liste aurait été inventer une décision, et une extension activée se retire moins facilement qu'elle ne s'ajoute. Arbitrage de Jonathan sur les trois issues possibles. | Validée |
| `DEC-464` | Le garde-fou « aucune variable ne vaut encore `CHANGE_ME_*` » porte sur les variables que **l'API déclare**, non sur l'ensemble de `.env.example`. | Appliqué littéralement à tout le fichier, il empêcherait l'API de démarrer aujourd'hui : `IMPORT_SOURCE_RETENTION_DAYS` reste en `CHANGE_ME` parce que sa valeur relève de `QO-100`, bloquante, et `UPTIME_KUMA_PUSH_URL` parce qu'elle appartient au LOT 13. Aucune n'est utilisée par un code existant. Le jour où le LOT 9 ajoutera la première à sa configuration, `QO-100` devra être tranchée — c'est l'effet recherché, et il vaut mieux qu'un garde-fou contourné. | Validée |
| `DEC-465` | Les healthchecks Compose deviennent des contrôles applicatifs réels : `api` interroge **`/health/ready`**, qui sonde effectivement PostgreSQL, Redis et MinIO ; `worker` teste la connexion à son **courtier Redis**. Les endpoints de santé restent **hors du préfixe `/api/v1`**. | `ready` et non `live` parce que Compose ne redémarre pas un conteneur au seul motif qu'il est `unhealthy` : aucun risque de boucle de redémarrage, et `depends_on: service_healthy` attend alors que l'API soit réellement capable de servir. Preuve d'effectivité : **Redis arrêté pour de vrai**, `ready` répond **503** avec `redis indisponible`, tandis que `live` reste à 200 — la sonde discrimine par dépendance. Les endpoints restent hors du préfixe versionné parce qu'ils relèvent de l'exploitation : l'adresse que sonde un orchestrateur ne doit pas bouger avec les versions de l'API. | Validée |

## 1.7 Réalisation du LOT 1 — sous-étape `T4`

Décisions prises pendant la mise en place de la journalisation JSON corrélée, story
`MVP-L01-US004`, issue `#5`. Validées par Jonathan le 28 juillet 2026.

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-466` | La journalisation, le masquage des secrets et l'identifiant de corrélation vivent dans un **paquet Python partagé, `packages/observabilite`**, membre du workspace `uv`, dont dépendent l'API **et** le worker. Le module de corrélation, créé dans `apps/api/app/shared/` en `T3`, y déménage ; l'ancien emplacement n'est plus qu'un réexport sans logique. | Le cahier §28.1 impose le même format aux deux applications et le §28.2 la même interdiction de fuite. **Dupliquer le filtre de masquage aurait été la pire option** : deux filtres divergent, et le jour où l'un oublie un motif, la fuite est silencieuse. Une seule implémentation, deux consommateurs, une seule suite de tests. `packages/` est l'un des sept répertoires du cahier §15.3, qui ne le réserve pas au JavaScript ; `pnpm-workspace.yaml` liste ses membres explicitement, ce paquet Python n'y entre donc pas par accident. | Validée |
| `DEC-467` | **La rotation des journaux est assurée par le pilote `json-file` de Docker**, avec `max-size` et `max-file`, sur les huit services. Les processus écrivent sur `stdout` et n'ouvrent aucun fichier. | Le §28.3 exige « rotation et limite de taille obligatoires ». Écrire dans un fichier à l'intérieur d'un conteneur produirait une donnée d'état que `DEC-447` interdit de sortir par un bind mount, et que personne ne rotaterait. **Ce que cette décision ne couvre pas, et il faut le dire** : le §28.3 demande aussi une conservation de 30 jours, or `json-file` borne par la taille et jamais par la durée. La conservation calendaire suppose une collecte centralisée, qui appartient au LOT 13. `LOG_RETENTION_DAYS` porte l'intention. Voir `QO-113`. | Validée |
| `DEC-468` | Le champ `resultat` du §28.1 prend **trois** valeurs et non deux : **`succes`** pour 2xx et 3xx, **`refus`** pour 4xx, **`echec`** pour 5xx. Seul `echec` est journalisé au niveau `error`. | La première version n'en avait que deux, et annonçait `resultat=succes` à côté d'un `code_erreur=http_404` : contradictoire à la lecture, et ambigu à l'agrégation — on ne savait plus si `succes` comptait les refus. La distinction dit **où est la faute** : `refus` chez l'appelant, `echec` chez nous. Journaliser un 404 au niveau `error` ferait par ailleurs sonner une alerte à chaque adresse mal tapée. | Validée |
| `DEC-469` | **Ne sont jamais journalisés** : la chaîne de requête HTTP, les arguments d'un job — seul leur nombre l'est —, les traces d'exception — seul le type l'est —, le journal d'accès d'uvicorn, et les journaux de `httpx`, `botocore` et `urllib3`, réduits aux avertissements. | Le §28.2 interdit le magic link complet : la chaîne de requête le porterait, et ne pas l'écrire du tout est la parade la plus sûre. Les arguments d'un job porteront une adresse e-mail, un identifiant de personne ou un jeton. Une trace d'exception contient les variables locales, donc des secrets. Le journal d'accès d'uvicorn, mesuré sur les journaux réels, double la ligne applicative **sans aucun des dix champs**, journalise les sondes de santé toutes les dix secondes — **8 640 lignes par jour et par service** — et écrit le chemin brut avec sa chaîne de requête. `httpx` et `botocore` écrivent des URL complètes, dont des URL signées. | Validée |

## 1.8 Réalisation du LOT 1 — sous-étape `T5`

Décisions prises pendant la réalisation de la page de statut, story `MVP-L01-US002`,
issue `#3`. Soumises à Jonathan le 28 juillet 2026.

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-470` | **La page et l'API partagent une seule origine.** Le bloc `app.onboarding.localhost` du `Caddyfile` mandate `/health/*` et `/api/*` vers `api:8000`, le reste vers `web:5173`. Aucun CORS n'est ajouté à l'API, et aucun renvoi n'est configuré dans le serveur de développement Vite. `VITE_API_BASE_URL` reste à `/api/v1` et n'est **pas** employée pour les endpoints de santé, hors préfixe par `DEC-465`. | La page est servie sur `app.onboarding.localhost` et l'API sur `api.onboarding.localhost` : deux origines pour un navigateur, et l'API n'a **aucun CORS** — mesuré, 0 occurrence. Trois montages étaient possibles. CORS ajouterait une surface de sécurité permanente et compliquerait les cookies `Secure` et `SameSite` du LOT 3, or c'est précisément pour pouvoir les éprouver que `DEC-446` impose HTTPS local. Un renvoi par Vite disparaîtrait dès qu'une image de production sert un artefact statique, donc à refaire en `T7`. Le mandatement par Caddy ne modifie pas l'API, laisse l'en-tête `X-Request-ID` lisible par la page sans `Access-Control-Expose-Headers`, et survit à la recette comme à la production. **`CLAUDE.md` §9.3 affirmait « `Caddyfile` inchangé » : c'était faux**, aucune route n'y menait à l'API. | Validée |
| `DEC-471` | Les tests de la page emploient **Testing Library** sur l'environnement **`jsdom`**, déclaré dans `vite.config.ts`. Deux dépendances de développement sont ajoutées : `@testing-library/react` et `@testing-library/dom` — pair explicite depuis la version 16 — et `jsdom`. | Testing Library est **prescrite** par le cahier §17.1 et par la fiche §6 : ce n'est pas un choix nouveau. En revanche aucun document ne tranche l'environnement DOM. `jsdom` est l'implémentation de référence, celle que documente Testing Library, et la seule dont le comportement sur `navigator.onLine` et sur le presse-papiers est stable — les deux mécanismes que la page doit éprouver. `restoreMocks` et `unstubGlobals` sont activés : un test qui laisse fuir son bouchon fait passer ou échouer le suivant pour une raison invisible. | Validée |
| `DEC-472` | Le `Caddyfile` est monté par **son répertoire** — `../caddy:/etc/caddy:ro` — et non plus par le fichier seul, et **`make up` recharge explicitement Caddy** par la cible `caddy-reload`. | Un bind mount de fichier unique épingle l'**inode**. La plupart des éditeurs n'écrivent pas en place : ils écrivent un temporaire puis renomment, produisant un inode neuf. Le conteneur continue alors de pointer vers l'ancien inode supprimé : `ls` affiche encore l'entrée, mais toute ouverture répond « No such file or directory ». **Mesure du 28/07/2026 : le conteneur voyait un `Caddyfile` de 1 573 octets quand l'hôte en portait 2 844**, et Caddy servait une configuration périmée en paraissant parfaitement sain. Monter le répertoire résout la classe entière, le chemin étant résolu à chaque ouverture. Le rechargement traite le second volet du même défaut : Caddy ne surveille pas son fichier, et Compose ne recrée pas le conteneur quand seul le contenu du fichier monté change. Reste de la **configuration en lecture seule**, donc conforme à `DEC-447`. | Validée |
| `DEC-473` | Un **`.dockerignore`** exclut du contexte de construction `node_modules`, `.venv`, les caches d'outillage, `.git`, `docs/prototype`, les copies de conflit iCloud et **`.env`**. | Sans lui, `COPY apps/web ./apps/web` recopie le `node_modules` de l'**hôte** par-dessus celui que `pnpm install` construit dans l'image. Mesure du 28/07/2026 : l'hôte résout `@rolldown/binding-darwin-arm64`, `lightningcss-darwin-arm64` et `@typescript/typescript-darwin-arm64` ; l'image résout les variantes `linux-arm64-musl`. Les deux arborescences ne sont pas interchangeables. Le défaut n'était **pas actif** — les liens de `apps/web/node_modules` sont relatifs et pointent vers le magasin `.pnpm` du conteneur — mais **latent** : un `node_modules` d'hôte désynchronisé du verrou produirait des liens vers des chemins absents, et l'échec surviendrait au démarrage, pas à la construction. L'exclusion de `.env` est une barrière supplémentaire : aucun `Dockerfile` ne le copie aujourd'hui, et un secret gravé dans une couche d'image y reste. **Ce fichier ne résout pas `ROAD-RSK-030`** : la réduction de l'image `web` exige un `Dockerfile` multi-étapes, en `T7`. | Validée |

**Ce que `T5` a délibérément écarté**

- **`axe`** et tout audit d'accessibilité outillé : `jsx-a11y` couvre le lint JSX, et l'audit
  automatisé du cahier §14.2 relève de `T10` et de l'audit du LOT 12. Le dire vaut mieux que le
  laisser croire.
- **React Router** : `DEC-456` ne l'installe pas avant le LOT 4, et le LOT 1 n'a qu'une page.
- **Zod** : la validation des deux formes de réponse est écrite à la main, pour la même raison.
- **Un bind mount du code source** vers le conteneur `web` : `DEC-447` reste intact, les
  modifications passent par le `make up` qui reconstruit. Le rechargement à chaud n'est exigé
  par aucun critère du lot.
- **Toute couleur de marque** : `packages/ui` est vide jusqu'à `T10` et la charte relève de
  `DEP-006`. Poser une palette approximative créerait la dette que `US007` cherche à éviter.

**Prochain identifiant libre : `DEC-474`.**

---

# 2. Décisions de droits — matrice des rôles et permissions §26

Reprises sans altération. Source : `docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md` v1.1,
validée le 25 juillet 2026.

| ID | Décision |
|---|---|
| `RIGHTS-001` | Toute permission est refusée par défaut si elle n’est pas explicitement accordée. |
| `RIGHTS-002` | Une personne possède une seule entité principale active. |
| `RIGHTS-003` | Les autres entités sont accessibles en lecture seule aux employés authentifiés. |
| `RIGHTS-004` | Les responsabilités se cumulent dans l’entité principale. |
| `RIGHTS-005` | Le DG reçoit automatiquement la responsabilité DSM dans son entité. |
| `RIGHTS-006` | Le DSM est limité à ses consultants. |
| `RIGHTS-007` | Le Booster est limité à son cercle. |
| `RIGHTS-008` | Le responsable de bureau est limité à son bureau. |
| `RIGHTS-009` | L’ESM dispose des pouvoirs fonctionnels transverses de son entité. |
| `RIGHTS-010` | L’administrateur d’entité administre et supporte son entité uniquement. |
| `RIGHTS-011` | Le super-administrateur possède les droits globaux et la purge définitive. |
| `RIGHTS-012` | Les collaborateurs ne modifient plus leur profil après validation. |
| `RIGHTS-013` | Le nouvel arrivant modifie uniquement les informations personnelles autorisées avant validation. |
| `RIGHTS-014` | Les exports respectent toujours le périmètre de consultation. |
| `RIGHTS-015` | Les permissions sont recalculées côté API pour chaque requête. |
| `RIGHTS-016` | Les changements de rôle, archivages, restaurations et purges sont audités. |
| `RIGHTS-017` | Une intervention globale du super-administrateur dans une entité exige une traçabilité renforcée. |
| `RIGHTS-018` | Les comptes de service utilisent des scopes limités et ne remplacent pas un utilisateur humain. |
| `RIGHTS-019` | La clôture d’une responsabilité révoque immédiatement les permissions associées. |
| `RIGHTS-020` | Les contraintes métier peuvent interdire une action pourtant autorisée par le rôle. |
| `RIGHTS-021` | Après cinq minutes, seules l’ESM, l’administrateur d’entité et le super-administrateur peuvent réouvrir une tâche. |
| `RIGHTS-022` | L’administrateur d’entité ne peut pas attribuer les responsabilités Framework. |
| `RIGHTS-023` | L’ESM peut effectuer les restaurations fonctionnelles de son entité. |
| `RIGHTS-024` | Le Booster ne peut pas modifier les données hors cercle d’un membre secondaire. |
| `RIGHTS-025` | Les modèles DSM et Booster restent limités à leur périmètre. |

## 2.1 Arbitrages de droits — matrice §25

| ID | Arbitrage |
|---|---|
| `ARB-DROIT-001` | Réouverture d'une tâche après cinq minutes : seuls l'ESM, l'administrateur d'entité et le super-administrateur. Motif et audit obligatoires. |
| `ARB-DROIT-002` | L'attribution et le retrait des responsabilités DSM, ESM, Booster et responsable de bureau sont réservés à l'ESM et au super-administrateur. L'administrateur d'entité n'en dispose pas. |
| `ARB-DROIT-003` | L'ESM peut restaurer dans son entité un profil, un contenu, un événement, un cercle ou un bureau. Les restaurations techniques, massives ou liées aux imports restent réservées à l'administrateur d'entité et au super-administrateur. |
| `ARB-DROIT-004` | Le Booster gère l'appartenance secondaire à son cercle ainsi que les contenus et onboardings liés. Il ne peut pas modifier le cercle principal, le DSM, le client ou le statut d'un membre seulement secondaire. |
| `ARB-DROIT-005` | Modèles d'onboarding : le DSM crée pour ses consultants, le Booster pour son cercle, l'ESM et l'administrateur d'entité en transverse, le super-administrateur les modèles génériques globaux. |

---

# 3. Décisions de modèle de données — modèle §32

Source : `docs/architecture/MODELE_DONNEES_EXALT.md` v1.0, validée le 25 juillet 2026.

| ID | Décision |
|---|---|
| `DATA-001` | Une personne possède une identité globale unique. |
| `DATA-002` | Les données propres à une entité sont portées par une appartenance historisée. |
| `DATA-003` | Les responsabilités Framework et les rôles techniques sont séparés. |
| `DATA-004` | Les clients sont globaux et activés par entité. |
| `DATA-005` | Les alias clients exigent une validation humaine. |
| `DATA-006` | Les modèles d’onboarding sont versionnés et les versions publiées sont immuables. |
| `DATA-007` | Les instances conservent des snapshots des tâches. |
| `DATA-008` | Les fichiers sont stockés dans MinIO et leurs métadonnées dans PostgreSQL. |
| `DATA-009` | Les contenus utilisent un modèle hybride typé, sans HTML arbitraire. |
| `DATA-010` | Les imports passent par une zone d’analyse avant écriture. |
| `DATA-011` | Les jobs sont persistés dans PostgreSQL et exécutés par Dramatiq. |
| `DATA-012` | Une outbox transactionnelle coordonne les effets externes. |
| `DATA-013` | Les actions sensibles produisent un audit atomique. |
| `DATA-014` | Les références locales sont protégées contre les liens inter-entités. |
| `DATA-015` | Les suppressions physiques sont rares et contrôlées. |
| `DATA-016` | Les historiques utilisent des périodes de validité. |
| `DATA-017` | Les données dérivées ne deviennent pas la source de vérité. |
| `DATA-018` | Le schéma reste compatible avec Entra ID et Graph en V2. |

## 3.1 Arbitrages de modèle — modèle §31

| ID | Arbitrage |
|---|---|
| `ARB-DATA-001` | Séparation `person` / `entity_membership` : identité globale unique, données locales dans l'appartenance. |
| `ARB-DATA-002` | Table générique `framework_responsibility_assignment` avec type et scope contrôlés, plutôt que quatre tables séparées. |
| `ARB-DATA-003` | Modèle éditorial hybride : pages typées composées de blocs autorisés, pas de CMS libre, pas de HTML arbitraire. |
| `ARB-DATA-004` | Historisation temporelle systématique : les affectations structurantes sont clôturées puis recréées, jamais écrasées. |
| `ARB-DATA-005` | Outbox transactionnelle et jobs PostgreSQL : audit, outbox et jobs écrits dans la même transaction que l'action métier. Redis sert uniquement au transport. |

---

# 4. Décisions de roadmap — roadmap §17

Source : `docs/product/ROADMAP_MVP_V1_V2_EXALT.md` v1.0, validée le 25 juillet 2026.

| ID | Décision |
|---|---|
| `ROAD-001` | Le MVP est réalisé en 15 lots séquentiels de 0 à 14. |
| `ROAD-002` | Chaque lot possède une démonstration et une validation explicite. |
| `ROAD-003` | Aucun lot dépendant ne commence avant validation du précédent. |
| `ROAD-004` | Le socle MinIO est installé tôt et la chaîne média est finalisée dans un lot spécialisé. |
| `ROAD-005` | Le MVP inclut la production temporaire et la préparation de la production générale. |
| `ROAD-006` | La production générale reste conditionnée aux dépendances externes validées. |
| `ROAD-007` | La V1 commence après une période d’usage réel du MVP. |
| `ROAD-008` | La V2 est conditionnée aux autorisations de la DSI. |
| `ROAD-009` | Les intégrations Microsoft ne sont pas sur le chemin critique du MVP ou de la V1. |
| `ROAD-010` | Les fonctions explicitement différées ne doivent pas être ajoutées silencieusement au MVP. |
| `ROAD-011` | Les tests de performance commencent avant la recette finale. |
| `ROAD-012` | Une exigence Must non terminée empêche la validation du lot concerné. |

## 4.1 Arbitrages de roadmap — roadmap §16

| ID | Arbitrage |
|---|---|
| `ARB-ROAD-001` | Conserver 15 lots MVP numérotés de 0 à 14. |
| `ARB-ROAD-002` | Amorcer MinIO dès le LOT 1, utiliser les médias simples dans les lots métier, finaliser la chaîne média au LOT 11. |
| `ARB-ROAD-003` | Rendre obligatoire la validation du MVP sur la production temporaire locale avant migration vers l'hébergement permanent. |
| `ARB-ROAD-004` | Ne pas démarrer la V1 immédiatement : le MVP doit d'abord être exploité et avoir exécuté au moins un parcours d'arrivée réel. |
| `ARB-ROAD-005` | Considérer tous les lots Microsoft comme conditionnels, sans engagement avant validation des accès, scopes, responsabilités et sources de vérité. |

---

# 5. Décisions de backlog — backlog §14

Source : `docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md` v1.0, validée le 25 juillet 2026.

| ID | Décision |
|---|---|
| `BACKLOG-001` | Le backlog est structuré par les 15 lots MVP validés. |
| `BACKLOG-002` | Les priorités P0, P1 et P2 gouvernent l’ordre de réalisation. |
| `BACKLOG-003` | Une story P0 ouverte empêche la validation de sa porte. |
| `BACKLOG-004` | Les tailles relatives ne constituent pas des estimations de délai. |
| `BACKLOG-005` | Toute story XL est découpée avant implémentation. |
| `BACKLOG-006` | Seul le lot ouvert par Jonathan peut être réalisé. |
| `BACKLOG-007` | Les stories V1 et V2 ne sont pas développées avant leurs conditions d’entrée. |
| `BACKLOG-008` | Les défauts critiques préemptent les fonctions prévues. |
| `BACKLOG-009` | Une story n’est Done qu’avec tests, documentation et démonstration. |
| `BACKLOG-010` | GitHub conserve la traçabilité entre story, décision, PR, tests et porte. |

## 5.1 Arbitrages de backlog — backlog §13

| ID | Arbitrage |
|---|---|
| `ARB-BACK-001` | Retenir `P0`, `P1` et `P2`, avec interdiction de franchir une porte tant qu'une story `P0` reste ouverte. |
| `ARB-BACK-002` | Utiliser les tailles `S`, `M`, `L`, `XL` sans les convertir en délais. Toute story `XL` est découpée avant réalisation. |
| `ARB-BACK-003` | Seul le lot explicitement ouvert par Jonathan peut passer à `Ready` ou `In progress`. |
| `ARB-BACK-004` | Conserver les stories V1 et V2 dans le backlog pour la traçabilité, mais les laisser `Blocked` jusqu'aux conditions de la roadmap. |
| `ARB-BACK-005` | Tout défaut critique de sécurité, de données, d'isolation ou d'accessibilité essentielle devient immédiatement prioritaire sur les fonctionnalités du lot en cours. |

---

# 6. Contrôle de complétude

| Séquence | Attendu | Présent dans ce registre |
|---|---:|---:|
| `RIGHTS` | 25 | 25 |
| `DATA` | 18 | 18 |
| `ROAD` | 12 | 12 |
| `BACKLOG` | 10 | 10 |
| `ARB-DROIT` | 5 | 5 |
| `ARB-DATA` | 5 | 5 |
| `ARB-ROAD` | 5 | 5 |
| `ARB-BACK` | 5 | 5 |
| `DEC-418+` | 21 | 21 |
| `DEC-439+` — arbitrages `T0` | 10 | 10 |
| `DEC-449` — mise en place GitHub | 1 | 1 |
| `DEC-450` — ouverture du LOT 1 | 1 | 1 |
| `DEC-451+` — réalisation du LOT 1, `T1` | 7 | 7 |
| `DEC-458+` — réalisation du LOT 1, `T2` | 4 | 4 |
| `DEC-462+` — réalisation du LOT 1, `T3` | 4 | 4 |
| `DEC-466+` — réalisation du LOT 1, `T4` | 4 | 4 |
| `DEC-470+` — réalisation du LOT 1, `T5` | 4 | 4 |
| **Total** | **141** | **141** |

Les nombres attendus ont été obtenus par comptage automatique dans les documents sources.
Voir [contrôles de sortie du lot 0](../operations/) en sous-étape S8.
