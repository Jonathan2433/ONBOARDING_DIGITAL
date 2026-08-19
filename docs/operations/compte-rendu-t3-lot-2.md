# Compte rendu — LOT 2, sous-étape `T3`

**`person` — l'identité globale d'une personne**
**Story :** `MVP-L02-US002` — issue `#40`
**Réalisée le :** 19 août 2026
**Décisions produites :** `DEC-503`, `DEC-504`
**Écart ouvert et clos :** `ECART-029`

---

## 1. Ce que cette sous-étape devait faire

Une seule table, `person`, modèle §6.1, point 3 de l'ordre du §28. **Et aucune table
d'authentification.**

**Critère de sortie de la fiche :** `person(email_normalized)` unique éprouvé par **témoin**,
**normalisation comprise** — deux graphies du même e-mail doivent collisionner.

---

## 2. Le constat qui a orienté toute la sous-étape — `ECART-029`

**Deux passages du corpus se contredisent, et l'un des deux est un raccourci qui a perdu une
exigence.**

| Source | Ce qu'il dit |
|---|---|
| §6.1, contraintes de `person` | « **unicité insensible à la casse** de `email_normalized` » |
| §25.1, index à prévoir | `person(email_normalized) UNIQUE` — un index **simple**, donc **sensible** à la casse |

**L'index spécifié ne satisfait pas la contrainte exigée.** `Jean.Dupont@exalt.com` et
`jean.dupont@exalt.com` sont deux valeurs distinctes pour un index simple : elles **coexisteraient**.

**L'impact n'est pas théorique et il est silencieux.** Deux comptes pour la même personne se
découvriraient au premier magic link ambigu — donc au **LOT 3**, dans une fonctionnalité
d'authentification, avec des conséquences de sécurité.

**Et la bonne réponse n'était pas de choisir entre les deux textes.** Une troisième voie les satisfait
tous les deux : **exiger que la valeur STOCKÉE soit déjà en minuscules**. L'index simple du §25.1
devient alors suffisant, puisque deux graphies ne peuvent pas coexister — l'une des deux ne peut pas
être écrite.

**Elle est aussi plus forte qu'un index fonctionnel sur `lower(email_normalized)`** : celui-ci
empêcherait le doublon mais laisserait entrer une valeur non normalisée dans une colonne nommée
`_normalized`.

---

## 3. Ce que la normalisation NE fait pas, et pourquoi c'est le point le plus important

`normaliser_email()` met en minuscules et retire les espaces de bordure. **Rien d'autre.**

Elle ne retire **pas** les points, ne coupe **pas** à un `+`, et ne touche à aucune particularité de
fournisseur. **Ces règles fusionneraient des personnes DISTINCTES**, et aucun document du corpus ne
les demande : deux collaborateurs peuvent parfaitement s'appeler `j.dupont` et `jdupont`.

**Un test l'exige explicitement**, pour qu'un futur lecteur ne « complète » pas la normalisation en
croyant l'améliorer.

**Même retenue sur la validation de forme.** La contrainte `email_normalise_plausible` refuse un
espace et une arobase en première position, **et c'est tout**. Le corpus ne prescrit aucun format, et
une expression prétendant valider selon la RFC rejette des adresses légitimes : **un refus à l'import
du LOT 9 coûterait plus cher qu'une adresse mal formée stockée**. Un témoin accepte
`jean.dupont+equipe@exalt-company.com` et `j_d@sous.exalt.co.uk`, qu'un validateur strict aurait pu
rejeter.

---

## 4. Une contrainte DÉRIVÉE, et elle est signalée comme telle

Le §6.1 déclare `account_state` et `anonymized_at` **sans lier leurs valeurs**. La contrainte
`anonymisation_coherente` exige leur cohérence dans les deux sens :

- une personne `anonymized` **sans** horodatage rendrait le LOT 10 incapable de dire **quand**
  l'anonymisation a eu lieu, ce que le RGPD exige de tracer ;
- un horodatage **sans** l'état décrirait une anonymisation qui n'a pas pris.

**Elle n'est pas écrite dans le modèle : elle en est dérivée.** Le dire, plutôt que de la faire passer
pour une exigence.

---

## 5. Le déclencheur, et pourquoi il refuse TOUTE sortie

Le §6.1 pose qu'« une personne anonymisée ne peut pas être réactivée sans création d'une nouvelle
identité ». La règle compare l'état **nouveau** à l'**ancien** : aucune contrainte de ligne ne le
voit. Même classe et même parti que `DEC-502`.

**Il refuse toute sortie de `anonymized`, pas seulement vers `active`** — le §6.1 n'en prévoit aucune,
et **l'anonymisation est irréversible par nature** : les données qu'elle a effacées ne sont plus là
pour être restaurées. Un test parcourt les quatre cibles possibles.

**Et le témoin inverse existe** : on doit pouvoir **entrer** dans `anonymized`, et les autres
transitions restent permises. Sans lui, un déclencheur qui refuserait tout changement d'état
passerait.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
Schéma | **6 tables**, 2 déclencheurs, 2 fonctions |
`person` | **aucune colonne `entity_id`** — `ARB-DATA-001` vérifié par contrôle |
**Tables d'authentification** | **0 sur 7** — `user_account`, `magic_link_request`, `user_session`, `auth_event`, `service_account`, `service_token`, `admin_password_credential` |
Migration `0004` | `0004` → `0003` → `0004`, déclencheur et fonction retirés puis rétablis |
`alembic check` | **« No new upgrade operations detected »** |
Tests de `T3` | **19 passés** |
Suite complète | **208 pytest** + **116 Vitest** = **324** (était 305) |
11 cibles de contrôle | **0** ×11 |

**Chaque refus a son témoin :**

| Refus éprouvé | Témoin |
|---|---|
`email_normalized` unique | deux adresses différentes acceptées |
forme normalisée avec majuscules | trois formes minuscules distinctes acceptées |
forme implausible — espace, arobase en tête, arobase absente | trois formes plausibles acceptées, dont deux qu'un validateur strict rejetterait |
`account_state` hors liste | **les cinq** valeurs du §6.1 passent |
`anonymized` sans horodatage | l'inverse aussi : horodatage sans l'état |
sortie de `anonymized` | **les quatre** cibles refusées ; **l'entrée** dans `anonymized` permise ; les autres transitions permises |

**Le brouillon d'`autogenerate` était propre cette fois, et c'est un résultat.** Les quatre défauts de
`T2` — fuseau manquant, `VARCHAR` au lieu de `text`, clé étrangère absente, `name=` écrasant la
convention — ne se sont pas reproduits **parce qu'ils sont devenus des points de relecture**.

---

## 7. Deux défauts, dont un dans mon propre contrôle

### `T3-1` — un témoin qui interrogeait le mauvais artefact

Le message du déclencheur est écrit sur **deux littéraux SQL adjacents**, PostgreSQL les concaténant.
J'ai voulu vérifier que la concaténation avait lieu, et j'ai interrogé `pg_proc.prosrc` :

```text
TEMOIN du message SQL scinde sur deux lignes Python :
  NON — le message est tronque
```

**Le témoin avait tort, pas le code.** `prosrc` contient le **source** de la fonction, où les deux
fragments sont séparés par une apostrophe, un retour à la ligne et des espaces : la chaîne recherchée
n'y est donc pas contiguë. La concaténation a lieu à l'**exécution**.

**Mesuré correctement, en déclenchant réellement l'erreur :**

```text
ERROR:  person.account_state : une personne anonymisee ne peut pas etre reactivee
        (personne 1e953f4f-…, etat anonymized vers active)
```

**La leçon est celle du §7.0 encore une fois** : mon contrôle ne mesurait pas ce qu'il annonçait
mesurer. Et il annonçait un défaut **là où il n'y en avait pas**, ce qui est la variante coûteuse — on
part corriger du code correct. Le test d'intégration `test_une_personne_anonymisee_ne_peut_PAS_etre_reactivee`
porte désormais l'assertion sur le **message levé**, et sa docstring dit pourquoi.

### `T3-2` — une panne extérieure, et elle n'est pas de notre ressort

`make code-refresh` a échoué à la résolution de `docker/dockerfile:1` :

```text
ERROR: DeadlineExceeded: context deadline exceeded
target api: failed to solve
```

**C'est Docker Hub, pas notre code.** Même famille que le piège du §5.2 — un registre qui ne répond
pas se lit facilement comme une image inexistante. Réussi à la seconde tentative, sans aucune
modification. Consigné comme dixième symptôme dans
[`exploitation-locale.md`](exploitation-locale.md) : **relancer, et ne pas chercher un défaut chez
soi.**

---

## 8. Ce qui n'est PAS couvert

- **aucune table d'authentification**, et c'est vérifié par un contrôle et non par la vigilance. Le
  §28 groupe « `person` et authentification » à son point 3, mais c'est un ordre **global** sur
  dix-sept étapes couvrant tous les lots. Rien ne les exige plus tôt : c'est `user_account` qui
  référence `person`, jamais l'inverse ;
- **« le nom et l'e-mail ne sont pas dupliqués dans les tables d'appartenance » (§6.1) n'est pas
  traité ici** : la règle porte sur `entity_membership`, qui n'existe pas encore — **`T4`** ;
- **la normalisation n'est pas appliquée par la base.** La contrainte **refuse** une valeur non
  normalisée, elle ne la corrige pas : c'est à l'appelant d'appeler `normaliser_email()`. Un
  déclencheur qui normaliserait à l'insertion masquerait un défaut d'appel plutôt que de le signaler ;
- **aucune validation d'adresse au-delà du strictement vérifiable**, par choix tracé ;
- **`person` est vide à la sortie de `T3`.** Aucune donnée, et surtout aucune donnée réelle de
  collaborateur — le jeu de test fictif relève de `T12`.

---

## 9. Registres

| Registre | Mouvement |
|---|---|
Décisions | **`DEC-503`** `person` et ses quatre contraintes · **`DEC-504`** le déclencheur d'anonymisation terminale. Total **172**, prochain libre `DEC-505` |
Écarts | **`ECART-029`** ouvert et clos. Total **29**, dont 22 clos |
Questions | aucun mouvement |
Risques | aucun mouvement |

---

## 10. Ce que `T4` devra savoir

1. **`test_le_modele_declare_exactement_les_tables_attendues` échouera** : ajouter
   `entity_membership` à `TABLES_DECLAREES` **et** la migration, dans la même pull request ;
2. **`entity_membership` est le cœur de `US002`**, et sa règle centrale est l'index unique partiel du
   §25.1 : `entity_membership(person_id) UNIQUE WHERE membership_state IN ('future','active')`. Une
   seule appartenance principale active ;
3. **deux règles héritées de sous-étapes précédentes y arrivent** : « une entité **archivée** ne
   reçoit plus de nouveaux membres » (§5.1, notée en `T2`) et « le nom et l'e-mail ne sont pas
   dupliqués dans les tables d'appartenance » (§6.1, notée ici). La seconde est une règle de
   **non-duplication de colonnes**, pas une contrainte : `entity_membership` ne doit **pas** porter de
   colonnes `first_name`, `last_name` ni `email` ;
4. **les états d'appartenance sont au §24.1**, pas au §6.2 : lire les deux ;
5. **le patron d'un déclencheur** est dans `0003` et `0004` : `ERRCODE = check_violation` pour que le
   refus arrive comme une violation d'intégrité, `CONSTRAINT` nommé pour qu'un test puisse exiger que
   l'échec vienne de cette règle, et la descente qui supprime **la fonction** et pas seulement le
   déclencheur.
