# Checklist de validation — porte `G0`

**Pour :** Jonathan
**Lot :** 0 — Référentiel projet et préparation
**Date :** 27 juillet 2026
**Issue :** porte `G0` **validée** par Jonathan le 27 juillet 2026 — décision `DEC-438`
**Preuves détaillées :** [controles-sortie-lot-0.md](controles-sortie-lot-0.md)

Cette checklist tient sur une page. C'est la mesure du risque `ROAD-RSK-010`, « Jonathan devient
un goulot de validation ».

---

## 1. Les cinq critères de sortie

| | Critère | Preuve | État |
|:--:|---|---|:--:|
| ☐ | Les documents de cadrage sont présents dans le dépôt | 5 empreintes SHA-256 identiques aux valeurs d'avant travaux ; 4 sous-dossiers conformes | ✅ |
| ☐ | Chaque décision possède un identifiant stable | 104 décisions, 0 doublon, 0 absence, 89 libellés vérifiés au caractère près | ✅ |
| ☐ | Les responsabilités produit et techniques sont identifiées | `responsabilites-projet.md`, 8 domaines du cahier §5.1 | ✅ |
| ☐ | Aucun fichier réel de collaborateurs n'est versionné | 128 patronymes du prototype confrontés au dépôt : 0 présent. 7 commits scannés, 0 secret | ✅ |
| ☑ | **Jonathan valide le référentiel** | `DEC-438`, 27 juillet 2026 | ✅ |

---

## 2. Les sept stories du lot

| | Story | Prio | Livrable principal | État |
|:--:|---|:--:|---|:--:|
| ☐ | `US001` Dépôt privé et arborescence | P0 | Dépôt, `.gitignore`, 4 sous-dossiers | validée S1 |
| ☐ | `US002` Documents validés versionnés | P0 | 5 documents + preuve d'intégrité | validée S2 |
| ☐ | `US003` Conventions Git et versions | P0 | `CONTRIBUTING.md`, conventions, gabarits GitHub | validée S3 |
| ☐ | `US006` Registres | P0 | Décisions, écarts, risques, questions, dépendances | validée S4 |
| ☐ | `US007` Configuration sans secrets | P0 | `.env.example` v0.1, politique de secrets | validée S5 |
| ☐ | `US004` Schéma initial du CSV | P0 | 19 champs, 68 codes, jeu fictif vérifié | validée S6 |
| ☐ | `US005` Inventaire du prototype | **P1** | 29 contenus, 44 tâches d'onboarding | validée S7, **statut `à relire`** |

Les 6 stories `P0` sont terminées. La story `P1` a fait l'objet de l'arbitrage **(a)** : validée
au statut `à relire`, la relecture étant portée au LOT 6.

---

## 3. Les neuf critères d'empêchement du backlog §12

| | Critère | État |
|:--:|---|:--:|
| ☐ | Aucune story `P0` non terminée | ✅ |
| ☐ | Permissions critiques testées | sans objet |
| ☐ | Migrations fonctionnelles sur base propre | sans objet |
| ☐ | Aucun secret ni donnée réelle versionné | ✅ |
| ☐ | Aucune anomalie bloquante ou critique ouverte | ✅ |
| ☐ | Comportement mobile et clavier utilisable | sans objet |
| ☐ | Démonstration conforme aux critères de la roadmap | ✅ preuve documentaire |
| ☐ | Documentation minimale présente | ✅ 36 documents |
| ☑ | Validation explicite de Jonathan | ✅ |

Les quatre « sans objet » le sont parce que le LOT 0 ne produit **aucun code**, aucune interface
et aucune migration. Ces critères s'appliqueront dès le LOT 1.

---

## 4. Ce que tu valides précisément

En validant `G0`, tu confirmes :

1. **les 19 décisions `DEC-418` à `DEC-436`** deviennent la référence opposable du projet ;
2. **les conventions Git, de versions et de contribution** s'appliqueront dès le LOT 1 ;
3. **le schéma initial du CSV** en version `1.0-initiale` est le contrat d'entrée des données ;
4. **la politique de configuration et de secrets** encadre les trois environnements ;
5. **les 15 écarts, 34 questions, 28 risques, 17 dépendances** constituent l'état connu du projet ;
6. l'inventaire du prototype est exploitable au statut `à relire`.

---

## 5. Ce que tu ne valides pas

| Point | Reste ouvert |
|---|---|
| Le schéma définitif du CSV | `QO-096`, avant données réelles |
| La nomenclature des en-têtes du CSV | `QO-110` |
| Le catalogue des métiers | à établir avec l'ESM |
| Le contenu final de `.env.example` | à compléter au LOT 1 |
| La relecture des contenus éditoriaux | Léa, Tess, Diane, au LOT 6 |
| Les liens Hub, Academy et SharePoint | à fournir, absents du prototype |

---

## 6. Trois points à traiter avant d'ouvrir le LOT 1

Ce ne sont pas des conditions de `G0`, mais des prérequis du lot suivant.

| | Point | Référence |
|:--:|---|---|
| ☐ | Mettre en place la traçabilité GitHub : 13 étiquettes, 15 milestones, protection de `main`. `gh` n'est pas installé | `ECART-010`, `QO-107`, `QO-108` |
| ☐ | Décider des atténuations iCloud pour les volumes Docker et les dépendances, **avant** de créer les volumes | `QO-109`, `ROAD-RSK-026` |
| ☐ | Arbitrer l'exécution non simultanée des trois environnements : 16 Gio de mémoire vive | `ROAD-RSK-027`, `QO-085` |

---

## 7. Publication

Les 7 commits sont **locaux**. Rien n'a été envoyé sur GitHub.

```bash
git push -u origin main
```

---

## 8. Décision

| Décision | Effet |
|---|---|
| **Je valide `G0`** | Le LOT 0 est verrouillé. Je peux préparer le plan du LOT 1, **sans l'exécuter** |
| **Je valide `G0` avec réserves** | Précise lesquelles ; elles sont enregistrées au registre des écarts avant verrouillage |
| **Je ne valide pas** | Précise ce qui manque ; le LOT 0 reste ouvert et je corrige |

Aucun travail du LOT 1 ne commencera avant ta validation explicite (`ROAD-003`,
`ARB-BACK-003`, `BACKLOG-006`).
