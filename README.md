# eXalt Onboarding Digital

Plateforme interne de découverte de l'organisation eXalt et d'onboarding des nouveaux
arrivants. Multi-entités dès le MVP, contenu initial pour Bordeaux.

- **Dépôt :** privé — `Jonathan2433/ONBOARDING_DIGITAL`
- **Décideurs :** Léa pour le produit et le métier ; Jonathan pour la technique et l'exploitation
- **Mode de réalisation :** lots successifs, avec validation explicite de Jonathan avant
  l'ouverture du lot suivant

---

## 1. État d'avancement

| Élément | Valeur |
|---|---|
| Lots verrouillés | **LOTS 0 à 8** — de `G0` (27/07/2026) à **`G8` (07/10/2026, `DEC-634`, `v0.8.0`)** |
| Dernière porte franchie | **`G8`** — les six critères du LOT 8 sont acquis, dont un (vidéo) classé sans objet, et Jonathan a validé l'accueil et les événements — [checklist](docs/operations/checklist-validation-G8.md) |
| **Lot en cours** | **LOT 9 — Back-office, administration et import CSV**, ouvert le 08/10/2026 (`DEC-635`) |
| Sous-étape en cours | **`T3` — modification structurante et transitions** sur un collaborateur. `T1`/`T2` livrées : les quatre tables de l'import, puis `POST …/people` (création) |
| Lots 10 à 14 | `Planned` — aucun travail anticipé autorisé |
| Passation | [`CLAUDE.md`](CLAUDE.md) — état, méthode et les leçons payées par les défauts nommés. **Les deux nombres se dérivent**, voir son §7 : les recopier ici les ferait vieillir au premier ajout |

**Ce que la plateforme fait aujourd'hui.** Elle démarre, répond, s'affiche, elle est empaquetée, et
elle existe en **deux environnements isolés** — les huit services du cahier §15.4 en développement,
huit autres en recette sur les images **publiées dans GHCR** et épinglées par empreinte, dont les
**sept** séparations du cahier §22.2 sont prouvées sur l'état réel.

Au-dessus de ce socle :

| Livré | Depuis |
|---|---|
| **48 tables métier** PostgreSQL, **24 migrations** rejouables et **10 déclencheurs** ; l'isolation multi-entités est contrôlée au catalogue | LOTS 2, 3, 6, 7, 8 et 9 |
| **l'authentification complète** — magic link, comptes administrateurs, sessions, CSRF, limitation de débit, révocation au départ, comptes de service — et ses huit écrans | LOT 3 |
| **le portail national et le cadre applicatif** : l'entité consultée, la navigation, la barre mobile, la carte, et la résolution des permissions de la matrice §23.1 | LOT 4 |
| **le trombinoscope paginé**, la **recherche sans accents** et ses **cinq filtres**, la **fiche profil** complète, la **miniature de photo** avec son autorisation, l'**écriture dans son périmètre**, l'**archivage et la restauration**, l'**historique organisationnel**, et **deux écrans** | LOT 5, les onze |
| **le Framework complet** — synthèse, cercles, bureaux, contenus, cycle de vie, liens internes et écrans d'édition | LOT 6, les douze sous-étapes |
| **les fiches d'arrivée et l'onboarding** — modèles versionnés, parcours, tâches, progression calculée, suivi et deux écrans | LOT 7, les quinze sous-étapes |
| **le socle événementiel complet : lecture paginée, création, modification, publication, annulation, archivage, restauration et médias**, les **arrivées récentes**, et les **trois écrans** du lot — consultation (onglets « à venir »/« passés », badge « Annulé »), gestion (créer/modifier/publier/annuler/archiver/restaurer/médias, deux grilles de rôles jamais fusionnées) et l'**accueil final**, qui compose à l'écran les cinq sections du cahier §8.4 (présentation, Framework, arrivées, événements, liens), lecture ouverte aux huit rôles et ouverture externe explicite des liens, **avec ses carrousels accessibles sur mobile** (défilement manuel sous 768 px, liste verticale au-delà) ; chaque rôle agit dans sa portée exacte, rattachements multiples, `ECART-067` clos, `ARB-DROIT-003` tient la restauration ; une fiche d'arrivée publiée apparaît immédiatement, sans information organisationnelle ni photo ; **un contrôle de pile réelle** (`make accueil-check`, 29 contrôles, Caddy en HTTPS) prouve tout cela sur l'artefact réellement servi, **rejoué sur la recette de clôture** épinglée sur les images publiées | LOT 8, `T1`–`T14` |

**Le LOT 8 est verrouillé, porte `G8` franchie le 07/10/2026 (`DEC-634`), tag `v0.8.0`.** Jonathan a
validé explicitement l'accueil et les événements ; le critère de sortie 2 (vidéo) reste classé
**sans objet**, `US005` étant reportée. `ECART-012`, `ECART-068` et `QO-121` restent ouverts et non
bloquants — repris aux lots suivants au besoin.

**Ce qui n'existe pas encore, et c'est dit parce qu'un lecteur le supposerait acquis :** la
**vidéo chargée sur action** (`MVP-L08-US005`) reste **explicitement reportée** — aucune
convention de `payload_json` n'existe pour un bloc de contenu `VIDEO` (`QO-121` ouverte) et aucune
vidéo réelle n'existera avant la V1 (`CONT-026`) ; le back-office et l'import CSV sont **en
construction au LOT 9** ; le pilotage avancé du LOT 10 et les traitements asynchrones du LOT 11
restent à venir. Les 29 contenus inventoriés restent à relire.

> Les huit stories du LOT 7 sont fermées sur leurs critères propres. Au LOT 8, `#207`, `#208`,
> `#209` et `#212` sont fermées de même ; `#210` reste ouverte (bloquée par `ECART-068`) et `#211`
> reste ouverte (`US005` reportée) — un critère non tenu ne se referme pas par effet de bord d'une
> porte ultérieure.

Voir [`docs/README.md`](docs/README.md) §8 pour l'avancement lot par lot.

### Démarrer sur une machine propre

```bash
make tools      # verifier que uv, node et pnpm sont disponibles
make install    # installer les dependances Python et JavaScript
make check      # qualite complete : format, lint, types, tests, sources, documents
make up         # les 8 services, le bucket MinIO, les TROIS roles PostgreSQL, Caddy recharge
make migrate    # appliquer les migrations jusqu'a la tete 0022
make api-check  # interroger les trois endpoints de sante
make web-check  # controler la page nationale a travers Caddy, en HTTPS
```

> **`make up` fait plus que démarrer les conteneurs, et l'ordre compte.** Il crée le bucket MinIO
> **avant** que l'API doive être saine — sans quoi sa sonde `ready` échoue sur une machine propre
> (`DEC-477`) — provisionne les **trois** rôles PostgreSQL du moindre privilège (`DEC-520`), et
> **recharge Caddy**, qui ne surveille pas son fichier de configuration (`DEC-472`).

**Les contrôles de stack, tous dans l'intégration continue.** Chaque sous-étape depuis le LOT 3 en
ajoute un, et chacun porte ses témoins :

```bash
make trombinoscope-check   # 38 controles — les trois tailles SERVIES, huit refus, la pagination
make profil-check          # 17 controles — les 17 champs, aucun masquage, et les OCTETS de la miniature
make permissions-check     # 15 controles — l'union des droits, et les quatre tables INCHANGEES
make entites-check         # 13 controles — une entite par etat, les trois non actifs exclus
make residu-check          # la suite d'integration, ET la preuve qu'elle ne laisse rien en base
```

`make help` fait foi pour la liste complète — **86 cibles documentées**.

**Et la recette, depuis `T8`.** Elle tire les images publiées, donc elle exige un
`docker login ghcr.io` — sans quoi elle **refuse de démarrer** plutôt que de se rabattre sur une
construction locale :

```bash
make up-recette        # les 8 services de recette, sur les images PUBLIEES
make recette-check     # sante, ports, coherence de .env.recette, et les 7 separations
make down-recette      # arret, volumes conserves
```

Les cibles de stack acceptent `ENVIRONNEMENT=recette` ; `make up-recette` en est l'alias. Un nom
d'environnement fautif **échoue à la lecture du `Makefile`**, avant toute action, et la liste des
noms valides est **dérivée du disque**.

> **Pour aller plus loin — arrêt, réinitialisation, diagnostic :**
> [`docs/operations/exploitation-locale.md`](docs/operations/exploitation-locale.md). Toutes ses
> commandes ont été exécutées et ses sorties sont réelles. Il porte les **14** publications de ports,
> les **12** volumes et **quinze symptômes de diagnostic** réellement rencontrés sur ce projet —
> dont ceux qui n'ont aucun message clair : une variable manquante après une mise à jour du modèle,
> un port « déjà alloué » par un conteneur **arrêté**, et un Caddy sain qui sert une configuration
> périmée.

> **La racine de l'autorité interne de Caddy est approuvée** dans le trousseau de session depuis
> le 29 juillet 2026 : `https://app.onboarding.localhost` s'ouvre sans avertissement. Si le volume
> `caddy-data` est détruit, une nouvelle racine est engendrée et l'approbation doit être refaite —
> la commande, **sans `sudo`**, figure dans [`CLAUDE.md`](CLAUDE.md) §5.6.

---

## 2. Source de vérité

Les documents de cadrage validés se trouvent dans [`docs/`](docs/README.md).

Règle de préséance, en cas de contradiction :

1. le cahier des charges consolidé prévaut ;
2. une décision validée plus récente prévaut sur une décision plus ancienne ;
3. les annexes validées précisent les règles détaillées ;
4. aucune hypothèse ne remplace une décision explicite de Jonathan.

Toute proposition nouvelle est une **recommandation** jusqu'à validation explicite.

---

## 3. Architecture cible

Rappel des choix validés — aucun remplacement sans arbitrage explicite.

| Domaine | Choix validé |
|---|---|
| Frontend | React, TypeScript strict, Vite |
| API | Python, FastAPI |
| Base de données | PostgreSQL, SQLAlchemy, Alembic |
| Asynchrone | Redis, Dramatiq |
| Stockage objet | MinIO, compatible S3 |
| Reverse proxy | Caddy |
| E-mails hors production | Mailpit, en développement **et** en recette |
| Conteneurisation | Docker Compose |
| Images | `linux/arm64` et `linux/amd64`, publiées dans GHCR privé |
| Machine initiale | MacBook Pro Apple Silicon M5 |
| Environnements locaux | `onboarding-dev`, `onboarding-recette`, `onboarding-prod-local` |
| Versions épinglées | Python **3.12** · Node **24 LTS** · PostgreSQL **17** (`DEC-443`) |
| Monorepo | `pnpm` workspaces + workspace `uv`, orchestrés par le `Makefile` (`DEC-441`, `DEC-455`) |
| Qualité Python | Ruff, **mypy strict** (`DEC-442`), pytest |
| Qualité JS/TS | ESLint flat config avec `jsx-a11y`, Prettier, `tsc --noEmit` strict (`DEC-451`) |

Explicitement hors périmètre du MVP : PWA, fonctionnement hors ligne, Microsoft Entra ID,
Microsoft Graph, Teams, MFA, Kubernetes.

---

## 4. Règles non négociables

Ces règles sont issues des documents validés. Elles s'appliquent à chaque lot.

- aucun secret dans Git ;
- aucun fichier réel de collaborateurs, aucun CSV réel, aucune photo réelle versionnés ;
- aucune donnée métier durable dans `localStorage` ;
- aucune donnée ni image en Base64 dans PostgreSQL ou dans le code ;
- aucune règle de permission uniquement côté frontend : l'API est l'autorité finale ;
- isolation multi-entités respectée dès les fondations ;
- aucune création automatique de table en production ;
- aucun contournement du magic link ni de Mailpit en recette ;
- aucune image de production référencée par `latest` seul ;
- aucun code du prototype historique réutilisé ;
- aucune exigence `Must` ni story `P0` supprimée, fusionnée ou dégradée sans décision
  explicite et tracée.

---

## 5. Structure du dépôt

```text
.
├── README.md                  ← ce fichier
├── CLAUDE.md                  ← passation : état, méthode de travail, pièges de l'environnement
├── CONTRIBUTING.md            ← règles de contribution, définitions de Ready et de Done
├── Makefile                   ← point d'entrée unique des commandes (DEC-441)
├── .env.example               ← modèle de configuration, sans aucun secret
├── .gitignore                 ← barrière contre secrets et données réelles
├── .gitattributes             ← normalisation des fins de ligne
├── .editorconfig              ← normalisation dans l'éditeur
├── .node-version              ← 24.16   (DEC-443)
├── .python-version            ← 3.12    (DEC-443)
├── package.json               ← racine pnpm, pnpm épinglé par `packageManager`
├── pnpm-workspace.yaml        ← espaces de travail JS, store hors iCloud (DEC-439)
├── pyproject.toml             ← workspace uv, config Ruff, mypy strict, pytest (DEC-455)
├── tsconfig.base.json         ← TypeScript strict, partagé
├── eslint.config.js           ← ESLint flat config, dont jsx-a11y (DEC-451)
├── .prettierrc.json           ← Prettier
├── .prettierignore            ← Markdown exclu : protège les documents immuables (DEC-454)
├── .dockerignore              ← contexte de construction : deps, caches, .env (DEC-473)
├── .github/                   ← gabarits, workflows/ci.yml : les 11 controles (T6)
│                                 workflows/images.yml : multiarchitecture + GHCR (T7)
├── .gitleaks.toml             ← detection de secrets, regles propres au projet (T6)
├── apps/
│   ├── api/                   ← API FastAPI, 3 healthchecks, migration Alembic
│   ├── worker/                ← worker Dramatiq, les 7 files declarees
│   └── web/                   ← frontend React/Vite — page de statut, 5 etats (T5)
│                                 Dockerfile a DEUX cibles depuis T7 (DEC-479)
├── packages/
│   ├── observabilite/         ← journal JSON, masquage, corrélation (DEC-466)
│   ├── ui/                    ← design system        — coquille, tokens en T10
│   └── contracts/             ← contrat API partagé  — coquille, génération en T10
├── infra/
│   ├── compose/               ← base + surcouche dev, les 8 services (DEC-444)
│   ├── caddy/                 ← Caddyfile, tls internal (DEC-446)
│   └── scripts/               ← exclusion iCloud, verification ports, sante, persistance
└── docs/
    ├── product/               ← cahier des charges, matrice des droits, roadmap, backlog
    │   └── contenus/          ← inventaire du prototype, parcours d'onboarding relevés
    ├── architecture/          ← modèle de données
    │   └── donnees/           ← schéma CSV, codes d'erreur, listes contrôlées, exemple fictif
    ├── decisions/             ← registre des décisions, registre des écarts
    ├── operations/            ← conventions, registres, politique de secrets, contrôles de sortie
    └── prototype/             ← prototype historique, non versionné, non réutilisable
```

Chaque espace de travail porte son propre `README.md` : rôle, commandes, et **ce qui y arrive
à quelle sous-étape**.

> **Ne pas remettre `node_modules` ni `.venv` dans la synchronisation iCloud.** Le dépôt
> réside dans iCloud Drive (`DEC-418`) ; ces répertoires en sont exclus par `DEC-439` et
> `DEC-453`. `pnpm install` efface le marquage, un `postinstall` le repose automatiquement, et
> `make icloud-verify` échoue s'il manque.

---

## 6. Prototype historique

Le fichier `docs/prototype/V1.html` est conservé sur disque à des fins d'historisation.
Il n'est **pas versionné** et ne constitue **pas** une base de code réutilisable.
Voir [`docs/prototype/README.md`](docs/prototype/README.md).

---

## 7. Configuration

La configuration passe exclusivement par des variables d'environnement. Le fichier `.env`
local n'est **jamais** versionné.

- [`.env.example`](.env.example) — modèle documenté en **version 1.6**, **84 variables**, aucune
  valeur réelle. Chaque variable porte sa source documentaire et le lot où elle devient effective.
  **Neuf** valent encore `CHANGE_ME` : sept sont engendrées localement par `make env`, et **deux ne
  le sont pas et ce n'est pas un oubli** — `IMPORT_SOURCE_RETENTION_DAYS` attend `QO-100` au LOT 9,
  `UPTIME_KUMA_PUSH_URL` attend le LOT 13.
- **`make env` ne réconcilie RIEN.** Il ne touche jamais un `.env` existant — c'est voulu, il porte
  des secrets engendrés — donc une variable ajoutée au modèle **après** la première création n'y
  arrive jamais. **Lance `make env-check` en début de session** : il nomme les manquantes, et une
  variable a manqué à *chaque* lot.
- **Cinq variables ne sont consommées par personne** : les seuils du cahier §20.2, `ECART-034`.
  Elles portent l'annotation qui le dit, plutôt que de laisser croire qu'elles agissent.
- [`docs/operations/politique-configuration-et-secrets.md`](docs/operations/politique-configuration-et-secrets.md)
  — séparation des trois environnements, garde-fous de démarrage, rotation, conduite à tenir en
  cas de fuite.

---

## 8. Suivi du projet

| Registre | Entrées |
|---|---:|
| [Décisions](docs/decisions/registre-decisions.md) | **232** — 85 reprises des documents validés, **147** de réalisation depuis `DEC-418` |
| [Écarts](docs/decisions/registre-ecarts.md) | **52** — 10 ouverts, 39 clos, 3 acceptés |
| [Questions ouvertes](docs/operations/registre-questions-ouvertes.md) | **42** — 32 ouvertes, 10 closes |
| [Risques](docs/operations/registre-risques.md) | **34** |
| [Dépendances externes](docs/operations/registre-dependances-externes.md) | **17** |
| [Contenus inventoriés](docs/product/contenus/inventaire-prototype.md) | **29**, tous au statut `à relire` — **aucun n'est publiable en l'état** |

> **CES NOMBRES SONT DÉRIVÉS, PAS RECOPIÉS, ET C'EST UN CONTRÔLE QUI LE GARANTIT.**
>
> `make docs-check` relève les identifiants que chaque registre **déclare** et les confronte au
> total que son en-tête **annonce** — il échoue si l'un diverge, et il nomme la ligne fautive. Il
> vérifie aussi qu'un seul marqueur « prochain identifiant libre » existe par registre, et
> recalcule les **cinq empreintes SHA-256** des documents immuables.
>
> **Ce contrôle ne couvrait qu'un registre sur six jusqu'au 07/09/2026** : le registre des risques
> annonçait **33** pour **34** déclarés, et ce README en annonçait **32**. `ECART-053`, `DEC-565`.
> C'est la classe `ECART-021`, rejouée une douzaine de fois sur ce projet — **un nombre qu'on ne
> dérive pas vieillit en silence à la première addition.**

**Les preuves, porte par porte :**

| Porte | Ce qu'elle a validé |
|---|---|
| [`G0`](docs/operations/checklist-validation-G0.md) | le référentiel documentaire — [contrôles de sortie](docs/operations/controles-sortie-lot-0.md) |
| [`G1`](docs/operations/checklist-validation-G1.md) | le monorepo, la stack, la CI, les images multiarchitecture, la recette |
| [`G2`](docs/operations/checklist-validation-G2.md) | le socle de données — 18 tables métier, l'historisation, l'isolation |
| [`G3`](docs/operations/checklist-validation-G3.md) | l'authentification complète et ses huit écrans |
| [`G4`](docs/operations/checklist-validation-G4.md) | le portail, le cadre applicatif et les permissions — **et ce que le lot n'a PAS fait** |
| [`G5`](docs/operations/checklist-validation-G5.md) | les collaborateurs, les profils et l'organisation — les **sept** critères, huit gestes de démonstration, et **son §7 : ce que le lot n'a PAS fait**, qu'il faut lire en premier |

Arbitrages d'entrée du LOT 1 : [compte rendu `T0`](docs/operations/compte-rendu-t0-lot-1.md).
Un **compte rendu par sous-étape** consigne le travail, les contrôles, et **les défauts de mes
propres contrôles** : `docs/operations/compte-rendu-t*-lot-*.md`.
