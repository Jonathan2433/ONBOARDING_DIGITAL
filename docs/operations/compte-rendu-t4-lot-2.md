# Compte rendu — LOT 2, sous-étape `T4`

**`entity_membership` — la règle centrale de `US002`**
**Story :** `MVP-L02-US002` — issue `#40`
**Réalisée le :** 19 août 2026
**Décisions produites :** `DEC-505`, `DEC-506`, `DEC-507` · **`DEC-500` rectifiée**
**Écart ouvert et clos :** `ECART-030`

---

## 1. Ce que cette sous-étape devait faire

`entity_membership`, modèle §6.2, point 4 de l'ordre du §28. **Elle porte la règle centrale de la
story** : une seule appartenance active ou future par personne.

Et **deux règles héritées** y convergeaient : « une entité archivée ne reçoit plus de nouveaux
membres » (§5.1, notée en `T2`) et « le nom et l'e-mail ne sont pas dupliqués dans les tables
d'appartenance » (§6.1, notée en `T3`).

---

## 2. Deux contraintes se partagent la règle, et aucune ne suffit

**C'est le point le plus important de cette sous-étape**, et il aurait été facile de n'en poser qu'une.

| Contrainte | Ce qu'elle interdit | Ce qu'elle laisserait passer |
|---|---|---|
Index unique **partiel** §25.1<br>`WHERE state IN ('future','active')` | deux appartenances **occupantes** simultanées | deux appartenances **`departed` qui se chevauchent** |
Contrainte d'**exclusion** §25.2<br>sans clause `WHERE` | tout **chevauchement temporel** | deux appartenances **occupantes à des périodes disjointes** |

**Deux tests montrent chacun ce que l'autre contrainte ne verrait pas**, et ils assertent le **nom** de
la contrainte qui refuse :

- `test_UNE_SEULE_appartenance_occupante_par_personne` emploie des périodes **disjointes**, et exige
  que le refus vienne de l'**index** ;
- `test_deux_appartenances_HISTORIQUES_qui_se_chevauchent_sont_refusees` emploie deux états
  `departed`, donc **hors du `WHERE`** de l'index, et exige que le refus vienne de l'**exclusion**.

**Sans ces deux tests, on pourrait croire l'une redondante et la retirer.**

**L'exclusion est sans clause `WHERE`, et c'est délibéré** : le §6.2 écrit « pas de chevauchement
temporel entre deux appartenances » sans restriction d'état. Une personne n'a pas été dans deux
entités en même temps, **même dans le passé**.

---

## 3. Trois lectures du modèle

**`daterange`, pas `tstzrange`.** Le §6.2 déclare `arrival_date` et `departure_date` en **`date`** : le
mixin `Periode` du socle, qui produit un `tstzrange`, **ne s'applique pas**. La convention semi-ouverte
de `T1` est conservée — `[arrivée, départ)` — pour que la fin d'une appartenance et le début de la
suivante puissent porter le **même jour**.

**« Principale » est descriptif, pas une colonne.** Le §6.2 écrit « une seule appartenance active ou
future **principale** », mais n'expose aucune colonne qui distinguerait une appartenance principale
d'une autre, et le §25.1 écrit son index **sans** cette notion. Le §2.2 tranche : « une consultation
d'une autre entité ne crée pas une appartenance supplémentaire ». **Au MVP, toute appartenance est
principale.**

**Le verrou optimiste est câblé, et c'est la première fois.** Le §6.2 l'écrit explicitement :
« `version` | entier | **Concurrence optimiste** ». `T1` avait déclaré la colonne **sans** la câbler, en
posant que ce serait un choix par table. Le test qui le prouve est **le seul de ce fichier à passer par
l'ORM** — et c'est nécessaire, le verrou optimiste *étant* un comportement de l'ORM.

---

## 4. `ECART-030` — le diagramme montre un état que la colonne ne déclare pas

Le §6.2 déclare **quatre** valeurs de `membership_state`. Le diagramme du §24.1, intitulé
« Appartenance à une entité », en montre **cinq** : il ajoute `Anonymized`.

**Lecture retenue : la colonne fait autorité sur le diagramme.** Le diagramme décrit le cycle de vie du
collaborateur vu depuis son appartenance — ce qui est naturel pour un lecteur métier — mais
l'anonymisation est une opération sur l'**identité**, et le §6.1 la place sur `person.account_state`.
**Le diagramme mêle deux niveaux que les tables séparent.**

Ajouter `anonymized` à l'appartenance créerait un **second endroit** où le même fait est représenté.
Deux représentations du même fait divergent.

**Un test l'exige en nommant l'écart**, et la lecture est inscrite dans la docstring de l'énumération —
à l'endroit où quelqu'un tenté d'ajouter la cinquième valeur la lira.

**Une conséquence pour le LOT 10** : anonymiser une personne **ne changera pas** l'état de ses
appartenances. C'est cohérent, mais il faudra que le LOT 10 le **dise** et non le découvre.

---

## 5. `DEC-507` — un défaut de nommage, trouvé par la table d'essai de `T1`

L'exclusion s'appelait d'abord `sans_chevauchement`, sans préfixe. La table jetable des tests du socle
en portait déjà une du même nom, et la seconde création a échoué :

```text
psycopg.errors.DuplicateTable: relation "sans_chevauchement" already exists
```

**Deux faits se combinent, et il faut les deux pour comprendre :**

1. **PostgreSQL implémente une contrainte d'exclusion par un INDEX**, et les noms d'index sont uniques
   à l'échelle du **schéma** — pas par table, à la différence des noms de contraintes ;
2. **la convention de nommage de SQLAlchemy n'a aucune clé pour les exclusions.** Elle connaît `ix`,
   `uq`, `ck`, `fk`, `pk` ; le `name=` d'un `ExcludeConstraint` est pris **tel quel**.

**Le §25.2 prévoit des exclusions sur SEPT relations.** Sans règle, la collision se reproduirait **six
fois**, et chaque fois **à la création de la table** — donc dans une migration, au pire moment.

**Corrigée comme une classe, pas comme une instance** : une fonction `nom_exclusion()`, un contrôle
`noms_exclusions_non_conformes()`, et **son témoin** — sans lequel le contrôle passerait même si la
règle était cassée.

**Et c'est un test de `T1` qui a trouvé le défaut de `T4`.** La table d'essai du socle n'existe que
pour éprouver les mixins ; elle a servi à autre chose. C'est l'argument pour la garder.

---

## 6. Une contrainte OMBRAGÉE, et un test qui a dû dire le vrai

J'attendais que `departure_date < arrival_date` viole la contrainte
`ck_entity_membership_depart_apres_arrivee`. **La mesure dit autre chose :**

```text
psycopg.errors.DataException: range lower bound must be less than or equal to range upper bound
```

**La colonne générée `period` est calculée AVANT que les contraintes de vérification soient
évaluées**, et `daterange(juin, janvier)` est une valeur impossible à construire. **La contrainte n'est
donc jamais atteinte : elle est ombragée par la colonne générée.**

**Elle est néanmoins conservée**, pour deux raisons qui ne sont pas de la superstition : elle est ce que
le §6.2 écrit, et elle redeviendrait la **seule** barrière si la colonne générée était un jour retirée.
Une contrainte ombragée ne coûte rien ; son absence coûterait au premier changement.

**Et le test porte sur le mécanisme réel, pas sur celui que j'espérais.** Un test qui aurait exigé le
nom de la contrainte aurait **échoué sur un livrable conforme** — c'est le §7.20 de la passation, et la
bonne réaction est de faire dire le vrai au contrôle, pas de l'affaiblir.

---

## 7. `DEC-500` rectifiée par la mesure

`DEC-500` affirmait qu'`autogenerate` « n'écrit **pas** les clauses `WHERE` des index partiels, ni les
contraintes d'exclusion ». **C'est trop large, et la mesure le dément** : il a rendu fidèlement les
deux, dès lors qu'elles sont déclarées dans les métadonnées.

**Ce qui fonde réellement la décision reste vrai** : il ne peut pas **inventer** ce qui n'est pas dans
les métadonnées — les **déclencheurs** et leurs fonctions, dont les migrations `0003`, `0004` et `0005`
portent trois exemplaires écrits à la main. Le statut de brouillon est maintenu, et **il s'est justifié
en `T2`** en révélant quatre défauts de modèle.

**Rectifier sa propre décision quand la mesure la dément est le §7.22** : un motif mesuré à une date
n'est pas une vérité acquise.

---

## 8. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
Schéma | **7 tables**, 3 déclencheurs, 3 fonctions, **1 exclusion** |
Migration `0005` | `0005` → `0004` → `0005`, déclencheur, fonction et exclusion retirés puis rétablis |
`alembic check` | **« No new upgrade operations detected »** |
Tests de `T4` | **24 passés** |
Suite complète | **234 pytest** + **116 Vitest** = **350** (était 324) |
11 cibles de contrôle | **0** ×11 |

**Les témoins, un par refus :**

| Refus | Témoin |
|---|---|
deux appartenances occupantes | une appartenance **historique** coexiste avec une active (§2.2) ; **deux personnes** peuvent être occupantes en même temps |
chevauchement temporel | deux appartenances **adjacentes** acceptées ; **deux personnes** peuvent se chevaucher |
`departed` sans date de départ | **`archived` sans date acceptée** — le §24.1 autorise « arrivée annulée » |
départ avant arrivée | départ le **même jour** accepté, `departure_date >= arrival_date` |
trois énumérations | **toutes** les valeurs déclarées acceptées |
clés étrangères | personne **et** entité inexistantes refusées séparément |
**entité archivée** | `draft`, `active`, `suspended` **reçoivent** des membres ; et **déplacer** une appartenance vers une entité archivée est refusé |

---

## 9. Trois défauts, tous dans mon propre travail

| | Défaut | Ce qui l'a révélé |
|:--:|---|---|
| `T4-1` | **Nom d'exclusion sans préfixe**, collision à l'échelle du schéma | la table d'essai de `T1` — `DEC-507` |
| `T4-2` | **Mon aide de test réutilisait un paramètre** pour trois colonnes de types différents : `varchar(64)` et `text`. PostgreSQL a répondu « inconsistent types deduced for parameter $1 » et **dix-huit tests ont échoué d'un coup**, pour une cause qui n'était pas dans le modèle | l'exécution |
| `T4-3` | **Mon attente sur la contrainte de dates était fausse** : elle est ombragée par la colonne générée | l'exécution — §6 |

**`T4-2` mérite une note de méthode.** Dix-huit échecs simultanés font croire à un défaut de
conception. La première chose à faire est de lire **un seul** message d'erreur en entier : il nommait
la cause exacte — un paramètre, deux types. Chercher une cause commune dans le modèle aurait coûté
bien plus.

---

## 10. Ce qui n'est PAS couvert

- **une plage vide échappe à l'exclusion.** `arrival_date = departure_date` est autorisé par le §6.2
  (`>=`), et une plage semi-ouverte de bornes égales est **vide** ; or une plage vide ne chevauche
  rien. Deux appartenances `departed` du même jour coexisteraient donc. **Le résiduel est borné** :
  l'index partiel couvre le cas des appartenances occupantes, et une appartenance de zéro jour est un
  cas de saisie, non un cas métier. Un test le **nomme** plutôt que de le laisser découvrir ;
- **« l'archivage d'une appartenance révoque les accès et clôture les relations actives » (§6.2) n'est
  pas traité** : les relations en question — métier, statut, cercle, DSM, responsabilités — n'existent
  pas encore. Sous-étapes `T5` à `T9` ;
- **`profile_visibility` et `profile_published_at` ne sont PAS liées par une contrainte**, contrairement
  au couple état/horodatage de l'anonymisation en `T3`. **L'analogie ne tient pas** : masquer un profil
  publié est réversible, et `profile_published_at` garde alors la date de **première** publication. Une
  biconditionnelle serait fausse ;
- **aucune donnée.** `entity_membership` est vide à la sortie de `T4`.

---

## 11. Registres

| Registre | Mouvement |
|---|---|
Décisions | **`DEC-505`** la table et ses cinq choix · **`DEC-506`** le déclencheur inter-tables · **`DEC-507`** le nommage des exclusions · **`DEC-500` rectifiée**. Total **175**, prochain libre `DEC-508` |
Écarts | **`ECART-030`** ouvert et clos. Total **30**, dont 23 clos |
Questions | aucun mouvement |
Risques | aucun mouvement |

---

## 12. Ce que `T5` devra savoir

1. **`TABLES_DECLAREES` échouera** : y ajouter `job_catalog`, `membership_job_assignment` et
   `professional_status_assignment`, **et** la migration ;
2. **`ECART-012` est échu en `T5`**, et ce n'est **pas** une décision technique : « `intercontrat`
   imposé à une direction générale ». **Léa décide du produit** ; `T5` instruit et pose la question,
   il ne tranche pas seul ;
3. **le couple `(id, entity_id)` de `entity_membership` est prêt** : les clés étrangères composites du
   §25.3 peuvent le viser dès `T5` ;
4. **toute contrainte d'exclusion se nomme par `nom_exclusion()`** — `DEC-507`. Le contrôle échouera
   sinon ;
5. **`membership_job_assignment` et `professional_status_assignment` sont dans la liste du §25.2** :
   elles auront donc des contraintes d'exclusion, et le §25.1 pose de plus
   `job_catalog(entity_id, code) UNIQUE WHERE archived_at IS NULL` — un index **partiel**, comme celui
   de `T4` ;
6. **`intercontrat` interdit un client actif** (§6.5) : c'est une règle inter-tables, et `client`
   n'existe qu'en `T6`. La noter pour `T9` ou `T10` plutôt que de l'inventer en `T5`.
