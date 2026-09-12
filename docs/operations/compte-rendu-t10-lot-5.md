# Compte rendu — `T10` du LOT 5 : le trombinoscope à l'écran

**Story :** `MVP-L05-US003` — *Utiliser une carte retournable accessible*, `P0`, taille **M**, issue `#118`
**Décision :** `DEC-571`
**Écart ouvert :** `ECART-060`
**Date :** 12 septembre 2026

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 5**, ouvert le 24/08/2026, **onze** sous-étapes |
| Faites | `T1` à `T5`, `T7` à `T9`, et **`T10`** |
| Prochaine | **`T11` — la page de profil à l'écran** (`US003`, `US004`) |
| Périmètre de `T10` | la liste paginée, la recherche temporisée, la **carte retournable**, et « Voir plus » |
| Hors périmètre, **nommé** | quatre des six filtres (`ECART-060`) · le contenu de la fiche profil, qui est `T11` |
| Issue `#118` | **reste ouverte** : `US003` porte aussi la carte du profil, que `T11` livrera |

**C'est le premier écran métier du projet.** Les LOTS 1 à 4 ont livré la page de statut, le portail
national, le cadre et la navigation ; tout le reste était de l'API.

---

# 2. Ce que la sous-étape a produit

## 2.1 La réponse au critère est STRUCTURELLE, pas testée

Le critère dit « le recto/verso fonctionne au **clic, toucher et clavier** ». La face de la carte est
un **`<button>` natif**, et c'est tout :

| Mode | Ce qui le rend vrai |
|---|---|
| clic | le bouton |
| **toucher** | le navigateur dérive un `click` d'un `touchend`, pour un bouton, sans code |
| clavier | **Entrée et Espace**, le `role`, le `tabIndex`, l'état annoncé — tout est natif |

Un `<div onClick>` avec `onKeyDown` couvre les mêmes cas **tant qu'on n'oublie rien**. C'est le §7.35 :
rendre la propriété structurelle plutôt que la tester.

> **ET LE TOUCHER NE PEUT PAS ÊTRE ÉPROUVÉ DANS `jsdom`**, qui ne synthétise aucun `click` à partir
> d'un `touchend`. Un test qui déclencherait un `touchStart` puis appellerait `click()` ne prouverait
> que **son propre appel** — §7.0, quatrième proposition. Ce qui est donc exigé est **la balise** :
> `expect(face.tagName).toBe('BUTTON')`. C'est la seule observation qui distingue un livrable tactile
> d'un `<div>` qui ne l'est pas, et la retirer casse les trois modes d'un coup.

**Les deux faces existent, et la cachée porte `hidden`** — l'attribut, non une classe : il la retire
du parcours de tabulation **et** de l'arbre d'accessibilité. `aria-expanded` porte l'état.

## 2.2 Le §10.1 exige un verso professionnel, et l'API n'en servait aucun

> « Le recto présente principalement la photo et l'identité. Le **verso** présente les informations
> **professionnelles principales**. »

La ligne de liste portait **huit** champs, aucun professionnel. Un écran ne peut pas inventer ce que
l'API ne sert pas : elle en porte **douze**.

**Le montage est une TROISIÈME requête, non quatre jointures de plus**, et le motif est mesurable :

| Montage | Coût |
|---|---|
| quatre `LEFT JOIN` sur la requête de **page** | elle trie toute la population filtrée **avant** son `LIMIT` — cinq mille lignes au volume du quatrième critère de sortie, pour n'en garder que vingt-cinq |
| une **troisième requête** sur les identifiants rendus | bornée à **cent** lignes par le §18.2, et le chemin chaud reste intact |

**Trois reste un nombre BORNÉ**, et c'est ce que le cinquième critère de sortie demande : il ne dépend
ni du nombre de lignes — quatre tests le vérifient sur les trois tailles — ni du nombre de cercles.

## 2.3 Cinq tests gelés sont tombés, et c'était leur rôle

| Où | Ce qui a changé |
|---|---|
| `test_trombinoscope.py` | les champs : 8 → **12**, deux tests |
| `test_recherche_et_filtres.py` | le compte de requêtes : 2 → **3**, quatre tests |
| `test_photo_de_profil.py` | le même compte, un test |
| `verifier-trombinoscope.py` | les champs servis, « ni plus ni moins » |

`T5` avait déjà fait tomber le premier en ajoutant `photo`, et son docstring le dit : « le laisser
échouer jusqu'à ce que l'attendu soit mis à jour est ce qui rend l'addition d'un champ **visible en
revue** ». Aucun n'a été affaibli en comparant par inclusion.

## 2.4 La couleur du cercle n'est jamais seule — §10.1

> « La couleur du cercle peut être utilisée sur les bordures, arrière-plans légers et badges, mais
> **jamais comme seul moyen de transmettre une information**. »

Le **nom** du cercle est du texte sur le verso ; la couleur ne fait que border la carte. Un test
l'exige, sans quoi la règle resterait une intention. **Le jeton voyage avec le nom** dans la réponse —
servir le seul jeton rendrait la règle inapplicable côté écran.

**Un jeton inconnu ne donne AUCUNE couleur.** Le design system dit, depuis `T10` du LOT 1 : « aucune
couleur de cercle : c'est une notion métier du **LOT 6** ». Seuls les quatre jetons de marque sont
reconnus ; tout autre laisse la bordure neutre, et le nom reste lisible — ce que le §10.1 protège.

## 2.5 La temporisation de 300 ms, et deux filtres sur six

`ECART-050` avait établi que les 300 ms du §9.3 sont un **délai d'écran**, non un budget de réponse —
le §25.2 donne 800 ms au P95. `T3` l'avait retiré de son périmètre **en le nommant** ; il arrive ici.
Sans lui, « Alexandra » lancerait dix requêtes sur cinq mille profils.

**Deux filtres sur six, et c'est mesuré plutôt qu'oublié.** Quatre des cinq filtres de `T3` prennent
un **identifiant**, et aucun endpoint ne sert ces listes — **zéro occurrence** sur les vingt-et-un
chemins du manifeste. Les fabriquer depuis la page courante donnerait un filtre qui ne propose que ce
qui est déjà visible. `statut` fait exception : son domaine est **fermé**, §6.5. `ECART-060`.

## 2.6 « Voir plus » mène à une route réelle, dont le contenu est `T11`

Le critère l'exige — c'est `US003`, donc **cette** sous-étape. Un lien qui tombe sur le fourre-tout
404 est atteignable et **inutile** : la navigation serait simulée. La route existe donc, et la page
**dit quel lot** apportera son contenu — exactement le parti de `PageRubrique`, posé au `T4` du LOT 4.

**Et « Voir plus » est FRÈRE du bouton, jamais enfant** : un lien dans un bouton est un imbriquement
interactif invalide.

---

# 3. Contrôles exécutés

```text
make check                 code=0 — Tous les controles sont passes
make profil-check          code=0 — controles executes : 45   echecs : 0
make trombinoscope-check   code=0 — controles executes : 38   echecs : 0
make web-check             code=0 — 7 controles, la racine de Caddy est approuvee
make docs-check            code=0

913 pytest  ·  336 Vitest (93 contracts + 103 ui + 140 web)  ·  1 249 au total
```

Et la route est **servie** par la coquille, mesurée à travers Caddy :

```text
/entites/BORDEA00/trombinoscope   ->  200, text/html
API sans session                  ->  401
```

Le contrôle de stack gagne une épreuve que le gel des champs ne couvrait pas :

```text
ok   les 4 champs du VERSO sont RENSEIGNES — metier « Ingenieure logicielle »,
     statut « mission », client « Client Alpha », cercle « Cercle des essais »
```

> **Un contrôle de présence n'aurait pas suffi.** « Douze champs, ni plus ni moins » passerait avec
> les quatre à `null` — ce que rendrait exactement une requête d'enrichissement qui ne joindrait
> rien. §7.0, quatrième proposition.

**Ce qui n'est PAS prouvé :** je n'ai **pas** ouvert l'écran dans un navigateur. Il faut une session,
donc un compte et un mot de passe, et je n'en crée ni n'en saisis (§7.14). Les 137 tests `jsdom`
prouvent la structure et le comportement ; le **rendu visuel** reste à voir, et la recette est au §6.

---

# 4. Défauts trouvés — **huit, tous dans mon propre travail**

> **LE HUITIÈME A ÉTÉ TROUVÉ APRÈS LA PORTE VERTE**, en préparant la démonstration — et il vivait dans la fiche profil depuis `T4`. Une porte d'intégration continue qui passe dit que les contrôles écrits sont verts, jamais qu'ils regardent au bon endroit.

## `T10-1` — Un `setState` synchrone dans un effet, et la correction vaut mieux que le contournement

`eslint` : « Calling setState synchronously within an effect can trigger cascading renders ». Il a
raison. Le chargement est désormais **dérivé** — on compare les critères du résultat à ceux demandés —
plutôt que posé.

**Et l'écran y gagne** : les résultats précédents restent visibles pendant le chargement du suivant,
au lieu de disparaître à chaque frappe. C'est ce qu'une recherche à la volée doit faire.

## `T10-2` — Deux propriétés CSS employées et non définies, que `cadre-check` a nommées

`--encre-doux` n'existe pas : le jeton s'appelle **`--encre-douce`**. Et `--carte-cercle` était posée
**en ligne** par le composant, donc absente de toute feuille.

> Le contrôle le dit mieux que moi : « la page rendra les défauts du navigateur, **sans que rien
> n'échoue** ». C'est le défaut mesuré le 23/08/2026, quatorze propriétés d'`auth.css` qui ne
> résolvaient rien.

## `T10-3` — Le nom accessible concaténait sans séparateur, deux fois

Un `<span>` masqué à l'œil produisait **« Voir plussur Ada Lovelace »** et **« …informations
professionnellesAda Lovelace »**. Le calcul du nom accessible concatène les nœuds de texte **sans
séparateur**, et ni JSX ni une accolade n'y changent rien.

Corrigé par `aria-label` sur les deux — ce qui, au passage, évite qu'une grille de cent cartes
présente cent commandes nommées « Voir plus ».

## `T10-4` — J'ai affirmé que `queryByText` respecte `hidden`. C'est faux.

Mon test disait « la face cachée est absente de la requête ». **`queryByText` parcourt le DOM sans
regarder la visibilité**, et les deux tests qui s'y fiaient ont échoué. La mesure exacte est
l'attribut lui-même — `closest('[hidden]')` — et le commentaire dit désormais le vrai.

C'est le §7.11 dans mon propre code : **vérifie ce que la documentation affirme, même quand c'est toi
qui l'écris.**

## `T10-5` — Un composant exporté sans test, que `cadre-check` a refusé

`CarteRetournable` était exporté par `packages/ui` sans un seul test. Le contrôle exige un test par
composant exporté, et il a raison : un composant du design system est fait pour être réemployé, donc
son contrat doit être figé ailleurs que dans son unique appelant.

## `T10-6` — Les minuteurs feints non restaurés, et six tests en attente de 5 000 ms

`restoreMocks` et `unstubGlobals` sont actifs (`DEC-471`) ; **ils ne restaurent pas les minuteurs**.
Un test qui échoue avant son `useRealTimers` laisse les suivants attendre pour toujours — six
échecs à 5 000 ms, dont la cause n'était dans aucun d'eux. Un `afterEach` le règle.

## `T10-7` — J'ai ensemencé la base de dev, et soixante-six tests sont tombés

Pour **voir** l'écran, j'ai lancé `make jeu-de-donnees` : 25 entités, 5 000 profils, **commités**.
Le `make check` suivant a rendu **66 échecs** sur des tests qui n'ont rien à voir avec `T10`.

> **C'est la classe §7.30, exactement.** Les tests d'intégration comptent des lignes **en absolu**
> dans une transaction annulée : `assert count == 2` ne vaut que sur une base propre. Aucun des 66
> messages ne nommait la cause — ils disaient « assert 5157 == 2 ».

Remis à zéro par le chemin documenté au §5.6 : `make down`, suppression du **seul** volume
`db-data`, `make up`, `make migrate`. **Pas `make destroy`**, qui aurait emporté `caddy-data` avec
lui, donc l'autorité approuvée dans le trousseau — et coûté à Jonathan une réapprobation.

**Le piège vaut d'être connu :** `make jeu-de-donnees` est fait pour mesurer la performance au
volume, et il **commite**. Il n'a aucune cible de nettoyage. Le lancer sur la base de développement
rend la suite d'intégration rouge jusqu'à ce qu'on la remette à zéro.

## `T10-8` — `str(None)` rend la chaine « None », et elle est servie à cent pour cent des cercles

**Trouvé en préparant la démonstration, après que la porte d'intégration continue est passée au
vert.** L'API servait, pour **chaque** cercle du jeu de données :

```json
"cercle": {"code": "CLOUD", "nom": "Cloud", "jeton_de_couleur": "None"}
```

`circle.color_token` est **nullable** — `information_schema` rend `is_nullable = YES`, mesuré — et
le service faisait `str(color_token)`. Sur `None`, `str()` rend la chaîne `"None"` : **un jeton
d'apparence parfaitement plausible**, qu'aucun écran ne reconnaît, et que le contrat déclarait
`string`.

| Mesure | Valeur |
|---|---|
| cercles du jeu de données | **100** |
| dont un `color_token` non nul | **0** |
| donc lignes servant `"None"` | **100 %** |

**LE DÉFAUT EST NÉ EN `T4`, PAS EN `T10`.** La fiche profil porte les **deux** premiers sites —
`profil.py`, le cercle principal et les secondaires — et `T10` n'a fait que **recopier le motif**
dans la liste. Ne corriger que l'instance que je venais d'écrire aurait été le §7.40 exactement :
*une correction appliquée aux fichiers sous la main ne couvre que ceux-là.*

**Le périmètre a donc été DÉRIVÉ du catalogue, non listé de mémoire.** Parmi toutes les colonnes
textuelles que ces requêtes traversent, **`circle.color_token` est la SEULE nullable** qui atterrisse
dans un champ non optionnel : `person.first_name`, `circle.name`, `entity_membership.professional_category`,
`media_variant.object_key` et les autres sont toutes `NOT NULL`. Trois sites, deux modules, et la
mesure dit qu'il n'y en a pas un quatrième.

```sql
SELECT table_name||'.'||column_name, is_nullable FROM information_schema.columns
WHERE data_type IN ('character varying','text') AND table_name IN (…);
```

**POURQUOI AUCUN TEST NE LE VOYAIT : TOUS MES DÉCORS POSAIENT UN JETON.** Les trois fixtures — celle
de la recherche, celle de la fiche, celle du vérificateur de stack — écrivaient `'bleu'`. Un décor
qui ne produit jamais la valeur en cause ne peut rien dire d'elle. Et le contrôle de stack de `T10`
exigeait que les quatre champs du verso soient **renseignés** : `cercle` est une **structure**, donc
il l'était — avec un jeton mensonger à l'intérieur.

**La correction fait porter à chaque décor le COUPLE**, deux lignes ne différant que par la colonne
en cause :

| Décor | Témoin | Cas |
|---|---|---|
| `test_recherche_et_filtres.py` | cercle A, `'bleu'` | cercle B, **aucun jeton** |
| `test_fiche_profil.py` | principal et `second-a`, `'bleu'` | `second-b`, **aucun jeton** |
| `verifier-profil.py` | cercle principal, `'bleu'` | cercle secondaire, **aucun jeton** |

**Témoins négatifs exécutés, dans les deux mondes.** Défaut réintroduit aux trois sites :

```text
pytest        2 failed, 40 passed   — la liste ET la fiche
profil-check  controles 45, echecs 1
              ECHEC  jetons : principal 'bleu', secondaire sans couleur
                     {'nom': 'Cercle sans couleur', 'jeton_de_couleur': 'None'},
                     chaine « None » absente : False
contrat       1 failed | 92 passed  — « accepte un cercle dont le JETON vaut `null` »
```

> **ET LE CONTRÔLE DE STACK CHERCHE LA CHAÎNE DANS LES OCTETS SERVIS**, pas dans l'objet décodé :
> `b'"None"' not in reponse.corps`. C'est la forme exacte que le défaut produisait **sur le
> réseau**, et c'est elle qu'un futur retour en arrière reproduirait.

**UNE MOITIÉ DE LA CORRECTION N'EST OBSERVABLE PAR AUCUN TEST, ET C'EST MESURÉ.** Côté écran,
`COULEURS_DE_CERCLE[null]` rend `undefined` — exactement ce que rend le chemin gardé. Les 140 tests
`web` restent **verts** avec le défaut en place. Ce qui le refuse est le **type** :

```text
src/pages/PageTrombinoscope.tsx(340,60): error TS2538: Type 'null' cannot be used as an index type.
```

C'est le §7.35 dans l'autre sens : là où la propriété n'est pas observable, c'est la **structure**
qui la tient — ici le vérificateur de types, et le dire vaut mieux que de laisser croire qu'un test
la prouve.

**Et l'écran gagne un troisième cas de figure éprouvé** : jeton posé → bordure de marque · jeton
`null` → bordure neutre · jeton **inconnu du design system** → bordure neutre. Les trois affichent le
**nom** du cercle, ce que le §10.1 exige. Le premier est le témoin sans lequel un code qui ne
poserait **jamais** de couleur passerait les deux autres.

---

## Et un point de propreté, corrigé avant commit

Ma première version appelait `_professionnel` **quatre fois par ligne**, une par champ. Sans
conséquence mesurable à cent lignes, et sans excuse : une fonction appelée pour son résultat se lit
une fois.

---

# 5. Écart ouvert

## `ECART-060` — des filtres que l'API accepte et que l'écran ne peut pas proposer

Quatre des cinq filtres de `T3` prennent un identifiant, et **aucun endpoint ne sert ces listes**.
Ce n'est pas une contradiction entre documents : c'est l'ordre de livraison, les écrans venant après
les routes. **Échéances : LOT 6 pour les cercles, LOT 9 pour les métiers, clients et DSM.** Le jour où
ces listes existent, l'écran gagne quatre sélecteurs **sans qu'une ligne de l'API ne change**.

---

# 6. Ce que `T10` laisse à la suite

| Point | Où il va |
|---|---|
| **le rendu visuel n'est pas vu** | à faire par Jonathan, recette ci-dessous |
| **`#118` reste OUVERTE** | `US003` porte aussi la carte du profil, que `T11` livre |
| **`ECART-012`** | attend toujours Léa, et il est **maintenant à l'écran** : un `dg` affiche « En intercontrat ». La fiche §8.1 disait que `T10` est l'endroit où le choix ne peut plus attendre |
| **`ECART-060`** | LOT 6 et LOT 9 |
| **la fiche profil à l'écran** | `T11`, avec la route déjà en place |

## La recette, pour voir l'écran

```bash
make up && make migrate && make jeu-de-donnees
make admin-local ADRESSE=<ton adresse>
```

Puis `https://app.onboarding.localhost/entites/BORDEA00/trombinoscope` — **76 profils listables** sur
cette entité, mesuré. La carte se retourne au clic, au **Tab + Entrée**, et au **Tab + Espace**.

> **LE JEU DE DONNÉES NE POSE AUCUN JETON DE COULEUR** — 100 cercles, 0 `color_token` non nul,
> mesuré. Les cartes sont donc bordées de neutre, et c'est **juste** : `T10-8` a rendu ce cas
> fidèle plutôt que mensonger. Pour voir les bordures de marque, il faut poser des jetons dans la
> base ; le faire dans le **générateur** appartiendrait au LOT 6, qui est le lot des cercles.

---

# 7. Chiffres, tous dérivés le 12/09/2026

| Grandeur | Valeur |
|---|---|
| Tests | **1 249** — 913 pytest dont **602 d'intégration**, **336** Vitest (+37) |
| Tests gelés mis à jour **délibérément** | **8** — 7 pytest, 1 contrôle de stack |
| Défauts nommés | **8**, tous chez moi — et le huitième est né en `T4` |
| Contrôles de `profil-check` | **45** (+2) |
| Champs d'une ligne de liste | **12** (+4) |
| Requêtes par page de liste | **3** (+1), et **borné** |
| Endpoints du contrat | **21**, inchangé — `T10` change une charge utile, pas un chemin |
| Cibles du `Makefile` | **86**, inchangé |
| Migrations | **16**, inchangé |

**Aucune migration** : `T10` ne fait que **lire** et **afficher**.
