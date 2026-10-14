# Compte rendu — `T2` du LOT 9 : créer un collaborateur depuis le back-office

**Sous-étape :** la deuxième du lot — `MVP-L09-US002` (1/2)
**Date :** 8 octobre 2026
**Décision :** `DEC-637`
**Stories :** `US002` (1/2) — la création ; `T3` livrera les transitions structurantes

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | `T1`, **`T2`** |
| Restent | `T3` à `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/people/creation.py` | le service `creer_un_collaborateur`, les six écritures relationnelles dans l'ordre que les déclencheurs contraignent |
| `apps/api/app/permissions/perimetre.py` | `resoudre_l_autorisation_de_creation`, la grille du §6.1 « Créer manuellement un profil » sans `cible` existante |
| `apps/api/app/people/routes.py` | `POST /entities/{code}/people`, `DemandeDeCreationDeCollaborateur`, `ReponseDeCreationDeCollaborateur` |
| `packages/contracts/src/contrat-api.json` | l'entrée `creationDUnCollaborateur`, chemin et méthode déclarés dès cette sous-étape — aucun module TypeScript propre, aucun écran consommateur avant `T14` |
| `apps/api/tests/test_creation_collaborateurs.py` | **13 tests**, dont **12 d'intégration** |

Aucune migration : `T2` écrit dans le schéma posé par les LOTS 2, 5 et 6 (`person`,
`entity_membership`, `membership_job_assignment`, `circle_membership`,
`professional_status_assignment`, `dsm_assignment`).

## 2.1 La première écriture du projet qui crée une personne

Mesuré avant d'écrire une ligne : `grep -rn "INSERT INTO person"` hors tests et hors
`app/shared/fabriques.py` (le générateur de données fictives) ne rend **aucune** occurrence.
Toutes les routes existantes modifient, archivent ou restaurent une personne déjà présente ;
aucune n'en créait. Le même constat vaut pour `entity_membership` : seul le générateur de données
fictives y écrivait, jamais une route métier.

## 2.2 La catégorie professionnelle reste `consultant`, et ce n'est pas un oubli

Le déclencheur `dg_implique_dsm_local` exige qu'une responsabilité DSM existe **déjà** pour la
personne au moment où `entity_membership.professional_category` devient `dg`. Le service qui
satisfait cet invariant, `app.organization.services.attribuer_la_categorie_dg`, **n'est exposé par
aucune route à ce jour** — mesuré. L'exposer ici aurait mélangé deux mécanismes distincts (créer
une appartenance ; promouvoir une catégorie) et anticipé une route que personne n'a demandée.
`professional_category` n'est donc **pas** un champ de la demande : toute création par cette route
est un `consultant`. Un test structurel (`test_la_demande_ne_porte_aucune_categorie_
professionnelle`) le fixe.

## 2.3 Le périmètre de création n'a pas de cible à interroger, et c'est la vraie différence

`resoudre_le_perimetre` (modification, `T7` du LOT 5) répond « quels champs sur CETTE cible » en
interrogeant `dsm_assignment`/`circle_membership` existants. À la création, cette cible n'existe
pas encore : **la proposition porte ce que la cible aurait porté**. Un DSM ne crée que pour
LUI-MÊME (`dsm_person_id = acteur`, même règle que `_RATTACHE_A_CE_DSM`) ; un Booster ne crée que
dans SON cercle (même règle que `_TYPE_DANS_LE_CERCLE_DU_BOOSTER`) et ne peut PAS assigner de DSM
du tout (même exclusion que `CHAMPS_DU_BOOSTER` pour la modification, « hors changement de DSM »)
— la différence étant qu'ici l'exclusion porte sur la proposition entière (403), pas sur un champ
écrivable en moins.

## 2.4 Le déclencheur `dsm_responsabilite_active` est traduit, pas masqué

`fn_dsm_responsabilite_active` (migration `0009`) refuse un `dsm_assignment` dont le DSM désigné
n'a pas de responsabilité DSM active dans l'entité, avec `ERRCODE = 'check_violation'` — déjà
couvert par `traduire_un_refus_de_la_base` (LOT 5, `T7`), réutilisé tel quel. Un test le prouve :
le refus sort en `422`, jamais en `500`.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_creation_collaborateurs.py` | **13/13** |
| `make isolation-check` | inchangé — 35 locales, 29 composites, 0 référence nue |
| `uv run pytest apps/api/tests/test_contrat.py` | **5/5** — chemins du schéma et du manifeste identiques dans les deux sens |
| `make format-check`, `make lint`, `uv run mypy` | verts (203 fichiers) |
| collecte depuis la racine | **1 590 pytest** (+13), dont **1 178 d'intégration** (+12) ; **74 échecs environnementaux**, liste identique à celle mesurée avant `T2` |
| frontend | **794 Vitest** inchangés — aucun fichier frontend touché |
| `make audit` | zéro avis |

**Défaut trouvé et corrigé avant tout commit, dans mes propres tests de permission.** Le premier
jet de `test_TEMOIN_un_ESM_cree_sans_restriction` donnait un acteur sans aucune responsabilité
Framework, en supposant — à tort — qu'`ESM` se dérive de la seule appartenance. La résolution
réelle (`resoudre_les_permissions`) a renvoyé un ensemble de rôles vide, et le test a échoué en le
disant : `ESM` est une responsabilité `framework_responsibility_assignment`, comme `DSM` et
`BOOSTER`. Corrigé en donnant à l'acteur la responsabilité `ESM`, et les cinq tests de la grille de
permission ont ensuite été réécrits pour dériver les rôles via `resoudre_les_permissions` plutôt
que de les injecter à la main — une couverture plus fidèle, qui aurait attrapé la même erreur
immédiatement.

---

# 4. Décisions et écarts

- `DEC-637` consigne la réalisation et les choix strictement dérivés du modèle ;
- aucun nouvel écart ni aucune nouvelle question n'est ouvert par `T2` ;
- `ECART-035`, `ECART-060` restent ouverts, à fermer explicitement à `T13`/`T8` ;
- un résiduel est nommé, pas un écart : `professional_category = 'dg'` reste inatteignable par
  cette route — `attribuer_la_categorie_dg` n'est exposé par aucune route, et ce n'est pas le
  périmètre de `T2` de le faire.

---

# 5. Ce que `T2` laisse

- un collaborateur complet se crée en une transaction, avec ses cinq relations organisationnelles ;
- les transitions structurantes (changement d'entité, de statut, de rattachement) restent `T3` ;
- `professional_category = 'dg'` reste hors de portée de cette route, nommé explicitement ;
- le manifeste du contrat déclare la route dès cette sous-étape, sans module TypeScript propre —
  même discipline que `T7` du LOT 8 pour les arrivées récentes.

# Validation demandée à Jonathan

`T2` est faite. Après fusion, la prochaine sous-étape est `T3` : modification structurante et
transitions (changement d'entité, de statut, de rattachement) sur un collaborateur déjà créé.
