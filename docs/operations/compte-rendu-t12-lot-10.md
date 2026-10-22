# Compte rendu — `T12` du LOT 10 : le traitement des signalements

**Sous-étape :** la douzième du lot — consultation et traitement des signalements de bug
**Date :** 22 octobre 2026
**Décision :** `DEC-666`
**Story :** `MVP-L10-US006`

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 10**, ouvert le 14/10/2026 (`DEC-654`), **seize** sous-étapes |
| Faites | `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7`, `T8`, `T9`, `T10`, `T11`, **`T12`** |
| Restent | `T13` à `T16` |
| Issues | épic `#267`, story `#273` |

---

# 2. Ce que le corpus décidait déjà, et ce qui restait à faire

## 2.1 Le périmètre de lecture, dérivé matrice §17 ligne par ligne

Trois lignes du §17 après « Reporter un bug » (`T11`) :

```
Consulter ses signalements                Soi   Soi   Soi   Soi   Entité   Global
Consulter les signalements de l'entité     —    Lecture fonctionnelle  —   —   Entité   Global
Modifier l'état d'un signalement           —     —     —     —    Entité   Global
```

(colonnes `DSM`/`ESM`/`BOOST`/`OFFICE`/`ADM-E`/`SUPER`.)

**« Consulter ses signalements » ne porte aucun tiret** : les six rôles reçoivent tous quelque
chose, `Soi` au plancher — même motif que `PerimetreDuSuivi` (LOT 7, `T12`) : `Soi` est le plancher
universel de n'importe quelle session établie, pas une conséquence d'un rôle précis, cohérent avec
« Reporter un bug » qui est déjà universel. **« Modifier l'état d'un signalement » porte quatre
tirets sur six** : cette fois l'absence de colonne `EMP`/`NEW` se lit normalement, comme refus.

La résolution est donc au rôle le plus large détenu : `SUPER` → `GLOBAL`, `ADM-E` → `ENTITE_COMPLETE`,
`ESM` → `ENTITE_FONCTIONNELLE`, tout le reste → `SOI`. Jamais un refus — même motif que
`resoudre_le_perimetre_du_suivi`.

## 2.2 `QO-092` résolue par la matrice, pas arbitrée

Le registre ouvrait `QO-092` : « le cahier ne dit pas si un signalement part vers Jonathan seul ou
vers un canal eXalt plus large ». La matrice §17 — **verrouillée depuis le 25 juillet 2026**,
« référence fonctionnelle » que seule une nouvelle décision explicite peut modifier — règle déjà la
destination EN APPLICATION : `ADMINISTRATEUR_D_ENTITE` (dans son entité) ET `SUPER_ADMINISTRATEUR`
(globalement), jamais « Jonathan seul » au sens propre — n'importe quel `ADM-E` d'une entité peut
traiter les signalements de SA entité. Le cahier confirme par une phrase distincte, dans sa section
« Support » : « visibilité du super-administrateur » — qui ne contredit pas la matrice, elle en
nomme juste un cas.

Aucun canal externe (e-mail, Teams, billetterie) n'est décrit nulle part pour les signalements —
à la différence des alertes, qui nomment explicitement Uptime Kuma comme SOURCE externe (§21.2) —
et ce lot ne pose aucune infrastructure de notification (`async_job`, LOT 11). `QO-092` reste donc
ouverte au registre pour son seul volet réellement indécidé — un canal de notification futur, hors
périmètre de ce lot — mais ne bloquait rien ici : l'implémentation ne dépend d'aucune réponse à ce
volet, elle découle entièrement de la matrice.

## 2.3 « Commentaires et historique » : servis par l'audit, pas par une table dédiée

Le backlog `US006` : « États nouveau, en analyse, corrigé et rejeté ; compteur back-office ;
commentaires et historique. » Les quatre états existent depuis `T1` (`EtatSignalement`). Le
« compteur back-office » est la pagination du §18.2 elle-même : une liste filtrée par état rend
déjà son `total`, jamais une route séparée qui pourrait diverger du compte réel (§7.27).

« Commentaires et historique » n'a PAS de table dédiée : `alert_comment` (modèle §21.3) est FK'ée à
`operational_alert_id` SEULE — « commentaires d'acquittement et de résolution » d'une ALERTE, jamais
d'un signalement. Construire une seconde table de commentaires pour `bug_report` inventerait une
capacité que le §17 ne nomme nulle part comme une ligne séparée : à la différence des alertes, qui
portent DEUX verbes distincts (« Acquitter » et « Résoudre ou commenter une alerte », `T13`), les
signalements n'en portent qu'UN SEUL — « Modifier l'état d'un signalement ». Pas de ligne
« commenter sans changer l'état ».

**Réutilisé plutôt qu'inventé** : chaque changement d'état écrit un `audit_event` via le service
générique de `T2`, avec le commentaire porté dans `reason` — même discipline que « le motif de
réouverture porté dans `reason` » (`T6`) et « le motif d'annulation porté dans `reason` » (`T5`).
« Historique » devient alors la SUITE de ces événements pour CE signalement, jamais une seconde
table.

## 2.4 Pourquoi l'historique n'est pas servi par `GET /entities/{code}/audit`

`app.audit.lecture.FiltresDAudit` n'a pas d'axe `resource_reference` (un seul `resource_type`,
jamais un identifiant précis) — et même s'il en avait un, la garde de cette route est
`ROLES_DE_L_AUDIT` (matrice §16, six rôles, axes Consultants/Cercle/Bureau), un périmètre
ENTIÈREMENT DIFFÉRENT de celui du support (`PerimetreDesSignalements`, §17). Un DSM a un périmètre
`Consultants` sur l'audit mais seulement `Soi` sur les signalements : le servir par la route d'audit
violerait le critère de sortie 3 du lot — « les rapports respectent les mêmes droits que les écrans
source ». L'historique d'un signalement est donc une lecture DÉDIÉE, qui interroge `audit_event`
directement (même table, même colonnes) mais vérifie le périmètre DU SUPPORT, jamais celui de
l'audit.

## 2.5 « Lecture fonctionnelle » : les champs techniques, pas une seconde forme

Le modèle §21.4 distingue déjà « saisie utilisateur »/« ajout automatique »
(`description`/`reproduction_steps`/`page_path` contre
`application_version`/`environment`/`browser_summary`/`correlation_token`) — et le backlog `US005`
nomme lui-même ces derniers « contexte technique non sensible ». « Lecture fonctionnelle » pour
l'`ESM` masque exactement ces quatre colonnes techniques, jamais les colonnes métier — même
principe que `a_les_details_techniques` (`app.audit.perimetre`, `T8`), déclaré ICI séparément
plutôt qu'importé : même coïncidence que `ROLES_D_EXPORT_DE_L_AUDIT` contre
`ROLES_DES_DETAILS_TECHNIQUES` (`T9`) — deux lignes distinctes de deux matrices différentes (§16
contre §17), pas une identité conceptuelle à lier au silence.

Qui voit SES PROPRES signalements (`Soi`) voit TOUJOURS les quatre colonnes techniques, y compris
pour `DSM`/`BOOST`/`OFFICE` : ce sont des informations que son propre navigateur a transmises à sa
propre demande.

## 2.6 `ECART-064` s'applique, pas retrofité

`T7` a retrofité le motif obligatoire (`app.audit.motif`) sur la totalité des fonctions câblées par
`T2` à `T6`, portée large explicitement validée par Jonathan — mais la règle qu'il ferme
(`ECART-064`, cahier §18.1, `RIGHTS-017`) est désormais une règle PERMANENTE du projet : « un motif
est obligatoire pour toute intervention du super-administrateur dans une entité », pas seulement
pour les ~25 fonctions nommées à l'époque. « Modifier l'état d'un signalement » est la PREMIÈRE
fonction de `T8` à `T16` qui porte une grille Entité/Global où `SUPER` agit DANS une entité
particulière (les lectures de `T8`/`T9`/`T10` en sont exemptées, §18.1 bornant l'obligation aux
écritures ; `T11` en est exemptée, aucune garde de rôle) — elle applique donc la même règle, avec
le même mécanisme (`exiger_un_motif_si_necessaire`). Le champ `commentaire` du corps sert les
DEUX : le commentaire métier du backlog, ET le motif du §18.1 quand `SUPER` autorise l'appel — un
seul champ, jamais deux redondants.

## 2.7 Aucune transition restreinte

Aucun diagramme d'état (type §24.2 pour l'onboarding) n'existe dans le corpus pour `bug_report`.
Inventer une machine à états serait §6.5 : les quatre états restent donc tous atteignables depuis
n'importe lequel des quatre.

**Aucun arbitrage de Jonathan n'a été nécessaire.**

---

# 3. Ce que la sous-étape a produit

## 3.1 `app/support/perimetre.py` — nouveau module

- `PerimetreDesSignalements` (`GLOBAL`/`ENTITE_COMPLETE`/`ENTITE_FONCTIONNELLE`/`SOI`).
- `resoudre_le_perimetre_des_signalements(roles)` — au rôle le plus large, `Soi` en dernier recours.
- `ROLES_DE_TRAITEMENT_DES_SIGNALEMENTS` = `{ADM-E, SUPER}`.
- `a_la_lecture_complete(perimetre)` — `False` seulement pour `ENTITE_FONCTIONNELLE`.

## 3.2 `app/support/traitement.py` — nouveau module

- `lister_les_signalements` : page + total, filtrable par `etat`, masquage des quatre champs
  techniques selon le périmètre.
- `signalement_visible` : la même vérification de portée pour la liste et l'historique — jamais
  deux règles qui pourraient diverger.
- `lire_l_historique_d_un_signalement` : lecture directe d'`audit_event`, aucune vérification de
  périmètre (déléguée à l'appelant, même séparation que `app.audit.lecture`).
- `modifier_l_etat_d_un_signalement` : verrou optimiste (`FOR UPDATE`), version du cahier §18.4,
  écriture de `bug_report.state` et de l'`audit_event` dans la MÊME transaction.

## 3.3 `app/support/routes.py` — trois routes nouvelles

- `GET /entities/{code}/bug-reports` — liste périmétrée, pagination §18.2.
- `GET /entities/{code}/bug-reports/{signalement}/historique` — 404 hors périmètre.
- `POST /entities/{code}/bug-reports/{signalement}/etat` — `ADM-E`/`SUPER` seuls, deux barrières
  CSRF, motif obligatoire si `SUPER` autorise l'appel.

## 3.4 Contrat

`packages/contracts/src/contrat-api.json` étendu à 95 chemins (`signalements`,
`historiqueDUnSignalement`, `changementDEtatDUnSignalement`). Aucun module TypeScript propre, même
discipline que `T8`/`T9`/`T10` : aucun écran consommateur avant `T15`.

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `pytest` racine | 1 885 collectés (+35 : 26 d'intégration, 9 unitaires), 1 808 passés / 77 échecs |
| Comparaison de worktree avec `origin/develop` | 77 échecs environnementaux **identiques**, `diff` vide |
| `uv run mypy` (racine) | vert, 267 fichiers (+3) |
| `uv run ruff check`/`format` | vert, dépôt entier |
| Vitest `contracts` | 385, inchangé |
| `make isolation-check` | 37 tables locales, 29 clés composites, 0 référence nue — aucune migration |
| `make migrations-check` | schéma identique, tête `0027` inchangée |
| `make parametres-check` | aucun paramètre lié partagé entre deux types |
| `make docs-check` / `sources-check` | verts |
| `test_contrat.py` | 5/5, manifeste étendu à 95 chemins |

**Trente-cinq tests nouveaux** (`apps/api/tests/test_traitement_signalements.py`) : la résolution du
périmètre pour les huit combinaisons de rôles (cumul compris), le masquage des quatre champs
techniques pour la seule `ENTITE_FONCTIONNELLE` ; `Soi` ne voit que son propre signalement en détail
complet, `ESM` voit toute l'entité sans le contexte technique, `ADM-E`/`SUPER` voient
l'entité/le global en détail complet ; l'isolation inter-entités dans les deux sens (liste et
changement d'état) ; le filtre `etat` comme compteur ; l'historique vide avant tout traitement puis
conforme après, hors du périmètre `Soi` et hors entité en 404 ; le refus 403 pour les cinq rôles
sans droit de traitement ; le refus CSRF (négatif) apparié à chaque succès (positif, §7.39) ; le
motif obligatoire pour `SUPER` sans commentaire (négatif) apparié au même appel avec commentaire
(positif) ; l'absence de cette obligation pour `ADM-E` seul ; la version périmée en 409 ; le
contenu exact de l'`audit_event` écrit.

**Aller-retour réel effectué** (§7.43 de la passation), après `make code-refresh`, à travers Caddy
en HTTPS : un décor réel inséré directement en base (une entité, un DSM reporteur, un `ADM-E`, un
signalement) — la liste consultée par le DSM (`Soi`, contexte technique visible) et par l'`ADM-E`
(détail complet), l'historique initialement vide, un refus 403 pour le DSM sur le changement
d'état, puis un changement d'état réel par l'`ADM-E` avec commentaire (CSRF réel, jeton calculé),
et l'historique relu — conforme : ancien état, nouvel état, commentaire et acteur tous corrects.
Décor nettoyé après coup.

---

# 5. Décisions et écarts

`DEC-666` consigne cette sous-étape. Aucun écart ouvert ni fermé. `QO-092` reste ouverte au
registre pour son seul volet hors périmètre (canal de notification externe, LOT 11/13) ; son volet
applicatif (qui traite un signalement) est résolu par la matrice, documenté en §2.2 ci-dessus.

---

# 6. Ce que `T12` laisse

- **Les alertes opérationnelles** restent `T13` — `US007`, cycle ouverture/acquittement/
  commentaire/résolution/réouverture, suivi applicatif seul (pas l'intégration Uptime Kuma, LOT 13).
- **Les écrans back-office** (audit, reporting, support) restent `T15` — aucun écran ne consomme
  encore les trois routes de ce module.

---

**Validation demandée à Jonathan.**

```bash
~/.local/bin/gh pr merge <n> --squash --delete-branch   # fusion
~/.local/bin/gh pr close <n> --delete-branch            # retour arrière
```
