# Compte rendu — LOT 3, sous-étape `T1`

**Moindre privilège PostgreSQL — deux rôles**
**Question ouverte close :** `QO-116`
**Réalisée le :** 20 août 2026
**Décision produite :** `DEC-520` · **Écart consigné :** `ECART-033`
**Migration produite :** **aucune** — un rôle est un objet de cluster, non de schéma

---

## 1. Ce que cette sous-étape devait faire

**C'est ton arbitrage du 20/08/2026**, tracé par `DEC-518` : `QO-116` en **première** sous-étape du
LOT 3, avant l'authentification elle-même.

Le cahier §20.1 pose le moindre privilège. La mesure du 18/08/2026, en `T1` du LOT 2, avait établi que
l'application se connectait avec le compte qu'`initdb` crée : **superutilisateur, propriétaire du
cluster**, capable de détruire la base, de lire toute table et de créer toute extension.

---

## 2. Trois mesures avant de concevoir, et l'une débloquait la sous-étape

| Inconnue | Mesure du 20/08/2026 | Conséquence |
|---|---|---|
| `btree_gist` est-elle **de confiance** ? | **`trusted = t`** sur PostgreSQL 17.7 | un rôle **non superutilisateur** ayant `CREATE ON DATABASE` peut l'installer — **la migration `0002` reste applicable** |
| Qui possède les objets ? | `onboarding_app` : **19 tables**, **196 fonctions** | la propriété doit être **transférée**, sinon aucune migration future ne pourrait modifier une table |
| Combien de séquences ? | **0** | tout est en `uuid` : aucun `GRANT` de séquence n'est nécessaire aujourd'hui |

**Sans la première, cette sous-étape n'aurait pas pu aboutir** : `CREATE EXTENSION` exige normalement
le superutilisateur, et la migration `0002` installe `btree_gist`. Mesurer avant de concevoir a évité
de découvrir l'impasse après avoir tout écrit.

---

## 3. Trois comptes, et pas deux

**`initdb` crée un superutilisateur, et rien ne peut l'empêcher d'exister.** Prétendre le contraire
serait pire que le nommer.

| Compte | Ce qu'il peut | Qui l'emploie |
|---|---|---|
| `POSTGRES_USER` — superutilisateur | tout | **`initdb`, et `make roles-provision`. Rien d'autre** |
| `POSTGRES_MIGRATIONS_USER` | possède le schéma, peut le créer et le modifier | **Alembic, et lui seul** |
| `POSTGRES_RUNTIME_USER` | **lire et écrire des LIGNES** | l'API et le worker |

Ce qui change, c'est que **l'application ne l'emploie plus**. `make privileges-check` le vérifie sur la
connexion **réelle**, pas sur un fichier de configuration.

---

## 4. L'approvisionnement est une cible `make`, pas une migration

**La dépendance serait circulaire.** Un rôle est un objet de **cluster**, non de schéma ; `CREATE ROLE`
exige le superutilisateur ; et une migration exécutée par le rôle de migration ne pourrait pas créer
ce rôle.

`make roles-provision` est appelée par `make up` **après** que la base est saine et **avant** que l'API
ne démarre — même place et même motif que la création du bucket MinIO, `DEC-477`.

**Elle est idempotente, et cela se mesure** : elle dit ce qu'elle a créé et ce qui existait déjà. Au
second appel : « existait deja, mot de passe repose » et « tables=0 fonctions=0 ».

---

## 5. `REASSIGN OWNED` a échoué, et la mesure a donné la cause en deux nombres

Ma première version transférait la propriété d'un geste. PostgreSQL a refusé :

> `cannot reassign ownership of objects owned by role onboarding_app because they are required by the
> database system`

**Diagnostic avant correction** — §7.18. Deux nombres l'ont donné :

| Mesure | Valeur |
|---|---:|
| fonctions du schéma `public` | **196** |
| dont **membres de l'extension** `btree_gist` | **188** |
| **les nôtres** | **8** |

**Une extension n'a pas d'`ALTER … OWNER TO`** : ses fonctions sont des membres, et leur propriété
suit celle de l'extension. `REASSIGN OWNED` butait sur elles, et sur la propriété de la **base**.

Le transfert est donc **explicite**, filtré sur `pg_depend.deptype = 'e'`, et il **compte** ce qu'il a
transféré : **19 tables, 8 fonctions**. Le résiduel est **nommé** : l'extension et la base restent au
superutilisateur, sans conséquence — le rôle de migration a `CREATE ON DATABASE` explicitement.

---

## 6. Les privilèges par défaut — le point le plus subtil

Une table créée par une migration **future** n'existe pas au moment du `GRANT`.

> Sans privilèges par défaut, chaque migration devrait accorder ses droits elle-même. **Et le jour où
> l'une l'oublie, l'application échoue à l'EXÉCUTION avec « permission denied » alors que la migration
> a RÉUSSI.** Le défaut se manifesterait loin de sa cause.

`ALTER DEFAULT PRIVILEGES FOR ROLE migrations IN SCHEMA public` accorde d'avance. **Le contrôle
l'éprouve** en créant une table *après* l'approvisionnement et en la lisant immédiatement avec le rôle
d'exécution.

---

## 7. Le contrôle exige quatre propriétés, et le témoin en est une

`make privileges-check` :

| | Propriété | Résultat mesuré |
|:--:|---|---|
| 1 | le rôle d'exécution n'est **pas** superutilisateur, ne peut créer ni base ni rôle | `rolsuper = f`, et les deux autres aussi |
| 2 | il **échoue** sur le DDL | **5 refus** : `CREATE TABLE`, `DROP TABLE`, `ALTER TABLE`, `CREATE ROLE`, `TRUNCATE` |
| 3 | il **réussit** sur le DML | `SELECT` et `INSERT` autorisés |
| 4 | une table **neuve** est immédiatement lisible | privilèges par défaut actifs |

**La troisième est le témoin indispensable.** Un rôle qui ne pourrait **rien** faire passerait les cinq
refus : sans elle, le contrôle prouverait l'absence de privilège, non le **moindre** privilège.

**Et `TRUNCATE` est refusé délibérément** : c'est un DDL déguisé qui contourne les déclencheurs
`ON DELETE`. Un test le dit explicitement, sans quoi on pourrait croire que « écrire des lignes »
l'inclut.

---

## 8. Contrôles exécutés et résultats

**Tout a été rejoué sur une base RECRÉÉE DE ZÉRO** — volume `db-data` supprimé, `initdb` relancé,
rôles approvisionnés, migrations appliquées. C'est ce que la fiche promettait.

| Contrôle | Résultat |
|---|---|
| `make up` sur une base **vierge** | **code 0** — 8 services sains, rôles créés, bucket MinIO présent |
| `make roles-provision` | **code 0**, et **idempotent** au second appel |
| `make migrate` | **code 0** — les **11** migrations appliquées **par le rôle de migration**, `0011 (head)` |
| `make privileges-check` | **code 0** — 5 refus DDL, DML autorisé, privilèges par défaut actifs |
| `make api-check` · `web-check` | code 0 · code 0 — l'API et la page fonctionnent **avec le rôle borné** |
| `make stack-check` · `ports` · `code-check` · `alembic-check` | code 0 partout |
| `make historisation-check` · `isolation-check` | code 0 · code 0 |
| `uv run pytest` | **390 tests, 0 échec** — 373 avant, dont **204 d'intégration** |
| `make check` | **code 0** |

**Le compte de tests est dérivé, et son écart est expliqué** : 373 → 390, soit **+17**. Treize sont les
tests nouveaux de cette sous-étape. **Les quatre autres, je ne les ai pas écrits** :
`test_1_une_variable_obligatoire_absente_refuse_le_demarrage` est **paramétré sur la liste des
variables obligatoires**, et mes quatre ajouts y ont engendré quatre cas. C'est la discipline du §6.4
qui rend service : une suite dérivée couvre les ajouts sans qu'on y pense.

---

## 9. Sept défauts, tous dans mon travail — et deux garde-fous ont fait leur travail

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T1-1` | `REASSIGN OWNED` refusé : je transférais tout d'un geste sans distinguer les membres d'extension | PostgreSQL, et la mesure 196 / 188 / 8 |
| `T1-2` | Les 4 variables **non transmises aux conteneurs** `api` et `worker` | **le garde-fou de démarrage**, qui a nommé les quatre |
| `T1-3` | Les 4 variables absentes du **harnais de test** — 193 erreurs de connexion | `fe_sendauth: no password supplied` |
| `T1-4` | Neuf tests du socle créent des tables : le rôle d'exécution les refuse | `permission denied for schema public` |
| `T1-5` | Les **bases jetables** n'étaient pas possédées par le rôle de migration | 4 tests de migration en échec |
| `T1-6` | `alembic_version` lu par la connexion d'**exécution** sur une base jetable | `permission denied for table alembic_version` |
| `T1-7` | Une directive `# noqa` placée **après l'ouverture** d'une chaîne multiligne se retrouve **dans le SQL** | échec de syntaxe au transfert |
| `T1-8` | **La liste des variables de lancement de `verifier-images.py` était RECOPIÉE** : mes quatre ajouts ne l'ont pas atteinte, et **la publication de `353e570` a échoué** | l'intégration continue, après la fusion |
| `T1-9` | `make privileges-check` **exige une base migrée et ne le disait pas** : cinq épreuves emploient `entity` comme sujet | la recette, dont la base est vierge |

**`T1-2` est le plus satisfaisant, et ce n'est pas un paradoxe.** Le garde-fou de démarrage du cahier
§20.3 a refusé de démarrer et **a nommé les quatre variables manquantes** :

```text
Demarrage refuse : 4 garde-fou(s) de configuration en echec.
  - POSTGRES_RUNTIME_USER : variable obligatoire absente ou vide
  - POSTGRES_RUNTIME_PASSWORD : variable obligatoire absente ou vide
  - POSTGRES_MIGRATIONS_USER : variable obligatoire absente ou vide
  - POSTGRES_MIGRATIONS_PASSWORD : variable obligatoire absente ou vide
```

**C'est exactement ce pour quoi il existe.** Et `make env-check` avait fait de même une étape plus tôt,
au titre de `ECART-022` : `make env` ne réconcilie jamais un `.env` existant, et il l'a nommé.

**`T1-4`, `T1-5` et `T1-6` ont ceci de commun qu'ils ne sont pas des défauts du livrable** : le rôle
d'exécution refusait **exactement ce qu'on lui demande de refuser**. Ce sont les **tests** qui
supposaient un compte tout-puissant. `moteur_migrations()` rend désormais explicite lesquels font du
DDL, ce qui est une amélioration de lisibilité obtenue par contrainte.

**`T1-7` est le §7.25 dans un troisième costume** : une annotation d'outil placée dans une chaîne
devient une donnée, et une annotation **citée dans un commentaire** est lue comme une annotation —
expliquer la directive en la nommant produisait un avertissement de l'outil lui-même.

---

## 10. `ECART-033` — un contrôle rendu faux par notre propre changement

`make ports` concaténait les deux flux de sortie de Compose puis **parsait le tout en JSON**. Quatre
variables absentes de `.env.recette` ont fait écrire à Compose « The "POSTGRES_MIGRATIONS_USER"
variable is not set », et le contrôle a échoué sur :

```text
json.decoder.JSONDecodeError: Extra data: line 521 column 2 (char 14258)
```

**La trace ne nommait ni Compose, ni l'avertissement, ni la variable.**

**Le contrôle était juste quand il a été écrit**, en `T11` du LOT 1 : rien n'émettait alors
d'avertissement. C'est `ECART-024` à l'identique, et le §7.21 : *un contrôle ne devient pas faux tout
seul, il le devient quand le monde change autour de lui — et ce changement, c'est nous qui le faisons*.

`lancer_json()` sépare les flux, parse `stdout` **seul**, **compte et affiche** les avertissements — le
silence les rendrait invisibles, ce qui serait le §7.6 — et rattrape un `JSONDecodeError` en **nommant
l'environnement** concerné.

---

## 10 bis. Deux défauts découverts APRÈS la fusion, et le premier a rougi la publication

**`T1-8` est le plus sérieux de cette sous-étape, et il est de la même famille que tout le reste.**

`verifier-images.py` portait une liste **recopiée** de sept variables — « les sept variables que l'API
déclare avec un défaut vide ». Mes quatre ajouts ne l'ont pas atteinte, si bien que la tâche
« Lancer les images publiées » a démarré un conteneur **sans** elles. Le conteneur a refusé de
démarrer, **ce qui est exactement ce que le garde-fou doit faire** — et la porte des images est
devenue rouge sur `develop`.

**Deux leçons, et je les ai commises toutes les deux :**

- **`ECART-021`** — une liste recopiée vieillit au premier ajout. La liste est désormais **dérivée de
  `settings.py`**, et un ajout futur l'atteindra sans qu'on y pense ;
- **§7.16** — `make images-verify` **LANCE** les conteneurs, et je ne l'avais pas rejoué. J'avais lancé
  `make check`, qui contient `images-check` **statique** : elle n'ouvre aucune connexion au démon et ne
  démarre rien. **Deux cibles de noms voisins, dont une seule éprouve ce qui m'intéressait.**

**Et la dérivation a elle-même un piège, mesuré :** importer `Parametres` pour lire la liste exigerait
`pydantic`, or ce script est invoqué par `python3` hors environnement virtuel — `images-check` est dans
`make check` et ne demande ni Docker ni dépendance. La lecture passe donc par **`ast`**, qui n'exige
rien, et une forme inattendue **fait échouer** la lecture en la nommant plutôt que de rendre une liste
vide qui passerait.

**Éprouvé localement cette fois** : `make images-build` puis `make images-verify`, **code 0**, `api`,
`worker` et `web` lancés sur `linux/amd64` **et** `linux/arm64`, avec le témoin de plateforme absente.

**`T1-9`** est plus léger mais de la même veine. Sur la recette, dont la base est vierge, cinq épreuves
de `privileges-check` ont échoué avec « relation "entity" does not exist ». Le contrôle **disait
correctement** « a échoué pour une AUTRE raison » — il ne prétendait pas au succès — **mais il ne
nommait pas la cause**. Il vérifie désormais son prérequis **en premier** et donne le remède.

---

## 11. Ce qui n'est PAS couvert

- **aucun garde-fou de DÉMARRAGE ne vérifie que le rôle n'est pas superutilisateur**, et c'est
  délibéré : le cahier §20.3 fixe la liste à **onze**, et faire dépendre le démarrage d'une requête de
  privilèges changerait la sémantique du démarrage. La parade est un **contrôle** — dans `make check`
  pour la partie statique, dans la CI pour la partie base — plus **13 tests** à chaque pull request ;
- **la recette est levée, mais elle ne peut PAS encore prouver le moindre privilège**, et le motif est
  structurel. Mesuré le 20/08/2026 : `docker login ghcr.io` était **déjà fait** — mon avertissement
  était inutile, et j'aurais dû le mesurer avant de le donner. Les deux rôles y sont bien créés,
  nommés `onboarding_recette_migrations` et `onboarding_recette_runtime`. **Mais l'API de recette se
  connecte en `onboarding_app`**, mesuré dans `pg_stat_activity` — parce que la recette exécute
  l'artefact **publié et épinglé par empreinte** (`DEC-486`), dont la révision est `1060ad6`, celle de
  `T8` du **LOT 1**. Le moindre privilège n'y sera effectif qu'après republication et
  `make images-pin`. **À faire avant `G3`**, avec `make separations-check` ;
- **`ALTER DEFAULT PRIVILEGES` ne couvre que le rôle de migration.** Une table créée par le
  superutilisateur — donc hors migration — ne serait pas lisible par l'exécution. C'est voulu : aucune
  table ne doit être créée hors migration, et `make migrations-check` le prouve déjà ;
- **0 séquence aujourd'hui.** Le `GRANT` sur les séquences futures est posé par précaution, mais rien
  ne l'exerce : le modèle emploie `uuid` partout. Si une séquence apparaît, elle sera couverte.

---

## 12. Ce que `T2` devra savoir

1. **`T2` crée les sept tables du modèle §10**, migration `0012`. Elle sera la **première migration
   écrite sous le nouveau régime** : elle s'appliquera avec le rôle de migration, et ses tables seront
   immédiatement lisibles par l'exécution grâce aux privilèges par défaut. **Un test devra le
   vérifier sur les tables réelles**, pas seulement sur une table jetable.
2. **Aucun mot de passe ni jeton en clair dans une colonne.** Le §10.2 dit « aucun mot de passe brut ni
   historique réversible », et le §10.3 « hash uniquement ». Un contrôle devra chercher un **usage**,
   pas un nom de colonne — leçon `T12-2` du LOT 2.
3. **`auth_event` est un historique spécialisé, pas l'audit général.** Le §30.20 — « une action métier
   et son audit sont atomiques » — reste classé **LOT 12** par `make recette-modele-check`, et le
   reclasser exigerait de le prouver.
4. **Le rôle d'exécution ne peut pas créer de table.** Si un test de `T2` en crée une pour éprouver une
   contrainte, il doit employer `moteur_migrations()` — sinon il échouera sur
   « permission denied for schema public », et le message ne dira pas que c'est le rôle qui est en cause.
