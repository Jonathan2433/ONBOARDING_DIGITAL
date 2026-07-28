# `apps/api` — API FastAPI

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §15.1, §16.1, §16.2, §18

---

## 1. État actuel

**Squelette et outillage seuls.** Ce paquet ne contient aucun code applicatif.
`app/__init__.py` n'expose qu'une version.

## 2. Ce qui arrive, et quand

| Contenu | Sous-étape | Story |
|---|---|---|
| Application FastAPI, lecture et validation de la configuration, **11 garde-fous de démarrage** | `T3` | `MVP-L01-US003` |
| Endpoints de santé `live`, `ready`, `version` (cahier §18.7) | `T3` | `MVP-L01-US003` |
| Migration Alembic `0001_initial` — **extensions PostgreSQL seules** | `T3` | `MVP-L01-US003` |
| Journalisation JSON avec `correlation_id` (cahier §28.1) | `T4` | `MVP-L01-US004` |
| `Dockerfile` multiarchitecture | `T2`, `T7` | `MVP-L01-US002`, `US006` |
| Modules métier de `app/` (cahier §16.1) | **LOT 2 et suivants** | — |

**Aucune table métier, aucun modèle SQLAlchemy métier, aucune authentification**
ne relève du LOT 1 : voir [`fiche-lot-1.md`](../../docs/operations/fiche-lot-1.md) §11.

## 3. Commandes

Tout passe par le `Makefile` de la racine. Ce paquet est un membre du workspace
`uv` déclaré dans le [`pyproject.toml`](../../pyproject.toml) racine, qui porte
aussi la configuration de Ruff, de mypy et de pytest.

```bash
make install     # uv sync + pnpm install
make lint        # Ruff
make typecheck   # mypy strict (DEC-442)
make test        # pytest
```

Pour n'agir que sur ce paquet :

```bash
uv run pytest apps/api/tests
```

## 4. Versions

Python **3.12** (`DEC-443`), géré par `uv` — le Python système 3.9.6 de macOS
n'est jamais utilisé.
