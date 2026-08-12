# Checklist de validation — porte `G1`

**Pour :** Jonathan
**Lot :** 1 — Monorepo, qualité et environnement local
**Date :** 12 août 2026
**Tag posé à la validation :** `v0.1.0` sur `main` (`DEC-428`)
**Preuves détaillées :** les onze comptes rendus [`compte-rendu-t0`](compte-rendu-t0-lot-1.md) à [`t10`](compte-rendu-t10-lot-1.md)

Cette checklist est faite pour être lue et tranchée. C'est la mesure du risque `ROAD-RSK-010`,
« Jonathan devient un goulot de validation ».

**Tout ce qui suit a été exécuté le 12/08/2026 sur le commit `3effa2f`.** Les codes de sortie cités
sont réels. Aucune ligne n'affirme un résultat qui n'a pas été mesuré.

---

## 1. Les sept critères de sortie de la roadmap

| | Critère, littéral | Preuve | État |
|:--:|---|---|:--:|
| 1 | Tous les services démarrent sur le Mac M5 | `make up` et `make up-recette` → **8/8 sains** chacun. Et **depuis une machine réellement propre** en `T9` : 0 volume, 0 image, remontée en **34 s** | ☑ |
| 2 | Les images multiarchitectures sont construites | 3 images, **une seule liste de manifestes** portant `linux/amd64` **et** `linux/arm64`, vérifié à l'instant. **Lancées** sur les deux — 39 contrôles en `T7` — et `arm64` **natif** sur l'image publiée depuis `T8` | ☑ |
| 3 | **Aucun secret réel n'est présent** | Gitleaks à chaque pull request depuis `T6`, **historique compris**, avec des règles taillées sur les formats de ce projet. **47 commits scannés, 0 fuite.** Aucun secret de dépôt n'existe : `gh secret list` est vide | ☑ |
| 4 | Une migration Alembic vide ou initiale s'exécute | `make migrate` → `0001 (head)`. Rejouée à chaque pull request, **et sur une base créée de zéro** en `T9` | ☑ |
| 5 | Les logs possèdent un identifiant de corrélation | `T4` : les 10 champs du cahier §28.1 dans les journaux **réels**, corrélation en requête **et** en job. Le nom de l'en-tête est **partagé et vérifié** depuis `T10` | ☑ |
| 6 | **La CI bloque volontairement une erreur de lint, de test et de secret** | `T6` : trois défauts introduits **un par un**, trois exécutions rouges, **`mergeStateStatus: BLOCKED` dans les trois cas**. Témoin positif indispensable : la même porte laisse passer une branche saine | ☑ |
| 7 | **Jonathan valide le socle** | **c'est cette checklist** | ☐ |

---

## 2. Les huit stories du lot

| Story | Objet | Sous-étapes | Issue |
|---|---|---|:--:|
| `MVP-L01-US001` | Squelette du monorepo | `T1` | `#2` ✅ |
| `MVP-L01-US002` | Stack Docker locale | `T2`, `T5`, **`T8`** | `#3` ✅ |
| `MVP-L01-US003` | Les trois endpoints de santé | `T3` | `#4` ✅ |
| `MVP-L01-US004` | Logs JSON corrélés | `T4` | `#5` ✅ |
| `MVP-L01-US005` | CI qualité et sécurité | `T6` | `#6` ✅ |
| `MVP-L01-US006` | Images ARM64/AMD64 dans GHCR | `T7` | `#7` ✅ |
| `MVP-L01-US007` | Design system et contrat API (**`P1`**) | `T10` | `#8` ✅ |
| `MVP-L01-US008` | Documentation d'exploitation | `T9` | `#9` ✅ |

**Les huit sont `Done`.** `US007`, seule story `P1`, a été **réalisée et non reportée** : la
condition « les stories `P1` non terminées ont fait l'objet d'un arbitrage explicite » est donc sans
objet.

---

## 3. Les neuf critères d'empêchement du backlog §12

| | Critère | État |
|:--:|---|:--:|
| ☑ | Une migration fonctionne sur une base propre | prouvé sur une base créée de zéro en `T9` |
| ☑ | Aucun secret ni donnée réelle versionné | **vérifié automatiquement**, historique compris |
| ☑ | La documentation minimale d'exploitation existe et fonctionne depuis une machine propre | [`exploitation-locale.md`](exploitation-locale.md), **toutes ses commandes exécutées** |
| ☑ | La démonstration correspond aux critères de la roadmap | §5 de cette checklist |
| — | Permissions critiques · comportement mobile ou clavier essentiel · authentification · écrans métier | **sans objet au LOT 1** : ces périmètres appartiennent aux LOTS 3 à 5 |

---

## 4. Les contrôles rejoués, avec leurs codes de sortie réels

**33 contrôles, tous à 0**, exécutés le 12/08/2026.

**Développement — 24 contrôles :**

```text
tools 0 · versions 0 · tree 0 · icloud-verify 0 · env-check 0
lint 0 · format-check 0 · typecheck 0 · test 0 · test-unit 0
test-integration 0 · test-frontend 0 · check 0 · docs-check 0 · audit 0
images-check 0 · stack-check 0 · health 0 · ports 0 · api-check 0
web-check 0 · alembic-check 0 · migrate-status 0 · persistence-test 0
```

**Recette — 9 contrôles :**

```text
env-check 0 · health 0 · ports 0 · stack-check 0 · api-check 0
web-check 0 · alembic-check 0 · migrate-status 0 · persistence-test 0
```

**Les deux ensemble :** `separations-check` **0** — *57 contrôles, 0 échec, 7 séparations attendues /
7 vérifiées* — et `recette-check` **0**.

**Chiffres dérivés de la source, pas recopiés :**

| Grandeur | Valeur | Commande qui la donne |
|---|---:|---|
| Tests | **260** — 144 pytest, 116 Vitest | `make check` |
| Cibles `Makefile` | **50** | `make help` |
| Fichiers suivis | **170** | `git ls-files \| wc -l` |
| Décisions | **76** en usage, max `DEC-493` | `make docs-check` les **dérive** |
| Écarts · questions · risques | **24** · **39** · **34** | idem |
| Publications de ports | **14** — 7 + 7, bandes disjointes | `make ports` par environnement |
| Volumes | **12** — 6 + 6, aucun partagé | `docker volume ls --filter label=…` |

---

## 5. Démonstration guidée

**Les six éléments que la roadmap demande, dans l'ordre, avec la commande et ce que tu dois voir.**
Chaque sortie ci-dessous a été relevée le 12/08/2026.

### 5.1 Lancement complet avec **une commande documentée**

```bash
make up
```

Elle construit, démarre les huit services d'infrastructure, **crée le bucket MinIO**, démarre les
services applicatifs, recharge Caddy, puis contrôle santé et ports. Elle **échoue** si l'un des huit
n'est pas sain.

À voir : `--> les 8 services sont sains`, puis `--> 7 publications, toutes limitées à la boucle
locale`.

> **L'ordre n'est pas cosmétique** : sans le bucket créé **avant** que l'API doive être saine, la
> sonde de disponibilité répond 503 et le démarrage échoue. C'est `DEC-477`, et le symptôme est
> documenté au §7.2 de l'exploitation.

### 5.2 Page web de statut

Ouvre **`https://app.onboarding.localhost`** dans Safari, Chrome ou Edge.

À voir : l'état réel des **trois** dépendances sondées, la version du build, et la mention explicite
que le worker, Mailpit et Caddy **ne sont pas sondés** — la page dit ce qu'elle ne sait pas.

Mesuré à l'instant, à travers Caddy en HTTPS :

```text
dev      racine React : 1   module d'entree : /src/main.tsx
recette  racine React : 1   module d'entree : /assets/index-BVCc0Fm0.js
```

**Les deux formes sont normales et la différence est le sujet de `DEC-479`** : le développement sert
le serveur Vite avec rechargement à chaud, la recette sert l'**artefact bâti**.

> **Firefox affichera un avertissement de certificat**, et c'est normal : il gère son propre magasin.
> Safari, Chrome et Edge font confiance à la racine que tu as approuvée. La recette avertira dans
> **tous** les navigateurs — sa racine n'est pas approuvée, et ce n'est pas un défaut.

Pour le vérifier sans navigateur :

```bash
make web-check
```

### 5.3 API répondant aux trois healthchecks

```bash
make api-check
```

Relevé à l'instant, **depuis l'hôte, à travers Caddy en HTTPS** :

```text
dev      /health/live      {"statut":"vivant"}
dev      /health/version   {"version":"0.0.0-dev","revision":"inconnue","environnement":"development"}
dev      /health/ready     HTTP 200   3 dependances nommees
recette  /health/live      {"statut":"vivant"}
recette  /health/version   {"version":"0.0.0-dev","revision":"1060ad6","environnement":"recette"}
recette  /health/ready     HTTP 200   3 dependances nommees
```

**Deux choses à remarquer, et elles sont voulues :**

- **la recette annonce `revision: 1060ad6`, le développement `inconnue`.** La recette exécute une
  image **publiée et épinglée** ; le développement construit localement et n'a pas de révision
  gravée. C'est la preuve visible que les deux environnements exercent des artefacts différents ;
- **`/health/ready` répond 503 quand une dépendance manque, avec la même forme JSON qu'un 200.** Un
  503 est un **diagnostic exploitable**, pas une panne de transport. Éprouvé en `T3` et `T5` **en
  arrêtant réellement Redis**.

### 5.4 PostgreSQL, Redis, MinIO, worker et Mailpit **sains**

```bash
make health
make health ENVIRONNEMENT=recette
```

Relevé à l'instant : **`onboarding-dev` 8/8 sains**, **`onboarding-recette` 8/8 sains**.

La cible **échoue** si l'un n'est pas sain — elle ne se contente pas d'afficher.

### 5.5 Arrêt et redémarrage **sans perte des volumes**

```bash
make persistence-test
```

Elle relève cinq empreintes, **arrête**, **redémarre**, compare, et **annonce combien elle en a
comparées** — `5 empreintes relevées, 5 comparées`.

> **Le témoin négatif a été réellement exécuté en `T2`** : le volume `redis-data` supprimé, le
> contrôle a signalé `redis PERDU`. Un contrôle de persistance qui ne peut pas échouer ne prouve rien.

### 5.6 Pipeline CI réussi

```bash
gh run list --limit 3
```

Relevé à l'instant :

```text
Integration continue | main    | success | 31606327386
Integration continue | develop | success | 31606316038
Integration continue | develop | success | 31604904521
```

**Les 11 contrôles du cahier §23.1** tournent sur chaque pull request en ~2 min 20, découpés en deux
tâches et une **porte** unique que la protection de branche exige.

### 5.7 En supplément — ce que la roadmap ajoute par les critères de sortie

**Les images multiarchitecture**, vérifié à l'instant sur le registre :

```text
api    : ['linux/amd64', 'linux/arm64']
worker : ['linux/amd64', 'linux/arm64']
web    : ['linux/amd64', 'linux/arm64']
```

**Et les sept séparations du cahier §22.2**, sur l'état réel des deux environnements :

```bash
make separations-check
```

→ *57 contrôles, 0 échec, 7 séparations attendues / 7 vérifiées.*

---

## 6. Ce que tu valides précisément

En validant `G1`, tu valides :

1. **le socle technique** : monorepo, chaîne de qualité, huit services, deux environnements isolés,
   images multiarchitecture publiées, intégration continue bloquante ;
2. **les 76 décisions** `DEC-418` à `DEC-493` inscrites au registre ;
3. **les choix d'outillage qui engagent tout le projet** — `pnpm`, `uv`, `mypy` strict, Ruff, Vitest,
   Caddy, Compose base + surcouches — que les lots suivants hériteront ;
4. **les jetons visuels de `T10`**, relevés du prototype et mesurés contre WCAG 2.2 AA, **en sachant
   qu'ils sont une approximation de la charte réelle** (`QO-115`) ;
5. **la pose du tag `v0.1.0`** sur `main`.

---

## 7. Ce que tu ne valides PAS

| | |
|---|---|
Aucun écran métier | il n'en existe aucun ; ils arrivent au LOT 4 |
Aucune authentification | LOT 3. Aucun contournement n'existe non plus |
Aucune donnée de collaborateur | ni réelle, ni fictive, dans aucune base |
Aucun modèle de données métier | LOT 2. La migration `0001` est **volontairement vide** (`DEC-463`) |
La charte graphique définitive | `QO-115` — elle existe chez eXalt, nous ne l'avons pas |
La production temporaire locale | LOT 13, avec sauvegardes et supervision |
Les 29 contenus éditoriaux | statut **`à relire`**. Aucun n'est publiable |

---

## 8. Ce qui reste ouvert, et qu'il faut savoir avant de trancher

| Élément | Ce que cela veut dire concrètement |
|---|---|
| **`QO-115`** | La **charte graphique** et la **police officielle** ne sont pas dans le corpus. Les jetons livrés sont tracés à deux sources concordantes et mesurés accessibles, mais **une charte réelle pourra les contredire**. À instruire avant le LOT 4 |
| **`ROAD-RSK-034`** | Les **ports publiés** d'un environnement restent joignables depuis l'autre : Docker accepte le trafic vers un port publié avant d'appliquer son isolement. Le cahier §22.2 exige un réseau **distinct**, ce qui est acquis ; ce qui protège est le fait que **les secrets diffèrent**, et le contrôle en fait une exigence. **À réévaluer avant le LOT 13**, où la production locale portera des données réelles |
| **`ROAD-RSK-033`** | 23 avis `HIGH`/`CRITICAL` sans correctif dans `python:3.12-slim`. **Nos couches n'en ajoutent aucun.** À réexaminer, pas à archiver : `T10` vient de montrer qu'un tel résiduel peut se corriger du jour au lendemain |
| **`ROAD-RSK-026`** | iCloud a **matérialisé** son risque deux fois. `make icloud-verify` et `make caddy-recreate` sont les parades, et elles fonctionnent |
| `QO-111`, `QO-112` | Collation et extensions PostgreSQL — **à trancher au LOT 2**, avant la première table |
| `QO-113` | Conservation calendaire des journaux — LOT 13 |
| `QO-114` | **Tu n'as aucun droit d'administration sur cette machine.** `restic`, Uptime Kuma et les services au démarrage en réclament habituellement. À instruire avant le LOT 13 |
| 5 écarts ouverts | `ECART-005`, `012` à `015`, tous rattachés à un lot ultérieur |

---

## 9. Ce que la pose du tag déclenchera

**À savoir avant, pas après.**

1. **La fusion `develop` → `main` passe par une pull request.** `main` est protégée avec
   `enforce_admins` : aucun commit direct, y compris pour toi. *(Tu l'as déjà faite pour l'état
   actuel — PR #30, `be65b53`. Les documents de `T11` demanderont une seconde fusion.)*
2. **Le tag `v*` déclenchera `images.yml`** avec la **version exacte** `0.1.0`. Ce sera la **première
   publication d'une version non `develop`** dans GHCR — jusqu'ici seules les étiquettes
   `sha-<empreinte>` et `develop` existent.
3. **L'ordre est imposé par `DEC-428`** : fusion d'abord, tag ensuite, **sur `main`**.

```bash
git switch main && git pull --ff-only
git tag -a v0.1.0 -m "LOT 1 — socle local, CI et images. Porte G1 validee."
git push origin v0.1.0
```

**Retour arrière**, si le tag était posé par erreur :

```bash
git push --delete origin v0.1.0 && git tag -d v0.1.0
```

---

## 10. Trois points à traiter à la validation

1. **Le projet Docker tiers est arrêté depuis le 28/07/2026** et attend ta décision de le relancer :

   ```bash
   docker compose -p observatoire-ecom-studio start
   ```

2. **`DEC-440` n'autorise qu'un environnement à la fois.** `QO-085` a mesuré que deux tiennent
   ensemble — **836,6 Mio pour seize services, 10,5 %** du budget — mais **mesurer la simultanéité
   ne l'autorise pas**. Si tu veux changer cette règle, c'est une décision à tracer.
3. **L'epic `#1`** reste ouverte et sera refermée à la validation.

---

## 11. Décision demandée

☐ **La porte `G1` est validée**, le tag `v0.1.0` peut être posé, et le LOT 2 peut être ouvert.

☐ **La porte `G1` n'est pas validée** — préciser ce qui manque.

**Rappel de la règle qui ne se négocie pas :** aucun lot dépendant ne commence avant validation
explicite du précédent (`ROAD-003`, `ARB-BACK-003`). **Le LOT 2 n'est pas ouvert** tant que cette
case n'est pas cochée.
