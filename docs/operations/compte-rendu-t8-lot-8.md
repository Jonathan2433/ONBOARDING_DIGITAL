# Compte rendu — `T8` du LOT 8 : l'agrégat API de l'accueil

**Sous-étape :** la huitième du lot — `GET /entities/{code}/accueil`
**Date :** 5 octobre 2026
**Décision :** `DEC-627`
**Story :** `MVP-L08-US001` (1/2), `MVP-L08-US006` (1/2)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, **`T8`** |
| Restent | `T9` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/accueil/__init__.py` | docstring du module, aucune table propre |
| `apps/api/app/accueil/lecture.py` | `lire_l_accueil`, `AccueilDEntite` — compose les cinq services sources |
| `apps/api/app/accueil/routes.py` | `GET /entities/{code}/accueil`, `ReponseDeLAccueil` et les assemblages Pydantic |
| `apps/api/app/main.py` | montage de `routeur_accueil`, en dernier |
| `apps/api/tests/test_accueil.py` | **6 tests**, tous marqués `integration` |
| `packages/contracts/src/contrat-api.json` | entrée `accueilDUneEntite` |

Aucune migration : `T8` ne lit que des tables déjà posées par les LOTS 6 et 7 et par `T1`/`T2`
du LOT 8.

## 2.1 Cinq sections composées, et aucune règle recopiée

Le cahier §8.4 donne l'ordre : présentation, Framework, arrivées récentes, événements à venir,
liens internes. Ce module **n'écrit aucune règle propre** — il appelle directement les cinq
services déjà construits par leurs sous-étapes sources :

| Section | Service réutilisé | Sous-étape source |
|---|---|---|
| Présentation | `app.content.pages.lire_la_page_de_contenu` | LOT 6, `T6` |
| Framework | `app.organization.framework.lire_la_page_framework` | LOT 6, `T2` |
| Arrivées récentes | `app.onboarding.arrivees_recentes.lister_les_arrivees_recentes` | LOT 8, `T7` |
| Événements à venir | `app.events.lecture.lister_les_evenements` | LOT 8, `T2` |
| Liens internes | `app.content.liens.lister_les_liens` | LOT 6, `T8` |

Les recopier aurait été la classe `ECART-021`/§7.27 : une seconde source qui diverge au premier
changement de l'une des cinq sous-étapes. La matrice §5 donne « Lecture » aux huit rôles
authentifiés sur chacune des six ressources composées (l'accueil lui-même compris), sans aucune
divergence entre elles — mesuré ligne par ligne. La garde de la route est donc une simple session
établie ; il n'y a rien à réconcilier entre les permissions des cinq sections.

## 2.2 La présentation peut être absente, et ce n'est pas une erreur

`lire_la_page_de_contenu` rend `None` si aucune page `HOME`/`presentation` n'existe encore pour
l'entité — une entité neuve n'a pas encore de texte de présentation, et le LOT 6 a déjà établi
qu'une page sans contenu (ou absente) est un état valide. `AccueilDEntite.presentation` est donc
la seule section nullable ; les quatre autres rendent au pire une liste vide.

Le couple `(type_de_page="HOME", slug="presentation")` qui retrouve cette page n'est **pas une
invention** de cette sous-étape : c'est la convention déjà posée par l'écran `PageEntite.tsx`
(LOT 6, `T10`), qui crée et retrouve TOUJOURS la page de présentation d'une entité par ce couple
exact (`cibleCorrespond`/`demandeDeCreation` dans ce fichier). La réutiliser plutôt que d'en
inventer une autre est la règle §6.5.

## 2.3 Aucun nombre n'est décidé pour les carrousels, et ce n'est pas inventé ici

Ni le cahier, ni la matrice, ni la fiche de lot ne nomment un nombre d'éléments à afficher par
section sur l'accueil — mesuré, zéro occurrence d'un chiffre associé à « arrivées récentes » ou
« événements » dans ce contexte. Le découpage réserve explicitement le « carrousel » à `T11`
(accueil desktop) et `T12` (carrousels mobiles).

Plutôt que d'inventer une borne ou de bloquer `T8` sur une question de **présentation** qui
n'est pas la sienne, les deux sections paginées (arrivées, événements) rendent leur première page
à la taille **par défaut** du cahier §18.2 (`25`, déjà décidée, pas inventée pour l'occasion) ;
`total` reste dans la réponse pour qu'un écran futur sache s'il y a davantage à montrer ailleurs.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make migrations-check` | tête `0023` inchangée, schéma identique |
| `make isolation-check` | **31 locales, 25 composites** — inchangé, `T8` n'ajoute aucune table |
| `make sources-check` | OK |
| `uv run pytest -q tests/test_accueil.py` | **6/6** |
| `uv run pytest -q tests/test_evenements.py tests/test_creation_evenements.py tests/test_modification_et_publication_evenements.py tests/test_annulation_archivage_et_restauration_evenements.py tests/test_medias_evenements.py tests/test_lecture_evenements.py tests/test_fiche_arrivee.py tests/test_validation_de_la_fiche_arrivee.py tests/test_arrivees_recentes.py tests/test_framework.py tests/test_liens_internes.py tests/test_rendu_des_blocs.py tests/test_accueil.py tests/test_contrat.py` | **249/249** |
| `make format-check`, `make lint`, `make typecheck` (depuis la racine) | verts |
| collecte depuis la racine | **1 547 pytest**, dont **1 145 d'intégration** (+6, tous d'intégration) |
| frontend | **706 Vitest** inchangés — aucun écran ne consomme encore l'agrégat d'accueil |
| **zéro régression** | `git worktree` sur `origin/develop` (après fusion de `T7`), même base : **74 échecs identiques des deux côtés** (jeu de démo, comptes en absolu) |

**Une première comparaison avait rendu 5 échecs de plus** (`test_debit.py`, trois tests,
`test_catalogue_des_taches.py`, un test), tous disparus à la relance isolée de la branche : les
deux suites `pytest` (développement et branche) tournaient **simultanément** sur la même base
PostgreSQL de développement partagée, et les tests de limitation de débit comptent des tentatives
dans une table commune — une collision de concurrence, pas une régression. Relancées **en
séquence**, les deux comparaisons rendent la liste identique.

---

# 4. Décisions

- `DEC-627` consigne la réalisation de `T8` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact, ouvert — sans objet direct ici,
  cette sous-étape ne porte aucune écriture.

---

# 5. Ce que `T8` laisse

- l'agrégat `GET /entities/{code}/accueil`, composant les cinq sections décidées par le cahier
  §8.4, dans leur ordre ;
- aucun écran ne consomme encore cette route : `T9` (écrans de consultation des événements),
  `T11` (accueil final desktop) et `T12` (accueil mobile, carrousels) restent à faire ;
- le choix du nombre d'éléments affichés par carrousel reste ouvert, délibérément, à `T11`/`T12`.

# Validation demandée à Jonathan

`T8` est faite. Après fusion, la prochaine sous-étape est `T9` : les écrans de consultation des
événements.
