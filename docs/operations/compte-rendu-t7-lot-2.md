# Compte rendu — LOT 2, sous-étape `T7`

**Cercles, bureaux et appartenance aux cercles**
**Stories :** `MVP-L02-US001` et `US003` — issues `#39` et `#41`, **toutes deux closes**
**Réalisée le :** 19 août 2026
**Décision produite :** `DEC-511`

---

## 1. Ce que cette sous-étape devait faire

Les trois tables du modèle §8.1 à §8.3, point 7 de l'ordre du §28. **Et elle clôt deux stories** :
l'entité n'est complète qu'avec ses cercles et bureaux, les catalogues qu'avec l'organisation.

---

## 2. Le piège de cette sous-étape était un contresens, et deux témoins l'écartent

Le §8.2 pose deux règles qui semblent voisines et ne le sont pas :

| Règle du §8.2 | Ce qu'elle interdit |
|---|---|
« un seul cercle **principal** actif par appartenance » | deux principaux simultanés |
« **plusieurs cercles secondaires actifs autorisés** » | **rien** — c'est une PERMISSION |

**Une contrainte d'exclusion posée sans clause `WHERE` sur `(entity_membership_id, period)` aurait
interdit les cercles secondaires multiples.** Et — c'est le point — **le livrable aurait paru
correct** : il refuserait bien quelque chose, simplement pas ce qu'il faut. Les tests du principal
seraient passés.

**Le §25.2 confirme la lecture** : il ne liste que le « cercle **principal** » parmi les relations à
contrainte temporelle. L'exclusion est donc **partielle**.

**Deux témoins l'écartent, et le second est celui qui compte :**

- `test_plusieurs_cercles_SECONDAIRES_actifs_sont_autorises` — un principal et **trois** secondaires,
  tous actifs ;
- `test_deux_periodes_SECONDAIRES_qui_se_chevauchent_sont_ACCEPTEES` — sans la clause `WHERE`, **ce
  test échouerait**.

---

## 3. Trois contraintes pour trois règles, et il faut les distinguer

| Contrainte | Règle | Portée |
|---|---|---|
`uq_circle_membership_principal_actif` | §25.1, écrit **littéralement**, sur **deux** conditions | `principal` **et** `ends_at IS NULL` |
`ex_circle_membership_principal_sans_chevauchement` | §25.2, « cercle principal » | **partielle**, `principal` seulement |
`uq_circle_membership_cercle_actif` | §8.2, « deux relations actives identiques au même cercle » | **les deux** types |

**L'index du §25.1 est ombragé par l'exclusion** — deux principaux actifs ont tous deux `ends_at` à
NULL, donc des plages non bornées qui se chevauchent toujours.

> **Il est néanmoins conservé, et la différence avec `T5` est nette.** En `T5`, les deux index retirés
> étaient **ma dérivation**, absente du §25.1. Celui-ci est **écrit dans le modèle**. Même parti que
> `ck_entity_membership_depart_apres_arrivee` en `T4` : une contrainte ombragée ne coûte rien, et
> redevient la seule barrière si l'autre change.

**Et la troisième n'empêche pas plusieurs secondaires** : ce sont des cercles **différents**, donc des
couples `(appartenance, cercle)` différents.

---

## 4. Un résiduel NOMMÉ, et non comblé

Le §8.1 pose « impossible d'archiver un cercle avec des membres actifs ». Règle **inter-tables** — elle
interroge `circle_membership` depuis `circle` — donc portée par un déclencheur, cas type du §25.4.

**Mais le §8.1 ne l'énonce que dans UN sens.** Il ne dit **pas** qu'on ne peut pas ajouter un membre
actif à un cercle **déjà archivé**. L'invariant « archivé ⇒ aucun membre actif » n'est donc pas
globalement garanti.

**Et l'asymétrie est probablement délibérée :** pour `entity`, le §5.1 énonce explicitement les **deux**
sens — « une entité archivée ne reçoit plus de nouveaux membres » — et `DEC-506` les applique. **Le
modèle sait exprimer le sens inverse quand il le veut.** Poser ici une règle qu'il n'écrit pas serait
inventer.

**Un test MONTRE le résiduel** plutôt que de le taire, et sa docstring dit ce qu'il faudra faire si
quelqu'un le comble :

```text
« Si ce test se met un jour a echouer, c'est que quelqu'un a comble le residuel.
  Il faudra alors le remplacer par son inverse ET tracer la decision, pas le
  supprimer. »
```

C'est le parti du §7.20 : **exiger ce qui est exigible, rapporter visiblement ce qui ne l'est pas.**

---

## 5. Deux règles du §8 qui ne sont pas de ce ressort

- « **la couleur ne constitue jamais la seule information visuelle** » (§8.1) est une règle
  d'**interface**, LOT 6. Et `T10` du LOT 1 l'a déjà anticipée : ses jetons de marque sont des
  **surfaces** portant un texte apparié mesuré, jamais des couleurs de texte libres. C'est pourquoi
  `color_token` est une **référence** — `marque.bleu` — et non une valeur hexadécimale : une couleur en
  base contournerait les contrastes mesurés du design system ;
- « **le Booster d'un cercle secondaire ne modifie pas le cercle principal, le DSM, le client ou le
  statut** » (§8.2) porte sur des tables dont deux n'existent pas encore. Règle de **non-effet**, à
  éprouver en `T9` ou `T10`.

Et une du §25.4 attend `T8` : « un bureau publié avec un à trois responsables actifs ». **Le §8.3 ne
pose donc aucune contrainte propre à `office`.**

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
Schéma | **16 tables**, **4** déclencheurs, **4** exclusions, **18** clés étrangères, **7** index partiels |
Chaîne complète depuis une base vide · descente-remontée de `0008` | code 0 |
`alembic check` | **« No new upgrade operations detected »** |
Noms d'index de 63 caractères exactement | **aucun** |
Tests de `T7` | **17 passés** |
Suite complète | **295 pytest** + **116 Vitest** = **411** (était 394) |
11 cibles de contrôle | **0** ×11 |

**Les témoins :**

| Refus | Témoin |
|---|---|
code de cercle ou de bureau dupliqué | le même code existe dans **deux** entités ; un cercle **archivé libère** son code |
deux cercles **principaux** actifs | **trois secondaires actifs acceptés** ; un principal **clos** coexiste avec un nouveau |
chevauchement de périodes **principales** | **deux périodes secondaires qui se chevauchent sont ACCEPTÉES** |
deux relations actives au même cercle | — |
cercle d'une **autre entité** | clé composite du §25.3 |
archiver un cercle à membres actifs | archiver **sans** membre accepté ; archiver aux membres **clos** accepté — « actif » se lit « sans fin » |

---

## 7. Un défaut, dans mon déclencheur, attrapé par les tests

La première version écrivait :

```sql
SELECT count(*) INTO actifs FROM circle_membership
WHERE circle_id = NEW.id AND ends_at IS NULL FOR SHARE;
```

**PostgreSQL le refuse** : « FOR SHARE is not allowed with aggregate functions ». Cinq tests ont
échoué d'un coup.

`PERFORM 1 … FOR SHARE` suivi de `FOUND` fait le même travail **sans agréger**, et conserve le verrou
de lecture. **Et la règle demande s'il EXISTE un membre actif, pas combien** : l'agrégat n'apportait
rien de toute façon.

---

## 8. Ce qui n'est PAS couvert

- **le résiduel du §4** : un membre actif peut être ajouté à un cercle archivé ;
- `FOR SHARE` **ne protège pas d'un INSERT concurrent** — c'est précisément le même résiduel, vu du
  côté de la concurrence ;
- **« un bureau publié avec un à trois responsables actifs »** (§25.4) attend `T8` ;
- **la règle de non-effet du Booster** (§8.2) attend `T9` ou `T10` ;
- **`office` n'a aucune contrainte métier propre**, le §8.3 n'en posant aucune ;
- **`display_order` n'a ni unicité ni continuité**, ni pour les cercles ni pour les bureaux — même
  parti qu'en `T5` pour `job_catalog` : le modèle le nomme sans rien en dire.

---

## 9. Registres

| Registre | Mouvement |
|---|---|
Décisions | **`DEC-511`** les trois tables, l'exclusion partielle, le déclencheur et le résiduel nommé. Total **179**, prochain libre `DEC-512` |
Écarts | aucun mouvement. **30**, dont `ECART-012` **instruit** et en attente de Léa |
Questions | aucun mouvement. **41**, dont **34** ouvertes |
Risques | aucun mouvement |

---

## 10. Ce que `T8` devra savoir

1. **`TABLES_DECLAREES` échouera** : y ajouter `framework_responsibility_assignment`,
   `dsm_assignment`, `technical_role_assignment`, **et** la migration ;
2. **`US004` est la seule story `XL` du lot**, et la fiche lui donne **deux** sous-étapes, `T8` et
   `T9`. `T8` crée les tables, `T9` porte l'historisation et les contraintes temporelles ;
3. **le §25.1 écrit DEUX index partiels pour `T8`**, littéralement :
   `dsm_assignment(consultant_membership_id) UNIQUE WHERE ends_at IS NULL` et
   `framework_responsibility_assignment(circle_id) UNIQUE WHERE responsibility_type='BOOSTER' AND
   ends_at IS NULL`. Le second est partiel sur **deux** conditions, comme celui de `T7` ;
4. **attention à l'ombrage** : un index partiel `WHERE ends_at IS NULL` est **ombragé** par une
   exclusion non partielle sur la même colonne — c'est ce qui a fait retirer deux index en `T5`. Mais
   **ceux-ci sont dans le §25.1**, donc ils se conservent, comme en `T7`. La question à se poser est
   toujours la même : **le modèle l'écrit-il, ou est-ce moi qui le dérive ?** ;
5. **`circle` et `office` exposent leur couple `(id, entity_id)`** : les clés composites du §25.3
   peuvent les viser dès `T8` ;
6. **deux règles du §25.4 arrivent en `T8`** : « un bureau publié avec un à trois responsables actifs »
   et « l'attribution automatique DSM au DG », plus « la vérification du rôle actif du DSM cible ».
   Elles sont **inter-tables** ou **comptantes**, donc déclencheurs ou services — et une règle de
   **comptage borné** (un à trois) ne s'exprime pas par un index : elle exige un déclencheur.
