# Compte rendu — `T7` du LOT 5 : l'écriture dans son périmètre

**Story :** `MVP-L05-US006` — *Modifier un profil dans son périmètre*, `P0`, taille **XL**, issue `#121`
**Décision :** `DEC-568`
**Écarts ouverts et clos :** `ECART-056`, `ECART-057`
**Date :** 9 septembre 2026

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 5**, ouvert le 24/08/2026 (`DEC-558`), **onze** sous-étapes depuis `DEC-564` |
| Faites | `T1` à `T5`, et **`T7`** |
| Prochaine | **`T8` — archivage et restauration** (`US007`) |
| Périmètre de `T7` | **les six champs que le cahier §10.2 nomme « données organisationnelles »** : date d'arrivée, métier, statut, client, DSM, cercle principal. Arbitrage de Jonathan du 09/09/2026 |
| Hors périmètre, **nommé** | présentation courte, fun fact, cercles secondaires — trois lignes **distinctes** du §6.1, aux portées propres |
| Issue `#121` | **reste ouverte** : `T7` n'achève pas `US006`, comme `#120` que `T5` n'a pas refermée |

---

# 2. Ce que la sous-étape a produit

## 2.1 La première écriture métier du projet, et c'est mesuré

Avant `T7`, **hors de `app/auth/`, les onze routes du dépôt étaient toutes des `GET`.** La mesure
a été faite par AST plutôt que par `grep`, les décorateurs multi-lignes échappant à un motif d'une
ligne :

```text
POST   /api/v1/auth/connexion
POST   /api/v1/auth/deconnexion
POST   /api/v1/auth/magic-link
POST   /api/v1/auth/magic-link/consommation
POST   /api/v1/auth/mot-de-passe
PATCH  /api/v1/entities/{code}/people/{appartenance}   <- T7
```

Le contrat partagé passe de 16 à **17 endpoints**, et `patch` y apparaît pour la première fois.

## 2.2 Deux grilles d'autorisation, et une seule ne suffisait pas

`resoudre_les_permissions` répond « **quels rôles** cette personne porte dans cette entité ». C'est
tout ce dont la lecture avait besoin — la matrice §5 ne distingue aucun rôle en lecture.

**L'écriture pose l'autre question, et le §6.2 la rend inévitable :**

| Rôle | Ce que le §6.2 écrit |
|---|---|
| `DSM` | « ne peut modifier que les consultants ayant un rattachement DSM **actif vers lui** » |
| `BOOST` | « que les membres **actifs de son cercle**. Pour un membre **secondaire**, ses actions doivent rester limitées aux données du cercle et ne pas permettre de modifier un autre cercle principal » |
| `OFFICE` | « n'obtient **aucun** droit général sur les profils du seul fait de sa responsabilité de bureau » |

Un contrôle par rôle seul rendrait donc « autorisé » à un DSM **sur le consultant d'un autre DSM**.

`T7` livre donc `resoudre_le_perimetre`, qui rend **les champs que cet acteur peut écrire sur CETTE
cible** — un ensemble vide étant le refus. Et `exiger_un_role_dans_l_entite`, écrite et testée au
`T9` du LOT 4 et **sans emploi depuis**, trouve enfin son premier consommateur : elle refuse `EMP`,
`NEW` et `OFFICE` **avant toute transaction**.

## 2.3 L'union des droits porte sur les couples (rôle, portée)

Le §23.1 cumule, et **son propre exemple le borne** : Booster du cercle Data **et** responsable du
BDE, « elle peut gérer le contenu du cercle Data, elle peut gérer le contenu du BDE, **elle ne peut
pas gérer le cercle Forge ni le BDG** ». Chaque rôle contribue donc son ensemble de champs **pour
cette cible seulement**, et l'union est prise ensuite.

**Conséquence assumée, et il vaut mieux la dire :** une personne à la fois `BOOST` et `ESM` **peut**
changer le DSM, alors que `BOOST` seul ne peut pas. Ce n'est pas un trou — « hors changement de
DSM » est une restriction de **rôle**, non de ressource, donc le §23.2 ne la fait pas survivre au
cumul. Un test l'exige explicitement.

## 2.4 Un membre secondaire n'ouvre aucun des six champs, et c'est dérivé de deux sources

Le §6.2 limite les actions du Booster sur un membre **secondaire** « aux données du cercle » et lui
interdit « de modifier un autre cercle principal ». Or **aucun des six champs n'est une donnée du
cercle** — sauf `cercle_principal`, que la phrase exclut précisément.

Et la roadmap le confirme dans sa **démonstration attendue**, là où la fiche est muette : « ajout
d'un membre secondaire par un Booster » puis « **impossibilité** pour le Booster de modifier son
cercle principal ou son client ».

Gérer l'appartenance secondaire elle-même est une **autre** ligne du §6.1, hors périmètre.

## 2.5 La grille d'état prévaut sur le cumul, `SUPER` compris

§23.2 : « une interdiction liée à la **ressource ou à l'état** prévaut sur le cumul des rôles ». La
modification porte sur un profil **vivant** : le §6.1 traite séparément « consulter un profil
archivé » et « réactiver un profil archivé », tous deux restreints, et l'archivage est `T8`.

La cible doit donc être dans un état **occupant**, et `ETATS_OCCUPANTS` porte déjà ce regroupement
dans `app/people/modeles.py`. En réécrire une copie aurait été le §7.27.

## 2.6 Clore puis ouvrir — et « jamais écrasées » est une propriété du SCHÉMA

§23.4 : « la suppression d'un rôle actif **clôture** la relation au lieu d'effacer l'historique ».
Quatre des six champs sont portés par des relations historisées du §25.2.

**Ce qui rend le critère de sortie n°6 du lot structurel plutôt que promis :**

- `period` est un `tstzrange(starts_at, ends_at)`, donc en bornes `[)` — fermer à `T` et ouvrir à
  `T` **ne se chevauchent pas** ;
- chaque table porte une exclusion `(clé WITH =, period WITH &&)` : toute écriture qui
  chevaucherait est **refusée par la base**.

Ce module ne peut donc que s'y conformer ou échouer bruyamment. **Conséquence à connaître :** si une
période **future** existe, `period @> :instant` n'en ferme aucune et l'insertion chevaucherait — la
base refuse, et ce refus est traduit en `409 periode_incompatible`. Un test l'exerce.

## 2.7 Statut et client sont une seule période, et le `CHECK` est une biconditionnelle

Ils vivent sur la même ligne, et la base les lie par `(status = 'mission') = (client_id IS NOT
NULL)` — le §30.5 est donc structurel **dans les deux sens**.

Deux conséquences que la mesure impose :

1. **une demande qui ne porte que l'un doit reporter la valeur courante de l'autre**, sinon la
   biconditionnelle refuse une demande légitime ;
2. **passer à `intercontract` retire le client sans qu'on le nomme** — c'est une conséquence du
   statut, pas une saisie de l'appelant.

## 2.8 La concurrence optimiste, ancrée sur la racine de l'agrégat

§18.4, littéralement : « les modifications sensibles utilisent une concurrence optimiste. Une
version obsolète produit une réponse **409 sans écrasement silencieux** ».

L'ancre est `entity_membership.version`, **racine** de l'agrégat, et non la version de chaque table
fille : modifier le métier et le DSM en même temps doit entrer en conflit, or ces deux écritures ne
touchent pas la même ligne fille. Ancrer sur les filles laisserait passer deux éditeurs qui se
croient seuls.

**Et la version ne monte pas quand rien n'a changé** : l'historique ne doit pas se remplir de
périodes d'une microseconde, et une demande sans effet ne doit pas faire échouer la suivante.

## 2.9 La règle CSRF est déplacée, jamais recopiée

`_proteger_du_csrf` était **privée** à `app/auth/routes.py`, où elle n'a servi qu'aux cinq écritures
d'authentification pendant deux lots. En recopier une version dans `app/people/` aurait donné **deux
règles pour une seule** — `DEC-466` pour le masquage, `ECART-022` pour les modèles d'environnement —
dont l'une oublierait un jour une barrière, **en silence**.

Elle vit dans `app/auth/dependances.py`, le module que les routes métier importent déjà. La mettre
dans `csrf.py` aurait couplé des primitives **pures**, testables sans FastAPI, à `Request` et à
`Parametres`.

**`SessionEtablie` ne porte toujours pas le jeton**, à dessein — son docstring le dit : « le faire
circuler multiplierait les endroits d'où il peut fuir vers un journal ». La route lit donc son
cookie elle-même, comme le fait la déconnexion. **154 tests d'authentification** passent après le
déplacement.

## 2.10 Seul `client` accepte un `null` explicite, et c'est mesuré

Un `PATCH` doit distinguer « champ absent » de « champ nul ». Mesure du 09/09/2026 sur les six
colonnes cibles : **seule `professional_status_assignment.client_id` est nullable**.

`model_fields_set` fait la distinction, et un `null` explicite sur les cinq autres est refusé en
`422` **avant** d'atteindre la base — dont le message ne dirait pas que la cause est une demande mal
formée. Et `extra="forbid"` : un client qui enverrait `presentation_courte` l'apprend, au lieu de
croire sa modification prise.

---

# 3. Contrôles exécutés

## 3.1 Les tests

```text
uv run pytest -q --collect-only | tail -1
#  857 tests collected            (+19)

uv run pytest -m integration -q --collect-only | tail -1
#  546/857 tests collected        (+16)

uv run pytest apps/api/tests/test_ecriture_organisationnelle.py -q
#  19 passed

uv run pytest apps/api/tests -q
#  779 passed
```

**Chaque refus est apparié à un témoin qui ne diffère QUE par la valeur en cause** — §7.39, parce
que deux des trois critères de `T7` sont des refus, et que cinq refus indistinguables laissent
passer un `WHERE` faux qui refuse tout, comme les huit refus du défaut `T2-3`.

| Témoin | Ce qu'il rend non trivial |
|---|---|
| le même DSM sur une cible **rattachée** et une **non rattachée** | un `WHERE` trop large les autoriserait toutes deux, un `WHERE` faux les refuserait toutes deux |
| **seul l'instant avance** sur un rattachement futur | le refus mesuré pourrait sinon venir de n'importe quel filtre trop large |
| `OFFICE` refusé, puis **`ESM` sur la MÊME cible** | prouve que la cible est modifiable |
| une appartenance archivée, puis **la même active** | prouve que le refus vient de l'état |
| `BOOST` seul, puis **`BOOST` + `ESM`** | prouve que le cumul du §23.1 s'applique |

## 3.2 Le contrôle de stack, à travers Caddy en HTTPS

**`T7` n'ajoute AUCUNE cible : elle étend `make profil-check`, de 17 à 26 contrôles**, comme `T5`
l'avait fait de 10 à 17. Le décor de `T4` donne le couple apparié **pour rien** — « Ada Complete »
est rattachée au DSM, « Rosa Retiree » est active et ne l'est pas.

**Bénéfice direct :** aucune cible nouvelle, donc **rien à ajouter dans `ci.yml`** — la cible y est
déjà, et le §7.36 rappelle qu'une cible ajoutée à `make check` n'entre pas dans la CI de ce projet.

```text
make profil-check
#  ok       TEMOIN : le DSM se connecte, et `GET /auth/session` rend son jeton
#  ok       LE CRITERE : un DSM modifie SON consultant — 200, et la reponse nomme le champ ecrit
#  ok       le MEME DSM est REFUSE sur un consultant non rattache — 403 `champ_hors_perimetre`
#  ok       sans role d'ecriture : 403 `acces_refuse` — c'est le cas d'`OFFICE`
#  ok       sans session : 401 — aucune ecriture n'est ouverte a `ANON`
#  ok       sans jeton CSRF : 403 `requete_refusee` — PREMIER emploi sur une route METIER
#  ok       version OBSOLETE : 409, et l'historique est INCHANGE — §18.4
#  ok       champ INCONNU : 422 — l'ignorer ferait croire la modification prise
#  ok       l'historique du metier est INTACT apres deux refus
#
#  controles executes : 26   echecs : 0
```

## 3.3 La qualité

```text
make typecheck        code 0    mypy strict, 121 fichiers
make lint             code 0
make docs-check       code 0
make docs-temoin      code 0
make recette-modele-check  code 0   13 acquis · 1 partiel · 10 reportes · 1 inapplicable
make test-frontend    code 0    299 (81 + 97 + 121)
uv run pytest apps/api/tests/test_contrat.py -q   5 passed
```

---

# 4. Les défauts de cette sous-étape

## `T7-1` — J'ai rejoué la leçon §7.25, et seize tests sont tombés d'un coup

Mon aide de décor employait **un seul paramètre lié** pour `entity.code`, `display_name` et `city`.
Or `code` est `character varying(64)` quand les deux autres sont `text` : psycopg rend
`inconsistent types deduced for parameter $1`, et **le message ne nomme ni la table ni la colonne**.

`test_permissions.py` emploie trois paramètres distincts depuis le LOT 4 ; je les avais réunis. **Le
§7.25 documente exactement ce piège**, et c'est sa quatrième occurrence dans le projet.

*La leçon n'est pas « faire attention » : c'est que la forme sûre est d'écrire un paramètre par
colonne, même quand une seule valeur les alimente. Le discriminant est le TYPE, que le lecteur n'a
pas sous les yeux.*

## `T7-2` — Ni `ruff` ni `mypy` n'ont vu que l'application ne pouvait pas démarrer

J'avais écrit la dépendance en `Annotated[SessionEtablie, Depends(fabrique(parametres, ...))]`. Ce
module porte `from __future__ import annotations`, donc toute annotation est une **chaîne** que
Pydantic doit résoudre — or `parametres` est une variable de **fermeture** du routeur, invisible au
niveau module.

**Les deux contrôles statiques passaient au vert.** Seul le montage de l'application l'a dit :
`PydanticUserError: is not fully defined`. C'est le §7.28 — lis ce que la cible **fait** — et le
piège que `T1` du LOT 4 avait déjà payé, nommé dans le commentaire de la route voisine.

La forme correcte existait dans le dépôt depuis le `T8` du LOT 4 : `permissions/routes.py:129`,
`appelant: SessionEtablie = Depends(...)` **sur une seule ligne** avec son exemption.

## `T7-3` — Une exemption de règle posée « par précaution », qui n'exemptait rien

J'avais mis une directive d'exemption `S608` sur mon gabarit de `UPDATE`. `ruff` a répondu
`RUF100 unused`. **Une suppression qu'on n'a pas vérifiée nécessaire apprend à en poser d'autres**,
et le jour où la règle tire vraiment ailleurs, personne ne sait laquelle est justifiée.

**Et sa correction a produit le défaut suivant :** le commentaire qui expliquait le retrait
**écrivait la directive en clair**, et `ruff` l'a lue comme une directive — « Invalid directive ».
C'est le défaut de `T11` du LOT 2, un garde-fou qui se déclenche sur le commentaire énonçant sa
propre règle, pour la **quatrième** fois. *On nomme la règle, on ne l'écrit pas.*

## `T7-4` — J'ai introduit la forme dépréciée du 422 que le dépôt avait abandonnée

`HTTP_422_UNPROCESSABLE_ENTITY`, en trois endroits, alors que `auth/routes.py`,
`shared/errors.py` et `people/routes.py` emploient déjà `HTTP_422_UNPROCESSABLE_CONTENT`.

**C'est un avertissement de dépréciation qui me l'a dit**, au montage de l'application. Le §7.6 :
ne masque jamais l'erreur d'un contrôle dont tu vas interpréter le silence — et ici il suffisait de
la **lire**.

## `T7-5` — Mon décor de stack était incomplet, et le garde-fou avait raison

Cinq de mes neuf contrôles rendaient `403 acces_refuse` : le DSM du décor n'avait **aucune
appartenance**, donc aucune entité principale, et le §5.1 ne lui laissait que `EMP`.

**Le refus était juste.** C'est le décor qu'il fallait corriger, pas le contrôle — et c'est
exactement le genre de constat que seul un contrôle **à travers l'API** produit : les dix-neuf tests
unitaires passaient, parce qu'ils fournissent les rôles directement.

Son appartenance est posée en **`draft`** : en `published`, elle ferait **trois** profils listés et
casserait un témoin de `T2`. Et **l'appelant sans rôle n'a pas été touché** — le contrôle 5 prouve
qu'aucun champ n'est masqué à quelqu'un « sans appartenance, ni responsabilité, ni rôle technique »
(`ECART-051`), et lui donner un rôle aurait détruit ce témoin. `T7` ajoute donc un **second** compte
connectable au lieu d'en modifier un.

## Un événement extérieur, et il n'est pas de mon fait

**`make audit` est passé de 0 à 2 avis pendant la sous-étape**, sans qu'aucun fichier de
dépendances ne soit dans mon diff — vérifié. Deux avis **modérés** nouvellement publiés sur
`vitest` et `@vitest/mocker` (`GHSA-82fw-gwwq-j7x9`), corrigés en `>= 4.1.11` quand le dépôt
déclarait `^4.1.10`.

`DEC-493` a fixé l'audit à **zéro avis, zéro tolérance**, et `audit` est un contrôle **requis** en
CI : le corriger n'était donc pas optionnel.

**LA PREMIÈRE FORME DU CORRECTIF A ÉTÉ RETIRÉE, ET LA MESURE L'A IMPOSÉ.** `pnpm update -r` — le
geste de `T10` du LOT 1 — a bougé **onze** plages et non une : `eslint`, `typescript-eslint`,
`vite`, `react-router`, `jsdom`, `globals`, `@vitejs/plugin-react`, `@testing-library/react`, les
deux `@types/react*` et `vitest`. Toutes en mineur ou patch, aucune majeure forcée, et `make check`
restait vert — mais **cette PR est celle de `T7`**, et mêler onze montées à une écriture métier
rendrait toute régression future inattribuable.

`pnpm update -r vitest` suffit, et c'est mesuré : **une seule** plage bouge, `^4.1.10` → `^4.1.11`,
et `@vitest/mocker` est résolu en `4.1.11` — la version corrigée — parce qu'il est une dépendance
**transitive** de `vitest`.

**Et le correctif a été mesuré dans ce qu'il casse** (§7.0, cinquième proposition) : `audit` rend
« No known vulnerabilities found », les **299** tests Vitest passent, et `lint`, `typecheck` et
`format-check` restent à 0.

*Le premier geste n'était pas faux, il était trop large. C'est une nuance que le §7.0 cinquième
proposition ne couvre pas : mesurer ce qu'un correctif casse ne dit rien de ce qu'il **mélange**.*

*C'est le §7.22 : un audit vert décrit l'écosystème **à une date**. Avant d'attribuer une
régression à son travail, on mesure l'état d'avant — ici, l'absence de tout changement de
dépendance suffisait.*

## Deux choses que la base m'a apprises, et qui ne sont pas des défauts

- **`ck_client_canonical_name_en_minuscules`** : le nom canonique d'un client est la forme
  **normalisée**, l'affichage garde la casse. C'est tout l'objet des deux colonnes ;
- **un déclencheur exige « un client active dans cette entité »** pour une mission — il faut la
  liaison `entity_client`. **Son message nommait la règle ET les identifiants**, si bien que le
  diagnostic a pris une lecture. C'est ce que le §12 appelle « la première correction à écrire est
  celle qui te le dira », appliqué par quelqu'un d'autre avant moi.

---

# 5. Écarts ouverts et clos

## `ECART-056` — le seul `ends_at IS NULL` applicatif restant, et `T7` allait le consommer

`responsabilite_dsm_active` rendait un identifiant pour une responsabilité DSM **future**, alors que
la fonction **immédiatement en dessous** documente sur dix lignes pourquoi cela ne suffit pas.

**Scénario d'échec mesuré :** `attribuer_la_categorie_dg` **saute** la création quand elle rend
non-`None`. Une personne promue DG aujourd'hui, portant une responsabilité DSM programmée le mois
prochain, n'obtenait **aucune** responsabilité DSM active — et l'action rendait un **succès**.

**Périmètre vérifié :** les trois autres requêtes en `(ends_at IS NULL OR ends_at > :instant)` ne
sont **pas** des défauts — celle du départ porte `starts_at <= :instant`, les deux autres sont des
**rapports** et non des octrois. Les signaler aurait été accuser du code conforme (§7.25).

## `ECART-057` — une échéance qui nommait une sous-étape supprimée

Le §30.12 était `REPORTE` avec pour échéance « LOT 5 **`T6`** », or `DEC-564` a fusionné `T6` dans
`T5` et `T5` a livré le service. `make recette-modele-check` exige que chaque contrôle **soit
classé** et que chaque `ACQUIS` **nomme un test qui existe** — il ne vérifie pas que l'échéance d'un
`REPORTE` désigne une sous-étape **réelle**. §7.31, encore.

Reclassé `ACQUIS` avec **trois** tests nommés, dont le témoin temporel. Le compte passe de 12 à
**13 acquis**.

---

# 6. Ce que `T7` laisse à la suite

| Point | Ce qu'il faut savoir |
|---|---|
| **`US006` n'est PAS achevée** | présentation courte, fun fact et cercles secondaires sont **trois lignes distinctes** du §6.1. L'issue `#121` **reste ouverte**, comme `#120` |
| **`T8` doit casser deux tests, et c'est leur rôle** | la grille d'état refuse une appartenance `archived` **même à `SUPER`** ; l'archivage et la restauration devront la relâcher **délibérément**, et deux tests les y obligeront (§7.32) |
| **retirer une affectation n'existe pas** | seul `client` accepte un `null`. Clôturer sans réouvrir n'est pas « modifier », et le §30.4 veut qu'un consultant actif **ait** un DSM. L'opération n'est pas dans le §6.1 |
| **`exiger_un_scope` attend TOUJOURS son premier consommateur** | la dépendance de scope des comptes de service, livrée au LOT 3. `T7` a consommé `exiger_un_role_dans_l_entite` et la protection CSRF, pas celle-là |
| **le rafraîchissement de session reste un résiduel nommé** | `GET …/auth/session` demeure la seule écriture n'exigeant aucun jeton, et `T7` la consomme désormais pour obtenir le jeton CSRF |
| **§30.4 reste `PARTIEL`** | « un consultant actif possède un DSM actif » est une règle de **processus** : `T7` écrit les rattachements, il ne garantit pas leur existence. Échéance LOT 7 |

---

# 7. Chiffres, tous dérivés le 09/09/2026

| Grandeur | Valeur | Commande |
|---|---|---|
| Tests pytest | **857** (+19) | `uv run pytest -q --collect-only \| tail -1` |
| dont d'intégration | **546** (+16) | `uv run pytest -m integration -q --collect-only \| tail -1` |
| Tests Vitest | **299** | `make test-frontend 2>&1 \| grep -oE 'Tests  [0-9]+ passed'` |
| Contrôles de `profil-check` | **26** (17 + 9) | `make profil-check` |
| Endpoints du contrat | **17** (+1) | lu dans `contrat-api.json` |
| Cibles `Makefile` | **86**, inchangé | `grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile` |
| Cibles invoquées par `ci.yml` | **41**, inchangé | dérivé du workflow |
| Migrations | **16**, inchangé | `ls apps/api/alembic/versions/*.py \| wc -l` |
| Leçons du §7 | **41** | `grep -c '^## 7\.' CLAUDE.md` |

**Aucune migration** : les quatre relations et la colonne existaient depuis le LOT 2, et les
contraintes d'exclusion qui rendent le critère n°6 structurel aussi. `T7` n'ajoute **aucune cible**
et **aucune variable d'environnement**.
