# Jeu de données d'exemple — intégralement fictif

**Produit en :** LOT 0, sous-étape S6 — story `MVP-L00-US004`
**Fichier :** [`collaborateurs-exemple-fictif.csv`](collaborateurs-exemple-fictif.csv)

---

## 1. Nature de ce fichier

**Ce fichier ne contient aucune donnée réelle.** Aucun nom, aucune adresse, aucun client, aucun
métier n'y correspond à une personne ou à une organisation existante.

| Convention | Choix retenu |
|---|---|
| Noms | Tous les patronymes valent `EXEMPLE` |
| Prénoms | Alphabet radio international : Alpha, Bravo, Charlie… Quebec |
| Adresses | `<prenom>.exemple@exalt-company.com`, forme volontairement non plausible |
| Domaine non autorisé | `fournisseur-externe.example` — le domaine de premier niveau `.example` est réservé à la documentation par la RFC 2606, et ne peut donc désigner aucune organisation réelle |
| Clients | `Client Fictif Un`, `Client Fictif Deux`, `Client Fictif 1` |

C'est le seul fichier `.csv` versionné du dépôt. Il constitue l'exception explicitement prévue
dans [`.gitignore`](../../../../.gitignore), toutes les autres extensions `.csv` étant
interdites au versionnement.

Le CSV réel, lui, ne sera **jamais** versionné ni placé dans une image (cahier §29.2, critère
de sortie du LOT 9).

---

## 2. Réserve importante sur les en-têtes

La première ligne du fichier utilise un **profil de correspondance provisoire**, sans aucune
valeur normative.

La nomenclature des en-têtes du fichier réel est **en suspens** : question `QO-110`. La source
de données n'est pas encore connue. Le schéma définit des **champs logiques** `F01` à `F19`, et
un profil de correspondance versionné associera les en-têtes réelles à ces champs
(décision `DEC-434`).

Ce profil provisoire existe uniquement pour rendre le schéma démontrable. Il ne préjuge ni de
la langue ni de l'intitulé des colonnes définitives.

---

## 3. Ce que ce jeu couvre

17 lignes de données, couvrant les **six états** de ligne du cahier §12.4 et les **huit critères
de qualité** du cahier §12.6.

| Ligne | Prénom | État attendu | Code attendu | Ce qui est démontré |
|---:|---|---|---|---|
| 1 | Alpha | valide | — | Cas nominal complet en mission |
| 2 | Bravo | valide | — | Intercontrat sans client, refus de photo exprimé |
| 3 | Delta | valide | — | Cumul `DSM`, `BOOSTER:DATA` et `OFFICE_MANAGER:BDE` ; cercles secondaires ; présentation contenant une virgule sans guillemets |
| 4 | Charlie | avertissement | `W-CERCLE-001` | Catégorie `dg`, sans cercle principal ni DSM : la responsabilité DSM est attribuée automatiquement (`RIGHTS-005`) |
| 5 | Echo | avertissement | `W-PRESENTATION-001`, `W-DATE-001`, `W-PHOTO-001` | Trois avertissements cumulés ; arrivée future ; autorisation photo vide donc `inconnu` |
| 6 | Foxtrot | avertissement | `W-DEPART-001` | Départ déjà passé : importé puis archivé |
| 7 | Golf | à confirmer | `D-CLIENT-001`, `D-PERSONNE-003` | `Client Fictif 1` ressemble à `Client Fictif Un` : aucune fusion automatique. Également homonyme de la ligne 8 |
| 8 | Golf *(hotel)* | à confirmer | `D-PERSONNE-003`, `W-PHOTO-001` | Homonyme exact de la ligne 7 avec une adresse différente : décision humaine. Autorisation photo `inconnu` |
| 9 | India | rejetée | `E-EMAIL-001` | Ligne sans e-mail, bloquée jusqu'à correction |
| 10 | Juliett | rejetée | `E-SIT-003` | Mission sans client |
| 11 | Kilo | rejetée | `E-SIT-004` | Intercontrat avec client |
| 12 | Lima | rejetée | `E-EMAIL-004` | Doublon d'e-mail avec la ligne 1. La **ligne 1 est retenue**, seule la ligne 12 est rejetée (`DEC-435`) |
| 13 | Mike | rejetée | `E-EMAIL-003` | Domaine non autorisé |
| 14 | November | rejetée | `E-DSM-001` | Consultant actif sans DSM |
| 15 | Oscar | rejetée | `E-RESP-007` | Conflit de Booster sur le cercle `SHIELD` avec la ligne 17 : **les deux lignes** sont rejetées (`DEC-435`) |
| 16 | Papa | rejetée | `E-DATE-002` | Date au format `JJ/MM/AAAA` : conversion par tableur, cause fréquente de rejet |
| 17 | Quebec | rejetée | `E-RESP-007`, `E-ROLE-002` | Demande de `SUPER_ADMIN`, refusée à l'import. Second membre du conflit de Booster `SHIELD` |

### 3.1 Réconciliation attendue

| État | Lignes | Nombre |
|---|---|---:|
| Valides | 1, 2, 3 | 3 |
| Valides avec avertissement | 4, 5, 6 | 3 |
| À confirmer | 7, 8 | 2 |
| Rejetées | 9 à 17 | 9 |
| **Total** | | **17** |

### 3.2 Vérification exécutée

Cette classification n'est pas déclarative : elle a été **vérifiée par script**. Un contrôle
implémentant les règles du schéma et les arbitrages de `DEC-435` a été exécuté sur le fichier
le 27 juillet 2026, ligne par ligne.

| Résultat | Valeur |
|---|---|
| Lignes vérifiées | 17 |
| Classifications conformes | **17 / 17** |
| Écarts | **0** |
| Décompte obtenu | 3 valides, 3 avertissements, 2 à confirmer, 9 rejetées |

Le script de contrôle n'est pas versionné : ce n'est pas un livrable, et l'analyseur d'import
réel appartient au LOT 9 (`MVP-L09-US004`). Le contrôle est reproductible à partir des règles
documentées dans le [schéma](../schema-csv-collaborateurs.md) et les
[codes d'erreur](../codes-erreurs-import.md).

### 3.3 Anomalies impliquant plusieurs lignes

Trois cas du jeu illustrent les arbitrages de `DEC-435`, qui déterminent **quelle** ligne est
pénalisée quand l'anomalie naît d'une relation :

| Cas | Lignes | Règle appliquée |
|---|---|---|
| Doublon d'e-mail | 1 et 12 | La première occurrence est **retenue** ; seule la ligne 12 est rejetée |
| Conflit de Booster | 15 et 17 | **Les deux** lignes sont rejetées : désigner un Booster par l'ordre du fichier serait une décision métier arbitraire |
| Homonymie | 7 et 8 | **Les deux** lignes attendent une décision : l'ambiguïté est symétrique, aucune n'est fautive |

Un quatrième cas mérite d'être noté : les lignes 1, 5, 11 à 17 portent `Client Fictif Un`, nom
canonique, et ne reçoivent **aucun** code de rapprochement. Seule la ligne 7, qui porte la
variante `Client Fictif 1`, déclenche `D-CLIENT-001`. Sans cette règle, un rapprochement proposé
contaminerait toutes les lignes du même client.

3 + 3 + 2 + 9 = 17. Le rapport d'import doit **totaliser exactement** toutes les lignes
(cahier §12.6, démonstration attendue du LOT 9). Ce jeu sert de contrôle à ce calcul.

À l'import effectif, les 6 lignes valides ou en avertissement passeraient à l'état `importée`,
les 9 rejetées resteraient documentées, et les 2 à confirmer attendraient une décision — sans
empêcher l'import des autres (contrôle de recette du modèle n°18).

---

## 4. Hypothèses nécessaires à cette classification

La classification attendue ci-dessus suppose deux conditions. Sans elles, des codes
supplémentaires apparaîtraient légitimement.

| Hypothèse | Sans elle |
|---|---|
| Le catalogue métier de l'entité contient déjà `Data Analyst`, `Product Owner`, `Engineering Manager`, `Developpeur` et `Direction generale` | Chaque valeur produirait `D-METIER-001`. Le catalogue métier est **à établir** : voir [listes contrôlées §10](../listes-controlees.md) |
| Les clients `Client Fictif Un` et `Client Fictif Deux` sont déjà activés dans l'entité | Ils produiraient `W-CLIENT-001` ou `D-CLIENT-002` |

Ces hypothèses sont explicites parce qu'un jeu de test dont on ignore les prérequis ne prouve
rien.

---

## 5. Un point de modélisation à clarifier

Le schéma rend `F12` obligatoire pour **toute** personne, avec deux valeurs seulement :
`mission` ou `intercontrat`.

Pour la ligne 4, de catégorie `dg`, la valeur `intercontrat` est la seule possible, puisque la
personne n'est pas sur une mission client. Or « intercontrat » porte, dans le langage métier,
une connotation de consultant en attente de mission, qui ne décrit pas une direction générale.

Cet écart de vocabulaire est enregistré en `ECART-012`. Il est **non bloquant** et sera clarifié
avec Léa et l'ESM, au plus tard au LOT 2 lors de l'implémentation de
`professional_status_assignment`. Aucune modification du modèle n'est faite ici : le modèle de
données v1.0 est validé et ne se change pas sans décision.

---

## 6. Usage autorisé

| Usage | Autorisé |
|---|---|
| Valider le schéma et les codes d'erreur | Oui |
| Servir de jeu de test à l'analyseur d'import du LOT 9 | Oui |
| Servir de base au générateur de données fictives du LOT 2 (`MVP-L02-US007`) | Oui |
| Servir de gabarit vierge à remettre à l'ESM | Non — le profil d'en-têtes est provisoire |
| Être importé dans un environnement contenant des données réelles | Non |
| Être complété avec des données réelles | **Non, jamais.** Le fichier est versionné : y ajouter une donnée réelle la graverait dans l'historique Git |
