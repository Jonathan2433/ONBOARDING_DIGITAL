# Compte rendu — `T5` du LOT 10 : le câblage sur les événements

**Sous-étape :** la cinquième du lot — câblage sur les événements (LOT 8)
**Date :** 18 octobre 2026
**Décision :** `DEC-659`
**Stories :** `MVP-L10-US001`/`US002`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, **`T5`** |
| Restent | `T6` à `T16` |
| Issues | épic `#267`, stories `#268` à `#275`, jalon `G10` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/events/ecriture.py` | sept fonctions écrivent aussi `audit_event` — `creer_un_evenement` (littéral `creer`), `modifier_un_evenement` (un seul `audit_event` pour l'appel entier), `publier_un_evenement`/`annuler_un_evenement`/`archiver_un_evenement`/`restaurer_un_evenement` (`ActionEvenement`), `gerer_les_medias_d_un_evenement` (un seul `audit_event` pour tout le remplacement de la liste, y compris vide) |
| `apps/api/tests/test_audit_evenements.py` | **10 tests d'intégration**, le câblage lui-même |

Aucune migration, aucune route : `T5` câble sept fonctions déjà posées par le LOT 8 sur le service
générique de `T2`, exactement le périmètre que `fiche-lot-10.md` lui donne.

## 2.1 Le périmètre retenu, et pourquoi

Le découpage validé nomme : « créations, modifications, publications, cycle de vie ». Mesuré avant
d'écrire une ligne (grep exhaustif de `INSERT INTO event`/`UPDATE event*` sur tout `app/`, hors
tests) : toutes les écritures sur `event` et ses quatre tables associées (`event_circle_scope`,
`event_office_scope`, `event_dsm_scope`, `event_media`) vivent exclusivement dans
`apps/api/app/events/ecriture.py`, sept fonctions publiques :

| Fonction | Tables touchées | Sous-étape LOT 8 |
|---|---|---|
| `creer_un_evenement` | `event` + une des trois tables de portée selon le cas | `T3` |
| `modifier_un_evenement` | `event` + `event_circle_scope`/`event_office_scope` si fournis | `T4` |
| `publier_un_evenement` | `event` | `T4` |
| `annuler_un_evenement` | `event` | `T5` (LOT 8) |
| `archiver_un_evenement` | `event` | `T5` (LOT 8) |
| `restaurer_un_evenement` | `event` | `T5` (LOT 8) |
| `gerer_les_medias_d_un_evenement` | `event_media` + `event` (version seule) | `T6` (LOT 8) |

**Les sept fonctions ont chacune EXACTEMENT UN appelant HTTP**, vérifié explicitement pour chacune
avant de choisir où câbler — même configuration qu'à `T4` (LOT 6, contenus), pas celle de `T3`
(fonctions partagées à appelants multiples). Aucun report vers le niveau des appelants n'était donc
nécessaire : le câblage se pose directement dans chaque fonction, juste avant son `return`.

## 2.2 Le vocabulaire : réutilisé pour six actions sur sept, littéral pour la septième

Une énumération du périmètre existe déjà, `ActionEvenement` (`app.events.perimetre`, posée par le
LOT 8 `T4`/`T5`), et couvre SIX des sept gestes : `MODIFIER`, `PUBLIER`, `ANNULER`, `ARCHIVER`,
`RESTAURER`, `GERER_LES_MEDIAS`. Elle est réutilisée telle quelle pour l'`action_code`, comme
`ActionEditoriale` l'a été à `T4` et `ChampOrganisationnel`/`ActionDeCycleDeVie` à `T3`.

**Il manque `CREER`, et ce n'est pas un oubli à corriger.** La docstring de `ActionEvenement` dit
explicitement qu'elle couvre « les six lignes du §11 » — les lignes de PERMISSION de la matrice.
« Créer » n'y a pas de ligne propre : qui peut créer, et dans quelle portée, se règle par
`PorteeDeCreation`, une structure entièrement distincte. Ajouter un membre `CREER` à
`ActionEvenement` aurait donc inventé une valeur qu'AUCUNE ligne du §11 ne nomme — à la différence
d'`ActionEditoriale.CREER` au LOT 6, qui correspond à une vraie ligne du §13 (« une seule ligne au
§13 », dit la docstring de cette enum-là). La création reçoit donc un littéral, `"creer"`, même
discipline que les trois littéraux posés par `T4` pour les liens internes — une enum partielle
n'est pas une raison d'inventer la case manquante, c'est une raison d'écrire un littéral pour ce
qu'elle ne couvre pas.

**`modifier_un_evenement` émet un seul `audit_event` pour un appel qui écrit plusieurs lignes SQL**,
et c'est délibéré : elle remplace les champs ET, si fournies, les listes de cercles/bureaux
rattachés — plusieurs écritures, un seul geste métier, un seul événement, même principe que
`remplacer_le_contenu` à `T4`. Aucune valeur ancienne n'est portée dans `old_values` : cette
fonction ne lit jamais l'état antérieur des champs avant de les écraser (contrairement à
`remplacer_le_contenu`, qui avait déjà l'ancien titre sous la main pour une autre raison) — ajouter
une lecture supplémentaire uniquement pour l'audit aurait dépassé le périmètre de cette sous-étape.

**`gerer_les_medias_d_un_evenement` émet aussi un seul `audit_event` pour tout le remplacement de
la liste** — même principe que `reordonner_les_liens` à `T4`. **Mais le contraste avec
`reordonner_les_liens` est précisément ce qu'il faut retenir** : `reordonner_les_liens` a un retour
anticipé sur une liste vide (rien à réordonner, zéro écriture, audit compris) ; `gerer_les_medias_
d_un_evenement` n'en a AUCUN — une liste vide VIDE la galerie, c'est une forme normale de ce geste,
pas un cas particulier. Un `audit_event` est donc écrit MÊME quand `medias=[]`, témoin dédié.

**`annuler_un_evenement` porte un vrai motif humain**, `motif` (optionnel), que le §18.1 ne rend
pas obligatoire pour cette action mais que le modèle porte déjà (`cancellation_reason`). Il est
transmis via `reason=motif` au service générique, jamais glissé dans `summary` — même discipline
que `raison` pour la révocation de session (LOT 3) ou `motif` pour la catégorie DG (LOT 2 `T3`).
`archiver_un_evenement` ne porte aucun motif, conformément au §18.1 qui n'en fait pas un cas
obligatoire pour l'archivage d'un événement.

## 2.3 Aucun défaut trouvé en câblant — mesuré, comme à `T4`

**Comme à `T4`, aucun défaut n'a été trouvé en câblant ces sept fonctions**, et ce n'est pas
présumé : une recherche exhaustive, menée AVANT tout code, a cherché les mêmes classes de défaut
déjà documentées à `T2`/`T3`/`T4` :

- **grep sur tous les `infra/scripts/verifier-*.py`** pour toute suppression des cinq tables
  événementielles : un seul script en porte, `verifier-accueil-evenements.py` (LOT 8 `T13`), et son
  décor nettoie DÉJÀ `audit_event` par `actor_person_id` ET par `entity_id`, dans le bon ordre
  (avant `person`/`entity`) — déjà correct avant même ce câblage, aucun correctif requis ;
- **grep sur tous les fichiers de test exerçant une route HTTP réelle** de ce domaine (via
  `TestClient`, avec un nettoyage manuel plutôt que la fixture `cx` en rollback) : deux fichiers
  correspondent (`test_lecture_evenements.py`, `test_gestion_evenements.py`), mais aucun des deux
  n'exerce de route d'ÉCRITURE — leurs décors `TestClient` ne font que des `GET`, les événements de
  test étant posés par INSERT SQL direct. Aucun `audit_event` n'y naît donc, pas de risque actif ;
- un point de vigilance est noté pour l'avenir : le jour où un test HTTP réel de ce domaine
  exercera une route d'écriture via ces mêmes fixtures, leur nettoyage devra ajouter les deux lignes
  `audit_event` manquantes, exactement comme `verifier-accueil-evenements.py` le fait déjà.

**Cette mesure a été vérifiée empiriquement, pas seulement déduite par grep** : `make
accueil-check` (le contrôle de pile réelle du LOT 8, 29 contrôles) a été rejoué sur la pile réelle
(après `make code-refresh`) une fois le câblage en place, et ses 29 contrôles — dont plusieurs
routes d'écriture de ce module exercées en vrai (création, modification, publication, annulation,
archivage, restauration) — sont passés sans aucun échec, y compris sa ligne finale de ménage.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_audit_evenements.py` | **10/10** |
| suite complète du domaine événementiel (sept fichiers existants) + `test_audit_evenements.py` + `test_accueil.py` | **140/140** |
| `make accueil-check` (pile réelle, 29 contrôles) | **29/29**, 0 échec, décor nettoyé |
| collecte depuis la racine | **1 759 pytest** (+10), dont **1 326 d'intégration** (+10) |
| `uv run mypy` racine | vert, **247 fichiers** (+1) |
| `uv run ruff check`/`format` racine | verts |
| `make sources-check` | vert, 667 fichiers examinés |
| `make residu-check` | mêmes 73 échecs environnementaux, **aucun résidu** signalé |
| comparaison de worktree `origin/develop` (§7.22 de la passation) | **73 échecs identiques, un par un**, `diff` vide entre les deux listes triées |

---

# 4. Décisions et écarts

- `DEC-659` consigne la réalisation et les choix dérivés du modèle ;
- aucun écart n'est ouvert ni fermé par `T5` ; `ECART-064` (motif du super-administrateur) reste à
  fermer à `T7`, sans rapport avec le domaine de `T5`.

---

# 5. Ce que `T5` laisse

- sept fonctions métier du LOT 8 câblées sur le service générique de `T2` ;
- aucun résidu d'infra ou de test à corriger, confirmé par `make accueil-check` sur la pile réelle ;
- un point de vigilance nommé (pas un défaut) : les deux fixtures `TestClient` en lecture seule du
  domaine événementiel devront étendre leur nettoyage le jour où elles exerceront une écriture ;
- `ECART-064` reste ouvert, à fermer à `T7` ;
- la divergence des annotations `lot=` du §30.19-24 dans `verifier-recette-modele.py` intacte, à
  vérifier à `T16`.

# Validation demandée à Jonathan

`T5` est faite. Après fusion, la prochaine sous-étape est `T6` : le câblage sur l'onboarding
(LOT 7).
