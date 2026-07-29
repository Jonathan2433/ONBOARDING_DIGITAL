# Compte rendu — sous-étape `T5` du LOT 1

**Exécutée le :** 28 juillet 2026
**Objet :** frontend Vite — page de statut consommant les healthchecks
**Story :** `MVP-L01-US002`, issue [#3](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/3), **rouverte** pour cette sous-étape
**Fondement :** [fiche du LOT 1](fiche-lot-1.md) §3, §6 et §7 ; roadmap LOT 1, démonstration attendue ; cahier §17.1, §17.2, §17.4, §13.4, §14.2, §18.7
**Décisions produites :** `DEC-470` à `DEC-473`
**Écarts ouverts et clos :** `ECART-020`, `ECART-021`

---

## 1. Critère de sortie, et ce qui le prouve

> « La page affiche l'état réel des services et la version ; TypeScript strict sans erreur. »
> — fiche §3

| Volet | Preuve | Résultat |
|---|---|---|
| La page est servie | `make web-check` : 6 contrôles, à travers Caddy en HTTPS, depuis l'hôte | **0** |
| Elle affiche l'état **réel** | **Redis arrêté pour de vrai** → la charge utile passe à 503, `redis indisponible`, motif `ConnectionError`, PostgreSQL et MinIO toujours `disponible` | **503 obtenu** |
| Elle affiche la version du build | `/health/version` lu depuis l'origine de la page : `0.0.0-dev` / `inconnue` / `development` | **0** |
| TypeScript strict sans erreur | `tsc --noEmit` sur 8 fichiers, `tsconfig.base.json` inchangé | **0** |
| Les états exigés | **25 tests** Vitest et Testing Library | **0** |

Sortie réelle de `make web-check` :

```text
  Page de statut, vue depuis https://app.onboarding.localhost
    ok       GET /                         HTTP 200  index.html avec la racine React
    ok       GET /src/main.tsx             type text/javascript  module transforme par Vite
    ok       GET /health/ready            HTTP 200  3 dependances, mandate vers l'API
    ok       GET /health/version          HTTP 200  {"version":"0.0.0-dev", ...}
    ok       GET /api/v1/                 HTTP 200  contrat monte
    ok       GET /api/v1/health/ready     HTTP 404  attendu : la sante est hors du prefixe (DEC-465)

  controles attendus : 6   executes : 6
  --> la page de statut est servie et partage l'origine de l'API (DEC-470)
```

Le sixième contrôle est le **discriminant** : il exige un **404**. Un montage trop large aurait
répondu 200, et six contrôles de succès n'auraient pas su distinguer un mandatement juste d'un
mandatement qui avale tout.

---

## 2. Ce qui a été livré

| Emplacement | Contenu |
|---|---|
| `apps/web/index.html` | Point d'entrée Vite. `lang="fr"` — sans lui un lecteur d'écran prononce le français avec les règles de l'anglais |
| `apps/web/src/main.tsx` | Montage React. L'absence de l'élément hôte **lève** au lieu de monter dans le vide |
| `apps/web/src/App.tsx` | Racine, sans routeur — `DEC-456`, une seule page au LOT 1 |
| `apps/web/src/FrontiereErreur.tsx` | Frontière d'erreur du cahier §17.4 |
| `apps/web/src/pages/PageStatut.tsx` | La page : cinq états, réessai, corrélation copiable |
| `apps/web/src/api/sante.ts` | Client typé des deux endpoints, validation à la main de la charge réseau |
| `apps/web/src/styles.css` | Mise en forme **neutre**, sans couleur de marque |
| `apps/web/src/*.test.ts{,x}` | **25 tests** répartis en 3 fichiers |
| `apps/web/Dockerfile` | `CMD` passe de `sleep infinity` au serveur Vite |
| `infra/caddy/Caddyfile` | Mandatement de même origine, `DEC-470` |
| `infra/compose/docker-compose.base.yml` | Healthcheck `web` par **vrai appel HTTP** ; `Caddyfile` monté par son répertoire |
| `infra/scripts/verifier-page-statut.sh` | 6 contrôles avec comptage |
| `.dockerignore` | **Nouveau**, `DEC-473` |
| `Makefile` | 2 cibles : `web-check`, `caddy-reload`. **33 cibles** au total |

**Retirés :** `apps/web/src/version.ts` et son test, échafaudage de `T1` dont le commentaire
disait lui-même être « volontairement le seul contenu de `src` à ce stade ». La version affichée
vient désormais de `/health/version`, autorité du build, et non d'une constante du frontend.

### Ce que `T5` n'a pas fait, et ne devait pas faire

Aucun écran métier, aucune donnée de collaborateur, **aucune authentification, même partielle,
même de test**, aucune navigation — le LOT 4 la possède —, aucune couleur de marque, aucune
bibliothèque du cahier §17.1 sans usage avant le LOT 4.

---

## 3. Le montage de même origine — `DEC-470`, et une affirmation fausse de la passation

`CLAUDE.md` §9.3 affirmait : « `Caddyfile` inchangé : le mandatement existe déjà. » **C'était
faux, et cela aurait bloqué la sous-étape.**

Mesure : le bloc `app.onboarding.localhost` renvoyait **tout** vers `web:5173` ; aucune route
n'y menait à l'API. Or `VITE_API_BASE_URL` vaut `/api/v1`, un chemin **relatif** : un appel à
`/health/ready` depuis la page atteignait Vite, pas l'API. L'autre voie, appeler
`api.onboarding.localhost` en absolu, est une **autre origine** — et l'API n'a **aucun CORS**,
mesuré à 0 occurrence.

Trois montages étaient possibles. Arbitrage de Jonathan : **Caddy fait suivre**.

| Montage | Écarté parce que |
|---|---|
| CORS sur l'API | Surface de sécurité permanente, et cookies `Secure` / `SameSite` du LOT 3 compliqués — or c'est **pour pouvoir les éprouver** que `DEC-446` impose HTTPS local |
| Renvoi par le serveur Vite | Disparaît dès qu'une image de production sert un artefact statique : à refaire en `T7` |
| **Mandatement par Caddy** | **Retenu.** Une seule origine, API non modifiée, `X-Request-ID` lisible sans `Access-Control-Expose-Headers`, et le montage survit à la recette et à la production |

**Preuve discriminante obtenue gratuitement** : le service `web` arrêté, `/health/ready` et
`/health/version` répondaient **toujours 200** depuis l'origine de la page. Ces chemins vont donc
bien à l'API et non à Vite.

---

## 4. Les cinq états de la page

La fiche §6 en exige trois. Il y en a **cinq**, parce que deux d'entre eux étaient confondus.

| État | Déclencheur | Ce que la page montre |
|---|---|---|
| **Chargement** | montage, réessai, retour du réseau | « Interrogation de l'API… », `aria-busy="true"` |
| **Nominal** | 200 sur les deux endpoints | « Plateforme prête », les 3 dépendances, la version |
| **Dégradé** | **503** sur `ready` | « Plateforme dégradée », **quelle** dépendance manque et **pourquoi** |
| **Erreur** | autre code, transport rompu, forme inattendue | Motif rapporté, bouton **Réessayer** |
| **Hors connexion** | `navigator.onLine` faux, événement `offline` | État explicite, **et aucune interrogation lancée** |

### Pourquoi un 503 n'est pas une erreur

`/health/ready` répond 503 avec **exactement la même forme JSON** qu'un 200 : il fixe
`status_code` sans passer par le gestionnaire d'erreur du §18.3. Le traiter comme une panne
réseau reviendrait à **jeter le diagnostic au moment où il devient utile**. Le client accepte
donc 200 **et** 503 pour `ready`, et 200 seul pour `version` — un test éprouve cette
discrimination : un client qui accepterait 503 partout afficherait une version qu'il n'a pas lue.

### Accessibilité — ce qui est fait, ce qui ne l'est pas

Fait : `lang="fr"`, un `<main>` et un `<h1>`, région `aria-live` avec `aria-busy`, `role="alert"`
sur l'erreur, tableau à en-têtes de ligne et de colonne, **information jamais portée par la seule
couleur** — le libellé est explicite et le symbole diffère par sa **forme**, `●` contre `▲` —,
`:focus-visible` conservé, `prefers-reduced-motion` neutralisant la seule transition de la page,
aucune largeur fixe.

**Non fait, et il faut le dire :** aucun audit outillé. `axe` n'est pas installé — `jsx-a11y`
couvre le lint JSX, l'audit automatisé du §14.2 relève de `T10` et de l'audit du LOT 12. Les
largeurs de recette du §13.4 n'ont pas été éprouvées dans un navigateur, pour la raison du §7.

---

## 5. Contrôles exécutés

### 5.1 Chaîne de qualité

| Contrôle | Résultat |
|---|---|
| `make check` | **0** — 139 tests pytest, **27 Vitest** dont 25 nouveaux |
| `tsc --noEmit` strict sur 8 fichiers | **0** |
| ESLint sur `apps/web/src` | **0** sur 8 fichiers examinés, comptés |
| Empreintes des 5 documents immuables | **5/5 conformes avant ET après `make format`** |

### 5.2 Témoins négatifs — 6 sur 6 concluants

| Maillon | Défaut injecté ou action réelle | Code |
|---|---|---:|
| **`jsx-a11y`** | `<img>` sans `alt` | **1**, règle `jsx-a11y/alt-text` citée |
| `tsc` strict sur `.tsx` | type de retour faux | 1 |
| Vitest | assertion faussée sur `ConnectionError` | 1, puis **0** au rétablissement |
| Healthcheck `web` | commande pointée sur un port fermé | 1, contre **0** sur 5173 |
| `make web-check` | **arrêt réel** du service `web` | 2, et `make health` à 2 |
| Vérificateur d'empreintes | comparaison à une empreinte bidon | écart détecté |

**Le premier compte plus que les autres.** `eslint-plugin-jsx-a11y` est le **motif déterminant**
de `DEC-451`, et il n'avait jamais eu un seul fichier JSX à examiner : il n'existait aucun `.tsx`
dans ce dépôt. Il déclare par ailleurs une compatibilité ESLint `^3 || … || ^9` alors qu'**ESLint
10.8.0** est installé — `pnpm peers check` le signale. Un greffon inerte n'aurait rien dit. Le
témoin prouve qu'il examine et qu'il **sait échouer**.

### 5.3 Stack et non-régression

| Contrôle | Résultat |
|---|---|
| `make up` | **0** — 8 services sains |
| `make stack-check` | **0** — 8/8 sains, **7 publications déclarées, 7 réelles**, toutes sur `127.0.0.1` |
| `make api-check` | **0** — 3/3 endpoints |
| `make test-integration` | **0** — 8 exécutés, 131 désélectionnés |
| `make persistence-test` | **0** — **5 empreintes relevées, 5 comparées** |
| `make icloud-verify` | **0** — 10 lignes `ok`, aucune copie de conflit |

**Le port 5173 n'est pas publié** : Caddy le joint par le réseau interne. Les 7 publications de
`DEC-460` sont inchangées.

### 5.4 Résolution des modules

Les 7 modules dont la page a besoin sont servis **comme du code** : `text/javascript`. Le témoin
négatif discrimine — `/src/module-inexistant.tsx` est servi en `text/html`, Vite retombant sur
`index.html`. Voir le défaut `T5-6` : ce contrôle a d'abord conclu sur le seul code HTTP, et
concluait donc faux.

### 5.5 Sécurité et hygiène

**22 fichiers** dans l'index, **0 correspondance** sur 6 familles de motifs — mot de passe, clé
PEM, jeton GitHub, clé AWS, URL avec identifiants, `CHANGE_ME` résiduel. **Témoin positif** : le
même détecteur trouve **4** correspondances dans `.env`, qui porte de vrais secrets. Le zéro est
donc un vrai zéro.

`.env` n'est pas dans l'index. `V1.html` : 0 occurrence. Les 10 références d'image réelles sont
**toutes** épinglées par `@sha256:`, **0 `latest`**.

> **Une exception à déclarer.** Le contrôle d'hygiène `git ls-files | grep -Ei
> '\.(csv|env|pem|key|mp4|html)$'` montre désormais **deux** fichiers : le CSV fictif et
> **`apps/web/index.html`**. Le filtre visait le prototype `V1.html` ; `.gitignore` ne vise que
> `docs/prototype/V1.html`, jamais `*.html`. Un point d'entrée Vite est légitime et imposé par
> l'outil. L'exception est déclarée ici plutôt que glissée en silence : un contrôle dont on
> ignore les alertes cesse d'être un contrôle.

---

## 6. Défauts détectés pendant `T5`

**Huit défauts. Cinq étaient dans mes propres contrôles**, un dans mes tests, deux dans le
livrable ou l'infrastructure.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T5-1` | Quatre tests de la page attendaient sur `findByRole('status')`. Or la bannière de **chargement** porte elle aussi `role="status"` : la recherche aboutissait immédiatement et **n'attendait rien**. Les quatre échouaient sur « attendu `Plateforme dégradée`, reçu `Interrogation de l'API…` » | **Test faux.** Même classe que `T3-3` : un test qui semble attendre un état et n'attend rien | Fonction `attendreEtatCharge()` qui attend le **tableau des dépendances**, présent dans le seul état chargé, puis lit la bannière |
| `T5-2` | Caddy servait une configuration **périmée** en paraissant parfaitement sain. Le conteneur voyait un `Caddyfile` de **1 573 octets** quand l'hôte en portait **2 844**. Un bind mount de **fichier unique** épingle l'inode ; l'éditeur ayant remplacé le fichier, le conteneur pointait vers un inode supprimé — `ls` affichait l'entrée, `open` répondait « No such file or directory » | **Livrable silencieusement inactif.** Les quatre contrôles d'API échouaient avec « HTTP 200 » et du HTML : c'était Vite qui répondait | Montage du **répertoire** `../caddy:/etc/caddy:ro`, et cible `caddy-reload` appelée par `make up`. `DEC-472`. Contrôle ajouté : aucun bind mount de fichier seul ne subsiste, **1 bind sur 14 entrées de volume examinées** |
| `T5-3` | **Aucun `.dockerignore` n'existait.** `COPY apps/web ./apps/web` recopiait le `node_modules` de l'hôte par-dessus celui de l'image. L'hôte résout `@rolldown/binding-darwin-arm64` et `lightningcss-darwin-arm64` ; l'image résout les variantes `linux-arm64-musl` | **Défaut latent, non actif** : les liens sont relatifs et pointent vers le magasin `.pnpm` du conteneur. Il devenait actif au premier `node_modules` d'hôte désynchronisé du verrou, et l'échec serait survenu au **démarrage**, pas à la construction | `.dockerignore`, `DEC-473`. Le défaut était invisible jusqu'ici : aucune image n'avait besoin d'**exécuter** le code copié |
| `T5-4` | `setVue({nom:'chargement'})` appelé **synchronement dans le corps d'un effet**, provoquant un rendu en cascade | **Livrable défectueux**, trouvé par `react-hooks/set-state-in-effect` dès le premier JSX de ce dépôt | L'état de chargement est posé dans les **gestionnaires d'événement** — bouton de réessai, retour du réseau — l'état initial du composant étant déjà `chargement`. Meilleur code, comme les corrections de `T3-1` et `T3-2` |
| `T5-5` | Mon témoin négatif sur les motifs de Vite s'écrivait `grep … \| head -1; echo $?` : j'ai lu le code de `head`, donc **0**, et j'ai conclu qu'un motif inexistant existait | **Contrôle menteur. Cinquième occurrence du piège du tuyau** dans ce lot, après `T0-1`, `T2-4`, `T3-6`, `T4-3` | Sortie capturée en variable, code lu directement. Témoin positif 0 / 2 occurrences, témoin négatif **1** |
| `T5-6` | Mon contrôle de résolution des modules concluait « 7/7 résolus » sur le seul **code HTTP 200**. Or Vite répond **200 avec `index.html`** pour tout chemin inconnu : un module absent aurait aussi donné 200 | **Contrôle incapable de discriminer**, détecté parce que le témoin négatif est passé quand il devait échouer | Discrimination sur le **type MIME**. Le module absent est servi en `text/html`, les 7 vrais en `text/javascript` |
| `T5-7` | Mon détecteur de bind mounts annonçait **0 bind mount** alors que le `Caddyfile` en était un. L'expression régulière était fausse | **Contrôle qui ne peut rien trouver**, détecté parce que je savais qu'il devait en trouver au moins un | Réécrit, et il **annonce le nombre d'entrées examinées** : 14 entrées, 1 bind, 0 de fichier seul |
| `T5-8` | `for m in $modules` a échoué sur « read-only variable: modules » | **Piège d'environnement** : `modules` est une variable spéciale en lecture seule de `zsh`. À rapprocher de §7.5 — `zsh` ne découpe pas non plus les variables en mots | Variable renommée, et **liste littérale** dans le `for` plutôt qu'une variable |

### 6.1 Ce que ces huit défauts enseignent

**Cinq sur huit étaient mes contrôles, pas le livrable.** C'est la proportion la plus élevée du
lot, et elle est cohérente avec `T2` — quatre contrôles menteurs sur sept défauts. La classe ne
se referme pas : elle se déplace. `T5-5` reproduit à l'identique un piège documenté quatre fois.

`T5-6` est le plus instructif, parce qu'il ajoute une variante. Le contrôle ne mentait pas sur le
**nombre** d'éléments examinés — il en annonçait bien 7, et il en avait bien examiné 7. Il
mentait sur ce que « examiné avec succès » **signifie** : un code 200 ne prouvait rien, puisque
la valeur d'échec produit le même code. La parade du lot — compter, et confronter le compte à un
attendu — était respectée, et pourtant le contrôle ne prouvait pas ce qu'il annonçait.

> **La règle mérite donc une troisième proposition, et c'est l'apport de `T5` :**
> un contrôle doit se demander **quelle valeur produirait l'échec**. Si l'échec produit la même
> observation que le succès, le contrôle ne prouve rien — quel que soit le nombre d'éléments
> qu'il a comptés. C'est exactement le défaut `T2-5`, où un Mailpit vide et un volume effacé
> donnaient tous deux `{"total":0}`, et c'est ce que le témoin négatif détecte quand il **passe**
> alors qu'il devait échouer.

`T5-2` mérite un mot pour l'exploitation : **un service peut être sain et servir une
configuration périmée.** Le healthcheck de Caddy interrogeait son API d'administration, qui
répondait — sur l'ancienne configuration. Aucun contrôle du lot ne comparait la configuration
**chargée** au fichier **présent**. C'est maintenant `make up` qui l'impose, en rechargeant.

---

## 7. Ce qui n'est PAS couvert

Trois choses, et il vaut mieux les dire que les laisser croire.

> **✅ Ce point est levé depuis le 29 juillet 2026, sous-étape `T6`.** Jonathan a approuvé la
> racine dans son trousseau **de session** — la commande donnée ici employait `sudo`, dont il ne
> dispose pas, voir `QO-114`. `security verify-cert` est passé de **1** à **0**, et la page a été
> **vue dans un vrai navigateur** : rendu complet, **console sans erreur** — les deux seules
> lignes étant `[vite] connecting… connected.`, ce qui prouve au passage que le rechargement à
> chaud traverse Caddy en `wss` —, **cinq largeurs de recette sur cinq sans débordement** de page
> à 320, 390, 768, 1280 et 1920 px, le tableau défilant dans son propre conteneur à 320 px,
> navigation au clavier et focus visible conformes, et l'**état dégradé rendu de bout en bout** en
> arrêtant réellement Redis. Le détecteur de débordement a lui-même été éprouvé par une sonde de
> 5 000 px. Un défaut de rédaction a été trouvé à cette occasion, invisible aux tests : voir
> `T6-8`.

1. **La page n'a pas été vue dans un navigateur.** La racine de l'autorité interne de Caddy
   n'est pas approuvée dans le trousseau macOS : `security verify-cert` sort en **1**,
   `CSSMERR_TP_NOT_TRUSTED`, et le navigateur refuse la connexion. Cause isolée par élimination —
   le même navigateur atteint sans peine `http://127.0.0.1:8025`. Ce qui est prouvé : la page est
   servie, ses 7 modules sont transformés, et ses composants rendent correctement les cinq états
   sous `jsdom`. Ce qui ne l'est pas : le rendu par un moteur de navigateur réel, les largeurs de
   recette du §13.4, et l'absence d'erreur de console. **C'est l'action de Jonathan**, elle
   demande son mot de passe.

2. **L'état hors connexion est prouvé par test, pas en réel.** Il est éprouvé en forçant
   `navigator.onLine` et en émettant l'événement `offline`. Couper réellement le réseau de l'hôte
   couperait aussi la stack.

3. **Aucun audit d'accessibilité outillé.** `axe` n'est pas installé, `T10` et le LOT 12 le
   possèdent.

---

## 8. État à la sortie de `T5`

| | |
|---|---|
| Sous-étape | **`T5` terminée.** Story `MVP-L01-US002` prête pour validation, issue `#3` à refermer à la fusion |
| Décisions | `DEC-470` à `DEC-473`. Prochaine libre : **`DEC-474`** |
| Écarts | `ECART-020` et `ECART-021` ouverts **et clos**. Prochain libre : **`ECART-022`** |
| Risques | **`ROAD-RSK-031` ouverte** — serveur de développement en recette. **`ROAD-RSK-030` aggravé** : image `web` de 924 Mio à **1,02 Gio**. Prochain libre : **`ROAD-RSK-032`** |
| Questions | **`QO-085` mesurée en charge réelle** — 389 Mio, 5,0 % du budget. **Reste ouverte**, à clore en `T8`. Prochaine libre : `QO-114` |
| Tests | **166** — 139 pytest (131 unitaires, 8 d'intégration) et **27 Vitest**, dont 25 nouveaux |
| Cibles `Makefile` | **33** — `web-check` et `caddy-reload` ajoutées |
| `make check` · `stack-check` · `api-check` · `web-check` · `test-integration` · `persistence-test` | Tous **code 0** |

### Les 7 critères de la porte `G1`

| | Critère | État |
|:--:|---|---|
| ☑ | Tous les services démarrent sur le Mac M5 | `T2`, et **`web` sert enfin quelque chose** depuis `T5` |
| ☐ | Les images multiarchitectures sont construites | `T7` |
| ☑ | Aucun secret réel n'est présent | contrôlé, avec témoin positif |
| ☑ | Une migration Alembic vide ou initiale s'exécute | `T3` |
| ☑ | Les logs possèdent un identifiant de corrélation | `T4` |
| ☐ | **La CI bloque une erreur de lint, de test et de secret** | **`T6`, le test le plus important du lot** |
| ☐ | Jonathan valide le socle | `T11` |

La démonstration attendue par la roadmap est désormais satisfaite à **5 sur 6** : seul le
pipeline CI manque, et c'est `T6`.

### Ce qui attend `T6`

Les **11 contrôles** du cahier §23.1, dont trois échecs volontaires à **prouver**. Trois apports
de `T5` y entrent directement :

- **« tests frontend »** est l'un des 11 contrôles, et il a désormais 25 tests à exécuter, là où
  il n'en aurait trouvé qu'un ;
- `ROAD-RSK-029` recommande un contrôle recalculant les **cinq empreintes SHA-256** des documents
  immuables. `ECART-021` recommande d'y ajouter un contrôle **dérivant de la source** les nombres
  que la documentation affirme — quatre étaient faux, dont un marqueur d'identifiant libre en
  retard de 19 décisions, qui aurait provoqué une collision ;
- `pnpm peers check` sort en **1** : `eslint-plugin-jsx-a11y@6.10.2` ne déclare pas ESLint 10.
  Le greffon fonctionne — prouvé par témoin — mais un contrôle de CI sur les pairs échouerait.
  **À trancher en `T6` :** corriger, tolérer explicitement, ou ne pas contrôler les pairs.
