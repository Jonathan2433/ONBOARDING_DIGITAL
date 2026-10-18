# Compte rendu — `T4` du LOT 10 : le câblage sur les contenus et le Framework

**Sous-étape :** la quatrième du lot — câblage sur les contenus et le Framework (LOT 6)
**Date :** 18 octobre 2026
**Décision :** `DEC-658`
**Stories :** `MVP-L10-US001`/`US002`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, **`T4`** |
| Restent | `T5` à `T16` |
| Issues | épic `#267`, stories `#268` à `#275`, jalon `G10` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/content/ecriture.py` | `creer_une_page` écrit aussi `audit_event` (`ActionEditoriale.CREER`, `resource_type="content_page"`) ; `remplacer_le_contenu` écrit UN SEUL `audit_event` pour l'appel entier (`ActionEditoriale.MODIFIER`) |
| `apps/api/app/content/cycle_de_vie.py` | `publier_une_page`/`archiver_une_page`/`restaurer_une_page` écrivent aussi `audit_event` (`action_code` = `ActionEditoriale.value`) |
| `apps/api/app/content/liens.py` | `creer_un_lien`/`modifier_un_lien`/`reordonner_les_liens` écrivent aussi `audit_event` (littéraux `"lien_cree"`/`"lien_modifie"`/`"liens_reordonnes"`) |
| `apps/api/tests/test_audit_contenus.py` | **11 tests d'intégration**, le câblage lui-même |

Aucune migration, aucune route : `T4` câble huit fonctions déjà posées par le LOT 6 sur le service
générique de `T2`, exactement le périmètre que `fiche-lot-10.md` lui donne.

## 2.1 Le périmètre retenu, et pourquoi

Le découpage validé nomme : « créations, modifications, publications, cycle de vie des pages et
blocs ». Mesuré avant d'écrire une ligne (recherche exhaustive, menée par un agent dédié, des sites
d'écriture métier sur les trois tables du modèle §15 — `content_page`, `content_block`,
`internal_link`) : huit fonctions couvrent exactement cet énoncé, et aucune autre n'écrit sur ces
tables en dehors d'elles :

| Fonction | Module | Ce qu'elle écrit |
|---|---|---|
| `creer_une_page` | `content/ecriture.py` | une page, toujours en brouillon (LOT 6 `T6`) |
| `remplacer_le_contenu` | `content/ecriture.py` | le titre et les blocs d'une page — archivage des anciens, insertion des nouveaux (LOT 6 `T6`) |
| `publier_une_page` | `content/cycle_de_vie.py` | `state`/`published_at` d'une page (LOT 6 `T7`) |
| `archiver_une_page` | `content/cycle_de_vie.py` | `state`/`archived_at` d'une page (LOT 6 `T7`) |
| `restaurer_une_page` | `content/cycle_de_vie.py` | `state` d'une page archivée, retour à `draft` (LOT 6 `T7`) |
| `creer_un_lien` | `content/liens.py` | un lien interne, ajouté en queue de liste (LOT 6 `T8`) |
| `modifier_un_lien` | `content/liens.py` | la définition d'un lien, y compris sa désactivation (LOT 6 `T8`) |
| `reordonner_les_liens` | `content/liens.py` | l'ordre d'affichage de tous les liens vivants de l'entité (LOT 6 `T8`) |

**Aucune de ces huit fonctions n'a l'ambiguïté multi-appelants de `creer_l_appartenance` (LOT 2,
reportée au niveau de ses appelants par `T3`).** Chacune n'a qu'UN SEUL appelant HTTP, à la
sémantique non ambiguë — vérifié explicitement pour chacune avant de choisir où câbler. Aucun
report vers un niveau supérieur n'était donc nécessaire : le câblage se pose directement dans
chaque fonction.

`app.content.perimetre` (permissions seules), `app.content.pages` (lecture seule) et
`app.organization.framework` (la synthèse Framework, lecture seule) ont été lus en entier et
confirmés sans écriture — la « synthèse Framework » du titre de `T4` renvoie, en pratique, aux
pages de cercle et de bureau qu'elle décrit (du contenu `content_page`, déjà couvert ci-dessus),
pas à une écriture organisationnelle distincte des LOTS 2/4/5/9 déjà câblée par `T3`.

## 2.2 Le vocabulaire : réutilisé quand il existe, littéral sinon (§7.27)

Une énumération du périmètre existe déjà et est réutilisée telle quelle, comme `TypeEvenementAuth`
l'a été à `T2` et `ChampOrganisationnel`/`ActionDeCycleDeVie` à `T3` :

- **`ActionEditoriale`** (`app.content.perimetre`, posée au LOT 6 `T7`) — quatre de ses cinq
  valeurs collent un à un aux fonctions d'écriture des pages : `CREER` → `creer_une_page`,
  `MODIFIER` → `remplacer_le_contenu`, `PUBLIER` → `publier_une_page`, `ARCHIVER` →
  `archiver_une_page`, `RESTAURER` → `restaurer_une_page`.

Pour les liens internes, qu'aucune enum ne nomme, trois littéraux sont posés, un par action
distincte : `lien_cree`, `lien_modifie`, `liens_reordonnes` — même discipline que les six littéraux
de `T3` pour les actions sans vocabulaire existant.

**Deux fonctions émettent un seul `audit_event` pour un appel qui écrit plusieurs lignes SQL**, et
c'est délibéré dans les deux cas :

- `remplacer_le_contenu` archive les anciens blocs, en insère de nouveaux et met à jour le titre de
  la page — trois écritures SQL, un seul geste métier, un seul événement. **À la différence de
  `modifier_les_donnees_organisationnelles` au LOT 2** (un `audit_event` par champ, parce que cette
  fonction calcule un DIFF entre l'ancien et le nouveau), `remplacer_le_contenu` n'est pas une
  fonction de diff : elle archive et recrée systématiquement les blocs à CHAQUE appel, qu'un bloc
  ait changé ou non. Il n'y a donc rien à distinguer par champ, et un seul événement est le niveau
  de granularité exact ;
- `reordonner_les_liens` réécrit le rang de tous les liens vivants de l'entité en un seul geste
  métier — un événement par lien déplacé aurait rendu inexploitable la lecture d'un reclassement
  global. **Quand la liste soumise est vide, la fonction retourne avant toute écriture** (y compris
  avant l'audit) : aucun `audit_event` n'est écrit, témoin exécuté.

## 2.3 Aucun défaut trouvé en câblant — mesuré, pas seulement constaté

**Contrairement à `T2` et `T3`, aucun défaut n'a été trouvé en câblant ces huit fonctions.** Cela
n'a pas été présumé : une recherche exhaustive, menée AVANT tout code, a cherché les mêmes deux
classes de défaut déjà documentées à `T2` (nettoyage de décor incomplet sur `actor_person_id`) et
à `T3` (nettoyage de décor incomplet sur `entity_id`) :

- **grep sur tous les `infra/scripts/verifier-*.py`** pour toute suppression de `content_page`,
  `content_block` ou `internal_link` : un seul script en porte, `verifier-accueil-evenements.py`,
  et son décor insère ces lignes DIRECTEMENT en SQL, jamais via les fonctions câblées par `T4` —
  aucune ligne `audit_event` n'y naît donc de ce chemin ;
- **grep sur tous les fichiers de test exerçant une route HTTP réelle** de ce domaine (par
  `TestClient`, avec un nettoyage manuel plutôt que la fixture `cx` en rollback, le motif exact qui
  avait trouvé le troisième défaut de `T3`) : aucun ne correspond — les cinq fichiers de test du
  domaine éditorial (`test_contenus.py`, `test_cycle_de_vie_des_contenus.py`,
  `test_ecriture_des_contenus.py`, `test_liens_internes.py`, `test_rendu_des_blocs.py`) utilisent
  tous la fixture `cx` standard en rollback, qui annule aussi tout `audit_event` écrit par les
  fonctions câblées ;
- **`grep` sur tous les scripts qui exercent une route HTTP d'écriture de ce domaine** : un seul,
  `verifier-framework.py` (le contrôle de pile réelle du LOT 6, 77 contrôles), et il nettoie déjà
  `audit_event` par `actor_person_id` depuis le correctif de `T2` — chacune des huit fonctions de
  `T4` renseigne toujours `actor_person_id` (aucune n'a de chemin anonyme ou de compte de service),
  ce nettoyage existant suffit donc sans ligne `entity_id` supplémentaire.

**Cette mesure a été vérifiée empiriquement, pas seulement déduite par grep** : `make
framework-check` a été rejoué sur la pile réelle (après `make code-refresh`) une fois le câblage en
place, et ses 77 contrôles — dont sept routes d'écriture du domaine éditorial exercées en vrai —
sont passés sans aucun échec de nettoyage, y compris sa ligne finale de ménage.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_audit_contenus.py` | **11/11** |
| suite complète du domaine éditorial (`test_contenus.py`, `test_cycle_de_vie_des_contenus.py`, `test_ecriture_des_contenus.py`, `test_liens_internes.py`, `test_rendu_des_blocs.py`, `test_accueil.py`) | **207/207** |
| `make framework-check` (pile réelle, 77 contrôles) | **77/77**, 0 échec, décor nettoyé |
| collecte depuis la racine | **1 749 pytest** (+11), dont **1 316 d'intégration** (+11) |
| `uv run mypy` racine | vert, **246 fichiers** (+1) |
| `uv run ruff check`/`format` racine | verts |
| `make sources-check` | vert, 665 fichiers examinés |
| `make residu-check` | mêmes 73 échecs environnementaux, **aucun résidu** signalé |
| comparaison de worktree `origin/develop` (§7.22 de la passation) | **73 échecs identiques, un par un**, `diff` vide entre les deux listes triées |

---

# 4. Décisions et écarts

- `DEC-658` consigne la réalisation et les choix dérivés du modèle ;
- aucun écart n'est ouvert ni fermé par `T4` ; `ECART-064` (motif du super-administrateur) reste à
  fermer à `T7`, sans rapport avec le domaine de `T4`.

---

# 5. Ce que `T4` laisse

- huit fonctions métier du LOT 6 câblées sur le service générique de `T2` ;
- aucun résidu d'infra ou de test à corriger, confirmé par `make framework-check` sur la pile
  réelle ;
- `ECART-064` reste ouvert, à fermer à `T7` ;
- la divergence des annotations `lot=` du §30.19-24 dans `verifier-recette-modele.py` intacte, à
  vérifier à `T16`.

# Validation demandée à Jonathan

`T4` est faite. Après fusion, la prochaine sous-étape est `T5` : le câblage sur les événements
(LOT 8).
