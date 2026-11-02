# Compte rendu — `T7` du LOT 11 : `T6` vide fusionnée, recette de clôture, §30 et checklist `G11`

**Sous-étape :** la septième et dernière du lot — constat que `T6` (« écrans consommateurs
résiduels et recollement ») est vide et fusionnée avec `T7`, correctif d'une image publiée,
reclassement du §30 du modèle (`§30.19`/`§30.21`/`§30.23` vérifiés contre les témoins déjà
existants, pas recopiés), recette sur les images publiées, préparation de la checklist `G11`
**Date :** 1er novembre 2026
**Décision :** `DEC-681`
**Branche :** `lot11-t7-recette-de-cloture`, depuis `develop` à jour (`5389f3c`, fusion de `T5`,
PR #317)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 11**, ouvert le 30/10/2026 (`DEC-674`), découpage compilé en **sept** sous-étapes |
| Faites | `T1` à `T5` (`DEC-676` à `DEC-680`), et cette sous-étape `T7` — `T6` ne livre aucun code, elle est **fusionnée** avec `T7` (§2 ci-dessous), conformément à la clause de contingence de la fiche (§3) |
| Reste | la décision de porte elle-même — `G11` n'est **pas** déclarée franchie ici : le critère de sortie 7 de la fiche exige la validation explicite de Jonathan |
| Issues | aucune n'existe pour ce lot (`gh issue list --search "MVP-L11"` ne rend rien, mesuré le 30/10/2026 et reconfirmé ici) — la fermeture d'issue de l'étape 7 de la boucle habituelle reste un no-op, comme annoncé par la fiche |

---

# 2. `T6` est vide : le constat annoncé avant d'être exécuté

La fiche (`fiche-lot-11.md` §3) anticipait explicitement ce cas : « `T6` peut se révéler vide (zéro
écran résiduel) si `T2` et `T3` livrent déjà des écrans complets et reliés à la navigation — dans ce
cas elle sera fusionnée avec `T7` plutôt que livrée comme une coquille vide, et ce constat sera
annoncé avant d'être exécuté, jamais décidé a priori. »

Vérifié par recherche dans le code, pas supposé depuis les comptes rendus :

- **`T2` (photo de profil)** : `PanneauPhoto` est importé et rendu dans `PageProfil.tsx`, elle-même
  routée sous `CHEMINS.entite` et atteignable depuis la rubrique « trombinoscope »
  (`NavigationPrincipale.tsx`, `routes.ts`) — aucun écran orphelin.
- **`T3` (organisation)** : `SectionCerclesEtBureaux` et `SectionAttributionFramework` sont rendues
  dans `SectionOrganisation.tsx`, elle-même affichée sous l'onglet « Organisation » de
  `PageAdministration.tsx`, routée et atteignable depuis la rubrique « administration ».
- **`T1` (socle asynchrone)** : pur backend, le cahier ne lui attribue structurellement aucun écran
  — `apps/api/app/jobs/outbox.py` n'a, à juste titre, aucun appelant frontend.
- **`T4` (planification)** et **`T5` (métier optionnel)** : `T4` ne livre aucune route HTTP (aucun
  écran prévu par la fiche) ; `T5` modifie un écran déjà existant (`SectionOrganisation.tsx`,
  libellé « Métier (facultatif) »), déjà relié.
- **Seul stub résiduel du dépôt**, `SectionAVenir.tsx` (onglets « Contenu »/« Configuration ») :
  posé par le LOT 9 `T14` pour des groupes du cahier §8.1/§10.8 sans route à consommer — **hors
  périmètre de LOT 11**, jamais destiné à recevoir `T1`-`T5`.

Aucun écran de `T1`-`T5` n'est donc sans point d'entrée dans la navigation. Ce constat a été
annoncé à Jonathan avant toute exécution (recherche déléguée à un agent d'exploration, résultat
communiqué, proposition de fusion avec `T7`), et confirmé explicitement (« très bien tu peux passer
à T7 », 01/11/2026). **`T6` ne livre donc aucun code et n'ouvre aucune pull request propre** — la
règle n°1 du §2 de `CLAUDE.md` reste respectée : c'est la fusion elle-même, pas un à-côté, que la
fiche avait pré-autorisée.

---

# 3. Travail réalisé

## 3.1 Un défaut réel trouvé en vérifiant l'état des images publiées, corrigé avant la recette

Avant toute recette « sur les images publiées », l'état réel du workflow `images.yml` a été
contrôlé (`gh run list --workflow=images.yml`) plutôt que supposé sain. **Les cinq publications de
`T1` à `T5` du LOT 11 sont toutes en échec** — la tâche « Construire et publier » réussit à chaque
fois (les images SONT publiées), mais la porte échoue sur la tâche « Trivy sur les images
publiées ».

**Cause mesurée, pas supposée** : `CVE-2026-111497`, `CRITICAL`, corrigeable
(`brotli-libs` 1.2.0-r0 → 1.2.1-r0), dans la base `caddy:2.11-alpine` (Alpine 3.23.5) de la cible
`execution` de l'image `web`. `DEC-482` bloque précisément sur ce cas (CRITICAL corrigeable) — la
porte fait donc exactement ce qu'elle doit faire.

**Ce défaut PRÉCÈDE le LOT 11** : rejoué sur l'exécution de « Chantier front S14 » (30/10/2026,
08:49, avant l'ouverture du lot), la même `CVE-2026-111497` y bloque déjà — contre un succès à « S11 »
(28/10/2026). Le CVE a donc été publié par Alpine entre le 28 et le 30/10/2026, et **personne ne
s'en est aperçu pendant six poussées consécutives** (S14 puis `T1` à `T5` du LOT 11), parce que
cette porte n'est pas, et ne doit pas devenir, un contrôle requis de pull request (§9.4 de la
passation) — rien dans la boucle habituelle n'oblige à la regarder avant une recette.

**Mesuré avant d'être corrigé** (§7.38 de la passation, « ne pas appliquer un correctif sans
l'avoir d'abord mesuré ») : `docker run caddy:2.11-alpine@sha256:5f5c86...` montre que le dépôt
`main` d'Alpine 3.23 porte déjà `brotli-libs-1.2.1-r0`, et `apk add --no-cache
brotli-libs=1.2.1-r0` l'installe proprement sur les **deux** architectures (`x86_64` et `aarch64`,
testées séparément avant d'écrire la ligne), sans toucher à l'empreinte de l'image de base épinglée.
Même classe que `DEC-581` (la couche `apt` épinglée pour `perl-base` sur `python:3.12-slim`), pour
une base Alpine cette fois. Corrigé dans `apps/web/Dockerfile`, cible `execution`, avant
`adduser` — testé localement par une construction complète (`docker buildx build --target
execution`) sur les deux plateformes, artefact lancé, Caddy démarre et sert normalement.

## 3.2 Reclassement du §30 : trois contrôles reportés au LOT 11, désormais acquis

La fiche du LOT 10 (`T16`, `DEC-670`) avait déjà corrigé les annotations `lot=` de `§30.19`,
`§30.21` et `§30.23` pour les porter sur ce lot. Vérifiés ici contre les témoins **déjà écrits** par
`T1`, `T2` et `T4` — jamais rapprochés du §30 avant cette relecture :

| § | Libellé | Classement | Preuve (témoins existants, aucun test nouveau) |
|---|---|---|---|
| `§30.19` | un job rejoué avec la même clé ne crée pas de doublon | **ACQUIS** | `T1` — `test_rejouer_le_relais_sur_un_message_deja_traite_ne_renvoie_pas_le_courriel` ; `T2` — `test_rejouer_le_job_sur_un_media_deja_traite_ne_regenere_pas_la_variante` |
| `§30.21` | une purge ne laisse aucun média ou lien orphelin | **ACQUIS** | `T4` — `test_un_media_pret_sans_reference_est_archive_comme_orphelin`, `test_un_media_pret_avec_une_autorisation_active_n_est_jamais_archive`, `test_un_media_orphelin_depuis_plus_de_sept_jours_est_supprime_definitivement`, `test_un_media_orphelin_depuis_moins_de_sept_jours_n_est_pas_encore_supprime` |
| `§30.23` | l'anonymisation respecte les durées validées | **ACQUIS** | `T4` — `test_une_personne_partie_depuis_plus_de_trois_mois_est_anonymisee`, `test_une_personne_toujours_active_n_est_pas_anonymisee`, `test_une_personne_partie_depuis_moins_de_trois_mois_n_est_pas_anonymisee`, `test_rejouer_l_anonymisation_ne_retouche_jamais_une_personne_deja_anonymisee` |

Les neuf témoins cités suivent tous la forme exigée par le §7.39 de la passation (paire
négatif/positif, ou borne mesurée des deux côtés) : `§30.19` et `§30.23` prouvent l'idempotence en
simulant un relais interrompu puis en vérifiant qu'un second passage ne rejoue pas l'effet ;
`§30.21` prouve, par un témoin dédié, qu'un orphelin **expiré** est réellement supprimé de MinIO
(`lire_l_objet` lève ensuite `ObjetIntrouvable`), apparié à un témoin négatif (référencé par une
autorisation active, jamais archivé) qui élimine l'hypothèse d'un nettoyage trop large.

**Classement final** (`infra/scripts/verifier-recette-modele.py`) : **23 acquis, 2 partiel,
0 reporté, 0 inapplicable** — était 20/2/3/0 depuis `T16` du LOT 10. Les deux seuls éléments
`PARTIEL` (`§30.4`, `§30.8`) sont antérieurs au LOT 11 et documentent un résiduel de
**processus**, pas de LOT 11 ; aucun des trois reports hérités n'appartenait à un autre lot.

## 3.3 Les sept critères de sortie de la fiche, vérifiés un par un

Aucun n'a exigé de code nouveau au-delà du correctif Trivy du §3.1 — tous étaient déjà prouvés par
`T1` à `T5` :

| # | Critère | État | Preuve |
|---:|---|---|---|
| 1 | seuls les médias `ready` sont servis | **Tenu** | `T2` — `ETAT_AFFICHABLE` (LOT 5) réutilisé tel quel par l'upload et la génération de variantes |
| 2 | Redis peut être vidé sans perte de la source de vérité métier | **Tenu** | `T1` — `async_job`/`outbox_message` persistés dans PostgreSQL, Redis au seul transport |
| 3 | un job rejoué ne duplique pas son effet | **Tenu** | `§30.19` ci-dessus, `T1`/`T2` |
| 4 | les tâches planifiées ne s'exécutent pas en parallèle | **Tenu** | `T4` — index unique PARTIEL sur `scheduled_task_run.task_name WHERE state='running'` |
| 5 | les fichiers rejetés sont supprimés selon la politique | **Tenu** | `§30.21` ci-dessus, `T4` — délai de sept jours, même règle pour rejeté/temporaire/orphelin |
| 6 | les workers et files sont supervisés | **Tenu** | `T4` — battement poussé vers Uptime Kuma si `UPTIME_KUMA_PUSH_URL` est configurée |
| 7 | Jonathan valide les traitements asynchrones | **En attente** | checklist `G11`, section 6 |

Les deux sous-étapes hors backlog (création de cercle/bureau et attribution, `T3`) et la déviation du
métier (`T5`) sont, comme prévu par la fiche, vérifiées par leurs propres contrôles de sous-étape et
par la recette finale plutôt que par un critère de sortie officiel dédié.

## 3.4 Recette sur les images publiées

- Branche poussée, puis `images.yml` déclenché par `workflow_dispatch` sur cette branche (le fichier
  existe déjà sur `main` depuis la porte `G1` — pas besoin du déclencheur temporaire qu'avait exigé
  `T7` du LOT 1) pour vérifier le correctif AVANT fusion, plutôt que de fusionner d'abord et
  constater ensuite : la tâche « Trivy sur les images publiées » passe au vert sur cette branche,
  `brotli-libs-1.2.1-r0` confirmé par le rapport complet (non bloquant) qui liste maintenant
  `CRITICAL: 0` sur les trois images.
- `make images-pin` : épinglage de la recette sur la publication réussie de cette branche.
- `make recette-check` (57 contrôles, les 7 séparations du cahier §22.2) rejoué sur l'artefact
  publié et corrigé.
- Aucun contrôle de pile réelle propre au LOT 11 n'existe (`T1` à `T5` n'en ont ajouté aucun — leurs
  propres comptes rendus documentent des allers-retours réels par script HTTP et navigateur, jamais
  une cible `make X-check` nouvelle) : les contrôles hérités (`back-office-check`,
  `onboarding-check`, `accueil-check`, `framework-check`) sont rejoués `ENVIRONNEMENT=recette` par
  discipline, même pattern que `T16` des LOTS 9/10.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `gh run list --workflow=images.yml` | défaut trouvé : cinq publications LOT 11 en échec, porte Trivy — voir §3.1 |
| Construction locale `apps/web/Dockerfile` cible `execution`, `linux/amd64` et `linux/arm64` | les deux construisent, `brotli-libs-1.2.1-r0` installé, Caddy démarre et sert |
| `infra/scripts/verifier-recette-modele.py` (modifié) | 25/25 classés — **23 acquis, 2 partiel, 0 reporté, 0 inapplicable** |
| `make recette-modele-check` | idem, vert |
| `make docs-check` | vert — 5 documents immuables intacts, 6 séquences cohérentes (`DEC-681` prochain libre), 12 contrôles de totaux dérivés, 12 contrôles sur la passation |
| `make sources-check` | vert — 781 fichiers source examinés, les deux seules exceptions déclarées |
| `make isolation-check` | vert — 38 tables locales, 29 clés composites, 0 référence nue, 0 clé simple entre deux tables locales |
| `make migrations-check` | vert — base vide → tête `0029` → schéma identique (912 colonnes/333 contraintes/269 index/10 déclencheurs/199 fonctions) |
| `make check` (qualité complète, racine) | Ruff, Prettier, ESLint, `mypy` (305 fichiers), `tsc --noEmit` (3 projets) : tous verts |
| `uv run pytest` (racine, développement) | **2 092 collectés, inchangé** — `T7` n'ajoute aucun test applicatif, le reclassement du §30 réutilisant des témoins existants |
| Comparaison de worktree `origin/develop` (§7.22 de la passation) | voir §4 bis — liste comparée, pas seulement le compte |
| `make test-frontend` | **992 Vitest**, inchangé |
| `make residu-check` | aucun résidu laissé par la suite |
| `make images-pin` / `make recette-check` | épinglage sur la publication corrigée ; 57 contrôles, 0 échec, 7/7 séparations |
| `make back-office-check` / `onboarding-check` / `accueil-check` / `framework-check` (développement et `ENVIRONNEMENT=recette`) | tous verts, mêmes résultats dans les deux environnements |

**Zéro régression applicative** : seuls `apps/web/Dockerfile` (une ligne, image seule) et
`infra/scripts/verifier-recette-modele.py` (reclassement, aucune ligne de production) sont modifiés
— aucune route, aucune migration, aucun module Python ou TypeScript applicatif touché. Les totaux
pytest, Vitest et mypy sont donc structurellement inchangés, pas seulement mesurés identiques.

---

# 5. Décisions

- `DEC-681` consigne la réalisation de `T7`, le constat de `T6` vide et sa fusion, le correctif de
  l'image `web`, et le reclassement du §30 ;
- aucun écart nouveau n'est ouvert par cette sous-étape. Les réserves déjà connues restent ouvertes
  et non bloquantes pour `G11` : `ECART-012` (Léa), `ECART-061` (LOT 13), les questions héritées des
  LOTS 6/9/10 (`QO-092` volet canal externe, `QO-096`/`QO-097`/`QO-099`/`QO-100`/`QO-110`, `QO-121`,
  `QO-125`, `QO-126`), `ROAD-RSK-033`/`ROAD-RSK-034` (à réévaluer avant le LOT 13).

---

# 6. Ce que `T7` laisse

- le LOT 11 est **techniquement complet** : les cinq sous-étapes de code (`T1`-`T5`) et la clôture
  (`T7`, `T6` fusionnée) sont réalisées, et `G11` attend la seule validation explicite de Jonathan ;
- `checklist-validation-G11.md` est prête, séparant les six preuves techniques tenues du septième
  critère, qui est la décision de Jonathan lui-même ;
- l'intégration des données de démonstration (entité EXALT Bordeaux) reste explicitement **hors**
  de ce découpage — action distincte, postérieure au franchissement de `G11` (fiche §2) ;
- une fois `G11` validée, consigner la décision (`DEC-682` probable, pattern `DEC-617`/`DEC-634`/
  `DEC-652`/`DEC-671`) et poser le tag `v0.11.0` sur `main`.

# Validation demandée à Jonathan

`T7` est faite, `T6` est vide et fusionnée dans `T7` — le LOT 11 est techniquement complet. Peux-tu
lire [`checklist-validation-G11.md`](checklist-validation-G11.md) et confirmer si `G11` peut être
déclarée franchie ? Cette décision sera consignée séparément (`DEC-682` probable), comme
`DEC-617`/`DEC-634`/`DEC-652`/`DEC-671` l'ont été pour `G7`/`G8`/`G9`/`G10` après validation.

```bash
gh pr merge <n> --squash --delete-branch   # fusion de T7 après validation
gh pr close <n> --delete-branch            # retour arrière avant fusion
```
