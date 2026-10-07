# Compte rendu — `T6` du LOT 8 : rattacher des médias à un événement

**Sous-étape :** la sixième du lot — `PUT /entities/{code}/events/{evenement}/medias`
**Date :** 4 octobre 2026
**Décision :** `DEC-625`
**Story :** `MVP-L08-US004`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, **`T6`** |
| Restent | `T7` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/events/perimetre.py` | `ActionEvenement.GERER_LES_MEDIAS` ; granté dans les mêmes blocs que `ANNULER`/`ARCHIVER` |
| `apps/api/app/events/ecriture.py` | `gerer_les_medias_d_un_evenement`, `_resoudre_les_medias`, et leurs requêtes |
| `apps/api/app/events/routes.py` | `PUT .../events/{evenement}/medias` |
| `apps/api/tests/test_medias_evenements.py` | **15 tests** — structure (2), service (13 marqués `integration`) |
| `apps/api/tests/test_modification_et_publication_evenements.py` | 3 assertions de `T5` élargies : `GERER_LES_MEDIAS` n'a pas de précondition d'état, contrairement à `ANNULER` |
| `packages/contracts/src/contrat-api.json` | entrée `gestionDesMediasDUnEvenement` |

Aucune migration : `T6` écrit dans `event_media`, posée par `T1` (migration `0022`).

## 2.1 Une sixième ligne du §11, et elle rejoint la grille « Périmètre » du DSM

« Ajouter une image ou vidéo » porte, pour le DSM, **exactement la même cellule que
« Publier »/« Annuler »/« Archiver »** — « Périmètre » (ses consultants nommés dans
`event_dsm_scope`), jamais « créé OU rattaché à son périmètre » (la grille de « Modifier »). Un DSM
créateur seul modifie un événement de portée Entité qu'il a créé, mais ne peut pas y rattacher de
média par cette seule voie — sixième mesure de l'asymétrie du §7.45 de la passation (LOT 6), après
`Publier`, `Annuler` et `Archiver`.

Pour `ESM`/`ADM-E`/`SUPER`/`BOOST`/`OFFICE`, aucune grille supplémentaire n'était nécessaire :
`GERER_LES_MEDIAS` rejoint simplement les blocs qui accordaient déjà `MODIFIER`/`PUBLIER`/
`ANNULER`/`ARCHIVER`.

Un événement **archivé** n'offre toujours que `RESTAURER` (la branche posée par `T5`) — aucune
modification nécessaire à cette branche, `GERER_LES_MEDIAS` n'y est simplement jamais ajouté.

## 2.2 La liste remplace la liste, et l'ordre est l'index du tableau — jamais un décalage calculé

Même motif que les cercles/bureaux de `T4` et les blocs de contenu du LOT 6 : chaque appel
**remplace la liste complète**. Les lignes `event_media` retirées sont **archivées**, jamais
supprimées, et les nouvelles sont insérées avec `display_order = index` dans le tableau soumis —
jamais un décalage calculé sur le nombre de lignes vivantes.

C'est précisément le piège déjà mesuré au LOT 6 (`T8-1`, défaut non déterministe sur la
réécriture d'ordre des liens internes) : archiver **toutes** les lignes avant de réinsérer rend
les rangs `0..n-1` **contigus par construction**, sans jamais les calculer. Un témoin le prouve
directement :
`test_l_ordre_est_l_INDEX_du_tableau_JAMAIS_un_decalage_calcule` attache trois médias, retire le
**premier**, et vérifie que les deux restants reçoivent les rangs `0` et `1` — pas `1` et `2`,
qu'un calcul naïf sur leur ancien rang aurait produits.

Une liste vide (`[]`) vide la galerie — seule forme de ce geste, puisque cette route n'a qu'une
seule dimension (contrairement à `cercles`/`bureaux` de `T4`, qui distinguent `None` de `[]`).

## 2.3 Seul un média `ready` est rattachable — réutilisation, pas invention

Le fiche du lot nomme deux contraintes explicites : « ordre stable » et « média de la même
entité ». Rien n'exige un état précis. Plutôt que d'inventer une règle, ce module **réutilise**
`ETAT_AFFICHABLE` (`app/media/photo.py`, LOT 5) — la définition **déjà décidée** de ce qu'est un
média « affichable », employée pour servir une miniature de profil. L'accueil (`T11`/`T12`)
consommera la même liste de médias d'événement ; un média encore `pending`/`processing`, ou
`rejected`/`archived`/`deleted`, n'a rien à y faire.

Un témoin pose le **couple** ready/non-ready plutôt que le seul cas heureux (§7.42 de la
passation) : `test_un_media_NON_PRET_est_refuse` attache d'abord un média `ready` (accepté), puis
tente d'attacher un média `pending` (refusé, `422 media_non_pret`).

## 2.4 Isolation et doublons, même discipline que les cercles et bureaux

Un média introuvable, hors de l'entité, ou dont le `archived_at` générique est posé, rend le
**même** `422 ressource_introuvable` qu'un cercle ou un bureau inconnu — même discipline de refus
par défaut (§2.5). Un doublon dans la même liste (le même `media_asset_id` soumis deux fois) est
refusé sous `422 doublon_dans_la_liste`, même garde que pour les cercles/bureaux de `T4`.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make migrations-check` | tête `0023` inchangée, schéma identique |
| `make isolation-check` | **31 locales, 25 composites** — inchangé, `T6` n'ajoute aucune table |
| `make sources-check` | OK |
| `uv run pytest -q tests/test_medias_evenements.py` | **15/15** |
| `uv run pytest -q tests/test_evenements.py tests/test_creation_evenements.py tests/test_modification_et_publication_evenements.py tests/test_annulation_archivage_et_restauration_evenements.py tests/test_contrat.py` | **99/99** (3 assertions de `T5` élargies) |
| `make format-check`, `make lint`, `make typecheck` | verts |
| collecte depuis la racine | **1 521 pytest**, dont **1 122 d'intégration** (+15, dont +13 d'intégration) |
| frontend | **706 Vitest** inchangés — aucun écran ne consomme encore la gestion des médias |
| **zéro régression** | `git worktree` sur `origin/develop` (après fusion de `T5`), même base : **74 échecs identiques des deux côtés** (jeu de démo, comptes en absolu) |

---

# 4. Décisions

- `DEC-625` consigne la réalisation de `T6` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact, ouvert.

---

# 5. Ce que `T6` laisse

- le rattachement, le remplacement et le retrait des médias d'un événement, dans la portée exacte
  de chaque rôle ;
- aucun téléversement ni traitement de variantes — LOT 11 ;
- aucune lecture publique des médias d'un événement : `T2` ne les rend pas encore, aucun
  consommateur avant les écrans (`T9` à `T12`) ;
- aucun écran, aucun contrat TypeScript propre — même parti que `T3`/`T4`/`T5`, tant qu'aucun
  écran ne consomme ces routes.

# Validation demandée à Jonathan

`T6` est faite. Après fusion, la prochaine sous-étape est `T7` : arrivées récentes.
