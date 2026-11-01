# Compte rendu — `T4` du LOT 11 : planification et supervision

**Sous-étape :** `T4` — tâches planifiées avec verrou, nettoyage des médias, supervision
Uptime Kuma
**Stories fermées :** `MVP-L11-US006`, `US007`, `US008` — les HUIT stories officielles du
backlog du LOT 11 sont désormais toutes fermées
**Décision :** `DEC-679`
**Date :** 1 novembre 2026

---

# 1. État du lot

Le LOT 11 est ouvert depuis le 30/10/2026 (`DEC-674`), découpage en sept sous-étapes. `T1`
(`DEC-676`), `T2` (`DEC-677`) et `T3` (`DEC-678`) sont faites et fusionnées. `T4` ferme les trois
dernières stories officielles du backlog (`US006`/`US007`/`US008`) sans en ouvrir aucune nouvelle
hors backlog — contrairement à `T3`, cette sous-étape ne livre aucun écran.

---

# 2. Ce que la sous-étape a produit

| Fichier | Rôle |
|---|---|
| `apps/api/alembic/versions/0029_taches_planifiees.py` | migration : table `scheduled_task_run` (modèle §20.3) |
| `apps/api/app/scheduling/modeles.py` | `ScheduledTaskRun`, `NomDeTachePlanifiee` (six valeurs), `EtatDeLaTachePlanifiee` |
| `apps/api/app/scheduling/execution.py` | `commencer_l_execution`/`terminer_avec_succes`/`terminer_en_echec` — le verrou |
| `apps/api/app/scheduling/taches.py` | les six fonctions de tâche |
| `apps/api/app/scheduling/supervision.py` | le battement Uptime Kuma |
| `apps/api/app/scheduling/orchestrateur.py` | `executer_le_cycle` — une transaction, une savepoint par tâche |
| `apps/worker/worker/actors.py` | `executer_le_cycle_planifie`, acteur auto-replanifié |
| `apps/worker/worker/amorcage.py` | `DemarrerLaPlanification`, middleware `after_worker_boot` |
| `apps/api/app/media/objets.py` | `supprimer_l_objet` (première suppression MinIO du projet) |
| `apps/api/app/configuration/settings.py` | cinq nouveaux réglages, dont `UPTIME_KUMA_PUSH_URL` enfin consommée |
| `infra/compose/docker-compose.base.yml` | `APP_SECRET_KEY` ajoutée au bloc `worker` (défaut latent corrigé) |
| `apps/api/tests/test_taches_planifiees.py` | vingt-six tests d'intégration |

## 2.1 Le verrou est un index unique partiel, jamais un `pg_advisory_lock`

Le modèle §20.3 laisse le mécanisme ouvert : « un verrou PostgreSQL ou distribué ». Ce dépôt en
porte déjà un, éprouvé par `async_job`/`outbox_message` (LOT 11 `T1`) : qu'une seule ligne porte
`state = 'running'` pour un `task_name` donné, à la fois
(`uq_scheduled_task_run_task_name_en_cours`). Un `INSERT` qui violerait cela échoue sur la
contrainte — la même garantie qu'un `pg_advisory_lock` nommerait, sans dépendre d'une connexion
tenue ouverte pendant tout le cycle. Réutilisé, pas inventé une seconde fois (§7.27 de la
passation).

`app.scheduling.execution` reprend le même découpage en trois fonctions qu'`app.jobs.execution`
pour `async_job` : `commencer_l_execution` ouvre une ligne `running` ou lève `TacheDejaEnCours` (la
violation de l'index traduite), `terminer_avec_succes`/`terminer_en_echec` la closent. Sans
`idempotency_key` ni `max_attempts` : une tâche planifiée n'est pas demandée par un appelant
précis, elle est la même tâche cycle après cycle, et un échec se rattrape simplement au cycle
suivant.

## 2.2 Six tâches, une transaction par cycle, une savepoint par tâche

`app.scheduling.orchestrateur.executer_le_cycle` ouvre une transaction unique pour le cycle entier
et isole chaque tâche dans sa propre savepoint — même patron qu'`app.jobs.outbox.relayer_le_lot` et
`app.imports.execution` (§7.27) : une tâche qui échoue n'annule ni les précédentes ni les suivantes
du même cycle.

**1. Expiration des liens, sessions et jetons de service** — pure hygiène. `expires_at`/
`absolute_expires_at`/l'inactivité à sept jours sont déjà les bornes réelles de sécurité depuis le
LOT 3 ; cette tâche rend seulement `invalidated_at`/`revoked_at` cohérents pour toute lecture
administrative. Le §20.3 cite « expiration des liens » et « sessions » séparément, mais les deux
relèvent du même geste sur deux familles de tables sœurs — les séparer aurait doublé le verrou pour
un seul mécanisme.

**2. Événements passés** — arbitrage explicite de Jonathan (`AskUserQuestion`, 31/10/2026). Le
cahier §16.4/le modèle §20.3 la nomment tâche planifiée ; une autre section du modèle dit que le
classement passé/à venir se CALCULE à la lecture, sans rien enregistrer — ce que le LOT 8 fait déjà.
Réponse retenue : rien de plus que confirmer l'exécution, pour la preuve de supervision. Construire
un mécanisme supplémentaire aurait été le §6.5.

**3. Anonymisation après départ à trois mois** (`DEPARTURE_ARCHIVE_MONTHS`, modèle §22.5). Réutilise
`person.account_state = 'anonymized'`/`anonymized_at` et leur déclencheur d'irréversibilité
(`fn_person_anonymisation_terminale`), posés par le LOT 2 et jamais consommés jusqu'ici — `T4` en
est le premier consommateur réel, sans migration nouvelle sur `person`. Nom/prénom remplacés par un
jeton fixe, e-mail par une adresse synthétique unique (`anonymise+<uuid>@anonymise.invalid`, qui
satisfait les contraintes de forme et d'unicité du §6.1), `entity_membership.short_bio`/`fun_fact`
vidés, `arrival_profile.short_intro` remplacé par un texte non vide (la contrainte
`short_intro_requis_hors_brouillon` l'exige hors brouillon) et `fun_fact`/`photo_media_id` vidés,
toutes les `photo_authorization` actives retirées. **Elle ne touche JAMAIS au média lui-même** :
elle sèvre les références, et c'est la tâche 6, au même cycle, qui constate l'absence de référence
et engage le délai de grâce — deux responsabilités, jamais dupliquées. Idempotente par construction
(`account_state <> 'anonymized'` dans la clause `WHERE`).

**4. Purge de l'audit à un an** — `audit_event.retention_until` est déjà calculé à l'écriture par le
LOT 10 (`T2`, `DUREE_DE_RETENTION`) ; cette tâche applique seulement la borne déjà posée, sans
relire `AUDIT_RETENTION_DAYS`.

**5. Détection des jobs bloqués** (cahier §27.4, deux seuils). `WORKER_ABSENT_ALERT_MINUTES` (un
`async_job` `queued` sans worker depuis dix minutes) et `JOB_STALLED_ALERT_MINUTES` (un job
`running` sans battement depuis trente minutes) lèvent chacun une alerte via `lever_une_alerte`
(LOT 10 `T13`), réutilisée telle quelle — aucune seconde voie d'alerte.

**6. Nettoyage des médias** (`US007`) — voir §2.3.

## 2.3 Le nettoyage des médias : un délai unique, un marqueur réutilisé

**Deux arbitrages explicites de Jonathan** (`AskUserQuestion`, 31/10/2026) tranchent ce que ni le
cahier ni `.env.example` ne chiffraient : sept jours de délai avant suppression définitive d'un
média rejeté, resté bloqué en traitement, ou orphelin — la MÊME règle pour les trois catégories, un
seul mécanisme de nettoyage plus simple à auditer.

Un média `pending`/`processing`/`rejected` depuis plus de sept jours (compté depuis `created_at`,
jamais devenu affichable) est supprimé directement. Un média `ready` sans aucune référence active
dans les trois tables connues (`event_media`, `photo_authorization` active, `arrival_profile.
photo_media_id` — faute de `media_usage`, §16.3, reportée à la médiathèque V1 par `DEC-558`) est
d'abord ARCHIVÉ (`media_asset.archived_at`, DÉJÀ consommé en lecture par `app.media.photo` depuis le
LOT 5 pour exclure un média archivé de l'affichage — réutilisé comme horodatage de première
détection, aucune colonne nouvelle), puis supprimé sept jours plus tard si la vérification,
REFAITE au moment de la suppression, confirme toujours l'absence de référence.

Chaque suppression physique passe par `supprimer_l_objet` (nouvelle fonction, `app.media.objets`,
la première suppression MinIO du projet après la première lecture et le premier dépôt), supprime
aussi les variantes, marque `media_asset.state = 'deleted'` (état terminal depuis le LOT 5,
déclencheur `fn_media_asset_suppression_terminale`), et écrit un `audit_event`
(`media_nettoye_automatiquement`) — « chaque suppression sensible est auditable » (critère
d'acceptation d'`US007`).

## 2.4 Supervision Uptime Kuma : un seul battement poussé, pas onze moniteurs

Le cahier §27.2 nomme onze composants à superviser, mais `.env.example` ne déclare qu'UNE seule
variable, `UPTIME_KUMA_PUSH_URL` — au singulier. La plupart des composants se TIRENT déjà via
`/health/ready` (LOT 1 `T3`, déjà sondé) ; ce que ce battement POUSSE est précisément ce qui ne peut
pas se tirer : la preuve que le worker exécute ses cycles — la démonstration citée par le cahier,
« heartbeat de sauvegarde ou de maintenance reçu dans Uptime Kuma ». `envoyer_le_battement`
(`app.scheduling.supervision`) suit le protocole public d'Uptime Kuma (GET avec `status`/`msg`), ne
lève jamais (une supervision qui ferait échouer le cycle qu'elle supervise serait son propre
défaut), et ne fait rien si l'URL reste vide — le cas de développement et de recette, où aucune
instance Uptime Kuma ne tourne.

`httpx` devient une dépendance de PRODUCTION d'`apps/api` (jusqu'ici dev seule, pour `TestClient`) :
le premier appel HTTP sortant du projet.

## 2.5 L'auto-réplanification : le mécanisme natif de Dramatiq, pas un `cron` ajouté

Aucun outil de planification périodique (type `cron`, `dramatiq-crontab`) n'est une dépendance de
ce dépôt. Le mécanisme retenu, mesuré dans la bibliothèque avant d'être employé, est celui que
Dramatiq offre déjà nativement : `send_with_options(delay=...)`, que `RedisBroker.enqueue` honore
sans middleware supplémentaire (vérifié dans la source de `dramatiq.brokers.redis` avant d'écrire
une ligne). L'acteur `executer_le_cycle_planifie` se renvoie lui-même, `SCHEDULED_TASKS_INTERVAL_
MINUTES` plus tard, **dans un `finally`** : un cycle qui échoue ne doit jamais interrompre la
boucle, sous peine de perdre toute supervision silencieusement.

Le premier envoi — qui démarre la boucle — ne vient PAS de l'import du module `worker.main` (cela
romprait `test_aucun_acteur_metier_n_est_declare` du LOT 1 et tenterait une connexion Redis à
chaque simple import dans les tests). Il vient du nouveau middleware `DemarrerLaPlanification`
(`worker.amorcage`), sur le crochet `after_worker_boot` de Dramatiq — invoqué par le PROCESSUS
worker réel, jamais par une importation de test.

## 2.6 Deux défauts trouvés en construisant, corrigés avant commit

**`APP_SECRET_KEY` n'était jamais transmise au worker** dans `docker-compose.base.yml`, défaut
LATENT depuis `T1` du LOT 11 : `worker.actors.relayer_l_outbox` appelle déjà `parametres_en_cache()`
(qui exige cette variable dans tous les environnements depuis `T7` du LOT 3), mais son seul chemin
de déclenchement réel passait jusqu'ici par `BackgroundTasks` côté API — qui possède déjà ses
propres `Parametres` chargés — jamais par un message Dramatiq réellement traité par le worker
lui-même. Le tout premier cycle réel de `executer_le_cycle_planifie`, sur la pile réelle, l'a trouvé
immédiatement : `ConfigurationInvalide` dans les journaux du worker. Corrigé en ajoutant la
variable au bloc `worker` de `docker-compose.base.yml`, avec les cinq nouvelles variables de `T4`
posées sur les deux blocs `api`/`worker` — même classe que `PUBLIC_BASE_URL` à `T3` du LOT 3
(§7.16 de la passation : ce qui n'a jamais tourné n'est pas éprouvé).

**Deux noms de contrainte doublement préfixés** (`ck_scheduled_task_run_ck_scheduled_task_run_...`,
67 caractères) : ma première version de `app.scheduling.modeles` passait des noms déjà préfixés à
`contrainte_enumeration`/`CheckConstraint`, alors que la convention de nommage du socle les
préfixe elle-même — exactement le défaut déjà documenté dans l'en-tête d'`app.media.modeles`
(`photo_authorization`) et rejoué ici, trouvé par `test_aucun_nom_de_contrainte_du_modele_ne_
depasse_la_limite` avant tout commit.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run ruff check`/`format` | 0 défaut, dépôt entier |
| `uv run mypy` | 0 erreur, 305 fichiers |
| `make migrations-check` | base vide → `0029` → schéma identique (912 colonnes, 333 contraintes, 269 index, 10 déclencheurs, 199 fonctions) |
| `make isolation-check` | 57 tables (38 locales, 19 globales, +1 globale), 29 composites inchangé, 0 référence nue |
| `make sources-check` | aucun fichier source ignoré |
| `make docs-check` | 5 documents immuables intacts, 6 séquences cohérentes, 12 contrôles de totaux, 12 contrôles sur la passation |
| `uv run pytest apps/api/tests/test_taches_planifiees.py` | 26/26 |
| `uv run pytest` (racine) | 2 085 collectés (+26), 78 échecs environnementaux identiques à `origin/develop` |
| Aller-retour réel sur la pile | voir §3.2 |

## 3.1 Zéro régression, mesurée par comparaison de worktree

Un `git worktree` sur `origin/develop`, pointant la MÊME base de développement (même `.env` copié),
a rendu exactement **78 échecs** — comparés terme à terme à la branche (`comm -23`/`comm -13` dans
les deux sens) : liste strictement identique, aucune différence. Les 78 échecs restent les mêmes
défauts environnementaux documentés depuis plusieurs lots (jeu de démonstration chargé sur cette
machine, assertions en compte absolu).

## 3.2 Aller-retour réel effectué sur la pile réelle, malgré l'absence d'écran

`T4` ne livre aucune route HTTP ni aucune page — la fiche ne la nomme sur aucune des deux. Le §7.43
de la passation (aller-retour réel) s'applique traditionnellement à un écran ; ici, la preuve
équivalente est que le MÉCANISME ASYNCHRONE tourne réellement, de bout en bout, sans aucun bouchon.

Après correction du défaut `APP_SECRET_KEY` (§2.6), `make up` a été relancé. Les journaux réels du
worker (format JSON corrélé) montrent :

```json
{"message":"demarrage de la boucle des taches planifiees"}
{"message":"job traite","route":"maintenance/executer_le_cycle_planifie","resultat":"succes"}
```

Six lignes `scheduled_task_run` réelles, toutes `succeeded`, ont été vérifiées en base :

```text
         task_name          |   state   | items_processed
----------------------------+-----------+-----------------
 expiration_liens_sessions  | succeeded |              16
 evenements_passes          | succeeded |               0
 anonymisation_apres_depart | succeeded |               1
 purge_audit                | succeeded |               0
 detection_jobs_bloques     | succeeded |               0
 nettoyage_medias           | succeeded |               0
```

**L'anonymisation a réellement traité une personne du jeu de démonstration déjà présent sur cette
machine**, partie depuis plus de trois mois — vérifiée en base : nom/prénom remplacés par le jeton,
e-mail synthétique unique, `account_state = 'anonymized'`, `anonymized_at` renseigné. C'est une
preuve PLUS forte qu'un décor de test construit pour l'occasion : le mécanisme fonctionne sur des
données réelles, pas seulement sur un cas fabriqué.

**L'auto-réplanification a été confirmée sans attendre les cinq minutes** : la clé Redis
`dramatiq:maintenance.DQ.msgs` (la file de délai de Dramatiq, `.DQ` étant le suffixe que
`RedisBroker.enqueue` emploie pour un message différé) est apparue immédiatement après le premier
cycle, prouvant que le second envoi a bien été programmé.

Les cinq autres tâches ont rendu zéro élément traité, ce qui est le résultat ATTENDU sur une base
sans anomalie à ce moment (aucun lien/session expiré au-delà des seize déjà traités, aucune ligne
d'audit échue, aucun job bloqué, aucun média à nettoyer) — chaque cas POSITIF (quelque chose à
faire) est, lui, prouvé par le décor contrôlé de `test_taches_planifiees.py` (§3 ci-dessus), pas
par cette seule observation de production qui ne peut pas garantir qu'un cas positif se présente.

---

# 4. Décisions et écarts

**`DEC-679`** enregistre cette sous-étape. Trois arbitrages explicites de Jonathan (délai de
nettoyage des médias, règle unique pour les trois catégories, portée de la tâche « événements
passés ») sont tracés au §2.2/§2.3 ci-dessus et dans le registre.

Aucun écart nouveau. `ECART-061` (mot de passe provisoire jamais forcé de changer) et `QO-113`
(conservation calendaire des journaux) restent sans rapport avec cette sous-étape.

---

# 5. Ce que `T4` laisse

- **Le déclenchement manuel « Lancer l'anonymisation RGPD »** (matrice §18, `ADM-E`/`SUPER`) n'est
  pas construit : la fiche ne nomme, pour `T4`, que la tâche AUTOMATIQUE à trois mois. Résidu nommé,
  à instruire si un lot futur en a besoin.
- **La détection d'orphelin ne peut pas voir une référence cachée dans un `payload_json`** de bloc
  de contenu — aucun type de bloc n'en porte aujourd'hui (`QO-121` reste ouverte), donc sans
  conséquence actuelle, mais à revoir le jour où un bloc référencera un média.
- **`AUDIT_RETENTION_DAYS` reste non consommée en tant que variable** : la durée d'un an est un
  `dt.timedelta` fixe dans `app.audit.services` (LOT 10), et `purger_l_audit` applique la colonne
  déjà calculée plutôt que de relire la variable. Pré-existant, non introduit par `T4`.
- **Aucun script `make taches-planifiees-check` n'est construit** : `T4` ne livre aucune route HTTP
  ni aucune page à travers Caddy, et les vingt-six tests d'intégration de
  `test_taches_planifiees.py`, tous exécutés sur la pile réelle (PostgreSQL et MinIO vrais),
  couvrent déjà chaque tâche, le verrou et l'orchestrateur — un script de pile dupliquerait cette
  preuve sans rien ajouter. Si un lot futur expose ces mécanismes par une route, le script devra
  être posé à ce moment-là.
- **`T5`** (métier, rendu optionnel partout, `DEC-675`) est la sous-étape suivante.

---

# Validation demandée à Jonathan

`T4` du LOT 11 est techniquement complète : les huit stories officielles du backlog sont fermées,
zéro régression mesurée, aller-retour réel effectué sur la pile réelle (sans écran, puisque `T4`
n'en livre aucun). Pull request à ouvrir, numéro à venir.
