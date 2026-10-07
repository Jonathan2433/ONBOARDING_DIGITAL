# Compte rendu — `T10` du LOT 8 : l'écran de gestion des événements

**Sous-étape :** la dixième du lot — créer, modifier, publier, annuler, archiver,
restaurer et rattacher des médias, à l'écran
**Date :** 5 octobre 2026
**Décision :** `DEC-629`
**Story :** `MVP-L08-US004`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1` à `T9`, **`T10`** |
| Restent | `T11` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Un trou trouvé en construisant l'écran, pas anticipé par la fiche

`T2` (lecture, `DEC-621`) ne sert que les événements `published`/`cancelled` —
exactement ce qu'exige la consultation (`US003`). Un écran de **gestion** doit
pourtant retrouver un **brouillon** (pour le publier) et un **archivé** (pour le
restaurer), et aucune route n'en rendait jamais la `version`, dont toute
écriture a besoin pour la concurrence optimiste du §18.4.

**Même motif exactement que `/pages/gestion` au LOT 6 (`T10`)**, et la fiche de
LOT 6 ne l'avait pas davantage anticipé — un même trou, retrouvé deux lots plus
tard, pour la même raison structurelle : une lecture publique et une lecture de
gestion ne sont jamais la même route. `T10` pose donc deux routes nouvelles,
non prévues par le découpage initial mais découlant directement de son
critère :

- `GET /entities/{code}/events/gestion` — tous les événements, tous états,
  garde **coarse** seule (`ROLES_DE_CREATION_EVENEMENT`), même parti que
  `/pages/gestion` : un Booster voit tous les événements de son entité, mais ne
  pourra **ouvrir** que le sien ;
- `GET /entities/{code}/events/{evenement}/gestion` — un événement et ses
  rattachements (cercles, bureaux, médias), avec sa `version` ; périmètre
  **complet** résolu par `resoudre_le_perimetre_de_l_evenement` (la même
  fonction que `PUT …/events/{evenement}`), 403 `acces_refuse` si l'ensemble
  d'actions est vide — **un seul gabarit**, même discipline que les six verbes
  d'écriture : un événement inconnu et un rôle sans aucun droit rendent le
  **même** refus, jamais un 404 distinct.

Aucune migration : les deux routes ne lisent que le schéma posé par `T1`/`T3`.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/events/lecture.py` | `lister_les_evenements_pour_gestion`, `lire_un_evenement_pour_gestion`, `EvenementDeGestion`, `EvenementPourGestion`, `MediaDeGestion` |
| `apps/api/app/events/routes.py` | les deux routes `GET …/events/gestion` et `GET …/events/{evenement}/gestion`, leurs modèles de réponse |
| `apps/api/tests/test_gestion_evenements.py` | **17 tests** (5 structurels + 12 d'intégration) |
| `packages/contracts/src/contrat-api.json` | 2 nouveaux `endpoints` (`listeDesEvenementsPourGestion`, `lectureDUnEvenementPourGestion`), 2 nouvelles grilles de rôles (`rolesGestionDesEvenements`, `rolesRestaurationDUnEvenement`) |
| `packages/contracts/src/evenements.ts` | tout le côté écriture : types et validateurs pour les 6 verbes et les 2 lectures de gestion, `peutGererLesEvenements`, `peutRestaurerUnEvenement` |
| `packages/contracts/src/evenements.test.ts` | **+15 tests** |
| `packages/contracts/src/index.ts` | réexports étendus |
| `apps/web/src/api/evenements.ts` | `ecrire<T>` (même montage que `administration.ts`), les 9 fonctions d'écriture et de lecture de gestion |
| `apps/web/src/pages/PageGestionDesEvenements.tsx` | le sommaire (tous états) + la création — `versDatetimeLocal`/`depuisDatetimeLocal` |
| `apps/web/src/pages/PageGestionDesEvenements.test.tsx` | **6 tests** |
| `apps/web/src/pages/PageEditionEvenement.tsx` | l'édition : champs, cercles/bureaux, médias, cycle de vie |
| `apps/web/src/pages/PageEditionEvenement.test.tsx` | **7 tests** |
| `apps/web/src/pages/PageEvenements.tsx` | lien « Gérer les événements », gardé par `peutGererLesEvenements` |
| `apps/web/src/routes.ts`, `App.tsx` | deux routes nouvelles : `gestionDesEvenements`, `editionEvenement` |
| `apps/web/src/pages/application.css` | classes `.evenements-gestion-*`, `.evenements-edition-*` |

## 3.1 Deux grilles de rôles, jamais fusionnées

`rolesGestionDesEvenements` (DSM/ESM/BOOST/OFFICE/ADM-E/SUPER) est
`ROLES_DE_CREATION_EVENEMENT` — le même ensemble qui garde déjà les six verbes
d'écriture côté API. `rolesRestaurationDUnEvenement` (ESM/ADM-E/SUPER) est
`ROLES_DE_PORTEE_ENTITE` — la ligne « Restaurer » du §11, qui exclut DSM/BOOST/
OFFICE **en bloc**, `ARB-DROIT-003`. Les fusionner proposerait un bouton
« Restaurer » que l'API refuserait pour trois des six rôles — l'avertissement
faux du §7.21 de la passation. Les deux clés sont confrontées, dans les deux
sens, aux constantes Python par un test (`test_gestion_evenements.py`),
`DEC-492`.

## 3.2 Le frontend n'est pas l'autorité — deux fois de plus

Un rôle suffisant pour `peutGererLesEvenements` peut recevoir un **403** : la
portée locale (son cercle, son bureau, ses consultants nommés dans
`event_dsm_scope`) n'est résolue que par l'API. Un DSM qui a seulement **créé**
un événement de portée Entité voit les boutons Publier/Annuler/Archiver/
Médias, mais sera refusé — seule la grille « Périmètre » (ses consultants
nommés) les ouvre, jamais « créé par lui » seul. Même discipline, documentée au
même endroit, que `PanneauEditionDeContenu.tsx` (LOT 6) pour un Booster sur une
page de contenu.

## 3.3 Aucun `Date`, dans aucun sens — la première saisie de date-heure du dépôt

`T9` lisait des dates ISO servies par l'API en segments à position fixe,
jamais par `Date`. `T10` est le **premier** écran à en **écrire** : un
`<input type="datetime-local">` rend/attend `YYYY-MM-DDTHH:mm`, exactement le
préfixe d'une chaîne ISO. `versDatetimeLocal`/`depuisDatetimeLocal` ne
convertissent donc **rien** — ils découpent et recomposent la chaîne, avec un
décalage `+00:00` explicite et fixe. Un `new Date()` ici réinterpréterait la
saisie dans le fuseau du navigateur, exactement le défaut que `dateComplete`
évite déjà en lecture ; rester cohérent exigeait de l'éviter aussi en écriture.
Un test (`PageGestionDesEvenements.test.tsx`) prouve que les deux fonctions
sont l'inverse exacte l'une de l'autre.

## 3.4 `cercles`/`bureaux` : un champ texte, pas un sélecteur inventé

Aucun composant de sélection de cercle ou de bureau n'existe dans ce dépôt — en
livrer un sans un second écran qui le réemploie serait du code non éprouvé,
même principe que l'absence de primitive d'onglets (`T9`). Un champ texte
« codes séparés par des virgules » restitue exactement les trois états que
l'API distingue : vide envoie `[]` (vide la liste), un ou plusieurs codes la
remplacent — jamais de distinction `None`/`[]` artificielle côté écran,
puisque l'écran envoie toujours un tableau concret.

## 3.5 Les médias : rattachement seul, aucun téléversement

Même principe que l'API (`T6`) : le champ « Identifiant du média » suppose un
`media_asset` déjà `ready` dans cette entité — une médiathèque n'existe pas
encore (LOT 11). La liste REMPLACE la liste complète à chaque « Enregistrer les
médias », `display_order` valant l'index du tableau envoyé — jamais un
décalage calculé, piège `T8-1` du LOT 6.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q --collect-only` | **1 564** (+17), dont **1 157** d'intégration (+12) |
| `uv run pytest -q apps/api/tests/test_gestion_evenements.py` | 17/17 |
| `uv run pytest -q -k evenement` | **136/136**, inchangé pour `T1`-`T9`, +17 pour `T10` |
| `uv run pytest -q` (suite complète) | **1 490 passed, 74 failed** — les 74 sont les échecs environnementaux du jeu de démo, aucun sur `evenement`/`gestion` (confirmé par `grep -i evenement` sur les échecs) |
| `uv run mypy` (depuis la racine) | vert, **197** fichiers (+1) |
| `uv run ruff check .` / `ruff format --check .` | vert |
| `pnpm --filter @onboarding/contracts test` | **367/367** (+15) |
| `pnpm --filter web test` | **279/279** (+13) |
| `pnpm --filter @onboarding/ui test` | **111/111**, inchangé |
| `pnpm run typecheck` (tsc, 3 paquets) | vert |
| `pnpm run lint` / `pnpm run format:check` | vert |
| `python3 infra/scripts/verifier-cadre.py` | **25 contrôles, 0 échec** |
| `python3 infra/scripts/verifier-sources-suivies.py` | OK |
| `python3 infra/scripts/verifier-documentation.py` | 5 documents immuables intacts, séquences cohérentes |
| **aller-retour réel** (§7.43) | décor psql réel (entité `T10DEMO`, ESM `t10-verification@exalt-company.com`, cercle `DATA`, média `ready`), lien magique réel consommé, cycle complet à travers Caddy/HTTPS : créer (brouillon) → publier (v2) → archiver (v3) → restaurer (v4, redevient brouillon) → modifier avec cercle rattaché (v5) → rattacher un média (v6), vérifié à chaque étape par relecture de l'écran — desktop **et** mobile (375 px) — décor nettoyé après coup |
| **témoin de frontière** | l'événement en cours de gestion (brouillon) reste **absent** de l'écran de consultation publique (`T9`), confirmé après rechargement |

**Zéro régression** : le total pytest/Vitest passe de **2 276** à **2 321**
(+45 : +17 pytest, +15 `contracts`, +13 `web`), et les 74 échecs pytest restants
sont identiques, en nature et en nombre, à ceux déjà documentés comme
environnementaux (jeu de démo chargé sur la base de dev) — aucun ne porte sur
les événements.

---

# 5. Décisions

- `DEC-629` consigne la réalisation de `T10` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact, ouvert — la
  matrice exige un audit de la modification/publication/annulation/archivage,
  et `audit_event` reste au LOT 10 (de pilotage, à ne pas confondre avec ce
  LOT 8). `T10` n'anticipe rien à ce sujet.

---

# 6. Ce que `T10` laisse

- l'écran de gestion complet : créer, modifier, publier, annuler, archiver,
  restaurer, rattacher des médias — les sept verbes de la matrice §11 ;
- deux routes API nouvelles, posées en construisant l'écran plutôt
  qu'anticipées par le découpage, suivant le précédent exact de
  `/pages/gestion` au LOT 6 ;
- `T11`/`T12` (accueil final desktop puis mobile) consommeront l'agrégat de
  `T8`, qui compose déjà la section « événements à venir » — rien à changer
  ici pour eux ;
- `T13` (contrôle de pile réelle) devra couvrir la gestion des événements au
  même titre que les autres écrans — aucun script `make evenements-check`
  n'existe encore pour la gestion, seulement pour la consultation (`T9`,
  6 contrôles déjà dans `make check`) ; `T13` est le moment prévu pour
  l'étendre, même parti que `make onboarding-check` combiné au LOT 7.

# Validation demandée à Jonathan

`T10` est faite. Après fusion, la prochaine sous-étape est `T11` : l'accueil
final desktop.
