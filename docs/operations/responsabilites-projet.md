# Responsabilités produit et techniques

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Fondement :** cahier des charges §5.1, roadmap LOT 0 « Validation », matrice §14.1
**Répond au critère de sortie du LOT 0 n°3 :** « les responsabilités produit et techniques sont identifiées »

---

## 1. Responsabilités de décision

Reprises sans altération du cahier des charges §5.1.

| Domaine | Responsable principal |
|---|---|
| Arbitrages produit et métier | **Léa** |
| Architecture et choix techniques | **Jonathan** |
| Validation fonctionnelle et éditoriale | **Tess** |
| Validation métier des contenus et parcours | **Diane** |
| Validation technique, sécurité, sauvegardes et déploiement | **Jonathan** |
| Validation des consultants et missions | DSM concernés |
| Validation des cercles | Boosters concernés |
| Validation des bureaux | Responsables concernés |

Un problème critique de sécurité, d'intégrité, de confidentialité ou d'isolation
multi-entités **bloque la livraison** jusqu'à résolution ou arbitrage documenté.

---

## 2. Validation des portes

| Porte | Validateur principal | Contributeurs |
|---|---|---|
| `G0` | Jonathan | Léa, Tess et Diane pour les éléments métier et éditoriaux |
| `G1` à `G6` | Jonathan | — |
| `G7` | Jonathan | **Tess, Léa et Diane valident les parcours d'onboarding** |
| `G8` | Jonathan | — |
| `G9` | Jonathan | **Léa valide le rapport de répétition d'import en recette** |
| `G10` à `G13` | Jonathan | — |
| `G14` | **Léa pour le produit, Jonathan pour la technique** | Tess et Diane sur leurs périmètres |

Aucun lot dépendant ne commence avant validation explicite du lot précédent (`ROAD-003`).
Seul le lot explicitement ouvert par Jonathan peut contenir des stories `Ready` ou
`In progress` (`ARB-BACK-003`, `BACKLOG-006`).

---

## 3. Validation métier lors de l'import des données

Reprise de la matrice §14.1.

| Périmètre | Valideur |
|---|---|
| Collaborateurs, statuts, arrivées et contenus généraux | ESM |
| Consultants, missions et clients de leur périmètre | DSM concernés |
| Membres de leur cercle | Boosters concernés |
| Contenus de leur bureau, hors import collaborateur | Responsables de bureau |
| Structure technique et rapport d'import | **Jonathan** |
| Chargement final des données réelles | **Léa et Jonathan** |

---

## 4. Responsabilités d'exploitation pendant la phase locale

| Sujet | Responsable | Référence |
|---|---|---|
| Destinataire unique des alertes Uptime Kuma | **Jonathan** | Cahier §27.1, matrice §17 |
| Affectation par défaut des alertes opérationnelles | **Jonathan** | Modèle de données §21.2 |
| Suivi des signalements de bugs | **Jonathan** | Cahier §9.6 |
| Sauvegardes, restauration et tests de restauration | **Jonathan** | Cahier §26 |
| Déploiements et retours arrière | **Jonathan** | Cahier §23.4, §29.8 |
| Secrets et configuration des trois environnements | **Jonathan** | Cahier §20.3 |

---

## 5. Point de vigilance

Le risque `ROAD-RSK-022` — « Jonathan seul référent » — est qualifié d'impact **Élevé** par le
cahier des charges. Sa réponse principale est « documentation, automatisation et second
référent futur ». Ce second référent fait l'objet de la question ouverte `QO-094`, non
bloquante pour le développement mais **attendue avant la production générale**.

Ce point a une conséquence concrète et immédiate : la décision `DEC-429` fixe **zéro
approbation requise** sur les pull requests, GitHub interdisant d'approuver sa propre pull
request. La règle deviendra révisable dès qu'un second relecteur existera.

Le risque `ROAD-RSK-010` — « Jonathan devient un goulot de validation » — est traité par des
démonstrations structurées et une checklist concise à chaque porte. La checklist de la porte
`G0` est produite en sous-étape S8.
