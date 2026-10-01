# Compte rendu — `T1` du LOT 8 : les quatre tables événementielles

**Sous-étape :** la première du lot — `event`, `event_circle_scope`,
`event_office_scope` et `event_media`  
**Date :** 1er octobre 2026  
**Décision :** `DEC-620`  
**Stories :** socle — les six stories du LOT 8 en dépendent

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faite | **`T1`** |
| Restent | `T2` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/events/modeles.py` | les quatre tables du §17 et l'énumération des quatre états |
| `apps/api/alembic/versions/0022_evenements.py` | la migration, appliquée et rejouée depuis une base vide |
| `apps/api/tests/test_evenements.py` | **16 tests**, dont **13 d'intégration** |
| `apps/api/tests/test_isolation.py` | couverture portée de 18 à **24** chemins composites |

Le schéma passe de **39 à 43 tables métier**, de 21 à **22 migrations**, tête `0022`,
sans nouveau déclencheur. `make migrations-check` confronte **673 colonnes**, **247
contraintes**, **205 index**, **10 déclencheurs** et **199 fonctions** : le schéma issu des
migrations est identique à celui qui tourne, et le retour à `base` ne laisse aucune table métier.

## 2.1 Toutes les relations répètent `entity_id`

Le §25.3 donne précisément l'exemple d'une relation entre un événement et un cercle :
`event_id`, `circle_id` et `entity_id` doivent former deux clés étrangères composites. La même
règle s'applique au bureau et au média. Les trois tables de relation sont locales en substance et
ferment donc **six** chemins :

- portée cercle → événement et cercle ;
- portée bureau → événement et bureau ;
- média d'événement → événement et actif média.

Chaque chemin est éprouvé dans les deux sens : un témoin de la même entité réussit, la seule
variation inter-entités échoue sur le nom exact de la clé. `make isolation-check` dérive désormais
**30 tables locales, 13 globales, 24 clés composites, zéro référence nue et zéro clé simple
injustifiée**.

## 2.2 « Passé » est une lecture, jamais un état

Le §17.1 et le §27 imposent la même règle : un événement passé est calculé depuis `ends_at`.
L'énumération reste donc strictement `draft`, `published`, `cancelled`, `archived` ; aucune
colonne `past`, `is_past` ou `passed_at` n'existe. La base impose seulement
`starts_at < ends_at`. `T2` appliquera la même ancre temporelle aux deux listes.

## 2.3 Aucun vocabulaire de rôle média n'est inventé

Le §17.3 exige « un ordre et un rôle d'affichage » sans nommer les rôles possibles.
`display_role` est donc une chaîne bornée et non vide, pas une énumération fermée. L'ordre est
positif et unique parmi les médias non archivés d'un même événement : le rendu futur est
déterministe sans figer une liste absente des sources.

## 2.4 Les absences du MVP sont structurelles

Il n'existe aucune table ni colonne de récurrence, occurrence, participant, inscription, présence
ou notification métier. Un test balaie les quatre tables et tout le catalogue déclaré. Les contrats
HTTP n'existent pas encore en `T1` : `T3`/`T4` devront étendre ce même témoin aux modèles de
requête et au manifeste, faute de quoi le critère de sortie ne serait que partiellement prouvé.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make stack-check` puis `make migrate` | huit services sains, tête `0022` |
| `uv run pytest -q apps/api/tests/test_evenements.py` | **16/16** |
| témoin global des clés composites | **24/24** chemins couverts |
| `make migrations-check` | base vide → `0022` → schéma identique ; retour à `base` propre |
| `make isolation-check` | **30 locales, 24 composites, 0 référence nue, 0 clé simple injustifiée** |
| `make format-check`, `make lint`, `make typecheck` | verts |
| collecte depuis la racine | **1 430 pytest**, dont **1 046 d'intégration** |
| frontend | **706 Vitest** inchangés |

La sélection historique complète de `test_isolation.py` a aussi révélé cinq témoins qui comptent
toute leur table et supposent une base vide, alors que le volume de développement contient déjà
des milliers de lignes de test. Ces cinq échecs existaient dans l'environnement, ne touchent aucun
test du LOT 8 et ne sont pas masqués : le contrôle structurel autonome et les 16 nouveaux tests
passent. La CI repartira, elle, d'une base propre.

---

# 4. Décisions et écarts

- `DEC-620` consigne la réalisation et les choix strictement dérivés du modèle ;
- `ECART-067` reste ouvert : la portée « consultants » du DSM doit être tranchée avant `T3` ;
- `ECART-068` reste ouvert : l'audit transverse doit être instruit avant de fermer `US004` ;
- aucun nouvel écart ni aucune nouvelle question n'est ouvert par `T1`.

---

# 5. Ce que `T1` laisse

- les quatre tables et la migration rejouable, prêtes pour `T2` ;
- la lecture à venir/passée à construire uniquement depuis `ends_at` ;
- aucune route, aucun service, aucun contrat HTTP anticipé ;
- `ECART-067` et `ECART-068` intacts, sans extension silencieuse du modèle.

# Validation demandée à Jonathan

`T1` est faite. Après fusion, la prochaine sous-étape est `T2` : lecture paginée des événements
à venir et passés, événements annulés visibles et archivés absents.
