# Compte rendu — `T1` du LOT 7 : les huit tables

**Sous-étape :** la **première** du lot — `arrival_profile` et les six tables d'onboarding
**Date :** 25 septembre 2026
**Décision :** `DEC-599`
**Stories :** socle — `MVP-L07-US001` à `US008` en dépendent toutes

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 7**, ouvert le 25/09/2026 (`DEC-598`), **quinze** sous-étapes |
| Faite | **`T1`** |
| Restent | `T2` à `T15` |
| Issues | épic `#175`, stories `#176` à `#183`, jalon `G7` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/onboarding/modeles.py` | les huit tables du §12.1 et §13.1 à §13.7, six énumérations |
| `apps/api/alembic/versions/0020_fiche_arrivee_et_onboarding.py` | la migration, **appliquée et rejouée à vide** |
| `apps/api/tests/test_onboarding.py` | **34 tests**, chaque refus apparié à son témoin |
| `apps/api/tests/test_isolation.py` | `COUVERTURE` étendue de douze à **dix-huit** chemins |
| `infra/scripts/verifier-isolation.py` | une **troisième** raison légitime à une clé simple, découverte et outillée |

**Le schéma passe de 32 à 39 tables**, et de 19 à 20 migrations, tête `0020`.
`photo_authorization` (LOT 5) n'est **pas** recréée : `arrival_profile.photo_media_id` s'y
raccroche par `media_asset`.

## 2.1 Pourquoi deux tables seulement portent un `entity_id` nullable

Le §13.1 et le §13.2 écrivent explicitement « `entity_id` | Nullable pour une tâche/un modèle
**GLOBAL** ». Ce sont les deux seuls endroits du corpus qui admettent l'absence d'entité :
`onboarding_task_reference` et `onboarding_template` portent donc un `entity_id` nullable, hors du
mixin `RessourceLocale`. Toutes les autres tables du lot sont locales **en substance** — une fiche,
une instance, une tâche d'instance, un événement appartiennent toujours à une entité par la chaîne
de l'appartenance — et reçoivent `RessourceLocale`, comme `content_block` l'a fait au LOT 6 pour la
même raison (§25.3 est aussi le modèle).

## 2.2 `make isolation-check` a trouvé un trou que la mesure n'avait pas anticipé, et deux fois

**Premier trou, `MATCH SIMPLE` — `T8-1` transposé.** `onboarding_template.scope_circle_id` a
d'abord reçu une clé **composite** vers `circle`, au motif qu'une contrainte structurelle garantit
`entity_id` NOT NULL dès que `scope_circle_id` l'est. Le contrôle l'a refusée quand même : il exige
`entity_id` NOT NULL à la **source**, sans condition, et ne raisonne pas sur une contrainte tierce.
Clé **simple** retenue.

**Second trou, une classe que le contrôle n'avait jamais rencontrée.** Une clé composite entre deux
tables « locales » (`onboarding_instance_task -> onboarding_task_reference`) devient **fausse** dès
que la table CIBLE a un `entity_id` légitimement nullable : une tâche GLOBALE (`entity_id IS NULL`)
ne matcherait **jamais** l'`entity_id` non nul de l'instance qui la réutilise, et la clé refuserait
silencieusement l'usage que le modèle prévoit explicitement. `infra/scripts/verifier-isolation.py`
ne connaissait que la raison « cible globale » pour une clé simple ; il connaît désormais une
**troisième** raison — le §1 de ce script, dynamiquement dérivé du modèle — rapportée, jamais
masquée. Deux clés en profitent : `onboarding_instance_task -> onboarding_task_reference` et
`onboarding_template -> circle`.

**Trois colonnes d'acteur ont dû recevoir une clé étrangère.** `published_by_person_id`,
`completed_by_person_id`, `reopened_by_person_id` ressemblaient aux trois colonnes d'auteur du
§3.1, dont l'absence de clé est un choix tracé — mais `make isolation-check` ne dispense que
**ces trois-là**, nommément, pas toute colonne qui leur ressemble. Corrigées, `person` étant globale.

## 2.3 Un témoin a trouvé un défaut NULL classique, sans avoir été écrit pour ça

`test_une_fiche_HORS_BROUILLON_SANS_presentation_est_refusee` attendait un refus et ne l'a pas eu.
La contrainte `state = 'draft' OR length(btrim(short_intro)) > 0` est **satisfaite** quand
`short_intro` est `NULL` : `length(btrim(NULL))` rend `NULL`, et une `CHECK` dont l'expression rend
`NULL` est acceptée — seul `FALSE` la refuse. Corrigée en `state = 'draft' OR (short_intro IS NOT
NULL AND length(btrim(short_intro)) > 0)`.

## 2.4 Une cinquième occurrence du paramètre lié partagé — dans mon propre test

`_tache_reference` écrivait `VALUES (:e, :c, :c)` pour `code` (`character varying(64)`) et `title`
(`text`) : « inconsistent types deduced for parameter $2 ». §7.25, rejouée une cinquième fois — cette
fois dans un test, pas dans le code livré. `make parametres-check` ne l'a pas vue : il ne lit que
`app/`, jamais `tests/`. Corrigée avec deux paramètres distincts.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make code-refresh` | conteneurs reconstruits, code identique au dépôt |
| `make migrate` puis `alembic downgrade 0019` / `upgrade head` (deux fois, après chaque correction) | `0020 (head)` |
| `make isolation-check` | **26 tables locales, 18 clés composites, 0 référence nue, 0 clé simple non justifiée** |
| `make migrations-check` | base vide → migrations → schéma **identique** à celui qui tourne ; `downgrade base` ne laisse aucune table métier |
| `make parametres-check` | 0 partage illégitime |
| `make privileges-check`, `secrets-check`, `historisation-check` | tous verts, inchangés par ce lot |
| `uv run pytest apps/api/tests/test_onboarding.py -m integration` | **28/28** |
| `uv run pytest apps/api/tests/test_isolation.py::test_les_cles_composites_sont_toutes_couvertes` | vert, 18 chemins |
| `uv run pytest` (base réelle, jeu de démo) | **74 échecs, identiques à `origin/develop`** — 0 lié au code livré |
| `make lint`, `make typecheck`, `make docs-check`, `make icloud-verify`, `make sources-check` | tous verts |

---

# 4. Décisions, écarts et questions

- `DEC-599` (détail complet dans `docs/decisions/registre-decisions.md`)
- Aucun écart ouvert par cette sous-étape. `ECART-066` reste ouvert, non touché ici — il bloque
  `T6`/`T11`, pas `T1`
- Aucune question ouverte

---

# 5. Ce que `T1` laisse

- Le socle complet des huit tables, prêt pour `T2` (fiche d'arrivée en lecture)
- `ECART-066` (restauration « Conditionnelle ») reste à trancher avant `T6`
- `ECART-013` (identifiants stables des tâches communes) est **résolu structurellement** par
  `onboarding_task_reference.code`, mais reste à éprouver **pour de vrai** à `T10`

# Validation demandée à Jonathan

`T1` est faite : les huit tables, la migration rejouable, 34 tests, zéro régression sur la base
réelle. La prochaine est `T2`, la fiche d'arrivée en lecture.

```bash
gh pr merge <n> --squash --delete-branch   # fusion de T1
gh pr close <n> --delete-branch            # retour arrière
```
