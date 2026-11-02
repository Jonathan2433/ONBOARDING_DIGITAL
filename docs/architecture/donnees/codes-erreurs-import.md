# Codes d'erreur et d'avertissement d'import

**Version :** `1.0-initiale`
**Produit en :** LOT 0, sous-étape S6 — story `MVP-L00-US004`
**Fondement :** modèle de données §19.2 et §19.3 ; cahier des charges §12.4 et §18.3

---

## 1. Principe

Chaque anomalie détectée sur une ligne produit une entrée dans `import_row_issue`, portant
(modèle §19.3) : un **code stable**, le champ concerné, un **message destiné à l'utilisateur**,
un niveau, éventuellement une valeur normalisée sûre, et une résolution attendue.

Un code stable ne change **jamais** de signification. Une règle qui évolue reçoit un **nouveau**
code.

### 1.1 Structure du code

```text
<NIVEAU>-<DOMAINE>-<NNN>
```

| Niveau | Sens | Effet sur la ligne | État de `import_row` |
|---|---|---|---|
| `E` | Erreur | La ligne est **rejetée**. Elle n'est pas importée. | `rejected` |
| `W` | Avertissement | La ligne est **importable** en l'état. L'anomalie est signalée et conservée. | `warning` |
| `D` | Décision requise | La ligne attend une **décision humaine explicite** avant tout import. | `needs_decision` |

Une ligne rejetée **n'empêche pas** les lignes valides d'être importées (cahier §12.4,
contrôle de recette du modèle n°18). Aucune ligne rejetée n'est masquée : c'est un critère de
sortie du LOT 9.

### 1.2 Anomalies portant sur plusieurs lignes

Certaines anomalies naissent de la **relation entre plusieurs lignes** : un doublon implique au
moins deux lignes, un conflit de Booster au moins deux personnes. Il faut donc dire lesquelles
sont pénalisées, sans quoi une ligne parfaitement correcte pourrait être rejetée par ricochet.

Deux règles, décision `DEC-435` :

| Type d'anomalie | Règle retenue | Motif |
|---|---|---|
| **Doublon technique d'un identifiant** — `E-EMAIL-004` | La **première occurrence dans le fichier est retenue** ; les occurrences suivantes sont seules signalées et rejetées. | L'e-mail normalisé est l'identifiant fonctionnel unique. Conserver la première occurrence est déterministe, et le rapport nomme explicitement la ligne conservée et les lignes écartées. |
| **Conflit d'attribution métier** — `E-RESP-007`, `E-RESP-008`, `E-RESP-009` | **Toutes** les lignes du groupe en conflit sont signalées et rejetées. Aucune n'est retenue. | Désigner un Booster par l'ordre d'apparition dans un fichier serait une décision métier arbitraire. Le conflit doit être tranché à la source, par l'ESM. |

Les autres anomalies relationnelles suivent la seconde règle : en cas de doute, aucune ligne du
groupe n'est retenue. `D-PERSONNE-003`, homonymie, signale également **les deux lignes** du
couple, puisque l'ambiguïté est symétrique et qu'aucune des deux n'est fautive.

**Cas particulier des rapprochements de clients.** `D-CLIENT-001` ne signale **que** la ligne
portant la variante non reconnue, jamais les lignes portant le nom canonique. La résolution
suit cet ordre :

| Situation de la valeur du champ `F13` | Traitement |
|---|---|
| Correspondance **exacte** avec un client activé dans l'entité | Rattachement direct, aucun code |
| Correspondance exacte avec un client global non activé localement | `W-CLIENT-001`, activation locale |
| **Ressemblance** avec un client existant, sans correspondance exacte | `D-CLIENT-001` sur cette ligne seulement |
| Aucune correspondance ni ressemblance | `D-CLIENT-002` sur cette ligne |

Sans cette règle, un rapprochement proposé contaminerait toutes les lignes de l'entreprise
cliente concernée, y compris celles qui sont correctes.

### 1.3 Règle de confidentialité

Un message d'erreur ne reproduit **jamais** la valeur brute d'un champ nominatif au-delà du
strict nécessaire à la correction. Le contenu d'une ligne n'est **jamais** recopié dans les
logs (modèle §19.2). Le CSV complet est exclu de l'audit (matrice §16.2).

---

## 2. Erreurs de structure du fichier

Ces erreurs portent sur le fichier, pas sur une ligne. Elles interrompent l'analyse.

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-STRUCT-001` | Le fichier est vide ou ne contient aucune ligne de données. | Fournir un fichier contenant une ligne d'en-têtes et au moins une ligne de données. |
| `E-STRUCT-002` | L'encodage du fichier n'est pas décodable en UTF-8. | Réenregistrer le fichier en UTF-8. |
| `E-STRUCT-003` | Le séparateur de champs n'a pas pu être déterminé de façon non ambiguë. | Réenregistrer avec le point-virgule comme séparateur. |
| `E-STRUCT-004` | La ligne d'en-têtes est absente. | Ajouter la ligne d'en-têtes en première position. |
| `E-STRUCT-005` | Un champ obligatoire du schéma n'a pas d'en-tête correspondante : `<champ>`. | Compléter le fichier, ou corriger le profil de correspondance des en-têtes. |
| `E-STRUCT-006` | Une en-tête n'est associée à aucun champ du schéma : `<en-tête>`. | Retirer la colonne, ou compléter le profil de correspondance. |
| `E-STRUCT-007` | La ligne `<n>` ne comporte pas le même nombre de champs que l'en-tête. | Vérifier les guillemets et les séparateurs de cette ligne. |
| `E-STRUCT-008` | Plusieurs colonnes sont associées au même champ du schéma : `<champ>`. | Supprimer la colonne en doublon. |

---

## 3. Erreurs de ligne — `E`

### 3.1 E-mail — champ `F01`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-EMAIL-001` | L'adresse e-mail professionnelle est absente. La ligne ne peut pas être importée. | Renseigner l'adresse officielle. Règle non contournable : cahier §12.2. |
| `E-EMAIL-002` | L'adresse e-mail n'a pas un format valide. | Corriger l'adresse. |
| `E-EMAIL-003` | Le domaine de l'adresse e-mail n'est pas autorisé. | Utiliser une adresse d'un domaine autorisé, ou faire ajouter le domaine par le super-administrateur. |
| `E-EMAIL-004` | Cette adresse e-mail apparaît sur plusieurs lignes du fichier. | Conserver une seule ligne par personne. Une personne n'a qu'une appartenance principale active. |

### 3.2 Identité — champs `F02`, `F03`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-IDENT-001` | Le nom est absent. | Renseigner le nom. |
| `E-IDENT-002` | Le prénom est absent. | Renseigner le prénom. |
| `E-IDENT-003` | Le nom ou le prénom dépasse la longueur autorisée. | Raccourcir à 100 caractères au maximum. |

### 3.3 Entité — champ `F05`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-ENTITE-001` | L'entité est absente. | Renseigner le code de l'entité. |
| `E-ENTITE-002` | L'entité indiquée est inconnue. | Utiliser un code d'entité existant, ou faire créer l'entité par le super-administrateur. |
| `E-ENTITE-003` | L'entité indiquée est archivée et ne peut plus recevoir de nouveaux membres. | Choisir une entité active. |

### 3.4 Dates — champs `F06`, `F07`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-DATE-001` | La date d'arrivée est absente. | Renseigner la date d'arrivée au format `AAAA-MM-JJ`. |
| `E-DATE-002` | La date d'arrivée n'est pas au format attendu `AAAA-MM-JJ`. | Corriger le format. Attention aux dates converties par le tableur. |
| `E-DATE-003` | La date de départ n'est pas au format attendu `AAAA-MM-JJ`. | Corriger le format. |
| `E-DATE-004` | La date de départ est antérieure à la date d'arrivée. | Corriger l'une des deux dates. |

### 3.5 Catégorie professionnelle — champ `F08`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-CAT-001` | La catégorie professionnelle est absente. | Renseigner `consultant` ou `dg`. |
| `E-CAT-002` | La catégorie professionnelle indiquée n'est pas reconnue. | Utiliser une valeur de la liste contrôlée. Attention : un métier ou une responsabilité n'est pas une catégorie professionnelle. |

### 3.6 Métier — champ `F11`

| Code | Message utilisateur | Résolution |
|---|---|---|
| ~~`E-METIER-001`~~ | ~~Le métier est absent alors que le profil est actif.~~ | **RETIRÉ (`DEC-675`, LOT 11 `T5`) : le métier ne bloque plus jamais l'import, même pour un profil actif — déviation tracée, le champ devient optionnel partout.** |

Une valeur de métier absente du catalogue ne rejette pas la ligne : elle déclenche
`D-METIER-001`, décision humaine — inchangé.

### 3.7 Situation professionnelle — champs `F12`, `F13`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-SIT-001` | La situation professionnelle est absente. | Renseigner `mission` ou `intercontrat`. |
| `E-SIT-002` | La situation professionnelle indiquée n'est pas reconnue. | Utiliser une valeur de la liste contrôlée. |
| `E-SIT-003` | La situation est `mission` mais aucun client n'est renseigné. | Renseigner le client, ou corriger la situation en `intercontrat`. Critère de qualité du cahier §12.6. |
| `E-SIT-004` | La situation est `intercontrat` mais un client est renseigné. | Vider le client, ou corriger la situation en `mission`. Critère de qualité du cahier §12.6. |

### 3.8 Cercles — champs `F14`, `F15`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-CERCLE-001` | Le cercle principal est absent. | Renseigner le cercle principal. Seule exception : une personne portant la responsabilité DSM peut ne pas en avoir. |
| `E-CERCLE-002` | Le cercle principal indiqué est inconnu dans cette entité. | Utiliser un code de cercle existant. |
| `E-CERCLE-003` | Un cercle secondaire indiqué est inconnu dans cette entité. | Corriger ou retirer la valeur. |
| `E-CERCLE-004` | Le cercle principal est également listé en cercle secondaire. | Retirer la valeur en doublon. Une même personne ne peut pas avoir deux relations actives identiques au même cercle. |
| `E-CERCLE-005` | Un cercle indiqué appartient à une autre entité. | Corriger la valeur. Aucune relation croisée entre entités n'est autorisée. |

### 3.9 DSM — champ `F16`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-DSM-001` | Le consultant est actif mais aucun DSM n'est renseigné. | Renseigner l'adresse e-mail du DSM. Critère de qualité du cahier §12.6. |
| `E-DSM-002` | L'adresse e-mail du DSM ne correspond à aucune personne du fichier ni de la base. | Corriger l'adresse, ou ajouter la ligne du DSM au fichier. |
| `E-DSM-003` | La personne désignée comme DSM ne porte pas de responsabilité DSM active. | Ajouter `DSM` à ses responsabilités Framework, ou désigner un autre DSM. |
| `E-DSM-004` | La personne désignée comme DSM appartient à une autre entité. | Désigner un DSM de la même entité. |
| `E-DSM-005` | La personne est désignée comme son propre DSM. | Corriger la référence. |

### 3.10 Responsabilités Framework — champ `F17`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-RESP-001` | Une responsabilité indiquée n'est pas reconnue. | Utiliser `DSM`, `ESM`, `BOOSTER:<cercle>` ou `OFFICE_MANAGER:<bureau>`. |
| `E-RESP-002` | La responsabilité `BOOSTER` est indiquée sans cercle. | Préciser le cercle, par exemple `BOOSTER:DATA`. |
| `E-RESP-003` | La responsabilité `OFFICE_MANAGER` est indiquée sans bureau. | Préciser le bureau, par exemple `OFFICE_MANAGER:BDE`. |
| `E-RESP-004` | Un scope est indiqué pour `DSM` ou `ESM`, qui n'en acceptent pas. | Retirer le scope. |
| `E-RESP-005` | Le cercle indiqué pour `BOOSTER` est inconnu dans cette entité. | Corriger le code du cercle. |
| `E-RESP-006` | Le bureau indiqué pour `OFFICE_MANAGER` est inconnu dans cette entité. | Corriger le code du bureau. |
| `E-RESP-007` | Plusieurs personnes sont désignées Booster du même cercle. | Ne conserver qu'un seul Booster actif par cercle. Critère de qualité du cahier §12.6. |
| `E-RESP-008` | La personne est désignée Booster dans plusieurs entités. | Une personne ne peut pas être Booster active dans plusieurs entités. |
| `E-RESP-009` | Le bureau `<code>` compte plus de trois responsables actifs. | Un bureau publié en compte entre un et trois. |

### 3.11 Rôles techniques — champ `F18`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-ROLE-001` | Un rôle technique indiqué n'est pas reconnu. | Seul `ENTITY_ADMIN` est accepté à l'import. |
| `E-ROLE-002` | Le rôle `SUPER_ADMIN` ne peut pas être attribué par import. | Retirer la valeur. L'attribution se fait depuis la super-administration, avec audit et alerte de sécurité. |

### 3.12 Autorisation photo — champ `F19`

| Code | Message utilisateur | Résolution |
|---|---|---|
| `E-PHOTO-001` | La valeur d'autorisation de photographie n'est pas reconnue. | Utiliser `oui`, `non` ou `inconnu`, ou laisser le champ vide. |

---

## 4. Avertissements — `W`

Une ligne en avertissement **est importable**. L'avertissement est conservé au rapport et
consultable.

| Code | Message utilisateur | Effet à l'import |
|---|---|---|
| `W-PRESENTATION-001` | La présentation courte est absente. | Le profil est importé et compté comme **incomplet**. Le collaborateur la renseignera lors de sa fiche d'arrivée. |
| `W-DATE-001` | La date d'arrivée est dans le futur. | Le profil est créé en état `future`. Il apparaîtra en arrivée à venir. |
| `W-DATE-002` | La date d'arrivée est antérieure de plus de vingt ans. | Importé tel quel. À vérifier : conversion de date par le tableur probable. |
| `W-DEPART-001` | La date de départ est déjà passée. | Le profil est importé puis **archivé**, sans accès. |
| `W-PHOTO-001` | L'autorisation de photographie est inconnue. | Aucune photo n'est publiée, l'avatar neutre est utilisé. |
| `W-USAGE-001` | Le nom d'usage est identique au nom. | La valeur est ignorée. |
| `W-CERCLE-001` | Le cercle principal est absent, mais la personne porte la responsabilité DSM. | Accepté : un DSM peut ne pas avoir de cercle principal. |
| `W-CLIENT-001` | Le client n'est pas encore activé dans cette entité. | Le client global est activé localement lors de l'import. |
| `W-CASSE-001` | Le nom est intégralement en majuscules. | Importé tel quel. Aucune normalisation automatique n'est appliquée à un nom de personne. |

---

## 5. Décisions requises — `D`

Une ligne en décision requise **n'est pas importée** avant qu'un rôle autorisé ait tranché.
Chaque décision est enregistrée dans `import_decision` avec son auteur, sa date et son motif
(modèle §19.4).

| Code | Message utilisateur | Décision attendue | Qui décide |
|---|---|---|---|
| `D-PERSONNE-001` | Cette adresse e-mail correspond à un profil actif existant. | Mettre à jour le profil existant, ou rejeter la ligne. | ESM, administrateur d'entité, super-administrateur |
| `D-PERSONNE-002` | Cette adresse e-mail correspond à un profil **archivé**. | **Confirmation explicite** requise pour réactiver, sinon rejet. | ESM ou administrateur d'entité, avec confirmation explicite (matrice §14) |
| `D-PERSONNE-003` | Une autre personne porte les mêmes nom et prénom, avec une adresse différente. | Confirmer qu'il s'agit de deux personnes distinctes, ou corriger. | ESM |
| `D-CLIENT-001` | Le client indiqué ressemble à un client existant : `<candidat>`. | Créer un alias vers le client canonique, sélectionner un autre client, ou créer un nouveau client. **Aucune fusion automatique.** | ESM ou DSM du périmètre (matrice §14) |
| `D-CLIENT-002` | Le client indiqué est inconnu du référentiel global. | Créer le client, ou corriger la valeur. | ESM |
| `D-METIER-001` | Le métier indiqué est absent du catalogue de l'entité. | Créer l'entrée au catalogue, ou corriger la valeur. | ESM ou administrateur d'entité |
| `D-CERCLE-001` | Le cercle indiqué est absent du catalogue de l'entité. | Créer le cercle, ou corriger la valeur. | ESM ou administrateur d'entité |
| `D-BUREAU-001` | Le bureau indiqué est absent du catalogue de l'entité. | Créer le bureau, ou corriger la valeur. | ESM ou administrateur d'entité |

Aucune de ces décisions ne peut être prise automatiquement. La validation humaine avant fusion
ou création d'alias est une exigence du cahier §12.3 et de la décision `DATA-005`.

---

## 6. Synthèse

| Niveau | Domaines couverts | Nombre de codes |
|---|---|---:|
| Structure du fichier | 1 | 8 |
| `E` erreurs de ligne | 12 | 42 |
| `W` avertissements | 7 | 9 |
| `D` décisions requises | 5 | 8 |
| **Total** | | **67** |

Comptage recalculé le 01/11/2026, après le retrait de `E-METIER-001` (`DEC-675`, LOT 11 `T5`) —
la ligne barrée du §3.6 ne correspond plus au motif, ce qui est voulu : un code retiré ne doit
plus être compté parmi ceux produits. Avant ce retrait, le comptage du 27 juillet 2026 (LOT 0)
rendait 43/68.

```bash
grep -cE '^\| `E-STRUCT-[0-9]{3}`' codes-erreurs-import.md
grep -cE '^\| `E-(EMAIL|IDENT|ENTITE|DATE|CAT|METIER|SIT|CERCLE|DSM|RESP|ROLE|PHOTO)-[0-9]{3}`' codes-erreurs-import.md
grep -cE '^\| `W-[A-Z]+-[0-9]{3}`' codes-erreurs-import.md
grep -cE '^\| `D-[A-Z]+-[0-9]{3}`' codes-erreurs-import.md
```

Répartition des erreurs de ligne par domaine : e-mail 4, identité 3, entité 3, dates 4,
catégorie 2, métier 0 (retiré), situation 4, cercles 5, DSM 5, responsabilités 9, rôles
techniques 2, autorisation photo 1.

---

## 7. Règles de tenue

- un code stable ne change **jamais** de signification ;
- une règle qui évolue reçoit un **nouveau** code ; l'ancien est marqué obsolète, jamais réutilisé ;
- tout code produit par l'analyseur doit figurer dans ce document ;
- un code présent ici mais jamais produit doit être retiré ou justifié ;
- les messages sont rédigés pour la personne qui corrige le fichier, pas pour le développeur ;
- aucun message ne cite un secret, un jeton, ni le contenu complet d'une ligne.
