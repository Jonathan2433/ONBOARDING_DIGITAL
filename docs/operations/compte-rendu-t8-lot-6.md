# Compte rendu — `T8` du LOT 6 : la présentation de l'entité et les liens internes

**Sous-étape :** `T8` · **Story :** `MVP-L06-US005` · **Issue :** `#150` · **Décision :** `DEC-587`
**Réalisée le :** 22 septembre 2026
**Branche :** `t8-presentation-et-liens-internes`, partant de `develop`, jamais empilée

---

# 1. État du lot

**LOT 6 ouvert le 13/09/2026** (`DEC-575`), douze sous-étapes validées le même jour.
**`T1` à `T8` sont faites**, `T9` à `T12` restent.

`T8` livre les liens internes — cinq routes, une migration, une question **bloquante close** —
et elle **n'a écrit aucune ligne** pour la présentation de l'entité, parce que la mesure a
montré qu'elle n'en demandait aucune.

---

# 2. Ce que la sous-étape a produit

```text
GET  /api/v1/entities/{code}/liens            l'accueil : les liens ACTIFS, ordonnés
GET  /api/v1/entities/{code}/liens/gestion    l'éditeur : tous, actifs comme inactifs
POST /api/v1/entities/{code}/liens            créer un lien, EN QUEUE de liste
PUT  /api/v1/entities/{code}/liens/ordre      réordonner : rang = index de la liste
PUT  /api/v1/entities/{code}/liens/{lien}     modifier, ou DÉSACTIVER
```

Plus la migration `0019`, qui pose `ck_internal_link_url_https` — **aucune colonne nouvelle**,
une contrainte de vérification.

---

## 2.1 `QO-120` était bloquante, et le corpus ne donne rien — **la mesure d'abord**

Le modèle §15.3 **et** le cahier §13 écrivent tous deux, mot pour mot, « Les URL sont validées
selon une **liste de protocoles autorisés** ». Mesure du 22/09/2026 sur les cinq documents de
cadrage, confirmant celle du 13/09 :

| Motif cherché | Occurrences |
|---|---:|
| « protocole » | **2** — ce sont ces deux phrases |
| `https?://`, `mailto:`, `javascript:`, `ftp://`, `data:`, `tel:` | **0** |

**Zéro.** Le corpus nomme l'exigence et ne fournit pas la liste.

**Les deux erreurs sont symétriques, et c'est le §7.29.** Ne rien valider enfreint une phrase
écrite deux fois ; poser une liste **fermée** fige une interprétation là où la source ne
tranche pas — la même faute que la liste blanche de scopes du LOT 3, dont le §22 disait
« par exemple ».

**Arbitrage de Jonathan, `DEC-587` : `https` seul, et `http` refusé NOMMÉMENT.** Trois motifs,
dans l'ordre de force :

1. **les trois destinations que le critère nomme sont des SaaS d'entreprise** — Hub, eXalt
   Academy, SharePoint — et aucune ne se sert en clair ;
2. **un lien en clair dégrade la page qui le porte.** Le cahier exige HTTPS pour la plateforme
   (`MVP-L14-US002`, §22.3, « ouverture générale ») : y coudre des liens `http` ferait retomber
   en clair un parcours qui ne l'est nulle part ailleurs ;
3. **`http` mérite son PROPRE refus.** « Protocole inconnu » sur une adresse que l'auteur a
   tapée juste, à un `s` près, est un message qui n'apprend rien. Un contrôle exact vaut mieux
   qu'un contrôle large (§7.25).

**La liste n'est pas fermée pour autant :** l'élargir coûte trois caractères dans
`PROTOCOLES_AUTORISES` **plus** une migration d'une ligne, et le message de refus **énumère**
ce qu'il autorise — il ne peut donc pas vieillir derrière la liste (§7.27). Les schémas
d'application — `ms-teams:`, `onenote:` — n'entrent pas au MVP, et la question le dit.

---

## 2.2 **Une liste de protocoles ne suffit pas**, et c'est le constat le plus utile

C'est le résultat qui contredit la lecture littérale de la phrase du corpus. Mesure du
22/09/2026 sur `urlsplit` :

```text
entrée                          scheme        netloc
'https://hub.exemple.test/'     'https'       'hub.exemple.test'
'https:alert(1)'                'https'       ''            <-- !
'https:/hub.exemple.test'       'https'       ''            <-- !
'https://'                      'https'       ''            <-- !
```

**`https:alert(1)` passe une liste blanche de protocoles.** Une validation qui s'arrêterait au
schéma accepterait donc une chaîne qui n'adresse aucune ressource, et qu'un navigateur traite
comme une référence relative. La validation exige **aussi un hôte**, sous le code
`url_sans_hote` — le cinquième refus, et le seul qu'une lecture littérale aurait omis.

**Deux autres mesures du même jour commandent le code :**

```text
'HTTPS://X'                 -> scheme 'https'       urlsplit MINUSCULISE
'java\nscript:alert(1)'     -> scheme 'javascript'  urlsplit RETIRE \t \r \n
'java\tscript:alert(1)'     -> scheme 'javascript'  idem
```

La première dit qu'une comparaison de schéma doit se faire **après** l'analyse, sans quoi
`HTTPS://` serait refusé. La seconde dit l'inverse pour la même raison : l'analyseur
**normalise** une chaîne que l'auteur n'a pas tapée, et un contrôle qui lirait la chaîne brute
verrait `java\nscript` là où le navigateur verra `javascript`.

D'où **`url_ambigue`**, qui **n'énumère aucun caractère interdit** — recopier la liste interne
de CPython la ferait vieillir à la première version (§7.27) — mais exige que le segment de
protocole **tel qu'il est tapé** soit, à la casse près, exactement celui que l'analyseur a lu.
Toute divergence est refusée sans chercher laquelle. **Cette règle ferme une classe entière
sans la connaître.**

**Les six refus, et aucun n'est décoratif :**

| Code | Cause | Exemple |
|---|---|---|
| `url_illisible` | aucun `:`, donc aucun protocole | `hub.exemple.test`, `//hôte/` |
| `url_ambigue` | le protocole tapé ≠ le protocole lu | `java\nscript:alert(1)` |
| `url_non_chiffree` | exactement `http` | `http://hub.exemple.test/` |
| `url_protocole_refuse` | tout autre protocole | `javascript:`, `data:`, `mailto:` |
| `url_sans_hote` | protocole autorisé, aucun serveur | `https:alert(1)` |
| `type_de_lien_refuse` | hors des quatre types du §15.3 | `INTRANET` |

---

## 2.3 Deux étages, et `T1` avait raison de ne pas poser le second

La règle vit à **deux** endroits, et ce n'est pas une redondance :

| Étage | Ce qu'il apporte |
|---|---|
| `ck_internal_link_url_https`, migration `0019` | **le plancher.** Il rend « aucune URL `javascript:` n'existe en base » **structurel** et non promis (§7.35) : l'y écrire exige de casser une migration, pas d'oublier un appel |
| `valider_une_url`, `app/content/liens.py` | **le refus exact.** Il distingue cinq causes là où la contrainte n'en rend qu'une, et il **exige l'hôte**, que `LIKE 'https://%'` ne sait pas exiger |

**`T1` avait refusé la contrainte, et son argument était juste à sa date** : « inventer la liste
ici la figerait dans le schéma ». Ce qui a changé n'est pas l'argument, c'est que la liste
**n'est plus une invention** — `DEC-587` la tranche. Et la figer coûte exactement ce que coûte
le `contrainte_enumeration` de `page_type`, une migration d'une ligne, qui est précisément le
motif pour lequel ce dépôt préfère une vérification à un type `enum` natif.

**Le plancher couvre ce que le service ne peut pas couvrir**, et trois écrivains futurs sont
déjà nommés au corpus qui n'appellent pas ce module : la reprise relue du prototype
(`MVP-L06-US007`, sous-étape `T11`), les modèles génériques locaux du §19, et les imports du
LOT 9. **Aucun d'eux ne peut plus écrire `javascript:` dans `internal_link`.**

Un test confronte les deux listes. Sans lui, le service accepterait un jour ce que la base
refuse, et l'API rendrait **500** là où elle doit rendre 422.

---

## 2.4 La grille est la **quatrième voisine** du lot, et la première qui concorde

`T6` avait trouvé le §13 divergent du §6.1 **dans les deux sens** ; `T7` avait trouvé la
restauration plus étroite que l'archivage. La confrontation de `T8`, faite avant d'écrire une
ligne :

```text
LECTURE — matrice §5, le seul tableau qui porte les HUIT rôles authentifiés

    « Présentation de l'entité »          ANON —, les huit **Lecture**
    « Liens Hub/Academy/SharePoint »      ANON —, les huit **Lecture**

GESTION — matrice §13 (six colonnes) et §19 (trois)

    §13 « Gérer les cartes Hub/Academy/SharePoint »
                 DSM —  ESM Entité  BOOST —  OFFICE —  ADM-E Entité  SUPER Global
    §13 « Modifier la présentation de l'entité »
                 DSM —  ESM Entité  BOOST —  OFFICE —  ADM-E Entité  SUPER Global
    §19 « Modifier les liens internes »
                        ESM Entité                     ADM-E Entité  SUPER Global
```

**Les trois lignes de gestion donnent le même ensemble**, et le §19 ne contredit rien : son
tableau n'a **que trois colonnes** — ni `DSM`, ni `BOOST`, ni `OFFICE` — ce qui est une
**absence de colonne** et non une exclusion (§7 du `DEC-584`). C'est le §13, qui les porte, qui
les met à tiret.

**Les deux ressources de `T8` sont NOMMÉMENT citées au §5**, et c'est ce qui commande la
lecture : une session établie, rien de plus. Lire à sa place la ligne « Consulter » du §13 —
six colonnes, ni `EMP` ni `NEW` — refuserait la ressource à l'Employé, pour qui ce portail
existe. C'est le piège que `T5` avait déjà nommé.

**Aucune portée locale n'est possible, et c'est structurel** : `internal_link` ne porte ni
`circle_id` ni `office_id`, donc un Booster n'aurait **aucune ressource** sur laquelle borner
son droit. Lui en accorder une exigerait d'inventer un rattachement — exactement le
raisonnement qui a fermé la cellule `DSM` de `ECART-063`. Un test le mesure sur les colonnes
réelles de la table, et non sur cette phrase.

**Et `Entité fonctionnel` du §19 ne mord pas ici.** Sa ligne « Modifier nom d'affichage, ville
et contenus locaux » porte ce qualificatif, mais elle vise `entity.display_name` et
`entity.city`, que `T8` n'écrit pas. Sa ligne des liens internes dit « Entité » sans réserve.

---

## 2.5 La **présentation de l'entité** n'a demandé aucune ligne de code

C'est un résultat, pas un manque. Trois faits concordants :

1. **le cahier la situe** : « accueil d'une entité contenant **la présentation** et les accès au
   Framework », et « page d'accueil dans l'ordre validé : **1. présentation de l'entité** ;
   2. Framework ; 3. arrivées récentes ; 4. prochains événements ; **5. liens internes** ». C'est
   donc une **page de contenu**, du type `HOME` du §15.1 ;
2. **le §13 lui donne une grille identique cellule par cellule** à « Créer un contenu général » ;
3. **`HOME` tombe par soustraction** dans `TYPES_SANS_PORTEE_LOCALE`, donc
   `resoudre_le_perimetre_editorial` le réserve déjà à `ROLES_DE_PORTEE_ENTITE` — `ESM`,
   `ADM-E`, `SUPER`, exactement ce que la ligne du §13 nomme.

`T6` la crée et l'écrit, `T7` la publie. **Deux tests le MESURENT** au lieu que ce paragraphe
ne l'affirme : l'un que les trois rôles obtiennent `MODIFIER` sur une page `HOME` réelle,
l'autre qu'un Booster, un DSM, un responsable de bureau et un Employé ne l'obtiennent pas. Ils
échoueront si un lot ultérieur donne une portée locale à `HOME`, **et c'est leur objet** (§7.32).

---

## 2.6 `entity_setting` nomme aussi « liens internes », et ce n'est pas une seconde citerne

Le modèle §5.3 liste « textes d'accueil ; présentateur ; **liens internes** ; contact RGPD ;
informations juridiques ; options fonctionnelles ; configuration locale de l'onboarding »
parmi les clés d'`entity_setting`.

**Le §15.3 donne une table DÉDIÉE**, avec `label`, `url`, `link_type`, `description`,
`icon_reference`, `display_order`, `active`, et les contraintes que `T1` a posées.
`entity_setting` est un magasin clé/valeur générique — « chaque clé est validée par un schéma
connu ». Y écrire les liens perdrait tout ce que `T1` a posé.

**Le §5.3 énumère des CATÉGORIES de paramètres locaux ; le §15.3 en implémente une.** Mesuré :
`entity_setting` existe depuis la migration `0003` et **aucune ligne de code applicatif ne
l'écrit ni ne la lit** — seuls des tests l'exercent.

---

## 2.7 Le rang n'est **jamais** choisi par l'appelant, et une mesure l'exige

`T1` a posé `uq_internal_link_entity_ordre_non_archive`, unique et partiel sur
`archived_at IS NULL`, en écrivant « même motif que `content_block` ». Mesure du 22/09/2026 sur
la base réelle, deux liens aux rangs 900 et 901 :

```text
un seul UPDATE, échange direct   -> REFUSÉ (uq_internal_link_entity_ordre_non_archive)
deux temps, décalage DÉRIVÉ      -> ACCEPTÉ
```

**Un simple échange de deux liens est refusé par la base.** Une route qui aurait laissé
l'appelant poser son rang aurait rendu la permutation de deux cartes **impossible** — un trou
fonctionnel sur un livrable conforme, et personne ne l'aurait vu avant l'écran de `T10`.

Deux conséquences, et elles tiennent tout le dessin du module :

1. **la création ajoute EN QUEUE**, le rang valant `max + 1` lu dans la même transaction. Aucun
   champ `rang` n'est offert : deux liens de même rang sont **inexprimables** plutôt que refusés
   (§7.35), exactement comme `display_order` vaut l'index de la liste chez `T6` ;
2. **la réécriture d'ordre se fait EN DEUX TEMPS**, avec un décalage **dérivé en SQL**. Voir le
   défaut `T8-1` au §4 : la première version dérivait le décalage du **nombre** de liens, et
   c'était faux.

---

## 2.8 La concurrence optimiste du §18.4 est tenue **deux fois, de deux façons**

| Geste | Ce qui tient le §18.4 |
|---|---|
| `PUT …/liens/{lien}` | la **`version` du lien**, lue `FOR UPDATE`, obligatoire, 409 `version_obsolete` |
| `PUT …/liens/ordre` | l'**exigence d'exhaustivité** : la liste doit nommer exactement une fois chacun des liens non archivés |

**Une collection n'a pas de porteur de version**, et c'est le fond de la seconde ligne. Un lien
créé ou archivé entre la lecture et l'envoi rend la liste **incomplète**, donc 422
`ordre_incomplet`. Fabriquer un jeton sur `entity.version`, qui change pour tout autre chose,
aurait donné un verrou qui se déclenche à tort et ne se déclenche pas à propos — le faux
positif du §7.25.

**La comparaison porte sur les MULTI-ensembles, pas sur les ensembles.** `set(ordre) ==
set(existants)` serait satisfait par une liste qui nomme deux fois le même lien et en omet un
autre : deux rangs seraient alors écrits sur la même ligne, et un lien garderait son rang
décalé. Un test l'exige.

---

## 2.9 `actif` et `archived_at` ne sont **pas** fondus, et aucune route n'archive un lien

Le §15.3 déclare `active` **en plus** des champs communs du §3.1, qui portent déjà
`archived_at`. `T1` a refusé de les confondre : « on DÉSACTIVE un lien pour le retirer de
l'affichage sans perdre sa définition, on l'ARCHIVE pour le sortir du jeu de données courant. »

`T8` en tire deux conséquences :

- **`actif = false` est le seul moyen de retirer un lien de l'accueil**, et c'est le geste que
  le §15.3 prévoit ;
- **aucune route n'archive un lien.** Ni le §13 ni le §19 n'en portent la ligne, et en inventer
  une serait le §6.5.

D'où **deux lectures** : l'accueil ne sert que les actifs — sans quoi le champ `active` serait
vide de sens — et la gestion les sert tous, **sans quoi désactiver serait un aller sans
retour**. Deux audiences, deux routes, **une seule garde par route** : un garde-fou dont le
périmètre dépendrait d'un paramètre de requête est un garde-fou qu'on finit par se tromper à
relire.

---

# 3. Contrôles exécutés

```text
make lint · make format-check · make typecheck            0 échec
make parametres-check      749 requêtes, 49 partages légitimes, 0 anomalie
make sources-check         aucun fichier source ignoré par git
make alembic-check         une seule tête : 0019
make migrations-check      base vide reconstruite, schéma IDENTIQUE, chaîne rejouée
make docs-check            5 empreintes, 6 séquences, totaux dérivés
make cadre-check           25 contrôles, 0 échec
make framework-check       68 contrôles, 0 échec        (61 avant `T8`)
make test-frontend         526 tests Vitest — contracts 223, ui 111, web 192
pytest apps/api/tests/test_liens_internes.py             37 tests, 0 échec
```

**`framework-check` passe de 61 à 68 sans aucune cible `make` nouvelle**, donc **rien à ajouter
dans `ci.yml`** — bénéfice direct du §7.27, et c'est le sixième lot d'affilée où l'extension
d'un vérificateur existant évite de dupliquer décor, connexion et ménage.

---

## 3.1 Le témoin qui rend le critère non trivial

« Présentation, Hub, Academy et SharePoint sont modifiables localement ; **les URL sont
validées** » est **parfaitement tenu par une API qui refuse tout** — c'est le §7.39, et c'est
ce qui a coûté la fusion de `T5` et `T6` au LOT 5.

Le contrôle 62 crée donc, **par l'API et à travers Caddy en HTTPS**, les trois destinations que
le critère **nomme**, puis les relit par la route de l'accueil :

```text
ok   LE TEMOIN : Hub, eXalt Academy et SharePoint crees par l'API
     puis SERVIS par l'accueil, rangs 0-1-2 — ajoutes EN QUEUE, et
     AUCUN champ de rang n'est offert a l'appelant
```

Et chaque refus d'URL est apparié à un témoin qui ne diffère **que par la valeur en cause** :
le `s` de `https`, les deux barres obliques, le protocole. Sans eux, un `valider_une_url` qui
lèverait sur tout laisserait les quinze refus verts — le défaut `T2-3` du LOT 5, où **huit**
épreuves de refus passaient sur une route qui refusait aussi les trois valeurs valides.

---

## 3.2 Le plancher est éprouvé **par une insertion SQL directe**

Le contrôle 64 n'appelle pas l'API : il écrit dans la table, comme le feraient une reprise ou
un import.

```text
ok   la contrainte `ck_internal_link_url_https` refuse un
     `javascript:` insere EN SQL, et laisse passer un `https://` —
     « aucune URL hostile en base » est STRUCTUREL (§7.35, `0019`)
```

Le couple est complet : le témoin `https://` passe par le **même** chemin SQL. Un contrôle qui
n'aurait montré que le refus serait satisfait par une contrainte qui refuserait tout.

---

## 3.3 La campagne de témoins — **23 filtres, et zéro muet**

`PYTHONDONTWRITEBYTECODE=1` (§7.44), vingt-trois filtres retirés un par un.

**Première passe : 16 travaillent, 6 muets.** Et **cinq des six étaient de vrais trous de
couverture**, tous de la même famille — aucun de mes cas ne mettait **deux entités en
présence**, ni ne faisait passer une valeur fautive par l'**écriture** plutôt que par la
fonction de validation appelée seule :

| Filtre muet | Ce que le trou laissait passer |
|---|---|
| lecture : cloisonnement `entity_id` | une entité aurait vu les liens d'une autre |
| création : rang dérivé **par entité** | les rangs de la seconde entité auraient commencé à 3 |
| **modification : validation de l'URL** | un lien créé conforme pouvait être **réécrit** en `javascript:` |
| création : validation du type | un type inconnu aurait rendu **500** au lieu de 422 |
| ordre : cible non archivée | une liste légitime serait devenue « incomplète » |

Le troisième est le plus sérieux : **tous** mes cas d'URL fautive passaient par
`valider_une_url` appelée seule, ou par la création. Le second chemin d'écriture n'était exercé
par personne — le §7.39 dans un autre costume.

**Le sixième n'est pas un trou.** Retirer `FOR UPDATE` ne fait tomber aucun test, et **aucun
test séquentiel ne le pourrait** : un verrou ne se manifeste que lorsque deux transactions se
rencontrent, et son absence produit exactement la même observation que sa présence tant qu'une
seule connexion écrit. **Renforcer le test ne servirait à rien ; ce qui sert est de le DIRE**
(§7.42). Un test exige donc la seule chose observable — que la clause reste écrite — et son
docstring dit ce qu'il ne prouve pas.

**Seconde passe, les cinq trous comblés : 23 sur 23 travaillent, 0 muet.** Deuxième campagne du
lot à finir ainsi, après `T7`.

---

# 4. Défauts trouvés — **un seul**, et c'est un test neuf qui l'a trouvé

## `T8-1` — le décalage de la réécriture d'ordre était dérivé du **nombre** de liens

**Symptôme.** Le test « réordonner ignore les liens archivés » — écrit pour combler un trou que
la campagne venait de nommer — a échoué sur
`duplicate key value violates unique constraint "uq_internal_link_entity_ordre_non_archive"`.

**Diagnostic avant correction (§7.18),** par une sonde qui énumère les cas :

```text
vivants  archivés  décalage = n      décalage = max + 1
[0,1,2]  []        [3,4,5]  ok       [3,4,5]  ok
[0,2]    [1]       [2,4]    COLLISION : 2 est encore pris
[0,3]    [1,2]     [2,5]    ok       [4,7]  ok
```

**La cause.** `len(ordre)` n'est un décalage sûr que si les rangs vivants sont `0..n-1` **sans
trou** — ce que l'archivage d'un lien détruit, son rang restant pris. J'avais **mesuré**
`max + 1` dans ma sonde préalable, puis écrit `len(ordre)` dans le module « pour faire plus
simple ». Une valeur que je n'avais pas mesurée, dans le calcul que la mesure venait de
justifier.

**Ce qui le rend pire qu'un échec franc : il est NON DÉTERMINISTE.** La troisième ligne du
tableau passe. Selon quels rangs ont été archivés, le défaut se manifeste ou non — exactement
la forme du défaut `T6-4`, où un `.pyc` périmé rendait la campagne instable.

**Correction.** Le décalage est dérivé **dans la requête** — `SELECT max(display_order) + 1`
en sous-requête — et non passé en paramètre : c'est la seule forme où l'appelant ne peut pas se
tromper (§7.35). `max + 1` est toujours sûr, et le module écrit pourquoi : les rangs décalés
valent tous plus que le maximum vivant, donc plus que n'importe quel rang encore en place ; et
`max >= n - 1` pour n rangs distincts et positifs, donc `max + 1 >= n`, donc au-dessus de tous
les rangs finaux.

**La campagne porte désormais une variante qui remet `count(*)` à la place de `max + 1`**, et
elle fait tomber un test. Le défaut ne peut plus revenir en silence.

---

## Un défaut qui n'en est pas un : le test de `T1` que `T8` a rendu faux

`test_un_lien_a_URL_ou_LIBELLE_vide_est_refuse[url]` attendait
`ck_internal_link_url_non_vide`. La migration `0019` a posé une contrainte **plus forte**, et
les deux sont désormais **emboîtées** : une URL blanche viole les deux, puisqu'elle ne peut pas
commencer par `https://`. PostgreSQL en nomme une seule, **et ce n'est pas à nous de choisir
laquelle** — l'ordre d'évaluation n'est pas garanti.

L'attendu est donc **corrigé, pas affaibli** (§7.20, §7.21) : un test qui accepterait « l'une ou
l'autre » ne dirait plus rien du jour où aucune ne mordrait. Et **`url_non_vide` est conservée
bien qu'elle ne soit plus atteignable seule** : elle le redeviendrait si la liste de protocoles
s'élargissait à un schéma sans `//`. La retirer aujourd'hui serait retirer un plancher pour la
seule raison qu'un mur plus haut le cache.

C'est le §7.21 à la lettre — *un contrôle juste hier peut être faux aujourd'hui, et c'est toi
qui l'as rendu faux*.

---

# 5. Écarts et questions

## `QO-120` — **close**, et elle était bloquante

`DEC-587` : `https` seul, `http` refusé nommément. Voir §2.1 et §2.2. La question portait trois
points, et les trois sont tranchés : la liste elle-même ; `http` **non** toléré ; les schémas
d'application **hors** MVP.

## `QO-123` — **ouverte** : quel vocabulaire pour `icon_reference` ?

Le §15.3 nomme le champ et **ne dit rien de son contenu** — aucune bibliothèque d'icônes n'est
citée dans les cinq documents de cadrage, et le design system de `T10` du LOT 1 n'en pose
aucune : il porte des jetons de couleur, des boutons, des badges et des cartes.

**C'est exactement la classe de `QO-121`** : un champ que le modèle nomme et dont le corpus ne
donne pas le vocabulaire. Le champ est donc servi comme une **donnée opaque**, et ce qui reste
à trancher est au registre. **Non bloquante pour `T8` ni `T9` ; bloquante pour `T10`**, l'écran
d'édition, qui doit proposer un choix — et pour la reprise relue de `T11`, qui devra en poser
une par lien.

## `ECART-015` — ce que `T8` en fait

« Le prototype ne fournit ni descriptions de cercles ni **liens internes** », échéance LOT 6.
`T8` livre la **mécanique** ; le **contenu** relève de la reprise relue, `MVP-L06-US007`,
sous-étape `T11`, et des 29 éléments `CONT-001` à `CONT-029` au statut « à relire ». L'écart
reste ouvert, et il se refermera là.

---

# 6. Ce que `T8` ne fait pas

- **aucun écran.** Les écrans de lecture sont `T9`, ceux d'édition `T10`. Le contrat TypeScript
  ne porte donc que la **lecture** — c'est le partage que le lot suit depuis `T2`, et `T6` comme
  `T7` n'avaient rien ajouté au contrat ;
- **aucun archivage de lien.** Ni le §13 ni le §19 n'en portent la ligne ;
- **aucune vérification de l'existence de la cible.** Ce module valide une **adresse** ; il
  n'ouvre aucune connexion, ne résout aucun nom, ne suit aucune redirection. Le faire serait un
  appel sortant depuis une requête d'écriture, donc un vecteur de saturation — et le §7.33 a
  mesuré ce que coûte une attente réseau sur un chemin de requête ;
- **aucune écriture de `entity_setting`.** Voir §2.6 ;
- **aucun champ de la table `entity`.** Le §19 « Modifier nom d'affichage, ville » vise
  `display_name` et `city`, qui relèvent de la configuration d'entité et non de ce critère.

---

# 7. Ce que `T8` laisse

| Pour qui | Quoi |
|---|---|
| **`T9`** — les écrans de lecture | `GET …/liens` et son validateur TypeScript. La page d'accueil du cahier §26 place les liens en **cinquième** position, après la présentation, le Framework, les arrivées récentes et les événements — dont deux appartiennent à d'autres lots |
| **`T10`** — les écrans d'édition | les quatre routes d'écriture, `rolesGestionDesLiensInternes` et `protocolesDeLienAutorises` au manifeste. **`QO-123` devient bloquante ici** : un formulaire doit proposer un choix d'icône. **Et le §7.43 s'applique** — un aller-retour RÉEL avant de déclarer le client terminé, deux défauts étant tombés ainsi en `T11` du LOT 5 |
| **`T11`** — la reprise relue | `ck_internal_link_url_https` s'applique à elle **aussi**, et c'est voulu : une reprise qui insérerait par SQL est refusée comme le reste. Les liens du prototype devront donc être en `https`, ou l'écart devra être instruit |
| **au LOT 9** | les imports écriront peut-être des liens : ils passent par la même contrainte, et doivent appeler `valider_une_url` pour obtenir un refus **nommé** plutôt qu'un 500 |

**Et un point de vigilance pour qui touchera à `PROTOCOLES_AUTORISES` :** la liste vit à
**trois** endroits qui doivent bouger ensemble — la constante Python, le motif de la migration
`0019`, et `protocolesDeLienAutorises` au manifeste. Deux tests les confrontent ; le troisième
lien est le manifeste, lu par TypeScript **et** par Python. **Élargir la liste sans migrer
ferait rendre 500 à l'API** sur une adresse que le service accepte.
