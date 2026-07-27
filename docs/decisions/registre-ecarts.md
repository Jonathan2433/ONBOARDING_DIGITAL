# Registre des écarts

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Séquence créée par :** `DEC-431`
**Dernière mise à jour :** 27 juillet 2026

Un écart est une différence constatée entre l'existant et les documents validés. Il n'est
jamais corrigé silencieusement : il est décrit, son impact est évalué, une recommandation est
formulée, et son caractère bloquant est explicité.

| Statut | Ouverts | Clos | Acceptés |
|---|---:|---:|---:|
| Total 11 | 3 | 6 | 2 |

---

## Vue synthétique

| ID | Écart | Bloquant | Statut |
|---|---|---|---|
| `ECART-001` | Documents de cadrage hors de l'arborescence exigée | Non | **Clos** |
| `ECART-002` | Prototype avec données personnelles à la racine du futur dépôt | Oui, avant premier commit | **Clos** |
| `ECART-003` | Le document prévalent portait le statut « soumis à validation finale » | Non | **Clos** |
| `ECART-004` | Registre `DEC-001` à `DEC-417` absent du corpus | Oui, pour la clôture de `US002` | **Clos** |
| `ECART-005` | Schéma CSV initial attendu au LOT 0 alors que le schéma définitif reste ouvert | Non | Ouvert |
| `ECART-006` | Contenu de `.env.example` dépendant du LOT 1 | Non | Ouvert |
| `ECART-007` | 12 risques du cahier §33 sans identifiant | Non | **Clos** |
| `ECART-008` | Aucune séquence pour les écarts et les dépendances | Non | **Clos** |
| `ECART-009` | Identité Git personnelle sur un projet interne | Non | **Accepté** |
| `ECART-010` | Traçabilité GitHub non mise en place | Non pour `G0`, prérequis du LOT 1 | Ouvert |
| `ECART-011` | Cinq questions absentes de la plage `QO-072` à `QO-105` | Non | **Accepté** |

**Prochain identifiant libre : `ECART-012`.**

---

## `ECART-001` — Documents de cadrage hors de l'arborescence exigée

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, prise en charge du LOT 0 |
| Source | Roadmap, LOT 0, section Livrables : `/docs/product/`, `/docs/architecture/`, `/docs/decisions/`, `/docs/operations/` |
| Constat | Les cinq documents se trouvaient dans un dossier unique `DOCS/`, sans dépôt Git initialisé. |
| Impact | Le livrable littéral du LOT 0 n'était pas satisfait. |
| Bloquant | Non |
| Recommandation | Réorganiser en `docs/` avec les quatre sous-dossiers. |
| Résolution | **Clos** par `DEC-421` et `DEC-425`, appliqués en sous-étapes S1 et S2. Le renommage `DOCS` → `docs` a nécessité une manœuvre en deux temps, le système de fichiers étant insensible à la casse. |

## `ECART-002` — Prototype avec données personnelles à la racine du futur dépôt

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026 |
| Source | Roadmap, LOT 0, critère de sortie n°4 ; backlog §12 |
| Constat | `V1.html`, 2,83 Mo, se trouvait à la racine du répertoire devenu dépôt Git. Il contient environ 130 noms de collaborateurs, leurs photos en Base64, leurs clients, un mot de passe administrateur en clair, 11 usages de `localStorage` et des dépendances CDN. |
| Impact | **Critique.** Un premier commit non protégé aurait gravé des données personnelles et un secret dans l'historique Git, de façon quasi indélébile, et rendu la porte `G0` invalidable. |
| Bloquant | Oui, avant le premier commit |
| Recommandation | Conserver le fichier sur disque et l'exclure du suivi Git. |
| Résolution | **Clos** par `DEC-420`. Fichier déplacé vers `docs/prototype/V1.html`, exclu par `.gitignore`, exclusion vérifiée par contrôle. Voir [docs/prototype/README.md](../prototype/README.md). Risque résiduel suivi en `ROAD-RSK-025`. |

## `ECART-003` — Le document prévalent portait le statut « soumis à validation finale »

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026 |
| Source | Cahier des charges, en-tête ligne 6, contre §35 qui qualifie les quatre annexes de validées |
| Constat | Le cahier des charges, qui prévaut sur les annexes selon la règle de préséance, portait un statut moins abouti que les documents sur lesquels il prévaut. |
| Impact | Ambiguïté du statut de la source de vérité. |
| Bloquant | Non |
| Recommandation | Validation explicite par Jonathan, enregistrée comme décision, sans modification du fichier. |
| Résolution | **Clos** par `DEC-423`, le 27 juillet 2026. |

## `ECART-004` — Registre `DEC-001` à `DEC-417` absent du corpus

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026 |
| Source | Les cinq documents référencent « décisions `DEC-001` à `DEC-417` issues des ateliers de cadrage » |
| Constat | La table correspondante n'est présente dans **aucun** document du corpus. Seules les tables consolidées `RIGHTS`, `DATA`, `ROAD`, `BACKLOG` et `ARB-*` existent, soit 85 entrées. |
| Impact | Le critère de sortie n°2 exige que chaque décision possède un identifiant stable, et `US002` qu'aucune décision ne soit perdue. Sans la source, ni la preuve ni la reconstitution n'étaient possibles. |
| Bloquant | Oui, pour la clôture de `US002` |
| Recommandation | Faire foi des 85 décisions consolidées et réserver la plage `DEC-001` à `DEC-417`. |
| Résolution | **Clos** par `DEC-422`. La plage réservée permettra un import ultérieur des comptes rendus d'ateliers sans conflit d'identifiant. |

## `ECART-005` — Schéma CSV initial attendu au LOT 0 alors que le schéma définitif reste ouvert

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026 |
| Source | `MVP-L00-US004`, priorité `P0`, contre `QO-096` déclarée bloquante avant données réelles |
| Constat | Le LOT 0 doit livrer un schéma de colonnes documenté, alors que le schéma définitif dépend du CSV réel, non disponible. |
| Impact | Aucun, à condition de ne pas confondre les deux. Le risque serait de déclarer `QO-096` close en livrant le schéma initial. |
| Bloquant | Non |
| Recommandation | Livrer le schéma en **v1.0 initiale**, explicitement versionné, et laisser `QO-096` ouverte. |
| Résolution | Ouvert. Traitement prévu en sous-étape S6. |

## `ECART-006` — Contenu de `.env.example` dépendant du LOT 1

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026 |
| Source | `MVP-L00-US007`, priorité `P0`, contre le périmètre du LOT 1 qui définit les services |
| Constat | La liste exhaustive des variables d'environnement dépend de la configuration réelle des services, établie au LOT 1. |
| Impact | Un `.env.example` livré au LOT 0 sera nécessairement incomplet. |
| Bloquant | Non |
| Recommandation | Livrer une **v0.1** couvrant les variables déductibles des décisions déjà validées, avec placeholders explicites et statut « à compléter au LOT 1 ». |
| Résolution | Ouvert. Traitement prévu en sous-étape S5. |

## `ECART-007` — 12 risques du cahier §33 sans identifiant

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026 |
| Source | Cahier des charges §33, contre roadmap §14 qui numérote ses 12 risques |
| Constat | Les 12 risques majeurs du cahier n'ont aucun identifiant, donc ne peuvent être ni référencés dans une pull request ni suivis dans le temps. |
| Impact | Registre des risques partiellement inexploitable. |
| Bloquant | Non |
| Recommandation | Poursuivre la séquence `ROAD-RSK`. |
| Résolution | **Clos** par `DEC-430` : les risques du cahier §33 deviennent `ROAD-RSK-013` à `ROAD-RSK-024`, sans modification de leur libellé. |

## `ECART-008` — Aucune séquence pour les écarts et les dépendances

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026 |
| Source | `MVP-L00-US006` exige un registre de dépendances portant responsable, échéance, impact, statut et caractère bloquant |
| Constat | Aucune séquence d'identifiants n'existait pour les écarts ni pour les dépendances externes. |
| Impact | Registres non référençables. |
| Bloquant | Non |
| Recommandation | Créer deux séquences dédiées. |
| Résolution | **Clos** par `DEC-431` : séquences `ECART-nnn` et `DEP-nnn`. |

## `ECART-009` — Identité Git personnelle sur un projet interne

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S1 |
| Source | Constat local : `user.email = jonathan.dupau24@gmail.com` |
| Constat | Les commits d'un projet interne à eXalt sont signés d'une adresse personnelle. |
| Impact | Aucun impact technique. La traçabilité des contributions gagnerait à l'adresse professionnelle. |
| Bloquant | Non |
| Recommandation | Basculer `user.email` sur l'adresse eXalt pour ce dépôt uniquement. |
| Résolution | **Accepté** par `DEC-424` : le dépôt appartenant au compte personnel de Jonathan, la cohérence est défendable. Écart connu et documenté, non corrigé. |

## `ECART-010` — Traçabilité GitHub non mise en place

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S3 |
| Source | Backlog §11 et `BACKLOG-010` |
| Constat | Les 13 étiquettes prescrites, les 15 milestones, les epics, les issues et la protection de branche `main` n'existent pas encore sur GitHub. `gh` n'est pas installé sur la machine et aucun connecteur GitHub n'est disponible dans la session de travail. |
| Impact | Aucune traçabilité story ↔ issue ↔ pull request n'est possible aujourd'hui. Or elle est exigée dès le LOT 1. |
| Bloquant | Non pour la porte `G0`. **Prérequis du LOT 1.** |
| Recommandation | Installer `gh` ou effectuer la mise en place dans l'interface GitHub. Les commandes prêtes à l'emploi figurent dans [traçabilité GitHub §5](../operations/traceabilite-github.md). |
| Résolution | Ouvert. Suivi par `QO-107` et `QO-108`. |

## `ECART-011` — Cinq questions absentes de la plage `QO-072` à `QO-105`

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S4 |
| Source | Recomptage automatique des identifiants dans le cahier des charges §32 |
| Constat | La plage couvre 34 numéros mais **29** questions seulement sont présentes. Absentes : `QO-075`, `QO-079`, `QO-080`, `QO-082`, `QO-090`. |
| Impact | Ces cinq questions ont probablement été résolues pendant les ateliers, mais leur résolution n'est documentée nulle part dans le corpus. Une question bloquante pourrait s'y trouver. Phénomène de même nature que `ECART-004`. |
| Bloquant | Non |
| Recommandation | Ne pas combler les trous, conformément aux règles de numérotation. Si les comptes rendus d'ateliers sont retrouvés, vérifier le contenu de ces cinq entrées à ce moment-là. |
| Résolution | **Accepté**, écart connu et documenté. Les trous sont conservés et signalés dans le registre des questions ouvertes. |
