# Compte rendu — `T3` du LOT 8 : créer un événement et résoudre le périmètre d'écriture

**Sous-étape :** la troisième du lot — `POST /entities/{code}/events`
**Date :** 4 octobre 2026
**Décision :** `DEC-622`
**Story :** `MVP-L08-US004` (1 sur 3)
**Écart fermé :** `ECART-067`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1`, `T2`, **`T3`** |
| Restent | `T4` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Préalable : instruction et arbitrage d'`ECART-067`

La matrice §11 donne au DSM deux portées de création, « Entité ou consultants », là où le modèle
validé (§17.2) n'en représente que trois : entité entière, un ou plusieurs cercles, un ou
plusieurs bureaux. Aucune des trois n'est « les consultants d'un DSM » — ce n'est pas une unité
organisationnelle stable comme un cercle ou un bureau, à laquelle un événement se rattacherait par
un identifiant fixe, mais un ensemble de personnes résolu dynamiquement par `dsm_assignment`
(modèle §8.5).

Deux options ont été présentées à Jonathan, avant tout code :

- **Option A (recommandée) :** une cinquième table, `event_dsm_scope(event_id, entity_id,
  dsm_person_id)`, symétrique aux deux portées déjà posées par `T1` — même motif de clé composite,
  même discipline d'isolation ;
- **Option B :** une colonne unique sur `event`, `dsm_scope_person_id`, plus légère mais rompant
  l'uniformité structurelle avec les deux autres portées, qui sont des tables.

**Arbitrage explicite de Jonathan : Option A.** La table est posée par la migration `0023`,
`dsm_person_id` référençant `person.id` par une clé SIMPLE — exactement le choix déjà fait par
`dsm_assignment.dsm_person_id` (modèle §8.5) — et un index unique partiel sur `event_id` **seul**
(pas sur le couple `(event_id, dsm_person_id)` comme les tables sœurs) rend structurel ce que la
matrice écrit en disjonction : « Entité OU consultants », jamais les deux à la fois.

`ECART-067` est clos. Détail dans `docs/decisions/registre-ecarts.md`.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/events/modeles.py` | `EventDsmScope`, la cinquième table |
| `apps/api/alembic/versions/0023_evenement_portee_dsm.py` | la migration, appliquée et rejouée depuis une base vide |
| `apps/api/app/events/perimetre.py` | `peut_creer_un_evenement` (la grille complète du §11), `verifier_le_rattachement_au_cercle`/`_bureau` |
| `apps/api/app/events/ecriture.py` | `creer_un_evenement` — validation de portée, résolution de cercle/bureau par code, écriture en une transaction |
| `apps/api/app/events/routes.py` | `POST /entities/{code}/events`, `DemandeDeCreationDEvenement`, `ReponseDeCreationDEvenement` |
| `apps/api/tests/test_evenements.py` | **+3 tests** — témoin positif et deux témoins d'isolation/unicité pour `event_dsm_scope` |
| `apps/api/tests/test_creation_evenements.py` | **24 tests** — structure (5), service (19 marqués `integration`) |
| `packages/contracts/src/contrat-api.json` | entrée `creationDUnEvenement` |

## 3.1 La grille du §11 n'est pas une seule ligne de création, contrairement aux contenus du LOT 6

Au LOT 6, une seule ligne de création (« Créer un contenu général ») était réservée à `ESM`,
`ADM-E` et `SUPER` : Booster et responsable de bureau ne créaient rien, ils **modifiaient** le
contenu d'une ressource déjà créée. Ici, la matrice §11 donne directement à Booster et responsable
de bureau un droit de **création**, borné à LEUR cercle ou LEUR bureau. Une seule grille coarse
(« a le droit de créer ») ne suffit donc pas : il faut savoir **quelle portée** est demandée pour
savoir **quel rôle** l'autorise.

La route ne le sait qu'avec le corps de la requête, jamais avant : la garde de route
(`exiger_un_role_dans_l_entite`) se limite donc à exiger l'un des six rôles qui portent au moins
une ligne du §11 (`EMP` exclu), et `creer_un_evenement` revalide le couple (rôle, portée précise)
via `peut_creer_un_evenement` — même répartition que `ecrire_le_contenu_d_une_page` au LOT 6, qui
revalide le couple (rôle, page) après sa propre garde coarse.

## 3.2 L'asymétrie entre deux porteurs du même rôle est la preuve qui compte

Un refus de la forme « Booster, portée cercle, refusé » ne prouve rien tant qu'il n'est pas
apparié à un témoin où **le même Booster** réussit sur **son** cercle. La suite pose donc, pour
Booster et pour responsable de bureau, le couple : succès sur sa propre ressource, refus sur celle
d'un autre porteur du même rôle dans la même entité. Sans ce couple, une fonction qui refuserait
toujours passerait aussi bien les refus (§7.39 de la passation).

## 3.3 L'isolation inter-entités sur la résolution par code

Un cercle ou un bureau nommé par son `code` est résolu à l'intérieur de l'entité du chemin, jamais
par identifiant global — même motif que `resoudre_le_rattachement` au LOT 6. Un code valide dans
une **autre** entité rend `ressource_introuvable` (422), jamais une référence qui échapperait
ensuite à la clé composite en 500.

## 3.4 La chronologie est validée en Python, pas laissée à la contrainte

`ck_event_chronologie_valide` (posée par `T1`) refuserait aussi un `finit_le` antérieur à
`commence_le`, mais en `IntegrityError`, donc en 500 — un 500 sur une faute de l'appelant
l'accuserait d'un défaut du service. `creer_un_evenement` la valide donc elle-même, au format
`422 chronologie_invalide` du §18.3, même motif que `type_de_page` dans `creer_une_page`.

## 3.5 Ce que `T3` ne fait pas encore

Un événement créé par `T3` n'a ni médias, ni rattachement multiple (plusieurs cercles ou bureaux à
la fois), et reste `draft` — publier est une ligne séparée du §11, réservée à `T4`. La demande de
création ne porte d'ailleurs aucun champ d'état, structurellement : `DemandeDeCreationDEvenement`
n'a ni `etat`, ni `publiee_le`, ni `cancelled`.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make migrate` | huit services sains, tête `0023` |
| `make migrations-check` | base vide → `0023` → schéma identique (685 colonnes, 252 contraintes, 211 index, 10 déclencheurs, 199 fonctions) ; retour à `base` propre |
| `make isolation-check` | **31 locales, 13 globales, 25 composites, 0 référence nue, 0 clé simple injustifiée** — `event_dsm_scope.dsm_person_id → person` reconnue comme clé simple légitime vers une table globale |
| `uv run pytest -q tests/test_creation_evenements.py` | **24/24** |
| `uv run pytest -q tests/test_evenements.py tests/test_lecture_evenements.py` | **31/31** |
| `uv run pytest -q tests/test_contrat.py` | **5/5** — le nouveau `codesExploitables` est documenté par le schéma réel |
| `make format-check`, `make lint`, `make typecheck` | verts |
| `make sources-check` | OK, aucun fichier source ignoré par git |
| collecte depuis la racine | **1 469 pytest**, dont **1 077 d'intégration** (+27, dont +22 d'intégration) |
| frontend | **706 Vitest** inchangés — aucun écran ne consomme encore la création |

## 4.0 Un vrai défaut trouvé par la CI, pas par moi — et ce que ma propre comparaison avait masqué

La première CI de la PR a échoué sur `test_isolation.py::test_les_cles_composites_sont_toutes_couvertes` :
ce test dérive du catalogue PostgreSQL la liste des clés étrangères composites réellement posées, et
la confronte à `COUVERTURE`, un dictionnaire **déclaré** qui rattache chaque chemin à son témoin de
refus. `event_dsm_scope → event` est une **septième** clé du domaine événementiel (après les six de
`T1`), et je ne l'avais pas ajoutée à `COUVERTURE` ni mis à jour le compte attendu (`24` → `25`).

**Ma propre preuve de zéro régression ne l'avait pas vu, et la raison est précise.** Le `git worktree`
posé sur `origin/develop` partage la base PostgreSQL de développement — déjà migrée à la tête `0023`
par mes soins avant la comparaison. Ce test lit le catalogue PostgreSQL **en direct**, pas les
métadonnées du code : sur la base déjà migrée, il échoue identiquement que le code qui tourne soit
celui de `develop` ou celui de la branche, puisque la clé composite existe physiquement dans les deux
cas. Il est donc apparu, à tort, dans les « 75 échecs environnementaux identiques des deux côtés » —
masqué par un vrai défaut qui ressemblait exactement à la signature attendue. C'est le piège déjà nommé
par `CLAUDE.md`, §9 : « le worktree partage la base, donc il subit DÉJÀ tes migrations » — ici il ne
l'a pas fait échouer à tort, il a fait passer à tort un vrai défaut pour un défaut connu.

Corrigé : l'entrée est ajoutée à `COUVERTURE`, pointant vers le témoin déjà écrit dans
`test_evenements.py` (`test_une_portee_dsm_ne_peut_pas_pointer_un_evenement_d_une_AUTRE_entite`), et
le compte attendu passe de 24 à 25. Vérifié isolément : `test_les_cles_composites_sont_toutes_couvertes`
passe seul.

## 4.1 Zéro régression, mesurée dans un `git worktree`

`make residu-check` rend **75 échecs** sur la base de développement, qui porte un jeu de démo
(entités et profils en nombre, comptés en absolu par des tests du LOT 2/3). Pour écarter toute
imputation à `T3`, un `git worktree` a été posé sur `origin/develop`, avec le même `.env` (le
worktree ne l'hérite pas, n'étant pas versionné) pour partager la même base :

```bash
uv run pytest -q -m integration apps/api/tests   # sur origin/develop ET sur la branche
```

Les deux listes de tests en échec sont **rigoureusement identiques**, 75 sur 75. Les échecs sont
environnementaux, nommés comme tels, et ne touchent aucun test du LOT 8.

---

# 5. Décisions et écarts

- `DEC-622` consigne l'arbitrage d'`ECART-067` et la réalisation de `T3` ;
- `ECART-067` est **clos** ;
- `ECART-068` reste ouvert — l'audit de la modification/publication doit être résolu avant la
  fermeture de `US004`, et n'est pas anticipé silencieusement ici ;
- aucun nouvel écart n'est ouvert par `T3`.

---

# 6. Ce que `T3` laisse

- la création d'un événement, dans sa portée exacte, pour les six rôles autorisés ;
- la cinquième table, prête pour la lecture et l'écriture des sous-étapes suivantes ;
- aucune modification, publication, annulation ni archivage — `T4` et `T5` ;
- aucun rattachement multiple à la création — `T4` ;
- aucun écran, aucun contrat TypeScript propre — le manifeste JSON suffit tant qu'aucun écran ne
  consomme la route (même parti que les routes de l'onboarding avant leur premier écran, LOT 7).

# Validation demandée à Jonathan

`T3` est faite, `ECART-067` est clos. Après fusion, la prochaine sous-étape est `T4` :
modification, publication et rattachements multiples.
