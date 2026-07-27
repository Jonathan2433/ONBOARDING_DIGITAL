# Compte rendu — sous-étape `T0` du LOT 1

**Exécutée le :** 27 juillet 2026, **hors lot**
**Nature :** prérequis et arbitrages techniques. **Aucune écriture de code, aucune dépendance installée.**
**Fondement :** [fiche du LOT 1](fiche-lot-1.md) §9.1 et §9.2
**Décisions produites :** `DEC-439` à `DEC-448`

---

## 1. Pourquoi `T0` a été exécutée avant l'ouverture du lot

La fiche du LOT 1 contient une contradiction interne : son §9.1 exige que les 3 prérequis
bloquants soient traités **« avant l'ouverture du lot »**, tandis que son §3 fait de `T0` —
la sous-étape qui les résout — la **première sous-étape du lot**. On ne peut pas à la fois
exiger qu'un point soit réglé avant l'ouverture et le régler dans le lot.

Arbitrage retenu par Jonathan : `T0` devient une **porte d'entrée hors lot**. Elle ne produit
aucune écriture applicative, donc son exécution sans lot ouvert n'enfreint ni `ROAD-003`, ni
`ARB-BACK-003`, ni `BACKLOG-006`. Le LOT 1 s'ouvrira à `T1`, sur des prérequis réellement levés.

Le présent compte rendu et l'inscription des décisions au registre sont des **livrables
documentaires**, de même régime que les sous-étapes du LOT 0 : commit direct sur `main`,
conforme à `DEC-427` qui ne déclenche le circuit branche + pull request qu'au premier commit
**de code**.

---

## 2. Les 3 prérequis bloquants — état de sortie

### 2.1 Prérequis 1 — traçabilité GitHub et protection de `main`

**Levé.** Décisions `DEC-448` puis **`DEC-449` qui la remplace**. `ECART-010`, `QO-107` et
`QO-108` clos.

État initial constaté le 27/07/2026, confirmant `ECART-010` :

| Élément | Contrôle | Résultat initial |
|---|---|---|
| `gh` installé | `which gh` | Non — code de sortie 127 |
| Connecteur GitHub en session | recherche d'outils sur `github`, `issue`, `label`, `milestone` | Aucun outil disponible |
| Accès Git distant | `git ls-remote --heads --tags origin` | **Fonctionne**, identifiants valides |
| Protection de `main` | déduite du push direct réussi du 27/07 à 14:21:37 | **Absente** |
| Branche `develop` | `git ls-remote` et `git branch -a` | **N'existait ni en local ni sur `origin`** |

#### Comment le prérequis a été levé

Jonathan a créé `develop`, puis autorisé l'installation de `gh` et **l'a authentifié lui-même**.
L'agent n'entre pas d'identifiants à sa place et n'extrait pas le jeton du trousseau macOS.

Homebrew s'est révélé inutilisable : `/opt/homebrew` appartient à l'utilisateur `admin`, pas à
`jonathan.dupau`, et le correctif `sudo chown` exige un mot de passe. Le binaire officiel
`gh 2.96.0` a donc été posé dans `~/.local/bin/gh`, **empreinte SHA-256 vérifiée** contre celle
publiée par `cli/cli` — `f23a0c37…a463`.

| Livrable | Contrôle | Résultat |
|---|---|---|
| 13 étiquettes prescrites | comparaison nom **et** couleur | **13/13 conformes**. 9 étiquettes GitHub par défaut subsistent |
| 15 milestones `G0`–`G14` | comptage et état | **15/15**, `G0` **fermée** (`DEC-438`), 14 ouvertes |
| Epic et stories du LOT 1 | comptage, milestone, étiquettes | Epic `#1`, stories `#2`–`#9`. **8/8 rattachées à `G1`**, 7 `p0` + 1 `p1` |
| Fidélité des issues au backlog | intitulé et critères recherchés mot pour mot | **8/8**, apostrophes `U+2019` préservées. Corps **générés** depuis le backlog, non transcrits |
| Protection de `main` et `develop` | lecture de l'API | PR obligatoire, **0 approbation**, `enforce_admins` **actif**, push forcés et suppressions rejetés, historique linéaire, résolution des conversations |

**Preuve d'effectivité, et non simple constat de réglage.** Un commit vide poussé directement
sur `main`, puis sur `develop`, a été **rejeté** :

```text
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: - Changes must be made through a pull request.
 ! [remote rejected] HEAD -> main (protected branch hook declined)
```

**Témoin positif :** le même push vers une branche neuve non protégée a **réussi**, puis la
branche a été supprimée. Le test sait donc distinguer un succès d'un échec.

> **Point relevé en `T0` et résolu.** Aucune des 12 sous-étapes de la fiche ne créait la branche
> `develop`, alors que `CONTRIBUTING.md` §3 en fait la première commande du premier commit de
> code. Jonathan l'a créée. Elle avait été créée **avant** le push des deux commits de `T0` et
> accusait donc 2 commits de retard sur `main` ; une avance rapide `main:develop` l'a alignée
> avant que la protection ne soit posée.

**Effet de bord à connaître :** `enforce_admins` s'applique aussi à Jonathan. Plus aucun commit
direct sur `main` ni `develop`, **y compris documentaire**. `DEC-427` ne prévoyait ce régime
qu'au premier commit de code du LOT 1 ; il s'applique en pratique dès maintenant.

### 2.2 Prérequis 2 — atténuations iCloud

**Levé.** Décisions `DEC-439` et `DEC-447`. `QO-109` close.

La mesure a montré que le périmètre du risque était **plus étroit qu'annoncé** :

```text
docker info --format '{{.DockerRootDir}}'   ->  /var/lib/docker
du -sh ~/Library/Containers/com.docker.docker/Data/vms   ->  28G
```

`Docker Root Dir` est un chemin **interne à la machine virtuelle** Docker Desktop, dont l'image
disque réside sous `~/Library/Containers/`, **hors iCloud Drive**. Tout volume Docker nommé est
donc déjà hors iCloud, sans aucune action. `ROAD-RSK-026` ne portait réellement que sur
`node_modules/`, le cache de paquets, et sur d'éventuels bind mounts de données vers le dépôt.

Atténuations retenues : exclusion de `node_modules/` et du cache de la synchronisation iCloud,
store `pnpm` hors du dossier synchronisé, et **interdiction de tout bind mount de donnée
d'état** vers `./data`, `./volumes` ou `./backups`. Le dépôt reste dans iCloud : `DEC-418` n'est
pas rouverte. Risque résiduel assumé et inchangé : la synchronisation de `.git` lui-même.

### 2.3 Prérequis 3 — exécution non simultanée des environnements

**Levé.** Décision `DEC-440`. `ROAD-RSK-027` réécrit, `QO-085` complétée sans être close.

Les deux prémisses du risque d'origine étaient inexactes, **dans le sens défavorable** :

| Grandeur | Ce que disait le registre | Ce que mesure `T0` |
|---|---|---|
| Plafond mémoire applicable | 16 Gio, la machine | **7,75 Gio**, alloués à la VM Docker |
| Budget disponible | implicitement entier | **~5,8 Gio** — un projet tiers en occupait 25 % |

`observatoire-ecom-studio`, sans rapport avec eXalt, exécutait **5 conteneurs depuis 5 jours**
pour **~1,93 Gio**, dont 1,77 Gio pour son seul worker. La coexistence de deux stacks complètes,
envisagée en `T8`, est hors d'atteinte sans intervention.

Traitement : un seul environnement à la fois, limites mémoire par service, et arrêt du projet
tiers pendant la durée du LOT 1 — ce qui porte le budget à ~7,7 Gio pour une stack. `T8` prouvera
la **séparation** des environnements par démarrages **successifs** : le cahier §22.2 exige des
ressources distinctes, il n'exige nulle part la simultanéité.

> Le projet tiers **n'a pas été arrêté** en `T0`. L'arrêt interviendra en `T2`, au moment où la
> stack en aura besoin, et sur confirmation de Jonathan.

---

## 3. Les 7 choix techniques — synthèse

Aucun document validé ne les fixait. Tous sont tranchés et inscrits au registre.

| # | Choix | Décision retenue | ID |
|---:|---|---|---|
| 1 | Paquets JavaScript et outillage monorepo | `pnpm` workspaces, sans orchestrateur de tâches | `DEC-441` |
| 2 | `mypy` ou `pyright` | **`mypy`**, mode strict, dans l'environnement `uv` | `DEC-442` |
| 3 | Versions épinglées | Python 3.12 · Node 24 LTS · PostgreSQL 17, empreinte `sha256` dans les `Dockerfile` | `DEC-443` |
| 4 | Organisation des fichiers Compose | Base + surcouches, 3 projets Compose distincts | `DEC-444` |
| 5 | Nommage et étiquetage GHCR | `ghcr.io/jonathan2433/onboarding-digital/{api,web,worker}` | `DEC-445` |
| 6 | HTTPS local par Caddy | `tls internal` sur `*.onboarding.localhost` | `DEC-446` |
| 7 | Emplacement physique des volumes | Volumes nommés exclusivement | `DEC-447` |

Les outils candidats du cahier §23.5 — `uv`, Ruff, Pytest, pytest-cov, Alembic, Gitleaks,
pip-audit, Trivy, Vitest, Playwright, axe — sont retenus sans objection, ces choix étant déjà
inscrits au cadrage.

### 3.1 Dépendances entre choix, à ne pas défaire

- `DEC-441` (`pnpm`) **dépend** de `DEC-439` : le store partagé et l'arborescence non aplatie ne
  sont un avantage que si `node_modules` sort d'iCloud. Si `DEC-439` était rouverte, `npm`
  workspaces redeviendrait le choix sûr.
- `DEC-447` (volumes nommés) **est** la mise en œuvre de l'atténuation `DEC-439` côté données.
- `DEC-446` (HTTPS local) est motivé par le **LOT 3**, pas par le LOT 1 : les cookies `Secure` et
  `SameSite` ne peuvent pas être éprouvés en HTTP clair, et les découvrir après la porte `G1`
  serait le scénario de réouverture que signale `ROAD-RSK-002`.

---

## 3.2 Défauts détectés pendant `T0`

Même règle qu'au LOT 0, dont les sept défauts sont documentés dans
[`controles-sortie-lot-0.md`](controles-sortie-lot-0.md) §7 : un défaut détecté est consigné,
y compris — et surtout — quand c'est le contrôle qui était faux et non le livrable.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T0-1` | Le contrôle de rejet du push direct affichait « push ACCEPTÉ » alors que le serveur avait renvoyé `GH006` et refusé la mise à jour. Le test était écrit `if git push … \| sed; then` : le `if` évaluait le code de sortie de `sed`, toujours nul, et non celui de `git push` | **Contrôle faux, livrable correct.** C'est exactement le piège documenté en passation §6.2, « le code de sortie d'un pipeline est celui du dernier maillon » | Contrôle réécrit sans pipeline, sortie capturée dans une variable et code de sortie testé directement, avec témoin positif sur branche non protégée |
| `T0-2` | `DEC-448` énonçait que la traçabilité GitHub serait posée « par Jonathan dans l'interface GitHub ». La mise en place a en réalité été faite par `gh`, l'agent exécutant les créations après authentification par Jonathan | **Décision devenue inexacte.** Une décision validée ne se modifie pas en silence (`CONTRIBUTING.md` §8) | Remplacée par `DEC-449`, qui la référence explicitement |
| `T0-3` | `develop` avait été créée depuis `main` **avant** le push des deux commits de `T0`, et accusait 2 commits de retard. Une branche de travail partie de `develop` aurait ignoré `ECART-016` et les 10 arbitrages | **Livrable incohérent**, détecté par `git rev-list --left-right --count` avant toute création de branche de travail | Avance rapide `main:develop`, effectuée avant la pose de la protection. Vérifiée à `0/0` |

Le défaut `T0-1` est le plus instructif : il reproduit, sur un contrôle de sécurité, la même
classe d'erreur que le défaut n°7 du LOT 0 — un contrôle qui affichait « aucun secret » sans
rien vérifier. **Un contrôle qui ne peut pas échouer ne prouve rien ; un contrôle dont on ne
lit pas le code de sortie ne prouve rien non plus.**

---

## 4. Constats de `T0` restés sans traitement

Trois écarts entre la documentation et l'état réel ont été relevés lors de la prise en charge et
**n'ont pas été corrigés**, faute d'approbation. Ils sont consignés ici pour ne pas être perdus.

Trois écarts relevés à la prise en charge, **tous corrigés** dans la même pull request que la
clôture des prérequis, sur arbitrage de Jonathan.

| Réf. | Constat | Effet | Traitement |
|---|---|---|---|
| B-3 | `CLAUDE.md` §4 annonçait 44 fichiers versionnés et 39 Markdown ; le dépôt en porte **45 et 40**. L'écart est `CLAUDE.md` lui-même, ajouté par le commit qui portait la phrase. `.gitattributes` était absent de la cartographie §8 | Aucun | Chiffres rectifiés, `.gitattributes` ajouté à la cartographie |
| B-4 | La fiche du LOT 1 §5 attribuait `DB_AUTO_CREATE=false` au cahier §16.2. Le cahier **ne contient pas** cette chaîne — 0 occurrence, témoin positif `SQLAlchemy` à 4 occurrences. Le nom de variable vient de `.env.example` L104, et le cahier limite l'interdiction à la **production** | Citation fausse ; le fond était juste et plus strict que le cahier | Source rectifiée dans la fiche, en explicitant que le LOT 1 applique la contrainte à **tous** les environnements |
| B-5 | La fiche §6 annonçait **7** garde-fous de démarrage. `politique-configuration-et-secrets.md` §6 en définit **11** : 4 dans tous les environnements et 7 en production seule. La fiche ne retenait que les 7 de production, ceux qui **ne s'exercent pas** en local | **Changeait ce que `T3` et `T6` doivent tester** | Porté à 11, avec la répartition 4 + 7 et la mention qu'il faut forcer `APP_ENV=production` en test pour éprouver les 7 derniers |

`ECART-016`, relevé dans le même temps, a été corrigé et clos séparément : la documentation de
clôture du LOT 0 affirmait que les commits étaient locaux alors que les 11 commits sont poussés
depuis le 27/07/2026 à 14:21:37.

**Reste non traité, en attente de décision de Jonathan :** le fichier `AGENTS.md`, apparu à la
racine le 27/07/2026 à 15:02, copie de `CLAUDE.md` à huit lignes près et figée à un état
intermédiaire. Il n'a pas été créé par l'agent et **n'est pas suivi par Git**. Deux passations
concurrentes divergeraient dès le commit suivant : c'est la double source de vérité que
[`traceabilite-github.md`](traceabilite-github.md) §2.2 s'attache à éviter.

---

## 5. État à la sortie de `T0`

| | |
|---|---|
| LOT 1 | **Non ouvert.** Tous les prérequis sont levés : l'ouverture ne dépend plus que de la décision de Jonathan |
| Prérequis levés | **3 sur 3** |
| Choix techniques tranchés | **7 sur 7** |
| Décisions ajoutées | `DEC-439` à `DEC-449`, dont `DEC-449` qui **remplace** `DEC-448`. Prochain libre : **`DEC-450`** |
| Questions closes | `QO-086`, `QO-107`, `QO-108`, `QO-109` — 30 restent ouvertes sur 34. Prochain libre : `QO-111` |
| Risques réévalués | `ROAD-RSK-026` atténué, `ROAD-RSK-027` réécrit sur mesures |
| Écarts | `ECART-010` et `ECART-016` **clos**. 6 restent ouverts : `005`, `006`, `012`, `013`, `014`, `015`. Prochain libre : `ECART-017` |
| Traçabilité GitHub | 13 étiquettes, 15 milestones, epic `#1`, stories `#2`–`#9`, `main` et `develop` protégées |
| Régime de contribution | **Branche + pull request obligatoire**, y compris pour la documentation. `enforce_admins` actif |
| Sous-étape suivante | `T1` — squelette du monorepo, story `MVP-L01-US001`, issue `#2` |
