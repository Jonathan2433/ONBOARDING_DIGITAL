# Compte rendu — `T13` du LOT 10 : le cycle des alertes opérationnelles

**Story :** `MVP-L10-US007` — « Suivre les alertes fonctionnelles importantes. »
**Décision :** `DEC-667`
**Date :** 22 octobre 2026

---

# 1. État du lot

LOT 10 ouvert le 14/10/2026 (`DEC-654`), découpage validé en seize sous-étapes. `T1` à `T12` sont
faites. `T13` ferme `US007` : le cycle applicatif d'une alerte opérationnelle — ouverture,
acquittement, commentaire, résolution, réouverture automatique en cas de récidive (cahier §21.2,
§27.5) — matrice §17 « Consulter les alertes de sécurité »/« Acquitter une alerte »/« Résoudre ou
commenter une alerte ». `T14` (le suivi d'une demande de droit RGPD) est la suivante.

---

# 2. Ce que le corpus décidait déjà, et ce qui restait à faire

## 2.1 `operational_alert` est une ressource GLOBALE, et c'est la clé de tout le reste

Le modèle §21.2 pose `operational_alert` et `alert_comment` (§21.3) sans aucune colonne
`entity_id` — `T1` l'a posé ainsi dès l'ouverture du lot, avec le motif écrit dans son propre
en-tête (`app/audit/modeles.py`) : « une alerte opérationnelle (disque, worker, sauvegarde) n'est
pas un fait D'UNE entité ». Ce fait structurel commande toutes les décisions de `T13` :

- les six routes sont **plates** (`/alerts`, `/alerts/{alerte}`, `/alerts/{alerte}/commentaires`,
  `/alerts/{alerte}/acquittement`, `/alerts/{alerte}/resolution`), jamais
  `/entities/{code}/...` — troisième famille de routes entité-less du dépôt, après
  `POST /bug-reports` (`T11`) et `POST /entities` (LOT 9 `T12`), qui sont les deux seules autres
  routes du projet sans code d'entité dans le chemin ;
- `app.permissions.dependances.exiger_un_role_dans_l_entite` **ne peut pas garder ces routes** :
  cette dépendance exige structurellement un paramètre de chemin `code` (son propre docstring le
  dit), absent par construction ici ;
- la grille **Entité/Global** que la matrice §17 porte pour `ADM-E`/`SUPER` sur les trois lignes
  des alertes ne peut donc **pas** se lire comme un filtrage par entité — il n'y a aucune colonne
  à filtrer. Elle se lit comme ce qu'elle désigne déjà pour `SUPER` dans tout le reste du dépôt
  (une portée qui s'étend à tout), et pour `ADM-E` elle s'étend PAREIL : détenir ce rôle dans
  N'IMPORTE QUELLE entité suffit, puisqu'aucune alerte n'« appartient » à une entité précise dont
  il faudrait restreindre la vue.

Mesuré avant d'écrire une ligne : `resoudre_les_permissions` (LOT 4, `T8`) n'accorde `ADM-E`/`ESM`
que DANS l'entité **principale** consultée (`app/permissions/services.py`) — aucune route de ce
dépôt n'avait encore eu besoin de « ce rôle, n'importe où », à l'exception de `SUPER`
(`est_super_administrateur`, extrait par la `T12` du LOT 9 pour la création d'entité, qui n'a elle
non plus aucune entité à consulter). `T13` **étend ce même patron** à `ADM-E` et `ESM` — deux
nouvelles fonctions, `_est_administrateur_d_entite_quelque_part`/`_est_esm_quelque_part`
(`app/support/perimetre_alertes.py`), reprenant EXACTEMENT la forme de requête
d'`est_super_administrateur` (même `SELECT EXISTS`), simplement sans le filtre `entity_id` que
`ADM-E`/`ESM` portent d'ordinaire. Ce n'est pas une règle inventée : c'est la seule lecture
techniquement cohérente d'une grille Entité/Global appliquée à une ressource qui n'a pas d'entité.

## 2.2 « Limité fonctionnel » (`ESM`) est lu par analogie avec la « lecture fonctionnelle » de `T12`

La matrice §17 écrit, pour l'`ESM`, « **Limité fonctionnel** » sur la ligne « Consulter les
alertes de sécurité » — pas seulement « Limité », qu'elle réserve juste au-dessus à « Consulter
les KPI techniques ». C'est le MÊME adjectif que la « lecture fonctionnelle » de
`PerimetreDesSignalements` (`T12`), qui masque un « contexte technique non sensible » nommé par le
backlog `US005`.

`operational_alert` n'a pas de backlog qui nomme ses champs techniques un par un, mais le modèle
distingue déjà ce qui EST technique de ce qui est l'état MÉTIER d'une alerte :

- `source` — vocabulaire OUVERT nommant le sous-système émetteur (« API, worker, security,
  backup, Uptime Kuma », §21.2) : un détail de plomberie de supervision, jamais lu par un humain
  qui veut savoir si quelque chose est cassé ;
- `fingerprint` — une clé de déduplication opaque, jamais signifiante pour un lecteur ;
- contre `severity`/`state`/les trois horodatages/l'assignation, qui disent CE QUI est cassé,
  depuis quand, et si quelqu'un s'en occupe — l'essentiel fonctionnel.

`T13` applique donc le même principe que `T12`, par **analogie textuelle** plutôt qu'inventé :
l'`ESM` lit TOUTES les alertes (aucun filtrage par rangée n'étant possible, voir §2.1) avec
`source`/`fingerprint` masqués, jamais les colonnes métier. Déclaré séparément de
`a_la_lecture_complete` du module `app.support.perimetre` (signalements) — même discipline que
`ROLES_D_EXPORT_DE_L_AUDIT` contre `ROLES_DES_DETAILS_TECHNIQUES` à `T9` : une analogie n'est pas
une identité à lier au silence.

## 2.3 Aucun plancher `Soi` — à la différence des signalements

`PerimetreDesSignalements` (`T12`) dégrade toujours vers `SOI` pour une session sans rôle étendu,
parce que les trois lignes du §17 propres aux signalements ne portent aucun tiret total.
Les trois lignes propres aux alertes sont différentes : `DSM`/`BOOST`/`OFFICE` y portent un tiret
plein sur les trois, et `EMP` n'a même pas de colonne dans cette partie du tableau. Il n'existe
aucune notion de « mes propres alertes » que le corpus décrirait (`assigned_to_person_id` n'est
pas un filtre de visibilité, juste un champ d'assignation). `resoudre_le_perimetre_des_alertes`
rend donc `None` — jamais un repli `Soi` qu'aucune cellule ne nomme — et les routes de lecture
répondent 403.

## 2.4 Aucun motif obligatoire, et ce n'est pas un oubli

Le §18.1/`RIGHTS-017` (fermé par `T7`, `ECART-064`) exige un motif pour « toute intervention du
super-administrateur **dans une entité** ». `operational_alert` ne porte structurellement aucune
entité (§2.1) : la précondition textuelle du §18.1 ne peut donc **jamais** être remplie ici —
aucune action sur une alerte ne peut être « une intervention dans une entité », puisqu'il n'y a
pas d'entité où intervenir. `app.audit.motif.exiger_un_motif_si_necessaire` n'est appelée par
AUCUNE route de ce module : première exemption du genre depuis que `T7` a rendu la règle
permanente, mais elle procède de la même lecture littérale du cahier que `T9` a déjà appliquée
pour exempter une lecture (un export n'est pas une « intervention ») — ici, ce n'est pas la nature
de l'écriture qui exempte, c'est l'absence totale d'entité où « intervenir ».

Conséquence directe : ni `DemandeDAcquittement` ni `DemandeDeResolution` ne portent de champ
`motif` — la version suffit pour l'une, la version et un commentaire facultatif pour l'autre.

## 2.5 Le cycle du §27.5 est lu par le modèle, pas par la prose

Le cahier §27.5 décrit le cycle en PROSE : « ouverte ; acquittée ; commentée ; résolue ; rouverte
automatiquement en cas de récidive. » Mais `operational_alert.state` (modèle §21.2, posé par `T1`)
ne ferme que **trois** valeurs — `open`, `acknowledged`, `resolved` — jamais un quatrième état
« commentée ». Commenter n'est donc PAS une transition d'état : c'est une action INDÉPENDANTE,
superposable à n'importe lequel des trois états réels, confirmée par l'existence même d'
`alert_comment` (modèle §21.3, FK'ée à `operational_alert_id` SEULE) — à la différence du
signalement (`T12`, qui réutilise `audit_event.reason` faute de table dédiée), la matrice porte ici
DEUX verbes distincts (« Acquitter » et « Résoudre ou commenter »), jamais un seul comme pour les
signalements.

**Deux transitions sont restreintes, une ne l'est pas**, et ce n'est pas un diagramme inventé
(aucun n'existe pour cette table, en inventer un au-delà de ce que les noms d'état portent
eux-mêmes serait §6.5) — c'est le SENS des trois noms d'état :

- « Acquitter » n'est offert que depuis `open` — acquitter une alerte déjà résolue ou déjà
  acquittée n'a pas de sens opérationnel, et le §27.5 nomme l'acquittement comme précédant la
  résolution, jamais l'inverse ;
- « Résoudre » est offert depuis `open` OU `acknowledged` — rien n'exige l'acquittement préalable,
  et une résolution directe (on corrige immédiatement sans étape d'acquittement formel) est un cas
  réel ; seule une alerte déjà résolue refuse ;
- « Commenter » n'a AUCUNE précondition d'état — une note d'investigation est utile à tout moment
  du cycle, y compris après résolution (suivi a posteriori).

Le commentaire, qu'il soit ajouté seul (`POST .../commentaires`) ou joint à une résolution
(`POST .../resolution`, champ `commentaire` facultatif), vit UNE SEULE FOIS dans `alert_comment` —
jamais dupliqué dans `audit_event.reason`, ce qui créerait deux sources pour la même donnée,
divergentes au premier correctif (§7.27). `audit_event` reste le journal des TRANSITIONS
(`alerte_acquittee`/`alerte_resolue`/`alerte_commentee`/`alerte_levee`/`alerte_rouverte`), jamais
le contenu du commentaire lui-même.

## 2.6 `lever_une_alerte` n'a aucune route HTTP, et c'est délibéré

Le §17 ne nomme AUCUNE ligne « Ouvrir une alerte » dans la matrice : l'ouverture (et sa
réouverture automatique en cas de récidive) vient du système de supervision (Uptime Kuma, LOT 13)
ou du code applicatif qui détecte une condition (disque, sauvegarde, e-mail), jamais d'un geste
humain via l'API. Construire une route que la matrice ne nomme pas inventerait un droit que
personne n'a demandé. `lever_une_alerte` (`app.support.traitement_alertes`) est donc une fonction
de **service pure**, exercée directement par les tests et réservée au câblage futur — même nature
que les fonctions internes non câblées à une route propre du LOT 9 (`_accorder_les_responsabilites`,
etc., `T7`).

**Réouverture = la MÊME ligne repasse à `open`**, jamais une seconde (le modèle l'exige par son
index UNIQUE sur `fingerprint`, qui « permet la réouverture ET la déduplication », §21.2) : les
horodatages `acknowledged_at`/`resolved_at` du cycle PRÉCÉDENT sont remis à `NULL` — ils
décrivaient un cycle désormais clos, les garder laisserait croire qu'ils décrivent le cycle
courant. L'historique complet n'est pas perdu : `audit_event` porte l'ancien état avant chaque
transition, réouverture comprise (`action_code="alerte_rouverte"`, `old_values`/`new_values`
exacts).

`assigned_to_person_id` reste un **paramètre** du service, jamais une valeur câblée en dur : « Jonathan
est affecté par défaut en local » (backlog `US007`) est un fait d'EXPLOITATION — qui reçoit les
alertes dans CET environnement — pas une règle de ce service générique. Câbler un e-mail ou un
identifiant en dur dans une fonction de domaine mélangerait une identité d'environnement avec une
logique métier réutilisable ; l'assignation par défaut reste une décision du câblage futur
(LOT 13), qui connaîtra la configuration réelle.

## 2.7 Un test existant corrigé : une hypothèse rendue fausse par cette sous-étape

`test_garde_de_role.py::test_le_nom_du_parametre_de_chemin_est_celui_du_CONTRAT` (LOT 4, `T9`)
exigeait que TOUT gabarit paramétré du manifeste de contrat porte `{code}` — une hypothèse VRAIE
tant que la seule route entité-less paramétrée du dépôt
(`/bug-reports/{signalement}/historique`, `/etat`) portait AUSSI `{code}` dans le MÊME chemin.
`/alerts/{alerte}` est la PREMIÈRE route à porter un paramètre de chemin sans jamais porter
`{code}`, puisqu'aucune `exiger_un_role_dans_l_entite` ne la garde (§2.1). Corrigé par une
exclusion EXPLICITE et documentée (`_PREFIXES_SANS_GARDE_D_ENTITE`), jamais un filtre élargi qui
masquerait une vraie faute de frappe ailleurs — zéro régression confirmée par comparaison de
worktree avant et après le correctif.

**Aucun arbitrage de Jonathan n'a été nécessaire** pour l'ensemble de `T13` : chaque question est
réglée par dérivation du corpus (§2.1 à §2.6) ou par extension documentée d'un patron déjà validé
ailleurs dans ce dépôt.

---

# 3. Ce que la sous-étape a produit

## 3.1 `app/support/perimetre_alertes.py` — nouveau module

`PerimetreDesAlertes` (`COMPLET`/`LIMITE`, aucun troisième membre pour un refus — `None` le porte).
`ROLES_DE_TRAITEMENT_DES_ALERTES` (`ADM-E`/`SUPER`, les deux verbes d'écriture partageant
exactement la même grille). `resoudre_les_roles_pour_les_alertes` (l'équivalent entité-less de
`resoudre_les_permissions`, pour les trois seuls rôles concernés). `resoudre_le_perimetre_des_alertes`/
`a_la_lecture_complete`.

## 3.2 `app/support/traitement_alertes.py` — nouveau module

`lister_les_alertes`/`lire_une_alerte`/`lister_les_commentaires` (lecture, masquage selon le
périmètre). `lever_une_alerte` (service seul, ouverture/réouverture). `acquitter_une_alerte`/
`resoudre_une_alerte`/`ajouter_un_commentaire` (écriture, verrou optimiste `SELECT ... FOR UPDATE`
→ vérification de version → `UPDATE ... RETURNING` → `enregistrer_un_evenement`, même patron
qu'`archiver_un_cercle`, LOT 9 `T4`).

## 3.3 `app/support/routes.py` — six routes nouvelles

`GET /alerts` (liste, pagination §18.2, filtre `etat`), `GET /alerts/{alerte}` (détail),
`GET /alerts/{alerte}/commentaires` (liste), `POST /alerts/{alerte}/acquittement`,
`POST /alerts/{alerte}/commentaires`, `POST /alerts/{alerte}/resolution` — toutes protégées par les
deux barrières CSRF pour les écritures (`_proteger`, réutilisée, jamais recopiée).

## 3.4 `apps/api/tests/test_garde_de_role.py` — correctif

Exclusion explicite documentée des chemins `/api/v1/alerts` du contrôle « tout gabarit paramétré
porte `{code}` » (§2.7).

## 3.5 Contrat

`packages/contracts/src/contrat-api.json` étendu de 95 à 101 chemins (`alertes`, `uneAlerte`,
`commentairesDUneAlerte`, `ajouterUnCommentaireAUneAlerte`, `acquittementDUneAlerte`,
`resolutionDUneAlerte`). Aucun module TypeScript propre — aucun écran consommateur avant `T15`,
même discipline que `T8`/`T9`/`T10`/`T12`.

---

# 4. Contrôles exécutés

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
pnpm -r exec tsc --noEmit && pnpm exec eslint . && pnpm exec prettier --check .
uv run pytest apps/api/tests/test_traitement_alertes.py -q
uv run pytest -q
make test-frontend
make docs-check
make sources-check
make isolation-check
make migrations-check
make parametres-check
```

**Résultats :**

- `uv run ruff check`/`format --check` : vert, dépôt entier.
- `uv run mypy` : vert, 270 fichiers (+3 : `perimetre_alertes.py`, `traitement_alertes.py`,
  `test_traitement_alertes.py`).
- `pnpm -r exec tsc --noEmit`/`eslint .`/`prettier --check .` : verts.
- `apps/api/tests/test_traitement_alertes.py` : **54 tests, 54 passés** (11 unitaires, 43
  d'intégration).
- `uv run pytest -q` (racine, dépôt entier) : **1 939 collectés** (+54 par rapport à `T12`),
  **1 862 passés, 77 échecs** — comparaison de worktree avec `origin/develop` (`a53ef3c`) :
  **77 échecs environnementaux identiques, un par un**, `diff` vide entre les deux listes triées
  après correctif de `test_garde_de_role.py` (§2.7) — la seule différence transitoire avant
  correctif.
- `make test-frontend` : Vitest **812 au total, inchangé** (385 `contracts`, 120 `ui`, 307 `web`) —
  aucun module TypeScript propre, aucun écran consommateur avant `T15`.
- `make docs-check` : 5 documents immuables intacts, 6 séquences d'identifiants cohérentes, 12
  contrôles de totaux dérivés et 12 contrôles sur la passation — tous verts au premier passage
  après mise à jour de `registre-decisions.md`, `docs/README.md` et `CLAUDE.md`.
- `make sources-check` : 703 fichiers source examinés, aucun ignoré hors les deux exceptions
  connues.
- `make isolation-check` : **37 tables locales, 29 clés composites, 0 référence nue** — INCHANGÉ
  (`operational_alert`/`alert_comment` restent globales, posées par `T1`).
- `make migrations-check` : schéma identique, tête `0027` inchangée.
- `make parametres-check` : aucun partage de paramètre fautif dans les requêtes nouvelles.
- `test_contrat.py` : 5/5, manifeste étendu confirmé contre le schéma OpenAPI réellement servi.

**Aller-retour réel effectué** (§7.43 de la passation) après `make code-refresh`, à travers Caddy
en HTTPS, sur la pile Docker réelle (pas seulement `TestClient`) :

1. décor inséré directement dans la base (une personne `SUPER`, une alerte `CRITICAL`/`backup`),
   session réelle ouverte (`ouvrir_une_session`), jeton CSRF calculé (`jeton_pour`,
   `empreinte_de_session`) ;
2. `GET /api/v1/alerts` et `GET /api/v1/alerts/{alerte}` — lecture complète confirmée (`source`,
   `empreinte` présents pour `SUPER`) ;
3. `POST .../acquittement` (version 1 → 2, état `acknowledged`) ;
4. `POST .../commentaires` (contenu inséré, relu par `GET .../commentaires`) ;
5. `POST .../resolution` (version 2 → 3, état `resolved`, avec un second commentaire joint) ;
6. **réouverture automatique** : un second appel à `lever_une_alerte` (service, même empreinte)
   depuis un script exécuté dans le conteneur — la MÊME ligne repasse à `open`
   (`reouverture=True`, version 4), confirmée par une relecture HTTP (`acquittee_le`/`resolue_le`
   remis à `null`) — la démonstration littérale du cahier Annexe C, « résolution puis réouverture
   automatique d'une alerte récurrente » ;
7. `audit_event` confronté ligne par ligne : `alerte_acquittee` → `alerte_commentee` →
   `alerte_resolue` → `alerte_rouverte`, `reason` toujours vide (le commentaire vit SEULEMENT dans
   `alert_comment`) ;
8. refus CSRF confirmé en 403 sans l'en-tête `X-Csrf-Token` ;
9. décor nettoyé (personne, alerte, commentaires, audit_event, session).

---

# 5. Décisions et écarts

**`DEC-667`** — ce compte rendu. Aucun écart ouvert ni fermé par cette sous-étape. `QO-092` et les
autres questions/écarts déjà ouverts du LOT 10 restent inchangés, non bloquants pour `G10`.

---

# 6. Ce que `T13` laisse

- aucun écran consommateur — `T15` construira les écrans back-office (audit/reporting/support),
  qui consommeront ces six routes dans un onglet dédié ;
- le câblage réel avec Uptime Kuma (seuils de production, canaux de notification, cahier §27) et
  l'assignation par défaut à Jonathan en environnement local restent hors périmètre — LOT 13, où
  la production temporaire existera réellement ;
- `T14` (le suivi d'une demande de droit RGPD, `data_subject_request`) est la sous-étape suivante.

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arrière
```
