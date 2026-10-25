# Compte rendu — `T10` du LOT 10 : le reporting étendu

**Sous-étape :** la dixième du lot — reporting étendu, compteurs et tableaux du §15.1/§10.10,
distinct du tableau de bord administratif
**Date :** 21 octobre 2026
**Décision :** `DEC-664`
**Story :** `MVP-L10-US003`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, `T8`, `T9`, **`T10`** |
| Restent | `T11` à `T16` |
| Issues | épic `#267`, story `#270` |

---

# 2. Ce que le corpus décidait déjà, et ce qu'il restait à faire

**Mesuré avant tout code : le tableau de bord administratif (LOT 9, `T5`, cahier §10.8) et ce
reporting (cahier §10.10) sont deux ressources distinctes qui se recoupent — exactement, pas
approximativement.** La fiche §2 l'anticipait sans trancher (« à vérifier en construisant si des
comptes se recoupent, jamais supposé »). Mesure : les six grandeurs du tableau de bord (profils
actifs, arrivées futures, onboardings actifs, tâches en retard, profils incomplets, derniers
imports en échec) sont TOUTES gouvernées par le §15.1 « Reporting et exports », et le docstring de
`app/administration/perimetre.py` le cite déjà explicitement. `T10` ne reconstruit donc RIEN de
ces six grandeurs : il ajoute uniquement ce que le cahier §10.10 nomme et que `T5` ne sert pas.

**La grille de rôle n'est pas redéclarée — c'est la MÊME ligne du §15.1, contrairement à `T9`.**
`T9` avait déclaré `ROLES_D_EXPORT_DE_L_AUDIT` séparément de `ROLES_DES_DETAILS_TECHNIQUES` parce
que les deux lignes de la matrice qui les gouvernent sont DISTINCTES et ne coïncident
qu'aujourd'hui. Ici, les quatre premières lignes du §15.1 (« Consulter les compteurs », « le
détail onboarding », « les profils incomplets », « les arrivées à 30 jours ») portent
**littéralement** la même grille — `DSM` Consultants, `ESM`/`ADM-E`/`SUPER` Entité, `BOOST` Cercle,
`OFFICE` —. `app.reporting` réimporte donc `ROLES_DU_TABLEAU_DE_BORD`/`PerimetreDuTableauDeBord`/
`resoudre_le_perimetre_du_tableau_de_bord` (LOT 9, `T5`) directement : une liste derivable d'une
même règle ne se recopie pas (§7.27).

**Trois formules dérivées du modèle, jamais nommées littéralement par le corpus, documentées
plutôt que devinées en silence :**

- **« Onboardings terminés »** : le modèle §13.5 déclare un état `completed` sur
  `onboarding_instance.state`, mais `app.onboarding.instances` documente explicitement que cet état
  n'est **jamais produit** — un parcours achevé transite directement `active -> archived`. La seule
  colonne qui distingue un archivage par COMPLÉTION (`archiver_le_parcours_si_termine`/
  `archiver_un_parcours_termine`, qui posent `completed_at`) d'un archivage par DÉPART
  (`archiver_le_parcours_au_depart`, qui ne le pose JAMAIS) est donc `completed_at`. « Onboarding
  terminé » = `state = 'archived' AND completed_at IS NOT NULL`.
- **« Durée moyenne »** : aucune formule n'est écrite nulle part. Seules les colonnes
  `started_at`/`completed_at` existent et rendent calculable `completed_at - started_at`, sur la
  MÊME population que « onboardings terminés » — un parcours actif n'a pas de durée achevée, un
  parcours interrompu par un départ n'a pas de `completed_at` pour la mesurer. `NULL` (jamais `0`)
  si cette population est vide.
- **« Progression moyenne »** : le couple (`taches_obligatoires_totales`,
  `taches_obligatoires_terminees`) de `Progression` (LOT 7, `T7`, « comptée à chaque appel, jamais
  stockée ») est SOMMÉ sur les instances **actives seules** de la portée — une instance terminée
  est à 100 % par définition et diluerait la mesure sans rien dire de la progression en cours.

**« Filtrer par période, DSM, cercle, client » (§15.1) est un axe transversal, pas une septième
ligne** — même lecture que les cinq filtres facultatifs d'`app.audit.lecture.FiltresDAudit` (§6.4).
Il borne `entity_membership.arrival_date` et narrowe par des clauses `EXISTS` corrélées à `em`,
jamais une escalade au-delà du périmètre déjà résolu.

**La sixième ligne du §15.1, « Consulter les événements » (seule où `OFFICE` reçoit `Bureau`),
n'est PAS construite.** Elle est absente du cahier §10.10 (la liste normative des indicateurs MVP)
et des critères d'acceptation littéraux d'`US003` (« Compteurs et tableaux respectent ESM, DSM,
Booster, admin et superadmin »). Sa grille est mot pour mot identique à celle de « Archiver un
événement » (§18) et de quatre lignes du §11 — une lecture plausible la rattacherait au calendrier
d'événements du LOT 8 — mais aucune phrase du corpus ne le dit explicitement, et bâtir une route
sur une inférence serait enfreindre §6.5. `QO-126` ouverte au registre, non bloquante.

**Aucun arbitrage de Jonathan n'a été nécessaire.**

---

# 3. Ce que la sous-étape a produit

## 3.1 `app/reporting/lecture.py` — nouveau module

- `FiltresDeReporting` : `depuis`/`jusqua`/`dsm`/`cercle`/`client`, tous facultatifs.
- `lire_les_indicateurs` : onboardings terminés, progression moyenne, durée moyenne, arrivées à
  30 jours, et les trois répartitions (cercle/client/DSM), toutes sur la population « profils
  actifs » (répartitions) ou « instances actives »/« instances archivées par complétion » (le
  reste), dans la portée résolue.
- `lister_le_detail_onboarding` : page paginée de la progression par personne, instances actives
  seules.
- `lister_les_profils_incomplets` : page paginée, reprenant EXACTEMENT la règle des quatre
  relations manquantes de `app.administration.tableau_de_bord` (métier, cercle principal, DSM,
  statut), en détail plutôt qu'en compte.
- Les clauses de périmètre (`_CLAUSE_CONSULTANTS`/`_CLAUSE_CERCLE`) sont REDÉCLARÉES à l'identique
  de `tableau_de_bord.py`, pas importées — même discipline que `suivi.py` vs `tableau_de_bord.py`.

## 3.2 Les trois routes

`app/reporting/routes.py` : `GET /entities/{code}/reporting` (scalaires), `.../reporting/onboarding`
et `.../reporting/profils-incomplets` (paginées). Toutes gardées par
`exiger_un_role_dans_l_entite(ROLES_DU_TABLEAU_DE_BORD)`, le rôle étant RE-RÉSOLU dans le corps de
la route pour calculer le périmètre précis — même motif que `consulter_le_tableau_de_bord`/
`consulter_le_journal_d_audit`.

---

# 4. Contrôles exécutés

**Quinze tests d'intégration nouveaux**, `apps/api/tests/test_reporting.py`, décor propre au
module — `test_tableau_de_bord.py` (LOT 9, `T5`) prouve déjà `resoudre_le_perimetre_du_tableau_de_
bord`, retestée nulle part ici (§7.27).

| Contrôle | Résultat |
|---|---|
| `pytest` racine | 1 837 collectés (+15, tous d'intégration), 1 759 passés / 78 échecs |
| Comparaison de worktree avec `origin/develop` | 77 échecs environnementaux **identiques** après correction du manifeste de contrat (voir ci-dessous) |
| `uv run mypy` (racine) | vert, 260 fichiers (+4) |
| `uv run ruff check`/`format` | vert, tout le dépôt |
| `make migrations-check` | schéma identique, tête `0027` inchangée — aucune migration |
| `make isolation-check` | 37 tables locales, 29 clés composites, 0 référence nue |
| `make docs-check` | vert |
| `make sources-check` | aucun fichier source ignoré par git |
| Contrat (`test_contrat.py`) | mis à jour (`indicateursDeReporting`, `detailOnboardingDuReporting`, `profilsIncompletsEnDetail`), 91 chemins, 5/5 |

**Une régression réelle, trouvée et corrigée avant la preuve finale** : la comparaison de worktree
a montré 78 échecs sur la branche contre 77 sur `origin/develop`, la seule différence étant
`test_contrat.py::test_les_chemins_du_schema_sont_exactement_ceux_du_manifeste` — les trois routes
nouvelles n'étaient pas déclarées dans `packages/contracts/src/contrat-api.json`. Corrigé en
ajoutant les trois entrées ; la seconde comparaison rend les deux listes identiques.

**Un défaut trouvé et corrigé dans le décor de test, avant le premier commit** : `client.
canonical_name` (`character varying(256)`) et `.display_name` (`text`) partageaient un paramètre
lié — même classe que §7.25 de la passation (« un paramètre lié partagé par deux colonnes de types
différents »). Un second défaut, dans le même décor : une situation professionnelle en `mission`
exige un client ACTIVÉ POUR L'ENTITÉ (`entity_client`, déclencheur `fn_mission_client_actif`,
dette du LOT 2 acquittée par un lot antérieur) — sans cette ligne, l'insertion échoue en
`CheckViolation`.

---

# 5. Décisions et écarts

`DEC-664` consigne cette sous-étape. `QO-126` ouverte (« Consulter les événements » du §15.1, non
construite, non bloquante). Aucun écart ouvert ni fermé.

---

# 6. Ce que `T10` laisse

- **La sixième ligne du §15.1** reste sans route — `QO-126`.
- **Aucun écran** ne consomme encore ces routes : les écrans back-office arrivent à `T15`.
- **Le bouton « Reporter un bug »** (`US005`) reste à `T11`.

---

**Validation demandée à Jonathan.**

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
