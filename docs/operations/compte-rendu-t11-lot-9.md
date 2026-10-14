# Compte rendu — LOT 9, `T11`

**Sous-étape :** `T11` — opérations de masse contrôlées
**Story :** `MVP-L09-US003`, `P1`, dépend de `T2`/`T3`
**Décision :** `DEC-646`
**Date :** 12 octobre 2026

---

## 1. État du lot

`T1` à `T10` du LOT 9 sont faites et fusionnées. `T11` ferme `US003` : « Effectuer des opérations
de masse contrôlées. La prévisualisation indique l'impact ; les opérations sont idempotentes et
auditées ; les erreurs partielles sont explicites. »

## 2. Le point arbitré

Ni le cahier (§10.8, « changements unitaires et en masse »), ni la matrice, ni le backlog ne
nomment QUELLE action doit recevoir une variante « plusieurs à la fois » — seulement qu'il en
existe une. La création en masse est déjà servie par l'import CSV (`T6` à `T10`).

Posé à Jonathan via `AskUserQuestion`, reformulé sans jargon :

> « T2 a servi la création d'un collaborateur, T3 le changement d'entité — et la création en
> masse existe déjà par l'import CSV. Sur quelle action faut-il construire le mode « plusieurs
> collaborateurs à la fois » pour cette sous-étape ? »

Trois options présentées :

1. **(Recommandé)** Changement d'entité seulement — la seule action structurante que `T2`/`T3`
   ont construite et qui n'a pas déjà de variante en masse.
2. Changement d'entité ET changement de statut/cercle — portée plus large, réutilisant aussi le
   module de LOT 5.
3. Autre chose (archivage/restauration groupée, etc.).

**Réponse de Jonathan : l'option 1.** Seul le changement d'entité (`T3`) reçoit une forme en
masse dans cette sous-étape.

## 3. Ce que `T11` a produit

### 3.1 Nouveau module `app/people/transfert_masse.py`

`executer_le_transfert_en_masse` est une BOUCLE autour de `changer_d_entite` (`T3`) — aucune
règle de permission, de biconditionnelle ou de transition métier n'est réécrite (§7.27) : les
réécrire divergerait de l'original au premier reglage changé. Le seul code neuf est la boucle et
l'isolation par élément, calquée sur le motif déjà posé par `app.imports.execution` (`T9`) :
chaque élément dans son PROPRE savepoint (`connexion.begin_nested()`).

Pour chaque élément : résoudre l'entité de destination (rapporter `entite_introuvable` sinon),
vérifier LA MÊME permission que la création (`resoudre_l_autorisation_de_creation`, « même
périmètre que `T2` », évaluée PAR ÉLÉMENT sur SA destination — deux éléments du même lot peuvent
viser des destinations différentes, avec des grilles différentes selon le rôle de l'acteur dans
chacune), puis appeler `changer_d_entite`. Toute `ErreurApplicative` est RAPPORTÉE sur l'élément,
jamais propagée.

### 3.2 L'aperçu : aucune estimation séparée

« La prévisualisation indique l'impact » est servie en exécutant EXACTEMENT le même chemin que
l'exécution réelle — même permission, même appel à `changer_d_entite` — à l'intérieur d'un
savepoint TOUJOURS annulé, succès ou échec. L'impact rendu (sessions révoquées, liens invalidés,
relations closes) est donc le résultat RÉEL de l'exécution, jamais une estimation séparée qui
pourrait diverger du chemin réellement emprunté.

Deux routes distinctes plutôt qu'un paramètre de mode dans une seule : `POST
.../people/transferts-en-masse/apercu` (toujours annulé) et `POST .../people/transferts-en-masse`
(succès commités, échecs annulés) — même séparation de verbes que « Charger un CSV »/« Lancer
l'import ».

### 3.3 L'idempotence (§18.6), sans mécanisme nouveau

`changer_d_entite` refuse déjà, en `409` (`CODE_ETAT_INCOMPATIBLE`), toute cible qui n'est plus
`active` ni `future` — précisément l'état d'une appartenance déjà transférée par un appel
précédent. Rejouer le MÊME lot de transferts est donc sans danger : chaque élément déjà traité
est refusé explicitement, aucun jeton d'idempotence n'étant introduit — l'état de la cible EST le
jeton, déjà verrouillé (`FOR UPDATE`) par `_lire_sous_verrou`. Prouvé par
`test_rejouer_le_meme_lot_est_sans_danger` : le même lot exécuté deux fois ne produit AUCUNE
deuxième écriture.

### 3.4 Les erreurs partielles explicites

Chaque élément du lot reçoit son propre sort dans la réponse — `succes`, et selon le cas
`code_erreur`/`message_erreur` ou l'impact du transfert. Un refus sur un élément — permission,
destination introuvable, version obsolète, état incompatible, biconditionnelle refusée —
n'affecte AUCUN autre élément du lot. Prouvé par
`test_un_echec_au_milieu_n_annule_pas_les_elements_voisins` : trois éléments, celui du milieu
refusé (version obsolète), les deux autres COMMITTÉS malgré l'échec voisin.

### 3.5 Ce que ce module ne fait jamais

Le critère d'acceptation du backlog nomme aussi « auditées », mais le découpage validé de
`fiche-lot-9.md` avait déjà réduit l'énoncé de `T11` à « prévisualisation d'impact, idempotence,
erreurs partielles explicites » — sans ce mot — avant même l'ouverture de cette sous-étape. C'est
cette portée, déjà arrêtée, qui est suivie : aucune écriture d'audit, `archive_reason`/
`assignment_reason` et `audit_event` restant hors de ce lot (`ECART-064`, LOT 10).

### 3.6 Borne technique, pas une règle métier

`TAILLE_MAXIMALE_DU_LOT = 100` protège la transaction unique d'une taille non bornée — une
sauvegarde d'ingénierie, documentée comme telle dans le code, et non un nombre décidé par
Jonathan. Elle peut être ajustée sans nouvelle question si elle se révèle trop étroite.

## 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest apps/api/tests/test_transfert_en_masse.py` | **6/6 passants** |
| `uv run pytest` (suite complète, racine) | **1 693 collectés** (+6, tous d'intégration), **74 échecs environnementaux** — la base documentée, inchangée (liste de fichiers comparée, identique) |
| `uv run pytest -m integration --collect-only` | **1 272 collectés** (+6) |
| `make isolation-check` | **35 tables locales, 29 clés composites, 0 référence nue** — inchangé |
| `make migrations-check` | tête `0026` inchangée, **aucune migration** — colonnes/contraintes/index/déclencheurs/fonctions identiques des deux côtés |
| `uv run mypy` (strict) | **233 fichiers**, 0 erreur |
| `uv run ruff check` / `ruff format --check` | 0 erreur, tout formaté |
| `pnpm lint` / `pnpm format:check` | 0 erreur |
| `uv run pytest apps/api/tests/test_contrat.py` | **5/5 passants** — contrat mis à jour (`previsualisationDuTransfertEnMasse`, `transfertEnMasse`) |
| `make sources-check` | 623 fichiers examinés, 0 ignoré hors les 2 exceptions déclarées |
| `make docs-check` | **12/12 contrôles verts** — séquences, totaux des registres, cohérence de la passation |

Aucun défaut trouvé dans le code livré.

## 5. Décisions et écarts

- `DEC-646` enregistrée au registre des décisions.
- Aucun écart ouvert ou clos par cette sous-étape.
- Aucune question ouverte nouvelle : la seule ambiguïté réelle (quelle action recevoir en masse)
  a été tranchée par Jonathan avant tout code, pas laissée en suspens.

## 6. Ce que `T11` laisse

- `US003` est fermée. Issue `#237` à fermer manuellement à la main après fusion (`gh issue
  close`, §7.19 de `CLAUDE.md` : `Closes #N` ne referme rien depuis `develop`).
- Prochaine sous-étape : `T12` — création d'une nouvelle entité depuis des modèles génériques
  (`US007`, `P0`, dépend des LOTS 2/6/7). `T12` ferme `ECART-035` pour la part « invitations » si
  l'objet est posé, sinon le nommer explicitement non résolu.
- Ouverts et non bloquants pour `G9` : `ECART-012`, `ECART-068`, `QO-100`, `QO-121`, `QO-125`.
  `ECART-060` reste ouvert pour ses volets métier/DSM.

## Validation demandée

Pull request à fusionner vers `develop`, puis fermeture manuelle de l'issue `#237`.

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
