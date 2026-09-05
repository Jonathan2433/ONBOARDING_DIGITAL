# Compte rendu — LOT 5, sous-étape `T3`

**Objet :** recherche et filtres du trombinoscope — story `MVP-L05-US002`, issue #117
**Réalisé le :** 26 août 2026
**Décisions :** `DEC-562`
**Écarts :** `ECART-050` ouvert et clos

---

## 1. Le critère nommait la mauvaise durée, et il fallait chercher les deux

La fiche annonce « **300 ms** · performance mesurée sur 5 000 profils ». Le corpus porte **deux**
durées pour la recherche, et ce ne sont pas les mêmes :

| Source | Texte | Ce que c'est |
|---|---|---|
| **§9.3 étape 2** | « saisie avec recherche déclenchée à chaque frappe et **temporisation** d'environ **300 ms** » | un délai avant de **partir** — un comportement d'**écran** |
| **§25.2, au P95** | « Recherche trombinoscope \| moins de **800 ms** » | un budget de **réponse** — une exigence d'**API** |

Les critères de sortie du LOT 5 reprennent le second : « recherche sous **800 ms** au P95 ». Et le
backlog `US002` confirme le premier : « la recherche **démarre** après environ 300 ms ».

**Et il a fallu une seconde fois la même leçon pour savoir quoi en faire.** Mon premier test comparait
une horloge de poste de développement à ce budget de **production**. Ce sont encore deux grandeurs
différentes : le §25.2 se mesure sous charge réelle, pas dans une suite qui vient d'engendrer et
d'annuler plusieurs jeux de 28 000 lignes. **Mesuré** : le même code rend **2 ms** isolément et
**1 400 ms** en fin de suite complète.

**C'est le §7.0 sixième proposition.** Deux nombres dans la même unité, sur le même sujet, qui ne
mesurent pas la même chose — et le plus visible n'est pas celui du critère : le 300 ms est dans le
bloc « Inclus » du §LOT 5, le 800 ms trente pages plus loin.

**L'impact n'est pas nul, et c'est ce qui rend l'écart insidieux.** 300 est plus strict que 800 :
mesurer contre 300 serait passé. Mais le critère du cahier n'aurait jamais été vérifié **en tant que
tel**, et surtout la **temporisation de saisie** — celle qui évite d'interroger l'API à chaque frappe
— serait restée **sans porteur**, `T3` la croyant faite. Elle est rattachée à **`T10`**. `ECART-050`.

---

## 2. Six axes au cahier, cinq filtres dans l'API — et le sixième est la route

Le §9.3 étape 3 nomme « entité, métier, cercle, DSM, client ou statut ». Le trombinoscope est
**per-entité** : le §8.1 y fait atterrir depuis la page nationale, et `DEC-545` a mis le code dans
l'adresse.

> **L'axe « entité » EST le `{code}` de la route.** Ajouter un `entite=` sur une adresse déjà bornée
> par `{code}` serait redondant au mieux, et une **fuite inter-entités** au pire — ce que le §25.3
> existe pour empêcher.

**Et cinq filtres tiennent en quatre tables**, mesuré sur le schéma réel :
`professional_status_assignment` porte `status` **et** `client_id`. Le client actif n'est pas une
relation séparée, c'est une **colonne du statut**.

---

## 3. `EXISTS` et non jointure, et une personne à deux cercles le prouve

Le §8.2 autorise **un cercle principal et plusieurs secondaires**. Une jointure rendrait la personne
autant de fois qu'elle a de cercles : **le `total` serait faux et la pagination répéterait des
lignes**.

`EXISTS` dit exactement ce que le filtre veut dire — « au moins une affectation correspond » — et ne
multiplie rien. Le décor porte donc une personne à **deux** cercles : sans elle, une jointure fautive
donnerait **la même observation** qu'un `EXISTS` correct.

**Et la période est `period @> :instant`, jamais `ends_at IS NULL`.** Une affectation **future** a
elle aussi `ends_at` nul — la leçon est écrite dans `organization/services.py`, et le §24.12 l'exige.
Le décor porte `passee` (close) **et** `future`, plus **un témoin dans l'autre sens** : à un instant
postérieur, `future` correspond. Sans ce témoin, un filtre qui ne rendrait **jamais** rien passerait.

---

## 4. La recherche : deux arbitrages, et une fonction plutôt qu'une extension

Le §26.1 écrit « normalisation et index de recherche sur **prénom et nom** », et la recherche
**tolérante** n'y est qu'un « pourra ». Deux points restaient donc ouverts, tranchés le 26/08/2026 :

| Question | Arbitrage |
|---|---|
| « elodie » doit-il trouver « Élodie » ? | **Oui**, les accents sont ignorés |
| chercher aussi l'e-mail ou le nom d'usage ? | **Non — prénom et nom seulement.** Un test **fige l'absence** |

### `translate` et non l'extension `unaccent`

`unaccent()` est déclarée **`STABLE`**, pas `IMMUTABLE` : son résultat dépend d'un dictionnaire
remplaçable. L'usage répandu consiste à l'envelopper dans une fonction qu'on déclare `IMMUTABLE`
**en le sachant faux** — et un index bâti sur ce mensonge se corrompt le jour où le dictionnaire
change.

`translate()` est **réellement** immuable : sa table est écrite dans la migration `0015`, et elle
n'exige **aucune extension**, ce qui évite de rouvrir `QO-112`. Le prix est nommé : la table est une
**liste**, donc elle vieillit si une lettre manque — elle est éprouvée caractère par caractère.

**Et la migration porte son propre garde-fou**, qui a servi immédiatement : la table doit avoir
exactement autant de remplacements que d'accents, un décalage étant **silencieux**.

### La normalisation s'applique DES DEUX CÔTÉS

Une seule fonction SQL, sur la colonne **et** sur le terme. Deux normalisations — l'une en Python,
l'autre en SQL — divergeraient au premier caractère oublié et la recherche rendrait silencieusement
moins de résultats. **Éprouvé** : en retirant la normalisation du seul terme, le contrôle de stack
rend **2 échecs** — « zzélodie » et « ZZELODIE » ne trouvent plus rien, quand « zzelodie » marche
toujours. C'est la paire qui discrimine.

---

## 5. « Aucun N+1, compté et non supposé » — le mot est *compté*

Un compteur écoute le pilote et relève les requêtes **réellement envoyées**. Une relation chargée
paresseusement, un accès à un attribut différé : rien de cela ne se voit dans la requête qu'on a
écrite.

| Ce qui est exigé | Mesure |
|---|---|
| taille 25, 50, 100 | **2 requêtes** dans les trois cas — le comptage et la page |
| six axes actifs à la fois | **2 requêtes** — ils tiennent dans une seule clause |
| **le compteur voit-il quelque chose ?** | témoin : 5 `SELECT 1` → **5 vues**. Sans lui, un compteur aveugle rendrait 0 et « 0 ≠ 2 » échouerait bruyamment, mais un compteur qui rendrait toujours 2 passerait |

---

## 6. Treize défauts, tous dans mon travail — et six dans la mesure elle-même

| | |
|---|---|
| `T3-1` | **la table d'accents que j'ai écrite à la main** avait 54 sources pour 55 cibles, et mappait `Ò` sur le **chiffre zéro**. Attrapée par le garde-fou que je venais d'écrire dans la migration ; la table est désormais **engendrée** (§6.4) |
| `T3-2` | **un paramètre lié partagé par deux colonnes de types différents** — `code` est `varchar`, `display_name` est `text`. Quatrième occurrence de la classe §7.25, et le message ne nomme ni la table ni la colonne |
| `T3-3` | j'ai écrit `"secondaire"` là où l'énumération dit **`secondary`** — un littéral de mémoire au lieu d'une dérivation (§7.27) |
| **`T3-4`** | **mon « P95 » était le MAXIMUM.** Avec 20 échantillons, `int(20 × 0.95)` vaut **19**, l'indice du plus grand. Une seule pointe — 1 289 ms sur des mesures à 2 ms — faisait échouer le test |
| **`T3-5`** | **mon compteur fuyait un écouteur sur le moteur partagé.** `with Compteur().brancher(cx)` : Python évalue `brancher(cx)` — qui attachait l'écouteur — **puis** appelle `__enter__`, qui remettait le moteur à `None`. `__exit__` ne retirait donc rien |
| `T3-6` | l'entité mesurée était tirée par `LIMIT 1` **sans `ORDER BY`** : deux exécutions mesuraient deux entités de tailles différentes et rapportaient des durées incomparables **sur le même code** |
| `T3-7` | **mon contrôle de stack comparait l'ordre ICU de PostgreSQL au tri par OCTETS de Python.** « zzélodie » passe après « zzvisible » en octets, avant en français : le contrôle échouait sur un livrable conforme dès que le décor a porté un accent |
| **`T3-8`** | **j'ai posé des statistiques étendues sur une hypothèse que je n'avais pas vérifiée**, puis constaté qu'avec et sans, l'estimation et les durées étaient **identiques**. Le changement a été **retiré** : garder un correctif dont le motif est faux laisse croire que la cause est traitée |
| **`T3-9`** | **mon `VACUUM` ne nettoyait rien** : il tournait alors que la transaction de la fixture `cx` était **déjà ouverte**, et son instantané empêche toute récupération. Le test passait seul et échouait dans la suite complète |
| **`T3-10`** | **j'ai comparé une horloge de poste de développement à un objectif de PRODUCTION.** Le §25.2 vise 800 ms au P95 **sous charge réelle** ; mon test l'exigeait sur un poste de travail. Il **rapporte** désormais le P95 et **exige** les deux choses qu'un test peut prouver : pas d'effondrement, et un plan qui ne parcourt pas `person` |
| `T3-11` | mon terme accentué n'était **pas percent-encodé** dans l'URL — `urllib` lève, un navigateur encode de lui-même, si bien que le contrôle n'éprouvait pas le décodage côté API |
| `T3-12` | une variable de boucle nommée `valeur` **masquait la fonction `valeur()`** du module — Python fixe la portée à la compilation, et l'échec surgissait **cent lignes avant** mon code |
| **`T3-13`** | **j'ai conclu à un plan fragile en production, et c'était faux.** La CTE `MATERIALIZED` posée pour le corriger **n'a rien corrigé** — 45 879 lignes rejetées avec elle — et la mesure a montré que `ANALYZE` **ne publie rien d'exploitable sur des lignes non validées** : le planificateur croit les tables vides. La CTE a été **retirée**, et la propriété structurelle est **rapportée** au lieu d'être exigée |

**Six d'entre eux — `T3-4` à `T3-6`, `T3-8` à `T3-10` — portent sur la MESURE et non sur le
livrable**, et il a fallu **quatre** diagnostics successifs pour arriver à la cause, dont **deux
étaient faux**.

### La chronologie, parce que c'est elle qui instruit

| Hypothèse | Ce que la mesure a dit |
|---|---|
| « la fonction SQL n'est pas *inlinée* » | **réfutée** : `fonction SQL`, `expression en clair` et `lower()` seul rendent **0,6 ms** tous les trois |
| « mon compteur fuit un écouteur » | **vraie, mais pas la cause** : la fuite existait et est corrigée (`T3-5`) ; la lenteur est revenue sans elle |
| « le planificateur sous-estime des colonnes corrélées » | **réfutée par l'expérience faite pour la confirmer.** J'avais posé des `CREATE STATISTICS` sur les trois colonnes ; **avec et sans, l'estimation restait `rows=1` et les durées étaient identiques**. Les statistiques ont été **retirées** — garder un changement dont le motif est faux serait pire que le défaut |
| **les tuples MORTS laissés par le harnais** | **confirmée** : trois tours consécutifs, même réglage, même volume → **467, 490 et 539 ms** côté serveur ; puis **0,5 ms** une fois la base nettoyée |

Chaque test de ce fichier engendre 28 000 lignes dans une transaction **annulée**. Les lignes
annulées restent physiquement en table jusqu'au passage d'`autovacuum` : après quelques exécutions,
`person` porte des dizaines de milliers de tuples morts que tout parcours d'index doit enjamber —
`Buffers: shared hit=372 681` dans le plan lent, contre 326 dans le plan sain.

**Le test retire donc ce débris avant de mesurer**, par un `VACUUM (ANALYZE)` sur une connexion
séparée en autovalidation. Le critère du §25.2 porte sur l'API **en service**, pas sur une base
saturée par son propre banc d'essai.

**Et le premier nettoyage ne nettoyait rien — `T3-9`.** Le test employait la fixture `cx`, dont la
transaction est **déjà ouverte** quand le corps s'exécute : son instantané empêche `VACUUM` de
récupérer quoi que ce soit. Le test passait **seul** et échouait dans la **suite complète**, la
différence étant exactement le débris des tests précédents. Il ouvre désormais sa propre connexion,
**après** le nettoyage.

### Et la dernière hypothèse était fausse aussi — `T3-13`

Une fois le débris nettoyé, le test passait — **sauf dans `make check`**, où il rendait encore
`Rows Removed by Join Filter: 46 297` pour une entité de 210, et **508 ms**. J'en ai conclu que le
plan était **fragile en production**, et j'ai posé une CTE `MATERIALIZED` pour borner le travail à
l'entité.

**Deux choses ont démenti cette conclusion :**

1. **la CTE n'a rien corrigé** — avec elle, le plan dégradé rejetait toujours **45 879** lignes ;
2. **et la mesure a nommé la vraie cause** :

```text
apres VACUUM (ANALYZE) sur base validee      reltuples(entity_membership) = 0
apres 5 155 insertions NON validees
  puis ANALYZE dans la transaction           reltuples(entity_membership) = 0
```

**`ANALYZE` ne publie pas de statistiques exploitables pour des lignes que la transaction n'a pas
validées.** Le planificateur croit les tables **vides**, estime `rows=1` partout, et choisit des
plans qu'il ne choisirait jamais en service. La dégradation est donc **construite par le banc
d'essai**, et rien ne prouve qu'elle se produise en production.

> **Et cela dément aussi un commentaire hérité du LOT 2**, que j'avais recopié sans le vérifier :
> « sans `ANALYZE`, PostgreSQL raisonne sur des tables qu'il croit vides ». **Il les croit vides
> quand même.** L'appel est conservé — il ne coûte rien et redeviendra utile sur des données
> validées — mais **aucune conclusion sur le plan ne peut être tirée de ce banc d'essai**.

**La CTE a donc été retirée**, comme les statistiques étendues avant elle. Garder un correctif dont
le motif est faux **et** l'effet nul laisserait croire qu'une cause est traitée.

**Et la propriété structurelle est désormais RAPPORTÉE, non exigée.** L'exiger ici ferait échouer un
livrable conforme, puisque le planificateur est aveugle par construction — et un contrôle qui refuse
du code correct apprend à passer outre (§7.25). Elle reste dans la sortie, avec la mention de ce
qu'elle vaut ici.

> **La leçon, sans jargon :** un test de performance mesure **le système, son harnais, et l'état
> physique de la base**. Quand les trois se confondent, on attribue au produit ce qui appartient au
> banc d'essai. Et **une hypothèse ne se confirme pas en appliquant son remède** : elle se confirme
> en mesurant **avec et sans**. Mes statistiques étendues « marchaient » au premier essai — le second
> réglage, identique, était tout aussi lent.

**Et trois règles apprises de la base**, ce qui est la bonne façon de les apprendre : une
`dsm_assignment` exige une **responsabilité DSM active** dans l'entité ; `assigned_by_person_id` est
`NOT NULL` ; et `membership_type` vaut `secondary`, pas « secondaire ».

---

## 7. Mesures

| Grandeur | Valeur, dérivée |
|---|---|
| pytest | **795**, dont **495** d'intégration — **30 nouveaux** dans `test_recherche_et_filtres.py`, **4** dans `test_trombinoscope.py` |
| Vitest | **265** — 47 `contracts` (**+4**), 97 `ui`, 121 `web` |
| `make trombinoscope-check` | **0** — **38 contrôles** (23 en `T2`), à travers Caddy en HTTPS |
| le même, normalisation d'un seul côté | **1** — 2 échecs, « zzélodie » et « ZZELODIE » |
| **performance, P95 sur 40 mesures** | **1,1 à 2,8 ms**, RAPPORTÉ face au budget de **800 ms** — sur l'entité la plus peuplée (**210 appartenances**) d'un jeu de **28 011 lignes** |
| **plafond d'effondrement EXIGÉ** | **3 000 ms**, large et assumé, comme celui de `test_jeu_de_recette.py` au LOT 2 |
| **propriété structurelle RAPPORTÉE** | `Rows Removed by Join Filter` = **0** pour 210 appartenances — rapportée et non exigée : le planificateur est aveugle sur des lignes non validées |
| suite API complète | **717 tests**, verte **deux fois de suite** |
| plan de la recherche | index sur `entity_membership.entity_id`, puis filtre sur 76 lignes — **0,151 ms** côté serveur, **326 tampons** |
| le même, base saturée de tuples morts | **467 à 539 ms**, **372 681 tampons** — artefact du banc d'essai, retiré par un `VACUUM` avant mesure |
| statistiques sur lignes non validées | `reltuples` = **0** pour 5 155 lignes réelles, **après** `ANALYZE` — le planificateur est aveugle ici, par construction |
| `make migrations-check` | **0** — la chaîne rejouée sur base **vide** rend une signature **identique** |
| `make check` | **0** |

---

## 8. Ce que `T3` laisse à la suite

- **`T10`** porte la **temporisation de 300 ms** du §9.3, que `T3` ne fait pas — et `ECART-050`
  existe pour qu'on ne la croie pas faite ;
- **la ligne rendue ne porte toujours ni photo ni informations professionnelles affichées.** Les cinq
  relations servent à **filtrer**, pas à enrichir : le verso du §10.1 est l'affaire de `T10`, avec ce
  que `T4` aura défini ;
- **l'index `ix_person_recherche_nom` est posé et son usage n'est pas exigé.** Sur ce volume
  PostgreSQL choisit un filtre après jointure, et exiger l'index exigerait le contraire de la
  performance (§7.20). Il sert le §25.1, « augmentation possible sans refonte » ;
- **`fn_normaliser_pour_recherche` est disponible pour `T4` et au-delà** — c'est la seule
  normalisation de recherche du projet, et elle doit le rester.
