# Compte rendu — LOT 3, sous-étape `T8`

**Limitation de débit**
**Stories :** `MVP-L03-US001` et `MVP-L03-US003`
**Traçabilité GitHub :** **`T8` n'a AUCUNE issue propre, et ce n'est pas un oubli.** Le jalon `G3`
porte huit issues, `#63` à `#70`, une par story — pas une par sous-étape. Les deux stories de `T8`
ont été refermées à `T3` (`#63`) et à `T5` (`#65`), chacune sur son propre critère. Ce que `T8`
achève est le **critère de sortie du lot** : « les limites de débit produisent les résultats
attendus », suivi au §9 de la fiche. Un commentaire est déposé sur `#63` et `#65` pour que la trace
existe là où un relecteur la cherchera — **sans les réouvrir** : leurs critères étaient satisfaits
**Réalisée le :** 21 août 2026
**Décisions produites :** `DEC-533`, `DEC-534`
**Écart ouvert et clos :** `ECART-034`
**Migration produite :** **aucune**

---

## 1. Le premier travail a été de découvrir que la fiche affirmait faux

Le §8 de la fiche du lot annonçait : « **Valeurs des limites de débit** — le cahier exige une
limitation, **sans donner de seuil** ». J'allais donc instruire une décision.

**Le cahier §20.2 s'intitule « Seuils initiaux » et en énumère six**, dont trois portent sur
l'authentification. Et **`.env.example` en porte cinq depuis le LOT 0**, chacune avec son commentaire
`[source] cahier 20.2`, introduites par le commit `802fe69`.

**Suivre la fiche aurait produit un seuil inventé qui contredit le cahier**, lequel « prévaut sur
tout ». C'est `ECART-034`, et c'est l'avertissement du §9.0 pris à l'envers : le document
n'annonçait pas à tort que le travail était fait, il annonçait à tort qu'une **décision restait à
prendre**.

**La parade est mécanique, et elle est posée** : deux tests **relisent le cahier** et exigent que
chaque constante corresponde à la phrase qui la produit, **verbe inclus**. Une constante changée à
la main, ou un cahier modifié, font désormais échouer la suite au lieu de passer en silence.

---

## 2. Deux verbes, et la distinction commande tout le comportement

```text
« 10 demandes de magic link par adresse et par heure : LIMITATION »
« 5 echecs administrateur en 15 minutes : ALERTE »
« 50 demandes depuis une meme origine en une heure : ALERTE »
```

**Une seule des trois est une « limitation ».** Ce que `T8` livre s'aligne sur les verbes :

| | Ce qui est fait |
|---|---|
| **limitation** | la demande de lien par adresse — refus effectif, **429** |
| **détection** | l'origine, et les échecs administrateur — journalisée avec un motif nommé |
| **pas ici** | l'**alerte** elle-même, qui exige `operational_alert` du modèle §21.2 — **LOT 10** |

**Transformer une « alerte » en « limitation » aurait été inventer une règle, et la conséquence
serait concrète** : cinquante requêtes depuis une même origine bloqueraient **tout un bureau derrière
un partage d'adresse**. Le cahier a choisi ce verbe ; ce n'est pas à une sous-étape de le changer.

**La lecture de « 50 demandes depuis une même origine » est DÉCLARÉE.** Cette ligne n'écrit pas « de
magic link » quand la précédente le fait ; la lecture retenue est donc la plus large — toute demande
d'authentification — et c'est aussi la plus utile : un attaquant qui balaie mille adresses
différentes ne fait avancer **aucun** compteur par adresse, et seule cette dimension le voit.

---

## 3. Le piège principal : la limite pouvait devenir l'oracle que `T3` a fermé

**Si le compteur ne portait que sur les adresses connues** — en comptant par exemple les lignes de
`magic_link_request`, qui n'existent que pour un profil actif et autorisé — alors une adresse inconnue
ne serait **jamais** limitée. **Le 429 dirait « ce compte existe ».**

Le compteur porte donc sur **l'adresse normalisée, avant toute lecture de la base**. La onzième
demande rend 429 pour **n'importe quelle** adresse.

**Et ce n'est pas une lecture personnelle du cahier** : le §20.1 énumère « limitation des requêtes »
et « réponses génériques pour les demandes de magic link » **dans la même liste**.

**Les deux refus sont donc comparés corps ET en-têtes**, exactement comme `T3` comparait ses 202.

**Et cela réduit le résiduel que `T3` avait nommé.** Le chemin d'une adresse connue fait davantage de
requêtes SQL que celui d'une adresse inconnue ; l'écart, de l'ordre de la milliseconde, n'est
exploitable que **statistiquement**, donc par répétition. Dix demandes par heure la rendent
impraticable. La docstring de `routes.py` annonçait `T8` comme la sous-étape qui le ferait.

**Deux corollaires mesurés :**

- **la casse ne contourne pas.** L'adresse est normalisée par la **même fonction** que le service :
  sans cela, `Jean@x.fr` et `jean@x.fr` auraient deux compteurs, et une adresse a autant de graphies
  que de lettres ;
- **ni l'adresse ni l'IP n'entrent en clair dans Redis.** Une adresse dans une clé serait une donnée
  personnelle dans un magasin **sans politique de conservation**, lisible par `redis-cli`. Les deux
  dimensions emploient un **HMAC** — nécessaire là où un SHA-256 simple se renverse par énumération,
  32 bits pour une IPv4, une adresse étant devinable.

---

## 4. Le trou du verrou de `T5`, et pourquoi le combler sans rien révéler

`failed_login_count` vit sur `user_account` : **une adresse sans compte n'a aucun compteur**, donc
peut être sollicitée sans fin, et un attaquant qui balaie mille adresses ne fait avancer aucun verrou.

Le compteur d'échecs par **adresse** double celui par **compte**, avec les **mêmes deux nombres** —
« 5 échecs administrateur en 15 minutes », la phrase que `T5` employait déjà.

**Et il s'applique aux DEUX cas, ce qui est la condition pour ne rien révéler.** S'il ne portait que
sur les adresses sans compte, la sixième tentative rendrait **429** pour une adresse inconnue et
**400** pour une connue : le **code HTTP deviendrait l'oracle** que `T5` avait fermé.

**Il est effacé sur succès, et ce n'est pas un confort.** Le §7 de la fiche nomme le risque « le
verrouillage administrateur bloque Jonathan lui-même » ; un compteur qui survivrait à une connexion
réussie le réintroduirait quinze minutes durant. Réussir exige le mot de passe : effacer ne donne
rien à un attaquant.

---

## 5. Trois choix techniques dont l'inverse casse quelque chose

**`INCR` et `EXPIRE … NX` dans une seule transaction** — cinquième occurrence du compare-et-pose
après `T4`, `T5`, `T6` et `T7`. Deux défauts distincts sont évités, et **chacun bloque une adresse
pour toujours** :

| Forme naïve | Conséquence |
|---|---|
| `INCR` puis `EXPIRE` **inconditionnel** | la fenêtre est repoussée à **chaque** demande. Une requête par minute maintient la clé vivante indéfiniment, et l'adresse d'un collaborateur légitime reste bloquée |
| `INCR` puis `EXPIRE` **hors transaction** | si le processus meurt entre les deux, la clé survit **sans délai**. Même conséquence, et rien ne le dit |

**Redis injoignable → 503, refus.** Le premier principe du §20.1 est « refus par défaut » : laisser
passer ferait d'une panne de Redis le moyen de **désactiver la protection**. Le coût est assumé et
déjà rapporté — `/health/ready` rend 503 avec le motif `redis indisponible` depuis `T3` du LOT 1.

**La fenêtre est fixe, et le résiduel est nommé** : elle laisse passer jusqu'à **deux fois** le
plafond à cheval sur une frontière. Le §20.2 écrit « par heure », ce qu'elle satisfait littéralement,
et une fenêtre glissante exigerait de conserver l'horodatage de **chaque** demande — donc davantage de
données sur une adresse.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **613 tests, 0 échec** — 585 avant `T8`, dont **363 d'intégration** |
| zéro résidu mesuré | `person` 0, `entity` 0, `user_account` 0, `auth_event` 0 |
| `make check` · `make audit` | **0** · **0** |
| **`make debit-check`** | **0 — 12 contrôles**, à travers Caddy en HTTPS |
| `magic-link-check` · `admin-check` | **0 — 15** · **0 — 10** |
| `sessions-check` · `csrf-check` | **0 — 13** · **0 — 10** |
| 13 autres contrôles | tous à **0** |

**Ce que `make debit-check` prouve :**

```text
TEMOIN — les 10 premieres demandes passent (202)
adresse CONNUE : 429, reprise dans 3600 s
adresse INCONNUE : 429 — l'oracle de `T3` reste ferme
les deux refus sont IDENTIQUES : corps et en-tetes
la casse ne contourne pas la limite (429)
TEMOIN — 51 demandes depuis la meme origine, AUCUNE refusee
5 echecs puis 429, adresse connue ET inconnue — meme code, donc aucun oracle
TEMOIN — un succes efface le compteur (200 puis 400, non 429)
2 cles examinees, toutes en empreinte HMAC — ni adresse ni IP en clair
2 cles ont un delai, et il ne recule pas (900 -> 900 s)
89 evenements, tous avec `request_origin_hash` en empreinte — jamais une IP brute
journal : 2/2 motifs presents, aucune adresse ni empreinte
```

**Le témoin négatif a été exécuté** : les deux appels au limiteur retirés du routeur, **8 des 28
tests de `test_debit.py` échouent**. Sans cette mesure, je n'aurais pas trouvé le défaut `T8-1`.

---

## 7. Défauts, dont trois dans mes propres contrôles

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T8-1` | **Mon test d'égalité PASSAIT avec la limitation retirée.** Il comparait deux signatures sans exiger qu'elles soient des 429 — et **deux réponses 202 sont identiques elles aussi**. §7.0, proposition 4 : l'échec produisait la même observation que le succès | **le témoin négatif**, en passant là où il devait échouer |
| `T8-2` | `verifier-debit.py` levait `StopIteration` au lieu de rapporter, quand aucune clé n'existait — **les trois contrôles suivants n'étaient jamais exécutés**. Une trace Python n'est pas un diagnostic | première exécution réelle |
| `T8-3` | Mon témoin « un succès efface le compteur » échouait : le contrôle précédent avait **verrouillé le compte** par le mécanisme de `T5`, si bien que la connexion légitime rendait 400. **Le témoin n'exerçait pas ce qu'il croyait** | première exécution réelle |
| `T8-4` | Le contrôle de verrouillage de `make admin-check` **passait pour la mauvaise raison** : il n'exigeait que « pas 200 », et un 429 le satisfaisait en annonçant « verrou déclenché » | après correction de la cause `T8-5` |
| `T8-5` | `ruff --fix` a retiré des imports momentanément inutilisés pendant la rédaction du fichier de tests. **Troisième occurrence — `T6`, `T7`, `T8`** | `ruff check` |
| `T8-6` | **Deux tests de concurrence intermittents**, `T4` et `T6` : la barrière ouvrait son horloge avant que la connexion de B ne soit établie. **2 échecs sur 8** exécutions complètes, jamais en isolement. Voir §7 bis | l'état que le test affiche, après trois cycles |
| `T8-7` | **Ma fixture `autouse` a BLOQUÉ l'intégration continue** : elle tentait une connexion Redis deux fois par test, et `socket_connect_timeout` ne borne **rien** — redis-py 8 reprend **dix fois** par défaut. Voir §7 quater | la tâche « qualité » restée en cours **plus de quarante minutes** sur l'étape des tests unitaires |

**Et un test plus trois contrôles antérieurs sont devenus faux, tous légitimement :**

| Ce qui a échoué | Cause |
|---|---|
| `test_les_CINQ_causes_de_refus_rendent_la_MEME_reponse` | il produit **six** échecs sur une adresse pour atteindre l'état « verrouillé ». La sixième requête est désormais 429 |
| `make admin-check`, 3 contrôles | même cause — il pousse délibérément un compte jusqu'au verrouillage |
| `make csrf-check`, 2 contrôles | il fait une dizaine de demandes sur la **même** adresse ; au-delà de dix, aucun lien n'est émis |
| `make magic-link-check` | **pas `T8` : moi.** Mon diagnostic de résidu avait supprimé `allowed_email_domain`. `make domaines-provision` le rétablit |

> **Ce que `T8` ajoute au §7.21, et c'est la variante que `T7` avait déjà entrevue :** *quand une
> sous-étape ajoute une condition à une opération existante, les contrôles qui exerçaient cette
> opération deviennent faux — et si la condition vit dans **Redis**, elle **survit d'un contrôle au
> suivant**, là où un nettoyage SQL repart d'un état connu.* « Un état connu » n'est plus seulement
> une table vide : c'est une table vide **et** un compteur remis à zéro.

**La parade est structurelle et non une liste :** une fixture `autouse` dans `conftest.py` purge les
compteurs avant **et** après chaque test, et un module partagé — `infra/scripts/debit_partage.py` —
sert les trois vérificateurs. Corriger les deux fichiers fautifs aurait produit une **liste implicite
des fichiers à corriger**, qui vieillit au premier test ajouté : c'est le §7.27, quatrième occurrence.

---

## 7 bis. Deux tests de concurrence intermittents — diagnostiqués, puis corrigés

**C'est le travail le plus utile de la sous-étape, et il ne figurait pas au périmètre.**

Deux tests de concurrence — celui de `T4` sur la consommation, puis celui de `T6` sur le
rafraîchissement — ont échoué **par intermittence** pendant `T8`, jamais en isolement, toujours en
suite complète. **Trois cycles perdus avant de les faire parler**, ce qui est exactement le §7.18.

**La cause est établie, et elle est lisible dans l'état que le test affiche :**

```text
AssertionError: B n'a pas ete bloquee ; etat observe :
  [(75972, [], 'ROLLBACK'), (75801, [], 'ROLLBACK'), …,
   (76003, [], 'INSERT INTO auth_event (event_type, occurred_at, p'), …]
```

**Le backend de B n'est PAS dans la liste.** Ce n'est donc pas le verrou qui manquait : c'est **la
connexion de B qui n'était pas encore ouverte**. La barrière démarrait son horloge de dix secondes à
`fil.start()`, et sous la charge d'une suite complète l'ouverture d'une connexion PostgreSQL neuve
consommait ce budget.

**Même famille que le défaut `T4-4`**, où les deux délais se chevauchaient — et la même leçon : *un
contrôle intermittent coûte plus cher qu'un contrôle faux*, parce qu'on apprend à le relancer.

**La correction ne touche pas les délais**, ce qui aurait été inventer un nombre. B pose un signal
`threading.Event` **après** l'ouverture de sa connexion et le réglage de son `lock_timeout`,
**avant** son instruction bloquante ; la barrière n'ouvre son horloge qu'après ce signal. Le temps
d'ouverture sort donc du budget **par construction**, et non par élargissement.

Deux détails qui comptent : le signal est **aussi posé sur exception**, sans quoi la barrière
attendrait un signal qui ne viendrait jamais ; et l'échec du signal a **son propre message**, qui dit
que la cause est la connexion et non l'absence de verrou.

**Les trois tests de concurrence du lot reçoivent la même forme** — `T4`, `T5`, `T6` — parce que le
mécanisme est identique dans les trois, et qu'en corriger un seul aurait laissé les deux autres
échouer plus tard sans qu'on sache pourquoi.

| Mesure | Résultat |
|---|---|
| avant correction, suite complète | **2 échecs sur 8** exécutions, sur **deux tests différents** |
| en isolement | 3 sur 3, et 58 sur 58 sur son seul fichier — donc invisible hors suite |
| **après correction** | **5 exécutions complètes consécutives, 613 sur 613, résidu nul** |

**Et un second garde-fou, sur la CASCADE.** Chacun de ces échecs en produisait **huit autres** dans
`test_personnes.py` et `test_roles_et_perimetres.py`, qui comptent des lignes sans filtre : le décor
restait en base. Un nettoyage en `finally` ne suffit pas — si B tient encore un verrou de ligne, le
`DELETE` **attend**, et sans borne il suspend la suite ou laisse tout derrière lui. Le nettoyage porte
donc un `lock_timeout` borné et **imprime un diagnostic** si le fil B est encore vivant. **Un échec
ne peut plus en devenir neuf.**

## 7 ter. Un point de méthode

Dix tests sans rapport ont échoué sur un résidu d'une personne en base. J'ai **mesuré avant
d'attribuer** — purge, exécution isolée, réexécution complète — et ce résidu-là venait d'un état
intermédiaire de ma propre session, non du livrable. Attribuer à `T8` aurait coûté une correction
inutile ; c'est le §7.22, seconde leçon.

**Et une hypothèse que j'ai formée puis RÉFUTÉE, plutôt que corrigée d'office.** J'ai soupçonné ma
fixture `autouse` d'épuiser les descripteurs de fichier : 613 clients Redis non refermés. Mesure
faite avant d'agir — 50 clients ouvrent bien 50 descripteurs, **le ramasse-miettes les reprend
tous**, et la limite du processus est de **1 048 576**. L'hypothèse ne tient pas, et « corriger »
sur cette base aurait ajouté du code pour rien. C'est le §7.18 dans l'autre sens : diagnostiquer
avant de corriger vaut aussi quand le diagnostic **innocente**.

**Un constat réel produit par cette mesure, et il n'est pas de `T8` seul** : `debit.py` comme
`idempotence.py` construisent un `redis.Redis` — donc un pool de connexions — **à chaque appel**, sur
le chemin d'une requête. Ce n'est ni une fuite ni la cause du test intermittent, mais c'est une
connexion TCP neuve là où un pool partagé suffirait. Le patron vient de `T7` ; le changer relève
d'une sous-étape qui touche les deux, pas de celle-ci. **Signalé, non corrigé.**

> **ET MA RÉFUTATION ÉTAIT JUSTE SUR LE MAUVAIS CRITÈRE.** J'avais bien soupçonné cette fixture ;
> j'ai mesuré les **descripteurs de fichier**, et conclu qu'elle ne coûtait rien. La grandeur qui
> comptait était le **temps** — 4,06 s par tentative quand Redis est absent — et elle a bloqué
> l'intégration continue quelques minutes plus tard. Voir §7 quater, défaut `T8-7`. *Réfuter une
> hypothèse exige de mesurer la grandeur qu'elle prédit, pas une grandeur voisine.*

---

## 7 quater. `T8-7` — un délai qui ne bornait rien, et une CI bloquée

**Le défaut le plus coûteux de la sous-étape, et il est entièrement de mon fait.**

La fixture `autouse` qui purge les compteurs ouvrait un client Redis **avant et après chaque test**,
en s'appuyant sur `socket_connect_timeout=1` pour borner l'attente. **Ce délai ne bornait rien.**

| Mesure | Valeur |
|---|---|
| reprises appliquées par redis-py 8.0.1, **par défaut** | **10** |
| coût d'**une** tentative sur un port fermé | **4,06 s** |
| la même, reprise bornée à zéro | **0,003 s** |
| `port_ouvert` sur un port fermé, pour comparaison | **0,001 s** |

La tâche **« qualité »** de l'intégration continue n'a **pas** de stack : 250 tests unitaires × deux
purges × 4,06 s. Elle est restée **en cours plus de quarante minutes** sur l'étape des tests
unitaires, la porte n'a jamais rendu son verdict, et la fusion a été **refusée** — `BLOCKED`, la
protection de branche faisant son travail.

> **C'est la sixième proposition du §7.0 sous un autre jour** : *un contrôle qui compare deux nombres
> doit prouver qu'ils mesurent la même grandeur.* Ici « délai de connexion » et « attente totale »
> sont deux grandeurs différentes, d'un **facteur dix**. J'ai affiché la première en croyant borner la
> seconde — exactement le plafond de taille de `T7-6`, dans un autre costume.

**Deux parades, et la première suffit presque :**

1. **la sonde de port précède la connexion**, et son résultat est mémorisé pour la session —
   `port_ouvert` coûte **quatre mille fois moins** qu'une tentative redis-py ;
2. **la reprise est bornée à zéro**, ce qui couvre le cas où le port est ouvert mais Redis ne répond
   pas — un conteneur qui démarre.

**Preuve :** `.env` pointé sur un port fermé, les **250 tests unitaires passent en 5,46 s**. C'est
exactement la situation de la tâche qualité.

**Et le même défaut existait sur le CHEMIN D'UNE REQUÊTE, dans deux modules.** `debit.py` et
`idempotence.py` déclaraient tous deux `DELAI_REDIS_SECONDES = 2` « pour qu'un Redis lent ne fasse pas
pendre la requête ». Il ne l'empêchait pas : **quatre secondes par requête**. Le « refus par défaut »
du §20.1 ne vaut que s'il est **rapide** — sinon une panne de Redis transforme la protection en vecteur
de saturation. Les deux sont corrigés ; `idempotence.py` vient de `T7`, et le laisser aurait été
livrer sciemment une attente de quatre secondes sur chaque écriture.

**Ce que je retiens, et c'est une leçon de méthode :** j'avais formé cette hypothèse plus tôt — « ma
fixture coûte quelque chose quand Redis est absent » — puis je l'avais **réfutée** sur le mauvais
critère. J'ai mesuré les **descripteurs de fichier**, pas le **temps**. La mesure était juste, la
question était fausse. *Réfuter une hypothèse exige de mesurer la grandeur qu'elle prédit.*

---

## 8. Ce qui n'est PAS couvert

- **l'alerte** elle-même : `operational_alert` du §21.2, **LOT 10**. `T8` livre la **détection**,
  journalisée avec un motif nommé, sur laquelle le LOT 10 branchera son alerte ;
- **les trois autres alertes du §20.2** — attribution de super-administrateur, purge définitive,
  exports d'audit — dont les objets n'existent pas encore ;
- **la configuration des seuils.** `platform_setting` (modèle §5.2, « seuils de sécurité »), avec
  l'écran de réglages du **LOT 9** et l'audit du **LOT 10**. Les cinq variables de `.env.example` §8
  sont **annotées `[non consommée — ECART-034]`** plutôt que silencieuses : un exploitant qui
  abaisserait un seuil croirait avoir durci la sécurité et se tromperait ;
- **une fenêtre glissante.** Résiduel nommé au §5 ;
- **la limitation des routes métier.** Elles n'existent pas ; le mécanisme les attend ;
- **la recette.** Images publiées de révision antérieure à `T1`. À republier avant `G3`.

---

## 9. Ce que `T9` devra savoir

1. **`T9` est la révocation au départ, et elle rend `§30.22` acquis.** Le contrôle qui le classe est
   `make recette-modele-check`, et il **échoue** si un contrôle du §30 cesse d'être classé.
2. **`revoquer()` existe depuis `T6`**, dans `apps/api/app/auth/sessions.py`, et elle est
   **idempotente** — elle écrit `SESSION_REVOKED`. `T9` doit la rendre **atomique avec l'archivage**,
   ce qui veut dire : dans la **même transaction** que la transition d'état de l'appartenance.
3. **Trois choses sont à révoquer, et le critère de la fiche les nomme** : sessions, invitations et
   **futurs magic links**. Les liens actifs vivent dans `magic_link_request` ; l'index partiel de
   `T2` en autorise **un seul** actif par personne, donc l'invalidation est un `UPDATE` ciblé, pas
   une suppression — supprimer effacerait la trace.
4. **Une session révoquée ne doit plus répondre, et il faut le MESURER** — pas déduire de l'écriture
   de `revoked_at`. `lire_et_rafraichir` filtre déjà sur `revoked_at IS NULL` ; le contrôle doit
   faire un aller-retour HTTP réel.
5. **Le compteur de débit de `T8` n'est PAS lié à l'identité**, et c'est voulu : il porte sur une
   empreinte d'adresse, pas sur une personne. Un départ ne le vide donc pas, et il n'a pas à le
   faire — mais **si `T9` écrit un contrôle qui enchaîne plusieurs connexions sur une même adresse,
   il devra purger** : `purger_les_compteurs_de_debit(env)`, dans `infra/scripts/debit_partage.py`.
   Trois vérificateurs sont passés par là.
6. **`auth_event` n'a que SEPT types**, et `SESSION_REVOKED` en est un. N'en invente pas un huitième :
   `T12` auditera exactement les sept du §10.6.
