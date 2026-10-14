# Compte rendu — `T3` du LOT 9 : changer un collaborateur d'entité

**Sous-étape :** la troisième du lot — `MVP-L09-US002` (2/2)
**Date :** 8 octobre 2026
**Décision :** `DEC-638`
**Stories :** `US002` (2/2) — `US002` est désormais complète

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | `T1`, `T2`, **`T3`** |
| Restent | `T4` à `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Ce que la fiche nomme, et ce que `T3` livre réellement

La fiche (`fiche-lot-9.md` §`T3`) nomme trois mouvements : « changement d'entité, de statut, de
rattachement ». **Deux des trois sont déjà servis**, mesuré avant d'écrire une ligne :
`modifier_les_donnees_organisationnelles` (`PATCH .../people/{appartenance}`, LOT 5 `T7`) modifie
déjà le statut (et le client), le métier, le cercle et le DSM d'une appartenance **dans son
entité**. La seule opération que rien ne sert encore est le **changement d'entité** lui-même — ce
que le cahier §16.3 nomme parmi les opérations atomiques, aux côtés du départ et du changement de
statut, et que le §11.1 résume en une phrase : « cloture l'ancienne appartenance et les
responsabilités incompatibles ». `T3` livre donc cette seule opération, et referme `US002`.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/people/creation.py` | refactorisé : `DemandeDAppartenance` et `creer_l_appartenance` extraites, **partagées** entre `T2` (personne neuve) et `T3` (personne existante) |
| `apps/api/app/people/transfert.py` | **nouveau** — `changer_d_entite`, `Transfert` |
| `apps/api/app/people/routes.py` | `POST /entities/{code}/people/{appartenance}/changement-d-entite`, `DemandeDeChangementDEntite`, `ReponseDeChangementDEntite` |
| `packages/contracts/src/contrat-api.json` | l'entrée `changementDEntite` |
| `apps/api/tests/test_transfert_collaborateurs.py` | **6 tests d'intégration** |
| `apps/api/tests/test_creation_collaborateurs.py` | adapté à la forme imbriquée de `DemandeDeCollaborateur` |

Aucune migration : `T3` compose les mêmes primitives que `archiver_un_profil` (LOT 5 `T8`) et
`creer_l_appartenance` (`T2`), sans toucher au schéma.

## 3.1 Deux points arbitrés par Jonathan avant tout code

Le corpus ne dit rien de plus que la phrase du §11.1 citée plus haut — ni procédure, ni motif de
transfert, ni si la nouvelle appartenance doit être immédiate. Deux conséquences concrètes ont été
posées en question avant d'écrire :

1. **La révocation.** Le même moteur que le départ (`enregistrer_un_depart`) est réutilisé pour
   fermer l'ancienne appartenance : TOUTES les sessions et liens magiques de la personne sont donc
   révoqués, pas seulement ceux de l'entité quittée. Réponse : **oui, tout révoquer** — c'est déjà
   ce que `uq_entity_membership_person_id_occupante` impose structurellement (au plus une
   appartenance occupante par personne, toutes entités confondues), et une session qui survivrait
   dans la nouvelle entité serait une session jamais authentifiée pour cette appartenance-là.
2. **L'atomicité.** Fermeture de l'ancienne et création de la nouvelle : une seule transaction, ou
   deux gestes séparés ? Réponse : **une seule transaction** — un transfert à moitié fait (ancienne
   fermée, nouvelle absente) laisserait un collaborateur sans aucune appartenance occupante nulle
   part, ce que rien dans le corpus n'envisage comme un état valide.

## 3.2 Pourquoi `archiver_un_profil` n'est pas réutilisé tel quel

`archiver_un_profil` (LOT 5 `T8`) compose déjà `enregistrer_un_depart` /
`archiver_une_appartenance` / `archiver_le_parcours_au_depart` dans le bon ordre — mais son
périmètre (`ROLES_DU_CYCLE_DE_VIE` = ESM/ADM-E/SUPER seuls) est plus étroit que celui que la fiche
donne à `T3` (« même périmètre que `T2` » : DSM et Booster y entrent, dans leur portée restreinte).
L'appeler aurait donc refusé à un DSM un transfert qu'il a par ailleurs le droit de faire. `T3`
compose les mêmes primitives, dans le même ordre, avec son propre contrôle de périmètre — évalué
sur l'entité de **destination**, exactement comme `T2`.

## 3.3 L'ancienne appartenance va jusqu'à `archived`, jamais seulement `departed`

Contrairement à un vrai départ — où `departed` reste une étape avant un geste humain délibéré — ici
la nouvelle appartenance existe déjà à la fin du même appel. La laisser en `departed` créerait un
résidu à archiver séparément, sans raison. Le chemin complet du §24.1 est donc parcouru :
`Active --> Departed --> Archived` si la cible était active, `Future --> Archived` seul si elle
n'était pas encore arrivée.

## 3.4 Un troisième point, trouvé en écrivant les tests — pas anticipé par la fiche

`ex_entity_membership_sans_chevauchement` (§25.2) ne porte **aucune** clause `WHERE` : deux
périodes d'une même personne ne se chevauchent jamais, même archivées, même entre deux entités
différentes — « une personne n'a pas été dans deux entités en même temps, même dans le passé ».
Annuler une arrivée `future` (`archiver_une_appartenance`) **ne pose pas** `departure_date` — « une
arrivée annulée » n'est pas un départ, `test_l_archivage_d_une_arrivee_FUTURE_n_enregistre_AUCUN_
depart`, LOT 5 `T8`, intact. Sa période reste donc `[arrival_date, )`, non bornée, pour toujours.

Transférer une personne `future` créait donc **toujours** un chevauchement avec sa propre ancienne
période non bornée, quelle que soit la date choisie dans l'entité de destination — deux plages non
bornées se recoupent nécessairement. Posé en question à Jonathan, avant toute correction :
arbitrage du 08/10/2026, **une arrivée annulée DANS LE CADRE D'UN TRANSFERT libère la date** — son
`departure_date` est posé à `arrival_date`, ce qui rend sa période **vide** (`[x, x)`), donc inerte
pour l'exclusion. Seulement dans ce cadre : l'annulation **seule** (`archiver_un_profil`, hors
transfert) n'est **pas** modifiée, et son témoin du LOT 5 continue de prouver `departure_date IS
NULL` pour ce chemin-là, inchangé — vérifié, `test_archivage.py` est toujours vert sans aucune
modification.

---

# 4. Défauts trouvés et corrigés dans mes propres tests, avant tout commit

1. **Régression introduite par le partage de `DemandeDAppartenance`.** En déplaçant la
   biconditionnelle statut/client dans `creer_l_appartenance` seule, un test de `T2`
   (`test_une_mission_sans_client_est_refusee_AVANT_toute_ecriture`) a échoué : la personne était
   créée avant que la biconditionnelle ne soit vérifiée. Corrigé en appelant
   `valider_la_biconditionnelle_statut_client` explicitement en tête de `creer_un_collaborateur`,
   en plus de son appel dans `creer_l_appartenance` — la fonction est pure, sans accès base, donc
   l'appeler deux fois ne coûte rien et ne risque aucun effet de bord.
2. **Un bug dans mon propre premier jet de `changer_d_entite`** : `revocation = ...` était
   réassigné deux fois (dépaquetage, archivage), perdant silencieusement le décompte du départ.
   Trouvé en relisant mon propre code avant de le lancer, pas par un test qui aurait échoué —
   corrigé en `Transfert.revocations: tuple[Revocation, ...]`, même convention qu'`Archivage`
   (LOT 5 `T8`), accumulée dans une liste locale.
3. **Trois défauts dans mes propres fixtures de test**, aucun dans le code livré :
   - une date de destination antérieure à une arrivée annulée non encore libérée (`T3.4`
     ci-dessus, trouvé AVANT la correction, pas après) ;
   - `_collaborateur_occupant(..., etat="departed", ...)` sans `departure_date` : la contrainte
     `ck_entity_membership_depart_date_si_departed` refusait le DÉCOR lui-même, avant même d'
     atteindre `changer_d_entite` ;
   - un test attendait une `IntegrityError` brute pour le déclencheur `dsm_responsabilite_active`,
     alors que `changer_d_entite` la traduit en `ErreurApplicative` (`422`), exactement comme `T2`
     le fait déjà et le prouve (`test_un_dsm_SANS_responsabilite_active_est_refuse_en_422`).

---

# 5. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_transfert_collaborateurs.py` | **6/6** |
| `uv run pytest -q apps/api/tests/test_creation_collaborateurs.py` | **13/13**, inchangé après le refactor |
| `uv run pytest -q apps/api/tests/test_contrat.py` | **5/5** |
| `uv run pytest -q apps/api/tests/test_archivage.py` | **54/54** au total sur les quatre fichiers — aucune régression sur les chemins partagés (`archiver_une_appartenance`, `enregistrer_un_depart`) |
| `make isolation-check` | inchangé — 35 tables locales, 29 clés composites, 0 référence nue |
| `make lint`, `make format-check`, `uv run mypy`, `pnpm run typecheck` | verts (205 fichiers Python) |
| `make docs-check`, `make sources-check` | verts |
| `make audit` | zéro avis |
| collecte depuis la racine | **1 596 pytest** (+6), dont **1 184 d'intégration** (+6, toutes marquées `@pytest.mark.integration`) ; **74 échecs environnementaux**, liste identique à celle mesurée avant `T3` (comparée fichier par fichier, aucun test de `T2`/`T3`/contrat/archivage parmi eux) |
| frontend | **794 Vitest** inchangés — aucun fichier frontend touché |

---

# 6. Décisions et écarts

- `DEC-638` consigne la réalisation et les trois arbitrages de Jonathan (révocation totale,
  transaction unique, libération de la période annulée) ;
- aucun nouvel écart ni aucune nouvelle question n'est ouvert par `T3` ;
- `US002` est désormais complète dans ses deux volets.

---

# 7. Ce que `T3` laisse

- un collaborateur actif ou futur se transfère d'une entité à l'autre en une transaction, avec
  revocation de session complète et archivage du parcours d'onboarding actif le cas échéant ;
- le changement de statut et de rattachement **dans une même entité** reste servi par le `PATCH`
  de LOT 5 `T7`, inchangé ;
- `parcours_onboarding_archive` est câblé mais non reprouvé en détail : aucun parcours n'existe
  dans les fixtures de `T3`, et sa correction reste celle, déjà prouvée, de LOT 7 `T11`.

# Validation demandée à Jonathan

`T3` est faite. Après fusion, la prochaine sous-étape est `T4` : restauration des ressources
archivées autorisées par back-office (`US008`), qui dépend de `T2`/`T3` et distingue les
restaurations simples (déjà couvertes par la matrice) des restaurations techniques/massives
(rôles réservés).
