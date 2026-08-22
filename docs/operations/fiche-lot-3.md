# Fiche du LOT 3 — Authentification, sessions et sécurité applicative

**Porte de validation :** `G3` · **Tag prévu :** `v0.3.0`
**Ouvert par Jonathan le :** 20 août 2026 — décision `DEC-518`
**Rédigée le :** 20 août 2026, à la sortie de la porte `G2`
**Statut de cette fiche :** **découpage VALIDÉ par Jonathan le 20/08/2026** — « tout me convient »
**Avancement :** `T1` à **`T11`** terminées. **Une seule sous-étape restante**, `T12`
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
| ~~**`T2`**~~ | ~~**Les sept tables du modèle §10**, migration `0012`.~~ **TERMINÉE le 21/08/2026.** Les §25.2 à §25.4 n'imposent **aucune** contrainte à ces tables ; le §25.1 s'ouvrant par « à prévoir **notamment** », **quatre unicités de plus** sont posées, chacune **dérivée** d'une règle écrite. L'index partiel de `magic_link_request` porte l'**invariant** du §10.3, pas son action — parti de `DEC-514`. **`make secrets-check` distingue deux familles d'empreintes**, et il a d'abord échoué sur mon propre code : une empreinte argon2 est de longueur variable. **7/7 tables lisibles par le rôle d'exécution**, le point de passation de `T1`. **415 tests.** Compte rendu : [`compte-rendu-t2-lot-3.md`](compte-rendu-t2-lot-3.md) | toutes | ☑ |
| ~~**`T3`**~~ | ~~**Magic link — la demande.**~~ **TERMINÉE le 21/08/2026.** L'égalité est obtenue **en n'ayant qu'un seul gabarit de réponse**, non en comparant deux chemins de code — `202`, 143 octets, 7 en-têtes, 0 divergence entre connue, inconnue et archivée, mesuré **à travers Caddy en HTTPS**. **`§30.11` est passé de `reporte` à `acquis`** : 11 acquis contre 10. L'autorité des domaines est la **table**, pas une variable (`DEC-523`), et `make domaines-provision` pose la ligne initiale **sans jamais réactiver** un domaine coupé. Le jeton porte un **préfixe**, `oml_`, qui rend les deux détecteurs **exacts** au lieu d'heuristiques, et la famille `oss_`/`ost_` est **réservée** pour `T6` et `T10`. **`PUBLIC_BASE_URL` était fausse et n'était transmise à personne** — §7.16. **469 tests**, `make magic-link-check` **dans la CI**. Compte rendu : [`compte-rendu-t3-lot-3.md`](compte-rendu-t3-lot-3.md) | `US001` | ☑ |
| ~~**`T4`**~~ | ~~**Magic link — la consommation.**~~ **TERMINÉE le 21/08/2026.** L'usage unique est une **course**, pas une vérification : un **compare-et-pose atomique** dont le nombre de lignes affectées EST le verdict. **Trois versions du test de concurrence, et les deux premières ne prouvaient rien** — la seconde ne discriminait pas, un service lire-puis-écrire prenant le même verrou. Le témoin négatif est décisif : sur une implémentation vulnérable, le test concurrent échoue **et les deux autres passent**. **Le jeton voyage dans le CORPS, jamais dans l'URL.** Un seul gabarit de refus pour quatre causes, dérivé de l'écran unique de `T11`. **L'absence de journal d'accès Caddy est rapportée comme une absence et GARDÉE** par un contrôle. **482 tests**, `magic-link-check` passe de 10 à **15 contrôles**. Compte rendu : [`compte-rendu-t4-lot-3.md`](compte-rendu-t4-lot-3.md) | `US002` | ☑ |
| ~~**`T5`**~~ | ~~**Compte administrateur local.**~~ **TERMINÉE le 21/08/2026.** `scrypt` de la bibliothèque standard, **et le motif du choix est la MÉMOIRE** : 64 Mio par calcul contre 128 à `N = 2^17`, pour une limite de service de 1 024 Mio — huit connexions suffiraient à la saturer. **Zéro dépendance ajoutée.** Le verrouillage réutilise les **deux nombres du §20.2** plutôt que d'en inventer, **se relâche seul**, et une tentative sur un compte verrouillé **ne le prolonge pas** — sans quoi le verrouillage serait un déni de service permanent. Le compteur est un **compare-et-pose atomique**, témoin négatif à l'appui : « le compteur vaut 1 au lieu de 2 ». **La dette du §8.4 est acquittée**, et le jeu de recette a révélé une lacune de lui-même — il attribuait `dg` par un DSM et ne créait aucun ESM. **525 tests**, `make admin-check` dans la CI, **`QO-118` ouverte**. Compte rendu : [`compte-rendu-t5-lot-3.md`](compte-rendu-t5-lot-3.md) | `US003` | ☑ |
| ~~**`T6`**~~ | ~~**Sessions.**~~ **TERMINÉE le 21/08/2026.** **Rien n'était à inventer, et j'allais le faire** : `.env.example` écrit `SameSite=lax`, le nom du cookie et les deux durées depuis le LOT 0 — quatre valeurs déjà tranchées (§9.0). Le jeton **n'apparaît dans AUCUN corps** : c'est ce qui rend « aucun jeton dans `localStorage` » **structurel** plutôt que disciplinaire. Le contrôle du frontend est **exact** — il retire les commentaires, garde les chaînes — et son témoin l'éprouve dans les deux sens. Les deux expirations sont bornées **des deux côtés**, et un test les **distingue** : une session gardée active meurt au trentième jour. Le rafraîchissement est un **compare-et-pose atomique** — troisième fois dans le lot — et les 8 tests séquentiels sont **aveugles** au défaut. **550 tests**, `make sessions-check` dans la CI. Compte rendu : [`compte-rendu-t6-lot-3.md`](compte-rendu-t6-lot-3.md) | `US004` | ☑ |
| ~~**`T7`**~~ | ~~**CSRF et idempotence.**~~ **TERMINÉE le 21/08/2026.** **Deux barrières, dont la portée diffère** : l'`Origin` sur les **cinq** écritures — trois précèdent toute session, un jeton y est impossible — et un jeton **dérivé de la session par HMAC**, jamais stocké, sur celles qui en ont une. `SameSite=lax` ne suffit pas, et c'est le §7.4 qui le dit. **L'idempotence est adossée à Redis, sans inventer de table** : le modèle place déjà la clé sur `async_job` (LOT 11), et le résiduel — Redis n'est pas durable — est **nommé**. **`APP_SECRET_KEY` devient obligatoire partout**, et le garde-fou a immédiatement nommé quatre tests où elle ne traversait pas la frontière de processus. **585 tests**, `make csrf-check` dans la CI. **Huit tests antérieurs ont échoué, tous légitimement.** Compte rendu : [`compte-rendu-t7-lot-3.md`](compte-rendu-t7-lot-3.md) | `US005` | ☑ |
| ~~**`T8`**~~ | ~~**Limitation de débit.**~~ **TERMINÉE le 21/08/2026.** **Le cahier §20.2 donne les seuils, et le §8 de cette fiche affirmait le contraire** — `ECART-034`. **Deux verbes, et la distinction commande tout** : « limitation » pour l'adresse → **429** ; « alerte » pour l'origine et pour les échecs administrateur → **détection journalisée**, l'alerte exigeant `operational_alert` du §21.2, LOT 10. **Le compteur porte sur l'adresse normalisée AVANT toute lecture de la base** : sinon le 429 dirait « ce compte existe » et rouvrirait l'oracle de `T3`. Adresse et origine entrent dans Redis en **empreinte HMAC**. **Le compteur d'échecs par adresse comble le trou du verrou de `T5`**, avec les mêmes deux nombres. **613 tests**, `make debit-check` — **12 contrôles** — dans la CI. Compte rendu : [`compte-rendu-t8-lot-3.md`](compte-rendu-t8-lot-3.md) | `US001`, `US003` | ☑ |
| ~~**`T9`**~~ | ~~**Révocation au départ.**~~ **TERMINÉE le 22/08/2026.** **La révocation tient au DÉPART, et le §24.1 le tranche** : il n'a **aucune** transition `Active --> Archived`, donc attendre l'archivage — la lettre de `US006` — laisserait une fenêtre pendant laquelle un partant garde une session, ce que « **immédiatement** » interdit. Les deux transitions révoquent, la seconde étant **idempotente**. **`invitation` n'existe pas** : 0 occurrence dans le modèle et dans la matrice — `ECART-035`, à reprendre au LOT 9. **L'ordre est imposé par un déclencheur** : `fn_dg_implique_dsm_local` aurait fait échouer le départ d'un DG, et un test l'éprouve. **Quatre situations sont rapportées, jamais décidées** — rôles globaux, relations futures, consultants privés de DSM, liens déjà consommés. **Une garde a été retirée plutôt qu'écrite**, remplacée par un test qui prouve l'invariant en base. **630 tests**, `make revocation-check` — **6 contrôles** — dans la CI. Compte rendu : [`compte-rendu-t9-lot-3.md`](compte-rendu-t9-lot-3.md) | `US006` | ☑ |
| ~~**`T10`**~~ | ~~**Comptes de service et scopes.**~~ **TERMINÉE le 22/08/2026.** **Le §8 de cette fiche annonçait deux choses fausses** : le cahier §22 **énumère cinq scopes** (`ECART-036`), et la durée des jetons était **déjà numérotée `QO-072`** dans le cahier §32. **Mais les mots « par exemple » disent que la liste des scopes n'est PAS fermée** : la valider par liste blanche aurait bloqué les LOTS 9 et 11 — la validation porte donc sur la **forme**, et deux tests relisent le cahier. **`QO-072` est CLOSE par arbitrage de Jonathan : 90 jours**, et la valeur reste **configurable**, ce que le §10.5 exige — l'inverse de `T8`. **`ECART-037`** : `auth_event` ne portait pas le lien vers `service_account` que le diagramme §11 déclare, d'où la migration **`0013`** — sans elle, « chaque appel est audité » exigeait un huitième type d'événement que le §10.6 interdit. **661 tests**, `make service-check` — **11 contrôles, 3 témoins** — dans la CI. **Résiduel nommé : aucune route ne consomme encore le scope**, comme le CSRF de `T7`. Compte rendu : [`compte-rendu-t10-lot-3.md`](compte-rendu-t10-lot-3.md) | `US007` (`P1`) | ☑ |
| ~~**`T11`**~~ | ~~**Les écrans d'authentification.**~~ **TERMINÉE le 22/08/2026.** **Le compte est DÉRIVÉ** : six puces au cahier dont la dernière nomme trois pages → 5 + 3 = **huit**, et chaque libellé déclaré est confronté **mot pour mot** au document. **`DEC-456` tranchait déjà le routeur, dans l'autre sens que mon instinct** : le cahier §17.1 **nomme React Router**, et `DEC-456` ne l'installait pas « faute d'usage **avant le LOT 4** » — `T11` crée cet usage une étape plus tôt. Les **quatre autres** bibliothèques restent dehors, même raisonnement. **Le contrôle exerce pour la première fois le repli `try_files`** posé en `T7` du LOT 1, qui l'anticipait sans jamais avoir de chemin à replier — §7.16 — et le **type MIME** fait foi, Vite rendant 200 pour tout chemin inconnu. **Trois invariants que l'interface pouvait défaire** : la réponse générique (deux adresses, un rendu identique), le jeton retiré de la barre d'adresse, aucun stockage navigateur. **Et le linter a imposé un meilleur découpage** que le mien. **794 tests**, `make ecrans-check` — **7 contrôles** — dans la CI. Compte rendu : [`compte-rendu-t11-lot-3.md`](compte-rendu-t11-lot-3.md) | — | ☑ |
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
| ~~**La vérification « ESM ou super-administrateur »**~~ du §8.4 | **ACQUITTÉE en `T5`**, le 21/08/2026. Les deux droits vivent dans **deux tables** — `ESM` est une responsabilité Framework d'**une** entité, `SUPER_ADMIN` un rôle technique **global** — et la vérification exige la **période**, non `ends_at IS NULL` : une affectation **future** a elle aussi `ends_at` nul. C'est le contrôle §24.12 du cahier |
| ~~**`§30.11`**~~ — « un profil archivé ne reçoit pas de magic link » | **ACQUIS en `T3`**, le 21/08/2026. Le service exige `membership_state = 'active'`, ce qui écarte les **trois** autres états et non le seul `archived` — et la réponse reste **identique** à celle d'un profil actif : le refus ne se lit pas |
| **`§30.22`** — « le départ révoque immédiatement les sessions et rôles » | reporté au LOT 3. **`T9`** |

**Le contrôle de recette du modèle échouera** si ces classements ne sont pas mis à jour : il exige que
chacun des 25 contrôles du §30 soit classé, et qu'un « acquis » nomme un test qui **existe**.

---

## 5. Les cinq garde-fous déjà en place qui vont enfin servir

Ce lot est le premier à **exercer** des garde-fous posés au LOT 1 et jamais éprouvés en vrai :

1. ~~**`SESSION_COOKIE_SECURE=true` et `CSRF_PROTECTION_ENABLED=true`**~~ sont deux des sept
   garde-fous de production du cahier §20.3, testés depuis `T3` du LOT 1 — mais **rien ne les
   consommait**. **`T6` les rend effectifs**, et a trouvé pire : **Compose ne les transmettait même
   pas au conteneur**, 0 occurrence mesurée. Elles valaient donc leur défaut, et le garde-fou ne
   pouvait pas se déclencher sur une valeur réelle — même classe que `PUBLIC_BASE_URL` en `T3`.
   **`T7` a rendu `CSRF_PROTECTION_ENABLED` effective** : deux barrières, `Origin` sur les cinq
   écritures et un jeton sur celles qui ont une session ;
2. **L'origine unique de `DEC-470`** — la page et l'API sont servies par le même hôte, sans CORS —
   existe **précisément** pour que les cookies `Secure` et `SameSite` soient éprouvables. Ne remets pas
   ce montage en cause ;
3. **Les trois barrières de masquage** de `packages/observabilite` devront recevoir les **formats
   réellement produits par ce lot** : jeton de magic link, jeton de session, jeton de service. La
   leçon de `T4-1` est explicite — un test de filtre doit énumérer les formes **que ce projet
   produit**, pas des exemples de documentation.
   **FAIT EN `T3` POUR LES TROIS PRÉFIXES À LA FOIS** : `oml_`, `oss_` et `ost_` sont reconnus dès
   maintenant, et les constantes vivent dans `observabilite.masquage` — le filtre ne peut pas importer
   `apps/api`, c'est l'inverse. `T6` et `T10` n'auront rien à ajouter, mais devront **éprouver** ;
4. **`DEC-469`** interdit déjà de journaliser la chaîne de requête et les arguments de job. Un magic
   link arrive **dans une URL** : c'est exactement le cas que cette décision anticipait ;
5. **Gitleaks** examine chaque pull request avec des règles taillées sur les formats de ce projet. Un
   nouveau format de jeton **devra y être ajouté**, sinon la règle ne le verrait pas.
   **FAIT EN `T3`**, règle `onboarding-jeton-du-projet`, les trois préfixes. Et parce que le TOML
   n'importe rien, cette règle est nécessairement une **copie** : un test **lit `.gitleaks.toml`** et
   exige qu'elle attrape un jeton réellement engendré, avec le témoin inverse sur une chaîne base64
   sans préfixe. §7.27.

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
| ~~**Algorithme de hachage**~~ | **TRANCHÉE le 21/08/2026, `DEC-526`** : `scrypt` de la bibliothèque standard, `N = 2^16`. Le motif est la **mémoire**, non la durée. Résiduel nommé : `argon2id` est le premier choix des recommandations publiques, et les deux colonnes du §10.2 rendent le changement possible sans casser les comptes — un test le prouve | ~~`T5`~~ |
| **Politique de mot de passe** — longueur, classes de caractères, validité | **`QO-118`, ouverte par `T5`.** **Aucun document du corpus n'en écrit une**, et le §8 de cette fiche ne l'avait pas vue. Un plancher de 12 caractères s'applique comme **recommandation déclarée**, en une constante | avant le LOT 13 |
| ~~**Valeurs des limites de débit**~~ | **CETTE LIGNE ÉTAIT FAUSSE — `ECART-034`, mesuré en `T8`.** Le cahier **§20.2 s'intitule « Seuils initiaux » et en énumère six**, dont trois portent sur l'authentification : « 10 demandes de magic link par adresse et par heure : **limitation** », « 5 échecs administrateur en 15 minutes : **alerte** », « 50 demandes depuis une même origine en une heure : **alerte** ». `.env.example` en porte cinq **depuis le LOT 0**. Rien n'était à choisir, et choisir aurait **contredit le cahier** | close |
| ~~**Durée maximale d'un jeton de service**~~ | **CLOSE le 22/08/2026.** Et cette ligne était **incomplète** : la question existait déjà dans le cahier §32 sous le numéro **`QO-072`**, attribuée à « Jonathan / sécurité », échéance « LOT 3, story `MVP-L03-US007` ». En ouvrir une nouvelle aurait été une collision. **Arbitrage de Jonathan : 90 jours**, valeur **configurable** par `SERVICE_TOKEN_MAX_DAYS` | close |
| ~~**Liste des scopes**~~ | **CETTE LIGNE ÉTAIT FAUSSE — `ECART-036`.** Le cahier **§22 en énumère cinq** : `people:read`, `people:import`, `media:process`, `email:send`, `reports:generate`. **Mais les mots « par exemple » disent que la liste n'est pas fermée** — même forme que le « à prévoir **notamment** » du §25.1. La validation porte donc sur la **forme**, et deux tests relisent le cahier | close |

---

## 9. Critères de sortie de la porte `G3`, littéralement

| | Critère | Sous-étape qui le prouvera |
|:--:|---|---|
| ☐ | tous les scénarios autorisés et refusés sont testés | `T3` à `T10` |
| ☑ | **aucun jeton n'est stocké dans `localStorage`** | **`T6`, acquis le 21/08/2026.** Deux barrières : `HttpOnly` et le jeton absent de tout corps rendent la règle **structurelle**, et un contrôle **exact** des sources du frontend couvre le reste — avec son témoin dans les deux sens |
| ☑ | aucune adresse absente de la base ne peut se connecter | **`T3`, acquis le 21/08/2026** — et la réponse ne le révèle pas |
| ☑ | **les magic links ne figurent pas dans les logs** | **`T4`, acquis le 21/08/2026** — dans `api` ET dans `caddy`, et l'absence de journal d'accès Caddy est **gardée** par un contrôle (`DEC-525`) |
| ☑ | **les limites de débit produisent les résultats attendus** | **`T8`, acquis le 21/08/2026** — `make debit-check` : **12 contrôles, 0 échec**, à travers Caddy en HTTPS, avec **trois témoins** ; et les **deux** refus — adresse connue, adresse inconnue — sont comparés corps et en-têtes (`DEC-533`) |
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
