# Compte rendu — LOT 3, sous-étape `T4`

**La consommation d'un magic link, une fois et une seule**
**Story :** `MVP-L03-US002`, issue `#64`
**Réalisée le :** 21 août 2026
**Décisions produites :** `DEC-524`, `DEC-525`
**Migration produite :** **aucune**

---

## 1. L'usage unique est une COURSE, pas une vérification

`T2` du LOT 3 avait annoncé le sujet : « l'usage unique est une règle de **processus** : `used_at`
ne se pose qu'une fois, ce qu'aucune contrainte de ligne n'exprime ». C'est vrai, et cela ne dit pas
encore **comment** le porter.

**Lire puis écrire ne suffit pas.** Deux requêtes concurrentes portant le même jeton liraient toutes
deux `used_at IS NULL` et poursuivraient : le lien serait consommé **deux fois**, et un lien de
connexion rejouable est un **contournement d'authentification**.

La consommation est donc un **compare-et-pose atomique** — un seul `UPDATE` conditionnel dont le
nombre de lignes affectées **est** le verdict :

```sql
UPDATE magic_link_request SET used_at = :instant_usage
WHERE token_hash = :empreinte
  AND used_at IS NULL              -- usage unique
  AND invalidated_at IS NULL       -- « le dernier lien invalide les precedents »
  AND expires_at > :instant_expiration   -- « 15 minutes apres emission »
RETURNING person_id
```

Toutes les conditions sont dans la clause `WHERE`. Les évaluer avant, dans un `SELECT` séparé,
ouvrirait exactement la fenêtre que cette forme ferme.

---

## 2. Le test de concurrence : trois versions, et les deux premières ne prouvaient RIEN

**C'est le passage le plus instructif de la sous-étape, et il a coûté trois essais.**

| Version | Ce qu'elle faisait | Pourquoi elle ne prouvait rien |
|---|---|---|
| 1 | validait `A` **avant** de lancer `B` | purement **séquentielle** : équivalente au test « un second usage échoue », qu'un autre test couvre déjà |
| 2 | bornait `B` par un `lock_timeout` court et exigeait qu'elle échoue sur le verrou | **ne discriminait pas** : un service qui lit puis écrit prend le **même** verrou au moment d'écrire, donc il aurait produit **la même observation** |
| 3 | `B` **attend** le verrou, `A` valide, `B` **reprend** | c'est là que les deux implémentations divergent |

La version 2 est la quatrième proposition du §7.0 dans sa forme la plus pure : *un contrôle dont
l'échec produirait la même observation que le succès ne prouve rien.* J'avais raisonné sur le verrou
sans me demander ce que produirait l'implémentation fautive.

**Ce qui discrimine :**

```text
1. A consomme, tient le verrou, NE VALIDE PAS
2. B, dans un fil, tente de consommer -> elle ATTEND
3. A valide. B reprend :
     compare-et-pose  -> la clause WHERE est reevaluee APRES l'obtention du
                         verrou, `used_at` n'est plus nul, 0 ligne -> REFUS
     lire-puis-ecrire -> la lecture avait deja conclu « eligible », et
                         l'ecriture n'a plus de garde -> SUCCES, double consommation
4. TEMOIN : sur un AUTRE lien, non verrouille, B reussit
```

**Aucune attente arbitraire.** La barrière de l'étape 2 n'est pas un `sleep` : une troisième
connexion interroge `pg_blocking_pids()` jusqu'à voir un backend réellement bloqué par un autre.
C'est une **condition observée**, pas un délai espéré.

**Et le témoin négatif est décisif :**

```text
implementation lire-puis-ecrire :
  test de concurrence        -> ECHEC  « B A AUSSI CONSOMME LE LIEN »
                                       assert 'lien_consomme' == 'lien_refuse'
  test « second usage »      -> passe
  test « quatre causes »     -> passe

implementation compare-et-pose :
  test de concurrence        -> passe, 6 executions sur 6, ~0,35 s
```

**Les deux autres tests passent sur l'implémentation vulnérable.** Ils ne couvrent donc pas cette
propriété, et sans le test concurrent la faille aurait été invisible.

---

## 3. Le jeton voyage dans le CORPS, jamais dans l'URL

Trois canaux de fuite qu'une chaîne de requête ouvre et que **nos** journaux ne contrôlent pas :

| Canal | Pourquoi `DEC-469` n'y suffit pas |
|---|---|
| l'historique du navigateur | il n'est pas à nous |
| l'en-tête `Referer` | il part vers d'autres origines |
| le journal d'accès d'un mandataire | `DEC-469` protège nos journaux, pas ceux d'autrui |

`POST …/auth/magic-link/consommation`, jeton **en corps**. Le lien de l'e-mail porte bien le jeton
en query string — il ouvre une page du frontend — mais **la fenêtre d'exposition s'arrête au
navigateur du destinataire**, et `T11` devra la refermer par un `Referrer-Policy`.

---

## 4. Un seul gabarit de refus, et la dérivation est écrite

Jeton inconnu, expiré, déjà consommé, invalidé par un lien plus récent : les **quatre** rendent le
même `400`, le même corps, les mêmes en-têtes.

**Ce n'est pas une précaution vague.** Le §3 de la fiche du lot énumère les huit écrans de `T11` et
n'en prévoit **qu'UN** pour « lien expiré **ou** consommé » : l'API n'a pas à distinguer ce que
l'interface ne distingue pas.

**Et le contrôle de cette égalité a trouvé une divergence réelle** — 289 octets contre 289, même
longueur, contenu différent. La cause : le corps d'erreur porte l'`identifiant_correlation` du
§18.3, qui **doit** varier. Le comparateur le neutralise, le **nomme**, et **exige qu'il varie** :
s'il était identique, la corrélation du §28.1 serait cassée, et l'avoir neutralisé aurait masqué ce
défaut-là.

---

## 5. La borne des quinze minutes est semi-ouverte, et c'est déclaré

Le §10.3 écrit « 15 minutes après émission » sans trancher l'inclusion. La convention du socle —
plages semi-ouvertes `[début, fin)` — est appliquée. **Trois tests la bornent** :

| Instant | Verdict |
|---|---|
| 14 minutes | **accepté** — le témoin : la borne ne doit pas être plus stricte que le modèle |
| 15 minutes pile | **refusé** |
| 16 minutes | **refusé** |

Le temps est **injecté**. Aucun test ne dort.

---

## 6. Les journaux de Caddy : une absence, transformée en absence GARDÉE

**Mesure du 21/08/2026 :** `0` occurrence d'un jeton dans les journaux de Caddy — et `0` ligne
« handled request » sur **3 171** lignes examinées.

**Ce n'est pas une protection, c'est une absence.** Le bloc global `log { format json }` configure le
journal **propre** de Caddy — API d'administration, TLS, démarrage. Les journaux d'**accès** exigent
une directive `log` **dans un bloc de site**, et il n'y en a aucune.

Or le lien de l'e-mail porte le jeton dans la query string d'une page **servie par Caddy**. Le jour
où quelqu'un ajoutera un journal d'accès — et le cahier §28 rend la chose plausible — `request.uri`
y porterait le jeton, et **rien ne le signalerait**. C'est le §7.23 : *un état dormant ne se voit pas
dans ce qui tourne.*

`make magic-link-check` **rapporte** l'état et **échoue** si un bloc de site déclare un journal
d'accès sans filtrer la chaîne de requête. Éprouvé dans les deux sens : le témoin ajoute un bloc
`log` au `Caddyfile`, et le contrôle le nomme, ligne comprise.

---

## 7. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `uv run pytest` | **482 tests, 0 échec** — 469 avant `T4` |
| — et **zéro résidu** en base, mesuré après purge et suite complète | `auth_event` 0, `person` 0, Mailpit 0 |
| `make check` · `make audit` | **0** · **0** |
| **`make magic-link-check`** | **0 — 15 contrôles**, contre 10 en `T3` |
| Test de concurrence, 6 exécutions | **6 passages**, ~0,35 s |
| — témoin négatif, implémentation lire-puis-écrire | **échec sur l'assertion qui discrimine** |
| — témoin du garde-fou `Caddyfile` | **détecte** un journal d'accès non filtré, ligne nommée |
| `code-check` · `api-check` · `stack-check` · `web-check` | 0 · 0 · 0 · 0 |
| 8 contrôles de schéma | tous à **0** |
| `recette-modele-check` | **0 — 11 acquis** (inchangé : `T4` ne clôt aucun contrôle du §30) |

**Les 13 tests nouveaux** couvrent l'usage unique, les trois bornes d'expiration, l'invalidation, le
jeton inconnu, le jeton fantaisiste, l'égalité des quatre refus, l'atomicité sous concurrence, et
trois propriétés d'audit.

---

## 8. Cinq défauts, tous dans mon travail

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T4-1` | Mon test de concurrence **validait `A` avant de lancer `B`** — séquentiel — et son commentaire affirmait le contraire du code | relecture du code que je venais d'écrire, après l'avoir vu passer |
| `T4-2` | La version suivante, bornée par un `lock_timeout` court, **ne discriminait toujours pas** : lire-puis-écrire prend le même verrou | je me suis demandé ce que produirait l'implémentation fautive — §7.0, quatrième proposition |
| `T4-3` | Ma réécriture du test avait **supprimé son bloc de nettoyage**, et les résidus ont fait échouer l'exécution suivante | `pytest` a échoué juste après une exécution du témoin, puis la base a montré 6 personnes et 6 liens résiduels |
| `T4-4` | `lock_timeout` de `B` **égal** au délai de la barrière : les deux s'affrontaient, **échec une fois sur trois**. Et ma sonde filtrait sur le **texte** de la requête, si bien qu'elle n'a jamais vu `B` alors que `B` était démontrablement bloquée | la barrière a été rendue bavarde (§7.18) et a nommé la cause : « canceling statement due to lock timeout … while updating tuple in relation `magic_link_request` » |
| `T4-5` | Mon nettoyage ne pouvait pas atteindre l'événement `LOGIN_FAILURE` du refus de `B` : `person_id` y est **nul**, donc le marqueur ne s'y applique pas | comptage du résidu après la suite complète : **1** ligne |

**Et un faux témoin, qui vaut d'être dit.** Mon premier témoin négatif a bien fait échouer le test —
mais pour une raison **incidente** : ma requête de remplissage était malformée
(`could not determine data type of parameter $1`). **Un témoin qui échoue pour la mauvaise raison ne
prouve rien du contrôle qu'il devait éprouver** — c'est la seconde leçon du §7.25, et je l'ai
rejouée. La parade a été de lire l'assertion exacte, pas le code de sortie.

**`T4-4` est la classe la plus coûteuse.** Un contrôle intermittent apprend à relancer plutôt qu'à
lire, et il aurait fini par être ignoré. La correction n'a pas été de tolérer l'instabilité mais
d'écarter les deux bornes — 10 s pour la barrière, 60 s pour le verrou — et de remplacer une sonde
fondée sur du **texte** par `pg_blocking_pids()`, qui interroge la relation de blocage elle-même.
**Quand un contrôle dépend d'un détail de présentation, il dépend de la mauvaise chose.**

**`T4-3` et `T4-5` sont la même leçon que `T3-3`, pour la troisième fois** : un test qui **valide**
sa transaction doit nettoyer, et la trace d'un refus **sans personne** échappe à tout filtre fondé
sur l'identité. La parade est une borne temporelle sur `created_at` — et non sur `occurred_at`, qui
porte l'instant **injecté** du test.

---

## 9. Ce qui n'est PAS couvert

- **la session.** Aucune, et c'est explicite dans le code : `user_session` et les trois attributs de
  cookie du cahier §7.4 relèvent de **`T6`**, `US004`. La consommation **n'authentifie encore
  personne** — elle établit qu'un porteur de jeton **est** une personne donnée, et rend son
  identifiant ;
- **`LOGIN_SUCCESS`.** Volontairement non écrit : rien n'est connecté. `T6` pourra le tracer ;
- **les cinq autres types d'événement du §10.6.** `T12` porte l'audit complet et son contrôle
  d'exhaustivité ;
- **la limitation de débit** sur la consommation. `T8`. Un jeton inconnu écrit une ligne
  `auth_event` : c'est voulu — un échec doit être traçable — mais c'est une surface de saturation à
  borner ;
- **le `Referrer-Policy` de la page qui reçoit le lien.** Le jeton est dans **son** URL ; l'empêcher
  de partir dans un en-tête `Referer` relève de **`T11`** ;
- **la recette.** Elle exécute les images publiées, de révision antérieure à `T1`. À republier avant
  `G3` — dette déjà tracée, `exploitation-locale.md` §2.4.

---

## 10. Ce que `T5` devra savoir

1. **`user_account.state`, `failed_login_count` et `admin_password_credential.must_change` portent
   des défauts CÔTÉ PYTHON**, pas `server_default`. Un `INSERT` en SQL brut ne les reçoit pas et la
   colonne `NOT NULL` refuse la ligne — c'est le défaut `T3-2`. Nomme ces colonnes, ou passe par
   l'ORM.
2. **La cinquième condition de `T3` t'attend** : un `user_account` existant et non `active` refuse le
   magic link, son **absence** ne le refuse pas. C'est par cette colonne que ton verrouillage prendra
   effet, sans une ligne de plus dans le service de demande.
3. **`_tracer_consommation` et `_tracer` sont deux fonctions distinctes** dans `services.py`, parce
   que les types d'événement diffèrent. Si `T5` en ajoute un troisième, regarde s'il vaut mieux les
   unifier — mais ne les unifie pas au prix d'un paramètre que personne ne lit.
4. **La vérification « ESM ou super-administrateur » de l'attributeur du §8.4 est rattachée à `T5`**
   par la fiche §4, et `attribuer_la_categorie_dg` reçoit déjà l'attributeur en paramètre. Il ne reste
   qu'à vérifier son droit.
5. **Le compare-et-pose atomique est un patron réutilisable.** Le verrouillage après échecs a la même
   forme de course : lire `failed_login_count`, l'incrémenter, décider — trois requêtes concurrentes
   verrouilleraient ou non selon l'ordre. Emploie un `UPDATE … RETURNING` conditionnel, et éprouve-le
   **sous concurrence** : les tests séquentiels ne voient pas cette classe de défaut, `T4` l'a mesuré.
