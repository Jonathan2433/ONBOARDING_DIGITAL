# Fiche de lot — LOT 2 : Socle de données et isolation multi-entités

> **✅ LE LOT 2 EST OUVERT** depuis le 18 août 2026, décision `DEC-496`.
>
> **Cette fiche est un PLAN soumis à validation, pas un compte rendu.** Rien n'y est prouvé.
> **Aucune ligne de code n'est écrite avant que Jonathan ait validé le découpage du §3** — c'est
> une condition posée dans `DEC-496` elle-même.
>
> Les **LOTS 3 à 14 restent `Planned`** : aucune de leurs stories ne peut être entamée.

**Porte de validation :** `G2` — « Fin du modèle implémenté — contraintes et isolation validées »
**Tag posé à la validation :** `v0.2.0` (`DEC-428`, conventions §4)
**Dépendance :** roadmap, « LOTS 0 et 1 ». **Satisfaite** — `G0` le 27/07/2026, `G1` le 12/08/2026
**Jalon GitHub :** `G2`, déjà créé, 0 issue
**Stories :** `MVP-L02-US001` à `US008` — **sept en `P0`**, une en `P1`

---

## 1. Objectif et périmètre

### 1.1 Objectif littéral

Roadmap, LOT 2 : « **Implémenter le noyau relationnel validé avant d'ajouter les écrans
métier.** »

Le mot qui commande tout est **avant**. Ce lot ne produit **aucun écran** et **aucune donnée
réelle**. Ce qu'il livre se démontre en base et par des tests.

### 1.2 Périmètre inclus — les 22 éléments de la roadmap, littéralement

| # | Élément | Table(s) du modèle |
|---:|---|---|
| 1 | entités | `entity` §5.1 |
| 2 | paramètres globaux et locaux | `platform_setting` §5.2, `entity_setting` §5.3 |
| 3 | domaines e-mail autorisés | `allowed_email_domain` §5.4 |
| 4 | personnes | `person` §6.1 |
| 5 | appartenances aux entités | `entity_membership` §6.2 |
| 6 | métiers | `job_catalog` §6.3, `membership_job_assignment` §6.4 |
| 7 | statuts professionnels | `professional_status_assignment` §6.5 |
| 8 | clients globaux, clients activés et alias | `client` §7.1, `entity_client` §7.2, `client_alias` §7.3 |
| 9 | cercles | `circle` §8.1, `circle_membership` §8.2 |
| 10 | bureaux | `office` §8.3 |
| 11 | affectations DSM | `dsm_assignment` §8.5 |
| 12 | responsabilités Framework | `framework_responsibility_assignment` §8.4 |
| 13 | rôles techniques | `technical_role_assignment` §8.6 |
| 14 | archivage et historisation | champs communs §3.1, principes §2.3 et §2.4 |
| 15 | contraintes temporelles | §25.2 |
| 16 | contraintes d'unicité | §25.1 |
| 17 | protection des références inter-entités | §25.3, principe §2.5 |
| 18 | repositories et services de base | — |
| 19 | factories de données fictives | — |
| 20 | jeu de test jusqu'à 25 entités et 5 000 profils | — |

Soit **16 tables**, et non 22 : la roadmap énumère des éléments fonctionnels, dont certains sont
portés par la même table et d'autres ne sont pas des tables. **Compte-les sur le modèle, jamais
sur cette fiche** — c'est la leçon de `ECART-023`.

### 1.3 Périmètre exclu, et pourquoi

| Exclu | Où cela appartient |
|---|---|
| **Authentification** : `user_account`, `admin_password_credential`, `magic_link_request`, `user_session`, `service_account`, `service_token`, `auth_event` | **LOT 3**, porte `G3` |
| Fiches d'arrivée, autorisations photo | LOT 7 |
| Médias et variantes | LOT 11 |
| Contenus éditoriaux, liens internes | LOT 6 |
| Événements | LOT 8 |
| Onboarding : tâches, modèles, instances | LOT 7 |
| Imports CSV | LOT 9 |
| Jobs, outbox, planification | LOT 11 |
| Audit, alertes, signalements, exports | LOT 10 |
| RGPD, notices, conservation | LOT 10 |
| **Tout écran, toute route métier de l'API** | LOTS 4 et suivants |

> **Le modèle §28 groupe « `person` et authentification » à son point 3. Ce n'est PAS une
> frontière de lot, et il faut le lire correctement.** Le §28 décrit un ordre **global** sur
> **17** étapes couvrant **tous** les lots — ses points 9 à 15 concernent médias, contenus,
> onboarding, imports, jobs et audit, qui sont manifestement postérieurs. Son point 3 dit donc
> « quand tu arriveras à l'authentification, place-la après `person` », pas « fais-la
> maintenant ».
>
> **Et rien ne l'exige plus tôt :** c'est `user_account` qui référence `person`, jamais l'inverse.
> `person` peut donc exister seule. **Ne crée aucune table d'authentification dans ce lot** — la
> règle §2.6 de la passation l'interdit d'ailleurs explicitement, « même partielle, même de
> test ».

---

## 2. Stories sélectionnées et ordre interne

| Ordre | Story | Prio | Taille | Dépendances déclarées |
|---:|---|:--:|:--:|---|
| 1 | `MVP-L02-US008` — migrations Alembic initiales | `P0` | L | `US001`–`US006` |
| 2 | `MVP-L02-US001` — créer et configurer une entité | `P0` | L | L01 |
| 3 | `MVP-L02-US002` — personne et appartenance principale | `P0` | L | `US001` |
| 4 | `MVP-L02-US003` — catalogues métier et clients | `P0` | L | `US001` |
| 5 | `MVP-L02-US004` — historiser DSM, client, cercle, responsabilités | `P0` | **XL** | `US002`, `US003` |
| 6 | `MVP-L02-US005` — contraintes de rôles et de périmètres | `P0` | L | `US004` |
| 7 | `MVP-L02-US006` — bloquer les références croisées entre entités | `P0` | L | `US001`–`US005` |
| 8 | `MVP-L02-US007` — jeu de données fictif représentatif | `P1` | M | `US001`–`US006` |

### 2.1 Justification de l'ordre

**`US008` est placée en premier ET en dernier, et ce n'est pas une contradiction.** Le backlog la
déclare dépendante de `US001`–`US006`, ce qui est exact pour son **critère** — « une base vide est
construite uniquement par migrations » ne peut être prouvé qu'une fois toutes les tables écrites.
Mais son **outillage** — convention de nommage des contraintes, mixins de champs communs,
stratégie de test sur PostgreSQL réel — conditionne la première table. La story est donc **ouverte
à `T1` et close à `T12`**, comme `US002` l'a été au LOT 1 sur trois sous-étapes.

**L'ordre des tables suit le §28 du modèle, pas mon jugement.** Ses points 2 puis 4 à 8, restreints
au périmètre de ce lot, donnent exactement la suite : entités → personnes → appartenances → métiers
et statuts → clients → cercles et bureaux → responsabilités et rôles.

**`US004` est en `XL` et c'est la seule.** L'historisation touche **sept** relations (§25.2) et
c'est le seul endroit du lot où une erreur de conception serait coûteuse à défaire : une contrainte
d'exclusion mal posée se découvre quand les données existent. Elle reçoit donc **deux**
sous-étapes.

---

## 3. Sous-étapes proposées — **c'est ce que Jonathan valide**

| | Objet | Stories | §28 | Ce qui devra être prouvé |
|:--:|---|---|:--:|---|
| **`T1`** | **Socle technique du modèle et extensions.** Trancher `QO-111` et `QO-112`. Base déclarative SQLAlchemy, convention de nommage des contraintes, mixins des champs communs §3.1, stratégie de test sur PostgreSQL réel. Migration des extensions. | `US008` | 1 | La migration s'applique sur une base **vide**, se rejoue, et **se défait**. Les 7 choix du §9.2 sont tranchés et tracés |
| **`T2`** | **Entités, paramètres et domaines e-mail.** `entity`, `platform_setting`, `entity_setting`, `allowed_email_domain`. Archivage §2.4. | `US001` | 2 | `entity(code)` unique éprouvé par **témoin** ; l'archivage **ne supprime pas** l'historique ; un paramètre local **surcharge** le global |
| **`T3`** | **Personnes.** `person`, e-mail normalisé unique. **Aucune table d'authentification.** | `US002` | 3 | `person(email_normalized)` unique éprouvé par témoin, **normalisation comprise** — deux graphies du même e-mail doivent collisionner |
| **`T4`** | **Appartenance à une entité.** `entity_membership`, ses états §24.1, et **la règle d'une seule appartenance principale active**. | `US002` | 4 | L'index partiel `UNIQUE WHERE membership_state IN ('future','active')` **refuse** la seconde ; les états suivent §24.1 |
| **`T5`** | **Métiers et statuts professionnels.** `job_catalog`, `membership_job_assignment`, `professional_status_assignment`. **Instruire `ECART-012`.** | `US003` | 5 | Unicité partielle `WHERE archived_at IS NULL` ; `intercontrat` **interdit** un client actif ; `ECART-012` est instruit et arbitré |
| **`T6`** | **Clients, activations locales et alias.** `client`, `entity_client`, `client_alias`. | `US003` | 6 | Un rapprochement d'alias **ne fusionne rien** automatiquement — éprouvé par témoin |
| **`T7`** | **Cercles, bureaux et appartenance aux cercles.** `circle`, `circle_membership`, `office`. | `US001`, `US003` | 7 | Unicité partielle par entité ; **un seul cercle principal actif** par appartenance ; un cercle **à membres actifs refuse** d'être archivé (§25.4) |
| **`T8`** | **DSM, responsabilités Framework et rôles techniques.** `dsm_assignment`, `framework_responsibility_assignment`, `technical_role_assignment`. | `US004` | 8 | **Un seul Booster actif par cercle** ; **un seul DSM actif** par consultant — les deux par index partiel **et** témoin |
| **`T9`** | **Historisation et contraintes temporelles.** Les **sept** relations du §25.2, sans chevauchement. | `US004` | 16 | Toute modification **clôture** la période précédente et en crée une neuve ; **tout chevauchement est rejeté par la base**, pas seulement par le service ; les 7 relations sont **comptées** |
| **`T10`** | **Contraintes de rôles et de périmètres.** `DG` implique `DSM` local ; aucune responsabilité métier active dans plusieurs entités ; Booster dans une seule entité. Services transactionnels du §25.4. | `US005` | 16 | Chaque règle a **deux** tests : celui qui l'enfreint, et le témoin qui la respecte |
| **`T11`** | **Isolation inter-entités.** Couples uniques `(id, entity_id)` et **clés étrangères composites** §25.3. Repositories et services de base. | `US006` | 16 | Une relation croisée entre deux entités est **refusée par la base** ; le contrôle **compte** les couples examinés et **nomme** ce qu'il n'a pas couvert |
| **`T12`** | **Factories, jeu de test et recette du modèle.** 25 entités, 5 000 profils, historiques cohérents et cas limites. Les contrôles §30 du modèle. Checklist de la porte `G2`. | `US007`, `US008` | — | Une base **vide** se construit **uniquement** par migrations ; les migrations se **rejouent** ; **aucune dépendance SQLite** ; les 7 critères de sortie sont à zéro |

**Douze sous-étapes, comme au LOT 1.** Chacune se termine par un rapport au format imposé et attend
la validation de Jonathan avant la suivante.

> **Le découpage suit une règle simple, et elle est délibérée : une sous-étape = une migration
> vérifiable.** Le §28 exige que **chaque** migration soit testée « sur une base vide, depuis la
> version précédente, et avec un rollback applicatif compatible lorsque possible ». Regrouper deux
> domaines dans une migration rendrait ce triple test impossible à attribuer en cas d'échec — c'est
> la leçon de `T6` au LOT 1, où trois défauts ont dû être introduits **un par un**, chacun dans sa
> propre poussée, pour que l'échec soit attribuable.

---

## 4. Fichiers et modules probablement affectés

**Créations attendues**, sous `apps/api/app/` — les modules suivent la nomenclature des portées de
commit, conventions §3.2 :

```text
app/entities/       entity, platform_setting, entity_setting, allowed_email_domain
app/people/         person, entity_membership, job_catalog, professional_status
app/organization/   circle, office, dsm, framework_responsibility, technical_role
app/shared/         base declarative, mixins des champs communs, types, periodes
alembic/versions/   une migration par sous-etape, T1 a T11
tests/integration/  les contraintes, sur PostgreSQL REEL
tests/factories/    factories de donnees FICTIVES
```

**Modifications attendues :** `alembic/env.py` (métadonnées et convention de nommage),
`pyproject.toml` (aucune dépendance nouvelle attendue — SQLAlchemy et Alembic sont déjà là),
`Makefile` (cibles de recette du modèle), et les registres.

**Aucune modification** de `packages/contracts` : il ne portera **aucun type métier** avant que des
routes existent, et il n'y en a pas dans ce lot.

---

## 5. Migrations prévues

**Onze migrations, `0002` à `0012`**, une par sous-étape de `T1` à `T11`. `0001_initial` reste
**vide** (`DEC-463`) et n'est pas modifiée : une migration appliquée ne se réécrit pas.

Chacune sera testée selon le §28 :

1. sur une base **vide** ;
2. **depuis la version précédente** ;
3. avec un **retour arrière** applicatif quand il est possible — et **quand il ne l'est pas, la
   migration le dira**, plutôt que de laisser croire le contraire.

> **Un piège hérité de `T9` au LOT 1, et il faut le connaître avant d'écrire la première
> migration :** après un démarrage à froid, `make migrate-status` sur une base non migrée
> **n'affiche rien et sort en 0**. Une sortie vide ne veut pas dire « tout va bien », elle veut
> dire « rien n'est appliqué ». Le contrôle de ce lot devra **compter les révisions appliquées et
> les confronter à un attendu**.

---

## 6. Tests à écrire

| Famille | Nature | Où |
|---|---|---|
| Contraintes d'unicité §25.1 | **intégration, PostgreSQL réel** — un index partiel ne s'éprouve pas en mémoire | `tests/integration/` |
| Contraintes temporelles §25.2 | **intégration** — le chevauchement doit être rejeté par la **base** | `tests/integration/` |
| Clés étrangères composites §25.3 | **intégration** — la référence croisée doit être refusée | `tests/integration/` |
| Règles métier §25.4 | **intégration** — service transactionnel, avec le témoin qui respecte la règle | `tests/integration/` |
| Migrations | base vide, montée, descente, rejeu | `tests/integration/` |
| Repositories et services | unitaires, sur transaction annulée | `tests/` |
| Factories | unitaires — cohérence des historiques produits | `tests/` |

> **« Aucune dépendance à SQLite n'existe pour les tests d'intégration » est un critère de sortie,
> pas une préférence.** Un index partiel, une contrainte d'exclusion et une clé étrangère composite
> **n'existent pas** en SQLite : un test qui passerait dessus ne prouverait rien. **Et un contrôle
> devra le vérifier**, plutôt que de compter sur la vigilance.

---

## 7. Démonstration attendue — les six éléments de la roadmap

| | Élément | Sous-étape qui le rend possible |
|:--:|---|---|
| 1 | création de Bordeaux et d'une seconde entité fictive | `T2` |
| 2 | création d'une personne et de son appartenance principale | `T4` |
| 3 | changement **historisé** de DSM, client et cercle | `T9` |
| 4 | **refus** d'une seconde entité principale active | `T4` |
| 5 | **refus** d'un Booster actif dans deux entités | `T10` |
| 6 | **refus** d'une relation croisée entre entités | `T11` |

**Trois des six sont des REFUS.** Une démonstration qui montrerait seulement que les créations
fonctionnent ne démontrerait pas la moitié de ce lot.

---

## 8. Risques propres au lot

| Risque | Nature | Parade proposée |
|---|---|---|
| **Une contrainte d'exclusion mal posée se découvre quand les données existent** | conception | `T9` avant `T12` : les contraintes sont éprouvées **avant** que le jeu de 5 000 profils ne soit engendré |
| **Le jeu de 25 entités / 5 000 profils sur cette machine** — 16 Gio, 7,75 Gio alloués à Docker | exploitation | **mesurer** le temps et la mémoire, et l'annoncer. `QO-085` a montré que la mesure surprend |
| **Un ordre de migration circulaire** : les champs communs §3.1 portent `created_by_person_id`, or `entity` précède `person` | technique | choix à trancher en `T1`, §9.2 point 1 |
| **`autogenerate` d'Alembic ignore ou déforme les index partiels et les contraintes d'exclusion** | technique | choix à trancher en `T1`, §9.2 point 7 |
| **Le LOT 2 est le premier à créer des tables : `make destroy` devient destructeur de données** | exploitation | l'avertissement de `destroy` devra **mesurer** ce qu'il détruit, comme `T9` l'a appris (§7.21) |

---

## 9. Décisions encore nécessaires

### 9.1 Questions ouvertes à trancher — les deux sont bloquantes pour `T1`

| ID | Question | Pourquoi elle bloque |
|---|---|---|
| `QO-111` | **Fournisseur de collation PostgreSQL** | **Ne se change pas sans recréer le cluster.** Doit être tranché avant la première table |
| `QO-112` | **Liste des extensions PostgreSQL** | `CREATE EXTENSION` exige des droits élevés, et **le choix du §9.2 point 3 en dépend** : une contrainte d'exclusion sur `(uuid, plage temporelle)` réclame `btree_gist` |

### 9.2 Choix techniques que les documents validés ne tranchent pas

**Sept, à instruire en `T1` et à trancher avec Jonathan. Aucun ne sera inventé** — c'est la règle
§6.5, la plus utilisée du LOT 1.

1. **`created_by_person_id` et `updated_by_person_id`** : clé étrangère vers `person` — impossible
   en `T2`, où `person` n'existe pas encore — ou colonne `uuid` sans contrainte ? Le §3.1 écrit
   `uuid null` et **ne mentionne aucune clé étrangère**.
2. **Représentation d'une période** : deux colonnes `starts_at` / `ends_at`, comme le §25.1
   l'implique par ses `WHERE ends_at IS NULL`, ou une plage `tstzrange` que le §25.2 réclame pour
   ses contraintes d'exclusion ? Les deux, avec colonne générée ?
3. **Contraintes d'exclusion** : posées en base, ou règle de service seule ? Le §25.2 dit
   « **pourra** utiliser », ce qui est une permission, pas une prescription.
4. **Énumérations** : type `enum` PostgreSQL, contrainte `CHECK`, ou table de référence ? Le modèle
   énumère des valeurs sans imposer de représentation.
5. **Convention de nommage des contraintes** : sans elle, un retour arrière de migration ne
   retrouve pas les objets qu'il doit défaire.
6. **Génération des UUID** : applicative, ou `gen_random_uuid()` — ce qui rattache le choix à
   `QO-112`.
7. **`autogenerate` d'Alembic** : activé, ou migrations écrites à la main ?

### 9.3 Un écart échu dans ce lot

**`ECART-012` — « la valeur `intercontrat` est imposée à une direction générale ».** Son registre le
dit : « à clarifier avec Léa et l'ESM, **au plus tard au LOT 2** lors de l'implémentation de
`professional_status_assignment`, et avant le LOT 5 ». Il est donc rattaché à **`T5`**.

**Ce n'est pas une décision technique** : la recommandation du registre est de **ne pas modifier le
modèle**, et d'arbitrer entre conditionner l'affichage ou ajouter une troisième valeur. **Léa décide
du produit.** `T5` l'instruira et le posera, il ne le tranchera pas seul.

---

## 10. Checklist de validation de la porte `G2`

Les **sept** critères de sortie de la roadmap, littéralement :

| | Critère | Sous-étape qui le prouve |
|:--:|---|---|
| ☐ | toutes les migrations s'appliquent sur une base vide | `T12` |
| ☐ | les migrations sont rejouables dans un environnement de test | `T12` |
| ☐ | les contraintes critiques disposent de tests PostgreSQL | `T2` à `T11` |
| ☐ | les relations structurantes sont historisées | `T9` |
| ☐ | les tests d'isolation réussissent | `T11` |
| ☐ | aucune dépendance à SQLite n'existe pour les tests d'intégration | `T12`, **par un contrôle** |
| ☐ | **Jonathan valide le modèle implémenté** | la porte |

Et les critères du backlog §« Validation du lot » : les **sept** stories `P0` sont `Done`, la story
`P1` est terminée **ou** a fait l'objet d'un arbitrage explicite, la démonstration et les preuves
sont présentées, et Jonathan valide **explicitement** `G2` avant l'ouverture du lot suivant.

---

## 11. Ce que ce lot ne doit pas faire

- créer **une seule table d'authentification** — `user_account`, `magic_link_request`,
  `user_session`, `service_token`, `auth_event` : LOT 3 ;
- implémenter une authentification, même partielle, même de test, ni aucun contournement ;
- créer un écran, une page, ou une route métier de l'API ;
- déclarer un **type métier** dans `packages/contracts` avant qu'une route l'expose ;
- charger **une seule donnée réelle** de collaborateur — aucun CSV réel, aucune photo ;
- modifier `0001_initial`, ni aucune migration déjà appliquée ;
- modifier les **cinq documents de cadrage**, qui restent immuables ;
- créer une table d'un lot postérieur « pendant qu'on y est » ;
- introduire une dépendance SQLite pour les tests d'intégration ;
- exposer PostgreSQL, Redis, MinIO ou Mailpit ailleurs que sur `127.0.0.1` ;
- réutiliser une ligne du prototype historique.

---

**Cette fiche est un plan. Elle attend la validation de Jonathan sur le §3.**
