# Compte rendu — sous-étape `T2` du LOT 1

**Exécutée le :** 28 juillet 2026
**Objet :** Compose développement — les huit services démarrent et sont sains
**Story :** `MVP-L01-US002`, issue [#3](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/3)
**Fondement :** [fiche du LOT 1](fiche-lot-1.md) §3 ; cahier des charges §15.4, §22.2, §22.3
**Décisions produites :** `DEC-458` à `DEC-461`

---

## 1. Critère d'acceptation, et ce qui le prouve

> « PostgreSQL, Redis, MinIO, Mailpit, Caddy, web, API et worker démarrent avec une
> commande ; les volumes survivent au redémarrage. » — backlog, littéral

| Moitié du critère | Preuve | Code de sortie |
|---|---|---:|
| Les 8 services démarrent avec **une** commande | `make up` : construit, démarre, attend l'état sain, crée le bucket, contrôle santé et ports | **0** |
| Les volumes survivent au redémarrage | `make persistence-test` : relève 5 empreintes, arrête, redémarre, compare | **0** |

`make health` énumère les huit services et **échoue si l'un n'est pas `healthy`**.
`make ports` vérifie les publications. `make persistence-test` est rejouable.

---

## 2. Ce qui a été livré

| Emplacement | Contenu |
|---|---|
| `infra/compose/docker-compose.base.yml` | Les 8 services, volumes nommés, réseau, healthchecks, limites mémoire |
| `infra/compose/docker-compose.dev.yml` | Surcouche `onboarding-dev` : publication des ports sur la boucle locale |
| `infra/caddy/Caddyfile` | `tls internal` sur `app.` et `api.onboarding.localhost`, API d'administration pour le healthcheck |
| `apps/{api,worker,web}/Dockerfile` | Images multi-étapes, bases épinglées par empreinte, utilisateur non privilégié |
| `infra/scripts/verifier-ports.sh` | Contrôle des publications, déclarées **et** réelles |
| `infra/scripts/verifier-persistance.sh` | Preuve de survie des volumes, modes `capture` et `compare` |
| `Makefile` | 11 cibles ajoutées : `env`, `up`, `down`, `destroy`, `ps`, `logs`, `health`, `ports`, `minio-bucket`, `stack-check`, `persistence-test` |

`.env.example` **n'a pas eu besoin d'être complété** : les 74 variables du LOT 0 couvraient
exactement ce dont Compose avait besoin, `POSTGRES_HOST_PORT` et `REDIS_HOST_PORT` compris.
`ECART-006` reste donc ouvert et se refermera en `T3`, quand l'API lira sa configuration.

---

## 3. Les huit images, toutes épinglées

Empreintes relevées le 28/07/2026, **toutes vérifiées `linux/amd64` ET `linux/arm64`**
(cahier §22.3). **Zéro référence à `latest`**, seule ou non — contrôlé, pas supposé.

| Service | Référence | Registre |
|---|---|---|
| db | `postgres:17.7` | Docker Hub |
| redis | `redis:8.4-alpine` | Docker Hub |
| minio | `minio:RELEASE.2025-09-07T16-13-09Z` | **quay.io** |
| mailpit | `mailpit:v1.30` | **ghcr.io** |
| caddy | `caddy:2.11-alpine` | Docker Hub |
| api, worker | `python:3.12-slim` | Docker Hub |
| web | `node:24.16-alpine` | Docker Hub |
| (construction api, worker) | `ghcr.io/astral-sh/uv:0.11.32` | ghcr.io |

Deux choix méritent leur motif.

**PostgreSQL en Debian, pas en Alpine.** Alpine repose sur musl, dont la gestion des locales
est réduite. Ce socle portera un trombinoscope de noms français accentués et les index de
recherche du cahier §26.1 ; la collation ne se change pas après coup sans recréer le cluster.
Le choix du fournisseur de collation lui-même relève du LOT 2 : `QO-111` est ouverte plutôt que
tranchée ici, pour ne pas inventer une décision.

**Python en `slim`, pas en Alpine.** De nombreuses roues Python n'existent pas en musl, ce qui
forcerait une compilation depuis les sources à chaque installation — `psycopg` et les
dépendances du LOT 2 en bénéficieront.

---

## 4. Contrôles exécutés

### 4.1 Santé, ports, persistance

| Contrôle | Résultat | Témoin négatif |
|---|---|---|
| `make health` | **8/8 sains** | Un service absent ou non sain fait sortir en ≠ 0 |
| `make ports` | **7 publications déclarées, 7 réelles, toutes sur la boucle locale** | Le script échoue si les deux vues ne concordent pas |
| `make persistence-test` | **5/5 empreintes identiques, 5 comparées sur 5** | **Suppression réelle du volume `redis-data` → contrôle en échec, code 1** |
| `make minio-bucket` | Idempotent, 2 exécutions à 0 | `mc stat` sur un bucket inexistant → code 1 |

Le témoin négatif de la persistance a été **réellement exécuté** : le volume `redis-data` a été
supprimé, la stack redémarrée, et le contrôle a signalé `redis PERDU`. Seul ce volume a été
détruit — `caddy-data` porte l'autorité de certification interne, et sa perte obligerait
Jonathan à réapprouver la racine dans son trousseau.

### 4.2 HTTPS local (`DEC-446`)

| Contrôle | Résultat |
|---|---|
| `app.onboarding.localhost` et `api.onboarding.localhost` résolus | **127.0.0.1**, et `/etc/hosts` **n'a pas été modifié** — 0 occurrence |
| TLS servi par Caddy | Émetteur : `CN=Caddy Local Authority - ECC Intermediate` |
| Réponse HTTP | **502**, attendu : `api` et `web` n'écoutent pas avant `T3` et `T5` |
| Racine approuvée dans le trousseau | **Non**, et c'est normal : c'est l'action de Jonathan, elle demande son mot de passe |

### 4.3 Mémoire — élément de réponse à `QO-085`

Projet tiers `observatoire-ecom-studio` arrêté par `docker compose stop` — conteneurs et volume
`observatoire-ecom-studio_pgdata` **préservés**, redémarrage par `docker compose -p
observatoire-ecom-studio start`. Budget rendu : **7,75 Gio en totalité**.

| Service | Consommation | Limite appliquée |
|---|---:|---:|
| minio | 84,96 Mio | 1 024 Mio |
| db | 19,35 Mio | 1 024 Mio |
| caddy | 15,36 Mio | 256 Mio |
| mailpit | 13,25 Mio | 256 Mio |
| redis | 10,71 Mio | 512 Mio |
| api | 672 Kio | 1 024 Mio |
| worker | 672 Kio | 1 024 Mio |
| web | 556 Kio | 1 024 Mio |
| **Total** | **146 Mio, soit 2 % du budget** | 6 144 Mio déclarés |

Les huit limites de `DEC-440` sont **effectivement appliquées** : lecture de
`HostConfig.Memory` sur chaque conteneur, pas de la déclaration.

> **Cette mesure est un plancher, pas la charge réelle.** `api`, `worker` et `web` tiennent
> 672 Kio parce qu'ils exécutent un processus d'attente : leur code applicatif arrive en `T3`
> et `T5`. Uvicorn, Dramatiq et Vite changeront l'ordre de grandeur. `QO-085` reste ouverte, et
> la mesure qui compte se fera après `T5`.

### 4.4 Isolation et sécurité

- **Aucune exposition publique.** Les 7 publications sont liées à `127.0.0.1`. Sans ce préfixe
  explicite, Docker publie sur toutes les interfaces et contourne le pare-feu de macOS.
- **Un seul bind mount**, le `Caddyfile`, en **lecture seule** — de la configuration, pas une
  donnée d'état (`DEC-447`).
- **Six volumes nommés**, tous préfixés `onboarding-dev_`, donc distincts par environnement.
- **Utilisateur non privilégié** dans les trois images applicatives.
- **Aucune table créée.** La seule migration du lot reste `0001_initial`, en `T3`.

---

## 5. Défauts détectés pendant `T2`

Sept défauts, dont **quatre étaient des contrôles menteurs**. C'est le cas le plus dangereux :
le livrable est bon, mais on croit l'avoir prouvé.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T2-1` | Ma sonde d'empreintes d'images signalait `caddy:2-alpine` et `mailpit` **ABSENTS**. Le registre renvoyait en réalité **429 Too Many Requests** : mon `2>/dev/null` masquait la limite de débit anonyme de Docker Hub | **Contrôle menteur.** J'aurais conclu que des images officielles n'existent pas | Erreur lue au lieu d'être supprimée. Images résolues depuis quay.io et ghcr.io, non soumis à cette limite |
| `T2-2` | Le `postinstall` de `package.json` appelait `bash`, absent de l'image `node:alpine` : la construction de l'image web échouait | **Livrable incomplet.** J'avais converti le script en `sh` POSIX et corrigé le `Makefile`, **en oubliant `package.json`** | `sh` partout. Le script vérifié en POSIX, avec témoin négatif sur un faux `uname` renvoyant `Linux` |
| `T2-3` | `make health` et `make minio-bucket` échouaient sur `couldn't find env file: /Users/.../Library/Mobile` | **Chemin non cité.** Le dépôt vit sous `~/Library/Mobile Documents/` : `$(CURDIR)` contient une espace | `--env-file "$(ENV_FILE)"` cité, et le piège commenté dans le `Makefile` |
| `T2-4` | `make ports` annonçait « aucune publication hors de 127.0.0.1 » **en n'ayant examiné que 5 publications sur 7** : mon découpage de la colonne `PORTS` de `docker ps` ne gardait que la première par conteneur, et MinIO en a deux | **Contrôle menteur, et le plus grave des sept** : il portait sur un contrôle de sécurité | Réécrit en script dédié qui compare les publications **déclarées** et **réelles**, et **échoue si les deux nombres ne concordent pas** |
| `T2-5` | Le témoin Mailpit de la persistance relevait `{"total":0,...}`. Un volume **effacé** aurait rendu la même valeur | **Contrôle incapable d'échouer.** La comparaison aurait conclu « identique » sur du vide | La capture dépose un vrai message par SMTP depuis le conteneur `api`, et **refuse de continuer si le total reste nul** |
| `T2-6` | Le contrôle de persistance affichait `db identique` puis « **les 5 volumes ont survécu** ». Il en avait vérifié **un**. Les `docker compose exec` de la boucle consommaient l'entrée standard et avalaient le reste du relevé | **Contrôle menteur.** Il affirmait cinq en ayant regardé un | Lecture sur le descripteur 3, `</dev/null` sur les commandes internes, et **compteur d'empreintes comparées confronté au nombre attendu** |
| `T2-7` | `MINIO_BUCKET` n'était pas passé au conteneur MinIO : le chemin devenait `local//temoin.txt`, et `mc` répondait « Object name cannot be empty » | Livrable incomplet | Variable ajoutée au service. Les commandes `mc` d'exploitation s'écrivent désormais sans que l'opérateur retrouve le nom du bucket — utile pour `T9` |

### 5.1 Ce que ces sept défauts disent

Quatre sur sept — `T2-1`, `T2-4`, `T2-5`, `T2-6` — étaient des contrôles qui affirmaient plus
qu'ils ne vérifiaient. Deux d'entre eux portaient sur des exigences du cahier : la non-exposition
des services et la survie des volumes.

La parade employée est la même à chaque fois, et elle est généralisable : **compter, et
confronter le compte à un attendu**. `make ports` compare déclarées et réelles ;
`verifier-persistance.sh` compare examinées et relevées ; la boucle de `T1-1` comparait
itérations et cibles. Un contrôle qui n'annonce pas combien d'éléments il a examinés peut
toujours en avoir examiné un seul.

---

## 6. État à la sortie de `T2`

| | |
|---|---|
| Sous-étape | **`T2` terminée.** Story `MVP-L01-US002` prête pour validation |
| Décisions | `DEC-458` à `DEC-461`. Prochaine libre : **`DEC-462`** |
| Écarts | `ECART-019` ouvert et clos. `ECART-006` **reste ouvert**, se refermera en `T3`. Prochain libre : **`ECART-020`** |
| Risques | `ROAD-RSK-030` ouvert — image `web` de 924 Mio. Prochain libre : **`ROAD-RSK-031`** |
| Questions | **`QO-111` ouverte** — fournisseur de collation PostgreSQL, à trancher au LOT 2. `QO-085` complétée, non close. Prochaine libre : **`QO-112`** |
| `make check` | Vert, code 0 — la chaîne de `T1` n'a pas régressé |
| `make stack-check` | Vert, code 0 |
| Sous-étape suivante | **`T3`** — API FastAPI, 3 healthchecks, migration `0001_initial`, story `MVP-L01-US003`, issue `#4` |

**Deux points d'attention pour `T3`.**

1. **La racine de Caddy n'est pas approuvée** dans le trousseau macOS. Tant qu'elle ne l'est
   pas, un client strict refusera le certificat. C'est l'action de Jonathan.
2. **Le projet tiers est arrêté** et doit le rester pendant le lot (`DEC-440`). Sa remise en
   route : `docker compose -p observatoire-ecom-studio start`.
