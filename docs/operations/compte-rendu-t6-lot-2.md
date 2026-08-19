# Compte rendu — LOT 2, sous-étape `T6`

**Clients globaux, activations locales et alias**
**Story :** `MVP-L02-US003` — issue `#41`
**Réalisée le :** 19 août 2026
**Décision produite :** `DEC-510` · **Question ouverte :** `QO-117`

---

## 1. Ce que cette sous-étape devait faire

Les trois tables du modèle §7.1 à §7.3, point 6 de l'ordre du §28. **Et acquitter la dette de `T5`** :
la clé étrangère de `professional_status_assignment.client_id`.

---

## 2. La dette de `T5`, et pourquoi elle a failli ne pas être acquittée

`T5` avait déclaré `client_id` **sans clé étrangère**, `client` n'existant pas encore, et l'avait
**annoncé dans l'en-tête de la migration `0006`**.

**Le premier brouillon d'`autogenerate` en `T6` ne contenait aucun `create_foreign_key`.** La clé
n'était pas déclarée dans le **modèle** — seulement dans un **commentaire**.

> **Une dette notée dans un commentaire n'est pas une dette outillée.** `autogenerate` ne peut pas
> deviner une intention écrite en prose. Depuis que la clé est déclarée, `alembic check` en garantit
> la présence — et une prochaine dette du même genre devrait être outillée de la même façon, non
> confiée à la mémoire du lecteur.

**Et elle est éprouvée par le COMPORTEMENT, pas par la lecture du catalogue** : un test tente
d'insérer une mission avec un client inexistant et exige le refus, puis réussit avec un client réel.

---

## 3. La normalisation est minimale, et c'est le modèle qui l'impose

`canonical_name` est la forme **normalisée**, `display_name` la forme présentée — même couple que
`email_normalized` / `email` au §6.1. Le §7.1 écrit « nom officiel **unique selon normalisation** »,
donc la voie de `ECART-029` : **la valeur stockée doit déjà l'être**, ce qui rend l'index unique simple
suffisant.

**Et l'étroitesse de cette normalisation n'est pas une facilité : elle est exigée.** Minuscules,
espaces de bordure retirés, espaces internes réduits. **Ni accents, ni ponctuation, ni formes
juridiques.**

| Ce qu'une normalisation agressive ferait | Pourquoi c'est interdit |
|---|---|
`Saint-Gobain` = `Saint Gobain` | **rapprochement automatique** |
`Élevate` = `Elevate` | idem |
`Acme SAS` = `Acme` | idem |

`DATA-005` exige une **validation humaine** des alias, et le §7.3 conclut qu'« aucune proposition de
rapprochement n'écrit directement dans cette table sans validation humaine ».

> **Une normalisation agressive serait précisément le rapprochement automatique que le modèle
> interdit** — et pire : elle le ferait **en amont**, sans même laisser de trace dans `client_alias`.
> Un test unitaire verrouille les trois cas.

---

## 4. Deux tests portent sur des NON-ACTIONS, et ce sont les plus difficiles à écrire

**« Les rapprochements ne fusionnent rien automatiquement »** est le critère d'acceptation de `US003`
sur les alias. Une règle de non-action ne se prouve qu'en montrant que **l'état n'a pas changé**.

Le test crée **deux** clients — `acme corporation` et `acme corp` — puis déclare un alias `acme corp`
pointant vers le **premier**. C'est exactement le cas où une fusion automatique serait tentante et
destructrice. Il compare ensuite **toutes les colonnes de tous les clients** avant et après :

```text
assert apres == avant
assert count(*) == 2   # les deux clients subsistent, homonyme compris
```

**Le second test de non-action est celui de la normalisation** (§3), qui montre qu'elle **ne rapproche
pas** ce que rien n'autorise à rapprocher.

---

## 5. Trois lectures du modèle, dont deux sont des refus d'inventer

**`validated_at` et `validated_by_person_id` sont `NOT NULL`.** Le §7.3 les dit « obligatoire », et
« obligatoire avant usage automatique » aurait pu se lire « nullable, mais inutilisable tant que
nul ». **La dernière phrase du §7.3 tranche** : « aucune proposition de rapprochement n'écrit
directement dans cette table sans validation humaine ». Une proposition en attente ne vit donc **pas**
ici — elle vivra dans `import_decision`, §19.4, au **LOT 9**.

**Le §7.2 n'énumère aucune colonne**, et l'une de ses trois capacités n'en est pas une : « ne pas
afficher tous les clients partout » signifie que **l'ABSENCE de ligne est signifiante**. Aucune
colonne ne dit « visible » — c'est l'existence de la ligne qui le dit, et son `archived_at` qui la
révoque **localement** sans toucher au client global. Un test montre les trois capacités, dont
l'archivage local qui laisse le client global `active` **et** l'autre entité intacte.

**Aucune contrainte d'unicité sur `client_alias`, et c'est `QO-117`.** Le modèle n'en pose aucune, et
le §25.1 ne mentionne pas cette table. **La portée est un choix métier que rien ne tranche** : globale
— un alias désigne un seul client partout — ou par entité, `entity_id` étant nullable, ce qui est
concevable après une fusion d'entreprises. **`T5` a montré ce que coûte une dérivation d'index absente
du modèle** : deux index inatteignables.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
Schéma | **13 tables**, 3 déclencheurs, 3 exclusions, **14 clés étrangères** |
**Dette de `T5` en base** | `fk_professional_status_assignment_client_id_client` **présente** |
Descente-remontée de `0007` | code 0 dans les deux sens |
**Chaîne complète depuis une base vide** | code 0 |
`alembic check` | **« No new upgrade operations detected »** |
Noms d'index de 63 caractères exactement | **aucun** |
Tests de `T6` | **21 passés** |
Suite complète | **278 pytest** + **116 Vitest** = **394** (était 373) |
11 cibles de contrôle | **0** ×11 |

**Les témoins :**

| Refus | Témoin |
|---|---|
`canonical_name` dupliqué | deux noms différents acceptés |
nom non normalisé — majuscules, espaces de bordure, espace double, vide | **quatre** noms normalisés acceptés, dont `saint-gobain`, `élevate` et `acme sas` — précisément ce qu'une normalisation agressive aurait écrasé |
`status` hors liste | les deux valeurs acceptées |
activation dupliquée | **le même client dans deux entités accepté** — c'est tout le propos de `DATA-004` |
alias **sans validation** | alias validé accepté ; alias **global** et alias **local** tous deux acceptés |
clés étrangères | client, entité et **valideur** inexistants refusés séparément |
**mission avec un client inexistant** | mission avec un client **réel** acceptée |

---

## 7. Un défaut, et il n'est pas dans le livrable

**Trois tests de `T5` sont passés au rouge**, parce qu'ils passaient un `uuid` fictif comme client — ce
qui fonctionnait quand la colonne n'avait pas de clé étrangère.

**Ils étaient justes quand ils ont été écrits ; c'est `T6` qui les a rendus faux.** C'est le §7.21, et
c'est la **quatrième** fois dans ce lot. La bonne réaction est de les mettre à jour **en disant
pourquoi**, jamais de contourner la clé.

**Et un quatrième test, celui du refus, a été corrigé sans être en échec** : il passait aussi un `uuid`
fictif à une situation `intercontract`. Il passait — la contrainte de vérification se déclenchant avant
la clé étrangère — mais **l'ordre d'évaluation des contraintes n'est pas garanti**. Un client réel y
est désormais employé, pour que **seule** la contrainte visée puisse échouer.

---

## 8. Ce qui n'est PAS couvert

- **`QO-117`** : aucune unicité sur `client_alias`. Non bloquant pour `G2`, **bloquant pour le LOT 9** ;
- « **`mission` exige un client ACTIF POUR L'ENTITÉ** » (§6.5) porte sur `entity_client`, qui existe
  désormais. Règle inter-tables, **planifiée en `T10`** — « contraintes de rôles et de périmètres ».
  Ce n'est pas une question ouverte, c'est du travail programmé ;
- **`entity_client` n'expose pas de couple `(id, entity_id)`.** Le §25.3 le demande pour les tables
  locales **référencées** ; rien ne la référence aujourd'hui. Même parti qu'`entity_setting` en `T2`.
  L'ajouter le jour où quelque chose la référence est une migration d'une ligne ;
- **`client.status = 'archived'` n'empêche rien.** Le §7.1 déclare les deux valeurs sans dire ce
  qu'archiver interdit. Aucune règle inventée : ce que l'archivage empêche relèvera de `T10` ou du
  service ;
- **aucune donnée.** Les trois tables sont vides à la sortie de `T6`.

---

## 9. Registres

| Registre | Mouvement |
|---|---|
Décisions | **`DEC-510`** les trois tables, quatre choix, et la dette acquittée. Total **178**, prochain libre `DEC-511` |
Écarts | aucun mouvement. **30**, dont `ECART-012` **instruit** et en attente de Léa |
Questions | **`QO-117` ouverte**. **41** entrées, **34** ouvertes — nombres **dérivés du corps** |
Risques | aucun mouvement |

---

## 10. Ce que `T7` devra savoir

1. **`TABLES_DECLAREES` échouera** : y ajouter `circle`, `circle_membership`, `office`, **et** la
   migration ;
2. **`T7` clôt `US001` ET `US003`** — l'entité n'est complète qu'avec ses cercles et bureaux, et les
   catalogues avec l'organisation. Les deux issues `#39` et `#41` pourront être refermées ;
3. **le §25.1 pose DEUX index partiels** pour cette sous-étape : `circle(entity_id, code) UNIQUE WHERE
   archived_at IS NULL` et `office(entity_id, code)` de même, plus
   `circle_membership(entity_membership_id) UNIQUE WHERE membership_type='principal' AND ends_at IS
   NULL` — celui-ci est **partiel sur DEUX conditions**, et il n'est **pas** redondant avec une
   exclusion, contrairement à ceux que `T5` a retirés : il porte sur `membership_type`, pas seulement
   sur `ends_at` ;
4. **`circle` et `office` sont référencés par d'autres tables locales** — `framework_responsibility_
   assignment` vise `circle_id`. Ils ont donc besoin du couple `(id, entity_id)` du §25.3, **sans
   `name=`** (`DEC-509`) ;
5. **deux règles du §25.4 y arrivent** : « un bureau publié avec un à trois responsables actifs » et
   « le refus d'archiver un cercle comportant des membres actifs ». La seconde est **inter-tables**,
   donc un déclencheur, comme `DEC-506` ;
6. **`ECART-014` et `ECART-015` sont rattachés au LOT 6**, pas ici — « représentant de cercle » contre
   « Booster », et l'absence de descriptions de cercles dans le prototype. Ne les instruis pas en `T7`.
