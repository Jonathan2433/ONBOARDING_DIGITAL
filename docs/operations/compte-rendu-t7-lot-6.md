# Compte rendu — `T7` du LOT 6 : brouillon, publication, archivage, restauration

**Sous-étape :** `T7` · **Story :** `MVP-L06-US006` · **Issue :** `#151` · **Décision :** `DEC-586`
**Réalisée le :** 19 septembre 2026
**Branche :** `feat/l06-t7-cycle-de-vie-des-contenus`, partant de `develop`, jamais empilée

---

# 1. État du lot

**LOT 6 ouvert le 13/09/2026** (`DEC-575`), douze sous-étapes validées le même jour.
**`T1` à `T7` sont faites**, `T8` à `T12` restent.

`T7` livre le cycle de vie d'une page de contenu : trois routes, une migration, et la
fermeture de `ECART-063` **par la mesure**.

---

# 2. Ce que la sous-étape a produit

```text
POST /api/v1/entities/{code}/pages/{page}/publication    le brouillon devient public
POST /api/v1/entities/{code}/pages/{page}/archivage      la page quitte le public
POST /api/v1/entities/{code}/pages/{page}/restauration   elle revient en BROUILLON
```

`apps/api/app/content/cycle_de_vie.py` porte les trois services,
`apps/api/app/content/perimetre.py` accueille les trois nouvelles grilles, et la migration
`0018` pose le déclencheur du §8.4.

## 2.1 `ECART-063` est clos, et il ne restait **qu'une cellule**

`T6` avait relevé que l'annexe A §13 et §18 donnent deux grilles pour « Archiver un
contenu », divergentes dans les deux sens. La consigne était de retenir la plus restrictive
de chaque cellule à défaut de réponse. **La mesure a fait mieux que cela.**

**Premier fait : la légende §4 ne définit pas `Périmètre`.** Elle définit la coche, `—`,
`Soi`, `Consultants`, `Cercle`, `Bureau`, `Entité`, `Global`, `Lecture` et `Conditionnel` —
**dix valeurs** — alors que `Périmètre` est employé dans plus de vingt cellules du document.

**Second fait : le §3 le définit, dans une colonne qui s'appelle « Périmètre principal ».**

```text
DSM      « ses consultants dans son entite »
ESM      « ENSEMBLE DE SON ENTITE »
BOOST    « son cercle et ses membres »
OFFICE   « son bureau »
ADM-E    « ensemble de son entite »
SUPER    « toutes les entites »
```

Or la légende §4 définit `Entité` par « **ensemble de l'entité principale** ». **Pour
l'`ESM`, `Périmètre` et `Entité` dénotent donc le même ensemble** — `RIGHTS-009` le redit — et
la divergence de cette colonne n'était **qu'une différence de vocabulaire**.

| rôle | §13 « Archiver » | §18 « Archiver un contenu » | concordent ? |
|---|---|---|---|
| `DSM` | — | Périmètre | **NON** |
| `ESM` | Périmètre **= Entité** | Entité | **OUI, même ensemble** |
| `BOOST` | Cercle | Cercle | OUI |
| `OFFICE` | Bureau | Bureau | OUI |
| `ADM-E` | Entité | Entité | OUI |
| `SUPER` | Global | Global | OUI |

**Troisième fait : la cellule du `DSM` n'est pas exprimable.** Le §3 fait de son périmètre un
ensemble de **personnes** ; `content_page` ne porte aucune colonne qui rattache une page à un
DSM — mesuré sur le catalogue : `entity_id`, `page_type`, `circle_id`, `office_id`, `title`,
`slug`, `state`, `published_at`, plus les champs communs du §3.1. Lui accorder ce droit
exigerait d'**inventer un rattachement**, ce que le §6.5 interdit. Et le cahier §10.1 le met
lui aussi à **tiret** sur « Archiver/restaurer une page ».

**Le `—` du §13 est retenu**, et ce n'est pas seulement la lecture la plus restrictive : c'est
la seule que le modèle permette d'écrire.

> **La leçon est §7.45, et elle est neuve.** Un mot employé comme **valeur** et absent de la
> légende ne se devine pas : il se cherche **ailleurs dans le document**. `T6` avait conclu
> « deux mots différents, donc deux droits » — une lecture prudente, et elle avait raison de
> s'y tenir. Ce qui l'a corrigée n'est pas un raisonnement mais une **recherche du mot dans
> tout le document**, qui l'a trouvé en titre de colonne au §3.

## 2.2 La restauration a une grille **plus étroite**, et trois sources le disent

```text
source                                 DSM  ESM             BOOST  OFFICE  ADM-E   SUPER
matrice §13  « Restaurer »             —    Conditionnel    —      —       Entite  Global
matrice §18  « Restaurer un contenu »  —    Entite, fonct.  —      —       Entite  Global
cahier  §10.1 « Archiver/restaurer »   —    Conditionnel    —      —       Entite  Global
```

**Le Booster archive la page de son cercle et ne la restaure pas.** C'est asymétrique, c'est
écrit trois fois, et c'est la leçon de `T8` du LOT 5 transposée : le §6.1 y portait déjà deux
grilles, et réutiliser celle de l'écriture aurait accordé l'archivage à deux rôles qui en sont
exclus.

**« Conditionnel » est défini**, §4 : « autorisé si une règle métier complémentaire est
satisfaite ». `ARB-DROIT-003` nomme la règle — l'ESM restaure **fonctionnellement** dans son
entité, les restaurations techniques, massives ou liées aux imports restant à l'`ADM-E` et au
`SUPER`. Restaurer **une** page est fonctionnel, et aucune route n'offre de geste massif.

## 2.3 La restauration rend un **brouillon**, et le corpus ne le dit pas

Trois raisons concordantes, et la plus forte n'est pas la prudence :

1. **restaurer n'est pas publier**, et le §13 en fait deux lignes à deux grilles différentes ;
2. `RIGHTS-001` — « toute permission est refusée par défaut si elle n'est pas explicitement
   accordée ». Une page redevenue visible sans que personne ne l'ait publiée serait une
   publication que **personne n'a décidée** ;
3. **rien n'est perdu** : la grille de restauration est **incluse** dans celle de la
   publication, donc qui restaure peut republier dans le geste suivant — et ce geste laisse
   une trace.

`QO-122` porte la question à Léa. Elle n'est **pas bloquante** : un changement d'avis tiendrait
dans une constante, `ETAT_APRES_RESTAURATION`, sans migration ni changement de contrat.

## 2.4 Ni dépublication, ni republication — et les deux sont **inexprimables**

Le §13 porte trois lignes — « Publier immédiatement », « Archiver », « Restaurer » — et
**aucune ligne de dépublication**. Retirer une page du public se fait en l'archivant.

Et republier une page déjà publiée **écraserait `published_at`**, donc la date même que
`US006` demande d'identifier. Le refus n'est pas un filtre : la demande ne porte **aucun champ
d'état**, l'état cible est porté par la **route**, et `_actions_selon_l_etat` n'offre `PUBLIER`
qu'à un brouillon. Les transitions que le document n'écrit pas sont inexprimables plutôt que
refusées — §7.35.

## 2.5 Aucune contrainte ne couple `state`, `archived_at` et `published_at`

`T1` avait laissé la question à `T7` : « le §15.1 ne lie pas `state` à `published_at` ; une
page `published` sans date n'est interdite nulle part ».

**La réponse est : aucune contrainte**, et le motif est mesuré. Le corpus ne les couple nulle
part, et **le décor de `T4` fabrique délibérément les deux divergences** — une page
`state = archived` sans `archived_at`, une page `state = published` avec `archived_at` — pour
prouver que sa lecture de `publie` est exacte. Poser une biconditionnelle les rendrait
impossibles et **détruirait cette preuve pour rien** (§6.5, §7.41).

**Ce qui garantit que l'API n'en crée jamais n'est pas une contrainte, c'est que les deux
colonnes sont écrites dans le MÊME `UPDATE`** : les séparer exigerait de casser le code, pas
d'oublier un appel (§7.35). Et les divergences existantes sont lues **au plus restrictif** :
`archived_at` discrimine l'archivage, `state` ne distingue que brouillon et publié parmi les
pages vivantes.

---

# 3. Contrôles exécutés

```text
make framework-check    --> 61 controles, 0 echec   (49 avant T7)
pytest test_cycle_de_vie_des_contenus.py            40 tests, dont 32 d'integration
campagne de temoins     12 filtres retires un par un, 0 MUET
make check              74 echecs, IDENTIQUES a la baseline de develop (base de demo)
make residu-check · docs-check · audit · icloud-verify · env-check · mypy · ruff   verts
```

**Aucune cible `make` nouvelle** — `framework-check` passe de **49 à 61** contrôles, donc rien
à ajouter dans `ci.yml`. Cinquième sous-étape consécutive.

## 3.1 Le contrôle de stack le plus utile est un **couple d'adresses identiques**

« Brouillon et publication sont distingués » est satisfait par une API qui ne publie **rien du
tout** — §7.39. Ce qui rend le critère non trivial est que **la même adresse** change de
verdict, et c'est la route de `T5`, écrite avant et sans rapport, qui le rend :

```text
avant publication     GET .../pages/HOME/<slug>   404
apres publication     GET .../pages/HOME/<slug>   200
apres archivage       GET .../pages/HOME/<slug>   404
apres restauration    GET .../pages/HOME/<slug>   404   <- RESTAURER N'EST PAS PUBLIER
apres republication   GET .../pages/HOME/<slug>   200   <- le TEMOIN du refus precedent
```

**La quatrième ligne est le contrôle le plus utile de la sous-étape**, et la cinquième est ce
qui l'empêche d'être satisfaite par une restauration cassée.

## 3.2 La borne du §8.4 mord, et elle a son témoin

`DEC-583` avait renvoyé ici le déclencheur du comptage borné. Sur la pile réelle :

```text
bureau a ZERO responsable actif    POST .../publication   409 `borne_des_responsables`
un responsable ACTIF ajoute        POST .../publication   200   <- LA MEME publication
```

Et en tests : **un, deux et trois** responsables publient ; **zéro et quatre** sont refusés ;
une responsabilité **future** ne compte pas — `period @> now()`, jamais `ends_at IS NULL` ; et
un `page_type` autre que `OFFICE` n'est pas concerné, sans quoi un déclencheur qui refuserait
**toute** publication passerait les deux refus.

## 3.3 Ce que le déclencheur ne garantit **pas**, et c'est mesuré

Il est déclaré `BEFORE UPDATE OF state`, **exactement comme
`circle_archivage_sans_membres_actifs` du LOT 2** est déclaré `BEFORE UPDATE OF archived_at`.
Il garde donc la **transition**, pas l'état permanent.

| ce qu'il garantit | ce qu'il ne garantit pas |
|---|---|
| on ne **publie** pas un bureau non conforme | qu'un bureau **publié reste** conforme |

Un test le mesure plutôt que de l'affirmer (§7.20) : après une publication conforme, clôturer
le seul responsable laisse un bureau **publié à zéro responsable**. **C'est exactement l'état
que le décor de `T4` fabrique**, et c'est ce qui prouve que sa lecture tolérante reste
**nécessaire** — le déclencheur ne la rend pas obsolète, il **explique pourquoi elle existe**.

L'autre côté — interdire d'ajouter un quatrième responsable à un bureau publié — n'est pas
posé, et c'est dit : `ARB-DROIT-002` réserve l'affectation des responsables à l'ESM et au
super-administrateur, et **aucune route de ce lot ne l'écrit**. Garder ce côté appartient au
lot qui la servira.

**Résiduel nommé** : un `INSERT` direct d'une page déjà `published` contourne le déclencheur,
comme pour `circle`. Aucun chemin applicatif n'y mène — `T6` crée toute page en `draft`, et un
test l'exige.

## 3.4 La campagne de témoins — douze filtres, et **zéro muet**

Une première dans ce lot. **Cinq étaient muets à la première passe, et les cinq étaient de
vrais trous de couverture** — aucun n'était une redondance.

| filtre d'abord muet | pourquoi il l'était |
|---|---|
| `publier : archived_at IS NULL` | le filtre d'état suffisait **tant que les deux colonnes ne divergent pas** |
| `publier : state = draft` | aucun test n'appelait le service sur une page déjà publiée |
| `publier : entity_id` | aucun test ne l'appelait avec une autre entité |
| `archiver : archived_at IS NULL` | aucun test ne l'appelait sur une page déjà archivée |
| `restaurer : efface archived_by` | personne ne relisait cette colonne après restauration |

**La cause commune** : tous mes autres cas passent par `resoudre_le_perimetre_editorial`, qui
refuse déjà la transition en 403 — si bien que **la précondition du service n'était exercée par
personne**.

**Ce n'est pas une redondance, et le motif est celui de `T2` du LOT 5** : ces fonctions sont
appelables hors HTTP — un export, un script de reprise — et une précondition qui ne vivrait que
dans la route rendrait la règle **dépendante de son appelant**. Elles couvrent en outre la
fenêtre entre la résolution du périmètre et l'écriture.

Six tests ont été écrits pour les exercer. **Le dernier a demandé de chercher** : pour rendre
`archived_at IS NULL` non muet, il fallait l'état **divergent** — une page `draft` portant
`archived_at` — que seul un `UPDATE` direct produit, et qui est un état **réel** de cette base
puisque `T7` a refusé de poser la contrainte qui l'interdirait. *Un filtre muet n'est pas
forcément redondant : il peut n'avoir aucun témoin.*

---

# 4. Défauts trouvés — **trois**, tous dans mon propre travail

## `T7-1` — mes tests d'intégration n'avaient pas leur marqueur

Les vingt-quatre tests qui touchent la base ont été écrits sans `@pytest.mark.integration`.
Conséquence mesurée : `pytest -m integration` en **désélectionnait la totalité**, donc ils
n'auraient **jamais tourné dans la tâche qui les exécute** — `make residu-check` sélectionne
sur ce marqueur. Ils auraient en revanche tourné dans la tâche **qualité**, sans base, où ils
se seraient **silencieusement passés** par `pytest.skip`.

**Un test désélectionné et un test qui passe donnent la même observation dans un résumé** :
« 0 échec ». Corrigé, et vérifié **dans les deux sens** — `-m integration` en sélectionne 32,
`-m 'not integration'` en sélectionne 8, et la somme vaut le fichier.

## `T7-2` — mes contrôles de stack héritaient d'un état qu'ils n'avaient pas posé

Ils ont échoué en annonçant « brouillon servi : 200 » et « publication : 403 ».

**Diagnostic avant correction** (§7.18) : une sonde qui fait dire au contrôle ce qu'il voit —
le chemin appelé, l'identifiant visé, et le contenu de la table. La cause en une ligne :

```text
en base : ... HOME t2l6-xxxx-t6 published
```

**Le contrôle 44 de `T6` publie la page par SQL**, pour prouver que l'écriture n'y touche pas —
la route de publication n'existait pas alors. Mes contrôles la croyaient en brouillon.

**Le remède n'est pas de défaire cet état** : c'est de partir d'une page que `T7` crée
lui-même. Un contrôle qui hérite d'un état qu'il n'a pas posé mesure le décor d'un autre.

## `T7-3` — un nom de champ recopié de mémoire, jamais vérifié

Le décor de la borne du §8.4 envoyait `code_de_bureau` dans la charge de création ; le champ de
la demande s'appelle `bureau` — `code_de_bureau` est le nom du **paramètre du service**, pas
celui du **modèle HTTP**. Résultat : 422, et le contrôle s'est arrêté net.

L'échec a été **bruyant et immédiat**, ce qui est la seule bonne nouvelle. C'est le §7.10 dans
un costume de plus : *inspecte les champs réels avant de les employer, ne te fie pas à ta
mémoire d'une API* — y compris quand c'est la tienne, écrite la veille.

---

# 5. Écarts et questions

## `ECART-063` — **clos**, et par la mesure

Voir §2.1. Cinq rôles sur six concordaient déjà une fois `Périmètre` lu par le §3 ; la sixième
cellule n'est pas exprimable dans le modèle.

## `ECART-064` — **ouvert** : le motif du §18.1 n'est demandé nulle part

Le §18.1 énumère cinq cas où un motif est obligatoire, dont « **intervention du
super-administrateur dans une entité** » — et `RIGHTS-017` le redit. **Aucune route du dépôt
n'en demande un**, et les deux colonnes prévues pour le porter sont vides : mesure du
19/09/2026, `archive_reason` et `assignment_reason` n'apparaissent **nulle part** dans
`apps/api/app/` hors de leur déclaration.

**Non bloquant pour le MVP** — aucune donnée réelle, un seul super-administrateur, et
`archived_by_person_id` nomme l'auteur. **À instruire au LOT 10 avec `audit_event`** : un motif
stocké sans consommateur serait un champ que personne ne lit, et `ECART-061` a montré ce que
cela coûte.

**Le l'implémenter dans `T7` seul aurait été fautif** : une règle transversale appliquée à une
route sur quarante est la forme exacte du garde-fou à couverture partielle du §7.40.

## `QO-122` — **ouverte** : la restauration republie-t-elle ?

Voir §2.3. Relève de Léa, non bloquante.

---

# 6. Ce que `T7` ne fait pas

- **aucun écran** — les écrans d'édition sont `T10` ;
- **aucun audit métier** : `audit_event` est le §21.1 du modèle et appartient au **LOT 10**.
  La trace de `T7` est `updated_by_person_id` et `archived_by_person_id`, et rien de plus ;
- **aucune dépublication**, aucune republication, aucune restauration massive ;
- **aucune table de versions** : le modèle §15 n'en déclare pas, et l'inventer serait §6.5.
  Conséquence nommée — une écriture de `T6` sur une page publiée incrémente `version` sans
  changer `published_at`, si bien que le contenu servi change sans nouvelle publication. C'est
  la conséquence directe de « Publier **immédiatement** ». L'historique existe malgré tout,
  `T6` **archivant** les blocs retirés au lieu de les supprimer ;
- **aucun garde-fou sur l'affectation des responsables** — §20 et `ARB-DROIT-002`, hors lot.

---

# 7. Ce que `T7` laisse

**L'issue `#151` reste OUVERTE**, et ce n'est pas un oubli. Sur les trois membres du critère de
`US006` :

| critère | état |
|---|---|
| « brouillon et publication sont distingués » | **tenu**, et prouvé par le couple d'adresses du §3.1 |
| « la version publiée est identifiable » | **tenu avec une limite nommée** — `version` et `publiee_le`, sans table de versions |
| « les modifications sont auditées » | **non tenu** — `audit_event` est au LOT 10 |

**Pour `T8` — la présentation de l'entité et les liens internes :**

- **`QO-120` attend Léa**, et elle est **bloquante** : le §15.3 et le cahier §13 écrivent tous
  deux « les URL sont validées selon une **liste de protocoles autorisés** », et **ni l'un ni
  l'autre ne la donne**. Une liste blanche fermée serait aussi fautive qu'une absence de liste
  (§7.29) ;
- `internal_link` existe depuis `T1` et **aucune route ne la sert** ;
- `ROLES_DE_CREATION` et `ROLES_D_ECRITURE_EDITORIALE` sont posés et réemployables ; la grille
  du §19 « Modifier les liens internes | ESM Entité | ADM-E Entité | SUPER Global » devra être
  **confrontée** au §13 avant d'être réutilisée — c'est la troisième fois de ce lot qu'une
  grille voisine n'est pas la même.
