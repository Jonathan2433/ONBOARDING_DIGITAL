# Registre des questions ouvertes

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Dernière mise à jour :** 29 juillet 2026, sous-étape `T6` du LOT 1
**Source reprise :** cahier des charges §32

| Catégorie | Nombre | Dont closes |
|---|---:|---:|
| Bloquantes avant données réelles ou production générale | 17 | 0 |
| Non bloquantes pour le développement | 12 | 1 |
| Ouvertes par la réalisation, à partir de `QO-106` | 9 | 3 |
| **Total** | **38** | **4** |

**34 questions restent ouvertes.** Ouvertes le 28 juillet 2026 : `QO-111` en `T2`
(fournisseur de collation PostgreSQL) et `QO-112` en `T3` (liste des extensions
PostgreSQL), les deux à trancher au **LOT 2** avec le modèle de données ; `QO-113` en `T4`
(conservation calendaire des journaux), à trancher au **LOT 13**. Closes le 27 juillet 2026 en sous-étape `T0` : `QO-086`
(moteur Docker constaté), `QO-107` (protection de branche possible, prouvée, `DEC-449`),
`QO-108` (moyen de mise en place GitHub, `DEC-448` puis `DEC-449`), `QO-109` (atténuations
iCloud, `DEC-439` et `DEC-447`). Une question close conserve son identifiant, sa réponse et sa
date de clôture ; elle n'est jamais retirée du registre.

**Prochain identifiant libre : `QO-115`.**

> **Trous conservés dans la séquence.** La plage `QO-072` à `QO-105` couvre 34 numéros mais
> seules **29** questions sont présentes dans le corpus. Absentes : `QO-075`, `QO-079`,
> `QO-080`, `QO-082`, `QO-090`. Ces trous ne sont **jamais** comblés, conformément aux règles
> de numérotation. Voir `ECART-011`.

---

# 1. Bloquantes avant données réelles ou production générale

Aucune de ces questions ne bloque le développement local. Chacune bloque soit le chargement
de données réelles, soit l'ouverture générale.

| ID | Question | Responsable | Bloque | Statut |
|---|---|---|---|---|
| `QO-072` | Durée maximale des jetons de comptes de service | Jonathan / sécurité | LOT 3, story `MVP-L03-US007` | Ouverte |
| `QO-073` | Personnes morales exactes responsables de traitement | eXalt / juridique | Production générale | Ouverte |
| `QO-074` | Contact RGPD ou DPO | eXalt | Production générale | Ouverte |
| `QO-076` | Base légale exacte des traitements | eXalt / juridique | Production générale | Ouverte |
| `QO-077` | Nécessité d'une AIPD | eXalt / RGPD | Production générale | Ouverte |
| `QO-078` | Modalités d'effacement dans les sauvegardes | Architecture / RGPD | Production générale | Ouverte |
| `QO-081` | Hébergement permanent de production | Jonathan / eXalt | Production générale, LOT 14 | Ouverte |
| `QO-083` | Emplacement de sauvegarde local | Jonathan | LOT 13 | Ouverte |
| `QO-085` | RAM et espace disque exacts du Mac M5 | Jonathan | LOT 1 | **Mesurée en charge réelle en `T5` — 389 Mio, 5,0 % du budget.** Reste ouverte : le dimensionnement de deux environnements simultanés relève de `T8`. Voir §1.1 |
| `QO-087` | SSD externe de sauvegarde | Jonathan | LOT 13 | Ouverte |
| `QO-088` | Destination chiffrée hors site | Jonathan / eXalt | Production générale | Ouverte |
| `QO-096` | Schéma définitif des colonnes du CSV | Jonathan / ESM | Données réelles, LOT 9 | Ouverte |
| `QO-097` | Personne remettant formellement le CSV final | Léa / ESM | Données réelles, LOT 14 | Ouverte |
| `QO-098` | Preuves disponibles d'autorisation des photos | RH / ESM | Données réelles, LOT 5 | Ouverte |
| `QO-099` | Nombre maximal de lignes rejetées acceptable au lancement | Léa / Jonathan | LOT 9 | Ouverte |
| `QO-100` | Durée de conservation du CSV source | RGPD / architecture | Données réelles, LOT 9 | Ouverte |
| `QO-101` | Configuration matérielle de l'hébergement final | Jonathan / eXalt | Production générale | Ouverte |

## 1.1 Éléments de réponse constatés pour `QO-085`

Mesures relevées en lecture seule sur la machine de développement le 27 juillet 2026 :

| Grandeur | Valeur constatée |
|---|---|
| Processeur | Apple M5 |
| Mémoire vive | **16 Gio** |
| Espace disque disponible | 564 Gio sur 926 Gio |
| FileVault | Actif |
| Docker | 29.5.3, Compose v5.1.4 |

Ces constats **alimentent** la question, ils ne la ferment pas : la décision d'exploitation
appartient à Jonathan.

### Mesures complémentaires du 27 juillet 2026, sous-étape `T0`

Les 16 Gio de la machine **ne sont pas le plafond applicable**. Mesures directes :

| Grandeur | Valeur mesurée | Source |
|---|---|---|
| Mémoire allouée à la VM Docker | **7,75 Gio**, soit la moitié de la machine | `docker info --format '{{.MemTotal}}'` |
| Conteneurs tiers actifs au moment de la mesure | **5**, projet `observatoire-ecom-studio`, actifs depuis 5 jours | `docker ps` |
| Mémoire occupée par ces conteneurs | **~1,93 Gio, soit 25 % du budget Docker**, dont 1,77 Gio pour le seul worker | `docker stats --no-stream` |
| Marge restante pour les 8 services du LOT 1 | **~5,8 Gio** | déduction |
| Image disque de la VM Docker | 28 Go, sous `~/Library/Containers/`, **hors iCloud** | `du -sh` |

Ces éléments **ne closent pas** `QO-085` : le dimensionnement définitif reste à confirmer par
Jonathan une fois les 8 services démarrés et mesurés en charge. Ils ont en revanche conduit à
réécrire `ROAD-RSK-027`, dont les deux prémisses étaient inexactes, et à la décision `DEC-440`
— exécution non simultanée et arrêt du projet tiers pendant le LOT 1.

### Mesures complémentaires du 27 juillet 2026, sous-étape `T1` — empreinte disque de l'outillage

Le volet **disque** de `QO-085` n'avait encore aucune mesure. Le squelette du monorepo en
fournit une première, avant toute image Docker.

| Emplacement | Taille | Fichiers | Dans iCloud ? |
|---|---:|---:|---|
| `node_modules` racine | 178 Mio | 11 066 | Non — exclu par `DEC-453` |
| `.venv` racine | 98 Mio | 2 176 | Non — exclu par `DEC-453` |
| `node_modules` des 3 espaces de travail | 40 Kio | 10 | Non — exclus par `DEC-453` |
| **Sous-total dans le dépôt** | **276 Mio** | **13 252** | **Exclu de la synchronisation** |
| Store `pnpm`, `~/.local/share/pnpm/store` | 166 Mio | — | Non, hors dépôt (`DEC-439`) |
| Cache `uv`, `~/.cache/uv` | 103 Mio | — | Non, hors dépôt |
| CPython 3.12.13 géré par `uv` | 69 Mio | — | Non, hors dépôt |
| **Total outillage** | **~614 Mio** | — | — |

Deux enseignements pour la suite du lot :

1. **13 252 fichiers** sont soustraits à iCloud dans le seul dépôt, pour un socle qui ne
   contient encore **aucune dépendance applicative** — ni FastAPI, ni SQLAlchemy, ni Alembic,
   ni les cinq bibliothèques frontend du cahier §17.1. Le chiffre croîtra nettement aux
   sous-étapes `T3` et `T5`.
2. L'espace disque n'est pas le facteur limitant : 563 Gio restent libres. **La mémoire l'est**,
   avec 7,75 Gio pour Docker. La mesure en charge attendue par `QO-085` reste donc à faire en
   `T2`, une fois les 8 services démarrés.

### Mesures complémentaires du 28 juillet 2026, sous-étape `T2` — les 8 services démarrés

Projet tiers `observatoire-ecom-studio` arrêté par `docker compose stop` — conteneurs et volume
préservés. Budget rendu : **7,75 Gio en totalité**.

| Service | Consommation | Limite appliquée (`DEC-440`) |
|---|---:|---:|
| minio | 84,96 Mio | 1 024 Mio |
| db | 19,35 Mio | 1 024 Mio |
| caddy | 15,36 Mio | 256 Mio |
| mailpit | 13,25 Mio | 256 Mio |
| redis | 10,71 Mio | 512 Mio |
| api | 672 Kio | 1 024 Mio |
| worker | 672 Kio | 1 024 Mio |
| web | 556 Kio | 1 024 Mio |
| **Total mesuré** | **146 Mio, soit 2 % du budget** | 6 144 Mio déclarés |

Les huit limites sont **effectivement appliquées** : lecture de `HostConfig.Memory` sur chaque
conteneur, et non de la déclaration Compose.

> **⚠ Cette mesure est un plancher, pas la charge réelle, et `QO-085` reste ouverte.**
> `api`, `worker` et `web` tiennent dans 672 Kio parce qu'ils exécutent un simple processus
> d'attente : leur code applicatif arrive en `T3` et `T5`. Uvicorn, Dramatiq et Vite changeront
> l'ordre de grandeur, PostgreSQL aussi dès qu'il portera un schéma et des index. La mesure qui
> permettra de répondre se fera **après `T5`**, sur une stack qui travaille.

Empreinte disque des images construites, à comparer aux 276 Mio de dépendances mesurés en `T1` :

| Image | Taille |
|---|---:|
| `onboarding-dev-web` | **924 Mio** — voir `ROAD-RSK-030` |
| `onboarding-dev-api` | 284 Mio |
| `onboarding-dev-worker` | 284 Mio |

### Mesures du 28 juillet 2026, sous-étape `T5` — la stack travaille réellement

C'est **la mesure que `T2` annonçait**, et elle vaut celle-là : uvicorn sert, Dramatiq consomme
son courtier, Vite transforme et sert la page de statut. Aucun service n'exécute plus un
processus d'attente.

| Service | `T2` — processus d'attente | `T5` — code applicatif en marche | Limite appliquée |
|---|---:|---:|---:|
| api | 672 Kio | **92,55 Mio** | 1 024 Mio |
| minio | 84,96 Mio | 90,25 Mio | 1 024 Mio |
| web | 556 Kio | **80,67 Mio** | 1 024 Mio |
| worker | 672 Kio | **42,25 Mio** | 1 024 Mio |
| db | 19,35 Mio | 36,77 Mio | 1 024 Mio |
| mailpit | 13,25 Mio | 18,78 Mio | 256 Mio |
| caddy | 15,36 Mio | 16,84 Mio | 256 Mio |
| redis | 10,71 Mio | 11,19 Mio | 512 Mio |
| **Total** | **146 Mio, 2 %** | **389 Mio, soit 5,0 % du budget** | 6 144 Mio déclarés |

Les trois services applicatifs passent d'environ **2 Mio à 215 Mio** : c'est le facteur qui
manquait. Aucune limite n'est approchée — la plus sollicitée est `api`, à **9,0 %** de la sienne.

**Réponse au volet RAM :** une stack complète en fonctionnement consomme **5,0 %** des 7,75 Gio
alloués à Docker. Même en supposant une croissance d'un ordre de grandeur avec les données du
LOT 2 et la chaîne média du LOT 11, la marge reste confortable pour **un** environnement.

> **`QO-085` n'est pas close pour autant, et voici précisément ce qui manque.** La question porte
> sur le dimensionnement de la machine, et `DEC-440` n'autorise qu'**un environnement à la fois**
> — arbitrage pris justement parce que le budget paraissait contraint. La mesure qui permettrait
> de trancher est celle de `T8` : deux stacks complètes, développement et recette, avec leurs
> volumes distincts. `T8` prouvera la **séparation** par démarrages successifs, non la
> simultanéité ; si Jonathan souhaite un jour les faire coexister, c'est là que la mesure devra
> être faite. **Recommandation : clore `QO-085` à `T8`, pas avant.**

Empreinte disque des images après `T5` :

| Image | `T2` | `T5` | Motif de l'écart |
|---|---:|---:|---|
| `onboarding-dev-web` | 924 Mio | **1,02 Gio** | `jsdom` et Testing Library, ajoutés par `DEC-471`. Voir `ROAD-RSK-030`, **aggravé** |
| `onboarding-dev-api` | 284 Mio | 662 Mio | Dépendances applicatives réelles installées depuis `T3` |
| `onboarding-dev-worker` | 284 Mio | 662 Mio | Idem |

---

# 2. Non bloquantes pour commencer le développement

| ID | Question | Responsable | Échéance utile | Statut |
|---|---|---|---|---|
| `QO-084` | Introduction immédiate ou différée de PostgreSQL RLS | Architecture | LOT 2 | Ouverte |
| `QO-086` | Installation actuelle de Docker Desktop ou moteur alternatif | Jonathan | LOT 1 | **Close le 27/07/2026**, sous-étape `T0` : Docker Desktop 29.5.3, Compose v5.1.4, pilote `overlayfs`, `aarch64`. Aucun moteur alternatif |
| `QO-089` | Confirmation du RTO de quatre heures | Exploitation | LOT 13 | Ouverte |
| `QO-091` | Supervision du Mac par Tailscale ou moniteurs Push | Jonathan | LOT 13 | Ouverte |
| `QO-092` | Destination des signalements de bugs | Jonathan / eXalt | LOT 10 | Ouverte |
| `QO-093` | Pièce jointe de capture d'écran dans les bugs | Produit | LOT 10 | Ouverte |
| `QO-094` | Second référent technique avant production | eXalt | Production générale | Ouverte |
| `QO-095` | Suivi des maintenances annoncées dans Uptime Kuma | Exploitation | LOT 13 | Ouverte |
| `QO-102` | Volumétrie vidéo annuelle attendue | Tess / ESM | LOT 11 | Ouverte |
| `QO-103` | Limites médias configurables dès la V1 | Produit | V1 | Ouverte |
| `QO-104` | Outil de charge : k6 ou Locust | Architecture | LOT 12 | Ouverte |
| `QO-105` | Taux d'erreur maximal contractuel | Produit / technique | LOT 12 | Ouverte |

`QO-094` mérite une attention particulière : elle conditionne la décision `DEC-429`. Tant que
Jonathan est l'unique relecteur, aucune approbation de pull request ne peut être exigée,
GitHub interdisant l'auto-approbation.

---

# 3. Questions ouvertes par la réalisation

| ID | Question | Responsable | Bloque | Statut |
|---|---|---|---|---|
| `QO-106` | Retient-on les compléments d'étiquettes GitHub proposés — familles `type`, `gravité` et `état` ? Ils ne sont pas prescrits par les documents validés. | Jonathan | Non. Confort de suivi. | Ouverte |
| `QO-114` | **Les droits d'administration sont-ils nécessaires à la production temporaire locale du LOT 13, et si oui qui les accorde ?** Mesure du 29/07/2026 : `id -Gn` ne place `jonathan.dupau` dans **aucun** groupe `admin`, et `sudo` répond « is not in the sudoers file ». Le LOT 13 prévoit `restic`, Uptime Kuma, des services au démarrage et une rotation de journaux hors Docker — plusieurs réclament habituellement des droits élevés. Ce qui a déjà été contourné sans eux : outillage dans `~/.local/bin`, ports 80 et 443 publiés par Docker Desktop, `*.onboarding.localhost` résolu sans toucher à `/etc/hosts`, et l'approbation de la racine Caddy faite dans le trousseau **de session**. | Jonathan / DSI | **LOT 13, à instruire avant** | Ouverte |
| `QO-107` | Le plan GitHub du compte permet-il les règles de protection de branche sur un dépôt privé personnel ? Si non, le repli documenté est un garde-fou local `pre-push`, qui ne remplace pas la protection côté serveur. | Jonathan | Non pour `G0`. Prérequis du LOT 1 pour rendre `DEC-429` effective. | **Close le 27/07/2026 par l'affirmative.** Le plan autorise la protection classique sur ce dépôt privé personnel : `main` et `develop` sont protégées avec `enforce_admins`, et le rejet du push direct est prouvé (`GH006`). **Le repli `pre-push` devient sans objet.** `DEC-449` |
| `QO-108` | Comment réalise-t-on la mise en place GitHub — installation de `gh`, interface web, ou connecteur ? Aucun outil d'accès à l'API GitHub n'est disponible dans la session de travail. | Jonathan | Non pour `G0`. Prérequis du LOT 1. | **Close le 27/07/2026.** Réponse initiale `DEC-448` — mise en place dans l'interface par Jonathan. **Réponse effective `DEC-449`, qui remplace `DEC-448`** : installation du binaire `gh` 2.96.0 dans `~/.local/bin` par l'agent, Homebrew étant inutilisable, puis authentification par Jonathan et exécution par `gh` |
| `QO-109` | Quelles atténuations retient-on pour les volumes Docker et les dépendances, le dépôt résidant dans iCloud Drive par `DEC-418` ? `.gitignore` empêche Git de les suivre mais n'empêche pas iCloud de les synchroniser. | Jonathan / architecture | Non pour `G0`. Était à trancher au LOT 1, avant création des volumes. | **Close le 27/07/2026**, sous-étape `T0`, par `DEC-439` et `DEC-447` |
| `QO-113` | **Comment appliquer la conservation de 30 jours des journaux techniques ?** Le cahier §28.3 demande « logs techniques : 30 jours » **et** « rotation et limite de taille obligatoires ». `DEC-467` satisfait le second volet : le pilote `json-file` de Docker rotate par taille sur les huit services. Il ne peut pas satisfaire le premier : **ce pilote borne par la taille, jamais par la durée**. Une conservation calendaire suppose une collecte centralisée — agrégateur externe, ou politique de rétention sur un volume dédié. `LOG_RETENTION_DAYS=30` porte l'intention dans `.env.example` mais n'est consommée par aucun code aujourd'hui, et c'est délibéré : une variable lue sans effet serait plus trompeuse qu'une variable inerte. | Jonathan / exploitation | **Non pour `G1`.** Le LOT 1 n'a pas d'exigence de conservation. À trancher au **LOT 13**, avec la production temporaire et la supervision. | Ouverte |
| `QO-112` | **Quelles extensions PostgreSQL activer, et dans quelle migration ?** Le modèle §28 place en première étape « les extensions strictement nécessaires », mais **aucun document du corpus n'en nomme une seule** — vérifié le 28/07/2026, zéro occurrence de `pg_trgm`, `unaccent`, `citext`, `pgcrypto`, `uuid-ossp` dans le cahier comme dans le modèle. Deux constats : `gen_random_uuid()` est intégré à PostgreSQL depuis la version 13, donc les clés UUID du modèle §3 n'exigent aucune extension ; et le modèle §26.1 laisse la recherche tolérante explicitement ouverte, ses index arrivant à la migration 16. `DEC-463` a donc livré une migration `0001_initial` **vide**, ce que la roadmap autorise. Point d'attention : `CREATE EXTENSION` exige des droits élevés qu'un compte applicatif de production n'aura peut-être pas — la migration qui les activera doit en tenir compte. | Jonathan / architecture | **Non pour `G1`.** À trancher au **LOT 2**, avec les tables et les index de recherche. | Ouverte |
| `QO-111` | **Quel fournisseur de collation et quelle locale pour le cluster PostgreSQL ?** La collation est fixée à l'`initdb` : la changer plus tard exige de **recréer le cluster**, donc de perdre les données. À `T2`, l'instance a été créée avec les valeurs par défaut de l'image, volontairement, faute de décision. Le trombinoscope portera des noms français accentués et le cahier §26.1 exige des index de recherche : le tri, la comparaison insensible à la casse et la recherche sans accent en dépendent directement. Options connues : le fournisseur `libc` avec une locale `fr_FR.UTF-8`, ou le fournisseur **`icu`** avec une locale `fr-FR`, disponible dans l'image Debian retenue par `DEC-458`. | Jonathan / architecture | **Non pour `G1`.** Bloquante **avant toute donnée réelle**, donc avant le LOT 9, et à trancher au **LOT 2** avec le modèle de données — c'est là que naissent les index de recherche. | Ouverte |
| `QO-110` | Quelle nomenclature et quelle langue pour les en-têtes du CSV collaborateurs ? Jonathan n'a pas encore de visibilité sur la source de données réelle. Traitement retenu en attendant : le schéma définit des champs logiques `F01` à `F19` et un profil de correspondance versionné associe les en-têtes réelles (`DEC-434`). Un profil provisoire, non normatif, est utilisé dans le jeu d'exemple. | Jonathan / ESM | Non pour `G0`. Rattachée à `QO-096`, **bloquante avant l'import réel** au LOT 9. | Ouverte |

---

# 4. Règles de tenue

- une question fermée conserve son identifiant, sa réponse et sa date de clôture ;
- une question qui devient bloquante voit son statut modifié, jamais son identifiant ;
- une réponse partielle est consignée comme élément de réponse, sans clore la question ;
- une question résolue par un arbitrage renvoie vers la décision `DEC-nnn` correspondante ;
- les trous de séquence ne sont jamais comblés.
