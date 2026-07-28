# `apps/api` — API FastAPI

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Fondement :** cahier des charges §15.1, §16.1, §16.2, §18

---

## 1. État actuel

**L'API démarre et répond** depuis `T3`. Elle expose les trois endpoints de santé du cahier
§18.7, valide sa configuration au démarrage par **11 garde-fous**, porte le format d'erreur
unique du §18.3 avec identifiant de corrélation, et sa migration `0001_initial` s'applique.

**Aucune route métier, aucune table, aucune authentification.**

```bash
make migrate     # appliquer la migration
make api-check   # interroger /health/live, /health/ready et /health/version
```

| Endpoint | Ce qu'il fait |
|---|---|
| `/health/live` | Vivacité du processus. **Ne sonde aucune dépendance**, volontairement |
| `/health/ready` | Sonde réellement PostgreSQL, Redis et MinIO. **503** si l'une manque |
| `/health/version` | Version et empreinte de commit, injectées à la construction en `T7` |
| `/api/v1/` | Racine du contrat versionné, vide au LOT 1 |

## 2. Ce qui arrive, et quand

| Contenu | Sous-étape | Story |
|---|---|---|
| ~~Application FastAPI, configuration, **11 garde-fous**~~ | ✅ `T3` | `MVP-L01-US003` |
| ~~Endpoints `live`, `ready`, `version` (cahier §18.7)~~ | ✅ `T3` | `MVP-L01-US003` |
| ~~Migration `0001_initial`~~ — **vide**, voir `DEC-463` et `QO-112` | ✅ `T3` | `MVP-L01-US003` |
| Journalisation JSON consommant le `correlation_id` (cahier §28.1) | `T4` | `MVP-L01-US004` |
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
