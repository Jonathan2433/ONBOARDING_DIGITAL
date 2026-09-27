# Compte rendu — `T8` du LOT 7 : terminer et annuler une tâche dans les cinq minutes

**Date :** 27 septembre 2026
**Sous-étape :** `T8` — terminer une tâche, l'annuler dans les cinq minutes
**Décisions :** `DEC-607` (correctif de `T7`), `DEC-608`
**Story :** `MVP-L07-US005`

---

# 1. État du lot

`T1` à `T8` du LOT 7 sont désormais faites. Sept sous-étapes restent, `T9` —
réouvrir une tâche après cinq minutes — est la prochaine. Détail du
découpage : [`fiche-lot-7.md`](fiche-lot-7.md) §3.

---

# 2. Ce que la sous-étape a produit

Deux routes, matrice §8.1 : `POST .../onboarding-parcours/taches/{tache}/
completion` (« Marquer une tâche comme terminée ») et `.../annulation`
(« Annuler la completion dans les 5 minutes »). Nouveau module
`app/onboarding/taches.py`, extension de `app/onboarding/perimetre.py`
(quatrième grille) et d'`app/onboarding/routes.py`. Aucune nouvelle table :
`onboarding_instance_task` existe depuis `T1`, ses colonnes `state`/
`completed_at`/`completed_by_person_id` n'avaient jamais été écrites. Aucun
module de contrat propre : `ReponseDeTacheDuParcours` existe déjà depuis
`T7`, et deux nouvelles entrées du manifeste (`contrat-api.json`) la
réutilisent — « écriture pure », même règle que les routes de `T5`/`T6`.

## 2.1 La grille la plus stricte du module — `Soi` seul, sans exception

Piège n°1 de `fiche-lot-7.md` §2.1 : consulter n'est pas agir. Sur la
lecture du parcours (`T7`), `DSM`/`BOOST` ont « Consultants »/« Cercle » ;
sur ces deux lignes précises, ils sont à **tiret**, comme `ESM`/`ADM-E`/
`SUPER`. `peut_agir_sur_sa_tache_onboarding` ne lit même pas la base — une
comparaison d'identité pure suffit et est exhaustive. Le témoin qui compte
n'est donc pas un rôle sans rattachement, ce qui ne prouverait qu'une
absence triviale : c'est un **DSM rattaché à ce consultant précis**, qui lit
pleinement son parcours (`T7`) et doit pourtant être refusé d'agir sur sa
tâche. Deux témoins le prouvent, un par action.

## 2.2 `annuler_la_completion` ne produit jamais l'état `cancelled`

Le modèle §13.6 donne quatre états — `todo`, `completed`, `reopened`,
`cancelled` — et une lecture rapide pourrait faire croire à une transition
directe `completed` → `cancelled` pour « annuler ». Ce n'est pas le cas :
`cancelled` est réservé à `T10` (§13.7, événement
`CANCELLED_ON_REPLACEMENT` — une tâche rendue obsolète par un changement de
statut, jamais désirée à nouveau). Annuler une complétion dans les cinq
minutes est un geste du nouvel arrivant sur sa propre erreur : la tâche
redevient `todo`, `completed_at`/`completed_by_person_id` sont effacés. Un
témoin le prouve **directement** en re-terminant la même tâche après
l'avoir annulée — une transition vers `cancelled` (terminale) l'aurait
interdit.

## 2.3 La fenêtre de cinq minutes — ancrée à `completed_at`, jamais mockée

Exigence explicite de `fiche-lot-7.md` §3 : « la fenêtre de cinq minutes
doit être injectable, jamais un `sleep()` de test ni une horloge figée ».
La précondition compare l'`instant` réel de la requête (jamais figé, comme
partout ailleurs dans le module) à `completed_at`, une valeur déjà
**stockée** en base — et c'est cette valeur que les témoins font varier, en
la reculant directement par SQL. Aucune horloge n'est jamais mockée.

**La précondition entière — état de départ et fenêtre — est dans le `WHERE`
d'un seul `UPDATE` atomique**, même parti que `cycle_de_vie.py` (`T6`).
Contrairement à ce module, qui replie toute cause d'échec dans un seul code
(délibérément, pour ne pas distinguer une course d'un état erroné), `T8`
**distingue** `transition_de_tache_invalide` (mauvais état de départ) de
`delai_d_annulation_depasse` (bon état, fenêtre fermée) : la différence
oriente l'appelant vers `T9` (réouverture administrative) dans le second
cas seulement. Cette distinction ne rouvre aucune fenêtre de course : un
diagnostic en lecture seule, après l'échec de l'écriture, choisit entre les
deux codes — jamais une décision.

## 2.4 Correctif `DEC-607` : `T7` ne posait aucun événement

Critère de sortie n°4 de la fiche (§1.2) : « les événements de tâche sont
historisés […] `onboarding_task_event`, écrit à `T7`-`T10` ». `T7` livrait
la table et l'affectation, mais n'écrivait **aucun** événement — un résidu
non nommé dans son propre compte rendu (§2.7, « ce que `T7` ne fait pas »
ne le mentionnait pas), trouvé en relisant ce critère avant d'écrire `T8`.
`affecter_un_parcours` reçoit désormais `acteur` et pose un événement
`ASSIGNED` par tâche snapshottée, via `enregistrer_un_evenement_de_tache` —
la même fonction que `T8` emploie pour `COMPLETED`/`CANCELLED` (§7.27 :
une seule écriture d'événement, jamais une par sous-étape). Un témoin
interroge directement `onboarding_task_event` et vérifie la séquence
`ASSIGNED`, `COMPLETED`, `CANCELLED`, chacun avec un acteur humain non nul.

## 2.5 Un défaut de mon propre décor, pas du livrable

`T8-1`. Le décor de test créait un modèle `GLOBAL` avec la session de
l'ESM — refusé 403, puisque seul `SUPER` gère `portee: GLOBAL` (règle de
`T5`). C'est **exactement** le défaut `T7-5` du compte rendu précédent,
rejoué à l'identique dans un fichier de test différent. Corrigé en créant
le modèle en `portee: ENTITY`, que l'ESM gère pleinement — le geste testé
(terminer/annuler) n'exige aucune portée particulière.

## 2.6 Ce que `T8` ne fait pas, et ce n'est pas un oubli

Ni réouverture après le délai (`T9`, `ESM`/`ADM-E`/`SUPER`, motif
obligatoire), ni changement automatique mission/intercontrat (`T10`), ni
archivage du parcours terminé (`T11`). **Résidu nommé, non instruit** : le
§8.2 du corpus (matrice et cahier, concordants) écrit en prose « sauf
correction technique explicitement auditée par l'administrateur ou le
super-administrateur » — une exception qu'aucune section du corpus ne
développe (pas de route nommée, pas de motif ni de champ d'audit dédiés),
et que le découpage de `fiche-lot-7.md` §3 n'assigne à aucune des quinze
sous-étapes. L'inventer aurait été §6.5 — une décision non tranchée.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check .` / `ruff format --check .` | 0 erreur |
| `make typecheck` (mypy strict + `tsc --noEmit`) | 0 erreur, 171 fichiers Python |
| `uv run pytest apps/api/tests/test_taches_onboarding.py -q` | **15 nouveaux tests, tous verts** |
| `uv run pytest` (T1–T7 de l'onboarding + contrat, 92 tests) | 92/92, aucune régression |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes |
| `make migrations-check` | tête `0021` inchangée — aucune migration nécessaire |

**Zéro régression, prouvée par comparaison nommée sur la MÊME base.** Un
`git worktree` sur `origin/develop` (`072da34`), `.env` copié, a rendu **74
échecs environnementaux** — contre 74 sur cette branche également, et la
comparaison `comm` des deux listes triées de noms est **vide dans les deux
sens**.

`uv run pytest -q --collect-only` : **1 353** tests (1 338 → 1 353, +15) ;
`-m integration` : **974** (959 → 974, +15). `make test-frontend` :
inchangé, **282 + 111 + 225 = 618** — écriture pure, aucun module de
contrat propre.

---

# 4. Décisions, écarts et questions

| ID | Objet |
|---|---|
| `DEC-607` | Correctif trouvé en écrivant `T8` : `affecter_un_parcours` (`T7`) pose désormais un événement `ASSIGNED` par tâche snapshottée |
| `DEC-608` | `T8` livrée : terminer/annuler une tâche. `Soi` seul, `annuler` ne produit jamais `cancelled`, fenêtre ancrée à `completed_at` |

Aucun écart nouveau, aucune question nouvelle. `ECART-066` (volet
parcours) reste ouvert, bloquant pour `T11`, sans objet pour `T8`.

---

# 5. Ce que `T8` laisse

- Le §8.2 du corpus nomme une exception (« correction technique auditée par
  l'administrateur ou le super-administrateur ») qu'aucune sous-étape du
  découpage n'assigne — résidu nommé, non instruit, voir §2.6.
- `T9` réouvre APRÈS le délai — `ESM`/`ADM-E`/`SUPER` seulement, motif
  obligatoire, `DSM`/`BOOST` explicitement exclus (§8.3) — une grille
  DIFFÉRENTE de celle de `T8` (`Soi` seul), et une transition vers l'état
  `reopened`, jamais un retour à `todo` (réservé à l'annulation dans la
  fenêtre).
- `T9` réutilise la lecture de `completed_at` pour son propre délai,
  n'invente pas un second mécanisme de fenêtre.

---

# Validation demandée à Jonathan

Merci de valider `T8` pour fusion. Commande de fusion et de retour arrière
ci-dessous.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arriere
```
