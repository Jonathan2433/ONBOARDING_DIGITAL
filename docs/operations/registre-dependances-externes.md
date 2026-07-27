# Registre des dépendances externes

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Séquence créée par :** `DEC-431`
**Dernière mise à jour :** 27 juillet 2026
**Sources reprises :** cahier des charges §31, roadmap §13, LOT 14

Une dépendance externe est un élément attendu d'un tiers, avec un responsable et une
échéance. Elle se distingue d'une question ouverte, qui attend une réponse, et d'un risque,
qui n'est qu'une éventualité.

| Catégorie | Identifiants | Nombre | Bloque |
|---|---|---:|---|
| Bloquantes avant l'ouverture générale | `DEP-001` à `014` | 14 | Porte `G14` |
| V2, conditionnelles à la DSI | `DEP-015` à `017` | 3 | Rien avant la V2 |
| **Total** | | **17** | |

**Prochain identifiant libre : `DEP-018`.**

> **Aucune de ces dépendances ne bloque le développement local.** La roadmap §13.1 est
> explicite : domaine web public, fournisseur d'e-mails réel, hébergement final, Entra ID,
> Graph et Teams sont **non bloquants pour le développement local**. Elles deviennent
> bloquantes avant l'ouverture générale.

---

# 1. Dépendances bloquant l'ouverture générale

Critère d'ouverture de la porte `G14` : **toutes les dépendances externes sont résolues.**

| ID | Dépendance | Responsable | Impact si absente | Lot concerné | Questions liées | Statut |
|---|---|---|---|---|---|---|
| `DEP-001` | Hébergement permanent disponible en continu | Jonathan / eXalt | **Bloque l'ouverture générale.** Le MVP reste sur la production temporaire locale, sans garantie de disponibilité. | LOT 14 | `QO-081`, `QO-101` | Ouverte |
| `DEP-002` | Domaine web officiel | eXalt | Bloque l'ouverture générale. Aucun domaine public n'est nécessaire pendant la phase locale. | LOT 14 | — | Ouverte |
| `DEP-003` | DNS et HTTPS sur le domaine officiel | Jonathan / DSI | Bloque l'ouverture générale. Caddy assure HTTPS local en attendant. | LOT 14 | — | Ouverte |
| `DEP-004` | Fournisseur d'e-mails transactionnels réel | Jonathan / eXalt | Bloque l'ouverture générale : sans lui, aucun magic link réel ne peut être délivré. Mailpit couvre développement et recette. | LOT 14 | — | Ouverte |
| `DEP-005` | Domaine e-mail `@exalt-company.com` confirmé dans la configuration | eXalt / DSI | Bloque l'authentification réelle. Domaine initial déjà confirmé par le cahier §7.2, à valider en configuration de production. | LOT 14 | — | Ouverte |
| `DEP-006` | Charte, logo et typographie officiels exploitables, licence web incluse | Léa / eXalt | Bloque l'identité visuelle définitive. Des design tokens provisoires remplaçables sans refonte sont prévus. | LOT 4, définitif au LOT 14 | — | Ouverte, liée à `ROAD-RSK-006` |
| `DEP-007` | Fichier CSV final validé, gelé et empreinté | Léa / ESM | Bloque le chargement des données réelles. Un schéma initial et des données fictives sont préparés dès le LOT 0. | LOTS 9, 12, 14 | `QO-096`, `QO-097`, `QO-099`, `QO-100` | Ouverte, liée à `ROAD-RSK-004` |
| `DEP-008` | Personnes morales responsables de traitement identifiées | eXalt / juridique | Bloque la notice de confidentialité et la conformité RGPD. | LOT 10, définitif au LOT 14 | `QO-073`, `QO-076`, `QO-077` | Ouverte |
| `DEP-009` | Contact RGPD ou DPO désigné | eXalt | Bloque la notice d'information et le traitement des demandes de droits. | LOT 10, définitif au LOT 14 | `QO-074` | Ouverte |
| `DEP-010` | Sauvegarde extérieure à l'hôte, destination chiffrée hors site | Jonathan / eXalt | Bloque l'ouverture générale : le RPO de 24 heures ne serait pas couvert hors de l'hôte. | LOTS 13, 14 | `QO-083`, `QO-087`, `QO-088` | Ouverte, liée à `ROAD-RSK-020` |
| `DEP-011` | Supervision depuis une machine distincte | Jonathan | Bloque la détection d'une panne de l'hôte lui-même. | LOTS 13, 14 | `QO-091`, `QO-095` | Ouverte, liée à `ROAD-RSK-019` |
| `DEP-012` | Restauration testée avec succès | Jonathan | Bloque l'ouverture générale. Test obligatoire avant données réelles, puis mensuel. | LOTS 12, 13 | `QO-089` | Ouverte, liée à `ROAD-RSK-020` |
| `DEP-013` | Recette complète sur l'hébergement cible | Tess, Léa, Diane, Jonathan | Bloque l'ouverture générale. La recette locale ne remplace pas la recette sur l'hôte final. | LOTS 12, 14 | — | Ouverte |
| `DEP-014` | Tests de sécurité et de charge sur l'hôte final | Jonathan | Bloque l'ouverture générale : 100 utilisateurs simultanés et absence de défaut critique. | LOTS 12, 14 | `QO-104`, `QO-105` | Ouverte |

---

# 2. Dépendances V2, conditionnelles

Ces dépendances **ne bloquent ni le MVP ni la V1** (`ROAD-009` : les intégrations Microsoft
ne sont pas sur le chemin critique). Elles sont enregistrées pour la traçabilité.

| ID | Dépendance | Responsable | Condition préalable | Statut |
|---|---|---|---|---|
| `DEP-015` | Microsoft Entra ID : tenant, application enregistrée, autorisations, URLs officielles, politique de sécurité, stratégie de secours | DSI | Validation DSI du principe des intégrations Microsoft | Conditionnelle |
| `DEP-016` | Microsoft Graph : scopes approuvés, responsabilités de source de vérité par champ | DSI | `DEP-015` résolue | Conditionnelle |
| `DEP-017` | Teams : identité technique dédiée, scopes minimaux, canal de publication | DSI | `DEP-015` résolue | Conditionnelle |

Aucun engagement de réalisation V2 ne doit être pris avant validation des accès, scopes,
responsabilités et sources de vérité (`ARB-ROAD-005`, `ROAD-008`).

---

# 3. Ce qui n'est pas une dépendance externe

Pour éviter de gonfler ce registre :

| Élément | Où il est suivi |
|---|---|
| Traçabilité GitHub non mise en place, `gh` absent | `ECART-010`, `QO-107`, `QO-108` — outillage local, non un tiers |
| Mémoire vive de la machine | `ROAD-RSK-027`, alimente `QO-085` |
| Emplacement du dépôt dans iCloud Drive | `DEC-418`, `ROAD-RSK-026`, `QO-109` |
| Choix d'outil de test de charge | `QO-104` — décision d'architecture |
| Second référent technique | `QO-094`, `ROAD-RSK-022` |

---

# 4. Règles de tenue

- chaque dépendance porte un responsable **nommé**, jamais une entité vague ;
- une dépendance résolue conserve son identifiant, sa date de résolution et la preuve ;
- une dépendance ne se ferme pas sur une promesse : elle se ferme sur un élément livré ou
  configuré et vérifié ;
- l'échéance est exprimée en lot concerné plutôt qu'en date, le projet n'étant pas piloté par
  un calendrier contractuel ;
- une dépendance dont l'absence bloque une porte est signalée dans la checklist de cette
  porte.
