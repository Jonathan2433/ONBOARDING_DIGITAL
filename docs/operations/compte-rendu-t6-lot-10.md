# Compte rendu — `T6` du LOT 10 : le câblage sur l'onboarding

**Sous-étape :** la sixième du lot — câblage sur l'onboarding (LOT 7)
**Date :** 19 octobre 2026
**Décision :** `DEC-660`
**Stories :** `MVP-L10-US001`/`US002`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, **`T6`** |
| Restent | `T7` à `T16` |
| Issues | épic `#267`, stories `#268` à `#275`, jalon `G10` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/onboarding/catalogue.py` | `creer_une_tache_de_reference` écrit aussi `audit_event` (littéral `tache_de_reference_creee`) |
| `apps/api/app/onboarding/gabarits.py` | `creer_un_modele`/`creer_une_version`/`definir_les_taches_de_la_version` écrivent aussi `audit_event` (trois littéraux, un seul `audit_event` pour l'appel entier de la troisième, y compris sur une liste vide) |
| `apps/api/app/onboarding/cycle_de_vie.py` | `publier_une_version`/`archiver_une_version`/`restaurer_une_version` écrivent aussi `audit_event` (trois littéraux) |
| `apps/api/app/onboarding/instances.py` | `affecter_un_parcours` (un seul `audit_event`, `TypeEvenementTache.ASSIGNED`), `archiver_un_parcours_termine`/`restaurer_un_parcours` (deux littéraux) |
| `apps/api/app/onboarding/taches.py` | `terminer_une_tache`/`annuler_la_completion`/`reouvrir_une_tache` écrivent aussi `audit_event` (`action_code` réutilisant `TypeEvenementTache`) |
| `apps/api/app/onboarding/routes.py` | huit routes transmettent désormais `acteur`/`instant` aux fonctions qui ne les recevaient pas encore |
| `apps/api/tests/test_audit_onboarding.py` | **18 tests d'intégration**, le câblage lui-même |
| sept fichiers de test existants | nettoyage de décor étendu à `audit_event` |

Aucune migration, aucune route : `T6` câble treize fonctions déjà posées par le LOT 7 sur le service
générique de `T2`, exactement le périmètre que `fiche-lot-10.md` lui donne (« modèles, versions,
parcours, tâches »).

## 2.1 Le périmètre retenu, et pourquoi

Mesuré avant d'écrire une ligne (grep exhaustif de `INSERT INTO onboarding_*`/`UPDATE onboarding_*`
sur tout `app/`, hors tests) : toutes les écritures sur les sept tables de l'onboarding vivent
exclusivement dans cinq modules, treize fonctions publiques :

| Fonction | Fichier | Appelant HTTP |
|---|---|---|
| `creer_une_tache_de_reference` | `catalogue.py` | 1 (route dédiée) |
| `creer_un_modele` | `gabarits.py` | 1 |
| `creer_une_version` | `gabarits.py` | 1 |
| `definir_les_taches_de_la_version` | `gabarits.py` | 1 |
| `publier_une_version` | `cycle_de_vie.py` | 1 |
| `archiver_une_version` | `cycle_de_vie.py` | 1 |
| `restaurer_une_version` | `cycle_de_vie.py` | 1 |
| `affecter_un_parcours` | `instances.py` | 1 |
| `terminer_une_tache` | `taches.py` | 1 |
| `annuler_la_completion` | `taches.py` | 1 |
| `reouvrir_une_tache` | `taches.py` | 1 |
| `archiver_un_parcours_termine` | `instances.py` | 1 (geste manuel) |
| `restaurer_un_parcours` | `instances.py` | 1 (geste manuel) |

**Les treize fonctions ont chacune EXACTEMENT UN appelant HTTP** — même configuration qu'à `T4`/`T5`.
Aucun report vers le niveau des appelants n'était donc nécessaire.

**Trois fonctions internes, sans appelant HTTP propre, ne sont PAS câblées séparément** :

- `archiver_le_parcours_si_termine` — appelée automatiquement par `terminer_une_tache`, qui est
  elle-même câblée. L'archivage automatique d'un parcours terminé est une CONSÉQUENCE de cette
  complétion, pas une décision distincte de l'acteur ;
- `archiver_le_parcours_au_depart` — appelée automatiquement par `app.people.archivage.
  archiver_un_profil`, déjà câblée par `T3` ;
- `remplacer_le_parcours_apres_changement_de_statut` — appelée automatiquement par
  `app.people.ecriture._ecrire_le_statut`, dont le champ `STATUT` est déjà audité PAR CHAMP par
  `modifier_les_donnees_organisationnelles` (`T3`).

Leur donner un second `audit_event` dupliquerait le journal d'UN SEUL geste humain sous deux
entrées. **Même discipline que `T3`** pour l'import CSV et le transfert en masse, qui héritent du
câblage de leurs fonctions partagées sans câblage séparé. Un test dédié
(`test_terminer_la_derniere_tache_obligatoire_n_ecrit_QU_UN_SEUL_audit_event`) prouve que
l'archivage automatique déclenché par `terminer_une_tache` n'écrit effectivement aucun second
`audit_event`.

**`arrival_profile` (la fiche d'arrivée, LOT 7 `T3`) est explicitement hors du texte de `T6`** —
le découpage validé dit « modèles, versions, parcours, tâches », jamais « fiche d'arrivée » — et
n'est couvert par aucune autre sous-étape visible du découpage. Résidu nommé, non bloquant.

## 2.2 Le vocabulaire : réutilisé pour quatre actions, littéral namespacé pour les neuf autres

**`TypeEvenementTache`** (`app.onboarding.modeles`, posé par le LOT 7 `T7`-`T10`) est le journal
PROPRE du domaine (`onboarding_task_event`, §13.7) — six valeurs, dont quatre correspondent
exactement aux quatre gestes sur une tâche câblés ici (`ASSIGNED`, `COMPLETED`, `CANCELLED`,
`REOPENED`). Il est réutilisé TEL QUEL comme `action_code`, même lecture que `TypeEvenementAuth` à
`T2` : une enum posée pour le journal D'UN DOMAINE est le bon vocabulaire pour `audit_event`, sans
en inventer un second. Les deux valeurs restantes (`RETAINED_ON_REPLACEMENT`,
`CANCELLED_ON_REPLACEMENT`) ne sont PAS exercées par `T6` — elles appartiennent à
`remplacer_le_parcours_apres_changement_de_statut`, une des trois fonctions internes non câblées
séparément (§2.1).

**Aucune enum n'existe pour les modèles, les versions ou les parcours** : `EtatDuModele`,
`EtatDeLaVersionDuModele` et `EtatInstance` ne nomment que des ÉTATS (`draft`/`published`/
`retired`, etc.), jamais des ACTIONS — à la différence d'`ActionEvenement`/`ActionEditoriale`. Neuf
littéraux nouveaux couvrent donc ces neuf gestes : `tache_de_reference_creee`, `modele_cree`,
`version_creee`, `taches_de_version_definies`, `version_publiee`, `version_archivee`,
`version_restauree`, `parcours_archive`, `parcours_restaure`. **Chaque littéral est NAMESPACÉ par
ressource** (`version_archivee` plutôt qu'un simple `archiver`) — même convention que `cercle_archive`/
`bureau_restaure` (`T3`) et `lien_cree` (`T4`), continuée ici plutôt que le mot nu employé une seule
fois à `T5` (`"creer"`), qui reste l'exception du corpus plutôt que la règle.

**`definir_les_taches_de_la_version` et `affecter_un_parcours` écrivent UN SEUL `audit_event` pour
l'appel entier**, malgré plusieurs écritures de plus bas niveau :

- `definir_les_taches_de_la_version` remplace la liste ENTIÈRE des tâches d'une version (DELETE
  inconditionnel puis ré-insertion) — un seul geste métier, un seul événement, même principe que
  `reordonner_les_liens` (`T4`) et `gerer_les_medias_d_un_evenement` (`T5`). **Mais, comme ce
  dernier et à la différence de `reordonner_les_liens`, AUCUN retour anticipé n'existe sur une liste
  vide** : le `DELETE` s'exécute inconditionnellement, et vider la liste de tâches d'une version
  brouillon est une forme normale de ce geste. Un `audit_event` est donc écrit MÊME quand
  `taches=()`, témoin dédié (`test_la_definition_des_taches_a_vide_ecrit_QUAND_MEME_un_audit_event`) ;
- `affecter_un_parcours` snapshotte N tâches et pose un `onboarding_task_event` PAR tâche (journal
  §13.7, déjà posé par le LOT 7), mais un SEUL `audit_event` pour l'ensemble — « affecter un
  parcours » est une action métier, jamais une par tâche. Un test dédié
  (`test_laffectation_d_un_parcours_ecrit_un_SEUL_audit_event_malgre_plusieurs_taches`) compte
  explicitement les deux journaux pour prouver qu'ils divergent en nombre.

## 2.3 `entity_id` de l'audit porte le périmètre réel de la ressource, jamais celui de l'appelant

Plusieurs ressources de ce domaine peuvent être GLOBALES (`entity_id IS NULL`) — une tâche de
référence ou un modèle GLOBAL, consultables depuis n'importe quelle entité. Même lecture que
`creer_une_entite` à `T3` (`entity_id` de l'audit est l'entité qui vient de naître, jamais celle de
l'appelant) : `entity_id` de l'audit est l'`entity_id` RÉEL de la ressource créée — `None` pour un
modèle ou une tâche GLOBAL, même quand la route a été appelée depuis une entité précise. Un test
dédié (`test_la_creation_d_une_tache_GLOBALE_ecrit_un_audit_event_SANS_entite`) le prouve
explicitement.

Cette discipline a exigé de faire voyager `entite_du_modele`/`modele.entity_id` jusqu'aux fonctions
de cycle de vie d'une version (`creer_une_version`, `publier_une_version`, `archiver_une_version`,
`restaurer_une_version`), qui n'en avaient pas besoin pour leur propre logique métier.

## 2.4 Six fonctions sur treize ne recevaient ni `acteur` ni `instant` — étendues STRICTEMENT pour l'audit

`creer_une_tache_de_reference`, `creer_un_modele`, `creer_une_version`,
`definir_les_taches_de_la_version`, `archiver_une_version`, `restaurer_une_version` et
`restaurer_un_parcours` ne recevaient, avant ce câblage, ni l'acteur ni l'instant de leur appel — un
choix documenté du LOT 7 : « aucun motif, aucun acteur tracé sur l'archivage ni la restauration »
(`app/onboarding/cycle_de_vie.py`, en-tête), parce que le modèle §13.3 ne déclare aucune colonne
`archived_by_person_id` pour `onboarding_template_version`.

Ces sept fonctions ont été étendues pour recevoir `acteur: uuid.UUID`/`instant: dt.datetime` (ou les
deux), **STRICTEMENT pour alimenter l'appel à `enregistrer_un_evenement`** — aucune n'écrit ces
valeurs dans une colonne métier qu'elle n'écrivait pas déjà. Le choix documenté du LOT 7 reste donc
intact : `onboarding_template_version` ne porte toujours aucune trace de qui l'a archivée ou
restaurée dans ses propres colonnes ; seul `audit_event`, la table dédiée du LOT 10, porte
désormais cette trace, exactement le rôle pour lequel elle a été posée à `T1`.

## 2.5 Aucun défaut trouvé en câblant — mesuré, mais sept fichiers de test ont dû être étendus

**Comme à `T4`/`T5`, aucun défaut n'a été trouvé en câblant ces treize fonctions sur le plan
infrastructure**, et ce n'est pas présumé : une recherche exhaustive, menée AVANT tout code, a
cherché les mêmes classes de défaut déjà documentées à `T2`-`T5` :

- **grep sur `infra/scripts/verifier-*.py`** pour toute suppression des sept tables de l'onboarding :
  un seul script en porte, `verifier-administration-onboarding.py` (LOT 7 `T14`, `make
  onboarding-check`), et son décor nettoie DÉJÀ `audit_event` par `actor_person_id` ET par
  `entity_id` — déjà correct avant même ce câblage, aucun correctif requis ;
- **grep sur tous les fichiers de test exerçant une route HTTP réelle** de ce domaine (via
  `TestClient`, avec un nettoyage manuel plutôt que la fixture `cx` en rollback) : **SEPT fichiers**
  correspondent et ne portaient AUCUNE mention `audit_event` — `test_modeles_onboarding.py`,
  `test_instances_onboarding.py`, `test_taches_onboarding.py`, `test_reouverture_onboarding.py`,
  `test_catalogue_des_taches.py`, `test_suivi_onboarding.py`, `test_cycle_de_vie_des_modeles.py`.
  **Exactement la classe déjà documentée pour les « neuf fichiers » de `T2`** (§7.30 de la
  passation) : une table nouvelle qui référence `person`/`entity` rend incomplet un nettoyage qui
  l'ignore. Corrigés en ajoutant, dans chacun, les deux lignes `audit_event` symétriques
  (`actor_person_id`, `entity_id`), AVANT `person`/`entity` ;
- trois fichiers qui appellent les fonctions directement (sans `TestClient`, donc via la fixture
  `cx` en rollback) ont dû mettre à jour leurs appels pour les nouveaux paramètres
  (`test_remplacement_onboarding.py`) mais n'avaient aucun résidu à nettoyer.

**Cette mesure a été vérifiée empiriquement, pas seulement déduite par grep** : `make
onboarding-check` (le contrôle de pile réelle du LOT 7 `T14`, 14 contrôles) a été rejoué sur la pile
réelle (après `make code-refresh`) une fois le câblage en place — 14/14, 0 échec, y compris le
témoin d'asymétrie DSM/ESM et `ECART-066` éprouvé dans le sens du refus.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_audit_onboarding.py` | **18/18** |
| suite complète du domaine onboarding (18 fichiers existants) + `test_audit_onboarding.py` | **180/180** |
| `make onboarding-check` (pile réelle, 14 contrôles) | **14/14**, 0 échec, décor nettoyé |
| collecte depuis la racine | **1 777 pytest** (+18), dont **1 344 d'intégration** (+18) |
| `uv run mypy` racine | vert, **248 fichiers** (+1) |
| `uv run ruff check`/`format` racine | verts |
| `make sources-check` | vert, 669 fichiers examinés |
| `make residu-check` | mêmes 71 échecs environnementaux, **aucun résidu** signalé |
| comparaison de worktree `origin/develop` (§7.22 de la passation) | **71 échecs identiques, un par un**, `diff` vide entre les deux listes triées |

---

# 4. Décisions et écarts

- `DEC-660` consigne la réalisation et les choix dérivés du modèle ;
- aucun écart n'est ouvert ni fermé par `T6` ; `ECART-064` (motif du super-administrateur) reste à
  fermer à `T7`, sans rapport avec le domaine de `T6`.

---

# 5. Ce que `T6` laisse

- treize fonctions métier du LOT 7 câblées sur le service générique de `T2` ;
- sept fichiers de test corrigés pour nettoyer `audit_event` ;
- aucun résidu d'infra à corriger, confirmé par `make onboarding-check` sur la pile réelle ;
- un résidu nommé (pas un défaut) : la fiche d'arrivée (`arrival_profile`, LOT 7 `T3`) n'est câblée
  par aucune sous-étape visible du découpage du LOT 10 — ni `T6`, dont le texte ne la nomme pas, ni
  une autre sous-étape identifiée ;
- `ECART-064` reste ouvert, à fermer à `T7` ;
- la divergence des annotations `lot=` du §30.19-24 dans `verifier-recette-modele.py` intacte, à
  vérifier à `T16`.

# Validation demandée à Jonathan

`T6` est faite. Après fusion, la prochaine sous-étape est `T7` : le câblage sur l'import CSV et le
back-office (LOT 9), et le motif obligatoire des interventions du super-administrateur
(`ECART-064`).
