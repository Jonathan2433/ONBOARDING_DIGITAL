# Compte rendu — `T15` du LOT 9 : le contrôle de pile réelle du back-office

**Sous-étape :** la quinzième du lot — `make back-office-check`, un script qui exerce
l'asymétrie de rôles des écrans livrés par `T14` et l'isolation multi-entités pendant
l'import à travers Caddy, en HTTPS, sur les conteneurs réellement en marche
**Date :** 13 octobre 2026
**Décision :** `DEC-650`
**Stories :** transversale — critère de sortie 6 de la fiche (§1.2 : « l'isolation
multi-entités est testée pendant l'import »), aucune nouvelle route, aucun nouveau critère ;
`T15` prouve ce que `T1` à `T14` ont déjà livré, sur la pile réelle

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 9**, ouvert le 08/10/2026 (`DEC-635`), **seize** sous-étapes |
| Faites | `T1` à `T14`, **`T15`** |
| Reste | `T16` |
| Issues | épic `#234`, stories `#235` à `#242`, jalon `G9` |

---

# 2. Ce que ce contrôle prouve, et pourquoi pytest ne le prouve pas déjà

Les suites pytest de `T1` à `T14` éprouvent chaque règle via `TestClient` — la même
application Python, en mémoire. Un contrôle de pile réelle passe par **Caddy, en HTTPS, sur
les conteneurs réellement en marche** : c'est la seule manière de prouver que le mandatement
(`DEC-470`), le conteneur `api` à jour (`make code-refresh`) et les cookies
`Secure`/`SameSite` du LOT 3 sont tous en jeu en même temps — §7.28 de la passation, une
cible statique ne prouve rien de ce qu'un conteneur sert réellement. Même motif exactement
que `verifier-administration-onboarding.py` (LOT 7, `T14`) et
`verifier-accueil-evenements.py` (LOT 8, `T13`).

**Aucune route nouvelle, aucune migration.** `T15` ne construit qu'un script de vérification
et l'inscrit dans `make check`/`ci.yml` — exactement le mandat de la fiche : « contrôle de
pile réelle, asymétrie de rôles, isolation multi-entités pendant l'import » (§3, pattern
`T13`/`T14` des LOTS 7/8).

**Et un trou réel que ni `T6` à `T10` ni aucune suite pytest du module n'avaient comblé** :
le critère de sortie 6 (§1.2 de la fiche) exige un « témoin d'isolation dédié », et mesuré
avant d'écrire une ligne de script, aucun test — pas même à l'échelle de la suite
`apps/api/tests/test_*import*.py` — ne posait deux entités et ne vérifiait qu'un lot de
l'une est invisible depuis l'autre. Le code l'implémentait déjà correctement (toutes les
requêtes SQL d'`app.imports.rapport`/`execution` filtrent `entity_id = :entite` avant de
regarder le lot ou la ligne, même discipline que les clés composites du LOT 2) — c'était la
**preuve** qui manquait, pas le mécanisme.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `infra/scripts/verifier-back-office.py` | Nouveau script, **16 contrôles** sur la pile réelle |
| `Makefile` | Nouvelle cible `back-office-check` |
| `.github/workflows/ci.yml` | `back-office-check` nommé explicitement (§7.36 : une cible ajoutée à `make check` n'entre pas dans la CI sans l'être) |

## 3.1 Partie A — le témoin central : le tableau de bord, deux portées différentes

Le cahier §10.8 donne au tableau de bord (`T5`) une portée qui dépend du rôle : `DSM` voit
« Consultants », `ESM`/`ADM-E`/`SUPER` voient « Entité ». Un contrôle qui ne poserait qu'un
seul rôle verrait une seule portée et ne pourrait rien distinguer (§7.0 de la passation,
quatrième proposition). Le décor pose donc, dans la **même** entité : un DSM, un ESM, un
OFFICE, **un consultant lié au DSM** par `dsm_assignment`, et **un second profil actif sans
aucun lien à ce DSM**. Résultat mesuré : `profils_actifs` vaut **1** pour le DSM (son seul
consultant) et **5** pour l'ESM (toute l'entité — les cinq profils actifs, comptes de test
compris). Sans le second profil « sans lien », un DSM qui verrait toute l'entité par défaut
rendrait la même observation qu'un DSM correctement scopé mais à qui il ne resterait qu'un
seul profil à compter — c'est la paire des deux profils, l'un lié et l'un non lié, qui rend
le témoin discriminant.

## 3.2 Partie A — trois paires rôle-refusé / rôle-accepté sur la même action

Chacune pose un rôle REFUSÉ à côté d'un rôle ACCEPTÉ sur la **même** action, pour que
l'échec produise une observation différente du succès :

- **le dépôt d'import** (matrice §14 « Charger un CSV ») : `ESM` → `201`, `DSM` → `403`,
  `OFFICE` → `403` — les trois contre le même CSV, la même entité ;
- **la création d'entité** (cahier §21) : `SUPER` → `201`, `ESM` → `403` — `SUPER` seul, un
  littéral, jamais une grille de plus ;
- **le catalogue des métiers** (`T14`, route nouvelle de la sous-étape précédente) : `OFFICE`
  → `200` — aucun rôle n'y est distingué, par contraste direct avec le même `OFFICE` refusé
  partout ailleurs dans ce script (deux extrêmes de la matrice dans le même script, même
  parti que `verifier-administration-onboarding.py` pour `OFFICE` sur les modèles contre le
  suivi).

## 3.3 Partie B — l'isolation multi-entités pendant l'import, critère de sortie 6

Un CSV à une seule ligne, sans e-mail (`E-EMAIL-001`, bloquant), suffit à produire un lot
`preview_ready` puis `completed` sans construire le référentiel complet (métier, cercle,
DSM...) que `T9` valide — ce script n'a besoin que de l'isolation des routes, jamais de
réussir une création de profil. Le lot déposé par l'ESM de l'entité A est visé par l'ESM de
l'entité B sur les **trois** routes scopées par lot :

| Route | Depuis A (propriétaire) | Depuis B (étrangère) |
|---|---|---|
| `GET .../imports/{lot}/rapport` | `200` | `404 lot_introuvable` |
| `POST .../imports/{lot}/lancement` | `200` (`preview_ready -> completed`) | `404`, **y compris rejoué après que le lot soit `completed` dans A** |
| `POST .../imports/{lot}/rows/{ligne}/rejeu` | `409 rejeu_hors_portee` | `404`, sur les **mêmes** identifiants de lot et de ligne |

**Le lancement rejoué depuis B est le témoin qui ferme la question de l'état.** Une fois le
lot `completed` dans A, appeler `lancement` une seconde fois depuis A rendrait `409`
(`etat_non_lancable`) — c'est le même service, la même requête verrouillée
`WHERE id = :lot AND entity_id = :entite`. Depuis B, la réponse reste `404`, jamais `409` :
la preuve que le refus porte sur l'**entité**, et non sur l'état du lot.

**Le couple `409`/`404` sur le rejeu est le témoin le plus discriminant du script.** La ligne
unique du CSV est rejetée pour une anomalie d'e-mail (`E-EMAIL-001`), explicitement **hors de
portée** du rejeu (`_CODES_HORS_PORTEE_DU_REJEU` dans `app.imports.execution`) : rejouée
depuis A, lot et ligne sont trouvés, et la route refuse pour cette raison précise, `409`.
Rejouée depuis B, avec les **identiques** identifiants de lot et de ligne, la route rend
`404` — ni un rôle insuffisant (ce serait `403`, identique pour toute entité), ni un état de
lot (ce serait `409`, comme pour A), mais une absence structurelle du lot dans le périmètre
de B.

Chaque paire de témoins par entité est appariée à un témoin positif dans l'entité
propriétaire (`rapport`/`lancement` réussissent depuis A), sans lequel le refus de B serait
indistinguable d'une route cassée (§7.39 de la passation).

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make back-office-check` (nouveau) | **16/16**, exécuté sur la pile réelle à travers Caddy en HTTPS |
| `uv run ruff check` / `ruff format --check` | vert sur le nouveau fichier et sur tout le dépôt |
| `uv run mypy` (bare, portée `pyproject.toml`) | **238** fichiers, inchangé — `infra/scripts/` n'est **pas** dans `files` du mypy strict, même portée que tous les scripts de pile réelle existants |
| `uv run pytest -q --collect-only` | **1 707**, inchangé — aucune ligne Python applicative touchée |
| `make sources-check` | **650** fichiers source examinés (+1 : le nouveau script), 0 ignoré hors les 2 exceptions connues |
| `make docs-check` | vert — 5 documents immuables intacts, 6 séquences cohérentes, 12 contrôles de totaux dérivés, 12 contrôles sur la passation |
| `make lint` / `make format-check` | vert (Ruff, ESLint, Prettier) |
| YAML de `ci.yml` | validé par `yaml.safe_load` après l'ajout de l'étape |
| `make residu-check` | **74 échecs environnementaux**, base documentée, inchangée — et confirme explicitement l'absence de résidu laissé par le décor du script |

**Zéro régression** : `git status` confirme qu'aucun fichier Python applicatif, aucun
fichier frontend et aucune migration n'ont été touchés — seuls `Makefile`,
`.github/workflows/ci.yml` et le nouveau script le sont. Le total pytest (1 707) et le total
mypy (238 fichiers) sont donc **structurellement** inchangés, pas seulement mesurés
identiques.

**Aucun défaut trouvé dans le code livré** : les 16 contrôles sont passés du premier coup —
l'isolation et les grilles de rôles étaient déjà correctement implémentées par `T2` à `T14`,
ce que ce script vient seulement **prouver** sur la pile réelle, conformément à son mandat.

---

# 5. Décisions

- `DEC-650` consigne la réalisation de `T15` ;
- aucun écart nouveau n'est ouvert ; le critère de sortie 6 de la fiche (§1.2) est désormais
  couvert par un témoin dédié, `make back-office-check` ; `ECART-012`, `ECART-068`,
  `QO-100`, `QO-121` et `QO-125` restent ouverts, non davantage instruits — `T15` ne touche
  ni au statut professionnel d'une direction générale, ni à l'audit, ni au schéma réel des
  colonnes, ni au contenu, ni au filtrage DSM/Booster du rapport d'import.

---

# 6. Ce que `T15` laisse

- un contrôle de pile réelle pour le back-office, nommé dans `make check` et `ci.yml`, qui
  s'exécutera à chaque pull request désormais ;
- `T16` — la recette de clôture, le classement du §30 (règles 17/18 à vérifier) et la
  checklist `G9` — est la dernière sous-étape du lot. Elle devra composer la démonstration
  guidée du critère de sortie 7 (« Léa et Jonathan valident le rapport de répétition en
  recette ») et classer les huit critères de sortie du §1.2 de la fiche, dont le sixième est
  désormais couvert par le témoin de `T15`.

# Validation demandée à Jonathan

`T15` est faite. Après fusion, la prochaine et dernière sous-étape du LOT 9 est `T16` : la
recette de clôture, le classement du §30 et la checklist `G9`.
