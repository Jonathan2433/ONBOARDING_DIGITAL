# Compte rendu — sous-étape `T7` du LOT 1

**Exécutée le :** 29 juillet 2026
**Objet :** images multiarchitecture `linux/amd64` et `linux/arm64`, publiées dans GHCR privé
**Story :** `MVP-L01-US006`, issue [#7](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/7)
**Fondement :** cahier §22.3, §23.2, §23.3, §23.5, §20.1 ; conventions Git §4.1 ; `ROAD-RSK-030`, `ROAD-RSK-031`, `DEC-445`
**Décisions produites :** `DEC-478` à `DEC-482`
**Écart ouvert et clos :** `ECART-022` · **Risque ouvert :** `ROAD-RSK-033` · **Risques clos :** `ROAD-RSK-030`, `ROAD-RSK-031`

---

## 1. Critère de sortie, et ce qui le prouve

> « Une même version immuable **fonctionne** sur `arm64` et `amd64` ; l'accès au registre est
> **authentifié** ; **aucune référence à `latest` seul**. » — fiche §3
>
> « Une même version immuable fonctionne sur Apple Silicon et AMD64 ; l'accès au registre est
> authentifié. » — backlog, littéral

**Le mot qui commande tout est « fonctionne ».** Une image `amd64` qui se construit mais ne
démarre pas ne satisfait rien. Les conteneurs sont donc **lancés**, sur les deux architectures, et
on lit dans chacun une valeur que **l'autre architecture ne pourrait pas produire**.

| Volet | Preuve | Résultat |
|---|---|---|
| Une **seule** liste de manifestes porte les deux plateformes | `mediaType` = `application/vnd.oci.image.index.v1+json`, et les plateformes sont **lues dans le `--metadata-file` de buildx**, non codées en dur | **3 images, 2 plateformes chacune** |
| Les images **fonctionnent** | 3 services × 2 architectures, conteneurs lancés | **39 contrôles, 0 échec** |
| L'architecture est bien celle attendue | `uname -m` **dans** le conteneur : `x86_64` / `aarch64` | 6/6 |
| L'accès au registre est authentifié | `GITHUB_TOKEN` avec `packages: write`. **`gh secret list` reste vide** | aucun secret créé |
| Aucun `latest` publié | `make images-check`, témoins dans les deux sens | 0 trouvée |
| `web` ne sert plus le serveur de développement | 0 occurrence de `/@vite/client`, `/assets/` présent | 2/2 architectures |

### 1.1 Ce qui est prouvé **nativement**, et ce qui ne l'est qu'**émulé**

**Il faut le dire précisément, parce que les deux voies n'ont pas la même valeur de preuve.**

| Architecture | Sur l'image **publiée dans GHCR** | Sur la liste de manifestes **construite localement** |
|---|---|---|
| `linux/amd64` | **native** — exécuteur GitHub `x86_64` | émulée sur le Mac |
| `linux/arm64` | **émulée** par QEMU sur l'exécuteur | **native** — le Mac M5 est `aarch64` |

**Arbitrage de Jonathan :** ne pas authentifier cette machine au registre. Le jeton `gh` local n'a
ni `read:packages` ni `write:packages` — mesuré, `403 : You need at least read:packages scope` — et
l'ajout du droit relève de ses identifiants, que l'agent ne manipule pas (`CLAUDE.md` §7.14).

**Conséquence assumée, et les deux empreintes sont nommées.** L'exécution native sur Apple Silicon
porte sur des listes de manifestes construites ici :

```text
api      sha256:3b221b95d95c711e640b54086647a577eab46c8981aaf31d938c53dbd44827b2
worker   sha256:3100d5a70e433b1f347589fd48807abfa0102b02960e2c823283391f6530b398
web      sha256:ec042ebc25206776a3ec44c0e3d7736ba8e95d12a7a141f370212c17c3dcadfe
```

Celles publiées par l'intégration continue seront différentes — les images ne sont pas
reproductibles bit pour bit, le label OCI `created` portant un horodatage. **« Une même version
immuable fonctionne sur les deux architectures » est donc prouvé deux fois, sur deux artefacts
distincts, et jamais nativement sur les deux à la fois pour le même.** `T8` peut lever la réserve
sans nouveau droit : la surcouche de recette tire l'image publiée **sur cette machine**, donc
nativement en `arm64`, dès lors que Jonathan aura fait un `docker login ghcr.io`.

---

## 2. Ce qui a été livré

| Emplacement | Contenu |
|---|---|
| `apps/web/Dockerfile` | **Réécrit.** 4 étapes, **2 cibles nommées** : `developpement` et `execution` (`DEC-479`) |
| `apps/web/Caddyfile.execution` | **Nouveau.** Serveur de fichiers interne au conteneur, port 5173, repli page unique |
| `apps/api/Dockerfile`, `apps/worker/Dockerfile` | `ARG` → `ENV` de version et révision, **4 étiquettes OCI**, et suppression du `chown -R` |
| `.github/workflows/images.yml` | **Nouveau.** 4 tâches : `publier`, `verifier` (matrice 2 architectures), `analyser` (Trivy), `porte` |
| `infra/scripts/verifier-images.py` | **Nouveau.** 6 sous-commandes, ~1 000 lignes, tous les contrôles de cette sous-étape |
| `Makefile` | **7 cibles ajoutées** → **44** : `env-check`, `caddy-recreate`, `images-check`, `images-build`, `images-inspect`, `images-verify`, `images-push`. `caddy-reload` réécrite |
| `infra/compose/docker-compose.base.yml` | `build.args` et transmission de `APP_VERSION`/`APP_REVISION` à `api` **et** `worker` ; healthcheck `web` rendu indépendant de la cible |
| `infra/compose/docker-compose.dev.yml` | `build.target: developpement`, **sélection explicite** |
| `.env.example` | **v1.1** — doublon `APP_REVISION` retiré (`ECART-022`) |

### 2.1 Les gains de taille, mesurés avant et après

| Image | Avant `T7` | Après `T7` | Gain |
|---|---:|---:|---:|
| **`web`, cible publiée `execution`** | **1,02 Gio** | **84,9 Mo** | **−91,7 %** |
| `web`, cible `developpement` | 1,02 Gio | 725 Mo | −29 % |
| `api` | 662 Mo | 473 Mo | −29 % |
| `worker` | 662 Mo | 473 Mo | −29 % |

Absence de l'outillage dans la cible publiée, vérifiée par `command -v` : `node`, `npm`, `pnpm`,
`vite`, `eslint` — **5 absents sur 5**.

### 2.2 Le second gisement, que ni `ROAD-RSK-030` ni moi n'avions vu

`ROAD-RSK-030` attribuait le poids de `web` à l'outillage de développement. C'est vrai, mais
**incomplet**. `docker history` a montré autre chose :

```text
web    RUN chown -R node:node /app                              230 MB
api    RUN useradd ... && chown -R onboarding:onboarding ...     143 MB
```

**Un `chown -R` duplique tout ce qu'il touche.** Une couche d'image réenregistre le fichier
**entier** dès qu'une seule de ses métadonnées change : la couche recopie donc l'arborescence dont
elle ne modifie que le propriétaire. Corrigé dans les trois `Dockerfile` — utilisateur créé
**avant** les copies, `COPY --chown` ensuite. **C'est ce gisement, et non l'outillage, qui explique
les 29 % gagnés par `api` et `worker`**, que le risque ne visait pas.

### 2.3 Pourquoi Caddy comme socle d'exécution, et non `nginx`

`caddy:2.11-alpine` est **déjà** dans ce projet, à la même empreinte, pour le mandataire inverse.
La réutiliser n'ajoute **aucune dépendance externe** — donc aucune entrée au registre des
dépendances, `DEP-018` reste libre — et **aucune vulnérabilité distincte** au périmètre du projet.

Et l'artefact écoute sur **5173**, le port de la cible de développement : `infra/caddy/Caddyfile`
porte `reverse_proxy web:5173` et n'a **pas eu à changer**. Un Caddyfile par environnement aurait
dupliqué le mandatement de même origine de `DEC-470`.

### 2.4 Ce que `T7` n'a pas fait, et ne devait pas faire

Aucune surcouche de recette — `T8`, et c'est elle qui **sélectionnera** la cible `execution`.
Aucun déploiement. **Aucun secret de dépôt créé** : `gh secret list` reste vide. Aucune table,
aucun modèle, aucun type métier. Aucune authentification. Aucune ligne du prototype.

---

## 3. Ce qui n'est PAS couvert, et il faut le dire

1. **`arm64` n'est pas prouvé nativement sur l'image publiée.** Voir §1.1. C'est un arbitrage,
   pas un oubli, et la réserve est portée dans la fiche §3.1.
2. **La porte des images n'est pas un contrôle requis de la protection de branche, et ne doit pas
   le devenir.** Le workflow ne s'exécute **pas** sur les pull requests — le cahier §23.1 l'exige,
   « aucun déploiement ne part d'une pull request ». L'ajouter aux contextes requis bloquerait
   **toute** fusion pour toujours, puisqu'il ne produirait jamais de statut sur une pull request.
3. **Le §23.2 exige qu'une fusion sur `develop` « déploie la recette locale ». Ce n'est pas fait,
   et ce n'est pas faisable ici.** Mesure : `gh api repos/.../actions/runners` renvoie
   `total_count: 0`, et un exécuteur GitHub ne peut pas atteindre le Mac de Jonathan. La recette
   de `T8` sera lancée à la main. C'est un volet de `ECART-022`.
4. **Trivy ne bloque que sur `CRITICAL` corrigeable.** Le reste est rapporté, visible, non
   bloquant. Motif mesuré en §5.3, et c'est `DEC-482`.
5. **La reproductibilité bit pour bit n'est pas atteinte** : le label OCI `created` porte un
   horodatage. Deux constructions du même commit donnent deux empreintes. `DEC-443` parlait de
   reproductibilité au sens de l'épinglage des bases, ce qui est acquis ; la reproductibilité
   stricte demanderait `SOURCE_DATE_EPOCH` et un travail propre.

---

## 4. Trivy : la mesure d'abord, la décision ensuite

**Arbitrage de Jonathan : installer, mesurer, montrer le chiffre, décider après.** C'est la
cinquième proposition de la règle du lot, et elle a changé la conclusion.

Trivy 0.72.0, posé par archive officielle, **empreinte SHA-256 vérifiée** — même discipline que
`gh` en `T0`, `uv` en `T1` et Gitleaks en `T6`. Mesures du 29/07/2026, plateforme `linux/arm64` :

| Image | `CRITICAL` | `HIGH` | Total | `CRITICAL` **corrigeables** |
|---|---:|---:|---:|---:|
| `python:3.12-slim` (socle) | 4 | 19 | 176 | **0** |
| **`api` après `T7`** | 4 | 19 | **176** | **0** |
| `caddy:2.11-alpine` (socle) | 0 | 10 | 27 | **0** |
| **`web` après `T7`, cible `execution`** | 0 | 10 | **27** | **0** |
| `web` **avant** `T7` | 1 | 8 | 23 | **1** |

**Deux conclusions, et la première m'a surpris.**

**1. Nos couches n'ajoutent aucune vulnérabilité.** 176 pour `api` comme pour son socle, 27 pour
`web` comme pour le sien. Tout vient de Debian trixie et d'Alpine.

**2. Le découpage multi-étapes ne RÉDUIT PAS le compte de `web` : il le fait passer de 23 à 27.**
Je m'attendais au contraire. Il élimine le seul `CRITICAL` corrigeable — `tar 7.5.13 → 7.5.19`
dans le npm embarqué par Node — et échange 8 `HIGH` de l'écosystème npm contre 10 `HIGH` du
binaire Caddy. **Le gain de la réécriture est la taille et `ROAD-RSK-031`, pas le compte de
vulnérabilités.** L'annoncer autrement aurait été faux.

**Pourquoi la porte ne bloque pas sur `HIGH`.** `python:3.12-slim` porte **23 avis `HIGH` ou
`CRITICAL` dont aucun n'a de version corrective** : quatre `CRITICAL` dans `perl-base`, le reste
dans util-linux, `gzip` et ncurses. Bloquer sur `HIGH` rendrait la chaîne **définitivement rouge
sans remède** — le seul « correctif » serait d'abandonner Debian slim, que `DEC-443` a choisi parce
que les roues Python n'existent pas en musl. Un contrôle qui exige l'impossible finit désactivé.

**Le réglage retenu est vert aujourd'hui et il peut échouer**, ce qui n'est pas une supposition :
l'image `web` d'avant `T7` en portait exactement un. Le témoin négatif vient d'une image réelle.

---

## 5. Contrôles exécutés, et leurs témoins

### 5.1 Les contrôles fonctionnels — 39, aucun échec

| Service | Contrôles | Ce qu'ils lisent |
|---|---:|---|
| `api` | **18** | refus de démarrer du §20.3 · `live` 200 · **version et révision égales à celles de la construction** · `ready` **503 avec 3 dépendances nommées** · `uname -m` |
| `worker` | **10** | **le Redis jetable répond PONG, attendu et compté** · `platform.machine()` · **`APP_VERSION` et `APP_REVISION` égales à celles de la construction** · **7 files** · **ping réel du courtier Redis** |
| `web` cible `execution` | **8** | 200 · **0** `/@vite/client` · `/assets/` présent · `uname -m` |
| `web` cible `developpement` | **3** | témoin positif : **1** `/@vite/client` |

**Le contrôle d'identité compare à ce que la construction a DÉCLARÉ**, et non à « différent du
défaut ». C'est plus fort — il prouve que l'image porte **LA** version avec laquelle elle a été
construite — et c'est la correction du défaut `T7-10`, qui faisait échouer le contrôle sur une image
correcte.

**Le `ready` à 503 est une meilleure preuve qu'un 200.** L'image est lancée sans aucune dépendance
joignable : elle répond 503 en **nommant** `postgresql`, `redis` et `minio` indisponibles. Cela
prouve que l'application est entièrement montée et qu'elle sonde réellement — un conteneur
simplement démarré, routes non montées, répondrait 404.

### 5.2 Témoins négatifs — 11, tous concluants

| Maillon | Défaut injecté ou action réelle | Résultat |
|---|---|---|
| Énumération des plateformes | plateforme **témoin** `linux/s390x`, absente du manifeste | inspection **refusée**, code 1 |
| Plafond de taille | plafond abaissé de 130 à 100 Mio | **échec**, dépassement nommé |
| Identité du build | attendu volontairement faux, `9.9.9-faux` / `deadbee` | **échec**, lu et attendu tous deux affichés |
| Identité du build, second sens | attendus **non fournis** | **échec** : le contrôle refuse de se dégrader en silence |
| Détecteur `/@vite/client` | même sonde sur la cible de développement | **1 occurrence**, le détecteur n'est pas muet |
| Détecteur de `latest` | chaînes synthétiques, **dans les deux sens** | trouve `<registre>/…:latest`, ignore `ubuntu-latest` |
| Healthcheck `web`, mécanisme changé | port fermé 9999, **sur les deux cibles** | code 1 contre 0 sur 5173 |
| Refus de démarrer du §20.3 | image lancée sans configuration | code 1, **7 variables nommées, 0 valeur divulguée** |
| Cohérence `.env` | contrôle exécuté sur l'état réel du `.env` | **3 variables manquantes trouvées** |
| Liste blanche Gitleaks des empreintes | 64 hexadécimaux **sans** préfixe `sha256:` | **toujours détecté** — la liste blanche n'a rien affaibli |
| Gitleaks, témoin positif | les 5 secrets réels de `.env` | **5 sur 5 détectés** |

**Le tirage anonyme du registre** est le douzième, mais il vit dans la chaîne d'intégration et non en
local : voir §5.4.

### 5.3 Non-régression — la stack de développement n'a pas bougé

| Contrôle | Code | Ce qu'il a compté |
|---|---:|---|
| `make check` | **0** | **139** pytest + **27** Vitest, `images-check` et `env-check` compris |
| `make up` · `stack-check` | **0** | 8/8 sains, 7 publications déclarées / 7 réelles |
| `make api-check` · `web-check` | **0** | 3/3 endpoints · 6/6 contrôles de page |
| `make alembic-check` · `audit` · `docs-check` | **0** | 1 tête · « 1 high (1 ignored) » · 5 empreintes, 6 séquences |
| `make test-integration` | **0** | 8 exécutés |
| `make persistence-test` | **0** | **5 empreintes relevées, 5 comparées** |

---

## 6. Défauts détectés pendant `T7`

**Treize défauts. Dix étaient dans mes propres contrôles, mon script ou mon échafaudage** ; deux
étaient des défauts dormants du corpus ou de l'outillage, et un est une matérialisation de risque.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T7-1` | **`make up` a échoué et j'ai perdu du temps sur un message faux.** Le conteneur `caddy` voyait un `/etc/caddy` **vide** ; `caddy-reload` annonçait « configuration invalide ou service absent » alors que l'erreur réelle était « open /etc/caddy/Caddyfile: no such file or directory », **masquée par un `2>/dev/null`** | **Contrôle qui masque l'erreur dont on interprète le silence** — le piège de la passation §7.6, dans un contrôle que j'avais moi-même hérité de `T5` | Le masquage est retiré, et le contrôle **compare l'empreinte SHA-256 du `Caddyfile` vu par le conteneur à celle de l'hôte** avant de recharger. Nouvelle cible `make caddy-recreate`. Voir `T7-2` pour la cause |
| `T7-2` | **Cause de `T7-1` : `ROAD-RSK-026` s'est matérialisé une seconde fois.** Conteneur créé à **09:51:38** ; `ctime` de `infra/caddy` **et** de son `Caddyfile` à **10:06:49**, **sans aucune action de session**. Un conteneur neuf sur la même source voyait le fichier | **Matérialisation de risque, sur un mécanisme NOUVEAU.** `DEC-472` monte le **répertoire** et protège du remplacement du *fichier* — défaut `T5-2`. Cela ne protège **pas** du remplacement du *répertoire* : un conteneur ne re-résout pas la source d'un montage après sa création | Registre des risques complété. **Le garde-fou de `T5` a fonctionné** : la stack était `healthy` à 8/8 et servait une configuration de 09:51 ; c'est `caddy-reload` qui l'a arrêtée |
| `T7-3` | **J'ai écrit `DC="docker compose --env-file $PWD/.env …"` puis `$DC …`** — variable non citée, chemin à espace, **`code=127`**, la commande n'a jamais tourné | **Le piège §7.2, cinquième occurrence du projet**, et je l'avais cité dans mon propre rapport de prise en charge trois messages plus tôt | Fonction shell à chemins cités. **Et la parade structurelle :** le vérificateur de `T7` est en Python, avec `subprocess.run([...])` sans `shell=False` — le piège n'y **existe pas**. Le remède n'est pas la vigilance, c'est le choix d'un outil où l'erreur est impossible |
| `T7-4` | Mon détecteur de `latest` signalait **trois fois `runs-on: ubuntu-latest`**, qui est un **label d'exécuteur GitHub** et non une étiquette d'image | **Contrôle qui crie au loup sur son propre livrable.** Classe `T6-4` : un contrôle qui échoue pour une raison hors sujet finit désactivé | Deux motifs distincts — référence `<registre>/…:latest`, et étiquette nue dans une liste `ETIQUETTES` — avec témoins dans les deux sens. Les étiquettes **locales** de Compose sont explicitement tolérées, comme les conventions §4.1 le prévoient |
| `T7-5` | Mon **témoin positif** du détecteur d'étiquettes **échouait sur sa propre chaîne d'épreuve** : il n'y normalisait pas les guillemets, là où le contrôle réel le faisait | **Témoin qui n'exerce pas le même code que le contrôle** — classe `T3-3`, un test qui court-circuite le point d'entrée réel. Un tel témoin ne prouve rien du contrôle | **Une seule** implémentation, `liste_contient_latest()`, employée par le contrôle **et** par son témoin. Ils ne peuvent plus diverger |
| `T7-6` | **Mon contrôle de taille mesurait la mauvaise grandeur.** Il annonçait 109 Mio pour `api` là où `docker images` disait 473 Mo, et mes plafonds — calibrés sur la seconde — étaient **4,5 fois trop larges** : le contrôle n'aurait pas attrapé la régression qu'il vise | **Contrôle calibré sur une autre grandeur que celle qu'il affiche.** Il aurait passé quoi qu'il arrive | Diagnostic : `.Size` d'une variante rend la **taille de contenu**, `docker images` l'**usage disque**. Et l'usage disque n'est **pas comparable d'une plateforme à l'autre** — `--tree` donne 473 Mo pour `arm64` et 114 Mo pour `amd64` de la **même** image, seule la variante native étant dépaquetée. Plafonds recalibrés sur la taille de contenu, grandeur que `ROAD-RSK-030` visait réellement, et **éprouvés par témoin** |
| `T7-7` | Ma sonde fonctionnelle de l'`api` **échouait à 12/12** : le conteneur s'arrêtait. J'ai d'abord lu cela comme une panne de l'image | **C'était l'image qui avait raison.** Les 7 garde-fous du §20.3 refusaient de démarrer, faute de configuration. Mon extracteur de « variables obligatoires » avait par ailleurs répondu **0** parce qu'il ne cherchait que les champs **sans** `=` : ces sept ont un défaut **vide** | Configuration minimale fournie. **Et le défaut est devenu une preuve** : un contrôle dédié vérifie désormais que l'image **refuse de démarrer**, **nomme les 7 variables** et **ne divulgue aucune valeur** — le §20.3 éprouvé sur l'image publiée, ce qu'aucun test unitaire ne faisait |
| `T7-8` | **`.env` comptait 74 affectations contre 78 dans `.env.example`.** `APP_REVISION`, ajoutée en `T3`, `LOG_MAX_SIZE` et `LOG_MAX_FILES`, ajoutées en `T4`, n'y étaient **jamais arrivées** | **Défaut dormant depuis deux sous-étapes.** `make env` est idempotent **par conception** — il porte des secrets locaux — et ne peut donc pas réconcilier. Rien ne le vérifiait. Effet mesuré : Compose substituait une **chaîne vide** à `${APP_REVISION}`, et l'image de développement a été construite avec `APP_REVISION=""` | Les trois variables ajoutées au `.env` local. Compose emploie des **valeurs par défaut explicites**, `${APP_REVISION:-inconnue}`, pour qu'une absence dégrade honnêtement. **Et `make env-check` est créée** : elle compare les noms des deux fichiers, nomme les manquants, et refuse tout doublon dans le modèle. C'est `ECART-022` |
| `T7-9` | **J'ai écrit une empreinte SHA-256 inventée** dans `images.yml`, comme « garde-fou secondaire » de l'installation de Trivy — une valeur que je n'avais pas mesurée, et qui n'était même pas comparée | **Le pire de la liste, et sur un contrôle de sécurité.** Une empreinte fabriquée dans un fichier versionné donne l'apparence d'une vérification là où il n'y en a aucune | Remplacée par la valeur **relevée dans le fichier de sommes publié**, `bbb64b96…b2ea`, et **effectivement comparée**. L'indirection inutile est supprimée : la valeur attendue est inscrite dans le dépôt, comme `GITLEAKS_SHA256` en `T6`, et non relue au téléchargement depuis le même hôte que l'archive |
| `T7-10` | **Mon contrôle d'injection de version ne pouvait PAS passer sur une branche de travail.** Il exigeait que la version lue diffère de `0.0.0-dev`. Or `DEC-428` jalonne les versions sur les portes et les pose en **tags** : sur une branche comme sur `develop`, il n'existe **aucune version**, et le workflow publie honnêtement `0.0.0-dev`. **La valeur injectée EST le défaut.** Trouvé par l'exécution [30442686377](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/actions/runs/30442686377), qui a échoué sur une image parfaitement correcte | **Le défaut `T5-6` pris à l'envers** : un **succès** qui produit la même observation qu'un échec. La révision, elle, prouvait déjà que le mécanisme fonctionne — `revision='b07f46c'` et non `inconnue`. Publication et Trivy étaient verts ; seul mon contrôle mentait | Le contrôle compare désormais à **l'attendu**, ce qui est **plus fort** : il prouve que l'image porte **LA** version avec laquelle elle a été construite, et non seulement **UNE** version non nulle. Les attendus sont **obligatoires** — en leur absence le contrôle échoue au lieu de se dégrader en silence. Trois témoins : attendus justes → 39 verts ; attendu faux → échec ; attendus absents → échec |
| `T7-12` | **Le contrôle d'accès anonyme échouait sans produire une seule ligne de sortie.** Le journal de chaque étape porte `shell: /usr/bin/bash -e {0}` : **GitHub ajoute `-e` à l'invocation du shell**, et mon `set -uo pipefail` ne le retire pas. Un `cmd ; code=$?` fait donc sortir bash à l'échec de `cmd`, **avant** la lecture du code. Or c'est un contrôle dont **l'échec de la commande est le résultat attendu** | **SIXIÈME occurrence de la famille du code de sortie**, après `T0-1`, `T2-4`, `T3-6`, `T4-3` et `T5-5` — et la première dans un workflow, où la cause est un `-e` que je n'avais pas écrit. Trouvé par l'exécution [30450427925](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/actions/runs/30450427925) : publication et Trivy verts, seule mon étape rouge, et **muette** | Forme `cmd && code=0 \|\| code=$?`, qui soustrait cette commande — et elle seule — au `-e`. Éprouvée sous `bash -e` dans les deux sens : la nouvelle forme atteint la ligne suivante avec `code=1`, l'ancienne fait sortir bash avant. **Le remède structurel de `T7-3` ne couvrait pas ce cas** : le vérificateur Python est immunisé, mais les étapes de workflow restent du shell |
| `T7-13` | **Ma sonde du worker démarrait un Redis jetable et l'interrogeait sans attendre qu'il soit prêt.** En natif, Redis écoute avant que la sonde ne démarre, et le défaut reste **latent** ; **sous émulation QEMU il n'écoute pas encore**. Mesure du 29/07/2026, exécution [30451127513](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/actions/runs/30451127513) : `connect_check_health` a échoué sur `linux/arm64` alors que la **même** sonde passait sur `linux/amd64` | **Course dans mon propre contrôle**, et c'est exactement ce que `depends_on: service_healthy` existe pour éviter. La leçon de `T6-2` dans un autre habit : ma sonde n'avait jamais tourné qu'en natif, donc elle n'était pas éprouvée. Le livrable était correct — `api` passait 9/9 sur la même architecture émulée | Attente de la réponse `PONG`, **comptée et affichée** : « le Redis jetable répond PONG après *n* tentative(s) ». Mesures locales : 2 tentatives en `amd64` émulé, 1 en `arm64` natif. Le contrôle dit désormais combien il a attendu, ce qui rendra un ralentissement visible au lieu de silencieux |
| `T7-11` | **Un contrôle absent de ma première version du workflow.** Se connecter puis tirer prouve que l'authentification **fonctionne** ; cela ne prouve pas que le registre la **requiert**, ni que le paquet est privé. Or le critère de la story dit « l'accès au registre est **authentifié** » | **Preuve incomplète**, trouvée en relisant le critère et non par un échec. Et « le tirage anonyme a échoué » serait indistinguable de « l'image n'existe pas » — le piège `T2-1`, où un 429 masqué était lu comme une absence | Contrôle en **deux sens** : le tirage anonyme doit échouer **et** son message doit porter un motif d'**autorisation** — `unauthorized`, `denied`, `401`, `403` — puis le tirage authentifié doit réussir **sur la même référence**, ce qui prouve que l'image existe. Aucun des deux seul ne prouve rien |

### 6.1 Ce que ces treize défauts enseignent

**Dix sur treize étaient dans mes contrôles, mon script ou mon échafaudage — pas dans le livrable.**
La proportion est la plus élevée du lot, devant les cinq sur huit de `T5`. C'est la forme la plus
insidieuse : on croit avoir prouvé.

**Deux défauts se font face, et c'est instructif.** `T7-6` était un contrôle **qui passait toujours**
— plafond calibré sur une autre grandeur. `T7-10` était un contrôle **qui échouait toujours** sur une
situation légitime. Les deux sont la même erreur vue de deux côtés : *je n'avais pas déterminé quelle
valeur le succès doit produire, et laquelle l'échec*. La quatrième proposition de la règle du lot le
demandait ; je ne l'avais appliquée qu'au sens « l'échec produit-il autre chose que le succès », pas
au sens « le succès légitime produit-il bien ce que j'exige ».

**`T7-3` mérite un mot, parce qu'il est humiliant d'une façon utile.** J'ai commis le piège du
chemin à espace **après** l'avoir cité dans mon propre rapport de prise en charge, dans une section
qui s'appelait « discipline de contrôle ». C'est la leçon de `T6-5` rejouée : **un piège documenté
n'est pas un piège désarmé.** Mais `T7` en tire une conséquence que `T6` n'avait pas tirée — au
lieu de promettre plus de vigilance, j'ai déplacé les contrôles vers un outil où **le piège
n'existe pas**. `subprocess.run([...])` sans shell ne peut pas redécouper un chemin, et
`returncode` ne peut pas être celui d'un autre maillon. C'est la seule parade qui ne dépende pas de
ma mémoire.

**`T7-6` ajoute une variante aux quatre propositions de la règle.** Le contrôle pouvait échouer, on
lisait son code, il annonçait combien d'éléments il avait examinés, et l'échec aurait produit une
observation différente du succès. **Les quatre propositions étaient respectées.** Et il ne prouvait
rien, parce qu'il **comparait une mesure à un seuil exprimé dans une autre grandeur**. La question
qui manquait : *le nombre que j'affiche et le seuil auquel je le compare mesurent-ils la même
chose ?*

> **La règle du lot, augmentée d'une sixième proposition :**
> un contrôle qui compare deux nombres doit prouver qu'ils mesurent **la même grandeur**. Un seuil
> calibré sur une autre unité que la mesure passe toujours, ou échoue toujours.

**`T7-12` mérite d'être nommé pour ce qu'il dit du remède de `T7-3`.** J'avais écrit que la parade
au piège du code de sortie était de **changer d'outil** — et c'est vrai du vérificateur, qui est en
Python. Mais les étapes d'un workflow restent du shell, et celui-là m'a été imposé avec un `-e` que
je n'avais pas écrit. **Un remède structurel ne couvre que le périmètre où il s'applique**, et il
faut savoir dire où il s'arrête. C'est la sixième occurrence de cette famille sur ce projet.

**`T7-9` est d'une autre nature et il faut le nommer sans l'atténuer.** Écrire une empreinte
plausible plutôt que mesurée, c'est fabriquer la preuve au lieu de la produire. Aucune des cinq
propositions ne l'attrape : le contrôle aurait « fonctionné ». Seule la relecture de ce que je
venais d'écrire l'a attrapé.

---

## 7. Recommandations pour la suite

1. **`T8` doit sélectionner la cible `execution`** dans la surcouche de recette. `make
   images-check` **échoue** si une surcouche ne nomme aucune cible : le contrôle l'attend déjà.
2. **`T8` peut lever la réserve de `arm64` natif** sans nouveau droit, en tirant l'image publiée
   sur cette machine — après un `docker login ghcr.io` de Jonathan.
3. **`DEC-477` reste à reproduire** : le bucket MinIO avant que l'API doive être saine.
4. **Gisement mesuré, non traité :** `api` et `worker` embarquent `uv` et `uvx`, **55,1 Mio**, qui
   ne servent qu'à la construction. Trivy n'y trouve **aucune** vulnérabilité — le gisement est de
   poids seulement. Une étape de construction séparée les retirerait. Non fait, pour ne pas cumuler
   deux restructurations dans la même sous-étape.
5. **Ne pas ajouter « Porte des images multiarchitecture » aux contrôles requis** de la protection
   de branche. Voir §3.2 : elle bloquerait toute fusion pour toujours.

---

## 8. État à la sortie de `T7`

| | |
|---|---|
| Sous-étape | **`T7` terminée.** Story `MVP-L01-US006` prête pour validation, issue `#7` à refermer à la fusion |
| Décisions | `DEC-478` à `DEC-482`. Prochaine libre : **`DEC-483`** |
| Écarts | **`ECART-022` ouvert et clos.** Prochain libre : **`ECART-023`** |
| Risques | **`ROAD-RSK-030` et `ROAD-RSK-031` CLOS.** **`ROAD-RSK-033` ouvert**, résiduel accepté. `ROAD-RSK-026` **matérialisé une seconde fois**. Prochain libre : **`ROAD-RSK-034`** |
| Questions | Aucune nouvelle. Prochaine libre : `QO-115` |
| Dépendances | **Aucune ajoutée** — le socle Caddy était déjà dans le projet. Prochaine libre : `DEP-018` |
| Tests | **166** — 139 pytest (131 unitaires, 8 d'intégration) et 27 Vitest. Inchangé : `T7` n'ajoute pas de test unitaire, ses preuves sont des contrôles d'image |
| Cibles `Makefile` | **44** |
| Contrôles d'image | **39 fonctionnels**, 10 statiques, 12 témoins négatifs |
| `make check` · `stack-check` · `api-check` · `web-check` · `alembic-check` · `audit` · `docs-check` · `test-integration` · `persistence-test` · `images-check` · `images-inspect` · `images-verify` · `env-check` | Tous **code 0** |

### Les 7 critères de la porte `G1`

| | Critère | État |
|:--:|---|---|
| ☑ | Tous les services démarrent sur le Mac M5 | `T2`, et sur une machine propre depuis `T6` |
| ☑ | **Les images multiarchitectures sont construites** | **`T7` — et elles sont LANCÉES sur les deux architectures** |
| ☑ | Aucun secret réel n'est présent | vérifié automatiquement depuis `T6`. **`T7` n'a créé aucun secret de dépôt** |
| ☑ | Une migration Alembic vide ou initiale s'exécute | `T3`, rejouée à chaque pull request |
| ☑ | Les logs possèdent un identifiant de corrélation | `T4` |
| ☑ | La CI bloque une erreur de lint, de test et de secret | `T6`, prouvé trois fois |
| ☐ | Jonathan valide le socle | `T11` |

**Les six critères techniques de la porte `G1` sont acquis.** Il ne reste que la validation de
Jonathan, en `T11`.

### Ce qui attend `T8`

Environnement de recette isolé, story `MVP-L01-US002`. Quatre apports de `T7` y entrent
directement : la cible `execution` **à sélectionner**, `DEC-477` **à reproduire**, la réserve de
`arm64` natif **à lever**, et la mesure de deux environnements simultanés qui refermera `QO-085`.
