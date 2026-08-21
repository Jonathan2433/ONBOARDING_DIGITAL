# Compte rendu — LOT 3, sous-étape `T6`

**Les sessions, le cookie, et ce qu'il ne rend pas**
**Story :** `MVP-L03-US004`, issue `#66`
**Réalisée le :** 21 août 2026
**Décisions produites :** `DEC-529`, `DEC-530`
**Migration produite :** **aucune**

---

## 1. Rien n'était à inventer, et j'allais le faire

Le cahier §7.4 exige « cookie `HttpOnly`, `Secure` et `SameSite` » **sans dire laquelle**. J'avais
préparé une dérivation : le même §7.4 exige aussi la protection CSRF, et `Lax` + CSRF est la
combinaison documentée.

**`.env.example` écrivait déjà la réponse, depuis la sous-étape S5 du LOT 0 :**

```text
SESSION_COOKIE_NAME=exalt_session
SESSION_COOKIE_SAMESITE=lax
SESSION_IDLE_DAYS=7
SESSION_ABSOLUTE_DAYS=30
```

**Quatre valeurs déjà tranchées**, et je m'apprêtais à en dériver une. C'est le §9.0 dans sa forme la
plus utile : *vérifie avant de bâtir dessus — surtout quand la documentation t'annonce que tu n'as
rien à faire.* La mesure a pris trente secondes ; la dérivation aurait produit la bonne valeur pour
une mauvaise raison, et aurait laissé croire que le choix venait de moi.

---

## 2. Le jeton n'apparaît dans AUCUN corps, et c'est ce qui rend le critère tenable

Le critère du §3 de la fiche est double : les trois attributs sur la réponse réelle, **et** « aucun
jeton dans `localStorage`, prouvé par un contrôle du frontend ».

**Le second ne se tient pas par discipline.** Un frontend qui **reçoit** un jeton finit par le
stocker — c'est une question de temps et de développeurs. Deux barrières, et la première est
structurelle :

| Barrière | Ce qu'elle empêche |
|---|---|
| `HttpOnly` + le jeton absent de tout corps | un frontend **ne peut pas** stocker ce qu'il ne peut pas lire |
| le contrôle des **sources** du frontend | le §7.4 interdit *toute* donnée d'authentification durable, pas seulement le jeton |

C'est le §7.2 appliqué à une règle de sécurité : *changer de forme plutôt que promettre de
l'attention.*

**Et le contrôle des sources est EXACT, pas heuristique.** Il retire les **commentaires** avant de
chercher, mais garde les **chaînes** — `window["localStorage"]` est un usage. Sans le retrait des
commentaires, il se déclencherait sur le commentaire qui explique la règle : c'est exactement le
défaut mesuré en `T11` du LOT 2. Son témoin, `make sessions-temoin`, l'éprouve **dans les deux
sens** et tourne dans `make check` parce qu'il n'exige aucune stack :

```text
ok   un USAGE reel est detecte — apps/web/src/__temoin_usage.ts:1
ok   un COMMENTAIRE qui les mentionne ne declenche PAS
```

---

## 3. Les deux expirations, et le test qui les distingue

| Expiration | Où elle vit |
|---|---|
| absolue, 30 jours | **une colonne**, `absolute_expires_at`, bornée par la contrainte `duree_absolue_bornee` |
| inactivité, 7 jours | **aucune colonne** — elle se calcule sur `last_activity_at`, `T2` l'avait posé |

**Le test qui compte est celui qui les distingue.** Une session gardée active par une lecture tous
les cinq jours doit **mourir au trentième**. Sans lui, une implémentation qui n'aurait que
l'inactivité vivrait indéfiniment. Et symétriquement, une lecture au sixième jour **repousse** la
borne d'inactivité — ce qu'une durée fixe depuis `created_at` ne ferait pas ; sans ce test, une
implémentation bornée sur `created_at` passerait les deux autres.

Chaque borne est éprouvée **des deux côtés** : six jours passe, huit jours expire ; trente jours
passe, trente-et-un expire. Sans le côté permissif, une expiration à cinq minutes passerait le test
de l'expiration — défaut du §7.20.

**La durée absolue est tenue à trois niveaux** — contrainte en base, garde-fou de démarrage, test —
et l'inactivité à deux. C'est délibéré, et le §4 dit pourquoi.

---

## 4. Le garde-fou : les deux durées ne sont pas également exposées

`SESSION_ABSOLUTE_DAYS` est bornée **en base**. Une valeur supérieure ferait refuser l'insertion, et
le message de PostgreSQL ne nommerait pas la variable.

**`SESSION_IDLE_DAYS` n'a aucune contrainte en base**, puisque l'inactivité se calcule. Une
divergence y serait donc **silencieuse** : la plateforme déconnecterait au bout de quatorze jours en
affirmant sept, et rien ne le signalerait. **C'est le cas le plus dangereux des deux**, et celui qui
justifie le plus un garde-fou de démarrage.

```text
idle=14  -> ['SESSION_IDLE_DAYS : doit valoir 7 (cahier §7.4, modele §10.4).
             Aucune contrainte en base ne le refuserait : une divergence serait SILENCIEUSE']
abs=60   -> ['SESSION_ABSOLUTE_DAYS : doit valoir 30, valeur imposee EN BASE par la
             contrainte `duree_absolue_bornee` (modele §10.4)']
```

---

## 5. Le rafraîchissement est une course — troisième fois dans ce lot

Lire `last_activity_at`, décider, puis écrire laisserait deux requêtes concurrentes juger valide une
session que l'une des deux vient de laisser expirer : la seconde lirait l'ancienne valeur, concluerait
« valide », et **écrirait un horodatage frais sur une session morte**.

Le patron est celui de `T4` (usage unique) et `T5` (compteur d'échecs) : un seul `UPDATE`
conditionnel dont le nombre de lignes affectées est le verdict.

**Le témoin négatif est le plus net des trois :**

```text
implementation lire-puis-ecrire :
  test de concurrence   -> ECHEC  assert 'session_valide' == 'session_refusee'
                                  « B a RAVIVE une session revoquee »
  les 8 tests sequentiels -> TOUS PASSENT
```

Comme en `T4`, les tests séquentiels sont **entièrement aveugles** à ce défaut.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **550 tests, 0 échec** — 525 avant `T6` |
| — et **zéro résidu**, mesuré après purge et suite complète | `person` 0, `user_session` 0, `auth_event` 0 |
| `make check` · `make audit` | **0** · **0** |
| **`make sessions-check`** | **0 — 13 contrôles**, à travers Caddy en HTTPS |
| **`make sessions-temoin`** | **0** — le contrôle du frontend sait échouer, **et** ne crie pas au loup |
| `magic-link-check` · `admin-check` | **0** · **0**, et **zéro résidu chacun** après correction |
| 12 autres contrôles | tous à **0** |

**Ce que `make sessions-check` prouve, en treize contrôles :**

```text
aucun localStorage ni sessionStorage dans les 21 fichiers source du frontend
cookie pose avec HttpOnly, Secure, SameSite=lax, Path=/    sur la reponse REELLE
Max-Age=2592000                                            la duree absolue du §10.4
le jeton n'apparait dans AUCUN corps                        cookie seul
le cookie ouvre la session (200), son absence la refuse (401)
3 causes de refus indistinguables                          toutes 401
TEMOIN — le comparateur distingue un succes d'un refus
deconnexion — le meme jeton est refuse ensuite (401)       le SERVEUR fait autorite
deconnexion idempotente — 200 rejouee, 200 sans cookie
1 session, REVOQUEE et non effacee, empreinte de 64 hexadecimaux
audit — 1 SESSION_REVOKED, la deconnexion rejouee n'en cree pas
aucun `oss_` dans les journaux de api, ni de caddy
```

**Les 25 tests nouveaux** couvrent le jeton, les deux expirations bornées des deux côtés, la
révocation et son idempotence, l'atomicité sous concurrence, et le cookie sur la réponse réelle.

---

## 7. Trois défauts, tous dans mon travail

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T6-1` | Mes deux tests d'aller-retour du cookie rendaient **401** : `TestClient` parle `http://` par défaut, et **un cookie `Secure` n'est jamais renvoyé sur une origine non chiffrée**. Le code était juste ; c'était le client qui exerçait une autre configuration que la vraie | `uv run pytest` — 23 passaient, 2 échouaient |
| `T6-2` | **Le nettoyage de `T5` ne connaissait pas `user_session`**, et la clé étrangère a bloqué la suppression de la personne. Le résidu a fait échouer **dix tests sans rapport** dans trois fichiers | la suite complète, puis le `DETAIL` de PostgreSQL : « is still referenced from table `user_session` » |
| `T6-3` | Les **deux** vérificateurs de `T3`/`T4` et de `T5` avaient le même trou, et laissaient 3 personnes et 4 sessions derrière eux | comptage du résidu après la batterie complète |

**`T6-1` mérite d'être regardé en face.** La correction facile aurait été de mettre
`SESSION_COOKIE_SECURE=false` dans les tests — et le test aurait alors éprouvé **un cookie que la
production n'emploie pas**. La correction juste est de parler HTTPS, comme Caddy le fait. *Un test qui
contourne un attribut de sécurité pour passer ne prouve rien de cet attribut.*

**`T6-2` et `T6-3` sont la même leçon, et c'est la quatrième et la cinquième fois dans ce lot.** La
classe est désormais nette :

> **Quand une sous-étape ajoute une TABLE, tous les nettoyages écrits avant elle deviennent
> incomplets — et la clé étrangère transforme un nettoyage incomplet en résidu, puis le résidu en
> échec de tests qui n'ont rien à voir.**

Cinq nettoyages ont été touchés par l'ajout de `user_session` : deux dans `test_administrateur.py`, un
dans chacun des trois vérificateurs. Aucun n'était négligent : tous étaient **complets à leur date**.
C'est le §7.21, et cette variante — l'ajout d'une table, non d'un environnement — mérite d'y figurer.

---

## 8. Ce qui n'est PAS couvert

- **la protection CSRF.** `T7`, `US005`. **Et c'est elle qui rendra `SameSite=lax` suffisant** :
  `lax` laisse passer une navigation de haut niveau en `GET` avec le cookie, ce qui est sans danger
  tant qu'aucune écriture n'est déclenchée par une navigation. `T7` doit le fermer ;
- **la limitation de débit** sur les routes de session. `T8` ;
- **le rafraîchissement à chaque requête métier.** Aucune route métier n'existe encore : `GET
  …/auth/session` est le seul consommateur, et c'est lui qui rafraîchit. Le LOT 4 devra décider si
  chaque requête rafraîchit — un `UPDATE` par requête a un coût — ou seulement au-delà d'un délai ;
- **la révocation au départ.** `T9`, `US006`, et `revoke_reason` existe pour la distinguer d'une
  déconnexion ;
- **les écrans.** `T11`, dont la page de déconnexion ;
- **la recette.** Images publiées de révision antérieure à `T1`. À republier avant `G3`.

---

## 9. Ce que `T7` devra savoir

1. **`SameSite=lax` n'est PAS suffisant seul, et c'est ton travail.** Le cahier §7.4 énumère
   `SameSite` **et** la protection CSRF dans la même liste : `lax` laisse passer une navigation de
   haut niveau avec le cookie. Toute écriture déclenchable par une simple navigation est exposée
   jusqu'à ce que `T7` la ferme.
2. **`CSRF_PROTECTION_ENABLED` est désormais TRANSMISE au conteneur.** Elle ne l'était pas — 0
   occurrence dans Compose — donc le garde-fou de production du §20.3 ne pouvait pas se déclencher
   sur une valeur réelle. Elle vaut `true` et n'est pas désactivable.
3. **Les routes qui écrivent sont déjà là** : demande de magic link, consommation, connexion,
   changement de mot de passe, déconnexion. Cinq écritures, dont **trois ne peuvent pas exiger de
   jeton CSRF** — elles précèdent la session. Le §18.6 énumère les opérations idempotentes, et aucune
   des cinq n'y figure : c'est une lecture à poser, pas à supposer.
4. **`GET …/auth/session` rafraîchit l'activité.** Ce n'est donc pas une lecture pure, et `T7` doit
   décider si une route qui écrit un horodatage sur un `GET` relève de sa protection. Je ne l'ai pas
   tranché : la lire est ce que le frontend fera à chaque chargement de page, et exiger un jeton CSRF
   sur elle rendrait impossible de savoir si l'on est connecté.
5. **Le patron compare-et-pose a servi trois fois** — `T4`, `T5`, `T6`. Les clés d'idempotence du
   §18.6 en sont un quatrième cas : deux requêtes portant la même clé ne doivent produire qu'un
   effet. **Éprouve-le sous concurrence** ; les tests séquentiels y sont aveugles, mesuré trois fois.
6. **Cinq nettoyages ont été corrigés en `T6`** parce qu'ils précédaient `user_session`. Si `T7` crée
   une table, relis-les : la liste est dans `test_administrateur.py`, `test_sessions.py`, et les trois
   `verifier-*.py` d'authentification.
