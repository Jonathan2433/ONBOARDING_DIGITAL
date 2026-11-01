# Compte rendu — `T5` du LOT 11 : le métier devient optionnel

**Sous-étape :** `T5` — suppression du caractère obligatoire de `job_catalog`/
`membership_job_assignment`, rendu optionnel partout
**Déviation tracée :** `DEC-675` (validée le 30/10/2026, exécutée ici)
**Décision :** `DEC-680`
**Date :** 1 novembre 2026

---

# 1. État du lot

Le LOT 11 est ouvert depuis le 30/10/2026 (`DEC-674`), découpage en sept sous-étapes. `T1`
(`DEC-676`), `T2` (`DEC-677`), `T3` (`DEC-678`) et `T4` (`DEC-679`) sont faites et fusionnées — les
huit stories officielles du backlog sont closes depuis `T4`. `T5` exécute une déviation déjà
tracée au moment de l'ouverture du lot (`DEC-675`, §1.3 de `fiche-lot-11.md`) : Jonathan a demandé,
le 30/10/2026, « nous ne voulons plus gérer ce champ » — le métier reste décrit par le modèle de
données comme faisant partie du socle « personnes » (§6.3-6.4), mais devient facultatif partout où
il est aujourd'hui obligatoire dans l'application. **Rien n'est supprimé** : aucune table, aucune
colonne, aucune ligne existante.

---

# 2. Ce que la sous-étape a produit

| Fichier | Rôle |
|---|---|
| `apps/api/app/people/ecriture.py` | `_ecrire_le_metier` : ajoute le chemin « clore sans rouvrir » quand la demande porte `metier: null` |
| `apps/api/app/people/routes.py` | `metier` devient `uuid.UUID \| None` sur les trois schémas d'écriture ; `metier` rejoint `client` dans `CHAMPS_SANS_NUL` exclu |
| `packages/contracts/src/collaborateurs.ts` | les trois formes d'écriture passent de `metier: string` requis à `metier?: string \| null` |
| `apps/web/.../SectionOrganisation.tsx` | `champsCompletes` ne bloque plus l'envoi sur l'absence de métier ; le `<select>` devient « Métier (facultatif) », option vide renommée « — aucun — » |
| `apps/api/app/imports/organisation.py` | `E-METIER-001` (`CODE_METIER_ABSENT`) retiré : un profil actif sans métier n'est plus rejeté à l'import |
| `apps/api/app/administration/tableau_de_bord.py` | le métier sort des relations comptées par « profil incomplet » |
| `apps/api/app/reporting/lecture.py` | miroir exact du tableau de bord pour le détail des profils incomplets |
| `apps/api/app/reporting/routes.py` | `ProfilIncompletRendu` perd le champ `metier_manquant` |
| `packages/contracts/src/reporting.ts` | miroir TypeScript du retrait |
| `docs/architecture/donnees/codes-erreurs-import.md` | `E-METIER-001` marqué RETIRÉ, jamais réutilisé (§7 du document) |
| `apps/api/tests/test_ecriture_organisationnelle.py`, `test_creation_collaborateurs.py`, `test_transfert_collaborateurs.py`, `test_import_transactionnel.py`, `test_tableau_de_bord.py`, `test_reporting.py` | sept tests nouveaux, un test existant corrigé |

**Aucune migration, aucune table, aucune colonne, aucune ligne supprimée** — conforme à `DEC-675`.

## 2.1 Le mécanisme : « pas de ligne » représente « pas de métier », pas une colonne nullable

Mesuré avant tout code (§6.5 de `CLAUDE.md`) : `membership_job_assignment.job_catalog_id` est
`NOT NULL` en base, et c'est une table HISTORISÉE (mixin période, `starts_at`/`ends_at`) — exactement
comme `dsm_assignment`/`circle_membership`, qui n'ont jamais eu de métier obligatoire et dont
« pas de ligne ouverte » signifie déjà « pas d'affectation ». Rendre `job_catalog_id` nullable
aurait été une seconde façon d'exprimer la même absence, en contradiction avec le patron déjà
établi par ces deux tables sœurs. **Aucune migration n'était donc nécessaire** : le service devait
seulement apprendre à fermer une affectation sans en ouvrir une nouvelle quand la valeur demandée
est `null`.

`app.people.creation` (`creer_l_appartenance`) était déjà dans cet état depuis le LOT 9 `T9` — un
`job_catalog_id` absent n'écrit simplement pas la ligne. Le seul point réellement obligatoire était
`app.people.ecriture._ecrire_le_metier` (`PATCH .../donnees-organisationnelles`), qui fermait
l'affectation courante mais **insérait toujours** une nouvelle ligne avec la valeur demandée —
`None` aurait violé le `NOT NULL` et échoué bruyamment. Le correctif ajoute un retour anticipé après
la fermeture, symétrique à ce qui existe déjà implicitement pour `client` (seul champ déjà nullable
en base).

## 2.2 Trois couches touchées, dans cet ordre : service, routes/contrat, écran

1. **Service** (`app.people.ecriture`) — voir §2.1.
2. **Routes et contrat** : `DemandeDeCreationDeCollaborateur.metier`, `DemandeDeChangementDEntite.
   metier` et `ElementDeTransfertEnMasseRequete.metier` passaient de `uuid.UUID` requis à
   `uuid.UUID | None` facultatif — ces trois schémas appellent déjà des services (`creer_l_
   appartenance`/`changer_d_entite`) qui géraient `None` depuis le LOT 9, seul le verrou Pydantic en
   amont empêchait de leur envoyer `null`. `CHAMPS_SANS_NUL` (le garde-fou qui refuse un `null`
   explicite sur une colonne `NOT NULL`, dérivé d'une mesure directe d'`information_schema` depuis
   `T7` du LOT 5) perd `METIER` au profit de la même exception que `CLIENT`.
3. **Écran** : `SectionOrganisation.tsx` — le `<select>` « Métier » ne portait déjà aucun attribut
   HTML `required` ; seule la fonction `champsCompletes`, qui désactive le bouton d'envoi des trois
   formulaires (création, transfert unitaire, transfert en masse), le rendait obligatoire côté
   interface. La retirer suffit ; l'option vide devient « — aucun — », la même convention déjà
   employée par le champ DSM (facultatif depuis le LOT 9).

## 2.3 Deux arbitrages explicites de Jonathan (`AskUserQuestion`, 01/11/2026)

Ni la fiche ni `DEC-675` ne précisaient si « optionnel partout » couvrait aussi l'import CSV et le
critère de complétude du tableau de bord — deux endroits mesurés comme réellement obligatoires
aujourd'hui, mais hors du périmètre littéral de « la création et la modification d'un
collaborateur » cité par la décision. Reposé avant tout code plutôt que deviné (§6.5) :

- **Import CSV** : `E-METIER-001` rejetait une ligne de profil actif sans `F11`. Jonathan a confirmé
  le retrait, cohérent avec « nous ne voulons plus gérer ce champ » appliqué à toute l'application —
  un profil actif s'importe désormais sans métier, exactement comme à la création manuelle. Le code
  est marqué RETIRÉ au référentiel (`codes-erreurs-import.md` §7 : « un code stable ne change jamais
  de signification […] l'ancien est marqué obsolète, jamais réutilisé »), jamais réutilisé pour une
  autre règle. Une valeur de métier INCONNUE du catalogue reste, elle, une décision humaine
  (`D-METIER-001`, inchangé) : seule l'ABSENCE cesse d'être bloquante.
- **Profil incomplet** (tableau de bord administratif et son détail en reporting) : Jonathan a
  confirmé le retrait du métier des relations comptées — un profil sans métier ne sera plus listé
  « incomplet » pour cette seule raison. Les deux implémentations de la même règle
  (`app.administration.tableau_de_bord._COMPTER_PROFILS_INCOMPLETS` et `app.reporting.lecture.
  ProfilIncomplet`, déjà documentées comme non-duplicables l'une de l'autre, §7.27) sont corrigées en
  miroir, et `metier_manquant` est retiré de la forme rendue par l'API et par le contrat TypeScript.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check`/`format` | 0 défaut, dépôt entier |
| `uv run mypy` | 0 erreur, 305 fichiers |
| `pnpm run typecheck` | 0 erreur, `contracts`/`ui`/`web` |
| `pnpm run lint` | 0 défaut |
| `pnpm exec prettier --check` | conforme |
| `make isolation-check` | 57 tables (38 locales, 19 globales), 29 composites inchangé, 0 référence nue |
| `make migrations-check` | base vide → `0029` → schéma identique (912 colonnes, 333 contraintes, 269 index, 10 déclencheurs, 199 fonctions) — aucune migration nouvelle |
| `make sources-check` | aucun fichier source ignoré |
| `uv run pytest` (racine) | 2 092 collectés (+7), 78 échecs environnementaux identiques à `origin/develop` |
| Vitest (`contracts`/`ui`/`web`) | 992 au total, inchangé — 478/141/373 |
| Aller-retour réel sur la pile | voir §3.2 |

## 3.1 Zéro régression, mesurée par comparaison de worktree

Un `git worktree` sur `origin/develop`, pointant la MÊME base de développement (même `.env`
copié), a rendu exactement **78 échecs** — comparés terme à terme à la branche (`comm -23`/
`comm -13` dans les deux sens) : liste strictement identique, aucune différence. Les 78 échecs
restent les mêmes défauts environnementaux documentés depuis plusieurs lots (jeu de démonstration
chargé sur cette machine, assertions en compte absolu).

## 3.2 Aller-retour réel effectué sur la pile réelle, API et navigateur

Après `make code-refresh`, deux preuves indépendantes, chacune avec son propre décor jetable nettoyé
ensuite :

**1. Script HTTP direct**, à travers Caddy en HTTPS, une session ESM réelle (compte `ADMIN_LOCAL`,
mot de passe), protection CSRF réelle (en-tête `Origin` + jeton double-soumission dérivé de la
session) :

- `POST .../people` **sans** `metier` → `201`, **zéro** ligne `membership_job_assignment` posée ;
- `POST .../people` **avec** `metier` → `201` (témoin positif, §7.39 : le chemin existant n'a pas
  régressé), **une** ligne posée ;
- `PATCH .../people/{appartenance}` avec `metier: null` sur une affectation existante → `200`
  (jamais `500`), l'affectation est CLOSE, aucune ligne n'est rouverte.

**2. Navigateur réel**, session ESM par mot de passe, écran « Administration » → « Organisation » →
« Créer un collaborateur » : le champ affiche bien « Métier (facultatif) » avec « — aucun — »
sélectionné par défaut ; le formulaire rempli (e-mail, prénom, nom, date d'arrivée, statut
intercontrat, cercle principal) **sans toucher au métier** a produit le message « Collaborateur créé
(appartenance …) » — confirmé en base : zéro ligne `membership_job_assignment` pour cette
appartenance.

Décor nettoyé dans les deux cas (entité, personnes, comptes, sessions, affectations).

---

# 4. Décisions et écarts

**`DEC-680`** enregistre cette sous-étape, exécutant la déviation déjà tracée par `DEC-675`. Deux
arbitrages explicites de Jonathan (import CSV, critère de profil incomplet) sont tracés au §2.3
ci-dessus et dans le registre.

Aucun écart nouveau. Les deux points nommés par `DEC-675`/`fiche-lot-11.md` comme hors de la portée
de cette déviation restent inchangés : aucune extension de schéma pour un rôle Framework de portée
groupe, aucune représentation structurelle de la hiérarchie DG > DSM Coach > DSM.

---

# 5. Ce que `T5` laisse

- **`cercle_principal` reste obligatoire partout** : la déviation `DEC-675` ne vise que le métier,
  jamais nommé pour le cercle — aucune confusion possible, les deux champs vivent côte à côte dans
  les mêmes formulaires et seul le premier a changé.
- **L'intégration des données de démonstration** (entité EXALT Bordeaux, 125 personnes) reste hors
  du découpage de ce lot (§2 de `fiche-lot-11.md`) — elle consommera directement un métier
  facultatif quand elle sera menée, action distincte postérieure à `G11`.
- **`T6`** (écrans consommateurs résiduels et recollement) est la sous-étape suivante. Les écrans de
  `T2` et `T3` étant déjà complets et reliés à la navigation, `T6` pourrait se révéler vide — constat
  à faire et annoncer avant d'être exécuté, jamais décidé a priori (§3 de `fiche-lot-11.md`).

---

# Validation demandée à Jonathan

`T5` du LOT 11 est techniquement complète : le métier est désormais facultatif dans la création, la
modification, le transfert (unitaire et en masse) d'un collaborateur, dans l'import CSV, et n'entre
plus dans le critère de « profil incomplet » — sur arbitrage explicite pour ces deux derniers points.
Zéro régression mesurée, aller-retour réel effectué à la fois par script HTTP et dans un navigateur
réel. Pull request à ouvrir, numéro à venir.
