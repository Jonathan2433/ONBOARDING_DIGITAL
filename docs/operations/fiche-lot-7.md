# Fiche de lot — LOT 7

**Intitulé :** Fiches d'arrivée et onboarding
**Épic :** `MVP-L07`
**Ouvert par Jonathan le :** 25 septembre 2026
**État :** **OUVERT**, découpage **validé** le 25/09/2026 — `DEC-598`. **`T1` à `T10` FAITES**, `DEC-599`, `DEC-600`, `DEC-601` (+ correctif `DEC-602`), `DEC-603`, `DEC-604`, `DEC-605`, `DEC-606` (+ correctif `DEC-607`), `DEC-608`, `DEC-609`, `DEC-610`
**Dernière mise à jour :** 28 septembre 2026 — `T10`
**Porte de sortie :** `G7`, tag `v0.7.0` prévu

> **TOUS LES NOMBRES DE CETTE FICHE SONT DÉRIVÉS, PAS RECOPIÉS**, et chacun est accompagné de la
> commande qui le produit. C'est la classe `ECART-021`, rejouée une douzaine de fois dans ce projet.
> **Recompte avant de réutiliser.**

---

# 1. Ce que le lot doit produire

## 1.1 Les **huit** stories, comptées dans le backlog

```bash
grep -cE '^\| `MVP-L07-US[0-9]{3}`' docs/product/BACKLOG_INITIAL_PRIORISE_EXALT.md
```

| Story | Priorité | Taille | Objet | Dépend de |
|---|---|---|---|---|
| `MVP-L07-US001` | `P0` | L | Compléter sa fiche d'arrivée | LOT 5 |
| `MVP-L07-US002` | `P0` | M | Valider et publier une fiche d'arrivée | `US001` |
| `MVP-L07-US003` | `P0` | **XL** | Créer et versionner un modèle mission ou intercontrat | LOT 2, LOT 5 |
| `MVP-L07-US004` | `P0` | L | Créer un onboarding depuis la date d'arrivée | `US003` |
| `MVP-L07-US005` | `P0` | L | Terminer et annuler une tâche pendant cinq minutes | `US004` |
| `MVP-L07-US006` | `P0` | M | Réouvrir une tâche après cinq minutes | `US005` |
| `MVP-L07-US007` | `P0` | **XL** | Changer automatiquement de parcours mission/intercontrat | `US003`–`US005` |
| `MVP-L07-US008` | `P0` | L | Suivre les onboardings dans son périmètre | `US004`–`US007` |

**Les HUIT sont `P0`, et DEUX sont `XL`** — `US003` et `US007`. Aucune autre story du backlog ne
porte deux tailles `XL` dans le même lot : c'est ce qui commande le découpage du §3.

## 1.2 Les **sept** critères de sortie — dérivés des **deux** sources, qui concordent

La roadmap autonome (§ LOT 7) et le cahier consolidé (`## LOT 7`, ligne 5082) portent le **même
texte, mot pour mot** — comparé avant d'être recopié ici, parce qu'un document dérivé peut
prescrire autre chose que sa source dès sa rédaction (`ECART-023`) :

| # | Critère | Ce qui devra le prouver |
|---|---|---|
| 1 | les parcours mission et intercontrat sont validés par Tess, Léa, Diane et Jonathan | `T5`/`T6` livrent les deux modèles utilisables ; **la validation nominative elle-même est un geste humain hors CI** — voir §8.4, trois noms nouveaux dans ce lot |
| 2 | les règles de périmètre DSM, Booster et ESM sont testées | un témoin par périmètre à chaque écriture — `T4` à `T12` |
| 3 | la progression est calculée et non stockée comme source de vérité | `T7` : aucune colonne `progress` en base, et le contrôle exige un **témoin positif** — une progression SERVIE et exacte, pas seulement l'absence de colonne |
| 4 | les événements de tâche sont historisés | `onboarding_task_event`, écrit à `T7`–`T10` |
| 5 | le départ d'un collaborateur archive le parcours et révoque les sessions | `T11`, qui doit s'accrocher à `enregistrer_un_depart` (LOT 3, `T9`) — pas le réécrire |
| 6 | un parcours réel complet est exécuté en recette | `T15`, un aller-retour complet, `arrival_date` → tâches → complétion → archivage |
| 7 | Jonathan valide l'organisation et l'onboarding | la démonstration guidée de la checklist `G7` |

> **LE CRITÈRE 3 EST NÉGATIF, ET C'EST LE MÊME PIÈGE QUE LE LOT 6, §7.39.** « La progression n'est
> pas stockée » est satisfait tout seul si elle n'est ni calculée ni servie. Le témoin doit donc
> être positif : une instance avec des tâches dans des états mêlés (`todo`/`completed`/`reopened`),
> et la progression lue plusieurs fois **change** quand une tâche change d'état — sans qu'aucune
> écriture ne touche une colonne de progression.

---

# 2. Ce que le corpus tranche déjà, et qu'il ne faut pas réinventer

| Point | Où c'est écrit | Ce qui est tranché |
|---|---|---|
| Verrouillage du nouvel arrivant | matrice §6.2 | avant validation, `NEW` ne modifie que photo, présentation et fun fact ; arrivée, métier, statut, DSM, client et cercle principal sont **préremplis et verrouillés** |
| Publication de la fiche | matrice §7.1 | automatique à la validation, **aucune approbation préalable** d'un responsable |
| Affichage récent | matrice §7.2, modèle §12.1 | mis en avant jusqu'à **un mois** après `arrival_date`, via `recent_until` |
| Le catalogue de tâches | modèle §13.1 | `entity_id` **nullable** pour une tâche générique globale ; le `code` (ou l'UUID) est ce qui identifie une tâche commune lors d'un changement de parcours |
| Les versions de modèle | modèle §13.3 | chaque publication crée une version **immuable** ; une instance existante garde sa version, sauf remplacement métier explicite |
| Cinq minutes, pas plus | matrice §8.3, modèle §13.6 | après le délai, seuls `ESM`, `ADM-E` et `SUPER` réouvrent ; motif **obligatoire**, `DSM` et `BOOST` **exclus** |
| Aucun tiers, aucun commentaire | matrice §8.2 | pas de pièce jointe ni de validation par un tiers dans le MVP ; un responsable ne peut pas compléter une tâche à la place du nouvel arrivant |
| Portée des modèles | `ARB-DROIT-005` | DSM → ses consultants ; Booster → son cercle ; ESM/ADM-E → transverse à l'entité ; SUPER → modèles génériques globaux |
| Restauration fonctionnelle | `ARB-DROIT-003` | couvre profil, contenu, événement, cercle, bureau — **pas** l'onboarding, voir `ECART-066` |

## 2.1 Deux pièges de la matrice, mesurés avant de commencer

**Premier piège — consulter n'est pas agir, et la même ligne du §8.1 porte les deux.** `DSM` et
`BOOST` ont « Consultants » / « Cercle » pour **consulter** le parcours d'un collaborateur — mais
sont à **tiret partout** sur les actions de la tâche elle-même : marquer terminé, annuler dans les
cinq minutes, réouvrir. Un raccourci qui accorderait le droit d'agir parce que le droit de consulter
existe déjà accorderait à un DSM ou un Booster une action que la matrice leur refuse en toutes
lettres, et que §8.3 attribue **nommément** à trois rôles seulement.

**Second piège — la colonne `OFFICE` est entièrement à tiret sur les modèles d'onboarding, §9.**
Troisième fois que ce piège apparaît sous cette forme précise (LOT 5, LOT 6) : un responsable de
bureau n'a **aucun** droit sur les modèles, ni en création ni en publication ni en restauration,
alors qu'il en a sur d'autres ressources de son bureau. La seule ligne où `OFFICE` apparaît est
« Consulter les modèles publiés », à **Lecture** — comme tous les autres rôles y ont `✓`.

**Une troisième nuance, sur les mots.** §9.1 dit que « le DSM crée des modèles limités à ses
consultants », mais le tableau §9 donne au DSM le **même droit plein** que l'ESM sur chaque ligne —
créer, versionner, publier, archiver — seule la **portée** diffère (Consultants contre Entité). Rien
dans le corpus ne dit si un modèle publié par un DSM seul est immédiatement utilisable comme les
modèles ESM/ADM-E, ou s'il exige une validation supplémentaire ; aucune section ne le confirme ni ne
l'infirme, et rien ne l'exige donc `T5`/`T6` ne l'inventeront pas.

---

# 3. Le découpage — **quinze** sous-étapes, validées le 25/09/2026 (`DEC-598`)

Chaque sous-étape porte le témoin qui rend son critère non trivial, et une seule pull request la
fusionne. **Une sous-étape à la fois**, et elle part toujours de `develop`.

| # | Sous-étape | Stories | Ce qui la rend non triviale |
|---|---|---|---|
| ~~`T1`~~ | ~~Les huit tables — `arrival_profile` + les six tables d'onboarding, migration `0020`~~ **FAITE le 25/09/2026**, `DEC-599` | socle | `photo_authorization` **existe déjà** depuis le LOT 5 (`0014`), rien à recréer. **`make isolation-check` a trouvé deux classes de défaut inédites** — voir `compte-rendu-t1-lot-7.md` §2.2 — corrigées par une clé simple à trois raisons désormais légitimes plutôt que deux |
| ~~`T2`~~ | ~~La fiche d'arrivée en lecture — préremplissage verrouillé~~ **FAITE le 25/09/2026**, `DEC-600` | `US001` (1/2) | les données organisationnelles sont **réutilisées** de `lire_la_fiche` (LOT 5), jamais recalculées — une population élargie (future/active, trois visibilités), pas une deuxième requête. Périmètre du §7 prouvé, `DSM` à tiret malgré un rattachement réel |
| ~~`T3`~~ | ~~Validation et publication — `recent_until`, « ils nous ont rejoints récemment »~~ **FAITE le 26/09/2026**, `DEC-601` + correctif `DEC-602` | `US001` (2/2), `US002` | la publication est **automatique** à la validation (§7.1), prouvée en un seul appel. `Support`/`Support cercle` (absents de la légende §4) couvrent Entité/Cercle/Global ; `BOOST` diverge sur la seule ligne « Valider et publier ». **Correctif post-fusion** : une quatrième ligne, « Corriger après publication », manquée à la première lecture — sa grille s'inverse sur `NEW`/`DSM` |
| ~~`T4`~~ | ~~Le catalogue des tâches — `onboarding_task_reference`, identifiants stables~~ **FAITE le 26/09/2026**, `DEC-603` | structurel, ferme `ECART-013` | **la clé de tout le lot** : un identifiant fonctionnel unique par tâche commune, réutilisé par les modèles mission ET intercontrat, jamais la numérotation à deux préfixes du prototype. `DSM`/`BOOST` (`Consultants`/`Cercle` au §9) se réduisent à l'`Entité` pour cette table précisément : elle ne porte ni cercle ni DSM, seulement `entity_id` — collapsage documenté, pas une lecture large. Seul `SUPER` atteint `Global` |
| ~~`T5`~~ | ~~Les modèles et leurs versions — `onboarding_template`, `_version`, `_task`, scopes `GLOBAL/ENTITY/DSM/CIRCLE`~~ **FAITE le 26/09/2026**, `DEC-604` | `US003` (1/2) | une version publiée est **immuable** (modèle §13.3) : le témoin est une tentative de modification d'une version déjà publiée, refusée. **Contrairement au catalogue de `T4`, `Consultants`/`Cercle` NE se réduisent PAS à l'entité** : `onboarding_template` porte de vraies colonnes de portée, un DSM/Booster ne gère que SON propre DSM-ship/cercle |
| ~~`T6`~~ | ~~Cycle de vie d'un modèle — publication, archivage, restauration~~ **FAITE le 26/09/2026**, `DEC-605` | `US003` (2/2) | **`ECART-066` (volet version de modèle) résolu ICI, avant d'écrire la route** : l'ESM restaure librement dans son entité. Le volet « parcours » (§8.1) reste ouvert pour `T11`. « Duplication » du libellé initial n'était rien de plus que la création de version déjà livrée par `T5` — aucune quatrième route |
| ~~`T7`~~ | ~~Création d'une instance depuis la date d'arrivée — lecture du parcours, progression calculée~~ **FAITE le 27/09/2026**, `DEC-606` | `US004` | ferme le critère 3 (témoin positif, §1.2) ; « une seule instance active par appartenance » (modèle §13.5) éprouvée au volume (40 affectations distinctes), pas seulement à l'unité. Priorité de résolution du modèle DSM > CIRCLE > ENTITY > GLOBAL, arbitrage de Jonathan |
| ~~`T8`~~ | ~~Compléter et annuler une tâche dans les cinq minutes~~ **FAITE le 27/09/2026**, `DEC-608` | `US005` | les deux lignes du §8.1 sont `Soi` **seul** (grille la plus stricte du module, `DSM`/`BOOST` à tiret malgré un rattachement réel) ; `annuler_la_completion` ne produit **jamais** `cancelled` — la tâche redevient `todo` ; la fenêtre de cinq minutes est **ancrée à `completed_at`**, jamais une horloge mockée. **Correctif `DEC-607`** : `T7` ne posait aucun événement `onboarding_task_event`, `ASSIGNED` est désormais posé par l'affectation |
| ~~`T9`~~ | ~~Réouverture après cinq minutes — motif obligatoire, `onboarding_task_event`~~ **FAITE le 27/09/2026**, `DEC-609` | `US006`, ferme `§30.15` | seuls `ESM`, `ADM-E`, `SUPER` — le témoin négatif porte sur `DSM` et `BOOST`, **explicitement exclus** par §8.3, pas seulement absents de la liste. **Correctif à `terminer_une_tache` (`T8`)** : le diagramme §24.2 exige `Reopened -> Completed`, transition que `T8` n'avait pas prévue |
| ~~`T10`~~ | ~~Changement automatique mission ↔ intercontrat~~ **FAITE le 28/09/2026**, `DEC-610` | `US007`, ferme `§30.14` | l'ancienne instance passe à `replaced`, la nouvelle instantiée depuis le modèle adapté, **les tâches communes déjà terminées conservées par référence stable** — `ECART-013` mis à l'épreuve pour de vrai. **Aucune route propre** : la garde déjà exercée sur l'écriture du champ `statut` (LOT 5) est *a fortiori* dans le périmètre du parcours (`T7`), vérifié contre le code des deux modules |
| `T11` | Archivage automatique du parcours terminé + révocation au départ | ferme `§30.13` | deux déclencheurs distincts : complétion totale des tâches obligatoires (modèle §13.5), et départ d'un collaborateur — qui doit **s'accrocher** à `enregistrer_un_depart` (LOT 3, `T9`) sans le dupliquer (§7.27) |
| `T12` | Suivi par périmètre — DSM/ESM/Booster/ADM-E/SUPER | `US008` | « reporting de base » seulement (cahier, Inclus) : aucun graphique, aucun export — ce serait le LOT 10 |
| `T13` | Écrans du nouvel arrivant — fiche d'arrivée, parcours, tâches | — | un aller-retour réel avant de déclarer un client terminé (§7.43 du LOT 6) : les écrans écrivent (compléter, annuler) |
| `T14` | Écrans d'administration — catalogue, modèles, suivi par périmètre | — | mêmes grilles de rôles qu'au §2.1, à l'écran cette fois : `OFFICE` ne doit voir apparaître aucune action de gestion |
| `T15` | Recette, §30 et checklist `G7` | — | un parcours réel complet exécuté en recette, sur une base remise à zéro — critère 6 |

**`US003` est découpée en deux, `US007` reste seule.** `US003` couvre la création ET le cycle de vie
d'un modèle — deux familles de contrôles distinctes, comme `T5`/`T6` du LOT 6. `US007` ne dépend
d'aucune autre story pour son propre découpage : c'est la substitution d'instance elle-même qui est
complexe, pas sa composition avec autre chose.

> **CE DÉCOUPAGE DIFFÈRE DE CELUI PRÉSENTÉ EN CHAT AVANT CETTE FICHE, ET C'EST DÉLIBÉRÉ.** La
> première version bundlait les écrans d'administration avec la recette dans un `T14` unique. En
> l'écrivant, la règle constante du projet — la recette et la checklist de porte forment **toujours**
> une sous-étape seule, sans code (`T12` du LOT 5, `T12` du LOT 6) — a été retrouvée et appliquée :
> `T14` et `T15` sont donc désormais séparées. Quinze sous-étapes, pas quatorze.

---

# 4. Ce que ce lot NE fera PAS

**Hors périmètre, et c'est un autre lot :**

- **aucun événement** ni accueil dynamique — LOT 8 ;
- **aucun import CSV** — LOT 9 ;
- **aucun reporting graphique ni export** de suivi — cahier §10.3 (LOT 10), et le §8.1/§9 de la
  matrice marquent « Exporter le suivi » et l'export image 16:9 / texte Teams comme `V1` ;
- **aucune médiathèque avancée** — matrice §12.2, explicitement V1 ;
- **aucun commentaire ni pièce jointe** sur une tâche — matrice §8.2, explicitement hors MVP ;
- **aucune validation d'une tâche par un tiers** — matrice §8.2, idem ;
- **aucun onboarding déclenché par autre chose que la date d'arrivée** — pas d'affectation
  rétroactive, pas de modèle multi-entités.

**Les interdits absolus, qui ne dépendent d'aucun lot :** aucun contournement de l'authentification ·
aucun jeton ni mot de passe en clair · aucun jeton dans `localStorage` · aucune donnée réelle de
collaborateur · aucune modification d'une migration déjà appliquée ni des cinq documents de cadrage ·
aucune ligne du prototype historique réutilisée comme code.

---

# 5. Ce qui est déjà livré et que ce lot consomme

| Élément | D'où il vient |
|---|---|
| `entity_membership`, `professional_status_assignment` | LOT 2. `arrival_profile.entity_membership_id` et `onboarding_instance.entity_membership_id` s'y rattachent |
| `photo_authorization` | LOT 5, `T1`. **Rien à recréer** pour `arrival_profile.photo_media_id` |
| `resoudre_le_perimetre`, `exiger_un_role_dans_l_entite` | LOT 4 `T8`, LOT 5 `T7` — deux grilles distinctes, le §8 et le §9 de la matrice en imposent d'autres |
| la protection CSRF sur une route métier | `app/auth/dependances.py`, **ne jamais recopier** (`DEC-466`) |
| `enregistrer_un_depart` | LOT 3, `T9`. `T11` doit s'y accrocher pour archiver le parcours actif, pas dupliquer la logique de révocation |
| le design system, le manifeste `contrat-api.json` | LOT 1, `T10` — source unique lue par TypeScript **et** Python |

**Et une chose attend toujours son premier consommateur :** `exiger_un_scope`, posée au LOT 3 `T9`
pour les comptes de service. Le LOT 7 ne la consomme pas non plus — LOT 9.

---

# 6. Les risques propres à ce lot

| Risque | Pourquoi il est réel ici |
|---|---|
| **Deux stories `XL`, aucune autre l'an dernier** | `US003` (modèles versionnés) et `US007` (changement de parcours) sont les deux pièces les plus complexes du lot, et `US007` dépend du bon fonctionnement des trois précédentes |
| **`ECART-013` est structurel, pas cosmétique** | si `T4` ne pose pas un identifiant fonctionnel correctement partagé, `T10` (US007) ne peut PAS conserver les tâches communes terminées — le défaut ne se verrait qu'au premier changement réel de statut |
| **`ECART-012` reste ouvert** | un DG ou toute personne sans mission n'a que `intercontract` par défaut ; `US003`/`US007` en dépendent pour choisir le bon modèle. Non bloquant, position de Jonathan reconduite (§8.1), mais Léa doit encore trancher |
| **`ECART-066`, nouveau** | la restauration d'un modèle ou d'un parcours archivé par l'ESM est « Conditionnel » sans définition. Bloquant pour `T6` et `T11` seulement |
| **La fenêtre de cinq minutes** | un test qui dort cinq minutes ferait exploser la CI ; le temps doit être injectable dès `T8`, comme l'ancre `INSTANT` du LOT 6 (§7.47) |
| **`ROAD-RSK-033` / `034`** | inchangés, à réévaluer avant le LOT 13 |

---

# 7. Les leçons du LOT 6 qui s'appliquent directement

| Leçon | Où elle mordra dans ce lot |
|---|---|
| **§7.39** — un critère négatif est satisfait par une route qui ne sert rien | le critère 3 (§1.2) : la progression doit être **servie et exacte**, pas seulement absente de la base |
| **§7.47** — une date absolue est une bombe à retardement datée | ce lot est le plus chargé en dates du projet : `arrival_date`, `due_offset_days`, `recent_until`, la fenêtre de cinq minutes. **Toute ancre de temps doit être injectable**, jamais figée dans un test |
| **§7.42** — un décor qui ne produit jamais la valeur en cause ne dit rien d'elle | `title_override`/`description_override` (nullable, modèle §13.4), `photo_media_id` (nullable, §12.1), `replaced_by_instance_id` (nullable, §13.5) — chaque décor doit produire le couple avec/sans |
| **§7.43** — un bouchon prouve ce que TU as écrit dans le bouchon | `T13`/`T14` écrivent (compléter une tâche, publier un modèle) : un aller-retour réel avant de déclarer l'écran terminé |
| **§7.26** — ce qui n'a jamais tourné à l'échelle n'est pas éprouvé | « une seule instance active par appartenance » est une contrainte d'unicité ; le témoin de `T7` doit tourner à un volume qui rendrait une collision possible, pas sur trois personnes |
| **§7.45 / §7.46** — un mot employé comme valeur et absent de la légende se définit ailleurs, ou nulle part | appliqué dans cette fiche même : `Conditionnel` (§8.1, §9) a été cherché dans tout le corpus avant d'ouvrir `ECART-066`, pas deviné |
| **§7.27** — une liste recopiée vieillit au premier ajout | la logique de révocation au départ (LOT 3) ne doit pas être dupliquée dans `T11` ; `T11` s'y **accroche** |

---

# 8. Ce que le corpus NE tranche PAS

## 8.1 `ECART-012` — reconduit, toujours à Léa

**Non résolu, non bloquant.** Position de Jonathan du 12/09/2026 reconduite le 25/09/2026 : rien
n'est affiché pour une direction générale sans mission. Le modèle `onboarding_template.target_status`
ne porte toujours que `mission`/`intercontract` ; une personne dans aucun des deux cas ne reçoit
aucune instance — c'est la conséquence technique de la position, **pas sa résolution**. Léa décide
du produit.

## 8.2 `ECART-013` — se résout structurellement, à `T4`, **et mis à l'épreuve pour de vrai à `T10`**

Les cinq tâches communes du prototype portent des identifiants différents entre les deux parcours
(`ic_a1` contre `m_a1`, etc.). `onboarding_task_reference` porte un identifiant fonctionnel **unique**,
partagé par les deux modèles dès sa création. **La numérotation du prototype n'est jamais reprise
telle quelle.** `T4` posait la structure ; `T10` (`DEC-610`) l'a exercée pour de vrai, en retenant
une tâche `completed` par ce seul identifiant lors d'un changement réel de statut.

## 8.3 `ECART-066` — volet « version de modèle » résolu le 26/09/2026, volet « parcours » ouvert pour `T11`

La matrice donne `ESM` → « Conditionnel » sur la restauration d'un parcours archivé (§8.1) et d'une
version de modèle (§9). `ARB-DROIT-003` définit « Conditionnel » pour cinq ressources — profil,
contenu, événement, cercle, bureau — et n'en nomme aucune des deux. **Résolu pour la version de
modèle avant `T6`** : l'ESM restaure librement dans son entité, même régime que les cinq autres
ressources — `DEC-605`. **Le volet « parcours archivé » (§8.1) n'a pas été reposé** : la question
posée à Jonathan ne portait que sur la version de modèle, et rien ne permet de présumer la même
réponse pour un parcours sans la reposer explicitement. **À reposer avant `T11`.** Détail complet
dans `docs/decisions/registre-ecarts.md`.

## 8.4 Un point non résolu, découvert en écrivant cette fiche — pas un écart, une question pour Jonathan

**Le critère de sortie 1 nomme quatre validateurs — Tess, Léa, Diane et Jonathan.** `docs/README.md`
§6 (table des portes) répète les mêmes quatre noms pour `G7` : ce n'est donc pas une invention isolée
du cahier, la porte elle-même le prévoit. Mais **ni la matrice, ni le modèle, ni aucun autre document
lu jusqu'ici ne dit qui sont Tess et Diane ni comment obtenir leur validation** — à la différence de
Léa, dont le rôle produit est établi dès le §12 de cette passation. Ce n'est **pas** un écart
technique : rien dans le travail de `T1` à `T15` n'en dépend, et une sous-étape ne peut de toute façon
pas produire une validation nominative humaine. Mais avant `T15` et la checklist `G7`, il faudra
savoir comment recueillir ces deux validations — sans quoi le critère 1 ne pourra être coché que
partiellement à la porte.

---

# 9. Traçabilité GitHub

**À créer à l'ouverture**, sur le modèle des lots précédents :

| Élément | Valeur |
|---|---|
| épic | `[EPIC MVP-L07] Fiches d'arrivée et onboarding` |
| stories | **huit** issues, `MVP-L07-US001` à `US008` |
| jalon | `G7` |

> **`Closes #N` ne referme pas une issue depuis `develop`** (§7.19) : chaque issue se referme **à
> la main**, et son commentaire de fermeture est l'endroit où cocher les critères d'acceptation avec
> leurs preuves (backlog §11).
