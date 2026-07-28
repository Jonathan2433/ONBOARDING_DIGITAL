# `packages/ui` — design system eXalt

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §13.1 à §13.3, §14

---

## 1. État actuel

**Coquille d'espace de travail.** `src/index.ts` n'exporte qu'une constante de
nom. Aucun token, aucun composant, aucune couleur.

## 2. Ce qui arrive, et quand

| Contenu | Sous-étape | Story |
|---|---|---|
| Tokens de couleur, typographie, espacement ; composants de base | `T10` | `MVP-L01-US007` (**`P1`**) |

`MVP-L01-US007` est la **seule story `P1`** du lot : c'est la seule qui puisse
faire l'objet d'un report arbitré sans empêcher la porte `G1`.

## 3. Contrainte à ne pas enfreindre

Backlog, critère d'acceptation littéral : les tokens et composants sont
initialisés « **sans dépendance visuelle arbitraire** ». L'identité visuelle
relève du cahier §13.1 et de Léa, pas d'un choix d'implémentation.

L'accessibilité (cahier §14) est une exigence dure, auditée au LOT 12 :
`eslint-plugin-jsx-a11y` est actif sur tout fichier `.jsx` ou `.tsx` de ce
paquet (`DEC-451`).

## 4. Commandes

```bash
make typecheck
make test
```
