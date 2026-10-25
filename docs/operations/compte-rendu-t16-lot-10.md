# Compte rendu — `T16` du LOT 10 : recette de clôture, §30 et checklist `G10`

**Sous-étape :** la seizième et dernière du lot — reclassement du §30 du modèle
(`§30.19`-`§30.24` vérifiés contre la roadmap, pas recopiés), recette sur les images publiées,
préparation de la checklist `G10`
**Date :** 24 octobre 2026
**Décision :** `DEC-670`
**Branche :** `feature/lot10-t16-recette-cloture`, depuis `develop` à jour (`b4e3b92`, fusion de
`T15`, PR #291)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | les SEIZE — `T1` à `T16` |
| Reste | la décision de porte elle-même — `G10` n'est **pas** déclarée franchie ici : le critère de
sortie 6 de la fiche exige encore la validation explicite de Jonathan |
| Issues | épic `#267`, stories `#268` à `#275`, jalon `G10` |

---

# 2. Sous-étape en cours

`T16` clôture techniquement le lot, pattern `T14`/`T15`/`T16` des LOTS 7/8/9 : reclassement
exécutable des contrôles du §30 du modèle immuable, recette sur les images publiées, préparation
de la checklist `G10`.

---

# 3. Travail réalisé

## 3.1 Reclassement du §30 : quatre annotations `lot=` fautives, deux contrôles déjà acquis

La fiche (`fiche-lot-10.md` §2.1) signalait une divergence trouvée dans
`infra/scripts/verifier-recette-modele.py` : les annotations `lot=` de `§30.19` à `§30.24` dataient
d'avant que la roadmap ne fixe l'ordre définitif des LOTS 10 à 13, « à vérifier à `T16`, pas à
recopier ». Vérifié contre la roadmap réelle (`ROADMAP_MVP_V1_V2_EXALT.md`), pas contre ce qui
était déjà écrit dans le script — exactement l'instruction de la fiche, et le §9.0 de la passation
(« vérifie avant de bâtir dessus ») :

| § | Libellé | Annotation fautive | Correction |
|---|---|---|---|
| `§30.19` | un job rejoué avec la même clé ne crée pas de doublon | `lot="LOT 10"` | `LOT 11` — la roadmap donne « un job rejoué ne duplique pas son effet » comme critère de sortie du LOT 11 ; ce lot ne pose ni `async_job` ni worker |
| `§30.20` | une action métier et son audit sont atomiques | `lot="LOT 12"` | **reclassé ACQUIS** — c'est le critère de sortie 1 de CE lot |
| `§30.21` | une purge ne laisse aucun média ou lien orphelin | `lot="LOT 12 — purge RGPD"` | `LOT 11` — la roadmap place « nettoyage des objets orphelins » dans le LOT 11, jamais dans le LOT 12 (qualité transversale), qui ne construit rien |
| `§30.23` | l'anonymisation respecte les durées validées | `lot="LOT 12"` | `LOT 11` — la roadmap place « anonymisation après départ » et « purge de l'audit » dans le LOT 11 |
| `§30.24` | les exports respectent le même périmètre que la consultation | `lot="LOT 11 — exports"` | **reclassé ACQUIS** — c'est l'export d'audit de CE lot (`T9`) |

**`§30.21` n'était pas nommé par la fiche**, qui ne citait explicitement que `§30.19`/`§30.20`/
`§30.23`/`§30.24`. Il a été vérifié quand même, par discipline (`§7.40` de la passation : « un
garde-fou écrit contre une instance ne couvre pas la classe » — la fiche donnait des exemples, pas
une liste fermée, et l'instruction était « corrigées si besoin à `T16`, contre la roadmap »). La
roadmap confirme qu'il appartenait au même lot mal annoté que `§30.19`/`§30.23`.

**`§30.20` et `§30.24` sont reclassés ACQUIS, sans aucun test nouveau** — réutilisation plutôt que
réécriture (§7.27 de la passation) :

- **`§30.20`** : CINQ témoins existent déjà, un par domaine câblé sur le service générique
  `enregistrer_un_evenement` par `T2` à `T6` (authentification, organisation, contenus, événements,
  onboarding), chacun nommé `test_un_echec_APRES_l_ecriture_annule_AUSSI_l_audit_event` et portant
  littéralement `ARB-DATA-005/§30.20` dans son en-tête. Chacun force un échec APRÈS l'écriture de
  `audit_event`, dans la MÊME transaction que l'action métier, et vérifie que les DEUX écritures
  sont annulées ensemble — la preuve d'atomicité, répétée dans cinq domaines indépendants plutôt
  qu'affirmée une fois.
- **`§30.24`** : `T9` a déjà construit `lister_tout_le_journal_d_audit` en RÉUTILISANT la même
  construction SQL que `lister_le_journal_d_audit` (`T8`, `_cte_et_source`), seul l'`ORDER BY`/
  `LIMIT` final différant — le périmètre de l'export est celui de la lecture PAR CONSTRUCTION,
  jamais une seconde résolution qui pourrait diverger. Deux tests déjà existants le prouvent
  directement : `test_le_perimetre_de_l_export_est_celui_de_la_lecture` et
  `test_le_csv_rend_les_memes_evenements_que_la_lecture`.

**Classement final** (`infra/scripts/verifier-recette-modele.py`) : **20 acquis, 2 partiel,
3 reportés, 0 inapplicable** — était 18/2/5/0 depuis `T16` du LOT 9.

## 3.2 Les six critères de sortie de la fiche, vérifiés un par un

Aucun n'a exigé de code nouveau — tous étaient déjà prouvés par `T1` à `T15` :

| # | Critère | État | Preuve |
|---:|---|---|---|
| 1 | les événements sensibles sont atomiques avec l'action métier | **Tenu** | §3.1 ci-dessus, `§30.20` |
| 2 | aucune donnée interdite n'apparaît dans l'audit | **Tenu** | `T8` — `test_aucune_donnee_interdite_et_la_correlation_est_tracee` |
| 3 | les rapports respectent les mêmes droits que les écrans source | **Tenu** | `T8`/`T9`/`T10` — `lister_tout_le_journal_d_audit` et le reporting réutilisent littéralement les grilles de périmètre déjà construites, jamais une seconde résolution |
| 4 | les durées de conservation sont configurées | **Tenu** | `T1` — `retention_until` posé à un an par défaut ; `T8` — `test_retention_jusqua_est_un_an_apres_l_occurrence` |
| 5 | l'identifiant de corrélation relie interface, API et logs | **Tenu** | `T2`-`T7` — réutilisation de `correlation_courante()` (`packages/observabilite`, LOT 1 `T4`), jamais un second mécanisme ; `T8` — même test que le critère 2 |
| 6 | Jonathan valide l'audit et le pilotage | **En attente** | checklist `G10`, section 7 |

## 3.3 Recette sur les images publiées de `b4e3b92`

- `make images-pin` : épinglage sur la publication réussie de `b4e3b92` (fusion de `T15`, exécution
  `40128090340`).
- Conflit de port `8080` connu (`observatoire-ecom-studio`, §7.23 de la passation), résolu en
  arrêtant temporairement son conteneur puis en le relançant après la recette.
- **Premier démarrage parti dans un état incohérent** : Caddy, créé pendant le conflit de port,
  avait démarré `healthy` mais SANS ses deux publications (`80/tcp, 443/tcp` nus, aucune liaison
  `127.0.0.1:...`) — `make down-recette` puis `make up-recette` propre a corrigé l'état, les 7
  publications déclarées correspondant alors aux 7 réelles.
- **La base de recette était restée pointée sur une image pré-LOT 10** (`.env.recette` datait du
  13/10/2026, avant l'ouverture du lot) : `alembic upgrade head` rendait `0026`, pas `0027` —
  mesuré, pas supposé. `make images-pin` l'a réépinglée sur `b4e3b92`, puis `make migrate
  ENVIRONNEMENT=recette` a amené la tête à `0027`.
- `make recette-check` (57 contrôles, les 7 séparations du cahier §22.2) et les trois contrôles de
  pile réelle du lot et des lots hérités ont été rejoués `ENVIRONNEMENT=recette` : `back-office-check`
  (LOT 9), `onboarding-check` (LOT 7), `accueil-check` (LOT 8) — même discipline que `T16` du LOT 9,
  qui avait rejoué les trois mêmes pour la même raison.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `infra/scripts/verifier-recette-modele.py` (modifié) | 25/25 classés — **20 acquis, 2 partiel, 3 reportés, 0 inapplicable** |
| `make recette-modele-check` | idem, vert |
| `make docs-check` | vert — 5 documents immuables intacts, 6 séquences cohérentes (`DEC-670` prochain libre), 12 contrôles de totaux dérivés, 12 contrôles sur la passation |
| `make format-check` / `lint` / `typecheck` | verts (Ruff, Prettier, ESLint, `mypy` — 276 fichiers) |
| `make sources-check` / `sources-temoin` | verts, témoin discriminant |
| `make parametres-check` / `parametres-temoin` | verts |
| `make cadre-check` / `cadre-temoin` | verts — 25 contrôles, témoin aux quinze motifs |
| `make sessions-temoin` | vert |
| `make images-check` | 11 contrôles, 0 échec |
| `make versions` / `tree` / `icloud-verify` | verts |
| `make test-frontend` | **889 Vitest** (459 `contracts`, 120 `ui`, 310 `web`), inchangé |
| `make audit` | zéro avis, zéro tolérance (`pip-audit` et `pnpm audit`) |
| `uv run pytest -q --collect-only` | **1 992** collectés, inchangé — `T16` n'ajoute aucun test, les deux reclassements réutilisant des témoins existants |
| `uv run pytest -q` (développement) | 1 914 passés, **78 échecs environnementaux** |
| Comparaison de worktree `origin/develop` (§7.22 de la passation) | **78 échecs identiques, un par un** (liste comparée par `diff`, pas seulement le compte) — 1 914 passés des deux côtés |
| `make residu-check` | mêmes 78 échecs environnementaux ; **aucun résidu** laissé par la suite |
| `make code-refresh` / `make migrate` (développement) | conteneur à jour, tête `0027` inchangée |
| `make api-check` / `web-check` / `isolation-check` / `migrations-check` / `permissions-check` | tous verts, pile réelle de développement |
| `make back-office-check` | **16/16**, 0 échec |
| `make onboarding-check` | **14/14**, 0 échec |
| `make accueil-check` | **29/29**, 0 échec |
| `make framework-check` | **77/77**, 0 échec |
| `make images-pin` | épinglage sur `b4e3b92` (exécution `40128090340`) |
| `make up-recette` / `make migrate ENVIRONNEMENT=recette` | tête `0027`, après correction de l'épinglage périmé |
| `make recette-check` | **57 contrôles, 0 échec** ; 7/7 séparations ; artefact publié confirmé par empreinte, `aarch64` natif |
| `make back-office-check ENVIRONNEMENT=recette` | **16/16**, 0 échec |
| `make onboarding-check ENVIRONNEMENT=recette` | **14/14**, 0 échec |
| `make accueil-check ENVIRONNEMENT=recette` | **29/29**, 0 échec |

**Zéro régression** : seul `infra/scripts/verifier-recette-modele.py` est modifié dans le code —
aucune route, aucune migration, aucun fichier frontend ni backend applicatif touché. Les totaux
pytest (1 992 collectés), Vitest (889) et mypy (276 fichiers) sont donc **structurellement**
inchangés, pas seulement mesurés identiques.

---

# 5. Décisions

- `DEC-670` consigne la réalisation de `T16` et le reclassement du §30 ;
- aucun écart nouveau n'est ouvert. `ECART-012`, `QO-092` (volet canal externe), `QO-096`, `QO-097`,
  `QO-099`, `QO-100`, `QO-110`, `QO-121`, `QO-125`, `QO-126` et `ROAD-RSK-033`/`ROAD-RSK-034` restent
  ouverts et non bloquants pour `G10` — aucun n'est nommé par le découpage du lot.

---

# 6. Ce que `T16` laisse

- le LOT 10 est **techniquement complet** : les seize sous-étapes sont réalisées, et `G10` attend la
  seule validation explicite de Jonathan ;
- `checklist-validation-G10.md` est prête, séparant les cinq critères techniquement tenus du
  sixième qui est la décision de Jonathan lui-même ;
- une fois `G10` validée, consigner la décision (`DEC-671` probable, pattern `DEC-617`/`DEC-634`/
  `DEC-652`) et poser le tag `v0.10.0` sur `main`, comme `G7`/`G8`/`G9` l'ont fait.

# Validation demandée à Jonathan

`T16` est faite — le LOT 10 est techniquement complet. Peux-tu lire
[`checklist-validation-G10.md`](checklist-validation-G10.md) et confirmer si `G10` peut être
déclarée franchie ? Cette décision sera consignée séparément (`DEC-671` probable), comme
`DEC-617`/`DEC-634`/`DEC-652` l'ont été pour `G7`/`G8`/`G9` après validation.

```bash
gh pr merge <n> --squash --delete-branch   # fusion de T16 après validation
gh pr close <n> --delete-branch            # retour arrière avant fusion
```
