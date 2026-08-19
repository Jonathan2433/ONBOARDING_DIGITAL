# Compte rendu — LOT 2, sous-étape `T9`

**Historisation et contraintes temporelles**
**Story :** `MVP-L02-US004` — issue `#42`
**Réalisée le :** 19 août 2026
**Décision produite :** `DEC-513`

---

## 1. Ce que cette sous-étape devait faire

**Elle ne crée aucune table.** Les **sept** relations du §25.2 existaient depuis `T4` à `T8`, et chacune
avait son test. La fiche assigne à `T9` trois preuves :

- « **les 7 relations sont comptées** » ;
- « **tout chevauchement est rejeté par la base**, pas seulement par le service » ;
- « toute modification **clôture** la période précédente et en crée une neuve ».

---

## 2. Pourquoi un contrôle qui compte était nécessaire

**Sept contraintes posées une par une dans cinq sous-étapes différentes, c'est exactement la situation
où l'on croit avoir tout fait.** Chaque sous-étape avait ses tests, et aucun contrôle ne disait **combien
de relations étaient couvertes**.

C'est la troisième proposition du §7.0 : *un contrôle qui n'annonce pas combien d'éléments il a examinés
peut toujours n'en avoir examiné qu'un.*

**Et le compte attendu est DÉRIVÉ du §25.2 lui-même**, lu dans le modèle. Recopier « 7 » aurait été un
`ECART-021` en puissance. Le rattachement d'un libellé à une table est, lui, une **interprétation** —
« cercle principal » ne nomme pas `circle_membership` — donc elle est déclarée, et le contrôle **exige
que chaque libellé du modèle soit rattaché**.

```text
info     7 relation(s) enumeree(s) par le §25.2, lues dans le modele
ok       les 7 libelles sont tous rattaches a une table
ok       les 7 relations du §25.2 sont couvertes EN BASE
```

---

## 3. Le contrôle a trouvé un défaut le jour même

**`technical_role_assignment` portait une exclusion dont la clé incluait `entity_id`.** Or `entity_id`
est **nul** pour un `SUPER_ADMIN` — le §8.6 l'exige — et l'opérateur `=` ne rapproche jamais deux NULL :

> **Deux `SUPER_ADMIN` de la même personne aux périodes qui se chevauchent n'auraient PAS été
> détectés.**

**C'est exactement le défaut `T8-1`, dans une table où je croyais l'avoir traité.** J'avais corrigé
`framework_responsibility_assignment` en `T8` et pas celle-ci.

> **Une correction appliquée à la main table par table en oublie une.** Le contrôle mécanique, lui, les a
> toutes examinées. C'est la même leçon que le §7.2 du LOT 1 : quand une classe d'erreur résiste à la
> vigilance, **change d'outil** au lieu de promettre d'être plus attentif.

**Aucun test ne l'avait vu** — les tests de `T8` éprouvaient `ENTITY_ADMIN`, pas deux `SUPER_ADMIN`
concurrents. Un test manquant ne se voit pas ; un compte manquant, si.

---

## 4. Un angle mort d'`alembic check`, mesuré

**Avec 10 exclusions déclarées dans le modèle et 9 en base**, dont une portant une clause `WHERE`
différente :

```text
alembic check : No new upgrade operations detected.   (code 0)
autogenerate  : une migration ne contenant que `pass`
```

**`alembic check` est aveugle aux contraintes d'exclusion : il ne les compare pas.**

Cela **complète la rectification de `DEC-500`** faite en `T4`. Elle disait qu'`autogenerate` *rend*
fidèlement une exclusion — c'est vrai **à la création d'une table**, et faux pour la **détection de
dérive** ensuite. Les deux affirmations sont exactes, elles portent sur des directions différentes.

> **Conséquence pratique : `make historisation-check` est le seul contrôle du dépôt qui détecte une
> dérive d'exclusion.** C'est ce qui justifie son existence, et pourquoi un test de la suite en double
> une partie — le script est une cible séparée, le test tourne à **chaque pull request**.

---

## 5. Une heuristique retirée d'un contrôle

Ma première version tolérait toute clause `WHERE` mentionnant `responsibility_type`, au motif que la
contrainte `portee_selon_le_type` garantissait la non-nullité.

**C'était une heuristique dans un contrôle**, et elle aurait accepté n'importe quelle exclusion
restreinte par ce type, même sans garantie. L'exigence est désormais **exacte** : la clause doit contenir
un `IS NOT NULL` explicite.

**Et le fond est meilleur ainsi** : une contrainte dont la justesse dépend d'une **autre** contrainte est
fragile — la seconde peut disparaître sans que la première le signale. La rendre autoportante coûte une
redondance et se vérifie mécaniquement.

---

## 6. Le critère « clôturer puis créer », et ce que la base garantit vraiment

« Toute modification clôture la relation précédente et crée une nouvelle période » est le critère
d'acceptation de `US004`. **Aucune contrainte ne l'exprime** : c'est un **comportement**.

Ce que la base garantit, et ce que deux tests prouvent :

| Séquence | Résultat |
|---|---|
clore la période, **puis** créer la suivante | **acceptée** — deux périodes, l'historique conservé |
créer **sans** clore | **refusée** par l'exclusion |

> **L'orchestration reste à faire.** Aucun service ne l'applique avant `T11` : **la base refuse la faute,
> elle ne corrige pas l'appelant.** Le dire, plutôt que de laisser croire que le critère est acquis.

---

## 7. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
`make historisation-check` | **7 relations couvertes**, 10 exclusions, 3 colonnes nullables toutes protégées |
Chaîne complète depuis une base vide · descente-remontée de `0010` | code 0 |
`alembic check` | propre — **mais aveugle aux exclusions**, voir §4 |
Tests de `T9` | **8 passés** |
Suite complète | **322 pytest** + **116 Vitest** = **438** (était 430) |
12 cibles de contrôle | **0** ×12 |
Cibles du `Makefile` | **53**, dérivées du fichier |

**Le test du contrôle compte ce qu'il examine** : 10 exclusions et 3 colonnes nullables, confrontées à
des minima. Sans cela, une erreur d'énumération l'aurait rendu creux — il passerait **en n'ayant rien
regardé**.

---

## 8. Quatre défauts, tous dans mon travail

| | Défaut | Ce qui l'a révélé |
|:--:|---|---|
| `T9-1` | **`technical_role_assignment.entity_id` nullable dans une clé d'exclusion** — `T8-1` non corrigé | le contrôle posé par `T9` |
| `T9-2` | **Une heuristique dans mon contrôle** — voir §5 | la relecture |
| `T9-3` | **Un remplacement de message sans assertion de compte**, qui n'a rien fait **silencieusement** | la sortie du contrôle, qui affichait l'ancien texte |
| `T9-4` | **Deux affirmations fausses dans l'en-tête de `0010`** sur le rangement du contrôle : « dans `make check` », puis « dans `make stack-check` » | la lecture du `Makefile`, puis de l'ordre des étapes de la CI |

**`T9-3` est une leçon sur mes propres habitudes.** J'assertis systématiquement le nombre d'occurrences
avant de remplacer un texte — et je l'ai omis une fois. **Le remplacement a échoué sans bruit**, et je
l'ai découvert parce que le contrôle affichait l'ancien message. C'est précisément ce que la règle existe
pour éviter.

**`T9-4` est instructif sur le rangement d'un contrôle.** `historisation-check` exige une base
**migrée** : il n'entre ni dans `make check`, qui est statique, ni dans `make stack-check`, que la CI
lance **avant** `make migrate`. **Un contrôle qui dépend de l'état de la base ne se range pas où l'on
croit.**

---

## 9. Ce qui n'est PAS couvert

- **l'orchestration « clôturer puis créer » attend `T11`** : la base refuse la faute, aucun service ne
  guide l'appelant ;
- **`alembic check` reste aveugle aux exclusions.** Rien ne le corrige — `historisation-check` le
  compense, mais un contributeur qui se fierait à `alembic check` seul serait trompé. C'est écrit dans
  `DEC-513` ;
- **le contrôle vérifie l'existence d'une exclusion par relation, non sa justesse.** Qu'une exclusion
  porte sur la bonne clé reste éprouvé par les tests de `T4` à `T8`, un par relation ;
- **les déclencheurs emploient `FOR SHARE`**, qui ne protège pas d'un INSERT concurrent — résiduel de
  `T7` et `T8`, inchangé.

---

## 10. Ce que `T10` devra savoir

1. **`T10` porte les contraintes de rôles et de périmètres**, `US005`, issue `#43`. Aucune table
   nouvelle n'est attendue : ce sont des **règles**, dont trois sont **inter-tables** ;
2. **trois règles y convergent, toutes notées dans les sous-étapes précédentes** :
   « **`mission` exige un client ACTIF POUR L'ENTITÉ** » (§6.5, noté en `T5` et `T6`) ·
   « **un DG reçoit automatiquement une responsabilité DSM** » (§8.4, noté en `T8` — c'est une **action**,
   non une contrainte) · « **le Booster d'un cercle secondaire ne modifie pas le cercle principal, le
   DSM, le client ou le statut** » (§8.2, noté en `T7` — règle de **non-effet**) ;
3. **le critère de `US005` cite trois règles** : « un seul Booster actif par cercle » — **déjà acquis en
   `T8`** — « DG implique DSM local », et « aucune responsabilité métier active dans plusieurs
   entités » — **déjà acquis en `T8`** par le déclencheur du Booster. **Vérifier avant de refaire** :
   deux des trois sont faites ;
4. **une règle de non-effet se prouve en montrant que rien n'a changé**, comme en `T6` pour les alias :
   comparer l'état avant et après, sur **toutes** les colonnes concernées ;
5. **`ECART-031` est ouvert** et concerne `T8` : le bureau publié. `T10` ne peut pas le clore, l'état de
   publication n'existant toujours pas ;
6. **`ECART-012` attend Léa**, `QO-117` le LOT 9.
