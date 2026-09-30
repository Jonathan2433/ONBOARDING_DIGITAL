# Compte rendu — `T10` du LOT 7 : le changement automatique de parcours au changement de statut

**Date :** 28 septembre 2026
**Sous-étape :** `T10` — remplacement automatique mission ↔ intercontrat
**Décision :** `DEC-610`
**Story :** `MVP-L07-US007`, ferme `§30.14`

---

# 1. État du lot

`T1` à `T10` du LOT 7 sont désormais faites. Cinq sous-étapes restent, `T11` — l'archivage
automatique du parcours terminé et la révocation au départ — est la prochaine. Détail du
découpage : [`fiche-lot-7.md`](fiche-lot-7.md) §3.

---

# 2. Ce que la sous-étape a produit

**Aucune nouvelle table, aucune nouvelle colonne, aucune route propre.** Le modèle §13.5 déclarait
déjà `state='replaced'`, `replaced_by_instance_id`, `replacement_reason` sur `onboarding_instance` ;
le modèle §13.7 déclarait déjà les deux événements `RETAINED_ON_REPLACEMENT`/
`CANCELLED_ON_REPLACEMENT` — tout posé dès `T1`, jamais exercé avant cette sous-étape.

Une seule fonction, `remplacer_le_parcours_apres_changement_de_statut`
(`app/onboarding/instances.py`), appelée par `app.people.ecriture._ecrire_le_statut` (LOT 5, `T7`)
dans la MÊME transaction que l'écriture du champ `statut`, après les cinq écritures
organisationnelles. 7 tests d'intégration (`test_remplacement_onboarding.py`), appelant
`modifier_les_donnees_organisationnelles` directement — même parti que
`test_ecriture_organisationnelle.py` (LOT 5, `T7`) : `T10` n'ajoute aucune grille de permission
propre, retester la permission d'écrire `statut` aurait retesté le LOT 5.

## 2.1 Aucune grille de permission propre, et c'est vérifié contre le code, pas seulement affirmé

Le diagramme §14.1 ne nomme que « Service métier » et « PostgreSQL » — aucun acteur HTTP. La
question posée avant d'écrire une ligne : la grille du parcours (`T7`,
`_dans_le_perimetre_du_parcours` — ESM/ADM-E/SUPER entité, DSM rattaché, Booster rattaché) est-elle
au moins aussi large que celle qui autorise déjà l'écriture du champ `statut` (LOT 5, `T7`,
`CHAMPS_DU_BOOSTER`) ?

Mesuré en lisant les deux modules :

| Grille | Booster rattaché admis |
|---|---|
| LOT 5 `T7`, écriture de `statut` (`resoudre_le_perimetre`) | **seulement** s'il est membre **PRINCIPAL** du cercle cible (`_TYPE_DANS_LE_CERCLE_DU_BOOSTER`, filtré `== 'principal'`) |
| LOT 7 `T7`, périmètre du parcours (`_dans_le_perimetre_du_parcours`) | **n'importe quel** membre du cercle, principal ou secondaire (`_MEMBRE_DU_CERCLE_DU_BOOSTER`, commentaire du module : « aucune ligne du §7 ne restreint au seul principal ») |

La grille du parcours est donc **strictement plus large**. Quiconque réussit à écrire `statut` (en
ayant passé la grille la plus stricte des deux) est *a fortiori* dans le périmètre du parcours
(la grille la plus large). Poser une seconde garde ici serait une règle pour un ensemble d'acteurs
déjà inclus dans le premier — §7.27 de `CLAUDE.md`. `_ecrire_le_statut` a déjà vérifié le droit
d'écrire `STATUT` avant d'appeler la fonction de remplacement : la garde exercée par l'appelant EST
la garde de ce geste.

## 2.2 `ECART-013` mis à l'épreuve pour de vrai

Le catalogue (`onboarding_task_reference`, `T4`) porte un identifiant fonctionnel **stable**,
partagé par les deux modèles (mission et intercontrat). Une tâche `completed` de l'ancienne
instance est lue par `task_reference_id` ; toute tâche de la nouvelle version qui porte le MÊME
identifiant reçoit une ligne `completed` d'emblée :

- `completed_at`/`completed_by_person_id` **copiés tels quels** — même discipline que `T9` sur la
  réouverture, préserver la trace, jamais l'inventer ;
- `title_snapshot`/`description_snapshot`/`required`/`due_at` **recalculés depuis la NOUVELLE
  version** — une instance est toujours un instantané de SA version (`T7`) ;
- événement posé : `RETAINED_ON_REPLACEMENT`, jamais `ASSIGNED` — cette tâche n'a pas été affectée,
  elle a été retenue.

Un test (`test_une_tache_commune_terminee_est_retenue_et_ses_echeances_recalculees`) prouve les deux
volets à la fois : la valeur COPIÉE (`completed_at`, `completed_by_person_id`) et la valeur
RECALCULÉE (`due_at`, `title_snapshot`, avec un `due_offset_days` et un `title_override` différents
entre les deux modèles pour que le recalcul soit observable et non une coïncidence).

## 2.3 Les deux dernières transitions du diagramme §24.2

`T7`/`T8`/`T9` avaient exercé `Assigned`, `Completed`, `Todo -> Completed`, `Completed -> Todo`
(annulation), `Reopened -> Completed` (correctif `T9`). Il restait `Todo -> Cancelled`
(« remplacement de parcours ») et « `Completed -> Preserved` » — cette dernière ne correspondant à
**aucun état écrit** : le modèle §13.6 ne déclare que quatre états (`todo`, `completed`, `reopened`,
`cancelled`), pas de cinquième valeur `preserved`. Une tâche retenue reste `completed`, dans une
instance qui n'est plus `active` ; la préservation est donc **gratuite**, une conséquence du garde-
fou déjà posé (`lire_l_instance_active` ne trouve plus jamais une instance `replaced`), jamais une
colonne à ajouter.

`todo` ET `reopened` (une tâche pas encore refaite après réouverture administrative) rejoignent
tous deux `cancelled` — le diagramme ne nomme que `Todo`, mais `reopened` est le même état « pas
terminé » sous un autre nom, et le laisser traîner sur une instance devenue `replaced` serait une
troisième forme de tâche orpheline que ni le diagramme ni le modèle ne décrivent. Un test
(`test_les_taches_todo_et_reopened_de_l_ancienne_deviennent_cancelled`) prouve les deux cas dans le
même décor, avec l'événement `CANCELLED_ON_REPLACEMENT` posé pour chacun.

**Aucune fonction existante n'a eu besoin d'un correctif symétrique à celui de `T9`.**
`lire_l_instance_active` filtre déjà sur `state='active'` : une instance `replaced` cesse d'être
visible pour `terminer_une_tache`/`annuler_la_completion`/`reouvrir_une_tache` sans qu'aucun des
trois n'ait dû changer. Le diagramme §24.2 n'a donc plus rien à donner à ce lot : les six
transitions sur les quatre états sont désormais toutes exercées.

## 2.4 Un changement de client seul, même statut, ne remplace rien

`_ecrire_le_statut` distingue les champs ÉCRITS (qui incluent `CLIENT` dès que `STATUT` ou `CLIENT`
est demandé) de la VALEUR du statut qui a effectivement changé — seule cette seconde condition
déclenche le remplacement, portée par une dataclasse dédiée, `_EcritureDuStatut`, dont le champ
`changement` vaut `(ancien, nouveau)` uniquement quand `statut` lui-même diffère de l'ancien. Un
test (`test_un_changement_de_client_seul_meme_statut_ne_remplace_rien`) le prouve : l'instance reste
`active`, `replaced_by_instance_id` reste `NULL`.

## 2.5 `reference_date` de la nouvelle instance est l'instant du changement, jamais `arrival_date`

`affecter_un_parcours` (`T7`) ancre les échéances sur la date d'ARRIVÉE — la seule date connue à
l'affectation initiale. Un remplacement a lieu des mois plus tard : ancrer sur `arrival_date`
daterait les échéances de la nouvelle version dans le passé. `reference_date` du nouveau parcours
est donc l'instant du changement de statut lui-même, littéralement `starts_at` de la nouvelle ligne
`professional_status_assignment` que `_ecrire_le_statut` vient de poser.

## 2.6 Clore puis ouvrir, même parti qu'`app.people.ecriture`

L'ancienne instance passe `replaced` **avant** l'insertion de la nouvelle, sans quoi l'index unique
partiel de `T1` (`uq_onboarding_instance_membership_active`) refuserait une seconde ligne `active`
pour la même appartenance. `_LIER_LE_REMPLACEMENT` pose ensuite `replaced_by_instance_id` sur
l'ancienne, par une clé étrangère COMPOSITE `(replaced_by_instance_id, entity_id)` — les deux côtés
sont `onboarding_instance`, dont l'`entity_id` est toujours `NOT NULL` : aucun piège `MATCH SIMPLE`
ici.

## 2.7 Deux points confirmés par Jonathan le 28/09/2026, pas présumés

**`replacement_reason` reste `NULL`.** `DemandeDeModification` (LOT 5, §10.2) ne porte aucun champ
« motif », et `extra="forbid"` interdit d'en glisser un en silence — il n'existe structurellement
aucune source pour l'alimenter aujourd'hui. Ajouter un champ aurait élargi le périmètre de `T10` au
formulaire de modification du profil. Confirmé par Jonathan : laisser vide, le champ attend un
écrivain futur (LOT 10, avec le motif d'intervention du super-administrateur, `ECART-064`).

**Aucun `outbox_message`/`async_job` n'est écrit.** Le diagramme §14.1 termine par « Job disponible
via outbox » / « Worker recalcule progression et échéances secondaires ». Mesuré avant d'écrire :
**aucune ligne du dépôt n'écrit encore ces deux tables** — `app/auth/idempotence.py` (LOT 3, `T7`)
les nomme déjà comme un mécanisme qui « restera porté … au LOT 11 ». Et la progression (critère de
sortie n°3 du lot) n'est **jamais stockée** — aucune colonne n'existe pour qu'un worker la
« recalcule ». Inventer ici un message pour un consommateur qui n'existe nulle part aurait été
§6.5 (ne jamais inventer ce qui n'est pas décidé). Confirmé par Jonathan : documenter comme reste à
faire pour le LOT 11.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check .` / `ruff format --check .` | 0 erreur, dépôt entier |
| `uv run mypy` | 0 erreur, 173 fichiers Python |
| `uv run pytest apps/api/tests/test_remplacement_onboarding.py -q` | **7 tests, tous verts** |
| `make migrations-check` | tête `0021` inchangée — aucune migration nécessaire, toutes les colonnes existaient depuis `T1` |
| `make sources-check` | le nouveau fichier de test est suivi par git, aucune anomalie |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes |

**Zéro régression, prouvée par comparaison nommée sur la MÊME base.** Un `git worktree` sur
`origin/develop` (`cc5cb6a`), `.env` copié, a rendu **74 échecs environnementaux** — contre 74 sur
cette branche également (base de développement polluée par le jeu de démonstration, §11 de
`CLAUDE.md`), et la comparaison des deux listes triées de noms de tests en échec est **vide dans
les deux sens** : aucune régression, aucun défaut masqué par le bruit environnemental.

`uv run pytest -q --collect-only` : **1 377** tests (1 370 → 1 377, +7) ; `-m integration` :
**998** (991 → 998, +7). `make test-frontend` : inchangé, **282 + 111 + 225 = 618** — écriture pure,
aucune route propre, aucun module de contrat propre.

---

# 4. Décisions, écarts et questions

| ID | Objet |
|---|---|
| `DEC-610` | `T10` livrée : le changement automatique de parcours au changement de statut. Aucune grille de permission propre (vérifiée *a fortiori* contre le code), `ECART-013` mis à l'épreuve pour de vrai, les deux dernières transitions du diagramme §24.2 écrites, `replacement_reason` et l'absence d'`outbox_message`/`async_job` confirmés par Jonathan |

Aucun écart nouveau, aucune question nouvelle. `ECART-066` (volet parcours) reste ouvert, devient
**bloquant pour `T11`** — sans objet pour `T10`, qui n'archive ni ne restaure aucun parcours.

---

# 5. Ce que `T10` laisse

- `T11` — archivage automatique du parcours terminé et révocation au départ — devra s'accrocher à
  `enregistrer_un_depart` (LOT 3, `T9`) sans dupliquer sa logique de révocation, et devra reposer
  `ECART-066` (volet parcours) à Jonathan avant d'écrire quoi que ce soit — la question n'a été
  posée que pour la version de modèle (`T6`), et rien ne permet de présumer la même réponse.
- Le diagramme §24.2 est désormais entièrement exercé : les six transitions sur les quatre états
  (`todo`, `completed`, `reopened`, `cancelled`) ont chacune leur témoin. `T11` ajoutera l'archivage
  d'une instance `completed` (critère de sortie n°3 et modèle §13.5), un état déjà déclaré mais
  jamais encore atteint par aucune route.
- `outbox_message`/`async_job` restent des tables sans écrivain — résidu nommé, non bloquant,
  confirmé par Jonathan comme relevant du LOT 11.

---

# Validation demandée à Jonathan

Merci de valider `T10` pour fusion. Commande de fusion et de retour arrière ci-dessous.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arriere
```
