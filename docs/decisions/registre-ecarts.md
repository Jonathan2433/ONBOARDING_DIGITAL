# Registre des écarts

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Séquence créée par :** `DEC-431`
**Dernière mise à jour :** 21 août 2026, LOT 3 sous-étape `T8`

Un écart est une différence constatée entre l'existant et les documents validés. Il n'est
jamais corrigé silencieusement : il est décrit, son impact est évalué, une recommandation est
formulée, et son caractère bloquant est explicité.

| Statut | Ouverts | Clos | Acceptés |
|---|---:|---:|---:|
| Total 34 | 7 | 25 | 2 |

---

## Vue synthétique

| ID | Écart | Bloquant | Statut |
|---|---|---|---|
| `ECART-001` | Documents de cadrage hors de l'arborescence exigée | Non | **Clos** |
| `ECART-002` | Prototype avec données personnelles à la racine du futur dépôt | Oui, avant premier commit | **Clos** |
| `ECART-003` | Le document prévalent portait le statut « soumis à validation finale » | Non | **Clos** |
| `ECART-004` | Registre `DEC-001` à `DEC-417` absent du corpus | Oui, pour la clôture de `US002` | **Clos** |
| `ECART-005` | Schéma CSV initial attendu au LOT 0 alors que le schéma définitif reste ouvert | Non | Ouvert |
| `ECART-006` | Contenu de `.env.example` dépendant du LOT 1 | Non | **Clos** |
| `ECART-007` | 12 risques du cahier §33 sans identifiant | Non | **Clos** |
| `ECART-008` | Aucune séquence pour les écarts et les dépendances | Non | **Clos** |
| `ECART-009` | Identité Git personnelle sur un projet interne | Non | **Accepté** |
| `ECART-010` | Traçabilité GitHub non mise en place | Non pour `G0`, prérequis du LOT 1 | **Clos** |
| `ECART-011` | Cinq questions absentes de la plage `QO-072` à `QO-105` | Non | **Accepté** |
| `ECART-012` | La valeur `intercontract` est imposée à une direction générale, faute de troisième valeur. **Instruit en `T5`** : le coût des deux options est mesuré, la décision revient à Léa | Non | **Ouvert, instruit** |
| `ECART-013` | Les tâches communes aux deux parcours du prototype portent des identifiants différents | Non | Ouvert |
| `ECART-014` | Le prototype emploie « Représentant de cercle » là où les documents validés emploient « Booster » | Non | Ouvert |
| `ECART-015` | Le prototype ne fournit ni descriptions de cercles ni liens internes, contrairement à ce qu'annonce le cahier §2.2 | Non | Ouvert |
| `ECART-016` | La documentation de clôture du LOT 0 affirme que les commits sont locaux alors qu'ils sont poussés sur GitHub | Non | **Clos** |
| `ECART-017` | La documentation du LOT 1 est restée dans son état d'avant l'ouverture | Non | **Clos** |
| `ECART-018` | La fiche du LOT 1 annonce 8 contrôles d'intégration là où le cahier §23.1 en énumère 11 | Non pour `G1`, structurant pour `T6` | **Clos** |
| `ECART-019` | La passation annonce 9 placeholders `CHANGE_ME_*` dans `.env.example`, il y en a 7 | Non | **Clos** |
| `ECART-020` | La fiche du LOT 1 rattache `T5` à la story `US003`, dont la page de statut ne complète aucun critère | Non pour `G1`, structurant pour la traçabilité | **Clos** |
| `ECART-021` | Quatre nombres du corpus ne sont pas dérivés de leur source : tests, masquage, commits, lignes, et le prochain identifiant de décision | Non | **Clos** |
| `ECART-022` | Quatre affirmations du corpus non dérivées de leur source, **et un fichier de configuration qui déclare deux fois la même variable** | Non pour `G1` | **Clos** |
| `ECART-023` | La fiche du LOT 1 énumère **six** des **sept** séparations du cahier §22.2, et importe dans `T8` deux exigences des LOTS 11 et 13 | Non pour `G1` | **Clos** |
| `ECART-024` | Deux contrôles affirmaient un état que la mesure contredit — l'avertissement de `make destroy` et le contrôle de page — tous deux nés d'un environnement unique | Non pour `G1` | **Clos** |
| `ECART-025` | La bande de ports de la recette a été choisie sur une mesure de ce qui **écoutait**, non de ce qui était **déclaré** : un projet tiers arrêté réclamait déjà `8080` | Non pour `G1` | **Clos** |
| `ECART-026` | Les conventions Git prescrivaient une stratégie de fusion que la protection de branche **interdisait** : deux règles justes séparément, incompatibles ensemble | Non pour `G1`, **bloquant pour `G2`** | **Clos** |
| `ECART-027` | Trois tests d'intégration recopiaient la révision de tête d'Alembic au lieu de la dériver, et sont devenus faux à la première migration du LOT 2 | Non | **Clos** |
| `ECART-028` | Le modèle place les domaines e-mail autorisés à **deux endroits** : catégorie de `platform_setting` au §5.2, et table dédiée au §5.4 | Non | **Clos** |
| `ECART-029` | L'index simple du §25.1 **ne satisfait pas** l'unicité insensible à la casse exigée par le §6.1 | Non pour `G2`, **le serait pour `G3`** | **Clos** |
| `ECART-030` | Le diagramme du §24.1 montre **cinq** états d'appartenance là où le §6.2 en déclare **quatre** : il y ajoute `anonymized` | Non | **Clos** |
| `ECART-031` | Le §8.4 exige « un bureau **publié** avec un à trois responsables actifs », mais le §8.3 ne déclare **aucun état de publication** sur `office` | Non pour `G2`, **à instruire avant le LOT 6** | **Ouvert** |
| `ECART-032` | Le backlog interdit « aucune **responsabilité métier** active dans plusieurs entités », là où le cahier, la matrice **et** le modèle restreignent tous les trois au seul **Booster** | Non — le cahier prévaut, le livrable est conforme | **Ouvert** |
| `ECART-033` | `make ports` concaténait les deux flux de sortie de Compose puis parsait le tout en **JSON** : le moindre avertissement le cassait, et la trace ne disait pas que la cause était un avertissement | Non — détecté avant toute conséquence | **Clos** |
| `ECART-034` | La fiche du lot annonçait « le cahier exige une limitation, **sans donner de seuil** » : le §20.2 en énumère **six**. Et les cinq variables de seuil de `.env.example` ne sont **consommées par personne** depuis le LOT 0 | Non — détecté avant d'inventer une valeur | **Clos** pour la fiche, **signalé** pour les variables |

**Prochain identifiant libre : `ECART-035`.**

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
| Résolution | **Traité** en sous-étape S6 : schéma livré en version `1.0-initiale`, statut « initial » inscrit en tête du document. `QO-096` demeure **ouverte** et n'est pas déclarée close. L'écart reste ouvert jusqu'à la livraison du schéma définitif. |

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
| Résolution | **Clos** le 28 juillet 2026, sous-étape `T3`. `.env.example` passe en **v1.0**. La sous-étape `T2` avait montré que les 74 variables du LOT 0 couvraient exactement les besoins de Compose ; `T3` y ajoute la seule variable manquante, **`APP_REVISION`**, exposée par `/health/version` et par le label OCI `revision` de `DEC-445`. Les 7 variables en `CHANGE_ME` sont inchangées, et `DEC-461` en génère cinq localement. |

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
| Résolution | **Clos** le 27 juillet 2026, en sous-étape `T0`, par `DEC-449`. `gh` 2.96.0 installé dans `~/.local/bin` — Homebrew inutilisable, ses répertoires appartenant à l'utilisateur `admin` — et authentifié par Jonathan. **Livré :** 13 étiquettes conformes en nom et couleur, 15 milestones `G0` à `G14` avec `G0` fermée, l'epic `#1` et les 8 stories `#2` à `#9` toutes rattachées à `G1`, et la protection de `main` et `develop`. Le rejet du push direct est **prouvé** (`GH006`), avec témoin positif sur branche non protégée. `QO-107` et `QO-108` closes. |
| Reste ouvert par ailleurs | Les 104 issues des LOTS 2 à 14 ne sont **pas** créées : elles le seront lot par lot, quand chaque fiche existera. Les familles d'étiquettes complémentaires de `QO-106` ne sont pas créées, n'étant pas prescrites. Les 9 étiquettes GitHub par défaut subsistent. |

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

## `ECART-012` — La valeur `intercontrat` est imposée à une direction générale

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S6, en construisant le jeu d'exemple |
| Source | Modèle de données §6.5 : `professional_status_assignment.status` vaut **`mission` ou `intercontract`**, une seule situation active par appartenance.<br>**Rectifié le 19/08/2026, LOT 2 sous-étape `T5`** : ce champ citait `intercontrat`, la forme **française**. La mesure sépare nettement les deux usages du modèle — `intercontract` aux lignes 352, 361 et 770, **toujours entre accents graves**, donc là où il spécifie une **valeur** ; `intercontrat` aux lignes 48, 69, 353, 915 et 1710, en **prose**. Quelqu'un implémentant depuis cet écart plutôt que depuis le modèle aurait stocké une valeur que rien ne reconnaît. |
| Constat | Le champ de situation professionnelle est obligatoire pour **toute** personne et n'offre que deux valeurs. Pour une catégorie `dg`, ou pour une personne dont l'activité n'est pas une mission client, `intercontrat` est la seule valeur possible. Or ce terme désigne, dans le langage métier, un consultant en attente de mission. |
| Impact | Aucun impact technique : les contraintes restent cohérentes, `intercontrat` interdisant un client actif. L'impact est **fonctionnel et éditorial** : le trombinoscope afficherait « intercontrat » sur une fiche de direction générale, ce qui serait lu comme une erreur par les collaborateurs. |
| Bloquant | Non |
| Recommandation | Ne pas modifier le modèle de données, qui est validé. Deux pistes à arbitrer avec Léa : soit l'affichage du statut est conditionné par la catégorie professionnelle, la situation restant `intercontrat` en base ; soit une troisième valeur est ajoutée à l'énumération, ce qui exige une décision et une nouvelle version du modèle. La première piste est moins coûteuse et ne touche pas au socle. |
| Résolution | **Ouvert — INSTRUIT le 19/08/2026 en `T5`, et il attend Léa.**<br>`professional_status_assignment` existe désormais, avec les **deux** valeurs que le modèle validé écrit. `T5` n'a pas tranché, et ne devait pas : **Léa décide du produit**.<br>**Ce que `T5` apporte à la décision, c'est le COÛT mesuré de chaque option** — et il est faible dans les deux cas, ce qui n'était pas connu quand l'écart a été ouvert :<br>• **conditionner l'affichage** par la catégorie professionnelle, la valeur restant `intercontract` en base : **aucune modification du socle**, tout se joue au LOT 5 avec le trombinoscope ;<br>• **ajouter une troisième valeur** : **une migration d'UNE LIGNE**, parce que `DEC-499` a choisi une contrainte de vérification et non un type `enum` natif. C'était précisément le motif de ce choix, et il se réalise ici.<br>**Le coût n'est donc pas ce qui doit départager les deux options** : c'est un choix de produit, et il revient à Léa.<br>**MISE À JOUR DU 20/08/2026.** Jonathan prend le sujet en main **directement auprès de Léa**, sans note écrite préalable — son choix explicite parmi trois options proposées. Le coût des deux issues reste mesuré depuis `T5` et consigné ci-dessus ; il est donc disponible s'il en a besoin. **L'écart reste OUVERT jusqu'à la réponse de Léa**, et sa réponse sera consignée ici. Échéance inchangée : **avant le LOT 5**. |

## `ECART-013` — Identifiants de tâches non stables entre les deux parcours

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S7 |
| Source | Relevé des parcours du prototype, contre `DATA-007`, cahier §10.4 et `MVP-L07-US007` |
| Constat | Cinq tâches ont un libellé **identique** dans les deux parcours, mais des identifiants **différents** : `ic_a1` contre `m_a1`, `ic_m1_1` contre `m_m1_5`, et ainsi de suite. |
| Impact | Reprendre cette numérotation ferait échouer une exigence centrale du LOT 7 : lors d'un changement mission ↔ intercontrat, les tâches communes déjà terminées doivent être **conservées** grâce à un identifiant fonctionnel immuable. Avec des identifiants distincts, un collaborateur perdrait la complétion de ces cinq tâches. |
| Bloquant | Non pour `G0`. **Structurant pour le LOT 7.** |
| Recommandation | Au LOT 7, attribuer à chaque tâche commune **un seul** code de référence partagé dans `onboarding_task_reference`, réutilisé par les deux modèles. Ne pas transposer la numérotation du prototype. |
| Résolution | Ouvert. Traitement au LOT 7, story `MVP-L07-US003`. |

## `ECART-014` — Divergence de terminologie sur le responsable de cercle

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S7 |
| Source | Relevé des parcours du prototype, contre la matrice §3 et `RIGHTS-007` |
| Constat | Le prototype emploie « **Représentant de cercle** », trois fois dans les parcours d'onboarding. Le terme « **Booster** », retenu par tous les documents validés, n'apparaît **nulle part** dans le prototype. |
| Impact | Faible techniquement, réel pour l'utilisateur : deux vocabulaires concurrents désigneraient la même responsabilité, dans un produit dont la finalité est précisément de faire comprendre l'organisation. |
| Bloquant | Non |
| Recommandation | Retenir la terminologie validée, « Booster », et corriger les libellés relevés lors de la relecture. Si Tess ou Léa préfèrent « Représentant de cercle », c'est un changement de vocabulaire à arbitrer formellement, avec mise à jour de la matrice et du modèle. |
| Résolution | Ouvert. À trancher lors de la relecture de l'inventaire, au plus tard au LOT 6. |

## `ECART-015` — Le prototype ne fournit ni descriptions de cercles ni liens internes

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S7 |
| Source | Cahier des charges §2.2 et §12.1, qui annoncent que le prototype fournit « textes de présentation, descriptions de cercles, descriptions de bureaux et liens internes » |
| Constat | Après retrait des chaînes Base64 et analyse des 194 566 caractères de texte réel : les descriptions de **bureaux** existent bien, au nombre de trois. En revanche **aucune description de cercle** n'existe, les huit cercles ne portant qu'une couleur et une variante d'icône ; et **aucun lien interne** n'existe, les sept URL du fichier étant quatre dépendances CDN, une police web et deux exemples fictifs placés dans des commentaires. Le terme « Hub » n'apparaît pas une seule fois. |
| Impact | Le LOT 6 devra **rédiger** les huit descriptions de cercle au lieu de les reprendre, et les trois liens internes devront être fournis par Léa ou Tess. Aucun impact sur le LOT 0. |
| Bloquant | Non |
| Recommandation | Ne pas attendre du prototype ce qu'il ne contient pas. Prévoir la rédaction des huit descriptions de cercle dans la charge du LOT 6, et la saisie des liens en configuration d'entité. |
| Résolution | Ouvert. Documenté dans l'inventaire et dans le document des liens internes. |

## `ECART-016` — La documentation de clôture affirme à tort que les commits sont locaux

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, prise en charge par l'agent suivant, avant ouverture du LOT 1 |
| Source | `CLAUDE.md` §1 et §10 ; `docs/operations/controles-sortie-lot-0.md` §9 |
| Constat | Trois emplacements affirment que les commits du LOT 0 sont **locaux** et qu'aucun envoi vers GitHub n'a été effectué. Le journal de références `.git/logs/refs/remotes/origin/main` enregistre `0000000… → 28ecc90 … update by push` à l'horodatage `1785154897 +0200`, soit le **27 juillet 2026 à 14:21:37**, 74 secondes après le dernier commit. `git ls-remote --heads --tags origin` confirme côté serveur que `origin` porte `refs/heads/main` à `28ecc90`. `main` est à `0 ahead / 0 behind` d'`origin/main`. **Les 11 commits sont publiés.** |
| Impact | Deux impacts distincts. **Opérationnel :** la convention de rapport du projet impose de fournir la commande de retour arrière de chaque sous-étape, `git reset --hard <commit précédent>`. Sur un commit déjà poussé, cette commande n'est pas applicable — la remise en cohérence exigerait un push forcé, interdit par les conventions Git §6. Un agent se fiant à la passation proposerait un retour arrière irréalisable. **Traçabilité :** l'affirmation figurait dans un document de contrôle de sortie, c'est-à-dire dans une preuve de porte. |
| Cause | L'affirmation était **exacte à sa rédaction**, en sous-étape S8, commit `7d8aa89`. Le push est intervenu après. Ni `CLAUDE.md`, rédigé au commit suivant, ni le document de contrôles n'ont été relus après l'envoi. Défaut de mise à jour, non défaut de contrôle. |
| Bloquant | Non. La porte `G0` reste valablement franchie : le contenu poussé est celui qui a été validé, et les contrôles de sortie eux-mêmes demeurent exacts. |
| Recommandation | Rectifier les trois emplacements, et inscrire dans la passation la règle de vérification préalable `git status -sb` avant d'annoncer tout point de retour. |
| Résolution | **Clos** le 27 juillet 2026. `CLAUDE.md` §1 et §10 et `controles-sortie-lot-0.md` §9 rectifiés, preuves de push versées au document de contrôles. |
| Constat associé | Le push a réussi **en poussée directe sur `main`**, ce qui prouve que la protection exigée par `DEC-429` n'est pas en place. Suivi par `ECART-010`, `QO-107` et `QO-108`, prérequis du LOT 1. |

## `ECART-017` — La documentation du LOT 1 est restée dans son état d'avant l'ouverture

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, prise en charge de la sous-étape `T1` |
| Source | `docs/operations/fiche-lot-1.md` L3 à L7 ; `docs/README.md` §8, ligne de la sous-étape `T0` |
| Constat | Deux inexactitudes, de même origine. **(a)** La fiche du LOT 1 portait toujours en tête l'avertissement « ⚠️ **LE LOT 1 N'EST PAS OUVERT** », alors que `DEC-450` l'a ouvert le 27/07/2026 et que `docs/README.md` §8 est intitulé « Avancement du LOT 1 — **lot ouvert** ». Deux documents du même corpus se contredisaient frontalement. **(b)** L'index attribuait à `T0` les décisions `DEC-439`–`DEC-447`, alors que `T0` a produit `DEC-439` à `DEC-449` — le compte rendu de `T0` §5 en fait foi, et `DEC-449` y remplace `DEC-448`. |
| Impact | Faible sur le travail, réel sur la confiance dans le corpus. La fiche est le premier document que lit un agent prenant le lot en charge : un avertissement de non-ouverture en tête est exactement l'information qu'il applique sans la vérifier. Le bornage `DEC-439`–`DEC-447` masquait deux décisions dont l'une, `DEC-449`, décrit la mise en place GitHub. |
| Cause | Défaut de mise à jour, non défaut de contrôle. La fiche a été rédigée **avant** l'ouverture et n'a pas été relue après `DEC-450` ; le bornage de l'index a été écrit alors que `T0` comptait sept arbitrages, avant l'ajout de `DEC-448` et `DEC-449`. Même classe que `ECART-016`. |
| Bloquant | Non |
| Recommandation | Rectifier les deux emplacements dans la pull request de `T1`, et non plus tard : un corpus qui se contredit perd sa valeur de source de vérité. |
| Résolution | **Clos** le 27 juillet 2026. Bandeau de la fiche remplacé par l'état réel du lot ; bornage de l'index porté à `DEC-439`–`DEC-449`. Arbitrage de Jonathan : correction dans la pull request de `T1`. |

## `ECART-018` — La fiche du LOT 1 annonce 8 contrôles d'intégration, le cahier en énumère 11

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, prise en charge de la sous-étape `T1` |
| Source | `docs/operations/fiche-lot-1.md` §3 sous-étape `T6`, et §4.1 ; cahier des charges §23.1 |
| Constat | La fiche annonce « **8 contrôles** du cahier §23.1 » à deux endroits. Le cahier §23.1 en énumère **11** : formatage, lint, typage, tests unitaires, tests d'intégration PostgreSQL, tests API, tests frontend, contrôle Alembic, détection de secrets, audit de dépendances, construction des images. La roadmap et le backlog en listent, eux, **7** — formatage, lint, types, tests, migrations, secrets, vulnérabilités. **Aucune source du corpus ne donne 8.** |
| Impact | **Structurant pour `T6`.** Le nombre annoncé détermine ce que la CI doit exécuter et ce que la porte `G1` contrôlera. Trois contrôles du cahier — tests API, tests frontend, construction des images — n'apparaissent dans aucun des deux décomptes inférieurs et auraient pu être omis. Aucun impact sur `T1`, qui ne crée pas de workflow. |
| Cause | Défaut de contrôle, pas défaut de livrable : le nombre n'a pas été obtenu par comptage dans la source. **Même classe exactement que le défaut `B-5` de `T0`**, où la fiche annonçait 7 garde-fous de démarrage là où la politique de configuration en définit 11, et retenait qui plus est les mauvais. |
| Bloquant | Non pour `G1`. Aurait été bloquant pour la validité de `T6`. |
| Recommandation | Porter le nombre à 11 dans la fiche et **énumérer les onze**, plutôt que d'en donner le seul décompte : c'est l'énumération, non le nombre, qui empêche une omission. Rappeler que la roadmap et le backlog en listent 7, et que le cahier prévaut (règle de préséance). |
| Résolution | **Clos** le 27 juillet 2026. Fiche §3 et §4.1 rectifiées, les onze contrôles énumérés depuis le cahier. Arbitrage de Jonathan : correction dans la pull request de `T1`. |

## `ECART-019` — Le nombre de placeholders `CHANGE_ME_*` annoncé ne correspond pas au fichier

| Champ | Valeur |
|---|---|
| Constaté le | 28 juillet 2026, sous-étape `T2` du LOT 1 |
| Source | `CLAUDE.md` §5.6 ; `.env.example` |
| Constat | La passation annonce « 74 variables, aucun secret, **9** placeholders `CHANGE_ME_*` ». Le fichier contient **9 occurrences de la chaîne** mais seulement **7 variables** dont la valeur est un `CHANGE_ME_*` : `APP_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `IMPORT_SOURCE_RETENTION_DAYS`, `UPTIME_KUMA_PUSH_URL`. Les deux occurrences restantes sont des **commentaires** — le mode d'emploi en tête de fichier, et la description du garde-fou en §352. Le nombre de variables est bien de 74, il est exact. |
| Impact | Faible mais réel, et il n'est **pas cosmétique**. Le premier des 11 garde-fous de démarrage exige qu'aucune variable ne vaille encore `CHANGE_ME_*` ; son test, à écrire en `T3`, doit énumérer les variables réellement concernées. Un test bâti sur « il y en a 9 » chercherait deux variables qui n'existent pas, ou compterait des commentaires. |
| Cause | **Défaut de contrôle, pas défaut de livrable** : le nombre a été obtenu par un `grep -c` sur la chaîne, et non sur les affectations. Même classe que `ECART-018` — 8 contrôles annoncés contre 11 — et que le défaut `B-5` de `T0`. Le comptage a été refait ici sur le motif `^[A-Z_][A-Z0-9_]*=CHANGE_ME`. |
| Bloquant | Non |
| Recommandation | Rectifier la passation, et **dériver le nombre du fichier** plutôt que de le recopier. En `T3`, le test du garde-fou doit lire la liste des variables `CHANGE_ME_*` depuis `.env.example` au lieu d'en coder le nombre en dur : c'est la seule forme qui ne se périme pas. |
| Résolution | **Clos** le 28 juillet 2026. `CLAUDE.md` §5.6 rectifié à 7, avec la liste. La distinction entre les 7 variables et les 2 mentions en commentaire est explicitée. |

## `ECART-020` — La fiche du LOT 1 rattache `T5` à une story que la page de statut ne complète pas

| Champ | Valeur |
|---|---|
| Constaté le | 28 juillet 2026, à la prise en charge de la sous-étape `T5` du LOT 1 |
| Source | [`fiche-lot-1.md`](../operations/fiche-lot-1.md) §3 ; backlog `EPIC MVP-L01` ; roadmap LOT 1 |
| Constat | La fiche §3 rattache `T5` aux stories **`MVP-L01-US002` et `MVP-L01-US003`**, dont les issues `#3` et `#4` étaient closes. Or le critère de `US003` est littéralement « chaque endpoint retourne un statut explicite ; readiness vérifie les dépendances nécessaires ; la version correspond au build » : il est **intégralement satisfait depuis `T3`**, et la page de statut n'y ajoute rien. La « page web de statut » ne figure nulle part dans un critère de story : elle appartient à la **démonstration attendue** du LOT 1 dans la roadmap. Le rattachement à `US002` est en revanche fondé, son critère nommant `web` parmi les huit services devant démarrer avec une commande — or le conteneur démarrait en `sleep infinity` et le navigateur recevait un **502**. La fiche §6 ne rattache d'ailleurs sa ligne « Frontend » qu'à **`US002`** : la fiche se contredit d'un paragraphe à l'autre. |
| Impact | Faible sur le code, réel sur la traçabilité. Rattacher un travail à une story déjà satisfaite dilue la preuve : à la porte `G1`, on ne saurait plus dire quel critère la page démontre. C'est aussi ce qui aurait conduit à rouvrir une issue sans motif. |
| Cause | La fiche a été rédigée avant `T3` : à ce moment-là, les endpoints de santé et leur consommation par une page semblaient un même travail. La séparation est apparue quand `T3` a livré les trois endpoints, complets et éprouvés, sans aucun écran. |
| Bloquant | Non pour `G1`, structurant pour la traçabilité de la démonstration |
| Recommandation | Rattacher `T5` à **`US002` seule**, cohérent avec la fiche §6, et tracer la page de statut comme élément 2 de la démonstration attendue. Laisser `#4` close. |
| Résolution | **Clos** le 28 juillet 2026. Arbitrage de Jonathan, rendu sur les trois options présentées : **rouvrir l'issue `#3`**, livrer `T5` sous `US002`, la refermer à la fusion. `#4` reste close. La fiche §3 est rectifiée. |

## `ECART-021` — Quatre nombres du corpus ne sont pas dérivés de leur source

| Champ | Valeur |
|---|---|
| Constaté le | 28 juillet 2026, sous-étape `T5` du LOT 1 |
| Source | [`compte-rendu-t4-lot-1.md`](../operations/compte-rendu-t4-lot-1.md) §2 et §6 ; [`docs/README.md`](../README.md) §8 ; `CLAUDE.md` §1 ; [`registre-decisions.md`](registre-decisions.md) |
| Constat | **1. Nombre de tests.** Le compte rendu de `T4` §6 et `docs/README.md` §8 annoncent **131 tests**. `pytest` en collecte **139**, prouvé par `pytest -m integration` : « 8 selected, 131 deselected ». Le compte des **unitaires** a été pris pour le total ; il manque les 8 tests d'intégration. `CLAUDE.md` §1 — « 139 : 131 unitaires, 8 d'intégration » — est le seul juste. Les **3 tests Vitest** n'étaient comptés nulle part.<br>**2. Tests de masquage.** Le compte rendu de `T4` §1 et §2 et la fiche §3 annoncent « **30 tests** » de masquage et de format. `packages/observabilite` collecte **52 cas** — 16 en journalisation, 36 en masquage — pour **21 fonctions**. Aucune lecture ne donne 30.<br>**3. Commits et lignes.** `CLAUDE.md` §1 annonce `develop` à **19 commits**, en avance de **6**, et **30 487 lignes**. La mesure donne **20**, **+7** et **30 566**. Recalculé au commit précédent `0178b43`, on retrouve exactement 30 487 : le document se décrit dans son état **d'avant son propre commit**. Même classe que le constat `B-3` de `T0`.<br>**4. Prochain identifiant de décision.** Le registre des décisions portait « **Prochain identifiant libre : `DEC-451`** » alors que `DEC-469` était en usage — **19 décisions de retard**. Le marqueur, ainsi que le bloc « ce que `T1` a délibérément écarté », étaient restés à la fin de la section 1, après le tableau de `T4`, les sous-étapes suivantes ayant inséré leurs tableaux avant eux. |
| Impact | Faible pour les trois premiers, **réel pour le quatrième** : un agent qui se fie au registre plutôt qu'à l'index de `docs/README.md` créerait `DEC-451`, en collision avec 19 décisions existantes. Un identifiant réutilisé est précisément ce que la règle de tenue interdit. Pour les trois premiers, l'effet est la confiance dans le corpus : un décompte de tests faux empêche de voir qu'une suite a régressé. |
| Cause | Même classe que `ECART-018` et `ECART-019` : des nombres **recopiés** plutôt que dérivés de la source. Le quatrième s'y ajoute d'un mécanisme différent — un bloc de fin de section qui n'a pas suivi l'insertion des sections suivantes. |
| Bloquant | Non |
| Recommandation | Corriger les quatre. Et pour ne pas les recréer : **`T6` doit ajouter à la CI un contrôle qui dérive ces nombres de la source et échoue s'ils divergent** de ce que la documentation affirme. C'est le même garde-fou que celui recommandé pour les cinq empreintes SHA-256 par `ROAD-RSK-029` — un contrôle qui recalcule plutôt qu'un humain qui relit. |
| Résolution | **Clos** le 28 juillet 2026. Les quatre nombres sont rectifiés, le bloc de `T1` est replacé dans sa sous-étape, et le marqueur d'identifiant libre est porté à `DEC-474`. La recommandation de contrôle de CI est reportée à `T6`. |

## `ECART-022` — Quatre affirmations non dérivées de leur source, et une variable déclarée deux fois

| Champ | Valeur |
|---|---|
| Constaté le | 29 juillet 2026, prise en charge de la sous-étape `T7` du LOT 1 |
| Source | `CLAUDE.md` §1, §5.4 et §9.2 ; [`.env.example`](../../.env.example) ; cahier des charges §23.2 |
| Constat | **Cinq constats, dont quatre partagent une propriété : une affirmation que la source contredit.**<br>**1. `.env.example` déclarait `APP_REVISION` deux fois**, aux lignes 53 et 357, dans des blocs **strictement identiques** — même commentaire, même valeur, vérifié octet pour octet. Le fichier comptait donc **78 affectations pour 77 noms distincts**, là où `CLAUDE.md` §5.4 annonce « 78 variables ». La seconde déclaration se trouvait de surcroît dans la section « FRONTEND », où elle n'a rien à faire : elle n'est pas préfixée `VITE_` et n'est pas exposée au navigateur.<br>**2. `CLAUDE.md` §1 annonce « 4 YAML ».** Le dépôt en portait **6** : 4 `.yml` et 2 `.yaml`. Le compte n'avait retenu qu'une des deux extensions.<br>**3. `CLAUDE.md` §9.2 affirme « Les 3 `Dockerfile` sont mono-étape ».** Mesure : `api` et `worker` en comptaient **deux `FROM`** chacun, `web` un seul. Le fond était juste — aucun n'avait de séparation construction/exécution — l'affirmation non.<br>**4. Le cahier §23.2 exige qu'une fusion sur `develop` « déploie la recette locale ».** Mesure du 29/07/2026 : `gh api repos/.../actions/runners` renvoie **`total_count: 0`**, il n'existe aucun exécuteur auto-hébergé, et un exécuteur GitHub ne peut pas atteindre le Mac de Jonathan. Ce volet du §23.2 **n'est pas atteignable** par l'intégration continue dans le montage actuel.<br>**5. Conséquence mesurée du constat 1, et la plus sérieuse.** `make env` est **idempotent** : si `.env` existe, il n'y touche pas. Une variable ajoutée à `.env.example` **après** la première création du `.env` n'y arrive donc jamais. Le `.env` de cette machine comptait **74 affectations contre 78** : manquaient `APP_REVISION`, ajoutée en `T3`, ainsi que `LOG_MAX_SIZE` et `LOG_MAX_FILES`, ajoutées en `T4`. |
| Impact | **Le cinquième constat a un effet réel et mesuré.** Compose substituait une **chaîne vide** à `${APP_REVISION}`, faute de valeur par défaut : l'image de développement a été construite avec `APP_REVISION=""`, et `/health/version` renvoyait une révision vide. `LOG_MAX_SIZE` et `LOG_MAX_FILES` ont, elles, un défaut dans Compose — `${LOG_MAX_SIZE:-10m}` : la rotation de `T4` fonctionnait donc **par le défaut, pas par `.env`**, ce qui est correct mais n'est pas ce que le compte rendu de `T4` laissait entendre. Le quatrième constat porte sur une exigence du cahier qu'il faut déclarer non couverte plutôt que laisser croire. Les trois premiers n'ont aucun effet technique, et l'effet réel est la confiance dans le corpus. |
| Cause | **Une seule pour les quatre premiers, et c'est la classe que `ECART-021` avait déjà nommée** : un nombre ou une affirmation **recopiés** au lieu d'être dérivés de la source. Le cinquième a une cause différente et instructive : une cible idempotente **par conception** ne peut pas réconcilier, et rien ne le vérifiait. `make docs-check`, posé en `T6`, couvre les empreintes et les séquences d'identifiants — pas les nombres cités en prose, ce que le compte rendu de `T6` §3 disait explicitement. |
| Bloquant | Non pour `G1` |
| Recommandation | Corriger les cinq. Et surtout **poser le contrôle qui manque** : `make env-check` compare les noms déclarés par `.env.example` à ceux de `.env`, nomme les manquants, et **refuse aussi tout doublon dans le modèle**. C'est la parade générale — `make env` ne peut pas corriger, mais quelque chose doit s'en apercevoir. |
| Résolution | **Clos** le 29 juillet 2026, sous-étape `T7`. Le doublon est retiré, `.env.example` passe en **v1.1** avec 77 variables et 77 noms distincts. Les trois variables manquantes sont ajoutées au `.env` local, valeurs reprises du modèle, aucune n'étant un secret. Compose emploie désormais des valeurs par défaut explicites — `${APP_VERSION:-0.0.0-dev}`, `${APP_REVISION:-inconnue}` — pour qu'une variable absente dégrade honnêtement au lieu de valoir la chaîne vide. **`make env-check` est créée**, appelée par `make env` et par `make check`. Les affirmations de `CLAUDE.md` §1 et §9.2 sont rectifiées. Le volet non atteignable du §23.2 est déclaré dans l'en-tête de [`images.yml`](../../.github/workflows/images.yml) et dans le compte rendu de `T7` : la recette de `T8` sera lancée à la main. |

## `ECART-023` — La fiche du LOT 1 énumère six des sept séparations du cahier §22.2, et importe deux exigences d'autres lots

| Champ | Valeur |
|---|---|
| Constaté le | 29 juillet 2026, prise en charge de la sous-étape `T8` du LOT 1 |
| Source | [`fiche-lot-1.md`](../operations/fiche-lot-1.md) §3, ligne `T8` ; cahier des charges §16.5, §22.2 ; backlog `MVP-L01-US002`, `MVP-L11-US003` ; cahier LOT 13, critères de sortie |
| Constat | **Trois constats de la même famille : le critère écrit dans la fiche ne correspond pas à sa source.**<br>**1. Une énumération tronquée.** Le cahier §22.2 énumère **sept** séparations, littéralement : « projet Docker distinct ; base PostgreSQL distincte ; bucket MinIO distinct ; volumes distincts ; secrets distincts ; réseau distinct ; ports distincts. » Le critère de la fiche pour `T8` en nomme **six** : « Volumes, base, bucket, réseau, ports et secrets distincts du développement ». **« Projet Docker distinct » manque** — et c'est précisément celle qui **produit** les volumes et le réseau distincts, Compose les préfixant du nom de projet.<br>**2. « Mailpit exclusif » n'est pas une exigence du LOT 1.** Le cahier §16.5 dit « Mailpit en développement **et recette** » : c'est cela que le LOT 1 doit satisfaire. La formule « Mailpit est **exclusif** en recette » est celle de `MVP-L11-US003`, donc du **LOT 11** ; et « aucun e-mail réel ne part de la recette » est un **critère de sortie du LOT 13**. La fiche importe donc dans `T8` deux exigences de lots à venir.<br>**3. Le critère d'acceptation du backlog pour `US002` ne parle pas de recette du tout** : « PostgreSQL, Redis, MinIO, Mailpit, Caddy, web, API et worker démarrent avec une commande ; les volumes survivent au redémarrage », satisfait depuis `T2`. Le mandat de `T8` vient du cahier — « Docker Compose pour développement **et recette** » — et de la fiche, pas de la story. |
| Impact | **Le premier constat est le plus sérieux, et il aurait été silencieux.** Un agent qui aurait compté sur la fiche aurait livré six séparations et déclaré le critère satisfait. Les deux suivants n'ont pas d'impact sur le livrable mais sur ce qu'on **affirme** : présenter comme prouvée au LOT 1 une exigence du LOT 11 ou du LOT 13 laisserait croire qu'elle est traitée alors qu'elle ne le sera que plus tard. |
| Cause | **La même que `ECART-018`**, où la fiche annonçait « 8 contrôles de CI » là où le cahier en énumère **11** : une énumération recopiée depuis la source au lieu d'être comptée sur elle. Pour les constats 2 et 3, une formule empruntée à un autre lot sans que sa provenance soit vérifiée. |
| Bloquant | Non pour `G1` |
| Recommandation | Compter les sept sur le cahier, jamais sur la fiche. Et **poser le contrôle qui les compte** : `make separations-check` annonce « 7 séparations attendues, N vérifiées » et échoue si les deux nombres diffèrent — un contrôle qui n'énumère pas ce qu'il examine peut toujours n'en avoir examiné qu'une partie. Dire explicitement, dans le compte rendu, ce que le LOT 1 prouve de Mailpit et ce qui appartient aux LOTS 11 et 13. |
| Résolution | **Clos** le 29 juillet 2026, sous-étape `T8`. Les **sept** séparations sont prouvées sur l'état réel des deux environnements — 57 contrôles, 0 échec — et le vérificateur compte les séparations examinées. Le critère de la fiche §3 est rectifié pour nommer les sept et pour renvoyer Mailpit à sa source réelle. Ce que `T8` prouve de Mailpit est énoncé sans extrapolation : aucun fournisseur réel configuré, et un e-mail émis par la recette reste dans **sa** capture sans que celle du développement bouge — l'absence de sortie réelle au sens du LOT 13 et la story `MVP-L11-US003` restent **non couvertes**, et c'est dit. |

## `ECART-024` — Deux contrôles affirmaient un état que la mesure contredit, tous deux nés d'un environnement unique

| Champ | Valeur |
|---|---|
| Constaté le | 29 juillet 2026, sous-étape `T9` du LOT 1 |
| Source | `Makefile`, cible `destroy` (écrite en `T2`, paramétrée en `T8`) ; `infra/scripts/verifier-page-statut.sh` (écrit en `T5`) |
| Constat | **Deux constats, une seule propriété commune : un contrôle écrit quand il n'existait qu'UN environnement, devenu faux quand un second est apparu.**<br>**1. `make destroy` annonçait une conséquence inexistante.** Son message avertissait, quel que soit l'environnement : « Sa perte obligera à réapprouver la racine dans le trousseau macOS, ce qui demande le mot de passe de Jonathan. » Mesure du 29/07/2026 sur les deux racines, qui sont distinctes : `security verify-cert` rend **code 0** pour `dev`, empreinte `c9a952a9…`, et **code 1** pour la recette, empreinte `fb8fbc2d…`. La racine de la recette **n'a jamais été approuvée** : l'avertissement était faux pour elle.<br>**2. `verifier-page-statut.sh` exigeait le comportement du serveur de développement.** Il demandait la référence `/src/main.tsx` dans l'index servi. Depuis `T8`, la recette sert l'artefact **bâti** — cible `execution`, `DEC-479` — dont l'index référence `/assets/index-<empreinte>.js` : `/src/main.tsx` n'y existe pas **par construction**. Mesuré : **2 contrôles sur 6 en échec sur une recette parfaitement saine**. |
| Impact | **Le premier porte sur la cible la plus destructive du dépôt, et son effet est pervers.** Un avertissement qui annonce une conséquence inexistante n'est pas seulement inutile : il apprend à l'opérateur à passer outre. Le jour où il porte sur `dev`, où la conséquence est **réelle** et coûte à Jonathan une réapprobation avec son mot de passe, il ne sera plus lu. Le second aurait fait échouer tout contrôle de page de la recette, et un contrôle qui échoue pour une raison étrangère à ce qu'il mesure finit désactivé — classe `T6-4` et `T7-4`. |
| Cause | **La même pour les deux, et elle est structurelle plutôt que négligente :** chacun a été écrit à une époque où il n'existait qu'un seul environnement, et il affirmait alors le vrai. `T8` a créé le second sans que ces deux affirmations soient revisitées. C'est la classe de `ECART-021` et `ECART-022` — une affirmation que sa source contredit — mais avec une nuance : ici la source n'a pas changé, **le monde a changé autour de l'affirmation**. |
| Bloquant | Non pour `G1` |
| Recommandation | Corriger les deux, et pour la même raison : **faire mesurer au lieu d'affirmer**. `destroy` interroge le trousseau et dit ce qu'il a mesuré — ou dit « indéterminé » quand il ne peut pas mesurer, plutôt que de trancher. Le contrôle de page **identifie la cible servie**, exige qu'elle soit l'une des deux formes connues, et applique les contrôles de cette forme — en **échouant** s'il n'en reconnaît aucune. Et une leçon plus large pour la suite : **quand une sous-étape ajoute un environnement, relire les contrôles qui n'en connaissaient qu'un.** |
| Résolution | **Clos** le 29 juillet 2026, sous-étape `T9`. `DEC-489` et `DEC-490`. Les deux corrections sont éprouvées par des témoins **dans les deux sens** : le message de `destroy` diffère réellement entre `dev` et la recette, mesure à l'appui, et le contrôle de page passe sur les deux environnements en nommant la cible servie — tout en **échouant** sur une origine qui ne sert pas la page, l'hôte de l'API, où il rend 2 échecs sur 6. |

## `ECART-025` — La bande de ports de la recette a été choisie sur une mesure de ce qui écoutait, non de ce qui était déclaré

| Champ | Valeur |
|---|---|
| Constaté le | 12 août 2026, **après la validation de la porte `G1`**, par l'exploitation réelle |
| Source | `DEC-487`, bande de ports de la recette ; sortie de `docker compose -p observatoire-ecom-studio start` |
| Constat | La bande de ports de la recette — `8080`, `8443`, `15432`, `16379`, `18025`, `19000`, `19001` — a été choisie en `T8` après avoir mesuré que ces ports étaient **libres**. La mesure employait `lsof -nP -iTCP -sTCP:LISTEN` : elle regardait ce qui **écoutait**.<br>**Le projet tiers `observatoire-ecom-studio` déclare `127.0.0.1:8080` depuis toujours.** Il était simplement **arrêté** au moment de la mesure — et un conteneur arrêté déclare ses ports sans en occuper aucun. À sa relance, le 12/08/2026 : `Bind for 127.0.0.1:8080 failed: port is already allocated`.<br>**La même mesure, refaite correctement, a révélé un SECOND conflit antérieur au projet** : `5432`, entre `onboarding-dev` et `ticket_master`, arrêté depuis quatre semaines et donc jamais manifesté. |
| Impact | **La recette et le projet tiers ne peuvent pas tourner en même temps.** L'effet est borné : `DEC-440` n'autorise de toute façon qu'un environnement à la fois, et le développement seul ne collisionne avec rien. Mais le symptôme est arrivé **sans avertissement**, et le message de Docker ne nomme pas le coupable — il dit qu'un port est pris, pas par qui. |
| Cause | **La mesure était juste à sa date ; la MÉTHODE était incomplète.** Elle répondait à « ce port est-il occupé maintenant ? » quand la question était « ce port sera-t-il disponible quand ce projet démarrera ? ». C'est la même famille que `ECART-024` — un contrôle juste au moment où il est écrit, faux quand l'état du monde autour de lui change — avec une variante : ici c'est un **état dormant** que la mesure ne voyait pas. |
| Bloquant | Non pour `G1`, qui était déjà validée. Aucun critère de sortie n'est remis en cause : les sept séparations du cahier §22.2 portent sur nos deux environnements, et elles restent prouvées |
| Recommandation | **Poser le contrôle qui manquait**, plutôt que de promettre plus d'attention. Arbitrage de Jonathan du 12/08/2026 : le contrôle est retenu, **et le déplacement du port de la recette ne l'est pas** — la collision reste, désormais visible. |
| Résolution | **Clos** le 12 août 2026 par `DEC-494`. `make ports` confronte désormais **deux sources** : les conteneurs existants, **arrêtés compris**, et la **configuration Compose assemblée** de nos environnements — indispensable, puisque `down` supprime les conteneurs et qu'un environnement arrêté ne déclare plus rien. Il **échoue** sur une collision entre deux de nos environnements — éprouvé par témoin, code 1 avec le port et les deux propriétaires nommés — et **rapporte visiblement** les collisions étrangères, dont les deux constatées. **La collision `8080` subsiste et est assumée** : elle est désormais annoncée avant d'être découverte. |

## `ECART-026` — Les conventions Git prescrivaient une stratégie de fusion que la protection de branche interdisait

| Champ | Valeur |
|---|---|
| Constaté le | 12 août 2026, **après la validation de la porte `G1`**, sur les conflits de la pull request `#33` |
| Source | [`conventions-git-et-versions.md`](../operations/conventions-git-et-versions.md) §2, tableau des réglages de protection, et §2.1, stratégie de fusion ; protection de branche de `main` et de `develop`, relevée par `gh api` |
| Constat | **Le document se contredit.** Sa ligne 94 pose « historique linéaire requis » comme réglage recommandé, au motif qu'il est « cohérent avec la fusion par squash ». Sa ligne 106 impose **`develop` → `main` : merge commit**, au motif de « conserver la traçabilité de l'ensemble intégré et validé ».<br>**Or ces deux règles s'excluent :** « historique linéaire requis » **refuse tout merge commit**. Les deux ont pourtant été appliquées — mesuré le 12/08/2026 : `required_linear_history` valait `true` sur `main` **et** sur `develop`, avec `enforce_admins`.<br>**Conséquence directe :** la PR `#30`, première fusion de `develop` dans `main`, **n'a pas été squashée par inadvertance — c'était la seule méthode que la protection autorisait.** |
| Impact | **Cumulatif, et c'est ce qui le rend sérieux.** Le squash a coupé `main` de l'histoire de `develop` : la base de fusion est restée `09ceb7c`, si bien que **tout fichier touché des deux côtés entre en conflit alors que le contenu ne divergeait pas**. Mesuré sur la PR `#33` : **9 fichiers en conflit, insolubles** — leur résolution exigeait elle-même un merge commit sur `develop`, que la protection refusait. Et le défaut se serait **reproduit à chaque porte**, en s'aggravant à mesure que les deux histoires s'éloignent. |
| Cause | **Deux règles justes séparément, incompatibles ensemble, dans un même document.** Ni la ligne 94 ni la ligne 106 n'est fausse en soi : la première sert la lisibilité de `develop`, la seconde la traçabilité de `main`. Aucune relecture de l'une n'aurait révélé le problème — il ne se voit qu'en les confrontant, et il ne s'est manifesté qu'à la **seconde** fusion vers `main`. C'est la classe de `ECART-023`, élargie : un document dérivé peut non seulement vieillir, il peut **prescrire l'impossible dès sa rédaction**. |
| Bloquant | Non pour `G1`, déjà validée, et aucun critère de sortie n'est remis en cause. Bloquant en revanche pour **toute** fusion de `develop` dans `main`, donc pour la porte `G2` et les suivantes |
| Recommandation | **Distinguer le réglage par branche** au lieu de l'appliquer uniformément : `develop` ne reçoit que des squash de branches de travail et gagne à rester linéaire ; `main` reçoit des merge commits et ne peut pas l'être. Et **poser le contrôle qui manquait** : après une fusion `develop` → `main`, comparer les **arbres** et vérifier l'**ascendance**, plutôt que de se fier au verdict de fusion. |
| Résolution | **Clos** le 12 août 2026 par `DEC-495`, la rectification des §2 et §2.1 des conventions, et la PR `#35`.<br>**Réglage :** `required_linear_history` retiré sur `main`, conservé sur `develop` — mesuré après application, `false` / `true`, les six autres réglages inchangés.<br>**Réparation :** la PR `#35` est une **vraie fusion**, `develop` devient ancêtre de `main`, et la base de fusion remonte de `09ceb7c` à `e526e57`, la tête de `develop`. Mesuré : `main^{tree}` = `develop^{tree}` = `9bc9359`, **2 parents**, `main`↔`develop` à **3 / 0**.<br>**Et le contrôle posé a immédiatement attrapé un défaut :** une résolution en `git merge -X theirs` avait rendu un arbre **divergent**, la stratégie ayant conservé un fragment **non conflictuel** du côté abandonné — **41 lignes dupliquées dans `fiche-lot-1.md`, aucun conflit signalé**. Sans la comparaison des arbres, cette fusion passait en paraissant propre. |

## `ECART-027` — Trois tests d'intégration recopiaient la révision de tête d'Alembic

| Champ | Valeur |
|---|---|
| Constaté le | 18 août 2026, LOT 2 sous-étape `T1`, en ajoutant la migration `0002` |
| Source | `apps/api/tests/test_integration.py`, trois tests écrits en `T3` du LOT 1 |
| Constat | Trois tests de migration — application sur base vide, rejeu, montée après descente — affirmaient `assert _revision_appliquee(base_vide) == "0001"`, **la révision écrite en dur**. Ils sont passés au rouge dès que la migration `0002` a été ajoutée, avec `assert '0002' == '0001'`. |
| Impact | Borné, et le défaut était bruyant. Mais **onze migrations restent à écrire dans ce lot** : sans correction de la cause, chacune aurait cassé les mêmes trois tests, et la tentation à chaque fois aurait été de mettre à jour le nombre plutôt que de supprimer la classe. |
| Cause | **Un identifiant recopié au lieu d'être dérivé de sa source.** C'est exactement `ECART-021`, appliqué non plus à un nombre de la documentation mais à une valeur d'un test. Et c'est `ECART-024` pour le mécanisme : les trois tests étaient **justes quand ils ont été écrits** — `0001` était alors la seule révision du dépôt — et c'est l'ouverture du LOT 2 qui les a rendus faux. Un contrôle ne devient pas faux tout seul. |
| Bloquant | Non. Découvert par l'échec des tests, corrigé dans la même sous-étape |
| Recommandation | **Dériver, jamais recopier** — la parade de `ECART-021`, transposée au code de test. |
| Résolution | **Clos** le 18 août 2026. Une fonction `_tete_de_migration()` interroge `alembic heads` et **exige d'y trouver exactement une tête**, puis les trois tests comparent à cette valeur dérivée. **Éprouvé par témoin** : une révision `0003` jetable a été ajoutée, les trois tests ont **continué à passer**, puis le témoin a été supprimé. Sans ce témoin, la correction n'aurait pas été distinguable d'un simple remplacement de `0001` par `0002`. |

## `ECART-028` — Le modèle place les domaines e-mail autorisés à deux endroits

| Champ | Valeur |
|---|---|
| Constaté le | 19 août 2026, LOT 2 sous-étape `T2`, en implémentant les quatre tables du §5 |
| Source | Modèle de données §5.2 `platform_setting` et §5.4 `allowed_email_domain` |
| Constat | Le §5.2 énumère « **domaines e-mail autorisés** » parmi les catégories de paramètres globaux de `platform_setting`. Le §5.4 consacre à ces mêmes domaines **une table dédiée**, avec ses colonnes nommées — `domain`, `entity_id`, `active`, `starts_at`, `ends_at`. La même donnée est donc rattachée à deux endroits du modèle. |
| Impact | Faible, mais réel si on l'ignore : une implémentation qui suivrait le §5.2 stockerait les domaines dans une clé de paramètre `jsonb`, **et perdrait au passage tout ce que le §5.4 apporte** — l'historisation par période, l'interrupteur `active`, et le rattachement optionnel à une entité. Deux endroits pour la même donnée finissent toujours par se contredire. |
| Cause | Le §5.2 décrit des **catégories fonctionnelles** de paramétrage, pas un schéma de stockage. La mention y est descriptive ; elle a été lue au premier abord comme prescriptive. |
| Bloquant | Non |
| Recommandation | **La table fait autorité.** Une table dédiée, avec ses colonnes nommées et ses règles d'historisation, l'emporte sur un libellé dans une liste à puces. |
| Résolution | **Clos** le 19 août 2026 par `DEC-501`. `allowed_email_domain` est la seule dépositaire des domaines : **aucune clé de `platform_setting` n'en portera**, et la contrainte de forme sur les clés ne réserve rien à cet usage. La lecture est inscrite en tête de `app/entities/modeles.py`, à l'endroit où quelqu'un qui ajouterait une clé de paramètre la lira. |

## `ECART-029` — L'index du §25.1 ne suffit pas à l'unicité insensible à la casse du §6.1

| Champ | Valeur |
|---|---|
| Constaté le | 19 août 2026, LOT 2 sous-étape `T3`, en implémentant `person` |
| Source | Modèle de données §6.1, contraintes de `person` ; §25.1, index uniques partiels |
| Constat | Le §6.1 pose parmi les contraintes de `person` : « **unicité insensible à la casse** de `email_normalized` ». Le §25.1 spécifie l'index correspondant : `person(email_normalized) UNIQUE` — un index **simple**, donc **sensible à la casse**.<br>**L'index spécifié ne satisfait pas la contrainte exigée.** `Jean.Dupont@exalt.com` et `jean.dupont@exalt.com` sont deux valeurs distinctes pour un index simple, et coexisteraient. |
| Impact | Réel et silencieux si on suit le §25.1 à la lettre : deux comptes pour la même personne, découverts au premier magic link ambigu — donc au LOT 3, dans une fonctionnalité d'authentification, avec des conséquences de sécurité. Nul si on suit le §6.1. |
| Cause | Le §25.1 est une liste d'**index à prévoir**, écrite en raccourci ; le §6.1 est la liste des **contraintes**. Le raccourci a perdu une exigence. Ni l'un ni l'autre n'est faux en soi — c'est leur conjonction qui l'est, la classe de `ECART-026`. |
| Bloquant | Non pour `G2`. Le serait pour `G3`, où l'authentification résout une personne par son adresse |
| Recommandation | **Ne pas choisir entre les deux.** Une troisième voie satisfait les deux textes : exiger que la valeur **stockée** soit déjà en minuscules. L'index simple du §25.1 devient alors suffisant, puisque deux graphies ne peuvent pas coexister — l'une des deux ne peut pas être écrite. |
| Résolution | **Clos** le 19 août 2026 par `DEC-503`. La contrainte `ck_person_email_normalise_en_minuscules` refuse toute forme normalisée non minuscule, et l'index unique simple du §25.1 est conservé tel qu'il est spécifié. **Éprouvé par témoin** : une forme normalisée avec majuscules est refusée, et trois formes minuscules distinctes sont acceptées.<br>**Cette voie est plus forte qu'un index fonctionnel sur `lower(email_normalized)`** : celui-ci empêcherait le doublon mais laisserait entrer une valeur non normalisée dans une colonne nommée `_normalized`. |

## `ECART-030` — Le diagramme d'états du §24.1 montre un état que l'énumération du §6.2 ne déclare pas

| Champ | Valeur |
|---|---|
| Constaté le | 19 août 2026, LOT 2 sous-étape `T4`, en implémentant `entity_membership` |
| Source | Modèle de données §6.2, colonne `membership_state` ; §24.1, diagramme « Appartenance à une entité » |
| Constat | Le §6.2 déclare `membership_state` comme une énumération de **quatre** valeurs : `future`, `active`, `departed`, `archived`.<br>Le diagramme du §24.1, intitulé « **Appartenance à une entité** », en montre **cinq** : il ajoute `Anonymized`, avec deux transitions entrantes — `Departed --> Anonymized: délai RGPD atteint` et `Archived --> Anonymized: délai RGPD atteint` — et une sortie vers l'état final. |
| Impact | Faible si la lecture est bonne, sérieux si elle ne l'est pas. Ajouter `anonymized` à l'énumération de l'appartenance créerait un **second endroit** où l'anonymisation est représentée, `person.account_state` en portant déjà la valeur. Deux représentations du même fait divergent, et le LOT 10 — RGPD et conservation — devrait alors les réconcilier. |
| Cause | Le diagramme décrit le **cycle de vie du collaborateur** vu depuis son appartenance, ce qui est naturel pour un lecteur métier : il part, il est archivé, puis ses données sont anonymisées. Mais l'anonymisation est une opération sur l'**identité**, pas sur le profil local — le §6.1 la déclare sur `person.account_state`, et le « délai RGPD » se compte par personne. Le diagramme mêle deux niveaux que les tables séparent. |
| Bloquant | Non |
| Recommandation | **La colonne fait autorité sur le diagramme.** Le §6.2 énumère explicitement quatre valeurs ; le §24.1 illustre. Et l'anonymisation reste là où le §6.1 la place, sur `person`. |
| Résolution | **Clos** le 19 août 2026 par `DEC-505`. `membership_state` porte **quatre** valeurs, et un test l'exige explicitement en nommant l'écart : `assert "anonymized" not in ETATS_APPARTENANCE`. La lecture est inscrite dans la docstring de l'énumération, à l'endroit où quelqu'un tenté d'ajouter la cinquième valeur la lira.<br>**Une conséquence à connaître pour le LOT 10** : anonymiser une personne ne changera pas l'état de ses appartenances, qui resteront `departed` ou `archived`. C'est cohérent — le profil local a cessé d'exister à son terme, l'identité est effacée ensuite — mais il faudra que le LOT 10 le dise, et non le découvre. |

## `ECART-031` — Une règle du §8.4 exige un état de publication que `office` ne déclare pas

| Champ | Valeur |
|---|---|
| Constaté le | 19 août 2026, LOT 2 sous-étape `T8`, en implémentant les responsabilités Framework |
| Source | Modèle de données §8.4, contraintes de `framework_responsibility_assignment` ; §8.3, champs de `office` ; §25.4, règles nécessitant un service ou un déclencheur |
| Constat | Le §8.4 pose parmi ses contraintes : « un bureau possède entre un et trois responsables actifs **lorsqu'il est publié** », et le §25.4 la reprend sous la forme « un bureau publié avec un à trois responsables actifs ».<br>**Or le §8.3 ne déclare aucun état de publication sur `office`.** Ses champs sont `entity_id`, `code`, `name`, `description`, `location_text`, `display_order` — auxquels s'ajoutent les champs communs du §3.1, dont `archived_at`, mais **aucun** `published_at` ni `visibility`.<br>La condition « lorsqu'il est publié » **n'a donc rien à quoi se rattacher**. |
| Impact | La règle est **inapplicable en l'état**, et son inapplicabilité est silencieuse : rien dans le schéma ne signale qu'une contrainte du modèle n'est pas portée. Sans consignation, elle serait simplement oubliée — et le §25.4 la liste pourtant parmi celles qui « seront appliquées par un service transactionnel ». |
| Cause | Le §8.4 emprunte une notion — la publication d'un bureau — à un domaine que le modèle traite ailleurs. Les contenus éditoriaux du §15 et les états de publication du §12.1 (`arrival_profile`) montrent que le modèle sait déclarer une publication ; il ne l'a pas fait pour `office`. **Même classe que `ECART-030`** : une règle qui suppose un état que la table ne porte pas. |
| Bloquant | Non pour `G2` : la règle n'est pas un critère de sortie du LOT 2, et aucune donnée réelle n'existe. **À instruire avant le LOT 6**, qui publie les cercles et bureaux au portail |
| Recommandation | **Ne rien inventer.** Trois issues sont concevables et le choix n'est pas technique : ajouter un état de publication à `office` (nouvelle version du modèle), rattacher la publication aux contenus du §15, ou lire « publié » comme « non archivé » — cette dernière étant la plus simple et la plus contestable, puisqu'elle ferait de tout bureau non archivé un bureau publié. |
| Résolution | **Ouvert.** `T8` a implémenté tout ce qui est applicable : les trois règles de portée, l'unicité du Booster par cercle, les trois exclusions, et les deux règles inter-tables par déclencheur. **La règle du bureau publié est consignée dans l'en-tête de la migration `0009`**, à l'endroit où quelqu'un cherchant pourquoi elle manque la lira.<br>**Et un second motif la rendrait de toute façon impossible en contrainte** : « entre un et trois » est un **comptage borné**, qu'aucune contrainte de ligne ni index n'exprime. Il faudra un déclencheur, le jour où l'état de publication existera. |

## `ECART-032` — Le backlog interdit plus largement que le cahier, la matrice et le modèle réunis

| Champ | Valeur |
|---|---|
| Constaté le | 19 août 2026, LOT 2 sous-étape `T10`, en vérifiant les trois critères de `MVP-L02-US005` **avant** de les implémenter |
| Source | Backlog §`MVP-L02-US005`, critères d'acceptation ; cahier des charges §4.1 ; matrice des rôles §3 ; modèle de données §8.4, contraintes de `framework_responsibility_assignment` |
| Constat | Le backlog énonce comme critère d'acceptation : « aucune **responsabilité métier** active dans plusieurs entités ». Sans qualificatif, la formule couvre les **quatre** types du §8.4 — `DSM`, `ESM`, `BOOSTER`, `OFFICE_MANAGER`.<br>**Les trois autres documents disent tous la même chose, et tous restreignent au seul Booster :**<br>• cahier des charges : « une personne ne peut pas être **Booster** active dans plusieurs entités » ;<br>• matrice des rôles : « Une personne ne peut pas être **Booster** active simultanément dans plusieurs entités. » ;<br>• modèle §8.4 : « une personne ne peut pas être **Booster** active dans plusieurs entités simultanément ».<br>**C'est donc le backlog qui est l'exception**, et non le modèle qui serait en retard. |
| Impact | **Aucun sur le livrable, et la règle de préséance suffit à le dire.** Le §3 de la passation pose que le cahier « prévaut sur tout » : le déclencheur `booster_une_seule_entite` posé en `T8`, restreint à `BOOSTER`, est **conforme**.<br>L'impact porte sur la **lecture de la porte `G2`** : le critère de `US005` sera lu dans le backlog, et un relecteur pourrait conclure à un critère non satisfait alors qu'il l'est au sens du cahier. |
| Cause | Une généralisation de vocabulaire dans un document dérivé. Le backlog résume en une ligne trois règles hétérogènes, et « Booster » y est devenu « responsabilité métier » — terme qui n'apparaît sous cette forme dans **aucun** des trois autres documents. **Même classe que `ECART-023`** : un document dérivé ne fait pas que vieillir, il peut **prescrire autre chose que sa source dès sa rédaction**. |
| Bloquant | Non. Le livrable est conforme au document prévalent, et aucune donnée réelle n'existe |
| Recommandation | **Ne pas appliquer l'énoncé large, et le dire.** L'appliquer interdirait des données que le corpus autorise ailleurs : la matrice §5.1 prévoit qu'un super-administrateur « intervienne dans toutes les entités », et le §8.6 rend `entity_id` **nullable** pour `SUPER_ADMIN` précisément pour cela. Poser une interdiction que trois documents sur quatre ne portent pas serait **inventer une contrainte** — §6.5 — et l'erreur serait du côté coûteux : **un refus est un échec dur, une permission se resserre plus tard.** C'est le contresens que `T7` a évité sur les cercles secondaires et `T8` sur la multiplicité des `DSM`.<br>Si Léa veut la portée large, elle est **techniquement immédiate** : le déclencheur de `T8` teste `NEW.responsibility_type = 'BOOSTER'`, et retirer cette condition suffit. À instruire **avant le LOT 6**, qui expose les responsabilités. |
| Résolution | **Ouvert.** Aucune correction du backlog : il est **immuable** (§3). L'écart est consigné, et le compte rendu de `T10` §2 dit explicitement lequel des deux énoncés est appliqué et pourquoi. **À annoncer à la porte `G2`**, pour qu'un relecteur du backlog ne conclue pas à un critère manquant. |

---

## `ECART-033` — Un contrôle parsait du JSON dans un flux mêlé d'avertissements

| Champ | Valeur |
|---|---|
| Constaté le | 20 août 2026, LOT 3 sous-étape `T1`, en ajoutant quatre variables d'environnement |
| Source | `infra/scripts/verifier-collisions-ports.py`, fonction `lancer()` — écrite en `T11` du LOT 1, `DEC-494` |
| Constat | La fonction rendait `(p.stdout + p.stderr)`, ce qui est commode pour un message d'erreur. Le contrôle **parsait ensuite ce résultat en JSON**.<br>`T1` du LOT 3 a ajouté quatre variables à `.env.example`. Avant qu'elles n'entrent dans `.env.recette`, Compose a écrit sur son flux d'erreur : « The "POSTGRES_MIGRATIONS_USER" variable is not set. Defaulting to a blank string. »<br>**`make ports` a échoué sur `json.decoder.JSONDecodeError: Extra data: line 521 column 2`.** La trace ne nommait ni Compose, ni l'avertissement, ni la variable : elle pointait une position dans un texte. |
| Impact | Aucun sur le livrable — le contrôle **échouait bruyamment**, ce qui est le bon comportement. L'impact était sur le **diagnostic** : rien dans le message ne conduisait à la cause. |
| Cause | **Le contrôle était JUSTE quand il a été écrit.** En `T11` du LOT 1, aucune commande Compose n'émettait d'avertissement, et mêler les deux flux n'avait aucune conséquence observable. C'est `ECART-024` à l'identique : un contrôle ne devient pas faux tout seul, il le devient quand le monde change autour de lui — et ce changement, c'est nous qui l'avons fait. §7.21. |
| Bloquant | Non |
| Recommandation | **Séparer les flux quand la sortie est parsée**, et **rapporter** le flux d'erreur au lieu de le mêler ou de le taire. Le taire serait le §7.6, le mêler est ce défaut. |
| Résolution | **Clos.** `lancer_json()` rend `(code, stdout, stderr)` séparément, le JSON est parsé sur `stdout` **seul**, et les avertissements de Compose sont **comptés et affichés** — une variable absente devient une chaîne vide dans la configuration assemblée, et le silence la rendrait invisible. Un `JSONDecodeError` est désormais rattrapé et **nomme l'environnement concerné**. |

---

## `ECART-034` — La fiche du lot annonçait un seuil à choisir là où le cahier en donne six

| Champ | Valeur |
|---|---|
| Constaté le | 21 août 2026, LOT 3 sous-étape `T8`, en ouvrant la limitation de débit |
| Source | `docs/operations/fiche-lot-3.md` §8, ligne « **Valeurs des limites de débit** \| le cahier exige une limitation, sans donner de seuil \| `T8` » |
| Constat | **Le cahier §20.2 s'intitule « Seuils initiaux » et en énumère six**, dont trois portent sur l'authentification :<br>• « **10** demandes de magic link par adresse et par heure : **limitation** » ;<br>• « **5** échecs administrateur en **15 minutes** : **alerte** » ;<br>• « **50** demandes depuis une même origine en une heure : **alerte** ».<br>**Et `.env.example` en porte cinq depuis le LOT 0**, chacune avec son commentaire `[source] cahier 20.2` — introduites par le commit `802fe69`.<br>**Un second constat, plus sérieux, est apparu en mesurant le premier :** ces cinq variables ne sont **consommées par personne**. `grep -rn` sur `apps/`, `packages/` et `infra/` rend **0 occurrence**. |
| Impact | **Deux impacts, et le second est un piège d'exploitation.**<br>**(a)** La fiche invitait à *choisir* une valeur. L'avoir suivie aurait produit un seuil inventé qui **contredit le cahier** — lequel « prévaut sur tout » (§3 de la passation). C'est l'inverse du cas habituel : le document n'annonçait pas à tort que le travail était fait, il annonçait à tort qu'une **décision restait à prendre**.<br>**(b)** Un exploitant qui abaisserait `MAGIC_LINK_MAX_PER_EMAIL_PER_HOUR` dans son `.env` croirait avoir durci la sécurité et **se tromperait**, sans qu'aucun contrôle ne le signale. C'est exactement le « avertissement faux » du §7.21 : il apprend à ne plus lire ce qui est écrit. |
| Cause | **Un document dérivé qui affirme au lieu de dériver.** Le §8 de la fiche liste les points « que le corpus ne tranche pas » — trois de ses quatre lignes sont justes (`QO-118`, la durée d'un jeton de service, la liste des scopes). La quatrième a été écrite sans relire le §20.2. Classe `ECART-021`, et même famille que `ECART-023` : un document dérivé peut **prescrire l'impossible dès sa rédaction**.<br>Pour l'impact **(b)**, la cause est différente : les variables ont été posées au LOT 0 pour leur traçabilité, avant qu'aucun code n'existe pour les lire, et rien n'a jamais mesuré l'écart entre « déclarée » et « consommée ». |
| Bloquant | Non. Détecté **avant** d'inventer une valeur, et le livrable applique les seuils du cahier |
| Recommandation | **(a)** Corriger la ligne du §8 de la fiche — fait — et **poser le contrôle qui l'aurait attrapée** : un test qui **relit le cahier** et exige que chaque constante de seuil corresponde à la phrase qui la produit, verbe inclus. Fait : `test_les_trois_seuils_sont_ceux_du_CAHIER_relu` et `test_les_deux_VERBES_du_cahier_sont_distincts`. Une constante changée à la main, ou un cahier modifié, font désormais échouer la suite au lieu de passer en silence.<br>**(b)** **Ne pas lire les seuils depuis l'environnement**, et le dire dans le fichier. `.env.example` §8 annonce lui-même « modifiables par le super-administrateur uniquement (matrice §19) » et « toute modification est **auditée** » : une variable d'environnement est modifiée par l'**exploitant**, pas par le super-administrateur, et sa modification n'est auditée par rien. La lire satisferait la forme et non la règle. Leur destination est **`platform_setting`** (modèle §5.2, « seuils de sécurité »), avec l'écran de réglages du **LOT 9** et l'audit du **LOT 10**.<br>**Recommandation ouverte pour la suite :** un contrôle qui exige que **chaque** variable de `.env.example` soit consommée quelque part **ou** porte une annotation explicite. Il transformerait cette classe en état contrôlé au lieu d'un état silencieux. Non posé en `T8` : hors périmètre, et il flaguerait des variables lues par Compose et non par l'API — donc il demande d'être exact avant d'être large, §7.25. |
| Résolution | **Clos pour (a), et signalé pour (b).** Les trois seuils appliqués sont ceux du §20.2, portés en constantes dans `apps/api/app/auth/debit.py`, deux tests les confrontent au cahier, et `DEC-533` en trace la lecture. Les cinq variables de `.env.example` §8 sont **conservées** — elles portent la traçabilité vers le §20.2 et le LOT 9 en aura besoin — mais chacune est désormais **annotée `[non consommée — ECART-034]`**, avec un avertissement en tête de section plutôt qu'en note. |

---

**Prochain identifiant libre : `ECART-035`.**
