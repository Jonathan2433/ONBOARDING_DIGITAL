# Passation — agent chef de projet technique

**Projet :** eXalt Onboarding Digital
**Rédigé le :** 27 juillet 2026, à la clôture du LOT 0
**Destinataire :** l'agent qui prend le relais
**Interlocuteur unique :** Jonathan — technique et exploitation. Léa décide du produit.

Ce document dit **où en est le projet**, **ce qui a été fait**, **comment il faut travailler**, et
**les pièges de cet environnement** qui m'ont coûté du temps. Lis-le en entier avant d'agir.

---

# 1. En un coup d'œil

| | |
|---|---|
| Lot terminé | **LOT 0 — Référentiel projet et préparation**, verrouillé le 27/07/2026 (`DEC-438`) |
| Porte franchie | **`G0`** |
| Lot suivant | **LOT 1 — Monorepo, qualité et environnement local**, porte `G1` |
| État du LOT 1 | **NON OUVERT.** Plan prêt : [`docs/operations/fiche-lot-1.md`](docs/operations/fiche-lot-1.md) |
| Code applicatif | **Aucun.** Le LOT 0 est exclusivement documentaire |
| Commits | 11, **tous poussés** sur `origin/main` le 27/07/2026 à 14:21:37 (`ECART-016`) |
| Dépôt distant | `Jonathan2433/ONBOARDING_DIGITAL`, privé, compte personnel de Jonathan |
| Conséquence | Un commit poussé **ne peut plus** être annulé par `git reset --hard` : le push forcé est interdit (conventions §6) |

**Première chose à vérifier :** le LOT 1 a-t-il été **explicitement ouvert** par Jonathan ? Si
non, tu ne touches à rien du LOT 1. Tu peux répondre à des questions, affiner le plan, corriger
un défaut du LOT 0. Rien d'autre.

---

# 2. Les règles qui ne se négocient pas

Elles viennent des documents validés, pas de moi.

1. **Un lot à la fois.** Seul le lot explicitement ouvert par Jonathan peut être réalisé
   (`ROAD-003`, `ARB-BACK-003`, `BACKLOG-006`). Ne commence jamais le lot suivant sans
   validation explicite de la porte précédente.
2. **Aucun secret dans Git.** Ni dans un fichier, ni dans un message de commit, ni dans un titre
   de branche, ni dans une description de pull request.
3. **Aucune donnée réelle de collaborateur versionnée.** Aucun CSV réel, aucune photo.
4. **Aucune ligne de code du prototype réutilisée.** `docs/prototype/V1.html` est une référence
   d'intention, pas une base de code.
5. **L'API est l'autorité finale** sur les permissions. Jamais le frontend seul.
6. **Aucun contournement de l'authentification**, à aucun moment, même en développement.
7. **Aucune exigence `Must` ni story `P0`** supprimée, fusionnée ou dégradée sans décision
   explicite et tracée.
8. **Toute proposition nouvelle est une recommandation** jusqu'à validation de Jonathan. Jamais
   une décision acquise.
9. **Ne repose jamais une question déjà tranchée** dans les documents. Lis avant de demander.
10. **Ne déclare jamais un lot terminé sans preuve.** Contrôles exécutés, sorties réelles
    montrées, critères de sortie vérifiés un par un.

La liste complète des interdictions est dans [`README.md`](README.md) §4 et
[`CONTRIBUTING.md`](CONTRIBUTING.md) §7.

---

# 3. Où est la vérité

| Question | Document |
|---|---|
| Que doit faire le produit ? | `docs/product/CAHIER_DES_CHARGES_EXALT_BORDEAUX.md` — **prévaut sur tout** |
| Qui a le droit de faire quoi ? | `docs/product/MATRICE_ROLES_PERMISSIONS_EXALT.md` |
| Comment sont structurées les données ? | `docs/architecture/MODELE_DONNEES_EXALT.md` |
| Dans quel ordre construit-on ? | `docs/product/ROADMAP_MVP_V1_V2_EXALT.md` |
| Quelle est l'unité de travail ? | `docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md` |
| Qu'a-t-on décidé depuis ? | `docs/decisions/registre-decisions.md` — **106 décisions** |
| Comment travaille-t-on ? | `CONTRIBUTING.md` et `docs/operations/conventions-git-et-versions.md` |

Ces cinq documents de cadrage sont **immuables**. Leur intégrité est prouvée par empreinte
SHA-256 dans `docs/operations/integrite-et-conformite-documents.md`. **Ne les modifie pas.** Toute
évolution suit la procédure du cahier §35 : décision enregistrée, changement de version,
analyse d'impact, mise à jour du cahier, contrôle de conformité des annexes rejoué.

Le cahier intègre les quatre autres en annexes A à D. J'ai vérifié : **aucune divergence de
contenu**. La règle de préséance ne masque donc rien.

Règle de préséance : le cahier prévaut ; une décision plus récente prévaut sur une plus
ancienne ; les annexes précisent le détail ; **aucune hypothèse ne remplace une décision
explicite de Jonathan**.

---

# 4. Ce qui a été livré au LOT 0

Sept stories, huit sous-étapes, un commit par sous-étape.

| Sous-étape | Story | Livrable |
|---|---|---|
| S1 | `US001` | Dépôt initialisé, `.gitignore` de 129 lignes, arborescence `docs/` à 5 sous-dossiers, prototype sorti du suivi Git |
| S2 | `US002` | Les 5 documents versionnés sans altération, preuve d'intégrité SHA-256, conformité des annexes A–D |
| S3 | `US003` | `CONTRIBUTING.md`, conventions Git et versions, traçabilité GitHub, 4 gabarits `.github/` |
| S4 | `US006` | 5 registres : décisions, écarts, risques, questions, dépendances. Plus les responsabilités projet |
| S5 | `US007` | `.env.example` v0.1 à 74 variables, politique de configuration et de secrets |
| S6 | `US004` | Schéma CSV `1.0-initiale` : 19 champs, 68 codes d'erreur, listes contrôlées, jeu fictif de 17 lignes, critères de qualité |
| S7 | `US005` | Inventaire du prototype : 29 contenus, les 2 parcours d'onboarding relevés (44 tâches), exclusions |
| S8 | — | Contrôles de sortie prouvés, checklist `G1`, verrouillage du lot |

**Volumétrie :** 44 fichiers versionnés, 39 documents Markdown, ~18 000 lignes.

## 4.1 Les séquences d'identifiants — à respecter absolument

Un identifiant n'est **jamais** réutilisé, **jamais** renuméroté, et un trou n'est **jamais**
comblé.

| Séquence | Étendue | Prochain libre |
|---|---|---|
| `DEC-nnn` décisions de projet | `001`–`417` **réservés**, `418`–`448` en usage | **`DEC-449`** |
| `RIGHTS-nnn` | `001`–`025` | `RIGHTS-026` |
| `DATA-nnn` | `001`–`018` | `DATA-019` |
| `ROAD-nnn` | `001`–`012` | `ROAD-013` |
| `BACKLOG-nnn` | `001`–`010` | `BACKLOG-011` |
| `ARB-DROIT / ARB-DATA / ARB-ROAD / ARB-BACK` | `-001`–`-005` chacun | `-006` |
| `ECART-nnn` écarts | `001`–`016` | **`ECART-017`** |
| `QO-nnn` questions | `072`–`105` avec **5 trous**, puis `106`–`110` | **`QO-111`** |
| `ROAD-RSK-nnn` risques | `001`–`028` | **`ROAD-RSK-029`** |
| `DEP-nnn` dépendances | `001`–`017` | **`DEP-018`** |
| `CONT-nnn` contenus | `001`–`029` | **`CONT-030`** |

Trous conservés, jamais comblés : `QO-075`, `QO-079`, `QO-080`, `QO-082`, `QO-090`
(`ECART-011`). Plage `DEC-001`–`DEC-417` réservée pour un import ultérieur des comptes rendus
d'ateliers (`DEC-422`).

L'index à jour est toujours dans [`docs/README.md`](docs/README.md) §4. **Consulte-le avant de
créer un identifiant.**

## 4.2 Les 21 décisions à connaître

Toutes dans `docs/decisions/registre-decisions.md`. Celles qui contraignent le travail
quotidien :

| ID | Décision |
|---|---|
| `DEC-418` | Le dépôt réside dans iCloud Drive. Risque accepté, atténuations à définir au LOT 1 |
| `DEC-420` | `V1.html` conservé dans `docs/prototype/`, **exclu du suivi Git** |
| `DEC-422` | Les 85 décisions consolidées font foi ; nouvelles décisions à partir de `DEC-418` |
| `DEC-423` | Le cahier des charges v1.0 est validé **sans modification du fichier** |
| `DEC-427` | Le circuit branche + pull request s'applique **dès le premier commit de code du LOT 1**. Le LOT 0 était en commits directs sur `main` |
| `DEC-428` | Versions jalonnées sur les portes : `v0.1.0` à `G1` … `v1.0.0` à `G14`. `G0` : aucun tag |
| `DEC-429` | `main` protégée : PR obligatoire, **zéro approbation requise** — GitHub interdit l'auto-approbation et Jonathan est seul relecteur (`QO-094`) |
| `DEC-432` | CSV : séparateur `;`, UTF-8, virgule tolérée, BOM non propagé |
| `DEC-433` | `autorisation_photo` à trois valeurs, défaut `inconnu`, aucune photo sans autorisation active |
| `DEC-434` | Le schéma CSV définit des **champs logiques** `F01`–`F19` ; les en-têtes réelles sont associées par un profil de correspondance versionné |
| `DEC-435` | Anomalies multi-lignes : doublon d'identifiant → première occurrence retenue ; conflit d'attribution métier → **toutes** les lignes rejetées |
| `DEC-437` | `US005` validée au statut `à relire`, relecture portée au LOT 6 |
| `DEC-438` | Porte `G0` validée, LOT 0 verrouillé |

---

# 5. Comment j'ai travaillé — la méthode à reprendre

C'est la partie la plus importante de cette passation. Le contenu s'apprend en lisant les
documents ; la méthode, non.

## 5.1 La boucle de travail

```text
1. Annoncer          ce qui va être modifié, pourquoi, les risques, le point de retour
2. Exécuter          une seule sous-étape, jamais deux
3. Contrôler         en lecture seule, après modification
4. Rapporter         au format de suivi imposé, avec les sorties réelles
5. Attendre          la validation explicite de Jonathan
6. Commiter          un commit par sous-étape, message détaillé
```

**Ne jamais enchaîner deux sous-étapes sans validation.** Jonathan valide par un message court
(« je valide S3, passe à S4 »). Attends-le.

## 5.2 Le format de suivi imposé

Chaque rapport de sous-étape comporte ces sections, dans cet ordre :

```text
État du lot
Sous-étape en cours
Travail réalisé
Contrôles exécutés
Résultats
Décisions ajoutées ou modifiées
Risques et écarts
Questions ouvertes
Validation demandée à Jonathan
```

Termine toujours par la commande de publication et **la commande de retour arrière** de la
sous-étape seule (`git reset --hard <commit précédent>`).

## 5.3 Les questions à Jonathan

Il a demandé explicitement d'utiliser **l'outil de question** plutôt que du texte libre :
questions courtes, 2 à 4 options, la recommandée en premier avec la mention
« (Recommandé) », et une description qui explique la **conséquence** de chaque option, pas
seulement son intitulé.

Ne l'interroge que si la réponse change réellement le travail. S'il te dit qu'un point doit
**rester en suspens** — comme il l'a fait pour la nomenclature des en-têtes du CSV —, ne force
pas un choix : **adapte la conception** pour que le point reste ouvert sans bloquer. C'est ce
qui a produit `DEC-434`, et c'était la bonne réponse technique de toute façon.

## 5.4 La discipline de contrôle — la leçon la plus coûteuse

**Un contrôle qui ne peut pas échouer ne prouve rien.**

Sept défauts ont été détectés pendant le LOT 0, tous par des contrôles, tous corrigés avant la
fin de leur sous-étape. Ils sont listés dans
[`controles-sortie-lot-0.md`](docs/operations/controles-sortie-lot-0.md) §7. **Trois d'entre eux
étaient des contrôles faux, pas des livrables faux** :

- `git check-ignore -v` sort avec le code 0 même sur une règle de **négation** : mon contrôle
  criait au loup sur des fichiers correctement réinclus ;
- une extraction `awk` avec `R.f.rentiel` ne matchait rien, `é` occupant **deux octets** en
  UTF-8 alors que `.` en consomme un ;
- le scan de secrets sur l'historique était **totalement inopérant** et affichait « OK » sans
  rien vérifier. Voir §6.1.

Depuis, la règle est : **tout contrôle de sécurité s'accompagne d'un témoin positif** — un motif
dont tu sais qu'il existe — **et d'un témoin négatif**. Si le témoin positif ne remonte rien,
c'est ton contrôle qui est cassé, pas le dépôt qui est propre.

## 5.5 Vérifier le texte, pas seulement les identifiants

En S4, mes contrôles comptaient les identifiants : 99/99, tout au vert. En étendant la
vérification au **texte**, j'ai découvert que **16 libellés sur 89** différaient de la source par
un caractère : apostrophe droite `'` au lieu de l'apostrophe typographique `’`. Or le registre
affirmait « repris sans altération ».

Les documents sources emploient systématiquement `’` (U+2019). Si tu recopies une décision,
**vérifie-la avec `grep -F`** contre la source.

## 5.6 Générer plutôt que transcrire

Pour les gros volumes — 44 tâches d'onboarding, 68 codes d'erreur — j'ai **généré le Markdown
par script** depuis les données extraites, au lieu de le transcrire à la main. Zéro erreur de
recopie, et le résultat est reproductible.

## 5.7 Ne jamais inventer ce qui n'est pas décidé

Trois exemples de ce lot :

- le **catalogue des métiers** n'est énuméré dans aucun document : je ne l'ai pas inventé, j'ai
  écrit « à établir avec l'ESM » ;
- `IMPORT_SOURCE_RETENTION_DAYS` reste en `CHANGE_ME` parce que sa valeur relève de `QO-100`,
  bloquante ;
- les intitulés de `BDS`/`BDE`/`BDG` étaient absents du corpus : je les ai relevés dans le
  prototype et marqués `à relire`, pas `validé`.

Une hypothèse déguisée en décision est pire qu'une case vide.

---

# 6. Pièges de cet environnement

Chacun m'a coûté du temps. Ils sont propres à cette machine et à ce dépôt.

## 6.1 `zsh` ne découpe pas les variables en mots

**Le piège le plus dangereux du lot.** En `zsh`, `$VAR` n'est pas soumis au découpage en mots.

```bash
COMMITS=$(git rev-list --all)
git grep -i 'motif' $COMMITS      # ← UN seul argument contenant 7 hachages : ne marche pas
```

Combiné à `2>/dev/null`, l'erreur était invisible et le contrôle affichait « OK » sans rien
vérifier. Sur le contrôle « aucun secret dans l'historique ».

```bash
for c in $(git rev-list --all); do git grep -i 'motif' "$c"; done   # ← correct
```

Même piège avec `set -- $var` dans une boucle. **Utilise une boucle explicite, un tableau, ou
`${=VAR}`.**

## 6.2 Le code de sortie d'un pipeline est celui du dernier maillon

```bash
if git grep 'motif' ... | head -5; then echo ALERTE; fi   # ← head sort toujours 0 : toujours vrai
```

Capture dans une variable et teste si elle est non vide.

## 6.3 Le système de fichiers est insensible à la casse

`DOCS` et `docs` désignent le **même** dossier. `mkdir docs` alors que `DOCS` existe réutilise
silencieusement l'existant. Tout renommage ne différant que par la casse exige une manœuvre en
deux temps :

```bash
mv DOCS __tmp__ && mv __tmp__ docs
```

## 6.4 Outils macOS différents de GNU

| N'existe pas | Utiliser |
|---|---|
| `cat -A` | `cat -vet` |
| `grep -P` | `grep -E` ou Python |

`grep` est ici **`ugrep`**, qui échoue avec « exceeds complexity limits » sur des motifs comme
`.{0,60}(a|b|c).{0,60}` appliqués à un gros fichier. **Passe par Python** pour les extractions
non triviales.

## 6.5 Ne jamais `grep` le prototype en entier

`V1.html` fait 2,83 Mo dont **2,64 Mo de Base64**. Ces chaînes produisent des correspondances
fortuites : j'ai d'abord annoncé « 96 occurrences de Hub », alors qu'il y en a **zéro** dans le
texte réel.

```bash
sed -E 's/data:image\/[a-z]+;base64,[A-Za-z0-9+\/=]+/<B64>/g' docs/prototype/V1.html > /tmp/propre.html
```

Le fichier tombe à 194 566 caractères analysables. **Travaille toujours sur la version
dépouillée**, hors du dépôt.

## 6.6 Attention au BOM

Un BOM `EF BB BF` s'est glissé en tête de `.env.example`. Dans un fichier `.env`, cela peut
corrompre la première entrée selon l'outil qui le lit.

```bash
head -c 3 fichier | od -An -tx1 | tr -d ' \n' | grep -q '^efbbbf' && echo "BOM present"
```

## 6.7 Le dépôt est dans iCloud Drive

Chemin : `~/Library/Mobile Documents/com~apple~CloudDocs/CODE/ONBOARDING_DIGITAL`.

Décision de Jonathan (`DEC-418`), risque accepté (`ROAD-RSK-026`). **`.gitignore` empêche Git de
suivre `node_modules/`, `data/`, `volumes/`, `backups/` — mais n'empêche pas iCloud de les
synchroniser.** C'est `QO-109`, à trancher **au LOT 1 avant de créer le premier volume Docker**.

## 6.8 Outillage GitHub absent

`gh` n'est **pas installé** et aucun connecteur GitHub n'est disponible dans la session. Je n'ai
donc pas pu créer les étiquettes, les milestones, ni la protection de branche. Les commandes
prêtes à l'emploi sont dans
[`traceabilite-github.md`](docs/operations/traceabilite-github.md) §5. C'est `ECART-010`,
`QO-107` et `QO-108` — **prérequis du LOT 1**.

Le caractère privé du dépôt n'est pas vérifiable techniquement : un accès anonyme retourne
HTTP 404, ce qui est le comportement d'un dépôt privé **comme** d'un dépôt inexistant. C'est la
confirmation de Jonathan qui fait preuve.

## 6.9 Contexte machine

Apple M5, **16 Gio de RAM**, 564 Gio libres, FileVault actif, Docker 29.5.3, Compose v5.1.4,
identité Git `jonathan <jonathan.dupau24@gmail.com>` (`DEC-424`).

Les 16 Gio sont une contrainte réelle : trois environnements × 8 services ≈ 24 conteneurs.
C'est `ROAD-RSK-027`, à arbitrer au LOT 1.

---

# 7. Ce qui reste ouvert

## 7.1 Prérequis avant d'ouvrir le LOT 1

| # | Prérequis | Références |
|---:|---|---|
| 1 | Traçabilité GitHub et protection de `main` | `ECART-010`, `QO-107`, `QO-108` |
| 2 | Atténuations iCloud, **avant** création des volumes | `QO-109`, `ROAD-RSK-026` |
| 3 | Exécution non simultanée des trois environnements | `ROAD-RSK-027`, `QO-085` |

## 7.2 Écarts ouverts

| ID | Objet | Échéance |
|---|---|---|
| `ECART-005` | Schéma CSV initial livré ; le définitif relève de `QO-096` | LOT 9 |
| `ECART-006` | `.env.example` en v0.1, à compléter | **LOT 1** |
| `ECART-010` | Traçabilité GitHub non mise en place | **LOT 1** |
| `ECART-012` | `intercontrat` imposé à une direction générale : cohérent techniquement, trompeur à l'écran | LOT 2, avant LOT 5 |
| `ECART-013` | Les 5 tâches communes du prototype ont des identifiants différents. **Reprendre cette numérotation ferait échouer `MVP-L07-US007`** | **LOT 7** |
| `ECART-014` | Le prototype dit « Représentant de cercle », les documents disent « Booster » | LOT 6 |
| `ECART-015` | Le prototype ne fournit **ni** descriptions de cercles **ni** liens internes | LOT 6 |

`ECART-009` et `ECART-011` sont **acceptés** : connus, documentés, non corrigés.

## 7.3 Ce que le prototype ne contient pas

Contrairement à ce qu'annonce le cahier §2.2, j'ai vérifié qu'il n'y a **aucune** description de
cercle, **aucun** lien interne — le mot « Hub » n'apparaît pas une seule fois — et **aucune**
vidéo, les onze emplacements étant vides. Le LOT 6 devra les **produire**, pas les reprendre.

En revanche il fournit bien les **descriptions des 3 bureaux** et surtout les **deux parcours
d'onboarding complets**, 44 tâches : c'est son apport le plus substantiel, et il alimente
directement le LOT 7.

## 7.4 Contenus en attente de relecture

Les 29 éléments `CONT-001` à `CONT-029` sont au statut **`à relire`**. Propriétaires : Léa pour
le produit, Tess pour l'éditorial, Diane pour les parcours. **Aucun n'est publiable en l'état.**

---

# 8. Cartographie du dépôt

```text
.
├── CLAUDE.md                    ← ce document
├── README.md                    ← état d'avancement, règles, structure
├── CONTRIBUTING.md              ← circuit de contribution, Ready et Done
├── .env.example                 ← 74 variables, aucun secret
├── .gitignore                   ← barrière : secrets, CSV, médias, volumes
├── .github/                     ← gabarits PR et issues
└── docs/
    ├── README.md                ← INDEX : documents, séquences d'ID, portes, avancement
    ├── product/                 ← cahier, matrice, roadmap, backlog  [IMMUABLES]
    │   └── contenus/            ← inventaire prototype, parcours relevés, exclusions
    ├── architecture/            ← modèle de données  [IMMUABLE]
    │   └── donnees/             ← schéma CSV, codes d'erreur, listes, exemple fictif
    ├── decisions/               ← registre des décisions, registre des écarts
    ├── operations/              ← conventions, registres, secrets, contrôles, fiche lot 1
    └── prototype/               ← V1.html, NON VERSIONNÉ
```

**Point d'entrée recommandé :** `docs/README.md`. Il porte l'index, les séquences
d'identifiants avec le prochain libre, l'état des 15 portes et l'avancement.

---

# 9. Démarrage type d'une session

1. Lire ce document.
2. Lire [`docs/README.md`](docs/README.md) : quel lot, quelle porte, quel prochain identifiant.
3. `git log --oneline` et `git status` : où en est le dépôt, l'arbre est-il propre.
4. Vérifier si le lot suivant a été **explicitement ouvert**. Sinon, ne rien entamer.
5. Si un lot est ouvert : lire sa fiche de lot, exécuter **une** sous-étape, contrôler,
   rapporter, attendre la validation.

Contrôle d'hygiène utile à tout moment :

```bash
git ls-files | grep -Ei '\.(csv|env|pem|key|mp4|html)$'   # doit ne montrer que le CSV fictif et .env.example
git ls-files | grep -c 'V1.html'                          # doit valoir 0
git status --short                                        # doit être vide
```

---

# 10. Une dernière chose

Jonathan valide vite et lit sérieusement. Ce qui a bien fonctionné avec lui :

- des rapports **denses mais courts**, avec les chiffres réels et non des approximations ;
- **signaler mes propres erreurs** dès que les contrôles les révèlent, sans les enjoliver — les
  sept défauts du LOT 0 sont tous documentés, y compris celui qui rendait un contrôle de
  sécurité inopérant ;
- distinguer nettement **ce qui est prouvé** de **ce qui est recommandé** ;
- lui donner à chaque fois la commande de publication **et** celle de retour arrière ;
- ne jamais pousser sur GitHub sans son accord. **Les 11 commits du LOT 0 ont été poussés** le
  27/07/2026 à 14:21:37 : à partir de là, seul un commit **non encore poussé** peut être annulé
  par `git reset --hard`. Vérifie systématiquement avec `git status -sb` avant d'annoncer un
  point de retour (`ECART-016`).

Le projet a une exigence de traçabilité inhabituellement élevée : 106 décisions identifiées pour
un lot documentaire. Ce n'est pas de la bureaucratie, c'est ce qui permettra, au LOT 9, de
justifier chaque ligne rejetée d'un import de données personnelles réelles. Tiens les registres
à jour dans la même pull request que le travail — jamais après.
