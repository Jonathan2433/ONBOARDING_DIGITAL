# Compte rendu — `T6` du LOT 7 : cycle de vie d'un modèle

**Date :** 26 septembre 2026
**Sous-étape :** `T6` — publier, archiver, restaurer une version
**Décision :** `DEC-605`
**Story :** `US003` (2/2)

---

# 1. État du lot

`T1` à `T6` du LOT 7 sont désormais faites. Neuf sous-étapes restent, `T7` —
création d'une instance depuis la date d'arrivée — est la prochaine. Détail
du découpage : [`fiche-lot-7.md`](fiche-lot-7.md) §3.

---

# 2. Ce que la sous-étape a produit

Trois routes, les trois dernières lignes du §9 : publier une version
(`draft` → `published`), l'archiver (`published` → `retired`), la restaurer
(`retired` → `published`). Nouveau fichier : `app/onboarding/cycle_de_vie.py`
(service), extensions de `app/onboarding/perimetre.py` et
`app/onboarding/routes.py`. Aucune nouvelle table, aucune nouvelle colonne :
le modèle §13.3 déclarait déjà tout ce qu'il fallait. Aucun module de
contrat TypeScript : trois écritures pures, même règle que `T3`/`T4`/`T5`.

## 2.1 `ECART-066` posé et résolu AVANT d'écrire la route de restauration

Conformément à la recommandation du registre des écarts, la question a été
posée à Jonathan sous forme fermée avant tout code : l'ESM restaure-t-il
librement dans son entité, comme pour les cinq ressources d'`ARB-DROIT-003`,
ou la restauration reste-t-elle à `ADM-E`/`SUPER` seuls ? **Réponse :
l'ESM restaure librement, même régime que les cinq autres ressources.**

**Ce volet de l'écart est résolu ; l'autre ne l'est pas.** `ECART-066`
couvre DEUX ressources — une version de modèle (§9) et un parcours archivé
(§8.1) — et la question posée ne portait QUE sur la première. Présumer que
la même réponse vaut pour le parcours sans la reposer serait exactement
l'erreur que l'écart lui-même met en garde contre : les deux objets ne sont
pas de même nature (un modèle est structurant et durable, un parcours est
nominatif et temporaire). **`T11` devra reposer la question pour le
parcours.**

## 2.2 La seule ligne du §9 où DSM et Booster sont exclus EN BLOC

Publier et archiver réutilisent `peut_gerer_un_modele_de_cette_portee` telle
quelle — même grille que la création (`T5`) : DSM/Booster agissent sur LEUR
PROPRE modèle, ESM/ADM-E sur l'entité, SUPER sur le global. **« Restaurer une
version » est différente** : la matrice met DSM et Booster à TIRET sans
sous-cas — jamais « son propre modèle » comme ailleurs. `peut_restaurer_une_
version_de_modele` (nouvelle fonction) l'encode directement, et la garde de
route est SÉPARÉE (`garde_de_restauration`), pas seulement le permis fin :
DSM/Booster sont donc refusés dès la garde générique, avant même la
résolution de portée.

Deux témoins d'asymétrie le prouvent : un DSM (ou un Booster) publie et
archive SON PROPRE modèle sans difficulté, puis est refusé sur SA PROPRE
restauration — pendant qu'un ESM restaure ce même modèle sans problème.

## 2.3 Le choix le plus important de la sous-étape : la restauration ne rouvre pas l'édition

Contrairement à `restaurer_une_page` (LOT 6, qui ramène une page archivée en
`draft`), restaurer une version de modèle la ramène en `published` — **jamais
en `draft`**. Le modèle §13.3 est sans équivoque : « Chaque publication crée
une version IMMUABLE », sans exception de cycle de vie. `T5` a déjà codé
cette garantie comme PERMANENTE (`definir_les_taches_de_la_version` refuse
dès que `state != 'draft'`, publiée OU retirée). Faire revenir une version en
`draft` après restauration rouvrirait cette même garde — une version qui a
déjà servi à instancier de vrais parcours redeviendrait modifiable.

**Le témoin est direct, pas seulement une valeur de `state` observée** :
après un cycle publier → archiver → restaurer, `PUT .../tasks` refuse
TOUJOURS avec `409 version_de_modele_immuable` — exactement comme sur une
version fraîchement publiée. Si la restauration rendait `draft`, ce même
appel réussirait.

`published_at`/`published_by_person_id` D'ORIGINE sont conservés, jamais
réécrits : la version a été publiée ce jour-là, restaurer n'est pas
republier — même discipline que `restaurer_une_page` pour `publiee_le`.

## 2.4 Ce que le modèle ne déclare pas, et que ce module n'invente donc pas

`onboarding_template_version` ne porte ni `archived_at`/`retired_at` ni
`archived_by_person_id`/`restored_by_person_id` — à la différence de
`content_page` (LOT 6), qui les porte. Aucun motif n'est demandé non plus :
le §18.1 n'énumère pas « archiver un modèle d'onboarding » parmi ses cinq
cas obligatoires — même raisonnement qu'`ECART-064`. Rien de tout cela n'est
inventé au-delà de ce que le modèle §13.3 déclare (§6.5).

## 2.5 La précondition d'état est dans le `WHERE`, pas dans une lecture préalable

À la différence de `definir_les_taches_de_la_version` (`T5`, qui lit puis
écrit en deux temps), chaque transition ici porte sa précondition dans le
MÊME `UPDATE` — `WHERE id = :version AND state = :etat_attendu` — et vérifie
qu'une ligne a bien été rendue. Aucune ligne rendue est toujours un `409
transition_de_version_invalide`, que la cause soit un état de départ erroné
ou une course entre deux acteurs : plus sûr que le motif ne l'exigeait pour
un contrôle (§7.0 sixième proposition), appliqué ici à une écriture.

## 2.6 Ce que `T6` ne fait pas, et ce n'est pas un oubli

Ni la restauration d'un parcours (§8.1, `T11`, second volet d'`ECART-066`),
ni « Consulter les modèles publiés », ni « Prévisualiser » (les deux
arrivent avec les écrans, `T13`/`T14`). Aucune contrainte d'exclusivité
« un seul `published` à la fois » n'est ajoutée : le corpus n'en écrit
aucune, et plusieurs versions d'un même modèle peuvent coexister dans des
états différents.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check .` | 0 erreur |
| `uv run ruff format --check .` | conforme |
| `make typecheck` (mypy strict + `tsc --noEmit`) | 0 erreur, 167 fichiers Python |
| `uv run pytest apps/api/tests/test_cycle_de_vie_des_modeles.py -q` | **18 nouveaux tests, tous verts au premier essai** |
| `uv run pytest apps/api/tests/test_modeles_onboarding.py apps/api/tests/test_onboarding.py apps/api/tests/test_contrat.py -q` | 68/68 — aucune régression sur `T1`/`T5`, manifeste à jour |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes |
| `make migrations-check` | tête `0021` inchangée — aucune migration nécessaire, schéma identique à celui qui tourne |

**Zéro régression, prouvée par comparaison nommée sur la MÊME base.** Un
`git worktree` sur `origin/develop` (`e91d69e`), `.env` copié, a rendu **74
échecs environnementaux** (pollution du jeu de démo, `CLAUDE.md` §11) —
contre 74 sur cette branche également, et la comparaison `comm` des deux
listes triées de noms est **vide dans les deux sens** : aucun nouvel échec,
aucun échec disparu.

`uv run pytest -q --collect-only` : **1 314** tests (1 296 → 1 314, +18,
tous marqués `integration`) ; `-m integration` : **935** (917 → 935, +18).
`make test-frontend` : inchangé, **270 + 111 + 225 = 606** — aucun module
de contrat pour trois écritures pures.

---

# 4. Décisions, écarts et questions

| ID | Objet |
|---|---|
| `DEC-605` | `T6` livrée : le cycle de vie d'une version de modèle — publier, archiver, restaurer. `ECART-066` (volet version de modèle) résolu : l'ESM restaure librement dans son entité |

**`ECART-066` partiellement clos** — voir §2.1. Son volet « parcours
archivé » reste ouvert, à reposer explicitement avant `T11`. Aucun autre
écart nouveau, aucune question nouvelle.

---

# 5. Ce que `T6` laisse

- La restauration d'un parcours d'onboarding (§8.1) reste à trancher pour
  `T11` — même écart, second volet, question à reposer plutôt qu'à présumer
  résolue.
- Aucun modèle réel n'est encore publié par cette sous-étape en dehors des
  décors de test : `T10` (`US007`) reste celle qui décide quels modèles sont
  réellement utilisés en production.
- Les deux tables `onboarding_instance`/`onboarding_instance_task` restent
  intouchées : `T7` les instanciera depuis une version publiée.

---

# Validation demandée à Jonathan

Merci de valider `T6` pour fusion. Commande de fusion et de retour arrière
ci-dessous.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arriere
```
