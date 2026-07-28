# Compte rendu — sous-étape `T3` du LOT 1

**Exécutée le :** 28 juillet 2026
**Objet :** API FastAPI, trois healthchecks, migration Alembic initiale
**Story :** `MVP-L01-US003`, issue [#4](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/4)
**Fondement :** [fiche du LOT 1](fiche-lot-1.md) §3 et §5 ; cahier §18.1, §18.3, §18.7, §20.3, §16.2, §16.4
**Décisions produites :** `DEC-462` à `DEC-465`

---

## 1. Critère d'acceptation, et ce qui le prouve

> « Chaque endpoint retourne un statut explicite ; readiness vérifie les dépendances
> nécessaires ; la version correspond au build. » — backlog, littéral

| Volet | Preuve | Code |
|---|---|---:|
| Trois endpoints, statut explicite | `make api-check` interroge les trois, lit le code HTTP **et** le contenu | **0** |
| `ready` vérifie réellement les dépendances | **Redis arrêté pour de vrai** → `ready` répond **503**, `redis indisponible`, motif `ConnectionError` ; PostgreSQL et MinIO restent `disponible` | **503 obtenu** |
| La version correspond au build | `/health/version` lit `APP_VERSION` et `APP_REVISION` de la configuration, injectées à la construction en `T7` | **0** |
| Migration sur base vide, rejeu, `downgrade` | 8 tests d'intégration sur **PostgreSQL réel**, base dédiée créée et détruite | **0** |

```text
/health/live      HTTP 200  {"statut": "vivant"}
/health/ready     HTTP 200  3 dependances sondees
                  postgresql disponible 0 ms · redis disponible 1 ms · minio disponible 2 ms
/health/version   HTTP 200  {"version": "0.0.0-dev", "revision": "inconnue",
                             "environnement": "development"}
/api/v1/          HTTP 200  {"api": "onboarding-digital", "version_contrat": "v1"}
```

Tout cela **à travers Caddy en HTTPS**, sur `api.onboarding.localhost`, avec l'identifiant de
corrélation propagé de bout en bout.

---

## 2. Ce qui a été livré

| Emplacement | Contenu |
|---|---|
| `app/configuration/settings.py` | Configuration et **les 11 garde-fous** de démarrage |
| `app/shared/correlation.py` | Identifiant de corrélation par requête, en `ContextVar` |
| `app/shared/errors.py` | Format d'erreur **unique** du cahier §18.3, cinq champs toujours présents |
| `app/shared/database.py` | Moteur SQLAlchemy. **Aucun `Base` métier, aucun `create_all`** |
| `app/health/dependances.py` | Sondes réelles : `SELECT 1`, `PING`, `head_bucket` |
| `app/health/routes.py` | Les trois endpoints du cahier §18.7 |
| `app/main.py` | Application FastAPI, préfixe `/api/v1`, doc interactive fermée en production |
| `alembic/`, `versions/0001_initial.py` | Chaîne de migration, revision `0001` |
| `worker/main.py` | Dramatiq, **les 7 files** du cahier §16.4 déclarées |
| `infra/scripts/verifier-sante.sh` | Contrôle des trois endpoints, avec comptage |
| `Makefile` | 6 cibles : `migrate`, `migrate-status`, `api-check`, `test-unit`, `test-integration` |
| `.env.example` | **v1.0** — `APP_REVISION` ajoutée. **Clôt `ECART-006`** |

**61 tests** : 53 unitaires, 8 d'intégration sur services réels.

### Ce que `T3` n'a pas fait, et ne devait pas faire

**Aucune table métier**, aucun modèle SQLAlchemy métier, **aucune authentification, même
partielle, même de test**, aucun mécanisme de contournement. Aucune route métier. La
journalisation JSON corrélée est en `T4`, la page de statut en `T5`.

---

## 3. La migration initiale est vide, et c'est une décision

La fiche §5 annonçait « les extensions PostgreSQL strictement nécessaires ». **Aucun document du
corpus n'en nomme une seule** : zéro occurrence de `pg_trgm`, `unaccent`, `citext`, `pgcrypto`,
`uuid-ossp` dans le cahier **comme** dans le modèle, témoin positif du même filtre — `SQLAlchemy`
y remonte quatre fois.

Deux constats ont achevé de trancher :

- le modèle §3 impose des clés primaires UUID, mais **`gen_random_uuid()` est intégré à
  PostgreSQL depuis la version 13** : aucune extension n'est requise ;
- le modèle §26.1 dit que la recherche tolérante « **pourra** » utiliser une colonne
  dénormalisée **ou** un index adapté. C'est ouvert, et ces index arrivent à la migration **16**
  de l'ordre recommandé, pas à la première.

La roadmap autorise littéralement « une migration Alembic **vide ou initiale** ». Choisir une
liste aurait été inventer une décision, et une extension activée se retire moins facilement
qu'elle ne s'ajoute. **Arbitrage de Jonathan (`DEC-463`) : migration vide, liste établie au
LOT 2 avec les tables et les index.** Question ouverte `QO-112`.

Ce que la migration prouve malgré tout, et c'est ce que le lot demande : la chaîne fonctionne.

| Contrôle du modèle §28 | Résultat |
|---|---|
| Application sur une base vide | `alembic_version` passe de absent à `0001` |
| Rejeu depuis l'état précédent | Second `upgrade head` sans effet, revision inchangée |
| `downgrade` puis `upgrade` compatible | `0001` → `base` → `0001` |
| **Aucune création automatique de table** | Démarrer l'API sur une base vide sans migration laisse **0 table** |
| **Aucune table métier** | `0 table` hors `alembic_version`, contrôlé par un test dédié |
| PostgreSQL réel, jamais SQLite | Base `onboarding_test_migration` créée et détruite par les tests |

---

## 4. Les onze garde-fous, et comment ils sont éprouvés

**Chaque garde-fou a deux tests** : un qui l'enfreint et vérifie le refus, un témoin qui
respecte la règle et vérifie le laissez-passer. Un garde-fou qui refuse tout serait aussi
inutile qu'un garde-fou qui accepte tout.

Les **sept contrôles de production** sont éprouvés en **forçant `APP_ENV=production`** — sans
cela, sept tests passeraient sans rien vérifier. Un test supplémentaire prouve la réciproque :
hors production, ces sept valeurs sont **admises**, faute de quoi le développement local serait
impossible, Mailpit et la documentation interactive y étant indispensables.

Deux tests portent sur la confidentialité :

- **aucun message ne divulgue une valeur** — la politique §6 l'exige ; un message de
  configuration finit dans un journal ou une capture d'écran ;
- **`/health/ready` ne divulgue aucun secret** — il est interrogeable sans authentification, et
  le motif remonté est le **type** de l'exception, jamais son message, qui peut contenir une URL
  avec mot de passe.

### Portée du garde-fou « aucun `CHANGE_ME` résiduel »

La politique §6.1 l'applique à tous les environnements. Or `IMPORT_SOURCE_RETENTION_DAYS`
(`QO-100`, bloquante, LOT 9) et `UPTIME_KUMA_PUSH_URL` (LOT 13) restent volontairement en
`CHANGE_ME` — appliqué littéralement, le garde-fou empêcherait l'API de démarrer aujourd'hui.

**`DEC-464` :** le garde-fou porte sur les variables que l'API **déclare**. Ces deux-là ne sont
utilisées par aucun code et ne figurent donc pas dans son modèle de configuration. Le jour où le
LOT 9 ajoutera la première, `QO-100` devra être tranchée — c'est précisément l'effet recherché.

---

## 5. Défauts détectés pendant `T3`

Six défauts. **Quatre étaient dans mes propres tests ou mon montage de test**, pas dans le
livrable — ce qui est la forme la plus insidieuse : on croit avoir prouvé.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T3-1` | `app/main.py` se terminait par `application = creer_application()`. Importer le module lisait donc l'environnement, et la simple **collecte** des tests échouait faute de variables | **Livrable non testable.** Un module qui lit son environnement à l'import ne se teste pas | Passage à une fabrique, `uvicorn --factory`. Le refus de démarrer du cahier §20.3 est préservé : uvicorn appelle la fabrique et l'exception remonte |
| `T3-2` | Les routes de santé lisaient la configuration par un cache global : impossible de tester `ready` sans arrêter des services réels | Livrable non testable | Configuration portée par `app.state`. Le test « `ready` répond 503 » se fait désormais **sans arrêter aucun service**, en pointant vers des ports fermés |
| `T3-3` | `test_3_un_entier_illisible` appelait `Parametres(...)` directement. Il attendait `ConfigurationInvalide` et recevait la `ValidationError` brute de Pydantic | **Test faux.** Il court-circuitait `charger_parametres()`, le point d'entrée réel, qui traduit l'une en l'autre | Test réécrit sur le point d'entrée |
| `T3-4` | `test_aucun_message_ne_divulgue_une_valeur` cherchait la chaîne `court`, qui est un fragment du message légitime « plus **court**e que 32 caracteres » | **Test faux**, échouant sur son propre libellé et non sur une fuite | Valeurs témoins distinctives, impossibles à confondre avec un libellé |
| `T3-5` | `make migrate` répondait « No `script_location` key found » : `alembic.ini` réside dans `apps/api`, et la commande partait de `/app` | Livrable incomplet | `--workdir /app/apps/api`, et le motif commenté |
| `T3-6` | Mon témoin négatif affichait « Redis arrêté » puis `ready` à **200**. La variable `DC` non citée avait été découpée sur l'espace du chemin : `code=127`, **Redis n'avait jamais été arrêté** | **Montage de test faux.** J'aurais conclu que la sonde ne détecte rien, alors qu'elle n'avait rien à détecter. **Même piège que `T2-3`**, dans un shell ad hoc cette fois | Fonction shell avec chemins cités. Témoin refait : `ready` répond bien **503** |

### 5.1 Ce que ces six défauts confirment

`T3-6` est le plus instructif : c'est la **troisième fois** dans ce lot que le chemin
`~/Library/Mobile Documents/`, avec son espace, casse un contrôle — après `T2-3` dans le
`Makefile` et le montage `eval` des scripts de `T2`. Le code de sortie `127` était visible et
c'est lui qui a permis de le voir.

Les quatre premiers défauts disent autre chose : **un livrable difficile à tester est un
livrable qu'on finit par ne pas tester**. Les deux corrections — fabrique et `app.state` — ont
été faites pour rendre les tests possibles, et elles ont produit un meilleur code : l'API ne lit
plus son environnement à l'import, et sa configuration est explicite.

---

## 6. État à la sortie de `T3`

| | |
|---|---|
| Sous-étape | **`T3` terminée.** Story `MVP-L01-US003` prête pour validation |
| Décisions | `DEC-462` à `DEC-465`. Prochaine libre : **`DEC-466`** |
| Écarts | **`ECART-006` clos** — `.env.example` en v1.0. Prochain libre : `ECART-020` |
| Questions | **`QO-112` ouverte** — liste des extensions PostgreSQL, au LOT 2. Prochaine libre : `QO-113` |
| Risques | Aucun ouvert. Prochain libre : `ROAD-RSK-031` |
| Tests | **61** — 53 unitaires, 8 d'intégration sur services réels |
| `make check` | Vert, code 0 |
| `make stack-check` · `api-check` | Vert, code 0 |
| Migration appliquée | Revision `0001`, **0 table métier** |
| Sous-étape suivante | **`T4`** — journalisation JSON corrélée, story `MVP-L01-US004`, issue `#5` |

**Ce qui attend `T4`.** L'identifiant de corrélation existe et traverse Caddy, mais **il n'est
pas encore écrit dans les journaux** : `app/shared/correlation.py` fournit le porteur, `T4`
branche la journalisation JSON qui le consomme, côté API **et** côté worker.

**Ce qui attend toujours Jonathan.** La racine de l'autorité interne de Caddy n'est pas
approuvée dans le trousseau macOS. Les contrôles ci-dessus utilisent `curl -k` : le certificat
est bien celui de Caddy, mais un client strict le refuse encore. C'est son action, elle demande
son mot de passe.
