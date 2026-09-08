# `infra` — infrastructure locale

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §15.4, §22.2, §22.3
**Dernière mise à jour :** 7 septembre 2026, `T5` du LOT 5

---

## 1. État actuel

**Deux environnements locaux, isolés et prouvés.** `make up` lève les huit services du
développement ; `make up-recette` lève les huit de la recette **sur les images publiées dans
GHCR**, épinglées par empreinte. Les **sept** séparations du cahier §22.2 sont vérifiées sur
l'**état réel** — jamais sur un fichier `.env`.

```text
infra/
├── compose/
│   ├── docker-compose.base.yml     les 8 services, volumes, reseau, sante
│   ├── docker-compose.dev.yml      surcouche onboarding-dev
│   ├── docker-compose.recette.yml  surcouche onboarding-recette, cible `execution`
│   └── differences-recette.env     CALQUE versionne, aucune valeur sensible
├── caddy/
│   └── Caddyfile                   tls internal, UNE seule origine (DEC-446, DEC-470)
└── scripts/                        42 scripts : 32 `verifier-*`, 4 `provisionner-*`
```

**Les nombres se dérivent, ils ne se recopient pas** — ce README a annoncé « 3 scripts » pendant
treize mois :

```bash
ls infra/scripts/ | grep -cE '\.(py|sh)$'      # 42
ls infra/scripts/ | grep -cE '^verifier-'      # 32
grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile      # 85 cibles documentees
```

> **Ni `postgres/init/` ni `minio/` n'existent, et c'est délibéré.** Les extensions PostgreSQL
> relèvent d'une **migration** (`0002`), pas d'un script d'initialisation : une extension créée par
> `initdb` échapperait à Alembic. Le bucket MinIO est créé par `make minio-bucket`, cible
> idempotente appelée par `make up`.

---

## 2. Les scripts sont en PYTHON, et c'est un remède, pas un goût

**37 des 42 sont en Python**, avec `subprocess.run([...])` et **sans `shell=True`**. Le motif est
mesuré, et il tient à une classe d'erreur qui a résisté à la vigilance **quatre fois** :

**Le dépôt vit sous `~/Library/Mobile Documents/`, donc `$(CURDIR)` contient une espace.**

```bash
# CE QUI CASSE, et le message n'accuse pas la bonne chose :
DC="docker compose --env-file $PWD/.env -f base.yml"    # code=127, la commande n'a JAMAIS tourne
eval docker compose $FICHIERS "$@"                       # eval redecoupe les arguments

# CE QUI TIENT : une FONCTION shell, jamais une variable
dc() { docker compose --env-file "$PWD/.env" -f base.yml -f dev.yml "$@"; }
```

En Python, les arguments sont passés tels quels : **aucune redécoupe n'a lieu**, et `returncode` ne
peut pas être celui d'un autre maillon d'un tuyau. **Le piège n'y existe pas.**

> **Quand une classe d'erreur résiste à la vigilance, change d'outil au lieu de promettre d'être
> plus attentif.** Ce piège a été commis quatre fois, dont deux par un agent qui l'avait lu **le
> jour même**.

**Et le remède a une limite, qu'il faut savoir dire :** les étapes d'un workflow GitHub Actions
restent du shell, avec un `-e` qu'on n'a pas écrit — `shell: /usr/bin/bash -e {0}`. Un
`commande ; code=$?` y fait sortir bash **à l'échec, avant la lecture du code**. Pour une commande
dont l'échec est le résultat **attendu** :

```bash
sortie=$(commande 2>&1) && code=0 || code=$?
```

---

## 3. Commandes

```bash
make env               # creer le .env local, 7 secrets generes (DEC-461)
make env-check         # .env contre .env.example — il NOMME les manquantes
make up                # construire, demarrer, attendre sain, bucket, 3 roles, recharger Caddy
make stack-check       # sante des 8 services + publication des ports
make persistence-test  # prouver que les volumes survivent a un redemarrage
make down              # arreter — LES VOLUMES SONT CONSERVES
make destroy           # arreter ET supprimer les volumes (demande confirmation)

make up-recette        # la recette, sur les images PUBLIEES
make separations-check  # les 7 separations du §22.2, sur l'etat REEL
make caddy-recreate    # le seul geste qui repare un montage lie perime
```

> **`make up` fait trois choses de plus que démarrer, et chacune a coûté un défaut :**
>
> 1. **le bucket MinIO est créé AVANT que l'API doive être saine** (`DEC-477`). Sa sonde `ready`
>    fait un `head_bucket` : sans bucket elle répond 503, `api` n'est jamais sain, et `up --wait`
>    échoue. En local le volume survit à `make down`, donc **le défaut ne pouvait pas se montrer**
>    — il a fallu un exécuteur neuf pour le révéler ;
> 2. **les trois rôles PostgreSQL** du moindre privilège sont provisionnés (`DEC-520`) ;
> 3. **Caddy est rechargé.** Il **ne surveille pas** son fichier de configuration, et Compose ne
>    recrée pas un conteneur quand seul le **contenu** d'un fichier monté change (`DEC-472`).

### Ports publiés, tous sur `127.0.0.1` uniquement

**Sept publications en développement**, sept en recette. Les compter, jamais les recopier :

```bash
docker compose --env-file "$PWD/.env" \
  -f infra/compose/docker-compose.base.yml \
  -f infra/compose/docker-compose.dev.yml config | grep -c 'published:'
```

| Service | Port hôte | Usage |
|---|---:|---|
| caddy | 80, 443 | `app.onboarding.localhost`, `api.onboarding.localhost` |
| db | 5432 | `psql` depuis la machine |
| redis | 6379 | `redis-cli` depuis la machine |
| minio | 9000, 9001 | API S3, console web |
| mailpit | 8025 | interface web des e-mails capturés |

**`make ports` confronte DEUX sources** : les conteneurs existants **et** la configuration Compose
assemblée. Le motif est mesuré : `make down` **supprime** les conteneurs, si bien qu'un
environnement arrêté ne déclare plus rien — la première version du contrôle était **aveugle au
défaut qui l'a fait naître**.

> **Un conteneur ARRÊTÉ déclare ses ports sans en occuper aucun.** En choisissant la bande de ports
> de la recette, `lsof` disait `8080` libre : il regardait **ce qui écoutait**. Un projet tiers
> arrêté le **réclamait** depuis toujours, et sa relance a rendu
> `Bind for 127.0.0.1:8080 failed: port is already allocated`. **Quand tu mesures une ressource
> partagée, demande-toi qui la RÉCLAME, pas seulement qui la détient.**

---

## 4. Décisions qui contraignent ce répertoire

| Décision | Contrainte |
|---|---|
| `DEC-444` | Compose **base + surcouches**. `COMPOSE_PROJECT_NAME` distinct : `onboarding-dev`, `onboarding-recette`, `onboarding-prod-local` |
| `DEC-443`, `DEC-458` | Images épinglées en `majeur.mineur` **et par empreinte `sha256`**. Jamais `latest` seul |
| `DEC-446`, `DEC-470` | Caddy en `tls internal`, et **UNE seule origine** : `app.onboarding.localhost` mandate `/health/*` et `/api/*` vers l'API. Ni CORS, ni proxy Vite — c'est ce qui rend les cookies `Secure` et `SameSite` éprouvables |
| `DEC-447` | **Volumes nommés exclusivement.** Bind mount de **configuration** en lecture seule toléré |
| `DEC-460` | **Publications sur `127.0.0.1` uniquement.** `make ports` le vérifie |
| `DEC-472` | Le `Caddyfile` est monté **par son répertoire**, et `make up` **recharge** Caddy |
| `DEC-479` | Image `web` à **deux cibles nommées**. Chaque surcouche **nomme sa cible**, `make images-check` échoue sinon |
| `DEC-485` | Les **15 cibles de stack** sont paramétrées par `ENVIRONNEMENT`, dont `dev` est le défaut. Les alias **délèguent** et ne portent aucune logique propre |
| `DEC-440` | **Un seul environnement à la fois.** `make separations-check` est une exception **bornée et motivée** : l'épreuve d'isolement serait sans valeur si la cible était arrêtée |

**PostgreSQL, Redis, MinIO et Mailpit ne sont jamais exposés publiquement.**

---

## 5. Les pièges d'infrastructure, tous rencontrés

### Un bind mount de FICHIER unique épingle l'inode

La plupart des éditeurs écrivent un temporaire puis renomment, ce qui produit un **inode neuf**. Le
conteneur continue de pointer vers l'ancien : `ls` affiche encore l'entrée, mais toute ouverture
répond « No such file or directory ». Mesuré : le conteneur voyait un `Caddyfile` de **1 573 octets**
quand l'hôte en portait **2 844**, et Caddy servait une configuration périmée **en étant
`healthy`**.

```yaml
- ../caddy:/etc/caddy:ro                       # le REPERTOIRE : resolu a chaque ouverture
- ../caddy/Caddyfile:/etc/caddy/Caddyfile:ro   # le FICHIER : epingle l'inode, ne fais plus ca
```

### Monter le répertoire ne suffit pas : **iCloud remplace aussi les répertoires**

Un conteneur ne **re-résout pas** la source d'un montage lié après sa création. Mesuré le
29/07/2026 : le `ctime` de `infra/caddy` **et** de son `Caddyfile` avait changé **15 minutes après**
la création du conteneur, **sans aucune action de session**. Les huit services étaient `healthy`.

```bash
make caddy-recreate   # le seul geste qui repare : le conteneur re-resout son montage
```

`caddy-reload` compare désormais l'**empreinte SHA-256** du fichier vu par le conteneur à celle de
l'hôte, et **ne masque plus son erreur** — elle annonçait « configuration invalide ou service
absent » là où le message réel était « no such file or directory ».

### Publier un port perce l'isolement inter-réseaux de Docker

`ROAD-RSK-034`, mesuré sur un **même conteneur**, ce qui élimine toute cause propre à un service :

| Cible | Publié sur l'hôte ? | Depuis la recette |
|---|---|---|
| `dev mailpit 172.20.0.4:8025` | **oui** | **JOIGNABLE** |
| `dev mailpit 172.20.0.4:1025` | non | `TimeoutError` |

La règle `ACCEPT` d'un port publié **précède** les règles `DOCKER-ISOLATION`. Le préfixe
`127.0.0.1` protège du réseau local et du pare-feu de macOS ; il ne protège **pas** d'un autre
réseau Docker de la même machine.

**Le cahier §22.2 exige un réseau distinct, pas l'inatteignabilité mutuelle.** Le contrôle **exige**
ce qui est exigible, **rapporte visiblement** ce qui ne l'est pas, et **exige la barrière** qui rend
le résiduel acceptable : avec le mot de passe de la recette, la base de développement **refuse**.
Une barrière qui rend un résiduel acceptable doit être un **contrôle**, jamais une affirmation.

### `sed -i ''` fonctionne sur macOS et **échoue en code 2** sur GNU

Tout ce qui est écrit ici tourne **aussi** sur un exécuteur Linux. Deux pièges mesurés :

| Sur macOS | Sur Linux |
|---|---|
| `sed -i ''` fonctionne | GNU sed lit le script comme un nom de fichier. Emploie `sed … > f.tmp && mv f.tmp f` |
| `app.onboarding.localhost` se résout | **`gaierror`, aucune adresse.** Linux ne résout pas les sous-domaines de `.localhost` — le workflow pose deux lignes dans `/etc/hosts` |

### L'image MinIO n'a pas `grep`, et Docker Hub limite le débit

`mc stat`, jamais `mc ls | grep`. `base64` **est** présent — vérifié avant emploi, parce que
supposer coûte un cycle. Et MinIO vient de **quay.io**, Mailpit de **ghcr.io** : leurs registres de
publication, non limités. **Si une inspection d'image échoue, lis l'erreur** avant de conclure à une
absence — un `429 Too Many Requests` masqué a déjà été lu comme « image inexistante ».

---

## 6. `scripts/exclure-icloud.sh` et les garde-fous iCloud

Applique `DEC-439` : marque `node_modules`, `.venv` et les caches d'un attribut étendu qui les
exclut de la synchronisation iCloud.

**Appelé à deux endroits, et c'est délibéré** : par `make icloud-exclude`, **et** par le
`postinstall` de `package.json`. Mesure du 27/07/2026 : `pnpm install` supprime et recrée les
`node_modules`, ce qui **efface l'attribut**.

```bash
make icloud-verify    # PAS une formalite : lance-la en debut de session
make sources-check    # aucun fichier source du disque n'est ignore par git
```

**`make icloud-verify` couvre TROIS modes de défaillance, et chacun a été payé :**

| Mode | Ce qui s'est passé |
|---|---|
| **copies de conflit** | un `node_modules 2` de 178 Mio, puis **142 copies de fichiers** dont **115 sont entrées dans un commit**. Le motif `* [0-9]` avait été écrit contre une copie de **répertoire** et n'a **jamais rien couvert pour les fichiers** — quatre motifs sont désormais posés, et le garde-fou **exige** que `git check-ignore` honore **quatre noms témoins** |
| **réversion silencieuse** | quatre fichiers **remis à une version antérieure**, même mtime à la seconde, **sans aucune action de session**. Le garde-fou passait au vert : il ne cherchait que les copies. Il compare désormais le contenu de travail aux versions de l'historique |
| **profondeur** | le `find` s'arrêtait à `-maxdepth 3` quand les copies étaient à la profondeur 4. **Un contrôle borné doit dire où il s'arrête** |

> **`make sources-check` existe pour une raison distincte, et elle vaut d'être connue : tous les
> contrôles lisent le DISQUE, git lit son INDEX.** Le motif `media/` de `.gitignore`, écrit au
> LOT 0 contre les médias déposés, attrapait `apps/api/app/media/` — un **module source**. Le
> module a été écrit, testé, `make check` est sorti en **0**, et `git add -A` **ne l'a pas
> ajouté**. Les huit motifs de données locales sont désormais **ancrés à la racine** ; ceux de
> vrais artefacts produits à toute profondeur — `dist/`, `node_modules/`, les caches — restent non
> ancrés, parce que c'est leur intention.
