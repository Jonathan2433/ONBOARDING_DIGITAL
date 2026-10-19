# Compte rendu — `T7` du LOT 10 : le câblage sur l'import CSV et le back-office, et le motif obligatoire du super-administrateur

**Sous-étape :** la septième du lot — câblage sur l'import CSV et le back-office (LOT 9), fermeture
de `ECART-064`
**Date :** 19 octobre 2026
**Décision :** `DEC-661`
**Stories :** `MVP-L10-US001`/`US002`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, **`T7`** |
| Restent | `T8` à `T16` |
| Issues | épic `#267`, stories `#268` à `#275`, jalon `G10` |

---

# 2. Deux arbitrages posés AVANT tout code

`fiche-lot-10.md` donne à `T7` deux textes distincts : câbler le service générique sur le reste du
LOT 9 (dépôt, décisions, lancement, rejeu — le transfert en masse et la création d'entité héritent
déjà du câblage de `T3`, voir §2.1), et fermer `ECART-064` — « aucune route n'écrit de motif pour
une intervention du super-administrateur dans une entité » (§18.1 du cahier, `RIGHTS-017`). L'écart
nomme sa propre recommandation (« ne pas l'implémenter dans `T7` [du LOT 6] seul […] l'instruire
avec `audit_event`, LOT 10 ») mais ne tranche ni la PORTÉE ni le MÉCANISME exact — deux questions
posées à Jonathan avant d'écrire une ligne, chacune reformulée sans jargon (`AskUserQuestion`).

**Question 1 — la portée.** Fermer `ECART-064` pour les seules fonctions NOUVELLES de `T7` (le
dépôt et la décision d'import) laisserait un motif exigé sur une route sur quarante et aucune part
ailleurs — exactement la forme du garde-fou à couverture partielle que l'écart lui-même met en
garde contre. Réponse de Jonathan : **« Large, maintenant »** — toucher les ~25 fonctions déjà
câblées par `T2` à `T6`, mettre à jour leurs tests, plutôt que de fermer l'écart par moitié.

**Question 2 — le mécanisme.** Le motif est-il exigé quand l'acteur PORTE globalement le rôle
`SUPER`, ou seulement quand `SUPER` est le rôle qui a RÉELLEMENT autorisé cet appel précis ? Réponse
de Jonathan : **« Le rôle réellement utilisé est SUPER »** — `SUPER` n'a pas d'entité à lui : toute
action qu'il mène dans une entité particulière compte, mais un ESM ou un ADM-E qui fait la même
action dans SA PROPRE entité n'a aucun motif à fournir. Dans ce projet, `resoudre_les_permissions`
ajoute `SUPER_ADMINISTRATEUR` à l'ensemble des rôles pour N'IMPORTE QUELLE entité, sans condition
(« branche 1 », global) — la question « SUPER est-il PARMI les rôles qui ont autorisé cet appel ? »
est donc, dans TOUS les cas mesurés de ce dépôt, équivalente à « l'acteur porte-t-il globalement
`SUPER` ? ». Aucune distinction entité-principale n'était donc nécessaire pour appliquer la réponse
littéralement.

---

# 3. Ce que la sous-étape a produit

## 3.1 Le module partagé, `app/audit/motif.py`

Un seul mécanisme, réutilisé partout — jamais un second écrit pour une seule route (§7.27) :

- `motif_exige_pour_cet_appel(roles_autorisants: frozenset[RoleDeLaMatrice]) -> bool` — `SUPER_ADMINISTRATEUR in roles_autorisants` ;
- `exiger_un_motif_si_necessaire(roles_autorisants, motif) -> None` — lève `ErreurApplicative(code="motif_obligatoire", statut=422)` si le motif est exigé et absent ou vide ;
- `DemandeDeMotif` — le corps Pydantic PARTAGÉ (`motif: str | None`, `max_length=2000`) pour les
  routes qui n'avaient jusqu'ici AUCUN corps (publier/archiver/restaurer une version, affecter/
  archiver/restaurer un parcours, lancer un import, rejouer une ligne).

## 3.2 Câblage NEUF — six action-codes qu'aucune sous-étape n'avait encore audités

Ces six écritures n'avaient JAMAIS appelé `enregistrer_un_evenement` avant `T7` — contrairement au
reste du lot, ce n'est pas un retrofit d'enforcement, c'est le premier audit de ces fonctions :

| Fonction | Fichier | `action_code` | Remarque |
|---|---|---|---|
| `deposer_un_csv` | `imports/depot.py` | `import_lot_depose` | un seul `audit_event` pour dépôt ET prévisualisation, même transaction |
| `enregistrer_une_decision` | `imports/decisions.py` | `decision_d_import_enregistree` | `reason` du corps sert DEUX fins : la justification métier (facultative, déjà posée au LOT 9) ET le motif du §18.1 (obligatoire pour `SUPER`) |
| `_accorder_les_responsabilites` | `imports/execution.py` | `responsabilites_framework_accordees` | un seul événement pour TOUTES les responsabilités accordées à une ligne ; rien n'est écrit si la liste est vide (pas de `DELETE` inconditionnel ici, à la différence de `definir_les_taches_de_la_version`) |
| `_accorder_les_roles_techniques` | `imports/execution.py` | `roles_techniques_accordes_a_l_import` | même discipline |
| `_rafraichir_les_cercles_secondaires` | `imports/execution.py` | `cercles_secondaires_rafraichis` | fermeture ET ouverture de cercles sont LA MÊME action métier, un seul événement — même lecture que `changer_d_entite` à `T3` |
| `_resoudre_les_dsm` | `imports/execution.py` | `dsm_resolu_a_l_import` | UN événement PAR appartenance résolue, pas un seul pour l'appel — cette boucle traite déjà des personnes distinctes dans un seul appel, les agréger masquerait qui a reçu quoi |

`lancer_l_import` et `rejouer_une_ligne` reçoivent toutes deux `exiger_un_motif_si_necessaire(roles,
motif)` en première instruction, puisqu'elles reçoivent déjà `roles` pour leur propre garde
métier — et transmettent le MÊME `motif` à chaque sous-écriture qu'elles orchestrent
(`_traiter_une_ligne` → `_creer`/`_mettre_a_jour` → les quatre fonctions ci-dessus) : **une seule
intervention humaine, un seul motif, répété sur chaque `audit_event` qu'elle produit**, jamais un
motif différent par sous-écriture.

## 3.3 Câblage RETROFIT — l'enforcement ajoutée aux ~25 fonctions déjà auditées par `T2`-`T6`

Portée « Large, maintenant » : `exiger_un_motif_si_necessaire` est ajoutée partout où `SUPER` peut
authentiquement autoriser l'appel, dans six domaines :

| Domaine | Fonctions/routes couvertes |
|---|---|
| Personnes et organisation (LOT 2/4/5/9, câblées à `T3`) | `creer_un_collaborateur`, `modifier_les_donnees_organisationnelles`, `changer_d_entite`, `archiver_un_profil`/`restaurer_un_profil`, `archiver_un_cercle`/`restaurer_un_cercle`/`archiver_un_bureau`/`restaurer_un_bureau`, `creer_une_entite`, `executer_le_transfert_en_masse` |
| Contenus et Framework (LOT 6, câblées à `T4`) | `creer_une_page`, `remplacer_le_contenu`, `publier_une_page`/`archiver_une_page`/`restaurer_une_page`, `creer_un_lien`/`modifier_un_lien`/`reordonner_les_liens` |
| Événements (LOT 8, câblées à `T5`) | `creer_un_evenement`/`modifier_un_evenement`, `publier_un_evenement`/`annuler_un_evenement`/`archiver_un_evenement`/`restaurer_un_evenement`, `gerer_les_medias_d_un_evenement` |
| Onboarding (LOT 7, câblées à `T6`) | `creer_une_tache_de_reference`, `creer_un_modele`/`creer_une_version`/`definir_les_taches_de_la_version`, `publier_une_version`/`archiver_une_version`/`restaurer_une_version`, `affecter_un_parcours`/`archiver_un_parcours_termine`/`restaurer_un_parcours` |
| Import CSV (LOT 9, câblées à `T7` elle-même) | `deposer_un_csv`, `enregistrer_une_decision`, `lancer_l_import`, `rejouer_une_ligne` |
| Entités (LOT 9, câblée à `T3`) | `creer_une_entite` — motif **obligatoire** (non conditionnel), voir §3.4 |

**Trente-huit sites d'appel** à `exiger_un_motif_si_necessaire` existent désormais dans
`apps/api/app/` (mesuré par grep), répartis sur neuf fichiers.

## 3.4 Deux emplacements d'application, selon ce que la fonction reçoit déjà

- **à l'intérieur du service**, quand il reçoit déjà `roles: frozenset[RoleDeLaMatrice]` pour sa
  propre garde métier (`creer_un_evenement`, `modifier_un_evenement`, `lancer_l_import`,
  `rejouer_une_ligne`, `enregistrer_une_decision`) ;
- **à la route**, juste après un appel FRAIS à `resoudre_les_permissions`, pour toutes les autres —
  ce qui a exigé d'ÉTENDRE trois fonctions d'aide partagées qui résolvaient déjà l'entité et le rôle
  mais jetaient l'information : `_resoudre_le_cycle` (`people/routes.py`, rend désormais un
  3-uplet `(entite_id, perimetre, roles)` au lieu d'un 2-uplet), `_resoudre_l_entite_et_verifier_le_role`
  (`organization/routes.py`, rend `(entite_id, roles)`), `_agir` (`content/routes.py`, reçoit et
  transmet `roles`). Plusieurs routes n'avaient ENCORE AUCUN appel à `resoudre_les_permissions` à
  leur niveau (la garde de rôle coarse suffisait jusqu'ici) : un appel neuf a dû y être ajouté avant
  de pouvoir vérifier le motif.

**`entities/routes.py` est le seul cas où le motif est REQUIS plutôt que conditionnel** : la garde
de cette route n'admet QUE `SUPER` (`_exiger_le_super_administrateur`), donc l'intersection avec les
rôles autorisants vaut TOUJOURS `{SUPER}` — `DemandeDeCreationDEntiteRequete.motif` porte
`Field(min_length=1, ...)`, sans défaut, plutôt qu'un appel conditionnel qui serait toujours vrai.

## 3.5 Un défaut trouvé en câblant, corrigé avant commit (`T7-1`)

`_creer` (`imports/execution.py`) transmettait `motif` à `attribuer_la_categorie_dg`, aux trois
fonctions d'octroi (§3.2) et à `_archiver_si_depart_passe`, mais **omettait `motif=motif` dans son
propre appel à `creer_un_collaborateur`**. Trouvé par mon propre test
(`test_rejouer_une_ligne_herite_le_meme_cablage`, qui attend `reason == "Rejeu autorise"` sur
l'événement `collaborateur_cree`) : l'assertion échouait sur `reason: None`. Corrigé en ajoutant le
mot-clé manquant, re-vérifié par la suite complète de `test_audit_imports.py`.

## 3.6 Un test d'infrastructure corrigé

`infra/scripts/verifier-back-office.py` crée une entité avec `cookie_super` pour éprouver `US007`
(§3 du script) : le corps ne portait pas `motif`, devenu requis par §3.4 — `make back-office-check`
échouait (`422 motif_obligatoire` au lieu de `201`). Corrigé en ajoutant `"motif": "Controle de pile
back-office"` au corps de cet unique appel ; les autres scripts de pile (`onboarding-check`,
`framework-check`, `accueil-check`, `permissions-check`) n'utilisent jamais `SUPER` comme acteur
d'une écriture et n'ont nécessité aucun correctif, confirmé en les rejouant tous après `make
code-refresh`.

## 3.7 Trente-cinq régressions de test, toutes attendues, toutes corrigées

La conséquence DIRECTE et attendue du choix « Large, maintenant » : `uv run pytest -q` est passé de
71 échecs (baseline) à 106 sur la branche avant correction. Diagnostiqué par comparaison de
worktree (`git worktree add … origin/develop`, §7.22 de la passation) : les 35 différences se
répartissent en deux classes, aucune n'étant un défaut du mécanisme lui-même —

- des assertions Pydantic à ensemble de champs EXACT (`set(corps.keys()) == {...}`), qui doivent
  désormais compter `"motif"` ;
- des décors de test qui utilisent `SUPER` comme acteur « qui peut tout faire » par commodité, sans
  lui fournir de motif, désormais refusés en `422`.

**Onze fichiers de test corrigés**, chacun en étendant l'aide locale partagée qui construit le corps
JSON plutôt qu'en dupliquant le correctif par test (§7.27) : `test_audit_evenements.py`,
`test_catalogue_des_taches.py`, `test_archivage_onboarding.py`, `test_creation_evenements.py`,
`test_cycle_de_vie_des_modeles.py`, `test_modeles_onboarding.py`, `test_instances_onboarding.py`,
`test_annulation_archivage_et_restauration_evenements.py`, `test_cycle_de_vie_des_contenus.py`,
`test_liens_internes.py`, `test_medias_evenements.py`, `test_modification_et_publication_evenements.py`.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_audit_imports.py` | **6/6** |
| onze fichiers de test retouchés, rejoués individuellement | tous verts (129+24+37+… tests) |
| collecte depuis la racine | **1 783 pytest** (+6), dont **1 350 d'intégration** (+6) |
| `uv run pytest -q` (suite complète) | **1 712 passed, 71 failed** |
| comparaison de worktree `origin/develop` | **71 échecs identiques, un par un**, `diff` vide entre les deux listes triées |
| `make residu-check` | mêmes 71 échecs environnementaux, **aucun résidu** signalé |
| `uv run mypy` racine | vert, **250 fichiers** (+2 : `app/audit/motif.py`, `tests/test_audit_imports.py`) |
| `uv run ruff check`/`format` racine | verts |
| `make sources-check` | vert, 672 fichiers examinés |
| `make onboarding-check` (pile réelle) | **14/14**, 0 échec |
| `make back-office-check` (pile réelle) | **16/16**, 0 échec (1 échec puis corrigé, §3.6) |
| `make framework-check` (pile réelle) | **77/77**, 0 échec |
| `make accueil-check` (pile réelle) | **29/29**, 0 échec |
| `make permissions-check` (pile réelle) | **15/15**, 0 échec |

Aucune migration, aucune route de lecture nouvelle : `T7` câble des fonctions déjà posées, et ajoute
l'enforcement sur des fonctions déjà auditées.

---

# 5. Décisions et écarts

- `DEC-661` consigne la réalisation, les deux arbitrages de Jonathan et le mécanisme retenu ;
- **`ECART-064` est CLOS** — toute intervention d'un super-administrateur dans une entité exige
  désormais un motif, tracé dans `audit_event.reason`. Les colonnes `archive_reason`/
  `assignment_reason` (modèle §3.1/§8.4) restent un résidu NOMMÉ, jamais écrites : la
  recommandation de l'écart demandait d'instruire le motif « avec `audit_event` », pas dans ces deux
  colonnes, et `audit_event` est la table qui porte à la fois le motif, l'acteur et le moment — un
  lecteur unique, plutôt qu'un champ dupliqué que personne ne lirait (`ECART-061` a montré ce que
  cela coûte).

---

# 6. Ce que `T7` laisse

- trente-huit sites d'application du motif obligatoire, sur neuf fichiers, six domaines ;
- six nouvelles actions d'audit jamais tracées avant `T7`, toutes dans le pipeline d'import ;
- `ECART-064` clos, comme prévu par la fiche du lot ;
- `QO-092` (destination des signalements) et la divergence des annotations `lot=` du §30.19-24 dans
  `verifier-recette-modele.py` restent intactes, non résolues par intuition, sans rapport avec `T7`.

# Validation demandée à Jonathan

`T7` est faite. Après fusion, la prochaine sous-étape est `T8` du LOT 10 (découpage validé).
