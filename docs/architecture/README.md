# Documentation d'architecture

Ce dossier contient le modèle de données validé et les contrats techniques produits par le
projet.

**Responsable :** Jonathan, pour l'architecture, les choix techniques, la sécurité, les
sauvegardes et le déploiement.

---

## 1. Documents validés

| Document | Version | Statut | Date |
|---|---|---|---|
| [MODELE_DONNEES_EXALT.md](MODELE_DONNEES_EXALT.md) | 1.0 | Validé par Jonathan | 25 juillet 2026 |

Ce fichier est **immuable** en l'état. Toute évolution structurante doit être enregistrée
comme une nouvelle décision et ne doit pas écraser silencieusement les règles validées
(modèle de données, section 33).

---

## 2. Ce que fixe le modèle de données

Entrée de référence : matrice des rôles et permissions v1.1.

Cible retenue : **monolithe modulaire** utilisant PostgreSQL comme source de vérité.

Principes structurants :

| Principe | Règle |
|---|---|
| Identité globale, contexte local | Une personne existe une seule fois dans `person` ; ses données locales sont portées par `entity_membership` |
| Une seule entité principale active | Pas de chevauchement temporel entre appartenances principales |
| Historisation plutôt qu'écrasement | Une modification clôture la relation active et en crée une nouvelle |
| Archivage fonctionnel | `archived_at` et `archived_by` ; la suppression physique est exceptionnelle |
| Refus par défaut et isolation | Toute table locale porte un `entity_id` non nul ; les références croisées entre entités sont refusées |
| Source de vérité PostgreSQL | Redis ne stocke aucune donnée métier durable ; MinIO stocke les fichiers, PostgreSQL les métadonnées |
| Transactions et effets externes | L'action métier, l'audit et l'outbox sont écrits dans la même transaction |

Contient 18 décisions `DATA-001` à `DATA-018`, 5 arbitrages `ARB-DATA-001` à `-005`, 25
contrôles de recette du modèle, et l'ordre recommandé des 17 migrations initiales.

Conventions techniques imposées : clé primaire UUID immuable, horodatage `timestamptz` en
UTC, nommage SQL en `snake_case`, e-mail stocké en version originale et normalisée unique,
concurrence optimiste par colonne `version`, périodes de validité `starts_at` / `ends_at`,
fichiers référencés par `object_key` MinIO et **jamais** en Base64, `jsonb` réservé aux
métadonnées non structurantes.

---

## 3. Documents à produire dans ce dossier

| Document | Sous-étape | Story |
|---|---|---|
| `donnees/schema-csv-collaborateurs.md` | S6 | `MVP-L00-US004` |
| `donnees/codes-erreurs-import.md` | S6 | `MVP-L00-US004` |
| `donnees/listes-controlees.md` | S6 | `MVP-L00-US004` |
| `donnees/exemples/collaborateurs-exemple-fictif.csv` | S6 | `MVP-L00-US004` |
| `donnees/criteres-qualite-import.md` | S6 | `MVP-L00-US004` |

Le fichier d'exemple sera **exclusivement fictif**. Il constitue la seule exception à
l'interdiction de versionner des fichiers `.csv`, explicitement prévue dans
[`.gitignore`](../../.gitignore).

---

## 4. Ce qui n'appartient pas à ce dossier au LOT 0

Les modèles SQLAlchemy, les schémas Pydantic, les migrations Alembic, les routes et services
FastAPI et les tests d'intégrité appartiennent au **LOT 2** et aux suivants. Le LOT 0 ne
produit aucun code et aucune migration.

Les décisions d'architecture prises en cours de réalisation seront consignées dans
[`docs/decisions/`](../decisions/), pas ici.
