# Compte rendu — sous-étape `T1` du LOT 1

**Exécutée le :** 27 et 28 juillet 2026
**Objet :** squelette du monorepo, outillage, versions épinglées
**Story :** `MVP-L01-US001`, issue [#2](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/2)
**Fondement :** [fiche du LOT 1](fiche-lot-1.md) §3 ; cahier des charges §15.3, §17.1, §23.5
**Décisions produites :** `DEC-451` à `DEC-456`
**Premier commit de code du projet.** Circuit branche + pull request en vigueur (`DEC-427`).

---

## 1. Ce qui a été livré

Les **sept répertoires** du cahier §15.3 existent et sont documentés : `apps/web`, `apps/api`,
`apps/worker`, `packages/ui`, `packages/contracts`, `infra`, `docs`. Chacun porte un `README.md`
indiquant son rôle, ses commandes, et **ce qui y arrive à quelle sous-étape**.

| Domaine | Livré |
|---|---|
| Outillage | `uv` 0.11.32 (empreinte SHA-256 vérifiée), `pnpm` 11.17.0 par `corepack` (épinglé avec empreinte d'intégrité), CPython 3.12.13 géré par `uv` |
| Workspaces | `pnpm-workspace.yaml` — 3 paquets JS ; `pyproject.toml` racine — workspace `uv` à 2 membres (`DEC-455`) |
| Versions épinglées | `.node-version` `24.16`, `.python-version` `3.12` (`DEC-443`), `engineStrict` actif |
| Qualité Python | Ruff (lint + format), **mypy strict** (`DEC-442`), pytest |
| Qualité TypeScript | ESLint flat config avec `jsx-a11y` et `react-hooks`, Prettier, `tsc --noEmit` strict (`DEC-451`) |
| Orchestration | `Makefile`, **15 cibles**, point d'entrée unique. Deviendra celui de la CI en `T6` |
| Atténuation iCloud | [`infra/scripts/exclure-icloud.sh`](../../infra/scripts/exclure-icloud.sh), `make icloud-exclude`, `make icloud-verify` (`DEC-453`) |

**Ce que `T1` n'a délibérément pas fait :** aucun `Dockerfile` (`T2`, `T7`), aucun fichier
Compose (`T2`), aucune application FastAPI ni migration Alembic (`T3`), aucune page de statut
(`T5`), aucun workflow GitHub Actions (`T6`), aucun token de design system ni contrat API
(`T10`), et `.env.example` non touché — `ECART-006` exige de le compléter « par les variables
réellement nécessaires », qui ne le seront qu'en `T2` et `T3`.

Les cinq bibliothèques du cahier §17.1 sans usage avant le LOT 4 — React Router, TanStack
Query, React Hook Form, Zod, Radix UI — **ne sont pas installées** (`DEC-456`).

---

## 2. Contrôles exécutés

Codes de sortie lus directement, **jamais à travers un tuyau** (leçon du défaut `T0-1`).

### 2.1 Témoins négatifs — 10 sur 10 concluants

Un défaut réel a été injecté dans chaque maillon, la cible `make` exécutée, son code de sortie
lu, puis le défaut retiré.

| Maillon | Défaut injecté | Code |
|---|---|---:|
| Ruff lint | import inutilisé | 2 |
| Ruff format | code désaligné | 2 |
| mypy strict | type de retour faux | 2 |
| pytest | assertion fausse | 2 |
| ESLint | variable inutilisée | 2 |
| Prettier | code désaligné | 2 |
| `tsc` strict | type incompatible | 2 |
| Vitest | attente fausse | 2 |
| `make tree` | répertoire absent | 2 |
| `make versions` | Node non conforme | 2 |

**Témoin positif :** `make check` repasse à 0 une fois les défauts retirés.

Trois contrôles supplémentaires ont été éprouvés de la même manière :

- **`engineStrict`** — `engines.node` porté à `>=99.0.0` : `pnpm install` échoue avec
  `ERR_PNPM_UNSUPPORTED_ENGINE`, code 1 ;
- **exclusion iCloud** — attribut retiré de deux répertoires : `make icloud-verify` échoue
  (code 2) ; `pnpm install` déclenche le `postinstall`, l'attribut est reposé, code 0 ;
- **empreinte SHA-256 de `uv`** — une archive volontairement altérée est rejetée.

### 2.2 Intégrité et hygiène

| Contrôle | Résultat | Témoin |
|---|---|---|
| Empreintes des 5 documents immuables | **5/5 conformes** | Empreinte bidon non trouvée dans le document de référence |
| Secrets dans les 48 fichiers indexés | **0 correspondance** sur 6 familles de motifs | Détecteur déclenché par un faux secret ; 9 `CHANGE_ME_` retrouvés dans `.env.example` |
| BOM | **0 fichier** | Détecteur reconnaît un BOM synthétique |
| Fins de ligne CRLF | **0 fichier** | — |
| Extensions interdites suivies par Git | **1**, le CSV explicitement fictif | Même filtre sur `.md` : 47 fichiers |
| Dépendances suivies par Git | **0 entrée** | Même filtre sur `package.json` : 4 entrées |

### 2.3 Empreinte disque — élément de réponse à `QO-085`

276 Mio et **13 252 fichiers** soustraits à iCloud dans le dépôt ; 338 Mio d'outillage hors
dépôt par construction. Détail dans le
[registre des questions ouvertes](registre-questions-ouvertes.md) §1.1.

---

## 3. Défauts détectés pendant `T1`

Même règle qu'au LOT 0 et qu'en `T0` : un défaut détecté est consigné, **y compris et surtout
quand c'est le contrôle qui était faux**.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T1-1` | La boucle de marquage iCloud itérait sur `$CIBLES`, non citée. **En `zsh`, une variable n'est pas découpée en mots** : la boucle a tourné **une seule fois** sur les huit noms concaténés, et `mkdir -p` a créé une arborescence au nom absurde. | **Le piège documenté en `CLAUDE.md` §7.2, commis malgré la lecture.** Détecté parce qu'une seule ligne « marque » s'est affichée pour huit cibles. | Résidu supprimé, boucle réécrite en `while IFS= read -r`, avec **comptage des itérations comparé à un attendu**. Le `Makefile` force `SHELL := /bin/bash` et le commente. |
| `T1-2` | Un `tests/__init__.py` avait été ajouté dans `apps/api` et `apps/worker` pour éviter une collision de noms de modules. Il en a créé une : deux paquets homonymes `tests`, que **mypy et pytest refusent tous les deux**. | Livrable faux, détecté par les outils eux-mêmes. | Les deux fichiers retirés : des basenames distincts suffisent. `DEC-455`. |
| `T1-3` | `store-dir` et `engine-strict` avaient été déclarés dans un `.npmrc`. **pnpm 11 ne lit plus ces clés depuis `.npmrc`** : `pnpm config get store-dir` renvoyait `undefined` et pnpm retombait sur son défaut macOS. | **Contrôle qui aurait menti.** Le défaut de pnpm se trouve hors iCloud : un contrôle vérifiant seulement « pas dans iCloud » aurait affiché « conforme » sur une base fausse. Détecté en comparant le chemin obtenu au chemin **déclaré**, et non à un simple critère de négation. | `.npmrc` supprimé, réglages portés dans `pnpm-workspace.yaml` où `${HOME}` s'expanse. Vérifié. |
| `T1-4` | `reactHooks.configs['recommended-latest']` est encore au format `eslintrc`, refusé par ESLint 10. | Livrable faux, détecté au premier lancement. | `reactHooks.configs.flat.recommended`, après inspection des exports réels du greffon. |
| `T1-5` | `vite.config.ts` importait `defineConfig` depuis `vite`, dont la signature ne connaît pas la clé `test` avec Vitest 4. | Livrable faux, détecté par `tsc --noEmit`. | Import depuis `vitest/config`. |
| `T1-6` | `ruff format --check` annonçait « **45 fichiers** » là où le dépôt ne contient que 4 fichiers Python. | **Résultat surprenant, diagnostiqué au lieu d'être accepté.** Ruff formate les blocs de code embarqués dans le Markdown : il traitait les 41 documents, dont les cinq immuables. | `*.md` exclu de Ruff **et** de Prettier. Voir `DEC-454` et `ROAD-RSK-029` ci-dessous. |

### 3.1 Le défaut le plus instructif : `T1-6`

En neutralisant l'exclusion, la mesure est sans ambiguïté : **Prettier réécrivait les cinq
documents de cadrage immuables**, ajoutant **54 661 octets** au seul cahier des charges — de
251 489 à 306 150 octets, soit **+21,7 %**.

L'intégrité de ces cinq fichiers est prouvée par empreinte SHA-256 dans
[`integrite-et-conformite-documents.md`](integrite-et-conformite-documents.md), et cette preuve
est un élément de la porte `G0`. Un `make format` lancé sans y penser aurait invalidé les cinq
empreintes en un commit, **sans qu'aucun contrôle existant ne le signale**, le contenu restant
sémantiquement identique.

Le risque `ROAD-RSK-029` en tire la conséquence qui déborde `T1` : l'exclusion protège des
outils d'aujourd'hui, pas de ceux de demain. **Recommandation pour `T6`** — ajouter à la CI un
contrôle qui recalcule les cinq empreintes et échoue si l'une diffère. C'est le seul garde-fou
qui ne dépende pas de la configuration d'un outil particulier.

---

## 4. Incident iCloud — `ROAD-RSK-026` s'est matérialisé

**Ce risque n'est plus théorique.** Chronologie établie sur les horodatages d'inode :

| Moment | Fait |
|---|---|
| 27/07 **17:21:19** | Création d'un répertoire **`node_modules 2`** — copie de conflit iCloud, 178 Mio, 11 066 fichiers — quelques minutes après la première pose de l'attribut d'exclusion |
| 27/07 **23:30:28** et **23:30:30** | Les deux répertoires subissent un changement de métadonnées d'inode. **Aucune action de session ne l'explique** |
| 28/07 au matin | La **copie** porte l'attribut d'exclusion ; l'**original** a perdu la totalité de ses attributs étendus |

Effet mesuré : `prettier --check .` passait de moins d'une seconde à **179 secondes**, et
échouait, en parcourant les 11 066 fichiers du duplicata.

**Trois enseignements.**

1. L'attribut d'exclusion **n'est pas durable** : il a disparu en moins de sept heures. Le
   poser ne suffit pas, il faut le vérifier.
2. Sa pose sur un répertoire qu'iCloud suivait déjà **a coïncidé** avec la duplication. Le
   mécanisme exact n'est pas établi et n'est pas affirmé ici — seule la corrélation temporelle
   est un fait.
3. C'est **`make icloud-verify` qui a détecté l'anomalie**, pas une inspection manuelle. Un
   vérificateur qui échoue est ce qui distingue une atténuation d'une intention.

**Atténuations ajoutées.** Le nom d'une copie de conflit iCloud est le nom d'origine suivi
d'une espace et d'un chiffre. Le motif `* [0-9]` est désormais exclu dans `.gitignore`,
`.prettierignore`, `[tool.ruff] extend-exclude` et `eslint.config.js`, et **`make icloud-verify`
échoue si une telle copie existe**.

**Arbitrage de Jonathan, rendu le 28/07/2026 sur présentation des mesures** — `DEC-457`. Trois
issues lui étaient soumises : maintenir le marquage avec vérificateur, sortir physiquement
`node_modules` et `.venv` de l'arborescence synchronisée, ou rouvrir `DEC-418`.

**Retenu : maintenir `DEC-453` en l'état**, marquage reposé automatiquement par le
`postinstall` et contrôlé par `make icloud-verify`, exécuté en début de session et intégré à
`make check`. `DEC-418` n'est pas rouverte. Le risque résiduel est **accepté en connaissance
de cause** : une nouvelle copie de conflit peut réapparaître ; le vérificateur la détectera,
il ne l'empêchera pas.

La copie `node_modules 2` a été **supprimée** le 28/07/2026 après cet arbitrage — duplicata
figé, non suivi par Git, régénérable par `pnpm install`. Les preuves de l'incident restent
intégralement consignées ici et dans `ROAD-RSK-026`. `make check` est depuis **vert sur la
totalité de ses maillons, code 0**.

---

## 5. Écarts documentaires corrigés

Deux écarts relevés à la prise en charge, corrigés et clos dans la même pull request, sur
arbitrage de Jonathan.

| ID | Constat | Effet |
|---|---|---|
| `ECART-017` | La fiche du LOT 1 portait toujours « **LE LOT 1 N'EST PAS OUVERT** » après `DEC-450`, en contradiction frontale avec `docs/README.md` §8. L'index bornait par ailleurs les décisions de `T0` à `DEC-439`–`DEC-447` au lieu de `DEC-449` | Faible sur le travail, réel sur la confiance dans le corpus : la fiche est le premier document que lit un agent qui prend le lot en charge |
| `ECART-018` | La fiche annonçait « **8 contrôles** du cahier §23.1 » à deux endroits. Le cahier en énumère **11**, la roadmap et le backlog **7**. Aucune source ne donne 8 | **Structurant pour `T6`** : tests API, tests frontend et construction des images n'apparaissaient dans aucun décompte inférieur et auraient pu être omis. Même classe exactement que le défaut `B-5` de `T0` |

Les onze contrôles du cahier §23.1 sont désormais **énumérés** dans la fiche, et non seulement
comptés : c'est l'énumération qui empêche une omission.

---

## 6. État à la sortie de `T1`

| | |
|---|---|
| Sous-étape | **`T1` terminée.** Story `MVP-L01-US001` prête pour validation |
| Décisions ajoutées | `DEC-451` à `DEC-457`. Prochaine libre : **`DEC-458`** |
| Écarts | `ECART-017` et `ECART-018` ouverts **et clos**. Prochain libre : **`ECART-019`** |
| Risques | `ROAD-RSK-029` ouvert. `ROAD-RSK-026` **matérialisé**, atténuation à revoir. Prochain libre : **`ROAD-RSK-030`** |
| Questions | `QO-085` complétée du volet disque, **non close**. Prochaine libre : `QO-111` |
| Dépendances | Aucune ajoutée. Prochaine libre : `DEP-018` |
| `make check` | **Vert en totalité, code 0**, y compris `icloud-verify`, après suppression de la copie de conflit (`DEC-457`) |
| Sous-étape suivante | **`T2`** — Compose développement, 8 services sains, story `MVP-L01-US002`, issue `#3` |

**Point d'attention pour `T2`.** Le projet Docker tiers `observatoire-ecom-studio` est
**toujours actif** : 5 conteneurs, **1,92 Gio** mesurés, dont 1,774 Gio pour son seul worker,
sur les 7,75 Gio alloués à Docker. `DEC-440` prévoit son arrêt pendant le LOT 1 —
**c'est une action à confirmer par Jonathan, le projet ne nous appartient pas.**
