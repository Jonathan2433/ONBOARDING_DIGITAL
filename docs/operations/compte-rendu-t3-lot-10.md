# Compte rendu — `T3` du LOT 10 : le câblage sur les personnes et l'organisation

**Sous-étape :** la troisième du lot — câblage sur les personnes et l'organisation (LOT 2, 4, 5, 9)
**Date :** 15 octobre 2026
**Décision :** `DEC-657`
**Stories :** `MVP-L10-US001`/`US002`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, **`T3`** |
| Restent | `T4` à `T16` |
| Issues | épic `#267`, stories `#268` à `#275`, jalon `G10` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/people/creation.py` | `creer_un_collaborateur` écrit aussi `audit_event` (`"collaborateur_cree"`, `resource_type="person"`) |
| `apps/api/app/people/ecriture.py` | `modifier_les_donnees_organisationnelles` écrit un `audit_event` **par champ** réellement modifié (`action_code` = `ChampOrganisationnel.value`) |
| `apps/api/app/people/transfert.py` | `changer_d_entite` écrit aussi `audit_event` (`"collaborateur_transfere"`, `old_values`/`new_values` portant les deux entités) |
| `apps/api/app/people/archivage.py` | `archiver_un_profil`/`restaurer_un_profil` écrivent aussi `audit_event` (`action_code` = `ActionDeCycleDeVie.value`) |
| `apps/api/app/organization/cycle_de_vie.py` | les quatre fonctions cercle/bureau écrivent aussi `audit_event` (`"cercle_archive"`/`"cercle_restaure"`/`"bureau_archive"`/`"bureau_restaure"`) |
| `apps/api/app/entities/creation.py` | `creer_une_entite` écrit aussi `audit_event` (`"entite_creee"`, `resource_type="entity"`) |
| `apps/api/app/organization/services.py` | `attribuer_la_categorie_dg` écrit aussi `audit_event` (`"categorie_dg_attribuee"`) ; défaut du double calcul d'instant corrigé au passage |
| `apps/api/tests/test_audit_organisation.py` | **13 tests d'intégration**, le câblage lui-même |
| `apps/api/tests/test_archivage_onboarding.py` | nettoyage de décor étendu à `audit_event` (défaut trouvé par la suite elle-même) |
| 8 fichiers `infra/scripts/verifier-*.py` | nettoyage de décor étendu à `audit_event` par `entity_id`, en plus de `actor_person_id` |

Aucune migration, aucune route : `T3` câble sept fonctions déjà posées par les LOTS 2/5/9 sur le
service générique de `T2`, exactement le périmètre que `fiche-lot-10.md` lui donne.

## 2.1 Le périmètre retenu, et pourquoi

Le découpage validé nomme : « créations, modifications, changements de rôle/DSM/cercle/client/
statut/entité, archivages et restaurations déjà servis par les LOTS 2/4/5/9 ». Mesuré avant
d'écrire une ligne (recherche exhaustive des sites d'écriture métier sur `person`,
`entity_membership` et ses cinq relations, `circle`, `office`, `entity`) : sept fonctions
couvrent exactement cet énoncé, et aucune autre n'écrit sur ces tables en dehors d'elles
(hors import CSV, voir §2.4) :

| Fonction | Module | Ce qu'elle écrit |
|---|---|---|
| `creer_un_collaborateur` | `people/creation.py` | `person` + les cinq relations de l'appartenance (LOT 9 `T2`) |
| `modifier_les_donnees_organisationnelles` | `people/ecriture.py` | date d'arrivée, métier, statut/client, DSM, cercle principal (LOT 5 `T7`) |
| `changer_d_entite` | `people/transfert.py` | fermeture de l'ancienne appartenance, ouverture de la nouvelle (LOT 9 `T3`) |
| `archiver_un_profil`/`restaurer_un_profil` | `people/archivage.py` | cycle de vie d'une appartenance (LOT 5 `T8`) |
| `archiver_un_cercle`/`restaurer_un_cercle`/`archiver_un_bureau`/`restaurer_un_bureau` | `organization/cycle_de_vie.py` | cycle de vie d'un cercle ou d'un bureau (LOT 9 `T4`) |
| `creer_une_entite` | `entities/creation.py` | une entité et son premier administrateur (LOT 9 `T12`) |
| `attribuer_la_categorie_dg` | `organization/services.py` | la catégorie `dg` et sa responsabilité DSM (LOT 2 `T11`) |

**Aucune de ces sept fonctions n'est câblée deux fois pour un même appelant.** `creer_l_appartenance`
(appelée par `creer_un_collaborateur` ET par `changer_d_entite`) n'est PAS câblée elle-même : chaque
appelant porte sa propre sémantique (« création » contre « transfert ») et son propre
`action_code` — câbler le point bas commun aurait masqué cette différence.

## 2.2 Le vocabulaire : réutilisé quand il existe, littéral sinon (§7.27)

Deux énumérations du périmètre existent déjà et sont réutilisées telles quelles, comme
`TypeEvenementAuth` l'a été à `T2` :

- **`ChampOrganisationnel`** (`app.permissions.perimetre`, posée au LOT 5 `T7`) — les six valeurs
  du §10.2 (`date_d_arrivee`, `metier`, `statut`, `client`, `dsm`, `cercle_principal`) deviennent
  directement l'`action_code` du champ qu'elles désignent ;
- **`ActionDeCycleDeVie`** (même module, posée au LOT 4) — `archiver`/`restaurer` servent
  l'archivage et la restauration d'un profil, exactement les deux valeurs que la grille de
  permission du module nomme déjà.

Pour les actions qu'aucune énumération ne nomme, six littéraux sont posés, un par action
distincte : `collaborateur_cree`, `collaborateur_transfere`, `cercle_archive`/`cercle_restaure`,
`bureau_archive`/`bureau_restaure`, `entite_creee`, `categorie_dg_attribuee`.

**Une seule fonction émet plusieurs lignes d'audit par appel** : `modifier_les_donnees_
organisationnelles` écrit UN `audit_event` PAR CHAMP réellement écrit, jamais un seul pour l'appel
entier. La granularité suit `Modification.champs` — l'ensemble que la fonction rapporte DÉJÀ à son
appelant (§18.3) — plutôt que d'inventer une seconde notion de « ce qui a changé ». Un champ
redonné à sa valeur courante (`ecrits` vide pour lui) n'écrit donc AUCUNE ligne, témoin exécuté.
Les six autres fonctions écrivent exactement une ligne par appel, la même discipline que `T2`.

## 2.3 Héritage sans câblage séparé — l'import CSV et le transfert en masse

**Aucune des sept fonctions câblées n'est dupliquée pour servir l'import ou le transfert en
masse** : `app.imports.execution` (LOT 9 `T9`/`T10`) appelle directement `creer_un_collaborateur`,
`modifier_les_donnees_organisationnelles`, `archiver_un_profil`, `restaurer_un_profil` et
`attribuer_la_categorie_dg` ; `app.people.transfert_masse` (LOT 9 `T11`) appelle directement
`changer_d_entite`, une fois par élément, dans son propre savepoint. Câbler au niveau de la
fonction PARTAGÉE suffit donc à couvrir les deux chemins sans rien ajouter dans `imports/
execution.py` ni dans `transfert_masse.py` — y compris le mode `apercu` de ce dernier, dont chaque
savepoint est systématiquement annulé : l'`audit_event` écrit à l'intérieur l'est aussi.

**Cela acquitte, pour sa part, la dette que `transfert_masse.py` nommait explicitement** : son
en-tête disait « Aucune écriture d'audit : … `audit_event` reste hors du périmètre de ce lot
(`ECART-064`, LOT 10) ». Le critère d'acceptation de `US003` nommait « auditées » ; `T3` le tient
désormais, sans qu'aucune ligne de `transfert_masse.py` n'ait eu à changer.

**Ce qui reste HORS du périmètre de `T3`, nommé et non oublié** : les écritures PROPRES à l'import,
sans équivalent dans aucune fonction partagée — `_accorder_les_responsabilites` (Framework,
au-delà de la catégorie `dg`), `_accorder_les_roles_techniques`, `_rafraichir_les_cercles_
secondaires`, `_resoudre_les_dsm` (passe 2, `F16`) dans `app.imports.execution`. Le découpage validé
réserve explicitement l'import CSV à `T7` (« câblage sur l'import CSV et le back-office »), qui
devra décider s'il les cite une à une ou les laisse à un résidu nommé.

## 2.4 Deux défauts trouvés en câblant, corrigés avant commit

**(1) `attribuer_la_categorie_dg` calculait l'instant courant DEUX FOIS indépendamment.** Quand
`debut` est omis, la fonction appelait `dt.datetime.now(tz=dt.UTC)` une fois pour `starts_at` de la
responsabilité DSM créée, et — en ajoutant l'audit — une seconde fois pour `occurred_at`, à
quelques microsecondes de la première. Exactement la classe déjà documentée pour `creer_un_jeton`
(§7.0 sixième proposition de la passation, §7.47 : « deux grandeurs qu'une contrainte compare
doivent venir de la même source »). Corrigé en résolvant l'instant UNE SEULE fois, en tête de
fonction, réutilisé par les deux écritures. Un test witness (`test_l_attribution_de_la_categorie_
dg_ecrit_un_audit_event`) compare `audit_event.occurred_at` à `framework_responsibility_
assignment.starts_at` et exige l'égalité STRICTE — sans quoi la divergence, invisible par ailleurs
(l'écart est de l'ordre de la microseconde), ne serait jamais mesurée.

**(2) `audit_event.entity_id` porte une clé étrangère vers `entity`, jamais exercée par `T2`.**
L'authentification n'écrit jamais `entity_id` (ses événements ne sont pas scopés par entité) ; les
sept fonctions de `T3` l'écrivent TOUTES. Mesure avant d'attendre un échec de CI : huit scripts
`infra/scripts/verifier-*.py` créent puis suppriment une entité de test par marqueur
(`back-office`, `accueil-evenements`, `administration-onboarding`, `csrf`, `profil`, `magic-link`,
`permissions`, `trombinoscope`) et auraient échoué en violation de clé étrangère à leur prochaine
exécution — exactement la classe déjà documentée à `T2` pour `actor_person_id` (§7.30 : une table
nouvelle qui référence une autre rend incomplet un nettoyage qui l'ignore), trouvée ici par grep
exhaustif sur `DELETE FROM entity` plutôt que d'attendre que chacun des huit échoue un par un en
CI. Corrigé en ajoutant, dans chaque script, une ligne `DELETE FROM audit_event WHERE entity_id IN
(…)` immédiatement avant la suppression de l'entité.

**Un troisième défaut, réel celui-là, a été trouvé PAR LA SUITE ELLE-MÊME, pas par une mesure
préalable** : `test_archivage_onboarding.py` (LOT 7 `T11`) exerce la route HTTP réelle d'archivage
d'un profil (donc `archiver_un_profil`, désormais câblée) avec un nettoyage manuel qui ne portait
pas `audit_event`. Révélé par la comparaison de worktree complète — 2 erreurs sur la branche, 0 sur
`origin/develop`, seul écart entre les deux listes triées — et non par une inspection a priori de
ce fichier, qui n'avait pourtant pas été identifié par la recherche initiale des sites candidats
(cette recherche portait sur les fonctions de SERVICE, pas sur les fichiers de test qui les
exercent via `TestClient`). Corrigé en ajoutant les deux lignes symétriques
(`actor_person_id`, `entity_id`).

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_audit_organisation.py` | **13/13** |
| collecte depuis la racine | **1 738 pytest** (+13), dont **1 305 d'intégration** (+13) |
| `uv run mypy` racine | vert, **245 fichiers** (+1) |
| `uv run ruff check`/`format` racine | verts |
| `make docs-check` | vert |
| `make residu-check` | mêmes 73 échecs environnementaux, **aucun résidu** signalé |
| comparaison de worktree `origin/develop` (§7.22 de la passation) | **73 échecs identiques, un par un**, `diff` vide entre les deux listes triées |

**La comparaison de worktree a, dans un premier temps, rendu 2 erreurs de PLUS sur la branche que
sur `origin/develop`** (`test_archivage_onboarding.py`, §2.4) : c'est cet écart, et lui seul, qui a
révélé le troisième défaut. Une fois corrigé, un second passage complet des deux côtés rend une
liste byte pour byte identique (73 `FAILED`, 0 `ERROR`, des deux côtés) — la preuve que la mesure a
bien été refaite après correction, pas seulement supposée réparée.

---

# 4. Décisions et écarts

- `DEC-657` consigne la réalisation et les choix dérivés du modèle ;
- `ECART-064` (motif d'intervention du super-administrateur) n'est PAS fermé par `T3` — aucune des
  sept fonctions câblées n'écrit `archive_reason`/`assignment_reason`, et le découpage validé
  réserve cette fermeture à `T7` (« ferme `ECART-064` ») ;
- la dette nommée par le module `app.people.transfert_masse` pour `US003` (« aucune écriture
  d'audit ») est acquittée SANS modification de ce module — héritée du câblage de `changer_d_entite`
  (§2.3).

---

# 5. Ce que `T3` laisse

- sept fonctions métier des LOTS 2/5/9 câblées sur le service générique de `T2` ;
- l'import CSV et le transfert en masse (LOT 9) audités sans câblage séparé ;
- les écritures PROPRES à l'import — responsabilités Framework au-delà de `dg`, rôles techniques,
  cercles secondaires, résolution du DSM en passe 2 — restent hors du périmètre de `T3`, nommées
  pour `T7` (§2.3) ;
- `ECART-064` reste ouvert, à fermer à `T7` ;
- la divergence des annotations `lot=` du §30.19-24 dans `verifier-recette-modele.py` intacte, à
  vérifier à `T16`.

# Validation demandée à Jonathan

`T3` est faite. Après fusion, la prochaine sous-étape est `T4` : le câblage sur les contenus et le
Framework (LOT 6).
