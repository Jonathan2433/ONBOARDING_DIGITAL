# Compte rendu — `T13` du LOT 8 : le contrôle de pile réelle événements et accueil

**Sous-étape :** la treizième du lot — `make accueil-check`, un script qui exerce la matrice
§11 et le cahier §8.4/§10.5/§10.6 à travers Caddy, en HTTPS, sur les conteneurs réellement
en marche
**Date :** 6 octobre 2026
**Décision :** `DEC-632`
**Stories :** transversale — `MVP-L08-US002`, `US003`, `US004` (aucune nouvelle route, aucun
nouveau critère ; `T13` prouve ce que `T1` à `T12` ont déjà livré, sur la pile réelle)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1` à `T12`, **`T13`** |
| Reste | `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Ce que ce contrôle prouve, et pourquoi pytest ne le prouve pas déjà

`test_evenements.py` et `test_accueil.py` éprouvent chaque règle de la matrice §11 et du
cahier §8.4 via `TestClient` — la même application Python, en mémoire. Un contrôle de pile
réelle passe par **Caddy, en HTTPS, sur les conteneurs réellement en marche** : c'est la
seule manière de prouver que le mandatement (`DEC-470`), le conteneur `api` à jour
(`make code-refresh`) et les cookies `Secure`/`SameSite` du LOT 3 sont tous en jeu en même
temps — §7.28 de la passation, une cible statique ne prouve rien de ce qu'un conteneur sert
réellement. Même motif exactement que `verifier-administration-onboarding.py` (LOT 7, `T14`)
pour l'onboarding.

**Aucune route nouvelle, aucune migration.** `T13` ne construit qu'un script de vérification
et l'inscrit dans `make check`/`ci.yml` — exactement le mandat de la fiche : « contrôle de
pile réelle événements et accueil ».

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `infra/scripts/verifier-accueil-evenements.py` | Nouveau script, **29 contrôles** sur la pile réelle |
| `Makefile` | Nouvelle cible `accueil-check` |
| `.github/workflows/ci.yml` | `accueil-check` nommé explicitement (§7.36 : une cible ajoutée à `make check` n'entre pas dans la CI sans l'être) |

## 3.1 Le témoin central : la grille à deux visages du DSM

Le §11 donne au DSM **deux grilles distinctes pour le même évènement** selon ce qu'il
demande : « Modifier » accepte « créé OU rattaché à son périmètre », mais « Publier »,
« Annuler », « Archiver » et « Gérer les médias » n'acceptent QUE « Périmètre » — ses
consultants nommés (`event_dsm_scope`), jamais la seule qualité de créateur. Un contrôle qui
ne poserait qu'un seul évènement DSM verrait une seule grille et ne pourrait pas distinguer
les deux (§7.0, quatrième proposition). Le script pose donc **deux** évènements DSM : l'un
créé en portée `entité` (créateur seul, jamais nommé), l'autre en portée `consultants` (nommé
par construction, `ECART-067`), et prouve que le premier n'ouvre que Modifier quand le second
ouvre tout le reste.

## 3.2 L'asymétrie entre deux porteurs du même rôle

Le compte rendu de `T3` nommait déjà ce témoin dans sa preuve d'origine : deux Boosters, deux
cercles distincts, et le second refusé sur le cercle du premier — à la création ET à
l'écriture ensuite. Le script pose donc **deux** Boosters (`BOOSTER1`/cercle A,
`BOOSTER2`/cercle B) : `BOOSTER2` est refusé (403) à la création sur le cercle A **et** en
modification sur l'évènement que `BOOSTER1` y a créé.

## 3.3 `ARB-DROIT-003` éprouvé dans le sens du refus, deux fois

Un évènement archivé n'offre plus que `RESTAURER`, et seulement aux rôles de portée Entité —
DSM et BOOST en sont exclus EN BLOC, même sur l'évènement dont ils sont respectivement le
créateur nommé et le Booster rattaché. Le script le prouve sur les **deux** évènements qu'il
a lui-même archivés (celui du Booster, celui du DSM nommé par son propre périmètre), pas
seulement sur l'un des deux — même discipline que `verifier-administration-onboarding.py`
pour `ECART-066` : l'exclusion est un fait du rôle, jamais une conséquence de ne pas être
« nommé ».

## 3.4 Le classement temporel, sur l'horloge réelle du conteneur

Un évènement créé avec `finit_le` déjà passé, publié, apparaît dans `classement=passes` et
jamais dans `a_venir` — l'inverse pour un évènement à venir. **Annuler ne retire PAS de la
consultation** : l'évènement à venir annulé reste visible dans `a_venir`, avec `etat=cancelled`
(badge « Annulé », cahier §10.6). **Archiver, lui, retire** : l'évènement passé archivé
disparaît de `passes`. Les deux témoins (positif et négatif) sont nécessaires : un filtre qui
retirerait tout évènement non-`published` masquerait aussi l'annulé, qui doit rester visible.

## 3.5 L'accueil compose, et la fenêtre des arrivées récentes est la fenêtre réelle

`GET …/accueil` est ouvert à huit rôles sans garde, `EMP` compris — le script ne pose donc
aucune session de rôle pour le lire, seulement `EMP`. Son témoin le plus utile reprend la
leçon de `T7` : une appartenance `future` dont la fiche est **déjà publiée** apparaît
**immédiatement** dans les arrivées récentes, avant même sa date d'arrivée — et une fiche
publiée mais dont `recent_until` est déjà dépassé en est **absente**. Les deux cas sont posés,
jamais un seul : un filtre trop large accepterait le second, un filtre trop étroit rejetterait
le premier, et aucun des deux défauts ne serait vu par l'autre témoin seul (même discipline
que §7.39 de la passation — un couple positif/négatif, jamais un refus seul). La même fenêtre
est vérifiée à la fois dans l'agrégat `/accueil` et dans la route dédiée
`GET …/arrivees-recentes` (`T7`), pour prouver qu'elles composent la MÊME population plutôt
que deux lectures divergentes.

L'accueil est aussi vérifié pour ce qu'il ne doit PAS composer : le brouillon créé par le DSM
(jamais publié) et l'évènement archivé n'apparaissent jamais dans `evenements_a_venir`, et le
lien interne posé en décor y apparaît bien.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make accueil-check` (nouveau) | **29/29**, exécuté deux fois de suite (stabilité, ménage vérifié) |
| `uv run ruff check` / `ruff format --check` | vert sur le nouveau fichier et sur tout le dépôt |
| `uv run mypy` (bare, portée `pyproject.toml`) | **197** fichiers, inchangé — `infra/scripts/` n'est **pas** dans `files` du mypy strict (même portée que tous les scripts de pile réelle existants, vérifié en confrontant `verifier-administration-onboarding.py` au même sondage) |
| `uv run pytest -q --collect-only` | **1 564**, inchangé — aucune ligne Python applicative touchée |
| `make sources-check` | **573** fichiers source examinés (+2 : le nouveau script, et son propre fichier étant déjà suivi par `git add`), 0 ignoré hors les 2 exceptions connues |
| `make docs-check` | vert — 5 documents immuables intacts, 6 séquences cohérentes, 12 contrôles de totaux dérivés, 12 contrôles sur la passation |
| `make lint` / `make format-check` | vert (Ruff, ESLint, Prettier) |
| YAML de `ci.yml` | validé par `yaml.safe_load` après l'ajout de l'étape |

**Zéro régression** : `git status` confirme qu'aucun fichier Python applicatif, aucun fichier
frontend et aucune migration n'ont été touchés — seuls `Makefile`, `.github/workflows/ci.yml`
et le nouveau script le sont. Le total pytest (1 564) et le total mypy (197 fichiers) sont
donc **structurellement** inchangés, pas seulement mesurés identiques.

**Un défaut trouvé et corrigé avant tout commit** : la première version du décor omettait
`account_state` dans l'insertion des deux personnes « arrivées récentes » — `INSERT has more
target columns than expressions`, l'erreur PostgreSQL nommant directement la cause (§7.6 : ne
jamais masquer l'erreur d'un contrôle dont on va interpréter le silence).

---

# 5. Décisions

- `DEC-632` consigne la réalisation de `T13` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact ; `QO-121` reste ouverte, non
  davantage instruite — `T13` ne touche à aucun contenu, seulement aux évènements et à
  l'accueil.

---

# 6. Ce que `T13` laisse

- un contrôle de pile réelle pour les évènements et l'accueil, nommé dans `make check` et
  `ci.yml`, qui s'exécutera à chaque pull request désormais ;
- `T14` — la recette, le classement du §30 et la checklist `G8` — est la dernière sous-étape
  du lot. Elle devra composer la démonstration guidée du critère de sortie 6 (« Jonathan
  valide l'accueil et les événements ») et classer les six critères de sortie du §1.2 de la
  fiche, dont les cinq premiers sont déjà couverts par les témoins de `T1` à `T13`.

# Validation demandée à Jonathan

`T13` est faite. Après fusion, la prochaine et dernière sous-étape du LOT 8 est `T14` : la
recette, le classement du §30 et la checklist `G8`.
