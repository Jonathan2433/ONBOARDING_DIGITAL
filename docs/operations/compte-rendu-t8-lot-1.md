# Compte rendu — sous-étape `T8` du LOT 1

**Exécutée le :** 29 juillet 2026
**Objet :** environnement de recette isolé, distinct du développement sur les **sept** séparations du cahier §22.2
**Story :** `MVP-L01-US002`, issue [#3](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/3), **rouverte** comme `T5` l'avait fait
**Fondement :** cahier §16.5, §22.2, §22.3, §23.2 ; roadmap LOT 1 ; `DEC-440`, `DEC-444`, `DEC-460`, `DEC-470`, `DEC-472`, `DEC-477`, `DEC-478`, `DEC-479`
**Décisions produites :** `DEC-483` à `DEC-488`
**Écart ouvert et clos :** `ECART-023` · **Risque ouvert :** `ROAD-RSK-034` · **Question close :** `QO-085` · **Réserve levée :** fiche §3.1

---

## 1. Le critère, et où il se compte

> « Volumes, base, bucket, réseau, ports et secrets distincts du développement ; Mailpit
> exclusif. » — fiche §3, **avant rectification**

**Ce critère énumérait six séparations là où le cahier §22.2 en énumère sept, et empruntait
« Mailpit exclusif » à deux lots à venir.** C'est `ECART-023`, et c'est la première chose que
`T8` a établie — avant d'écrire une ligne.

| | Cahier §22.2, littéral | Mécanisme retenu | Prouvé par |
|--:|---|---|---|
| 1 | **projet Docker distinct** — *absent de la fiche* | `COMPOSE_PROJECT_NAME=onboarding-recette` | étiquette `com.docker.compose.project` des 8 conteneurs en marche |
| 2 | base PostgreSQL distincte | `POSTGRES_DB=onboarding_recette` | `current_database()` **dans** chaque instance, **et** absence de la base de l'autre |
| 3 | bucket MinIO distinct | `MINIO_BUCKET=onboarding-recette-media` | `mc stat` dans chaque MinIO, **et** absence du bucket de l'autre |
| 4 | volumes distincts | automatique, préfixe de projet | 6 volumes de chaque côté, **intersection vide** |
| 5 | secrets distincts | **engendrés** à la création | 5 sur 5 distincts, **et** distincts dans le conteneur, aucune valeur imprimée |
| 6 | réseau distinct | `onboarding-recette-net` | noms, **sous-réseaux**, DNS, et routage éprouvé — voir §5.2 |
| 7 | ports distincts | bande `8080`–`19001` | 7 contre 7, **intersection vide**, toutes sur `127.0.0.1` |

**`make separations-check` compte lui-même les séparations examinées** et échoue si elles ne sont
pas sept. Un contrôle qui n'énumère pas ce qu'il examine peut toujours n'en avoir vu qu'une partie.

**Résultat : 57 contrôles, 0 échec.**

---

## 2. Ce qui a été livré

| Emplacement | Contenu |
|---|---|
| `infra/compose/docker-compose.recette.yml` | **Nouveau.** 7 publications sur `127.0.0.1`, **3 images publiées épinglées par empreinte**, `web: build: target: execution` |
| `infra/compose/differences-recette.env` | **Nouveau.** Calque versionné, 17 variables, **aucun secret** |
| `infra/scripts/composer-env.py` | **Nouveau.** Engendre un fichier d'environnement : modèle + calque + secrets |
| `infra/scripts/epingler-images.py` | **Nouveau.** `make images-pin` — **dérive** les empreintes de la publication |
| `infra/scripts/verifier-separations.py` | **Nouveau.** Les 7 séparations, l'artefact en marche, l'architecture, la cible `execution`, Mailpit, `QO-085` |
| `infra/scripts/verifier-documentation.py` | **Contrôle ajouté** : les totaux du registre des décisions, dérivés (`DEC-488`) |
| `Makefile` | **Paramétré par `ENVIRONNEMENT`.** 15 cibles généralisées, 44 → **50 cibles** |
| `infra/caddy/Caddyfile` | Adresses de site **substituées depuis l'environnement**, défauts = développement |
| `infra/compose/docker-compose.base.yml` | Le service `caddy` transmet `CADDY_SITE_APP` et `CADDY_SITE_API` |
| `.env.example` | **v1.2** — 79 variables : `CADDY_SITE_APP` et `CADDY_SITE_API` ajoutées |

### 2.1 Le vrai travail était le `Makefile`, et le vrai risque la régression

Quinze cibles étaient câblées sur la surcouche `dev` : `up down destroy ps logs minio-bucket
caddy-reload caddy-recreate health ports migrate migrate-status alembic-check api-check
persistence-test`. Dix-huit occurrences de `DC_DEV`, `ENV_FILE` en dur,
`MINIO_ROOT_USER=onboarding-dev-admin` en dur, et un message de confirmation de `destroy` qui
nommait `onboarding-dev` quel que soit l'environnement détruit.

**J'ai paramétré plutôt que dupliqué**, et il faut dire pourquoi : quinze cibles `*-recette`
portant chacune une copie de la recette de son homologue auraient été deux copies d'une même
logique, qui divergent en silence. C'est le motif de `DEC-466` pour le masquage et de `ECART-022`
pour les modèles de configuration. Les quatre alias `*-recette` **délèguent** et ne portent aucune
logique propre.

**Le risque assumé de ce choix est la régression sur `dev`, et la parade a été prise avant la
première modification** : les onze codes de sortie de la ligne de base ont été **relevés d'abord**,
puis confrontés après. C'est ce qui rend la non-régression du §5.4 démontrable et non affirmée.

**Une bonne surprise, mesurée :** les quatre scripts de contrôle de `T2` et `T5` étaient **déjà
paramétrables** — `verifier-ports.sh`, `verifier-sante.sh`, `verifier-persistance.sh` prennent le
fichier d'environnement et les fichiers Compose en arguments, `verifier-page-statut.sh` prend
l'origine. Le travail était donc dans le `Makefile` seul.

### 2.2 Un seul `Caddyfile`, et la mesure qui l'a permis

Le bloc `app.` porte le mandatement de même origine de `DEC-470` — `/health/*`, `/api/*` et le
fourre-tout. Le dupliquer par environnement aurait créé **deux copies d'une règle de sécurité**, et
le jour où l'une divergerait, la recette n'éprouverait plus le montage que la production emploie.
`T7` §2.3 avait déjà refusé cette duplication pour la même raison.

**Rien ne garantissait que Caddy substitue une variable dans une ADRESSE DE SITE**, qui est lue
avant l'analyse des directives. Éprouvé sur un conteneur jetable, **dans les deux sens** :

```text
sans les variables  ->  hotes adaptes : api.onboarding.localhost, app.onboarding.localhost
avec les variables  ->  hotes adaptes : api.recette.onboarding.localhost, app.recette....
```

Sans le second essai, « la configuration est valide » aurait été la même observation dans les deux
cas et n'aurait rien prouvé. Les défauts inscrits dans le fichier sont ceux du développement : un
environnement qui ne déclare rien se comporte exactement comme avant `T8` — vérifié en relisant la
configuration **chargée** par Caddy, et non le fichier.

### 2.3 La recette exécute l'artefact publié, et un contrôle le dit

`DEC-478` posait le motif : « une recette qui exerce un autre artefact que la production ne recette
rien. » La surcouche épingle donc les trois images **publiées**, par **empreinte de liste de
manifestes** et non par étiquette — trois raisons :

1. `make images-check` **exige** `@sha256:` sur toute référence des fichiers suivis (`DEC-443`,
   cahier §23.3). Le contrôle attendait cette surcouche ;
2. le critère de la story dit « une même version **immuable** fonctionne », et `develop` désigne un
   artefact différent à chaque fusion ;
3. le fichier de base déclare `build:` pour ces trois services. **Sans garde-fou, une image absente
   ferait construire localement et la recette exercerait un autre artefact en paraissant
   parfaitement saine.** `--no-build` transforme ce détournement silencieux en échec bruyant —
   éprouvé pour de vrai avant l'authentification : `unauthorized` sur les trois, **0 conteneur
   démarré, 0 construction de repli**.

**Les empreintes sont mesurées, pas transcrites.** `make images-pin` les dérive des journaux de la
tâche `publier`, qui les tient elle-même du `--metadata-file` de buildx. Contrôle croisé : les
valeurs dérivées et celles inscrites dans la surcouche sont **identiques, 3 sur 3**.

---

## 3. Ce qui n'est PAS couvert, et il faut le dire

1. **Les ports publiés d'un environnement restent joignables depuis l'autre.** Ce n'est pas une
   supposition : c'est mesuré, expliqué et rapporté à chaque exécution. Le cahier §22.2 exige un
   « réseau distinct », ce qui est acquis ; il n'exige pas l'inatteignabilité. `ROAD-RSK-034`.
2. **« Mailpit exclusif » et « aucun e-mail réel ne part de la recette » n'appartiennent pas au
   LOT 1.** La première est `MVP-L11-US003`, la seconde un critère de sortie du **LOT 13**. Ce que
   `T8` prouve est énoncé au §4 sans extrapolation.
3. **Le §23.2 « déploie la recette locale » n'est toujours pas automatisé**, et ne peut pas l'être :
   `total_count: 0` exécuteur auto-hébergé, mesuré en `T7`. La recette est lancée à la main par
   `make up-recette`.
4. **`make up` n'est pas auto-réparateur depuis un état laissé par un démarrage contourné.** Voir
   `T8-4` : c'est diagnostiqué, reproductible, et non corrigé — à documenter en `T9`.
5. **La simultanéité des deux environnements est MESURÉE, non autorisée.** `DEC-440` reste en
   vigueur ; `T8` prouve la séparation par démarrages **successifs**.
6. **Aucune donnée métier, aucune table, aucune authentification.** La recette est une plateforme
   vide, comme le développement.

---

## 4. Mailpit — ce que le LOT 1 prouve, et ce qui appartient ailleurs

**Où est la source, exactement.** Le cahier §16.5 dit « Mailpit en développement **et recette** » :
c'est l'exigence du LOT 1, et elle est satisfaite. La formule « Mailpit est **exclusif** en
recette » vient de `MVP-L11-US003`, donc du **LOT 11**. « Aucun e-mail réel ne part de la recette »
est un **critère de sortie du LOT 13**.

**Ce qui est prouvé ici, et comment :**

| Contrôle | Résultat |
|---|---|
| Aucun fournisseur réel configuré | `EMAIL_PROVIDER=mailpit` et `SMTP_HOST=mailpit` des **deux** côtés |
| `SMTP_HOST` résout dans **son** réseau | acquis par la sixième séparation : chaque réseau a son DNS |
| Un e-mail émis par la recette arrive dans **sa** capture | total de recette **0 → 1** |
| Et **ne touche pas** celle du développement | total de dev **6 → 6, inchangé** |

**Le refus de conclure sur un zéro est délibéré, et c'est la leçon de `T2-5`** : un Mailpit vide et
un volume effacé rendent la même valeur. Le contrôle **échoue** si le total de la recette reste nul,
et exige une augmentation d'exactement 1.

---

## 5. Contrôles exécutés, et leurs témoins

### 5.1 Les sept séparations — 57 contrôles, 0 échec

Extraits des mesures qui comptent :

```text
projet    onboarding-dev / onboarding-recette, 8 conteneurs etiquetes de chaque cote
base      current_database() = onboarding_dev / onboarding_recette
          base de l'autre : ABSENTE des deux instances
bucket    chaque MinIO porte SON bucket, aucun ne voit celui de l'autre
volumes   6 et 6, intersection VIDE
secrets   5 sur 5 distincts, et distinct DANS le conteneur. Aucune valeur imprimee
reseau    sous-reseaux 172.20.0.0/16 contre 172.22.0.0/16, DNS isole
ports     7 et 7, intersection VIDE, toutes sur 127.0.0.1
```

### 5.2 La sixième séparation a DÉMENTI ce que j'attendais

**Mon premier contrôle exigeait que la base de dev soit injoignable depuis la recette. Il a
échoué — sur un livrable conforme.** J'ai diagnostiqué avant de corriger, ce qui est la leçon de
`T7-13`, et le diagnostic a produit un constat que le critère ne visait pas.

**L'épreuve décisive porte sur un MÊME conteneur**, ce qui élimine toute cause propre à un service :

| Cible | Publié sur l'hôte ? | Depuis la recette |
|---|---|---|
| `dev mailpit 172.20.0.4:8025` | **oui** | **JOIGNABLE** |
| `dev mailpit 172.20.0.4:1025` | non | `TimeoutError` |

**Docker installe pour chaque port publié une règle `ACCEPT` dans la chaîne `FORWARD`, et elle
précède ses règles `DOCKER-ISOLATION`.** Le paquet est accepté avant que l'isolement n'ait la
parole. Confirmé de bout en bout : depuis la recette, une connexion à PostgreSQL de dev **aboutit**
et `current_database()` rend `onboarding_dev`.

**Ce qui protège réellement est la cinquième séparation, et c'est mesuré :** avec le mot de passe de
la recette, la même connexion est **refusée** — « password authentication failed ».

**Le contrôle a donc été refait pour affirmer le vrai et rapporter le résiduel**, plutôt que
d'être affaibli :

- **exigé** : noms de réseau distincts, **sous-réseaux** distincts, nom de conteneur non résolu,
  et un port **non publié** de l'autre environnement injoignable — avec son **témoin positif** sur
  un port non publié de son propre réseau, sans lequel une sonde muette donnerait la même
  observation ;
- **rapporté visiblement** : les 7 ports publiés qui restent joignables, nommés un par un ;
- **exigé aussi** : que le secret de la recette **n'ouvre pas** la base de dev. La barrière qui rend
  le résiduel acceptable doit être un contrôle, pas une affirmation.

C'est le parti de `DEC-482` pour Trivy : bloquer sur ce qui est exigible, rapporter le reste. Le
taire aurait produit un « 7 séparations prouvées » laissant croire davantage que ce qui est vrai.

### 5.3 Témoins — 12, tous concluants

| Maillon | Défaut injecté ou action réelle | Résultat |
|---|---|---|
| Substitution du `Caddyfile` | `caddy adapt` **sans** les variables, puis **avec** | hôtes différents dans les deux cas |
| Nom d'environnement | `ENVIRONNEMENT=recete` | **échec à la lecture du `Makefile`**, et liste des noms valides **dérivée du disque** |
| Calque de configuration | variable absente du modèle | **code 1, aucun fichier créé** |
| Calque, second sens | variable déclarée **deux fois** | code 1 |
| Calque, troisième sens | ligne malformée | code 1 |
| Idempotence du générateur | seconde exécution sur un fichier existant | **empreinte inchangée** |
| Cohérence `.env` | 2 variables ajoutées au modèle | `env-check` les **nomme** toutes les deux |
| Substitution silencieuse d'image | `make up-recette` **sans authentification** | `unauthorized`, **0 conteneur, 0 construction de repli** |
| `DEC-477`, ordre inversé | volume MinIO supprimé, démarrage **sans** créer le bucket | **échec**, `minio indisponible, motif=RuntimeError` |
| Détecteur de serveur Vite | même sonde sur **dev** | **1 occurrence** — le détecteur n'est pas muet |
| Isolement réseau | port **non publié** de son **propre** réseau | **JOIGNABLE** — la sonde n'est pas muette |
| Persistance de la recette | arrêt puis redémarrage | **5 empreintes relevées, 5 comparées** |

### 5.4 Non-régression sur `dev` — la ligne de base relevée AVANT toute écriture

Onze contrôles, tous à **code 0** avant modification, tous à **code 0** après :

```text
icloud-verify 0 · env-check 0 · check 0 · audit 0 · docs-check 0 · images-check 0
stack-check 0 · api-check 0 · web-check 0 · alembic-check 0 · test-integration 0
```

**166 tests inchangés** — 139 pytest, 27 Vitest. `images-check` voit désormais **2 surcouches,
chacune nommant sa cible** : `developpement` et `execution`. La recommandation 1 de `T7` est
satisfaite, et le contrôle qui l'attendait a tiré.

### 5.5 Sur la recette

| Contrôle | Résultat |
|---|---|
| `make up-recette` | **8 services sains**, 7 publications déclarées / 7 réelles, **au premier démarrage sur des volumes inexistants** |
| `make recette-check` | **code 0** — 57 contrôles de séparation, `env-check` 79/79 |
| `api-check` · `alembic-check` recette | code 0 — 3 endpoints, 1 tête de migration |
| `persistence-test` recette | code 0 — **5 relevées, 5 comparées** |
| Architecture | hôte `arm64`, `uname -m` dans les conteneurs de l'image **publiée** : **`aarch64` 3 sur 3** |
| Cible `execution` | **0** `/@vite/client`, `/assets/` présent. Sur dev : **1** occurrence, `/assets/` absent |
| Artefact en marche | les 3 conteneurs tournent sur l'**empreinte demandée** |
| Identité du build | `version='0.0.0-dev' revision='3d4080a'` **transmise = gravée**, les deux côtés dérivés |

---

## 6. Défauts détectés pendant `T8`

**Sept défauts. Les sept étaient dans mon propre travail** — contrôles, scripts ou méthode de mesure.
Aucun dans le comportement de la plateforme elle-même. **Le septième a été trouvé APRÈS la fusion**, à la
première exécution réelle de `make images-pin`, et il est corrigé par une pull request dédiée.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T8-1` | **Mon premier contrôle de la session concluait sur `${PIPESTATUS[0]}`**, qui n'existe pas en zsh. `make check` a affiché `code=` — vide. **Je n'avais pas lu le code de sortie de mon premier contrôle.** | **SEPTIÈME occurrence de la famille du code de sortie** sur ce projet, après `T0-1`, `T2-4`, `T3-6`, `T4-3`, `T5-5` et `T7-12`. Et la première commise dans un rapport de prise en charge, donc avant d'avoir écrit une ligne | Forme `sortie=$(cmd 2>&1) && code=0 \|\| code=$?` employée systématiquement ensuite, et les onze codes de la ligne de base relevés avec elle. Le remède structurel reste le même qu'en `T7` : les contrôles livrés sont en Python, où `returncode` ne peut pas être celui d'un autre maillon |
| `T8-2` | **J'ai mis `CADDY_SITE_APP` et `CADDY_SITE_API` dans le calque de recette sans les déclarer au modèle.** Avec la substitution `sed` de `T2`, la recette aurait servi les hôtes du **développement**, en silence | **Livrable incomplet, attrapé par un garde-fou que je venais d'écrire.** `composer-env.py` refuse un calque nommant une variable absente du modèle, précisément parce qu'un `sed` sur un motif absent sort en 0 sans rien changer | Les deux variables ajoutées à `.env.example`, qui passe en **v1.2**, 79 variables. `make env-check` a ensuite **nommé les deux manquantes** du `.env` local — témoin gratuit de la parade `ECART-022` |
| `T8-3` | **Ma sonde de la base employait `psql -U onboarding_app` sans `-d`.** Mesuré : code 2, « database "onboarding_app" does not exist ». Le contrôle de la deuxième séparation aurait échoué pour une raison **étrangère** à ce qu'il mesure | **Contrôle qui échoue pour une raison hors sujet**, classe `T6-4` et `T7-4` : un tel contrôle finit désactivé. Trouvé en relisant, pas en exécutant | `-d` ajouté, et le contrôle **renforcé** : il vérifie en plus que la base de l'autre environnement est **absente** de l'instance. Deux noms différents ne prouvaient pas la séparation des données |
| `T8-4` | **`make up` n'est pas auto-réparateur depuis un état laissé par un démarrage contourné.** Après un `docker compose up` brut sans création du bucket, le conteneur `api` reste `unhealthy` ; `make up` crée bien le bucket, puis `up --wait` évalue le verdict **périmé** et abandonne au lieu d'attendre l'intervalle de sonde suivant. **Un second `make up` répare** | **Diagnostiqué et reproductible, non corrigé — et c'est un choix.** L'état ne survient qu'en **contournant** `make up` ; le chemin propre fonctionne, prouvé deux fois sur des volumes inexistants. La cinquième proposition de la règle du lot demande de mesurer ce qu'un correctif casse : un redémarrage automatique du conteneur masquerait de vraies pannes, et je ne l'ai pas mesuré | Consigné ici, et **recommandé à `T9`** comme procédure de diagnostic documentée. Non silencieux : l'échec est bruyant et nomme le service |
| `T8-5` | **Mon contrôle des totaux du registre additionnait les lignes des DEUX tableaux de synthèse et comparait au total d'UN SEUL** : 170 au lieu de 85, 120 au lieu de 60 | **La sixième proposition de la règle du lot, rejouée** : un contrôle qui compare deux nombres doit prouver qu'ils mesurent **la même grandeur**. C'est `T7-6` sous une autre forme | Découpage par tableau, et **chaque synthèse vérifiée contre elle-même**. Un seul tableau juste ne suffirait pas : le contrôle exige d'en trouver au moins deux, sans quoi un détecteur muet conclurait « aucune incohérence » |
| `T8-6` | **Ma sonde d'audit des registres ne comptait que les lignes de tableau** : elle rendait 24 risques là où il y en a 33, les fiches `ROAD-RSK-025` à `034` étant des sections `##`. J'ai failli déclarer un défaut du registre | **Faux positif de mon propre outil de mesure**, et la docstring de `verifier-documentation.py` — écrite en `T6` — **nomme exactement ce piège**. Je l'ai rejoué sans l'avoir relu | Vérifié avant de conclure, et le registre est intact : **34 mentions, aucun trou**. Le contrôle livré, lui, gère les deux formes depuis `T6`. Leçon : un piège documenté n'est pas un piège désarmé, et il faut relire les contrôles existants avant d'en écrire un nouveau |

| `T8-7` | **`make images-pin` a été livrée sans avoir jamais tourné en conditions nominales**, l'authentification au registre n'existant pas encore quand je l'ai écrite. Première exécution réelle, **après la fusion de `T8`** : échec. Cause mesurée : `gh run view --log` prefixe chaque ligne de « tâche, **étape**, horodatage », et mon filtre portait sur le nom de l'étape. Sur l'exécution 30465685379, **TOUTES** les étapes du journal portent le libellé littéral `UNKNOWN STEP` — GitHub n'avait pas associé les noms d'étape aux lignes ; sur l'exécution précédente, le nom apparaît **20 fois**. Le journal contenait pourtant les trois empreintes, le compte et l'identité | **Deux défauts en un.** D'abord un contrôle **jamais exercé** : c'est exactement la classe `T6-1`/`T6-2` de la passation §7.16, « ce qui n'a jamais tourné ailleurs n'est pas éprouvé » — et ici, ce qui n'a jamais tourné **du tout**. Ensuite un contrôle qui **échoue pour une raison étrangère à ce qu'il mesure**, classe `T6-4` et `T7-4` : le libellé d'étape est une commodité d'affichage, pas une donnée | Le filtre par étape est **supprimé** : les trois motifs sont reconnus par leur **contenu**, et ils ne peuvent venir que de l'étape visée. Discrimination vérifiée contre le bruit réel du journal — les lignes buildx `api:sha-1060ad6@sha256:…` et l'écho du code source `${relevees}` ne correspondent pas. Le filet reste le même : mon compte confronté à celui du **producteur**. **Et l'échec dit désormais pourquoi** — il nomme le nombre de lignes lues, les empreintes reconnues et les libellés d'étape vus, ce qui est la leçon `T7-13`. **Cinq témoins sur la fonction réelle**, chacun produisant un message de cause distinct. Éprouvé de bout en bout : la recette tourne désormais sur les empreintes de `1060ad6`, et `/health/version` rapporte `revision: 1060ad6, environnement: recette` |

### 6.1 Ce que ces sept défauts enseignent

**Les sept étaient dans mon travail, aucun dans le comportement de la plateforme.** C'est la
proportion la plus élevée du lot, devant les dix sur treize de `T7`.

**`T8-7` est le plus instructif des sept, et c'est celui que j'ai failli ne jamais trouver.** J'ai
livré une cible que je n'avais **jamais exécutée** — l'authentification au registre n'existait pas
encore au moment de l'écriture, et je ne suis pas revenu l'éprouver après. Elle a passé `lint`,
`format-check`, `typecheck` et l'intégration continue, parce qu'aucun de ces contrôles ne lance une
commande qui parle à GitHub. La passation §7.16 dit exactement cela : « ce qui n'a jamais tourné
ailleurs n'est pas éprouvé ». Il faut l'élargir d'un cran — **ce qui n'a jamais tourné du tout ne
l'est pas non plus, et une chaîne verte ne dit rien d'une cible qu'elle n'appelle pas.**

**Trois défauts ont été attrapés par des garde-fous plutôt que par des échecs**, et c'est le point
le plus utile de cette sous-étape. `T8-2` a été attrapé par un contrôle écrit **le jour même**, qui
a payé son écriture immédiatement. `T8-3` et `T8-6` ont été attrapés en **relisant**, pas en
exécutant.

**`T8-1` mérite d'être nommé sans l'atténuer.** J'ai commis le piège du code de sortie dans le
tout premier contrôle de la session, après avoir écrit dans mon rapport de prise en charge que
cette famille comptait six occurrences. C'est `T7-3` rejoué à l'identique : **un piège documenté
n'est pas un piège désarmé.** Et `T8-6` le rejoue une seconde fois dans la même sous-étape, sur un
piège dont la parade était écrite dans un fichier du dépôt.

> **Ce que `T8` ajoute à la règle du lot, et ce n'est pas une septième proposition :**
> quand un contrôle échoue sur un livrable que tu crois conforme, **le diagnostic peut révéler que
> le critère n'exigeait pas ce que ton contrôle exige.** Ne l'affaiblis pas et ne le supprime pas :
> fais-lui affirmer ce qui est exigible, **rapporter visiblement** ce qui ne l'est pas, et **exiger
> la barrière** qui rend le résiduel acceptable. C'est ce que `DEC-482` avait fait pour Trivy, et
> c'est ce que la sixième séparation a demandé ici.

---

## 7. Recommandations pour la suite

1. **`T9` doit documenter la procédure de diagnostic de `T8-4`** : un `make up` qui échoue sur
   `dependency failed to start` après un démarrage interrompu se répare par un second `make up`. Et
   documenter les deux environnements, leurs ports et `make images-pin`.
2. **`ROAD-RSK-034` est à réévaluer avant le LOT 13**, où la production temporaire portera des
   données réelles et coexistera avec le développement et la recette sur la même machine.
3. **Ne pas ajouter de contrôle de recette à l'intégration continue** sans traiter la résolution
   des sous-domaines `.localhost`, que Linux ne fait pas — `ci.yml` pose deux lignes dans
   `/etc/hosts` pour le développement, il en faudrait deux de plus.
4. **Le gisement `uv`/`uvx` de 55,1 Mio dans `api` et `worker`** reste ouvert depuis `T7`, non
   traité, de poids seulement.
5. **`make images-pin` vieillit avec `develop`.** L'empreinte épinglée dans la surcouche est celle
   du commit `3d4080a` ; toute fusion ultérieure en publie une nouvelle. Le pointeur durable est un
   commit délibéré, et c'est voulu.

---

## 8. État à la sortie de `T8`

| | |
|---|---|
| Sous-étape | **`T8` terminée**, plus un correctif post-fusion `T8-7`. Story `MVP-L01-US002` prête pour validation, issue `#3` **à refermer à la main** après fusion (§7.19) |
| Décisions | `DEC-483` à `DEC-488`. Prochaine libre : **`DEC-489`** |
| Écarts | **`ECART-023` ouvert et clos.** Prochain libre : **`ECART-024`** |
| Risques | **`ROAD-RSK-034` ouvert**, résiduel accepté. Prochain libre : **`ROAD-RSK-035`** |
| Questions | **`QO-085` CLOSE** — 836,6 Mio pour deux stacks, 10,5 % du budget. 33 ouvertes sur 38. Prochaine libre : `QO-115` |
| Dépendances | **Aucune ajoutée.** Prochaine libre : `DEP-018` |
| Tests | **166** — inchangé. `T8` n'ajoute pas de test unitaire : ses preuves sont des contrôles d'environnement |
| Cibles `Makefile` | **50** — dérivé deux fois : 50 lignes `##`, 50 noms `.PHONY` |
| Contrôles de séparation | **57**, 0 échec · **12 témoins** |
| Réserve `arm64` | **LEVÉE.** Les deux architectures sont natives sur le **même artefact publié** |

### Les 7 critères de la porte `G1`

| | Critère | État |
|:--:|---|---|
| ☑ | Tous les services démarrent sur le Mac M5 | `T2`, machine propre depuis `T6`, **et en recette depuis `T8`** |
| ☑ | Les images multiarchitectures sont construites | `T7` — et **`arm64` est natif sur l'image publiée depuis `T8`** |
| ☑ | Aucun secret réel n'est présent | vérifié automatiquement depuis `T6`. **`T8` n'a créé aucun secret de dépôt** |
| ☑ | Une migration Alembic vide ou initiale s'exécute | `T3`, **et sur la base de recette depuis `T8`** |
| ☑ | Les logs possèdent un identifiant de corrélation | `T4` |
| ☑ | La CI bloque une erreur de lint, de test et de secret | `T6`, prouvé trois fois |
| ☐ | Jonathan valide le socle | `T11` |

### Ce qui attend `T9`

Documentation d'exploitation locale, story `MVP-L01-US008`, issue `#9`. Son critère — « les
procédures fonctionnent **depuis une machine propre** » — porte désormais sur **deux**
environnements, leurs quatorze publications de ports, leurs douze volumes, et la procédure de
diagnostic de `T8-4`.
