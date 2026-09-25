# Compte rendu — `T4` du LOT 6 : les bureaux en lecture

**Sous-étape :** la quatrième du lot · **Date :** 15 septembre 2026
**Décision :** `DEC-583` · **Story :** `MVP-L06-US003`, issue `#148`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 6**, ouvert le 13/09/2026 (`DEC-575`), **douze** sous-étapes |
| Faites | `T1`, `T2`, `T3`, **`T4`** |
| Restent | `T5` à `T12` |

---

# 2. Ce que la sous-étape a produit

`GET /api/v1/entities/{code}/offices/{code_bureau}` rend un bureau avec sa **description**, sa
**localisation**, ses **responsables actifs** et un booléen **`publie`**.

**`T2` émettait déjà le chemin de cette page**, sur chaque carte de bureau de la synthèse Framework,
et ce chemin ne menait nulle part. Un contrôle de stack lie désormais les deux : le
`chemin_detaille` de la **carte** et celui de la **page** doivent être le même, sinon le lien est
mort et rien ne le dirait.

## 2.1 Ce que `T4` NE fait pas, et c'est le cœur de la sous-étape

**La fiche et la passation annonçaient toutes deux que `T4` poserait un déclencheur.** Le §8 de
`fiche-lot-6.md` écrivait « `T4` posera un **déclencheur** » pour tenir « un bureau possède entre un
et trois responsables actifs **lorsqu'il est publié** » (§8.4 du modèle).

**C'était une prévision, pas une mesure — §7.41.** Deux choses la démentent :

| Ce qui la dément | Où |
|---|---|
| **le critère de la story dit « AFFICHÉS »** | `MVP-L06-US003` : « BDS, BDE et BDG sont configurables ; un à trois responsables actifs **sont affichés** ». De l'affichage, pas une interdiction |
| **le déclencheur n'aurait aucun ÉCRIVAIN** | la borne ne mord qu'à la publication, et au 15/09/2026 **aucune route n'écrit dans `content_page`** — zéro `INSERT INTO` et zéro `UPDATE` dans `app/`, mesuré |

Un déclencheur posé ici aurait eu son **témoin positif** — publier un bureau conforme et voir la
borne laisser passer — dans une sous-étape ultérieure. C'est exactement ce que le §7.39 a appris à
refuser au LOT 5, quand `T5` et `T6` ont dû fusionner pour cette raison.

**Arbitrage de Jonathan du 15/09/2026 : le déclencheur va à `T7`**, là où la publication a un
écrivain. `DEC-583`.

## 2.2 Ce que `T4` fait à la place, et qui est plus utile

**Son décor produit exactement ce que la borne interdit** :

```text
un bureau PUBLIE a ZERO responsable       ← §8.4 l'interdit, la base le permet
un bureau PUBLIE a QUATRE responsables    ← §8.4 l'interdit, la base le permet
```

Et il exige que la lecture les rende **tels quels**. Un service supposant « au moins un » se serait
effondré sur le premier ; un tronquant à trois aurait **menti** sur le second. **Aucun des deux
échecs n'aurait été visible avec un décor à deux responsables** — c'est le §7.42, la version
« comptage » du couple.

**Le contrat TypeScript ne refuse ni l'un ni l'autre**, et c'est délibéré : refuser ferait échouer
l'écran sur un état réel de l'API. Il **exige** en revanche que `nombre_de_responsables` vaille la
longueur du tableau — deux sources pour une même grandeur divergent (§7.0, sixième proposition) —
et une fonction séparée, `respecteLaBorneDuHuitQuatre`, porte la **question** de la conformité.
C'est la forme du §7.20 : *exiger ce qui est exigible, rapporter visiblement ce qui ne l'est pas*.

## 2.3 Aucune pagination — le raisonnement de `T3` à l'envers

`T3` pagine les membres d'un cercle parce que le §18.2 — intitulé « Pagination », dans le chapitre
**API**, ne nommant aucune ressource — régit toute **population**.

**Les responsables d'un bureau n'en sont pas une** : le §8.4 les déclare **bornés**. Paginer un
ensemble de trois éléments au plus inventerait un paramètre que le cahier ne demande pas (§6.5).

## 2.4 `publie` vient de la page de contenu, jamais de la table `office`

`DEC-576`, après `ECART-031` : la table `office` ne porte **aucun** état de publication. Sans ce
booléen, la réponse ne saurait pas distinguer un zéro **légitime** — un bureau en brouillon n'a
encore personne — d'un zéro qui **enfreint** le §8.4.

`EXISTS` et non une jointure : l'unicité posée par `T1` porte sur `(entity_id, page_type, slug)`, si
bien que plusieurs pages `OFFICE` coexistent légitimement. « Au moins une page publiée » est la
seule lecture qui ne suppose pas ce que le modèle n'écrit pas.

## 2.5 « Entièrement configurables » est prouvé par une ABSENCE, sur l'AST

Le cahier §10.3 dit « Bureaux initiaux : BDS ; BDE ; BDG. Ils restent **entièrement
configurables** », et c'est le premier membre du critère de `US003`. Un test l'exige : **aucun
littéral en position exécutable** ne porte l'un de ces codes, sur les **64** modules de
`apps/api/app/`, le périmètre dérivé du disque à chaque exécution.

Le discriminant est l'**AST** et non le texte — voir le défaut `T4-1` ci-dessous.

---

# 3. Contrôles exécutés

```text
make check              code=0   1 035 pytest (709 d'integration) · 488 Vitest
make framework-check    29 controles, 0 echec   ← a travers Caddy, vraie session
make parametres-check   code=0   166 fichiers, 672 requetes lues, 0 faute
make docs-check · make icloud-verify · make env-check              tous code=0
```

**Aucune cible `make` nouvelle.** `framework-check` est **étendu de 21 à 29 contrôles** — il porte
déjà le décor, la session et le ménage, qu'un second vérificateur aurait dupliqués (§7.27). Donc
**rien à ajouter dans `ci.yml`**, qui appelle les cibles une par une (§7.36).

## 3.1 Huit témoins exécutés, sept discriminent — et le huitième est le plus instructif

Chaque filtre a été retiré, un par un, et la suite relancée :

| Filtre retiré | Tests en échec |
|---|---|
| `fr.period @> :instant` | **1** — l'affectation future et l'affectation close réapparaissent |
| `cp.state = 'published'` | **2** — brouillon et archivée publient |
| `cp.page_type = 'OFFICE'` | **1** — une page `HOME` publie le bureau |
| `cp.office_id = o.id` | **1** — la page du voisin publie celui-ci |
| `cp.archived_at IS NULL` | **1** |
| `o.archived_at IS NULL` | **1** |
| `fr.archived_at IS NULL` | **1** |
| **`fr.responsibility_type = 'OFFICE_MANAGER'`** | **0** — voir le défaut `T4-2` |

---

# 4. Défauts trouvés — **quatre**, tous dans mon propre travail

## `T4-1` — mon garde-fou était un faux positif sur la prose qui le justifie

Le test « aucun code de bureau initial en dur » cherchait `\bBDS\b` dans les **lignes** des modules.
Il a échoué sur **cinq** citations du cahier en docstring, dont **trois dans le module qu'il était
censé protéger** :

```text
64 modules examines ; ces lignes ecrivent un code de bureau initial en dur :
['organization/bureaux.py:5', 'organization/bureaux.py:16', 'organization/bureaux.py:19',
 'permissions/perimetre.py:26', 'permissions/perimetre.py:27']
```

**C'est mot pour mot la première version du garde-fou du §7.25** — « elle se déclenchait sur le
**commentaire** expliquant le motif qu'elle interdit ».

**Le discriminant n'est pas le texte, c'est l'AST.** Ce que « entièrement configurables » interdit
est un code qui se **comporte** différemment selon le bureau ; un littéral cité dans une prose ne se
comporte pas. Deux propriétés de l'`ast` donnent l'exactitude gratuitement : les **commentaires n'y
figurent pas du tout**, et les **docstrings sont identifiables**. Tout autre littéral est une valeur
que le code manipule.

> **Et le garde-fou a désormais son propre témoin**, deux sources qui ne diffèrent que par la
> **position** du littéral — une en docstring, une dans un `return code == "BDS"`. Sans lui, un
> contrôle qui ne cherche rien rendrait une liste vide partout, donc vert partout.

## `T4-2` — mon test affirmait qu'un filtre discriminait ; le témoin dit qu'il ne peut pas

J'avais écrit, en toutes lettres : « le type est donc un discriminant réel, et non décoratif : sans
le filtre sur `responsibility_type`, le Booster d'un cercle apparaîtrait ici. »

**Retirer le filtre laisse les vingt-trois tests verts.** La cause est une contrainte lue au
catalogue :

```text
ck_framework_responsibility_assignment_portee_selon_le_type
  CHECK ((type = 'BOOSTER' AND circle_id IS NOT NULL AND office_id IS NULL) OR ...)
```

`office_id IS NOT NULL` implique donc `type = 'OFFICE_MANAGER'`, et `fr.office_id = :bureau` écarte
déjà tout le reste. **J'avais écrit une défense contre un état que la base interdit — §7.32.**

**Ce que j'en ai fait :** le filtre est **conservé** — il dit l'intention de la requête, et la carte
de `T2` le porte, deux lectures du même fait qui divergeraient sinon — mais le module **dit qu'il
est redondant**, avec sa mesure. Et la fausse preuve est remplacée par celle que le §7.32
prescrit : un test qui **exige que la base continue d'interdire** cet état, sur le **nom** de la
contrainte violée. Si un lot ultérieur la relâchait, ce test échouerait — et celui qui la relâche
saurait qu'il doit relire cette lecture.

## `T4-3` — l'ordre du ménage, neuvième occurrence de la classe §7.30

Le vérificateur supprimait `office` **avant** `content_page`, qui le référence. L'ordre a tenu tant
qu'**aucune page ne pointait un bureau** ; `T4` en a créé une.

**Le dommage a été bien plus large que l'erreur**, et c'est la signature de cette classe : le ménage
a laissé **2 entités et 3 bureaux**, et au `make check` suivant **trois tests sans aucun rapport ont
échoué** — `test_entites.py` et `test_organisation.py`, qui comptent des lignes en **absolu**.
Aucun des trois messages ne nommait la cause.

> **C'est le garde-fou posé après `T2-2` qui l'a dit**, en lisant les codes de sortie du ménage :
> « 2 suppression(s) en échec — des lignes SUBSISTENT ». Sans lui, l'échec aurait été **silencieux**
> et le diagnostic aurait coûté une heure au lieu de deux minutes.

**Et un second défaut du même endroit :** la ligne `ok nettoyage — tout ce qui portait … est retiré`
s'imprimait **même après l'échec**, juste sous « des lignes SUBSISTENT ». Un avertissement faux
apprend à ne plus le lire (§7.21). Elle est désormais dans un `else`.

**La preuve que c'est corrigé** est une mesure d'après, pas une affirmation : le vérificateur relancé
sort en 0, et le comptage des trois tables qui subsistaient rend **0, 0, 0**.

## `T4-4` — j'ai rejoué un piège documenté : `make code-refresh`

Le vérificateur a rendu **404** sur la page du bureau. Le §11 de la passation écrit pourtant, à deux
endroits : « Lance `make code-refresh` AVANT, jamais après ». Le conteneur portait le code d'avant, et
un 404 « route inconnue » est **indistinguable** du 404 légitime d'un bureau inconnu.

**Ce que mon contrôle a bien fait** : il a refusé de continuer — « sans page de bureau, les contrôles
suivants ne prouvent rien » — au lieu de laisser les sept suivants s'exécuter sur du vide.

**Et ma sonde de diagnostic était fausse elle aussi.** J'ai cherché `/app/app/organization/bureaux.py`
dans le conteneur et conclu « ABSENT » ; le module vit en `/app/apps/api/app/organization/bureaux.py`.
Ma sonde aurait dit « ABSENT » **même après** le rafraîchissement : elle ne distinguait pas « absent »
de « pas là où je regarde » — §7.21, troisième leçon. C'est la séquence 404 → `code-refresh` → 200 qui
a prouvé la cause, pas la sonde.

---

# 5. Ce que `T4` laisse

| Point | Où il va |
|---|---|
| **Le déclencheur du comptage borné** | **`T7`**, `DEC-583`. La borne ne mord qu'à la publication, et c'est `T7` qui publie — donc le premier écrivain qui puisse l'exercer |
| **Le rendu des blocs d'un bureau** | `T5`. `T4` sert la structure du bureau, **aucun contenu éditorial** |
| **L'écran du bureau** | `T9`. `#148` reste donc **ouverte** : son critère dit « affichés », et aucun écran n'existe |
| **`QO-119`** | attend **Léa** — le vocabulaire des blocs, avant `T11` |
| **`QO-120`** | attend Jonathan **et** Léa — la liste des protocoles d'URL, avant `T8` |
| **`ECART-014`, `ECART-015`** | attendent **Léa**. `T4` rend la **description** d'un bureau, qui sera vide pour les trois bureaux amorcés |

## 5.1 Ce qui a été corrigé ailleurs, et ce qui a été laissé intact

`DEC-583` renverse une prévision écrite en **six** endroits, dérivés sur le dépôt et non sur mes
onglets (§7.40). Ils ont été traités **par nature** :

| Document | Traitement |
|---|---|
| `fiche-lot-6.md` §8 et son tableau de découpage | **corrigés**, avec une note datée qui garde la trace de ce qui était écrit |
| `CLAUDE.md`, cellule « Prochaine action » | **réécrite** — c'est le document qu'un agent lit en entier |
| `routes.py`, docstring de `BureauRendu` · `test_framework.py` | **corrigés** : du code qui prédit faux se lit comme une consigne |
| `compte-rendu-t1-lot-6.md` et `compte-rendu-t2-lot-6.md` | **laissés intacts, délibérément.** Leurs sections « ce que cette sous-étape laisse » étaient **justes à leur date**, et réécrire un compte historique pour le faire coïncider avec ce qu'on sait après serait pire que de le nommer. C'est le §7.41 qui apprend à les lire comme des **prévisions** |
