# Compte rendu — `T1` du LOT 10 : les six tables de l'audit, des alertes, du support et du RGPD

**Sous-étape :** la première du lot — `audit_event`, `operational_alert`, `alert_comment`,
`bug_report`, `export_request` et `data_subject_request`
**Date :** 14 octobre 2026
**Décision :** `DEC-655`
**Stories :** socle — les huit stories du LOT 10 en dépendent

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faite | **`T1`** |
| Restent | `T2` à `T16` |
| Issues | épic `#267`, stories `#268` à `#275`, jalon `G10` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/audit/modeles.py` | les six tables du §21/§22.3 et les quatre énumérations (`SeveriteAlerte`, `EtatAlerte`, `EtatSignalement`, `TypeDeDemandeRGPD`) |
| `apps/api/app/audit/__init__.py` | les exports du module, même discipline que `app/imports/__init__.py` |
| `apps/api/alembic/versions/0027_audit_alertes_support_rgpd.py` | la migration, appliquée et rejouée depuis une base vide |
| `apps/api/tests/test_audit.py` | **6 tests**, structurels, aucun ne requiert PostgreSQL |
| `apps/api/tests/test_socle_modele.py` | les six tables ajoutées à `TABLES_DECLAREES` |
| `apps/api/app/modeles.py` | `audit_modeles` enregistré dans `MODULES_DE_MODELES` |
| `apps/api/app/auth/modeles.py` | une docstring stale corrigée (voir §2.4) |

Le schéma passe de **48 à 54 tables métier**, de 26 à **27 migrations**, tête `0027`, sans nouveau
déclencheur. `make migrations-check` confronte **858 colonnes**, **317 contraintes**, **257
index**, **10 déclencheurs** et **199 fonctions** : le schéma issu des migrations est identique à
celui qui tourne, et le retour à `base` ne laisse aucune table métier.

## 2.1 Quelles tables portent un `entity_id`, et pourquoi la réponse n'est pas uniforme

Contrairement au LOT 9 (quatre tables toutes locales), ce lot pose **cinq tables globales et une
seule locale** :

- `audit_event` porte un `entity_id` **nullable** — le §21.1 l'écrit explicitement (« Nullable pour
  événement global »), même motif que `onboarding_template` au LOT 7 `T1` : une clé composite y
  serait rendue inerte par `MATCH SIMPLE` dès qu'un événement global se produit ;
- `operational_alert`, `alert_comment`, `export_request` et `data_subject_request` **ne portent
  aucun `entity_id` du tout** — aucune de leurs sections du modèle n'en déclare un ;
- `bug_report` **seule** reçoit `RessourceLocale` — le §21.4 nomme explicitement sa portée
  (« Entité consultée »), sans la marquer nullable.

`make isolation-check` dérive désormais **37 tables locales, 17 globales, 29 clés composites
(inchangé), zéro référence nue**.

## 2.2 Vocabulaire fermé contre vocabulaire ouvert — mesuré champ par champ

Le modèle BACKTICKE les valeurs qu'il ferme et les écrit en prose quand il ne le fait pas — même
discipline qu'`import_row_issue.level` au LOT 9. Mesuré, pas supposé :

| Champ | Statut | Valeurs |
|---|---|---|
| `operational_alert.severity` | **fermé**, en MAJUSCULES | `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `operational_alert.state` | **fermé** | `open`, `acknowledged`, `resolved` |
| `operational_alert.source` | **ouvert** | « API, worker, security, backup, Uptime Kuma » est écrit en prose, et « Uptime Kuma » porte une espace qu'aucune valeur énumérée de ce dépôt ne tolère |
| `bug_report.state` | **fermé** | `new`, `investigating`, `fixed`, `rejected` |
| `data_subject_request.type` | **fermé par la phrase du §22.3** | `access`, `rectification`, `erasure`, `objection` |
| `data_subject_request.état` | **ouvert** | aucune section n'en donne le vocabulaire |

**Une divergence mesurée, pas résolue** : le §11.1 du cahier (ligne ~1299) écrit ailleurs « accès,
rectification, effacement et **limitation** » — un quatrième mot différent de celui du §22.3
(« opposition »). Le §22.3 est retenu ici parce qu'il décrit littéralement cette table ; la
divergence elle-même reste ouverte, à reposer à Jonathan si `T14` la rencontre.

## 2.3 Trois défauts trouvés par `make isolation-check`, corrigés avant commit

**Mesuré sur la base réellement migrée, pas sur l'état d'avant `make migrate`** — le contrôle lit
le catalogue PostgreSQL en direct, et sa première exécution (contre une base encore à `0026`)
rendait les mêmes comptes qu'avant cette sous-étape, en paraissant conforme sans avoir rien
examiné de neuf.

Une fois la migration appliquée, trois colonnes suffixées `_id` ont été refusées comme
**références nues** (aucune clé étrangère) :

- `audit_event.resource_id` — **volontairement polymorphe** (`resource_type` varie : `person`,
  `circle`, `import_batch`…), aucune clé étrangère unique ne pourrait jamais la couvrir ;
- `audit_event.correlation_id` et `bug_report.correlation_id` — un jeton de corrélation technique
  (même nom que `packages/observabilite`), jamais une référence à une ligne.

**Renommées plutôt que dispensées** : `resource_id` devient `resource_reference`,
`correlation_id` devient `correlation_token` sur les deux tables — un nom qui ne finit plus par
`_id` dit la vérité sur ce que la colonne EST, au lieu d'étendre la liste `COLONNES_D_AUTEUR` du
contrôle pour ce seul cas, ce qui aurait affaibli un contrôle qui a raison (§7.20 de la passation).

Un quatrième point, trouvé par la même mesure : `export_request.job_id` a été **retiré** plutôt que
posé nullable sans clé étrangère — `async_job` n'existe pas encore (LOT 11), et une colonne ne peut
référencer une table absente. Même régime que `import_batch.delimiter` au LOT 9 `T10` : un champ du
modèle que son lot propriétaire posera, pas ce module.

## 2.4 Une docstring stale corrigée au passage

`apps/api/app/auth/modeles.py` affirmait, depuis le LOT 3, que `audit_event` relevait du **LOT 12**
— écrit avant que la roadmap ne fixe l'ordre définitif des lots, et jamais corrigé depuis. Même
classe de divergence que celle mesurée dans `infra/scripts/verifier-recette-modele.py`
(annotations `lot=` des contrôles `§30.19`-`§30.24`, documentée dans `fiche-lot-10.md` §2.1, non
résolue ici — hors périmètre de `T1`, à vérifier à `T16`). La docstring, elle, contredisait
directement le code que ce commit ajoute : corrigée.

## 2.5 `retention_action` et les deux tables de notice RGPD ne sont pas posées

`retention_action` (§22.4), `privacy_notice_version` et `privacy_notice_acknowledgement` (§22.1,
§22.2) restent hors de cette migration : aucune des huit stories du LOT 10 ne les nomme, et les
poser sans consommateur ni règle métier validée serait inventer (§6.5 de la passation).

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make migrate` | huit services sains, tête `0027` |
| `uv run pytest -q apps/api/tests/test_audit.py` | **6/6** |
| `make migrations-check` | base vide → `0027` → schéma identique ; retour à `base` propre |
| `make isolation-check` | **37 locales, 17 globales, 29 composites (inchangé), 0 référence nue** |
| `make format-check`, `make lint`, `uv run mypy` | verts (242 fichiers) |
| collecte depuis la racine | **1 714 pytest** (+6), dont **1 282 d'intégration** |
| `uv run pytest -q` (développement) | 1 639 passés, **74 échecs environnementaux** |
| comparaison de worktree `origin/develop` (§7.22 de la passation) | 74 échecs **identiques, un par un** (listes comparées, pas seulement les comptes) — y compris `.env` copié dans le worktree, sans quoi la comparaison échouait sur une erreur d'authentification sans rapport avec une régression |
| `make residu-check` | 74 échecs environnementaux, aucun résidu laissé |
| `make sources-check` | **657** fichiers source (+3), 0 ignoré hors les 2 exceptions |
| frontend | **802 Vitest** inchangés — aucun fichier frontend touché |

**Un piège de méthode rencontré et corrigé pendant la mesure elle-même** : la première comparaison
de worktree contre `origin/develop` rendait 15 échecs et **1 259 erreurs** — pas une régression,
mais l'absence du `.env` dans le worktree (non versionné, donc non copié par `git worktree add`),
qui faisait échouer **la connexion PostgreSQL elle-même** sous un mauvais rôle. Copié depuis le
dépôt principal, la comparaison est retombée sur les 74 échecs attendus.

---

# 4. Décisions et écarts

- `DEC-655` consigne la réalisation et les choix strictement dérivés du modèle ;
- `QO-092` (destination des signalements) reste ouverte, non bloquante pour ce socle ;
- aucun nouvel écart n'est ouvert par `T1` ; `ECART-064` reste à fermer à `T7`.

---

# 5. Ce que `T1` laisse

- les six tables et la migration rejouable, prêtes pour `T2` ;
- aucune route, aucun service, aucun contrat HTTP anticipé ;
- la divergence des annotations `lot=` du §30.19-24 dans `verifier-recette-modele.py` intacte, à
  vérifier à `T16`, pas à recopier ;
- l'écriture d'audit synchrone fixée par un test structurel (`test_l_audit_reste_synchrone_aucune_
  table_async_job`).

# Validation demandée à Jonathan

`T1` est faite. Après fusion, la prochaine sous-étape est `T2` : le service d'écriture d'audit
générique, câblé sur l'authentification et les sessions (LOT 3).
