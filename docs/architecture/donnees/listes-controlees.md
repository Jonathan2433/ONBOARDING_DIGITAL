# Listes contrôlées du CSV collaborateurs

**Version :** `1.0-initiale`
**Produit en :** LOT 0, sous-étape S6 — story `MVP-L00-US004`
**Fondement :** cahier des charges §10.3, §6.1, §6.4 ; modèle de données §6, §8 ; matrice §2.2

---

## 1. Principe

Une liste contrôlée est un ensemble fermé de valeurs admises pour un champ. Une valeur hors
liste produit une erreur ou une décision requise, jamais une création silencieuse.

Ces listes sont **configurables en base de données**. Les valeurs ci-dessous sont l'état
initial validé, pas une contrainte figée dans le code.

| Champ | Liste | Nature |
|---|---|---|
| `F05` entité | §2 | Fermée, gérée par le super-administrateur |
| `F08` catégorie professionnelle | §3 | Fermée, énumération du modèle |
| `F12` situation professionnelle | §4 | Fermée, énumération du modèle |
| `F14`, `F15` cercles | §5 | Configurable par entité |
| `F17` responsabilités Framework | §6 | Fermée, énumération du modèle |
| scope `OFFICE_MANAGER` | §7 | Configurable par entité |
| `F18` rôles techniques | §8 | Fermée, avec restriction à l'import |
| `F19` autorisation photo | §9 | Fermée |
| `F11` métier | §10 | **À établir** |
| `F13` client | §11 | Ouverte, avec validation humaine |

---

## 2. Entités — champ `F05`

| Code | Nom | État au MVP |
|---|---|---|
| `BORDEAUX` | eXalt Bordeaux | Active. Seule entité portant du contenu réel au MVP. |

L'architecture doit permettre jusqu'à **25 entités** sans refonte (cahier §4.1). Le
super-administrateur crée les entités depuis la super-administration
(`MVP-L09-US007`) ; elles ne sont **jamais** créées par import.

Le code d'entité est **immuable après activation** (modèle §5.1).

Les jeux de test utilisent des entités fictives, jamais de données Bordeaux dans une autre
entité (roadmap §2.3).

---

## 3. Catégories professionnelles — champ `F08`

| Valeur | Sens |
|---|---|
| `consultant` | Collaborateur consultant |
| `dg` | Direction générale |

Énumération `professional_category` du modèle §6.2, qui prévoit d'autres catégories
configurables ultérieurement.

**Un `dg` reçoit automatiquement la responsabilité DSM dans son entité** (`RIGHTS-005`, cahier
§6.4), attribuée dans la même transaction que la catégorie (modèle §8.4). Il n'est donc pas
nécessaire de l'inscrire dans `F17`.

> **Piège de saisie fréquent.** `ESM` et `DSM` ne sont **pas** des catégories
> professionnelles : ce sont des **responsabilités Framework**, à porter dans `F17`. De même,
> « consultant en mission » et « consultant en intercontrat » ne sont pas deux catégories : la
> catégorie est `consultant` et la situation se porte dans `F12`. La matrice §2.2 interdit de
> fusionner ces dimensions.

---

## 4. Situations professionnelles — champ `F12`

| Valeur | Client `F13` | Modèle d'onboarding instancié |
|---|---|---|
| `mission` | **Obligatoire** | Modèle `mission` |
| `intercontrat` | **Doit être vide** | Modèle `intercontrat` |

Énumération `status` du modèle §6.5. Un changement de situation déclenche l'évaluation du
parcours d'onboarding et remplace le modèle actif, en conservant les tâches communes déjà
terminées (`DATA-007`, cahier §10.4).

---

## 5. Cercles — champs `F14` et `F15`

Huit cercles initiaux pour Bordeaux, **configurables en base** (cahier §10.3).

| Code | Nom |
|---|---|
| `CHANGE` | Change |
| `DATA` | Data |
| `DESIGN` | Design |
| `FORGE` | Forge |
| `IT` | IT |
| `PRODUIT` | Produit |
| `PROJET` | Projet |
| `SHIELD` | Shield |

Règles :

- un cercle appartient à **une seule entité** ; un code de cercle d'une autre entité est refusé ;
- une personne possède **un seul cercle principal actif** et éventuellement plusieurs cercles
  secondaires (cahier §11.1, modèle §8.2) ;
- le cercle principal ne doit pas être répété en secondaire ;
- **exception** : une personne portant la responsabilité DSM peut ne pas avoir de cercle
  principal (cahier §11.1) ;
- un cercle ne peut pas être archivé tant qu'il contient des membres actifs (`RIGHTS-020`).

La couleur de cercle est une donnée de présentation, propre à chaque entité. Elle n'apparaît
pas dans le CSV, et **ne constitue jamais l'unique information** transmise à l'écran (cahier
§10.1).

---

## 6. Responsabilités Framework — champ `F17`

| Valeur | Scope | Obligation du scope |
|---|---|---|
| `DSM` | aucun | Scope **interdit** |
| `ESM` | aucun | Scope **interdit** |
| `BOOSTER:<code_cercle>` | un cercle | Scope **obligatoire** |
| `OFFICE_MANAGER:<code_bureau>` | un bureau | Scope **obligatoire** |

Énumération `responsibility_type` du modèle §8.4.

Contraintes :

| Règle | Source |
|---|---|
| Un cercle possède **un seul** Booster actif | `RIGHTS-007`, cahier §6.4 et §12.6 |
| Une personne **peut** être Booster de plusieurs cercles d'une même entité | Modèle §8.4 |
| Une personne **ne peut pas** être Booster active dans plusieurs entités | Cahier §6.4 |
| Un bureau publié possède **de un à trois** responsables actifs | Cahier §6.4, modèle §8.4 |
| Les responsabilités **se cumulent** dans l'entité principale | `RIGHTS-004` |
| Un responsable de bureau n'obtient **aucun** droit général sur les profils | Matrice §6.2 |

Exemple de cumul valide dans une seule cellule :
`BOOSTER:DATA|OFFICE_MANAGER:BDE`

L'attribution des responsabilités Framework est réservée à l'ESM et au super-administrateur
(`ARB-DROIT-002`, `RIGHTS-022`). L'import initial les porte comme **état de départ** du
référentiel ; toute modification ultérieure passe par les rôles autorisés, avec audit.

---

## 7. Bureaux — scope de `OFFICE_MANAGER`

Trois bureaux initiaux, **entièrement configurables** (cahier §10.3).

| Code | Nom |
|---|---|
| `BDS` | BDS |
| `BDE` | BDE |
| `BDG` | BDG |

Les documents validés ne développent pas l'intitulé complet de ces sigles. Ils seront
renseignés par Tess et Diane lors de la reprise des contenus éditoriaux (LOT 6,
`MVP-L06-US003` et `MVP-L06-US007`). Je ne les invente pas ici.

---

## 8. Rôles techniques — champ `F18`

| Valeur | Portée | Accepté à l'import |
|---|---|---|
| `ENTITY_ADMIN` | Une entité | **Oui** |
| `SUPER_ADMIN` | Globale | **Non** — code `E-ROLE-002` |

Énumération `role_type` du modèle §8.6.

Le refus de `SUPER_ADMIN` à l'import est une **recommandation soumise à validation** : la
matrice §21 réserve la création d'un super-administrateur au rôle `SUPER`, et cette attribution
déclenche une alerte de sécurité (`RIGHTS-016`, cahier §20.2). L'autoriser par dépôt de fichier
contournerait ce contrôle.

Les rôles techniques sont **séparés** des responsabilités Framework (`DATA-003`, matrice §2.2).
Un administrateur d'entité ne peut pas attribuer de responsabilité Framework (`RIGHTS-022`).

---

## 9. Autorisation de photographie — champ `F19`

| Valeur | Sens | Effet à l'affichage |
|---|---|---|
| `oui` | Autorisation explicite recueillie | La photo peut être publiée, une fois le média chargé et validé |
| `non` | Refus exprimé | Avatar neutre |
| `inconnu` | Information manquante | Avatar neutre |
| *(vide)* | Équivaut à `inconnu` | Avatar neutre |

**Décision `DEC-433`.** Valeur par défaut : `inconnu`. Sans autorisation active, aucune photo
n'est publiée (cahier §21.2, `ROAD-RSK-018`).

`non` et `inconnu` produisent le même affichage mais se distinguent au registre : le premier
est un refus, le second une lacune à combler. Cette distinction est nécessaire au traitement
de `QO-098`, « preuves disponibles d'autorisation des photos », bloquante avant données
réelles.

---

## 10. Métiers — champ `F11`

**Liste à établir. Elle n'est délibérément pas renseignée ici.**

Le catalogue métier est configurable par entité (modèle §6.3) et **aucun document validé ne
l'énumère**. La matrice §2.2 cite seulement, à titre d'illustration, « Data Analyst », « Product
Owner » et « développeur ».

Inventer ce catalogue serait substituer une hypothèse à une décision, ce qui est interdit.

Procédure retenue :

1. les valeurs de métier du CSV réel sont **relevées** lors de l'analyse, sans écriture ;
2. l'ESM valide, corrige et consolide le catalogue de l'entité ;
3. chaque valeur non reconnue produit `D-METIER-001`, décision humaine, jamais une création
   automatique ;
4. le catalogue validé est enregistré dans `job_catalog` et ce document est mis à jour, avec
   une nouvelle version du schéma.

Ce point est rattaché à `QO-096`, « schéma définitif des colonnes du CSV ».

---

## 11. Clients — champ `F13`

**Liste ouverte, avec validation humaine obligatoire.**

Les clients constituent un référentiel **global**, activé par entité (`DATA-004`, modèle §7).
Le CSV porte un nom de client en texte libre.

| Situation | Traitement |
|---|---|
| Le nom correspond exactement à un client activé dans l'entité | Rattachement direct |
| Le nom correspond à un client global non activé localement | Activation locale, avertissement `W-CLIENT-001` |
| Le nom ressemble à un client existant | `D-CLIENT-001` — proposition d'alias, **décision humaine** |
| Le nom est inconnu du référentiel global | `D-CLIENT-002` — création ou correction, **décision humaine** |

**Aucune fusion ni création d'alias n'est automatique** (cahier §12.3, `DATA-005`). Un alias
n'est utilisable qu'après validation humaine horodatée et attribuée (modèle §7.3).

Les DSM valident les clients de leur périmètre, l'ESM ceux de l'entité (matrice §14.1).

---

## 12. Récapitulatif des valeurs admises

| Champ | Valeurs |
|---|---|
| `F05` entité | `BORDEAUX` |
| `F08` catégorie | `consultant`, `dg` |
| `F12` situation | `mission`, `intercontrat` |
| `F14`, `F15` cercles | `CHANGE`, `DATA`, `DESIGN`, `FORGE`, `IT`, `PRODUIT`, `PROJET`, `SHIELD` |
| `F17` responsabilités | `DSM`, `ESM`, `BOOSTER:<cercle>`, `OFFICE_MANAGER:<bureau>` |
| bureaux | `BDS`, `BDE`, `BDG` |
| `F18` rôles techniques | `ENTITY_ADMIN` |
| `F19` autorisation photo | `oui`, `non`, `inconnu`, vide |
| `F11` métier | **à établir** |
| `F13` client | libre, avec validation humaine |

---

## 13. Règles de tenue

- une valeur retirée d'une liste ne casse pas les données existantes : les relations
  historisées conservent leur référence ;
- l'ajout d'une valeur à une liste configurable ne requiert pas de nouvelle version du schéma ;
- la modification d'une liste **fermée** — catégories, situations, responsabilités, rôles
  techniques, autorisation photo — modifie le modèle de données et exige une décision tracée
  ainsi qu'une nouvelle version du schéma ;
- ce document est mis à jour en même temps que le catalogue réel, jamais après.
