# Compte rendu — `T6` du LOT 6 : l'écriture d'un contenu dans son périmètre

**Sous-étape :** la sixième du lot · **Date :** 18 septembre 2026
**Décision :** `DEC-585` · **Écarts ouverts :** `ECART-062`, `ECART-063` · **Story :** `MVP-L06-US004` (2 sur 3), issue `#149`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 6**, ouvert le 13/09/2026 (`DEC-575`), **douze** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, **`T6`** |
| Restent | `T7` à `T12` |

---

# 2. Ce que la sous-étape a produit

```text
POST /api/v1/entities/{code}/pages             creer une page, TOUJOURS en `draft`
PUT  /api/v1/entities/{code}/pages/{page}/contenu   remplacer son titre et ses blocs
```

## 2.1 Le troisième verbe, et il est tenu par la STRUCTURE

Le corpus écrit **quatre fois** la même exigence, en trois verbes que le découpage sépare :

| Verbe | Qui le tient | Comment |
|---|---|---|
| **stocké** | `T1` | aucune colonne ne peut porter du HTML libre |
| **exécuté** | `T5` | la **réponse** ne porte aucun champ de nature HTML |
| **accepté** | **`T6`** | la **demande** n'en porte aucun non plus |

**Et il n'y a pas de filtre.** Un filtre textuel serait une heuristique, donc un défaut (§7.25) : `<`
est légitime dans « a < b », `&` dans « R&D », et chercher `<script` laisserait passer
`<img onerror=…`. Un garde-fou à faux positifs apprend à passer outre ; un à faux négatifs ment.

Ce qui est exact est structurel : **la demande n'offre aucun champ par lequel un auteur puisse
déclarer que sa chaîne est du balisage**. Il n'existe ni `html`, ni `format`, ni `rendu` ; le contenu
d'un bloc est un objet JSON et son type est contrôlé. Un test **dérivé des champs du modèle** l'exige
des deux côtés — celui de `T5` sur la réponse, celui-ci sur la demande — et il échouerait si
quelqu'un ajoutait un champ, sans qu'on ait pensé à le mettre à jour.

> **La conséquence est assumée et nommée :** du balisage écrit dans une valeur de texte est
> **conservé tel quel**, et `T5` le ressert tel quel. Ce n'est pas une faille, c'est la preuve que
> cette API stocke des **données**. Le retirer en silence serait pire — un contenu mangé sans que
> personne le sache, et un contrôle qui ne pourrait plus distinguer « filtré » de « rien à filtrer ».

**Ce qui EST refusé, parce que c'est exact :** un `block_type` hors des onze de `DEC-577` — 422, et
la réponse les **énumère**, parce qu'un auteur qui a prouvé son rôle doit savoir ce qu'il peut poser
— et un contenu qui n'est pas un **objet** JSON. Ce second refus, à l'écriture, est ce qui garantit
que le 500 de `T5` ne survienne **jamais** pour une donnée écrite par l'API.

## 2.2 La grille du §13 diffère de celle du LOT 5 **dans les deux sens**

C'est le piège central de la sous-étape, et il ne va pas dans un seul sens :

| | `DSM` | `ESM` | `BOOST` | `OFFICE` | `ADM-E` | `SUPER` |
|---|---|---|---|---|---|---|
| §6.1, écriture d'un **profil** (LOT 5) | **✓** | ✓ | ✓ | **—** | ✓ | ✓ |
| §13, écriture d'un **contenu** (`T6`) | **—** | ✓ | ✓ | **✓** | ✓ | ✓ |

Réutiliser `ROLES_D_ECRITURE` aurait donc **accordé** un droit au DSM — que le §13 met à tiret sur
ses trois lignes de modification — et **retiré** le sien au responsable de bureau, dont la colonne du
§6.1 est entièrement à tiret alors que le §13 lui donne le contenu de **son** bureau.

**Trois autres distinctions que le document écrit, et qu'une grille unique aurait effacées :**

1. **« Créer » n'est pas « Modifier ».** Le §13 n'a qu'une ligne de création — « Créer un contenu
   général », à `ESM`, `ADM-E` et `SUPER` — quand ses deux lignes de modification portent `BOOST`
   (**Cercle**) et `OFFICE` (**Bureau**). Le Booster **modifie** le contenu de son cercle sans
   pouvoir **créer** sa page, exactement comme le §10.2 lui refuse « Créer un cercle » ;
2. **« Entité » n'est pas « Périmètre ».** L'ESM a « Entité » pour créer et modifier, **« Périmètre »**
   pour publier et archiver. La page naît donc `draft`, et la demande **ne porte aucun champ
   d'état** : la valeur n'est pas ignorée, elle n'existe pas ;
3. **« Bureau, contenu uniquement » ne mord pas ici.** Le §10.3 restreint `OFFICE` au contenu du
   bureau, et `T6` n'écrit **que** du contenu — le titre d'une page et ses blocs — jamais le `code`,
   le `name` ni le `display_order` de la table `office`, qui sont sa structure.

## 2.3 Trois partis de conception, et leur motif

**L'ordre d'affichage est l'index du tableau.** `display_order` n'est pas un champ de la demande :
deux blocs de même rang deviennent **inexprimables**, là où un champ libre les aurait laissés passer
jusqu'à l'index unique de `T1`, qui aurait rendu un 500. §7.35 — la propriété est tenue par la
structure, la perdre exigerait de changer la signature.

**Les blocs retirés sont ARCHIVÉS, jamais supprimés.** Modèle §2.4 : « les ressources métier sont
archivées par `archived_at` et `archived_by` », la suppression physique étant réservée aux données
temporaires, aux purges RGPD et aux opérations du super-administrateur. Un bloc retiré n'est aucun
des trois.

> **Et cela n'exige aucun motif** — le §18.1 en énumère cinq, et retirer un bloc n'y est pas. Le
> supposer sans lire le §18.1 aurait été une négligence ; en exiger un aurait été une invention.
>
> **Ce n'est PAS « archiver un contenu » au sens du §13 et du §18**, qui visent la **page** prise
> comme ressource — celle qui disparaît de la lecture. Retirer un bloc au cours d'une édition est le
> mécanisme même de « Modifier un contenu de … ». La distinction est réelle et elle est tenue : la
> route n'écrit **jamais** `content_page.archived_at`, et un test l'exige.

**L'écriture adresse par identifiant, la lecture par `(type, slug)`.** L'écriture porte d'abord sur
des **brouillons**, que la lecture ne sert pas ; et un slug est une adresse de publication, pas
l'identité d'une ressource en cours de rédaction.

## 2.4 Le seul caractère refusé dans un slug, et il est DÉRIVÉ de l'adressage

Le corpus ne donne **aucun** format de slug — ni casse, ni jeu de caractères, zéro occurrence dans
les cinq documents — et en inventer un serait le §6.5. Mais `T5` adresse une page par
`…/pages/{type}/{slug}`, et un paramètre de chemin FastAPI ne capture pas la barre oblique : une page
dont le slug en contiendrait une serait créée et **rien ne pourrait jamais la servir**.

**Le refus ne décrit donc pas une convention d'écriture**, il refuse un slug qui rendrait la page
inatteignable — et un test le **mesure** au lieu de l'affirmer : la page est posée en contournant le
service, publiée, et le service de lecture ne la trouve ni sous `a` ni sous `b`, alors qu'il la
trouve sous `a/b`. Ce n'est donc pas la page qui manque, c'est le chemin qui ne peut pas la nommer.

---

# 3. Contrôles exécutés

```text
make check              code=2   74 echecs ENVIRONNEMENTAUX, identiques a la reference
uv run pytest apps/api/tests/test_ecriture_des_contenus.py   36 passes, 0 echec
make framework-check    49 controles, 0 echec   <- a travers Caddy, vraie session
make residu-check       « aucun residu, cependant » — le delta avant/apres est NUL
make docs-check · make icloud-verify · make env-check              tous code=0
uv run mypy             143 fichiers, 0 probleme     uv run ruff check   0
```

> **LES 74 ÉCHECS DE `make check` SONT ENVIRONNEMENTAUX, ET C'EST MESURÉ.** La même commande rend
> **74 échecs / 982 passés** sur `1939c0a`, **avant toute ligne de `T6`** : ce sont des tests des
> LOTS 2 et 3 qui comptent des lignes en absolu — « assert 5157 == 2 » — sur une base qui porte le
> jeu de démonstration client. **Aucun ne vient du code.** La porte de la pull request tourne sur
> une base neuve, et c'est elle qui fait foi.

**Aucune cible `make` nouvelle.** `framework-check` est **étendu de 35 à 49 contrôles** — il porte
déjà le décor, la session et le ménage. Rien à ajouter dans `ci.yml`, ce qui est le bénéfice direct
du §7.27 pour la quatrième sous-étape consécutive.

## 3.1 Le contrôle de stack le plus utile est un ALLER-RETOUR complet

```text
ok   ALLER-RETOUR REEL : ecrit par l'API, relu par l'API — la charge
     traverse INTACTE dans les octets, en `application/json`, et
     rien n'a ete retire en silence
```

Il crée la page par l'API, écrit ses blocs par l'API — dont un portant
`<script>alert('xss')</script>` — la publie, puis la relit par la route de `T5` et cherche la charge
**dans les octets servis**. Trois choses y sont exigées ensemble : le type de contenu est
`application/json` et non `text/html` ; la charge s'y trouve **telle quelle**, ce qui prouve que rien
n'a été retiré en silence — *un filtre qui aurait mangé la chaîne donnerait la même observation
qu'une absence d'injection* ; et elle arrive comme une **valeur de chaîne** dans un objet JSON.

**Et la publication y est faite en SQL**, parce que la route de publication est `T7` : ce contrôle
prouve l'**écriture**, pas la publication.

## 3.2 La campagne de témoins — quinze filtres retirés un par un

| Filtre retiré | Tests en échec |
|---|---|
| la portée **Entité** élargie à tous les rôles d'écriture | **5** |
| la validation des types de bloc | **2** |
| `{colonne} = :ressource` de la responsabilité | **2** |
| `period @> :instant` · `person_id = :acteur` · `portee.role not in roles` | **1** chacun |
| `archived_at IS NULL` et `entity_id` de la page | **1** chacun |
| le verrou de version · le slug non adressable · le type de page | **1** chacun |
| `entity_id` de la résolution du cercle · l'exigence de rattachement | **1** chacun |
| **`responsibility_type`** et **`entity_id`** de la responsabilité | **0** — voir §3.3 |

**La première passe en donnait quatre à zéro, et deux de ces quatre étaient de vrais trous de
couverture** : `person_id = :acteur` — sans lui, la responsabilité de **n'importe qui** sur ce cercle
accorderait le droit — et `portee.role not in roles`, qui est le §5.1 : une personne hors de son
entité principale n'a que `EMP`, mais **sa responsabilité est toujours en base**, et sans ce test le
module irait la chercher et rendrait le droit que le §5.1 vient de retirer.

Les deux témoins sont écrits, et chacun ne diffère de son témoin positif que par **une** valeur :
l'acteur pour le premier, les rôles résolus pour le second.

## 3.3 Deux filtres sont REDONDANTS, et c'est la base qui protège

Mesure au catalogue du 18/09/2026, après que les témoins les ont dits muets :

```text
ck_..._portee_selon_le_type   un `circle_id` non nul IMPLIQUE `BOOSTER`,
                              un `office_id` non nul IMPLIQUE `OFFICE_MANAGER`
fk_framework_responsibility_circle
                              FOREIGN KEY (circle_id, entity_id)
                              REFERENCES circle(id, entity_id)
```

La première est une **biconditionnelle stricte** : filtrer sur la colonne fixe déjà le type. La
seconde est **composite** : une responsabilité qui pointe le cercle C a forcément l'entité de C,
comme la page.

**Les deux filtres sont conservés** — c'est l'idiome de cloisonnement de tout ce dépôt, et une
requête locale qui ne nommerait pas son entité se lirait comme une requête globale — **mais ils ne
sont pas ce qui protège**, et le module le dit avec sa mesure. Un test **exige que la base continue
de l'interdire** (§7.32) : si un lot ultérieur relâchait l'une des deux contraintes, il échouerait,
et celui qui la relâche saurait qu'il doit relire ce module.

> **C'est la troisième occurrence de cette classe après `T4-2` et `T5-1`** — et trois fois sur trois,
> ce qui protégeait vraiment était **une contrainte ailleurs, déjà sous contrôle**.

---

# 4. Défauts trouvés — **quatre**, tous dans mon propre travail

## `T6-1` — le marqueur du décor était en capitales, et la base exige des minuscules

`ck_person_email_normalise_en_minuscules`, posée au LOT 2. Les **vingt-cinq** tests d'intégration ont
échoué au décor, d'un coup. L'échec était **bruyant et nommait la contrainte**, ce qui est la seule
bonne nouvelle : un décor qui refuse de se poser ne laisse pas croire qu'il a testé quelque chose.

## `T6-2` — un refus de la BASE avorte la transaction, et rendait le témoin inatteignable

Sur **douze** refus de cette suite, **un seul** est produit par la base — le slug déjà pris ; les
onze autres viennent d'une validation du service, en amont de tout `INSERT`. Or un refus de la base
avorte la transaction : « current transaction is aborted, commands ignored until end of transaction
block ». Le témoin qui suivait — *le même slug sur un autre type, que le §15.1 autorise* — devenait
**inatteignable**, et le test échouait sur une ligne qui n'avait rien à se reprocher.

Corrigé par un `SAVEPOINT`. **La route, elle, n'a pas ce problème** : l'`ErreurApplicative` remonte
hors du `with moteur(...).begin()`, donc rien ne continue après. *C'est un piège de TEST, et il faut
savoir le distinguer d'un défaut du livrable.*

## `T6-3` — mon vérificateur de témoins a MENTI, et il l'a fait en silence

**Le défaut le plus intéressant de la sous-étape, et il porte sur l'outil de mesure lui-même.**

La première campagne annonçait **cinq** filtres muets. Rejoué isolément, l'un d'eux faisait pourtant
tomber son test. Diagnostic avant correction (§7.18) : une sonde qui compare l'empreinte du SQL **vu
par le processus** à celle du SQL **du disque**.

```text
responsibility_type    taille=13458  attendu=c30214dda39c  vu=c30214dda39c  OK
person_id              taille=13487  attendu=52a5534c10bb  vu=52a5534c10bb  OK
entity_id resp.        taille=13487  attendu=ed527f756226  vu=52a5534c10bb  ** BYTECODE PERIME **
archived_at page       taille=13487  attendu=e51fb5bc463e  vu=52a5534c10bb  ** BYTECODE PERIME **
entity_id page         taille=13487  attendu=482a3ce77fae  vu=52a5534c10bb  ** BYTECODE PERIME **
```

**CPython invalide un `.pyc` sur le couple `(mtime TRONQUÉ À LA SECONDE, taille en octets)`.** Quatre
de mes variantes pèsent **exactement 13 487 octets**, et chaque exécution dure moins d'une seconde :
trois d'entre elles ont donc exécuté le bytecode d'une variante **précédente**, et le vérificateur
annonçait « 0 échec ».

> **C'est le §7.0, quatrième proposition, dans l'outil de mesure :** « 0 échec » était la **même
> observation** pour deux causes différentes — « ce filtre ne travaille pas » et « ce filtre n'a
> jamais été retiré ». Et le défaut est **non déterministe** : selon le temps que prend chaque
> exécution, il se manifeste ou non, ce qui le rend d'autant plus insidieux.

**Parade mesurée avant d'être appliquée** : la même sonde sous `PYTHONDONTWRITEBYTECODE=1` rend les
quatre empreintes attendues. La campagne relancée donne un résultat stable, et c'est elle qui a
révélé les deux vrais trous du §3.2.

## `T6-4` — le décor de stack ne donnait aucune APPARTENANCE, et l'ESM n'avait aucun rôle

Trouvé au premier lancement de `make framework-check` : la personne du décor porte une
responsabilité `ESM` **active**, et la création rendait **403 `acces_refuse`**.

`resoudre_les_permissions` part de `entite_principale(personne)` : une personne **sans appartenance
occupante** ressort avec un ensemble de rôles **vide**, quelles que soient ses responsabilités
Framework. Le décor, hérité de `T2`, n'en posait aucune pour l'acteur — aucun contrôle de lecture
n'en avait eu besoin.

> **Aucun test unitaire ne pouvait le dire**, et c'est le §7.43 : mes trente-six tests passent
> `roles` **à la main**, la pile les **dérive**. Un bouchon prouve ce qu'on a écrit dans le bouchon.
>
> **Et le témoin compte autant que le cas** : l'appartenance de la personne *sans responsabilité* a
> été ajoutée avec celle de l'ESM. Sans elle, son 403 viendrait de l'absence d'appartenance et non de
> la grille du §13, et le contrôle aurait prouvé autre chose que ce qu'il annonce.

---

# 5. Deux écarts ouverts, et aucun ne bloque `T6`

## `ECART-062` — le §10.1 donne au DSM « Modifier la page DSM », et aucun type ne la porte

Le §10.1 est le **seul** endroit du corpus où le DSM reçoit un droit d'écriture éditoriale —
« Modifier la page DSM | **Entité ou propre contenu** ». Or **aucun `page_type` du §15.1 ne porte
cette page** : ni `DSM` ni `ESM` n'y figurent, et `T2` a émis pour elles un chemin d'**écran** sans
que rien ne dise quel contenu les porte.

Deux lectures, **aucune déductible** : une page `FRAMEWORK` particulière que rien ne distingue des
autres, ou un « autre type contrôlé » à créer. Sous la première, accorder le droit ouvrirait au DSM
**toutes** les pages `FRAMEWORK`, alors que le §10.1 lui refuse « Modifier la présentation
générale ».

`T6` suit donc le §13 — le DSM n'écrit aucun contenu — qui est la lecture **la plus restrictive** :
un refus se relâche, une permission accordée à tort a déjà été exercée. **À trancher avant `T9`**, et
la question relève de Léa.

## `ECART-063` — le §13 et le §18 divergent sur l'archivage d'un contenu

| | `DSM` | `ESM` |
|---|---|---|
| §13, « Archiver » | **—** | **Périmètre** |
| §18, « Archiver un contenu dans son périmètre » | **Périmètre** | **Entité** |

**Deux colonnes divergent, et dans les deux sens.** Trouvé en lisant le §18 pour une **autre**
question — celle du motif d'archivage (§18.1) — ce qui est le §7.24 : deux sections d'un même
document peuvent régler la même action, et il faut les confronter avant d'en appliquer une.

**Non bloquant pour `T6`, qui n'archive aucune page** ; **bloquant pour `T7`**, qui livre
précisément l'archivage. Et **surtout pas l'union** : le §23.1 pose l'union des droits pour le cumul
de **rôles** d'une personne, pas pour le cumul de deux rédactions d'une même cellule.

---

# 6. Ce que `T6` ne fait pas

- **aucune publication, aucun archivage de page, aucune restauration** — `US006`, `T7`. La route
  n'écrit **jamais** `state`, `published_at` ni `content_page.archived_at`, et un contrôle de stack
  le mesure **après deux écritures** sur une page publiée ;
- **aucune présentation d'entité, aucun lien interne** — `US005`, `T8`, et `QO-120` attend Léa sur la
  liste des protocoles d'URL ;
- **aucun écran** — `T9` en lecture, `T10` en édition. **`#149` reste donc ouverte** : son critère
  dit « le périmètre suit la matrice », ce qui est tenu, mais `US004` n'est complète qu'avec son
  écran ;
- **aucun champ de `payload_json` validé** — `QO-121` attend Léa, et elle reste **bloquante pour
  `T10`**, qui devra dessiner des formulaires.

---

# 7. Ce que `T6` laisse

| Point | Où il va |
|---|---|
| **`ECART-063`** | **`T7`, et c'est la première chose à instruire** : le §13 et le §18 donnent deux grilles différentes pour « Archiver un contenu ». À défaut de réponse, retenir la **plus restrictive** de chaque cellule |
| **`ECART-062`** | **Léa**, avant `T9`. Ce qu'est « la page DSM » comme objet de produit |
| **`QO-121`** | **Léa**, **bloquante pour `T10`.** Les champs de chaque type de bloc |
| **`QO-119`, `QO-120`** | **Léa**, avant `T11` et `T8` |
| **Le déclencheur du comptage borné** | `T7`, `DEC-583`. « Un à trois responsables actifs » ne mord qu'à la **publication**, et `T6` est la première sous-étape à écrire dans `content_page` — mais elle n'écrit jamais `state`, donc la borne n'a toujours aucun écrivain |
| **Comment un écran découvre les pages de son périmètre** | `T7`. `T6` rend l'identifiant à la **création** ; un auteur qui revient demain n'a aucune route pour lister ses brouillons |
| **`PYTHONDONTWRITEBYTECODE` dans toute campagne de témoins** | **toute sous-étape qui retire des filtres un par un.** Le défaut `T6-3` est non déterministe et silencieux ; il se reproduira sur n'importe quel module dont deux variantes pèsent le même nombre d'octets |
