# Fiche du LOT 3 — Authentification, sessions et sécurité applicative

**Porte de validation :** `G3` · **Tag prévu :** `v0.3.0`
**Ouvert par Jonathan le :** 20 août 2026 — décision `DEC-518`
**Rédigée le :** 20 août 2026, à la sortie de la porte `G2`
**Statut de cette fiche :** **découpage VALIDÉ par Jonathan le 20/08/2026** — « tout me convient »
**Traçabilité GitHub :** epic `#62`, jalon `G3`, huit stories `#63` à `#70`

> **Aucune ligne de code de ce lot n'est écrite avant que tu n'aies validé le §3.** C'est la règle qui
> a produit le LOT 2 en deux temps : ouverture du lot le 18/08, découpage validé le même jour, et
> douze sous-étapes ensuite.

---

## 1. Ce que ce lot doit produire

**L'accès sécurisé des employés et des administrateurs**, selon les règles déjà validées — le cahier,
la matrice des rôles et le modèle §10. Rien n'est à inventer : les sept tables, les durées, les
formats de cookie et les événements d'audit sont **écrits**.

**Ce qui change de nature par rapport au LOT 2.** Les onze sous-étapes du LOT 2 ne produisaient
**aucun accès extérieur** : ni écran, ni route métier, ni authentification. Ce lot ouvre la porte, et
tout ce qui était théorique devient réel — c'est le motif de l'arbitrage du §3.1.

---

## 2. Les huit stories du backlog `MVP-L03`

| ID | Priorité | Story | Sous-étape | Issue |
|---|:--:|---|---|---|
| `MVP-L03-US001` | `P0` | demander un magic link **sans révéler l'existence du compte** | `T3` | `#63` |
| `MVP-L03-US002` | `P0` | consommer un magic link **à usage unique** | `T4` | `#64` |
| `MVP-L03-US003` | `P0` | se connecter avec un **compte administrateur local** | `T5` | `#65` |
| `MVP-L03-US004` | `P0` | **session sécurisée** et déconnexion | `T6` | `#66` |
| `MVP-L03-US005` | `P0` | protéger les écritures contre **CSRF et doubles soumissions** | `T7` | `#67` |
| `MVP-L03-US006` | `P0` | **révoquer immédiatement** les accès au départ | `T9` | `#68` |
| `MVP-L03-US007` | `P1` | **compte de service** à périmètre minimal | `T10` | `#69` |
| `MVP-L03-US008` | `P0` | **auditer** les événements d'authentification | `T12` | `#70` |

**Sept `P0` et une `P1`**, comme au LOT 2.

---

## 3. Découpage proposé — **c'est ce que tu valides**

| | Sous-étape | Story | Ce qui prouvera qu'elle est finie |
|:--:|---|---|---|
| ~~**`T1`**~~ | ~~**Moindre privilège PostgreSQL — deux rôles.**~~ **TERMINÉE le 20/08/2026.** **`QO-116` CLOSE** (`DEC-520`). **TROIS comptes et non deux** : `initdb` crée un superutilisateur, rien ne peut l'empêcher — ce qui change, c'est que l'application ne l'emploie plus. **`btree_gist` est `trusted`**, mesuré, ce qui rend la migration `0002` applicable sans superutilisateur. **`REASSIGN OWNED` a échoué** : 188 des 196 fonctions appartiennent à l'extension, et une extension n'a pas d'`ALTER … OWNER TO` — transfert explicite et **filtré**, 19 tables et 8 fonctions. Les **privilèges par défaut** couvrent les tables futures. **Tout rejoué sur une base recréée de zéro** : 8 services sains, 11 migrations, **390 tests**. Compte rendu : [`compte-rendu-t1-lot-3.md`](compte-rendu-t1-lot-3.md) | — | ☑ |
| **`T2`** | **Les sept tables du modèle §10**, migration `0012`. `user_account`, `admin_password_credential`, `magic_link_request`, `user_session`, `service_account`, `service_token`, `auth_event`. | toutes | Migration éprouvée en montée, descente et remontée · `make migrations-check` compare le schéma · **aucun mot de passe ni jeton en clair** dans une colonne, vérifié par contrôle |
| **`T3`** | **Magic link — la demande.** Réponse **générique** quelle que soit l'existence de l'adresse, domaine autorisé configurable, profil actif exigé. | `US001` | La réponse et le **code HTTP** sont **identiques** pour une adresse connue et inconnue — deux tests, et la comparaison porte sur le corps **et** l'en-tête · un profil **archivé** ne reçoit rien (§30.11) · Mailpit capte le message |
| **`T4`** | **Magic link — la consommation.** Usage unique, expiration à 15 minutes, le dernier lien invalide les précédents. | `US002` | Un second usage **échoue** · un lien de 16 minutes échoue · émettre un nouveau lien invalide l'ancien · **aucun lien complet dans les journaux**, prouvé par un contrôle sur les barrières de masquage |
| **`T5`** | **Compte administrateur local.** Hachage, paramètres stockés, verrouillage après échecs, `must_change`. | `US003` | Le mot de passe n'est **jamais** stocké en clair ni journalisé · le verrouillage se déclenche et se relâche · l'algorithme et ses paramètres sont **en base**, pour pouvoir migrer sans casser les comptes |
| **`T6`** | **Sessions.** Cookie `HttpOnly`, `Secure`, `SameSite` ; inactivité **7 jours**, durée absolue **30 jours** ; déconnexion. | `US004` | Les trois attributs sont sur la réponse **réelle**, lue à travers Caddy en HTTPS · les deux expirations sont éprouvées · **aucun jeton dans `localStorage`**, prouvé par un contrôle du frontend |
| **`T7`** | **CSRF et idempotence.** Les écritures sensibles exigent la protection ; les clés d'idempotence empêchent les effets multiples. | `US005` | Une écriture sans jeton CSRF est **refusée**, avec témoin · une même clé d'idempotence rejouée ne produit **qu'un** effet (§30.19 partiellement) |
| **`T8`** | **Limitation de débit.** Sur la demande de magic link et sur la connexion administrateur. | `US001`, `US003` | Les limites **produisent les résultats attendus** — critère de sortie littéral · la valeur minimisée `request_origin_hash` du §10.3 est employée, jamais une adresse IP brute |
| **`T9`** | **Révocation au départ.** L'archivage d'un collaborateur invalide sessions, invitations et futurs magic links **dans la même action métier**. | `US006` | La révocation est **atomique** avec l'archivage · §30.22 devient **acquis** · une session révoquée ne répond plus, mesuré |
| **`T10`** | **Comptes de service et scopes.** Jeton révocable, expirant, borné à des scopes. | `US007` (`P1`) | Un jeton hors scope est **refusé** · l'expiration est effective · chaque appel est audité |
| **`T11`** | **Les écrans d'authentification.** Page de connexion, confirmation de demande, lien expiré ou consommé, connexion administrateur, déconnexion, `403`, `404`, erreur générale. | — | Les **huit** pages existent et sont servies à travers Caddy · accessibilité vérifiée par `jsx-a11y` **et** contraste mesuré · aucune couleur hors des jetons de `packages/ui` |
| **`T12`** | **Audit des événements, recette et checklist `G3`.** Les **sept** types d'événements du §10.6. | `US008` | Les 7 types sont tracés, **sans mot de passe ni lien complet** · `make recette-modele-check` reclasse `§30.11`, `§30.22` et le résiduel de `§30.4` · les **6** critères de sortie prouvés |

**Douze sous-étapes, comme le LOT 2.** Une pull request par sous-étape, un compte rendu, et une
validation de ta part avant de passer à la suivante.

### 3.1 Pourquoi `T1` est en premier, et ce que cela coûte

**C'est ton arbitrage du 20/08/2026**, tracé par `DEC-518`. Le registre de `QO-116` le disait depuis
`T1` du LOT 2 : « plus on attend, plus de lots auront été écrits en supposant ce compte ». Le LOT 3
est **celui qui introduit l'accès extérieur** — donc celui où l'exposition cesse d'être théorique.

**Le coût est nommé, pas minimisé.** La façon dont la plateforme se connecte à sa base change. Il
faudra reprouver que tout démarre, que les migrations s'appliquent et que les 373 tests passent — **et
sur une base recréée de zéro**, non sur celle qui tourne. C'est le §7.16 : *ce qui n'a jamais tourné
ailleurs n'est pas éprouvé*.

**Et un piège prévisible, à traiter dès `T1`.** Deux rôles signifient deux jeux d'identifiants, donc
**deux variables de plus** dans `.env.example` — or `make env` **ne réconcilie jamais** un `.env`
existant, c'est `ECART-022`. `make env-check` sera la parade, et il est déjà dans `make check`.

---

## 4. Ce que le LOT 2 laisse à ce lot, nommément

| Dette | Où elle est écrite |
|---|---|
| **`QO-116`** — compte superutilisateur contre le moindre privilège | `T1`, ci-dessus |
| **La vérification « ESM ou super-administrateur » de l'attributeur** du §8.4 | `T11` du LOT 2 l'a laissée : la base n'a **aucune notion de l'appelant**, et `attribuer_la_categorie_dg` reçoit déjà l'attributeur en paramètre. Il ne reste qu'à vérifier son droit — **rattachée à `T5`**, où les rôles d'administration existeront |
| **`§30.11`** — « un profil archivé ne reçoit pas de magic link » | reporté au LOT 3 par `make recette-modele-check`. **`T3`** |
| **`§30.22`** — « le départ révoque immédiatement les sessions et rôles » | reporté au LOT 3. **`T9`** |

**Le contrôle de recette du modèle échouera** si ces classements ne sont pas mis à jour : il exige que
chacun des 25 contrôles du §30 soit classé, et qu'un « acquis » nomme un test qui **existe**.

---

## 5. Les cinq garde-fous déjà en place qui vont enfin servir

Ce lot est le premier à **exercer** des garde-fous posés au LOT 1 et jamais éprouvés en vrai :

1. **`SESSION_COOKIE_SECURE=true` et `CSRF_PROTECTION_ENABLED=true`** sont deux des sept garde-fous de
   production du cahier §20.3, testés depuis `T3` du LOT 1 — mais **rien ne les consommait**. `T6` et
   `T7` les rendront effectifs ;
2. **L'origine unique de `DEC-470`** — la page et l'API sont servies par le même hôte, sans CORS —
   existe **précisément** pour que les cookies `Secure` et `SameSite` soient éprouvables. Ne remets pas
   ce montage en cause ;
3. **Les trois barrières de masquage** de `packages/observabilite` devront recevoir les **formats
   réellement produits par ce lot** : jeton de magic link, jeton de session, jeton de service. La
   leçon de `T4-1` est explicite — un test de filtre doit énumérer les formes **que ce projet
   produit**, pas des exemples de documentation ;
4. **`DEC-469`** interdit déjà de journaliser la chaîne de requête et les arguments de job. Un magic
   link arrive **dans une URL** : c'est exactement le cas que cette décision anticipait ;
5. **Gitleaks** examine chaque pull request avec des règles taillées sur les formats de ce projet. Un
   nouveau format de jeton **devra y être ajouté**, sinon la règle ne le verrait pas.

---

## 6. Tests à écrire

| Famille | Nature | Où |
|---|---|---|
| Contraintes des sept tables | **intégration, PostgreSQL réel** | `apps/api/tests/` |
| Réponse générique anti-énumération | **intégration** — comparaison du corps **et** du code, deux adresses | `apps/api/tests/` |
| Usage unique, expiration, invalidation | **intégration** — le temps est **injecté**, jamais attendu | `apps/api/tests/` |
| Hachage et verrouillage | **intégration**, avec témoin qui respecte la règle | `apps/api/tests/` |
| Attributs de cookie | **intégration à travers Caddy**, sur la réponse réelle | `apps/api/tests/` |
| Masquage des jetons | **unitaire**, sur les formats que ce projet produit | `packages/observabilite/` |
| Écrans | **Vitest et Testing Library**, plus `jsx-a11y` | `apps/web/` |
| Absence de jeton en `localStorage` | **contrôle**, pas une relecture | `infra/scripts/` |

> **Le temps ne s'attend pas, il s'injecte.** Un test qui dormirait 15 minutes pour éprouver
> l'expiration d'un magic link serait inutilisable en intégration continue. Les horodatages seront
> passés en paramètre, et un test vérifiera que la borne est bien **15 minutes** et non une valeur
> approchée.

---

## 7. Risques propres au lot

| Risque | Nature | Parade proposée |
|---|---|---|
| **`T1` change la connexion à la base et casse tout** | technique | l'éprouver sur une base **recréée de zéro**, et exiger un **témoin** : le rôle d'exécution doit **échouer** sur un `CREATE TABLE` |
| **Un magic link fuit dans un journal ou un message d'erreur** | **sécurité** | les trois barrières de masquage reçoivent les nouveaux formats, avec un test par format · `DEC-469` interdit déjà la chaîne de requête |
| **La réponse anti-énumération diverge par un détail** — un temps de réponse, un en-tête | **sécurité** | comparer le **corps et les en-têtes** de deux réponses, pas seulement le code HTTP |
| **Un contournement d'authentification « le temps de tester »** | **interdit absolu** | règle 6 du projet, et le §11 ci-dessous |
| **Les écrans de `T11` réclament la charte** | produit | **`QO-115` est close** (`DEC-519`) : les jetons de `packages/ui` font référence, et ils sont mesurés contre WCAG 2.2 AA |
| **Le verrouillage administrateur bloque Jonathan lui-même** | exploitation | prévoir et **documenter** le déverrouillage local, et l'éprouver |

---

## 8. Décisions encore nécessaires — **aucune n'est bloquante pour `T1`**

Elles seront instruites à leur sous-étape, et **rien ne sera inventé** — §6.5 :

| Sujet | Ce que le corpus dit, et ce qu'il ne dit pas | Quand |
|---|---|---|
| **Algorithme de hachage** du mot de passe administrateur | le §10.2 exige `algorithm` et `parameters` **en colonnes**, sans nommer d'algorithme | `T5` |
| **Valeurs des limites de débit** | le cahier exige une limitation, sans donner de seuil | `T8` |
| **Durée maximale d'un jeton de service** | le §10.5 dit « configurable **avant** leur création réelle » | `T10` |
| **Liste des scopes** | aucun document n'en énumère | `T10` |

---

## 9. Critères de sortie de la porte `G3`, littéralement

| | Critère | Sous-étape qui le prouvera |
|:--:|---|---|
| ☐ | tous les scénarios autorisés et refusés sont testés | `T3` à `T10` |
| ☐ | **aucun jeton n'est stocké dans `localStorage`** | `T6`, **par un contrôle** |
| ☐ | aucune adresse absente de la base ne peut se connecter | `T3` |
| ☐ | **les magic links ne figurent pas dans les logs** | `T4`, **par un contrôle** |
| ☐ | les limites de débit produisent les résultats attendus | `T8` |
| ☐ | **Jonathan valide l'authentification** | la porte |

Et les critères du backlog : les **sept** `P0` sont `Done`, la `P1` est terminée **ou** a fait l'objet
d'un arbitrage explicite, la démonstration est présentée, et Jonathan valide **explicitement** `G3`.

---

## 10. Démonstration attendue à la porte, telle que la roadmap l'énumère

1. demande d'un magic link pour une personne active ;
2. réception dans Mailpit ;
3. connexion avec le lien ;
4. **rejet d'un second usage** ;
5. **refus d'une adresse absente de la base** ;
6. **révocation d'une session après archivage** du collaborateur ;
7. **verrouillage après échecs administrateur répétés**.

---

## 11. Ce que ce lot ne doit pas faire

- **aucun contournement de l'authentification**, à aucun moment, même en développement, même « le
  temps d'un test » — règle 6 du projet, et le cahier l'écrit deux fois ;
- **aucun jeton en clair** en base, en journal, en audit, ou dans un message d'erreur ;
- **aucun mot de passe** stocké autrement que haché, et **aucun historique réversible** — §10.2 ;
- **aucun jeton dans `localStorage`** ni dans le stockage de session du navigateur ;
- **aucun écran ni route métier** au-delà des huit pages d'authentification du §3 : le portail est le
  LOT 4, les collaborateurs le LOT 5 ;
- **aucune table d'un lot postérieur** « pendant qu'on y est » — les contenus, les événements et les
  imports ont leurs lots ;
- **ni Entra ID, ni Graph, ni Teams, ni MFA** : le cahier les écarte explicitement du MVP ;
- **aucune donnée réelle de collaborateur**, aucun CSV réel, aucune photo ;
- **aucune modification** d'une migration déjà appliquée, ni des cinq documents de cadrage.

---

**Cette fiche est un plan. Elle attend la validation de Jonathan sur le §3.**
