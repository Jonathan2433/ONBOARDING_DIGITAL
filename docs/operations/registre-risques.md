# Registre des risques

**Produit en :** LOT 0, sous-étape S4 — story `MVP-L00-US006`
**Dernière mise à jour :** 7 septembre 2026, sous-étape `T5` du LOT 5 — et cette date **était la preuve du défaut corrigé ce jour-là** : elle disait `T7` du LOT 1 alors que `ROAD-RSK-034` a été ouvert en **`T8`**, si bien que le corps avait reçu le risque et l'en-tête non
**Sources reprises :** roadmap §14 et cahier des charges §33

| Origine | Identifiants | Nombre |
|---|---|---:|
| Roadmap §14, déjà numérotés | `ROAD-RSK-001` à `012` | 12 |
| Cahier des charges §33, numérotés par `DEC-430` | `ROAD-RSK-013` à `024` | 12 |
| Constatés pendant la réalisation | `ROAD-RSK-025` à `034` | 10 |
| **Total** | | **34** |

**Prochain identifiant libre : `ROAD-RSK-035`.**

Échelle d'impact reprise des documents sources : `Très élevé`, `Critique`, `Élevé`, `Moyen`,
plus les qualifications spécifiques `Accessibilité` et `Calendrier` employées au cahier §33.

> **CES TROIS NOMBRES ÉTAIENT FAUX JUSQU'AU 07/09/2026, ET ILS SONT DÉSORMAIS DÉRIVÉS.**
>
> Le tableau annonçait « `025` à `033` », **9** risques de réalisation et un total de **33**. Le
> corps en déclare **dix** — `ROAD-RSK-034`, ouvert en `T8` du LOT 1, mesure que publier un port
> perce l'isolement inter-réseaux de Docker — donc **34** au total. La date de mise à jour, restée
> à `T7`, était la preuve du mécanisme : classe `ECART-021`, un nombre affirmé sans être dérivé de
> sa source vieillit **en silence** à la première addition.
>
> **`make docs-check` les DÉRIVE désormais**, ce qu'il ne faisait que pour le registre des
> décisions — `ECART-053`, `DEC-565`. La commande qui fait foi, et qui compte **les déclarations
> barrées comme les autres** :
>
> ```bash
> uv run python infra/scripts/verifier-documentation.py
> ```
>
> **Ne rétablis aucun de ces nombres à la main sans relancer ce contrôle.**

---

# 1. Risques de roadmap — `ROAD-RSK-001` à `012`

Repris sans altération de la roadmap §14.

| ID | Risque | Impact | Mesure | Statut |
|---|---|---|---|---|
| `ROAD-RSK-001` | Le séquencement strict augmente le délai global | Élevé | Lots démontrables, périmètres fermes et validation rapide | Actif |
| `ROAD-RSK-002` | Un lot validé doit être rouvert après découverte tardive | Élevé | Tests d'intégration précoces et analyse d'impact | Actif |
| `ROAD-RSK-003` | Le lot collaborateurs devient trop volumineux | Moyen | Sous-démonstrations internes sans changer la porte de validation | Actif, LOT 5 |
| `ROAD-RSK-004` | Le vrai CSV arrive tardivement | Élevé | Schéma et données fictives préparés dès le LOT 0 | **Mesure en cours** — sous-étape S6 |
| `ROAD-RSK-005` | L’hébergement final retarde l’ouverture | Très élevé | Production temporaire locale et chantier infrastructure parallèle | Actif, lié à `QO-081` et `DEP-001` |
| `ROAD-RSK-006` | La charte officielle tarde | Moyen | Design tokens provisoires remplaçables sans refonte | Actif, lié à `DEP-006` |
| `ROAD-RSK-007` | Les dépendances Microsoft perturbent le MVP | Élevé | Maintien strict en V2 | Actif |
| `ROAD-RSK-008` | Les exigences de performance sont vérifiées trop tard | Élevé | Jeu de 5 000 profils dès le LOT 2 et mesures régulières | Actif |
| `ROAD-RSK-009` | La conformité vidéo reste incomplète | Moyen | Dérogation documentée et support facultatif des sous-titres en V1 | Actif |
| `ROAD-RSK-010` | Jonathan devient un goulot de validation | Élevé | Démonstration structurée et checklist concise à chaque porte | **Mesure en cours** — checklist `G0` prévue en S8 |
| `ROAD-RSK-011` | Un lot technique ne produit aucun résultat visible | Moyen | Démonstration obligatoire même pour le socle | Actif, LOT 1 |
| `ROAD-RSK-012` | Une fonction V1 est ajoutée prématurément | Moyen | Liste d'exclusion MVP et contrôle du backlog | Actif |

---

# 2. Risques majeurs du cahier des charges — `ROAD-RSK-013` à `024`

Repris sans altération du cahier §33. Ces risques n'y portaient **aucun identifiant** :
la décision `DEC-430` leur en attribue un afin de les rendre référençables et suivables.
Leur libellé et leur impact sont inchangés.

| ID | Risque | Impact | Réponse principale | Statut |
|---|---|---|---|---|
| `ROAD-RSK-013` | Fuite entre entités | Critique | Contrôles API, contraintes SQL et tests systématiques | Actif dès le LOT 2 |
| `ROAD-RSK-014` | Perte ou corruption de données | Critique | Transactions, sauvegardes et restauration testée | Actif |
| `ROAD-RSK-015` | Secret intégré au code | Critique | Scan de secrets et configuration externe | **Mesure partielle en place** — `.gitignore` et contrôles manuels ; détection automatique au LOT 1 |
| `ROAD-RSK-016` | Authentification indisponible | Élevé | Healthchecks, fournisseur validé et rollback | Actif dès le LOT 3 |
| `ROAD-RSK-017` | CSV réel exposé | Critique | FileVault, accès restreint, hors Git et sauvegardes chiffrées | **Mesure partielle** — FileVault constaté actif, `*.csv` exclu de Git |
| `ROAD-RSK-018` | Photo publiée sans autorisation | Élevé | Autorisation enregistrée et avatar par défaut | Actif dès le LOT 5 |
| `ROAD-RSK-019` | Mac local indisponible | Élevé | Production temporaire uniquement et migration vers hôte permanent | Actif |
| `ROAD-RSK-020` | Sauvegarde inutilisable | Critique | Test mensuel de restauration | Actif dès le LOT 13 |
| `ROAD-RSK-021` | Migration empêchant le rollback | Critique | Migrations progressives et compatibilité temporaire | **Mesure en place** — règle écrite dans les conventions de versions |
| `ROAD-RSK-022` | Jonathan seul référent | Élevé | Documentation, automatisation et second référent futur | Actif, lié à `QO-094` |
| `ROAD-RSK-023` | Sous-titres absents | Accessibilité | Écart documenté et ajout progressif | Actif |
| `ROAD-RSK-024` | Périmètre complet retardant l’ouverture | Calendrier | Lots séquentiels, sans sacrifice des exigences centrales | Actif |

---

# 3. Risques constatés pendant la réalisation — `ROAD-RSK-025` à `034`

## `ROAD-RSK-025` — Données personnelles et mot de passe en clair dans le prototype conservé

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S1 |
| Description | `docs/prototype/V1.html` contient environ 130 noms de collaborateurs, leurs photos en Base64, leurs clients, et un mot de passe administrateur en clair. Le fichier est conservé sur disque pour historisation par `DEC-420`. |
| Impact | **Critique** en cas de versionnement accidentel : l'historique Git est quasi indélébile. |
| Mesures en place | Exclusion par `.gitignore`, vérifiée par contrôle automatique ; interdiction explicite documentée dans `docs/prototype/README.md` ; contrôle de contenu à chaque commit vérifiant l'absence du mot de passe et de données Base64. |
| Mesure complémentaire | Le mot de passe du prototype doit être considéré comme **compromis** et ne jamais être réutilisé, dans aucun environnement. |
| Statut | **Atténué**, surveillance permanente. Retirer ce fichier de `.gitignore` exigerait une décision explicite et une analyse d'impact RGPD. |
| Écart associé | `ECART-002` |

## `ROAD-RSK-026` — Dépôt et futurs volumes dans iCloud Drive

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape S1 |
| Description | Le dépôt réside dans iCloud Drive par `DEC-418`. La synchronisation peut corrompre `.git`, provoquer des conflits, ou évincer des fichiers du disque local. À partir du LOT 1, `node_modules/`, les volumes Docker et les sauvegardes se trouveront dans une arborescence synchronisée. |
| Impact | Élevé sur les LOTS 1, 12 et 13. |
| Mesures en place | `.gitignore` empêche Git de suivre `node_modules/`, `data/`, `volumes/`, `backups/`. **Cela n'empêche pas iCloud de les synchroniser.** |
| **Mesure du 27/07/2026, sous-étape `T0`** | Le périmètre réel du risque est **plus étroit qu'annoncé**. `docker info` rapporte `Docker Root Dir : /var/lib/docker`, à l'intérieur de la machine virtuelle Docker Desktop, dont l'image disque de 28 Go réside sous `~/Library/Containers/com.docker.docker/Data/vms` — **hors iCloud Drive**. Tout **volume Docker nommé est donc déjà hors iCloud**, sans aucune action. Le risque ne portait réellement que sur `node_modules/`, le cache de paquets, et sur d'éventuels bind mounts de données vers le dépôt. |
| Atténuations retenues | `DEC-439` : `node_modules/` et le cache de paquets exclus de la synchronisation iCloud, store `pnpm` placé hors du dossier synchronisé, le dépôt restant dans iCloud. `DEC-447` : volumes nommés exclusivement, **aucun bind mount de donnée d'état** vers `./data`, `./volumes` ou `./backups` — c'est le seul geste qui ramènerait le risque sur les données. |
| **Mise en œuvre du 27/07/2026, sous-étape `T1`** | `DEC-453`. L'exclusion passe par l'attribut étendu `com.apple.fileprovider.ignore#P`. **Défaut découvert en posant la mesure : `pnpm install` supprime et recrée les `node_modules`, ce qui efface l'attribut** ; `uv` réutilise le `.venv` et le préserve. Une cible de `Makefile` seule n'aurait donc protégé que les installations lancées par `make`. Le marquage est confié à [`infra/scripts/exclure-icloud.sh`](../../infra/scripts/exclure-icloud.sh), appelé par `make icloud-exclude` **et** par le `postinstall` de `package.json`, que pnpm exécute après chaque installation. La cible `make icloud-verify` échoue si un répertoire n'est pas marqué : c'est elle qui a détecté l'effacement. |
| Volumétrie soustraite à iCloud, mesurée à `T1` | **276 Mio et 13 252 fichiers** dans le dépôt : `node_modules` 178 Mio / 11 066 fichiers, `.venv` 98 Mio / 2 176 fichiers, plus 40 Kio dans les trois `node_modules` d'espaces de travail. Hors dépôt et donc hors iCloud par construction : store `pnpm` 166 Mio, cache `uv` 103 Mio, CPython géré par `uv` 69 Mio. |
| **⚠ RISQUE MATÉRIALISÉ le 27/07/2026, constaté en `T1`** | **Ce risque n'est plus théorique.** Chronologie établie sur les horodatages d'inode, non sur des suppositions : **17:21:19** — création d'un répertoire `node_modules 2`, copie de conflit iCloud de 178 Mio et 11 066 fichiers, quelques minutes après la première pose de l'attribut d'exclusion ; **23:30:28 et 23:30:30** — les deux répertoires subissent un changement de métadonnées d'inode, sans qu'aucune action de session ne l'explique ; **au matin du 28/07** — la copie `node_modules 2` **porte** l'attribut d'exclusion, l'original `node_modules` l'a **perdu**, tous ses attributs étendus ayant disparu. Effets mesurés : `prettier --check .` passait de moins d'une seconde à **179 secondes** et échouait, en parcourant les 11 066 fichiers du duplicata. |
| Ce qu'il faut en retenir | **(1)** L'attribut d'exclusion **n'est pas durable dans le temps** : il ne suffit pas de le poser, il faut le vérifier. **(2)** Sa pose sur un répertoire qu'iCloud suit déjà a coïncidé avec la duplication — le mécanisme exact n'est pas établi et ne doit pas être affirmé, mais la corrélation temporelle est nette. **(3)** C'est `make icloud-verify` qui a détecté l'anomalie, pas un contrôle manuel : un vérificateur qui échoue est ce qui distingue une atténuation d'une intention. |
| Atténuations complétées en `T1` | Le nom d'une copie de conflit iCloud est le nom d'origine suivi d'une espace et d'un chiffre. Le motif `* [0-9]` est désormais exclu dans `.gitignore`, `.prettierignore`, `[tool.ruff] extend-exclude` et `eslint.config.js`, et **`make icloud-verify` échoue si une telle copie existe**. |
| Risque résiduel | Trois éléments. **(a)** La synchronisation de `.git` lui-même demeure, inchangée depuis `DEC-418`. **(b)** Le respect effectif de l'attribut par iCloud n'est **pas prouvé localement** : convention documentée par Apple, qu'aucun outil de cette machine ne permet de vérifier — `brctl` ne couvre pas les chemins CloudDocs et renvoie 0 sur erreur. **(c)** **Nouveau et le plus sérieux :** l'atténuation s'est révélée non durable en moins de sept heures, et la duplication qu'elle devait prévenir s'est produite. Un `node_modules` dans l'arborescence synchronisée reste exposé. |
| Arbitrage rendu le 28/07/2026 | `DEC-457`. Trois issues avaient été soumises à Jonathan : maintenir le marquage avec vérificateur, sortir physiquement `node_modules` et `.venv` de l'arborescence par liens symboliques, ou rouvrir `DEC-418`. **Retenu : maintenir l'atténuation en l'état**, avec `make icloud-verify` exécuté en début de session et intégré à `make check`. `DEC-418` n'est pas rouverte. La copie `node_modules 2` a été supprimée. **Le risque résiduel est accepté en connaissance de cause** : une nouvelle copie de conflit peut réapparaître ; le vérificateur la détectera, il ne l'empêchera pas. |
| **⚠ SECONDE MATÉRIALISATION le 29/07/2026, constatée en `T7`, et sur un mécanisme NOUVEAU** | Le conteneur `caddy` voyait un `/etc/caddy` **vide** alors que l'hôte portait bien son `Caddyfile` de 2 844 octets. Chronologie sur horodatages : conteneur créé à **09:51:38** ; `ctime` de `infra/caddy` **et** de `infra/caddy/Caddyfile` à **10:06:49**, soit 15 minutes plus tard, **sans aucune action de session** — la même signature que le 27/07 à 23:30:28. Diagnostic établi par élimination : un conteneur **neuf** monté sur la même source voyait le fichier sans peine, l'hôte le lisait, aucun attribut d'éviction iCloud n'était posé. **Ce que cela ajoute à ce risque :** `DEC-472` monte le **répertoire** et non le fichier, ce qui protège du remplacement du *fichier* par un éditeur — le défaut `T5-2`. Cela ne protège **pas** du remplacement du *répertoire*, car un conteneur ne re-résout pas la source d'un montage lié après sa création. Le périmètre du risque était donc plus large que `T5` ne l'avait établi. |
| Ce que la seconde matérialisation confirme, et ce qu'elle ajoute | **Confirme** que l'atténuation détecte sans empêcher, ce que `DEC-457` avait accepté. **Ajoute** que le garde-fou de `T5` a fonctionné : `make up` a échoué sur `caddy-reload`, alors que les huit services étaient `healthy` et que Caddy servait la configuration chargée à 09:51 — un service sain servant une configuration périmée, exactement le scénario que `T5` avait nommé. Mais le message masquait sa cause par un `2>/dev/null`, et annonçait « configuration invalide ou service absent » là où l'erreur réelle était « open /etc/caddy/Caddyfile: no such file or directory ». |
| Atténuation complétée en `T7` | `caddy-reload` **ne masque plus l'erreur** et **compare l'empreinte SHA-256 du `Caddyfile` vu par le conteneur à celle de l'hôte** avant de recharger : le contrôle nomme désormais la cause et donne le remède. Nouvelle cible **`make caddy-recreate`**, qui recrée le seul conteneur `caddy` — `--no-deps` — et lui fait re-résoudre son montage. C'est le seul geste qui répare un inode périmé. |
| Statut | **Accepté** par `DEC-418`, **atténué** par `DEC-439`, `DEC-447` et `DEC-453`, **matérialisé deux fois** — le 27/07/2026 sur `node_modules`, le 29/07/2026 sur `infra/caddy` —, **résiduel accepté** par `DEC-457`. `QO-109` close. À revoir à chaque porte. |

## `ROAD-RSK-027` — Mémoire vive insuffisante pour trois environnements simultanés

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026. **Réévalué le 27 juillet 2026** en sous-étape `T0`, sur mesures directes |
| Description d'origine | La machine dispose de **16 Gio** de mémoire vive. Chaque environnement compte environ huit services : PostgreSQL, Redis, MinIO, Caddy, API, worker, web, Mailpit. Trois environnements séparés sont exigés — développement, recette, production temporaire — soit environ 24 conteneurs si tous tournaient ensemble. |
| **Correction des prémisses** | Les deux prémisses d'origine étaient inexactes, dans le sens **défavorable**. **Premièrement**, le plafond réel n'est pas 16 Gio : `docker info` rapporte **7,75 Gio** alloués à la machine virtuelle Docker Desktop, soit la moitié de la mémoire physique. **Deuxièmement**, ce budget n'est pas libre : un projet tiers sans rapport avec eXalt, `observatoire-ecom-studio`, y exécutait **5 conteneurs depuis 5 jours** pour **~1,93 Gio**, soit **25 % du budget Docker**, dont 1,77 Gio pour son seul worker. La marge réellement disponible pour les 8 services du LOT 1 était donc d'environ **5,8 Gio**, et non de 16. |
| Impact | Élevé sur les LOTS 1, 12 et 13 : lenteur, échecs de démarrage, tests de charge non représentatifs. La coexistence de deux stacks complètes, envisagée en sous-étape `T8`, est **hors d'atteinte** sans intervention. |
| Mesures | `DEC-440` : les trois environnements ne sont jamais exécutés simultanément ; limites mémoire fixées par service ; mesure de performance réservée à un environnement exécuté seul ; **`observatoire-ecom-studio` arrêté pendant la durée du LOT 1**, ce qui porte le budget disponible à ~7,7 Gio pour une stack. La sous-étape `T8` prouve la **séparation** des environnements par démarrages **successifs** : le cahier §22.2 exige des ressources distinctes, il n'exige nulle part la simultanéité. |
| Statut | **Actif, traité** par `DEC-440`. Alimente `QO-085` d'un élément de réponse chiffré. |

## `ROAD-RSK-028` — Statut ambigu de la source de vérité prévalente

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026 |
| Description | Le cahier des charges, qui prévaut sur les quatre annexes validées, portait le statut « soumis à validation finale ». |
| Impact | Moyen : une source de vérité au statut incertain fragilise tout arbitrage qui s'en réclame. |
| Mesure | Validation explicite enregistrée sans modification du fichier. |
| Statut | **Clos** par `DEC-423`, le 27 juillet 2026. |
| Écart associé | `ECART-003` |

## `ROAD-RSK-029` — Un outil de formatage réécrit les documents de cadrage immuables

| Champ | Valeur |
|---|---|
| Constaté le | 27 juillet 2026, sous-étape `T1` du LOT 1 |
| Description | Les outils de formatage installés au LOT 1 traitent le Markdown par défaut. **Mesuré, non supposé :** exécuté sans exclusion, Prettier signalait les **cinq documents de cadrage immuables** comme à reformater, et la réécriture du seul cahier des charges lui ajoutait **54 661 octets**, soit **+21,7 %** — de 251 489 à 306 150 octets. Ruff, de son côté, voyait **41 fichiers Markdown** au lieu des 4 fichiers Python du dépôt, parce qu'il formate les blocs de code embarqués. |
| Impact | **Critique sur la traçabilité.** L'intégrité des cinq documents est prouvée par empreinte SHA-256 dans [`integrite-et-conformite-documents.md`](integrite-et-conformite-documents.md), et cette preuve est un élément de la porte `G0` franchie le 27/07/2026. Un reformatage automatique, y compris purement cosmétique, invaliderait les cinq empreintes d'un seul commit — sans qu'aucun contrôle existant ne le signale, puisque le contenu resterait sémantiquement identique. |
| Mesures | `DEC-454` : le Markdown est exclu de Ruff (`extend-exclude`) **et** de Prettier (`.prettierignore`), avec le motif inscrit dans les deux fichiers pour qu'un futur contributeur ne lève pas l'exclusion par méconnaissance. Contrôle de non-régression exécuté à `T1` : les 5 empreintes sont conformes, avec témoin négatif. |
| Risque résiduel | Réel. Tout outil ajouté plus tard — markdownlint, un formateur en CI, un greffon d'éditeur, un correcteur automatique de pull request — rouvrirait le risque. **Recommandation pour `T6` :** ajouter à la CI un contrôle qui recalcule les cinq empreintes et échoue si l'une diffère. C'est le seul garde-fou qui ne dépende pas de la configuration d'un outil particulier. |
| Statut | **Actif, traité** par `DEC-454`. Garde-fou de CI à poser en `T6`. |

## `ROAD-RSK-030` — L'image `web` embarque son outillage de développement

| Champ | Valeur |
|---|---|
| Constaté le | 28 juillet 2026, sous-étape `T2` du LOT 1 |
| Description | L'image `onboarding-dev-web` pèse **924 Mio**, contre 284 Mio pour `api` et `worker`. Son `Dockerfile` installe le workspace `pnpm` **complet** : ESLint et ses greffons, Prettier, `typescript-eslint`, Vitest, les types React — soit tout l'outillage de qualité, dont une image d'exécution n'a aucun besoin. |
| Impact | Nul en développement, **réel à partir de `T7`**. Le cahier §22.3 exige des images `linux/arm64` **et** `linux/amd64` publiées dans GHCR : une image de 924 Mio est publiée deux fois, téléchargée à chaque déploiement, et analysée par Trivy à chaque exécution de la CI. Elle augmente aussi la surface d'audit de `pip-audit` et de Trivy sans contrepartie : chaque dépendance de développement embarquée est une vulnérabilité potentielle à trier. |
| Cause | Choix assumé de `T2`, dont le critère porte sur le démarrage et la santé des services, non sur la taille des images. Un `Dockerfile` multi-étapes séparant construction et exécution relève de `T7`, qui possède la publication GHCR. |
| Mesure | Aucune à `T2`, volontairement — la corriger ici anticiperait `T7`. **`T7` doit produire une image d'exécution multi-étapes** : construction avec l'outillage complet, exécution avec le seul artefact statique servi. L'ordre de grandeur attendu est celui d'`api`, sinon moins. |
| Contrôle proposé pour `T7` | Faire échouer la construction si l'image d'exécution dépasse un plafond déclaré. Un contrôle de taille qui n'échoue pas ne sert à rien. |
| Réévaluation du 28/07/2026, sous-étape `T5` | **Le risque s'est aggravé, et c'est `T5` qui l'a aggravé.** L'image passe de **924 Mio à 1,02 Gio** : `T5` ajoute `jsdom`, `@testing-library/react` et `@testing-library/dom` aux dépendances de développement, indispensables aux tests de la page et prescrits par le cahier §17.1, et le `Dockerfile` mono-étape les embarque tous. Le `.dockerignore` de `DEC-473` **ne compense pas** : il retire du contexte le `node_modules` de l'hôte, qui n'était constitué que de liens symboliques, donc quasiment sans poids. Les 100 Mio supplémentaires sont bien installés dans l'image. Mesure : `api` et `worker` restent à 662 Mio. |
| **Traitement du 29/07/2026, sous-étape `T7` — `DEC-479`** | `Dockerfile` multi-étapes à **deux cibles nommées**. La cible publiée, `execution`, part de `caddy:2.11-alpine` et ne contient que l'artefact de `vite build`. **Mesures avant et après, usage disque :** `web` **1,02 Gio → 84,9 Mo**, soit **−91,7 %** ; `api` et `worker` **662 Mo → 473 Mo**, soit −29 %. Absence de l'outillage vérifiée par `command -v` sur cinq outils dans l'image d'exécution : `node`, `npm`, `pnpm`, `vite`, `eslint` — **5 absents sur 5**. |
| **Second gisement, découvert par la mesure et non prévu par ce risque** | `docker history` a montré que le `RUN chown -R` final de chaque image pesait **230 Mio dans `web`** et **143 Mio dans `api` et `worker`**. Motif : une couche d'image réenregistre le fichier **entier** dès qu'une seule de ses métadonnées change ; la couche **duplique** donc l'arborescence dont elle ne modifie que le propriétaire. Corrigé dans les trois `Dockerfile` par création de l'utilisateur avant les copies et `COPY --chown`. C'est ce gisement, et non l'outillage, qui explique les 29 % gagnés par `api` et `worker`, que ce risque ne visait pas. |
| Contrôle posé, et il échoue réellement | `make images-inspect` compare la **taille de contenu** de chaque variante publiée à un **plafond déclaré** — 130 Mio pour `api` et `worker`, 35 Mio pour `web` — et **échoue au-delà**. Éprouvé par témoin : plafond abaissé à 100 Mio, le contrôle sort en échec en nommant le dépassement. Le plafond porte sur la taille de **contenu** et non sur l'usage disque, pour un motif mesuré : `docker image ls --tree` annonce 473 Mo pour la variante `arm64` et 114 Mo pour la variante `amd64` de la **même** image, seule la variante native étant dépaquetée localement. Un plafond fondé sur cette grandeur passerait ou échouerait selon l'architecture de l'exécuteur. |
| Statut | **Clos** le 29 juillet 2026, sous-étape `T7`, par `DEC-479`. Risque résiduel nommé : les images `api` et `worker` embarquent encore `uv` et `uvx`, **55,1 Mio mesurés**, qui ne servent qu'à la construction. Trivy n'y trouve **aucune** vulnérabilité — cible `rustbinary`, 0 avis — le gisement est donc de poids seulement. Une étape de construction séparée les retirerait ; ce n'est pas fait, pour ne pas cumuler deux restructurations dans la même sous-étape. Recommandation consignée au compte rendu de `T7`. |

---

## `ROAD-RSK-031` — Le service `web` exécute un serveur de développement, y compris hors développement

| Champ | Valeur |
|---|---|
| Constaté le | 28 juillet 2026, sous-étape `T5` du LOT 1 |
| Description | Le `Dockerfile` de `apps/web` a pour commande `node ./node_modules/vite/bin/vite.js`, soit le **serveur de développement** Vite : transformation à la demande, aucun empaquetage, aucune minification, module de rechargement à chaud actif. Cette commande vit dans l'image, donc dans le service `web` de `docker-compose.base.yml`, que **toutes** les surcouches d'environnement héritent. |
| Impact | Nul en développement, où c'est le comportement voulu. **Réel à partir de `T8`** : l'environnement de recette servirait un artefact différent de celui de la production, ce qui vide la recette de sa valeur — le cahier §22.2 exige des environnements séparés, et recetter autre chose que ce qui sera déployé est pire qu'une séparation imparfaite. Réel aussi en production temporaire au LOT 13 : un serveur de développement n'a ni les performances, ni la surface d'attaque réduite d'un artefact statique. |
| Cause | `T5` doit rendre la page visible, et le critère de la fiche §3 porte sur l'affichage de l'état réel, pas sur le mode de service. Produire dès maintenant une cible d'exécution multi-étapes anticiperait `T7`, qui possède la construction des images. |
| Mesure | Aucune à `T5`, volontairement, et **c'est dit plutôt que laissé croire**. `T7` doit introduire un `Dockerfile` multi-étapes avec **deux cibles nommées** : une de développement conservant le serveur Vite, une d'exécution servant l'artefact de `vite build`. `T8` doit alors sélectionner explicitement la cible d'exécution dans la surcouche de recette. Traite le même défaut que `ROAD-RSK-030` par le même moyen. |
| Contrôle proposé pour `T8` | Vérifier que la page servie en recette ne porte **aucune** référence à `/@vite/client` — présente en développement, absente d'un artefact construit. Un contrôle qui distingue les deux modes, et non un contrôle qui vérifie seulement que la page répond. |
| **Traitement du 29/07/2026, sous-étape `T7` — `DEC-479`** | Deux cibles nommées, comme la mesure ci-dessus le prévoyait : `developpement` conserve le serveur Vite, `execution` sert l'artefact statique par Caddy. **Aucune n'est choisie dans `docker-compose.base.yml`** : chaque surcouche la sélectionne explicitement, et `make images-check` **échoue** si une surcouche omet la ligne. Motif : l'omission serait silencieuse — sans `target`, Docker construit la dernière étape du `Dockerfile`, soit `execution`, et la stack de développement perdrait le rechargement à chaud en restant parfaitement saine. |
| **Le contrôle proposé pour `T8` est posé dès `T7`, et il discrimine** | La cible `execution` est lancée sur les deux architectures et la page servie est examinée : **0 occurrence** de `/@vite/client`, et `/assets/` présent, donc un artefact empaqueté. **Le témoin positif est indispensable et il est exécuté** : la même sonde appliquée à la cible `developpement` trouve **1 occurrence**. Sans lui, « 0 occurrence » serait indistinguable d'une expression régulière fausse — c'est le défaut `T5-7`. `T8` héritera du contrôle au lieu de devoir l'écrire. |
| Statut | **Clos** le 29 juillet 2026, sous-étape `T7`, par `DEC-479`. `T8` doit encore **sélectionner** la cible `execution` dans la surcouche de recette : le contrôle l'y attend et échouera si elle ne nomme aucune cible. |

---

## ~~`ROAD-RSK-032`~~ — CLOS en `T10`

| Champ | Valeur |
|---|---|
| Constaté le | 29 juillet 2026, sous-étape `T6` du LOT 1, par le contrôle 10 du cahier §23.1 lui-même |
| Description | `GHSA-mh99-v99m-4gvg` — `brace-expansion` ≤ 5.0.7, déni de service par expansion non bornée provoquant un arrêt du processus faute de mémoire. **Sévérité haute.** Chemin : `eslint-plugin-jsx-a11y > minimatch@3.1.5 > brace-expansion@1.1.16`. |
| Impact réel, et il faut le mesurer plutôt que le supposer | **Faible.** La dépendance est **transitive** et **de développement seulement** : elle s'exécute pendant `eslint`, sur les motifs de fichiers que **nous** écrivons dans `eslint.config.js`, et n'entre dans **aucun artefact livré** — ni l'image `api`, ni `worker`, ni le futur artefact statique de `web`. Le déclencheur du déni de service serait un motif d'expansion hostile ; il n'y en a pas, et il n'y en aura pas sans qu'un humain l'écrive dans la configuration du lint. |
| Pourquoi ce n'est pas corrigé — **mesuré, pas supposé** | Deux mesures du 29/07/2026 ferment les deux issues évidentes. **1.** La dernière version publiée de la ligne 1.x **est** `1.1.16`, celle qui est installée : il n'existe **aucun correctif** dans cette ligne, seulement en `5.0.8`. **2.** Forcer `5.0.8` **casserait le lint** : son export CommonJS est un **objet** portant `.expand`, et non une fonction appelable, alors que `minimatch@3.1.5` fait `expand(motif)` — vérifié en installant la version et en l'appelant, « m is not a function ». On remplacerait donc un déni de service théorique par la neutralisation **certaine** d'ESLint, et avec lui de `eslint-plugin-jsx-a11y`, motif déterminant de `DEC-451` et seul garde-fou d'accessibilité automatisé du projet. |
| Mesure retenue | **Tolérance nommée et étroite** (`DEC-474`) : `auditConfig.ignoreGhsas` dans `pnpm-workspace.yaml`, cet avis et lui seul. Tout autre avis, de toute sévérité, continue de faire échouer `make audit` et donc l'intégration continue — éprouvé par témoin, un identifiant bidon fait rééchouer l'audit. La sortie affiche « 1 high (**1 ignored**) » : la tolérance est **visible** dans chaque exécution, jamais silencieuse. |
| Déclencheur de réévaluation | La mise à jour d'`eslint-plugin-jsx-a11y` vers un `minimatch` moderne. **Le même greffon déclare déjà ESLint `^3 || … || ^9` alors que nous exécutons ESLint 10** : sa mise à jour est à surveiller pour les deux motifs à la fois. Retirer alors la tolérance et vérifier que `make audit` reste vert sans elle. |
| Statut | **Ouvert, résiduel accepté en connaissance de cause.** À réévaluer à chaque lot, et au plus tard à la porte `G12`, recette transverse. |

> **✅ CLOS le 30 juillet 2026, sous-étape `T10`, et le motif renverse une mesure de `T6`.**
>
> `T6` avait mesuré qu'aucun correctif n'existait dans la ligne 1.x de `brace-expansion` — « la
> dernière version publiée de la ligne 1.x EST 1.1.16 » — et que forcer la ligne 5 cassait ESLint,
> donc `eslint-plugin-jsx-a11y`. Cette mesure était juste à sa date.
>
> **Mesure du 30/07/2026 : la ligne 1.x a reçu `1.1.18`.** Un `pnpm update -r brace-expansion
> nanoid`, dans les plages déjà déclarées et sans forcer aucune version majeure, suffit. L'audit
> passe de **4 avis hauts, 1 toléré** à **zéro avis**, et rien n'est cassé — lint, formatage,
> typage et les deux suites de tests restent à zéro, `jsx-a11y` compris, éprouvé par témoin négatif
> sur cinq fautes d'accessibilité.
>
> **La tolérance de `DEC-474` est retirée par `DEC-493`** : elle ne couvre plus rien, et une
> tolérance devenue inutile avalerait silencieusement une réapparition du même avis.
>
> **La leçon, et elle vaut pour la suite :** un résiduel accepté parce qu'« aucun correctif
> n'existe » doit être **réévalué**, pas archivé. Ici l'écosystème a bougé en un jour.

---

## `ROAD-RSK-033` — Les images publiées héritent de vulnérabilités sans correctif de leurs images de base

| Champ | Valeur |
|---|---|
| Constaté le | 29 juillet 2026, sous-étape `T7` du LOT 1, par la mesure Trivy qui précède `DEC-482` |
| Description | Les trois images publiées dans GHCR portent les vulnérabilités de leurs images de base officielles. Mesures du 29/07/2026, plateforme `linux/arm64`, Trivy 0.72.0 : `python:3.12-slim` — donc `api` et `worker` — **4 `CRITICAL`, 19 `HIGH`, 176 avis au total** ; `caddy:2.11-alpine` — donc la cible `execution` de `web` — **0 `CRITICAL`, 10 `HIGH`, 27 avis**. |
| Le fait qui commande la décision | **Aucun des 23 avis `HIGH` ou `CRITICAL` de `python:3.12-slim` n'a de version corrective publiée.** Quatre `CRITICAL` dans `perl-base`, le reste dans la famille util-linux, `gzip` et ncurses. Debian trixie ne propose pas de correctif : il n'y a rien à mettre à jour. |
| Second fait, qui borne la responsabilité du projet | **Nos couches n'ajoutent aucune vulnérabilité.** Les totaux des images sont **exactement** ceux de leurs bases : 176 pour `api` comme pour `python:3.12-slim`, 27 pour `web` comme pour `caddy:2.11-alpine`. Le paquet `uv` embarqué est analysé comme `rustbinary` et ne porte **aucun** avis. |
| Impact | **Modéré, et il faut le qualifier plutôt que le compter.** Ces images ne sont pas exposées : elles vivent derrière Caddy sur la boucle locale (`DEC-460`), sans authentification à protéger avant le LOT 3, et sans donnée réelle avant le LOT 9. L'impact deviendra réel à la production temporaire du LOT 13, où l'exposition change de nature. |
| Pourquoi la porte ne bloque pas sur `HIGH` — mesuré, pas supposé | Bloquer sur `HIGH` rendrait la chaîne **définitivement rouge sans remède** : le seul « correctif » serait d'abandonner Debian slim, que `DEC-443` a retenu sur un motif mesuré — de nombreuses roues Python n'existent pas en musl, ce qui forcerait une compilation depuis les sources. Un contrôle qui exige l'impossible finit désactivé, et un contrôle désactivé ne prouve rien. C'est la leçon de `T6-4` appliquée à un seuil au lieu d'une mise en forme. |
| Mesure retenue | **`DEC-482`.** La porte bloque sur `CRITICAL` **corrigeable** — `--ignore-unfixed`, qui n'abaisse pas le seuil mais retire ce qu'aucune action ne peut corriger — et **rapporte sans bloquer** tout le reste, le compte complet étant affiché à chaque exécution. Vert aujourd'hui : **0 `CRITICAL` corrigeable** sur les trois images. Capable d'échouer, et ce n'est pas une supposition : l'image `web` d'**avant** `T7` en portait exactement un, `tar 7.5.13 → 7.5.19` dans le npm embarqué par Node. |
| Un second gisement, mineur mais nommé | Le socle d'exécution de `web`, `caddy:2.11-alpine`, repose sur **Alpine 3.23.5** avec 17 avis de paquets système, là où `node:24.16-alpine` est sur **Alpine 3.24.1** avec **0**. La cible publiée porte donc un socle plus ancien que la cible de développement. Contrepartie mesurée et assumée : cette image est **déjà** dans le projet pour le mandataire inverse, à la même empreinte — la réutiliser n'ajoute **aucune vulnérabilité distincte** au périmètre du projet. |
| Déclencheur de réévaluation | La publication d'une image `caddy:2.11-alpine` sur un Alpine plus récent, ou d'un `python:3.12-slim` corrigeant `perl-base`. À réévaluer **avant le LOT 13**, où la production temporaire change la nature de l'exposition, et au plus tard à la porte `G12`. |
| Statut | **Ouvert, résiduel accepté en connaissance de cause** par `DEC-482`. Mesuré à chaque publication, et visible dans chaque exécution. |

---

## `ROAD-RSK-034` — Publier un port perce l'isolement inter-réseaux de Docker

| Champ | Valeur |
|---|---|
| Ouvert le | 29 juillet 2026, sous-étape `T8` du LOT 1 |
| Source | Constat de mesure pendant `T8`. Cahier des charges §22.2, « réseau distinct » ; `DEC-460`, publications limitées à `127.0.0.1` |
| Constat | **Deux réseaux Docker distincts ne sont pas mutuellement inatteignables, et l'écart vient des ports publiés.** Mesuré le 29/07/2026, **sur un même conteneur**, ce qui élimine toute cause propre à un service :<br>`dev mailpit 172.20.0.4:8025`, **publié** → **JOIGNABLE** depuis le conteneur `api` de la recette ;<br>`dev mailpit 172.20.0.4:1025`, **non publié** → `TimeoutError`.<br>Confirmé de bout en bout : depuis la recette, une connexion à PostgreSQL de dev **aboutit** et `current_database()` rend `onboarding_dev`. Les **7** ports publiés du développement sont joignables ainsi. |
| Cause | Docker installe pour chaque port publié une règle `ACCEPT` dans la chaîne `FORWARD`, et elle **précède** ses règles `DOCKER-ISOLATION` qui rejettent le trafic entre réseaux. Le paquet est donc accepté avant que l'isolement n'ait la parole. Le préfixe `127.0.0.1` de `DEC-460` protège du réseau local et du pare-feu de macOS ; il ne protège pas d'un autre réseau Docker **de la même machine**. |
| Ce que le cahier exige, et ce qu'il n'exige pas | Le §22.2 demande un « **réseau distinct** ». C'est **acquis et prouvé** : noms distincts, sous-réseaux distincts — `172.20.0.0/16` contre `172.22.0.0/16` — et DNS isolé, le nom d'un conteneur de dev n'étant pas résolu depuis la recette (`gaierror`). Le cahier ne demande **pas** l'inatteignabilité mutuelle. Le critère est donc satisfait ; ce risque porte sur ce qui **dépasse** le critère. |
| Barrière effective, et elle est MESURÉE | **Les secrets distincts.** Avec le mot de passe de la recette, la même connexion à la base de dev est **refusée** en « password authentication failed ». C'est la cinquième séparation du cahier qui protège, pas la sixième. `make separations-check` en fait une **exigence** et non une affirmation : le contrôle échoue si ce secret ouvre la base de l'autre environnement. |
| Impact | **Faible au LOT 1**, où aucun environnement ne porte de donnée réelle et où les deux stacks ne tournent ensemble que le temps d'une mesure (`DEC-440`). **À réévaluer avant le LOT 13** : la production temporaire locale portera des données réelles de collaborateurs, et coexistera sur la même machine que le développement et la recette. Un identifiant fuité d'un environnement deviendrait alors exploitable depuis un autre. |
| Atténuations disponibles, non retenues au LOT 1 | Ne pas publier les ports de la recette — mais ils servent au diagnostic, et `T9` les documentera ; `internal: true` sur le réseau — mais il coupe aussi l'accès sortant ; des règles d'isolement explicites — hors de portée sans droits d'administration (`QO-114`). Aucune n'est appliquée ici : la cinquième proposition de la règle du lot demande de mesurer ce qu'un correctif casse avant de l'appliquer, et aucune de ces trois n'a été mesurée. |
| Déclencheur de réévaluation | L'ouverture du **LOT 13**, et toute décision de faire coexister durablement deux environnements dont l'un porte des données réelles. |
| Statut | **Ouvert, résiduel accepté au LOT 1.** Mesuré et **rapporté visiblement** à chaque exécution de `make separations-check`, qui nomme les ports percés — le taire aurait produit un « 7 séparations prouvées » laissant croire davantage que ce qui est vrai. Même parti que `DEC-482` pour Trivy. |

---

# 4. Règles de tenue

- un risque clos conserve son identifiant, son texte et la mesure qui l'a traité ;
- un risque accepté reste actif au registre avec la mention `Accepté` et la décision associée ;
- les libellés repris des documents validés ne sont **jamais** reformulés ;
- un risque de sécurité, d'intégrité, d'isolation ou d'accessibilité essentielle qui se
  matérialise devient une anomalie prioritaire sur le lot en cours (`ARB-BACK-005`) ;
- chaque porte de validation revoit l'état des risques du lot concerné.
