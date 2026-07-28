# `apps/web` — frontend React et Vite

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §17.1, §17.2

---

## 1. État actuel

**Outillage seul.** `src/` ne contient qu'un module de version et son test.
Il n'y a **ni `index.html`, ni `main.tsx`, ni composant** : ils appartiennent à
`T5`. Les scripts `dev` et `build` ne sont donc pas encore déclarés — mieux vaut
pas de commande qu'une commande documentée qui échoue.

## 2. Ce qui arrive, et quand

| Contenu | Sous-étape | Story |
|---|---|---|
| Point d'entrée, `index.html`, page de statut consommant les 3 healthchecks | `T5` | `MVP-L01-US002`, `US003` |
| Service `web` de la stack Docker, `Dockerfile` | `T2`, `T7` | `MVP-L01-US002`, `US006` |
| Tokens et composants de base | `T10` → [`packages/ui`](../../packages/ui/README.md) | `MVP-L01-US007` |
| React Router, TanStack Query, React Hook Form, Zod, Radix UI | **LOT 4 et suivants** | — |

> Ces quatre dernières bibliothèques figurent bien au cahier §17.1, mais aucune
> n'a d'usage avant le LOT 4. Les installer maintenant ajouterait une surface
> d'audit de dépendances sans contrepartie.

## 3. Commandes

```bash
make typecheck   # tsc --noEmit, TypeScript strict
make test        # Vitest
```

Pour n'agir que sur cet espace de travail :

```bash
pnpm --filter @onboarding/web run test
```

## 4. TypeScript strict

L'exigence du cahier §17.1 est portée par
[`tsconfig.base.json`](../../tsconfig.base.json), dont ce paquet hérite :
`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`,
`verbatimModuleSyntax`, `forceConsistentCasingInFileNames`.

## 5. Versions

Node **24 LTS** (`DEC-443`), pnpm épinglé par le champ `packageManager` de la
racine.
