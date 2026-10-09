# Compte rendu — `T7` du LOT 9 : normaliser les e-mails, détecter les doublons

**Sous-étape :** la septième du lot — `MVP-L09-US004` (2/2)
**Date :** 9 octobre 2026
**Décision :** `DEC-642`
**Stories :** `US004`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, **`T7`** |
| Restent | `T8` à `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Le point arbitré par Jonathan avant tout code

Le cahier §9.5 nomme huit points, dont `T7` sert le troisième :
« prévisualisation des lignes valides, avertissements et rejets ». Mais le
référentiel produit au LOT 0 (`docs/architecture/donnees/codes-erreurs-
import.md`) nomme **68 codes sur 12 domaines** — e-mail, identité, entité,
dates, catégorie professionnelle, métier, situation/client, cercles, DSM,
responsabilités Framework, rôles techniques, autorisation photo — alors que
le titre de `T7` (fiche §3) ne nomme que « normalisation des e-mails,
détection des doublons, blocage des lignes sans e-mail ». Aucune des seize
sous-étapes du découpage validé ne nomme explicitement les onze autres
domaines : `T8` ne porte que les clients, `T9` importe transactionnellement
sans dire qu'elle validerait les autres champs.

Posé à Jonathan avant d'écrire une ligne : T7 doit-elle previsualiser les 68
codes, ou rester à la taille que son titre annonce ? Réponse : **`T7` reste
bornée à l'e-mail et aux doublons de personne.** Les autres règles (date,
métier, cercle, DSM, responsabilités...) ne sont **pas** prévisualisées ici ;
elles seront vérifiées seulement au moment de l'import réel (`T9`), en
réutilisant les règles déjà posées par la création d'un collaborateur (`T2`,
`app.people.creation`) plutôt que de les dupliquer dans le pipeline d'import.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/imports/correspondance.py` | **nouveau** — `PROFIL_DE_CORRESPONDANCE_PROVISOIRE`, `valeur_logique` |
| `apps/api/app/imports/analyse.py` | **nouveau** — `analyser_le_lot`, 7 codes (`E-EMAIL-001` à `004`, `D-PERSONNE-001` à `003`) |
| `apps/api/app/imports/depot.py` | **modifié** — `deposer_un_csv` appelle `analyser_le_lot` dans le même appel ; délimiteur corrigé (`DEC-432`) |
| `apps/api/app/imports/modeles.py` | **modifié** — `ImportBatch.needs_decision_rows` |
| `apps/api/app/imports/routes.py` | **modifié** — réponse étendue de quatre compteurs |
| `apps/api/alembic/versions/0025_compteur_des_lignes_a_confirmer.py` | **nouveau** — `needs_decision_rows` |
| `apps/api/tests/test_analyse_import.py` | **nouveau** — **13 tests** |
| `apps/api/tests/test_depot_import.py` | **modifié** — assertions mises à jour (pipeline complété), +1 témoin (délimiteur) |

## 3.1 Les sept codes couverts, et pourquoi ces sept précisément

- `E-EMAIL-001` (absent) — bloquant, aucune autre vérification n'a de sens
  sur une valeur vide ;
- `E-EMAIL-002` (format implausible) — **la même règle que la contrainte
  `email_normalise_plausible` déjà posée en base** (LOT 2) : pas d'espace,
  une arobase ailleurs qu'en première position. Jamais une regex plus
  stricte, qui rejetterait en prévisualisation ce que l'écriture (`T9`)
  accepterait (§7.37 : une même valeur doit franchir la même frontière) ;
- `E-EMAIL-003` (domaine refusé) — même table `allowed_email_domain` que
  `app.auth.services`, mais une **copie propre** à ce module (§7.27) ;
- `E-EMAIL-004` (doublon technique dans le fichier) — `DEC-435` : la
  **première** occurrence (ordre de `row_number`) est retenue, les suivantes
  sont seules rejetées ;
- `D-PERSONNE-001`/`002` (profil actif ou archivé existant) — une seule
  requête `= ANY(:emails)` pour tout le lot, jamais une par ligne ;
- `D-PERSONNE-003` (homonymie) — nom et prénom identiques (casse
  indifférente) entre deux lignes du **même fichier**, e-mails différents.
  Vérifiée uniquement dans le fichier, jamais contre la base entière — le
  jeu d'exemple du LOT 0 ne démontre que le cas intra-fichier, et une
  homonymie contre la base reste un résidu non couvert.

Une ligne peut porter plusieurs problèmes à la fois (le jeu d'exemple du
LOT 0 le montre : la ligne « Golf » porte `D-CLIENT-001`, hors périmètre
ici, ET `D-PERSONNE-003`). L'état final suit une priorité stricte : `E`
(rejeté) prévaut sur `D` (à confirmer) prévaut sur `W` (aucun ici) prévaut
sur rien (valide).

## 3.2 Le profil de correspondance provisoire

Le schéma du CSV (`DEC-434`) découple des champs logiques stables (`F01` à
`F19`) d'un « profil de correspondance » qui associe les en-têtes réelles à
ces champs — la nomenclature des en-têtes restant ouverte (`QO-110`). `T7`
ne résout pas `QO-110` : elle reprend tel quel le profil provisoire déjà
produit au LOT 0 pour le jeu d'exemple fictif (`email`, `nom`, `prenom`...),
la seule nomenclature non normative mais déjà officiellement produite.

## 3.3 Deux défauts trouvés en construisant `T7`, corrigés avant tout code de service

**Le délimiteur.** `T6` confiait la détection à `csv.Sniffer` sur virgule/
point-virgule/tabulation, une heuristique de fréquence. Or le schéma du CSV
(`docs/architecture/donnees/schema-csv-collaborateurs.md` §2, `DEC-432`,
décision **déjà validée**, non lue en construisant `T6`) tranche : le
point-virgule est **obligatoire**, la virgule n'est tolérée que si elle est
détectée **sans ambiguïté** — motif explicite : les présentations courtes
contiennent des virgules, pas des points-virgules. `_detecter_le_delimiteur`
applique désormais la règle à la lettre : point-virgule par défaut, virgule
seulement en l'absence de point-virgule dans l'échantillon, tabulation
retirée des candidats (`DEC-432` ne la nomme pas). Un témoin reproduit
exactement le cas cité par le document — une présentation libre contenant
une virgule non échappée, dans un fichier à point-virgule.

**Le compteur manquant.** `import_batch` portait quatre compteurs
(`total_rows`, `valid_rows`, `warning_rows`, `rejected_rows`), calqués sur
les quatre termes de la réconciliation **post-import** du modèle §19. Mais
`import_row.state` compte **six** valeurs, et `T7` est la première
sous-étape à produire des lignes `needs_decision` — sans colonne pour les
compter, `total_rows` aurait dépassé la somme des trois autres compteurs
sans qu'aucune colonne n'explique l'écart. Migration `0025` :
`needs_decision_rows`, dans la **même** contrainte `comptes_non_negatifs`
que les quatre autres (une colonne de plus dans une contrainte existante,
pas une règle nouvelle).

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_analyse_import.py` | **13/13** |
| `uv run pytest -q apps/api/tests/test_depot_import.py` | **21/21** (mis à jour + 1 nouveau témoin) |
| `uv run pytest -q apps/api/tests/test_contrat.py` | **5/5** |
| `uv run mypy` (racine) | vert, **221 fichiers** (+4 sur `T6`) |
| `make lint`, `make format-check` | verts |
| `make isolation-check` | **inchangé** — 35 tables locales, 29 clés composites, aucune table nouvelle |
| `make migrations-check` | vert — tête `0025`, colonnes/contraintes identiques des deux côtés |
| `make docs-check`, `make sources-check` | verts |
| `make audit` | zéro avis |
| collecte depuis la racine | **1 647 pytest** (+14), dont **1 226 d'intégration** (+12) ; **74 échecs environnementaux**, liste de fichiers identique à celle d'avant `T7` |
| frontend | **794 Vitest** inchangés — aucun fichier frontend touché |

---

# 5. Décisions et écarts

- `DEC-642` consigne la réalisation, l'arbitrage de périmètre de Jonathan, et
  les deux défauts trouvés et corrigés (délimiteur, compteur) ;
- aucun nouvel écart ni aucune nouvelle question n'est ouvert par `T7`.

---

# 6. Ce que `T7` laisse

- `POST /entities/{code}/imports` dépose ET prévisualise un CSV dans le même
  appel : le lot ressort `preview_ready`, avec ses quatre compteurs
  (`lignes_valides`, `lignes_avec_avertissement`, `lignes_a_confirmer`,
  `lignes_rejetees`) qui se réconcilient avec `total_lignes` ;
- une ligne `valid` à ce stade ne garantit **pas** qu'elle franchira les
  règles non encore construites (date, métier, cercle, DSM...) — vérifiées
  seulement à l'import réel, `T9` ;
- le séparateur retenu (`;` ou `,`) et l'encodage ne sont **pas encore**
  persistés dans `import_batch` au sens où `criteres-qualite-import.md` §4
  l'exige « aux côtés de l'empreinte SHA-256 » — ce document range cette
  exigence dans **le rapport d'import**, construit par `T10` ; le résidu est
  nommé ici pour ne pas le perdre ;
- aucun écran ne consomme encore cette route (aucun consommateur avant
  `T14`) ;
- aucune correspondance de client, aucune décision de fusion/alias : `T8`.

# Validation demandée à Jonathan

`T7` est faite, et ferme `US004` (1/2 et 2/2). Après fusion, la prochaine
sous-étape est `T8` : correspondances de clients proposées et validation
humaine (fusion/alias), `import_decision` (`US005`) — ferme `ECART-060` pour
les clients.
