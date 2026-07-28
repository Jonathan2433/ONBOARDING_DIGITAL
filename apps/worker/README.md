# `apps/worker` — worker Dramatiq

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §15.1, §16.4

---

## 1. État actuel

**Squelette et outillage seuls.** Ce paquet ne contient aucun code applicatif.

## 2. Ce qui arrive, et quand

| Contenu | Sous-étape | Story |
|---|---|---|
| Démarrage Dramatiq, déclaration des **7 files** validées | `T3` | `MVP-L01-US003` |
| Journalisation JSON avec `correlation_id` en job | `T4` | `MVP-L01-US004` |
| `Dockerfile` multiarchitecture | `T2`, `T7` | `MVP-L01-US002`, `US006` |
| Persistance des jobs en PostgreSQL, outbox transactionnelle, idempotence, tâches planifiées | **LOT 11** | `MVP-L11-US001`, `US002` |

Les 7 files du cahier §16.4 : `default`, `emails`, `imports`, `media`, `exports`,
`maintenance`, `security`.

> **Amorcer n'est pas implémenter.** Au LOT 1, le worker doit démarrer et être
> sain. Il ne traite aucun job réel.

## 3. Commandes

Tout passe par le `Makefile` de la racine. Ce paquet est un membre du workspace
`uv` déclaré dans le [`pyproject.toml`](../../pyproject.toml) racine.

```bash
make install
make lint
make typecheck
make test
```

## 4. Versions

Python **3.12** (`DEC-443`), géré par `uv`.
