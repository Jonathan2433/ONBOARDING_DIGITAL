# Fiche de lot — LOT 8

**Intitulé :** Événements et accueil dynamique  
**Épic :** `MVP-L08` — issue `#206`  
**Ouvert par Jonathan le :** 1er octobre 2026  
**État :** **OUVERT** — `DEC-619`; `T1` et `T2` faites par `DEC-620` et `DEC-621`
**Sous-étape suivante :** `T3`, création d'un événement et résolution préalable d'`ECART-067`
**Porte de sortie :** `G8`, tag attendu `v0.8.0`

> Tous les nombres de cette fiche sont dérivés des sources citées. Recompter avant de les
> réutiliser : une copie manuelle devient fausse dès la première évolution (`ECART-021`).

---

# 1. Ce que le lot doit produire

## 1.1 Les six stories du backlog

```bash
grep -cE '^\| `MVP-L08-US[0-9]{3}`' docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md
```

| Story | Priorité | Taille | Objet | Issue |
|---|---|---|---|---:|
| `MVP-L08-US001` | `P0` | L | Accueil dans l'ordre validé | `#207` |
| `MVP-L08-US002` | `P0` | M | Arrivées récentes pendant un mois | `#208` |
| `MVP-L08-US003` | `P0` | L | Événements à venir et passés | `#209` |
| `MVP-L08-US004` | `P0` | L | Créer, modifier, annuler et archiver | `#210` |
| `MVP-L08-US005` | `P1` | M | Vidéo d'accueil chargée sur action | `#211` |
| `MVP-L08-US006` | `P1` | S | Ressources internes configurées | `#212` |

Le lot porte **quatre stories `P0` et deux `P1`**, aucune `XL`. Les deux `P1` restent dans le
périmètre ouvert : le backlog n'autorise leur report qu'avec un arbitrage explicite à la porte.

## 1.2 Les six critères de sortie, concordants dans la roadmap et le cahier

| # | Critère | Preuve attendue |
|---:|---|---|
| 1 | aucune donnée de participants n'existe | migration et contrats sans inscription, participant ni notification métier ; témoin structurel à `T1` |
| 2 | aucune vidéo complète n'est téléchargée avant interaction | test navigateur/réseau à `T12` |
| 3 | les événements passés sont calculés de manière cohérente | lecture de part et d'autre de `ends_at`, avec la même ancre temporelle, à `T2` |
| 4 | les règles d'archivage et restauration sont respectées | transitions et grilles distinctes à `T5` |
| 5 | l'accueil respecte l'ordre et le design validés | test de structure, mobile et clavier à `T11`/`T12` |
| 6 | Jonathan valide l'accueil et les événements | démonstration et checklist `G8` à `T14` |

Le critère 1 est négatif : l'absence de table ne suffit pas si l'API accepte tout de même un
champ libre. Le témoin doit confronter la migration, les modèles de requête et le manifeste API.

---

# 2. Règles déjà tranchées

| Sujet | Règle |
|---|---|
| Classement temporel | « Passé » est **dérivé de `ends_at`**, jamais stocké comme état ; aucun job ne déplace une ligne |
| États métier | `draft`, `published`, `cancelled`, `archived` |
| Événement annulé | il reste consultable avec un badge « Annulé » |
| Périmètres stockables | entité entière (aucune ligne de portée), un ou plusieurs cercles, un ou plusieurs bureaux |
| Temporalité | `starts_at < ends_at`, contrôlée par la base et le service |
| Récurrence | V1, donc absente du schéma, des routes et de l'écran MVP |
| Participants | aucune inscription, liste, présence ou notification métier |
| Médias | réutilisation de `media_asset`; `event_media` porte l'ordre et le rôle d'affichage |
| Restauration ESM | fonctionnelle dans son entité, explicitement couverte par `ARB-DROIT-003` |
| Accueil | présentation, Framework, arrivées récentes, prochains événements, liens internes — dans cet ordre |
| Arrivée récente | fiche publiée visible jusqu'à `recent_until`, déjà calculé par PostgreSQL au LOT 7 |
| Vidéo | aucun autoplay, commandes de lecture et volume, chargement complet différé jusqu'à l'action |

## 2.1 Deux écarts à ne pas combler par intuition

`ECART-067` — la matrice autorise le DSM à créer pour « Entité ou consultants », alors que le
modèle ne sait représenter que l'entité, les cercles et les bureaux. Accorder l'entité entière au
DSM élargirait son droit ; inventer `event_dsm_scope` modifierait le modèle validé. `T1` pose donc
strictement les quatre tables prévues, et l'arbitrage doit être obtenu avant `T3`.

`ECART-068` — la matrice exige que modification et publication soient « toujours auditées », mais
le domaine `audit_event` est séquencé au LOT 10 et n'existe pas encore. Les colonnes d'auteur et de
cycle de vie ne constituent pas un historique. L'écart doit être résolu avant de fermer `US004` ;
il ne justifie pas d'anticiper silencieusement le LOT 10.

---

# 3. Découpage validé — quatorze sous-étapes

Chaque sous-étape part de `develop`, porte sa propre preuve et est fusionnée avant que la suivante
ne commence.

| # | Sous-étape | Stories | Témoin principal |
|---|---|---|---|
| `T1` ✅ | Les quatre tables `event`, `event_circle_scope`, `event_office_scope`, `event_media` — migration `0022` | socle | **16 tests**, 24 clés composites au total, migration rejouée à vide — `DEC-620` |
| `T2` ✅ | Lecture des événements à venir et passés | `US003` (1/2) | **12 tests** ; `ends_at <= instant` passé ; annulé visible ; brouillon/archivé absents — `DEC-621` |
| `T3` | Création d'un événement et résolution du périmètre d'écriture | `US004` (1/3) | chaque rôle autorisé dans sa portée, refus hors portée ; résolution préalable d'`ECART-067` |
| `T4` | Modification, publication et rattachements multiples | `US004` (2/3) | publication immédiate ; périmètres multiples sans fuite inter-entités |
| `T5` | Annulation, archivage et restauration | `US004` (3/3) | grilles distinctes ; restauration ESM fonctionnelle ; annulé toujours visible |
| `T6` | Médias d'événement | `US004` | ordre stable, média de la même entité, aucun téléversement ni traitement du LOT 11 |
| `T7` | Arrivées récentes | `US002` | publiée visible immédiatement puis absente après `recent_until`, ancre contrôlée |
| `T8` | Agrégat API de l'accueil | `US001` (1/2), `US006` (1/2) | cinq sections dans l'ordre, sans recopier les règles de leurs services sources |
| `T9` | Écrans de consultation des événements | `US003` (2/2) | onglets à venir/passés, badge annulé, mobile et clavier |
| `T10` | Écran de gestion des événements | `US004` | actions proposées selon les mêmes listes de rôles que l'API |
| `T11` | Accueil final desktop | `US001` (2/2), `US006` (2/2) | ordre structurel des cinq sections et ouverture externe explicite |
| `T12` | Accueil mobile, carrousels accessibles et vidéo sur action | `US005` | aucune requête vidéo avant interaction ; commandes natives ; navigation manuelle |
| `T13` | Contrôle de pile réelle événements + accueil | transversal | parcours HTTPS réel, migrations et permissions sur les huit services |
| `T14` | Recette, classement du §30 et checklist `G8` | porte | création par chaque périmètre, refus hors périmètre, bascule temporelle, annulation, desktop/mobile |

---

# 4. Frontières du lot

Le LOT 8 ne livre pas :

- la récurrence des événements — V1 ;
- les inscriptions, participants, présences ou notifications métier ;
- la génération de variantes et miniatures — LOT 11 ;
- les traitements planifiés et verrous distribués — LOT 11 ;
- le moteur d'audit transverse et les écrans de pilotage — LOT 10 ;
- l'import CSV — LOT 9 ;
- les contenus réels non encore validés par Léa/Tess/Diane.

---

# 5. Contrôles à conserver à chaque sous-étape

- `make docs-check`, `make sources-check`, `make isolation-check` ;
- tests unitaires et d'intégration depuis la racine ;
- tests de permissions avec un acteur **réellement rattaché** au périmètre refusé ;
- comparaison de zéro régression sur la même base ;
- `make migrations-check` dès `T1` ;
- aucune donnée réelle, aucun média réel, aucun secret ;
- aucun champ d'inscription ou de participant dans la base, le contrat ou l'UI.
