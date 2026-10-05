# Compte rendu — `T7` du LOT 8 : les arrivées récentes

**Sous-étape :** la septième du lot — `GET /entities/{code}/arrivees-recentes`
**Date :** 5 octobre 2026
**Décision :** `DEC-626`
**Story :** `MVP-L08-US002`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, **`T7`** |
| Restent | `T8` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/onboarding/arrivees_recentes.py` | `lister_les_arrivees_recentes`, `ArriveeRecente`, `PageDesArriveesRecentes` |
| `apps/api/app/onboarding/routes.py` | `GET /entities/{code}/arrivees-recentes`, `ArriveeRecenteRendue`, `ReponseDesArriveesRecentes` |
| `apps/api/tests/test_arrivees_recentes.py` | **20 tests** — structure (3), service (14 marqués `integration`), route HTTP (3 marquées `integration`) |
| `packages/contracts/src/contrat-api.json` | entrée `arriveesRecentes` |

Aucune migration : `T7` lit `arrival_profile`, posée par `T1` du LOT 7.

## 2.1 La fenêtre de visibilité est `[published_at, recent_until]`, pas `[arrival_date, recent_until]`

Le cahier §10.5 dit littéralement : « La fiche peut être publiée après validation, y compris
avant la date d'arrivée. Le nouvel arrivant apparaît dans la section « Ils nous ont rejoints
récemment » pendant un mois après sa date d'arrivée. » Le backlog (`MVP-L08-US002`) le confirme :
« Une fiche validée apparaît IMMÉDIATEMENT ; elle quitte automatiquement la section un mois après
la date d'arrivée. »

Une lecture rapide aurait pu conclure que la visibilité ne commence qu'À l'arrivée. C'est faux :
le modèle autorise explicitement la publication par anticipation (état `future` de
l'appartenance), et le backlog dit « apparaît immédiatement », pas « apparaît à l'arrivée ». Le
service filtre donc sur `ETATS_OCCUPANTS` (`future` ET `active`) — exactement la population déjà
retenue par `lire_la_fiche_arrivee` (`T2` du LOT 7) — et non sur `ETAT_LISTE` (`active` seul) du
trombinoscope, qui exclurait à tort une fiche publiée en avance. Un témoin le prouve directement :
`test_TEMOIN_une_fiche_publiee_AVANT_l_arrivee_apparait_immediatement` pose une appartenance
`future`, arrivée dans dix jours, fiche `published`, et vérifie qu'elle apparaît dès maintenant.

## 2.2 Ni métier, ni statut, ni cercle, ni photo — un test fige l'absence, pas un oubli

La matrice §5 donne « Arrivées récentes » en Lecture aux **huit** rôles authentifiés, sans
exception — y compris le DSM, qui est pourtant à **TIRET** sur « Consulter les informations
préremplies » (métier/statut/client/DSM/cercle, §7) ailleurs dans la même matrice. Exposer ces
champs dans la réponse de `T7` donnerait donc à **tout** rôle une porte dérobée vers une
information que la matrice lui refuse explicitement par une autre ligne — l'inverse de la règle
§6.5 : au lieu de combler un vide par une invention, ce serait **élargir un droit** en silence.

« Arrivées récentes » est donc une ressource différente de la fiche complète : c'est la « page web
de présentation » du §10.5, dont le contenu décidé est l'identité, la date d'arrivée, la
présentation courte et le fun fact — rien d'organisationnel.

`test_la_reponse_ne_porte_NI_metier_NI_statut_NI_cercle_NI_photo` fige cette décision
structurellement (§7.32) : si un lot ultérieur veut exposer l'un de ces champs, il devra casser ce
test, donc le décider explicitement plutôt que de l'ajouter en passant.

**Aucune photo non plus, et pour la même raison que `T2` du LOT 7.** `arrival_profile.photo_media_id`
existe au modèle (§12.1), mais aucune route du dépôt ne l'écrit — mesuré, zéro occurrence hors de
sa déclaration. Résoudre une colonne que rien ne remplit aurait servi un champ structurellement
toujours `null`, un code mort qu'aucun test ne peut distinguer d'un défaut. `resoudre_la_miniature`
(LOT 5) reste borné à la population du trombinoscope pour la même raison que `lire_la_fiche_arrivee`
l'a laissé de côté : à réexaminer quand un écran (`T9` à `T12`) en aura réellement besoin.

## 2.3 L'ancre est injectée, et la frontière de `recent_until` est éprouvée au jour près

`recent_until` est une colonne `date`, écrite une fois à la publication (`T3` du LOT 7,
`arrival_date + INTERVAL '1 month'`). Le service la compare à `instant.date()` — jamais un `now()`
caché dans le SQL — ce qui rend la frontière contrôlable par un test :
`test_TEMOIN_la_frontiere_exacte_de_recent_until` pose deux fiches dont seule la valeur de
`recent_until` diffère d'un jour (l'une égale à l'ancre, l'autre à l'ancre moins un jour) et prouve
que seule la première reste visible.

## 2.4 Même discipline de population que le trombinoscope, pour les deux colonnes qui restent

`profile_visibility` (`draft`/`hidden` exclus, `published` seul visible) et `membership_state`
(`departed`/`archived` exclus par construction via `ETATS_OCCUPANTS`) sont vérifiés indépendamment
l'un de l'autre — aucun n'est redondant, même raisonnement que celui déjà tenu pour le trombinoscope
(LOT 5, `T2`) : un partant resterait `published` si l'on ne filtrait que l'état d'appartenance, et un
nouvel arrivant `draft` serait listé avant d'exister publiquement si l'on ne filtrait que la
visibilité.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make migrations-check` | tête `0023` inchangée, schéma identique |
| `make isolation-check` | **31 locales, 25 composites** — inchangé, `T7` n'ajoute aucune table |
| `make sources-check` | OK |
| `uv run pytest -q tests/test_arrivees_recentes.py` | **20/20** |
| `uv run pytest -q tests/test_evenements.py tests/test_creation_evenements.py tests/test_modification_et_publication_evenements.py tests/test_annulation_archivage_et_restauration_evenements.py tests/test_medias_evenements.py tests/test_lecture_evenements.py tests/test_fiche_arrivee.py tests/test_validation_de_la_fiche_arrivee.py tests/test_contrat.py` | **168/168** |
| `make format-check`, `make lint`, `make typecheck` (depuis la racine) | verts |
| collecte depuis la racine | **1 541 pytest**, dont **1 139 d'intégration** (+20, dont +17 d'intégration) |
| frontend | **706 Vitest** inchangés — aucun écran ne consomme encore les arrivées récentes |
| **zéro régression** | `git worktree` sur `origin/develop` (après fusion de `T6`), même base, `.env` copié : **74 échecs identiques des deux côtés** (jeu de démo, comptes en absolu) |

---

# 4. Décisions

- `DEC-626` consigne la réalisation de `T7` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact, ouvert — sans objet direct ici,
  cette sous-étape ne porte aucune écriture.

---

# 5. Ce que `T7` laisse

- la lecture paginée des arrivées encore dans leur fenêtre d'un mois, dans la portée exacte de la
  matrice (tous rôles authentifiés) ;
- aucune information organisationnelle ni photo exposée — décision structurelle, voir §2.2 ;
- aucun écran, aucun consommateur : `T8` (agrégat API de l'accueil) appellera directement
  `lister_les_arrivees_recentes`, sans recopier son filtre ; les écrans arrivent à `T9`-`T12`.

# Validation demandée à Jonathan

`T7` est faite. Après fusion, la prochaine sous-étape est `T8` : l'agrégat API de l'accueil.
