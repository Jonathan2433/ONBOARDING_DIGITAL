# Compte rendu — `T4` du LOT 8 : modifier, publier et rattacher plusieurs cercles/bureaux

**Sous-étape :** la quatrième du lot — `PUT /entities/{code}/events/{evenement}`,
`POST /entities/{code}/events/{evenement}/publication`
**Date :** 4 octobre 2026
**Décision :** `DEC-623`
**Story :** `MVP-L08-US004` (2 sur 3)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1`, `T2`, `T3`, **`T4`** |
| Restent | `T5` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/events/perimetre.py` | `ActionEvenement`, `PerimetreEvenement`, `resoudre_le_perimetre_de_l_evenement` |
| `apps/api/app/events/ecriture.py` | `modifier_un_evenement`, `publier_un_evenement`, et leurs requêtes |
| `apps/api/app/events/routes.py` | `PUT .../events/{evenement}`, `POST .../events/{evenement}/publication` |
| `apps/api/tests/test_modification_et_publication_evenements.py` | **20 tests** — structure (3), service (17 marqués `integration`) |
| `packages/contracts/src/contrat-api.json` | entrées `modificationDUnEvenement`, `publicationDUnEvenement` |

Aucune migration : `T4` ne pose aucune table ni colonne, elle écrit dans les cinq tables
posées par `T1` et `T3`.

## 2.1 Deux lignes voisines du §11, et une seule cellule diffère — la leçon qui comptait

La matrice §11 donne EXACTEMENT la même portée à « Modifier » et à « Publier » pour
`ESM`/`ADM-E`/`SUPER`/`BOOST`/`OFFICE`. Seul le DSM diverge :

```
Modifier   « Événements créés OU rattachés à son périmètre »
Publier    « Périmètre »
```

**Et « Périmètre » ne dénote pas le même ensemble pour tous les rôles** — leçon déjà payée
au LOT 6 (§7.45 de la passation) pour l'ESM, où « Périmètre » et « Entité » coïncident parce
que le §3 définit le périmètre principal de l'ESM comme « ensemble de son entité ». **Pour le
DSM, le §3 donne « ses consultants dans son entité »** — un ensemble de personnes, exactement
ce que `EventDsmScope` porte. Les deux mots ne coïncident donc PAS pour ce rôle : un DSM peut
**modifier** un événement de portée Entité qu'il a créé (il l'a créé, première moitié de la
grille), mais ne peut **jamais le publier** par cette seule voie — seul un événement où il est
le DSM *nommé* (`event_dsm_scope.dsm_person_id = acteur`) ouvre « Publier ». Deux tests le
prouvent côte à côte : `test_un_DSM_MODIFIE_un_evenement_ENTITE_qu_il_a_CREE_mais_ne_le_PUBLIE_PAS`
et son témoin `test_un_DSM_MODIFIE_ET_PUBLIE_un_evenement_de_portee_CONSULTANTS`.

## 2.2 Les rattachements multiples, et pourquoi chaque code est revalidé à part

Le modèle §17.2 autorise « un ou plusieurs cercles », « un ou plusieurs bureaux ». `T3`
ne posait qu'un seul scope à la création ; `T4` permet d'en attacher plusieurs via
`cercles`/`bureaux`, qui **remplacent la liste complète** de leur dimension — même motif
« la liste remplace la liste » que `remplacer_le_contenu` au LOT 6, les lignes retirées
étant **archivées**, jamais supprimées.

**Le droit de modifier l'événement et le droit d'y attacher TEL cercle précis sont deux
questions indépendantes (§23.1).** Un Booster autorisé à modifier un événement — parce qu'il
est scopé à SON cercle — ne peut pas pour autant y attacher le cercle d'un AUTRE Booster :
chaque code soumis dans `cercles`/`bureaux` est donc revérifié individuellement
(`_resoudre_les_cercles`/`_resoudre_les_bureaux`), indépendamment du périmètre global déjà
validé par la route. Un rôle de portée ENTITE (`ESM`/`ADM-E`/`SUPER`) n'a besoin d'aucune
vérification supplémentaire : son périmètre couvre déjà l'entité entière. Deux témoins
d'asymétrie le prouvent, un pour les cercles et un pour les bureaux.

## 2.3 La concurrence optimiste et l'absence de republication

Même discipline que `publier_une_page` au LOT 6 : `Publier` n'est offert qu'à un `draft`
(matrice §11, §11.1 — « un événement passe automatiquement… » ne concerne que la lecture,
jamais une republication manuelle), et le verrou optimiste du §18.4 est revérifié au moment
de l'écriture — pas seulement résolu par le périmètre, lu à un instant distinct.

## 2.4 Un vrai défaut trouvé par mes propres tests, avant tout commit

En écrivant `test_un_ESM_rattache_PLUSIEURS_cercles_ET_bureaux_a_un_evenement_ENTITE`, les
deux requêtes `_ARCHIVER_LES_PORTEES_CERCLE`/`_ARCHIVER_LES_PORTEES_BUREAU` ont échoué :
`instant` était paramétré dans le SQL mais jamais passé dans l'appel `connexion.execute`.
Corrigé avant tout commit — aucune régression n'est entrée dans l'historique.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make migrations-check` | tête `0023` inchangée, schéma identique |
| `make isolation-check` | **31 locales, 25 composites** — inchangé, `T4` n'ajoute aucune table |
| `uv run pytest -q tests/test_modification_et_publication_evenements.py` | **20/20** |
| `uv run pytest -q tests/test_contrat.py` | **5/5** |
| `make format-check`, `make lint`, `make typecheck` | verts |
| `make sources-check` | OK |
| collecte depuis la racine | **1 489 pytest**, dont **1 094 d'intégration** (+20, dont +17 d'intégration) |
| frontend | **706 Vitest** inchangés — aucun écran ne consomme encore la modification/publication |
| **zéro régression** | `git worktree` sur `origin/develop` (après fusion de `T3`), même base : **74 échecs identiques des deux côtés** (jeu de démo, comptes en absolu) |

---

# 4. Décisions

- `DEC-623` consigne la réalisation de `T4` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact, ouvert.

---

# 5. Ce que `T4` laisse

- la modification et la publication, dans la portée exacte de chaque rôle ;
- les rattachements multiples (plusieurs cercles et/ou bureaux à la fois) ;
- aucune annulation, aucun archivage, aucune restauration — `T5` ;
- aucun rattachement de média — `T6` ;
- aucun écran, aucun contrat TypeScript propre — même parti que `T3`, tant qu'aucun écran ne
  consomme ces routes.

# Validation demandée à Jonathan

`T4` est faite. Après fusion, la prochaine sous-étape est `T5` : annulation, archivage et
restauration d'un événement.
