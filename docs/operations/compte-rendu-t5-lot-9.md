# Compte rendu — `T5` du LOT 9 : le tableau de bord administratif

**Sous-étape :** la cinquième du lot — `MVP-L09-US001`
**Date :** 9 octobre 2026
**Décision :** `DEC-640`
**Stories :** `US001`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, **`T5`** |
| Restent | `T6` à `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Ce que la fiche nommait, et ce que le cahier dit vraiment

La fiche (`fiche-lot-9.md` §`T5`) abrège : « Profils actifs, arrivées futures,
onboardings en retard, profils incomplets, derniers imports ; pattern `T8`
du LOT 8. » Le cahier §10.8 « Administration », lui, énumère **six** lignes
distinctes pour le « Tableau de bord initial » : profils actifs, arrivées
futures, onboardings **actifs**, tâches **en retard**, profils incomplets,
derniers **problèmes** d'import CSV — le backlog (`MVP-L09-US001`) confirme
les six, dans le même ordre : « Profils actifs, arrivées futures,
onboardings, retards, profils incomplets et derniers imports sont
**comptabilisés** dans son entité. »

`T5` sert donc les **six** grandeurs du cahier, pas les cinq de l'abrégé de
la fiche — « onboardings en retard » recouvrait en réalité deux comptes
distincts (onboardings actifs, et tâches en retard).

**Aucune ligne de la matrice ne s'appelle « tableau de bord ».** Mesuré avant
d'écrire une ligne : zéro occurrence de « tableau de bord »/« dashboard »
dans `MATRICE_ROLES_PERMISSIONS_EXALT.md`. Ce que le cahier §10.8 nomme est
gouverné par des grilles déjà écrites ailleurs : le §15.1 « Reporting et
exports » donne, pour « Consulter les compteurs », « Consulter les profils
incomplets » et « Consulter les arrivées à 30 jours », la MÊME grille — `DSM`
Consultants, `ESM` Entité, `BOOST` Cercle, `OFFICE` —, `ADM-E` Entité, `SUPER`
Global — et le §8.1 « Consulter les tâches en retard » porte sa propre
grille, déjà codée par `T12` du LOT 7.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/administration/__init__.py` | **nouveau** — nouveau paquet |
| `apps/api/app/administration/perimetre.py` | **nouveau** — `ROLES_DU_TABLEAU_DE_BORD`, `ROLES_DE_LECTURE_DES_IMPORTS`, `PerimetreDuTableauDeBord`, `resoudre_le_perimetre_du_tableau_de_bord` |
| `apps/api/app/administration/tableau_de_bord.py` | **nouveau** — `lire_le_tableau_de_bord`, six compteurs |
| `apps/api/app/administration/routes.py` | **nouveau** — `GET /entities/{code}/administration/tableau-de-bord` |
| `apps/api/app/main.py` | monte `routeur_administration`, après l'accueil |
| `packages/contracts/src/contrat-api.json` | l'entrée `tableauDeBordAdministratif` |
| `apps/api/tests/test_tableau_de_bord.py` | **10 tests** (8 d'intégration, 2 unitaires purs) |

Aucune migration : les six comptes lisent des tables déjà posées (LOT 2, 5,
7, 9).

## 3.1 « Profil incomplet » — arbitrage de Jonathan du 09/10/2026

Le terme revient cinq fois dans le cahier sans jamais être défini. Mesuré
avant d'écrire : aucune notion de complétude de fiche n'existe dans le
dépôt. Posé en question à Jonathan, avant tout code : **un profil `active`
est incomplet s'il lui manque au moins une de ses quatre relations
organisationnelles courantes** — métier, cercle principal, DSM, statut
professionnel. Ce n'est pas une invention : c'est exactement ce que
`Restauration.relations_a_redonner` (LOT 5, `T8`) mesure déjà après une
restauration — la seule notion de « ce qu'il manque à un profil » qui
existait avant `T5`, réutilisée à l'identique. Le **client** n'entre pas
dans le calcul : il est conditionnel au statut (biconditionnelle
`mission`/`intercontract`, `T2`/`T3`), donc son absence seule n'est pas un
manque.

## 3.2 « Derniers imports » — lu contre deux citations concordantes, pas contre l'abrégé

Le cahier nomme la grandeur DEUX fois, et les deux fois en la qualifiant :
§10.8 dit « derniers **problèmes** d'import CSV », la section LOT 9
« Inclus » dit « dernières **erreurs** d'import ». Seul l'abrégé de
`fiche-lot-9.md` dit « derniers imports », sans qualificatif — un
raccourci, pas une troisième source. Les deux citations qui comptent
concordent : ce module montre les lots **récents qui ont un problème**
(`state = 'failed'` ou au moins une ligne rejetée), jamais la liste complète
des imports réussis, limité à **cinq** (`NOMBRE_D_IMPORTS_MONTRES`, même
nombre que le LOT 8 `T11` pour un résumé de ce type — aucun autre n'étant
donné par le corpus).

## 3.3 Qui voit les imports, et pourquoi ce n'est pas la même grille

`ROLES_DE_LECTURE_DES_IMPORTS` (`ESM`, `ADM-E`, `SUPER` seulement) est plus
étroite que `ROLES_DU_TABLEAU_DE_BORD` : un `DSM` ou un `BOOST` qui atteint
la route voit les cinq autres compteurs mais une liste **vide** d'imports —
la fiche LOT 9 §2 dit que `DSM`/`BOOST` « valident dans leur périmètre »
pendant un import EN COURS (`T7`/`T8`, pas encore construits), jamais
qu'ils peuvent consulter une synthèse des imports passés. Rapporté
structurellement (§7.20), jamais un 403 partiel sur un agrégat qui rend par
ailleurs 200.

## 3.4 Composition, jamais recopie — même patron que l'accueil (LOT 8, `T8`)

Les tâches en retard sont obtenues par un appel **direct** à
`lister_les_taches_en_retard` (LOT 7, `T12`), avec sa **propre** résolution
de périmètre (`resoudre_le_perimetre_du_suivi`) — jamais une seconde requête
qui pourrait diverger de la sienne. Les quatre autres comptes (profils
actifs, arrivées futures, onboardings actifs, profils incomplets) n'avaient
aucun service existant : ils réutilisent l'**idiome** de portée déjà établi
par le suivi (clauses `Consultants`/`Cercle` corrélées à un alias `em` sur
`entity_membership`) sans importer ses constantes privées — deux modules
déclarent chacun leur propre grille, même discipline que `content`/`events`/
`onboarding`.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_tableau_de_bord.py` | **10/10** |
| `uv run pytest -q apps/api/tests/test_contrat.py` | **5/5** |
| `uv run mypy` (racine) | vert, **213 fichiers** (+5 sur `T4`) |
| `make lint`, `make format-check` | verts |
| `make isolation-check` | **inchangé** — 35 tables locales, 29 clés composites, aucune table nouvelle |
| `make docs-check`, `make sources-check` | verts |
| `make audit` | zéro avis |
| collecte depuis la racine | **1 613 pytest** (+10), dont **1 199 d'intégration** (+8) ; **74 échecs environnementaux**, liste de fichiers identique à celle d'avant `T5` |
| frontend | **794 Vitest** inchangés — aucun fichier frontend touché |

---

# 5. Décisions et écarts

- `DEC-640` consigne la réalisation et l'arbitrage de Jonathan (« profil
  incomplet » = profil actif sans métier, cercle principal, DSM ou statut) ;
- aucun nouvel écart ni aucune nouvelle question n'est ouvert par `T5`.

---

# 6. Ce que `T5` laisse

- un acteur `DSM`/`ESM`/`BOOST`/`ADM-E`/`SUPER` consulte six compteurs dans
  sa portée ; `OFFICE` et les rôles sans responsabilité sont refusés ;
- aucun écran ne consomme encore cette route (même discipline que `T2`/`T3`
  de ce lot, aucun consommateur avant `T14`) ;
- aucun graphique, aucun export : « Reporting de base » seulement, le
  surplus reste au LOT 10 (même limite déjà posée par `T12` du LOT 7 pour
  le suivi).

# Validation demandée à Jonathan

`T5` est faite. Après fusion, la prochaine sous-étape est `T6` : dépôt
sécurisé du CSV, empreinte SHA-256, `import_batch`, zone d'analyse sans
écriture métier (`US004`, 1/2).
