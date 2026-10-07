# Compte rendu — `T14` du LOT 8 : recette, §30 et checklist `G8`

**Sous-étape :** la quatorzième et dernière du lot — recette sur les images publiées,
relecture exécutable des 25 contrôles du §30, non-régression comparée à `origin/develop`,
préparation de la checklist `G8`
**Date :** 7 octobre 2026
**Décision :** `DEC-633`
**Branche :** `codex/lot8-t14-recette-g8`, depuis `develop` à jour (`3f5e542`, fusion de `T13`, PR #226)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1` à `T13`, **`T14`** |
| Reste | la décision de porte elle-même — `G8` n'est **pas** déclarée franchie ici : le corpus exige la validation explicite de Jonathan (critère de sortie 6) |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Sous-étape en cours

`T14` clôture techniquement le lot : recette sur les images publiées de la révision `3f5e542`
(fusion de `T13`), relecture des 25 contrôles du §30 du modèle immuable, non-régression comparée
à `origin/develop`, et préparation de la checklist `G8` — [`checklist-validation-G8.md`](checklist-validation-G8.md).

---

# 3. Travail réalisé

- Recette réinitialisée uniquement sur son volume PostgreSQL, démarrée sur les images publiées
  de `3f5e542` (`make images-pin`), migrée jusqu'à la tête `0023`.
- Les 8 services recette sains, 7 publications `127.0.0.1` sur 7 attendues, les 3 conteneurs
  applicatifs tournant nativement en `aarch64` sur l'artefact **publié** (jamais une construction
  locale).
- `make accueil-check ENVIRONNEMENT=recette` et `make onboarding-check ENVIRONNEMENT=recette`
  rejoués sur la recette : les mêmes témoins qui ont prouvé les permissions des LOTS 7 et 8 en
  développement tiennent sur l'artefact publié, à travers Caddy en HTTPS.
- `make recette-modele-check` relu : le classement du §30 est **inchangé** depuis `G7` — et c'est
  une mesure, pas un oubli (§3.1 ci-dessous).
- Checklist [`checklist-validation-G8.md`](checklist-validation-G8.md) créée, séparant les cinq
  preuves techniques de la validation humaine encore à recueillir (critère de sortie 6).
- Un résiduel nommé explicitement pour le critère de sortie 2 — voir §3.2.

## 3.1 Le §30 n'a RIEN à reclasser, et c'est vérifié, pas supposé

`T15` du LOT 7 avait reclassé trois contrôles du §30 (`§30.13` à `§30.15`) que ses propres
sous-étapes avaient livrés. La tentation, à la clôture d'un lot, est de supposer qu'un geste
pareil se reproduit systématiquement. **Ce n'est pas le cas ici, et seule une relecture des 25
libellés le prouve** : aucun des 25 contrôles du §30 ne porte sur les tables événementielles —
`event`, `event_circle_scope`, `event_office_scope`, `event_media`, `event_dsm_scope`, ni sur
l'accueil. Le classement reste **16 acquis, 2 partiel, 7 reportés, 0 inapplicable**, identique à
celui que `G7` a validé. `make recette-modele-check` le confirme en sortant à `0` sans qu'aucune
ligne de `infra/scripts/verifier-recette-modele.py` n'ait changé.

## 3.2 Le critère de sortie 2 n'est PAS tenu par absence de preuve — il est SANS OBJET, et c'est écrit

Le critère de sortie 2 de la fiche LOT 8 (§1.2) dit : « aucune vidéo complète n'est téléchargée
avant interaction — test navigateur/réseau à `T12` ». `T12` a explicitement **reporté** `US005`
(`DEC-631`) : aucune fixture, aucune route, aucun composant du dépôt n'exerce jamais un bloc de
type `VIDEO` en dehors de son existence dans l'énumération `TypeDeBloc` (`DEC-592`, LOT 6).

**Déclarer ce critère « Tenu » serait exactement le défaut que le §7.39 de la passation nomme** :
un critère négatif — « rien n'est téléchargé » — est satisfait de façon triviale par une
fonctionnalité qui n'existe pas. Un contrôle qui l'exercerait ne pourrait jamais échouer, donc il
ne prouverait rien (§7.0, quatrième proposition). La checklist `G8` le classe donc **SANS OBJET**,
distinctement d'un critère « Tenu » — la distinction est nommée à Jonathan au §1 de la checklist,
pas laissée implicite.

---

# 4. Contrôles exécutés

| Contrôle | Résultat relevé le 07/10/2026 |
|---|---|
| `make recette-check` | 57 contrôles, 0 échec ; 7/7 séparations effectives |
| `make api-check ENVIRONNEMENT=recette` | 3 endpoints de santé répondent, révision `3f5e542` |
| `make web-check ENVIRONNEMENT=recette` | 7 contrôles, 0 échec ; artefact `/assets/` servi, aucun serveur Vite |
| `make accueil-check ENVIRONNEMENT=recette` | **29 contrôles, 0 échec** — grille à deux visages du DSM, asymétrie entre deux Boosters, `ARB-DROIT-003` dans le sens du refus (×2), classement temporel réel, fenêtre réelle des arrivées récentes |
| `make onboarding-check ENVIRONNEMENT=recette` | 14 contrôles, 0 échec — asymétrie DSM/ESM, cycle de vie complet, `ECART-066` dans le sens du refus |
| `make recette-modele-check` | 25 contrôles classés : 16 acquis, 2 partiel, 7 reportés, 0 inapplicable — **inchangé depuis `G7`** |
| `make check` (qualité complète) | Ruff format/check, Prettier, ESLint, `mypy` (197 fichiers), `tsc --noEmit` (3 workspaces) : **tous verts** |
| `uv run pytest -q` depuis la racine | 1 564 collectés, **74 échecs environnementaux** (jeu de démonstration de développement, 33 entités/5 169 personnes), identiques en liste à ceux mesurés avant `T13` |
| `make test-frontend` | 794 Vitest : 380 `contracts`, 120 `ui`, 294 `web` — inchangé |
| `make audit` | zéro avis, `pip-audit` et `pnpm audit` : aucune vulnérabilité connue |
| `git status` | aucun fichier Python ni frontend touché — seule la documentation change |

Les 74 échecs `pytest` viennent du jeu de démonstration chargé sur la base de développement
(§11 de la passation : « NE RÉINITIALISE PAS LA BASE SANS L'ACCORD DE JONATHAN »). Ils comptent
des lignes en **absolu** — `assert 5171 == 2`, par exemple — et sont identiques, un par un, à ceux
déjà mesurés avant `T13` : aucune ligne Python applicative n'a changé entre les deux mesures,
`git status` le confirme structurellement.

---

# 5. Résultats

La recette exerce réellement l'artefact publié de `3f5e542`, pas le code local : les trois
conteneurs applicatifs tournent sur l'empreinte **demandée** par `.env.recette`, jamais sur une
reconstruction, et nativement en `aarch64` (réserve de la fiche `fiche-lot-1.md` §3.1, levée
depuis `T8` du LOT 1 et reconfirmée ici).

Le démarrage a rencontré le même conflit de port `8080` que `T15` du LOT 7, avec le même projet
tiers `observatoire-ecom-studio` : son seul conteneur `web` a été arrêté le temps du démarrage,
puis relancé. Caddy, créé pendant ce conflit sans ses publications réelles (§7.17 de la
passation), a été recréé par `make caddy-recreate ENVIRONNEMENT=recette` ; les sept ports
effectifs ont ensuite été mesurés par `make recette-check`.

Les 29 contrôles de `make accueil-check` et les 14 de `make onboarding-check` tiennent
**identiquement** sur la recette et sur le développement : aucune des permissions prouvées par
`T13` du LOT 8 ni `T14` du LOT 7 ne dépend d'un artefact construit localement.

---

# 6. Décisions ajoutées ou modifiées

- `DEC-633` — recette `T14`, confirmation du classement du §30 et préparation de `G8`.

Aucune autre décision n'est ajoutée : `T14` ne modifie aucun code applicatif.

---

# 7. Risques et écarts

- `ECART-012` (statut professionnel d'une direction générale) reste à décider par Léa, non
  bloquant pour la porte technique.
- `ECART-068` (audit de modification/publication/annulation/archivage, domaine `audit_event` du
  LOT 10) reste ouvert et borne `US004` — la story reste ouverte au registre des issues jusqu'à sa
  résolution, comme documenté depuis `T5`.
- `QO-121` (vocabulaire de `payload_json` par type de bloc) reste ouverte ; c'est elle qui rend le
  critère de sortie 2 sans objet plutôt que tenu — voir §3.2.
- `ROAD-RSK-033` et `ROAD-RSK-034` restent à réévaluer avant le LOT 13, inchangés par ce lot.

Aucun écart nouveau n'est ouvert par `T14`.

---

# 8. Questions ouvertes

Comme à `G7`, le canal de recueil des validations nominatives n'est nommé dans aucun document de
cadrage pour ce lot — ici un seul valideur, Jonathan, le cahier ne nommant personne d'autre pour
les événements et l'accueil. La checklist le dit explicitement plutôt que de l'omettre.

---

# Validation demandée à Jonathan

`T14` est techniquement prête à fusionner — elle ne modifie aucun code applicatif, seulement la
documentation de clôture. Une fois fusionnée, le dernier geste du lot est ta validation du
critère de sortie 6 : peux-tu lire [`checklist-validation-G8.md`](checklist-validation-G8.md) et
confirmer si `G8` peut être déclarée franchie ? Cette décision sera consignée séparément
(`DEC-634` probable), comme `DEC-617` l'a été pour `G7` après validation.

```bash
gh pr merge <n> --squash --delete-branch   # fusion de T14 après validation
gh pr close <n> --delete-branch            # retour arrière avant fusion
```
