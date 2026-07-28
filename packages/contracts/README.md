# `packages/contracts` — contrat API partagé

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §15.3, §18.1

---

## 1. État actuel

**Coquille d'espace de travail.** `src/index.ts` n'exporte qu'une constante de
nom. **Aucun type métier** n'y est déclaré.

## 2. Ce qui arrive, et quand

| Contenu | Sous-étape | Story |
|---|---|---|
| Génération du contrat depuis le schéma OpenAPI de l'API, et partage | `T10` | `MVP-L01-US007` (**`P1`**) |
| Types des ressources métier | **LOT 2 et suivants** | — |

## 3. Contrainte à ne pas enfreindre

Le modèle de données appartient au LOT 2, qui n'est pas ouvert. Déclarer ici un
type `Person`, `Entity` ou `OnboardingTask` serait une anticipation à refuser,
même si le type est « évident » : le modèle validé
([`MODELE_DONNEES_EXALT.md`](../../docs/architecture/MODELE_DONNEES_EXALT.md))
fait foi, et il est immuable.

Le contrat est **généré**, jamais transcrit à la main : c'est la seule manière
de garantir qu'il ne diverge pas de l'API, qui est l'autorité finale
(matrice §2.6, `RIGHTS-015`).

## 4. Commandes

```bash
make typecheck
make test
```
