# Compte rendu — LOT 2, sous-étape `T5`

**Métiers, affectations métier et situations professionnelles**
**Story :** `MVP-L02-US003` — issue `#41`
**Réalisée le :** 19 août 2026
**Décisions produites :** `DEC-508`, `DEC-509`
**Écart instruit, non tranché :** `ECART-012` — **il attend Léa**

---

## 1. Ce que cette sous-étape devait faire

Les trois tables du modèle §6.3 à §6.5, point 5 de l'ordre du §28. **Et instruire `ECART-012`, échu
dans cette sous-étape.**

**La première migration du lot sans aucun déclencheur** — et ce n'est pas un hasard : toutes les
règles applicables ici s'expriment de façon **déclarative**, parce que les clés étrangères
**composites** du §25.3 transforment une règle inter-tables en contrainte de ligne.

---

## 2. Le cœur de la sous-étape : les clés composites

Le §6.4 exige que « le métier appartienne à la même entité que l'appartenance ». Le §25.3 y répond par
un couple `(id, entity_id)` unique sur les tables référencées.

**Une paire de clés SIMPLES ne suffirait pas, et le test le prouve sur des entités réellement
différentes** : avec `entity_membership(id)` et `job_catalog(id)`, affecter un métier de Lille à une
appartenance de Bordeaux passerait — **les deux identifiants existent, rien ne relierait les
entités**.

**En faisant passer `entity_id` dans les deux clés, l'entité est forcément la même : c'est la MÊME
colonne.** C'est ce qui fait qu'aucun déclencheur n'est nécessaire.

---

## 3. Deux index que j'avais ajoutés, et que la mesure a fait retirer

Le §6.4 pose « une seule affectation métier active », le §6.5 « une seule situation active par
appartenance ». J'avais traduit chacune par un **index unique partiel `WHERE ends_at IS NULL`**, sur
le motif que le §25.1 emploie pour `dsm_assignment`.

**Mesure : ils ne peuvent JAMAIS se déclencher.** Deux relations actives ont toutes deux `ends_at` à
NULL, donc deux plages **non bornées** — et deux plages non bornées se chevauchent **toujours** :
`[janvier,)` contient décembre. **La contrainte d'exclusion les refuse systématiquement la
première.** Les deux tests qui visaient l'index ont échoué en nommant l'exclusion.

**C'est l'inverse de `entity_membership` en `T4`**, où l'index partiel et l'exclusion sont
complémentaires : là-bas l'index porte sur `membership_state` et **non** sur `ends_at`, et deux
appartenances occupantes peuvent avoir des périodes disjointes.

> **Le même motif est complémentaire dans une table et redondant dans l'autre, et seule la mesure les
> distingue.** Recopier un motif du §25.1 parce qu'il ressemble au besoin ne suffit pas.

Les deux index sont retirés. **Ils n'étaient pas dans le §25.1** — qui ne mentionne pas ces tables —
c'était ma dérivation, et elle était inutile. Un index redondant coûte à chaque écriture et **laisse
croire qu'il travaille**.

---

## 4. `DEC-509` — une doctrine de nommage, après deux collisions

| Sous-étape | Nom fautif | Type | Ce que la convention aurait fait |
|---|---|---|---|
`T4` | `sans_chevauchement` | **exclusion** | **rien** : SQLAlchemy n'a aucune clé pour les exclusions |
`T5` | `id_entite_unique` | **UNIQUE** | `uq_<table>_<colonnes>`, **déjà préfixé** |

**La cause commune est le `name=` explicite.** Dans un cas il était obligatoire mais non préfixé ;
dans l'autre il a **écrasé un préfixe qui existait déjà** — exactement le défaut `T2-4`, où un `name=`
sur une clé étrangère avait produit deux contraintes appelées `entity`.

**Et le fait technique qui rend cela grave** : PostgreSQL implémente clés primaires, contraintes
UNIQUE et exclusions par des **index**, et **les noms d'index sont uniques à l'échelle du SCHÉMA** —
pas par table, à la différence des vérifications et des clés étrangères.

**Le contrôle posé compare les noms ENTRE EUX**, et non à un préfixe : c'est ce que PostgreSQL fera de
toute façon, et un contrôle de préfixe laisserait passer deux tables préfixant de la même manière.

### La limite de 63 octets, et le contrôle de `T1` qui a servi quatre sous-étapes plus tard

La convention rend `fk_<table>_<toutes_les_colonnes>_<table_visée>`, ce qui est parfait pour une clé
simple et **explose** pour une clé composite :

```text
fk_professional_status_assignment_entity_membership_id_entity_id_entity_membership
-> 82 caracteres, pour une limite de 63
```

**Trois clés dépassaient : 77, 65 et 82 caractères.** PostgreSQL tronque à 63 octets **en silence**, et
deux noms qui ne diffèreraient qu'après le 63ᵉ caractère entreraient en collision sans qu'aucun message
ne le dise.

**C'est `noms_de_contraintes_trop_longs`, écrit en `T1`, qui les a attrapées.** J'avais d'abord
supposé ce contrôle **aveugle** aux noms conventionnels, au motif qu'ils ne seraient pas dans les
métadonnées. **La mesure a démenti mon hypothèse** : SQLAlchemy les résout dès l'attachement à la
table, et le contrôle les voit.

**Mesuré après correction** : 59 noms au total, le plus long à **56** caractères, et **aucun** nom
d'index de 63 caractères exactement en base — la signature d'une troncature.

---

## 5. `ECART-012` — instruit, et il attend Léa

**`T5` ne l'a pas tranché, et ne devait pas.** Le registre recommande de ne pas modifier le modèle, et
d'arbitrer entre conditionner l'**affichage** ou ajouter une **troisième valeur**. **Léa décide du
produit.**

**Ce que `T5` apporte à la décision est le COÛT mesuré de chaque option**, qui n'était pas connu quand
l'écart a été ouvert :

| Option | Coût |
|---|---|
Conditionner l'affichage par la catégorie professionnelle | **aucune modification du socle** ; tout se joue au LOT 5 |
Ajouter une troisième valeur | **une migration d'UNE LIGNE**, parce que `DEC-499` a choisi une contrainte de vérification et non un type `enum` natif |

**Le coût n'est donc pas ce qui doit départager les deux options** — et c'est utile de le dire, parce
qu'une décision de produit prise sur un argument de coût inexistant serait une mauvaise décision.

### Et une rectification du registre, qui n'est pas cosmétique

**`ECART-012` citait `intercontrat`, la forme française**, comme étant la valeur du modèle. La mesure
sépare nettement les deux usages :

| Forme | Où | Nature |
|---|---|---|
`intercontract` | lignes 352, 361, 770 — **toujours entre accents graves** | la **valeur** stockée |
`intercontrat` | lignes 48, 69, 353, 915, 1710 — en **prose** | le **concept** |

**Quelqu'un implémentant depuis l'écart plutôt que depuis le modèle aurait stocké une valeur que rien
ne reconnaît.** Le champ Source est corrigé, et **un test unitaire fixe l'orthographe** pour que la
confusion ne revienne pas.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
Schéma | **10 tables**, 3 déclencheurs, **3 exclusions**, 38 index |
**Chaîne complète depuis une base vide** | `base` → `0006`, code 0 |
Descente-remontée de `0006` | code 0 dans les deux sens |
`alembic check` | **« No new upgrade operations detected »** |
Noms d'index de 63 caractères exactement | **aucun** — pas de troncature |
Plus long nom d'index | **54** caractères |
Tests de `T5` | **23 passés** |
Suite complète | **257 pytest** + **116 Vitest** = **373** (était 350) |
11 cibles de contrôle | **0** ×11 |

**Les témoins, un par refus :**

| Refus | Témoin |
|---|---|
code de métier dupliqué dans une entité | un métier **archivé libère** son code ; le même code existe dans **deux** entités |
**métier d'une autre entité** | un métier de la **même** entité est accepté ; et l'**autre moitié** de la règle est éprouvée — une appartenance d'une autre entité est refusée aussi |
deux affectations actives | une affectation **close** coexiste avec une active |
chevauchement d'affectations | — |
`mission` sans client | `intercontract` **avec** client refusé aussi : les **deux sens** de la règle |
`intercontrat` en français | **refusé**, la valeur étant `intercontract` |
deux situations actives | une **succession** est acceptée |

---

## 7. Trois défauts, tous dans mon travail

| | Défaut | Ce qui l'a révélé |
|:--:|---|---|
| `T5-1` | **Trois clés composites dépassaient 63 octets** | le contrôle de `T1` — `DEC-509` |
| `T5-2` | **`id_entite_unique` collisionnait**, un `name=` explicite ayant écrasé la convention | l'application de la migration — `DEC-509` |
| `T5-3` | **Deux index unique partiels inatteignables** | deux tests qui ont échoué en nommant l'exclusion — `DEC-508` |

**Et un quatrième, dans la migration elle-même, que seul le rejeu a montré.** Ma descente renommait la
contrainte **avant** de supprimer les tables, donc elle collisionnait avec le nom que `job_catalog`
portait encore. **Une descente doit être le MIROIR de sa montée, non sa copie dans le même ordre.**
Une montée seule ne l'aurait jamais révélé — c'est le §28 qui exige le rejeu, et il a servi.

**Et une hypothèse de ma part que la mesure a démentie**, ce qui est le bon sens de la correction :
j'avais annoncé que le contrôle de longueur de `T1` serait **aveugle** aux noms conventionnels. Il ne
l'est pas.

---

## 8. Ce qui n'est PAS couvert

- **`professional_status_assignment.client_id` n'a pas de clé étrangère** : `client` arrive au point 6
  du §28, donc en `T6`, où la contrainte sera ajoutée. L'alternative — déplacer la table en `T6` —
  aurait contredit l'ordre du §28 et le découpage validé ;
- « **`mission` exige un client ACTIF POUR L'ENTITÉ** » et « **`intercontract` interdit un client
  actif** » supposent `entity_client` : `T6` au plus tôt, vraisemblablement `T9` ou `T10` avec les
  autres règles inter-tables. **Ce qui est appliqué ici est la FORME** que le §6.5 pose dans son
  tableau de colonnes : `client_id` obligatoire en mission, nul en intercontrat ;
- « un changement de statut déclenche l'évaluation du parcours d'onboarding » (§6.5) : **LOT 7** ;
- **`display_order` n'a aucune contrainte d'unicité ni de continuité.** Le §6.3 le nomme sans rien en
  dire ; deux métiers peuvent porter le même ordre, et l'affichage devra départager.

---

## 9. Registres

| Registre | Mouvement |
|---|---|
Décisions | **`DEC-508`** les trois tables et quatre choix · **`DEC-509`** la doctrine de nommage. Total **177**, prochain libre `DEC-510` |
Écarts | **`ECART-012` rectifié et instruit**, il **reste ouvert** — Léa décide. Total inchangé, **30** |
Questions | aucun mouvement |
Risques | aucun mouvement |

---

## 10. Ce que `T6` devra savoir

1. **`TABLES_DECLAREES` échouera** : y ajouter `client`, `entity_client`, `client_alias`, **et** la
   migration ;
2. **`T6` doit AJOUTER la clé étrangère de `professional_status_assignment.client_id`** vers `client`.
   C'est écrit dans l'en-tête de la migration `0006`, et c'est une dette explicite, non un oubli ;
3. **`client` est GLOBAL, `entity_client` est l'activation LOCALE** — §7.1 et §7.2. Donc `client` ne
   porte pas `entity_id`, et `entity_client` en porte un. Le §7.2 permet « d'archiver localement une
   relation sans supprimer le client global » : l'archivage local ne touche pas au global ;
4. **`entity_client` devra exposer un couple `(id, entity_id)`** si quelque chose le référence
   localement — §25.3, et `DEC-509` : **sans `name=`** ;
5. **le §25.1 pose `client_alias`… non, il ne le pose pas.** Ne dérive pas d'index qu'il ne nomme pas
   sans mesurer qu'il sert : `T5` en a retiré deux qui ne pouvaient jamais se déclencher ;
6. **« les rapprochements ne fusionnent rien automatiquement »** est le critère d'acceptation de
   `US003` sur les alias. C'est une règle de **non-action**, donc un témoin : un alias créé ne doit
   pas modifier le client global.
