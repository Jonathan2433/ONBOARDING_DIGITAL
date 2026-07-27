# Registre des décisions

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Dernière mise à jour :** 27 juillet 2026
**Règles de tenue :** [README.md](README.md)

Ce registre est la vue unique des décisions du projet. Il **reprend** sans les altérer les
85 décisions et arbitrages présents dans les documents validés, et **ajoute** les décisions
prises pendant la réalisation à partir de `DEC-418`.

| Origine | Nombre | Statut |
|---|---:|---|
| Décisions de droits `RIGHTS` | 25 | Validées le 25/07/2026 |
| Décisions de modèle `DATA` | 18 | Validées le 25/07/2026 |
| Décisions de roadmap `ROAD` | 12 | Validées le 25/07/2026 |
| Décisions de backlog `BACKLOG` | 10 | Validées le 25/07/2026 |
| Arbitrages `ARB-*` | 20 | Validés le 25/07/2026 |
| **Total repris** | **85** | |
| Décisions de réalisation `DEC-418+` | 19 | Validées le 27/07/2026 |
| **Total** | **104** | |

---

# 1. Décisions de réalisation — `DEC-418` et suivantes

Toutes validées par Jonathan le 27 juillet 2026, lot 0, sous-étapes S1 à S6.

| ID | Décision | Motif | Statut |
|---|---|---|---|
| `DEC-418` | Le dépôt local réside dans le dossier iCloud Drive du projet, `~/Library/Mobile Documents/com~apple~CloudDocs/CODE/ONBOARDING_DIGITAL`. | Choix de Jonathan après exposition du risque. Emplacement de travail habituel. | Validée |
| `DEC-419` | Le dépôt distant est `Jonathan2433/ONBOARDING_DIGITAL`, privé, sur le compte personnel de Jonathan. | Dépôt déjà créé par Jonathan. Caractère privé confirmé par lui le 27/07/2026. | Validée |
| `DEC-420` | Le prototype `V1.html` est conservé dans `docs/prototype/` pour historisation, et **exclu du suivi Git**. | Historisation souhaitée, mais le fichier contient des données personnelles réelles et un mot de passe en clair. Le versionner rendrait la porte `G0` invalidable. | Validée |
| `DEC-421` | Le dossier documentaire est nommé `docs` en minuscules, avec les sous-dossiers `product`, `architecture`, `decisions`, `operations`, plus `prototype`. | Exigence littérale de la roadmap. Le système de fichiers étant insensible à la casse, `DOCS` a été renommé en deux temps. | Validée |
| `DEC-422` | Les 85 décisions et arbitrages consolidés font foi comme registre décisionnel. La plage `DEC-001` à `DEC-417` est **réservée** pour un import ultérieur sans conflit. Les décisions de réalisation démarrent à `DEC-418`. | La table `DEC-001..417` n'est présente dans aucun document du corpus (`ECART-004`). Cette formulation préserve les deux issues possibles. | Validée |
| `DEC-423` | Jonathan valide le cahier des charges v1.0 le 27/07/2026, **sans modification du fichier**. Le statut faisant foi est celui de ce registre et de l'index `docs/README.md`. | Valider n'est pas une évolution de contenu : le cahier §35 n'exige donc aucun changement de version. L'immuabilité du fichier préserve la preuve d'intégrité par empreinte SHA-256. | Validée |
| `DEC-424` | L'identité Git personnelle `jonathan.dupau24@gmail.com` est conservée pour ce dépôt. | Le dépôt appartient au compte personnel de Jonathan : la cohérence est défendable. `ECART-009` clos en risque accepté. | Validée |
| `DEC-425` | Répartition documentaire : `docs/product/` reçoit le cahier des charges, la matrice des droits, la roadmap et le backlog ; `docs/architecture/` reçoit le modèle de données. | `product/` porte le quoi et le quand, `architecture/` porte le comment technique. La matrice est d'abord un arbitrage métier. | Validée |
| `DEC-426` | Les cinq documents validés conservent leur nom d'origine en majuscules. Les documents produits par le projet utilisent le kebab-case minuscule. | Préserve la traçabilité avec le prompt de cadrage et les références croisées internes. | Validée |
| `DEC-427` | Le circuit branche + pull request s'applique à partir du **premier commit de code du LOT 1**. Les sous-étapes documentaires du LOT 0 restent en commits directs sur `main`, chacune validée explicitement par Jonathan. | Au LOT 0 aucune intégration continue n'existe : une pull request n'y vérifierait rien automatiquement. La revue est portée par la validation de sous-étape. | Validée |
| `DEC-428` | Versionnement sémantique préfixé `v`, jalonné sur les portes : `v0.1.0` à `G1` … `v0.13.0` à `G13`, puis **`v1.0.0` à l'ouverture générale `G14`**. `G0` ne produit aucun tag. `PATCH` pour une correction sur un lot validé. | Le numéro mineur devient un indicateur d'avancement. `v1.0.0` signale sans ambiguïté le premier logiciel réellement ouvert à tous. La production temporaire n'est pas la production générale. | Validée |
| `DEC-429` | `main` est protégée : pull request obligatoire, **zéro approbation requise**, rejet des push directs et forcés. Les contrôles d'intégration deviendront bloquants au LOT 1. | GitHub interdit d'approuver sa propre pull request. Exiger une approbation bloquerait toute fusion tant que Jonathan est l'unique relecteur — objet de `QO-094`. | Validée |
| `DEC-430` | Les 12 risques du cahier des charges §33, jusqu'ici sans identifiant, deviennent `ROAD-RSK-013` à `ROAD-RSK-024`, sans modification de leur libellé. Les risques nouveaux démarrent à `ROAD-RSK-025`. | Un registre sans identifiant est inexploitable et non référençable dans une pull request. Une seule séquence de risques pour tout le projet. | Validée |
| `DEC-431` | Création des séquences `ECART-nnn` pour les écarts et `DEP-nnn` pour les dépendances externes. | `MVP-L00-US006` exige un registre de dépendances portant responsable, échéance, impact, statut et caractère bloquant. Une dépendance n'est ni une question ni un risque. | Validée |

| `DEC-432` | Le CSV collaborateurs utilise le séparateur `;` et l'encodage UTF-8. La virgule est tolérée si elle est détectée de façon non ambiguë, et le séparateur retenu est consigné au rapport d'import. Un BOM est retiré à la lecture et jamais propagé. | Les noms et présentations contiennent des virgules, pas des points-virgules : le besoin de guillemets et donc le risque de saisie diminuent. C'est aussi le format produit nativement par Excel en locale française. | Validée |
| `DEC-433` | Le CSV porte un champ `autorisation_photo` à trois valeurs `oui`, `non`, `inconnu`, avec **`inconnu` par défaut**. Sans autorisation active, aucune photo n'est publiée et l'avatar neutre est utilisé. | Le cahier §21.2 exige une autorisation explicite. `non` et `inconnu` produisent le même affichage mais se distinguent au registre, distinction nécessaire au traitement de `QO-098`. | Validée |
| `DEC-434` | Le schéma du CSV définit des **champs logiques** `F01` à `F19`, indépendants de tout intitulé de colonne. Les en-têtes du fichier réel sont associées à ces champs par un **profil de correspondance versionné**, enregistré avec le lot d'import aux côtés de l'empreinte et du séparateur. | La nomenclature des en-têtes est en suspens (`QO-110`), la source de données n'étant pas connue. Ce découplage est de toute façon nécessaire : les en-têtes du fichier réel ne correspondront pas à des intitulés inventés à l'avance. | Validée |
| `DEC-435` | Imputation des anomalies portant sur plusieurs lignes. **Doublon d'identifiant** : la première occurrence du fichier est retenue, les suivantes seules sont rejetées. **Conflit d'attribution métier** — Booster, responsables de bureau : toutes les lignes du groupe sont rejetées, aucune n'est retenue. **Homonymie** : les deux lignes attendent une décision. **Rapprochement de client** : seule la ligne portant la variante non reconnue est signalée. | Sans ces règles, une ligne correcte serait rejetée par ricochet. Désigner un Booster par l'ordre d'apparition dans un fichier serait une décision métier arbitraire ; conserver la première occurrence d'un e-mail est en revanche déterministe et tracé. | Validée |

| `DEC-436` | Création de la séquence `CONT-nnn` pour les éléments de contenu éditorial inventoriés. Chaque élément porte un identifiant stable, un propriétaire de relecture et un statut parmi `à relire`, `validé`, `à réécrire`, `écarté`. | L'inventaire du prototype doit être référençable story par story au LOT 6 et au LOT 7. Sans identifiant, un contenu relu ne peut pas être relié à sa validation ni à sa publication. Même motif que `DEC-431` pour les écarts et les dépendances. | Validée |

**Prochain identifiant libre : `DEC-437`.**

---

# 2. Décisions de droits — matrice des rôles et permissions §26

Reprises sans altération. Source : `docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md` v1.1,
validée le 25 juillet 2026.

| ID | Décision |
|---|---|
| `RIGHTS-001` | Toute permission est refusée par défaut si elle n’est pas explicitement accordée. |
| `RIGHTS-002` | Une personne possède une seule entité principale active. |
| `RIGHTS-003` | Les autres entités sont accessibles en lecture seule aux employés authentifiés. |
| `RIGHTS-004` | Les responsabilités se cumulent dans l’entité principale. |
| `RIGHTS-005` | Le DG reçoit automatiquement la responsabilité DSM dans son entité. |
| `RIGHTS-006` | Le DSM est limité à ses consultants. |
| `RIGHTS-007` | Le Booster est limité à son cercle. |
| `RIGHTS-008` | Le responsable de bureau est limité à son bureau. |
| `RIGHTS-009` | L’ESM dispose des pouvoirs fonctionnels transverses de son entité. |
| `RIGHTS-010` | L’administrateur d’entité administre et supporte son entité uniquement. |
| `RIGHTS-011` | Le super-administrateur possède les droits globaux et la purge définitive. |
| `RIGHTS-012` | Les collaborateurs ne modifient plus leur profil après validation. |
| `RIGHTS-013` | Le nouvel arrivant modifie uniquement les informations personnelles autorisées avant validation. |
| `RIGHTS-014` | Les exports respectent toujours le périmètre de consultation. |
| `RIGHTS-015` | Les permissions sont recalculées côté API pour chaque requête. |
| `RIGHTS-016` | Les changements de rôle, archivages, restaurations et purges sont audités. |
| `RIGHTS-017` | Une intervention globale du super-administrateur dans une entité exige une traçabilité renforcée. |
| `RIGHTS-018` | Les comptes de service utilisent des scopes limités et ne remplacent pas un utilisateur humain. |
| `RIGHTS-019` | La clôture d’une responsabilité révoque immédiatement les permissions associées. |
| `RIGHTS-020` | Les contraintes métier peuvent interdire une action pourtant autorisée par le rôle. |
| `RIGHTS-021` | Après cinq minutes, seules l’ESM, l’administrateur d’entité et le super-administrateur peuvent réouvrir une tâche. |
| `RIGHTS-022` | L’administrateur d’entité ne peut pas attribuer les responsabilités Framework. |
| `RIGHTS-023` | L’ESM peut effectuer les restaurations fonctionnelles de son entité. |
| `RIGHTS-024` | Le Booster ne peut pas modifier les données hors cercle d’un membre secondaire. |
| `RIGHTS-025` | Les modèles DSM et Booster restent limités à leur périmètre. |

## 2.1 Arbitrages de droits — matrice §25

| ID | Arbitrage |
|---|---|
| `ARB-DROIT-001` | Réouverture d'une tâche après cinq minutes : seuls l'ESM, l'administrateur d'entité et le super-administrateur. Motif et audit obligatoires. |
| `ARB-DROIT-002` | L'attribution et le retrait des responsabilités DSM, ESM, Booster et responsable de bureau sont réservés à l'ESM et au super-administrateur. L'administrateur d'entité n'en dispose pas. |
| `ARB-DROIT-003` | L'ESM peut restaurer dans son entité un profil, un contenu, un événement, un cercle ou un bureau. Les restaurations techniques, massives ou liées aux imports restent réservées à l'administrateur d'entité et au super-administrateur. |
| `ARB-DROIT-004` | Le Booster gère l'appartenance secondaire à son cercle ainsi que les contenus et onboardings liés. Il ne peut pas modifier le cercle principal, le DSM, le client ou le statut d'un membre seulement secondaire. |
| `ARB-DROIT-005` | Modèles d'onboarding : le DSM crée pour ses consultants, le Booster pour son cercle, l'ESM et l'administrateur d'entité en transverse, le super-administrateur les modèles génériques globaux. |

---

# 3. Décisions de modèle de données — modèle §32

Source : `docs/architecture/MODELE_DONNEES_EXALT.md` v1.0, validée le 25 juillet 2026.

| ID | Décision |
|---|---|
| `DATA-001` | Une personne possède une identité globale unique. |
| `DATA-002` | Les données propres à une entité sont portées par une appartenance historisée. |
| `DATA-003` | Les responsabilités Framework et les rôles techniques sont séparés. |
| `DATA-004` | Les clients sont globaux et activés par entité. |
| `DATA-005` | Les alias clients exigent une validation humaine. |
| `DATA-006` | Les modèles d’onboarding sont versionnés et les versions publiées sont immuables. |
| `DATA-007` | Les instances conservent des snapshots des tâches. |
| `DATA-008` | Les fichiers sont stockés dans MinIO et leurs métadonnées dans PostgreSQL. |
| `DATA-009` | Les contenus utilisent un modèle hybride typé, sans HTML arbitraire. |
| `DATA-010` | Les imports passent par une zone d’analyse avant écriture. |
| `DATA-011` | Les jobs sont persistés dans PostgreSQL et exécutés par Dramatiq. |
| `DATA-012` | Une outbox transactionnelle coordonne les effets externes. |
| `DATA-013` | Les actions sensibles produisent un audit atomique. |
| `DATA-014` | Les références locales sont protégées contre les liens inter-entités. |
| `DATA-015` | Les suppressions physiques sont rares et contrôlées. |
| `DATA-016` | Les historiques utilisent des périodes de validité. |
| `DATA-017` | Les données dérivées ne deviennent pas la source de vérité. |
| `DATA-018` | Le schéma reste compatible avec Entra ID et Graph en V2. |

## 3.1 Arbitrages de modèle — modèle §31

| ID | Arbitrage |
|---|---|
| `ARB-DATA-001` | Séparation `person` / `entity_membership` : identité globale unique, données locales dans l'appartenance. |
| `ARB-DATA-002` | Table générique `framework_responsibility_assignment` avec type et scope contrôlés, plutôt que quatre tables séparées. |
| `ARB-DATA-003` | Modèle éditorial hybride : pages typées composées de blocs autorisés, pas de CMS libre, pas de HTML arbitraire. |
| `ARB-DATA-004` | Historisation temporelle systématique : les affectations structurantes sont clôturées puis recréées, jamais écrasées. |
| `ARB-DATA-005` | Outbox transactionnelle et jobs PostgreSQL : audit, outbox et jobs écrits dans la même transaction que l'action métier. Redis sert uniquement au transport. |

---

# 4. Décisions de roadmap — roadmap §17

Source : `docs/product/ROADMAP_MVP_V1_V2_EXALT.md` v1.0, validée le 25 juillet 2026.

| ID | Décision |
|---|---|
| `ROAD-001` | Le MVP est réalisé en 15 lots séquentiels de 0 à 14. |
| `ROAD-002` | Chaque lot possède une démonstration et une validation explicite. |
| `ROAD-003` | Aucun lot dépendant ne commence avant validation du précédent. |
| `ROAD-004` | Le socle MinIO est installé tôt et la chaîne média est finalisée dans un lot spécialisé. |
| `ROAD-005` | Le MVP inclut la production temporaire et la préparation de la production générale. |
| `ROAD-006` | La production générale reste conditionnée aux dépendances externes validées. |
| `ROAD-007` | La V1 commence après une période d’usage réel du MVP. |
| `ROAD-008` | La V2 est conditionnée aux autorisations de la DSI. |
| `ROAD-009` | Les intégrations Microsoft ne sont pas sur le chemin critique du MVP ou de la V1. |
| `ROAD-010` | Les fonctions explicitement différées ne doivent pas être ajoutées silencieusement au MVP. |
| `ROAD-011` | Les tests de performance commencent avant la recette finale. |
| `ROAD-012` | Une exigence Must non terminée empêche la validation du lot concerné. |

## 4.1 Arbitrages de roadmap — roadmap §16

| ID | Arbitrage |
|---|---|
| `ARB-ROAD-001` | Conserver 15 lots MVP numérotés de 0 à 14. |
| `ARB-ROAD-002` | Amorcer MinIO dès le LOT 1, utiliser les médias simples dans les lots métier, finaliser la chaîne média au LOT 11. |
| `ARB-ROAD-003` | Rendre obligatoire la validation du MVP sur la production temporaire locale avant migration vers l'hébergement permanent. |
| `ARB-ROAD-004` | Ne pas démarrer la V1 immédiatement : le MVP doit d'abord être exploité et avoir exécuté au moins un parcours d'arrivée réel. |
| `ARB-ROAD-005` | Considérer tous les lots Microsoft comme conditionnels, sans engagement avant validation des accès, scopes, responsabilités et sources de vérité. |

---

# 5. Décisions de backlog — backlog §14

Source : `docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md` v1.0, validée le 25 juillet 2026.

| ID | Décision |
|---|---|
| `BACKLOG-001` | Le backlog est structuré par les 15 lots MVP validés. |
| `BACKLOG-002` | Les priorités P0, P1 et P2 gouvernent l’ordre de réalisation. |
| `BACKLOG-003` | Une story P0 ouverte empêche la validation de sa porte. |
| `BACKLOG-004` | Les tailles relatives ne constituent pas des estimations de délai. |
| `BACKLOG-005` | Toute story XL est découpée avant implémentation. |
| `BACKLOG-006` | Seul le lot ouvert par Jonathan peut être réalisé. |
| `BACKLOG-007` | Les stories V1 et V2 ne sont pas développées avant leurs conditions d’entrée. |
| `BACKLOG-008` | Les défauts critiques préemptent les fonctions prévues. |
| `BACKLOG-009` | Une story n’est Done qu’avec tests, documentation et démonstration. |
| `BACKLOG-010` | GitHub conserve la traçabilité entre story, décision, PR, tests et porte. |

## 5.1 Arbitrages de backlog — backlog §13

| ID | Arbitrage |
|---|---|
| `ARB-BACK-001` | Retenir `P0`, `P1` et `P2`, avec interdiction de franchir une porte tant qu'une story `P0` reste ouverte. |
| `ARB-BACK-002` | Utiliser les tailles `S`, `M`, `L`, `XL` sans les convertir en délais. Toute story `XL` est découpée avant réalisation. |
| `ARB-BACK-003` | Seul le lot explicitement ouvert par Jonathan peut passer à `Ready` ou `In progress`. |
| `ARB-BACK-004` | Conserver les stories V1 et V2 dans le backlog pour la traçabilité, mais les laisser `Blocked` jusqu'aux conditions de la roadmap. |
| `ARB-BACK-005` | Tout défaut critique de sécurité, de données, d'isolation ou d'accessibilité essentielle devient immédiatement prioritaire sur les fonctionnalités du lot en cours. |

---

# 6. Contrôle de complétude

| Séquence | Attendu | Présent dans ce registre |
|---|---:|---:|
| `RIGHTS` | 25 | 25 |
| `DATA` | 18 | 18 |
| `ROAD` | 12 | 12 |
| `BACKLOG` | 10 | 10 |
| `ARB-DROIT` | 5 | 5 |
| `ARB-DATA` | 5 | 5 |
| `ARB-ROAD` | 5 | 5 |
| `ARB-BACK` | 5 | 5 |
| `DEC-418+` | 19 | 19 |
| **Total** | **104** | **104** |

Les nombres attendus ont été obtenus par comptage automatique dans les documents sources.
Voir [contrôles de sortie du lot 0](../operations/) en sous-étape S8.
