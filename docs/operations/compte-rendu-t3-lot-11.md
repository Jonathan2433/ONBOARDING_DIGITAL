# Compte rendu — `T3` du LOT 11 : organisation

**Sous-étape :** la troisième du lot, hors backlog (`fiche-lot-11.md` §1.2) — création d'un cercle
et d'un bureau, attribution (et retrait) du Booster d'un cercle et d'un responsable de bureau, hors
import CSV
**Date :** 31 octobre 2026
**Décision :** `DEC-678`
**Périmètre :** matrice §10.2, §10.3, §20 — aucune story officielle du backlog, comble un trou
constaté par Jonathan à l'ouverture du lot

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 11**, ouvert le 30/10/2026 (`DEC-674`), **sept** sous-étapes |
| Faites | `T1` (`DEC-676`), `T2` (`DEC-677`), **`T3`** (`DEC-678`) |
| Restent | `T4` à `T7` |
| Issues | aucune — aucune issue GitHub n'existe encore pour ce lot |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/organization/creation.py` | nouveau module : `creer_un_cercle`, `creer_un_bureau`, `attribuer_le_booster`, `retirer_le_booster`, `attribuer_un_responsable_de_bureau`, `retirer_un_responsable_de_bureau` |
| `apps/api/app/organization/perimetre.py` | `ROLES_D_ATTRIBUTION_FRAMEWORK` (nouveau), en-tête mis à jour — `ROLES_DE_CYCLE_DE_VIE_FRAMEWORK` sert aussi la création |
| `apps/api/app/organization/routes.py` | six routes neuves, `_resoudre_l_entite_et_verifier_le_role` rendue paramétrable (`roles_autorises`) |
| `apps/api/tests/test_creation_organisation.py` | 17 tests — créations, remplacement du Booster, ajout d'un responsable, bornes, motif |
| `apps/api/tests/test_contrat_roles_lot11.py` | 2 tests — confrontation `rolesAttributionFramework` ↔ `ROLES_D_ATTRIBUTION_FRAMEWORK` |
| `packages/contracts/src/organisationCreationEtAttribution.ts` | chemins, codes, types de requête/réponse, validateurs des six routes |
| `packages/contracts/src/contrat-api.json` | six entrées (`creationDUnCercle`, `creationDUnBureau`, `attributionDuBoosterDUnCercle`, `retraitDuBoosterDUnCercle`, `attributionDUnResponsableDeBureau`, `retraitDUnResponsableDeBureau`), nouvelle grille `rolesAttributionFramework` |
| `packages/contracts/src/index.ts` | réexporte le nouveau module |
| `apps/web/src/api/organisation.ts` | `creerUnCercle`, `creerUnBureau`, `attribuerLeBooster`, `retirerLeBooster`, `attribuerUnResponsableDeBureau`, `retirerUnResponsableDeBureau` |
| `apps/web/src/pages/administration/SectionOrganisation.tsx` | `FormulaireCreationDeCercle`, `FormulaireCreationDeBureau` (dans `SectionCerclesEtBureaux`), `RecherchePersonne`, `SectionAttributionFramework` (nouvelle) |
| `apps/web/src/pages/administration/SectionOrganisation.test.tsx` | nouveau fichier — 9 tests, premier de ce composant |

Aucune migration, aucune nouvelle table : les trois tables du LOT 2 (`circle`, `office`,
`framework_responsibility_assignment`) suffisent — posées depuis `T7`/`T8` de ce lot, jamais
écrites par une route hors import avant celle-ci.

## 2.1 Deux grilles de rôles, mesurées dans la matrice avant tout code

Le §10.2/§10.3 donnent à **« Créer un cercle »**/**« Créer un bureau »** la MÊME grille qu'à
l'archivage et la restauration (`ESM`/`ADM-E` Entité, `SUPER` Global) — `ROLES_DE_CYCLE_DE_VIE_
FRAMEWORK` (LOT 9, `T4`) est donc **réutilisée telle quelle** pour la création, jamais recopiée
(§7.27 de la passation) : son en-tête, qui annonçait depuis `T4` du LOT 9 « la création […] ne sont
demandées par aucune sous-étape […] la construire ici déborderait le périmètre », est mis à jour
pour dire la fermeture de ce trou plutôt que de laisser croire qu'il reste ouvert (§7.21).

Le §20 donne en revanche à l'**attribution** (et au retrait) du Booster et d'un responsable de
bureau une grille **séparée** : `ESM` Entité, `SUPER` Global, et `ADM-E` **EXCLU** — `ARB-DROIT-002`
le dit en toutes lettres, « l'administrateur d'entité ne peut pas attribuer les responsabilités
Framework ». Une seule case diverge de la grille de création (celle d'`ADM-E`), ce qui justifie une
constante séparée, `ROLES_D_ATTRIBUTION_FRAMEWORK`, plutôt qu'une exception codée en dur sur la
première.

## 2.2 Attribuer le Booster est toujours un remplacement

`uq_framework_responsibility_booster_actif_par_cercle` (modèle §8.4, §25.1) n'autorise qu'un seul
Booster **actif** par cercle : « Affecter **ou remplacer** le Booster » (§10.2, §20) n'est donc
jamais une simple insertion. `attribuer_le_booster` verrouille l'actif du cercle (`FOR UPDATE`),
le ferme s'il diffère de la personne demandée, puis ouvre le nouveau — même patron que
`_ecrire_le_dsm`/`_ecrire_le_cercle` (`app.people.ecriture`, LOT 2). Désigner la personne **déjà**
Booster active du cercle est un **NO-OP** : aucune ligne de plus, aucune période d'une
microseconde, même discipline que ces deux fonctions.

« Une personne ne peut pas être Booster active dans plusieurs entités » (§8.4, §2.5) est un
déclencheur (`fn_booster_une_seule_entite`, migration `0009`), jamais une vérification
applicative — une règle inter-lignes qu'aucun index ne sait exprimer. Son refus est traduit au
format du §18.3 par le **nom** de la contrainte (`CONSTRAINT = 'booster_une_seule_entite'`), jamais
par le texte du message (§7.25 de la passation).

## 2.3 Attribuer un responsable de bureau ajoute, ne remplace jamais

Le §10.3/§20 disent « Affecter **les** responsables » (pluriel), et le modèle autorise
explicitement « un à trois » : aucune fermeture automatique d'un responsable existant.
L'exclusion GiST partielle (`office_manager`, modèle §25.2) refuse seulement un doublon exact
(même personne, même bureau, périodes qui se chevauchent) — traduite en `409
deja_responsable_de_bureau`, jamais laissée remonter brute (`ExclusionViolation` catchée en plus
de la vérification préalable, pour couvrir une course entre deux appels concurrents).

**La borne « un à trois » ne mord pas à l'écriture, et c'est mesuré, pas oublié.** `DEC-583` (LOT 6,
`T7`) pose déjà le déclencheur qui la tient sur `content_page`, à la **publication** de la page du
bureau — jamais sur `framework_responsibility_assignment` elle-même. Aucune décision, aucune
contrainte du corpus ne demande de la vérifier à l'attribution : l'inventer ici serait le §6.5.
Un témoin dédié (`test_un_QUATRIEME_responsable_de_bureau_est_ACCEPTE`) le prouve explicitement
plutôt que de le laisser deviner par un silence — un bureau peut donc, temporairement et comme
aujourd'hui, se retrouver à zéro ou à plus de trois responsables tant qu'il n'est pas publié,
exactement ce que `GET .../offices/{code}` rend déjà sans le masquer (LOT 6, `T4`).

## 2.4 Le retrait est générique au type, jamais à la ressource, et borné au périmètre de `T3`

Le §20 ne porte qu'**une** ligne « Retirer une responsabilité Framework », `ESM`/`SUPER`, pour tous
les types. Ce module ne l'expose que pour `BOOSTER` et `OFFICE_MANAGER` — le périmètre nommé de
`T3` (§1.2 de la fiche) — jamais pour `DSM`/`ESM`, qui resteraient une extension de portée non
demandée.

**Le retrait n'est proposé à l'écran que pour une affectation faite dans la session en cours.**
`GET .../framework` (`TitulaireFramework.identifiant`) rend l'identifiant de la **personne**,
jamais celui de la ligne `framework_responsibility_assignment` que `retirer_le_booster`/
`retirer_un_responsable_de_bureau` exigent pourtant. Aucune route de `T3` n'en liste pour une
ressource existante — en construire une déborderait le périmètre nommé de la sous-étape (création
et attribution, jamais une nouvelle lecture). **Même résidu, même parti que
`SectionCerclesEtBureaux`** pour la restauration d'un cercle ou d'un bureau archivé (LOT 9, `T14`) :
l'écran garde l'identifiant produit par **son propre** appel d'attribution, le temps de la session.
Un Booster ou un responsable déjà en place avant cette session ne peut donc pas être retiré par cet
écran — résidu nommé, voir §5.

## 2.5 Le motif suit la discipline de LOT 10 `T7`

Comme toute route câblée depuis `ECART-064` (`DEC-661`), le motif du §18.1 voyage toujours dans
`audit_event.reason`, jamais dans la colonne `assignment_reason` du modèle, qui reste un résidu
nommé et non écrit — `exiger_un_motif_si_necessaire` est appelée avec les rôles réellement
autorisants de chaque route, exactement comme `app.organization.routes` le fait déjà pour
l'archivage et la restauration.

## 2.6 Un défaut trouvé en écrivant l'écran, corrigé avant tout commit

`RecherchePersonne` (composant partagé des deux formulaires d'attribution) réutilisait d'abord
`collaborateur.id` — l'identifiant d'**appartenance** (`entity_membership.id`), celui qu'emploient
légitimement `FormulaireChangementDEntite`/`SectionTransfertEnMasse` pour **leur** propre besoin
(`lireLaFiche`/`changerDEntite`, qui prennent une appartenance). Les routes d'attribution de `T3`
exigent en revanche un `person_id` (`framework_responsibility_assignment.person_id`, qui référence
`person` directement). Le contrat du trombinoscope (`CollaborateurDuTrombinoscope`) expose
pourtant les **deux** champs séparément — `id` et `personneId` — et seul le second convient ici.
Non corrigé, l'écran aurait envoyé un identifiant d'appartenance à une route qui attend une
personne : `422 personne_introuvable` systématique, en silence pour l'utilisateur, jamais exercé
par aucun test si je n'avais pas vérifié le mapping exact avant d'écrire les tests. Trouvé et
corrigé avant le premier commit.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest apps/api/tests/test_creation_organisation.py apps/api/tests/test_contrat_roles_lot11.py -q` | **19/19** |
| `make test-frontend` | **contracts 478 (inchangé), ui 141 (inchangé), web 373 (+9)** — 0 échec |
| `uv run ruff check .` / `uv run ruff format --check .` | verts |
| `uv run mypy` (racine) | vert, 296 fichiers (+3) |
| `pnpm exec tsc --noEmit` (contracts, web) | vert |
| `pnpm exec eslint` (fichiers touchés) | vert |
| `pnpm exec prettier --check` (fichiers touchés) | vert |
| `make isolation-check` | **38 locales, 29 composites, 0 référence nue** — inchangé, aucune table nouvelle |
| `make sources-check` | 769 fichiers examinés, 0 fichier source ignoré |
| `make docs-check` | vert après mise à jour des registres et de `CLAUDE.md` |
| collecte depuis la racine | **2 059 pytest** (+19) |
| `uv run pytest -q` (développement) | **78 échecs environnementaux** |
| comparaison de worktree `origin/develop` (§7.22 de la passation) | sous-ensemble (`test_organisation.py`, `test_entites.py`, `test_contrat.py`) confronté explicitement, listes identiques terme à terme |

## 3.1 Zéro régression, mesurée et non supposée

`uv run pytest -q` depuis la racine rend **78 échecs, 1 981 réussis** sur **2 059 collectés** — le
même compte de 78 que `T1`/`T2`, et aucun des 78 noms ne figure dans mes fichiers nouveaux. Pour
confirmer qu'il s'agit bien de la pollution environnementale déjà documentée (le jeu de démonstration
présent sur cette machine, §9 de `CLAUDE.md`) et non d'une régression introduite par `T3`, un
`git worktree` sur `origin/develop` (avec le `.env` de développement copié, absent du worktree par
construction `.gitignore`) a rejoué `test_organisation.py`, `test_entites.py` et `test_contrat.py` :
dix échecs identiques sur les deux premiers fichiers (comptages absolus contre une base polluée),
zéro sur le troisième — cohérent avec le fait que `test_contrat.py` ne dépend d'aucune donnée de
base, seulement du schéma OpenAPI monté en mémoire.

## 3.2 Le contrat a d'abord cassé, et c'était le garde-fou qui fonctionnait

La première exécution de `test_contrat.py::test_les_chemins_du_schema_sont_exactement_ceux_du_
manifeste` après l'ajout des six routes a échoué, comme prévu : le manifeste ne les déclarait pas
encore. Corrigé en ajoutant les six entrées (§2 ci-dessus) et la grille `rolesAttributionFramework`
; `test_contrat.py` et le nouveau `test_contrat_roles_lot11.py` sont ensuite passés 5/5 et 2/2.

## 3.3 Aller-retour réel effectué (§7.43 de la passation)

Après `make code-refresh` (les trois conteneurs reconstruits), un script ad hoc (non versionné,
supprimé après usage) a exercé les six routes à travers Caddy en HTTPS, décor psql réel, deux
sessions réelles (`POST /auth/connexion` sur un compte `SUPER_ADMIN` puis sur un compte `ENTITY_
ADMIN` de l'entité, cookie et jeton CSRF lus en vrai) :

1. `POST .../circles` et `POST .../offices` (`SUPER`, motif fourni) → `201`, avec `identifiant`,
   `code`, `version` ;
2. `POST .../circles/{id}/booster` sur une personne sans Booster actif → `200`, `remplace: false` ;
3. **le même appel, même personne** → `200`, **même** `affectation`, `remplace: false` — le NO-OP ;
4. **le même appel, personne différente** → `200`, `remplace: true`, **nouvelle** `affectation` ;
   relu en base : l'ancienne ligne porte désormais `ends_at` non nul ;
5. `POST .../circles/{id}/booster/retrait` → `200` ; rejoué une seconde fois → `409
   affectation_introuvable` ;
6. `POST .../offices/{id}/responsables` deux fois, deux personnes différentes → `201` les deux
   fois, **aucun remplacement** ; relu en base : deux lignes actives simultanément ;
7. la même personne une troisième fois → `409 deja_responsable_de_bureau` ;
8. `POST .../offices/{id}/responsables/{affectation}/retrait` sur l'une des deux → `200` ; relu en
   base : une seule ligne active restante, la bonne ;
9. **la grille d'attribution éprouvée dans le sens du refus** : le compte `ENTITY_ADMIN` de
   l'entité crée un cercle avec succès (`201`, même grille que l'archivage) **puis** se voit
   refuser `POST .../booster` (`403 acces_refuse`) — la divergence d'une seule case entre les deux
   grilles, prouvée en vrai et non seulement par construction.

Décor entièrement nettoyé après coup (vérifié par un comptage final à zéro sur les tables
touchées). Un défaut trouvé dans mon propre script de vérification, pas dans le produit :
l'ordre de nettoyage supprimait `user_account` avant `auth_event`, qui le référence — corrigé en
insérant la suppression des événements d'authentification avant celle des comptes.

---

# 4. Décisions et écarts

- `DEC-678` consigne la réalisation et les choix de §2 ;
- aucun écart nouveau n'est ouvert par `T3` ;
- `ROAD-RSK`/`QO` : aucun impact, aucune question nouvelle.

---

# 5. Ce que `T3` laisse

- la création d'un cercle/bureau et l'attribution du Booster/d'un responsable de bureau, hors
  import CSV, prêtes pour `T4` (qui n'en dépend pas) et pour l'intégration des données de
  démonstration (post-`G11`), qui pourra désormais constituer l'organisation d'EXALT Bordeaux sans
  passer par un import CSV complet ;
- **le retrait du Booster/d'un responsable de bureau n'est accessible, à l'écran, que pour une
  affectation faite dans la session en cours** (§2.4) — un Booster ou un responsable déjà en place
  avant l'ouverture de l'écran ne peut être retiré QUE via un remplacement (pour le Booster) ou pas
  du tout par cet écran (pour un responsable de bureau) ; une route de lecture listant les
  affectations actives avec leur identifiant propre comblerait ce résidu, si un besoin réel apparaît
  — non construite ici, hors du périmètre nommé de `T3` ;
- aucun contrôle de pile réelle permanent (`make *-check`) n'a été construit pour ces six routes —
  la preuve de §3.3 est un script ad hoc, non versionné, supprimé après usage. Consolider ces
  contrôles dans `make framework-check` (qui couvre déjà cercles/bureaux) reste à faire, naturellement
  à `T6` (écrans résiduels et recollement) ou `T7` (recette de clôture), même séquencement que
  `make back-office-check` à `T15` du LOT 9 pour l'archivage de cercle/bureau posé à `T4`.

# Validation demandée à Jonathan

`T3` est faite : contrôles automatisés au vert, aller-retour réel effectué à travers Caddy en HTTPS
(§3.3), zéro régression. Après fusion, la prochaine sous-étape est `T4` : tâches planifiées avec
verrou, nettoyage des médias, supervision Uptime Kuma — ferme le reste du backlog officiel du lot
(`US006`/`US007`/`US008`).
