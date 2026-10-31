# Compte rendu — `T1` du LOT 11 : le socle asynchrone

**Sous-étape :** la première du lot — `async_job`, `outbox_message`, le cycle de vie idempotent
d'un job, l'outbox transactionnelle, l'interface fournisseur d'e-mail
**Date :** 30 octobre 2026
**Décision :** `DEC-676`
**Stories :** `MVP-L11-US001`, `US002`, `US003`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 11**, ouvert le 30/10/2026 (`DEC-674`), **sept** sous-étapes |
| Faite | **`T1`** |
| Restent | `T2` à `T7` |
| Issues | aucune — aucune issue GitHub n'existe encore pour ce lot |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/alembic/versions/0028_jobs_et_outbox.py` | migration `0028` : `async_job`, `outbox_message` |
| `apps/api/app/jobs/modeles.py` | les deux tables du §20.1/§20.2, `TypeDeJob`, `EtatDuJob` |
| `apps/api/app/jobs/execution.py` | `commencer_un_essai`/`terminer_avec_succes`/`terminer_en_echec` — le cycle de vie idempotent d'un job |
| `apps/api/app/jobs/outbox.py` | `publier_dans_l_outbox` (atomique avec l'appelant) et `relayer_le_lot` (par savepoint) |
| `apps/api/app/jobs/email.py` | `FournisseurDEmail` (interface), `FournisseurSMTP` (reprend `app.auth.courriel`) |
| `apps/api/app/jobs/gabarits.py` | le registre de gabarits versionnés — mécanisme seul, aucun gabarit métier |
| `apps/api/app/auth/courriel.py` | étendu d'un `corps_html` facultatif (alternative MIME), additif |
| `apps/worker/worker/actors.py` | l'acteur Dramatiq `relayer_l_outbox`, seul consommateur du courtier à ce lot |
| `apps/worker/worker/main.py` | import des acteurs après `set_broker` |
| `apps/worker/pyproject.toml` | `onboarding-api` devient une dépendance explicite (voir §2.2) |
| `apps/api/app/modeles.py` | `jobs_modeles` enregistré dans `MODULES_DE_MODELES` |
| `apps/api/tests/test_socle_modele.py` | `async_job`/`outbox_message` ajoutées à `TABLES_DECLAREES` |
| `apps/api/tests/test_jobs.py` | **13 tests d'intégration** |
| `apps/api/tests/test_audit.py` | corrigé — voir §3.2 |
| `apps/api/tests/test_imports.py` | corrigé — voir §3.2 |

Le schéma passe de **54 à 56 tables métier** (**38 locales, 18 globales**), de 27 à **28
migrations**, tête `0028`, sans nouveau déclencheur. `make migrations-check` confronte **897
colonnes**, **329 contraintes**, **266 index**, **10 déclencheurs** et **199 fonctions** : le
schéma issu des migrations est identique à celui qui tourne, et le retour à `base` ne laisse
aucune table métier.

## 2.1 Un périmètre volontairement compilé, pas élargi

`T1` regroupe ce qui, dans le découpage initial à quinze sous-étapes, aurait été trois
sous-étapes (tables, jobs persistés, outbox, fournisseur e-mail) — conformément à la demande
explicite de Jonathan de regrouper pour accélérer. Trois choix de scope, assumés et nommés :

- **`scheduled_task_run` (modèle §20.3) n'est PAS posée ici.** Aucune des trois stories de `T1`
  ne la nomme, et le §20.3 ne donne d'ailleurs aucune liste de champs — seulement une liste de
  tâches et « un verrou PostgreSQL ou distribué garantit une seule exécution logique ». L'inventer
  maintenant serait le défaut §6.5 de la passation. Elle sera posée à `T4`, avec le verrou réel ;
- **aucun gabarit d'e-mail métier n'est enregistré.** Le mécanisme de `app/jobs/gabarits.py` est
  posé et testé, mais aucune story de ce lot ne nomme un contenu d'e-mail concret — l'enregistrer
  serait inventer un texte que personne n'a décidé ;
- **aucune route existante (le magic link, LOT 3) n'est migrée vers ce mécanisme.** `US003`
  demande les propriétés du nouveau mécanisme (Mailpit exclusif, templates versionnés, échecs
  rejouables), pas la migration d'un flux déjà livré et sensible (la temporisation du magic link,
  §22.5, anti-énumération) — un changement plus risqué que ce que cette sous-étape doit prouver.
  Résidu nommé, à reprendre si une sous-étape future en a besoin.
- **le relais de l'outbox n'est PAS auto-planifié.** `relayer_l_outbox` traite un lot et s'arrête ;
  c'est à qui écrit dans l'outbox de programmer le relais après que sa propre transaction a
  commité — même discipline que `BackgroundTasks` après la réponse en `app.auth.routes` (LOT 3).
  Un déclenchement périodique réel appartient à `T4` (`scheduled_task_run`).

## 2.2 `onboarding-worker` dépend désormais explicitement d'`onboarding-api`

Le worker n'avait jusqu'ici aucun acteur, donc aucune raison d'importer `app.*`. Ses premiers
acteurs réutilisent la logique de `app.jobs.*` plutôt que de la dupliquer (§7.27 de la passation) :
la dépendance est ajoutée dans `apps/worker/pyproject.toml` (`[tool.uv.sources]` vers le membre du
workspace), `uv lock`/`uv sync` rejoués, le conteneur worker reconstruit par `make code-refresh` et
vérifié démarré sain. Cette dépendance est RÉELLE depuis `T7` du LOT 1 déjà : le `Dockerfile` du
worker copiait déjà la source `apps/api` et synchronisait les deux dans le même environnement
`uv` ; cette ligne la documente, elle n'en crée pas une nouvelle.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make code-refresh` | les trois conteneurs reconstruits (nouvelle dépendance worker), sains |
| `make migrate` | tête `0028` |
| `make isolation-check` | **38 locales, 18 globales (+1), 29 composites (inchangé), 0 référence nue** |
| `make migrations-check` | base vide → `0028` → schéma identique ; retour à `base` propre |
| `uv run pytest apps/api/tests/test_jobs.py -q` | **13/13** |
| `uv run ruff check`/`format --check`, `uv run mypy` | verts |
| collecte depuis la racine | **2 009 pytest** (+17 : 13 de `test_jobs.py`, 4 ajoutés ailleurs entre-temps) |
| `uv run pytest -q` (développement, rejoué jusqu'à stabilité) | **78 échecs**, reproductibles sur deux exécutions consécutives — voir §3.1/§3.2 |
| comparaison de worktree `origin/develop` (§7.22 de la passation) | **78 échecs, LISTE identique terme à terme** |
| `make permissions-check` | 15/15, 0 échec |

## 3.1 Trois classes de défaut trouvées EN MESURANT, toutes corrigées avant ce rapport

**Un piège de méthode d'abord, nommé parce qu'il a coûté deux exécutions complètes.** Deux
exécutions successives de `uv run pytest -q` sur CETTE branche ont d'abord rendu des LISTES
d'échecs différentes (81 puis 80, sur des fichiers disjoints) avant de se stabiliser à 78,
identique sur deux tours. Diagnostiqué avant de conclure à une régression : une des deux
exécutions avait chevauché dans le temps un `make permissions-check` lancé en parallèle sur la
MÊME base de développement — les deux processus écrivant/lisant les mêmes tables au même instant,
l'un a vu l'état transitoire de l'autre (`make permissions-check` a lui-même rendu un échec
d'empreinte isolé le temps de ce chevauchement, disparu au rejeu sans rien d'autre changé).
**Ne jamais faire tourner deux contrôles qui écrivent dans la même base de développement en
parallèle** — même base partagée que celle décrite au §9 de `CLAUDE.md`.

**Deux défauts réels trouvés et corrigés, tous deux de la même classe — un garde-fou écrit contre
l'ABSENCE d'une table, rendu faux par l'arrivée de cette table :**

- `test_audit.py::test_l_audit_reste_synchrone_aucune_table_async_job` (LOT 10, `T1`) asserait
  `"async_job" not in metadonnees.tables` — vrai tant que le LOT 11 n'existait pas, faux
  maintenant qu'il pose la table. Corrigé en `test_l_export_de_l_audit_n_a_jamais_eu_besoin_de_job_id` :
  `async_job` existe désormais, `export_request.job_id` n'a toujours jamais existé — les deux faits
  sont INDÉPENDANTS, le second seul reste à prouver ;
- `test_imports.py::test_l_import_reste_synchrone_aucune_table_async_job_ni_outbox_message`
  (LOT 9, `T10`) portait le même défaut sur les deux tables à la fois. Corrigé en
  `test_l_import_reste_synchrone_meme_apres_l_arrivee_d_async_job_et_outbox_message` : les deux
  tables existent, mais `app.imports.execution` ne les consomme toujours pas — le pipeline
  d'import CSV n'a pas été réécrit par ce lot, c'est CE fait-là que le test doit prouver, pas
  l'absence des tables elles-mêmes.

## 3.2 Les 78 échecs restants sont environnementaux, pas une régression

Après les trois corrections ci-dessus, **deux exécutions consécutives et stables** rendent
**exactement 78 échecs, la même liste à l'identité près**, sur des fichiers du socle LOT 2/LOT 3
(`test_appartenance.py`, `test_personnes.py`, `test_organisation.py`, `test_clients.py`,
`test_responsabilites.py`, `test_metiers_et_statuts.py`, `test_roles_et_perimetres.py`,
`test_isolation.py`, `test_jeu_de_recette.py`, et neuf autres) — `sqlalchemy.exc.
MultipleResultsFound` ou des comptes en ABSOLU, exactement la classe documentée par `CLAUDE.md`
§9 : **cette base de développement porte le jeu de démonstration** (`make jeu-de-donnees`), et
aucun de ces tests n'a de rapport avec le socle asynchrone de ce lot.

Comparaison de worktree sur `origin/develop` (`3816201`, tête de `develop` avant cette
sous-étape), **même base, même `.env`** : **78 échecs, la LISTE identique terme à terme**. Zéro
régression imputable à `T1`.

**Ne pas réinitialiser cette base** : elle sert la préparation de la démonstration métier
(§9 de `CLAUDE.md`, projet en cours).

---

# 4. Décisions et écarts

- `DEC-676` consigne la réalisation et les choix de scope du §2.1 ;
- aucun écart nouveau n'est ouvert par `T1`.

---

# 5. Ce que `T1` laisse

- les deux tables et la migration rejouable, le cycle de vie idempotent d'un job, l'outbox
  transactionnelle et l'interface fournisseur, prêts pour `T2` (upload de média) qui consommera
  `commencer_un_essai`/`terminer_avec_succes`/`terminer_en_echec` pour la génération de
  miniatures ;
- `scheduled_task_run` (modèle §20.3) à poser à `T4`, avec le verrou réel ;
- le registre de gabarits d'e-mail, vide de tout contenu métier — la première sous-étape qui
  envoie un e-mail réel y enregistre son gabarit ;
- aucune route HTTP, aucun écran : `US001`/`US002`/`US003` sont de la plomberie, sans
  consommateur d'écran avant `T6` (raccordement des écrans résiduels à la navigation).

# Validation demandée à Jonathan

`T1` est faite. Après fusion, la prochaine sous-étape est `T2` : les médias — upload en
quarantaine, génération de miniatures et variantes idempotente, écran de dépôt de photo de
profil.
