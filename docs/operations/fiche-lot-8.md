# Fiche de lot — LOT 8

**Intitulé :** Événements et accueil dynamique  
**Épic :** `MVP-L08` — issue `#206`  
**Ouvert par Jonathan le :** 1er octobre 2026  
**État :** **OUVERT** — `DEC-619`; `T1` à `T14` faites par `DEC-620` à `DEC-633`
**Sous-étape suivante :** aucune — porte `G8` en attente de la validation de Jonathan
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

`ECART-067` — **CLOS le 04/10/2026 (`DEC-622`), `T3`.** La matrice autorise le DSM à créer pour
« Entité ou consultants », alors que le modèle ne sait représenter que l'entité, les cercles et
les bureaux. `T1` pose strictement les quatre tables prévues, et l'arbitrage — demandé à Jonathan
avant tout code de `T3`, deux options présentées — retient une cinquième table dédiée,
`event_dsm_scope(event_id, entity_id, dsm_person_id)`, migration `0023` : symétrique aux deux
portées déjà posées, elle porte directement le DSM plutôt qu'une liste de consultants figée à la
création, et un index unique partiel sur `event_id` seul rend « Entité OU consultants » — jamais
les deux — structurel plutôt que testé.

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
| `T3` ✅ | Création d'un événement et résolution du périmètre d'écriture | `US004` (1/3) | **27 tests** ; chaque rôle autorisé dans sa portée, refus hors portée, asymétrie entre deux porteurs du même rôle ; `ECART-067` clos — `DEC-622` |
| `T4` ✅ | Modification, publication et rattachements multiples | `US004` (2/3) | **20 tests** ; publication immédiate sans republication ; périmètres multiples (plusieurs cercles/bureaux) sans fuite inter-entités ; DSM — deux grilles distinctes pour Modifier et Publier — `DEC-623` |
| `T5` ✅ | Annulation, archivage et restauration | `US004` (3/3) | **17 tests** ; grilles distinctes (DSM « Périmètre » pour Annuler/Archiver, jamais « créé OU rattaché ») ; restauration ESM fonctionnelle (`ARB-DROIT-003`), DSM/BOOST/OFFICE à tiret ; annulé toujours visible, archivé absent — `DEC-624` |
| `T6` ✅ | Médias d'événement | `US004` | **15 tests** ; ordre stable (index du tableau soumis), média de la même entité et `ready` (réutilisation de `ETAT_AFFICHABLE`, LOT 5), aucun téléversement ni traitement du LOT 11 — `DEC-625` |
| `T7` ✅ | Arrivées récentes | `US002` | **20 tests** ; publiée visible immédiatement — y compris avant `arrival_date` —, absente après `recent_until`, ancre contrôlée ; aucune information organisationnelle ni photo exposée — `DEC-626` |
| `T8` ✅ | Agrégat API de l'accueil | `US001` (1/2), `US006` (1/2) | **6 tests** ; cinq sections dans l'ordre, sans recopier les règles de leurs services sources ; `presentation` nullable, les deux sections paginées à la taille par défaut (25) — `DEC-627` |
| `T9` ✅ | Écrans de consultation des événements | `US003` (2/2) | onglets à venir/passés (`<button>` natifs, `role="tablist"`), badge « Annulé », aucun lien vers une page de détail qui n'existe pas — `DEC-628` |
| `T10` ✅ | Écran de gestion des événements | `US004` | créer/modifier/publier/annuler/archiver/restaurer/médias ; deux grilles de rôles jamais fusionnées (`rolesGestionDesEvenements`/`rolesRestaurationDUnEvenement`) ; deux routes de lecture nouvelles posées en construisant l'écran (`/events/gestion`, `/events/{evenement}/gestion`) — `DEC-629` |
| `T11` ✅ | Accueil final desktop | `US001` (2/2), `US006` (2/2) | **5 sections dans l'ordre §8.4** ; un rôle sans droit d'édition voit désormais la présentation (trou comblé) ; ouverture externe explicite des liens — `DEC-630` |
| `T12` ✅ | Accueil mobile, carrousels accessibles et vidéo sur action | `US005` **reportée** | **Carrousel manuel et accessible** (`<Carrousel>`, `@onboarding/ui`) pour les trois listes de l'accueil, défilement horizontal sous 768 px, liste verticale au-delà ; `US005` (vidéo sur action) explicitement reportée — aucune convention de `payload_json` pour un bloc `VIDEO`, `QO-121` ouverte, `CONT-026` — `DEC-631` |
| `T13` ✅ | Contrôle de pile réelle événements + accueil | transversal | `make accueil-check`, **29 tests** ; la grille à deux visages du DSM, l'asymétrie entre deux porteurs du même rôle, `ARB-DROIT-003` dans le sens du refus sur deux évènements, le classement temporel sur l'horloge réelle, la fenêtre réelle des arrivées récentes — `DEC-632` |
| `T14` ✅ | Recette, classement du §30 et checklist `G8` | porte | recette sur images publiées (`3f5e542`), 57+29+14 contrôles de pile réelle, 0 échec ; §30 relu, inchangé depuis `G7` (16 acquis, 2 partiel, 7 reportés) ; critère de sortie 2 classé **sans objet** (`US005` reportée) plutôt que tenu par défaut — `DEC-633` |

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
