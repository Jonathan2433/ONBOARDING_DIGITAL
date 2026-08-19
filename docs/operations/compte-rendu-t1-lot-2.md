# Compte rendu — LOT 2, sous-étape `T1`

**Socle technique du modèle et extensions PostgreSQL**
**Story :** `MVP-L02-US008` (ouverte en `T1`, close en `T12`) — issue `#46`
**Réalisée le :** 18 août 2026
**Décisions produites :** `DEC-497` à `DEC-500`
**Questions closes :** `QO-111`, `QO-112` · **Question ouverte :** `QO-116`
**Écart ouvert et clos :** `ECART-027`

---

## 1. Ce que cette sous-étape devait faire

Le §3 de la [fiche du LOT 2](fiche-lot-2.md) lui assigne : trancher `QO-111` et `QO-112`, poser la
base déclarative, la convention de nommage des contraintes, les mixins des champs communs du modèle
§3.1, la stratégie de test sur PostgreSQL réel, et la migration des extensions.

**Critère de sortie :** la migration s'applique sur une base vide, se rejoue, **se défait**, et les
**sept** choix techniques du §9.2 sont tranchés et tracés.

**`T1` ne crée aucune table**, et c'est délibéré : si une de ces briques est fausse, l'erreur se
retrouverait dans seize tables au lieu d'une.

---

## 2. Mesurer avant de recommander

**Neuf points étaient ouverts. Aucun n'a été tranché sur une intuition.** Voici ce que la mesure du
18/08/2026 a établi, sur l'état réel.

| Mesure | Valeur |
|---|---|
PostgreSQL servi | **17.7** Debian, `server_version_num` 170007 |
Base avant `T1` | `provider=c` (libc), `en_US.utf8`, `datcollversion` **2.41** |
ICU dans ce binaire | **871 collations**, dont **47 variantes `fr-*`**, toutes déterministes |
`btree_gist` | **disponible**, 1.7, s'installe sans difficulté |
`gen_random_uuid()` | **fournie par « le NOYAU »**, pas par une extension |
`onboarding_app` | **superutilisateur** (`rolsuper = t`) |
Collations non déterministes | **0**. `'Elodie' = 'Élodie'` vaut **`false`** |
Extensions disponibles / installées | **45** / **1** (`plpgsql`) |
Outillage | SQLAlchemy **2.0.51**, Alembic **1.18.5**, psycopg **3.3.4**, pytest **9.1.1** |
`alembic check` | **existe** en 1.18.5 |
Existant | **aucune base déclarative**, `target_metadata = None`, `0001_initial` seule, **aucune fixture de base** |
Corpus sur la collation | **zéro occurrence** de collation, `collate`, ICU, accent ou tri alphabétique |

---

## 3. `QO-111` — la collation, et une mesure qui a réfuté mon propre argument

**Le corpus ne dit rien.** Le modèle §26.1 réclame en revanche « normalisation et index de recherche
sur prénom et nom » et une « recherche tolérante » : le choix a donc une conséquence **documentée**.

**Premier test : les prénoms accentués.** Et il n'a rien prouvé.

```text
libc en_US.utf8 : Ana < Élodie < Émile < Étienne < Èva < Zoé
ICU fr-FR       : Ana < Élodie < Émile < Étienne < Èva < Zoé
TEMOIN          : IDENTIQUES — le test ne discrimine pas
```

**L'argument du « tri français des accents » que je m'apprêtais à avancer était faux.** C'est le
témoin qui l'a dit, pas moi.

**Second test, sur ce qu'un annuaire contient réellement.** Là, la différence est nette :

| Cas | libc `en_US.utf8` | ICU `fr-FR` |
|---|---|---|
Noms composés | `Jeanne < jean-paul < Jeanpierre < Jean Pierre < **Jean-Pierre**` | `Jean Pierre < jean-paul < Jean-Pierre < **Jeanne** < Jeanpierre` |
Particules | `… Delafontaine < **Legall < Le Gall**` | `… Delafontaine < **Le Gall < Legall**` |
Ligatures `Œ`, `ñ` | identiques | identiques |

**Aujourd'hui la base classait « Jeanne » AVANT « Jean-Pierre ».** Le trombinoscope du LOT 5
l'aurait affiché, et un lecteur y aurait vu une erreur.

**Un second argument a été avancé PUIS RETIRÉ, et c'est la mesure qui l'a tué.** J'avais annoncé que
la collation libc n'enregistrait aucune version, donc qu'un changement de règles serait indétectable.
Ma sonde regardait `pg_collation`, **le mauvais endroit**. Au bon endroit :

```text
pg_database.datcollversion — libc actuel : 2.41
                             ICU fr-FR   : 153.128
verdict : l'argument NE TIENT PAS tel que je l'avais formule
```

**Les deux enregistrent une version.** Une non-concordance serait détectée dans les deux cas.

**Il ne restait donc qu'un argument, et il a suffi.** Arbitrage de Jonathan : passer au tri français.
`DEC-497`.

**L'option a été ÉPROUVÉE avant d'être proposée**, sur un conteneur jetable, avec l'empreinte
**relevée** de Compose et non tapée au clavier :

```text
POSTGRES_INITDB_ARGS=--locale-provider=icu --icu-locale=fr-FR --encoding=UTF8
TEMOIN : IDENTIQUES — l initdb a bien pris
```

**Puis appliquée à l'état réel.** Les deux volumes de base ont été supprimés — et **ceux-là
seulement** : les 2 volumes `caddy-data` sont intacts, donc l'autorité approuvée dans le trousseau de
Jonathan n'a pas été touchée. Les bases ne contenaient que `alembic_version` à la révision `0001`.

```text
onboarding_dev | provider=i | locale=fr-FR | VERSION=153.128
TEMOIN 1 : IDENTIQUES — le defaut EST le francais
TEMOIN 2 : DIFFERENTS — le controle discrimine   (contre en_US.utf8)
```

**Deux témoins, et le second est celui qui compte** : sans lui, le test passerait aussi sur une base
restée en libc, puisque les deux collations trient à l'identique les prénoms simplement accentués.

**Déclaré dans le fichier Compose de BASE, pas dans une variable.** Une variable permettrait au
développement et à la recette de **diverger sur leur collation** : deux environnements qui ne trient
pas pareil ne recettent pas la même chose, et l'écart serait invisible.

---

## 4. `QO-112` — une seule extension, et ce qui n'est PAS installé est le plus instructif

**Aucun document ne nommait une extension.** La liste est donc dérivée d'un besoin technique nommé.

| Extension | Décision | Motif |
|---|---|---|
`btree_gist` | **installée** | Une exclusion sur `(uuid WITH =, tstzrange WITH &&)` mêle deux familles d'opérateurs. C'est la condition technique du §25.2 |
`pgcrypto` | **écartée** | **Mesure** : `gen_random_uuid()` est rattachée à « le NOYAU ». L'installer n'apporterait rien |
`uuid-ossp` | écartée | même motif, en plus ancien |
`citext` | écartée | `email_normalized` décide déjà d'une normalisation **applicative** |
`unaccent`, `pg_trgm` | écartées | servent la recherche tolérante du §26.1, qui est au **LOT 5** |

**Les six sont disponibles dans l'image.** Ne pas les installer est un **choix**, pas une
impossibilité : une extension posée par précaution est de la surface d'attaque et du code tiers que
nous n'auditons pas.

**Et `QO-112` annonçait un obstacle qui n'existe pas** : « `CREATE EXTENSION` exige des droits
élevés ». Mesuré, `onboarding_app` **est** superutilisateur — l'obstacle est levé, mais ce qui le
lève est lui-même un écart au cahier §20.1. Voir §7.

---

## 5. Les sept choix du §9.2, tranchés

| | Choix | Retenu | Décision |
|:--:|---|---|---|
| 1 | Clé étrangère des colonnes d'auteur | **`uuid` sans clé étrangère** | `DEC-499` |
| 2 | Représentation d'une période | **bornes + colonne `period` générée** | `DEC-499` |
| 3 | Exclusions en base ou en service | **en base**, service pour le message | `DEC-498` |
| 4 | Énumérations | **contrainte de vérification** | `DEC-499` |
| 5 | Nommage des contraintes | **convention sur la `MetaData`** | `DEC-499` |
| 6 | Génération des UUID | **deux défauts**, Python et serveur | `DEC-499` |
| 7 | `autogenerate` | **brouillon, jamais livrable** | `DEC-500` |

**Deux motifs valent d'être répétés, parce qu'ils sont mesurés et non stylistiques :**

- **la colonne `period` est GÉNÉRÉE**, donc PostgreSQL la calcule. Deux colonnes maintenues en
  parallèle par du code finiraient par se contredire, et la contradiction ne se verrait qu'à la
  lecture ;
- **les énumérations sont des contraintes de vérification et non des types `enum` natifs**, parce que
  `ECART-012` est ouvert, échu dans ce lot, et porte précisément sur l'ajout d'une **troisième**
  valeur à la situation professionnelle. Retirer ou renommer une valeur d'un `enum` natif exige de
  recréer le type et de réécrire les colonnes dépendantes ; altérer une contrainte de vérification
  est une migration d'une ligne.

**Les noms de tables et de colonnes sont ceux du modèle, à la lettre, donc en anglais** — exception
assumée au français du reste du code. Un dictionnaire de traduction serait un endroit où le modèle et
le schéma divergent en silence. Une chose, un nom.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
Migration `0002` : montée | `0002 (head)`, `btree_gist 1.7` installée |
**descente** vers `0001` | code 0, extension **retirée** — témoin vérifié |
**remontée** | code 0, `0002 (head)`, extension réinstallée |
Colonne générée | `["2026-01-01 00:00:00+00","2026-06-01 00:00:00+00")` — **semi-ouverte** |
`make code-check` | 16 fichiers identiques de part et d'autre |
`make alembic-check` | une seule tête, chaîne linéaire |
**Tests du socle** | **20 passés, 0 ignoré** |
Suite complète | **164 pytest** + **116 Vitest** = **280** (était 260) |
`icloud-verify` · `env-check` · `code-check` · `docs-check` · `check` · `audit` | **0** ×6 |
`stack-check` · `api-check` · `web-check` · `alembic-check` · `test-integration` | **0** ×5 |
Cibles du `Makefile` | **52**, dérivées du fichier (était 50) |

**Les témoins qui donnent leur valeur aux tests :**

- **le refus de chevauchement** a **trois** témoins : deux périodes **adjacentes** sont acceptées
  (sinon une contrainte qui refuse tout passerait), deux **sujets différents** peuvent se chevaucher
  (la contrainte porte bien sur le sujet), et le message d'erreur doit **nommer** la contrainte
  d'exclusion (sinon une autre contrainte produirait le même échec) ;
- **le contrôle de longueur d'identifiant** a son témoin : un nom de 64 caractères doit être
  **détecté**. Sans lui, le test passerait de toute façon, le modèle ne déclarant encore aucune
  table ;
- **la collation** a ses deux témoins, décrits au §3.

---

## 7. Les défauts trouvés, dont cinq dans mon propre travail

**Sept défauts. Cinq sont dans mes contrôles ou dans mes affirmations.**

| | Défaut | Ce qui l'a révélé |
|:--:|---|---|
| `T1-1` | **Ma sonde `SHOW lc_collate` a échoué** : ce n'est plus un paramètre en PostgreSQL 16+. L'autorité est `pg_database` | l'erreur lue au lieu d'être masquée |
| `T1-2` | **Mon test de tri ne prouvait rien** : j'avais choisi des prénoms **sans accent**, les deux ordres étaient forcément identiques | le témoin, ajouté ensuite |
| `T1-3` | **J'ai tapé une empreinte `sha256` inventée** dans une commande jetable | elle a échoué ; c'est l'interdit du §7.0, et l'empreinte est désormais **relevée de Compose** |
| `T1-4` | **Ma sonde de version de collation regardait `pg_collation`** au lieu de `pg_database.datcollversion`, ce qui m'a fait annoncer un argument **faux** à Jonathan | la sonde refaite au bon endroit |
| `T1-5` | **`make migrate` tournait sur du code périmé, en sortant en 0** | l'échec observé : `0002` écrite, `0001 (head)` rendu |
| `T1-6` | **Le message de remède de mon contrôle nommait une cible inexistante** | sa première exécution |
| `T1-7` | **Trois tests d'intégration recopiaient `0001` en dur** | leur échec — `ECART-027` |

### `T1-5` mérite un développement : le défaut le plus coûteux du lot s'il n'avait pas été vu

`apps/api` **n'est pas monté en bind** : le code est cuit dans l'image. Une migration écrite sur
l'hôte et non reconstruite est **invisible** du conteneur, et `alembic upgrade head` répond « déjà à
jour », **succès, code 0, rien d'appliqué**.

**En `T3` du LOT 1, le défaut ne pouvait pas se voir** : la migration et l'image naissaient du même
geste. C'est le §7.16 — ce qui n'a jamais tourné autrement n'est pas éprouvé. **Onze migrations
restent à écrire dans ce lot** : le défaut se serait produit onze fois.

**J'ai diagnostiqué avant de corriger** (§7.18), et j'ai mesuré le coût des remèdes :

| Remède | Coût mesuré | Retenu ? |
|---|---|---|
Monter `apps/api` en bind | rapide, mais **rouvre le piège iCloud du §7.17** — un conteneur ne re-résout pas la source d'un montage lié | **non** |
Reconstruire l'image | **3,2 s** avec cache, et le venv est dans `/opt/venv`, hors de `/app` | **oui** |

**Le remède est celui de `DEC-472`** : `make up` appelle `caddy-reload` parce qu'attendre du service
qu'il se rafraîchisse seul ne marche pas. `make migrate` **rafraîchit puis VÉRIFIE**, par comparaison
d'empreintes SHA-256 entre l'hôte et le conteneur. **Le contrôle après le rafraîchissement n'est pas
redondant** : un `build` qui n'aurait pas pris produirait exactement la même observation qu'un
`build` réussi.

**Et `--wait` n'est pas un confort.** `up --detach` rend la main dès que le conteneur est *démarré*,
pas *sain*. Sans l'attente, la CI enchaînerait `api-check` sur une API en cours de démarrage : un
défaut intermittent, donc pénible à attribuer.

### `T1-7` : dériver plutôt que recopier, jusque dans les tests

Trois tests écrits en `T3` affirmaient `== "0001"`. **Justes à leur date**, faux dès la première
migration du LOT 2. Corriger le nombre aurait corrigé l'instance ; onze migrations restent à écrire.
Une fonction `_tete_de_migration()` interroge donc `alembic heads` et **exige d'y trouver exactement
une tête**.

**Éprouvé par témoin** : une révision `0003` jetable a été ajoutée, les trois tests ont **continué à
passer**, puis le témoin a été supprimé. **Sans ce témoin, la correction ne serait pas distinguable
d'un simple remplacement de `0001` par `0002`.**

---

## 8. Ce qui n'est PAS couvert, et il faut le dire

- **`updated_at` n'est pas mise à jour par un `UPDATE` écrit en SQL brut.** L'ORM la renseigne ; seul
  un déclencheur le garantirait, et il n'y en a pas. Limite connue, non un oubli ;
- **`version` est déclarée mais n'est PAS câblée en verrou optimiste.** Ce câblage change la
  sémantique de tout `UPDATE` : c'est un choix par table, à faire dans la sous-étape qui écrit des
  mises à jour ;
- **`alembic check` est câblé mais son verdict est encore creux** : le modèle ne déclare aucune table,
  donc il ne peut rien détecter. Il devient utile en `T2` ;
- **le contrôle de longueur d'identifiant passe à vide** pour la même raison. Son **témoin** est ce
  qui prouve qu'il fonctionne ;
- **`verifier-code-embarque.py` ne couvre que `apps/api/alembic` et `apps/api/app`.** Un écart dans
  les **dépendances installées** ne serait pas vu ; il faudrait comparer les versions de paquets ;
- **l'insensibilité aux accents n'est pas acquise** : `0` collation non déterministe existe, et
  `'Elodie' = 'Élodie'` vaut `false`. La recherche tolérante du §26.1 relève du **LOT 5**, et pourra
  se faire par `unaccent` ou par une collation non déterministe — cette dernière interdisant les
  index de motif.

---

## 9. Registres

| Registre | Mouvement |
|---|---|
Décisions | **`DEC-497`** collation ICU `fr-FR` · **`DEC-498`** `btree_gist` seule et exclusions en base · **`DEC-499`** socle déclaratif, cinq choix · **`DEC-500`** `autogenerate` en brouillon et vérification du code embarqué. Total **168**, prochain libre `DEC-501` |
Écarts | **`ECART-027`** ouvert et clos. Total **27**, dont 20 clos |
Questions | **`QO-111`** et **`QO-112`** closes · **`QO-116`** ouverte (compte superutilisateur contre le moindre privilège, à traiter au LOT 3). **40** entrées, **33** ouvertes — nombres **dérivés du corps du registre**, dont le tableau annonçait 38 pour « 39 entrées » en prose et comptait `QO-085` comme non close |
Risques | aucun mouvement |

---

## 10. Fichiers créés et modifiés

**Créés**

```text
apps/api/app/shared/modele.py            socle declaratif, mixins, enumerations
apps/api/alembic/versions/0002_extensions.py
apps/api/tests/test_socle_modele.py      20 tests
infra/scripts/verifier-code-embarque.py  le controle du defaut T1-5
docs/operations/compte-rendu-t1-lot-2.md
```

**Modifiés**

```text
infra/compose/docker-compose.base.yml    POSTGRES_INITDB_ARGS (DEC-497)
Makefile                                 migrate rafraichit et verifie ; +2 cibles -> 52
apps/api/alembic/env.py                  target_metadata cable
apps/api/app/shared/database.py          docstring devenue fausse, rectifiee (§7.11)
apps/api/tests/test_integration.py       la tete de migration est DERIVEE (ECART-027)
docs/operations/fiche-lot-2.md           T1 barree, les 7 choix tranches
docs/decisions/registre-decisions.md · registre-ecarts.md
docs/operations/registre-questions-ouvertes.md · docs/README.md · CLAUDE.md
```

---

## 11. Ce que `T2` devra savoir

1. **`make migrate` reconstruit maintenant l'image avant d'agir.** C'est voulu. Si tu vois un
   `build`, ce n'est pas une anomalie ;
2. **deux tests échoueront volontairement en `T2`** : `test_le_socle_ne_declare_aucune_table_a_la_sortie_de_T1`
   et `test_la_migration_ne_cree_aucune_table_metier`. Ils sont des garde-fous de périmètre. Les
   mettre à jour avec la **liste des tables attendues**, jamais les supprimer ;
3. **`alembic check` devient utile dès la première table.** L'employer, et ne pas se fier à
   `autogenerate` : il n'écrit ni les `WHERE` des index partiels, ni les exclusions, ni les colonnes
   générées ;
4. **la table d'essai de `test_socle_modele.py` montre le montage complet** — champs communs,
   `entity_id`, période générée, exclusion `gist`, énumération — sur une `MetaData` distincte. S'en
   servir comme patron ;
5. **`ECART-012` est rattaché à `T5`**, et ce n'est pas une décision technique : Léa décide du
   produit.
