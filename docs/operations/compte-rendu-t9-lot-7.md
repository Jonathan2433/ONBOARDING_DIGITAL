# Compte rendu — `T9` du LOT 7 : réouvrir une tâche après le délai de cinq minutes

**Date :** 27 septembre 2026
**Sous-étape :** `T9` — réouverture administrative après le délai de cinq minutes
**Décision :** `DEC-609`
**Story :** `MVP-L07-US006`

---

# 1. État du lot

`T1` à `T9` du LOT 7 sont désormais faites. Six sous-étapes restent, `T10` —
le changement automatique mission ↔ intercontrat — est la prochaine. Détail
du découpage : [`fiche-lot-7.md`](fiche-lot-7.md) §3.

---

# 2. Ce que la sous-étape a produit

Une route, matrice §8.1/§8.3 : `POST .../onboarding-parcours/taches/{tache}/
reouverture` (« Réouvrir après le délai de 5 minutes »). Extension d'`app/
onboarding/taches.py` (`reouvrir_une_tache`, troisième fonction du module),
d'`app/onboarding/perimetre.py` (cinquième grille) et d'`app/onboarding/
routes.py`. Aucune nouvelle table ni colonne : le modèle §13.6 déclarait déjà
`state='reopened'`, `reopened_at`/`reopened_by_person_id`/`reopen_reason` et
la contrainte `motif_requis_a_la_reouverture`, tous posés dès `T1`. Aucun
module de contrat propre : `ReponseDeTacheDuParcours` existe depuis `T7`.

## 2.1 La cinquième grille du module — inverse exacte de la quatrième

Matrice §8.3, à la lettre : « Le DSM et le Booster ne peuvent pas effectuer
cette correction ». Là où `T8` accordait `Soi` seul et refusait tout le
reste, `T9` accorde `ESM`/`ADM-E`/`SUPER` et refuse tout le reste — y compris
`Soi`, qui n'a ici aucun rôle. Le témoin qui compte n'est donc pas un `DSM`
ou un `BOOST` sans aucun rattachement, ce qui ne prouverait qu'une absence
triviale : ce sont un `DSM` et un `BOOST` **rattachés** à ce consultant/ce
cercle précis, qui lisent et affectent pleinement ce parcours (`T7`, piège
n°1 de `fiche-lot-7.md` §2.1) et doivent pourtant être refusés ici — deux
témoins le prouvent, un par rôle.

**Aucune fonction `peut_...` séparée n'est nécessaire.** Contrairement au
parcours (`T7`, DSM/Booster rattachés admis par requête) et à la
restauration de modèle (`T6`, distinction GLOBAL/entité), cette grille n'a
ni rattachement ni portée à distinguer : une tâche d'instance vit toujours
dans une entité, jamais au niveau global. La garde de rôle coarse
(`exiger_un_role_dans_l_entite`, `ROLES_DE_REOUVERTURE_DES_TACHES` =
`{ESM, ADM-E, SUPER}`) EST la vérification complète — même parti que le
catalogue des tâches (`T4`), où la garde seule suffisait déjà.

## 2.2 La fenêtre — inverse stricte de celle de `T8`, même ancre

`fiche-lot-7.md` §3 dit explicitement que `T9` réutilise la lecture de
`completed_at` pour son propre délai, sans inventer un second mécanisme.
`annuler_la_completion` (`T8`) exige `completed_at >= instant - 5 minutes`
(encore dans la fenêtre) ; `reouvrir_une_tache` exige l'inverse **strict**,
`completed_at < instant - 5 minutes` (fenêtre close). Les deux frontières se
touchent sans se chevaucher : à l'instant exact où la fenêtre se ferme,
l'annulation en libre service est encore possible et la réouverture
administrative ne l'est pas encore — aucun moment n'ouvre les deux gestes ni
n'en ferme aucun. Un témoin refuse la réouverture tentée immédiatement après
la complétion (`409 reouverture_prematuree`), un autre la réussit après
avoir reculé `completed_at` de six minutes par SQL — jamais un `sleep()` ni
une horloge mockée.

La précondition entière reste dans le `WHERE` d'un seul `UPDATE` atomique,
et `_echouer` (généralisée pour servir les trois fonctions du module)
distingue toujours l'état de départ invalide (`transition_de_tache_
invalide`) de la fenêtre du mauvais côté — ici `reouverture_prematuree`,
symétrique du `delai_d_annulation_depasse` de `T8`.

## 2.3 Correctif à `terminer_une_tache` (`T8`) : le diagramme §24.2

Le modèle §24.2 donne le diagramme d'état complet d'une tâche
d'onboarding, et il porte une transition que `T8` n'avait pas anticipée :
`Reopened -> Completed`, « le nouvel arrivant termine à nouveau ». `T8`
n'avait écrit `_TERMINER_LA_TACHE` que pour l'état `todo` — sans correctif,
une tâche réouverte par un `ESM`/`ADM-E`/`SUPER` restait dans une **impasse
permanente**, ni le nouvel arrivant ni personne ne pouvant plus jamais la
terminer. `_TERMINER_LA_TACHE` accepte désormais `state IN ('todo',
'reopened')`. Un témoin re-termine directement une tâche après sa
réouverture administrative, prouvant le correctif à même l'API.

`completed_at`/`completed_by_person_id` de la complétion **originale** sont
laissés tels quels par la réouverture (contrairement à `annuler_la_
completion`, qui les efface) : le corpus n'exige nulle part de les effacer,
et l'inventer aurait été §6.5. Un témoin lit directement en base que les
deux colonnes de la complétion originale et les trois colonnes de la
réouverture (`reopen_reason`, `reopened_by_person_id`, et `reopened_at` via
la réponse) coexistent.

## 2.4 Le motif — obligatoire au corps ET à la base

Matrice §8.3 : « la réouverture exige un motif ». `DemandeDeReouverture`
porte `motif: str = Field(min_length=1)`, qui refuse la chaîne vide — un
`NOT NULL` seul l'aurait laissée passer, même piège que la `CHECK` de `T1`
sur `length(btrim(NULL)) > 0`. La contrainte `motif_requis_a_la_reouverture`
(posée dès `T1`, jamais exercée avant cette sous-étape) l'impose aussi côté
base : `reopened_at IS NULL OR reopen_reason IS NOT NULL`. **C'est la
PREMIÈRE route du projet à exiger et écrire un motif** — là où
`archive_reason`/`assignment_reason` (LOT 2) restent des colonnes jamais
écrites, `ECART-064`.

## 2.5 Ce que `T9` ne fait pas, et ce n'est pas un oubli

Ni changement automatique mission/intercontrat (`T10`), ni archivage du
parcours terminé (`T11`). `ECART-066` (volet parcours) reste sans objet
pour `T9`, qui n'archive ni ne restaure aucun parcours — il devient
bloquant pour `T11` seulement. Le résidu du §8.2 nommé par `T8` (« correction
technique auditée ») reste également sans objet ici : `T9` réouvre une
tâche, elle ne la marque pas terminée à la place du nouvel arrivant.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check .` / `ruff format --check .` | 0 erreur |
| `uv run mypy` | 0 erreur, 172 fichiers Python |
| `uv run pytest apps/api/tests/test_reouverture_onboarding.py -q` | **17 nouveaux tests, tous verts** |
| `uv run pytest` (T1–T9 de l'onboarding + contrat, 158 tests) | 158/158, aucune régression |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes |
| `make migrations-check` | tête `0021` inchangée — aucune migration nécessaire |

**Zéro régression, prouvée par comparaison nommée sur la MÊME base.** Un
`git worktree` sur `origin/develop` (`b799cb0`), `.env` copié, a rendu **74
échecs environnementaux** — contre 74 sur cette branche également, et la
comparaison `comm` des deux listes triées de noms est **vide dans les deux
sens**.

`uv run pytest -q --collect-only` : **1 370** tests (1 353 → 1 370, +17) ;
`-m integration` : **991** (974 → 991, +17). `make test-frontend` :
inchangé, **282 + 111 + 225 = 618** — écriture pure, aucun module de
contrat propre.

---

# 4. Décisions, écarts et questions

| ID | Objet |
|---|---|
| `DEC-609` | `T9` livrée : réouvrir une tâche après le délai. `ESM`/`ADM-E`/`SUPER` seuls, fenêtre inverse stricte de celle de `T8`, correctif du diagramme §24.2 à `terminer_une_tache`, motif obligatoire au corps et à la base |

Aucun écart nouveau, aucune question nouvelle. `ECART-066` (volet parcours)
reste ouvert, bloquant pour `T11`, sans objet pour `T9`.

---

# 5. Ce que `T9` laisse

- `T10` — changement automatique mission ↔ intercontrat — devra écrire la
  transition `Todo -> Cancelled` (« remplacement de parcours ») et
  `Completed -> Preserved` (« tâche commune conservée ») du même diagramme
  §24.2, jamais encore exercées.
- `T11` devra écrire l'archivage automatique du parcours terminé et la
  révocation au départ, en s'accrochant à `enregistrer_un_depart` (LOT 3,
  `T9`) sans dupliquer sa logique. `ECART-066` (volet parcours) devra être
  reposé à Jonathan avant `T11` — ne pas présumer la réponse du volet
  modèle (`T6`).
- Le résidu du §8.2 (« correction technique auditée par l'administrateur ou
  le super-administrateur ») reste nommé, non instruit, non assigné par le
  découpage — voir le compte rendu de `T8`, §2.6.

---

# Validation demandée à Jonathan

Merci de valider `T9` pour fusion. Commande de fusion et de retour arrière
ci-dessous.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arriere
```
