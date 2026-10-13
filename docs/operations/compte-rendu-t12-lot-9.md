# Compte rendu — LOT 9, `T12`

**Sous-étape :** `T12` — création d'une nouvelle entité depuis des modèles génériques
**Story :** `MVP-L09-US007`, `P0`, dépend des LOTS 2/6/7
**Décision :** `DEC-647`
**Date :** 13 octobre 2026

---

## 1. État du lot

`T1` à `T11` du LOT 9 sont faites et fusionnées. `T12` ferme `US007` : « Créer une nouvelle entité
depuis des modèles génériques. Aucune donnée Bordeaux n'est copiée ; rôles, contenus et onboarding
génériques sont initialisés puis configurables. »

## 2. Les deux points arbitrés

Ni le cahier (§4.1, §21), ni la matrice, ni le backlog ne précisent QUEL contenu générique poser
concrètement dans une nouvelle entité, ni si le premier administrateur doit être nommé dans le
même geste que la création. Deux questions posées à Jonathan via `AskUserQuestion`, reformulées
sans jargon, avant tout code.

### 2.1 Contenu de départ

> « Créer une nouvelle entité doit démarrer avec des « rôles, contenus et onboarding génériques…
> initialisés puis configurables », mais aucun document ne précise s'il faut concrètement POSER
> du contenu ou un modèle dans la nouvelle entité, ou si le système fonctionne déjà ainsi sans
> rien ajouter. Quelle version faut-il construire ? »

Options : (1) **Entité vierge, rien à copier** (recommandé) ; (2) contenu de démarrage réel
inventé par l'agent ; (3) autre chose.

**Réponse de Jonathan : l'option 1.** L'entité naît vierge.

### 2.2 Premier administrateur

> « Le cahier §21 dit qu'un super-administrateur peut aussi « nommer le premier administrateur de
> l'entité ». Une entité tout juste créée n'a, par construction, personne avec un rôle LOCAL tant
> que ce geste n'a pas eu lieu. Faut-il l'inclure dans cette sous-étape ? »

Options : (1) **Oui, dans le même appel** (recommandé) ; (2) non, un second geste séparé ; (3)
autre chose.

**Réponse de Jonathan : l'option 1.** Le premier administrateur est nommé dans la même transaction.

## 3. Ce que `T12` a produit

### 3.1 Pourquoi « entité vierge » satisfait le critère sans rien construire de neuf

- **Rôles** : aucune responsabilité Framework n'existe encore dans une entité neuve — exactement
  l'état de toute entité avant qu'un humain n'y affecte quiconque. « Initialisés » décrit cet état
  VIDE, pas une action de ce module.
- **Contenus** : `content_page`/`content_block` sont des ressources locales (LOT 6, `T1`) — une
  entité neuve n'en a AUCUNE, exactement comme aujourd'hui pour toute entité jamais éditée. Les
  écrans du LOT 6/8 rendent déjà ce cas (`presentation` vaut `null`, LOT 8 `T8`).
- **Onboarding** : le modèle « générique eXalt » du cahier §9.1 existe DÉJÀ structurellement —
  `onboarding_template.entity_id` est nullable pour la portée `GLOBAL` (LOT 7, `T5`), et la
  résolution `DSM > CIRCLE > ENTITY > GLOBAL` (LOT 7, `T7`) retombe déjà sur un modèle `GLOBAL` dès
  qu'aucun modèle `ENTITY` n'existe pour la nouvelle entité. Rien de nouveau à construire.
- « Aucune donnée Bordeaux n'est copiée » est donc vrai PAR CONSTRUCTION : aucun mécanisme de
  copie entre entités n'existe dans ce dépôt, et en ajouter un pour l'exclure ensuite aurait été
  une invention dans les deux sens.

### 3.2 Nouveau module `app/entities/creation.py`

`creer_une_entite` : vérifie l'existence de la personne désignée AVANT toute écriture (422
`personne_introuvable`), insère l'entité DIRECTEMENT `active` (`activated_at` posé — aucun état
`draft` intermédiaire, simplification documentée puisque le découpage ne nomme aucun geste
« activer » distinct de la création), traduit une violation d'unicité du code en 409
`code_deja_utilise`, puis nomme le premier administrateur dans la MÊME transaction
(`technical_role_assignment`, rôle `ENTITY_ADMIN`). `technical_role_assignment.person_id` ne
référence que `person` (§8.6), pas `entity_membership` : la personne désignée n'a pas besoin
d'appartenance préalable dans une entité qui vient de naître.

### 3.3 Nouvelle route `POST /entities`

Gardée par un rôle technique GLOBAL (`SUPER_ADMIN`), cahier §21 littéral : « Seul le rôle `SUPER`
peut […] créer une entité ». Protection CSRF, comme toute écriture.

### 3.4 Refactor partagé (§7.27)

`est_super_administrateur` est extrait de la branche 1 de `resoudre_les_permissions`
(`app/permissions/services.py`) — la même requête SUPER globale (`entity_id IS NULL`), reprise
sans duplication par la nouvelle garde.

### 3.5 Défaut trouvé et corrigé avant commit : cycle d'imports

Placer la nouvelle garde dans `app/permissions/dependances.py` créait un cycle :
`entities.routes -> permissions.dependances -> entities.routes` (ce dernier module importe déjà
`CODE_ENTITE_INTROUVABLE`/`MESSAGE_ENTITE_INTROUVABLE` depuis `entities.routes` pour
`exiger_un_role_dans_l_entite`). Mesuré directement par une `ImportError: cannot import name …
(most likely due to a circular import)` à la collecte des tests. Corrigé en définissant la garde
LOCALEMENT dans `app/entities/routes.py`, qui n'a besoin que de `est_super_administrateur`
(`app.permissions.services`, aucune dépendance retour).

### 3.6 Ce que `T12` ne fait jamais

Aucun contenu, aucune responsabilité Framework, aucun modèle d'onboarding n'est semé. `ECART-035`
(invitations au départ) **reste ouvert** : le geste du premier administrateur est une simple
affectation de rôle technique, pas un objet « invitation » au sens du critère de `US006` — le
découpage de la fiche prévoyait explicitement ce cas (« ferme `ECART-035` … si l'objet est posé
ici, sinon nommé explicitement non résolu »).

## 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest apps/api/tests/test_creation_entite.py` | **5/5 passants** |
| `uv run pytest` (suite complète, racine) | **1 698 collectés** (+5, tous d'intégration), **74 échecs environnementaux** — la base documentée, identique (liste de fichiers comparée) |
| `uv run pytest -m integration --collect-only` | **1 277 collectés** (+5) |
| `make isolation-check` | **35 tables locales, 29 clés composites** — inchangé |
| `make migrations-check` | tête `0026` inchangée, **aucune migration** |
| `uv run mypy` (strict) | **235 fichiers**, 0 erreur |
| `uv run ruff check` / `ruff format --check` | 0 erreur, tout formaté |
| `pnpm lint` / `pnpm format:check` | 0 erreur |
| `uv run pytest apps/api/tests/test_contrat.py` | **5/5 passants** — contrat mis à jour (`creationDUneEntite`) |
| `make sources-check` | 626 fichiers examinés, 0 ignoré hors les 2 exceptions déclarées |
| `make docs-check` | **12/12 contrôles verts** |

Aucun défaut dans le code livré hors le cycle d'imports, trouvé et corrigé avant tout commit.

## 5. Décisions et écarts

- `DEC-647` enregistrée au registre des décisions.
- `ECART-035` reste ouvert, sans changement de statut — voir §3.6.
- Aucune question ouverte nouvelle.

## 6. Ce que `T12` laisse

- `US007` est fermée. Issue `#241` à fermer manuellement à la main après fusion (`gh issue
  close`, §7.19 de `CLAUDE.md`).
- Prochaine sous-étape : `T13` — fermeture explicite de `ECART-035` (invitations au départ), un
  correctif qui relit la révocation `T9` du LOT 3.
- Ouverts et non bloquants pour `G9` : `ECART-012`, `ECART-068`, `QO-100`, `QO-121`, `QO-125`.
  `ECART-060` reste ouvert pour ses volets métier/DSM.

## Validation demandée

Pull request à fusionner vers `develop`, puis fermeture manuelle de l'issue `#241`.

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
