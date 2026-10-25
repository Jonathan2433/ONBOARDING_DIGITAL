# Compte rendu — `T14` du LOT 10 : le suivi d'une demande de droit RGPD

**Story :** `MVP-L10-US008` — « Suivre une demande de droit. »
**Décision :** `DEC-668`
**Date :** 22 octobre 2026

---

# 1. État du lot

LOT 10 ouvert le 14/10/2026 (`DEC-654`), découpage validé en seize sous-étapes. `T1` à `T13` sont
faites. `T14` ferme `US008` : la réception, la vérification d'identité, la clôture traçable d'une
demande de droit RGPD (accès, rectification, effacement ou opposition) — cahier §21.5, modèle
§22.3. `T15` (les écrans back-office — audit, reporting, support) est la suivante.

---

# 2. Ce que le corpus décidait déjà, et ce qui restait à faire

## 2.1 Aucune ligne de matrice ne nomme cette ressource — résolu par analogie, jamais arbitré

Le backlog `US008` donne pour acteur « **Responsable RGPD** » — un mot qui ne correspond à AUCUN
des dix codes du §3 de la matrice (`ANON`/`EMP`/`NEW`/`DSM`/`ESM`/`BOOST`/`OFFICE`/`ADM-E`/`SUPER`/
`SERVICE`). Ni la matrice ni le cahier ne portent de section dédiée aux demandes de droit RGPD —
contrairement aux alertes (`T13`) et aux signalements (`T12`), qui ont chacun leurs propres lignes
au §17.

La ligne la plus proche, et la SEULE qui porte sur une action RGPD touchant une personne précise,
est le §18 :

```
Lancer l'anonymisation RGPD   —   —   —   —   Entité contrôlée   Global
```

Cette ligne exclut `DSM`/`ESM`/`BOOST`/`OFFICE` EN BLOC — y compris l'`ESM`, qui reçoit pourtant une
lecture « Limitée fonctionnelle » sur les alertes. `data_subject_request` est le dossier qui
PRÉCÈDE structurellement cette anonymisation : une demande d'effacement aboutie EST ce qui la
déclenche (cahier §22.5, « planification de l'anonymisation à trois mois »). Le même périmètre
s'applique donc au dossier qui la prépare — même lecture que `T9` a déjà appliquée pour réserver
l'export d'audit à `ADM-E`/`SUPER` (une ligne de matrice qui dicte le rôle d'une action ADJACENTE,
pas une invention). **Aucun arbitrage de Jonathan n'a été nécessaire** : la ligne existe déjà,
explicite, et exclut exactement les rôles qu'une gestion de dossier légal individuel exclurait par
principe.

## 2.2 Ressource GLOBALE : `ADM-E` résolu n'importe où, même patron que `T13`

`data_subject_request` ne porte AUCUN `entity_id` (modèle §22.3, posé par `T1` — groupée avec
`operational_alert`/`alert_comment`/`export_request` parmi les quatre tables globales du lot). La
grille Entité/Global ne peut donc pas se lire comme un filtrage par entité : `ADM-E` est résolu DANS
N'IMPORTE QUELLE ENTITÉ, exactement le patron d'`app.support.perimetre_alertes` (`T13`).

**`est_administrateur_d_entite_quelque_part` est PROMUE** depuis `app.support.perimetre_alertes`
(où elle était une fonction privée, `_est_administrateur_d_entite_quelque_part`, son unique
appelant) vers `app.permissions.services`, aux côtés d'`est_super_administrateur` — `T14` en étant
le second appelant. Une fonction recopiée deux fois est exactement ce que le §7.27 de la passation
apprend à partager plutôt qu'à dupliquer : `app.support.perimetre_alertes` a été mis à jour pour
importer et utiliser la version partagée, ses 54 tests existants rejoués sans aucune régression
(voir §4). `_est_esm_quelque_part` reste propre aux alertes, faute d'un second appelant — `T14` n'a
aucun usage de l'`ESM`.

## 2.3 Aucune portée « Soi » NI « Limité » pour l'`ESM` — plus restrictif que les alertes

À la différence des alertes (`T13`, où l'`ESM` reçoit une lecture « Limitée fonctionnelle »),
AUCUNE ligne de matrice ne donne à l'`ESM` de visibilité partielle sur une demande RGPD. Et à la
différence des signalements (`T12`, où `Soi` est un plancher universel pour toute session établie),
aucune route de ce module n'est accessible par simple session : le cahier §21.5 nomme un « canal
officiel RGPD » — un canal EXTERNE (courrier, e-mail au contact RGPD), jamais un bouton dans
l'application. La réception elle-même est un geste du personnel habilité (`ADM-E`/`SUPER`), jamais
un self-service de la personne concernée : une seule garde, `ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD`,
protège TOUTES les routes de ce module, lecture et écriture confondues.

## 2.4 Deux états seulement, vocabulaire ouvert — lu par le modèle, pas deviné

`data_subject_request.state` ne porte AUCUNE `contrainte_enumeration` (modèle §22.3, dont l'en-tête
d'`app/audit/modeles.py` dit explicitement : « ni le §22.3 ni aucune autre section n'en donne le
vocabulaire. Chaîne non vide ») — à la différence d'`operational_alert.state`, fermé par le modèle.
`ETAT_RECU`/`ETAT_CLOS` sont un choix de CE module, UNE SEULE transition (`received` → `closed`).

Le backlog `US008` liste CINQ préoccupations — réception, vérification d'identité, export
structuré, actions, délais, clôture — mais UNE SEULE ferme le dossier. Les autres sont des colonnes
ou des actions ORTHOGONALES, jamais un état de plus (même lecture que « commentée » pour les
alertes, `T13`) :

- **vérification d'identité** → `identity_verified` (booléen), bascule par sa propre action
  (`POST .../verification-identite`), SANS précondition d'état, IDEMPOTENTE — vérifier deux fois
  n'écrit rien de plus, ne produit aucun second `audit_event` ;
- **export structuré / actions** → le texte libre `response`, écrit à la clôture — les ACTIONS
  concrètes sur les données de la personne (rectification, effacement d'un champ...) réutilisent
  les routes DÉJÀ auditées des autres domaines (`T3`-`T7`), ce module tient le DOSSIER qui les
  accompagne, il ne réécrit RIEN de ces écritures ;
- **délais** → `due_at`, calculé UNE SEULE FOIS à la réception, jamais modifié.

Inventer des états intermédiaires (« en_cours », « en_vérification »...) que rien ne nomme serait
le défaut §6.5 — un diagramme que le corpus ne porte pas.

## 2.5 `due_at` : le délai d'un mois est un fait légal externe, pas une règle à arbitrer

Le RGPD (article 12§3) fixe UN MOIS pour répondre à une demande de droit. C'est un FAIT LÉGAL
externe, pas une décision de Jonathan — même nature que `DUREE_DE_RETENTION` de l'audit (un an,
`T2`), elle aussi un défaut documenté plutôt qu'une question posée. `due_at = received_at + 30
jours`, calculé UNE SEULE FOIS depuis le MÊME `instant` que `received_at` — jamais un second
`now()`, même leçon que `creer_un_jeton` (§7.0 sixième proposition de la passation).

## 2.6 « L'export structuré » est un texte, jamais un fichier généré

Le modèle §22.3 ne pose NI colonne média NI référence d'objet pour `data_subject_request` — à la
différence d'`export_request` (modèle §21.5, `T9`), qui en porte une. La seule colonne disponible
pour consigner ce qui a été remis à la personne est `response` (texte libre), écrite à la clôture :
construire un mécanisme de génération de fichier ici inventerait une infrastructure qu'aucune
colonne ne prévoit (§6.5) — le responsable RGPD y résume ce qui a été transmis, hors ligne ou par un
canal propre. `response` n'est JAMAIS dupliqué dans `audit_event.reason`, même discipline que
`alert_comment` pour les alertes (`T13`) : deux sources pour la même donnée divergeraient au premier
correctif (§7.27).

## 2.7 Aucun motif obligatoire, même pour `SUPER`

Le §18.1/`RIGHTS-017` (`ECART-064`, fermé par `T7`) exige un motif pour « toute intervention du
super-administrateur DANS UNE ENTITÉ ». `data_subject_request` ne porte structurellement aucune
entité : la précondition textuelle ne peut jamais être remplie — même exemption qu'`T13` pour les
alertes. `app.audit.motif.exiger_un_motif_si_necessaire` n'est appelée par aucune route de ce
module.

## 2.8 Le `responsable` est toujours l'appelant, aucune réassignation

`responsible_person_id` est TOUJOURS celui qui réceptionne la demande — aucun champ de corps ne
permet de désigner quelqu'un d'autre. Aucun document ne nomme de mécanisme de réassignation d'une
demande déjà créée ; en inventer un serait §6.5. `assigned_to_person_id` pour les alertes (`T13`)
restait un paramètre de SERVICE, jamais exposé par une route faute de route HTTP d'ouverture — ici
la route existe, et le choix le plus simple qui ne tranche aucune question non posée est de fixer
le responsable à l'appelant.

**Aucun arbitrage de Jonathan n'a été nécessaire** pour l'ensemble de `T14` : chaque question est
réglée par analogie documentée avec une ligne de matrice déjà existante, par extension d'un patron
déjà validé, ou par un fait légal externe (RGPD article 12§3).

---

# 3. Ce que la sous-étape a produit

## 3.1 `app/permissions/services.py` — fonction promue

`est_administrateur_d_entite_quelque_part`, extraite d'`app.support.perimetre_alertes` (son unique
appelant jusqu'ici) et rendue publique, aux côtés d'`est_super_administrateur`. `app.support.
perimetre_alertes` mis à jour pour l'importer plutôt que d'en garder une copie privée.

## 3.2 `app/privacy/` — nouveau module

`app/privacy/perimetre.py` : `ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD` (`ADM-E`/`SUPER`),
`resoudre_les_roles_pour_les_demandes_rgpd`, `a_le_droit_de_traiter_les_demandes_rgpd` (booléen pur,
aucun périmètre à deux niveaux comme les alertes). `app/privacy/traitement.py` :
`receptionner_une_demande`, `lister_les_demandes`, `lire_une_demande`,
`lire_l_historique_d_une_demande`, `verifier_l_identite` (idempotente), `cloturer_une_demande`
(verrou optimiste `SELECT ... FOR UPDATE` → vérification de version → `UPDATE ... RETURNING` →
`enregistrer_un_evenement`, même patron que `archiver_un_cercle`, LOT 9 `T4`).

## 3.3 `app/privacy/routes.py` — six routes nouvelles

`POST /data-subject-requests` (réception), `GET /data-subject-requests` (liste, pagination §18.2,
filtres `etat`/`type_demande`), `GET /data-subject-requests/{demande}` (détail, `en_retard`
calculé), `GET .../historique`, `POST .../verification-identite`, `POST .../cloture` — toutes
protégées par les deux barrières CSRF pour les écritures (`_proteger`, réutilisée, jamais
recopiée), toutes gardées par la MÊME garde coarse (`ROLES_DE_TRAITEMENT_DES_DEMANDES_RGPD`),
lecture et écriture confondues.

## 3.4 `apps/api/tests/test_garde_de_role.py` — exclusion étendue

`_PREFIXES_SANS_GARDE_D_ENTITE` étendue à `/api/v1/data-subject-requests`, même motif structurel
qu'`/api/v1/alerts` (`T13`) : ressource globale, paramètre de chemin sans jamais porter `{code}`.

## 3.5 Contrat

`packages/contracts/src/contrat-api.json` étendu de 101 à 107 chemins (`demandesRGPD`,
`demandesRGPDEnListe`, `uneDemandeRGPD`, `historiqueDUneDemandeRGPD`,
`verificationIdentiteDUneDemandeRGPD`, `clotureDUneDemandeRGPD`). Aucun module TypeScript propre —
aucun écran consommateur avant `T15`, même discipline que `T8`/`T9`/`T10`/`T12`/`T13`.

---

# 4. Contrôles exécutés

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
pnpm -r exec tsc --noEmit && pnpm exec eslint . && pnpm exec prettier --check .
uv run pytest apps/api/tests/test_demandes_rgpd.py apps/api/tests/test_traitement_alertes.py -q
uv run pytest -q
make test-frontend
make docs-check
make sources-check
make isolation-check
make migrations-check
```

**Résultats :**

- `uv run ruff check`/`format --check` : vert, dépôt entier.
- `uv run mypy` : vert, 275 fichiers (+5 : `app/privacy/__init__.py`, `perimetre.py`,
  `traitement.py`, `routes.py`, `test_demandes_rgpd.py`).
- `pnpm -r exec tsc --noEmit`/`eslint .`/`prettier --check .` : verts.
- `apps/api/tests/test_demandes_rgpd.py` : **47 tests, 47 passés** (10 unitaires, 37 d'intégration).
- `apps/api/tests/test_traitement_alertes.py` (les 54 tests de `T13`) : **54 passés**, zéro
  régression après la promotion d'`est_administrateur_d_entite_quelque_part` (§2.2, §3.1).
- `uv run pytest -q` (racine, dépôt entier) : **1 986 collectés** (+47 par rapport à `T13`), **1 909
  passés, 77 échecs** — comparaison de worktree avec `origin/develop` (`5a34bc4`, `.env` du dépôt
  copié dans le worktree pour reproduire la même configuration que la stack réelle) : **77 échecs
  environnementaux identiques, un par un**, `diff` vide entre les deux listes triées.
- `make test-frontend` : Vitest **812 au total, inchangé** (385 `contracts`, 120 `ui`, 307 `web`) —
  aucun module TypeScript propre, aucun écran consommateur avant `T15`.
- `make docs-check` : 5 documents immuables intacts, 6 séquences d'identifiants cohérentes, 12
  contrôles de totaux dérivés et 12 contrôles sur la passation — tous verts après mise à jour de
  `registre-decisions.md`, `docs/README.md` et `CLAUDE.md`.
- `make sources-check` : aucun fichier source ignoré, hors les deux exceptions connues.
- `make isolation-check` : **37 tables locales, 29 clés composites, 0 référence nue** — INCHANGÉ
  (`data_subject_request` reste globale, posée par `T1`).
- `make migrations-check` : schéma identique, tête `0027` inchangée.
- `test_contrat.py` : 5/5, manifeste étendu confirmé contre le schéma OpenAPI réellement servi.

**Aller-retour réel effectué** (§7.43 de la passation) après `make code-refresh`, à travers Caddy en
HTTPS, sur la pile Docker réelle (pas seulement `TestClient`) :

1. décor inséré directement dans la base (une entité, une personne `ADM-E`, une personne
   « sujet »), session réelle ouverte (`ouvrir_une_session`), jeton CSRF calculé (`jeton_pour`,
   `empreinte_de_session`) ;
2. `POST /api/v1/data-subject-requests` — réception réelle (`201`, état `received`, `due_at` =
   `received_at` + 30 jours exactement, `responsable` = l'`ADM-E` appelant) ;
3. `GET /api/v1/data-subject-requests` et `GET .../{{demande}}` — la demande listée et lue,
   `en_retard` à `False` ;
4. refus CSRF confirmé en `403` sans l'en-tête `X-Csrf-Token` ;
5. `POST .../verification-identite` (version 1 → 2, `identite_verifiee` à `True`) ;
6. `POST .../cloture` (version 2 → 3, état `closed`, `reponse` enregistrée) ;
7. `GET .../historique` — les TROIS événements relus dans l'ordre le plus récent d'abord
   (`demande_rgpd_cloturee` → `demande_rgpd_identite_verifiee` → `demande_rgpd_receptionnee`) ;
8. `audit_event` confronté ligne par ligne par relecture SQL directe : les trois `action_code`
   exacts, `reason` TOUJOURS `NULL` (la réponse de clôture vit SEULEMENT dans `response`, jamais
   dupliquée) ;
9. décor nettoyé (entité, personnes, session, `data_subject_request`, `audit_event`).

---

# 5. Décisions et écarts

**`DEC-668`** — ce compte rendu. Aucun écart ouvert ni fermé par cette sous-étape. Les
questions/écarts déjà ouverts du LOT 10 (`QO-092`, `QO-126`) restent inchangés, non bloquants pour
`G10`.

---

# 6. Ce que `T14` laisse

- aucun écran consommateur — `T15` construira les écrans back-office (audit/reporting/support), qui
  consommeront ces six routes dans un onglet dédié ;
- aucun mécanisme de réassignation du `responsable` d'une demande déjà créée — aucun document ne le
  nomme, résidu documenté (§2.8) ;
- `privacy_notice_version`/`privacy_notice_acknowledgement`/`retention_action` (modèle §22.1/§22.2/
  §22.4) restent hors périmètre — aucune des huit stories du LOT 10 ne les nomme, posé par `T1` ;
- `T15` (les écrans back-office — audit, reporting, support) est la sous-étape suivante, puis `T16`
  (recette de clôture, classement du §30, checklist `G10`).

```bash
gh pr merge <n> --squash --delete-branch   # fusion
gh pr close <n> --delete-branch            # retour arrière
```
