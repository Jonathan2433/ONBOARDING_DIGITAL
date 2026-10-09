# Compte rendu — `T8` du LOT 9 : rapprocher les clients, enregistrer une décision

**Sous-étape :** la huitième du lot — `MVP-L09-US005`
**Date :** 9 octobre 2026
**Décision :** `DEC-643`
**Stories :** `US005`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, **`T8`** |
| Restent | `T9` à `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Le point arbitré par Jonathan avant tout code

`codes-erreurs-import.md` §1.2 nomme quatre situations pour le champ client
(`F13`) : une correspondance exacte avec un client déjà activé dans
l'entité (rattachement direct, aucun code), une correspondance exacte avec
un client global pas encore activé localement (`W-CLIENT-001`), **une
« ressemblance sans correspondance exacte »** (`D-CLIENT-001`), et aucune
correspondance ni ressemblance (`D-CLIENT-002`).

Aucun document ne dit **comment** reconnaître une ressemblance — quel
algorithme, quel seuil — et aucun outil de recherche approximative n'est
installé dans cette base : mesuré, `0002_extensions.py` (LOT 2) n'installe
que `btree_gist` ; `pg_trgm`/`unaccent` étaient prévus pour le trombinoscope
du LOT 5 et n'ont jamais été posés. Inventer un seuil ou une nouvelle
extension PostgreSQL pour cette seule sous-étape aurait été exactement ce
que le §6.5 interdit.

Posé à Jonathan avant d'écrire une ligne : réponse — **aucune détection
automatique de ressemblance.** Tout ce qui n'est pas une correspondance
exacte devient « client inconnu », et c'est un humain qui le recherche et
le choisit lui-même via `GET .../clients`. `D-CLIENT-001` reste donc un
code **déclaré par le référentiel mais jamais produit** par ce module — un
mécanisme déclencheur qui n'existe pas plutôt qu'une heuristique inventée
pour le simuler.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/imports/clients.py` | **modifié** (créé par une étape antérieure du même chantier) — `resoudre_les_clients`, `lister_les_clients`, `W-CLIENT-001`/`D-CLIENT-002` |
| `apps/api/app/imports/analyse.py` | **modifié** — intègre le rapprochement client dans `analyser_le_lot` |
| `apps/api/app/imports/decisions.py` | **nouveau** — `enregistrer_une_decision`, rôles de validation |
| `apps/api/app/imports/routes.py` | **modifié** — `GET .../clients`, `POST .../imports/{lot}/rows/{ligne}/decisions` |
| `apps/api/tests/test_rapprochement_clients.py` | **nouveau** — **14 tests**, tous d'intégration |

Aucune migration : `client`, `entity_client`, `client_alias` (LOT 2) et
`import_decision` (LOT 9, `T1`) existent déjà.

## 3.1 Ce qu'un alias déjà validé résout, et pourquoi c'est une correspondance exacte

`client_alias` (LOT 2) porte `validated_by_person_id`/`validated_at`
**NOT NULL** : une ligne n'y vit QUE si un humain l'a déjà validée
(`DATA-005`). Un nom qui correspond à un alias existant n'est donc **pas**
une ressemblance à confirmer une deuxième fois — c'est une correspondance
déjà humainement tranchée, au même titre que `canonical_name`. La priorité
va à l'alias **local** à l'entité, puis à l'alias **global**, puis au nom
canonique — jamais l'inverse, qui ferait qu'un alias plus récent et plus
spécifique à l'entité perde contre le nom d'origine. Une seule paire de
requêtes résout tous les noms candidats du lot, jamais une par ligne.

## 3.2 `GET .../clients` ferme `ECART-060` pour les clients

`ECART-060` constatait que le trombinoscope (LOT 5, `T3`) accepte un filtre
`client` sans qu'aucun endpoint n'en serve la liste. `GET
/entities/{code}/clients` liste le référentiel global des clients actifs,
**avec** ceux qui ne sont pas encore activés localement — sans quoi un
humain cherchant à rapprocher une ligne d'import ne pourrait jamais choisir
le client qui lui manque (exactement le cas `W-CLIENT-001`).

**`ECART-060` n'est que partiellement clos par `T8`** : son registre nomme
aussi les métiers et les DSM, et aucune sous-étape du découpage validé du
LOT 9 ne les nomme explicitement. Non bloquant : aucun critère de sortie du
lot ne les réclame.

## 3.3 Enregistrer une décision : générique sur cinq types, exercé sur deux

`import_decision.decision_type` ferme cinq catégories depuis `T1`
(`person_merge`, `profile_reactivation`, `client_alias_creation`,
`canonical_client_selection`, `voluntary_rejection`). `T7` avait déjà
produit `D-PERSONNE-001`/`002` sans aucun mécanisme pour les résoudre ; une
route limitée aux seuls types « client » aurait dupliqué, pour un gain nul,
exactement la même mécanique (verrou de la ligne, vérification du type
contre les codes en cours, écriture de `import_decision`). La route est
donc **générique**, mais **seuls `client_alias_creation` et
`canonical_client_selection` sont exercés et testés par `T8`** — les trois
autres existent structurellement, non éprouvés ici.

**N'importe rien** : `import_row.state` reste `needs_decision` après
l'appel — l'import réel (`T9`, transactionnel) relira les décisions
enregistrées et décidera, pour de vrai, si la ligne devient
`imported`/`updated`/`rejected`. Seule exception, structurelle :
`client_alias_creation` crée **immédiatement** la ligne `client_alias`
(puisqu'une ligne n'y vit que validée), et `normalized_data['F13']` est mis
à jour pour refléter la décision prise.

## 3.4 Qui décide, et la portée particulière du DSM

Matrice §14 « Valider les rapprochements clients » : `DSM` Consultants,
`ESM`/`ADM-E` Entité, `SUPER` Global — `BOOST`/`OFFICE` à tiret, à la
différence de la ligne voisine « Prévisualiser et corriger les
correspondances » qui admet `BOOST`. La garde de route admet les quatre
rôles ; le **service** resserre pour le DSM seul : sans `ESM`/`ADM-E`/
`SUPER` en plus, un DSM ne décide que sur une ligne dont le `F16` (e-mail
du DSM) le désigne lui-même — lu **directement dans le fichier**, puisque
aucun profil n'existe encore pour la relier autrement.

## 3.5 Un défaut trouvé et corrigé avant tout commit

`to_jsonb(:client_cible::text)` produit une erreur de syntaxe PostgreSQL :
le double deux-points immédiatement après un paramètre lié n'est pas
reconnu par le pilote comme un paramètre suivi d'un transtypage, et
`:client_cible` est transmis tel quel au serveur. Corrigé en
`to_jsonb(CAST(:client_cible AS text))`, l'idiome déjà établi par
`app.content.ecriture` pour les mêmes raisons.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_rapprochement_clients.py` | **14/14** |
| `uv run pytest -q apps/api/tests/test_depot_import.py apps/api/tests/test_analyse_import.py` | **34/34** (inchangés) |
| `uv run pytest -q apps/api/tests/test_contrat.py` | **5/5** |
| `uv run mypy` (racine) | vert, **224 fichiers** |
| `make lint`, `make format-check` | verts |
| `make isolation-check` | **inchangé** — 35 tables locales, 29 clés composites |
| `make migrations-check` | vert — tête `0025`, aucune migration nouvelle |
| `make docs-check`, `make sources-check` | verts |
| `make audit` | zéro avis |
| collecte depuis la racine | **1 661 pytest** (+14, tous d'intégration) ; **74 échecs environnementaux**, liste de fichiers identique à celle d'avant `T8` |
| frontend | **794 Vitest** inchangés |

---

# 5. Décisions et écarts

- `DEC-643` consigne la réalisation, l'arbitrage de Jonathan (aucune
  détection automatique de ressemblance), et le défaut `to_jsonb`/`CAST`
  corrigé avant commit ;
- `ECART-060` passe de « ouvert » à **« partiellement clos »** : les
  volets cercle (LOT 6) et client (`T8`) sont clos, les volets métier et
  DSM restent ouverts, non bloquants ;
- aucune nouvelle question n'est ouverte par `T8`.

---

# 6. Ce que `T8` laisse

- un acteur `DSM`/`ESM`/`ADM-E`/`SUPER` consulte le référentiel des clients
  et enregistre une décision sur une ligne `needs_decision` ;
- `import_row.state` ne change jamais par cette sous-étape : l'import réel
  reste entièrement `T9` ;
- aucun écran ne consomme encore ces routes (aucun consommateur avant
  `T14`) ;
- aucune validation du champ situation/mission (`F12`), aucune validation
  des autres domaines (date, métier, cercle, DSM) : `T9`, qui réutilisera
  les règles déjà posées par `T2`.

# Validation demandée à Jonathan

`T8` est faite. Après fusion, la prochaine sous-étape est `T9` : import
transactionnel des lignes valides, mises à jour par e-mail, confirmation
explicite pour réactiver un profil archivé (`US006`, 1/2).
