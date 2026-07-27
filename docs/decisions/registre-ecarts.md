# Registre des écarts

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Séquence créée par :** `DEC-431`
**Dernière mise à jour :** 27 juillet 2026

Un écart est une différence constatée entre l'existant et les documents validés. Il n'est
jamais corrigé silencieusement : il est décrit, son impact est évalué, une recommandation est
formulée, et son caractère bloquant est explicité.

| Statut | Ouverts | Clos | Acceptés |
|---|---:|---:|---:|
| Total 16 | 6 | 8 | 2 |

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
| `ECART-010` | Traçabilité GitHub non mise en place | Non pour `G0`, prérequis du LOT 1 | **Clos** |
| `ECART-011` | Cinq questions absentes de la plage `QO-072` à `QO-105` | Non | **Accepté** |
| `ECART-012` | La valeur `intercontrat` est imposée à une direction générale, faute de troisième valeur | Non | Ouvert |
| `ECART-013` | Les tâches communes aux deux parcours du prototype portent des identifiants différents | Non | Ouvert |
| `ECART-014` | Le prototype emploie « Représentant de cercle » là où les documents validés emploient « Booster » | Non | Ouvert |
| `ECART-015` | Le prototype ne fournit ni descriptions de cercles ni liens internes, contrairement à ce qu'annonce le cahier §2.2 | Non | Ouvert |
| `ECART-016` | La documentation de clôture du LOT 0 affirme que les commits sont locaux alors qu'ils sont poussés sur GitHub | Non | **Clos** |

**Prochain identifiant libre : `ECART-017`.**

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
| Source | Modèle de données §6.5 : `professional_status_assignment.status` vaut `mission` ou `intercontrat`, une seule situation active par appartenance |
| Constat | Le champ de situation professionnelle est obligatoire pour **toute** personne et n'offre que deux valeurs. Pour une catégorie `dg`, ou pour une personne dont l'activité n'est pas une mission client, `intercontrat` est la seule valeur possible. Or ce terme désigne, dans le langage métier, un consultant en attente de mission. |
| Impact | Aucun impact technique : les contraintes restent cohérentes, `intercontrat` interdisant un client actif. L'impact est **fonctionnel et éditorial** : le trombinoscope afficherait « intercontrat » sur une fiche de direction générale, ce qui serait lu comme une erreur par les collaborateurs. |
| Bloquant | Non |
| Recommandation | Ne pas modifier le modèle de données, qui est validé. Deux pistes à arbitrer avec Léa : soit l'affichage du statut est conditionné par la catégorie professionnelle, la situation restant `intercontrat` en base ; soit une troisième valeur est ajoutée à l'énumération, ce qui exige une décision et une nouvelle version du modèle. La première piste est moins coûteuse et ne touche pas au socle. |
| Résolution | Ouvert. À clarifier avec Léa et l'ESM, **au plus tard au LOT 2** lors de l'implémentation de `professional_status_assignment`, et avant le LOT 5 qui affiche le statut au trombinoscope. |

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
