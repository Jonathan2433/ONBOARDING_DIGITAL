# Compte rendu — `T2` du LOT 8 : lecture des événements à venir et passés

**Sous-étape :** la deuxième du lot — lecture paginée autour de `ends_at`  
**Date :** 4 octobre 2026  
**Décision :** `DEC-621`  
**Story :** `MVP-L08-US003` (première moitié ; l'écran reste à `T9`)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | **`T1` et `T2`** |
| Restent | `T3` à `T14` |
| Prochaine | `T3`, après résolution explicite d'`ECART-067` |
| Issues | épic `#206`, story `#209` encore ouverte jusqu'à l'écran de `T9` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/events/lecture.py` | classement temporel, filtrage, ordre total et pagination |
| `apps/api/app/events/routes.py` | `GET /api/v1/entities/{code}/events` et ses formes Pydantic |
| `apps/api/app/main.py` | montage du routeur sous `/api/v1` |
| `packages/contracts/src/contrat-api.json` | endpoint, codes exploitables et justification des droits |
| `apps/api/tests/test_lecture_evenements.py` | **12 tests**, dont **9 d'intégration** |

## 2.1 Une frontière temporelle unique

Le pseudo-état « passé » reste absent de la base. Le service reçoit un `instant` et applique deux
prédicats complémentaires :

- `ends_at > instant` → `a_venir`, y compris lorsqu'un événement a déjà commencé ;
- `ends_at <= instant` → `passes`, y compris lorsque la fin est exactement égale à l'ancre.

Le total et les éléments de la page réutilisent le même paramètre `instant` dans la même
transaction. Le témoin central pose trois événements de part et d'autre de la borne et exige que
leur somme reste égale à trois : aucun trou ni double classement n'est possible.

## 2.2 Annulé visible, brouillon et archive absents

La consultation publique filtre `state IN ('published', 'cancelled')` et `archived_at IS NULL`.
Un événement annulé reste donc présent avec `etat`, `annule_le` et `motif_d_annulation`, ce qui
permettra le badge de `T9`. Un événement `draft`, `archived`, ou seulement marqué par
`archived_at`, est absent. Le service n'anticipe ni restauration (`T5`), ni médias (`T6`).

## 2.3 La lecture n'a aucune grille de rôle locale

La matrice générale §5 et la section événementielle §11 concordent : les huit rôles authentifiés,
`EMP` et `NEW` compris, consultent. La route exige donc une session et ne résout aucun rôle. Un
témoin emploie une personne sans appartenance ni responsabilité dans l'entité cible et reçoit
`200` : RIGHTS-003, la lecture inter-entités, est ainsi éprouvée directement. L'isolation des
données reste assurée par le filtre `event.entity_id = :entite`.

## 2.4 Pagination sans nouvelle source

La route réutilise `TailleDePage` et `TAILLE_PAR_DEFAUT` de `app.shared.pagination` : 25 par
défaut, puis 50 ou 100, conformément au cahier §18.2. L'ordre est total : début puis identifiant
pour les événements à venir ; fin décroissante puis identifiant pour les passés.

---

# 3. Défaut trouvé avant fusion

`T2-1` — le premier décor réutilisait `:etat` à la fois pour la colonne `state varchar(16)` et
dans une expression `CASE` comparée à un littéral `text`. PostgreSQL a refusé avec
`inconsistent types deduced for parameter`, reproduisant exactement la classe du §7.25 de la
passation. Le décor calcule désormais `annule_le` et `motif_d_annulation` avant la requête et les
lie par des paramètres distincts. Aucun code produit n'était concerné.

`T2-2` — la première CI de la PR a révélé une bombe temporelle dans cinq suites du LOT 7 : leurs
dates métier étaient volontairement figées au 25/26 septembre, mais leurs sessions réutilisaient
la même ancre. Le 4 octobre, elles dépassaient pour la première fois les sept jours d'inactivité et
**98 tests** rendaient `401`, sans aucun résidu. Les dates métier restent déterministes ; seule la
création de session prend désormais l'heure réelle d'exécution. La seconde CI prouve la correction
sur une base reconstruite.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_lecture_evenements.py` | **12/12** |
| `make test-unit` | **387/387** |
| `uv run pytest -q --collect-only` depuis la racine | **1 442 pytest** |
| `uv run pytest -m integration -q --collect-only` depuis la racine | **1 055 d'intégration** |
| `make test-frontend` | **706/706** — 336 contrats, 111 UI, 259 web |
| `make format-check`, `make lint`, `make typecheck` | verts |
| `make docs-check`, `make sources-check` | verts |
| `make isolation-check` | **30 locales, 24 composites, zéro référence nue** |
| `make migrations-check` | tête `0022`, chaîne rejouée, schéma identique |

Le total du projet est désormais **2 148 tests** : 1 442 pytest et 706 Vitest. Aucun test
frontend n'est ajouté à cette sous-étape, l'écran étant explicitement séquencé à `T9`.

---

# 5. Ce que `T2` laisse

- `MVP-L08-US003` est servie côté API mais reste ouverte jusqu'à son écran de `T9` ;
- aucune route d'écriture, aucune grille de création et aucun rattachement n'ont été anticipés ;
- `ECART-067` devient le préalable bloquant de `T3` : le DSM a « Entité ou consultants », mais
  le modèle ne représente pas une portée consultants ;
- `ECART-068` reste intact et devra être résolu avant de fermer `US004`.

# Validation demandée à Jonathan

`T2` est techniquement faite. Après fusion, la prochaine action n'est pas de coder immédiatement
`T3`, mais de faire arbitrer `ECART-067`, puis d'implémenter la création dans le périmètre validé.
