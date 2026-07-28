# `infra` — infrastructure locale

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §15.4, §22.2, §22.3

---

## 1. État actuel

Seul [`scripts/`](scripts/) est peuplé. Les fichiers Compose, la configuration
Caddy et les initialisations PostgreSQL et MinIO arrivent en `T2`.

## 2. Contenu prévu

```text
infra/
├── scripts/
│   └── exclure-icloud.sh        ← T1. Applique DEC-439
├── compose/                     ← T2, T8
│   ├── docker-compose.base.yml
│   ├── docker-compose.dev.yml
│   └── docker-compose.recette.yml
├── caddy/Caddyfile              ← T2. tls internal (DEC-446)
├── postgres/init/               ← T2
└── minio/                       ← T2
```

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
