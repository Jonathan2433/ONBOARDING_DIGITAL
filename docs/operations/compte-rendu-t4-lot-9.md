# Compte rendu — `T4` du LOT 9 : restaurer un cercle ou un bureau archivé

**Sous-étape :** la quatrième du lot — `MVP-L09-US008`
**Date :** 9 octobre 2026
**Décision :** `DEC-639`
**Stories :** `US008`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, **`T4`** |
| Restent | `T5` à `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Ce que la fiche nommait, et ce que `T4` a trouvé avant d'écrire une ligne

La fiche (`fiche-lot-9.md` §`T4`) dit : « Restauration des ressources archivées
autorisées par back-office (`US008`), qui dépend de `T2`/`T3` et distingue les
restaurations simples (déjà couvertes par la matrice) des restaurations
techniques/massives (rôles réservés). » Le backlog nomme le même critère :
« Les restaurations simples suivent la matrice ; les restaurations techniques
ou massives restent réservées aux rôles prévus. »

**Mesure avant d'écrire une ligne, et elle a changé le périmètre réel de
`T4` :**

- **la restauration d'un COLLABORATEUR est déjà entièrement servie**, depuis
  le `T8` du LOT 5 (`app.people.archivage.restaurer_un_profil`,
  `POST .../people/{appartenance}/restauration`) — son propre docstring dit
  déjà, en toutes lettres, que « Conditionnel » pour l'ESM n'est pas une
  décision en suspens : `ARB-DROIT-003` la définit, et « un profil à l'unité
  est fonctionnelle ». Rien à faire de ce côté ;
- **`ARB-DROIT-003` nomme CINQ ressources** — « un profil, un contenu, un
  événement, un cercle ou un bureau » — et seules les deux dernières n'avaient
  **aucun** mécanisme d'archivage ni de restauration, nulle part dans le
  dépôt. `circle` et `office` portent `archived_at`/`archived_by_person_id`
  depuis le LOT 2 (`T7`), les deux index partiels du §25.1 les EXCLUENT déjà
  de toute lecture — mais rien ne l'ÉCRIT ni ne l'EFFACE. Mesuré :
  zéro occurrence de `archiver_un_cercle`, `restaurer_un_cercle`,
  `archiver_un_bureau` ou `restaurer_un_bureau` dans tout le dépôt ;
- **ce trou était déjà annoncé**, sans qu'aucune sous-étape ne le comble
  depuis : `T3` du LOT 6 écrivait, en lisant la matrice §10.2, « une lecture
  d'archivé viendra — et elle aura sa propre route, comme `fiche-archivee`
  au LOT 5 ». Treize sous-étapes et trois lots plus tard, personne ne
  l'avait construite.

Ce changement de périmètre — de « rien à coder » à « construire l'archivage
ET la restauration des cercles/bureaux » — a été posé en question à Jonathan
avant tout code, plutôt que décidé par défaut (§6.5). Réponse du 09/10/2026 :
**construire les deux**, dans `T4`.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/organization/perimetre.py` | **nouveau** — `ROLES_DE_CYCLE_DE_VIE_FRAMEWORK` (ESM, ADM-E, SUPER), une seule grille pour les deux ressources et les deux actions |
| `apps/api/app/organization/cycle_de_vie.py` | **nouveau** — `archiver_un_cercle`, `restaurer_un_cercle`, `archiver_un_bureau`, `restaurer_un_bureau` |
| `apps/api/app/organization/routes.py` | quatre routes `POST .../circles/{circle_id}/{archivage,restauration}` et `.../offices/{office_id}/{archivage,restauration}` |
| `packages/contracts/src/contrat-api.json` | quatre entrées : `archivageDUnCercle`, `restaurationDUnCercle`, `archivageDUnBureau`, `restaurationDUnBureau` |
| `apps/api/tests/test_cycle_de_vie_organisation.py` | **7 tests d'intégration** |

Aucune migration : `circle` et `office` portent déjà `archived_at`,
`archived_by_person_id` et `version` depuis le LOT 2 (`ChampsCommuns`,
`T7`) ; `T4` leur donne enfin un écrivain.

## 3.1 Pourquoi un cercle refuse l'archivage « si aucun membre actif », et un bureau non

Le §10.2 porte une condition que le §10.3 ne porte **pas** : « Archiver un
cercle | Entité, **si aucun membre actif** ». Mesuré avant d'écrire : cette
condition **ne dépend d'aucun rôle** — elle vaut pour `ESM`, `ADM-E` et
`SUPER` sans distinction, une interdiction liée à la ressource prévalant sur
le cumul des rôles (§23.2), exactement comme le 409 qui refuse d'archiver un
profil déjà archivé (`T8` du LOT 5). Elle est donc vérifiée par le
**service**, dans la même transaction que le verrou optimiste, jamais en
PostgreSQL : aucune des contraintes du §25 ne la porte, et un déclencheur pour
une seule règle non partagée aurait été un outil de plus pour un seul
appelant. Le §10.3 ne porte **aucune** condition équivalente pour un bureau
— elle n'a donc **pas** été inventée là (§6.5).

## 3.2 Ce que la restauration peut refuser, et pourquoi c'est attendu

Les deux index partiels du §25.1 — `uq_circle_entity_id_code_non_archive`,
`uq_office_entity_id_code_non_archive` — libèrent le **code** à l'archivage,
exactement comme le slug d'une page (`T7` du LOT 6). Si un cercle ou un
bureau neuf a repris ce code entre-temps, la restauration le reprendrait en
double : la base refuse, et le 409 nomme la cause (`code_deja_pris`) plutôt
que de laisser `IntegrityError` remonter brute.

## 3.3 Ce que `T4` n'a pas construit, et pourquoi

- **Aucune création ni modification de structure** d'un cercle ou d'un
  bureau (§10.2/§10.3 « Créer un cercle », « Modifier la structure ») :
  aucune sous-étape du découpage du LOT 9 ne les demande, et les construire
  ici aurait débordé le périmètre d'une sous-étape (§2, règle n°1) ;
- **Aucune route « consulter un cercle/bureau archivé »**, contrairement au
  profil (§6.1, qui porte explicitement cette troisième ligne). Ni le §10.2,
  ni le §10.3, ni le §18 ne nomment cette lecture pour un cercle ou un
  bureau — l'inventer aurait été le §6.5. Les quatre routes de `T4` prennent
  donc l'identifiant du cercle/bureau **directement** (son `id`, pas son
  `code`, même raison que le transfert d'un collaborateur prend une
  `appartenance` et non un nom) ; la façon de le **découvrir** reste une
  question pour la sous-étape qui construira l'écran (`T14`).

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_cycle_de_vie_organisation.py` | **7/7** |
| `uv run pytest -q apps/api/tests/test_contrat.py` | **5/5** |
| `uv run mypy` (racine) | verts, **208 fichiers** (+2 sur `T3`) |
| `make lint`, `make format-check` | verts |
| `make isolation-check` | **inchangé** — 35 tables locales, 29 clés composites, 0 référence nue ; aucune table nouvelle |
| `make docs-check`, `make sources-check` | verts |
| `make audit` | zéro avis |
| collecte depuis la racine | **1 603 pytest** (+7), dont **1 191 d'intégration** (+7, toutes marquées `@pytest.mark.integration`) ; **74 échecs environnementaux**, liste de fichiers identique à celle d'avant `T4` (comparée fichier par fichier) |
| frontend | **794 Vitest** inchangés — aucun fichier frontend touché |

---

# 5. Décisions et écarts

- `DEC-639` consigne la réalisation et l'arbitrage de Jonathan (construire
  l'archivage et la restauration des cercles/bureaux dans `T4`, plutôt que de
  les reporter) ;
- aucun nouvel écart ni aucune nouvelle question n'est ouvert par `T4` ;
- `ARB-DROIT-003` est désormais tenu pour ses **cinq** ressources — profil,
  contenu, événement, cercle, bureau — toutes archivables et restaurables.

---

# 6. Ce que `T4` laisse

- un cercle sans membre actif, ou un bureau, s'archive et se restaure en une
  transaction, par `ESM`/`ADM-E`/`SUPER` dans leur portée ;
- **aucune route ne liste les cercles/bureaux archivés** : la découverte de
  leur identifiant reste à construire, vraisemblablement par `T14` (écrans) ;
- **aucune création ni modification de structure** d'un cercle ou d'un
  bureau n'existe : si une sous-étape future en a besoin, elle part d'un
  module neuf, pas d'une extension de celui-ci.

# Validation demandée à Jonathan

`T4` est faite. Après fusion, la prochaine sous-étape est `T5` : tableau de
bord administratif — agrégat en lecture (`US001`), sur le patron de `T8` du
LOT 8.
