# Compte rendu — LOT 3, sous-étape `T7`

**CSRF et idempotence**
**Story :** `MVP-L03-US005`, issue `#67`
**Réalisée le :** 21 août 2026
**Décisions produites :** `DEC-531`, `DEC-532`
**Migration produite :** **aucune**

---

## 1. Deux questions que le corpus ne tranchait pas, et pourquoi elles se posaient

**Trois écritures précèdent toute session** — demander un lien, le consommer, se connecter en
administrateur. Un jeton anti-CSRF suppose une session pour le délivrer : elles ne peuvent pas en
exiger un. Ton arbitrage : **vérifier l'origine**.

**Et le modèle ne déclare de clé d'idempotence que sur `async_job`** (§20.1), une table du **LOT 11**.
Les six opérations que le cahier §18.6 veut idempotentes — invitations, imports, création d'entité,
purge, exports, opérations en masse — **n'existent aucune**. Ton arbitrage : un **mécanisme court
adossé à Redis**, sans inventer de table.

Les deux options écartées méritent d'être nommées : un jeton délivré d'avance à tout visiteur
aurait obligé le frontend à un aller-retour avant tout formulaire de connexion, et une nouvelle
table aurait laissé au LOT 11 **deux mécanismes à réconcilier**.

---

## 2. Deux barrières, et leur portée diffère

| Barrière | Portée | Ce qu'elle apporte |
|---|---|---|
| en-tête `Origin` | **les cinq** écritures | le navigateur le pose **lui-même**, aucun script ne peut le falsifier |
| jeton lié à la session | celles qui ont une session — **une seule** | ferme le cas d'un sous-domaine compromis, que `SameSite` ne voit pas |

**Pourquoi `SameSite=lax` ne suffit pas, et c'est le §7.4 qui le dit** : il énumère `SameSite` **et**
« protection CSRF » dans la même liste. `lax` laisse passer une navigation de haut niveau, et il
raisonne par **site** — non par origine — donc il ne protège pas d'un sous-domaine compromis. La
vérification d'`Origin` compare l'**origine exacte**.

**Une origine absente n'est pas refusée, et c'est un choix déclaré.** Son absence signale un appel
**hors navigateur** ; la refuser casserait `curl`, les sondes et `make api-check` — et n'apporterait
rien, le CSRF employant le navigateur d'une victime. Ce qui couvre ce cas est l'**authentification**.

**Le jeton est dérivé de la session par HMAC, jamais stocké.** Trois conséquences, et la troisième
est le motif : rien de nouveau en base — le modèle ne déclare aucune table de jeton CSRF ; il est
vérifiable **sans état** ; et **un jeton volé sans le cookie ne sert à rien**. Un test l'éprouve avec
le jeton d'une **autre** session.

**`403` et non `401`** : `401` signifie « authentifie-toi », ce qui est faux — une session valide peut
accompagner une requête CSRF refusée. `403` dit « je sais qui tu es, et je refuse cette requête-là ».

---

## 3. Le résiduel que `T6` m'avait laissé, et que je nomme plutôt que de le fermer

`GET …/auth/session` **écrit** — elle rafraîchit `last_activity_at` — et n'exige **aucun** jeton.
Trois raisons, et la première suffit :

1. **c'est elle qui DÉLIVRE le jeton.** L'exiger serait circulaire : un frontend qui vient de
   recharger n'en a pas encore ;
2. son effet porte sur la session de l'appelant **lui-même** : un site tiers qui la déclencherait ne
   prolongerait que la session de sa victime ;
3. c'est un `GET`, et `T7` protège les méthodes qui modifient. Qu'un `GET` écrive est une entorse
   assumée, et `T6` l'avait déjà nommée.

**À réexaminer au LOT 4** : si le rafraîchissement passe sur chaque requête métier, ce point
disparaît.

---

## 4. L'idempotence : ce qui est couvert, et ce qui ne l'est pas

| | |
|---|---|
| **couvert** | la **double soumission**, sur une fenêtre de quelques heures |
| **non couvert** | l'idempotence **durable** des six opérations du §18.6, qui restera portée par `async_job.idempotency_key` au **LOT 11** |

**Le dire est le point.** Redis n'est pas durable : un redémarrage efface les clés, et un rejeu
ultérieur produirait un second effet. C'est acceptable pour un double clic — dont la fenêtre est de
quelques secondes — et ce ne le serait pas pour un import.

**`SET … NX EX` est atomique** — quatrième occurrence du patron dans ce lot après `T4`, `T5` et `T6`.
Lire puis écrire laisserait deux requêtes simultanées produire leur effet **toutes les deux**, ce que
cette protection doit précisément empêcher.

**Trois choix qui méritent leur ligne :**

- **l'en-tête est optionnel**, parce qu'aucune route de ce lot n'est dans la liste du §18.6 :
  l'exiger serait exiger plus que le cahier. Le critère de `US005` porte sur ce qui se passe **quand
  une clé est fournie** ;
- **une clé est REFUSÉE, jamais nettoyée.** Nettoyer ferait que deux clés différentes deviendraient
  la même, et deux opérations distinctes se bloqueraient l'une l'autre ;
- **elle est libérée quand l'effet échoue**, sans quoi un client qui recommence après une erreur —
  ce qu'on attend de lui — serait refusé six heures sans rien avoir obtenu.

---

## 5. `APP_SECRET_KEY` devient obligatoire partout, et le garde-fou l'a prouvé

Elle n'était obligatoire **qu'en production**. `T7` la consomme **sans repli** : `jeton_pour` lève
sur une clé vide, car il n'existe pas de jeton « dégradé » qui aurait un sens.

Sans ce garde-fou, une API démarrée en développement avec une clé vide rendrait **500 à la première
connexion** — le défaut se manifesterait loin de sa cause.

**Et le garde-fou a immédiatement servi** : quatre tests de migration ont échoué parce que la
variable ne traversait pas la frontière de processus vers le sous-processus Alembic. **C'est la leçon
de `T1` rejouée**, et le message la nommait — ce qui a rendu les quatre échecs diagnosticables en une
lecture.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **585 tests, 0 échec** — 550 avant `T7` |
| — et **zéro résidu** mesuré | `person` 0, `user_session` 0, `entity` 0 |
| `make check` · `make audit` | **0** · **0** |
| **`make csrf-check`** | **0 — 10 contrôles**, à travers Caddy en HTTPS |
| `sessions-check` · `sessions-temoin` | **0** · **0** — après correction, voir §7 |
| `magic-link-check` · `admin-check` | **0** · **0** |
| 12 autres contrôles | tous à **0** |

**Ce que `make csrf-check` prouve, en dix contrôles :**

```text
les 5 ecritures sont refusees (403) depuis une origine etrangere
un seul gabarit de refus, hors identifiant de correlation
TEMOIN — les 3 memes ecritures passent depuis la bonne origine
sans `Origin` : accepte (202) — choix declare
deconnexion — 403 sans jeton, 200 avec, session revoquee
un jeton d'une AUTRE session est refuse (403)
meme cle rejouee — 1 SEUL lien en base, meme reponse
TEMOIN — sans cle, 2 liens dont 1 actif (§10.3)
cle malformee — 422, ne depend QUE de la requete
la route de session n'exige aucun jeton — RESIDUEL NOMME
```

**Le second témoin est celui qu'on oublie.** Sans lui, l'assertion « un seul lien » serait vraie pour
une raison **étrangère** à l'idempotence — par exemple si la route n'émettait jamais de lien. Deux
demandes **sans** clé doivent donc produire **deux** liens, dont un invalidé.

**Les 34 tests nouveaux** couvrent l'origine, le jeton, les clés, et les protections sur les routes
réelles.

---

## 7. Deux défauts, et cinq contrôles antérieurs rendus faux

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T7-1` | Mon insertion des blocs `403` s'est placée **après** la fermeture du dictionnaire `responses`, puis il manquait une virgule | `ruff`, deux fois de suite |
| `T7-2` | Mon témoin incluait la **déconnexion** dans les écritures qui doivent passer avec la bonne origine — elle a échoué sur `assert 403 != 403`, **et elle avait raison** : une session existait, donc le jeton était exigé | `uv run pytest` |

**Et huit tests antérieurs ont échoué, tous légitimement :**

| Famille | Cause |
|---|---|
| 2 tests de `test_configuration.py` | `APP_SECRET_KEY=""` était listée comme « n'échoue pas en développement ». **C'est désormais faux par conception** |
| 4 tests de `test_integration.py` | la variable ne traversait pas la frontière de processus vers Alembic — **la leçon de `T1`** |
| 2 tests de `test_sessions.py` | la déconnexion exige désormais un jeton |
| `make sessions-check` | même cause, et 4 de ses contrôles ont échoué |

**Aucun n'était négligent** : tous étaient justes **à leur date**. C'est le §7.21, et c'est la
sous-étape du lot où il s'est manifesté le plus largement — parce que `T7` ne change pas une table
mais **une règle qui traverse toutes les écritures**.

> **Une variante à ajouter au §7.21 :** *quand une sous-étape ajoute une CONDITION à une opération
> existante, tous les contrôles qui exerçaient cette opération deviennent faux — et ils échouent
> ailleurs que là où la condition a été ajoutée.* Les quatre tests de migration n'ont rien à voir
> avec le CSRF ; ils ont échoué parce qu'une variable est devenue obligatoire.

---

## 8. Ce qui n'est PAS couvert

- **la limitation de débit.** `T8`, et c'est la prochaine ;
- **l'idempotence durable** des six opérations du §18.6. `LOT 11`, sur `async_job.idempotency_key` ;
- **la protection CSRF des routes métier.** Elles n'existent pas encore ; le mécanisme les attend, et
  la seule écriture qui exige aujourd'hui un jeton est la déconnexion ;
- **`GET …/auth/session`.** Résiduel nommé, à réexaminer au LOT 4 ;
- **un `Origin` absent.** Choix déclaré : le CSRF est une attaque de navigateur ;
- **la recette.** Images publiées de révision antérieure à `T1`. À republier avant `G3`.

---

## 9. Ce que `T8` devra savoir

1. **`request_origin_hash` est renseignée depuis `T3`**, par HMAC de la dernière entrée de
   `X-Forwarded-For`. `T8` en a besoin, et **la limite de confiance est écrite** dans
   `origine_de_la_requete` : la valeur ne vaut que si l'API n'est joignable que par un mandataire de
   confiance. **Réexamine ce point** — c'était noté pour toi dès `T3`.
2. **Les deux seuils du §20.2 que `T8` doit porter sont écrits** : « 10 demandes de magic link par
   adresse et par heure : limitation » et « 50 demandes depuis une même origine en une heure :
   alerte ». `.env.example` les déclare déjà —
   `MAGIC_LINK_MAX_PER_EMAIL_PER_HOUR` et `MAGIC_LINK_MAX_PER_ORIGIN_PER_HOUR`. **Vérifie avant de
   dériver** : `T6` a failli inventer une valeur déjà tranchée.
3. **Le §20.2 distingue « limitation » et « alerte »**, et les deux mots ne veulent pas dire la même
   chose. Une alerte suppose `operational_alert` du §21.2 — **LOT 10**. Ne confonds pas.
4. **Une adresse SANS compte ne fait avancer aucun compteur d'échecs** — il vit sur `user_account`.
   C'est la limitation par **origine** qui couvre ce cas, et elle est à toi.
5. **Redis est déjà employé** par l'idempotence de `T7`, avec un préfixe d'espace de noms
   (`onboarding:idempotence:`) parce qu'il sert aussi de courtier Dramatiq. Emploie ton propre
   préfixe.
6. **Le compare-et-pose a servi quatre fois** — `T4`, `T5`, `T6`, `T7`. Un compteur de débit est le
   cinquième cas : `INCR` avec `EXPIRE` est atomique côté Redis, et lire-puis-écrire ne l'est pas.
   **Éprouve-le sous concurrence** ; les tests séquentiels y sont aveugles, mesuré quatre fois.
7. **`auth_event` grossit d'une ligne par tentative**, y compris sur adresse inconnue et jeton
   inconnu. C'est voulu — un échec doit être traçable — mais c'est une surface de saturation que
   `T8` doit borner.
