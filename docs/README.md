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
| `DEC-nnn` | Décisions de projet | `001` à `417` **réservés** ; `418` à `456` en usage | `DEC-457` | [décisions](decisions/registre-decisions.md) |
| `RIGHTS-nnn` | Décisions de droits | `001` à `025` | `RIGHTS-026` | [décisions](decisions/registre-decisions.md) |
| `DATA-nnn` | Décisions de modèle | `001` à `018` | `DATA-019` | [décisions](decisions/registre-decisions.md) |
| `ROAD-nnn` | Décisions de roadmap | `001` à `012` | `ROAD-013` | [décisions](decisions/registre-decisions.md) |
| `BACKLOG-nnn` | Décisions de backlog | `001` à `010` | `BACKLOG-011` | [décisions](decisions/registre-decisions.md) |
| `ARB-DROIT / ARB-DATA / ARB-ROAD / ARB-BACK-nnn` | Arbitrages | `-001` à `-005` chacun | `-006` | [décisions](decisions/registre-decisions.md) |
| `ECART-nnn` | Écarts | `001` à `018` | `ECART-019` | [écarts](decisions/registre-ecarts.md) |
| `QO-nnn` | Questions ouvertes | `072` à `105` avec **5 trous**, puis `106` à `110` | `QO-111` | [questions](operations/registre-questions-ouvertes.md) |
| `ROAD-RSK-nnn` | Risques | `001` à `029` | `ROAD-RSK-030` | [risques](operations/registre-risques.md) |
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
| `G1` | Fin du socle local | Stack, CI et images validées | **Porte courante** — LOT 1 ouvert le 27/07/2026 (`DEC-450`) |
| `G2` | Fin du modèle implémenté | Contraintes et isolation validées | Planifiée |
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

## 8. Avancement du LOT 1 — **lot ouvert**, porte `G1`

Ouvert par Jonathan le 27 juillet 2026 (`DEC-450`). Plan :
[`operations/fiche-lot-1.md`](operations/fiche-lot-1.md). Arbitrages préalables :
[`operations/compte-rendu-t0-lot-1.md`](operations/compte-rendu-t0-lot-1.md).
Comptes rendus de sous-étape :
[`T1`](operations/compte-rendu-t1-lot-1.md).

| Sous-étape | Objet | Story | Issue | État |
|---|---|---|---|---|
| `T0` | Prérequis et arbitrages techniques | — | — | **Terminée** hors lot. 3 prérequis levés, 7 choix tranchés (`DEC-439`–`DEC-449`, dont `DEC-449` qui remplace `DEC-448`) |
| `T1` | Squelette du monorepo, outillage, versions épinglées | `MVP-L01-US001` | `#2` | **Terminée** le 27/07/2026. 7 répertoires, chaîne de qualité Python et TypeScript, versions épinglées. `DEC-451`–`DEC-456`, `ECART-017` et `ECART-018` clos, `ROAD-RSK-029` ouvert |
| `T2` | Compose développement, 8 services sains | `MVP-L01-US002` | `#3` | Planifiée |
| `T3` | API FastAPI, 3 healthchecks, migration initiale | `MVP-L01-US003` | `#4` | Planifiée |
| `T4` | Journalisation JSON corrélée | `MVP-L01-US004` | `#5` | Planifiée |
| `T5` | Frontend Vite, page de statut | `MVP-L01-US002`, `US003` | `#3`, `#4` | Planifiée |
| `T6` | CI GitHub Actions, 3 échecs volontaires prouvés | `MVP-L01-US005` | `#6` | Planifiée |
| `T7` | Images multiarchitecture, GHCR privé | `MVP-L01-US006` | `#7` | Planifiée |
| `T8` | Environnement de recette isolé | `MVP-L01-US002` | `#3` | Planifiée |
| `T9` | Documentation d'exploitation locale | `MVP-L01-US008` | `#9` | Planifiée |
| `T10` | Design system et contrat API | `MVP-L01-US007` (`P1`) | `#8` | Planifiée |
| `T11` | Contrôles de sortie et porte `G1` | — | — | Planifiée |

Traçabilité GitHub en place (`DEC-449`) : 13 étiquettes, 15 milestones, epic `#1`, stories `#2`
à `#9`. **`main` et `develop` sont protégées** — toute modification passe par une pull request.
