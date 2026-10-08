# Fiche de lot — LOT 9

**Intitulé :** Back-office, administration et import CSV
**Épic :** `MVP-L09` — issue `#234`
**Ouvert par Jonathan le :** 8 octobre 2026
**État :** **OUVERT** — `DEC-635`; `T1` faite par `DEC-636`
**Sous-étape suivante :** `T2` — création d'un collaborateur depuis le back-office
**Porte de sortie :** `G9`, tag attendu `v0.9.0`

> Tous les nombres de cette fiche sont dérivés des sources citées. Recompter avant de les
> réutiliser : une copie manuelle devient fausse dès la première évolution (`ECART-021`).

---

# 1. Ce que le lot doit produire

## 1.1 Les huit stories du backlog

```bash
grep -cE '^\| `MVP-L09-US[0-9]{3}`' docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md
```

| Story | Priorité | Taille | Objet | Issue |
|---|---|---|---|---:|
| `MVP-L09-US001` | `P0` | L | Tableau de bord administratif | `#235` |
| `MVP-L09-US002` | `P0` | XL | Gérer collaborateurs et affectations individuellement | `#236` |
| `MVP-L09-US003` | `P1` | L | Opérations de masse contrôlées | `#237` |
| `MVP-L09-US004` | `P0` | XL | Téléverser et prévisualiser un CSV réel | `#238` |
| `MVP-L09-US005` | `P0` | L | Valider les rapprochements de clients | `#239` |
| `MVP-L09-US006` | `P0` | XL | Importer les lignes valides et obtenir un rapport | `#240` |
| `MVP-L09-US007` | `P0` | L | Créer une nouvelle entité depuis des modèles génériques | `#241` |
| `MVP-L09-US008` | `P1` | M | Restaurer les ressources archivées autorisées | `#242` |

Le lot porte **six stories `P0` et deux `P1`**, trois `XL`. Les deux `P1` restent dans le
périmètre ouvert : le backlog n'autorise leur report qu'avec un arbitrage explicite à la porte.

## 1.2 Les huit critères de sortie, concordants dans la roadmap et le cahier

La roadmap (`ROADMAP_MVP_V1_V2_EXALT.md`, §LOT 9) et le cahier (`CAHIER_DES_CHARGES_EXALT_BORDEAUX.md`,
Annexe C) portent le **même texte** pour ces huit critères — deux sources qui concordent, pas une
invention.

| # | Critère | Preuve attendue |
|---:|---|---|
| 1 | le CSV réel n'est ni dans Git ni dans une image | `make sources-check` et `make icloud-verify` étendus ; témoin à `T16` |
| 2 | les données réelles ne sont chargées qu'après vérification FileVault et sauvegarde | geste d'exploitation documenté, hors périmètre technique de la CI, à `T16` |
| 3 | le rapport correspond à l'empreinte du fichier | `import_batch.source_checksum_sha256` confronté au rapport, à `T10` |
| 4 | les règles d'intégrité de la reprise réussissent | critères de qualité du cahier §12.6, témoins à `T9`/`T10` |
| 5 | aucune ligne rejetée n'est masquée | rapport exhaustif (créations/mises à jour/avertissements/rejets), total réconcilié, à `T10` |
| 6 | l'isolation multi-entités est testée pendant l'import | témoin d'isolation dédié, à `T15` |
| 7 | Léa et Jonathan valident le rapport de répétition en recette | démonstration guidée, à `T16` |
| 8 | Jonathan valide le lot | checklist `G9`, à `T16` |

Les critères 1, 2 et 7 portent sur des **données réelles** et l'exploitation, pas sur le code :
ils sont démontrés en recette (`T16`), jamais exercés avec un vrai CSV pendant le développement
(cahier §29.2, FileVault).

---

# 2. Règles déjà tranchées

| Sujet | Règle |
|---|---|
| Traitement de l'import | **Synchrone**, comme le reste de l'API (`DEC-462`) — confirmé par Jonathan le 08/10/2026. `async_job`/`outbox_message` restent réservées au LOT 11 (précédent mesuré au LOT 7 `T10` : aucune ligne du dépôt n'écrit encore ces deux tables) |
| Schéma de colonnes | Le schéma **logique** `F01`–`F19`, versionné `1.0-initiale` (`DEC-434`), est la base de travail. Le schéma **réel** (en-têtes, langue, nomenclature) reste ouvert (`QO-096`, `QO-110`) et ne bloque que l'import de données réelles, jamais la construction du pipeline (`ECART-005`) |
| États d'une ligne | `valid`, `warning`, `needs_decision`, `rejected`, `imported`, `updated` (modèle §19.2) |
| États d'un lot d'import | `uploaded`, `analyzing`, `preview_ready`, `approved`, `importing`, `completed`, `failed`, `cancelled` (modèle §19.1, diagramme §24.4) |
| E-mail obligatoire | Une ligne sans e-mail professionnel est **bloquée** jusqu'à correction (cahier §12.2) |
| Fusion de client | **Jamais automatique** : toute fusion ou création d'alias exige une validation humaine, mémorisée dans `import_decision` (cahier §12.3, modèle §19.4) |
| Réactivation d'un profil archivé | Exige une **confirmation explicite** distincte de l'import normal (matrice §14) |
| Rollback complet d'un import | **V1**, hors périmètre MVP (cahier §14, §19.5, §30.2) |
| Permissions CSV | Seuls `ESM`, `ADM-E` (portée Entité) et `SUPER` (portée Globale) chargent, lancent et rejouent un import ; `DSM`/`BOOST` valident dans leur périmètre sans lancer ; `OFFICE` n'a aucun droit sur l'import collaborateur (matrice §14, §14.1) |
| Nouvelle entité | Créée depuis des **modèles génériques**, aucune donnée Bordeaux copiée ; rôles, contenus et onboarding génériques initialisés puis configurables (`US007`) |

## 2.1 Écarts et questions à ne pas combler par intuition

`ECART-035` — **à fermer dans ce lot.** Le critère de `MVP-L03-US006` nomme des « invitations »
qu'aucune table ne porte. Le registre l'a explicitement renvoyé ici : « à reprendre au LOT 9, où le
back-office créera les invitations ». La révocation posée par `T9` du LOT 3 devra recevoir une
ligne de plus le jour où l'objet existera.

`ECART-060` — **à fermer dans ce lot, au moins pour sa part « métiers, clients, DSM ».** Des
filtres que l'API accepte déjà sans qu'aucun écran ne puisse les proposer ; le registre nomme
explicitement le back-office du LOT 9 comme administrateur de ces listes de référence.

`ECART-064` — **ne concerne PAS ce lot sur son volet motif d'intervention.** Le motif
(`archive_reason`/`assignment_reason`) et l'audit transverse restent au LOT 10 avec `audit_event` ;
ne pas l'anticiper silencieusement ici, même si « rollback d'import » y est cité comme cas futur.

`QO-096`, `QO-097`, `QO-099`, `QO-100`, `QO-110` — **toutes ouvertes, aucune ne bloque la
construction du pipeline.** Elles bloquent uniquement le chargement de **données réelles** :
schéma exact des colonnes, personne remettant le CSV final, nombre maximal de lignes rejetées
tolérable, durée de conservation du fichier source, nomenclature des en-têtes. `.env.example`
porte déjà `IMPORT_SOURCE_RETENTION_DAYS=CHANGE_ME_EN_ATTENTE_DE_QO_100`, annotation **délibérée**
(`DEC-461`, `DEC-464`) : ne pas lui donner de valeur inventée.

---

# 3. Découpage validé — seize sous-étapes

Chaque sous-étape part de `develop`, porte sa propre preuve et est fusionnée avant que la suivante
ne commence.

| # | Sous-étape | Story | Note |
|---|---|---|---|
| `T1` ✅ | Les quatre tables de l'import — `import_batch`, `import_row`, `import_row_issue`, `import_decision`, migration `0024` | socle | **13 tests**, 29 clés composites au total, migration rejouée à vide ; `approved_by_person_id` corrigé pour porter une clé étrangère (défaut trouvé par `make isolation-check`) — `DEC-636` |
| `T2` | Création d'un collaborateur et de son appartenance depuis le back-office | `US002` (1/2) | Route inexistante à ce jour — vérifié, seuls `PATCH`/archivage/restauration existent sur `person`/`entity_membership` |
| `T3` | Modification structurante et transitions (changement d'entité, de statut, de rattachement) | `US002` (2/2) | Même périmètre que `T2` |
| `T4` | Restauration des ressources archivées autorisées par back-office | `US008` | dépend de `T2`/`T3` ; distinguer restaurations simples (matrice) et techniques/massives (rôles réservés) |
| `T5` | Tableau de bord administratif — agrégat en lecture | `US001` | Profils actifs, arrivées futures, onboardings en retard, profils incomplets, derniers imports ; pattern `T8` du LOT 8 |
| `T6` | Dépôt sécurisé du CSV, empreinte SHA-256, `import_batch`, zone d'analyse sans écriture métier | `US004` (1/2) | |
| `T7` | Normalisation des e-mails, détection des doublons, blocage des lignes sans e-mail, prévisualisation complète | `US004` (2/2) | |
| `T8` | Correspondances de clients proposées et validation humaine (fusion/alias), `import_decision` | `US005` | ferme `ECART-060` pour les clients |
| `T9` | Import transactionnel des lignes valides, mises à jour par e-mail, confirmation explicite pour réactiver un profil archivé | `US006` (1/2) | |
| `T10` | Rapport (créations/mises à jour/avertissements/rejets), rejeu des lignes rejetées, conservation temporaire maîtrisée | `US006` (2/2) | `QO-100` posée mais non bloquante ici |
| `T11` | Opérations de masse contrôlées (prévisualisation d'impact, idempotence, erreurs partielles explicites) | `US003` | `P1`, dépend de `T2`/`T3` |
| `T12` | Création d'une nouvelle entité depuis des modèles génériques | `US007` | dépend des LOTS 2/6/7 ; ferme `ECART-035` pour la part « invitations » si l'objet est posé ici, sinon nommé explicitement non résolu |
| `T13` | Fermeture explicite de `ECART-035` (invitations au départ) | correctif | revue de la révocation `T9` du LOT 3 |
| `T14` | Écrans back-office — navigation Organisation/Onboarding/Contenu/Données/Pilotage/Configuration/Super-administration, tableau de bord, écrans CRUD, import | transversal | premier et seul écran du lot |
| `T15` | Contrôle de pile réelle (nom à définir, ex. `make back-office-check`), asymétrie de rôles, isolation multi-entités pendant l'import | transversal | pattern `T13`/`T14` des LOTS 7/8 |
| `T16` | Recette de clôture, classement du §30 (règles 17/18 à vérifier), checklist `G9` | porte | pattern `T14`/`T15` des LOTS 7/8 |

---

# 4. Frontières du lot

Le LOT 9 ne livre pas :

- le rollback complet d'un import — V1 ;
- les exports CSV/PDF avancés et les graphiques de pilotage — LOT 10 ;
- la purge, l'anonymisation et le motif d'intervention du super-administrateur — LOT 10, `ECART-064` ;
- les traitements asynchrones, `async_job`, `outbox_message` — LOT 11 ;
- la génération de miniatures — LOT 11 ;
- les contenus réels non encore validés par Léa/Tess/Diane.

---

# 5. Contrôles à conserver à chaque sous-étape

- `make docs-check`, `make sources-check`, `make isolation-check` ;
- tests unitaires et d'intégration depuis la racine ;
- tests de permissions avec un acteur **réellement rattaché** au périmètre refusé ;
- comparaison de zéro régression sur la même base ;
- `make migrations-check` dès `T1` ;
- aucune donnée réelle, aucun CSV réel, aucun secret ;
- aucune ligne rejetée masquée dans un rapport ou un test.
