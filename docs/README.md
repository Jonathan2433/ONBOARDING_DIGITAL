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
| `decisions/` | Registre des décisions, registre des écarts | Jonathan |
| `operations/` | Conventions Git et versions, traçabilité GitHub, registres des risques, des questions ouvertes et des dépendances externes, politique de configuration et de secrets, contrôles de sortie | Jonathan |
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

| Séquence | Objet | Étendue constatée | Prochain identifiant libre |
|---|---|---|---|
| `DEC-nnn` | Décisions de projet | `DEC-001` à `DEC-417` réservés (voir ci-dessous) ; `DEC-418+` en usage | suivant le registre |
| `RIGHTS-nnn` | Décisions de droits | `RIGHTS-001` à `RIGHTS-025` | `RIGHTS-026` |
| `DATA-nnn` | Décisions de modèle | `DATA-001` à `DATA-018` | `DATA-019` |
| `ROAD-nnn` | Décisions de roadmap | `ROAD-001` à `ROAD-012` | `ROAD-013` |
| `BACKLOG-nnn` | Décisions de backlog | `BACKLOG-001` à `BACKLOG-010` | `BACKLOG-011` |
| `ARB-DROIT / ARB-DATA / ARB-ROAD / ARB-BACK-nnn` | Arbitrages | `-001` à `-005` chacun | `-006` |
| `QO-nnn` | Questions ouvertes | `QO-072` à `QO-105` | `QO-106` |
| `ROAD-RSK-nnn` | Risques | `ROAD-RSK-001` à `ROAD-RSK-012` | `ROAD-RSK-013` |
| `ECART-nnn` | Écarts entre l'existant et les documents | séquence créée par le projet | suivant le registre |
| `DEP-nnn` | Dépendances externes | séquence créée par le projet | suivant le registre |
| `MVP-Lnn-USnnn` | User stories | `MVP-L00-US001` à `MVP-L14-US007` | — |
| `Gn` | Portes de validation | `G0` à `G14` | — |

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
| `G0` | Fin du référentiel | Jonathan confirme les documents et conventions | **En cours** |
| `G1` | Fin du socle local | Stack, CI et images validées | Planifiée |
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

## 7. Avancement du LOT 0

| Sous-étape | Objet | Story | État |
|---|---|---|---|
| S1 | Dépôt, arborescence documentaire, barrières de sécurité | `MVP-L00-US001` | **Validée** par Jonathan le 27 juillet 2026 |
| S2 | Versionnement des documents validés | `MVP-L00-US002` | En cours |
| S3 | Conventions Git, versions et contribution | `MVP-L00-US003` | À faire |
| S4 | Registres décisions, risques, questions, dépendances, écarts | `MVP-L00-US006` | À faire |
| S5 | Modèles de configuration sans secrets | `MVP-L00-US007` | À faire |
| S6 | Schéma initial du CSV collaborateurs | `MVP-L00-US004` | À faire |
| S7 | Inventaire des contenus du prototype | `MVP-L00-US005` (`P1`) | À faire |
| S8 | Contrôles de sortie et préparation de la porte `G0` | — | À faire |
