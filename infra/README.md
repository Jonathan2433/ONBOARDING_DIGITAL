# `infra` — infrastructure locale

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §15.4, §22.2, §22.3

---

## 1. État actuel

La stack de **développement** est complète depuis `T2` : `make up` démarre les huit services et
les attend sains. La surcouche de **recette** arrive en `T8`.

```text
infra/
├── scripts/
│   ├── exclure-icloud.sh          ← T1. Applique DEC-439 et DEC-453
│   ├── verifier-ports.sh          ← T2. Applique DEC-460
│   └── verifier-persistance.sh    ← T2. Prouve la survie des volumes
├── compose/
│   ├── docker-compose.base.yml    ← T2. Les 8 services, volumes, réseau, santé
│   ├── docker-compose.dev.yml     ← T2. Surcouche onboarding-dev
│   └── docker-compose.recette.yml ← T8
└── caddy/
    └── Caddyfile                  ← T2. tls internal (DEC-446)
```

Ni `postgres/init/` ni `minio/` n'existent, et c'est délibéré. Les extensions PostgreSQL
relèvent de la **migration `0001_initial`** en `T3`, pas d'un script d'initialisation : le
cahier §16.2 veut des migrations explicites, et une extension créée par `initdb` échapperait à
Alembic. Le bucket MinIO est créé par `make minio-bucket`, cible idempotente appelée par
`make up`.

## 2. Commandes

```bash
make env               # creer le .env local, secrets generes (DEC-461)
make up                # construire, demarrer, attendre sain, creer le bucket, controler
make ps                # etat des conteneurs
make logs              # suivre les journaux
make stack-check       # sante des 8 services + publication des ports
make persistence-test  # prouver que les volumes survivent a un redemarrage
make down              # arreter — LES VOLUMES SONT CONSERVES
make destroy           # arreter ET supprimer les volumes (demande confirmation)
```

### Ports publiés, tous sur `127.0.0.1` uniquement

| Service | Port hôte | Usage |
|---|---:|---|
| caddy | 80, 443 | `app.onboarding.localhost`, `api.onboarding.localhost` |
| db | 5432 | `psql` depuis la machine |
| redis | 6379 | `redis-cli` depuis la machine |
| minio | 9000, 9001 | API S3, console web |
| mailpit | 8025 | interface web des e-mails capturés |

`make ports` **échoue** si l'un de ces ports est publié ailleurs que sur la boucle locale, ou
si les publications déclarées et réelles ne concordent pas.

> **La racine de l'autorité interne de Caddy doit être approuvée une fois dans le trousseau
> macOS.** C'est une action de Jonathan : elle demande son mot de passe. Sans elle, un client
> strict refuse le certificat de `app.onboarding.localhost`.

## 3. Décisions qui contraignent ce répertoire

| Décision | Contrainte |
|---|---|
| `DEC-444` | Compose **base + surcouches**. `COMPOSE_PROJECT_NAME` distinct : `onboarding-dev`, `onboarding-recette`, `onboarding-prod-local` |
| `DEC-443` | Images épinglées en `majeur.mineur` **et par empreinte `sha256`** dans les `Dockerfile`. Jamais `latest` seul |
| `DEC-446` | Caddy en `tls internal` sur `app.onboarding.localhost` et `api.onboarding.localhost`. macOS résout `.localhost` sans toucher à `/etc/hosts` |
| `DEC-447` | **Volumes nommés exclusivement.** Aucun bind mount de donnée d'état vers `./data`, `./volumes` ou `./backups`. Les bind mounts de code source pour le rechargement à chaud restent autorisés |
| `DEC-440` | **Un seul environnement à la fois.** Limites mémoire par service : Docker ne dispose que de 7,75 Gio |

Les sept séparations exigées par le cahier §22.2 — projet Docker, base
PostgreSQL, bucket MinIO, volumes, secrets, réseau, ports — doivent être
explicites. Le `COMPOSE_PROJECT_NAME` n'en couvre automatiquement que deux.

**PostgreSQL, Redis, MinIO et Mailpit ne sont jamais exposés publiquement.**

## 4. `scripts/exclure-icloud.sh`

Applique `DEC-439` : marque `node_modules`, `.venv` et les caches d'un attribut
étendu qui les exclut de la synchronisation iCloud.

Appelé à deux endroits, et c'est délibéré : par `make icloud-exclude`, **et**
par le `postinstall` de `package.json`. Mesure du 27/07/2026 : `pnpm install`
supprime et recrée les `node_modules`, ce qui efface l'attribut. Sans le
`postinstall`, une installation lancée hors `make` rouvrirait silencieusement
le risque `ROAD-RSK-026`.

```bash
make icloud-exclude   # poser
make icloud-verify    # verifier, echoue si un repertoire n'est pas marque
```
