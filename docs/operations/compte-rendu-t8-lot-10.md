# Compte rendu — `T8` du LOT 10 : le journal d'audit en lecture, filtrable par périmètre

**Sous-étape :** la huitième du lot — `GET` journal d'audit filtrable par périmètre, ferme
`US001`/`US002`
**Date :** 20 octobre 2026
**Décision :** `DEC-662`
**Stories :** `MVP-L10-US001` (clôt), `MVP-L10-US002` (clôt)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, **`T8`** |
| Restent | `T9` à `T16` |
| Issues | épic `#267`, stories `#268` à `#275`, jalon `G10` |

---

# 2. Deux arbitrages posés AVANT tout code

`T2` à `T7` n'ont écrit QUE de l'audit : aucune route de LECTURE n'existait, `audit_event` n'avait
jamais été interrogée. En construisant la résolution de périmètre (matrice §16), deux questions
que ni le cahier ni la matrice ne tranchent ont été posées à Jonathan avant une ligne de code,
chacune reformulée sans jargon (`AskUserQuestion`).

**Question 1 — les événements sans entité.** Mesuré par grep sur les sites d'appel réels de `T2` :
les quatre écritures d'authentification (`app/auth/services.py`, `sessions.py`,
`comptes_de_service.py`) n'écrivent JAMAIS `entity_id` — une connexion ou une demande de magic
link concernent une PERSONNE, jamais une entité. Un simple `WHERE entity_id = :entite` laisserait
donc le journal d'une entité muet sur les connexions de ses propres collaborateurs, alors que le
cahier §10.11 les cite EN PREMIER parmi ce qui est audité. Réponse de Jonathan : **« Par l'entité
actuelle du collaborateur »** — le journal d'une entité retrouve ces événements via l'appartenance
OCCUPANTE actuelle de l'acteur (`future`/`active`), jamais celle qu'il avait au moment de
l'événement. Limite assumée : un collaborateur qui a changé d'entité depuis voit sa connexion
ancienne dans sa NOUVELLE entité, pas celle où elle a eu lieu — aucune colonne ne capture ce
contexte historique, et en ajouter une serait une invention que rien ne demande (§6.5).

**Question 2 — le périmètre du Booster et du responsable de bureau.** La matrice §16 écrit
« Cercle »/« Bureau » pour ces deux rôles, jamais « Consultants » comme pour le DSM — un mot
différent, qui peut vouloir dire un périmètre plus large qu'un simple filtre sur les personnes.
Réponse de Jonathan : **« Aussi les autres ressources de leur périmètre »** — fidèle au mot choisi
par la matrice, plus de travail (reprendre la règle de périmètre déjà posée par chaque domaine et
l'appliquer à la lecture) mais fidèle au texte.

---

# 3. Ce que la sous-étape a produit

## 3.1 Le module `app/audit/perimetre.py`

`ROLES_DE_L_AUDIT` : les six rôles du §16 — DSM, ESM, Booster, responsable de bureau, ADM-E,
SUPER — jamais `EMP` ni `NEW`, à tiret comme `ANON` (§5, ligne « Audit »), refus `403` avant toute
résolution de périmètre. `PerimetreDAudit` : quatre portées — `ENTITE`/`CONSULTANTS`/`CERCLE`/
`BUREAU` —, même discipline que `PerimetreDuSuivi` (LOT 7, `T12`).
`resoudre_le_perimetre_de_l_audit` : ESM/ADM-E/SUPER → Entité, Booster → Cercle, responsable de
bureau → Bureau, DSM → Consultants, la portée la PLUS LARGE gagnant en cas de cumul (un témoin le
prouve, §4). `ROLES_DES_DETAILS_TECHNIQUES`/`a_les_details_techniques` : ADM-E/SUPER seuls — §16,
ligne « Consulter les détails techniques non sensibles », un axe des COLONNES exposées,
ORTHOGONAL au périmètre des lignes (l'ESM a `Entité` sur les lignes mais `Limité` sur les
colonnes).

## 3.2 La mesure complète des 21 types de ressource déjà audités

Les 21 valeurs de `resource_type` déjà écrites par `T2`-`T7` ont été ÉNUMÉRÉES par grep, puis
chacune confrontée à son modèle SQLAlchemy pour savoir si elle porte une colonne ou une relation
de rattachement à un cercle ou un bureau — jamais supposé :

| Classe | Types de ressource |
|---|---|
| **DIRECT** (colonne sur la ligne elle-même) | `circle`, `office` (racines), `content_page.circle_id`/`.office_id`, `framework_responsibility_assignment.circle_id`/`.office_id`, `circle_membership.circle_id`, `onboarding_template.scope_circle_id`/`.scope_person_id` |
| **UN SEUL SAUT** (table de jonction dédiée) | `event` → `event_circle_scope`/`event_office_scope`/`event_dsm_scope` (ce dernier posé par le LOT 8 `T3` pour `ECART-067`, jamais pensé pour l'audit mais signifiant littéralement « ce DSM précis ») |
| **DEUX OU TROIS SAUTS** (en remontant vers une appartenance) | `entity_membership`, `person`, `onboarding_instance`, `onboarding_instance_task`, `onboarding_template_version` |
| **JAMAIS SCOPÉ** par cercle ni bureau, mesuré par absence de colonne | `entity`, `internal_link`, `import_batch`, `import_decision`, `onboarding_task_reference`, `technical_role_assignment`, `service_account`, `user_account`, `user_session`, `magic_link_request` |

**Un bureau n'a AUCUNE table d'appartenance** (`app/organization/bureaux.py`, `ECART-059`/
`DEC-576`) : le périmètre `BUREAU` ne porte donc ni `person` ni `entity_membership` ni
`onboarding_*` — uniquement `office`, `content_page`, `event` et `framework_responsibility_
assignment`, plus l'acteur. Beaucoup plus court que `CERCLE`, et c'est le schéma qui l'impose, pas
une économie. **`CONSULTANTS` (DSM) garde la MÊME étendue que `CERCLE`** grâce à deux relations
directes trouvées en mesurant : `event_dsm_scope.dsm_person_id` et
`onboarding_template.scope_person_id` (quand `scope_type='DSM'`).

## 3.3 Le module `app/audit/lecture.py`

`FiltresDAudit` : cinq axes facultatifs dérivés des colonnes réelles d'`audit_event` (`depuis`,
`jusqua`, `action_code`, `resource_type`, `acteur`) — aucun n'étant nommé précisément par la
matrice, dérivés plutôt qu'inventés (§6.4). `lister_le_journal_d_audit` : deux requêtes dans la
MÊME transaction (total puis page), même discipline que `lister_le_trombinoscope`/`lister_les_
taches_en_retard`, ordre le plus RÉCENT d'abord (`occurred_at` DESC puis `id` DESC — jamais l'ordre
alphabétique d'un annuaire). Une CTE par périmètre (`mes_consultants` ; `mes_cercles`+`membres_du_
cercle` ; `mes_bureaux`+`co_responsables`), jamais interpolée avec une valeur utilisateur — seule
la PRÉSENCE d'une clause de filtre est assemblée dynamiquement en Python, ses valeurs toujours
liées (même discipline que `trombinoscope.py::_ou`). `resource_reference`/`correlation_token` sont
mis à `None` pour qui n'a pas les détails techniques — interprétation du mot « techniques », non
définie plus loin par le corpus, ancrée sur le vocabulaire du modèle lui-même : `T1` qualifie déjà
ces deux colonnes de « référence technique »/« jeton de corrélation technique » dans l'en-tête de
`app/audit/modeles.py`.

## 3.4 La route `GET /entities/{code}/audit`

Le rôle est RE-RÉSOLU dans le corps de la route, jamais par la dépendance coarse
`exiger_un_role_dans_l_entite` (qui ne rend pas `roles` à l'appelant) — même motif que
`_resoudre_l_entite_et_verifier_le_role` (`organization/routes.py`) et `_resoudre_le_cycle`
(`people/routes.py`) : une SEULE résolution, dans la transaction de la route, réutilisée pour la
garde, le périmètre ET les détails techniques — jamais deux appels à `resoudre_les_permissions`
qui pourraient diverger d'un instant à l'autre. Manifeste de contrat étendu (`journalDAudit`),
aucun module TypeScript propre — aucun écran consommateur avant `T15`, même discipline que
`suiviDesTachesEnRetard` au LOT 7.

---

# 4. Contrôles exécutés

**Vingt et un tests d'intégration nouveaux**, `apps/api/tests/test_journal_d_audit.py`, un par
branche significative : les gardes (session/rôle/entité), les quatre périmètres (positif ET
asymétrie négative pour chacun), les deux arbitrages de Jonathan (événement sans entité retrouvé
par l'entité actuelle, et son absence de l'entité d'un autre), le cumul de rôles (portée la plus
large gagne), les détails techniques (même ligne, deux lecteurs), le contenu interdit et la
corrélation (via un VRAI `app.auth.services.demander_un_magic_link`, jamais une ligne fabriquée —
seul endroit où la question posée est « le pipeline écriture-puis-lecture tient-il bout à bout ? »),
la rétention, les cinq filtres, la pagination. La plupart des témoins de périmètre INSÈRENT
`audit_event` DIRECTEMENT plutôt que de rejouer une écriture déjà prouvée par les sept fichiers
`test_audit_*.py` (`T2`-`T7`) — même discipline que `test_suivi_onboarding.py`, qui insère
directement dans `onboarding_instance_task` plutôt que d'appeler `terminer_une_tache`.

**Deux défauts trouvés en écrivant le décor de test, corrigés avant commit** — même classe que
`§7.25` de la passation, un paramètre lié partagé entre deux colonnes de types différents :
`circle.code` (`varchar`) et `circle.name` (`text`) partageaient `:c` dans mon aide `_cercle`/
`_bureau` ; `content_page.title` (`text`) et `.slug` (`varchar(160)`) partageaient `:slug` dans mon
aide `_page`. Les deux ont été séparés en paramètres distincts, et `make parametres-check` confirme
qu'aucun partage fautif ne subsiste dans tout le dépôt.

**Un troisième défaut, trouvé APRÈS l'ouverture de la pull request `#284`, par la CI elle-même, et
corrigé avant la fusion** — même théâtre que `§7.47` de la passation, déjà rencontré par
`test_analyse_import.py` : `make domaines-provision` sème le domaine e-mail global
(`exalt-company.com`) avec `starts_at = now()` au moment où `make migrate` tourne dans la tâche
« Stack réelle » de la CI. `ANCRAGE`, lui, est dérivé de `now() - 10 min` au moment de la COLLECTE
du module `test_journal_d_audit.py` — plus tard dans la même exécution, mais l'écart entre les
deux instants peut dépasser le tampon de dix minutes selon la durée des étapes qui précèdent
`residu-check` (environ dix minutes dans le run en cause). Quand c'est le cas, la période de
validité du domaine ne couvre pas encore `ANCRAGE`, et le témoin du pipeline écriture-puis-lecture
(`test_aucune_donnee_interdite_et_la_correlation_est_tracee`, §3) reçoit `domaine_non_autorise` au
lieu de `lien_emis` — un échec non reproductible en local, où ce délai est généralement plus court.
Corrigé par une seconde ligne globale du domaine, bornée dans le passé (`2020-01-01`), insérée dans
la même transaction que le reste du décor et effacée PAR SON IDENTIFIANT au ménage — jamais par le
nom du domaine, pour ne jamais toucher la ligne semée par `make domaines-provision` elle-même.

| Contrôle | Résultat |
|---|---|
| `pytest` racine | 1 804 collectés (+21, tous d'intégration), 1 727 passés / 77 échecs |
| Comparaison de worktree avec `origin/develop` | 77 échecs environnementaux **identiques**, `diff` vide entre les deux listes triées |
| `uv run mypy` (racine) | vert, 254 fichiers (+4) |
| `uv run ruff check`/`format` | vert, tout le dépôt |
| `make migrations-check` | schéma identique, tête `0027` inchangée — aucune migration |
| `make permissions-check` | 15/15 |
| `make parametres-check` | aucun partage de paramètre fautif (après correctif des deux trouvés dans mes propres décors) |
| `make sources-check` | aucun fichier source ignoré par git |

---

# 5. Décisions et écarts

`DEC-662` consigne cette sous-étape. Aucun écart n'est ouvert ni fermé par `T8` : `US001`/`US002`
sont closes, `QO-092` et la divergence des annotations `lot=` du §30.19-24 restent non bloquantes
pour ce socle, comme la fiche l'annonçait.

---

# 6. Ce que `T8` laisse

- **L'export CSV du journal** (`US004`, réservé à `ADM-E`/`SUPER`) reste à `T9` — la fiche l'annonce
  explicitement, « lui-même audité ».
- **Le reporting étendu** (`US003`, compteurs et tableaux du §15.1/§10.10) reste à `T10`, ressource
  distincte du tableau de bord administratif du LOT 9 `T5`.
- **Aucun écran** ne consomme encore cette route : les écrans back-office (audit, reporting,
  support) arrivent à `T15`, pattern `T14` du LOT 9.
- **Le résidu documentaire de `T1`** (`archive_reason`/`assignment_reason` non écrits, nommé par
  `T7`) reste inchangé : `T8` ne les lit pas davantage qu'ils ne sont écrits.

---

# Validation demandée à Jonathan

`T8` ferme `US001` et `US002` : le journal d'audit est consultable, filtrable par périmètre, et les
deux arbitrages ci-dessus sont appliqués et prouvés par témoin. Zéro régression mesurée par
comparaison de worktree. Réaliser `T9` (export CSV de l'audit) depuis `develop` une fois cette
sous-étape fusionnée.

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
