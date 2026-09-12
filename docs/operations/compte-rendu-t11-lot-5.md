# Compte rendu — `T11` du LOT 5 : la page de profil à l'écran

**Stories :** `MVP-L05-US004` — *Consulter une fiche profil complète*, `P0`, taille **L**, issue `#119`
· `MVP-L05-US008` — *Consulter l'historique organisationnel pertinent*, `P1`, issue `#123`
**Décision :** `DEC-572`
**Date :** 12 septembre 2026

> **CE COMPTE RENDU COUVRE LA PREMIÈRE DES DEUX PULL REQUESTS.** `DEC-572` découpe `T11` en deux :
> ce qui se **lit** — la fiche et l'historique — puis ce qui **écrit** — archiver et restaurer. La
> seconde partie complétera ce document, et la sous-étape n'est pas terminée avant.

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 5**, ouvert le 24/08/2026, **onze** sous-étapes |
| Faites | `T1` à `T5`, `T7` à `T10` · **`T11` en cours**, première partie |
| Périmètre de cette partie | la fiche profil en lecture, et l'historique organisationnel |
| Périmètre de la seconde | archiver et restaurer, les deux actions du §24.1 |
| Hors périmètre, **nommé** | **modifier** un profil (`US006`, `T7`) : son API est complète, elle reste **sans écran** |
| Issues `#119` et `#123` | **restent ouvertes** jusqu'à la fin de `T11` |

---

# 2. Le critère écrit dans la fiche était DÉJÀ satisfait

La fiche du lot donne à `T11` : « chaque composant livré est **employé** · contraste mesuré ».
Mesure sur `develop`, **avant** qu'une ligne de `T11` ne soit écrite :

```text
make cadre-check   ok  les 6 composants exportes sont TESTES et EMPLOYES :
                       Alerte, Badge, Bouton, Carte, CarteRetournable, Notification
prefers-reduced-motion : 7 occurrences dans 3 feuilles   (l'alternative de `US003`)
```

**Un critère qu'une sous-étape vide satisferait ne borne rien.** C'est le §7.39, **troisième fois
dans ce lot** — `T5` et `T6` ont été fusionnées pour la même raison, et le critère de `T7` portait
entièrement sur *qui* écrit.

Le périmètre vient donc du **libellé** de la fiche — « la page de profil à l'écran » — et du critère
du backlog `MVP-L05-US004`. Arbitrage de Jonathan du 12/09/2026 : `DEC-572`, et **trois API sans
écran** entrent dans `T11` plutôt que de rester invisibles à la porte `G5`.

## 2.1 « Contraste mesuré » a produit un vrai constat

Le design system mesurait ses couples **sur `fond` seulement** — huit couples, quatre par thème. Or
`fondDoux` **est une surface** : la page de statut l'emploie depuis `T5`, les blocs du cadre depuis
le LOT 4, l'en-tête de la fiche profil depuis `T11`. Du texte y a toujours été posé, **sans qu'aucun
couple ne soit mesuré**.

| | sur `fond` | sur `fondDoux` |
|---|---:|---:|
| clair / encre | 17,40 | **15,83** |
| clair / encre douce | 7,46 | **6,78** |
| sombre / encre | 16,12 | **13,55** |
| sombre / encre douce | 6,91 | **5,81** |

Les seize passent AA — le plus serré est **5,81** pour 4,50 exigé — et c'est **le contrôle** qui
manquait, pas les couleurs. §7.31 : exact pour la surface qu'il regardait, aveugle à l'autre.

---

# 3. Ce que la première partie a produit

## 3.1 `null` n'est pas `[]`, et l'écran ne les confond pas

`T9` a construit cette distinction en base, dans le service et dans la route : `[]` dit « rien à
montrer », `null` dit « hors de ton périmètre ». Un validateur qui absorberait l'un dans l'autre
« pour simplifier l'écran » ferait croire à un DSM que son consultant **n'a jamais porté de
responsabilité** — une affirmation fausse.

Le contrat la porte donc, et l'écran rend **trois** états distincts par axe : des périodes · « Aucune
période enregistrée » · « Hors de votre périmètre ». Deux tests côte à côte, ne différant que par la
valeur en cause, le prouvent — le second est celui sans lequel le premier ne prouverait rien.

## 3.2 Les deux appels partent ensemble, et leurs refus sont indépendants

La fiche relève du §5 « Fiches collaborateur », en Lecture pour les **huit** rôles authentifiés.
L'historique relève de la ligne « **Audit** » du même §5, qui **refuse `EMP` et `NEW`**.

**Un employé voit donc la fiche et se voit refuser l'historique, et c'est l'état normal.** Les
enchaîner n'afficherait rien du tout dans ce cas ; un test l'exige, avec une fiche à 200 et un
historique à 403.

## 3.3 L'entité vient du cadre, pas de l'API

Le §10.2 liste « entité » parmi les champs du profil, et la route ne la sert pas : elle est dans
l'**adresse**, et `useEntiteConsultee` l'a déjà résolue. L'ajouter à la charge utile ferait servir
deux fois la même donnée, dont une copie pourrait vieillir.

## 3.4 Les dates sont formatées SANS `Date`

L'API sert de l'ISO 8601 en **UTC**. `new Date('2026-01-01T00:00:00Z').getMonth()` rend **11**,
décembre, dans tout fuseau à l'est de Greenwich : une période close le 1er janvier deviendrait close
en décembre, **et le défaut ne se verrait qu'à Paris** — jamais sur un exécuteur en UTC, ce qui est
le §7.16.

Les segments sont donc lus dans la **chaîne**. Cela évite aussi `toLocaleDateString`, qui varie avec
l'ICU de la machine : un test qui en dépendrait mesurerait la machine.

## 3.5 Aucun champ n'est masqué, et l'écran ne le laisse pas croire

`ECART-051` avait établi que « règles de visibilité » ne paraît que dans les **deux copies du critère
de `US004` lui-même**, et que le §5 donne la fiche en Lecture aux huit rôles. L'écran affiche donc
tout, et « Non renseigné » dit ce qui est vrai — **la donnée manque**, jamais « vous n'y avez pas
droit ».

## 3.6 Une source unique pour ce que deux écrans présentent

`STATUTS` et les couleurs de cercle vivaient dans `PageTrombinoscope`, où ils n'avaient **un** seul
consommateur. La fiche est le second. Les importer d'une page à l'autre ferait dépendre un écran d'un
autre ; les recopier serait pire, §7.27. Ils sont dans `apps/web/src/affichage.ts`, et **les deux
valeurs de statut sont dérivées du contrat**, jamais réécrites.

---

# 4. Contrôles exécutés

```text
make lint                  code=0
make typecheck             code=0
make format-check          code=0
make sources-check         code=0
make docs-check            code=0
make audit                 code=0
make icloud-verify         code=0
pytest -m "not integration" code=0 — 311 passed, 602 deselected
make test-frontend         code=0 — 111 contracts · 111 ui · 156 web

make code-check            code=0
make cadre-check           code=0 — 25 controles, 0 echec
make ecrans-check          code=0 —  8 controles, 0 echec
make web-check             code=0
make trombinoscope-check   code=0 — 38 controles, 0 echec
make profil-check          code=0 — 45 controles, 0 echec
```

> **LA SUITE D'INTÉGRATION N'A PAS ÉTÉ REJOUÉE LOCALEMENT, ET IL FAUT LE DIRE.** La base de
> développement porte le **jeu de démonstration** — 25 entités, 5 000 profils — et 72 tests
> d'intégration comptent des lignes **en absolu** : c'est le défaut `T10-7`, et la remise à zéro
> détruirait la démonstration que Jonathan a sous la main. `T11` ne touche **aucun** fichier Python
> exercé par `pytest` ; les deux scripts modifiés sont des vérificateurs de stack, qui tournent sur
> l'hôte. **La porte d'intégration continue tranche, sur une base propre.**

---

# 5. Défauts trouvés — **cinq, tous dans mon propre travail**

## `T11-1` — Le frontend servi était périmé, et TROIS contrôles d'écran sont passés dessus

`make cadre-check`, `make ecrans-check` et `make web-check` sont sortis en **0** alors que le
conteneur `web` ne portait **aucun** fichier de `T11`. Le sondage qui l'a dit :

```text
/src/pages/PageProfil.tsx          200  text/html         <- le repli SPA : ABSENT
/src/api/profil.ts                 200  text/html         <- ABSENT
/src/affichage.ts                  200  text/html         <- ABSENT
/src/pages/PageProfilAVenir.tsx    200  text/javascript   <- SUPPRIME, et pourtant servi
```

Le code est **cuit dans l'image** ; j'avais lancé `make code-refresh` **avant** d'écrire ces
fichiers, pour restaurer un témoin.

> **LE `Makefile` DOCUMENTE EXACTEMENT CE PIÈGE**, dans le commentaire de `code-refresh` : « le
> frontend servi est resté celui du LOT 1 pendant **TOUT le LOT 3** […] `make ecrans-check` passait
> quand même, parce qu'il vérifiait que les huit chemins rendent `text/html` avec le point de
> montage — ce que le repli SPA fait pour **n'importe quel** chemin ».
>
> `T3` du LOT 4 avait corrigé la **cible**. Personne n'avait posé le **contrôle**. Un piège documenté
> n'est pas un piège désarmé — §12 de la passation, et je viens de le rejouer.

**Le remède est un contrôle, pas une promesse de vigilance.** `make ecrans-check` gagne un huitième
contrôle : les **30** modules d'écran, dérivés du disque, doivent être servis en **JavaScript**, et
un module inexistant doit retomber sur le repli. **Témoin exécuté** — un fichier posé sur le disque
et absent du conteneur :

```text
ECHEC  1 module(s) sur 31 NON servi(s) — le conteneur `web` porte un code plus ancien que le depot.
       /src/temoin-de-peremption.ts -> 'text/html'
       Remede : `make code-refresh`, qui reconstruit AUSSI `web`.
```

**Et il dit où il s'arrête** : il ne vaut que du serveur de développement, l'artefact bâti servant
`/assets/…` et non `/src/…`. Il **identifie la cible** avant de conclure, plutôt que de la supposer —
§7.21, le contrôle de page de `T5` du LOT 1 avait payé exactement cette erreur.

**Les trois contrôles ont été rejoués sur le conteneur rafraîchi**, et seuls ces résultats-là sont au
§4.

## `T11-2` — Mon contrôle de page servie ne pouvait pas échouer

J'avais ajouté à `profil-check` : « la page du profil est servie par la coquille », sur
l'identifiant réel rendu par la liste, avec `text/html` **et** le point de montage exigés. Mesure :

```text
/entites/BORDEA00/trombinoscope/<uuid reel>   200 text/html racine=1
/entites/BORDEA00/trombinoscope/bidon         200 text/html racine=1
/chemin/qui/n/existe/pas/du/tout              200 text/html racine=1
```

**L'échec aurait produit la même observation que le succès** — §7.0, quatrième proposition — et le
repli lui-même est déjà prouvé ailleurs. Les trois réactions possibles étaient : le supprimer,
l'affaiblir, le faire dire le vrai (§7.20). Ici **rien n'était exigible sans moteur de rendu** : il
est supprimé, et le motif est écrit dans le fichier pour qu'on ne le repose pas.

Ce que le rendu de cette page a de prouvé est ailleurs — **156 tests `jsdom`**. Une preuve dans un
vrai navigateur demande Playwright, que le cahier §17.1 nomme et que le **LOT 12** possède ;
`cadre-check` porte déjà la même réserve.

## `T11-3` — `--profil-cercle` employée sans être définie, rejeu de `T10-2`

`cadre-check` l'a nommée. J'avais écrit `var(--profil-cercle, var(--trait))` en croyant que la valeur
de repli suffisait : **elle ne suffit pas**, et le contrôle a raison — un repli **cache** l'absence au
lieu de la signaler, si bien qu'une propriété jamais posée résoudrait au défaut du navigateur sans
que rien n'échoue. Elle est déclarée dans la règle, comme `--carte-cercle` l'est depuis `T10`.

## `T11-4` — Une propriété nommée `role` sur un composant, que `jsx-a11y` a refusée

`<Cercle role="Principal" />` : la règle `aria-role` s'en est plainte, et **elle a raison**. Le jour
où ce composant diffuserait ses propriétés sur un nœud DOM, `role="Principal"` deviendrait un rôle
ARIA invalide. Renommée `nature`. Désactiver la règle aurait été le mauvais remède — c'est le
garde-fou qui a motivé `DEC-451`.

## `T11-5` — Un attendu faux, puis une redondance d'écran, sur le même test

Deux tours sur le témoin central, et **les deux verdicts étaient différents** :

| Tour | Message | Qui avait tort |
|---|---|---|
| 1 | « Found multiple elements: Dominique Lesmanager » | **mon attendu** — il paraît deux fois, dans la fiche et dans l'axe DSM, et c'est juste |
| 2 | « expected 2 but got 3 » sur le métier | **mon écran** — l'en-tête, le bloc, et l'historique |

Le second était une vraie redondance de conception : l'en-tête portait déjà le métier et le statut
sous le nom, et le bloc les redisait trois lignes plus bas. **Le bloc ne les porte plus** ; il porte
l'entité, le client, le DSM et la date d'arrivée.

> *Un test qui échoue ne dit pas lequel des deux a tort.* La première fois c'était l'attendu, la
> seconde le livrable — et corriger l'attendu au second tour aurait figé la redondance.

---

# 6. Ce que la première partie laisse à la seconde

| Point | Où il va |
|---|---|
| **archiver et restaurer** | seconde pull request de `T11` — confirmation, jeton anti-CSRF, traitement des refus |
| **modifier un profil** | **hors périmètre**, `US006` · l'API de `T7` reste sans écran, à annoncer à `G5` |
| **le rendu visuel** | non vu par moi (§7.14) · la recette est ci-dessous |
| **`ECART-012`** | attend toujours Léa, et la fiche l'affiche désormais aussi |

## La recette, pour voir l'écran

Ouvrir le trombinoscope d'une entité, puis **« Voir plus »** sur une carte. La page rend l'identité,
les informations professionnelles, les cercles, les responsabilités, la présentation, et
l'historique en cinq axes.

**Un compte `SUPER` voit les cinq axes.** Pour voir la moitié qui compte — « Hors de votre
périmètre » — il faut un compte dont le rôle ne donne pas l'axe des responsabilités, ce que
`make profil-check` éprouve déjà côté API avec un DSM.
