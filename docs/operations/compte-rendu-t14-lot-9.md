# Compte rendu — LOT 9, `T14`

**Sous-étape :** `T14` — écrans back-office : navigation Organisation/Onboarding/Contenu/Données/
Pilotage/Configuration/Super-administration, tableau de bord, écrans CRUD, import
**Référence :** `docs/operations/fiche-lot-9.md` ligne du découpage `T14` — « transversal, premier
et seul écran du lot »
**Décision :** `DEC-649`
**Date :** 13 octobre 2026

---

## 1. État du lot

`T1` à `T13` du LOT 9 sont faites et fusionnées. `T14` est la sous-étape **transversale** : le
seul écran du lot, qui expose tout ce que `T1` à `T13` ont construit côté API sans jamais avoir eu
de consommateur frontend.

## 2. Ce que le cahier prévoit pour ce back-office

Le cahier (§8.1, diagramme de navigation, et §10.8, « Administration ») nomme **sept groupes** :
Organisation, Onboarding, Contenu, Données, Pilotage, Configuration, Super-administration. Aucun
des deux documents ne détaille d'écran sous chaque groupe au-delà de cette énumération.

La matrice des rôles et permissions ne nomme ni ces sept groupes ni aucune notion de « navigation
du back-office » : elle raisonne par **action**, jamais par **écran**.

## 3. Le point arbitré

Après recherche, cinq des sept groupes ont un contenu réel après `T1`-`T13` (Organisation,
Onboarding — déjà construit au LOT 7, Données, Pilotage, Super-administration) ; **deux n'ont
AUCUNE route à consommer, pas seulement dans ce lot** — mesuré sur les 86 chemins du manifeste,
aucune des huit stories du LOT 9 ne nomme « Contenu » ni « Configuration ». La gestion des contenus
existe déjà, mais PAR RESSOURCE (Framework, cercle, bureau — `PanneauEditionDeContenu`, LOT 6),
jamais depuis une liste centralisée ; la configuration d'entité (matrice §19) n'a aucune route
d'écriture nulle part dans ce dépôt.

Posé à Jonathan via `AskUserQuestion`, reformulé sans jargon, **avant toute implémentation** :

> « Le cahier prévoit sept groupes de navigation dans le back-office. Mais seulement cinq ont
> vraiment quelque chose à montrer après T1-T13 du LOT 9 — Organisation, Onboarding, Données,
> Pilotage, Super-administration. "Contenu" et "Configuration" n'ont AUCUNE route API nulle part
> dans le projet — rien à afficher. Qu'est-ce que je fais de ces deux groupes dans le menu ? »

Options : (1) **Afficher en « à venir »** (recommandé) — les deux groupes apparaissent dans le
menu comme le cahier le prévoit, mais leur contenu dit explicitement que rien n'est construit ici
pour l'instant ; (2) ne pas les afficher du tout, au risque de devoir s'en souvenir plus tard.

**Réponse de Jonathan : l'option 1.**

## 4. Ce que `T14` a produit

### 4.1 Une seule page à onglets, sous la rubrique déjà réservée

`RUBRIQUES` (`apps/web/src/routes.ts`, LOT 4 `T4`) ne réserve toujours qu'**un** chemin,
`administration` : aucune route de navigation nouvelle. Les sept groupes sont SEPT ONGLETS d'une
seule page (`PageAdministration.tsx`), motif WAI-ARIA `tablist`/`tab`/`tabpanel` fabriqué à la
main — aucune primitive d'onglets n'existe dans `packages/ui` (mesuré, comme au LOT 8 `T9`), et en
bâtir une sans second écran consommateur aurait été du code non éprouvé.

Un onglet ne charge ses données que lorsqu'il devient actif : changer d'onglet démonte la section
précédente et monte la suivante, qui lance alors son propre chargement — contrairement à l'ancienne
page, sept sections chargées ensemble auraient multiplié les appels pour des sections jamais
regardées.

### 4.2 « Onboarding » et « Pilotage » : une extraction, pas une réécriture

L'ancienne page monolithique du LOT 7 `T14` (catalogue des tâches, modèles d'onboarding) devient
l'onglet « Onboarding » **sans aucune règle changée** : extraction pure dans
`administration/SectionOnboarding.tsx`, ses tests repris à l'identique (seule la source des props
— `code`/`roles` au lieu de `useEntiteConsultee` — a changé). Le suivi des tâches en retard
(LOT 7 `T12`) rejoint « Pilotage », son groupe propre au cahier (« rapports »), aux côtés du
**nouveau** tableau de bord (`T5`) — même emplacement conceptuel, règles inchangées.

### 4.3 Quatre sections nouvelles, consommant des routes posées sans écran depuis `T2`-`T12`

| Onglet | Fichier | Consomme |
|---|---|---|
| Organisation | `administration/SectionOrganisation.tsx` | création d'un collaborateur (`T2`), changement d'entité (`T3`), transfert en masse avec aperçu (`T11`), archivage/restauration d'un cercle ou d'un bureau (`T4`) |
| Données | `administration/SectionDonnees.tsx` | dépôt multipart, rapprochement des clients, décisions, lancement, rapport paginé, rejeu d'une ligne (`T6`-`T10`) |
| Pilotage | `administration/SectionPilotage.tsx` | tableau de bord administratif (`T5`) + suivi (déplacé) |
| Super-administration | `administration/SectionSuperAdministration.tsx` | création d'une entité (`T12`), `SUPER` seul |

### 4.4 Une route nouvelle, trouvée en construisant l'écran

`apps/web/src/api/trombinoscope.ts` le nommait déjà en tête de fichier depuis le LOT 5 : « les
métiers, clients et DSM arriveront avec le back-office du LOT 9 ». `job_catalog_id` est un champ
obligatoire de la création d'un collaborateur et du changement d'entité depuis l'ouverture du
lot, et **aucune route ne servait la liste des métiers d'une entité** — mesuré sur les 85 chemins
du manifeste avant `T14`.

`GET /entities/{code}/job-catalog` (`app/people/catalogues.py`, `lister_le_catalogue_des_metiers`)
sert les métiers ACTIFS et non archivés d'une entité — même motif exact que `GET .../templates`,
posée par `T14` du LOT 7 en construisant son propre écran. Gardée par une simple session établie
(aucun rôle n'est distingué, même régime que le Framework) ; confrontée à l'OpenAPI servi par le
test générique `test_contrat.py`, et ses propres tests de permission/isolement dans
`test_catalogue_des_metiers.py`.

`cercle_principal` et `dsm` sont résolus depuis `GET .../framework` (cercles et titulaires de la
responsabilité `DSM`, déjà exposés) ; `client` depuis `GET .../clients` (`T8`). **Aucun des quatre
champs organisationnels n'est un identifiant saisi à la main**, sauf deux résidus nommés
ci-dessous (§4.6).

### 4.5 Cinq nouvelles grilles de rôles, confrontées au manifeste

`T2` à `T11` avaient posé leurs grilles de rôles Python sans qu'aucun écran n'en ait besoin. `T14`
les ajoute au manifeste (`contrat-api.json`) et les confronte, dans les deux sens, par un nouveau
fichier de test (`apps/api/tests/test_contrat_roles_lot9.py`) :

| Clé du manifeste | Constante Python | Rôles |
|---|---|---|
| `rolesEcriture` | `ROLES_D_ECRITURE` | DSM, ESM, BOOST, ADM-E, SUPER |
| `rolesCycleDeVieFramework` | `ROLES_DE_CYCLE_DE_VIE_FRAMEWORK` | ESM, ADM-E, SUPER |
| `rolesTableauDeBord` | `ROLES_DU_TABLEAU_DE_BORD` | DSM, ESM, BOOST, ADM-E, SUPER |
| `rolesDepotDeLImport` | `ROLES_DE_DEPOT_DE_L_IMPORT` | ESM, ADM-E, SUPER |
| `rolesValidationDesRapprochements` | `ROLES_DE_VALIDATION_DES_RAPPROCHEMENTS` | DSM, ESM, ADM-E, SUPER |

La création d'entité reste gardée par `SUPER` seul (`_exiger_le_super_administrateur`) — un
littéral unique, jamais une grille de plus au manifeste.

### 4.6 Deux résidus nommés, pas inventés

- **`premier_administrateur`** (Super-administration) et les cibles `target_person_id` des
  décisions « personne » (Données, `person_merge`/`profile_reactivation`) restent des
  identifiants saisis à la main : aucune route ne liste les personnes toutes entités confondues,
  le trombinoscope étant borné à une entité.
- **L'archivage d'un cercle ou d'un bureau n'a aucune liste à parcourir pour la restauration** :
  `GET .../framework` exclut les ressources archivées et aucune route n'en liste — mesuré, `T4`
  n'a posé que les quatre transitions. L'écran garde donc l'identifiant et la version **en
  mémoire le temps de la session**, juste après un archivage réussi ; un geste plus loin dans le
  temps reste hors de portée de cet écran.

Ni l'un ni l'autre n'appelait une nouvelle route API au-delà de ce que `T14` a déjà posé (§4.4) :
inventer une route de recherche de personnes ou de liste d'archives aurait dépassé le périmètre
du lot sans qu'aucune story ne le demande.

### 4.7 Ce que `T14` ne fait jamais

Aucune migration. Aucune règle métier changée dans `app/`, hors l'unique route de lecture
(§4.4). `ECART-064` (motif d'intervention du super-administrateur) et `audit_event` restent au
LOT 10, jamais anticipés.

## 5. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q --collect-only` | **1 707 collectés** (+8 : 5 unitaires de confrontation des grilles, 3 d'intégration pour le catalogue des métiers) |
| `uv run pytest -m integration -q --collect-only` | **1 281** (+3) |
| `uv run pytest` (suite complète, racine), deux exécutions successives | **74 échecs environnementaux** les deux fois — la première exécution en comptait 79, cinq non déterministes (`test_debit.py`, `test_catalogue_des_taches.py`), absents en isolation et absents à la deuxième exécution complète |
| Comparaison croisée avec `origin/develop`, même environnement (stash/pop, même base) | strictement les mêmes **74** échecs |
| `uv run mypy` (racine, strict) | 0 erreur, 239 fichiers (+1, `app/people/catalogues.py`) |
| `uv run ruff check` / `ruff format --check` | 0 erreur, tout formaté |
| `pnpm run test` (Vitest, trois paquets) | **802 passés** (380 `contracts` inchangé, 120 `ui` inchangé, **302 `web`**, +8) |
| `pnpm run lint` / `pnpm run format:check` / `pnpm run typecheck` | 0 erreur dans les trois |
| `make isolation-check` | **35 tables locales, 29 clés composites** — inchangé |
| `make migrations-check` | tête de chaîne inchangée, **aucune migration** |
| `make sources-check` | 648 fichiers examinés, 0 ignoré hors les 2 exceptions déclarées |
| `make docs-check` | **12/12 contrôles verts** |
| `test_contrat.py` | vert — le nouvel endpoint confronté à l'OpenAPI réellement servi |

Vérification manuelle de pile : code rafraîchi sur les conteneurs de développement
(`make code-refresh`), une personne `SUPER` et une session réelle créées pour un essai dans le
navigateur. L'acheminement de l'e-mail de lien magique vers Mailpit n'a pas pu être observé dans
le temps imparti sur cette machine — non bloquant : la vérification complète de la pile réelle
(parcours des sept groupes, asymétrie de rôles, isolation multi-entités) est le rôle **explicite**
de `T15` (`make back-office-check`, pattern `T13`/`T14` des LOTS 7/8), pas de `T14`. Les fixtures
de test créées pour cet essai ont été nettoyées de la base de développement.

## 6. Décisions et écarts

- `DEC-649` enregistrée au registre des décisions.
- Aucun écart ouvert ni fermé par cette sous-étape.
- Aucune question nouvelle ouverte au registre : les deux résidus (§4.6) sont documentés en
  commentaire de code et dans ce compte rendu, pas au registre des questions — ce sont des notes
  d'implémentation, pas des décisions métier en attente.

## 7. Ce que `T14` laisse

- Les sept groupes du cahier sont dans le menu ; cinq avec un contenu réel, deux marqués
  « à venir ».
- Aucune issue GitHub propre à cette sous-étape transversale (elle ne clôt aucune story à elle
  seule — `US002`, `US003`, `US004`, `US006`, `US007` étaient déjà refermées par `T3`, `T11`,
  `T7`, `T10`, `T12`).
- Prochaine sous-étape : `T15` — le contrôle de pile réelle.

## Validation demandée

Pull request à fusionner vers `develop`.

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
