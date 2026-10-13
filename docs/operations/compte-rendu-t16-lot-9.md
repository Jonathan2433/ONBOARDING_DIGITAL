# Compte rendu — `T16` du LOT 9 : recette de clôture, §30 et checklist `G9`

**Sous-étape :** la seizième et dernière du lot — reclassement du §30 du modèle (règles 17/18
vérifiées), recette sur les images publiées, préparation de la checklist `G9`
**Date :** 13 octobre 2026
**Décision :** `DEC-651`
**Branche :** `codex/lot9-t16-recette-cloture-g9`, depuis `develop` à jour (`5f30443`, fusion de
`T15`, PR #258)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | les SEIZE — `T1` à `T16` |
| Reste | la décision de porte elle-même — `G9` n'est **pas** déclarée franchie ici : le corpus
exige encore la validation explicite de Jonathan (critère de sortie 8) |
| Issues | épic `#234`, stories `#235` à `#242` (déjà closes sur leurs preuves propres), jalon `G9` |

---

# 2. Sous-étape en cours

`T16` clôture techniquement le lot, pattern `T14`/`T15` des LOTS 7/8 : reclassement exécutable des
contrôles du §30 du modèle immuable, recette sur les images publiées, préparation de la checklist
`G9`.

---

# 3. Travail réalisé

## 3.1 Reclassement du §30 : `§30.17` et `§30.18`, reportés au LOT 9 depuis `T12` du LOT 2

La fiche nommait explicitement ces deux règles comme « à vérifier » à `T16`. Mesure avant toute
écriture :

- **`§30.17` — « un import n'écrit aucune ligne avant approbation »** : la lecture du code montrait
  déjà que le dépôt (`T6`) et l'analyse (`T7`/`T8`) n'appellent **jamais** `app.imports.organisation`
  ni aucune écriture de `person`/`entity_membership` — seul `lancer_l_import` (`T9`, l'APPROBATION
  du cahier §9.5) écrit. Mais **aucun témoin ne le prouvait** : une affirmation sans preuve,
  exactement ce que le §7.0 de la passation interdit (« un contrôle qui ne peut pas échouer ne
  prouve rien »).
- **`§30.18` — « une ligne invalide n'empêche pas les lignes valides d'être importées »** : déjà
  prouvé par `T9` (`test_une_ligne_en_echec_n_empeche_pas_les_autres_d_etre_importees`, chaque
  ligne dans son propre savepoint `connexion.begin_nested()`), sans jamais avoir été reclassé.

**Un seul test nouveau a été ajouté, pour `§30.17` seul** :
`test_aucune_ecriture_metier_avant_le_lancement_de_l_import`
(`apps/api/tests/test_import_transactionnel.py`). Il dépose une ligne entièrement valide, vérifie
qu'`import_row.target_person_id`/`target_membership_id` restent `NULL` et qu'**aucune ligne
`person` ne porte encore son e-mail** après l'analyse, puis lance l'import et vérifie le
**contraire** dans le MÊME test. Le témoin négatif est apparié à un témoin positif (§7.39 de la
passation) : sans lui, un pipeline qui n'écrirait **jamais** rendrait la même observation qu'un
pipeline conforme.

`§30.18` est reclassé **sans test nouveau**, le témoin existant de `T9` suffisant.

**Classement final** (`infra/scripts/verifier-recette-modele.py`) : **18 acquis, 2 partiel,
5 reportés, 0 inapplicable** — était 16/2/7/0 depuis `G7`.

## 3.2 Les critères de sortie 1, 2 et 7 de la fiche, sur des données réelles

Mesurés plutôt que supposés :

- **Critère 1** (« le CSV réel n'est ni dans Git ni dans une image ») : **structurellement acquis
  depuis le LOT 0**, pas construit ici. `.gitignore` exclut `*.csv` (seule exception déclarée, le
  jeu fictif de `docs/architecture/donnees/exemples/`) ; `make sources-check` n'examine aucune
  extension `.csv` (`EXTENSIONS` ne la porte pas) ; les motifs génériques de `make icloud-verify`
  (`* [0-9].*`, extension-agnostiques) couvriraient une copie de conflit. Témoin direct exécuté : un
  CSV déposé à la racine du dépôt est immédiatement ignoré par `git check-ignore` et absent de
  `git status --short`.
- **Critère 2** (« vérification FileVault et sauvegarde ») : un **geste procédural**, non
  éprouvable techniquement avant une production réelle — `exploitation-locale.md` §4 le dit déjà :
  « la sauvegarde et la restauration, aucune procédure n'existe, LOT 13 ». Documenté dans la
  checklist `G9` comme préalable humain, jamais exercé avec un vrai CSV pendant le développement.
- **Critère 7** (« Léa et Jonathan valident le rapport de répétition en recette ») : une
  **démonstration à organiser**, aucun canal de recueil n'étant nommé par le corpus pour Léa — même
  résidu que `G7`/`G8` pour Tess et Diane. La checklist le signale à Jonathan sans inventer de
  procédure.

## 3.3 Recette sur les images publiées de `5f30443`

- `make images-pin` : épinglage sur la publication réussie de `5f30443` (fusion de `T15`).
- Conflit de port `8080` connu (`observatoire-ecom-studio`, §7.23/§9.2 de la passation), résolu en
  arrêtant temporairement son conteneur `web` puis en le relançant après la recette.
- `make caddy-recreate ENVIRONNEMENT=recette` nécessaire : Caddy, créé pendant le conflit de port,
  avait démarré sans ses publications réelles (§7.17 de la passation) — `docker inspect` confirmait
  `{"443/tcp":[],"80/tcp":[]}`, aucune publication, bien que le conteneur soit `healthy`.
- **La base de recette était restée à la migration `0023` (état du LOT 8)** : `make back-office-check
  ENVIRONNEMENT=recette` a d'abord échoué sur « relation `import_decision` does not exist » —
  mesuré, pas supposé. `make migrate ENVIRONNEMENT=recette` l'a fait passer à `0026` (tête).
- Après migration, les trois contrôles de pile réelle disponibles dans `ci.yml` ont été rejoués
  `ENVIRONNEMENT=recette`, dans l'ordre chronologique de leur apparition : `back-office-check`
  (LOT 9), `onboarding-check` (LOT 7), `accueil-check` (LOT 8) — même discipline que `T14` du
  LOT 8, qui avait rejoué `onboarding-check` en plus de son propre `accueil-check`.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `test_aucune_ecriture_metier_avant_le_lancement_de_l_import` (nouveau) | passé — isolé et en suite complète |
| `uv run pytest -q --collect-only` | **1 708** collectés (+1) |
| `uv run pytest -q` (développement) | 1 634 passés, **74 échecs environnementaux** |
| Comparaison de worktree `origin/develop` (§7.22 de la passation) | 74 échecs **identiques, un par un** (liste comparée, pas seulement le compte) — 1 633 passés côté `develop` (+1 sur la branche, le nouveau test) |
| `make residu-check` | 74 échecs environnementaux ; aucun résidu laissé par le nouveau test |
| `uv run mypy` (bare, portée `pyproject.toml`) | **238** fichiers, inchangé |
| `uv run ruff check` / `ruff format --check` | verts sur le fichier modifié et sur tout le dépôt |
| `make lint` / `make format-check` | verts (Ruff, ESLint, Prettier) |
| `make test-frontend` | **802 Vitest** (380 `contracts`, 120 `ui`, 302 `web`), inchangé |
| `make sources-check` | **653** fichiers source examinés (+2 : ce compte rendu et la checklist `G9`), 0 ignoré hors les 2 exceptions connues |
| `make docs-check` | vert — 5 documents immuables intacts, 6 séquences cohérentes, 12 contrôles de totaux dérivés, 12 contrôles sur la passation |
| `make recette-modele-check` | 25/25 classés — **18 acquis, 2 partiel, 5 reportés, 0 inapplicable** |
| `make recette-check` (images publiées `5f30443`) | **57 contrôles, 0 échec** ; 7/7 séparations ; artefact publié confirmé par empreinte, `aarch64` natif |
| `make api-check ENVIRONNEMENT=recette` | 3 endpoints de santé répondent, révision `5f30443` |
| `make web-check ENVIRONNEMENT=recette` | 7 contrôles, 0 échec |
| `make back-office-check ENVIRONNEMENT=recette` | **16/16**, 0 échec |
| `make onboarding-check ENVIRONNEMENT=recette` | **14/14**, 0 échec |
| `make accueil-check ENVIRONNEMENT=recette` | **29/29**, 0 échec |

**Zéro régression** : seuls `apps/api/tests/test_import_transactionnel.py` et
`infra/scripts/verifier-recette-modele.py` sont modifiés — aucune route, aucune migration, aucun
fichier frontend touché. Le total mypy (238 fichiers) et le total Vitest (802) sont donc
**structurellement** inchangés, pas seulement mesurés identiques.

---

# 5. Décisions

- `DEC-651` consigne la réalisation de `T16` et le reclassement du §30 ;
- aucun écart nouveau n'est ouvert. `ECART-012`, `ECART-068`, `QO-100`, `QO-121` et `QO-125`
  restent ouverts et non bloquants pour `G9` — aucun n'est nommé par le découpage du lot. `ECART-060`
  reste ouvert pour ses volets métier/DSM.

---

# 6. Ce que `T16` laisse

- le LOT 9 est **techniquement complet** : les seize sous-étapes sont réalisées, et `G9` attend la
  seule validation explicite de Jonathan ;
- `checklist-validation-G9.md` est prête, séparant les cinq critères techniquement tenus des trois
  qui portent sur des données réelles ou l'exploitation (critères 1 — tenu, mesuré — 2 et 7 — des
  gestes humains à organiser) et du dernier qui est la décision de Jonathan lui-même ;
- une fois `G9` validée, consigner la décision (`DEC-652` probable, pattern `DEC-617`/`DEC-634`) et
  poser le tag `v0.9.0` sur `main`, comme `G7`/`G8` l'ont fait.

# Validation demandée à Jonathan

`T16` est faite — le LOT 9 est techniquement complet. Peux-tu lire
[`checklist-validation-G9.md`](checklist-validation-G9.md) et confirmer si `G9` peut être déclarée
franchie ? Cette décision sera consignée séparément (`DEC-652` probable), comme `DEC-617`/`DEC-634`
l'ont été pour `G7`/`G8` après validation.

```bash
gh pr merge <n> --squash --delete-branch   # fusion de T16 après validation
gh pr close <n> --delete-branch            # retour arrière avant fusion
```
