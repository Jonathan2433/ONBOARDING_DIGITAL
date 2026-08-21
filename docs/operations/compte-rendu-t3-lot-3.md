# Compte rendu — LOT 3, sous-étape `T3`

**La demande de magic link, sans révéler l'existence du compte**
**Story :** `MVP-L03-US001`, issue `#63`
**Réalisée le :** 21 août 2026
**Décisions produites :** `DEC-522`, `DEC-523`
**Migration produite :** **aucune** — les sept tables existaient depuis `T2`

---

## 1. Le critère est une ÉGALITÉ, et c'est ce qui a structuré la sous-étape

Le backlog écrit : « la réponse est **générique** ». La fiche du lot le reformule en risque de
sécurité au §7 : « la réponse anti-énumération diverge par un détail — un temps de réponse, un
en-tête ».

**Un test qui vérifierait « une adresse inconnue est refusée » prouverait le CONTRAIRE de ce que la
story demande.** L'objet n'est pas un refus, c'est une égalité entre deux observations.

**L'égalité n'a donc pas été obtenue en comparant deux chemins de code : elle est obtenue en n'en
ayant qu'un.** La route a **un seul gabarit de réponse** — `202`, corps constant, en-têtes constants
— et le service lui rend un motif dont elle ne fait qu'une chose : décider s'il y a un e-mail à
envoyer. C'est le §7.2 appliqué à une règle de sécurité : *quand une classe d'erreur résiste à la
vigilance, change de forme plutôt que de promettre de l'attention.*

**Mesuré sur la réponse réelle, à travers Caddy en HTTPS :** code `202`, **143 octets** de corps,
**7 en-têtes comparés**, `0` divergence entre adresse connue, adresse inconnue et profil archivé.

---

## 2. Quatre choses que le corpus tranche, et que je n'ai pas reposées

| Question | Ce que le corpus écrit |
|---|---|
| Qui autorise un domaine ? | **Le modèle §5.4**, littéralement : `active` \| « **Contrôle l'usage lors de l'authentification** ». C'est la TABLE. Et `T2` du LOT 2 avait déjà posé cette lecture dans sa docstring |
| Qu'est-ce qu'un « profil archivé » du §30.11 ? | Le §6.2 nomme `entity_membership` « profil », et `archived` est l'un de ses **quatre** états. Le cahier §7.2 exige plus large : « son appartenance doit être **active** » |
| Sous quelle forme le lien voyage-t-il ? | `journal.py` l'écrit depuis `T4` du LOT 1 : « Un magic link du LOT 3 y passera : `?token=...` », et la barrière de masquage porte déjà `[?&](token\|jeton\|code\|magic)=`. **Ce n'est pas un choix, c'est une anticipation écrite** |
| Combien de temps un lien vit-il ? | Le §10.3 écrit 15 minutes, et la contrainte `expiration_a_quinze_minutes` de `T2` l'impose **en base** |

**Une seule chose n'était pas tranchée, et elle t'a été posée** : comment la première ligne de
`allowed_email_domain` arrive en base. La table naît vide ; sans elle, personne ne peut demander de
lien, y compris pour le point 1 de la démonstration de `G3`. Ton arbitrage : une cible `make`
idempotente, comme `roles-provision` en `T1`. `DEC-523`.

**Et un point où j'avais tort dans ma propre question.** Je t'ai annoncé qu'elle serait appelée par
`make up`. C'est **`make migrate`** qui l'appelle, et le motif est l'ordre : elle écrit dans une
table, donc elle exige une base migrée, or là où `make up` appelle `roles-provision`, aucune
migration n'a tourné. Un appel qui « sauterait » quand la table manque aurait produit un succès
silencieux, ce que le §7.0 interdit.

---

## 3. Ce que le service exige, et pourquoi la cinquième condition est asymétrique

Quatre conditions sont écrites au cahier §7.2 et au modèle §10.3 :

| Condition | Source |
|---|---|
| la personne existe | cahier §7.2 |
| `person.account_state = 'active'` | modèle §10.3, « Personne **active** existante » |
| une appartenance `active` | cahier §7.2, « son appartenance doit être active » |
| un domaine autorisé, `active` **et** dans sa période, global ou de **son** entité | cahier §7.2, modèle §5.4, §2.5 |

**Une cinquième est dérivée, et son asymétrie est le point :**

```text
le compte `user_account` EXISTE et n'est pas `active`   ->  REFUS
le compte N'EXISTE PAS                                 ->  ce n'est PAS un refus
```

Le §10.1 pose `state` sur « un compte permettant l'authentification » : un compte `disabled` qui
recevrait quand même des liens rendrait cette colonne **sans effet**, alors que `T5` s'en servira pour
le verrouillage et `T9` pour la révocation.

**Mais exiger son existence serait exiger plus que le modèle.** `magic_link_request` référence
`person_id`, **jamais** `user_account_id`, et **aucun lot ne crée aujourd'hui de ligne
`user_account`** : la fonctionnalité serait inutilisable. C'est le défaut du §7.20, et
`test_un_compte_ABSENT_n_est_PAS_un_refus` est le témoin qui l'empêche de revenir.

Un dernier témoin sur ce point : un compte **`ADMIN_LOCAL` désactivé ne bloque pas** le magic link.
Le §10.1 permet deux comptes distincts ; les confondre verrouillerait l'un par l'autre — le
contresens que `T7` et `T8` du LOT 2 ont appris à éviter.

---

## 4. Le préfixe du jeton est une mesure de sécurité, pas une convention

Un jeton est 43 caractères base64url tirés au hasard. **Sans préfixe, aucun détecteur ne peut être
exact** : une règle de masquage ou une règle Gitleaks devrait se rabattre sur « une longue chaîne
base64 », donc refuser du contenu légitime — et **un garde-fou à faux positifs apprend à passer
outre**, §7.25.

Le préfixe rend les deux détecteurs exacts. C'est le motif du motif `gh[pousr]_` que le filtre porte
déjà pour les jetons GitHub : ce n'est pas la longueur qui rend un jeton détectable, c'est le préfixe.

**La famille est réservée ici, pour que `T6` et `T10` ne l'inventent pas chacune de leur côté** —
sans quoi le projet aurait trois formats et trois motifs :

| Préfixe | Usage | Sous-étape |
|---|---|---|
| `oml_` | magic link | **`T3`** |
| `oss_` | jeton de session | `T6`, `US004` |
| `ost_` | jeton de service | `T10`, `US007` |

**Et les constantes vivent dans `packages/observabilite`, pas dans `apps/api`.** Le format a **trois**
consommateurs : le code qui l'engendre, la barrière de masquage, et la règle Gitleaks. Le filtre **ne
peut pas** importer `apps/api` — c'est l'inverse. Les poser dans le paquet partagé donne une seule
source aux deux consommateurs Python, motif de `DEC-466`.

**Le troisième consommateur est du TOML, qui n'importe rien.** Sa règle est donc nécessairement une
copie, et une copie vieillit au premier changement, §7.27. La parade :
`test_le_MOTIF_de_la_regle_GITLEAKS_attrape_un_jeton_reellement_engendre` **lit `.gitleaks.toml`** et
exige que sa règle attrape un jeton réellement engendré — avec le témoin inverse, qui exige qu'elle
**n'attrape pas** une chaîne base64 sans préfixe.

---

## 5. Deux empreintes, deux algorithmes, et c'est mesuré

| Valeur | Algorithme | Motif |
|---|---|---|
| `token_hash` | **SHA-256 simple** | Le §10.3 écrit « hash uniquement ». Un HMAC n'apporte rien à 256 bits d'aléa — il n'y a rien à deviner — et il coûterait cher : une rotation d'`APP_SECRET_KEY` invaliderait **tous** les jetons actifs sans que rien ne le dise |
| `request_origin_hash` | **HMAC-SHA-256**, clé `APP_SECRET_KEY` | **Le cas inverse.** Une adresse IPv4 n'a que **32 bits** : une empreinte simple se renverse en énumérant 4,3 milliards de valeurs. Elle ne serait donc **pas** une valeur minimisée, seulement une valeur qui en a l'air |

`empreinte_d_origine` **lève** sur une clé vide plutôt que de produire une empreinte non salée. Et un
test exige que deux origines distinctes donnent deux empreintes distinctes : sans lui, une
implémentation qui rendrait une constante passerait le premier test — et la limitation de `T8`
deviendrait un plafond global.

---

## 6. `request.client.host` est CONSTANT derrière Caddy, et c'était un piège

L'API n'est joignable que par Caddy — cahier §22.2, `DEC-460`, le service n'est pas publié.
`request.client.host` est donc l'adresse du **conteneur Caddy**, la même pour tout le monde.

**Une origine constante n'est pas une origine.** Elle ferait de la limitation de `T8` un plafond
global, et l'échec aurait produit exactement la même observation que le succès — quatrième
proposition du §7.0.

L'origine retenue est donc le **dernier** élément de `X-Forwarded-For`. Le **premier** est fourni par
le client, donc **forgeable à volonté** : s'en servir permettrait de contourner la limitation en
changeant d'en-tête à chaque requête. Caddy **ajoute** l'adresse de son pair à la fin.

**La limite de confiance est dite** : la valeur ne vaut que si l'API n'est joignable que par un
mandataire de confiance. C'est le cas aujourd'hui. **`T8` doit la réexaminer**, et le LOT 13 aussi, où
un second mandataire pourrait s'intercaler.

---

## 7. `PUBLIC_BASE_URL` était FAUSSE, et rien ne pouvait le signaler

**Trois mesures, et c'est le §7.16 dans sa forme la plus pure — *ce qui n'a jamais tourné n'est pas
éprouvé* :**

| Mesure du 21/08/2026 | Constat |
|---|---|
| `.env` et `.env.example` | `PUBLIC_BASE_URL=https://localhost` |
| ce que Caddy sert | `app.onboarding.localhost` (`DEC-446`), **jamais** `localhost` |
| ce que Compose transmet au conteneur `api` | **rien** — 0 occurrence dans son bloc `environment` |
| le calque de recette | `https://app.recette.onboarding.localhost:8443`, **correct depuis `T8`** |

**La recette était juste et le développement faux.** Un magic link bâti sur `https://localhost` aurait
été inutilisable, et **aucun contrôle ne l'aurait dit** : la variable était déclarée par `settings.py`
depuis `T3` du LOT 1 et consommée par personne.

**Sept variables de plus ne sont plus seulement déclarées, elles sont transmises** :
`PUBLIC_BASE_URL`, `APP_SECRET_KEY`, `EMAIL_PROVIDER`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`,
`SMTP_FROM_ADDRESS`, `SMTP_FROM_NAME`, `MAGIC_LINK_TTL_MINUTES`. `EMAIL_PROVIDER` en particulier est
l'un des **sept garde-fous de production** du cahier §20.3 : non transmise, elle valait son défaut
`mailpit`, et le garde-fou ne pouvait donc pas se déclencher sur une valeur réelle.

> **`.env` n'est pas versionné et `make env` ne réconcilie rien** (`ECART-022`). J'ai corrigé la
> valeur **à la main** dans le `.env` de cette machine. `make env-check` ne compare que les **noms**,
> pas les valeurs : il ne l'aurait pas vu. **Si tu recrées un `.env` depuis le modèle, la valeur sera
> la bonne** — `.env.example` passe en **v1.4**.

**Et une variable qui n'était pas un réglage.** `MAGIC_LINK_TTL_MINUTES=15` cohabitait avec `15` en
dur dans la contrainte `expiration_a_quinze_minutes`. La porter à 20 n'aurait rien changé au
comportement : PostgreSQL aurait **refusé l'insertion**, et son message n'aurait pas nommé la
variable. Un garde-fou de démarrage refuse désormais la divergence, avec son témoin.

---

## 8. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **469 tests, 0 échec** — 415 avant `T3`, dont **268 d'intégration** |
| `make test-frontend` | **116** — 90 `ui`, 25 `web`, 1 `contracts` |
| `make check` | **code 0** — format, lint, mypy strict, docs-check, images-check, recette-modele-check |
| `make audit` | **code 0** — voir §10, il était **rouge à l'ouverture de la session** |
| **`make magic-link-check`** | **code 0 — 10 contrôles, 0 échec**, à travers Caddy en HTTPS |
| `make domaines-provision` | **code 0**, et **idempotent sur trois passages** : 1 ligne en base |
| — son témoin | domaine **désactivé à la main** → `SIGNALE`, **non réactivé**, 1 ligne, `active=false` |
| `make migrate` · `migrate-status` | code 0 · `0012 (head)` — **aucune migration ajoutée** |
| `make code-check` | **a échoué d'abord** — 44 fichiers de part et d'autre, **contenus différents**. Il a fait son travail |
| `alembic-check` · `migrations-check` | code 0 · code 0 |
| `privileges-check` · `secrets-check` | code 0 · code 0 |
| `isolation-check` · `isolation-temoin` | code 0 · code 0 |
| `historisation-check` | code 0 |
| **`recette-modele-check`** | **code 0 — 11 acquis** contre 10 avant : **`§30.11` est passé de `reporte` à `acquis`** |
| `stack-check` · `api-check` · `web-check` | code 0 · code 0 · code 0 |
| `env-check` · `docs-check` · `images-check` | code 0 · code 0 · code 0 |

**Les 54 tests nouveaux** : 45 dans `test_magic_link.py`, 9 dans `test_masquage.py`. Chaque règle a son
témoin, et le fichier porte **le témoin du comparateur lui-même** —
`test_TEMOIN_le_comparateur_sait_ECHOUER` exige qu'il signale deux réponses réellement différentes.
Sans lui, les trois tests d'égalité ne prouveraient rien.

**Ce que `make magic-link-check` prouve, en dix contrôles :**

```text
connue == inconnue          code 202, 143 octets, 7 en-tetes compares
connue == archivee          §30.11 sans divergence de reponse
en-tetes exclus             ['x-request-id'] — et la liste est EXIGEE, non supposee
TEMOIN                      4 differences detectees face a un corps malforme (422)
effet reel                  1 lien actif pour le profil ACTIF, 0 pour l'ARCHIVE
invalidation                seconde demande -> 2 liens en base, 1 SEUL actif
audit                       4 evenements, dont 1 SANS personne (adresse inconnue)
empreintes                  toutes 64 hexadecimaux, aucun jeton en clair
journaux                    aucun `oml_` dans les journaux du conteneur api
Mailpit                     1 message pour la connue, 0 pour l'inconnue, et
                            LE JETON DE L'E-MAIL CORRESPOND A LA LIGNE EN BASE
```

**Le dernier est le plus important.** « Un e-mail est arrivé » ne prouve rien : un service qui
enverrait un lien sans l'enregistrer — ou l'inverse — donnerait la même observation. Le contrôle
extrait le jeton du corps du message, en calcule l'empreinte, et exige qu'elle désigne **une** ligne
de `magic_link_request`. Le jeton n'est **jamais affiché**.

---

## 9. Les durées : mesurées, rapportées, et NON fermées

**La première mesure ne valait rien, et c'est la sixième proposition du §7.0.** Elle comparait une
requête à une autre :

```text
connue 95 ms · inconnue 22 ms · archivee 7 ms
```

Un facteur quatre — qui mesurait surtout **l'ouverture du pool de connexions SQLAlchemy**, payée par
le premier appel. **Les deux nombres ne mesuraient pas la même grandeur.**

La mesure est donc **entrelacée** — connue, inconnue, connue, inconnue — après deux tours de chauffe
jetés, et c'est la **médiane** de neuf tours qui est rapportée :

```text
connue 6,2 ms (min 5,1, max 8,0) · inconnue 5,3 ms (min 4,8, max 6,4)
ecart median : +0,9 ms
```

**Ce résiduel n'est pas fermé, et il n'est pas exigé nul.** L'exiger produirait un contrôle
intermittent, ce qui est pire qu'un résiduel nommé — §7.20. Il vaut le surcoût de **quatre requêtes
SQL**, contre les **dizaines de millisecondes** d'un aller-retour SMTP que l'envoi en tâche
d'arrière-plan a sorties du chemin de réponse.

---

## 10. Neuf défauts, tous dans mon travail sauf un

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T3-0` | **`make audit` était ROUGE à l'ouverture de la session**, et la CI de `develop` avec. `pip 26.1.2` a reçu `PYSEC-2026-3721` | le démarrage de session. **Ce n'est pas mon travail** : un avis publié sans nous, §7.22 |
| `T3-1` | Mon décor de test créait une appartenance `departed` **sans date de départ** | `ck_entity_membership_depart_date_si_departed`, posée en `T4` du LOT 2. **La base a fait son travail** |
| `T3-2` | Mon `INSERT` de `user_account` omettait `failed_login_count` | `NotNullViolation`. Ses défauts sont **côté Python**, pas `server_default` — voir §11 |
| `T3-3` | Ma fixture laissait **18 lignes** `auth_event` en base, et elles ont fait échouer **deux tests de `T2`** | `uv run pytest` sur la suite complète |
| `T3-4` | Ma mesure de durée comparait une requête à une autre, dont la première payait la chauffe du pool | la sortie elle-même : 95 ms contre 22 ms était trop gros pour 4 requêtes SQL |
| `T3-5` | Mon nettoyage de Mailpit annonçait « 0 supprimé » **alors qu'il supprimait**. Deux causes : mauvais point d'entrée, puis un succès lu comme un échec parce que la réponse n'est pas du JSON | j'ai compté les messages de Mailpit **après** le contrôle : 0. Le nettoyage marchait, le compte-rendu non |
| `T3-6` | **J'ai commis le piège du §7.2** : `DCEX="docker compose --env-file $PWD/.env …"`, espace dans le chemin, `code=127`, **la commande n'a jamais tourné** | le code de sortie. **Cinquième occurrence du projet**, et je l'avais lue le jour même |
| `T3-7` | Mon `# noqa: S608` s'est retrouvé **à l'intérieur** d'un littéral `f"""`, donc dans le SQL envoyé à PostgreSQL | j'ai relancé `make magic-link-check` au lieu de croire `ruff` — le `#` n'est pas un commentaire SQL |
| `T3-8` | Mon test écrivait `>= 40` en dur au lieu de dériver la borne de sa constante | `ruff` a signalé l'import devenu inutile, ce qui m'a fait relire — **troisième copie du même nombre**, §7.27 |

**`T3-6` mérite d'être regardé en face.** Le §7.2 nomme ce piège quatre fois, dont **deux fois par un
agent qui l'avait lu le jour même**, et sa parade est explicite : *quand une classe d'erreur résiste à
la vigilance, change d'outil.* Les scripts de ce dépôt sont en Python pour cette raison. Je l'ai
commis dans une commande de diagnostic ad hoc — le seul endroit où la parade ne s'applique pas. **Un
remède structurel ne couvre que le périmètre où il s'applique**, et il faut savoir dire où il
s'arrête : c'est le §7.3 dans l'autre sens.

**`T3-5` est la quatrième proposition du §7.0 appliquée à un NETTOYAGE.** Un nettoyage qui échoue et
un nettoyage qui n'a rien à faire produisaient tous deux « 0 supprimé ». Le compte est désormais
**confronté à ce qui a été trouvé**, et un écart est `SIGNALE`.

---

## 11. Trois contrôles de `T2` rendus faux par ce livrable — §7.21

**Cinq tests écrits au LOT 2 et au LOT 3 `T2` ont échoué, et ils avaient raison d'échouer.**

| Test | Ce qu'il supposait | Ce qui l'a cassé |
|---|---|---|
| `test_les_SEPT_types_d_evenement_sont_acceptes` | `auth_event` est vide | `T3` y écrit un événement **par demande** |
| `test_un_evenement_SANS_personne_est_accepte` | `auth_event` a **une** ligne | idem |
| `test_un_domaine_GLOBAL_a_une_entite_nulle` | `allowed_email_domain` est vide | `make domaines-provision` y pose une ligne **réelle** |
| `test_un_domaine_local_sur_une_entite_reelle_est_accepte` | idem | idem |
| `test_les_domaines_normalises_sont_acceptes` | idem | idem |

**La distinction entre les deux groupes compte.** Les deux premiers échouaient sur du **résidu de
test**, que j'ai supprimé (`T3-3`). Les trois suivants échouent sur une **donnée de référence
permanente** : il n'y a rien à nettoyer, la ligne doit rester.

**Le correctif est donc dans les tests, et aucun n'est affaibli** : chacun compte toujours exactement
ce qu'il vient d'insérer, avec un filtre au lieu d'un compte global. C'est le §7.21 — *un contrôle ne
devient pas faux tout seul, il le devient quand le monde change autour de lui, et ce changement, c'est
nous qui le faisons.*

**Et une observation pour `T5`, celle-là non corrigée parce qu'elle n'est pas un défaut.**
`user_account.state`, `user_account.failed_login_count` et `admin_password_credential.must_change`
portent des défauts **côté Python** (`default=`), pas `server_default`. Un `INSERT` en SQL brut ne les
reçoit donc pas, et la colonne `NOT NULL` refuse la ligne. `T5` créera des comptes : qu'elle nomme
ces colonnes, ou qu'elle passe par l'ORM.

---

## 12. Ce qui n'est PAS couvert

- **la consommation du lien.** `T4`, `US002`. `used_at` ne se pose pas encore, et l'invariant
  structurant est déjà là ;
- **la limitation de débit.** `T8`. `request_origin_hash` est **renseignée** dès maintenant : une
  colonne laissée nulle par `T3` serait inexploitable retroactivement ;
- **les six autres types d'événement du §10.6.** `T3` n'écrit que `MAGIC_LINK_REQUESTED`. L'audit
  complet et son contrôle d'exhaustivité relèvent de **`T12`** ;
- **l'égalité des DURÉES.** Mesurée, rapportée, non fermée. Voir §9 ;
- **la croissance de `auth_event` sur une adresse inconnue.** Chaque demande écrit une ligne, y
  compris pour une adresse qui n'existe pas : c'est voulu — un échec doit être traçable — mais c'est
  une surface de saturation que **`T8`** doit borner ;
- **la recette.** Elle exécute les images **publiées et épinglées par empreinte** (`DEC-486`), de
  révision antérieure à `T1`. Elle n'a donc ni les trois rôles, ni cette route. Il faut republier puis
  `make images-pin`. **Avant `G3`**, comme la passation §9.4 le dit déjà ;
- **la page qui consomme le lien.** `/connexion/lien` est une **dérivation déclarée**, en un seul
  endroit du code, et `T4` comme `T11` doivent employer la même constante.

---

## 13. Ce que `T4` devra savoir

1. **Le chemin et le paramètre sont des constantes, en un seul endroit** :
   `CHEMIN_DE_CONSOMMATION = "/connexion/lien"` et `PARAMETRE_DE_JETON = "token"` dans
   `app/auth/services.py`. Les recopier créerait deux valeurs qui divergeraient, et le lien
   enverrait sur une page absente.
2. **`empreinte_de_jeton` est la seule façon de retrouver une ligne** depuis un jeton reçu. La base ne
   porte **que** l'empreinte, et un jeton n'est jamais comparable directement.
3. **Le préfixe `oml_` est reconnu par les deux détecteurs**, et `oss_` est **déjà réservé** pour les
   sessions de `T6` : il n'y a rien à ajouter au filtre de masquage ni à `.gitleaks.toml`. Mais
   **éprouve-le** : une règle déclarée et jamais exercée est une règle dont on ne sait pas si elle
   marche.
4. **Le critère « aucun lien complet dans les journaux » est déjà à moitié acquis** : `make
   magic-link-check` vérifie l'absence de `oml_` dans les journaux du conteneur, et neuf tests de
   masquage éprouvent les trois barrières sur les formes que **ce projet** produit. `T4` doit y ajouter
   ce que **la consommation** produit — une URL reçue, pas seulement une URL émise.
5. **Le temps s'injecte.** `demander_un_magic_link` reçoit son `instant` ; fais de même, et n'écris
   aucun test qui dorme. La borne de quinze minutes est vérifiée par **égalité**, pas par intervalle :
   la contrainte en base l'exige.
6. **`make magic-link-check` nettoie ce qu'il crée, base ET Mailpit.** Si tu l'étends, garde cette
   propriété : trois tests de `T2` ont échoué faute d'elle, et un contrôle qui pollue son
   environnement finit par casser ceux des autres.
