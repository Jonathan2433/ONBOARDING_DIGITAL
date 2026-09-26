# Compte rendu — `T2` du LOT 7 : la fiche d'arrivée en lecture

**Sous-étape :** la deuxième du lot — `GET …/people/{appartenance}/arrival-profile`
**Date :** 25 septembre 2026
**Décision :** `DEC-600`
**Stories :** `MVP-L07-US001` (1/2)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 7**, ouvert le 25/09/2026 (`DEC-598`), **quinze** sous-étapes |
| Faites | `T1`, **`T2`** |
| Restent | `T3` à `T15` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/onboarding/fiche_arrivee.py` | le service de lecture, `lire_la_fiche_arrivee` |
| `apps/api/app/onboarding/perimetre.py` | qui peut lire — matrice §7 |
| `apps/api/app/onboarding/routes.py` | `GET …/people/{appartenance}/arrival-profile` |
| `packages/contracts/src/ficheArrivee.ts` | le contrat TypeScript, la lecture pose son module |
| `apps/api/tests/test_fiche_arrivee.py` | **11 tests d'intégration**, à travers le routeur réel |
| `packages/contracts/src/ficheArrivee.test.ts` | **9 tests** du validateur |

**1 821 tests** au total désormais (+20 sur `T1`) : 1 226 pytest (847 d'intégration), 595 Vitest.

## 2.1 Les données organisationnelles sont réutilisées, jamais recalculées

`lire_la_fiche` (LOT 5, `app/people/profil.py`) résout déjà métier, statut, client, DSM et cercle
principal par cinq `LEFT JOIN` sûrs — quatre contraintes d'exclusion le garantissent. `T2` l'appelle
avec une **population plus large** — `ETATS_OCCUPANTS` (future et active) et les trois visibilités,
au lieu du seul `active`/`published` — exactement le paramètre que `T8` du LOT 5 avait déjà ouvert
pour `lire_la_fiche_archivee`. **Une troisième population, pas une troisième requête.**

Aucune photo n'est servie : `resoudre_la_miniature` (LOT 5) est bornée à la population du
trombinoscope par une égalité, pas un `= ANY(...)`. L'étendre sans besoin écrit aurait été une
invention (§6.5) — à réexaminer quand un écran en aura réellement besoin.

## 2.2 Le périmètre de lecture, et son piège mesuré

La matrice §7 donne, sur « Consulter sa fiche non publiée » et « Consulter les informations
préremplies » : `NEW`=Soi, `DSM`=tiret, `ESM`/`ADM-E`=Entité, `BOOST`=Cercle, `SUPER`=Global.
**`DSM` est à tiret ici, alors qu'il porte « Consultants » ailleurs dans la même annexe** — §8.1,
« Modifier les informations organisationnelles ». Le témoin central du fichier de tests construit un
DSM **réellement rattaché** au nouvel arrivant par `dsm_assignment`, et vérifie qu'il reçoit quand
même un 403 : un DSM sans rattachement aurait prouvé « DSM refuse un inconnu », pas « DSM refuse le
sien ».

## 2.3 Un défaut découvert en construisant le décor de test : les rôles exigent une appartenance PROPRE

`resoudre_les_permissions` (LOT 4) n'accorde un rôle de responsabilité que dans l'**entité
principale** de l'acteur — `est_principale` compare l'entité consultée à celle de la PROPRE
appartenance de l'acteur, jamais à l'entité de la responsabilité seule. Un ESM ou un Booster de test
**sans sa propre appartenance dans l'entité** ne reçoit donc **aucun** rôle, quelle que soit sa
responsabilité réelle — mesuré en voyant `test_un_ESM_lit_la_fiche_d_un_AUTRE` échouer en 403 alors
que la responsabilité ESM existait bien en base. Corrigé en donnant à chaque acteur de test sa
propre appartenance. Ce n'est pas un défaut du LOT 7 : c'est une règle du LOT 4 que ce lot n'avait
encore jamais exercée avec un acteur sans appartenance locale.

## 2.4 Aucune ligne n'est créée par une lecture

`id` et `version` valent `null` tant qu'aucune ligne `arrival_profile` n'existe : `T3` la crée,
jamais `T2`. Un test vérifie les deux faits — la réponse porte des `null`, et la table reste vide
après l'appel.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest apps/api/tests/test_fiche_arrivee.py -m integration` | **11/11** |
| `uv run pytest apps/api/tests/test_contrat.py` | vert — chemin déclaré au manifeste |
| `pnpm --filter @onboarding/contracts run test` | **259/259** (+9) |
| `make test-frontend` | 595/595, tous paquets |
| `uv run pytest` (base réelle) | 74 échecs, **identiques** à `origin/develop` |
| `make lint`, `make typecheck`, `make parametres-check`, `make docs-check`, `make icloud-verify`, `make sources-check`, `make audit` | tous verts |

---

# 4. Décisions, écarts et questions

- `DEC-600` (détail dans `docs/decisions/registre-decisions.md`)
- Aucun écart ouvert par cette sous-étape

---

# 5. Ce que `T2` laisse

- La lecture complète ; `T3` écrit — validation et publication
- Aucune photo servie : résiduel nommé, à réexaminer quand un écran en aura besoin
- `ECART-066` reste ouvert, non touché ici, à trancher avant `T6`/`T11`

# Validation demandée à Jonathan

`T2` est faite : la fiche d'arrivée se lit, son périmètre est prouvé y compris le piège du DSM
rattaché, et rien n'est écrit par erreur. La prochaine est `T3`.

```bash
gh pr merge <n> --squash --delete-branch   # fusion de T2
gh pr close <n> --delete-branch            # retour arrière
```
