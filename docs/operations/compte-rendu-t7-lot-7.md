# Compte rendu — `T7` du LOT 7 : création d'une instance depuis la date d'arrivée

**Date :** 27 septembre 2026
**Sous-étape :** `T7` — affecter et consulter un parcours d'onboarding
**Décision :** `DEC-606`
**Story :** `MVP-L07-US004`

---

# 1. État du lot

`T1` à `T7` du LOT 7 sont désormais faites. Huit sous-étapes restent, `T8` —
compléter et annuler une tâche dans les cinq minutes — est la prochaine.
Détail du découpage : [`fiche-lot-7.md`](fiche-lot-7.md) §3.

---

# 2. Ce que la sous-étape a produit

Deux routes, matrice §8.1 : `POST .../onboarding-parcours` (« Affecter un
parcours ») et `GET .../onboarding-parcours` (« Consulter son parcours » /
« ... d'un collaborateur »), montées sous `/entities/{code}/people/
{appartenance}/`. Nouveau module `app/onboarding/instances.py`, extensions de
`app/onboarding/perimetre.py` et `app/onboarding/routes.py`. Aucune nouvelle
table : `onboarding_instance` et `onboarding_instance_task` existent depuis
`T1`, jamais encore écrites. Un module de contrat TypeScript,
`parcoursOnboarding.ts` : la lecture l'exige (règle constante depuis `T2`),
et un seul module sert les deux verbes puisque la création RENVOIE
exactement la même forme que la lecture.

## 2.1 « Le bon modèle » — une priorité que le corpus ne tranchait pas

Un nouvel arrivant porte un statut cible, un DSM et un cercle principal, tous
verrouillés dès sa fiche d'arrivée (matrice §6.2). Plusieurs modèles publiés
peuvent donc correspondre à son statut, à des niveaux différents. Recherché
dans la matrice, le modèle et le cahier : rien ne dit quel niveau prime.
Question posée à Jonathan avant tout code, sous forme fermée : **`DSM` >
`CIRCLE` > `ENTITY` > `GLOBAL`, le plus spécifique gagne.** Quatre témoins
postent les quatre modèles en même temps sur le même statut et retirent le
niveau gagnant un par un — jamais un seul modèle à la fois, ce qui ne
prouverait qu'une absence de refus, pas un ordre.

**Résiduel nommé, non instruit ici faute d'occurrence connue** : plusieurs
modèles publiés au MÊME niveau (deux modèles `ENTITY` pour `mission`, par
exemple) départagent par la publication la plus récente — aucune contrainte
du corpus n'exclut ce cas, et rien n'impose non plus un ordre différent.

## 2.2 `DSM` a ici « Consultants » plein — troisième grille du module

Piège n°1 de `fiche-lot-7.md` §2.1 : `DSM`/`BOOST` consultent le parcours
d'un collaborateur, ils n'agissent pas sur ses tâches. Sur la fiche
d'arrivée non publiée (`T2`), `DSM` était à tiret ; ici (§8.1), il porte le
même droit qu'ESM/ADM-E/SUPER à l'échelle de SES consultants. Deux témoins
le prouvent dans les deux sens : `DSM` LIT le parcours d'un consultant
rattaché, ce que `T2` lui refusait sur la fiche.

**« Affecter » N'A PAS de `Soi`, et c'est la seule asymétrie entre les deux
gestes** : `NEW` est à tiret sur cette ligne précise, contrairement à
« Consulter son parcours ». Un témoin le prouve explicitement.

## 2.3 Une seule instance active par appartenance — à l'unité ET au volume

Modèle §13.5, index partiel déjà posé par `T1`. L'écriture est un
compare-et-pose atomique, `INSERT ... ON CONFLICT (entity_membership_id)
WHERE state = 'active' DO NOTHING RETURNING` — même idiome que l'usage
unique du magic link (LOT 3, `T4`). Suivant la leçon §7.26 du LOT 6 (« une
contrainte d'unicité s'éprouve au volume, pas seulement à l'unité »), un
témoin affecte **40** parcours à 40 appartenances distinctes en boucle et
vérifie 40 instances distinctes — sans quoi une collision d'index n'aurait
pu être vue que sur un tirage malchanceux.

## 2.4 Les échéances sont calculées en base, jamais en Python

Même discipline que `recent_until` (`T3`) : `reference_date + due_offset_days
jours`, interprété à minuit UTC — le modèle §13.4 ne donne aucune heure.
Snapshot immédiat : une fois posé, `due_at` ne bouge plus même si `T6`
republie une nouvelle version du modèle.

**Un défaut de syntaxe SQL trouvé et corrigé avant tout commit** :
`:reference_date::date` — un paramètre lié directement suivi d'un cast
PostgreSQL `::` — n'est pas résolu par SQLAlchemy `text()`, qui laisse le
littéral `:reference_date::date` inchangé dans la requête envoyée au
serveur : `SyntaxError: syntax error at or near ":"`. Corrigé en
`CAST(:reference_date AS date)`, la forme sans ambiguïté.

## 2.5 Un second défaut trouvé en écrivant les tests : le mien, pas le livrable

Plusieurs tests créaient un modèle `GLOBAL` avec la session d'un ESM. Le
livrable est correct — seul `SUPER` gère `portee: GLOBAL` (règle de `T5`) —
et c'était mon décor qui l'ignorait. Corrigé en faisant créer les modèles
`GLOBAL` par `super_personne` dans tous les tests concernés, l'affectation
elle-même restant menée par l'ESM là où c'est le geste testé (§8.1 n'exige
aucune portée particulière pour « Affecter »).

## 2.6 Une ancre de test qui aurait pu devenir fausse le jour même

`ANCRAGE`, utilisée pour ouvrir les sessions de test, était d'abord fixée à
une date/heure absolue (le lendemain matin) — et s'est révélée déjà dans le
FUTUR au moment de l'exécution, l'horloge UTC réelle n'ayant pas encore
atteint minuit alors que le calendrier local l'annonçait. Le rafraîchissement
de session (`lire_et_rafraichir`) a alors refusé `last_activity_at >
created_at` — la session semblait créée dans le futur. Corrigée en dérivant
`ANCRAGE` de `now()` (`§7.47` du LOT 6) plutôt qu'en la figeant : elle reste
dans le passé quel que soit le moment où le test s'exécute.

## 2.7 Ce que `T7` ne fait pas, et ce n'est pas un oubli

Ni compléter/annuler une tâche (`T8`), ni réouverture (`T9`), ni changement
automatique mission/intercontrat (`T10`), ni archivage du parcours terminé
(`T11`). Aucun motif n'est demandé pour affecter un parcours : le §18.1 ne
l'exige pas pour ce geste. Aucune contrainte d'exclusivité « une seule
version publiée à la fois » n'est ajoutée au modèle : le corpus n'en écrit
aucune.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check .` / `ruff format --check .` | 0 erreur |
| Prettier | conforme |
| `make typecheck` (mypy strict + `tsc --noEmit`) | 0 erreur, 169 fichiers Python |
| `uv run pytest apps/api/tests/test_instances_onboarding.py -q` | **24 nouveaux tests, tous verts** |
| `uv run pytest` (T1/T5/T6/T7/contrat, 110 tests) | 110/110, aucune régression |
| Vitest `packages/contracts` | 282/282 (+12, `parcoursOnboarding.test.ts`) |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes |
| `make migrations-check` | tête `0021` inchangée — aucune migration nécessaire |

**Zéro régression, prouvée par comparaison nommée sur la MÊME base.** Un
`git worktree` sur `origin/develop` (`6d90875`), `.env` copié, a rendu **74
échecs environnementaux** — contre 74 sur cette branche également, et la
comparaison `comm` des deux listes triées de noms est **vide dans les deux
sens**.

`uv run pytest -q --collect-only` : **1 338** tests (1 314 → 1 338, +24,
tous marqués `integration`) ; `-m integration` : **959** (935 → 959, +24).
`make test-frontend` : **282 + 111 + 225 = 618** (606 → 618, +12 —
`parcoursOnboarding.test.ts`, la lecture pose son module de contrat).

---

# 4. Décisions, écarts et questions

| ID | Objet |
|---|---|
| `DEC-606` | `T7` livrée : affecter et consulter un parcours d'onboarding. Priorité de résolution du modèle DSM > CIRCLE > ENTITY > GLOBAL, arbitrage de Jonathan du 27/09/2026 |

Aucun écart nouveau, aucune question nouvelle. `ECART-066` (volet parcours)
reste ouvert, bloquant pour `T11`, sans objet pour `T7` — qui n'archive ni
ne restaure aucun parcours.

---

# 5. Ce que `T7` laisse

- La priorité DSM > CIRCLE > ENTITY > GLOBAL départage par la publication la
  plus récente en cas d'égalité de niveau — résiduel nommé, non rencontré.
- `T8` devra rendre la fenêtre de cinq minutes injectable, jamais figée
  (même discipline que l'ancre `INSTANT` du LOT 6, `§7.47`).
- `T11` devra reposer `ECART-066` pour la restauration d'un parcours, sans
  présumer que la réponse donnée pour la version de modèle (`T6`) s'y
  applique aussi.

---

# Validation demandée à Jonathan

Merci de valider `T7` pour fusion. Commande de fusion et de retour arrière
ci-dessous.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arriere
```
