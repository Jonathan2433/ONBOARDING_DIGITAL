# Fiche de lot — LOT 11

**Intitulé :** Médias, worker et tâches planifiées — périmètre élargi (organisation et démo)
**Épic :** `MVP-L11` — issues GitHub à créer (aucune n'existe encore pour ce lot, mesuré le
30/10/2026 : `gh issue list --search "MVP-L11"` ne rend rien)
**Ouvert par Jonathan le :** 30 octobre 2026 (`DEC-674`)
**État :** OUVERT — découpage en **SEPT** sous-étapes validé par Jonathan le 30/10/2026,
regroupé à sa demande pour accélérer (découpage initial à 15 sous-étapes compilé en 7)
**Sous-étape suivante :** `T1`
**Porte de sortie :** `G11`

> Tous les nombres de cette fiche sont dérivés des sources citées. Recompter avant de les
> réutiliser : une copie manuelle devient fausse dès la première évolution (`ECART-021`).

---

# 1. Ce que le lot doit produire

## 1.1 Les huit stories officielles du backlog

```bash
grep -cE '^\| `MVP-L11-US[0-9]{3}`' docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md
```

| Story | Priorité | Taille | Objet | Dépend de |
|---|---|---|---|---|
| `MVP-L11-US001` | `P0` | XL | Exécuter des jobs Dramatiq persistés | `L01` |
| `MVP-L11-US002` | `P0` | L | Publier les effets externes via une outbox transactionnelle | `US001` |
| `MVP-L11-US003` | `P0` | L | Envoyer les e-mails via une interface fournisseur | `L03`,`US001` |
| `MVP-L11-US004` | `P0` | XL | Téléverser un média en quarantaine | `L06`,`L08` |
| `MVP-L11-US005` | `P0` | L | Générer miniatures et variantes sans doublon | `US004` |
| `MVP-L11-US006` | `P0` | XL | Planifier les tâches périodiques avec verrou | `US001` |
| `MVP-L11-US007` | `P1` | M | Nettoyer les médias rejetés, temporaires et orphelins | `US004`-`US006` |
| `MVP-L11-US008` | `P0` | L | Superviser files, workers et tâches par Uptime Kuma | `US001`-`US007` |

Sept stories `P0`, une `P1` (`US007`), deux `XL` (`US001`, `US006` — en plus d'`US004`, trois `XL`
en réalité). Dépendance roadmap : « LOTS 1 à 10 », tous verrouillés.

## 1.2 Deux sous-étapes hors backlog, ajoutées sur décision explicite de Jonathan

À l'ouverture du lot (30/10/2026), en préparation de la démonstration métier, Jonathan a constaté
qu'aucune route ni aucun écran de ce dépôt ne permet de créer un cercle ou un bureau, ni d'attribuer
un rôle de Booster ou de Responsable de bureau en dehors de l'import CSV (LOT 9). Il a choisi
d'ajouter ces deux capacités à ce lot plutôt que d'ouvrir un lot séparé :

- création d'un cercle et d'un bureau (écran + route) ;
- attribution du Booster d'un cercle et du Responsable d'un bureau, hors import CSV (écran + route).

## 1.3 Une déviation explicite et tracée du cahier : le métier devient optionnel

Jonathan a également demandé, le 30/10/2026, le retrait du caractère obligatoire du champ
« métier » (`job_catalog`/`membership_job_assignment`) dans l'application — **« nous ne voulons plus
gérer ce champ »**. Le modèle de données (`docs/architecture/MODELE_DONNEES_EXALT.md`, §6.3-6.4)
décrit pourtant ce champ comme faisant partie du socle « personnes », au même titre que `person`,
`entity_membership` et `professional_status_assignment` — **une story ou une exigence `Must`/`P0`
n'est jamais dégradée sans décision explicite et tracée (règle n°7 du §2 de `CLAUDE.md`)**. Cette
décision est donc tracée ici et dans le registre (`DEC-675`), avec une portée délibérément bornée :
le champ devient **optionnel partout où il est aujourd'hui obligatoire** ; aucune table ni aucune
ligne existante n'est supprimée — réversible, conforme à la décision reformulée et confirmée par
Jonathan.

## 1.4 Les sept critères de sortie, concordants dans la roadmap et le cahier

La roadmap (`ROADMAP_MVP_V1_V2_EXALT.md`, §LOT 11) et le cahier
(`CAHIER_DES_CHARGES_EXALT_BORDEAUX.md`, §LOT 11) portent le **même texte**, mot pour mot — deux
sources qui concordent, pas une invention.

| # | Critère | Preuve attendue |
|---:|---|---|
| 1 | seuls les médias `ready` sont servis | garde déjà posée au LOT 5 (`ETAT_AFFICHABLE`), reprise par l'upload et la génération de variantes, `T2` |
| 2 | Redis peut être vidé sans perte de la source de vérité métier | jobs et outbox persistés dans PostgreSQL, `T1` ; témoin de redémarrage sans perte |
| 3 | un job rejoué ne duplique pas son effet | idempotence de la génération de variantes et de l'outbox, `T1`/`T2` |
| 4 | les tâches planifiées ne s'exécutent pas en parallèle | verrou de planification, `T4` |
| 5 | les fichiers rejetés sont supprimés selon la politique | nettoyage des médias rejetés/temporaires/orphelins, `T4` |
| 6 | les workers et files sont supervisés | intégration Uptime Kuma, `T4` |
| 7 | Jonathan valide les traitements asynchrones | checklist `G11`, `T7` |

Les deux sous-étapes hors backlog (§1.2) et la déviation du métier (§1.3) n'ajoutent aucun critère
de sortie officiel : ils sont vérifiés par leurs propres contrôles de sous-étape (§5) et par la
recette finale.

---

# 2. Règles déjà tranchées

| Sujet | Règle |
|---|---|
| Regroupement du découpage | Jonathan a demandé, le 30/10/2026, de regrouper les sous-étapes pour accélérer : le découpage initialement proposé à 15 sous-étapes est **compilé en sept**, chacune plus large mais toujours une seule sous-étape à la fois (règle n°1 du §2 de `CLAUDE.md`), avec sa propre preuve, son propre rapport et sa propre validation avant fusion |
| Métier (`job_catalog`) | Rendu **optionnel partout**, jamais supprimé — aucune table, aucune colonne, aucune ligne existante retirée. Décision tracée `DEC-675`, déviation assumée du modèle §6.3-6.4 |
| Rôle Framework de portée groupe | Les responsabilités citées par Jonathan comme « rôle groupe, pas uniquement bordelais » (mentorat Produit, mentorat Design) sont **documentées de façon descriptive seulement** — aucune extension de schéma, pas de portée « groupe » dans `framework_responsibility_assignment`. Décision confirmée (`AskUserQuestion`, réponse « Note descriptive seulement, pour l'instant ») |
| Hiérarchie DG > DSM Coach > DSM | Confirmée par Jonathan comme un fait d'organisation réel, mais **aucune décision de représentation structurelle n'a été prise** — traitée, par défaut et comme le rôle groupe ci-dessus, comme une information descriptive tant qu'aucun écran ou règle ne l'exige. Si une sous-étape en a besoin, la question sera reposée avant d'inventer un schéma (§6.5 de `CLAUDE.md`) |
| Intégration des données de démonstration | **Hors du découpage de ce lot.** Jonathan a explicitement séquencé : « dev du lot 11 puis intégration de tous nos éléments avec un script de seed » — le script d'alimentation (et de vidage) de l'entité EXALT Bordeaux est une action distincte, **postérieure au franchissement de `G11`**, qui consommera les mécanismes construits ici (upload et miniatures de `T2`, création de cercle/bureau et attribution Framework de `T3`, métier optionnel de `T5`) |
| Écriture de l'audit | Ce lot ne construit aucune nouvelle écriture d'`audit_event` au-delà de ce que le LOT 10 câble déjà ; les nouvelles routes d'organisation (`T3`) et de médias (`T2`) héritent du service générique `app.audit.services.enregistrer_un_evenement` (LOT 10, `T2`) si et seulement si un motif de super-administrateur l'exige (`app.audit.motif`, LOT 10 `T7`) |
| Dramatiq | Les sept files sont déjà déclarées dans `DRAMATIQ_QUEUES` depuis le LOT 1 (`default,emails,imports,media,exports,maintenance,security`) ; aucune n'est consommée avant ce lot — `T1` est la première sous-étape qui les exerce réellement |

## 2.1 Écarts et questions à ne pas combler par intuition

**Aucune donnée réelle de collaborateur ne doit être versionnée pendant ce lot** (règle n°3 du §2
de `CLAUDE.md`) : le dépôt reçoit uniquement du code et des fiches, jamais l'export Excel, les
photos originales ni le JSON consolidé des 125 personnes — qui restent dans le répertoire de travail
de l'agent, hors du dépôt synchronisé iCloud, et seront consommés directement par le script
d'intégration post-`G11`.

**Aucune route de schéma n'est ouverte pour la portée « groupe » d'un rôle Framework** (§2
ci-dessus) : si une sous-étape ultérieure (`T3` en particulier) découvre qu'elle ne peut pas
représenter fidèlement un rôle de portée groupe sans un champ nouveau, la question doit être
reposée à Jonathan plutôt que tranchée par défaut.

---

# 3. Découpage validé — sept sous-étapes

Chaque sous-étape part de `develop`, porte sa propre preuve et est fusionnée avant que la
suivante ne commence. Compilé le 30/10/2026 à la demande de Jonathan à partir d'un découpage
initial à 15 sous-étapes, pour accélérer.

| # | Sous-étape | Story | Note |
|---|---|---|---|
| `T1` | Socle asynchrone — tables `async_job`/`outbox_message` (modèle §20), jobs Dramatiq persistés, outbox transactionnelle, fournisseur e-mail générique rejouable | `US001`, `US002`, `US003` | Première exploitation réelle des files Dramatiq déjà déclarées depuis le LOT 1. Mailpit reste exclusif en recette |
| `T2` | Médias — upload en quarantaine (MIME réel, taille, extension, empreinte, nom serveur), génération de miniatures et variantes idempotente, écran de dépôt de photo de profil | `US004`, `US005` | Première route d'upload du projet, tous médias confondus. L'écran consomme directement ce que cette sous-étape construit — ce qui manquait depuis le LOT 5 pour que les avatars déjà posés (chantier front `S10`-`S12`) servent une vraie photo |
| `T3` | Organisation — création de cercle et de bureau (écran + route), attribution du Booster d'un cercle et du Responsable d'un bureau hors import CSV (écran + route) | hors backlog, §1.2 | Comble le trou trouvé le 30/10/2026 à l'ouverture du lot. Aucune extension de schéma pour un rôle de portée groupe (§2) |
| `T4` | Planification et supervision — tâches planifiées avec verrou (expiration, événements passés, anonymisation, purge, nettoyage, détection de jobs bloqués), nettoyage des médias rejetés/temporaires/orphelins, supervision Uptime Kuma | `US006`, `US007`, `US008` | Ferme les huit stories officielles du backlog |
| `T5` | Métier — suppression du caractère obligatoire de `job_catalog`/`membership_job_assignment`, rendu optionnel partout | déviation tracée, §1.3 | Décision produit assumée (`DEC-675`), déviation du modèle §6.3-6.4. Rien n'est supprimé : réversible |
| `T6` | Écrans consommateurs résiduels et recollement | transversal | Tout écran de `T1`-`T5` qui n'aurait pas encore de point d'entrée dans la navigation (menu, rubrique) ; aucun code métier nouveau si `T2`/`T3` ont déjà livré leurs écrans complets |
| `T7` | Recette de clôture — classement du §30 du modèle si concerné, checklist `G11` | porte | pattern `T14`-`T16` des LOTS 7/8/9/10 |

**`T6` peut se révéler vide** (zéro écran résiduel) si `T2` et `T3` livrent déjà des écrans complets
et reliés à la navigation — dans ce cas elle sera fusionnée avec `T7` plutôt que livrée comme une
coquille vide, et ce constat sera annoncé avant d'être exécuté, jamais décidé a priori.

---

# 4. Frontières du lot

Le LOT 11 ne livre pas :

- l'intégration des données de démonstration (entité EXALT Bordeaux, 125 personnes, photos) —
  action distincte, postérieure au franchissement de `G11` (§2) ;
- une extension de schéma pour un rôle Framework de portée groupe — documentation descriptive
  seulement (§2) ;
- une représentation structurelle de la hiérarchie DG > DSM Coach > DSM — information
  descriptive tant qu'aucune règle ne l'exige (§2) ;
- la suppression physique de `job_catalog`/`membership_job_assignment` ou de leurs données — rendu
  optionnel seulement (§1.3) ;
- les tests de charge et d'isolation à 25 entités / 5 000 profils — LOT 12 ;
- l'accessibilité et la performance transversales — LOT 12 ;
- toute donnée réelle de collaborateur versionnée dans le dépôt (règle n°3 du §2 de `CLAUDE.md`).

---

# 5. Contrôles à conserver à chaque sous-étape

- `make docs-check`, `make sources-check`, `make isolation-check` ;
- tests unitaires et d'intégration depuis la racine ;
- tests de permissions avec un acteur **réellement rattaché** au périmètre refusé ;
- comparaison de zéro régression sur la même base (`git worktree` contre `origin/develop`) ;
- `make migrations-check` dès `T1` ;
- un témoin d'idempotence par mécanisme asynchrone introduit (`T1`, `T2`, `T4`) : rejouer le même
  job ou la même tâche planifiée ne duplique jamais son effet — paire négatif/positif, jamais un
  seul sens (§7.39 de la passation) ;
- un aller-retour réel (§7.43 de la passation) pour tout écran livré (`T2`, `T3`, `T6`) ;
- aucune donnée réelle, aucun CSV réel, aucune photo réelle, aucun secret.
