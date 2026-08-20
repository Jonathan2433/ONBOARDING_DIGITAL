# Référentiel documentaire — eXalt Onboarding Digital

Ce dossier est la source de vérité du projet. Aucune décision de conception ne doit être
prise en dehors de ce qui y est écrit.

---

## 1. Documents de cadrage validés

| Document | Emplacement | Version | Statut | Date de validation |
|---|---|---|---|---|
| Cahier des charges consolidé | [`product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md`](product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md) | 1.0 | **Validé** par Jonathan — décision `DEC-423` | 27 juillet 2026 |
| Matrice des rôles et permissions | [`product/MATRICE_ROLES_PERMISSIONS_EXALT.md`](product/MATRICE_ROLES_PERMISSIONS_EXALT.md) | 1.1 | **Validé** par Jonathan | 25 juillet 2026 |
| Modèle de données et diagrammes | [`architecture/MODELE_DONNEES_EXALT.md`](architecture/MODELE_DONNEES_EXALT.md) | 1.0 | **Validé** par Jonathan | 25 juillet 2026 |
| Roadmap MVP, V1 et V2 | [`product/ROADMAP_MVP_V1_V2_EXALT.md`](product/ROADMAP_MVP_V1_V2_EXALT.md) | 1.0 | **Validé** par Jonathan | 25 juillet 2026 |
| Backlog initial priorisé | [`product/BACKLOG_INITIAL_PRIORISE_EXALT.md`](product/BACKLOG_INITIAL_PRIORISE_EXALT.md) | 1.0 | **Validé** par Jonathan | 25 juillet 2026 |

Ces cinq fichiers sont **immuables** en l'état. Leur intégrité est prouvée par empreinte
SHA-256 et la conformité des annexes du cahier des charges est vérifiée :
voir [`operations/integrite-et-conformite-documents.md`](operations/integrite-et-conformite-documents.md).

Le cahier des charges intègre les quatre autres documents en annexes contractuelles A à D.
Le contrôle de conformité établit qu'il n'existe **aucune divergence de contenu** entre les
annexes et les documents spécialisés.

### Statut du cahier des charges

Le fichier porte en en-tête la mention « soumis à validation finale de Jonathan », qui
correspond à son état du 25 juillet 2026. Jonathan l'a validé le 27 juillet 2026. Par
décision `DEC-423`, cette validation est enregistrée au registre des décisions **sans
modifier le fichier** : valider n'est pas une évolution de contenu, la procédure du cahier
des charges section 35 n'exige donc pas de changement de version, et l'immuabilité du
fichier préserve la preuve d'intégrité par empreinte. Le statut faisant foi est celui du
présent index et du registre des décisions.

---

## 2. Organisation des dossiers

| Dossier | Contenu | Responsable principal |
|---|---|---|
| [`product/`](product/README.md) | Cahier des charges, matrice des droits, roadmap, backlog, contenus éditoriaux | Léa (produit), Tess et Diane (contenus) |
| [`architecture/`](architecture/README.md) | Modèle de données, schéma du CSV collaborateurs, listes contrôlées, décisions d'architecture | Jonathan |
| [`decisions/`](decisions/README.md) | Registre des décisions, registre des écarts | Jonathan |
| `operations/` | Conventions Git et versions, traçabilité GitHub, registres des risques, des questions ouvertes et des dépendances externes, responsabilités, politique de configuration et de secrets, contrôles de sortie, fiches de lot | Jonathan |
| [`prototype/`](prototype/README.md) | Prototype historique, conservé pour historisation, non versionné, non réutilisable | — |

---

## 3. Règle de préséance

En cas de contradiction entre deux sources :

1. le cahier des charges consolidé prévaut ;
2. une décision validée plus récente prévaut sur une décision plus ancienne ;
3. les annexes validées précisent les règles détaillées ;
4. aucune hypothèse ne remplace une décision explicite de Jonathan.

Procédure d'évolution, cahier des charges section 35 :

1. une décision explicite est enregistrée ;
2. le document spécialisé concerné change de version ;
3. l'impact sur le modèle, la roadmap, le backlog et les tests est évalué ;
4. le cahier des charges est mis à jour ;
5. le contrôle de conformité des annexes est rejoué.

---

## 4. Séquences d'identifiants

Les identifiants ne sont **jamais** réutilisés. Toute nouvelle entrée poursuit la séquence
existante.

| Séquence | Objet | Étendue | Prochain libre | Registre |
|---|---|---|---|---|
| `DEC-nnn` | Décisions de projet | `001` à `417` **réservés** ; `418` à `515` en usage | `DEC-516` | [décisions](decisions/registre-decisions.md) |
| `RIGHTS-nnn` | Décisions de droits | `001` à `025` | `RIGHTS-026` | [décisions](decisions/registre-decisions.md) |
| `DATA-nnn` | Décisions de modèle | `001` à `018` | `DATA-019` | [décisions](decisions/registre-decisions.md) |
| `ROAD-nnn` | Décisions de roadmap | `001` à `012` | `ROAD-013` | [décisions](decisions/registre-decisions.md) |
| `BACKLOG-nnn` | Décisions de backlog | `001` à `010` | `BACKLOG-011` | [décisions](decisions/registre-decisions.md) |
| `ARB-DROIT / ARB-DATA / ARB-ROAD / ARB-BACK-nnn` | Arbitrages | `-001` à `-005` chacun | `-006` | [décisions](decisions/registre-decisions.md) |
| `ECART-nnn` | Écarts | `001` à `032` | `ECART-033` | [écarts](decisions/registre-ecarts.md) |
| `QO-nnn` | Questions ouvertes | `072` à `105` avec **5 trous**, puis `106` à `117` | `QO-118` | [questions](operations/registre-questions-ouvertes.md) |
| `ROAD-RSK-nnn` | Risques | `001` à `034` | `ROAD-RSK-035` | [risques](operations/registre-risques.md) |
| `DEP-nnn` | Dépendances externes | `001` à `017` | `DEP-018` | [dépendances](operations/registre-dependances-externes.md) |
| `CONT-nnn` | Contenus éditoriaux inventoriés | `001` à `029` | `CONT-030` | [inventaire](product/contenus/inventaire-prototype.md) |
| `MVP-Lnn-USnnn` | User stories | `MVP-L00-US001` à `MVP-L14-US007` | — | backlog validé |
| `Gn` | Portes de validation | `G0` à `G14` | — | roadmap validée |

Trous conservés et jamais comblés : `QO-075`, `QO-079`, `QO-080`, `QO-082`, `QO-090`
(`ECART-011`). Les règles de tenue figurent dans
[`decisions/README.md`](decisions/README.md).

### Traitement de la référence `DEC-001` à `DEC-417`

Les cinq documents référencent des décisions `DEC-001` à `DEC-417` issues des ateliers de
cadrage, mais la table correspondante n'est présente dans aucun document du corpus
(écart `ECART-004`).

Décision `DEC-422` : les **85 décisions et arbitrages consolidés** — `RIGHTS-*`, `DATA-*`,
`ROAD-*`, `BACKLOG-*` et `ARB-*` — font foi comme registre décisionnel du projet. La
référence `DEC-001` à `DEC-417` est conservée comme référence historique aux ateliers, et la
plage est **réservée** afin qu'un import ultérieur ne produise aucun conflit d'identifiant.
Les nouvelles décisions du projet démarrent à `DEC-418`.

Les registres sont créés en sous-étape **S4** du LOT 0.

---

## 5. Conventions de nommage

Décision retenue le 27 juillet 2026 :

- les **cinq documents validés** conservent leur nom d'origine en majuscules, afin de
  préserver la traçabilité avec le prompt de cadrage et les références croisées internes ;
- les **documents produits par le projet** utilisent le kebab-case minuscule, par exemple
  `registre-decisions.md`, `schema-csv-collaborateurs.md`.

Le système de fichiers de la machine de développement est **insensible à la casse** : tout
renommage ne différant que par la casse exige une manœuvre en deux temps.

---

## 6. Portes de validation

| Porte | Moment | Validation obligatoire | État |
|---|---|---|---|
| `G0` | Fin du référentiel | Jonathan confirme les documents et conventions | **Validée** le 27/07/2026 |
| `G1` | Fin du socle local | Stack, CI et images validées | **FRANCHIE** le 12/08/2026 — tag `v0.1.0` posé sur `main` |
| `G2` | Fin du modèle implémenté | Contraintes et isolation validées | **Porte courante** — LOT 2 ouvert le 18/08/2026 (`DEC-496`), tag `v0.2.0` |
| `G3` | Fin de l'authentification | Sécurité et sessions validées | Planifiée |
| `G4` | Fin du portail national | Navigation et lecture inter-entités validées | Planifiée |
| `G5` | Fin du trombinoscope | Profils et permissions validés | Planifiée |
| `G6` | Fin du Framework | Contenus et périmètres éditoriaux validés | Planifiée |
| `G7` | Fin de l'onboarding | Tess, Léa, Diane et Jonathan valident les parcours | Planifiée |
| `G8` | Fin de l'accueil | Événements et page d'accueil validés | Planifiée |
| `G9` | Fin du back-office | Import réel répété et validé | Planifiée |
| `G10` | Fin du pilotage | Audit, reporting et support validés | Planifiée |
| `G11` | Fin des traitements | Médias, worker et planification validés | Planifiée |
| `G12` | Fin de recette | Aucun défaut bloquant selon les règles convenues | Planifiée |
| `G13` | Production temporaire | Déploiement, sauvegarde et restauration validés | Planifiée |
| `G14` | Production générale | Léa valide le produit, Jonathan la technique | Planifiée |

Aucun lot dépendant ne commence avant validation explicite du lot précédent
(décision `ROAD-003`, arbitrage `ARB-BACK-003`).

---

## 7. Avancement du LOT 0 — **lot terminé et verrouillé**

| Sous-étape | Objet | Story | État |
|---|---|---|---|
| S1 | Dépôt, arborescence documentaire, barrières de sécurité | `MVP-L00-US001` | **Validée** par Jonathan le 27 juillet 2026 |
| S2 | Versionnement des documents validés | `MVP-L00-US002` | **Validée** par Jonathan le 27 juillet 2026 |
| S3 | Conventions Git, versions et contribution | `MVP-L00-US003` | **Validée** par Jonathan le 27 juillet 2026 |
| S4 | Registres décisions, risques, questions, dépendances, écarts | `MVP-L00-US006` | **Validée** par Jonathan le 27 juillet 2026 |
| S5 | Modèles de configuration sans secrets | `MVP-L00-US007` | **Validée** par Jonathan le 27 juillet 2026 |
| S6 | Schéma initial du CSV collaborateurs | `MVP-L00-US004` | **Validée** par Jonathan le 27 juillet 2026 |
| S7 | Inventaire des contenus du prototype | `MVP-L00-US005` (`P1`) | **Validée** par Jonathan le 27 juillet 2026, statut `à relire` (`DEC-437`) |
| S8 | Contrôles de sortie et préparation de la porte `G0` | — | **Validée**. Porte `G0` franchie le 27 juillet 2026 (`DEC-438`) |

---

## 8. Avancement du LOT 1 — **terminé**, porte `G1` **franchie**

Ouvert par Jonathan le 27 juillet 2026 (`DEC-450`), **verrouillé le 12 août 2026**. Plan :
[`operations/fiche-lot-1.md`](operations/fiche-lot-1.md). Arbitrages préalables :
[`operations/compte-rendu-t0-lot-1.md`](operations/compte-rendu-t0-lot-1.md).
Comptes rendus de sous-étape :
[`T1`](operations/compte-rendu-t1-lot-1.md) · [`T2`](operations/compte-rendu-t2-lot-1.md) · [`T3`](operations/compte-rendu-t3-lot-1.md) · [`T4`](operations/compte-rendu-t4-lot-1.md) · [`T5`](operations/compte-rendu-t5-lot-1.md) · [`T6`](operations/compte-rendu-t6-lot-1.md) · [`T7`](operations/compte-rendu-t7-lot-1.md) · [`T8`](operations/compte-rendu-t8-lot-1.md) · [`T9`](operations/compte-rendu-t9-lot-1.md) · [`T10`](operations/compte-rendu-t10-lot-1.md) · [`T11`](operations/compte-rendu-t11-lot-1.md).
Checklist de la porte : [`checklist-validation-G1.md`](operations/checklist-validation-G1.md).

| Sous-étape | Objet | Story | Issue | État |
|---|---|---|---|---|
| `T0` | Prérequis et arbitrages techniques | — | — | **Terminée** hors lot. 3 prérequis levés, 7 choix tranchés (`DEC-439`–`DEC-449`, dont `DEC-449` qui remplace `DEC-448`) |
| `T1` | Squelette du monorepo, outillage, versions épinglées | `MVP-L01-US001` | `#2` | **Terminée** les 27 et 28/07/2026. 7 répertoires, chaîne de qualité Python et TypeScript, versions épinglées. `DEC-451`–`DEC-457`, `ECART-017` et `ECART-018` clos, `ROAD-RSK-029` ouvert, `ROAD-RSK-026` matérialisé puis résiduel accepté |
| `T2` | Compose développement, 8 services sains | `MVP-L01-US002` | `#3` | **Terminée** le 28/07/2026. Les 8 services sains par une commande, volumes prouvés persistants. `DEC-458`–`DEC-461`, `ECART-019` clos, `ROAD-RSK-030` et `QO-111` ouverts |
| `T3` | API FastAPI, 3 healthchecks, migration initiale | `MVP-L01-US003` | `#4` | **Terminée** le 28/07/2026. 3 endpoints, 11 garde-fous testés, migration `0001` sur PostgreSQL réel, 61 tests. `DEC-462`–`DEC-465`, `ECART-006` clos, `QO-112` ouverte |
| `T4` | Journalisation JSON corrélée | `MVP-L01-US004` | `#5` | **Terminée** le 28/07/2026. Les 10 champs du cahier §28.1, 3 barrières de masquage, corrélation requête **et** job, rotation sur les 8 services. **139 tests** — corrigé de 131 au titre de `ECART-021`. `DEC-466`–`DEC-469`, `QO-113` ouverte |
| `T5` | Frontend Vite, page de statut | `MVP-L01-US002` | `#3` | **Terminée** le 28/07/2026. Page servie par Caddy, état réel des 3 dépendances éprouvé **en arrêtant Redis**, version du build, 5 états, 25 tests Vitest et Testing Library. `DEC-470`–`DEC-473`, `ECART-020` et `ECART-021` clos, `ROAD-RSK-031` ouvert, `ROAD-RSK-030` aggravé, `QO-085` mesurée |
| `T6` | CI GitHub Actions, 3 échecs volontaires prouvés | `MVP-L01-US005` | `#6` | **Terminée** le 29/07/2026. Les 11 contrôles du cahier §23.1 exécutés sur chaque pull request, pipeline vert, et **les trois échecs prouvés** — lint, test et secret, chacun bloquant la fusion. CI rendue **obligatoire** sur `develop` et `main`. `DEC-474`–`DEC-477`, `ROAD-RSK-032` et `QO-114` ouverts |
| `T7` | Images multiarchitecture, GHCR privé | `MVP-L01-US006` | `#7` | **Terminée** le 29/07/2026. Les 3 images construites pour `linux/amd64` **et** `linux/arm64` en une liste de manifestes unique, **lancées sur les deux** — 39 contrôles fonctionnels, 0 échec. Image `web` de **1,02 Gio à 84,9 Mo** par deux cibles nommées, `ROAD-RSK-030` et `ROAD-RSK-031` **clos**. Version et révision **gravées** dans les images. Trivy mesuré puis réglé. `DEC-478`–`DEC-482`, `ECART-022` clos, **`ROAD-RSK-033` ouvert** |
| `T8` | Environnement de recette isolé | `MVP-L01-US002` | `#3` | **Terminée** le 29/07/2026. Les **sept** séparations du cahier §22.2 prouvées sur l'état réel des deux environnements — **57 contrôles, 0 échec**, dont l'isolement du routage éprouvé avec ses témoins. La recette exécute les **images publiées épinglées par empreinte**, et `arm64` y est **natif** : la réserve de la fiche §3.1 est **levée**. `Makefile` paramétré par environnement, 44 → **50 cibles**, sans duplication. `DEC-483`–`DEC-488`, `ECART-023` clos, **`ROAD-RSK-034` ouvert**, **`QO-085` CLOSE** — 836,6 Mio pour deux stacks simultanées |
| `T9` | Documentation d'exploitation locale | `MVP-L01-US008` | `#9` | **Terminée** le 29/07/2026. [`exploitation-locale.md`](operations/exploitation-locale.md) créé, **toutes** ses commandes exécutées. Démarrage à froid véritable prouvé — 0 volume, 0 image, remontée en **34 s**. 14 publications et 12 volumes **dérivés**. Trois cibles jamais exercées éprouvées, dont `make destroy`, dont l'avertissement était **faux** pour la recette. `DEC-489`, `ECART-024` |
| `T10` | Design system et contrat API | `MVP-L01-US007` (`P1`) | `#8` | **Terminée** le 30/07/2026. Jetons **relevés** du prototype et **recalculés** contre WCAG 2.2 AA — la mesure a corrigé deux défauts d'accessibilité que le prototype portait. 3 composants de base, contrat partagé par manifeste unique lu par **TypeScript et Python**. **260 tests**, 11 témoins, **aucune dépendance ajoutée**. `DEC-491`–`DEC-493`, `QO-115` ouverte, **`ROAD-RSK-032` CLOS** — l'audit passe à **zéro avis, zéro tolérance** |
| `T11` | Contrôles de sortie et porte `G1` | — | — | **Terminée** le 12/08/2026. **33 contrôles rejoués, tous à 0**, tous les nombres **dérivés**. [Checklist](operations/checklist-validation-G1.md) remise à Jonathan avec une démonstration guidée. Aucune décision ajoutée. **Le tag `v0.1.0` attend la validation** |

Traçabilité GitHub en place (`DEC-449`) : 13 étiquettes, 15 milestones, epic `#1`, stories `#2`
à `#9`. **`main` et `develop` sont protégées** — toute modification passe par une pull request.

---

## 9. Avancement du LOT 2 — **lot ouvert**, porte `G2`

**Ouvert par Jonathan le 18 août 2026 (`DEC-496`).** Plan soumis à validation :
[`operations/fiche-lot-2.md`](operations/fiche-lot-2.md) — **12 sous-étapes, `T1` à `T12`**,
8 stories dont **7 en `P0`**, **16 tables** du modèle, tag `v0.2.0`.
**Découpage validé par Jonathan le 18/08/2026.** `ECART-012` est échu dans ce lot, rattaché à `T5`.

| | Sous-étape | Story | État |
|:--:|---|---|---|
| `T1` | Socle technique du modèle et extensions | `MVP-L02-US008` | **Terminée** le 18/08/2026. Collation **ICU `fr-FR`** posée avant la première table, `btree_gist` seule extension, socle déclaratif éprouvé — **20 tests**, dont le refus de chevauchement par la base et ses trois témoins. `QO-111` et `QO-112` **closes**, les **7** choix du §9.2 tranchés. `DEC-497`–`DEC-500`, `ECART-027` clos, **`QO-116` ouverte** |
| `T2` | Entités, paramètres et domaines e-mail | `MVP-L02-US001` | **Terminée** le 19/08/2026. **Les 4 premières tables du projet**, migration `0003` éprouvée en montée, descente et remontée. Règle « `code` immuable après activation » portée par **déclencheur** — 26 tests, chaque refus avec son témoin. `alembic check` sans écart. `DEC-501`, `DEC-502`, `ECART-028` clos |
| `T3` | La table `person` | `MVP-L02-US002` | **Terminée** le 19/08/2026. Identité **globale**, `ARB-DATA-001` : aucun `entity_id`. **`ECART-029` clos** — l'index du §25.1 ne satisfaisait pas l'unicité insensible à la casse du §6.1. Anonymisation **terminale** par déclencheur. **Aucune table d'authentification**, vérifié par contrôle. 19 tests. `DEC-503`, `DEC-504` |
| `T4` | `entity_membership` | `MVP-L02-US002` | **Terminée** le 19/08/2026. **La règle centrale de `US002`** : une seule appartenance occupante par personne. **Deux** contraintes complémentaires, et deux tests montrent chacun ce que l'autre ne verrait pas. Verrou optimiste câblé. **`ECART-030` clos**, **`DEC-507`** pose le nommage des exclusions. 24 tests. `DEC-505`–`DEC-507` |
| `T5` | Métiers et statuts professionnels | `MVP-L02-US003` | **Terminée** le 19/08/2026. **Clés étrangères COMPOSITES** du §25.3 : un métier d'une autre entité est refusé **par la base**. Deux index que j'avais ajoutés sont **retirés** — la mesure a montré qu'ils ne pouvaient jamais se déclencher. **`ECART-012` instruit**, il attend Léa. **`DEC-509`** pose la doctrine de nommage après deux collisions. 23 tests. `DEC-508`, `DEC-509` |
| `T6` | Clients, activations locales et alias | `MVP-L02-US003` | **Terminée** le 19/08/2026. **La dette de `T5` est acquittée** : clé étrangère de `client_id`. Normalisation **volontairement minimale** — `DATA-005` interdit tout rapprochement automatique. **`QO-117` ouverte** : le modèle ne pose aucune unicité sur les alias, et la portée est un choix métier. 21 tests, dont deux sur des **non-actions**. `DEC-510` |
| `T7` | Cercles, bureaux et appartenance aux cercles | `MVP-L02-US001`, `US003` | **Terminée** le 19/08/2026, et elle **clôt les deux stories**. **L'exclusion est PARTIELLE** — une exclusion sans `WHERE` aurait interdit les cercles secondaires multiples, et le livrable aurait **paru correct**. Un **résiduel du §8.1 est nommé, non comblé**. 17 tests. `DEC-511` |
| `T8` | DSM, responsabilités Framework et rôles techniques | `MVP-L02-US004` | **Terminée** le 19/08/2026. **Un défaut qui valait trois types sur quatre** : une clé d'exclusion contenant une colonne **nullable** ne contraint rien sur les lignes où elle est nulle. Deux **permissions** distinguées de deux interdictions voisines. **`ECART-031` ouvert** — le §8.4 exige un état de publication que `office` ne déclare pas. 19 tests. `DEC-512` |
| `T9` | Historisation et contraintes temporelles | `MVP-L02-US004` | **Terminée** le 19/08/2026. **Aucune table créée** : les 7 relations existaient. Elle pose le contrôle qui les **compte**, avec l'attendu **dérivé du §25.2** — et **il a trouvé un défaut le jour même**. **`alembic check` est AVEUGLE aux exclusions**, mesuré : 10 déclarées, 9 en base, code 0. 8 tests. `DEC-513` |
| `T10` | Contraintes de rôles et de périmètres | `MVP-L02-US005` | **Terminée** le 19/08/2026. **Deux des trois critères étaient DÉJÀ ACQUIS en `T8`** — vérifiés, non réimplémentés. **`ECART-032` ouvert** : le backlog interdit plus large que le cahier, la matrice **et** le modèle, qui restreignent tous au seul **Booster**. « DG implique DSM » appliqué comme **implication** — un déclencheur ne connaît pas l'attributeur et **inventerait une trace d'audit fausse**. Un **ombrage** de clé étrangère par un déclencheur `BEFORE` a inversé un test de `T6`. 11 tests, dont un sur une **non-action**. `DEC-514` |
| `T11` | Isolation inter-entités | `MVP-L02-US006` | **Terminée** le 20/08/2026. **Aucune migration** : les 8 clés composites du §25.3 fermaient déjà tous les chemins locaux. **Ma première mesure ne prouvait rien** — une référence sans clé étrangère aurait donné la même observation ; le contrôle examine les **colonnes**, pas les contraintes. `MATCH SIMPLE` rend une clé composite **inerte** sur une colonne nulle : `T8-1` transposé. **Dépôts cloisonnés** dont les deux types ne peuvent se confondre, et le service qui referme `DEC-514`. 34 tests, témoin en CI. `DEC-515` |
| `T12` | Voir la fiche | — | Non entamée |

---
