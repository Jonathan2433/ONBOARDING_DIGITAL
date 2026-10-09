# Compte rendu — `T6` du LOT 9 : le dépôt sécurisé du CSV

**Sous-étape :** la sixième du lot — `MVP-L09-US004` (1/2)
**Date :** 9 octobre 2026
**Décision :** `DEC-641`
**Stories :** `US004`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, **`T6`** |
| Restent | `T7` à `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Ce que la fiche nommait, et ce que le cahier dit vraiment

La fiche (`fiche-lot-9.md` §`T6`) dit : « Dépôt sécurisé du CSV, empreinte
SHA-256, `import_batch`, zone d'analyse sans écriture métier ». Le cahier
§9.5 « Import CSV » donne la séquence complète en huit points, dont `T6` sert
les **deux premiers** :

1. chargement du fichier ;
2. analyse complète **sans écriture** ;
3. prévisualisation des lignes valides, avertissements et rejets ;
4. validation humaine des rapprochements ;
5. confirmation explicite ;
6. import transactionnel des lignes valides ;
7. rapport complet ;
8. correction et rejeu des lignes rejetées.

Le point 3 (« prévisualisation ») suppose la normalisation des e-mails et la
détection des doublons que la fiche réserve explicitement à `T7` (`US004`,
2/2) — `T6` s'arrête donc au point 2, et le diagramme §24.4 le dit en
vocabulaire d'état : `Uploaded --> Analyzing --> PreviewReady`. `T6` sert les
deux premières transitions **dans le même appel** (import synchrone,
`DEC-462`) et s'arrête à `analyzing` ; `preview_ready` est `T7`.

**Aucune écriture métier, et c'est mesuré, pas seulement nommé** : les deux
seules tables touchées sont `import_batch` et `import_row` (posées par `T1`),
jamais `person`, `client`, `entity_membership` ou une autre table du domaine.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/imports/perimetre.py` | **nouveau** — `ROLES_DE_DEPOT_DE_L_IMPORT` |
| `apps/api/app/imports/depot.py` | **nouveau** — `deposer_un_csv`, `LotDepose` |
| `apps/api/app/imports/routes.py` | **nouveau** — `POST /entities/{code}/imports` |
| `apps/api/app/media/objets.py` | **modifié** — `deposer_l_objet`, `ObjetNonDepose` (première écriture MinIO) |
| `apps/api/app/main.py` | monte `routeur_imports`, après le tableau de bord |
| `apps/api/pyproject.toml` | **modifié** — `python-multipart` (FastAPI l'exige pour `UploadFile`) |
| `packages/contracts/src/contrat-api.json` | l'entrée `depotDUnImport` |
| `apps/api/tests/test_depot_import.py` | **20 tests** (15 d'intégration, 5 unitaires purs) |

Aucune migration : `import_batch`/`import_row` existent depuis `T1`.

## 3.1 La première écriture MinIO du projet

Mesuré avant d'écrire une ligne : zéro occurrence de `put_object` hors des
tests, dans tout le dépôt. Chaque photo du jeu de données ou des décors de
test est posée **directement** par `boto3`, jamais par une route de l'API —
aucune route n'avait encore eu besoin d'écrire dans le bucket. `T6` ajoute
`app.media.objets.deposer_l_objet`, qui réutilise `client_s3` (la
construction déjà faite pour la lecture, LOT 5 `T5`) plutôt que d'en bâtir
une seconde qui diverge au premier réglage changé.

L'ordre des écritures est délibéré : le lot (`import_batch`) est inséré
**avant** le dépôt dans MinIO, lui-même **avant** les lignes. Un échec du
dépôt MinIO annule l'insertion du lot via la transaction ouvrante (posée par
la route), plutôt que de laisser un lot orphelin sans objet. Le décodage et
l'analyse structurelle du CSV se font **encore plus tôt**, avant toute
écriture : un fichier illisible ne produit ni ligne `import_batch` ni objet
déposé.

## 3.2 Le délimiteur est détecté structurellement, jamais supposé

`QO-096`/`QO-110` (schéma réel des colonnes, en-têtes, nomenclature) restent
ouvertes et ne bloquent pas la construction du pipeline (fiche §2.1). Le
délimiteur (virgule, point-virgule, tabulation — les trois formes qu'un
tableur produit réellement) est donc **détecté** par `csv.Sniffer`, avec un
repli sur la virgule si la détection échoue : un choix mécanique et
réversible, jamais une règle métier gravée au schéma.

Chaque ligne devient un dictionnaire `{en-tête: valeur}` sans aucune
validation de contenu : une valeur manquante vaut `None` (`restval`), une
colonne en trop rejoint `_colonnes_excedentaires` en liste — jamais la clé
`None` que `csv.DictReader` emploierait par défaut pour `restkey`, qui n'est
pas une clé JSON valide.

## 3.3 Trois refus structurels, aucune règle métier

Fichier vide ou blanc, encodage non UTF-8, nom de fichier vide une fois
nettoyé des deux séparateurs de chemin (`/` et `\`) — les trois en 422, tous
avant la moindre écriture. Aucun de ces refus ne porte sur le **contenu**
métier des lignes (e-mail, doublons) : c'est `T7`.

## 3.4 Une grille déjà connue du dépôt, copiée et non importée

Matrice §14 « Charger un CSV » : `ESM`/`ADM-E` dans leur entité, `SUPER`
partout, `DSM`/`BOOST`/`OFFICE` à tiret — mot pour mot la grille déjà posée
par `T4` (`app.organization.perimetre.ROLES_DE_CYCLE_DE_VIE_FRAMEWORK`).
`app.imports.perimetre` en déclare une **copie propre**, jamais un import
croisé : les deux domaines (cercles/bureaux, imports CSV) n'ont aucun
rapport, et coupler deux modules sur une coïncidence de grille créerait une
dépendance qui pourrait diverger demain sans que personne n'en soit informé
(§7.27).

La garde est vérifiée **deux fois**, même discipline que `T4`/`T5` : la
dépendance FastAPI (`garde_du_depot_d_import`) rend un premier refus rapide,
et `_resoudre_l_entite_et_verifier_le_role` revérifie ensuite **dans la
transaction qui écrit** — la garde a résolu les siens dans sa propre
connexion et à son propre instant, s'y fier ferait agir sur ce qui a été
autorisé ailleurs.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_depot_import.py` | **20/20** |
| `uv run pytest -q apps/api/tests/test_contrat.py` | **5/5** |
| `uv run mypy` (racine) | vert, **217 fichiers** (+4 sur `T5`) |
| `make lint`, `make format-check` | verts |
| `make isolation-check` | **inchangé** — 35 tables locales, 29 clés composites, aucune table nouvelle |
| `make migrations-check` | vert — aucune migration, chaîne inchangée à `0024` |
| `make docs-check`, `make sources-check` | verts |
| `make audit` | zéro avis (`python-multipart` ajouté, `pip-audit`/`pnpm audit` toujours à zéro) |
| collecte depuis la racine | **1 633 pytest** (+20), dont **1 214 d'intégration** (+15) ; **74 échecs environnementaux**, liste de fichiers identique à celle d'avant `T6` |
| frontend | **794 Vitest** inchangés — aucun fichier frontend touché |

---

# 5. Décisions et écarts

- `DEC-641` consigne la réalisation : le dépôt sécurisé d'un CSV, la
  première écriture MinIO du projet, et la détection structurelle du
  délimiteur ;
- aucun nouvel écart ni aucune nouvelle question n'est ouvert par `T6`.

---

# 6. Ce que `T6` laisse

- un acteur `ESM`/`ADM-E`/`SUPER` dépose un CSV et obtient un lot `analyzing`
  avec son empreinte et son total de lignes ; `DSM`/`BOOST`/`OFFICE` sont
  refusés ;
- aucun écran ne consomme encore cette route (même discipline que `T2`/`T3`/
  `T5` de ce lot, aucun consommateur avant `T14`) ;
- aucune lecture d'un lot (lister, consulter un lot précis) : non demandée
  par le découpage avant `T14` ;
- aucune normalisation, aucune détection de doublon, aucun blocage des
  lignes sans e-mail : `T7`.

# Validation demandée à Jonathan

`T6` est faite. Après fusion, la prochaine sous-étape est `T7` :
normalisation des e-mails, détection des doublons, blocage des lignes sans
e-mail, prévisualisation complète (`US004`, 2/2).
