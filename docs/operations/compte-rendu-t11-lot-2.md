# Compte rendu — LOT 2, sous-étape `T11`

**Isolation inter-entités**
**Story :** `MVP-L02-US006` — issue `#44`
**Réalisée le :** 20 août 2026
**Décision produite :** `DEC-515`
**Migration produite :** **aucune** — voir §2

---

## 1. Ce que cette sous-étape devait faire, et ce que la mesure a trouvé

Le critère de `US006` : « les contraintes SQL **et services** refusent les relations incohérentes ;
les tests démontrent **l'absence de fuite** ».

**Ma propre recommandation en fin de `T10` était de mesurer avant de poser. Elle était juste.**

| Mesure du 20/08/2026 | Résultat |
|---|---|
| tables portant `entity_id`, donc **locales** | **14** sur 18 |
| clés étrangères entre deux tables locales | **8**, et **toutes composites** |
| clés **simples** entre deux tables locales | **0** |
| couple unique `(id, entity_id)` | **4** tables — exactement les 4 qui sont **cibles** |
| clés vers une table **globale** | **9** — une clé composite y est impossible |

Les huit clés viennent de `T5`, `T7` et `T8`. **Le mécanisme du §25.3 était intégralement appliqué
avant que `T11` ne commence.**

---

## 2. Aucune migration, et le dire valait mieux que d'en inventer une

La fiche §5 annonçait « **onze migrations**, `0002` à `0012`, une par sous-étape de `T1` à `T11` ».
Il y en a **dix**.

Rien ne doit changer au schéma : les huit clés composites ferment tous les chemins, et le couple
unique existe partout où il est nécessaire. **Écrire une migration pour honorer une arithmétique de
plan aurait été inventer** — §6.5. La fiche est corrigée, et son §5 dit désormais pourquoi.

`T9` et `T11` sont les deux sous-étapes de ce lot qui **produisent une preuve au lieu d'une table**.

---

## 3. Ma première mesure ne prouvait rien, et c'est le constat le plus utile

J'ai d'abord énuméré les **clés étrangères** et conclu : aucune clé simple entre deux tables
locales, donc zéro chemin de fuite.

> **Une référence posée SANS clé étrangère aurait produit exactement la même observation.**

Le contrôle aurait annoncé « zéro chemin de fuite » sur un schéma entièrement percé. C'est la
quatrième proposition du §7.0 — un contrôle dont l'échec produirait la même valeur que le succès ne
prouve rien — et je l'ai commise **en écrivant le contrôle censé la respecter**.

**`make isolation-check` part donc des COLONNES.** Les **85** colonnes en `_id` sont examinées une
par une : chacune doit être couverte par une clé étrangère, ou être l'une des trois colonnes
d'auteur du §3.1 — `created_by_person_id`, `updated_by_person_id`, `archived_by_person_id`, **54
occurrences, nommées et comptées**.

**Et ces 54 ne sont pas un trou que j'aurais découvert :** `app/shared/modele.py` trace le choix
depuis `T1`, avec trois motifs — le §3.1 les écrit `uuid null` sans clé, `entity` se crée avant
`person` dans l'ordre du §28, et le RGPD du LOT 10 devra effacer des personnes. Le contrôle les
**classe**, il ne les découvre pas. J'ai vérifié avant de crier au défaut.

---

## 4. `MATCH SIMPLE` — le défaut `T8-1` transposé aux clés étrangères

**PostgreSQL emploie `MATCH SIMPLE` par défaut, et cela veut dire : une clé étrangère composite dont
une colonne est nulle est satisfaite SANS aucune vérification.**

Une clé sur `(circle_id, entity_id)` dont `entity_id` serait nullable ne garantirait donc **rien**
des lignes où l'entité est nulle. C'est exactement `T8-1`, où une clé d'exclusion contenant une
colonne nullable ne contraignait rien sur trois types sur quatre — la même famille, dans un autre
mécanisme.

Le contrôle exige `entity_id NOT NULL` à la source des **8** clés composites. Mesuré : les huit le
sont. Deux colonnes de **portée** sont nullables — `circle_id` et `office_id` — et c'est **légitime** :
le §8.4 les veut absentes pour un `DSM`, et la contrainte de vérification de `T8` les impose pour un
`BOOSTER`. Elles sont **rapportées visiblement**, non exigées : §7.20.

**Trois tables locales portent un `entity_id` nullable** — `allowed_email_domain` §5.4,
`client_alias` §7.3, `technical_role_assignment` §8.6 — et **aucune n'est source d'une clé
composite**. Le contrôle le vérifie plutôt que de l'affirmer.

---

## 5. La nullabilité est dérivée du modèle, et ma dérivation était fausse

Le §2.5 pose que « toutes les tables propres à une entité portent un `entity_id` **non nul** », et le
§3.1 l'écrit littéralement dans le bloc des champs communs. Trois sections déclarent une exception.

**Ma première version cherchait `entity_id` dans la section de chaque table, et échouait sur CINQ
tables conformes** — dont `circle_membership`, dont la section ne le mentionne pas, parce qu'il vient
des champs communs. Le contrôle exigeait une déclaration que le modèle n'a aucune raison de répéter
dix-huit fois : **je prenais l'exception pour la règle**.

Corrigé : le défaut du §3.1 est **dérivé** du modèle, et une section n'en déclare que l'exception. La
correspondance est exigée **dans les deux sens** — une colonne nullable non déclarée est un échec,
une colonne `NOT NULL` déclarée nullable en est un autre.

**Et quatre exceptions portent sur des tables de lots ultérieurs** — `async_job`, `audit_event`,
`onboarding_task_reference`, `onboarding_template`. Elles sont **rapportées, non exigées** : exiger
leur présence serait exiger plus que le critère. L'inquiétude légitime — « et si c'était une table du
LOT 2 qu'on a oubliée ? » — est **déjà couverte ailleurs**, par `TABLES_DECLAREES` dans
`test_socle_modele.py`, et le contrôle le dit.

---

## 6. Le témoin a trouvé qu'un de mes quatre contrôles n'était jamais exercé

`make isolation-temoin` crée deux tables jetables portant **quatre** défauts délibérés, relance le
contrôle en sous-processus, et exige non seulement un code de sortie non nul mais **chacun des quatre
messages attendus** — sans quoi le contrôle pourrait échouer pour une raison étrangère et
l'observation serait la même.

**Sa première version a échoué, et elle avait raison.** Ma table jetable ne portait qu'une clé
**simple** : le contrôle la refusait au titre de « non composite », et **le contrôle `MATCH SIMPLE`
n'était jamais atteint**. Un témoin qui n'exerce pas un contrôle ne prouve rien de ce contrôle.
Corrigé par l'ajout d'une clé composite à `entity_id` nullable.

**Le témoin est dans la CI**, pas seulement dans ce compte rendu : un témoin qui n'a tourné qu'une
fois sur ma machine, c'est le §7.16.

---

## 7. Les dépôts — le cloisonnement rendu structurel, et le refus qui compte

Le critère dit « les contraintes SQL **et services** refusent ». Les dépôts **ne remplacent pas** la
base — `DEC-498` : une règle qui n'existe que dans le code est contournable par tout autre chemin
d'écriture — mais **un dépôt local ne sait pas construire une requête sans son `entity_id`** :
l'oubli n'est pas une faute à éviter, c'est une forme qui n'existe pas. C'est le §7.2 appliqué à
l'accès aux données.

**Le refus le plus important est celui de `DepotGlobal` sur une table locale.** Sans lui, il rendrait
les lignes de **toutes** les entités **en paraissant fonctionner** — la fuite que `US006` interdit,
par le seul chemin que les clés étrangères ne couvrent pas. Le classement local/global est lu sur
`information_schema` : une liste recopiée serait fausse au premier ajout de table.

**`obtenir` rend `None` sur une ligne d'une autre entité**, et non la ligne, et non une exception.
Une ligne d'une autre entité doit être **indistinguable d'une ligne inexistante** : distinguer les
deux révélerait son existence, ce que le §2.5 « refus par défaut » interdit. Même raisonnement qu'un
404 plutôt qu'un 403. Un test l'exige explicitement.

**`creer` refuse un `entity_id` contradictoire au lieu de le remplacer** : remplacer serait pire —
l'appelant croirait avoir écrit dans une entité et aurait écrit dans une autre, sans aucun signal.

---

## 8. Le service referme la boucle de `DEC-514`

`T10` avait posé l'**implication** « DG implique DSM local » en base, et laissé l'**action** du §8.4
au service, parce qu'un déclencheur ne connaît pas l'attributeur et **fabriquerait une trace d'audit
fausse**.

`attribuer_la_categorie_dg` reçoit l'attributeur — il n'a **pas de valeur par défaut**, et c'est tout
le motif — crée la responsabilité `DSM`, **puis** la catégorie. **L'ordre est imposé par le
déclencheur**, et c'est précisément ce que le service évite à son appelant d'avoir à savoir.

**Un test prouve qu'en le contournant, la base refuse toujours** : le service satisfait l'invariant,
il ne s'y substitue pas.

---

## 9. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `make isolation-check` | **code 0** — 14 tables locales, 8 clés composites, 0 référence nue, 0 clé simple |
| `make isolation-temoin` | **code 0** — les **4** défauts détectés et **nommés** |
| `uv run pytest` | **367 tests, 0 échec** — 333 avant `T11` |
| `make check` | **code 0**, code lu par `&& code=0 \|\| code=$?` |
| `make docs-check` | 5 empreintes, 6 séquences, 7 totaux dérivés |
| `make alembic-check` · `code-check` | 1 tête / 1 · 34 fichiers `.py` identiques |
| `make historisation-check` | 7 relations, 10 exclusions, 3 colonnes nullables protégées |
| Témoin **externe** du garde-fou de paramètres | faute introduite → **échec nommant les deux types** ; retirée → 17/17 |

**Les 34 tests nouveaux :** 17 d'isolation — dont **un qui dérive du catalogue la liste des huit
chemins et échouerait sur un neuvième non couvert** — et 17 de dépôts et services.

---

## 10. Six défauts, tous dans mon travail

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T11-1` | Ma dérivation de la nullabilité prenait **l'exception pour la règle**, et le contrôle échouait sur **cinq tables conformes** | la première exécution du contrôle |
| `T11-2` | **Un paramètre lié partagé par deux colonnes**, dans **six fabriques d'un coup** — troisième occurrence après `T4-2` et `T8-3` | `inconsistent types deduced for parameter $1`, 15 tests en échec |
| `T11-3` | **Huit noms de contraintes DEVINÉS** au lieu d'être relevés — je les avais tronqués à vue en supposant la limite des 63 octets | les huit assertions échouaient alors que les **refus avaient bien lieu** |
| `T11-4` | Mon témoin ne portait qu'une clé **simple**, donc le contrôle `MATCH SIMPLE` **n'était jamais exercé** | le témoin lui-même |
| `T11-5` | **Trois** versions du garde-fou de paramètres ont échoué sur du code conforme : sur son propre commentaire, sur sa propre docstring, puis sur `:p` employé pour deux colonnes `uuid` | l'exécution, trois fois |
| `T11-6` | Mon test d'appartenances séquentielles employait **deux périodes non bornées**, qui se chevauchent toujours | `ex_entity_membership_sans_chevauchement`, sur un livrable conforme |

**`T11-2` est le plus sérieux, parce que c'est la troisième fois.** Et la parade a été de **changer
d'outil** plutôt que de promettre de l'attention — §7.2 :
`test_aucun_parametre_lie_ne_couvre_deux_colonnes_de_TYPES_DIFFERENTS` lit les requêtes par `ast` et
les **types dans le catalogue**.

**`T11-5` dit pourquoi ce garde-fou a été si difficile à écrire, et la leçon dépasse ce fichier.**
Deux versions **syntaxiques** ont échoué sur du code conforme :

- la première se déclenchait sur le **commentaire** qui explique le motif interdit ;
- la seconde sur `:p` employé pour `person_id` **et** `assigned_by_person_id` — deux colonnes `uuid`,
  réutilisation parfaitement **légitime**.

**Le discriminant n'est pas dans le texte source : c'est le TYPE de colonne.** Mesuré :
`entity.code` est `character varying(64)` quand `display_name` et `city` sont `text` — d'où l'échec ;
mais `person.email` et `email_normalized` sont **tous deux** `character varying(320)`, donc cette
réutilisation-là ne cassait rien.

> **Un garde-fou à faux positifs est PIRE qu'aucun garde-fou : il apprend à passer outre**, exactement
> comme l'avertissement faux de `make destroy` au §7.21. Une heuristique dans un contrôle est un
> défaut — leçon `T9-2`. Le garde-fou final lit les types réels et n'échoue que sur la forme
> réellement fautive, avec un témoin qui prouve qu'il la voit.

**`T11-3` mérite d'être distingué de `T11-2`.** Les refus **avaient bien lieu** : chaque message était
un `ForeignKeyViolation` nommant la bonne table. Seules mes **valeurs attendues** étaient fausses,
parce que je les avais construites par raisonnement — « le nom fera plus de 63 octets, donc il sera
tronqué là » — au lieu de les lire dans `pg_constraint`. Les noms réels viennent de
`nom_cle_composite()` du socle, doctrine `DEC-509`, et sont bien plus courts. **C'est l'interdit du
§7.0 : n'écris jamais une valeur que tu n'as pas relevée.**

---

## 11. Ce qui n'est PAS couvert

- **`ECART-032`** reste ouvert : l'énoncé large du backlog n'est pas appliqué, le cahier prévaut ;
- **`ECART-031`** reste ouvert : `office` ne déclare aucun état de publication ;
- **la vérification « ESM ou super-administrateur »** de l'attributeur (§8.4) est une règle de
  **permission** : la base n'a aucune notion de l'appelant. **LOT 3**, et `QO-116` porte le sujet
  voisin du moindre privilège ;
- **les 9 clés vers une table globale ne sont pas des chemins de fuite**, et le contrôle les
  **nomme** plutôt que de les taire. `person` est globale par `ARB-DATA-001`, `client` est globale
  avec activation locale. La seule de ces neuf dont le modèle exige une condition de même entité est
  `professional_status_assignment.client_id` (§6.5), et elle est fermée **par le déclencheur de
  `T10`** — un test le montre ;
- **Row-Level Security**, que le §2.5 cite comme « compatibilité future », n'est pas mise en place.
  Rien dans le corpus ne la datant, elle n'est pas inventée ici ;
- **les dépôts ne couvrent pas la mise à jour ni l'archivage** : aucune sous-étape du LOT 2 n'en a
  besoin, et `version` n'est câblée en verrou optimiste que sur `entity_membership`. Les écrire sans
  appelant serait du code non éprouvé.

---

## 12. Ce que `T12` devra savoir

1. **`T12` clôt `US007` et `US008`** : factories, jeu de 25 entités et 5 000 profils, et la recette
   du modèle. C'est la **dernière** sous-étape avant la porte `G2`.
2. **Les factories doivent employer les dépôts**, sinon elles prouveront moins que ce qu'elles
   coûtent : un jeu de données fabriqué en SQL direct pourrait créer des relations croisées que la
   base refuserait, et le diagnostic serait pénible. `DepotLocal.creer` renseigne `entity_id`
   lui-même.
3. **`id` reçoit deux défauts, et c'est pour `T12`** : le défaut Python `uuid4` donne son identifiant
   avant le `flush`, ce dont un graphe d'objets qui se référencent a besoin. Voir `ChampsCommuns`.
4. **L'ordre de création est contraint par quatre déclencheurs**, et une factory qui l'ignore
   échouera : la responsabilité `DSM` avant la catégorie `dg` — ou `attribuer_la_categorie_dg` s'en
   charge ; l'activation locale du client avant une `mission` ; l'entité non archivée avant une
   appartenance ; la responsabilité `DSM` du DSM avant une `dsm_assignment`.
5. **Le jeu de 5 000 profils devra respecter `ex_entity_membership_sans_chevauchement`**, qui porte
   sur `(person_id, period)` **sans clause `WHERE`** : deux appartenances d'une même personne ne
   peuvent pas se chevaucher, même dans deux entités différentes, même archivées. Une mobilité
   inter-entités doit donc être **séquentielle**, avec une `departure_date`. C'est le défaut `T11-6`,
   et il coûterait beaucoup plus cher sur 5 000 lignes.
