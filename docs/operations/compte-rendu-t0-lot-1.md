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

**Non levé. Action de Jonathan attendue.** Décision `DEC-448`.

Vérifications refaites le 27/07/2026, qui confirment le constat de `ECART-010` :

| Élément | Contrôle | Résultat |
|---|---|---|
| `gh` installé | `which gh` | Non — code de sortie 127 |
| Connecteur GitHub en session | recherche d'outils sur `github`, `issue`, `label`, `milestone` | Aucun outil disponible |
| Accès Git distant | `git ls-remote --heads --tags origin` | **Fonctionne**, identifiants valides |
| Protection de `main` | déduite du push direct réussi du 27/07 à 14:21:37 | **Absente** |
| Branche `develop` | `git ls-remote` et `git branch -a` | **N'existe ni en local ni sur `origin`** |

`QO-108` est close par `DEC-448` : la mise en place se fera dans l'interface GitHub, par
Jonathan. `QO-107` — le plan du compte permet-il les règles de protection sur un dépôt privé
personnel — ne pourra être close qu'à ce moment-là. `ECART-010` reste **ouvert**.

> **Point relevé en `T0`, à ne pas perdre.** Aucune des 12 sous-étapes de la fiche ne crée la
> branche `develop`, alors que `CONTRIBUTING.md` §3 en fait la première commande du premier
> commit de code. En l'état, `T1` ne peut pas être livré conformément à `DEC-427`. La création
> de `develop` est inscrite à la checklist de mise en place remise à Jonathan.

**Contrôle de sortie prévu :** après la mise en place, tenter un push direct sur `main`.
**Ce push doit échouer.** Un contrôle qui ne peut pas échouer ne prouve rien.

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

## 4. Constats de `T0` restés sans traitement

Trois écarts entre la documentation et l'état réel ont été relevés lors de la prise en charge et
**n'ont pas été corrigés**, faute d'approbation. Ils sont consignés ici pour ne pas être perdus.

| Réf. | Constat | Effet |
|---|---|---|
| B-3 | `CLAUDE.md` §4 annonce 44 fichiers versionnés et 39 Markdown ; le dépôt en porte **45 et 40**. L'écart est `CLAUDE.md` lui-même. `.gitattributes` est absent de la cartographie §8 | Aucun |
| B-4 | La fiche du LOT 1 §5 attribue `DB_AUTO_CREATE=false` au cahier §16.2. Le cahier **ne contient pas** cette chaîne — 0 occurrence, témoin positif `SQLAlchemy` à 4 occurrences. Le nom de variable vient de `.env.example` L104, et le cahier limite l'interdiction à la **production** | Citation à corriger ; le fond est juste et plus strict que le cahier |
| B-5 | La fiche §6 annonce **7** garde-fous de démarrage. `politique-configuration-et-secrets.md` §6 en définit **11** : 4 dans tous les environnements et 7 en production seule. La fiche ne retient que les 7 de production, c'est-à-dire ceux qui ne s'exercent pas en local | **Change ce que `T3` et `T6` doivent tester** |

`ECART-016`, relevé dans le même temps, a été corrigé et clos : la documentation de clôture du
LOT 0 affirmait que les commits étaient locaux alors que les 11 commits sont poussés depuis le
27/07/2026 à 14:21:37.

---

## 5. État à la sortie de `T0`

| | |
|---|---|
| LOT 1 | **Non ouvert.** Ouverture conditionnée à la mise en place GitHub |
| Prérequis levés | 2 sur 3 — reste le prérequis 1, action de Jonathan |
| Choix techniques tranchés | 7 sur 7 |
| Décisions ajoutées | `DEC-439` à `DEC-448`. Prochain libre : **`DEC-449`** |
| Questions closes | `QO-086`, `QO-108`, `QO-109`. Prochain libre : `QO-111` |
| Risques réévalués | `ROAD-RSK-026` atténué, `ROAD-RSK-027` réécrit sur mesures |
| Écarts | `ECART-016` clos. `ECART-010` reste ouvert jusqu'à la mise en place GitHub |
| Sous-étape suivante | `T1` — squelette du monorepo, story `MVP-L01-US001` |
