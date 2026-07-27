# Référentiel documentaire — eXalt Onboarding Digital

Ce dossier est la source de vérité du projet. Aucune décision de conception ne doit être
prise en dehors de ce qui y est écrit.

> **État :** index provisoire créé en sous-étape **S1** du LOT 0.
> Le versionnement complet des cinq documents validés, avec version, statut, date,
> références croisées et empreintes SHA-256, est réalisé en sous-étape **S2**.
> Les cinq documents se trouvent temporairement à la racine de `docs/` et seront répartis
> dans `product/` et `architecture/` en S2.

---

## 1. Organisation des dossiers

| Dossier | Contenu | Responsable principal |
|---|---|---|
| [`product/`](product/) | Cahier des charges, matrice des rôles et permissions, roadmap, backlog, inventaire des contenus | Léa pour le produit, Tess et Diane pour les contenus |
| [`architecture/`](architecture/) | Modèle de données, schéma du CSV collaborateurs, listes contrôlées, décisions d'architecture | Jonathan |
| [`decisions/`](decisions/) | Registre des décisions, registre des écarts | Jonathan |
| [`operations/`](operations/) | Conventions Git et versions, traçabilité GitHub, registres des risques, des questions ouvertes et des dépendances externes, politique de configuration et de secrets, contrôles de sortie | Jonathan |
| [`prototype/`](prototype/) | Prototype historique, conservé pour historisation, non versionné, non réutilisable | — |

---

## 2. Documents de cadrage validés

| Document | Version | Statut | Date |
|---|---|---|---|
| `CAHIER_DES_CHARGES_EXALT_BORDEAUX.md` | 1.0 | Consolidé — validation finale à confirmer par Jonathan | 25 juillet 2026 |
| `MATRICE_ROLES_PERMISSIONS_EXALT.md` | 1.1 | Validé par Jonathan | 25 juillet 2026 |
| `MODELE_DONNEES_EXALT.md` | 1.0 | Validé par Jonathan | 25 juillet 2026 |
| `ROADMAP_MVP_V1_V2_EXALT.md` | 1.0 | Validé par Jonathan | 25 juillet 2026 |
| `BACKLOG_INITIAL_PRIORISE_EXALT.md` | 1.0 | Validé par Jonathan | 25 juillet 2026 |

Le cahier des charges intègre les quatre autres documents en annexes A à D. Un contrôle
comparatif ligne à ligne a été exécuté : les annexes sont **identiques** aux documents
spécialisés, aux seuls séparateurs de section près. Ce contrôle sera consigné comme
preuve en S2.

---

## 3. Règle de préséance

1. le cahier des charges consolidé prévaut ;
2. une décision validée plus récente prévaut sur une décision plus ancienne ;
3. les annexes validées précisent les règles détaillées ;
4. aucune hypothèse ne remplace une décision explicite de Jonathan.

Toute évolution suit la procédure du cahier des charges, section 35 :
décision explicite enregistrée, changement de version du document spécialisé, évaluation
de l'impact sur le modèle, la roadmap, le backlog et les tests, puis mise à jour du
cahier des charges.

---

## 4. Séquences d'identifiants

Les identifiants ne sont jamais réutilisés. Toute nouvelle entrée poursuit la séquence
existante.

| Séquence | Étendue constatée dans les sources | Prochain identifiant libre |
|---|---|---|
| `DEC-nnn` | `DEC-001` à `DEC-417`, référencés par les cinq documents | `DEC-418` |
| `RIGHTS-nnn` | `RIGHTS-001` à `RIGHTS-025` | `RIGHTS-026` |
| `DATA-nnn` | `DATA-001` à `DATA-018` | `DATA-019` |
| `ROAD-nnn` | `ROAD-001` à `ROAD-012` | `ROAD-013` |
| `BACKLOG-nnn` | `BACKLOG-001` à `BACKLOG-010` | `BACKLOG-011` |
| `ARB-DROIT / ARB-DATA / ARB-ROAD / ARB-BACK` | `-001` à `-005` chacun | `-006` |
| `QO-nnn` | `QO-072` à `QO-105` | `QO-106` |
| `ROAD-RSK-nnn` | `ROAD-RSK-001` à `ROAD-RSK-012` | `ROAD-RSK-013` |
| `MVP-Lnn-USnnn` | `MVP-L00-US001` à `MVP-L14-US007` | — |
| `Gn` | `G0` à `G14` | — |

Les registres correspondants sont créés en sous-étape **S4**.

---

## 5. Portes de validation

| Porte | Moment | Validation obligatoire |
|---|---|---|
| `G0` | Fin du référentiel | Jonathan confirme les documents et conventions |
| `G1` | Fin du socle local | Stack, CI et images validées |
| `G2` | Fin du modèle implémenté | Contraintes et isolation validées |
| `G3` | Fin de l'authentification | Sécurité et sessions validées |
| `G4` | Fin du portail national | Navigation et lecture inter-entités validées |
| `G5` | Fin du trombinoscope | Profils et permissions validés |
| `G6` | Fin du Framework | Contenus et périmètres éditoriaux validés |
| `G7` | Fin de l'onboarding | Tess, Léa, Diane et Jonathan valident les parcours |
| `G8` | Fin de l'accueil | Événements et page d'accueil validés |
| `G9` | Fin du back-office | Import réel répété et validé |
| `G10` | Fin du pilotage | Audit, reporting et support validés |
| `G11` | Fin des traitements | Médias, worker et planification validés |
| `G12` | Fin de recette | Aucun défaut bloquant selon les règles convenues |
| `G13` | Production temporaire | Déploiement, sauvegarde et restauration validés |
| `G14` | Production générale | Léa valide le produit, Jonathan la technique |
