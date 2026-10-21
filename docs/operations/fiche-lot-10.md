# Fiche de lot — LOT 10

**Intitulé :** Audit, reporting, supervision fonctionnelle et support
**Épic :** `MVP-L10` — issue `#267`
**Ouvert par Jonathan le :** 14 octobre 2026
**État :** **OUVERT** — `DEC-654`; découpage validé en seize sous-étapes, `T1`/`T2`/`T3`/`T4`/`T5`/`T6`/`T7`/`T8`/`T9` faites
**Sous-étape suivante :** `T10` — Reporting étendu, compteurs et tableaux du §15.1/§10.10
**Porte de sortie :** `G10`, tag attendu `v0.10.0`

> Tous les nombres de cette fiche sont dérivés des sources citées. Recompter avant de les
> réutiliser : une copie manuelle devient fausse dès la première évolution (`ECART-021`).

---

# 1. Ce que le lot doit produire

## 1.1 Les huit stories du backlog

```bash
grep -cE '^\| `MVP-L10-US[0-9]{3}`' docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md
```

| Story | Priorité | Taille | Objet | Dépend de | Issue |
|---|---|---|---|---|---:|
| `MVP-L10-US001` | `P0` | XL | Consulter un journal d'audit filtrable | `L03`-`L09` | `#268` |
| `MVP-L10-US002` | `P0` | L | Appliquer la politique de contenu et de conservation de l'audit | `US001` | `#269` |
| `MVP-L10-US003` | `P0` | XL | Consulter les indicateurs collaborateurs et onboarding | `L05`,`L07`,`L09` | `#270` |
| `MVP-L10-US004` | `P1` | M | Exporter l'audit en CSV | `US001` | `#271` |
| `MVP-L10-US005` | `P0` | L | Reporter un bug depuis l'application | `L04` | `#272` |
| `MVP-L10-US006` | `P1` | M | Traiter les signalements utilisateurs | `US005` | `#273` |
| `MVP-L10-US007` | `P1` | L | Suivre les alertes fonctionnelles importantes | `L01`,`L11` | `#274` |
| `MVP-L10-US008` | `P0` | L | Suivre une demande de droit (RGPD) | `L02`,`L05` | `#275` |

Le lot porte **cinq stories `P0` et trois `P1`**, deux `XL` (`US001`, `US003`). Les trois `P1`
restent dans le périmètre ouvert : le backlog n'autorise leur report qu'avec un arbitrage
explicite à la porte.

## 1.2 Les six critères de sortie, concordants dans la roadmap et le cahier

La roadmap (`ROADMAP_MVP_V1_V2_EXALT.md`, §LOT 10) et le cahier
(`CAHIER_DES_CHARGES_EXALT_BORDEAUX.md`, Annexe C, §LOT 10) portent le **même texte**, mot pour
mot, pour ces six critères — deux sources qui concordent, pas une invention.

| # | Critère | Preuve attendue |
|---:|---|---|
| 1 | les événements sensibles sont atomiques avec l'action métier | écriture dans la MÊME transaction que l'action, `T2` à `T7` ; témoin dédié à `T16` (`§30.20` du modèle) |
| 2 | aucune donnée interdite n'apparaît dans l'audit | exclusions du §21.1/§16.2 appliquées à chaque écriture, `T2` à `T7` ; témoin à `T8` |
| 3 | les rapports respectent les mêmes droits que les écrans source | périmètres de lecture confrontés à ceux des routes déjà construites, `T8` et `T10` |
| 4 | les durées de conservation sont configurées | `retention_until` posé par défaut à un an, `T1` ; lu et rapporté à `T8` |
| 5 | l'identifiant de corrélation relie interface, API et logs | réutilisation de `packages/observabilite` (LOT 1 `T4`), jamais un second mécanisme, `T2` à `T7` ; témoin à `T8` |
| 6 | Jonathan valide l'audit et le pilotage | checklist `G10`, à `T16` |

Aucun des huit critères de la fiche LOT 9 ne se répète ici : le texte des deux sources ne porte
que six critères pour ce lot.

---

# 2. Règles déjà tranchées

| Sujet | Règle |
|---|---|
| Écriture de l'audit | **Synchrone, dans la MÊME transaction que l'action métier** — ce n'est pas un choix mais une conséquence du critère de sortie 1 et de `ARB-DATA-005`/`§30.20` : « une action métier et son audit sont atomiques ». La file `security` déjà déclarée dans `DRAMATIQ_QUEUES` (LOT 1) n'est PAS consommée par ce lot — elle reste réservée aux traitements asynchrones du LOT 11 |
| Export de l'audit | Réservé à `ADM-E` (son entité) et `SUPER` (global) seuls — matrice §16, ligne « Exporter en CSV ». `DSM`/`ESM`/`BOOST`/`OFFICE` n'exportent jamais |
| Contenu interdit | Mots de passe, jetons de session, magic links complets, secrets, CSV complets, corps complet des e-mails — **jamais écrits**, pas seulement filtrés à la lecture (cahier §10.11/§16.2, modèle §21.1) |
| Reporting MVP | Compteurs et tableaux **seulement** (cahier §10.10) ; graphiques et exports PDF/CSV de reporting sont **V1**, hors périmètre (cahier §15.2) — à distinguer de l'export CSV de l'audit lui-même (`US004`), qui est MVP |
| Alertes opérationnelles | Le cycle applicatif (ouverture, acquittement, commentaire, résolution, réouverture automatique en cas de récidive, modèle §21.2/§21.3) est construit ici. **L'intégration réelle avec Uptime Kuma, ses seuils de production et ses canaux de notification (cahier §27) restent hors périmètre** — réservés au LOT 13, où la production temporaire existera réellement |
| Purge et anonymisation automatiques | **Hors périmètre.** Elles exigent un traitement planifié récurrent, infrastructure que ce lot ne pose pas (`async_job`, LOT 11). Seule la **traçabilité** des actions déjà existantes (départ, archivage) est renforcée ici si un trou est trouvé en construisant |
| Reporting et tableau de bord | Le tableau de bord administratif existe depuis le LOT 9 (`T5`, périmètre `DSM`/`ESM`/`BOOST`/`ADM-E`/`SUPER`, cahier §10.8). Le reporting de ce lot (`US003`, cahier §10.10/§15.1) est une ressource **distincte** — à vérifier en construisant si des comptes se recoupent, jamais supposé |

## 2.1 Écarts et questions à ne pas combler par intuition

`ECART-064` — **à fermer dans ce lot.** Le §18.1 exige un motif pour « toute intervention du
super-administrateur dans une entité » ; `archive_reason` et `assignment_reason` existent depuis
le LOT 2 et aucune route ne les écrit encore. Ce lot les alimente, avec `audit_event`.

`QO-092` — **ouverte, à trancher avant ou pendant `T12`** (traitement des signalements). Le cahier
ne dit pas si un signalement part vers Jonathan seul ou vers un canal eXalt plus large ; le
backlog nomme « Jonathan » comme rôle du besoin de `US006`, ce qui penche pour la première lecture
sans la trancher définitivement — à poser explicitement le moment venu.

**Une divergence trouvée dans `infra/scripts/verifier-recette-modele.py`, à vérifier à `T16`, pas
à recopier.** Les classements existants des contrôles `§30.19` à `§30.24` portent des annotations
`lot=` écrites tôt dans le projet, avant que la roadmap ne fixe l'ordre définitif des lots : `§30.19`
(jobs et idempotence) y est annoté « LOT 10 », `§30.20` (`audit_event` et atomicité) et `§30.23`
(anonymisation) « LOT 12 », `§30.24` (exports) « LOT 11 ». Ces annotations ne correspondent plus au
découpage réel de la roadmap — `§30.20` en particulier est le critère de sortie 1 de CE lot. Elles
seront relues et corrigées si besoin à `T16`, contre la roadmap et non contre ce qui est déjà écrit
dans le script (§9.0 de la passation : vérifier avant de bâtir).

---

# 3. Découpage validé — seize sous-étapes

Chaque sous-étape part de `develop`, porte sa propre preuve et est fusionnée avant que la
suivante ne commence.

| # | Sous-étape | Story | Note |
|---|---|---|---|
| `T1` ✅ | Les six tables — `audit_event`, `operational_alert`, `alert_comment`, `bug_report`, `export_request` (modèle §21) et `data_subject_request` (modèle §22.3), migration | socle | `DEC-655`. Trois références nues renommées (`resource_reference`, `correlation_token` ×2), `export_request.job_id` retiré (`async_job` n'existe pas), `retention_action`/`privacy_notice_*` du §22 hors périmètre |
| `T2` ✅ | Le service d'écriture d'audit générique, câblé sur l'authentification et les sessions (LOT 3) | `US001`/`US002` | `DEC-656`. `enregistrer_un_evenement` câblé sur les quatre sites `auth_event` du LOT 3 (magic link, connexion admin, révocation de session, compte de service) ; `action_code` réutilise `TypeEvenementAuth` |
| `T3` ✅ | Câblage sur les personnes et l'organisation (LOT 2, 4, 5, 9) | `US001`/`US002` | `DEC-657`. Sept sites câblés — `creer_un_collaborateur`, `modifier_les_donnees_organisationnelles` (un `audit_event` par champ), `changer_d_entite`, `archiver_un_profil`/`restaurer_un_profil`, les quatre cercle/bureau, `creer_une_entite`, `attribuer_la_categorie_dg` — l'import CSV et le transfert en masse héritent sans câblage séparé |
| `T4` ✅ | Câblage sur les contenus et le Framework (LOT 6) | `US001`/`US002` | `DEC-658`. Huit sites câblés — `creer_une_page`, `remplacer_le_contenu` (un seul `audit_event` pour l'appel entier), les trois du cycle de vie (`ActionEditoriale`), `creer_un_lien`/`modifier_un_lien`/`reordonner_les_liens` (un seul `audit_event` pour tout l'ensemble réordonné) |
| `T5` ✅ | Câblage sur les événements (LOT 8) | `US001`/`US002` | `DEC-659`. Sept sites câblés — `creer_un_evenement` (littéral `creer`, aucune valeur `ActionEvenement` n'étant une ligne du §11), `modifier_un_evenement` (un seul `audit_event` pour l'appel entier, même en remplaçant aussi les cercles/bureaux), les trois du cycle de vie (`ActionEvenement`, `motif` d'annulation porté dans `reason`), `gerer_les_medias_d_un_evenement` (un seul `audit_event` pour tout le remplacement de la liste, y compris quand elle est vidée) |
| `T6` ✅ | Câblage sur l'onboarding (LOT 7) | `US001`/`US002` | `DEC-660`. Treize fonctions câblées — catalogue des tâches, modèles et versions, cycle de vie d'une version, affectation d'un parcours, trois gestes sur une tâche, archivage/restauration manuels d'un parcours — `action_code` réutilisant `TypeEvenementTache` pour les quatre gestes sur une tâche, neuf littéraux pour le reste |
| `T7` ✅ | Câblage sur l'import CSV et le back-office (LOT 9), et le motif obligatoire des interventions du super-administrateur | `US001`/`US002`, ferme `ECART-064` | `DEC-661`. Six écritures jamais encore auditées (dépôt, décision, octroi des responsabilités/rôles techniques, rafraîchissement des cercles secondaires, résolution du DSM) ; retrofit du motif obligatoire sur la totalité des fonctions déjà câblées par `T2`-`T6`, nouveau module `app.audit.motif` |
| `T8` ✅ | `GET` journal d'audit filtrable par périmètre | `US001` (clôt), `US002` (clôt) | `DEC-662`. Deux arbitrages de Jonathan (événements sans entité retrouvés par l'entité actuelle de l'acteur ; Booster/bureau étendus aux autres ressources de leur périmètre, pas seulement les personnes) |
| `T9` ✅ | Export CSV de l'audit, réservé à `ADM-E`/`SUPER`, lui-même audité | `US004` (clôt) | `DEC-663`. Synchrone, sans dépôt MinIO — dicté par le docstring d'`ExportRequest` lui-même (`T1`) et la contrepartie explicite V1 asynchrone (`V1-L04-US002`). Aucun arbitrage de Jonathan nécessaire |
| `T10` | Reporting étendu — compteurs et tableaux du §15.1/§10.10 | `US003` | distinct du tableau de bord du LOT 9 `T5`, à vérifier en construisant |
| `T11` | Le bouton « Reporter un bug » et le signalement | `US005` | pied de page, pages d'erreur, menu mobile |
| `T12` | Le traitement des signalements par Jonathan | `US006` | `QO-092` à trancher ici |
| `T13` | Les alertes opérationnelles — cycle ouverture/acquittement/commentaire/résolution/réouverture | `US007` | suivi applicatif seul, pas l'intégration Uptime Kuma (LOT 13) |
| `T14` | Le suivi d'une demande de droit RGPD | `US008` | `data_subject_request` |
| `T15` | Les écrans back-office — audit, reporting, support | transversal | pattern `T14` du LOT 9, onglets de la page `administration` existante |
| `T16` | Recette de clôture, classement du §30 (`§30.19`-`§30.24` à vérifier, pas à recopier), checklist `G10` | porte | pattern `T14`/`T15`/`T16` des LOTS 7/8/9 |

---

# 4. Frontières du lot

Le LOT 10 ne livre pas :

- la purge physique et l'anonymisation automatiques — exigent un traitement planifié, LOT 11 ;
- l'intégration réelle avec Uptime Kuma (seuils de production, canaux de notification, cahier §27) — LOT 13 ;
- les graphiques et les exports PDF/CSV de reporting — V1, cahier §15.2 ;
- l'export image 16:9 et le texte Teams du suivi onboarding — V1 ;
- la médiathèque avancée — V1, matrice §12.2 ;
- le rollback complet d'un import — V1, déjà hors périmètre du LOT 9 ;
- `async_job`, `outbox_message` et tout traitement asynchrone — LOT 11 ;
- la génération de miniatures — LOT 11.

---

# 5. Contrôles à conserver à chaque sous-étape

- `make docs-check`, `make sources-check`, `make isolation-check` ;
- tests unitaires et d'intégration depuis la racine ;
- tests de permissions avec un acteur **réellement rattaché** au périmètre refusé ;
- comparaison de zéro régression sur la même base ;
- `make migrations-check` dès `T1` ;
- un témoin de contenu interdit par domaine câblé (`T2` à `T7`) : l'audit d'une action sensible
  ne contient JAMAIS un mot de passe, un jeton, un magic link complet, un secret, un CSV complet
  ou un corps d'e-mail brut — paire négatif/positif, jamais un seul sens (§7.39 de la passation) ;
- aucune donnée réelle, aucun CSV réel, aucun secret.
