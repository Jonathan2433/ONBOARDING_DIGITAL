# Compte rendu — `T2` du LOT 10 : le service d'écriture d'audit générique, câblé sur l'authentification

**Sous-étape :** la deuxième du lot — câblage sur l'authentification et les sessions (LOT 3)
**Date :** 14 octobre 2026
**Décision :** `DEC-656`
**Stories :** `MVP-L10-US001`/`US002`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, **`T2`** |
| Restent | `T3` à `T16` |
| Issues | épic `#267`, stories `#268` à `#275`, jalon `G10` |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/audit/services.py` | le service générique, `enregistrer_un_evenement` |
| `apps/api/app/audit/__init__.py` | export de `enregistrer_un_evenement` et `DUREE_DE_RETENTION` |
| `apps/api/app/auth/services.py` | les trois fonctions `_tracer*` (demande de magic link, consommation, connexion administrateur/changement de mot de passe) écrivent aussi `audit_event` |
| `apps/api/app/auth/sessions.py` | `revoquer` et `revoquer_toutes_les_sessions` écrivent aussi `audit_event` |
| `apps/api/app/auth/comptes_de_service.py` | `_tracer` (authentification de jeton de service) écrit aussi `audit_event` |
| `apps/api/tests/test_audit_authentification.py` | **11 tests** (10 d'intégration), le câblage lui-même |
| 8 fichiers de test existants | leur nettoyage de décor étend la suppression déjà faite sur `auth_event` à `audit_event` |

Aucune migration, aucune route : `T2` ne construit qu'un service et son câblage, exactement le
périmètre que `fiche-lot-10.md` lui donne.

## 2.1 Le service générique

`enregistrer_un_evenement(connexion, *, instant, action_code, resource_type, summary, ...)` suit
le MÊME patron que les quatre fonctions `_tracer*` du LOT 3 qu'il complète : une `Connection`
déjà ouverte, dans la transaction de l'appelant — jamais une transaction à lui. C'est la
conséquence directe d'`ARB-DATA-005`/`§30.20` : l'audit et l'action métier sont une seule
écriture, pas deux.

**`action_code` réutilise `TypeEvenementAuth`, il n'en invente pas un second.** Le modèle laisse
`audit_event.action_code` ouvert (« Code stable », sans énumération fermée, même lecture
qu'`operational_alert.source`) — mais les sept valeurs existent déjà pour l'authentification,
posées par `T2` du LOT 3 et écrites dans `auth_event.event_type`. Inventer un second vocabulaire
pour la même notion aurait dupliqué une classification déjà correcte (§7.27 de la passation).

**`correlation_token` est repris de `correlation_courante()`**, posé par le middleware sur chaque
requête depuis le LOT 1 `T4` — jamais régénéré tant qu'il existe. Le repli sur `engendrer()` ne
sert qu'un appel hors requête et hors job (un test qui invoque le service directement).

**`retention_until` est calculé EXPLICITEMENT depuis le même `instant` que `occurred_at`**
(`+ 365 jours`), jamais laissé au défaut serveur de la table (`now() + interval '1 year'`) — un
`instant` injecté qui diffère de `now()` aurait fait diverger les deux colonnes l'une de l'autre,
même leçon que `creer_un_jeton` au LOT 3 `T10` (`§7.0` sixième proposition de la passation).

Le service n'exerce AUCUN filtre de contenu a posteriori : le §16.2/§21.1 interdit mots de passe,
jetons, liens magiques complets, secrets — c'est à CHAQUE appelant de ne jamais les passer en
`summary`/`old_values`/`new_values`/`reason`. Un filtre ici masquerait un défaut d'appelant au lieu
de le faire échouer au bon endroit.

## 2.2 Le câblage, site par site

Les quatre sites qui écrivaient déjà `auth_event` depuis le LOT 3 écrivent désormais AUSSI
`audit_event`, dans la même transaction :

| Site | `action_code` | `resource_type` | `resource_reference` |
|---|---|---|---|
| Demande de magic link (`_tracer`) | `MAGIC_LINK_REQUESTED` | `magic_link_request` | aucun (famille polymorphe) |
| Consommation de magic link (`_tracer_consommation`) | `LOGIN_FAILURE`/`MAGIC_LINK_USED` | `magic_link_request` | aucun |
| Connexion administrateur / changement de mot de passe (`_tracer_connexion`) | sept valeurs possibles | `user_account` | le compte, quand connu |
| Révocation de session, une ou en masse (`revoquer`/`revoquer_toutes_les_sessions`) | `SESSION_REVOKED` | `user_session` | la session (le `RETURNING` existant étendu d'une colonne) |
| Authentification de jeton de service (`_tracer`) | `LOGIN_SUCCESS`/`LOGIN_FAILURE` | `service_account` | le compte, quand connu |

**La révocation de session porte `reason`** — `raison` (déconnexion, départ, retrait d'accès) est
DÉJÀ un paramètre obligatoire de ces deux fonctions depuis le LOT 3 `T9` : le motif humain que le
modèle demande pour les actions sensibles existait déjà, `T2` le relaie simplement.

**Aucun second acteur n'est inventé pour les autres sites** : les tentatives de connexion n'ont pas
de motif humain à transmettre, `reason` y reste `None`.

## 2.3 Un défaut trouvé par les tests existants, pas par un contrôle nouveau

**`audit_event.actor_person_id`/`actor_service_account_id` portent une clé étrangère vers
`person`/`service_account`, exactement comme `auth_event` depuis le LOT 3.** Neuf fichiers de test
existants nettoient déjà leur décor en retirant `auth_event` avant `person`/`service_account` — et
chacun d'eux s'est mis à échouer en violation de clé étrangère dès que ses tests ont commencé à
produire aussi des lignes `audit_event` non retirées par ce même nettoyage.

C'est EXACTEMENT la classe de défaut déjà documentée dans ces mêmes fichiers pour `user_session`
au LOT 3 `T6` (« son absence ici a cassé dix tests sans rapport ») : une table nouvelle qui
référence `person`/`service_account` rend incomplet un nettoyage qui l'ignore. Corrigé en ajoutant,
dans chacun des neuf blocs, la ligne `audit_event` symétrique à la ligne `auth_event` déjà
présente — `test_magic_link.py` (2 blocs), `test_sessions.py` (2 blocs), `test_comptes_de_service.py`,
`test_administrateur.py` (2 blocs), `test_csrf_et_idempotence.py`, `test_debit.py`,
`test_portail.py`, `test_revocation.py`.

**Un résidu de développement, distinct du défaut lui-même, a été nettoyé avant la mesure finale** :
les exécutions successives de la suite, avant que les neuf blocs ne soient tous corrigés, ont laissé
des lignes `audit_event`/`auth_event`/`magic_link_request`/`user_session`/`user_account`/`entity`/
`entity_membership` créées le jour même dans la base de développement. Toutes portaient un horodatage
du 14/10/2026 (`created_at::date = current_date`), jamais antérieur — donc jamais une ligne du jeu de
démonstration, qui date du 22/09/2026 ou avant. Retirées par date, jamais par motif de nom, pour ne
toucher QUE ce que cette session de travail a elle-même produit.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q apps/api/tests/test_audit_authentification.py` | **11/11** |
| collecte depuis la racine | **1 725 pytest** (+11), dont **1 292 d'intégration** (+10) |
| `uv run mypy` racine | vert, **244 fichiers** (+2) |
| `make format-check`, `make lint` | verts |
| `make sources-check` | **661 fichiers** (+2 réels — les deux autres sont `AGENTS.md`/`V1.html`, artefacts connus de la comparaison de worktree, pas du travail de cette sous-étape) |
| `make isolation-check` | **inchangé** : 37 tables locales, 17 globales, 29 clés composites, 0 référence nue |
| `make docs-check` | vert |
| comparaison de worktree `origin/develop` (§7.22 de la passation) | **71 échecs identiques, un par un**, des deux côtés (liste comparée, pas seulement le compte) |

**Le compte des échecs environnementaux baisse de 74 à 71 entre `T1` et `T2`, et ce n'est PAS une
régression corrigée par cette sous-étape** : trois tests de `test_authentification.py` échouaient à
cause de lignes `user_account`/`magic_link_request`/`auth_event` résiduelles, créées par des
exécutions précédentes de la suite dans CETTE base de développement précise — pas par le jeu de
démonstration lui-même. Une fois ces trois lignes retirées (même nettoyage que celui du §2.3), les
trois tests passent sur `origin/develop` ET sur la branche. **Mesuré sur les deux côtés de la
comparaison de worktree, qui partagent la même base** : 71 échecs identiques, donc ni régression ni
amélioration imputable au code de `T2` — un effet de bord de l'ordre d'exécution des sessions de
travail précédentes dans cette base, pas du travail de cette sous-étape. Ne pas recopier « 71 »
comme un nouveau total acquis : redérive-le avant de le réutiliser, comme pour tout nombre de ce
projet.

---

# 4. Décisions et écarts

- `DEC-656` consigne la réalisation et les choix dérivés du modèle ;
- aucun écart n'est ouvert ni fermé par `T2` ; `ECART-064` reste à fermer à `T7`.

---

# 5. Ce que `T2` laisse

- un service générique prêt à être appelé par `T3` à `T7`, sur leurs domaines respectifs ;
- l'authentification et les sessions (LOT 3) entièrement câblées — les quatre familles
  d'événements déjà tracées par `auth_event` le sont désormais aussi par `audit_event` ;
- aucune route de lecture de l'audit : `T8` construit le journal filtrable ;
- la divergence des annotations `lot=` du §30.19-24 dans `verifier-recette-modele.py` intacte, à
  vérifier à `T16`.

# Validation demandée à Jonathan

`T2` est faite. Après fusion, la prochaine sous-étape est `T3` : le câblage sur les personnes et
l'organisation (LOT 2, 4, 5, 9).
