# Fiche de lot — LOT 5

**Collaborateurs, profils et organisation**
**Ouvert par :** Jonathan, le 24 août 2026 (`DEC-558`)
**Porte de sortie :** `G5`
**Découpage :** douze sous-étapes, **validé le 24 août 2026 avant qu'une ligne ne soit écrite**
**Révisé le 6 septembre 2026 :** **onze**, `T5` et `T6` fusionnées — `DEC-564`, et le motif est au §3
**Avancement :** **`T1` à `T5` et `T7` à `T10` terminées** — la dernière le 12/09/2026. **Deux** restent : `T11` et `T12`

---

**Tous les nombres de cette fiche sont DÉRIVÉS, pas recopiés.** C'est la classe d'erreur la plus
fréquente du projet — `ECART-021`, rejouée une douzaine de fois — et trois fois au LOT 3 c'est le §8
d'une fiche qui a annoncé faux. Chaque grandeur ci-dessous est accompagnée de sa source.

---

# 1. Ce que le lot doit produire

## 1.1 Les huit stories, comptées dans le backlog

```bash
grep -c 'MVP-L05-US' docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md
```

| ID | Priorité | Taille | Résultat attendu |
|---|---|---|---|
| `US001` | `P0` | L | consulter un trombinoscope **paginé** — 25, 50 ou 100 |
| `US002` | `P0` | L | rechercher et filtrer — six axes combinables, **300 ms** |
| `US003` | `P0` | M | une **carte retournable accessible** — clic, toucher, clavier |
| `US004` | `P0` | L | consulter une **fiche profil complète** |
| `US005` | `P0` | L | gérer une **photo facultative avec autorisation** |
| `US006` | `P0` | **XL** | **modifier un profil dans son périmètre** |
| `US007` | `P0` | L | **archiver et restaurer** un profil |
| `US008` | `P1` | M | consulter l'**historique organisationnel** |

**Sept `P0` et une `P1`.** `US006` est la seule `XL` du MVP à ce jour, et c'est cohérent : elle porte
à elle seule les quinze actions du §6.1 de la matrice.

## 1.2 Les **sept** critères de sortie de la roadmap

1. les miniatures sont **inférieures à la cible de 100 Ko** ;
2. **aucune photo non autorisée** n'est publiée ;
3. les permissions suivent **intégralement** la matrice ;
4. les recherches respectent l'objectif de performance **avec 5 000 profils** ;
5. **aucune requête N+1 critique** n'est détectée ;
6. les **affectations structurantes** ne sont jamais écrasées ;
7. Jonathan valide le trombinoscope et les profils.

> **Sept, et le compte est DÉRIVÉ, non supposé.** J'ai d'abord écrit « huit » de tête, par symétrie
> avec les huit stories — puis la commande a dit sept. C'est exactement `ECART-021`, attrapé avant
> d'être écrit :
>
> ```bash
> awk '/^# LOT 5/,/^# LOT 6/' docs/product/ROADMAP_MVP_V1_V2_EXALT.md \
>   | awk '/Critères de sortie/,/^## Dépendances/' | grep -c '^- '
> ```

---

# 2. Ce que le corpus tranche déjà, et qu'il ne faut pas réinventer

| Question | Où c'est tranché |
|---|---|
| qui peut faire quoi sur un profil | **matrice §6.1** — quinze actions × huit rôles — et **§6.2**, huit règles complémentaires |
| ce qu'une photo exige | **cahier §21.2** : « facultative ; autorisation explicite ; retrait possible ; **avatar neutre sinon** » |
| qui gère les médias | **matrice §12.1**, tableau MVP — six rôles, sept actions |
| les tables de photo et de média | **modèle §12.2** `photo_authorization`, **§16.1** `media_asset`, **§16.2** `media_variant`, **§16.3** `media_usage` |
| la pagination | **cahier §18.2** : « 25 par défaut ; options 25, 50 et 100 ; **maximum 100** » |
| hors de son entité principale | **matrice §5.1** — déjà implémenté au LOT 4, et il s'applique ici à chaque route |

## 2.1 Le piège de la matrice §6, mesuré avant de commencer

**`OFFICE` n'a AUCUN droit sur les profils.** Sa colonne du §6.1 est **entièrement à tiret**, et le
§6.2 le dit en clair : « un responsable de bureau n'obtient **aucun** droit général sur les profils du
seul fait de sa responsabilité de bureau ».

> C'est le piège **symétrique** de `T9` du LOT 4, où `ESM` était le rôle qu'on perdait en écrivant
> « administrateur d'entité et super-administrateur ». Ici l'erreur serait d'**ajouter** `OFFICE`
> parce qu'il figure dans les autres tableaux de la matrice. **Chaque tableau a ses propres
> colonnes**, et il faut lire celui de la ressource.

**Et `EMP` a un droit, un seul, qui surprend** : « enregistrer l'autorisation photo — **Soi lors de
l'action** ». Un employé sans aucune responsabilité peut donc autoriser **sa** photo. Le retirer
serait plus restrictif que la matrice, ce que le §7.20 interdit.

---

# 3. Le découpage — **onze** sous-étapes depuis le 06/09/2026

> **`T5` ET `T6` SONT FUSIONNÉES**, arbitrage de Jonathan du 06/09/2026, `DEC-564`. Les deux
> moitiés de `US005` ne tiennent pas debout séparément : on ne peut pas prouver « sans
> autorisation, avatar neutre » sans **servir** quelque chose, servir une photo sans vérifier
> l'autorisation enfreindrait le §12.2, et surtout **le critère « l'originale n'est jamais
> servie » serait parfaitement satisfait par une route qui ne sert RIEN** — §7.0, quatrième
> proposition. Les deux lignes restent au tableau, barrées, parce qu'un découpage validé ne
> s'efface pas : il se révise, et la révision se lit.

**L'ordre suit les dépendances du backlog** : les tables d'abord, la lecture avant l'écriture, les
écrans **après** les routes qu'ils consomment — comme `T11` du LOT 4, qui arrivait après les écrans
employant ses composants.

| | Objet | Story | Critère de sortie |
|---|---|---|---|
| ~~**`T1`**~~ | ~~**Les trois tables de média et d'autorisation de photo**, et le §30.12 reclassé~~ **TERMINÉE le 24/08/2026.** `DEC-559`. **DEUX SECTIONS DU MODÈLE ONT DÛ ÊTRE CONFRONTÉES** : le §16.2 ne donne pas d'`entity_id` à `media_variant`, mais le §25.3 prescrit le couple `(id, entity_id)` pour toute table **locale** — et sans lui la clé serait **simple**, donc une variante pourrait pointer l'actif d'une autre entité. `isolation-check` compte désormais **neuf** clés composites. **`photo_authorization` reste globale**, et la dérivation du contrôle le confirme. **Un déclencheur rend `deleted` terminal** — le §24.3 le dit par son diagramme, et un `CHECK` ne peut pas l'exprimer. **Une seule unicité, dérivée** du §16.2 ; **aucune** sur `photo_authorization`, et un test **fige l'absence** pour que `T6` la traite. **La borne « photo 10 Mo » n'est PAS en base** : une photo est une image, la distinction est un **usage**, et `media_usage` est reportée. **Deux garde-fous du LOT 2 ont fait leur travail** : `noms_de_contraintes_trop_longs` a attrapé un nom de **66 caractères** que PostgreSQL aurait tronqué en silence, et `TABLES_DECLAREES` a échoué sur les trois tables nouvelles — c'est son objet. **729 tests** dont 20 nouveaux, migration **`0014`** rejouable sur base vide avec une signature **identique**. Compte rendu : [`compte-rendu-t1-lot-5.md`](compte-rendu-t1-lot-5.md) | — | ☑ |
| ~~**`T2`**~~ | ~~**Le trombinoscope en lecture** : route paginée 25/50/100~~ **TERMINÉE le 26/08/2026.** `DEC-561`. **LA MATRICE §5 NE DISTINGUE AUCUN RÔLE** : « Trombinoscope » est à « Lecture » pour les **huit** rôles authentifiés, `ANON` seul exclu — une session suffit, et `exiger_un_role_dans_l_entite` **attend toujours** son premier consommateur, contrairement à ce que le rapport de `T1` annonçait. **QUATRE ÉTATS SONT EXCLUS, ET LES DEUX FILTRES SONT NÉCESSAIRES** : le §22.5 étape 5 « masquage du profil » n'est implémenté **nulle part**, donc un partant reste `published` et filtrer la seule visibilité le listerait ; un nouvel arrivant est `active` avec un profil `draft`, donc filtrer le seul état le listerait trop tôt. Un test **fige** les exclusions pour un appelant `SUPER`, que `T8` devra casser. **DEUX ARBITRAGES DE JONATHAN** le 25/08/2026 : liste blanche des trois tailles, et ordre **nom puis prénom** — rendu **total** par la clé primaire, sans quoi la pagination répéterait des lignes. **LE DÉFAUT `T2-3` EST LA LEÇON DE LA SOUS-ÉTAPE** : `Literal[25, 50, 100]` **refuse la chaîne** « 25 », donc la route refusait les trois tailles valides — et **les huit épreuves de refus passaient toutes**. **761 tests** dont 32 nouveaux, **23 contrôles** de stack à travers Caddy. Compte rendu : [`compte-rendu-t2-lot-5.md`](compte-rendu-t2-lot-5.md) | `US001` | ☑ |
| ~~**`T3`**~~ | ~~**Recherche et filtres** — six axes combinables~~ **TERMINÉE le 26/08/2026.** `DEC-562`. **LE CRITÈRE NOMMAIT LA MAUVAISE DURÉE** : le §9.3 donne une **temporisation de saisie** de 300 ms — un délai d'écran, qui appartient à `T10` — et le §25.2 un **budget de réponse de 800 ms au P95**, que reprennent les critères de sortie du lot. `ECART-050`. **CINQ FILTRES ET NON SIX** : l'axe « entité » **est** le `{code}` de la route, y ajouter un `entite=` serait une fuite inter-entités en puissance. Et **cinq filtres tiennent en quatre tables** — `professional_status_assignment` porte `status` **et** `client_id`. **`EXISTS` ET NON JOINTURE** : le §8.2 autorise plusieurs cercles, et une jointure rendrait la personne autant de fois — le `total` serait faux et la pagination répéterait des lignes. La période est `period @> :instant`, **jamais `ends_at IS NULL`**, qui inclurait les affectations **futures**. **LA RECHERCHE IGNORE LES ACCENTS**, par une fonction **`IMMUTABLE`** en `translate` et non l'extension `unaccent`, qui est `STABLE` — un index bâti sur une fonction faussement déclarée immuable se corrompt. Elle s'applique **des deux côtés**. **TREIZE DÉFAUTS, TOUS CHEZ MOI, ET SIX DANS LA MESURE** : mon « P95 » était le **maximum**, mon compteur **fuyait un écouteur**, et j'ai posé des statistiques étendues sur une hypothèse **fausse** avant de les retirer. La vraie cause était les **tuples morts** laissés par le banc d'essai — 467 ms contre 0,5 ms sur la même requête. **P95 mesuré : 1,1 à 2,8 ms**, RAPPORTÉ face au budget de 800 — ce budget est un objectif de **production** ; le test exige, lui, un plafond d'effondrement et la propriété **structurelle** qui le garantit : `Rows Removed by Join Filter` borné par l'effectif de l'entité, jamais par la table. Compte rendu : [`compte-rendu-t3-lot-5.md`](compte-rendu-t3-lot-5.md) | `US002` | ☑ |
| ~~**`T4`**~~ | ~~**La fiche profil** et les règles de visibilité~~ **TERMINÉE le 26/08/2026.** `DEC-563`. **LE CRITÈRE RENVOIE À DES RÈGLES QUE LE CORPUS NE DÉFINIT PAS** : « règles de visibilité » ne paraît que dans les **deux copies du critère de `US004` lui-même**, et le seul « masquer » de la matrice porte sur les **actions**. Le §5 donne « Fiches collaborateur », « Statut mission/intercontrat » et « Client actif » en **Lecture aux huit** rôles. **Aucun champ n'est masqué**, et un test **fige l'absence** — l'appelant n'a ni appartenance, ni responsabilité, ni rôle technique, et voit tout. `ECART-051`. **LA CARDINALITÉ EST PROUVÉE PAR LE SCHÉMA** : quatre contraintes d'**exclusion** rendent métier, statut, client, DSM et cercle principal uniques à un instant donné, si bien que les `LEFT JOIN` ne peuvent pas multiplier — et un test **exige que ces contraintes existent toujours**. **LA PHOTO N'EST PAS DANS LA FICHE** : un champ qui vaudrait toujours `null` laisserait croire que le §12.2 est appliqué. **LE CONTRÔLE RELIE LA FICHE À LA LISTE** — il prend l'identifiant que le trombinoscope rend, puis un profil exclu, et exige le même 404 ; éprouvé, il rend « 200/404 » sans le filtre. **806 tests**, **10 contrôles** de stack, **3 requêtes** par fiche, comptées. **ET LA CI A REVELE UN DEFAUT DE `T3`** : son plafond d'effondrement de 3 000 ms était calibré sur ma machine — l'exécuteur a rendu **3 663 ms**. Le test de recherche n'exige plus **aucune durée** : il exige la **justesse au volume** et rapporte le reste. `T4-1`. Compte rendu : [`compte-rendu-t4-lot-5.md`](compte-rendu-t4-lot-5.md) | `US004` | ☑ |
| ~~**`T5`**~~ | ~~**Les miniatures** : variantes et cible 100 Ko~~ **ET `T6`, FUSIONNÉE. TERMINÉE le 07/09/2026.** `DEC-564`. **LE LOT PASSE À ONZE SOUS-ÉTAPES**, et le motif est mesurable : le critère « l'originale n'est jamais servie » serait **parfaitement satisfait par une route qui ne sert RIEN** — §7.0 quatrième proposition, et c'est le défaut `T2-3` où huit refus restaient verts. On ne peut pas non plus prouver « sans autorisation, avatar neutre » sans servir quelque chose, ni servir une photo sans vérifier l'autorisation sans enfreindre le §12.2. **QUATRE CONDITIONS, CHACUNE AVEC SON REFUS ET SON TÉMOIN** : autorisation **active** (§12.2), média `ready` (§16.1), **même entité** (§25.3), variante `thumbnail` (§16.2). **`withdrawn_at IS NULL` NE SUFFIT PAS SEUL** — une autorisation datée du **futur** a elle aussi un retrait nul, et c'est le seul refus qu'un `WHERE` trop large laisserait passer. **L'ORIGINALE N'EST JAMAIS SERVIE, ET C'EST STRUCTUREL** : la requête ne sélectionne pas `media_asset.object_key` et la structure rendue n'a aucun champ qui puisse le porter — le perdre exigerait de réécrire la requête. `make profil-check` le prouve **sur les OCTETS**, deux contenus distincts déversés dans MinIO : un contrôle « 200 et des octets » passerait si la route servait l'originale. **LA BORNE EST EN BASE, AU SEUL TYPE `thumbnail`** — la porter sur les cinq casserait le LOT 11 — et un test la franchit **à l'octet** : 99 999 passe, 100 000 est refusé. **`T5` NE FABRIQUE AUCUNE MINIATURE** : c'est `MVP-L11-US005`, et aucune bibliothèque de traitement d'image n'est installée. Le **format** reste donc non tranché : `ECART-052`, la fiche §8.2 attribuait à `T5` une décision qui appartient à qui **produit** les variantes. **QUATRE DÉFAUTS, TROIS DANS MES CONTRÔLES** — dont un commentaire affirmant « la cause reste au journal » alors que `gerer_erreur_applicative` ne journalise **rien**, et un décor ancré sur une **date en dur** que les tests injectant leur instant ne pouvaient pas voir. **838 tests** dont 32 nouveaux, **299 Vitest**, `make profil-check` de 10 à **17 contrôles**, migration **`0016`**. Compte rendu : [`compte-rendu-t5-lot-5.md`](compte-rendu-t5-lot-5.md) | `US005` | ☑ |
| ~~**`T6`**~~ | ~~**L'autorisation de photo** : sans elle, avatar neutre~~ **FUSIONNÉE DANS `T5`** le 06/09/2026, arbitrage de Jonathan, `DEC-564`. Ses deux critères — « aucune photo non autorisée publiée » et « le **retrait** effectif » — sont prouvés en `T5` : cinq causes d'avatar neutre, chacune avec son témoin, et l'autorisation **retirée** rend 404 au format du §18.3. **UN POINT RESTE OUVERT, ET IL EST NOMMÉ** : la **lecture** honore le retrait, mais **aucune ROUTE ne permet de retirer** — cela suppose un écran et une écriture, donc `T8` ou le LOT 9. À annoncer à la porte `G5`. | `US005` | ☑ |
| ~~**`T7`**~~ | ~~**L'écriture dans son périmètre** — la matrice §6 exigible~~ **TERMINÉE le 09/09/2026.** `DEC-568`. **LE PÉRIMÈTRE A DÛ ÊTRE ARBITRÉ, PARCE QUE LE CRITÈRE NE LE DONNE PAS** : « un DSM modifie son consultant · refusé sur un autre · `OFFICE` refusé partout » porte entièrement sur **qui** peut écrire, et **serait satisfait par une route qui n'écrirait qu'un champ trivial**. Or le **critère de sortie n°6 du lot** — « les affectations structurantes ne sont jamais écrasées » — n'avait **aucun propriétaire** : `T8` clôt, `T9` lit, `T10` et `T11` sont des écrans, `T12` prouve. §7.39 appliqué au découpage, **seconde fois dans ce lot**. Arbitrage de Jonathan : **les six champs du cahier §10.2**, et présentation courte, fun fact et cercles secondaires **nommés comme reportés**. **DEUX GRILLES, ET UNE SEULE NE SUFFISAIT PAS** : `exiger_un_role_dans_l_entite` — écrite au `T9` du LOT 4 et **sans emploi depuis** — refuse `EMP`, `NEW` et `OFFICE` avant toute transaction ; `resoudre_le_perimetre` applique ensuite le §6.2 **par cible**, sans quoi un DSM serait autorisé sur le consultant d'un autre. **L'UNION PORTE SUR LES COUPLES (RÔLE, PORTÉE)**, et le §23.1 le borne lui-même — conséquence assumée : `BOOST` **et** `ESM` peut changer le DSM, `BOOST` seul non. **UN MEMBRE SECONDAIRE N'OUVRE AUCUN DES SIX CHAMPS**, dérivé de deux sources concordantes, le §6.2 et la **démonstration attendue** de la roadmap là où la fiche est muette. **« JAMAIS ÉCRASÉES » EST UNE PROPRIÉTÉ DU SCHÉMA, PAS UNE PROMESSE** : `period` en bornes `[)` et une exclusion par table, si bien qu'une période **future** fait refuser l'écriture — traduit en `409`. **Statut et client sont UNE période**, liés par une **biconditionnelle** mesurée. **CONCURRENCE OPTIMISTE ancrée sur la RACINE** de l'agrégat (§18.4), et la version ne monte pas quand rien ne change. **LA RÈGLE CSRF EST DÉPLACÉE, JAMAIS RECOPIÉE** — premier emploi sur une route métier, 154 tests d'auth verts. **CINQ DÉFAUTS, DONT DEUX QUE NI `ruff` NI `mypy` N'ONT VUS** : une dépendance irrésoluble sous `from __future__ import annotations` que seul le montage de l'application a dite, et la leçon §7.25 rejouée — un paramètre lié partagé par des colonnes de types différents, **seize tests tombés d'un coup**. **857 tests** dont 19 nouveaux, `make profil-check` de 17 à **26 contrôles** — et **aucune cible nouvelle**, donc rien à ajouter dans `ci.yml`. `ECART-056` et `ECART-057` clos. Compte rendu : [`compte-rendu-t7-lot-5.md`](compte-rendu-t7-lot-5.md) | `US006` | ☑ |
| ~~**`T8`**~~ | ~~**Archivage et restauration**~~ **TERMINÉE le 10/09/2026.** `DEC-569`. **LA MOITIÉ « RÉVOQUE ET CLÔTURE » EXISTAIT DÉJÀ** : le `T9` du LOT 3 l'a livrée en août, et `make recette-modele-check` classe le §30.22 **`ACQUIS`** depuis lors. Mesuré le 10/09/2026, ce qui manquait : la **quatrième** transition du §24.1 — `Archived --> Active`, **zéro** occurrence dans `apps/api/app/` — et **aucune route**, le service n'étant appelé que par ses tests. **LE §6.1 PORTE DEUX GRILLES DE RÔLES, ET RÉUTILISER CELLE DE `T7` AURAIT ÉLARGI UN DROIT** : ses trois lignes d'archivage mettent `DSM` **et** `BOOST` à TIRET, alors que les deux modifient — le §6.2 le redit en mots. **« CONDITIONNEL » N'EST PAS UNE DÉCISION EN SUSPENS** (§7.29, sixième occurrence) : le §18 précise « restauration **fonctionnelle** » et `ARB-DROIT-003` réserve à l'ADM-E et au SUPER les restaurations « techniques, massives ou liées aux imports ». **ARCHIVER UN ACTIF EST UN CHEMIN, PAS UNE TRANSITION** — le §24.1 n'a aucun `Active --> Archived` — et **les deux étapes révoquent**, si bien que la seconde rend zéro : c'est la preuve que la première avait tout pris. **LA RESTAURATION NE ROUVRE RIEN**, arbitrage de Jonathan : rouvrir d'anciennes valeurs serait **décider à nouveau** (§23.4) et fabriquerait une trace d'audit fausse. Elle **NOMME** ce qui manque, par un `bool_or(period @> instant)` dont les trois valeurs distinguent « jamais existé », « a existé et plus maintenant » et « courante ». **LA BASE ARBITRE LES DEUX REFUS** de la restauration, et le `409` **ne nomme pas la cause** — elle porte sur une autre entité (§5.1). **LES DEUX TESTS QUE LA PASSATION ANNONÇAIT À CASSER RESTENT VERTS** : une seconde population servie par une **seconde route** est plus fidèle au §6.1 qu'un assouplissement de la première. **AUCUNE ÉNUMÉRATION DES ARCHIVES N'EST INVENTÉE** — zéro occurrence dans le corpus, et les six axes de filtre du `US002` n'incluent pas l'état d'appartenance : à annoncer à `G5`. **SIX DÉFAUTS, CINQ DANS MES CONTRÔLES** — dont une substitution non vérifiée qui n'a rien fait en silence, une branche neuve qu'aucun test n'atteignait, et un rapport qui nommait une relation **jamais existante**. **888 tests** dont 31 nouveaux, `make profil-check` de 26 à **36** contrôles, **aucune migration** et **aucune cible nouvelle**. `ECART-058` clos. Compte rendu : [`compte-rendu-t8-lot-5.md`](compte-rendu-t8-lot-5.md) | `US007` | ☑ |
| ~~**`T9`**~~ | ~~**L'historique organisationnel**~~ **TERMINÉE le 12/09/2026.** `DEC-570`. **LE CORPUS NE DIT RIEN DES AFFECTATIONS PASSÉES, ET « PERTINENT » NON PLUS** : zéro occurrence de « ancien DSM » ou « missions passées » dans les cinq documents, et le mot du titre de `US008` ne paraît que dans les **deux copies du critère lui-même** — la forme exacte d'`ECART-051`. **LA GRILLE VIENT DONC DE LA LIGNE « AUDIT » DU §5**, seul endroit où la matrice règle la consultation d'un historique, et elle **refuse `EMP` et `NEW`** : savoir qui a managé qui et chez quel client est une information de gestion, non une donnée d'annuaire. Arbitrage de Jonathan. **`OFFICE` N'OBTIENT RIEN**, et deux sources concordantes le disent — **aucune table ne rattache un collaborateur à un bureau**, et le §6.2 écrit qu'un responsable de bureau « n'obtient aucun droit général sur les profils » : `ECART-059`, même forme qu'`ECART-031`. **DEUX LIGNES DE LA MATRICE SE CONTREDISENT, ET LA PLUS ÉTROITE GAGNE** : le §20 réserve « l'historique des rôles » à l'ESM, l'ADM-E et le SUPER, et le §23.2 tranche — l'axe des responsabilités vaut donc `null` pour un DSM. **`null` N'EST PAS `[]`** : le premier dit « hors périmètre », le second « rien à montrer », et les confondre affirmerait faux. **CINQ AXES ET NON QUATRE** : le backlog omet le métier, la roadmap dit « historique des **affectations** », et une omission n'est pas une exclusion. **AUCUNE GRILLE D'ÉTAT**, contrairement à `T7` et `T8` — un profil archivé a justement l'historique le plus intéressant — et un test le prouve **par comparaison** avec `resoudre_le_perimetre`, qui refuse la même cible. **« SANS EXPOSER LES AUDITS TECHNIQUES » EST STRUCTUREL** : aucune requête ne touche `auth_event`, aucune structure rendue ne peut porter une colonne technique, et **deux** contrôles le figent — l'un sur les champs, l'autre sur les **octets servis**. **LE NOMBRE DE REQUÊTES SE COMPTE** : six pour cinq axes, quatre pour trois — un service qui filtrerait après coup rendrait six dans les deux cas. **TROIS DÉFAUTS, TOUS CHEZ MOI** — dont une factorisation qui ne factorisait rien et coûtait cinq exemptions, et des contrôles **dans le mauvais ordre** que la mesure a démasqués : le DSM rendait 404 sur son propre consultant, **et il avait raison**. **912 tests** dont 24 nouveaux, `make profil-check` de 36 à **43** contrôles, **aucune migration** et **aucune cible nouvelle**. Compte rendu : [`compte-rendu-t9-lot-5.md`](compte-rendu-t9-lot-5.md) | `US008` | ☑ |
| ~~**`T10`**~~ | ~~**Le trombinoscope à l'écran** : liste, pagination, **carte retournable**~~ **TERMINÉE le 12/09/2026.** `DEC-571`. **LE PREMIER ÉCRAN MÉTIER DU PROJET.** **LA RÉPONSE AU CRITÈRE EST STRUCTURELLE** : la face de la carte est un **`<button>` natif**, donc clic, toucher et clavier — Entrée **et** Espace — sont acquis sans un seul gestionnaire. **Et le toucher ne peut PAS être éprouvé dans `jsdom`** : un `touchend` n'y produit aucun `click`, c'est le navigateur qui le fait. Ce qui est donc exigé est **la balise**, seule observation qui distingue un livrable tactile d'un `<div>` qui ne l'est pas (§7.35). **LE §10.1 EXIGE UN VERSO PROFESSIONNEL, ET L'API N'EN SERVAIT AUCUN** : la ligne passe de huit à **douze** champs, servis par une **troisième requête** bornée aux lignes rendues — quatre `LEFT JOIN` sur la requête de page les feraient payer sur toute la population **triée avant le `LIMIT`**. **Trois reste BORNÉ**, et quatre tests le comptent. **CINQ TESTS GELÉS SONT TOMBÉS** — huit attendus mis à jour **délibérément**, aucun affaibli par inclusion. **LA COULEUR DU CERCLE N'EST JAMAIS SEULE** (§10.1) : son **nom** est du texte, la couleur ne fait que border, et un jeton inconnu ne donne **aucune** couleur — les cercles sont du LOT 6. **DEUX FILTRES SUR SIX**, et c'est mesuré : quatre prennent un identifiant et **aucun endpoint ne sert ces listes**, `ECART-060`. **« Voir plus » mène à une route RÉELLE**, dont le contenu est `T11` — un lien qui tombe en 404 simule la navigation au lieu de la prouver. **SEPT DÉFAUTS, TOUS CHEZ MOI** — dont un `setState` synchrone dans un effet, deux propriétés CSS que `cadre-check` a nommées, un nom accessible concaténé **sans séparateur** (« Voir plussur Ada Lovelace »), et une affirmation **fausse** de ma part : `queryByText` ne respecte pas `hidden`. **330 Vitest** (+31), `profil-check` à **44** contrôles, **aucune migration** et **aucune cible nouvelle**. **Le rendu visuel n'est PAS vu** : il faut une session, donc un compte, et je n'en crée ni n'en saisis (§7.14) — la recette est au §6 du compte rendu. Compte rendu : [`compte-rendu-t10-lot-5.md`](compte-rendu-t10-lot-5.md) | `US003` | ☑ |
| **`T11`** | **La page de profil à l'écran**, et les composants consolidés | `US003`, `US004` | chaque composant livré est **employé** · contraste mesuré |
| **`T12`** | **Recette, reclassements du §30 et checklist `G5`** | — | les **sept** critères de sortie prouvés |

**Une pull request par sous-étape**, un compte rendu, et les registres tenus **dans la même pull
request** que le travail.

> **`T1` NE CRÉE QUE TROIS TABLES SUR QUATRE, ET C'EST UN ARBITRAGE.** `media_usage` (§16.3) ne sert
> qu'à la médiathèque **V1** — « voir les usages », « détecter les médias inutilisés », matrice §12.2
> — donc la créer maintenant serait une table **sans consommateur**, ce que `T10` du LOT 1 et
> `DEC-537` refusent. Elle est **nommée comme reportée**, pas oubliée.

---

# 4. Ce que ce lot NE fera PAS

**Au-delà de son périmètre :** aucun cercle ni bureau créé ou modifié (LOT 6) · aucun contenu éditorial
(LOT 6) · aucune fiche d'arrivée ni onboarding (LOT 7) · aucun événement (LOT 8) · aucun import CSV
(LOT 9) · aucun export (LOT 11) · aucune médiathèque V1 · **aucune purge définitive**, réservée au
super-administrateur et rattachée au LOT 12.

**Les interdits absolus, qui ne dépendent d'aucun lot :** aucun contournement de l'authentification ·
aucun jeton ni mot de passe en clair · aucun jeton dans `localStorage` · **aucune donnée réelle de
collaborateur, aucune photo réelle** · aucune modification d'une migration déjà appliquée ni des cinq
documents de cadrage · aucune exposition de PostgreSQL, Redis, MinIO ou Mailpit ailleurs que sur
`127.0.0.1` · aucune référence d'image par `latest` seul · ni Kubernetes, ni PWA, ni hors ligne, ni
Entra ID · aucune ligne du prototype historique.

---

# 5. Ce qui est livré et attend son premier consommateur

| Livré | Où, et ce que ce lot doit en faire |
|---|---|
| **`exiger_un_role_dans_l_entite`** | `app/permissions/dependances.py`, LOT 4 `T9`. Il fait **six** des huit vérifications du §2.6 ; les deux qui manquent — « le **périmètre exact de la ressource** » et « les contraintes métier supplémentaires » — ne s'appliquaient pas à un lot en lecture seule. **Elles s'appliquent ici**, et `ECART-046` attend que ce lot prouve le refus **à travers Caddy** |
| **le jeu de 5 000 profils** | `make jeu-de-donnees` — 25 entités, 5 000 profils, LOT 2 `T12`. C'est **exactement** ce que le quatrième critère de sortie réclame |
| **`exiger_un_scope`** | LOT 3 `T9`, toujours sans consommateur. Les comptes de service liront des profils au LOT 9 |
| **le bucket MinIO** | `onboarding-dev-media`, créé par `make up` depuis `DEC-477`. **`T5` en est le premier consommateur**, et il l'a été le 07/09/2026 : `make profil-check` y déverse deux objets de contenus distincts, puis les retire |

---

# 6. Les risques propres à ce lot

| Risque | Ce qui le tient |
|---|---|
| **la matrice §6 est dense** — quinze actions, huit rôles, huit règles complémentaires | `T7` doit en faire un **contrôle** dérivé du document, jamais une liste recopiée (§7.27). Le LOT 4 l'a fait pour trois rôles ; ici il y en a quinze × huit |
| **la performance à 5 000 profils** | le jeu existe. `T3` doit mesurer la **durée**, qui est la grandeur du critère, et **rapporter** le plan — exiger « aucun Seq Scan » exigerait le contraire de la performance sur des tables de cette taille (§7.26) |
| **le N+1** | il se **compte**, il ne se suppose pas. `T3` doit compter les requêtes émises, et confronter ce compte à un attendu |
| **une photo est une donnée personnelle** | aucune photo réelle, jamais. **Tenu en `T5`** : les seuls octets employés sont des marqueurs de test — `MINIATURE-DE-VERIFICATION-mmm…` et `ORIGINAL-QUI-NE-DOIT-JAMAIS-SORTIR-ooo…` — engendrés dans le contrôle, jamais versionnés, et supprimés du bucket à la fin |
| **les affectations structurantes écrasées** | sixième critère de sortie. Le socle du LOT 2 porte des **relations historisées** : une modification **clôture** et ouvre, elle n'écrase pas. `T7` doit l'exiger, et le §24.4 du modèle le dit |

---

# 7. Trois leçons du LOT 4 qui s'appliquent directement

**`§7.29` — cherche la section dédiée avant de décider.** Elle a servi quatre fois au LOT 4, dont deux
fois où un point annoncé « ouvert » était déjà tranché ailleurs. Ici les sections dédiées sont la
matrice **§6** et **§12**, le cahier **§21.2** et **§18.2**, et le modèle **§12.2** et **§16**.

**`§7.35` — quand une propriété n'est observable par aucun contrôle, change le code.** Le LOT 4 l'a
payée sur l'ordre d'une liste de rôles. Ici la même question se posera sur l'ordre du trombinoscope :
un `ORDER BY` sur un seul champ non unique laisse PostgreSQL libre, et la pagination devient
**non déterministe** — deux pages pourraient omettre ou répéter une personne.

**`§7.27` — une liste recopiée vieillit au premier ajout.** Neuf occurrences au LOT 4, dont trois dans
mes propres contrôles et une **dans le manifeste du contrat**. La matrice §6 est le plus gros
gisement de listes du projet.

---

# 8. Ce que le corpus NE tranche PAS — **deux points, et ils sont nommés**

## 8.1 `ECART-012` — « intercontrat » sur une fiche de direction générale

**Ouvert, instruit, et il attend Léa.** `professional_status_assignment` n'offre que **deux** valeurs,
que le modèle validé écrit ; pour une catégorie `dg`, `intercontrat` est la seule possible. Le
trombinoscope l'**afficherait**, et cela serait lu comme une erreur.

**Non bloquant pour le lot**, mais il devient **visible** à `T4` et `T10`. Les deux options sont
chiffrées, et la moins coûteuse ne touche pas le modèle : conditionner l'**affichage** à la catégorie.
**`T4` doit donc rendre le statut d'une façon qui laisse ce choix ouvert**, et ne rien inventer.

## 8.2 ~~Le format et la taille exacte des miniatures~~ — **CLOS en `T5`, et la fiche se trompait de lot**

> **CORRECTION DU 06/09/2026.** Ce paragraphe disait « **`T5` devra donc décider** ». **Cette
> décision n'appartient pas à `T5`** — `ECART-052`, `DEC-564`.

Le constat était **juste et vérifié** : le corpus ne donne ni dimension ni format, et la mesure du
06/09/2026 le confirme — zéro occurrence de `webp`, `avif`, `jpeg` ou `png` dans les cinq documents.
La **conclusion** était fausse.

| Grandeur | Où elle se décide |
|---|---|
| la **taille** | **dans le corpus** : le §25.3 dit « moins de 100 Ko ». Posée en base par la migration `0016`, bornée au **seul** type `thumbnail`, et un test la franchit **à l'octet** |
| le **format** | **au LOT 11**, par `MVP-L11-US005` qui **produit** les variantes. `T5` sélectionne et sert ; elle n'en fabrique aucune, et aucune bibliothèque de traitement d'image n'est installée |

**Une liste blanche `('webp', 'avif')` écrite en `T5` aurait fait échouer le LOT 11** le jour où il
produit du `jpeg`, et le message n'aurait pas dit que la cause est une décision prise trop tôt. Un
format inconnu tombe donc sur `application/octet-stream` : un octet servi vaut mieux qu'une page
cassée.

> **L'apport de cet écart, et il vaut pour la suite du lot :** quand un document t'annonce une
> décision à prendre, pose **deux** questions et non une — *le cahier la porte-t-il déjà ?* (§7.29)
> **et** *à quel lot appartient-elle ?* La seconde se répond en cherchant qui **produit** la donnée,
> jamais qui la **consomme**.

---

# 9. Traçabilité GitHub

À créer **après validation du découpage** — donc maintenant : un epic `MVP-L05`, **huit** issues pour
les huit stories, et le jalon `G5`.

**Et la routine qui ne change pas :** une pull request par sous-étape, `Closes #N` **ne fonctionne pas
depuis `develop`** (§7.19), donc chaque issue est refermée **à la main** avec ses critères cochés et
leurs preuves.
