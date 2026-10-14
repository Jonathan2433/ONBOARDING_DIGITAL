# Compte rendu — LOT 9, `T13`

**Sous-étape :** `T13` — correctif : fermeture explicite de `ECART-035` (invitations au départ)
**Référence :** `docs/operations/fiche-lot-9.md` ligne du découpage `T13` — « revue de la révocation
`T9` du LOT 3 »
**Décision :** `DEC-648`
**Date :** 13 octobre 2026

---

## 1. État du lot

`T1` à `T12` du LOT 9 sont faites et fusionnées. `T13` est un **correctif**, pas une nouvelle
fonctionnalité : son objet, selon le découpage validé, est de relire la révocation posée par `T9`
du LOT 3 et de fermer explicitement `ECART-035`.

## 2. Ce que `ECART-035` demandait

Le backlog (`MVP-L03-US006`) exige que l'archivage d'un collaborateur invalide « sessions,
**invitations** et futurs magic links » dans la même action métier. `invitation` n'a jamais existé
comme objet de données — 0 occurrence dans le modèle et dans la matrice — et l'écart, ouvert le
22 août 2026 en construisant `T9` du LOT 3, recommandait explicitement de **ne pas inventer** une
table pour un objet que rien ne définissait, et de reprendre la question au LOT 9, « où le
back-office créera les invitations ».

## 3. Le point arbitré

En relisant les seize sous-étapes validées du LOT 9 (`DEC-635`) une par une, aucune ne pose d'objet
« invitation » :

- `T1` à `T11` ne touchent ni aux comptes ni à l'authentification ;
- `T12` (création d'une entité) nomme un premier administrateur par une simple affectation de rôle
  technique (`technical_role_assignment`, `ENTITY_ADMIN`) — jamais un objet de ce nom ;
- `T14` à `T16` sont des écrans back-office et des contrôles de pile, pas un nouveau modèle de
  données.

Le jour conditionnel que la recommandation visait — « le jour où l'objet existera » — n'arrive donc
jamais dans ce lot. Deux chemins restaient possibles : construire quand même un mécanisme minimal
d'invitation (en inventant un champ, un cycle de vie, une route — rien de tout cela n'étant décidé
par le corpus), ou fermer l'écart par constat. Posé à Jonathan via `AskUserQuestion`, reformulé sans
jargon, **avant toute action** :

> « ECART-035 dit : une fois que le back-office aura créé les invitations (prévu pour le LOT 9), la
> révocation au départ devra invalider ces invitations aussi. Mais en relisant les seize sous-étapes
> validées du LOT 9, aucune ne crée réellement d'objet « invitation ». Comment veux-tu que je ferme
> `T13` ? »

Options : (1) **Fermer l'écart par constat** (recommandé) — documenter que le LOT 9 ne crée aucun
objet « invitation », rien de nouveau à invalider, aucun code nouveau ; (2) construire un mécanisme
minimal d'invitation, au risque d'inventer une règle métier non décidée (§6.5).

**Réponse de Jonathan : l'option 1.** Fermeture par constat, zéro code nouveau.

## 4. Ce que `T13` a produit

### 4.1 La fermeture est falsifiable, pas seulement affirmée en prose

Une fermeture par constat qui ne serait qu'une phrase dans un registre ne se distinguerait pas d'une
simple promesse (§7.32 : « exige que la base continue de l'interdire »). Un nouveau test,
`test_AUCUNE_TABLE_INVITATION_N_EXISTE_A_INVALIDER` (`apps/api/tests/test_revocation.py`),
interroge `information_schema.tables` et exige qu'aucune table ne porte un nom contenant
« invitation ». Il est dérivé du catalogue réel, jamais d'une liste écrite à la main (§7.27) :
aucune maintenance requise à mesure que le schéma évolue.

**Témoin exécuté dans les deux sens**, avant de faire confiance au contrôle (§7.25) :

```text
# avec une table `invitation_witness_temoin` créée manuellement :
AssertionError: assert ['invitation_witness_temoin'] == []

# la table supprimée :
1 passed
```

Le test échouera donc le jour où un lot futur pose réellement un objet « invitation » sans
l'invalider au départ — et nommera, dans son propre message, qu'il faut relire
`app.people.services._appliquer` pour y ajouter la ligne de révocation que l'écart promettait.

### 4.2 Le module de révocation porte la fermeture en tête

Le docstring de `apps/api/app/people/services.py` (révocation `T9` du LOT 3) documentait déjà
`ECART-035` comme un point ouvert ; il est mis à jour pour dire explicitement la fermeture, nommer
`DEC-648` et le test qui la rend falsifiable — la même discipline que toutes les autres sous-étapes
de ce lot, qui documentent au plus près du code la décision qui le justifie.

### 4.3 Ce que `T13` ne fait jamais

Aucune table, aucune colonne, aucune route, aucune migration. Aucun mécanisme d'invitation n'est
inventé. Le module `_appliquer` reste exactement celui écrit par `T9` du LOT 3.

## 5. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest apps/api/tests/test_revocation.py` | **18/18 passants** (+1 depuis `T12`) |
| Témoin positif : table `invitation_witness_temoin` créée manuellement | le nouveau test **échoue**, nommant la table |
| Témoin négatif : la même table supprimée | le nouveau test **repasse au vert** |
| `uv run pytest` (suite complète, racine) | **1 699 collectés** (+1, intégration), **74 échecs environnementaux** — base identique, aucun nouveau |
| `uv run mypy` (strict) | 0 erreur |
| `uv run ruff check` / `ruff format --check` | 0 erreur, tout formaté |
| `pnpm lint` / `pnpm format:check` | 0 erreur |
| `make isolation-check` | **35 tables locales, 29 clés composites** — inchangé |
| `make migrations-check` | tête de chaîne inchangée, **aucune migration** |
| `make sources-check` | 627 fichiers examinés, 0 ignoré hors les 2 exceptions déclarées |
| `make docs-check` | **12/12 contrôles verts** |

Aucun défaut trouvé dans ce correctif : c'est la nature même de la sous-étape — relire, constater,
fermer — qui limite sa surface d'erreur possible.

## 6. Décisions et écarts

- `DEC-648` enregistrée au registre des décisions.
- `ECART-035` **CLOS** le 13/10/2026, par constat.
- Aucune question ouverte nouvelle.

## 7. Ce que `T13` laisse

- `ECART-035` est fermé. Aucune issue GitHub ne lui était propre (il n'appartenait à aucune story du
  LOT 9) : rien à fermer côté GitHub pour cette sous-étape.
- Prochaine sous-étape : `T14` — les écrans back-office (navigation
  Organisation/Onboarding/Contenu/Données/Pilotage/Configuration/Super-administration, tableau de
  bord, écrans CRUD, import) ; premier et seul écran du lot.
- Ouverts et non bloquants pour `G9` : `ECART-012`, `ECART-068`, `QO-100`, `QO-121`, `QO-125`.
  `ECART-060` reste ouvert pour ses volets métier/DSM.

## Validation demandée

Pull request à fusionner vers `develop`.

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
