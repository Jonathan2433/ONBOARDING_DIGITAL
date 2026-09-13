# Registre des questions ouvertes

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Dernière mise à jour :** 13 septembre 2026, `T1` du LOT 6 — `QO-120`
**Source reprise :** cahier des charges §32

| Catégorie | Nombre | Dont closes |
|---|---:|---:|
| Bloquantes avant données réelles ou production générale | 17 | 2 |
| Non bloquantes pour le développement | 12 | 1 |
| Ouvertes par la réalisation, à partir de `QO-106` | 15 | 7 |
| **Total** | **44** | **10** |

**34 questions restent ouvertes**, sur **44** entrées — `QO-072` **close le 22/08/2026** par `T10` du LOT 3, la **première du corpus** à l'être par arbitrage de Jonathan — et ces nombres sont **dérivés du corps de ce registre** — le tableau ci-dessus annonçait 38 pour 39 entrées en prose, et comptait `QO-085` comme non close alors qu'elle l'est depuis `T8`. Corrigé le 18/08/2026 au titre de la classe `ECART-021`, et **remis à jour le 20/08/2026** à la
clôture de `QO-115` (`DEC-519`).

> **Et la mise à jour du 20/08/2026 a d'abord été FAUSSE.** J'ai **décrémenté** le compte de closes de
> cette famille — 5 → 4 — alors que clore une question l'**incrémente**. Le total ne concordait plus
> avec ses composantes, et je l'ai vu en **dérivant** le compte du corps du registre plutôt qu'en
> raisonnant : `41 entrées, 8 closes, 33 ouvertes`. **Ce registre ne se met pas à jour de tête.** La
> commande qui fait foi :
>
> ```bash
> grep -cE '^\| ~?~?`QO-[0-9]+`' docs/operations/registre-questions-ouvertes.md   # 41 entrées
> ```

**Closes au LOT 2, sous-étape `T1`** : `QO-111` (collation PostgreSQL, `DEC-497`) et `QO-112` (extensions PostgreSQL, `DEC-498`). **Ouverte en `T1`** : `QO-116` (compte applicatif superutilisateur contre le moindre privilège du cahier §20.1, à traiter au LOT 3). `QO-113` (conservation calendaire des journaux) reste à trancher au **LOT 13**. Closes le 27 juillet 2026 en sous-étape `T0` : `QO-086`
(moteur Docker constaté), `QO-107` (protection de branche possible, prouvée, `DEC-449`),
`QO-108` (moyen de mise en place GitHub, `DEC-448` puis `DEC-449`), `QO-109` (atténuations
iCloud, `DEC-439` et `DEC-447`). Une question close conserve son identifiant, sa réponse et sa
date de clôture ; elle n'est jamais retirée du registre.

**Prochain identifiant libre : **`QO-121`.**

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
| `QO-072` | Durée maximale des jetons de comptes de service | Jonathan / sécurité | LOT 3, story `MVP-L03-US007` | **CLOSE le 22/08/2026, sous-étape `T10`.** **Arbitrage de Jonathan : 90 jours.** Son motif, dans ses termes : redonner une clé au script **quatre fois par an**, contre une clé fuitée qui **cesse de fonctionner au bout de trois mois**. Les deux options écartées le sont pour leur conséquence, non pour leur principe — 30 jours fait tomber le script sur un renouvellement oublié, ce qui est son risque réel et non la sécurité ; 365 jours laisse une clé volée valable un an. **La valeur reste CONFIGURABLE**, par `SERVICE_TOKEN_MAX_DAYS`, ce que le modèle §10.5 exige littéralement — c'est l'inverse des seuils de débit du §20.2, que `T8` a posés en constantes parce que le cahier les écrit. Et **c'est un plafond, pas un défaut** : demander davantage lève, aucune durée n'est écrêtée en silence. `DEC-536` |
| `QO-073` | Personnes morales exactes responsables de traitement | eXalt / juridique | Production générale | Ouverte |
| `QO-074` | Contact RGPD ou DPO | eXalt | Production générale | Ouverte |
| `QO-076` | Base légale exacte des traitements | eXalt / juridique | Production générale | Ouverte |
| `QO-077` | Nécessité d'une AIPD | eXalt / RGPD | Production générale | Ouverte |
| `QO-078` | Modalités d'effacement dans les sauvegardes | Architecture / RGPD | Production générale | Ouverte |
| `QO-081` | Hébergement permanent de production | Jonathan / eXalt | Production générale, LOT 14 | Ouverte |
| `QO-083` | Emplacement de sauvegarde local | Jonathan | LOT 13 | Ouverte |
| `QO-085` | RAM et espace disque exacts du Mac M5 | Jonathan | LOT 1 | **CLOSE le 29/07/2026, sous-étape `T8`.** Les deux environnements ont été mesurés **simultanément** : **836,6 Mio pour seize services**, soit **10,5 %** des 7 936 Mio alloués à Docker. Voir §1.2 |
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


## 1.2 Clôture de `QO-085` — la mesure de DEUX environnements simultanés

**Ce que la question demandait, et qui manquait depuis `T2`.** `QO-085` porte sur le
dimensionnement du Mac M5. `T2` avait mesuré 146 Mio au repos, `T5` 389 Mio en charge, `T7`
483 à 494 Mio — mais toujours **une seule stack**. Le compte rendu de `T5` §1.1 le disait :
« clore `QO-085` à `T8`, pas avant », parce que le dimensionnement de deux environnements
simultanés était le seul volet non mesuré.

**Mesure du 29 juillet 2026, sous-étape `T8`, les deux stacks démarrées en même temps.**
Relevée par `make separations-check`, qui lit `docker stats` sur les seize conteneurs :

| Environnement | Services | Mémoire |
|---|---:|---:|
| `onboarding-dev` | 8 | **528,5 Mio** |
| `onboarding-recette` | 8 | **308,2 Mio** |
| **Total** | **16** | **836,6 Mio** |
| Budget alloué à Docker | | 7 936 Mio |
| **Part employée** | | **10,5 %** |

**La recette consomme moins que le développement, et c'est explicable :** son image `web` sert
un artefact statique par Caddy — cible `execution`, `DEC-479` — là où le développement fait
tourner le serveur Vite, qui est à lui seul le poste le plus lourd et le plus variable de la
stack.

### Ce que cette mesure prouve, et ce qu'elle n'autorise pas

**Il faut distinguer les deux, parce que ce sont deux choses différentes.**

- **Prouvé :** deux environnements complets tiennent simultanément dans le budget alloué, avec
  une marge de près de 90 %. Le volet mémoire de `QO-085` est donc **clos**.
- **Non autorisé pour autant :** `DEC-440` n'admet **qu'un environnement à la fois** en
  exploitation courante, et cette décision n'est pas modifiée. `T8` prouve la **séparation** par
  démarrages successifs ; la simultanéité n'a été employée que le temps de la mesure, parce que
  l'épreuve d'isolement réseau l'exige — une base arrêtée rendrait un échec de connexion
  indistinguable d'un isolement effectif.

**Une précision qui évite un faux raisonnement.** Les huit limites mémoire de `DEC-440`
totalisent 6 144 Mio par stack, soit **12 288 Mio pour deux** — plus que les 7 936 Mio alloués.
Il n'y a pas de contradiction : ce sont des **plafonds**, non des réservations. Docker ne
préempte rien ; seule la consommation réelle compte, et elle est de 836,6 Mio.

**Le volet disque**, mesuré en `T5`, n'est pas modifié par `T8` : la recette ajoute six volumes
et tire trois images déjà présentes en variante `arm64`.

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
| ~~`QO-115`~~ | **Charte graphique eXalt et police officielle.** Le cahier §13.1 les exige ; aucune des deux n'est dans le corpus, et le prototype référence explicitement « la charte EXALT ». `T10` a livré des jetons **relevés du prototype** et une **pile système**. | Jonathan / Léa | **CLOSE le 20/08/2026, `DEC-519`** — les deux documents **n'existent pas**, et les jetons relevés du prototype font référence. Ils restent qualifiés d'**approximation**, non de charte. Deux sources concordantes les fondent — le prototype nomme sa palette, et le §13.2 écrit « dégradés bleu, rose et violet » — et la mesure de contraste avait **corrigé deux défauts d'accessibilité** que le prototype portait. Si la charte apparaît, les jetons sont dans un fichier unique et le contrôle se rejoue. | **Close** |
| ~~`QO-116`~~ | **L'application se connecte à PostgreSQL avec un compte SUPERUTILISATEUR, alors que le cahier §20.1 pose le « moindre privilège » comme principe de sécurité.** Mesure du 18/08/2026 : `SELECT rolsuper FROM pg_roles WHERE rolname = current_user` rend `t` pour `onboarding_app`. Ce compte est celui qu'`initdb` crée, donc propriétaire du cluster : il peut détruire la base, lire toute table et créer toute extension. Le moindre privilège demanderait **deux** rôles — un pour les migrations, qui a besoin du DDL, et un pour l'exécution, qui n'a besoin que du DML. | Jonathan | **Non pour `G2`.** Il n'y a ni authentification, ni donnée réelle, ni accès extérieur avant le LOT 3 : l'exposition reste théorique. Arbitrage de Jonathan du 18/08/2026 : **à traiter au LOT 3**, le lot dont la sécurité applicative est l'objet.<br>**PRÉCISÉ le 20/08/2026, `DEC-518` : c'est la PREMIÈRE sous-étape du LOT 3, `T1`, avant l'authentification elle-même.** Motif de Jonathan : le LOT 3 est celui qui introduit l'accès extérieur, donc celui où l'exposition cesse d'être théorique — écrire l'authentification sur un compte superutilisateur aurait aggravé la dette au moment précis où elle devient réelle. **Coût accepté et nommé** : la connexion à la base change, et il faudra reprouver le démarrage des huit services, les onze migrations et les 373 tests, sur une base **recréée de zéro**. | **CLOSE le 20/08/2026, `DEC-520`** — l'application se connecte en `onboarding_runtime`, qui **n'est pas superutilisateur** et ne peut ni créer une base, ni créer un rôle. Mesuré : `rolsuper` rendait `t`, il rend `f`. **Cinq opérations DDL sont refusées** — `CREATE TABLE`, `DROP TABLE`, `ALTER TABLE`, `CREATE ROLE`, `TRUNCATE` — et le DML fonctionne, ce qui est le témoin indispensable. `make privileges-check` est dans la CI, plus **13 tests**. Le superutilisateur subsiste — `initdb` le crée — mais son unique usage est désormais `make roles-provision`. | **Close** |
| `QO-117` | **Quelle est la portée de l'unicité d'un alias client, et faut-il en imposer une ?** Le modèle §7.3 décrit `client_alias` — `alias_normalized`, `client_id`, `entity_id` nullable, validation humaine — mais **ne pose aucune règle d'unicité**, et le §25.1 ne mentionne pas cette table. Un même alias pourrait donc désigner **deux clients canoniques différents**, ce qui rendrait la recherche ambiguë à l'import du LOT 9. **La difficulté n'est pas technique mais métier** : `entity_id` étant nullable, l'unicité peut être **globale** — un alias désigne un seul client partout — ou **par entité** — Bordeaux et Lille peuvent connaître le même alias sous deux clients différents. Le second cas est concevable après une fusion d'entreprises. **Aucun index n'a été inventé** : `T5` a montré ce que coûte une dérivation absente du modèle. | Jonathan et Léa | **Non pour `G2`.** Le socle accepte les deux réponses, et l'ajouter plus tard est une migration d'une ligne. **Bloquant pour le LOT 9**, où l'import a besoin d'une correspondance déterministe. | Ouverte |
| `QO-107` | Le plan GitHub du compte permet-il les règles de protection de branche sur un dépôt privé personnel ? Si non, le repli documenté est un garde-fou local `pre-push`, qui ne remplace pas la protection côté serveur. | Jonathan | Non pour `G0`. Prérequis du LOT 1 pour rendre `DEC-429` effective. | **Close le 27/07/2026 par l'affirmative.** Le plan autorise la protection classique sur ce dépôt privé personnel : `main` et `develop` sont protégées avec `enforce_admins`, et le rejet du push direct est prouvé (`GH006`). **Le repli `pre-push` devient sans objet.** `DEC-449` |
| `QO-108` | Comment réalise-t-on la mise en place GitHub — installation de `gh`, interface web, ou connecteur ? Aucun outil d'accès à l'API GitHub n'est disponible dans la session de travail. | Jonathan | Non pour `G0`. Prérequis du LOT 1. | **Close le 27/07/2026.** Réponse initiale `DEC-448` — mise en place dans l'interface par Jonathan. **Réponse effective `DEC-449`, qui remplace `DEC-448`** : installation du binaire `gh` 2.96.0 dans `~/.local/bin` par l'agent, Homebrew étant inutilisable, puis authentification par Jonathan et exécution par `gh` |
| `QO-109` | Quelles atténuations retient-on pour les volumes Docker et les dépendances, le dépôt résidant dans iCloud Drive par `DEC-418` ? `.gitignore` empêche Git de les suivre mais n'empêche pas iCloud de les synchroniser. | Jonathan / architecture | Non pour `G0`. Était à trancher au LOT 1, avant création des volumes. | **Close le 27/07/2026**, sous-étape `T0`, par `DEC-439` et `DEC-447` |
| `QO-113` | **Comment appliquer la conservation de 30 jours des journaux techniques ?** Le cahier §28.3 demande « logs techniques : 30 jours » **et** « rotation et limite de taille obligatoires ». `DEC-467` satisfait le second volet : le pilote `json-file` de Docker rotate par taille sur les huit services. Il ne peut pas satisfaire le premier : **ce pilote borne par la taille, jamais par la durée**. Une conservation calendaire suppose une collecte centralisée — agrégateur externe, ou politique de rétention sur un volume dédié. `LOG_RETENTION_DAYS=30` porte l'intention dans `.env.example` mais n'est consommée par aucun code aujourd'hui, et c'est délibéré : une variable lue sans effet serait plus trompeuse qu'une variable inerte. | Jonathan / exploitation | **Non pour `G1`.** Le LOT 1 n'a pas d'exigence de conservation. À trancher au **LOT 13**, avec la production temporaire et la supervision. | Ouverte |
| `QO-112` | **Quelles extensions PostgreSQL activer, et dans quelle migration ?** Le modèle §28 place en première étape « les extensions strictement nécessaires », mais **aucun document du corpus n'en nomme une seule** — vérifié le 28/07/2026, zéro occurrence de `pg_trgm`, `unaccent`, `citext`, `pgcrypto`, `uuid-ossp` dans le cahier comme dans le modèle. Deux constats : `gen_random_uuid()` est intégré à PostgreSQL depuis la version 13, donc les clés UUID du modèle §3 n'exigent aucune extension ; et le modèle §26.1 laisse la recherche tolérante explicitement ouverte, ses index arrivant à la migration 16. `DEC-463` a donc livré une migration `0001_initial` **vide**, ce que la roadmap autorise. Point d'attention : `CREATE EXTENSION` exige des droits élevés qu'un compte applicatif de production n'aura peut-être pas — la migration qui les activera doit en tenir compte. | Jonathan / architecture | **Non pour `G1`.** À trancher au **LOT 2**, avec les tables et les index de recherche. | **CLOSE le 18/08/2026, `DEC-498`.** **Une seule extension : `btree_gist`**, dans la migration `0002`, parce qu'une contrainte d'exclusion mêlant l'égalité d'un `uuid` et le chevauchement d'une plage l'exige. **`pgcrypto` n'est PAS installée** : `gen_random_uuid()` est rattachée au **noyau** de PostgreSQL — mesuré. `citext` non plus, la normalisation d'e-mail étant applicative ; `unaccent` et `pg_trgm` non plus, elles servent la recherche tolérante du §26.1 au **LOT 5**. Les six sont disponibles dans l'image : ne pas les installer est un choix, une extension posée sans besoin nommé étant de la surface d'attaque. |
| `QO-111` | **Quel fournisseur de collation et quelle locale pour le cluster PostgreSQL ?** La collation est fixée à l'`initdb` : la changer plus tard exige de **recréer le cluster**, donc de perdre les données. À `T2`, l'instance a été créée avec les valeurs par défaut de l'image, volontairement, faute de décision. Le trombinoscope portera des noms français accentués et le cahier §26.1 exige des index de recherche : le tri, la comparaison insensible à la casse et la recherche sans accent en dépendent directement. Options connues : le fournisseur `libc` avec une locale `fr_FR.UTF-8`, ou le fournisseur **`icu`** avec une locale `fr-FR`, disponible dans l'image Debian retenue par `DEC-458`. | Jonathan / architecture | **Non pour `G1`.** Bloquante **avant toute donnée réelle**, donc avant le LOT 9, et à trancher au **LOT 2** avec le modèle de données — c'est là que naissent les index de recherche. | **CLOSE le 18/08/2026, `DEC-497`.** Fournisseur **ICU**, locale **`fr-FR`**, posés par `POSTGRES_INITDB_ARGS` dans le fichier Compose de base. Les deux bases, qui ne contenaient que `alembic_version`, ont été détruites et recréées. **Motif mesuré** : en libc `en_US.utf8`, `Jeanne` se classait avant `Jean-Pierre` et `Legall` avant `Le Gall`. Sur des prénoms simplement accentués les deux collations trient à l'identique — le motif n'est pas l'accentuation mais la ponctuation interne aux noms. Un second argument, la détection d'un changement de règles, a été **retiré** : `datcollversion` vaut `2.41` pour libc et `153.128` pour ICU, les deux enregistrent une version. |
| `QO-118` | **Quelle politique de mot de passe pour les comptes administrateurs locaux ?** **Aucun document du corpus n'en écrit une**, et c'est une lacune que `T5` du LOT 3 a rencontrée en écrivant la route de changement. Mesure du 21/08/2026 : le cahier §7.3 parle du **stockage** — « stocké de manière sécurisée », « jamais en clair », « jamais dans les logs » — et jamais de la **force** ; le §20.2 donne des seuils de tentatives, pas de longueur ; le §20.3 ne borne que `APP_SECRET_KEY`, qui est une clé machine et non un mot de passe humain. Et **le §8 de la fiche du LOT 3 énumère quatre décisions à instruire dans ce lot — une politique de mot de passe n'en fait pas partie** : personne ne l'avait vue. Accepter un mot de passe d'un caractère serait pourtant contraire à tout le chapitre 7. **Un plancher de 12 caractères est donc appliqué comme RECOMMANDATION, en une seule constante**, `LONGUEUR_MINIMALE_MOT_DE_PASSE`, et il est déclaré comme non dérivé du corpus plutôt que déguisé en décision — §6.5. **Ce qui reste à trancher** : la longueur, l'exigence éventuelle de classes de caractères, une liste de mots de passe interdits, et une durée de validité. Le mot de passe d'amorçage est **engendré** sur 32 caractères, donc la question ne porte que sur ceux que les administrateurs choisissent. | Jonathan | **Non pour `G3`.** Le plancher actuel refuse le cas trivial, et la trancher est une ligne. **À instruire avant le LOT 13**, où des comptes réels existeront. | Ouverte |
| `QO-119` | **Quel vocabulaire pour les types de blocs de contenu, et combien y en a-t-il ?** **Le cahier §10.7 et le modèle §15.2 donnent DEUX listes différentes**, mesuré le 13/09/2026 en les confrontant : **cinq** types communs — titre, texte, image, vidéo, liste — **trois** que seul le cahier nomme — cartes, liens, blocs de présentation — et **trois** que seul le modèle nomme — carte de lien, citation, appel à l'action interne. **L'union n'a pas de compte unique** : **neuf** types si « cartes », « liens » et « carte de lien » n'en désignent qu'un seul, **dix** si « cartes » vaut « carte de lien » et « liens » reste à part, **onze** si les trois sont distincts — et **aucune des trois lectures n'est déductible des documents**. **`T1` du LOT 6 en pose ONZE**, la lecture la plus large, parce qu'une fusion détruirait une distinction que le cahier écrit et qu'une séparation n'en détruit aucune. **Ce qui reste à trancher, précisément** : *(a)* « cartes » et « liens » font-ils un type ou deux ? *(b)* le « bloc de présentation » du cahier est-il un type propre, ou une composition des autres ? *(c)* la « citation » et l'« appel à l'action interne » du modèle entrent-ils au MVP ? **Fermer l'une des deux listes serait aussi fautif que les ignorer** : toutes deux s'ouvrent par une formule non fermante — « Le produit permet de gérer » — comme le « à prévoir **notamment** » du §25.1 et le « par exemple » du §22, dont le LOT 3 a montré que les deux erreurs sont **symétriques**. | Léa | **Non bloquante pour `T1` du LOT 6** : `DEC-577` pose l'**union**, chaque type rattaché au document qui le nomme, et le type reste **contrôlé en base** — restreindre plus tard est une migration d'une ligne, élargir aussi. **À trancher avant `T11` du LOT 6**, la reprise relue des contenus, où un auteur devra choisir un type pour de vrai. | Ouverte |
| `QO-120` | **Quels protocoles d'URL sont autorisés pour un lien interne ?** Le modèle §15.3 et le cahier §13 écrivent tous deux, mot pour mot, « Les URL sont validées selon une **liste de protocoles autorisés** ». **Mesure du 13/09/2026 : le corpus contient exactement DEUX occurrences du mot « protocole », et ce sont ces deux phrases. La liste n'existe nulle part.** Inventer `https` seul serait plausible et non dérivé — c'est le §7.0 septième point — et cela casserait un lien SharePoint en `ms-` ou un partage réseau, que le §15.3 nomme pourtant parmi les « autres ressources internes ». **Ce qui reste à trancher** : la liste elle-même ; si `http` en clair est toléré sur un réseau interne ; et si les schémas d'application — `ms-teams:`, `onenote:` — entrent au MVP. | Jonathan, et Léa pour l'usage | **Non bloquante pour `T1`** : la table borne la **forme** — `url` non vide — et non le protocole, ce qui ne fige rien dans le schéma. **À trancher avant `T8` du LOT 6**, qui écrit les liens internes et donc leur validation. | Ouverte |
| `QO-110` | Quelle nomenclature et quelle langue pour les en-têtes du CSV collaborateurs ? Jonathan n'a pas encore de visibilité sur la source de données réelle. Traitement retenu en attendant : le schéma définit des champs logiques `F01` à `F19` et un profil de correspondance versionné associe les en-têtes réelles (`DEC-434`). Un profil provisoire, non normatif, est utilisé dans le jeu d'exemple. | Jonathan / ESM | Non pour `G0`. Rattachée à `QO-096`, **bloquante avant l'import réel** au LOT 9. | Ouverte |

---

# 4. Règles de tenue

- une question fermée conserve son identifiant, sa réponse et sa date de clôture ;
- une question qui devient bloquante voit son statut modifié, jamais son identifiant ;
- une réponse partielle est consignée comme élément de réponse, sans clore la question ;
- une question résolue par un arbitrage renvoie vers la décision `DEC-nnn` correspondante ;
- les trous de séquence ne sont jamais comblés.
