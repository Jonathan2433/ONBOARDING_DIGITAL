# Checklist de validation — porte `G6`

**Lot :** LOT 6 — Framework, cercles, bureaux et contenus éditoriaux
**Préparée le :** 25 septembre 2026, à la sortie de `T12`
**Destinataire :** Jonathan — c'est lui qui franchit la porte
**Décision attendue :** `DEC-596`

---

**Comment lire ce document.** Chaque affirmation est suivie de **la commande qui la produit**. Rien
n'est recopié : tous les nombres ci-dessous ont été **dérivés le 25/09/2026** — `ECART-021`, §7.27.
**Recompte avant de réutiliser.**

**Un seul des sept critères demande ton avis** — le septième. Les six autres sont **mécaniquement
prouvés**, ce qui veut dire qu'ils font échouer l'intégration continue si quelqu'un les casse.

---

## 1. Les sept critères de sortie — fiche §1.2

| # | Critère | Comment il est tenu | Ce qui le prouve |
|---|---|---|---|
| 1 | les contenus de Bordeaux sont **relus avant publication** | l'état `draft` est le défaut à la création (`T6`) ; la publication est un **geste distinct**, `POST …/publication`, versionné et daté (`T7`) | `test_une_page_creee_est_en_BROUILLON` · `publiee_le` et `version` dans les octets servis, mesuré en `T11` sur la reprise de `BORDEA00` |
| 2 | le modèle générique ne contient **aucune** donnée locale | une entité **GÉNÉRIQUE**, sans aucun décor, ne sert aucun octet « bordeaux » — et un **témoin positif** prouve que la recherche discrimine réellement (§7.39) | `make framework-check`, contrôles 75/76 (`T11`, `DEC-595`) — mis en échec **délibérément** avant d'être retenu |
| 3 | les composants respectent le **design system** | `cadre-check` étendu aux composants du lot ; aucune couleur hors jetons dans les feuilles | `make cadre-check` — 25 contrôles, 0 échec |
| 4 | les couleurs de cercle ne sont **jamais** l'unique information | le couple du §7.42 — un cercle **avec** jeton et un cercle **sans**, le libellé toujours écrit | test qui monte les deux cartes et lit la propriété personnalisée CSS (`T9`) |
| 5 | les animations respectent `prefers-reduced-motion` | `.framework-carte`, seule transition nouvelle du lot, neutralisée dans le même bloc `@media` que `.nat-entite` | `make cadre-check`, règle 5 — 4 transitions déclarées, toutes neutralisées |
| 6 | aucun contenu arbitraire ne peut **injecter du code** | **structurel**, pas un filtre : `BlocSoumis` n'offre aucun champ par lequel déclarer qu'une chaîne est du balisage | témoin positif (bloc légitime rendu) **et** charge d'injection refusée — `test_ecriture_des_contenus.py`, traversée intacte jusqu'aux octets servis (`make framework-check`) |
| 7 | **Jonathan valide** l'organisation et l'édition | **ta décision.** La démonstration du §3 est là pour cela | — |

---

## 2. Les contrôles de stack, et ce que chacun refuse

| Contrôle | Contrôles internes | Ce qu'il refuse |
|---|---:|---|
| `make framework-check` | **77** | un octet « bordeaux » servi par une entité générique ; une page archivée retrouvable sans droit ; une collision de route entre `/pages/{page}/gestion` et un slug utilisateur valant « gestion » ; un bureau publié hors de un-à-trois responsables ; un lien `http` ou sans hôte |
| `make cadre-check` | **25** | une couleur hors jetons ; une propriété personnalisée non définie ; une animation non neutralisée par `prefers-reduced-motion` |
| `make ecrans-check` | **8** | une couleur littérale dans les feuilles ; un jeton dans `localStorage` ; un conteneur `web` plus ancien que le dépôt |
| `make permissions-check` | 15 | une permission locale transférée hors de l'entité principale |
| `make recette-modele-check` | 25 (§30) | un contrôle du §30 non classé, ou un test cité qui n'existe pas |
| `make residu-check` | — | qu'un test laisse une ligne derrière lui — **74 échecs environnementaux connus, 0 résidu** |

```bash
make framework-check && make cadre-check && make cadre-temoin && make ecrans-check
make permissions-check && make recette-modele-check && make residu-check
```

**Tous sont dans l'intégration continue**, `ci.yml`, donc bloquants sur chaque pull request —
`framework-check` seul est passé de 68 à 74 (`T10`) puis 77 (`T11`) sans qu'aucune cible n'ait dû
être ajoutée à `ci.yml` (§7.27).

---

## 3. La démonstration guidée — dix gestes, dans cet ordre

**Ouvre Safari, Chrome ou Edge.** Pas Firefox.

| # | Où | Ce que tu regardes |
|---|---|---|
| 1 | `https://app.onboarding.localhost/connexion/administrateur` | Connexion avec le compte `demo.client@exemple.test` (mot de passe à régénérer, `make admin-local ADRESSE=demo.client@exemple.test REINITIALISER=1`) |
| 2 | `…/entites/BORDEA00` | « Accueil de l'entité » — la **présentation**, reprise verbatim du prototype, **Publiée — version 3** |
| 3 | `…/entites/BORDEA00/framework` | Les **trois familles** de cartes — responsabilités, cercles, bureaux — toujours les trois, même vides |
| 4 | clique un **cercle** | La page détaillée : membres paginés, Booster, bordure colorée et **nom toujours écrit** |
| 5 | clique un **bureau** | Ses responsables actifs, zéro à trois |
| 6 | `…/framework/cercles/{code}/editer` (rôle éditorial) | Réordonner/retirer un bloc existant. **Aucun bouton « créer un bloc »** — `QO-121` n'est pas tranchée, l'inventer serait §6.5 |
| 7 | le bouton **Publier / Archiver / Restaurer** | Selon l'état de la page, gaté par rôle — refus par défaut si le rôle ne l'a pas |
| 8 | `…/liens/gestion` | Les liens internes — Hub, eXalt Academy, SharePoint — création, réordonnancement, désactivation |
| 9 | tente de créer un lien en `http://…` | Refusé — `https` seul, et un lien sans hôte (`https:alert(1)`) l'est aussi sous un code distinct |
| 10 | `…/entites/BORDEA00/trombinoscope` | Inchangé depuis `G5` — preuve que le lot n'a rien cassé d'un lot précédent |

**Deux choses à dire pendant la démonstration :**

- **la présentation de `BORDEA00` est la seule vraie donnée de contenu du lot.** Les cercles et
  bureaux affichés sont le jeu de démonstration, pas des contenus « relus » — `ECART-015` : le
  prototype ne fournit ni descriptions de cercle ni liens internes, ce sont des contenus à produire
  par Léa ;
- **`QO-121` reste ouverte, par ton report explicite du 25/09/2026** — pas par oubli. Un écran qui
  proposerait de créer un bloc ou d'éditer ses champs resterait bloqué tant qu'elle n'est pas
  tranchée.

---

## 4. Les grandeurs, avec la commande qui les produit

| Grandeur | Valeur | Commande |
|---|---:|---|
| Tests | **1 767** | ci-dessous |
| — `pytest` | **1 181** | `uv run pytest -q --collect-only \| tail -1` |
| — dont d'intégration | **808** | `uv run pytest -m integration -q --collect-only \| tail -1` |
| — `Vitest` | **586** | `make test-frontend` — 250 `contracts`, 111 `ui`, 225 `web` |
| Tables PostgreSQL | **32** | `information_schema.tables` |
| Déclencheurs | **10** | `count(distinct trigger_name)`, `information_schema.triggers` |
| Migrations | **19**, tête `0019` | `ls apps/api/alembic/versions/*.py \| wc -l` |
| Endpoints du contrat | **37** | `packages/contracts/src/contrat-api.json` |
| Cibles du `Makefile` | **93** | `grep -cE '^[a-z][a-z0-9-]*:.*##' Makefile` |
| Variables de `.env.example` | **84** | `grep -cE '^[A-Z_][A-Z0-9_]*=' .env.example` |
| **Défauts nommés au LOT 6** | **26** | `grep -ohE '\`T[0-9]+-[0-9]+\`' docs/operations/compte-rendu-t*-lot-6.md \| sort -u \| wc -l`, filtré à `n == N` (§7 de `CLAUDE.md`) |
| Décisions du lot | `DEC-575` à `DEC-596` | dont **3** hors numérotation : `DEC-580`, `DEC-581`, `DEC-590` |
| Jeu de démonstration | **28** entités, **5 156** personnes, **1** page de contenu | mesuré en base |

---

## 5. La recette — FAITE le 25/09/2026

**La recette a été épinglée sur la dernière publication réussie** (`make images-pin`, commit
`07571f9`, `T11`), sa base **détruite et reconstruite** (`make down-recette`, suppression du volume
`db-data`, `make up-recette`, `make migrate ENVIRONNEMENT=recette`). Un conflit de port avec le
projet tiers `observatoire-ecom-studio` (port `8080`, §7.23) a été résolu en l'arrêtant le temps de
la recette — relancé ensuite.

```text
make images-pin             code=0   3 empreintes relevees, identite verifiee
make down-recette · up-recette · migrate ENVIRONNEMENT=recette      code=0, 8/8 services sains
make recette-check          code=0   57 controles, 7/7 separations du cahier 22.2

Sur DEV, base réelle (28 entités, 5 156 personnes) :
make check                  code=2   74 echecs ENVIRONNEMENTAUX connus (jeu de demo), 0 lie au code
make icloud-verify · env-check · audit                               tous code=0
make code-refresh           code=0   ← AVANT les controles d'ecran
make code-check · api-check · web-check · stack-check                tous code=0
make residu-check           74 echecs environnementaux, 0 RESIDU
make profil-check 45 · trombinoscope-check 38 · entites-check 13     tous code=0
make cadre-check 25 · cadre-temoin · ecrans-check 8                  tous code=0
make permissions-check                                               code=0
make framework-check        77 controles, 0 echec — dont le temoin du critere 2

Les ONZE controles d'authentification
  magic-link-check 15 · admin-check 10 · sessions-check 13 · sessions-temoin
  csrf-check 10 · debit-check 12 · revocation-check 6 · service-check 11
  evenements-check 6                                                  tous code=0

Les controles de schema
  privileges-check · secrets-check · isolation-check · isolation-temoin
  historisation-check · migrations-check · recette-modele-check · alembic-check
  stack-check · ports                                                 tous code=0
```

**Les 74 échecs pytest sont environnementaux, prouvés par comparaison à `origin/develop` sur la
même base**, via `git worktree` (§7.22) : listes de tests identiques à l'octet près, à chaque
sous-étape de `T7` à `T12`. Le jeu de démonstration (`make demo-init`) pollue les comptes absolus
que ces tests exigent ; aucun n'appartient au code livré par le LOT 6.

---

## 6. Les contrôles du §30 : **un reclassement**, mesuré et corrigé

```text
make recette-modele-check   code=0
  info  25 controles enumeres par le §30, LUS dans le modele
  ok    les 25 controles sont classes, aucun en trop
```

| Statut | Nombre | Évolution depuis `G5` |
|---|---:|---|
| **acquis** | **13** | inchangé |
| **partiel** | **2** | **+1** — §30.8 reclassé |
| **inapplicable** | **0** | **-1** — §30.8 sortait de ce statut |
| **reportés** | **10** | inchangé |

**Le seul reclassement possible a été trouvé, et il datait d'avant `T1`.** `§30.8` — « un bureau
publié possède entre un et trois responsables » — était classé `INAPPLICABLE`, citant `ECART-031`
comme motif : « le §8.4 exige un bureau publié, le §8.3 ne déclare aucun état de publication ». Or
`ECART-031` est **clos depuis `DEC-576`**, à l'ouverture même du lot, avant `T1` — le classement
n'avait simplement jamais été mis à jour. Reclassé `PARTIEL` : le déclencheur de `T7` (migration
`0018`, `DEC-583`) garde la **transition** vers `published` — acquis, quatre tests le prouvent, sur
les trois valeurs valides et les deux refusées — mais pas l'**état permanent** : un bureau publié
conforme peut le rester en apparence si ses responsables sont retirés ensuite, et rien ne l'en
empêche. `T4` ne ment pas sur ce résiduel : sa lecture rend zéro, un, deux, trois ou quatre
responsables actifs, jamais une hypothèse.

---

## 7. Ce que le lot n'a PAS fait, et qu'il ne faut pas croire acquis

| Point | État réel |
|---|---|
| **`QO-121`** | les champs de chaque bloc (`payload_json`) ne sont nommés pour aucun des onze types. Report **explicite** de ta part le 25/09/2026, pas un oubli. Bloque un écran qui proposerait la création d'un bloc ou l'édition de ses champs — aucun autre |
| **Contenus de cercle et de liens** | `ECART-015` : le prototype n'en fournit aucun. Seule la présentation d'entité a été reprise (`T11`) ; les cercles et bureaux affichés restent le jeu de démonstration |
| **`ECART-064`** | aucune route n'écrit `archive_reason` ni `assignment_reason` — motif d'intervention du super-administrateur, §18.1. Non bloquant pour le MVP, à instruire au LOT 10 avec `audit_event` |
| **La démonstration visuelle du LOT 5** | inchangée par ce lot, gestes 8-10 ci-dessus pour le vérifier |
| **`US006` sans écran** (résiduel du LOT 5) | toujours vrai, hors périmètre du LOT 6 |
| **`ECART-065`** | la fiche profil du LOT 5 porte encore le titre `<h1>` faux sur sous-page paramétrée ; corrigé seulement pour les gabarits que `T9` introduit |

---

## 8. Réserves à connaître avant de valider

**1. `QO-121` conditionne toute évolution future de l'écran d'édition.** Tant qu'elle n'est pas
tranchée, aucun écran ne pourra proposer la création d'un bloc — c'est un choix délibéré (§6.5), pas
une limite technique.

**2. `ROAD-RSK-033`/`034` restent inchangés**, à réévaluer avant le LOT 13 — aucune ligne du LOT 6
n'y touche.

**3. L'archive gelée `bitnamilegacy/minio` (`DEC-590`) ne recevra plus de correctif de sécurité.**
Résiduel accepté pour débloquer la CI le 25/09/2026 — MinIO a fermé l'accès public à ses images
officielles le même mois. À réévaluer si un avis de sécurité la concerne.

---

## 9. Ta décision

**Ce que tu valides :** les sept critères de sortie du LOT 6, dont le septième est ton avis sur
l'organisation et l'édition, formé au §3.

**Ce que la porte ouvre :** le **LOT 7** — dont le périmètre reste à cadrer.

**Ce qu'elle ne clôt pas :** `QO-121` — report explicite, non bloquant hors création de bloc ·
`ECART-064` — LOT 10 · `ECART-065` — prochaine sous-page paramétrée · `US006` du LOT 5 — toujours
sans écran.

| | |
|---|---|
| Date | |
| Décision | ☐ franchie ☐ à reprendre |
| Réserves | |
