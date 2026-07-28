# `apps/web` — frontend React et Vite

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §17.1, §17.2

---

## 1. État actuel

**La page de statut est livrée** (`T5`, story `MVP-L01-US002`). Le serveur Vite
sert `app.onboarding.localhost` à travers Caddy.

```text
index.html                  point d'entree, lang="fr"
src/main.tsx                montage React. Leve si l'element hote est absent
src/App.tsx                 racine. Aucun routeur : DEC-456, une seule page
src/FrontiereErreur.tsx     error boundary du cahier §17.4
src/pages/PageStatut.tsx    les CINQ etats
src/api/sante.ts            client des 2 endpoints. 200 ET 503 exploitables
src/styles.css              mise en forme NEUTRE, aucune couleur de marque
```

**Cinq états**, là où la fiche §6 en exige trois : chargement, nominal,
**dégradé**, erreur, hors connexion. Le dégradé est distinct de l'erreur parce
qu'un **503** de `/health/ready` porte la même forme JSON qu'un 200 : le traiter
comme une panne réseau jetterait le diagnostic au moment où il devient utile.

**Aucune identité visuelle n'est inventée** : la charte relève de `DEP-006` et
les tokens de `T10`. Poser ici une palette approximative créerait la dette que
`MVP-L01-US007` cherche justement à éviter.

## 2. Ce qui arrive, et quand

| Contenu | Sous-étape | Story |
|---|---|---|
| ~~Point d'entrée et page de statut~~ ✅ **fait** | `T5` | `MVP-L01-US002` |
| Image d'exécution multiarchitecture, **cible de production** — aujourd'hui l'image sert le serveur de développement (`ROAD-RSK-031`) et pèse 1,02 Gio (`ROAD-RSK-030`) | `T7` | `MVP-L01-US006` |
| Tokens et composants de base | `T10` → [`packages/ui`](../../packages/ui/README.md) | `MVP-L01-US007` |
| Audit d'accessibilité outillé par `axe` | `T10`, audit au LOT 12 | — |
| React Router, TanStack Query, React Hook Form, Zod, Radix UI | **LOT 4 et suivants** | — |

> Ces cinq dernières bibliothèques figurent bien au cahier §17.1, mais aucune
> n'a d'usage avant le LOT 4 (`DEC-456`). Les installer maintenant ajouterait une
> surface d'audit de dépendances sans contrepartie. **Testing Library**, elle, est
> installée : la fiche §6 l'exige pour les tests de cette page (`DEC-471`).

## 3. Commandes

```bash
make typecheck   # tsc --noEmit, TypeScript strict
make test        # Vitest — 25 tests sur cette page
make web-check   # la page vue comme un navigateur la voit, a travers Caddy
```

Pour n'agir que sur cet espace de travail :

```bash
pnpm --filter @onboarding/web run test
```

**Il n'y a pas de bind mount du code source** : `DEC-447` reste intact. Une
modification de `src/` exige donc `make up`, qui reconstruit l'image.

## 3.1 Réglages de `vite.config.ts` qui ne sont pas facultatifs

| Réglage | Sans lui |
|---|---|
| `server.host: '0.0.0.0'` | Vite écoute sur la boucle locale du conteneur : **personne** ne le joint, pas même Caddy |
| `server.strictPort: true` | Vite glisse silencieusement sur un autre port, que Caddy ne mandate pas → 502 sans cause visible |
| `server.allowedHosts` | Vite 8 refuse l'en-tête `Host: app.onboarding.localhost` : « Blocked request » |

## 4. TypeScript strict

L'exigence du cahier §17.1 est portée par
[`tsconfig.base.json`](../../tsconfig.base.json), dont ce paquet hérite :
`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`,
`verbatimModuleSyntax`, `forceConsistentCasingInFileNames`.

## 5. Versions

Node **24 LTS** (`DEC-443`), pnpm épinglé par le champ `packageManager` de la
racine.
