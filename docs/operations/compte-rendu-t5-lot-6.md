# Compte rendu — `T5` du LOT 6 : le rendu des blocs, et le refus de l'injection

**Sous-étape :** la cinquième du lot · **Date :** 15 septembre 2026
**Décision :** `DEC-584` · **Question ouverte :** `QO-121` · **Story :** `MVP-L06-US004` (1 sur 3), issue `#149`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 6**, ouvert le 13/09/2026 (`DEC-575`), **douze** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, **`T5`** |
| Restent | `T6` à `T12` |

---

# 2. Ce que la sous-étape a produit

`GET /api/v1/entities/{code}/pages/{type_de_page}/{slug}` rend une page **publiée** et ses blocs
dans l'ordre d'affichage.

## 2.1 Le critère est NÉGATIF, donc il lui fallait un témoin positif

« Aucun HTML arbitraire » **se satisfait tout seul quand rien n'est rendu**. Une sous-étape qui
aurait posé le refus sans servir un bloc aurait pu cocher son critère en toute bonne foi. C'est le
§7.39 — la leçon qui a fait **fusionner** `T5` et `T6` du LOT 5 — et c'est pourquoi le rendu et le
refus sont la même sous-étape ici.

Le test qui compte n'est donc pas un refus : c'est **un bloc légitime rendu**, et **du balisage qui
traverse comme du texte**.

## 2.2 Ce que `T5` NE valide pas, et pourquoi — `QO-121`

Le §15.2 dit qu'un bloc porte « des **champs structurés** ; un `payload_json` **validé par type
lorsque nécessaire** », et le cahier §10.7 ajoute « texte riche **limité** ».

**Mesure du 15/09/2026 : le corpus ne nomme AUCUN de ces champs, et ne dit pas ce qui limite le
texte riche.** Zéro occurrence dans les cinq documents de cadrage.

En inventer un schéma par type aurait été §6.5 — *une hypothèse déguisée en décision est pire qu'une
case vide* — et aurait coûté, si le vocabulaire arrêté par Léa différait, **une migration des données
ET un changement de contrat sur onze types**. Arbitrage de Jonathan du 15/09/2026 : le contenu est
servi comme une **donnée opaque**, et `QO-121` porte la question.

> **Ce que cela coûte est nommé, pas caché** : les écrans de **lecture** (`T9`) fonctionnent sur une
> donnée opaque ; les écrans d'**édition** (`T10`) auront besoin de noms de champs pour dessiner
> leurs formulaires. **`QO-121` est donc bloquante pour `T10`**, et elle se pose **après `QO-119`** —
> arrêter le vocabulaire des types avant leurs champs évite de décrire deux fois un type qui serait
> ensuite fusionné.

## 2.3 Ce qui EST tenu : la seule chose que le corpus écrit, et il l'écrit quatre fois

« Aucun HTML arbitraire n'est **stocké** ou **exécuté** » · « aucun HTML arbitraire ni script n'est
**accepté** ». **Trois verbes, que le découpage sépare :**

| Verbe | Qui le tient |
|---|---|
| **stocké** | `T1` — aucune colonne ne peut porter du HTML libre |
| **exécuté** | **`T5`** |
| **accepté** | `T6` — l'écriture |

**Et il est tenu par la STRUCTURE, jamais par un filtre.** Un filtre textuel serait une
**heuristique**, donc un défaut (§7.25) : `<` est parfaitement légitime dans « a < b », et chercher
`<script` laisserait passer `<img onerror=…`. Un garde-fou à faux positifs apprend à passer outre ;
un à faux négatifs ment.

Ce qui est exact est structurel :

- le contenu d'un bloc est un **objet** de part et d'autre — `dict[str, object]` en Python,
  `Readonly<Record<string, unknown>>` en TypeScript ;
- la réponse ne porte **aucun champ de nature HTML**, et un test le vérifie **sur les champs du
  modèle dérivés**, pas sur une liste : si quelqu'un ajoutait `html` ou `contenu_rendu`, il
  échouerait sans qu'on ait pensé à le mettre à jour ;
- `texteDuBloc` rend une **`string`**, et rien d'autre. Un écran qui passe par elle ne peut pas
  obtenir de balisage, **quelle que soit la donnée stockée** — §7.35, la propriété rendue
  structurelle plutôt que confiée à un contrôle qu'on pourrait retirer.

**Ce qui EST refusé, parce que c'est exact :** un `payload_json` qui n'est pas un **objet**. Refusé
**visiblement**, en 500, plutôt que réparé en silence (§7.20) — l'envelopper inventerait une clef,
l'ignorer ferait disparaître un bloc d'une page sans que personne le sache.

## 2.4 Deux partis d'adressage et de visibilité

**L'adresse porte le type ET le slug**, parce que le §15.1 dit « `slug` | Unique dans l'entité **et
le type** ». Adresser par le slug seul supposerait une unicité que le modèle n'écrit pas. Une seule
route couvre ainsi les **cinq** types, là où une route par ressource en aurait demandé autant.

**Une page en brouillon rend le MÊME 404 qu'un slug inconnu.** Distinguer apprendrait son existence,
et viderait `US006` — « **prévisualiser** puis publier » — de son sens. C'est la story de `T7`, avec
sa propre grille : le §13 donne « Publier » à une portée **Périmètre** là où « Modifier » vaut
**Entité**.

## 2.5 Qui lit — et l'annexe A §13 ne doit pas être lue seule

Le §13 porte une ligne « **Consulter** » à **six** colonnes : DSM, ESM, BOOST, OFFICE, ADM-E, SUPER.
**Ni `EMP` ni `NEW`.**

La lire seule refuserait le contenu à l'Employé, c'est-à-dire à l'acteur pour qui ce portail existe.
**Ces tableaux n'ONT PAS ces deux colonnes**, et une absence de colonne n'est pas une exclusion —
c'est le piège que `T2`, `T3` et `T4` ont tous les trois mesuré. Le §5, matrice générale de
**consultation**, accorde « Framework », « Cercles » et « Bureaux » aux huit rôles authentifiés ; le
contenu d'une page de cercle se consulte comme le cercle.

---

# 3. Contrôles exécutés

```text
make check              code=0   1 056 pytest (727 d'integration) · 509 Vitest
make framework-check    35 controles, 0 echec   ← a travers Caddy, vraie session
make docs-check · make icloud-verify · make env-check              tous code=0
```

**Aucune cible `make` nouvelle.** `framework-check` est **étendu de 29 à 35 contrôles** — il porte
déjà le décor, la session et le ménage. Rien à ajouter dans `ci.yml`.

## 3.1 Le contrôle de stack le plus utile porte sur les OCTETS

```text
ok   le balisage arrive COMME UNE DONNEE : type de contenu `application/json`,
     charge INTACTE dans les octets — rien n'est interprete, et rien n'est
     retire en silence
```

Trois choses y sont exigées ensemble, et aucune ne suffit seule : le type de contenu est
`application/json` **et non `text/html`**, donc aucun navigateur n'interprétera cette réponse comme
un document ; la charge `<script>alert('xss')</script>` s'y trouve **telle quelle**, ce qui prouve
que rien n'a été retiré en silence — *un filtre qui aurait mangé la chaîne donnerait la même
observation qu'une absence d'injection* ; et elle arrive comme une **valeur de chaîne** dans un
objet JSON.

## 3.2 Dix témoins exécutés, huit discriminent

| Filtre retiré | Tests en échec |
|---|---|
| `cp.state = :etat` | **2** |
| `b.archived_at IS NULL` | **2** |
| `ORDER BY b.display_order, b.id` | **2** |
| `cp.archived_at IS NULL` · `cp.page_type` · `cp.entity_id` · `b.content_page_id` | **1** chacun |
| le refus du payload non-objet | **1** |
| **`b.entity_id = :entite`** | **0** — défaut `T5-1` |
| **la copie `dict(charge)`** | **0** — défaut `T5-2` |

---

# 4. Défauts trouvés — **quatre**, tous dans mon propre travail

## `T5-1` — le filtre d'entité des blocs est redondant, et c'est la deuxième fois en deux sous-étapes

Retirer `AND b.entity_id = :entite` laisse les vingt-deux tests verts. La cause est au catalogue :

```text
fk_content_block_content_page
  FOREIGN KEY (content_page_id, entity_id) REFERENCES content_page(id, entity_id)
```

La clé étrangère **composite** du §25.3 interdit qu'un bloc pointe la page d'une autre entité, si
bien que `b.content_page_id = :page` suffit.

**Le filtre est conservé** — c'est l'idiome de cloisonnement de tout ce dépôt, et une requête locale
qui ne nommerait pas son entité se lirait comme une requête globale — **mais il n'est pas ce qui
protège**, et le module le dit avec sa mesure. Ce qui protège est la clé composite, et
`make isolation-check` exige déjà qu'elle existe.

> **C'est exactement `T4-2`, une sous-étape plus tard**, et la répétition est la leçon : quand un
> filtre paraît évident, le témoin dit s'il travaille. Deux fois sur deux, il ne travaillait pas — et
> deux fois sur deux, ce qui protégeait vraiment était **une contrainte ailleurs**, déjà sous
> contrôle. §7.32.

## `T5-2` — j'avais écrit une copie défensive, et un test qui prétendait la prouver

`contenu=dict(charge)`, avec ce commentaire : « une COPIE : la valeur rendue par le pilote ne doit
pas être partagée avec l'appelant ». Et un test qui mutait la valeur rendue puis relisait.

**Les deux ne tiennent pas**, et c'est mesuré : psycopg construit un objet **neuf par ligne lue**,
le retirer laisse les vingt-deux tests verts, et `mypy --strict` ne l'exige pas davantage. Mon test
relisait **depuis la base**, ce qui reconstruit un dictionnaire de toute façon : il aurait passé avec
ou sans la copie.

**La copie et le test ont été retirés.** §7.32 — n'écris pas de défense contre un état qu'aucun
contrôle ne peut observer — et §7.0 : un contrôle dont l'échec produirait la même observation que le
succès ne prouve rien.

## `T5-3` — j'ai doublé les accolades d'une valeur SUBSTITUÉE dans une f-string

Le décor du vérificateur est une f-string. J'y ai injecté la charge JSON en doublant ses accolades,
comme on le fait pour le texte **littéral** du gabarit.

**Une valeur substituée n'est pas retraitée** : seules les accolades littérales se doublent. Le
doublement a produit du JSON invalide. Corrigé, et le motif est écrit à côté.

## `T5-4` — les apostrophes de la charge ont cassé le littéral SQL

```text
ECHEC  decor impossible : ERROR: syntax error at or near "xss"
LINE 59: ...'{"texte": "<script>alert('xss')</scr...
```

La charge d'injection contient `alert('xss')`. Retenu : le **guillemet-dollar** `$json$…$json$`, et
non le doublement des apostrophes — doubler aurait marché, mais **altérerait la chaîne** que le
contrôle cherche ensuite dans les **octets servis**, ce qui aurait vidé le contrôle de son sens sans
le faire échouer.

> **`T5-3` et `T5-4` sont une seule classe, celle du §7.2** : du texte qui traverse une couche qui
> le réinterprète — le shell hier, une f-string et un littéral SQL aujourd'hui. Les deux ont échoué
> **bruyamment**, ce qui est la seule bonne nouvelle : un décor qui refuse de se poser ne laisse
> pas croire qu'il a testé quelque chose.

---

# 5. Ce que `T5` laisse

| Point | Où il va |
|---|---|
| **`QO-121`** | **Léa.** Les champs de chaque type de bloc, et ce que « limité » borne dans le texte riche. **Non bloquante** pour `T6` et `T9`, **bloquante pour `T10`** |
| **L'écriture d'un bloc** | `T6`, qui tient le verbe **accepté** — et la grille de l'écriture du LOT 5 **ne se réemploie pas** : le §13 donne « Modifier un contenu de cercle » au Booster avec portée **Cercle**, et **rien** au DSM |
| **Brouillon, publication, archivage** | `T7`, `US006`. Cette route ne sert **que** le publié |
| **Comment un écran découvre le slug d'une page de cercle** | `T9`. `T3` et `T4` servent les ressources, pas le slug de leur page de contenu — il faudra l'exposer, ou adresser autrement |
| **Les écrans** | `T9` en lecture, `T10` en édition. **`#149` reste donc ouverte** |
