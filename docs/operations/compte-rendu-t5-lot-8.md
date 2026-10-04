# Compte rendu — `T5` du LOT 8 : annuler, archiver et restaurer un événement

**Sous-étape :** la cinquième du lot — `POST /entities/{code}/events/{evenement}/annulation`,
`POST /entities/{code}/events/{evenement}/archivage`,
`POST /entities/{code}/events/{evenement}/restauration`
**Date :** 4 octobre 2026
**Décision :** `DEC-624`
**Story :** `MVP-L08-US004` (3 sur 3 — complète)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, **`T5`** |
| Restent | `T6` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/events/perimetre.py` | `ActionEvenement` étendu (`ANNULER`, `ARCHIVER`, `RESTAURER`) ; `resoudre_le_perimetre_de_l_evenement` restructuré pour isoler la branche « événement archivé » |
| `apps/api/app/events/ecriture.py` | `annuler_un_evenement`, `archiver_un_evenement`, `restaurer_un_evenement`, et leurs requêtes |
| `apps/api/app/events/routes.py` | `POST .../annulation`, `POST .../archivage`, `POST .../restauration` |
| `apps/api/tests/test_annulation_archivage_et_restauration_evenements.py` | **17 tests** — structure (2), service (15 marqués `integration`) |
| `apps/api/tests/test_modification_et_publication_evenements.py` | 4 assertions de `T4` corrigées : leur égalité stricte ne portait que `{MODIFIER, PUBLIER}` ; `T5` élargit légitimement la même grille à `ANNULER`/`ARCHIVER` pour les mêmes rôles, et un événement archivé n'offre plus que `RESTAURER` (au lieu de rien) |
| `packages/contracts/src/contrat-api.json` | entrées `annulationDUnEvenement`, `archivageDUnEvenement`, `restaurationDUnEvenement` |

Aucune migration : `T5` ne pose aucune table ni colonne, elle écrit dans les colonnes posées
par `T1` (`state`, `cancelled_at`, `cancellation_reason`) et dans les colonnes génériques de
`ChampsCommuns` (`archived_at`, `archived_by_person_id`) posées par le socle (LOT 2).

## 2.1 Une seule grille à deux formes, et la matrice la porte explicitement

« Annuler » et « Archiver » donnent, pour le DSM, **exactement la même cellule que « Publier »**
— « Périmètre », jamais « créé OU rattaché à son périmètre ». Un DSM créateur seul (non nommé
par `event_dsm_scope`) peut **modifier** un événement de portée Entité qu'il a créé, mais ne peut
**ni le publier, ni l'annuler, ni l'archiver** par cette seule voie — c'est le §7.45 de la
passation (LOT 6), rejoué à l'identique pour deux lignes de plus du §11. Un témoin le prouve :
`test_un_DSM_NOMME_annule_mais_un_DSM_CREATEUR_SEUL_ne_le_peut_pas` pose les deux événements côte
à côte, l'un porté par `event_dsm_scope.dsm_person_id`, l'autre par `created_by_person_id` seul,
et compare leurs périmètres respectifs.

Pour `ESM`/`ADM-E`/`SUPER`/`BOOST`/`OFFICE`, les quatre lignes « Modifier », « Publier »,
« Annuler », « Archiver » partagent la même portée (Entité/Entité/Global/Cercle/Bureau) : aucune
grille supplémentaire n'était nécessaire, `resoudre_le_perimetre_de_l_evenement` ajoute
simplement `ANNULER`/`ARCHIVER` aux mêmes blocs qui accordaient déjà `MODIFIER`/`PUBLIER`.

« Restaurer » n'a **qu'une seule** grille, et elle exclut DSM/BOOST/OFFICE **en bloc** — même
s'ils ont eux-mêmes archivé l'événement. `ARB-DROIT-003` nomme explicitement « un événement »
parmi les cinq ressources que l'ESM restaure librement dans son entité (profil, contenu,
événement, cercle, bureau) : **aucun `ECART-066` à rouvrir ici**, contrairement au LOT 7 où la
matrice disait « Conditionnel » sans que `ARB-DROIT-003` ne nomme la ressource. Un témoin pose un
DSM nommé et un Booster, chacun ayant archivé son propre événement, et confirme que les deux
obtiennent un périmètre **vide** sur l'événement archivé.

## 2.2 Trois préconditions d'état, posées au service et non laissées à la seule grille

| Transition | Précondition | Pourquoi |
|---|---|---|
| `published -> cancelled` | l'événement doit être `published` | annuler un brouillon que personne n'a jamais vu contournerait la porte de publication que `Publier` impose |
| `{draft,published,cancelled} -> archived` | l'événement ne doit pas être déjà archivé | aucune autre précondition : les trois états sont archivables, même parti que l'archivage d'une page (LOT 6, `T7`, archivable depuis `draft` OU `published`) |
| `archived -> draft` | l'événement doit être archivé | restaurer rend **toujours** `draft`, jamais l'état antérieur — restaurer n'est pas publier, `RIGHTS-001` refuse par défaut ce qui n'est pas explicitement redécidé |

Chaque précondition est portée par la requête `SELECT … FOR UPDATE` du verrou optimiste, pas par
une vérification séparée : un événement qui a changé d'état entre la résolution du périmètre (à
la route) et l'écriture (au service) rend le même refus `version_obsolete` (409) qu'une version
numériquement différente — même discipline que `publier_un_evenement` depuis `T4`.

`cancelled_at`/`cancellation_reason` **ne sont jamais effacés**, ni par l'archivage ni par la
restauration : l'événement a été annulé ce jour-là, et c'est un fait, pas un résidu — même parti
que `published_at` conservé à l'archivage et à la restauration d'une page (LOT 6, `T7`). Un
témoin du cycle complet le vérifie directement en lisant les colonnes après l'archivage.

## 2.3 Aucun motif pour l'archivage, et `ECART-064` reste la raison

Le modèle §17.1 donne un champ dédié pour l'annulation (`cancellation_reason`, facultatif) : la
demande d'annulation l'expose (`motif`, optionnel). Il n'existe **aucun** champ équivalent pour
l'archivage — `archive_reason` est la colonne générique de `ChampsCommuns`, et le §18.1 n'en fait
pas un cas de motif obligatoire pour cette ressource. `archive_reason` reste non écrit, comme
pour toutes les autres ressources du projet (`ECART-064`, ouvert, à instruire au LOT 10 avec
`audit_event`).

## 2.4 Le témoin que la fiche exige explicitement

La fiche du lot nomme trois preuves pour `T5` : « grilles distinctes ; restauration ESM
fonctionnelle ; annulé toujours visible ». `test_le_cycle_complet_PUBLIE_ANNULE_ARCHIVE_RESTAURE`
les porte toutes les trois dans un seul parcours : un événement créé par un ESM est publié,
annulé (badge visible dans `lister_les_evenements`, `T2`), archivé (disparaît de la même
lecture), puis restauré par le même ESM — `draft`, jamais `published` ni `cancelled`.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make migrations-check` | tête `0023` inchangée, schéma identique |
| `make isolation-check` | **31 locales, 25 composites** — inchangé, `T5` n'ajoute aucune table |
| `make sources-check` | OK |
| `uv run pytest -q tests/test_annulation_archivage_et_restauration_evenements.py` | **17/17** |
| `uv run pytest -q tests/test_evenements.py tests/test_creation_evenements.py tests/test_modification_et_publication_evenements.py tests/test_contrat.py` | **84/84** (4 assertions de `T4` corrigées pour la grille élargie) |
| `make format-check`, `make lint`, `make typecheck` | verts |
| collecte depuis la racine | **1 506 pytest**, dont **1 109 d'intégration** (+17, dont +15 d'intégration) |
| frontend | **706 Vitest** inchangés — aucun écran ne consomme encore annulation/archivage/restauration |
| **zéro régression** | `git worktree` sur `origin/develop` (après fusion de `T4`), même base : **74 échecs identiques des deux côtés** (jeu de démo, comptes en absolu) |

---

# 4. Décisions

- `DEC-624` consigne la réalisation de `T5` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact, ouvert.

---

# 5. Ce que `T5` laisse

- l'annulation, l'archivage et la restauration, dans la portée exacte de chaque rôle ;
- `MVP-L08-US004` est désormais **complète sur ses trois tiers** (créer, modifier/publier,
  annuler/archiver/restaurer) — mais l'issue `#210` **reste ouverte** : `ECART-068` (audit
  obligatoire) doit être résolu avant sa fermeture, et ne justifie pas d'anticiper `audit_event`
  (LOT 10) ;
- aucun rattachement de média — `T6` ;
- aucun écran, aucun contrat TypeScript propre — même parti que `T3`/`T4`, tant qu'aucun écran ne
  consomme ces routes.

# Validation demandée à Jonathan

`T5` est faite. Après fusion, la prochaine sous-étape est `T6` : rattacher des médias à un
événement.
