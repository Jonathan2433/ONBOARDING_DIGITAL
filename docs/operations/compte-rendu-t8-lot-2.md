# Compte rendu — LOT 2, sous-étape `T8`

**Responsabilités Framework, DSM et rôles techniques**
**Story :** `MVP-L02-US004` (taille **XL**) — issue `#42`
**Réalisée le :** 19 août 2026
**Décision produite :** `DEC-512` · **Écart ouvert :** `ECART-031`

---

## 1. Ce que cette sous-étape devait faire

Les trois tables du modèle §8.4 à §8.6, point 8 de l'ordre du §28. **`US004` est la seule story `XL`
du lot**, et la fiche lui donne deux sous-étapes : `T8` crée les tables, `T9` portera l'historisation et
les contraintes temporelles des sept relations.

---

## 2. Un défaut qui valait trois types sur quatre

**C'est le fait marquant de cette sous-étape**, et il ne se voyait pas.

Ma première version posait **une** contrainte d'exclusion incluant `circle_id`, pour qu'une personne
puisse être Booster de plusieurs cercles :

```text
EXCLUDE (person_id WITH =, responsibility_type WITH =, circle_id WITH =, period WITH &&)
```

**Or `circle_id` est NUL pour un `DSM` ou un `ESM`** — la contrainte `portee_selon_le_type` l'exige — et
**l'opérateur `=` ne rapproche jamais deux NULL.**

> **Deux `DSM` de la même personne aux périodes qui se chevauchent n'auraient PAS été détectés.** La
> contrainte existait, elle était nommée, elle apparaissait dans le catalogue — et elle **ne garantissait
> rien** sur trois types sur quatre.

**Trois exclusions PARTIELLES la remplacent**, chacune sur une clé **sans colonne nullable**, la clause
`WHERE` garantissant cette absence par construction :

| Exclusion | Clé | Portée |
|---|---|---|
`..._booster` | `person_id`, `circle_id` | `WHERE responsibility_type = 'BOOSTER'` |
`..._office_manager` | `person_id`, `office_id` | `WHERE responsibility_type = 'OFFICE_MANAGER'` |
`..._sans_portee` | `person_id`, `responsibility_type` | `WHERE responsibility_type IN ('DSM','ESM')` |

**Et elles n'empêchent que deux affectations IDENTIQUES qui se chevauchent.** Le §8.4 ne dit rien de la
multiplicité pour `DSM`, `ESM` et `OFFICE_MANAGER` : imposer « une seule active par personne » serait
inventer.

**La leçon, sans jargon :** une clé d'exclusion qui contient une colonne nullable **ne contraint rien
sur les lignes où elle est nulle**. Et c'est silencieux — le catalogue montre la contrainte, seul un
test la met à l'épreuve.

---

## 3. Deux permissions, deux interdictions voisines, et les confondre serait invisible

| Nature | Règle du §8.4 ou §8.5 |
|---|---|
**permission** | « une personne peut être Booster de **plusieurs cercles** d'une même entité » |
**interdiction** | « une personne ne peut pas être Booster active dans **plusieurs entités** » |
**permission** | « un DSM peut suivre **plusieurs consultants** » |
**interdiction** | « un consultant actif possède **un seul** DSM actif » |

**Un index unique naïf sur `person_id` casserait les deux permissions**, et le livrable paraîtrait
correct puisqu'il refuserait bien quelque chose. C'est le même piège qu'en `T7` avec les cercles
secondaires, et **c'est la deuxième fois dans ce lot** : les modèles métier énoncent des permissions
aussi souvent que des interdictions, et une permission mal lue devient une contrainte de trop.

**Et l'interdiction du Booster n'est pas exprimable par un index.** Elle demande que toutes les lignes
`BOOSTER` actives d'une personne partagent la **même** entité. **Un index unique exprime « au plus une
ligne », pas « au plus une valeur distincte ».** C'est donc un déclencheur.

---

## 4. `ECART-031` — une règle qui exige un état que la table ne déclare pas

Le §8.4 pose « un bureau possède entre un et trois responsables actifs **lorsqu'il est publié** », et le
§25.4 la reprend.

**Or le §8.3 ne déclare aucun état de publication sur `office`** : `entity_id`, `code`, `name`,
`description`, `location_text`, `display_order`. **La condition n'a rien à quoi se rattacher.**

**Même classe que `ECART-030`** — une règle qui suppose un état absent de la table. Trois issues sont
concevables et **le choix n'est pas technique** : ajouter un état de publication à `office`, rattacher la
publication aux contenus du §15, ou lire « publié » comme « non archivé » — la plus simple et la plus
contestable, puisqu'elle ferait de tout bureau non archivé un bureau publié.

**Et un second motif la rendrait de toute façon impossible en contrainte** : « entre un et trois » est
un **comptage borné**, qu'aucun index n'exprime. Il faudra un déclencheur, le jour où l'état existera.

**La règle est consignée dans l'en-tête de la migration `0009`**, à l'endroit où quelqu'un cherchant
pourquoi elle manque la lira.

---

## 5. Un contrôle de `T1` élargi, et son objet préservé

`contrainte_enumeration` refusait les valeurs en majuscules : son motif était `^[a-z][a-z0-9_]*$`.

**C'était juste pour `T2` à `T7`** — `draft`, `active`, `mission`, `principal` — et **faux ici** : le
§8.4 écrit `DSM`, `ESM`, `BOOSTER`, `OFFICE_MANAGER`, le §8.6 `ENTITY_ADMIN`, `SUPER_ADMIN`, et le §25.1
les cite ainsi : `responsibility_type = 'BOOSTER'`.

> **La casse est une décision du modèle, pas un style de ce dépôt.** Et **l'objet du contrôle n'a jamais
> été la casse** : c'est d'empêcher qu'une valeur portant une apostrophe ne produise du SQL malformé
> dans la contrainte interpolée. Le motif est élargi à la casse libre, **et cet objet est préservé
> entièrement** — un témoin vérifie qu'une apostrophe reste refusée.

C'est le §7.21 **dans un contrôle que j'ai moi-même écrit en `T1`** : juste à sa date, rendu faux par
une table ultérieure.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
Schéma | **19 tables**, **6** déclencheurs, **9** exclusions, **28** clés étrangères, **12** index partiels |
Chaîne complète depuis une base vide · descente-remontée de `0009` | code 0 |
`alembic check` | **« No new upgrade operations detected »** |
Noms de contraintes | **139**, le plus long à **59** caractères |
Tests de `T8` | **19 passés** |
Suite complète | **314 pytest** + **116 Vitest** = **430** (était 411) |
11 cibles de contrôle | **0** ×11 |

**Les témoins :**

| Refus | Témoin |
|---|---|
six formes de portée fautives | **les quatre** formes valides acceptées |
deux Boosters actifs sur un cercle | — |
Booster dans **deux entités** | un Booster **clos** dans l'une permet un nouveau dans l'autre ; **et trois cercles d'une même entité sont acceptés** |
deux `DSM` qui se chevauchent | **une personne peut être `DSM` ET `ESM`** en même temps |
cercle d'une **autre entité** | — |
DSM **sans** responsabilité active | DSM habilité accepté ; **DSM habilité dans une AUTRE entité refusé** |
deux DSM actifs pour un consultant | **un DSM suit trois consultants** ; une **succession** est acceptée |
`ENTITY_ADMIN` sans entité, `SUPER_ADMIN` avec | les deux formes valides acceptées ; **une personne administre deux entités** |

---

## 7. Trois défauts, tous dans mon travail

| | Défaut | Ce qui l'a révélé |
|:--:|---|---|
| `T8-1` | **Une exclusion avec une colonne nullable dans sa clé** — silencieuse sur trois types sur quatre | la relecture, puis un test dédié |
| `T8-2` | **Deux noms de contraintes au-delà de 63 octets** — 65 et 67 | le contrôle de `T1` |
| `T8-3` | **Un paramètre réutilisé pour deux colonnes de types différents** dans mes aides de test | l'exécution |

**`T8-3` mérite d'être dit franchement : c'est exactement le défaut `T4-2`, que j'avais documenté dans
le compte rendu de `T4`.** Cinq tests ont échoué d'un coup pour la même cause qu'alors.

> **Un piège documenté n'est pas un piège désarmé.** C'est ce que le §12 de la passation dit, et c'est
> la troisième fois de ce lot qu'un défaut déjà écrit se rejoue. La parade du LOT 1 était de **changer
> d'outil** plutôt que de promettre plus de vigilance ; ici l'outil serait une aide de test partagée
> entre fichiers, plutôt que réécrite dans chacun.

---

## 8. Ce qui n'est PAS couvert

- **`ECART-031`** : la règle du bureau publié, inapplicable ;
- « **l'administrateur d'entité ne peut pas créer ou clôturer ces affectations** » (§8.4) est une règle
  de **permissions** : API, LOT 3 et suivants ;
- « **un DG reçoit automatiquement une responsabilité DSM dans la même transaction** » (§8.4) est une
  **action**, non une contrainte — le §25.4 la nomme « attribution automatique DSM au DG ». Elle relève
  du service transactionnel, en `T10` ou au LOT 3 ;
- « **toute création ou clôture est auditée** » et « **l'attribution d'un super-administrateur déclenche
  une alerte de sécurité** » (§8.6) supposent `audit_event` et `operational_alert`, §21.1 et §21.2 :
  **LOT 10** ;
- **`assignment_reason` est nullable.** Le §8.4 la dit « obligatoire pour changement sensible » **sans
  définir ce qu'est un changement sensible** : la règle relève du service qui saura de quel changement
  il s'agit. L'inventer ici serait décider à la place du LOT 3 ;
- **les déclencheurs emploient `FOR SHARE`, qui ne protège pas d'un INSERT concurrent** — même résiduel
  qu'en `T7`.

---

## 9. Registres

| Registre | Mouvement |
|---|---|
Décisions | **`DEC-512`** les trois tables, trois exclusions partielles, deux déclencheurs, et le motif élargi. Total **180**, prochain libre `DEC-513` |
Écarts | **`ECART-031` OUVERT** — premier écart ouvert de ce lot qui ne se clôt pas dans sa sous-étape. Total **31**, dont **6 ouverts** |
Questions | aucun mouvement. **41**, dont 34 ouvertes |
Risques | aucun mouvement |

---

## 10. Ce que `T9` devra savoir

1. **`T9` ne crée AUCUNE table.** La fiche lui assigne « historisation et contraintes temporelles » sur
   les **sept** relations du §25.2 — et les sept existent désormais. Son travail est de **vérifier et
   compléter**, non d'ajouter ;
2. **les sept relations du §25.2, et leur état à la sortie de `T8`** :
   appartenance (`T4`, exclusion) · métier (`T5`, exclusion) · statut (`T5`, exclusion) · DSM (`T8`,
   exclusion) · cercle principal (`T7`, exclusion **partielle**) · responsabilités (`T8`, **trois**
   exclusions partielles) · rôles techniques (`T8`, exclusion). **Les sept sont couvertes** : `T9`
   devra le **prouver par un contrôle qui les compte**, et non l'affirmer ;
3. **« toute modification clôture la relation précédente et crée une nouvelle période »** est le critère
   d'acceptation de `US004`, et **aucune contrainte ne l'exprime** : c'est un comportement de **service**.
   `T9` devra soit l'éprouver par une transaction de test, soit dire qu'il attend `T11` ;
4. **attention aux clés d'exclusion contenant une colonne nullable** — défaut `T8-1`. Un contrôle
   systématique serait utile : aucune clé d'exclusion ne doit contenir de colonne nullable sans clause
   `WHERE` qui l'exclut ;
5. **`ECART-012` attend toujours Léa**, et `QO-117` le LOT 9.
