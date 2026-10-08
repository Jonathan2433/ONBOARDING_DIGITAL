# Compte rendu — `T1` du LOT 9 : les quatre tables de l'import CSV

**Sous-étape :** la première du lot — `import_batch`, `import_row`,
`import_row_issue` et `import_decision`
**Date :** 8 octobre 2026
**Décision :** `DEC-636`
**Stories :** socle — les huit stories du LOT 9 en dépendent

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faite | **`T1`** |
| Restent | `T2` à `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/imports/modeles.py` | les quatre tables du §19 et les trois énumérations (`EtatLotImport`, `EtatLigneImport`, `TypeDeDecisionImport`) |
| `apps/api/alembic/versions/0024_import_csv.py` | la migration, appliquée et rejouée depuis une base vide |
| `apps/api/tests/test_imports.py` | **13 tests**, dont **9 d'intégration** |
| `apps/api/tests/test_isolation.py` | couverture portée de 25 à **29** chemins composites |
| `apps/api/tests/test_socle_modele.py` | les quatre tables ajoutées à `TABLES_DECLAREES` |

Le schéma passe de **44 à 48 tables métier**, de 23 à **24 migrations**, tête `0024`,
sans nouveau déclencheur. `make migrations-check` confronte **754 colonnes**, **279
contraintes**, **234 index**, **10 déclencheurs** et **199 fonctions** : le schéma issu des
migrations est identique à celui qui tourne, et le retour à `base` ne laisse aucune table métier.

## 2.1 Toutes les relations répètent `entity_id`

Le §25.3 exige des clés étrangères composites `(id, entity_id)` pour toute relation entre deux
tables locales. Les trois tables dépendantes ferment donc **quatre** chemins :

- une ligne → son lot d'import ;
- une ligne → l'appartenance qu'elle met à jour (`target_membership_id`, nullable) ;
- un problème → la ligne qu'il concerne ;
- une décision → la ligne qu'elle concerne.

Chaque chemin est éprouvé dans les deux sens : un témoin de la même entité réussit, la seule
variation inter-entités échoue sur le nom exact de la clé. `make isolation-check` dérive désormais
**35 tables locales, 13 globales, 29 clés composites, zéro référence nue et zéro clé simple
injustifiée**.

## 2.2 Défaut trouvé par `make isolation-check`, corrigé avant commit

`import_batch.approved_by_person_id` avait d'abord été posé **sans** clé étrangère, par un faux
parallèle avec les trois colonnes d'auteur de `ChampsCommuns` (`created_by_person_id`,
`updated_by_person_id`, `archived_by_person_id`). Le contrôle d'isolation l'a refusé :
**ces trois colonnes sont la SEULE exception du dépôt**, parce qu'elles sont génériques et posées
sur TOUTE table ; toute colonne d'acteur **nommée** par un module — `media_asset.
uploaded_by_person_id`, `onboarding_template_version.published_by_person_id` — porte une clé
étrangère réelle vers `person`. Une référence nue donne la même observation qu'un schéma sans
fuite (§7.0 quatrième proposition de la passation) : corrigé, `approved_by_person_id` porte
désormais `fk_import_batch_approved_by_person_id_person`.

## 2.3 L'import reste synchrone — `async_job`/`outbox_message` ne sont pas posées

Arbitrage de Jonathan du 08/10/2026, posé **avant** d'écrire le schéma : l'import ne pose aucune
table `async_job` ni `outbox_message`, réservées au LOT 11 (précédent mesuré au LOT 7 `T10` :
aucune ligne du dépôt n'y écrit encore). Un test structurel (`test_l_import_reste_synchrone_
aucune_table_async_job_ni_outbox_message`) le fixe : il échouerait si une sous-étape future posait
l'une de ces deux tables sans décision explicite contraire.

## 2.4 Aucun vocabulaire de niveau n'est inventé pour les problèmes de ligne

Le §19.3 exige un « niveau » par problème de ligne, sans en donner le vocabulaire — exactement le
piège déjà rencontré sur `event_media.display_role` (LOT 8, `T1`). `import_row_issue.level` est
donc une chaîne bornée et non vide, jamais une énumération fermée inventée pour l'occasion.

## 2.5 Le schéma réel des colonnes CSV n'est pas ici, et ce n'est pas un oubli

`QO-096` et `QO-110` restent ouvertes : ni l'une ni l'autre ne bloque ce socle, parce que
`raw_data` et `normalized_data` sont volontairement opaques (`jsonb`). Le schéma logique
`F01`–`F19` (`DEC-434`, v1.0-initiale) n'intervient qu'à partir de `T6`/`T7`, quand une route lira
réellement un CSV. Inventer ici une liste de colonnes attendues trancherait `QO-096` par
anticipation (§6.5 de la passation).

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make stack-check` puis `make migrate` | huit services sains, tête `0024` |
| `uv run pytest -q apps/api/tests/test_imports.py` | **13/13** |
| témoin global des clés composites | **29/29** chemins couverts |
| `make migrations-check` | base vide → `0024` → schéma identique ; retour à `base` propre |
| `make isolation-check` | **35 locales, 29 composites, 0 référence nue, 0 clé simple injustifiée** |
| `make format-check`, `make lint`, `uv run mypy` | verts (201 fichiers) |
| collecte depuis la racine | **1 577 pytest**, dont **74 échecs environnementaux** (jeu de démonstration de développement, identiques en liste à ceux mesurés avant `T1`) |
| frontend | **794 Vitest** inchangés — aucun fichier frontend touché |

Les 74 échecs sont ceux déjà connus du jeu de démonstration chargé sur la base de développement
(§11 de la passation) : ils comptent des lignes en absolu et sont strictement identiques, un par
un, à ceux mesurés avant `T1` — aucune ligne Python applicative n'a changé ailleurs que dans
`apps/api/app/imports/`, les migrations et les trois fichiers de test cités ci-dessus.

---

# 4. Décisions et écarts

- `DEC-636` consigne la réalisation et les choix strictement dérivés du modèle ;
- `QO-096`, `QO-097`, `QO-099`, `QO-100`, `QO-110` restent ouvertes, non bloquantes pour ce socle ;
- `ECART-035` et `ECART-060` restent ouverts, à fermer explicitement à `T13` et `T8` ;
- aucun nouvel écart ni aucune nouvelle question n'est ouvert par `T1`.

---

# 5. Ce que `T1` laisse

- les quatre tables et la migration rejouable, prêtes pour `T2` ;
- aucune route, aucun service, aucun contrat HTTP anticipé ;
- `QO-096`/`QO-110` intactes : le schéma réel des colonnes reste à trancher par Jonathan avant
  tout import de données réelles, jamais par ce socle ;
- l'import reste synchrone, fixé par un test structurel.

# Validation demandée à Jonathan

`T1` est faite. Après fusion, la prochaine sous-étape est `T2` : création d'un collaborateur et de
son appartenance depuis le back-office (`US002`, 1/2).
