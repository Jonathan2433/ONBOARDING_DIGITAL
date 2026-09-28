# Compte rendu — `T12` du LOT 7 : le suivi par périmètre

**Date :** 28 septembre 2026
**Sous-étape :** `T12` — suivi par périmètre (DSM/ESM/Booster/ADM-E/SUPER)
**Décision :** `DEC-612`
**Story :** `MVP-L07-US008` — « Suivre les onboardings dans son périmètre »

---

# 1. État du lot

`T1` à `T12` du LOT 7 sont désormais faites. Trois sous-étapes restent — `T13`/`T14` (écrans),
`T15` (recette, §30, checklist `G7`) — `T13` est la prochaine. Détail du découpage :
[`fiche-lot-7.md`](fiche-lot-7.md) §3.

**`US008` est la story que `T12` fait avancer, mais ne ferme PAS.** Mesuré sur l'issue GitHub
elle-même (`#183`, `MVP-L07-US008`), pas présumé : son corps liste explicitement trois
contributeurs — « `T11` — archivage automatique … », « `T12` — suivi par périmètre », « `T14` —
l'écran d'administration » — et sa clause de fermeture exige de cocher le critère avec ses preuves,
ce qui n'a de sens qu'une fois les trois livrées. Son critère d'acceptation — « ESM, DSM et Booster
voient uniquement leur périmètre ; les onboardings terminés sont archivés et consultables selon
droits » — se décompose en deux parts : la seconde (« consultables selon droits ») était déjà tenue
par `lire_le_parcours` (`T7`, `T11` pour l'archivage) ; la première (le périmètre, côté API) est
livrée par `T12` ; le mot « voient » suggère un écran, que seul `T14` apportera. **`#183` reste donc
ouverte après `T12`**, et se refermera à `T14`.

---

# 2. Ce que la sous-étape a produit

**Aucune nouvelle table, aucune nouvelle colonne, aucune migration.** Nouveau module,
`app/onboarding/suivi.py`, une seule route : `GET .../entities/{code}/onboarding-suivi/taches-en-retard`.

Matrice §8.1, ligne « Consulter les tâches en retard » : `NEW` Soi, `DSM` Consultants, `ESM`
Entité, `BOOST` Cercle, `OFFICE` —, `ADM-E` Entité, `SUPER` Global. **C'était la dernière ligne de
consultation du §8.1 sans consommateur après `T11`** : les deux autres — « Consulter le parcours
d'un collaborateur » (`T7`) et l'archivage/la restauration (`T11`) — étaient déjà servies. `T12`
n'écrit donc aucune deuxième route de consultation : il ajoute le REPORTING, littéralement la seule
chose que le §8.1 nommait encore sans réponse.

## 2.1 Aucun rôle n'est refusé — la portée dégrade toujours vers `Soi`

`resoudre_le_perimetre_du_suivi` (`app/onboarding/perimetre.py`) transforme un ensemble de rôles en
une portée parmi quatre — `Entité` (si `roles & _ROLES_ENTITE`, donc ESM/ADM-E/SUPER), `Consultants`
(`DSM`), `Cercle` (`BOOSTER`), ou `Soi` en dernier recours. C'est une fonction **pure**, testable
sans base — même discipline que `peut_creer_une_tache_de_reference_globale` (`T4`) et
`peut_restaurer_une_version_de_modele` (`T6`).

**`Soi` n'est jamais une conséquence du rôle `OFFICE`, qui est à tiret sur cette ligne comme partout
ailleurs sur les modèles d'onboarding** (`fiche-lot-7.md` §2.1, piège n°2). C'est le plancher
universel de n'importe quel appelant authentifié sur SES PROPRES tâches — exactement le même
principe que `peut_lire_le_parcours_onboarding`/`peut_agir_sur_sa_tache_onboarding` (`T7`/`T8`),
qui vérifient l'identité de l'acteur AVANT tout rôle, jamais après. Cette fonction ne résout donc
jamais un refus : contrairement à `peut_affecter_un_parcours_onboarding` (qui rend `bool`, avec un
`False` possible), `resoudre_le_perimetre_du_suivi` rend toujours une portée exploitable. La route
n'a donc que deux codes de refus possibles — `401` (aucune session) et `422` (paramètres de
pagination invalides) — jamais un `403` de périmètre, à la différence de toutes les autres routes
du module.

`app/onboarding/suivi.py` traduit la portée résolue en clause SQL — jamais l'inverse, et jamais de
logique de rôle dans ce module : la séparation déjà établie entre « qui peut » (`perimetre.py`) et
« comment on lit » (`instances.py`, `taches.py`) est reconduite à l'identique.

## 2.2 « En retard » n'est pas restreint aux tâches obligatoires, mais seules les instances `active` comptent

Une tâche est « en retard » si `state IN ('todo', 'reopened')` et `due_at < instant`, sur TOUTE
tâche — le §8.1 ne restreint pas cette ligne aux tâches obligatoires, à la différence de « Archiver
un parcours terminé » (`T11`), qui lui ne regarde que celles-là.

**Seules les instances `active` sont comptées, et c'est délibéré, pas un oubli.** Une instance
`archived` a déjà vu toutes ses tâches obligatoires terminées (`T11`) ; une tâche NON obligatoire
encore `todo`, en retard, laissée sur une instance désormais archivée, est un résidu que rien dans
le corpus ne demande de signaler — l'omettre est la lecture qui n'invente rien (§6.5 de
`CLAUDE.md`). Une instance `replaced` (`T10`) est un parcours qu'un changement de statut a rendu
inerte : ses tâches ne sont l'affaire de personne.

**Un témoin construit ce cas précis plutôt que de l'affirmer**
(`test_tache_optionnelle_sur_instance_archivee_est_exclue`) : un consultant reçoit un modèle à deux
tâches, l'une rendue optionnelle par une écriture SQL directe après affectation, son échéance
forcée dans le passé ; l'autre, restée seule obligatoire, est complétée par le geste RÉEL de
complétion (`POST .../completion`), ce qui déclenche l'archivage automatique de `T11` dans le même
mouvement. L'instance est vérifiée `archived` en base, puis le suivi de l'ESM est interrogé : la
tâche optionnelle en retard n'y figure pas. Sans ce témoin, un filtre `oi.state = 'active'` qui ne
filtrerait rien passerait aussi bien.

## 2.3 Pagination réutilisée, première consommation par l'onboarding

`app/shared/pagination.py` (LOT 6, `T3`) fournit `TailleDePage`/`TAILLE_PAR_DEFAUT`/`TAILLES_DE_PAGE` —
les trois tailles du cahier §18.2, jamais redéclarées. Même discipline que
`lister_le_trombinoscope` (LOT 5, `T2`) : deux requêtes, le total et la page dans la MÊME
transaction, aucune boucle par ligne, un ordre TOTAL (`due_at` puis `id`, clé primaire en dernier
recours).

## 2.4 Contrat mis à jour

`packages/contracts/src/contrat-api.json` déclare `suiviDesTachesEnRetard`, forme
`PageDeSuiviOnboarding`. **Aucun module TypeScript propre n'est créé** — même parti que
`CatalogueDeTaches` (`T4`) : un nom de forme dans le manifeste n'exige un validateur TypeScript que
lorsqu'un écran le consomme réellement, ce que ni `T4` ni `T12` ne font. `parcoursOnboarding.ts`
(`T7`) reste la seule forme d'onboarding validée côté frontend, parce que `T7` avait un consommateur
immédiat que `T12` n'a pas encore.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check .` / `ruff format --check .` | 0 erreur, dépôt entier |
| `uv run mypy` | 0 erreur, 176 fichiers Python |
| `uv run pytest apps/api/tests/test_suivi_onboarding.py -q` | **11 tests, tous verts** |
| `uv run pytest -k onboarding -q` (depuis `apps/api/`) | **153 tests, tous verts** |
| `make migrations-check` | tête `0021` inchangée — aucune migration nécessaire |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes, 12 contrôles de totaux |
| `make sources-check` / `make parametres-check` | OK — le nouveau module `suivi.py` est bien suivi par git |
| `pnpm run typecheck` / `pnpm run lint` / `pnpm run format:check` | OK, `packages/contracts` inclus |
| `make test-frontend` | inchangé, **282 + 111 + 225 = 618** — aucun écran, aucune modification frontend |

## 3.1 Zéro régression, et une erreur de méthode trouvée et corrigée dans la preuve elle-même

**Premier passage, depuis `apps/api/` : 1 326 tests contre les 1 393 que `DEC-611` avait dérivés et
que `CLAUDE.md` annonçait.** Écart de 78 tests qui n'a rien à voir avec `T12`. Diagnostiqué avant de
conclure à une régression (§7.18 de `CLAUDE.md`) : `pyproject.toml`, à la racine du dépôt, déclare
`testpaths = ["apps/api/tests", "apps/worker/tests", "packages/observabilite/tests"]`. Un `pytest`
lancé depuis `apps/api/` ne voit donc que le premier des trois — **et `make check`/`make test`
invoquent `pytest` DEPUIS LA RACINE**, le `Makefile` y tournant lui-même (`cd` jamais fait). C'est
le §7.28 de `CLAUDE.md` (« lis ce que la cible fait, pas ce que son nom suggère ») transposé au
**répertoire de travail** de la commande plutôt qu'à son nom.

**Comparaison refaite depuis la racine, seule invocation qui reproduit celle de `make check` :** un
`git worktree` sur `origin/develop` (`2bbdb1b`, tête après fusion de `T11`), `.env` copié,
`uv sync --frozen`, `pytest` bare (sans filtre `-m integration`) lancé depuis la racine du worktree.

| | `origin/develop` | branche `T12` |
|---|---:|---:|
| `pytest -q --collect-only` | **1 393** | **1 404** (+11) |
| `pytest -m integration -q --collect-only` | 1 014 | **1 025** (+11) |
| échecs (`pytest -q`) | 75 | 75 |

Les deux listes triées de noms de tests en échec sont **identiques**, comparées par `diff` : aucune
régression, et le delta de +11 correspond exactement aux tests de `T12`.

**Un second défaut trouvé et corrigé dans mes propres tests, avant toute fusion.** Les 11 tests de
`test_suivi_onboarding.py` avaient d'abord été écrits sans `@pytest.mark.integration` — visible en
comparant `pytest -m integration -q --collect-only` avant/après l'ajout du fichier (1 014 dans les
deux cas, alors que les 11 tests exigent PostgreSQL via `parametres_de_la_stack`). Sans ce marqueur,
`make test-integration` et la porte d'intégration continue ne les auraient jamais exécutés,
silencieusement — le même défaut de fond que celui documenté au §7.36 de `CLAUDE.md` (« un contrôle
vert n'atteste pas que ton code est dans le commit »), transposé au marquage d'un test plutôt qu'à
son suivi par git. Corrigé en ajoutant le décorateur aux 11 fonctions ; `-m integration` passe alors
de 1 014 à **1 025**, comme attendu.

---

# 4. Décisions, écarts et questions

| ID | Objet |
|---|---|
| `DEC-612` | `T12` livrée : le suivi par périmètre, `US008`. Aucun rôle refusé, `Soi` en dernier recours. Seules les instances `active` comptées, délibérément. Erreur de méthode dans la preuve de zéro régression trouvée et corrigée — `pytest` doit être invoqué depuis la racine. Défaut de marquage `@pytest.mark.integration` trouvé et corrigé dans mes propres tests |

Aucun écart nouveau, aucune question nouvelle. `ECART-012` (report à Léa) et `QO-121` (LOT 6)
restent ouvertes, sans rapport avec `T12`.

**`#183` (`US008`) reste OUVERTE après `T12`**, comme son propre corps le prévoit — `T14` (l'écran
d'administration) est le dernier de ses trois contributeurs nommés. Aucune issue à fermer à la main
pour cette sous-étape.

Aucune erreur de process cette fois : la branche `feature/lot7-t12-suivi-par-perimetre` a été créée
depuis `develop` à jour (après la fusion de `T11`, PR `#196`), jamais empilée sur un travail non
fusionné.

---

# 5. Ce que `T12` laisse

- `T13` — les écrans du nouvel arrivant (fiche d'arrivée, parcours, tâches) — est la prochaine. Un
  aller-retour réel avant de déclarer un client terminé (§7.43 du LOT 6) : les écrans écrivent
  (compléter, annuler).
- `T14` (écrans d'administration, dont le suivi par périmètre à l'écran) consommera
  `suiviDesTachesEnRetard` : c'est à ce moment-là, s'il en a besoin, qu'un module TypeScript propre
  sera créé pour la forme `PageDeSuiviOnboarding` — jamais avant qu'un consommateur n'existe (§2.4).
- La leçon générale sur l'invocation de `pytest` (§3.1) est désormais consignée au §9.2 point 18 de
  `CLAUDE.md` : tout `git worktree` de comparaison future doit lancer `pytest` depuis sa racine.

---

# Validation demandée à Jonathan

Merci de valider `T12` pour fusion. Commande de fusion et de retour arrière ci-dessous.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arriere
```
