# `apps/api` — API FastAPI

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §15.1, §16.1, §16.2, §18
**Dernière mise à jour :** 7 septembre 2026, `T5` du LOT 5

> **L'API est l'autorité finale sur les permissions.** Jamais le frontend seul — règle non
> négociable, cahier §5 de la matrice : « le frontend peut masquer ou afficher les actions […] mais
> l'API reste l'autorité finale ».

---

## 1. État actuel

**Seize endpoints, dérivés du contrat partagé** — `packages/contracts/src/contrat-api.json` est la
source unique, et un test exige que les chemins du schéma OpenAPI servi soient **exactement** ceux
qu'il déclare :

```bash
python3 -c "import json,pathlib; m=json.loads(pathlib.Path('packages/contracts/src/contrat-api.json').read_text()); [print(f\"{e['methode'].upper():6} {e['chemin']}\") for e in m['endpoints']]"
```

| Famille | Endpoints | Lot |
|---|---|---|
| **santé** | `/health/{live,ready,version}` | LOT 1, `T3` |
| **authentification** | magic link, consommation, connexion, mot de passe, session, déconnexion | LOT 3 |
| **portail** | `/entities`, `/entities/{code}`, `/entities/{code}/permissions` | LOT 4 |
| **collaborateurs** | `/entities/{code}/people`, `…/{appartenance}`, `…/{appartenance}/photo` | LOT 5 |

**29 tables PostgreSQL, 16 migrations, tête `0016`.** Les compter par
`ls apps/api/alembic/versions/*.py | wc -l` — jamais de mémoire.

```bash
make migrate     # applique les 16 migrations
make api-check   # aller-retour applicatif REEL, pas une sonde de sante
```

### Les trois endpoints de santé, et leur particularité

| Endpoint | Ce qu'il fait |
|---|---|
| `/health/live` | Vivacité du processus. **Ne sonde aucune dépendance**, volontairement |
| `/health/ready` | Sonde réellement PostgreSQL, Redis et MinIO. **503** si l'une manque |
| `/health/version` | Version et empreinte de commit, **gravées dans l'image** par `ARG`→`ENV` (`DEC-480`) |

> **Un 503 de `/health/ready` porte la MÊME forme JSON qu'un 200**, et le frontend l'accepte comme
> un état exploitable depuis `T5` du LOT 1. Le lire comme une erreur réseau jetterait le diagnostic
> au moment où il devient utile.

---

## 2. Les modules de `app/`, et ce que chacun porte

```text
app/
├── configuration/settings.py   les 11 garde-fous de demarrage du cahier §20.3
├── shared/                     socle : modele declaratif, depots, moteurs, erreurs, journal
├── health/                     les trois sondes du §18.7
├── auth/                       les 7 tables du §10, sessions, CSRF, debit, comptes de service
├── entities/                   le portail national et la resolution par code
├── people/                     trombinoscope, recherche, fiche profil
├── media/                      la miniature de photo et la lecture d'objet MinIO
├── clients/ · organization/    clients, cercles, bureaux, responsabilites
└── permissions/                la resolution de la matrice §23.1
```

### `shared/database.py` — **DEUX moteurs, et employer le mauvais coûte une heure**

Depuis `T1` du LOT 3 (`DEC-520`), la base a **trois** comptes PostgreSQL :

| Compte | Ce qu'il peut | Qui l'emploie |
|---|---|---|
| `onboarding_app` | **tout** — superutilisateur créé par `initdb` | `initdb` et `make roles-provision`. **rien d'autre** |
| `onboarding_migrations` | possède le schéma, crée et modifie les tables | **Alembic seul**, et les rares tests qui créent des objets |
| `onboarding_runtime` | **lire et écrire des LIGNES** — rien de plus | l'API, le worker, et **tous** les tests d'intégration |

```python
moteur(parametres)              # le moteur d'EXECUTION  -> onboarding_runtime
moteur_migrations(parametres)   # celui des MIGRATIONS    -> onboarding_migrations
```

> **Un test qui crée une table doit employer `moteur_migrations()`.** Sinon il échoue sur
> « permission denied for schema public », **et le message ne dit pas que la cause est le rôle**.
> C'est ce qui est arrivé à neuf tests du socle en `T1` du LOT 3.
>
> Ce que le rôle d'exécution **refuse**, mesuré et testé : `CREATE TABLE`, `DROP TABLE`,
> `ALTER TABLE`, `CREATE ROLE`, et **`TRUNCATE`** — un DDL déguisé qui contourne les déclencheurs
> `ON DELETE`.

### `shared/depot.py` — le cloisonnement est **structurel**

`DepotLocal` ne sait pas construire une requête sans son `entity_id` ; `DepotGlobal` **refuse** une
table locale. Sans cela, il rendrait les lignes de **toutes** les entités **en paraissant
fonctionner** (`DEC-515`).

### `people/` — le trombinoscope, la recherche et la fiche

| Fichier | Ce qu'il porte, et le piège qu'il évite |
|---|---|
| `modeles.py` | les énumérations, **et les règles qui s'en dérivent** : `ETATS_OCCUPANTS`, `ETAT_LISTE`, `VISIBILITE_LISTEE`. Ces deux dernières vivaient dans le trombinoscope ; un **import circulaire** avec `media/photo.py` a montré qu'elles n'appartenaient à aucun des deux |
| `trombinoscope.py` | **deux** filtres, et aucun n'est redondant : le §22.5 étape 5 « masquage du profil » n'est implémenté **nulle part**, donc un partant reste `published`. Cinq axes de filtre en `EXISTS` — une jointure rendrait la personne autant de fois qu'elle a de cercles, le `total` serait faux et la pagination répéterait des lignes |
| `profil.py` | quatre contraintes d'**exclusion** rendent les `LEFT JOIN` sûrs, et **un test exige qu'elles existent toujours** : le jour où l'une serait relâchée, la fiche deviendrait fausse en silence |
| `routes.py` | `taille` est un **`IntEnum`**, jamais un `Literal` — voir le §4 ci-dessous |

### `media/` — la miniature, et **jamais l'original**

| Fichier | Ce qu'il porte |
|---|---|
| `photo.py` | la résolution de la miniature sous **quatre** conditions. Elle ne **sélectionne pas** `media_asset.object_key`, et `MiniatureServie` n'a **aucun champ** qui puisse le porter |
| `objets.py` | la lecture d'un objet MinIO. **Une seule construction du client S3** : deux divergeraient au premier réglage changé, et la sonde de santé dirait « MinIO joignable » pendant que la lecture échouerait |

**L'API sert les OCTETS, et non une URL signée.** Le corpus ne dit **pas** comment un média parvient
au navigateur — zéro occurrence d'« URL signée », de « presigned » ou de CDN — et une URL vers MinIO
exposerait le port 9000, contre `DEC-460` et `DEC-470`. Le choix reste **réversible** : seul le corps
de la route changerait.

**Les conditions de la miniature sont une source UNIQUE**, partagée par deux appelants :

```text
CONDITIONS_DE_LA_MINIATURE  ->  la LISTE l'emploie en EXISTS   (aucune multiplication de lignes)
                            ->  la ROUTE l'emploie en SELECT   (elle lit la variante)
```

Deux copies feraient annoncer par la liste un chemin que la route refuse — une image cassée dans le
trombinoscope, qu'aucun test de la liste seule ne verrait.

---

## 3. Ce que l'API ne fait PAS, et il faut le savoir

| Absent | Pourquoi, et quand |
|---|---|
| **aucune miniature n'est produite** | `MVP-L11-US005`, au **LOT 11**. Aucune bibliothèque de traitement d'image n'est installée. La route de photo rend donc **404 pour tout le monde**, et **un test l'exige** |
| **aucune route ne RETIRE une photo** | la lecture honore le retrait ; l'écriture suppose un écran, donc `T8` ou le LOT 9 |
| **aucun champ de la fiche n'est masqué** | la matrice ne définit **aucune** visibilité par champ — `ECART-051` — et un test **fige l'absence** pour qu'un lot ultérieur doive la décider |
| **`exiger_un_role_dans_l_entite` n'a aucun consommateur** | la matrice §5 ne distingue aucun rôle en **lecture**, et la restriction du §5.1 porte sur l'**écriture** |
| le **masquage du profil au départ** (§22.5 étape 5) | non implémenté. C'est pourquoi le trombinoscope a **deux** filtres et non un |

---

## 4. Les pièges mesurés sur cette API

**Chacun a coûté du temps réel, et chacun a un test qui l'empêche de revenir.**

### Un type juste dans le DOMAINE peut être faux à la FRONTIÈRE

Le cahier §18.2 donne trois tailles de page : 25, 50, 100. Le type qui décrit exactement ce domaine
est `Literal[25, 50, 100]` — et **un paramètre d'URL arrive toujours en chaîne** :

```text
TypeAdapter(Literal[25, 50, 100]).validate_python("25")   ->  REFUSE
TypeAdapter(IntEnum(...)).validate_python("25")           ->  25
```

La route refusait **les trois tailles valides**. Et **huit contrôles de refus restaient verts** :
ils demandaient un refus, et ils l'obtenaient — pour la mauvaise raison. **Toute famille de
contrôles négatifs a besoin de son témoin positif.**

### `ends_at IS NULL` n'est pas « actif »

Une affectation **future** a elle aussi un `ends_at` nul. Emploie `period @> :instant` avec
`archived_at IS NULL`, jamais `ends_at IS NULL`.

**La même erreur existe sur les autorisations de photo** : `withdrawn_at IS NULL` seul laisse passer
une autorisation datée du **futur**. C'est le seul des cinq refus qu'un `WHERE` trop large
laisserait passer, et le témoin qui **n'avance que l'instant** est ce qui le prouve — retirer
`granted_at <= :instant` fait échouer **quatre** tests.

### Un paramètre lié partagé par deux colonnes de types différents

```text
inconsistent types deduced for parameter $1
```

Le message **ne nomme ni la table ni la colonne**. `entity.code` est `character varying(64)` quand
`display_name` et `city` sont `text` : un `:code` réutilisé sur les deux échoue. Sépare les
paramètres.

### `# noqa: S608` dans une chaîne SQL triple-guillemets

Il doit être sur la ligne **de fermeture**, pas à l'intérieur de la chaîne. Commis deux fois.

### Le temps est INJECTÉ, jamais attendu

Toute fonction qui dépend de « maintenant » prend un paramètre `instant`. Un décor **ancré sur une
date en dur** est juste le jour où on l'écrit : mesuré en `T5`, un octroi « futur » posé à une date
fixe ne l'était plus, et **seuls les tests qui passent par la ROUTE** — laquelle lit l'horloge — le
voyaient. « Instant injecté » et « instant de l'horloge » sont **deux grandeurs**.

### Un nettoyage de test incomplet fait échouer des tests SANS RAPPORT

Le nettoyage d'une fixture est **une seule transaction** : un ordre de suppression fautif la fait
échouer, et **son échec l'annule entièrement** — rien n'est supprimé, pas même ce qui aurait pu
l'être. Une fois, quatorze lignes restées commitées ont fait échouer **23 tests du LOT 2**, dont
aucun message ne nommait la cause.

```bash
make residu-check   # compare un avant/apres table par table, la liste DERIVEE du catalogue
                    # « n ligne(s) avant » vaut 0 sur une base propre. Toute autre valeur
                    # est un residu a NOMMER avant de le supprimer.
```

### Le banc d'essai ne peut pas mesurer un plan d'exécution

**`ANALYZE` ne publie rien d'exploitable sur des lignes non validées.** Un test qui engendre son
volume dans une transaction **annulée** — le patron de ce projet — mesure donc un planificateur qui
croit les tables **vides** : `reltuples` reste à **0**. Aucune conclusion sur le plan, ni sur la
durée, ne peut en être tirée. Les tests **rapportent** ces grandeurs et **exigent** la justesse au
volume.

---

## 5. Commandes

Tout passe par le `Makefile` de la racine. Ce paquet est un membre du workspace `uv` déclaré dans le
[`pyproject.toml`](../../pyproject.toml) racine, qui porte aussi la configuration de Ruff, de mypy et
de pytest.

```bash
make check       # qualite complete : format, lint, types, tests, sources, documents
make lint        # Ruff
make typecheck   # mypy strict (DEC-442)
make residu-check   # les tests d'integration, ET la preuve qu'ils ne laissent rien
```

Pour n'agir que sur ce paquet :

```bash
uv run pytest apps/api/tests
uv run pytest apps/api/tests -m "not integration"   # sans stack
```

> **Un test ignoré ne prouve rien.** Les tests d'intégration se **sautent** si PostgreSQL est
> absent — c'est délibéré, pour que `make check` reste utilisable hors stack — mais `make
> residu-check` les exige et **échoue** s'ils ne tournent pas.

---

## 6. Versions

Python **3.12** (`DEC-443`), géré par `uv` — le Python système 3.9.6 de macOS n'est **jamais**
utilisé. `uvicorn --factory` et non un module qui s'instancie à l'import : sans cela, la **collecte**
des tests lit l'environnement et échoue (`DEC-462`).
