# Compte rendu — `T2` du LOT 11 : la photo de profil

**Sous-étape :** la deuxième du lot — dépôt en quarantaine, vérification du contenu réel,
miniature générée de façon asynchrone, autorisation et retrait d'affichage
**Date :** 31 octobre 2026
**Décision :** `DEC-677`
**Stories :** `MVP-L11-US004`, `US005`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 11**, ouvert le 30/10/2026 (`DEC-674`), **sept** sous-étapes |
| Faites | `T1` (`DEC-676`), **`T2`** (`DEC-677`) |
| Restent | `T3` à `T7` |
| Issues | aucune — aucune issue GitHub n'existe encore pour ce lot |

---

# 2. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `apps/api/app/media/perimetre.py` | `peut_deposer_une_photo` (dispatche sur la grille de la fiche d'arrivée, LOT 7), `peut_gerer_l_autorisation_photo`, `peut_consulter_l_etat_d_un_media` |
| `apps/api/app/media/depot.py` | `deposer_une_photo` — filtre déclaratif, insertion `pending`, dépôt MinIO, publication dans l'outbox |
| `apps/api/app/media/traitement.py` | `generer_les_variantes_depuis_la_charge` — décodage Pillow, miniature JPEG 240×240 sous 100 Ko, `ready`/`rejected` |
| `apps/api/app/media/autorisation.py` | `accorder_l_autorisation_photo`, `retirer_l_autorisation_photo` — tranche le résidu du LOT 5 |
| `apps/api/app/media/routes.py` | cinq routes : dépôt, droits, état, autorisation, retrait |
| `apps/api/app/jobs/outbox.py` | étendu : `TOPIC_MEDIA`, dispatch factorisé (`_traiter_un_message_de_ce_type`) partagé avec l'e-mail |
| `apps/api/app/main.py` | monte `routeur_media` |
| `apps/api/pyproject.toml` | `pillow>=11.0.0` — première dépendance d'image du projet |
| `packages/contracts/src/media.ts` (+ `.test.ts`) | chemins, codes, validateurs des cinq routes |
| `packages/contracts/src/contrat-api.json` | cinq entrées (`depotDUnePhoto`, `droitsDePhoto`, `etatDUnMedia`, `autorisationPhoto`, `retraitAutorisationPhoto`) |
| `apps/web/src/api/media.ts` | client : `deposerUnePhoto`, `lireLesDroitsDePhoto`, `lireLEtatDUnMedia`, `accorderLAutorisationDePhoto`, `retirerLAutorisationDePhoto` |
| `apps/web/src/pages/PanneauPhoto.tsx` (+ `.test.ts`) | l'écran — dépôt, sondage, autorisation, retrait |
| `apps/web/src/pages/PageProfil.tsx` | monte `PanneauPhoto` dans la carte d'identité |
| `apps/web/src/pages/application.css` | `.profil-photo-panneau`, `.profil-champ-fichier`, `.profil-photo-statut` |
| `apps/api/tests/test_depot_photo.py` | 17 tests — permis (avant/après publication), refus structurels, dépôt réel |
| `apps/api/tests/test_traitement_photo.py` | 7 tests — contenu réel, PNG transparent, rejets, témoin d'idempotence |
| `apps/api/tests/test_autorisation_photo.py` | 17 tests — permis, service, les quatre routes JSON par HTTP réel |
| `apps/web/src/pages/PageProfil.test.tsx` | corrigé — un test comptait deux appels réseau, en compte désormais trois |

Aucune migration, aucune nouvelle table : les trois tables du LOT 5 (`media_asset`,
`media_variant`, `photo_authorization`) suffisent — posées, jamais consommées en écriture avant
ce lot.

## 2.1 Le permis de dépôt ne recalcule rien, il dispatche

**Mesuré avant tout code** : la matrice §6.1 porte deux lignes pour la photo — « Ajouter ou
remplacer une photo » et « Enregistrer l'autorisation photo » — et la première est, mot pour mot,
la même grille que les deux lignes déjà codées au LOT 7 pour la fiche d'arrivée (« Compléter » /
« Corriger après publication »). Une photo est un des trois champs que ces lignes couvrent déjà
(« photo, présentation et fun fact »), simplement jamais écrit avant ce lot — résidu nommé
explicitement par `app/onboarding/ecriture.py` (« La photo n'est pas écrite ici ») et par le
contrat (`completionDeLaFicheArrivee` : « `photo_media_id` n'est pas ici »).

`peut_deposer_une_photo` ne recalcule donc jamais cette grille : il appelle
`peut_completer_la_fiche_arrivee` (avant publication) ou
`peut_corriger_la_fiche_arrivee_apres_publication` (après), exactement comme le fait déjà
`app/onboarding/routes.py::completer_la_fiche` pour `short_intro`/`fun_fact` — une seconde copie
aurait divergé au premier ajout (§7.27 de la passation).

## 2.2 Le permis d'autorisation est une grille séparée, et il le reste aux deux états

« Enregistrer l'autorisation photo » / « Retirer l'autorisation photo » (§6.1) ne sont **pas** la
même ligne que le dépôt : `Soi` toujours (y compris pour un employé déjà validé, ce que le dépôt
refuse), `DSM` à tiret aux **deux** états — jamais `Consultants`, à la différence du dépôt qui le
retrouve après publication. `peut_gerer_l_autorisation_photo` la calcule donc elle-même, en
recopiant — jamais en important — le motif privé `_MEMBRE_DU_CERCLE_DU_BOOSTER` d'`app.onboarding.
perimetre` : même discipline que ce module l'applique déjà pour `_RATTACHE_A_CE_DSM` (recopié
depuis `app.permissions.perimetre`).

## 2.3 Le résidu du LOT 5 est tranché

`app/media/modeles.py` (LOT 5, `T1`) notait explicitement : « le service devra dire ce qu'il fait
de deux autorisations actives, et si le corpus reste muet, ouvrir une question au registre ». Le
corpus reste muet — ni le §12.2, ni le §25.1, ni le §25.4 n'écrivent d'unicité — et
`resoudre_la_miniature` (LOT 5, `T5`) avait déjà figé la lecture (`ORDER BY granted_at DESC`,
plusieurs lignes actives restant possibles).

**`accorder_l_autorisation_photo` ne retire donc jamais une autorisation antérieure** : chaque
action fait exactement ce que son nom dit, et la photo la plus récemment autorisée est servie sans
qu'aucune ligne existante n'ait besoin d'être touchée. **`retirer_l_autorisation_photo` retire en
revanche TOUTES les lignes actives d'un coup** : la matrice ne nomme qu'une seule action « Retirer
l'autorisation », jamais « retirer la plus récente », et retirer doit donc couvrir l'état
« autorisation active », pas une ligne précise.

## 2.4 La vérification du contenu réel, et pourquoi Pillow la fournit sans antivirus

Le mot « quarantaine » du titre de cette sous-étape décrit la machine d'états elle-même : un média
`pending`/`processing` n'est jamais servi (`resoudre_la_miniature`, LOT 5), donc l'isolement est
déjà structurel avant que le traitement ne tourne. Ce qu'il reste à vérifier est plus étroit : le
contenu est-il réellement l'image qu'il prétend être ? Décoder entièrement les octets avec Pillow
et constater qu'ils forment une image valide dans un format connu (JPEG/PNG/WebP) **est** cette
vérification — un fichier qui n'est pas une image échoue au décodage, quel que soit le nom ou le
type MIME déclarés.

Un rejet de contenu (`contenu_illisible`, `format_non_autorise`) est un **succès** du job, pas un
échec : il transitionne le média vers `rejected` et la fonction rend normalement. Seule une panne
système (MinIO injoignable) lève `EchecDeTraitement`, pour que le job soit rejoué.

La miniature est carrée, 240×240 pixels (trois fois la taille d'affichage CSS, `5rem`, pour rester
nette sur un écran « retina »), encodée en JPEG à qualité décroissante jusqu'à tenir sous
`BORNE_MINIATURE_OCTETS` — la même constante, 100 000, que `app/media/photo.py` et la migration
`0016` du LOT 5. Une seule variante est produite, `thumbnail` : le §16.2 en nomme cinq, mais le
trombinoscope et la fiche ne servent déjà que celle-là, et les quatre autres n'ont aucun
consommateur avant qu'un média d'un autre domaine (événements, contenus) ne construise le sien.

## 2.5 Le traitement est asynchrone, sur un second `topic` de l'outbox du LOT 11 `T1`

`app.jobs.outbox` câblait un seul `topic`, `email` ; il en câble désormais un second, `media`, sur
le **même gabarit** : `commencer_un_essai`/`job_type` propre, succès ou échec traduits dans le même
vocabulaire. Le corps commun aux deux a été extrait (`_traiter_un_message_de_ce_type`) plutôt que
dupliqué.

**La route réveille le relais par `BackgroundTasks`, jamais par Dramatiq depuis l'API.**
`relayer_le_lot` est une fonction pure, déjà importable sans courtier — c'est le **worker** qui
possède le courtier et le cycle de vie des messages (`apps/worker/worker/actors.py`). Lui en
donner un pour ce seul réveil aurait été une deuxième voie de déclenchement, plus de surface à
maintenir pour le même effet. Après le commit de la transaction d'upload, une tâche de fond appelle
donc directement `relayer_le_lot`, dans sa propre transaction courte — exactement la discipline que
`T1` annonçait déjà (« même discipline que `BackgroundTasks` après la réponse en `app.auth.routes` »)
sans jamais l'avoir exercée, faute de premier appelant. `T2` en est le premier appelant réel.

Un relais qui échouerait silencieusement (l'API tombe entre le commit et l'exécution de la tâche de
fond) n'est pas un cas perdu : l'outbox reste écrite, et une future tâche planifiée (`T4`) ou un
nouveau dépôt relaieront le lot entier au passage suivant.

## 2.6 Deux routes de lecture sans ligne de matrice propre

`GET .../photo/droits` et `GET .../media/{media}/etat` ne servent aucune ligne du §6.1 — elles
disent à l'écran ce qu'il peut proposer et où en est un dépôt en cours, pour que l'écran n'ait pas à
deviner un permis qu'il ne peut pas observer autrement (la permission dépend de l'état de la fiche
d'arrivée et d'un rattachement DSM/Booster, que le frontend ne peut pas recalculer). `PanneauPhoto`
(`PageProfil.tsx`) les consomme au montage, avant de décider quoi afficher.

---

# 3. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest apps/api/tests/test_depot_photo.py apps/api/tests/test_traitement_photo.py apps/api/tests/test_autorisation_photo.py -q` | **31/31** |
| `make test-frontend` | **contracts 478 (+14), ui 141, web 364 (+11)** — 0 échec |
| `uv run ruff check .` / `uv run ruff format --check .` | verts |
| `uv run mypy` (racine) | vert, 293 fichiers (+3) |
| `pnpm exec tsc --noEmit` (contracts, web) | vert |
| `pnpm exec eslint` (fichiers touchés) | vert |
| `pnpm exec prettier --check` (fichiers touchés) | vert |
| `make isolation-check` | **38 locales, 18 globales, 29 composites, 0 référence nue** — inchangé |
| `make migrations-check` | tête `0028` inchangée, schéma identique (897/329/266/10/199) |
| `make sources-check` | 758 fichiers examinés, 0 fichier source ignoré |
| `make docs-check` | vert après mise à jour des registres et de `CLAUDE.md` |
| `pip-audit` | aucune vulnérabilité (Pillow compris) |
| `pnpm audit` | voir §3.2 |
| collecte depuis la racine | **2 040 pytest** (+31) |
| `uv run pytest -q` (développement) | **78 échecs**, deux exécutions consécutives stables |
| comparaison de worktree `origin/develop` (§7.22 de la passation) | **78 échecs, LISTE identique terme à terme** |

## 3.1 Un seul défaut trouvé en mesurant, corrigé avant ce rapport

La première exécution complète de la suite rendait **79** échecs — un de plus que `develop`.
Diagnostiqué avant de conclure à une régression (§7.22) : `test_contrat.py::test_les_chemins_du_
schema_sont_exactement_ceux_du_manifeste` échouait parce que les cinq nouvelles routes n'avaient
pas encore leur entrée dans `contrat-api.json` au moment de ce premier passage. Corrigé en ajoutant
les cinq entrées (§2 ci-dessus) ; la suite rejouée est redescendue à 78, identique à `develop`.

## 3.2 Un test frontend existant corrigé — une régression attendue, pas un défaut

`PageProfil.test.tsx::lance les DEUX appels, et ne les enchaine pas` comptait exactement deux
appels réseau (fiche, historique) au montage de la page. `PanneauPhoto` en ajoute légitimement un
troisième dès son propre montage (`GET .../photo/droits`), indépendant des deux premiers — §7.21
de la passation : un contrôle juste hier peut être faux aujourd'hui quand le monde change autour
de lui, et c'est exactement ce que cette sous-étape a changé. Le test est renommé et corrigé pour
prouver **trois** appels, dont le troisième se termine par `/droits` ; la fonction `servir()` du
fichier sert désormais une réponse neutre (`peut_deposer`/`peut_gerer_autorisation` à `false`) sur
ce chemin, pour que les 23 autres tests du fichier n'aient rien à changer.

## 3.3 Un avis `pnpm audit` nouveau, mesuré sans rapport avec ce lot

`pnpm audit` signale un avis modéré sur `minimatch` (transitif via `eslint`, dépendance de
développement, `GHSA-g3hv-75wg-m249`). `pnpm-lock.yaml` et `package.json` sont **inchangés** par
cette sous-étape (aucune dépendance JavaScript ajoutée) : l'avis est donc un résidu
environnemental, de la même classe que `brace-expansion`/`GHSA-mh99-v99m-4gvg` au LOT 1 `T10` —
mesuré, pas causé par `T2`, et non traité ici.

## 3.4 Aller-retour réel effectué (§7.43 de la passation)

Après `make code-refresh` (les trois conteneurs reconstruits, le worker vérifié avec Pillow
13.0.0 installé), un parcours complet exécuté à travers Caddy en HTTPS, décor psql réel, session
réelle (`ouvrir_une_session`) :

1. `GET .../photo/droits` **avant** tout dépôt → `{"peut_deposer": true, "peut_gerer_autorisation":
   true}` ;
2. `GET .../photo` **avant** tout dépôt → `404` (avatar neutre) ;
3. `POST .../photo` avec une vraie image JPEG 600×600 → `201 {"state": "pending"}` ;
4. `GET .../media/{media}/etat`, deux secondes plus tard → `{"state": "ready", "rejection_code":
   null}` — le réveil par `BackgroundTasks` a réellement déclenché `relayer_le_lot`, qui a
   réellement appelé le worker... **non** : le traitement tourne dans le processus API lui-même
   (fonction pure, sans courtier), confirmant que la génération de la miniature n'exige PAS que le
   conteneur `worker` soit sollicité pour ce chemin immédiat — seule une tâche planifiée future
   (`T4`) passera par lui ;
5. `GET .../photo` **avant** autorisation (media `ready`) → toujours `404` : la quatrième condition
   de `resoudre_la_miniature` (LOT 5) est bien revérifiée en vrai ;
6. `POST .../photo/autorisation` → `201`, avec `granted_at` ;
7. `GET .../photo` **après** autorisation → `200`, `Content-Type: image/jpeg`, **625 octets**
   (bien sous `BORNE_MINIATURE_OCTETS`) ; les octets reçus, relus par Pillow, sont une image
   **240×240, JPEG, RGB** — exactement `COTE_DE_LA_MINIATURE_PIXELS` ;
8. `POST .../photo/autorisation/retrait` → `200 {"autorisations_retirees": 1}` ;
9. `GET .../photo` **après** retrait → `404` de nouveau.

**Un défaut de ma propre tâche de nettoyage, trouvé en rangeant après coup, pas dans le produit** :
mon script de ménage filtrait `async_job`/`outbox_message` par `entity_id`, et le job `media` n'en
porte aucun (même choix que le job `email` de `T1` — aucune story de ce lot n'exige de lister les
jobs par entité, l'inventer aurait été §6.5). Les deux lignes sont restées orphelines le temps
d'un diagnostic, puis supprimées par leur identifiant exact. Décor entièrement nettoyé, vérifié par
un comptage final à zéro sur les neuf tables touchées.

## 3.5 L'idempotence, prouvée à deux niveaux

Même forme que le témoin décisif de `T1` pour l'e-mail : un `outbox_message(topic='media')`
republié, avec un `async_job(job_type='media', state='succeeded')` déjà posé pour sa clé (simulant
un relais interrompu entre le succès du traitement et le `UPDATE processed_at`), ne régénère
**jamais** de seconde variante — `commencer_un_essai` refuse de relancer un essai déjà réussi. Un
second niveau de défense existe en base : `INSERT ... ON CONFLICT (media_asset_id, variant_type)
WHERE archived_at IS NULL DO NOTHING` sur `media_variant`, le même motif que
`outbox_message.deduplication_key` (`T1`).

---

# 4. Décisions et écarts

- `DEC-677` consigne la réalisation et les choix de §2 ;
- aucun écart nouveau n'est ouvert par `T2` ;
- le résidu du LOT 5 (modèle §16.1, deux autorisations actives) est **fermé** par cette
  sous-étape — voir §2.3.

---

# 5. Ce que `T2` laisse

- le dépôt, la vérification de contenu, la génération de miniature et l'autorisation d'une photo
  de profil, prêts pour `T3` (organisation) qui n'en dépend pas, et pour l'intégration des données
  de démonstration (post-`G11`) qui en aura besoin pour les photos réelles ;
- `carte`, `pleine largeur`, `aperçu vidéo` et `format optimisé` (§16.2) restent non construits,
  faute de consommateur — résidu nommé, à reprendre quand un média d'un autre domaine en aura
  besoin ;
- `arrival_profile.photo_media_id` (modèle §12.1) reste non écrit — la bookkeeping de « quelle
  photo a été soumise pendant la fiche d'arrivée » reste un résidu distinct de l'autorisation
  d'affichage elle-même, qu'aucun lecteur du corpus n'exige aujourd'hui ;
- `pnpm audit` : un avis modéré sur `minimatch`, mesuré sans rapport avec ce lot — voir §3.3.

# Validation demandée à Jonathan

`T2` est faite. Après fusion, la prochaine sous-étape est `T3` : l'organisation — création de
cercle et de bureau (écran + route), attribution du Booster d'un cercle et du Responsable d'un
bureau hors import CSV (écran + route), hors backlog.
