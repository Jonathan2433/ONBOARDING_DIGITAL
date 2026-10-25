# Compte rendu — `T9` du LOT 10 : l'export CSV de l'audit

**Sous-étape :** la neuvième du lot — export CSV de l'audit, réservé à `ADM-E`/`SUPER`,
lui-même audité
**Date :** 21 octobre 2026
**Décision :** `DEC-663`
**Story :** `MVP-L10-US004`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, `T8`, **`T9`** |
| Restent | `T10` à `T16` |
| Issues | épic `#267`, story `#271` |

---

# 2. Ce que le corpus décidait déjà, et ce qu'il restait à faire

Contrairement à `T8`, cette sous-étape n'a exigé **aucun arbitrage** de Jonathan : chaque
question qu'un lecteur aurait pu poser est réglée par une comparaison directe de sources, jamais
par une invention.

**Le mécanisme (synchrone, sans dépôt MinIO) est dicté par le schéma lui-même.** `ExportRequest`
(`app/audit/modeles.py`, posé par `T1`) porte dans son PROPRE docstring : « `T9` sert cet export de
manière SYNCHRONE ». Et le backlog V1 (`V1-L04-US002` : « Demander un export CSV ou PDF
ASYNCHRONE. Le WORKER génère le fichier ; permissions revalidées ; expiration et téléchargement
sécurisé ») est la contrepartie explicite, hors périmètre (`async_job` n'existe pas, LOT 11). Les
colonnes `generated_media_id`/`expires_at` d'`export_request` restent donc `NULL` : réservées à
cette V1 future, jamais écrites avant qu'elle n'existe. Le CSV est rendu DIRECTEMENT dans la
réponse HTTP.

**La garde est la quatrième ligne du §16, jamais devinée.** « Exporter en CSV » : `—` pour DSM,
ESM, Booster, responsable de bureau ; `Entité` pour ADM-E, `Global` pour SUPER — confirmé par le
contrôle d'acceptation §24, point 18 : « l'export d'audit est refusé à tous les rôles sauf `ADM-E`
et `SUPER` ». Nouvelle constante `ROLES_D_EXPORT_DE_L_AUDIT`, déclarée séparément de
`ROLES_DES_DETAILS_TECHNIQUES` bien que les deux portent aujourd'hui les deux mêmes rôles — une
coïncidence de cette matrice, pas une identité conceptuelle (deux lignes distinctes du §16), et les
fusionner lierait au silence deux règles que la matrice pourrait un jour faire diverger.

**« Le périmètre est respecté » (backlog) est tenu par RÉUTILISATION, jamais par une seconde
résolution.** L'export appelle la MÊME `resoudre_le_perimetre_de_l_audit`/`a_les_details_techniques`
que la lecture de `T8`, et une nouvelle fonction, `lister_tout_le_journal_d_audit`, qui partage
avec `lister_le_journal_d_audit` la MÊME construction SQL (CTE par périmètre, clause de filtres) —
seule la partie finale diffère, un `ORDER BY` seul plutôt qu'un `LIMIT`/`OFFSET`.

**« Limité » (backlog) est lu comme « limité au périmètre déjà résolu », rien de plus.** Aucun
document ne nomme une borne de lignes ou de période propre à CET export ; en inventer une serait
§6.5 de la passation. Les cinq filtres déjà servis par `T8` (`depuis`/`jusqua`/`action_code`/
`resource_type`/`acteur`) restent le seul moyen de borner un export, à la demande de l'appelant.

**« L'export est journalisé » (backlog) et « exports » (cahier §10.11, listé parmi ce qui est
audité) sont tenus par le service générique de `T2`, jamais une seconde voie d'écriture.** L'export
pose une ligne `export_request` (modèle §21.5) PUIS un `audit_event` via
`app.audit.services.enregistrer_un_evenement` — exactement comme toute autre action sensible déjà
câblée par `T2`-`T7`.

**Aucun motif n'est exigé, même pour `SUPER`.** Le modèle §21 borne l'obligation du §18.1 aux
interventions du super-administrateur qui « modifient des données » ; un export est une LECTURE. Le
retrofit de `T7` (`app.audit.motif`) n'a donc rien à faire ici, et l'étendre serait une règle
inventée que ni le cahier ni la matrice ne demandent.

**Le format CSV lui-même (virgule, UTF-8, RFC 4180) est un choix par défaut, pas une règle
métier.** `DEC-432` fixe le séparateur du CSV collaborateurs, en ENTRÉE — un besoin différent (des
noms et présentations qui portent des virgules). Aucun document ne contraint le format de CET
export, en SORTIE.

---

# 3. Ce que la sous-étape a produit

## 3.1 `app/audit/perimetre.py` — une constante de plus

`ROLES_D_EXPORT_DE_L_AUDIT` (ADM-E, SUPER), déclarée à côté de `ROLES_DES_DETAILS_TECHNIQUES`
plutôt que réutilisée (voir §2).

## 3.2 `app/audit/lecture.py` — extraction partagée, une fonction de plus

`_cte_et_source` est extraite de `lister_le_journal_d_audit` (`T8`) : le CTE par périmètre, la
clause `FROM ... WHERE ...` et ses paramètres liés, communs à la lecture paginée et à l'export.
`lister_tout_le_journal_d_audit` l'appelle et ajoute un `ORDER BY ae.occurred_at DESC, ae.id DESC`
seul, sans `LIMIT`/`OFFSET` : toute la population du périmètre/des filtres résolus, dans le MÊME
ordre que la lecture paginée.

## 3.3 `app/audit/export.py` — nouveau module

- `generer_le_csv(evenements)` : le contenu CSV complet, un en-tête puis une ligne par événement,
  via le module `csv` standard. Une valeur `None` devient une cellule VIDE, jamais le mot `None` —
  défaut `T10-8` du LOT 6 (§7.42 de la passation), un témoin dédié le prouve (§4).
- `normaliser_la_portee` / `ecrire_la_demande_d_export` : posent la ligne `export_request` (modèle
  §21.5), `generated_media_id`/`expires_at` restant `NULL` (voir §2).
- Constantes `TYPE_EXPORT_AUDIT_CSV` (`"audit_csv"`, vocabulaire OUVERT comme le modèle l'exige),
  `ACTION_CODE_AUDIT_EXPORTE`/`RESOURCE_TYPE_EXPORT_REQUEST` (littéraux, aucune enum existante ne
  nommant ce geste).

## 3.4 La route

`POST /entities/{code}/audit/export` : `_resoudre_l_entite_et_les_roles` (déjà posée par `T8`) reste
la seule résolution ; une SECONDE garde, plus étroite (`ROLES_D_EXPORT_DE_L_AUDIT`), est vérifiée
en plus. Les cinq filtres sont REPRIS À L'IDENTIQUE de la lecture (mêmes bornes, même description) :
un export qui accepterait d'autres valeurs que la lecture pourrait exporter ce qu'aucune page ne
montre jamais. Réponse `text/csv`, `Content-Disposition: attachment`.

---

# 4. Contrôles exécutés

**Dix-huit tests d'intégration nouveaux**, `apps/api/tests/test_export_audit.py`, décor MINIMAL
(une entité, une autre pour l'asymétrie, sept rôles) — `test_journal_d_audit.py` (`T8`) prouve déjà
le périmètre et le masquage sur un décor bien plus large ; ce fichier ne reprend que ce que `T8` ne
pouvait pas prouver : la garde `ROLES_D_EXPORT_DE_L_AUDIT` (cinq rôles refusés, y compris DSM/ESM
qui LISENT pourtant le journal), l'absence de pagination (30 lignes injectées, 30 rendues), le
contenu du CSV (cellule vide plutôt que le mot `None`, `resource_reference`/`correlation_token`
jamais masqués pour l'exportateur, mêmes identifiants que la lecture JSON), les cinq filtres
repris à l'identique, et la journalisation de l'export lui-même (`export_request` + un second
`audit_event`).

| Contrôle | Résultat |
|---|---|
| `pytest` racine | 1 822 collectés (+18, tous d'intégration), 1 745 passés / 77 échecs |
| Comparaison de worktree avec `origin/develop` | 77 échecs environnementaux **identiques**, `diff` vide entre les deux listes triées |
| `uv run mypy` (racine) | vert, 256 fichiers (+2) |
| `uv run ruff check`/`format` | vert, tout le dépôt |
| `make migrations-check` | schéma identique, tête `0027` inchangée — aucune migration |
| `make permissions-check` | 15/15 |
| `make docs-check` | vert |
| `make sources-check` | aucun fichier source ignoré par git |
| Contrat (`test_contrat.py`) | mis à jour (`exportDuJournalDAudit`, `forme: "octets"` — même convention que `photoDuProfil`), 5/5 |

---

# 5. Décisions et écarts

`DEC-663` consigne cette sous-étape. Aucun écart n'est ouvert ni fermé par `T9` ; `US004` est
close.

---

# 6. Ce que `T9` laisse

- **Le reporting étendu** (`US003`, compteurs et tableaux du §15.1/§10.10) reste à `T10`.
- **Aucun écran** ne consomme encore cette route : les écrans back-office arrivent à `T15`.
- **`generated_media_id`/`expires_at` restent `NULL`** : le dépôt MinIO, l'expiration et le
  téléchargement sécurisé appartiennent à la V1 asynchrone (`V1-L04-US002`), hors de ce lot.

---

**Validation demandée à Jonathan.**

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
