# Documentation produit

Ce dossier contient le cadrage fonctionnel validé et les contenus éditoriaux du projet.

**Responsables :** Léa pour les arbitrages produit et métier, Tess pour la validation
fonctionnelle et éditoriale, Diane pour la validation métier des contenus et parcours.

---

## 1. Documents validés

| Document | Version | Statut | Date |
|---|---|---|---|
| [CAHIER_DES_CHARGES_EXALT_BORDEAUX.md](CAHIER_DES_CHARGES_EXALT_BORDEAUX.md) | 1.0 | Validé par Jonathan le 27 juillet 2026 — décision `DEC-423` | 25 juillet 2026 |
| [MATRICE_ROLES_PERMISSIONS_EXALT.md](MATRICE_ROLES_PERMISSIONS_EXALT.md) | 1.1 | Validé par Jonathan | 25 juillet 2026 |
| [ROADMAP_MVP_V1_V2_EXALT.md](ROADMAP_MVP_V1_V2_EXALT.md) | 1.0 | Validé par Jonathan | 25 juillet 2026 |
| [BACKLOG_INITIAL_PRIORISE_EXALT.md](BACKLOG_INITIAL_PRIORISE_EXALT.md) | 1.0 | Validé par Jonathan | 25 juillet 2026 |

Ces fichiers sont **immuables** en l'état. Toute évolution suit la procédure du cahier des
charges section 35 : décision explicite enregistrée, changement de version du document,
évaluation de l'impact sur le modèle, la roadmap, le backlog et les tests, mise à jour du
cahier des charges.

---

## 2. À quoi sert chaque document

### Cahier des charges — la référence prévalente

Consolide les ateliers 1 à 34. Couvre la vision, le périmètre organisationnel multi-entités,
la gouvernance, l'authentification, l'arborescence, les parcours, les exigences
fonctionnelles, les règles métier, les données et l'import initial, l'UX et le responsive,
l'accessibilité, l'architecture cible, l'API, les médias, la sécurité, le RGPD,
l'infrastructure locale, la CI/CD, les tests, la performance, les sauvegardes, le
monitoring, les logs, la recette, les périmètres MVP/V1/V2, les dépendances bloquantes, les
questions ouvertes et les risques majeurs.

Intègre les quatre autres documents en annexes A à D. Un contrôle de conformité prouve que
les annexes sont identiques aux documents spécialisés : voir
[integrité et conformité des documents](../operations/integrite-et-conformite-documents.md).

### Matrice des rôles et permissions — l'autorité des droits

Définit les dix types d'utilisateurs, leurs périmètres, et le détail des droits de
consultation, création, modification, publication, archivage, restauration, export et
suppression. Applique le **refus par défaut**.

Contient 25 décisions `RIGHTS-001` à `RIGHTS-025`, 5 arbitrages `ARB-DROIT-001` à `-005`, et
20 contrôles d'acceptation obligatoires. C'est l'entrée directe des règles d'autorisation
de l'API et des tests de permissions et d'isolation.

### Roadmap — le séquencement

Définit les 15 lots MVP numérotés 0 à 14, leurs dépendances, leurs livrables, leurs critères
de sortie et les 15 portes de validation `G0` à `G14`. Définit également les 6 lots V1 et les
6 lots V2 conditionnels, ainsi que les fonctions explicitement exclues du MVP.

Contient 12 décisions `ROAD-001` à `ROAD-012`, 5 arbitrages `ARB-ROAD-001` à `-005` et 12
risques `ROAD-RSK-001` à `ROAD-RSK-012`.

### Backlog initial priorisé — les unités de réalisation

Décompose les 15 lots en 112 user stories, dont 94 `P0`. Définit les priorités `P0`/`P1`/`P2`,
les tailles relatives, les états, la définition de Ready, la définition de Done, les règles
de gestion des anomalies et la traçabilité GitHub attendue.

Contient 10 décisions `BACKLOG-001` à `BACKLOG-010` et 5 arbitrages `ARB-BACK-001` à `-005`.

---

## 3. Chaîne de production des livrables de cadrage

Chaque document a servi d'entrée obligatoire au suivant.

```text
Matrice des droits (1/6)
        │
        ▼
Modèle de données (2/6)  ──►  docs/architecture/
        │
        ▼
Roadmap MVP/V1/V2 (3/6)
        │
        ▼
Backlog initial priorisé (4/6)
        │
        ▼
Cahier des charges consolidé (5/6)  ──►  intègre les 4 précédents en annexes A à D
        │
        ▼
Prompt du premier agent IA de réalisation (6/6)
```

---

## 4. Références croisées déclarées

| Document | Références qu'il déclare en entrée |
|---|---|
| Matrice v1.1 | Aucune — premier livrable de la chaîne |
| Modèle de données v1.0 | Matrice v1.1 |
| Roadmap v1.0 | Matrice v1.1, modèle v1.0, décisions `DEC-001` à `DEC-417` |
| Backlog v1.0 | Matrice v1.1, modèle v1.0, roadmap v1.0, décisions `DEC-001` à `DEC-417`, arbitrages des ateliers 1 à 34 |
| Cahier des charges v1.0 | Les quatre documents ci-dessus, en annexes contractuelles A à D |

Le traitement de la référence `DEC-001` à `DEC-417`, dont la table n'est présente dans aucun
document du corpus, est fixé par la décision `DEC-422`. Voir
[registre des décisions](../decisions/) — créé en sous-étape S4.

---

## 5. Contenus éditoriaux

Le sous-dossier `contenus/` accueillera, en sous-étape S7 du LOT 0
(story `MVP-L00-US005`, priorité `P1`) :

- l'inventaire des contenus du prototype à reprendre, avec propriétaire et statut de
  relecture ;
- les liens internes à confirmer ;
- la liste des exclusions explicites du prototype.

Aucune donnée personnelle n'y figurera. Le prototype lui-même est décrit dans
[docs/prototype/README.md](../prototype/README.md).
