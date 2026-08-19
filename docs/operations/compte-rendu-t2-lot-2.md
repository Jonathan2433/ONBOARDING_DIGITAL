# Compte rendu — LOT 2, sous-étape `T2`

**Entités, paramètres globaux et locaux, domaines e-mail autorisés**
**Story :** `MVP-L02-US001` — issue `#39`
**Réalisée le :** 19 août 2026
**Décisions produites :** `DEC-501`, `DEC-502`
**Écart ouvert et clos :** `ECART-028`

---

## 1. Ce que cette sous-étape devait faire

Les quatre tables du modèle §5.1 à §5.4, point 2 de l'ordre du §28. **Le premier `CREATE TABLE`
de ce projet.**

**Critère de sortie de la fiche :** `entity(code)` unique éprouvé par témoin, l'archivage **ne
supprime pas** l'historique, un paramètre local **surcharge** le global.

---

## 2. Trois lectures du modèle, posées plutôt que supposées

**Le §5.1 énumère ses colonnes. Les §5.2 et §5.3 n'en énumèrent AUCUNE.** Ils décrivent des
*catégories* de paramétrage — identité visuelle, durées de session, textes d'accueil, contact RGPD,
configuration de l'onboarding — dont la plupart appartiennent à des lots ultérieurs.

**Conséquence retenue :** `platform_setting` et `entity_setting` sont des tables **clé / valeur
`jsonb`, sans catalogue de clés**. La clé est bornée par sa **forme**, jamais par une liste. Un
catalogue en base devrait être modifié par chacun des douze lots restants — c'est exactement le motif
qui a écarté les types `enum` natifs en `DEC-499`.

**`allowed_email_domain.entity_id` est NULLABLE**, le §5.4 l'écrit : « nullable pour un domaine
global ». Le mixin `RessourceLocale` la déclare `NOT NULL` : **il ne s'applique donc pas**, et la
colonne est écrite à la main avec une clé étrangère nullable — PostgreSQL n'exige rien d'une clé
étrangère nulle, ce qui est exactement la sémantique voulue.

**Le §25.2 ne liste PAS cette table** parmi les relations à contrainte temporelle. **Aucune exclusion
n'est donc posée** : ce serait exiger plus que le modèle. `btree_gist` et la colonne `period` étant
déjà là, l'ajouter plus tard reste une migration d'une ligne.

---

## 3. `autogenerate` comme brouillon — et il a révélé quatre défauts de mes propres modèles

`DEC-500` lui assigne le rôle de **brouillon, jamais de livrable**. La relecture du brouillon a
trouvé ceci, qu'aucun test n'aurait attrapé avant plusieurs sous-étapes :

| | Défaut | Ce que le modèle exige |
|:--:|---|---|
| `T2-1` | `activated_at` sortait en `timestamp WITHOUT time zone` | §5.1 écrit **`timestamptz`**. `DateTime(timezone=True)` manquait |
| `T2-2` | `archive_reason` sortait en `VARCHAR` sans borne | §3.1 écrit **`text`**. Défaut hérité de `T1` |
| `T2-3` | **aucune clé étrangère vers `entity`** | Cahier §22.2 : « un `entity_id` **ou** une relation **VÉRIFIABLE** vers une entité ». Une colonne `uuid` sans contrainte n'est pas vérifiable. Et `allowed_email_domain` était créée **avant** `entity` |
| `T2-4` | mes clés étrangères portaient un `name=` explicite | ce qui **écrase la convention de nommage** posée en `T1` : les deux tables locales avaient une contrainte appelée `entity` tout court, sans dire d'où ni vers où |

**`T2-4` a été révélé par un test**, pas par la relecture : le test exigeait le nom conventionnel
`fk_allowed_email_domain_entity_id_entity` et a obtenu `entity`. Un test qui s'était contenté de
`pytest.raises(IntegrityError)` aurait passé sans rien voir.

**Le brouillon a donc payé sa place dès sa première utilisation.** C'est aussi la démonstration de
son statut : livré tel quel, il aurait posé quatre défauts dans le schéma.

---

## 4. Ce qu'`autogenerate` ne pouvait pas écrire

Le §5.1 pose « **`code` immuable après activation** ». Ce n'est pas exprimable par une contrainte de
vérification : la règle compare la valeur **nouvelle** à l'**ancienne**, ce qu'une contrainte de ligne
ne voit pas.

Le §25.4 prévoit ce cas — « appliquées par un service transactionnel [...] Une contrainte ou un
trigger défensif pourra être ajouté lorsque le risque le justifie ». **Un déclencheur est retenu**, et
le motif est **daté** : la couche de services n'arrive qu'en `T11`, soit **neuf sous-étapes** plus
loin. Une règle sans mise en œuvre pendant neuf sous-étapes est une règle qui n'est pas appliquée.

**Trois choix dans sa forme, et chacun sert un contrôle :**

- `BEFORE UPDATE OF code` — il ne se réveille que si `code` figure dans les colonnes affectées ;
- `ERRCODE = 'check_violation'` — le refus arrive comme une **violation d'intégrité**, au même titre
  qu'une contrainte, et non comme une erreur interne ;
- `CONSTRAINT = 'entity_code_immuable_apres_activation'` — le refus est **nommé**, ce qui permet à un
  test d'exiger que l'échec vienne de **cette** règle et pas d'une autre.

**Les deux autres règles du §5.1 ne sont pas de ce ressort, et il faut le dire :**

- « une entité suspendue reste consultable par le super-administrateur » est une règle de **lecture et
  de permissions** — API, LOT 3 et suivants ;
- « une entité archivée ne reçoit plus de nouveaux membres » porte sur `entity_membership`, qui
  n'existe pas encore — **`T4`**.

---

## 5. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
Schéma créé | **4 tables**, 1 déclencheur, 1 fonction, **2 clés étrangères**, 1 colonne générée |
`activated_at` en base | **`timestamp with time zone`** |
Migration `0003` : montée | `0003 (head)` |
**descente** vers `0002` | `1 table, 0 déclencheur, 0 fonction, 0 clé étrangère` |
**remontée** | `0003 (head)`, tout rétabli |
`alembic check` | **« No new upgrade operations detected »** — le déclaré égale le réel |
Tests de `T2` | **26 passés** |
Suite complète | **189 pytest** + **116 Vitest** = **305** (était 280) |
11 cibles de contrôle | **0** ×11 |

**Le témoin décisif de la réversibilité**, et il est indirect : la migration emploie
`CREATE FUNCTION` **sans** `OR REPLACE`. Si la descente n'avait pas supprimé la fonction, la remontée
aurait **échoué**. Elle a rendu code 0 : la descente fait donc bien son travail, et la fonction ne
reste pas orpheline.

**Chaque refus a son témoin :**

| Refus éprouvé | Témoin qui empêche le contrôle d'être creux |
|---|---|
`entity(code)` unique | deux codes différents sont acceptés |
`status` hors liste | **les quatre** valeurs du §5.1 passent |
`code` après activation | il **peut** changer avant activation ; les **autres colonnes** restent modifiables après |
clé de paramètre malformée | trois formes valides sont acceptées |
paramètre local sans entité | le même sur une entité réelle est accepté |
même clé deux fois dans une entité | la **même clé dans deux entités** est acceptée — c'est le sens d'un paramètre local |
domaine non normalisé | trois domaines normalisés sont acceptés |
domaine local sur entité inexistante | `entity_id` **NULL** est accepté — c'est le domaine global du §5.4 |

**Et un défaut de mes propres tests, `T2-5` :** deux tests parcouraient une liste de valeurs fautives
avec un `cx.rollback()` puis `cx.begin()` manuel. SQLAlchemy le signalait — « transaction already
deassociated from connection » — et **la boucle ne prouvait plus rien après le premier tour**.
Remplacé par `begin_nested()`, qui pose un point de sauvegarde : l'échec annule la seule insertion
fautive.

---

## 6. Les deux garde-fous de périmètre, remplacés par deux contrôles aux rôles distincts

`T1` avait laissé deux tests qui devaient échouer en `T2`, et ils ont échoué. Les remplacer par deux
listes écrites en dur aurait créé deux endroits à tenir d'accord. Retenu :

| Contrôle | Nature | Ce qu'il détecte |
|---|---|---|
`test_le_modele_declare_exactement_les_tables_attendues` | liste **écrite en dur** | une table **ajoutée sans décision** |
`test_les_migrations_creent_exactement_les_tables_DECLAREES` | attendu **dérivé** des métadonnées | une **dérive** entre les migrations et le modèle |

**La liste en dur est délibérée, et le test le dit dans sa docstring** pour qu'un futur lecteur ne la
« corrige » pas en la dérivant : elle comparerait alors les métadonnées à elles-mêmes.

---

## 7. Un défaut dans `docs-check`, et c'est le §7.21 pour la troisième fois

`make docs-check` a échoué en accusant le registre : « ses lignes `DEC-4xx` totalisent 83, le corps en
déclare 85 ». **Le registre était juste ; le contrôle était faux.**

Son motif était `` `DEC-4\d\d ``, donc borné à la **centaine 4**. La séquence a franchi `DEC-499` le
18/08/2026, en `T1`. Le contrôle ne voyait plus les lignes `DEC-501+`, et **son message accusait la
source au lieu de lui-même** — ce qui est la forme la plus coûteuse : on cherche le défaut là où il
n'est pas.

Corrigé en `` `DEC-\d+ ``. **Le mot « réalisation » ne désigne pas une centaine.**

---

## 8. `ECART-028` — le modèle place les domaines à deux endroits

Le §5.2 énumère « domaines e-mail autorisés » parmi les catégories de `platform_setting` ; le §5.4
leur consacre **une table dédiée**.

**Lecture retenue : la table fait autorité.** Une table avec ses colonnes nommées et ses règles
d'historisation l'emporte sur un libellé dans une liste à puces. Suivre le §5.2 aurait stocké les
domaines dans une clé `jsonb` et **perdu l'historisation par période, l'interrupteur `active` et le
rattachement optionnel à une entité**.

La lecture est inscrite en tête de `app/entities/modeles.py` — à l'endroit où quelqu'un qui
ajouterait une clé de paramètre la lira.

---

## 9. Ce qui n'est PAS couvert

- **`country_code` n'est pas borné à `FR`.** Le §5.1 dit « `FR` dans le MVP », ce qui décrit la
  donnée attendue et non une contrainte. Le borner empêcherait la seconde entité fictive de la
  démonstration si elle était étrangère ;
- **`timezone` n'est pas validée en base.** La liste des fuseaux vit dans le système d'exploitation et
  change avec lui : une contrainte figée deviendrait fausse à la première mise à jour de tzdata, sans
  que rien ne le signale ;
- **la résolution de la surcharge global / local est APPLICATIVE.** Le test prouve seulement que la
  base accepte la même clé des deux côtés. Quel niveau l'emporte est une règle de service, et aucun
  service n'existe avant `T11` ;
- **« les secrets ne sont jamais enregistrés dans cette table » (§5.2) n'est pas vérifiable en SQL** :
  rien ne distingue un secret d'une chaîne quelconque. Cela relève du service et de la revue ;
- **aucune clé de paramètre n'est créée.** Les tables sont vides à la sortie de `T2`, et c'est voulu.

---

## 10. Registres

| Registre | Mouvement |
|---|---|
Décisions | **`DEC-501`** les quatre tables et leurs quatre lectures · **`DEC-502`** le déclencheur d'immuabilité. Total **170**, prochain libre `DEC-503` |
Écarts | **`ECART-028`** ouvert et clos. Total **28**, dont 21 clos |
Questions | aucun mouvement |
Risques | aucun mouvement |

---

## 11. Ce que `T3` devra savoir

1. **`test_le_modele_declare_exactement_les_tables_attendues` échouera**, et c'est sa fonction :
   ajouter `person` à `TABLES_DECLAREES` **et** la migration correspondante, dans la même pull
   request ;
2. **`autogenerate` vaut le détour, mais relis son brouillon ligne par ligne.** Quatre défauts sur
   quatre tables ici. Vérifie en particulier les **fuseaux horaires**, les **types** exigés par le
   modèle, et l'**absence de `name=`** sur les clés étrangères ;
3. **`person` est GLOBALE** — modèle §6.1 et `ARB-DATA-001` : identité globale, données locales dans
   l'appartenance. Elle ne porte donc **pas** `entity_id`, et `RessourceLocale` ne s'y applique pas ;
4. **aucune table d'authentification**, même si le §28 groupe « `person` et authentification » : c'est
   un ordre global sur tous les lots, pas une frontière de lot. Voir §1.3 de la fiche ;
5. **le patron d'un test de refus** est dans `test_entites.py` : `begin_nested()` pour une liste de
   valeurs fautives, et une assertion sur le **nom** de la contrainte violée.
