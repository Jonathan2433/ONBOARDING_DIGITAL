# Compte rendu — `T10` du LOT 9

**Story :** `MVP-L09-US006` (2/2) — « Importer uniquement les lignes valides et obtenir un
rapport », issue `#240`
**Fondement :** cahier §9.5 (points 7 et 8), `criteres-qualite-import.md` §4 et §6, modèle §19.5,
matrice §14
**Décision :** `DEC-645`

---

# 1. État du lot

LOT 9 ouvert depuis le 08/10/2026 (`DEC-635`), seize sous-étapes validées. `T1` à `T9` faites
(`DEC-636` à `DEC-644`). `T10` ferme `US006` dans ses deux moitiés : `T9` avait livré l'import
transactionnel réel ; `T10` livre le rapport et le rejeu d'une ligne rejetée.

# 2. Les deux points arbitrés par Jonathan, avant tout code

## 2.1 Le mécanisme de correction du rejeu

Le cahier §9.5 nomme, en deux points distincts, « import transactionnel des lignes valides »
(point 6, `T9`) puis « correction et rejeu des lignes rejetées » (point 8). Le modèle §19.5 dit
« capacité de rejouer une ligne rejetée », sans dire COMMENT la correction arrive avant le
nouvel essai — et `import_row` n'a que deux colonnes de données : `raw_data` (immuable, copie
exacte du CSV) et `normalized_data` (calculé par le pipeline, jamais écrit à la main). Aucune
colonne pour une correction saisie dans l'application.

Deux lectures possibles, posées à Jonathan avant tout code (`AskUserQuestion`) :

- **re-essayer la ligne telle quelle, à l'instant présent** — utile quand le blocage venait
  d'ailleurs que la ligne elle-même (un métier ou un cercle créé entre-temps dans le
  back-office, une décision humaine désormais enregistrée) ;
- **permettre de modifier les champs de la ligne avant de la rejouer** — un écran/une route de
  correction, qui exigerait de décider quels champs sont modifiables, de les revalider un par
  un, et d'ajouter une colonne que le modèle ne prévoit pas.

**Arbitrage retenu : la première.** Aucune correction n'est saisie dans l'application. Le CSV
corrigé à la source, puis un nouveau dépôt (`T6`/`T7`), reste le chemin normal pour une ligne
dont les DONNÉES sont fausses.

## 2.2 Le périmètre de lecture du rapport

La matrice §14 donne « Consulter le rapport » à six rôles : `ESM`/`ADM-E` Entité, `SUPER`
Global — **et aussi** `DSM` Consultants, `BOOST` Cercle limité. Mesuré avant d'écrire une ligne :
aucun document ne dit COMMENT filtrer un rapport d'import par DSM ou par cercle, et une ligne
rejetée n'a souvent **aucun** collaborateur rattaché (`target_person_id`/`target_membership_id`
restent `NULL`) — il n'existe donc aucun moyen structurel de savoir, avant qu'elle n'ait réussi,
à quel DSM ou quel cercle elle appartient. Inventer une règle (filtrer sur le contenu brut non
validé du CSV, par exemple) aurait été une heuristique sur une donnée non vérifiée (§7.25).

Posé à Jonathan : construire seulement `ESM`/`ADM-E`/`SUPER` maintenant, ou inventer une
approximation pour DSM/Booster. **Arbitrage retenu : construire seulement les trois premiers**
(`ROLES_DE_DEPOT_DE_L_IMPORT`, réutilisée — même grille que « Charger un CSV » et « Lancer
l'import »). Le volet DSM/Booster est ouvert en question, `QO-125`, plutôt qu'inventé — même
discipline que `QO-121` pour les blocs de contenu. Aucun 403 partiel : la route leur est
simplement fermée.

---

# 3. Ce que `T10` a produit

## 3.1 Le refactor partagé — `_traiter_une_ligne` (§7.27)

`rejouer_une_ligne` a besoin EXACTEMENT de la même logique que le corps par ligne de
`lancer_l_import` (`T9`) : classer une ligne en créée / mise à jour / rejetée / en attente de
décision, à partir d'une résolution fraîche d'`app.imports.organisation`. La dupliquer aurait
reproduit la classe de défaut que ce dépôt a déjà payée — une règle à deux endroits qui
divergent au premier correctif. Le corps (178 lignes) est donc extrait de `lancer_l_import` en
une fonction privée, `_traiter_une_ligne`, qui rend l'un de quatre mots
(`"importee"`/`"mise_a_jour"`/`"rejetee"`/`"en_attente"`) ; `lancer_l_import` l'appelle dans sa
boucle, `rejouer_une_ligne` l'appelle une seule fois.

## 3.2 `rejouer_une_ligne` — préconditions, portée, et le défaut trouvé en l'écrivant

Nouvelle fonction dans `app/imports/execution.py`, exposée par `POST
.../imports/{lot}/rows/{ligne}/rejeu` :

1. le lot doit être `completed` (`CODE_LOT_NON_COMPLETE` sinon) — rejouer suppose qu'un premier
   lancement a eu lieu ;
2. la ligne doit exister dans ce lot, pour cette entité (`CODE_LIGNE_INTROUVABLE` sinon, code
   réutilisé tel quel depuis `app.imports.decisions`, §7.27) ;
3. la ligne doit être `rejected` (`CODE_LIGNE_NON_REJETEE` sinon) ;
4. ses codes d'erreur actuels ne doivent porter AUCUN code `E-EMAIL-*`
   (`CODE_REJEU_HORS_PORTEE` sinon).

Le point 4 est le résultat d'une analyse de l'en-tête de `T9` (« ce que `T7`/`T8` avaient déjà
jugé n'est pas rejoué ») : `lancer_l_import` ne revalide QUE `app.imports.organisation`, jamais
les codes `E-EMAIL-*` d'`app.imports.analyse` (format, domaine, doublon technique dans le
fichier) — des rejets qui ne reviennent JAMAIS dans la boucle de lancement (une ligne déjà
`rejected` y est explicitement sautée). Une ligne rejetée uniquement par ces codes ne serait
donc jamais rendue éligible par une revalidation d'organisation seule : la `rejouer` serait un
geste qui semble agir mais ne peut jamais réussir. Le garde-fou le refuse explicitement plutôt
que de laisser l'utilisateur découvrir un rejeu systématiquement sans effet.

**Défaut trouvé et corrigé avant tout commit, dans mes propres tests.** La première version
rappelait `_traiter_une_ligne` avec les `error_codes` **existants** de la ligne (ceux qui l'ont
fait rejeter). Une fois le cercle manquant créé et la ligne rejouée avec succès, le rapport
montrait encore `E-CERCLE-002` dans ses `codes_derreur` — la ligne « réussie » restait
visiblement en échec, par la seule union `set(ligne.error_codes) | {p.code for p in
resolution.problemes}` que `_traiter_une_ligne` effectue pour préserver les avertissements entre
deux lancements. Puisque le garde-fou du point 4 garantit que TOUS les codes présents sur une
ligne rejouable viennent d'`app.imports.organisation` (`analyse.py` ne produit aucun code `W-*`,
et ses codes `E-*` viennent d'être exclus), repartir d'une liste **vide** plutôt que de
l'ancienne est correct : la fraîche revalidation d'organisation recalcule tout depuis zéro.

## 3.3 Le rejeu résout aussi le DSM — passe 2 réutilisée

Si la ligne rejouée vient d'être créée ou mise à jour et que son `F16` (e-mail du DSM) désigne
une responsabilité qui existe désormais (créée par ce même rejeu, ou par une autre ligne depuis
le dernier lancement), `_resoudre_les_dsm` (passe 2 de `T9`) est rappelée sur cette seule ligne
après le traitement. Même discipline en deux passes que `lancer_l_import`.

## 3.4 `app/imports/rapport.py` — la réconciliation est une lecture fraîche

`GET .../imports/{lot}/rapport`, nouveau module :

- **la réconciliation** (`criteres-qualite-import.md` §4) — `creations`/`mises_a_jour`/`rejets`/
  `en_attente_de_decision` — est un `GROUP BY state` sur `import_row`, **jamais** un cache.
  `RapportDeLancement` (`T9`) ne compte que ce qu'UN appel de `lancer_l_import` a fait ; ce
  rapport relit l'état RÉEL de chaque ligne, qui reste exact après n'importe quel nombre de
  rejeux, sans aucun compteur à synchroniser ;
- `en_cours` (`valid`/`warning` non encore traités) est rapporté séparément — légitime avant un
  premier lancement, hors formule du critère 8 ;
- **le fichier** : nom nettoyé, empreinte SHA-256, délimiteur (`import_batch.delimiter`, voir
  §3.5), encodage (constante `"utf-8"` — `deposer_un_csv` refuse tout le reste en 422, donc
  rien à stocker), profil de correspondance (constante aussi — une seule version provisoire en
  usage, `DEC-434`, rien à versionner par lot) ;
- **les auteurs** : `depose_par` (`created_by_person_id`), `approuve_par`
  (`approved_by_person_id`, `null` avant lancement) ;
- **les compteurs de prévisualisation** : `total_rows`/`valid_rows`/`warning_rows`/
  `needs_decision_rows`/`rejected_rows`, valeurs figées de `T6`/`T7`, rapportées telles quelles
  aux côtés de la réconciliation réelle ;
- **les lignes**, paginées (cahier §18.2, 25/50/100), chacune avec son état, ses codes
  d'erreur, et ses problèmes (`import_row_issue` : code/champ/message/niveau) — **aucune ligne
  rejetée n'est masquée**, critère de sortie du LOT 9. Aucune requête supplémentaire sur une
  page vide (même discipline que `app.people.trombinoscope`).

## 3.5 Le résidu nommé par `T6`, corrigé : `import_batch.delimiter`

L'en-tête d'`app.imports.depot` disait déjà, explicitement, depuis `T6` : « Le séparateur RETENU
n'est, à ce stade, PAS persisté dans `import_batch` — `criteres-qualite-import.md` §4 l'exige
aux côtés de l'empreinte SHA-256 dans LE RAPPORT D'IMPORT, qui est construit par `T10` ». Mesuré
avant d'écrire une ligne : zéro colonne nommée `delimiter` ou équivalent sur `import_batch`,
dans le modèle comme dans le schéma réel.

Migration `0026` : une colonne `delimiter` (`Text`, NULLABLE — un lot déposé avant cette
migration, aucun hors des tests, n'a jamais eu cette valeur consignée), avec une contrainte
`CHECK (delimiter IS NULL OR delimiter IN (';', ','))` — pas une règle de plus, mais `DEC-432`
lui-même : les deux SEULES valeurs que `_detecter_le_delimiteur` peut jamais rendre.
`_analyser_les_lignes` (`app.imports.depot`) rend désormais le délimiteur détecté en plus des
lignes parsées ; `deposer_un_csv` le consigne dans le même `INSERT` que le reste du lot.

## 3.6 Ce que ce module ne pose jamais

- **l'export du rapport** (matrice §14 « Exporter le rapport ») : explicitement hors du
  périmètre du LOT 9 (§9.4 de `CLAUDE.md`, « aucun export CSV/PDF avancé ») ;
- **le rollback complet** (matrice §14 « Rollback complet ») : `V1 uniquement`, modèle §19.5,
  roadmap V1-LOT 3 ;
- **la purge du CSV source après un délai** : `QO-100` (durée de conservation) reste ouverte et
  non bloquante ; la purge elle-même relève d'un job planifié (`async_job`), réservé au LOT 11.
  Le fichier reste disponible dans MinIO pour que ce rapport puisse s'y référer — c'est
  précisément ce que « conservation temporaire maîtrisée » (roadmap, LOT 9) signifie
  concrètement ici : un accès restreint et retenu, pas encore une suppression programmée ;
- **la lecture scopée DSM/Booster** du rapport — `QO-125`, ouverte plutôt qu'inventée (§2.2).

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q -m integration apps/api/tests/test_rapport_import.py` | **9 passés** |
| `uv run pytest -q -m integration` (les cinq fichiers d'import ensemble) | **67 passés**, 12 désélectionnés |
| `pytest` racine, sans filtre | **1 687 collectés** (+9 depuis `T9`), **74 échecs environnementaux** — la base documentée, inchangée (le 75ᵉ échec transitoire nommé par `DEC-644` reste corrigé) |
| `make test-frontend` | **794 Vitest**, inchangé |
| `make typecheck` (`mypy` + `tsc`) | vert, **231 fichiers** Python (+3) |
| `make lint`, `make format-check` | verts |
| `make sources-check` | vert, 620 fichiers examinés |
| `make isolation-check` | vert, **35 tables locales, 29 clés composites**, inchangé — une seule colonne ajoutée, aucune table |
| `make historisation-check` | vert, inchangé |
| `make parametres-check` | vert, 130 partages légitimes |
| `make migrations-check` | vert, tête `0026` (+1), chaîne rejouée identique |
| `make docs-check` | vert, 12 contrôles — registres et passation mis à jour en même temps que le code |
| `uv run pytest -q apps/api/tests/test_contrat.py` | vert après ajout des deux entrées (`rejouerUneLigneDImport`, `consulterLeRapportDImport`) |
| `make api-check` (pile réelle) | vert, trois endpoints de santé |

## 4.1 Deux défauts trouvés en construisant `T10`, tous deux corrigés avant commit

1. **L'union avec l'historique masquait un rejeu réussi** — voir §3.2. Corrigé en repartant
   d'une liste de codes vide dans `rejouer_une_ligne`.
2. **Un nom/prénom par défaut identique sur plusieurs lignes du même décor de test déclenchait
   `D-PERSONNE-003` (homonymie) sans rapport avec ce que le test observait** — même piège déjà
   rencontré dans `test_import_transactionnel.py` (`T9`). Corrigé en variant le prénom par ligne
   dans mon propre décor. Rappelé ici parce que c'est la DEUXIÈME fois que ce piège se rejoue
   dans ce lot : un décor à plusieurs lignes du même fichier doit varier nom ET prénom, pas
   seulement l'e-mail.

---

# 5. Décisions et écarts

- `DEC-645` consigne les deux arbitrages de Jonathan (§2), le refactor partagé, le défaut
  corrigé (§3.2), et le résidu de `T6` corrigé (§3.5) ;
- `QO-125` est ouverte : filtrage du rapport d'import pour DSM/Booster, non résolue, non
  bloquante pour `T10` ;
- aucun écart n'est ouvert : `US006` est désormais **fermée** dans ses deux moitiés.

---

# 6. Ce que `T10` laisse

- `US006` est fermée — issue `#240` à fermer à la main après fusion, avec les preuves de ce
  compte rendu ;
- aucun écran ne consomme encore ces deux routes (aucun consommateur avant `T14`, premier et
  seul écran du lot — même discipline que les routes de `T2`/`T3`/`T5` restées sans écran
  jusqu'ici) ;
- `QO-100` (durée de conservation du CSV source) et `QO-125` (lecture scopée DSM/Booster du
  rapport) restent ouvertes et non bloquantes ;
- `ECART-012`, `ECART-068` restent ouverts, non bloquants pour `G9` ;
- `ECART-035` (invitations) reste explicitement à fermer dans ce lot — `T13` du découpage.

# Validation demandée à Jonathan

`T10` est faite. `US006` ferme. Après fusion, la prochaine sous-étape est `T11` : les
opérations de masse contrôlées (prévisualisation d'impact, idempotence, erreurs partielles
explicites), `US003`, `P1`, dépend de `T2`/`T3`.
