# Compte rendu — `T9` du LOT 9 : import transactionnel des lignes valides

**Sous-étape :** la neuvième du lot — `MVP-L09-US006` (1/2)
**Date :** 12 octobre 2026
**Décision :** `DEC-644`
**Stories :** `US006` (1/2)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, `T8`, **`T9`** |
| Restent | `T10` à `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Le point arbitré par Jonathan avant tout code

`T7` (`DEC-642`) avait explicitement renvoyé la majorité du référentiel du
LOT 0 — `codes-erreurs-import.md`, 68 codes sur 12 domaines — à « l'import
réel », en ne construisant que l'e-mail et les doublons de personne. Le
découpage validé du lot ne nomme aucune sous-étape dédiée à ces autres
domaines (date, identité, entité, métier, situation, cercles, DSM,
responsabilités Framework, rôles techniques, autorisation photo) : `T9`,
« import transactionnel », est la seule sous-étape restante qui les touche.

Posé à Jonathan avant d'écrire une ligne : fallait-il construire la
quarantaine de codes restants maintenant, au prix d'une sous-étape
nettement plus grosse que les précédentes, ou se limiter à écrire en base
les lignes déjà jugées bonnes par `T7`/`T8` (e-mail et client), en
traitant tout le reste par un rejet générique ?

Réponse — **tout construire maintenant**. Risque assumé : `T9` est,
mesuré, la sous-étape la plus large du lot (deux nouveaux modules, 17
tests, deux défauts d'architecture trouvés en construisant).

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/imports/structures.py` | **nouveau** — `Probleme`, les trois niveaux (`E`/`D`/`W`), extraits d'`analyse.py` pour éviter un import circulaire |
| `apps/api/app/imports/organisation.py` | **nouveau** — valide et résout `F02`–`F19` (hors `F01`, `F13`) |
| `apps/api/app/imports/execution.py` | **nouveau** — `lancer_l_import`, la transaction réelle |
| `apps/api/app/imports/analyse.py` | **modifié** — `Probleme`/niveaux déplacés vers `structures.py` ; `_etat_depuis_les_problemes` renommé `etat_depuis_les_problemes` (public), réutilisé par `execution.py` |
| `apps/api/app/imports/decisions.py` | **modifié** — défaut corrigé : `person_merge`/`profile_reactivation` exigent désormais `ROLES_DU_CYCLE_DE_VIE` |
| `apps/api/app/imports/routes.py` | **modifié** — `POST .../imports/{lot}/lancement` |
| `apps/api/app/people/creation.py` | **modifié** — `DemandeDAppartenance.job_catalog_id`/`circle_id` deviennent nullables |
| `apps/api/tests/test_import_transactionnel.py` | **nouveau** — **17 tests**, tous d'intégration |
| `packages/contracts/src/contrat-api.json` | **modifié** — `lancerLImport` |

Aucune migration : `T9` écrit dans des tables déjà posées (LOT 2 pour
`person`/`entity_membership`/`framework_responsibility_assignment`/
`technical_role_assignment`/`dsm_assignment`, `T1` du LOT 9 pour
`import_row`/`import_decision`).

## 3.1 Pourquoi `app.imports.organisation` n'est JAMAIS appelé à la prévisualisation

Premier essai, abandonné : appeler `valider_les_champs_organisationnels`
depuis `analyser_le_lot` (la même fonction que `T7`/`T8`), pour que la
prévisualisation montre tout de suite les ~40 nouveaux codes. Mesuré :
cela cassait **24 tests existants** de `test_analyse_import.py` et
`test_rapprochement_clients.py` — leurs CSV minimaux (`email,nom,prenom`)
n'avaient jamais eu besoin de renseigner `F05`–`F19`, et le fait de les
valider désormais faisait apparaître des dizaines de codes nouveaux
(métier absent, cercle absent, DSM absent…) sur des lignes que ces tests
jugeaient `valid` depuis `T7`.

Revert explicite. Relu le texte de `T7` au pied de la lettre : « les
autres règles […] ne seront vérifiées qu'au moment de l'import réel
(`T9`) » — pas à la prévisualisation. `app.imports.organisation` n'est
donc appelé que par `app.imports.execution.lancer_l_import`, à l'instant
réel du lancement, jamais en cache entre les deux appels : un métier créé
ou un cercle archivé **entre** la prévisualisation et le lancement change
le verdict, et c'est voulu — voir §3.4. Seule chose partagée entre les
deux modules : `etat_depuis_les_problemes` (la priorité `E > D > W`),
renommée publique pour ne pas dupliquer cette logique.

## 3.2 Pourquoi `D-METIER-001`/`D-CERCLE-001`/`D-BUREAU-001` ne passent jamais par `import_decision`

Le modèle §19.4 ferme `TypeDeDecisionImport` à **cinq** catégories (`T1`),
aucune ne nommant une création de catalogue. Le rapprochement client a
**deux** catégories dédiées (`T8`) parce qu'un nom de client peut
*ressembler* à plusieurs candidats — une ambiguïté réelle à trancher par
un humain, dans l'API. Un code de métier, de cercle ou de bureau est une
correspondance **exacte** ou rien : la décision attendue par le
référentiel (« créer l'entrée au catalogue, ou corriger la valeur ») est
**toujours hors-ligne** — un écran d'administration futur, ou une
correction du CSV suivie d'un nouveau dépôt — jamais un geste de ce
module. Ajouter une sixième catégorie exigerait une migration que le
découpage ne nomme pas pour `T9`.

La ligne reste `needs_decision` tant que l'entrée n'existe pas — et ce
n'est **pas une anomalie** : la formule de réconciliation du §4 de
`criteres-qualite-import.md` (`total = créations + mises à jour + rejets
+ en attente de décision`) le prévoit explicitement.

## 3.3 L'atomicité par ligne : premier `SAVEPOINT` du projet

Modèle §19.5, littéralement : « L'import des lignes valides […] garantit
pour chaque ligne […] aucune mise à jour partielle […] une ligne rejetée
n'empêche pas les lignes valides d'être importées. » Chaque ligne
éligible s'écrit donc dans son propre `SAVEPOINT`
(`connexion.begin_nested()`) — **premier usage de cette primitive dans ce
projet**, aucune autre sous-étape n'ayant eu besoin d'isoler un échec
partiel à l'intérieur d'une transaction HTTP unique. Un refus de la base
sur une ligne (contrainte d'exclusion, de vérification…) annule sa seule
écriture, jamais celle des lignes déjà traitées ni celles qui suivent.

## 3.4 Deux passes, pour que le DSM se résolve dans le fichier

schéma-csv-collaborateurs.md §5.5 : `F16` (le DSM) « doit désigner une
personne présente dans le fichier ou en base ». Une personne du fichier
n'existe réellement qu'après que ce module l'a créée, et sa
responsabilité DSM (`F17=DSM`, ou `F08=dg` par `RIGHTS-005`) n'existe
réellement qu'après que ce module l'a accordée.

- **Passe 1** crée ou met à jour chaque ligne éligible : personne,
  appartenance, métier, cercles principal et secondaires, statut/client,
  responsabilités Framework, rôles techniques, catégorie `dg` → DSM
  automatique (`RIGHTS-005`, réutilise
  `app.organization.services.attribuer_la_categorie_dg`), départ déjà
  passé → archivage immédiat (réutilise
  `app.people.archivage.archiver_un_profil` tel quel, qui enchaîne lui-même
  `enregistrer_un_depart`).
- **Passe 2**, une fois que la passe 1 a tout écrit, résout chaque `F16`
  par une requête ordinaire — plus besoin d'aucune logique « candidat du
  fichier », puisque la responsabilité DSM visée existe désormais
  réellement en base, quelle que soit la ligne qui l'a créée.

## 3.5 Ce qui est réutilisé tel quel, et ce qui change

- `app.people.creation.creer_un_collaborateur` (`T2`) pour la **création** ;
- `app.people.ecriture.modifier_les_donnees_organisationnelles` (LOT 5
  `T7`) pour la **mise à jour par e-mail** (`person_merge`) ;
- `app.people.archivage.restaurer_un_profil` (LOT 5 `T8`) pour la
  **réactivation** (`profile_reactivation`, confirmation explicite).

**`DemandeDAppartenance.job_catalog_id` et `.circle_id` deviennent
nullables** (`app.people.creation`, `T2`) : un profil `future` n'a pas
encore de métier assigné, et un DSM peut ne pas avoir de cercle principal
(schéma-csv §5.5, « un DSM peut ne pas avoir de cercle principal »). Le
formulaire de `T2` continue d'exiger les deux à son propre niveau — son
schéma Pydantic les déclare obligatoires — cette largeur ne sert que le
second appelant.

## 3.6 Défaut trouvé et corrigé avant commit, dans le code de `T8`

La route générique de décision (`app.imports.decisions`, `T8`) autorisait
un DSM dans son périmètre à enregistrer `person_merge` ou
`profile_reactivation` — correct pour `client_alias_creation`/
`canonical_client_selection` (matrice §14 « Valider les rapprochements
clients », DSM Consultants), mais `person_merge`/`profile_reactivation`
relèvent d'une **autre** ligne de la matrice (« Réactiver un profil
archivé » : DSM à **tiret**, ESM/ADM-E « Confirmation explicite », SUPER
Global — exactement `app.permissions.perimetre.ROLES_DU_CYCLE_DE_VIE`).
`codes-erreurs-import.md` §5 le confirme : `D-PERSONNE-001`/`002` ne
nomment ni Booster ni DSM parmi « qui décide ». Jamais exercée par `T8`,
qui ne testait que les deux types « client ». Corrigé : ces deux types
exigent désormais `ROLES_DU_CYCLE_DE_VIE`, un test le prouve
(`test_un_dsm_ne_peut_plus_enregistrer_une_reactivation`).

## 3.7 Ce que ce module ne pose jamais

- **`F19` (autorisation photo)** : validée seulement. `photo_authorization.
  media_asset_id` est `NOT NULL` (modèle §12.2, LOT 5) et aucun média
  n'existe à l'import — rien à quoi rattacher une autorisation ;
- **un changement de `professional_category` sur une personne existante**
  (fusion ou réactivation) : les six champs de `ChampOrganisationnel` (LOT
  5 `T7`) ne l'incluent pas, et `attribuer_la_categorie_dg` est le seul
  service qui sache poser un `dg` sans violer `dg_implique_dsm_local` — il
  n'est appelé qu'à la création ;
- **l'état `failed` du diagramme §24.4** : `T9` tourne dans une seule
  transaction HTTP synchrone (`DEC-462`). Un échec non rattrapé fait
  échouer la transaction entière, ce qui laisse le lot `preview_ready`
  (rien n'est jamais persisté) plutôt que de le figer dans un `importing`
  ou `failed` dont personne ne pourrait repartir avant le LOT 11.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_import_transactionnel.py` | **17/17** |
| `uv run pytest -q apps/api/tests/test_depot_import.py apps/api/tests/test_analyse_import.py apps/api/tests/test_rapprochement_clients.py` | **48/48** (inchangés) |
| `uv run pytest -q apps/api/tests/test_contrat.py` | **5/5** |
| `uv run mypy` (racine) | vert, **228 fichiers** (+4) |
| `make lint`, `make format-check` | verts |
| `make isolation-check` | **inchangé** — 35 tables locales, 29 clés composites |
| `make migrations-check` | vert — tête `0025`, aucune migration nouvelle |
| `make docs-check`, `make sources-check` | verts |
| `make audit` | zéro avis |
| `make test-frontend` | **794 Vitest** inchangé (380 + 120 + 294) |
| collecte depuis la racine | **1 678 pytest** (+17, tous d'intégration) |
| zéro régression | **74 échecs environnementaux**, conforme à la base — voir §4.1, un 75ᵉ échec transitoire trouvé et CORRIGÉ avant la fusion |

## 4.1 Un 75ᵉ échec environnemental, pas de `T9` dans son origine — mais corrigé ICI

**Mesure initiale, avant d'écrire une ligne de plus :** la pleine suite
rendait **75** échecs sur la branche contre **74** attendus. Diagnostiqué
avant de conclure (§7.18 de `CLAUDE.md`) : `git stash` de tout le travail
de `T9`, re-mesure sur `develop` strictement — **75** échecs identiques,
même liste de fichiers. Le nouvel échec n'était donc pas une régression
**introduite par le code de `T9`** — mais ce diagnostic initial s'est
arrêté un cran trop tôt : il concluait « résidu hors périmètre, non
corrigé », alors que la cause réelle touchait bien plus qu'un seul test.

**Ce que l'intégration continue a révélé, sur une base VRAIMENT fraîche**
(celle de `make residu-check`, sans aucune pollution locale) : non pas
un, mais **36 échecs**, répartis sur **quatre fichiers** —
`test_analyse_import.py` (`T7`), `test_depot_import.py` (`T6`),
`test_rapprochement_clients.py` (`T8`) et `test_import_transactionnel.py`
(`T9`, cette sous-étape elle-même) — tous portant le même code
`E-EMAIL-003` (domaine refusé) sur des lignes dont l'adresse est
parfaitement valide.

**Cause exacte, mesurée :** `make migrate` sème le domaine global
`exalt-company.com` via `make domaines-provision`, avec
`starts_at = now()` — à l'instant RÉEL où la stack démarre. Les quatre
fichiers comparent ensuite ce domaine à `INSTANT`, une constante **fixe**
(2026-10-10 09:00 UTC) commune aux quatre. Tant que le calendrier réel
n'avait pas dépassé cette date, `period @> INSTANT` restait vrai ; une
fois dépassée, la période du domaine commence APRÈS `INSTANT`, et
`period @> INSTANT` devient faux pour CHAQUE ligne du domaine — exacte-
ment la classe `§7.47` de `CLAUDE.md` (« une date absolue dans un test
est une bombe à retardement datée »), ici sous une forme plus insidieuse :
ce n'est pas une date absolue écrite dans un test qui vieillit, c'est
`now()`, injecté par un script de STACK hors du contrôle d'un test, qui
finit par dépasser l'ancre fixe à laquelle quatre fichiers le comparent.
`test_import_transactionnel.py` reproduisait le MÊME défaut dans son
propre helper `_domaine_local` (`starts_at = now()`), découvert en
écrivant ce correctif — pas anticipé par la fiche.

**Pourquoi il ne se voyait pas en local, et pourquoi la CI l'a vu :** une
ligne globale résiduelle de ce dépôt de développement porte
`starts_at = 2026-09-30`, antérieure à `INSTANT` — elle masquait le défaut
localement en fournissant, par accident, exactement la ligne qu'il fallait.
Une base fraîche (CI, ou `make destroy` suivi d'un redémarrage) n'a pas ce
résidu : seul le domaine semé **au moment présent** y existe, et la
période ne couvre plus `INSTANT`. §7.23 de `CLAUDE.md` : « un état dormant
ne se voit pas dans l'état courant ».

**Correctif appliqué, dans ce même `T9`, avant la fusion** : les quatre
fichiers insèrent désormais une seconde ligne `allowed_email_domain`,
globale, bornée dans le PASSÉ (`starts_at = '2020-01-01T00:00:00+00:00'`,
sans fin) — jamais `now()`. Elle vit dans la transaction annulée du test
(même fixture `cx`), donc elle ne laisse aucun résidu et ne touche jamais
la ligne réellement semée par `make migrate`. `test_analyse_import.py`
et `test_import_transactionnel.py` ont aussi vu leur propre
`_domaine_local` corrigé du même `now()` vers la même borne fixe.
Bien que `test_depot_import.py` (`T6`) et `test_rapprochement_clients.py`
(`T8`) soient des fichiers de sous-étapes déjà fusionnées, ce correctif
les touche : un défaut trouvé en construisant une sous-étape, qui atteint
des tests déjà livrés, se corrige — règle n°10 du §2 de `CLAUDE.md`
mise en pratique, pas contournée en ouvrant un écart de plus.

Mesuré après correctif : les quatre fichiers (65 tests, 58 d'intégration)
passent intégralement, et la pleine suite revient à **74** échecs
environnementaux — la base documentée, inchangée.

---

# 5. Décisions et écarts

- `DEC-644` consigne la réalisation, l'arbitrage de Jonathan (construire
  tout le référentiel maintenant), les deux découvertes d'architecture
  (§3.1, §3.2), le défaut corrigé dans `T8` (§3.6) et le défaut de
  datation partagé par quatre fichiers de test, trouvé par l'intégration
  continue et corrigé avant la fusion (§4.1) ;
- aucune nouvelle question n'est ouverte par `T9` ;
- aucun écart n'est ouvert pour le défaut du §4.1 : il est corrigé dans
  cette même pull request, dans les quatre fichiers qu'il touchait,
  avec preuve que la pleine suite revient à la base documentée (74).

---

# 6. Ce que `T9` laisse

- une ligne `valid`/`warning`, ou `needs_decision` dont une décision
  enregistrée résout le code, est désormais réellement importée ou mise à
  jour ;
- `import_row.state` devient `imported`/`updated`/`rejected` pour les
  lignes traitées ; `import_batch.state` devient `completed` ;
- aucun rapport consolidé n'est encore produit (créations/mises à
  jour/avertissements/rejets, réconciliation du total) : c'est `T10` ;
- aucun rejeu des lignes rejetées : c'est `T10` ;
- aucun écran ne consomme encore cette route (aucun consommateur avant
  `T14`).

# Validation demandée à Jonathan

`T9` est faite. Après fusion, la prochaine sous-étape est `T10` : le
rapport d'import (créations/mises à jour/avertissements/rejets), le rejeu
des lignes rejetées, la conservation temporaire maîtrisée du CSV source
(`US006`, 2/2).
