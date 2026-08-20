# Compte rendu — LOT 2, sous-étape `T12`

**Factories, jeu de test et recette du modèle**
**Stories :** `MVP-L02-US007` — issue `#45` · `MVP-L02-US008` — issue `#46`
**Réalisée le :** 20 août 2026
**Décision produite :** `DEC-516`
**Migration produite :** **aucune** — la deuxième de suite, après `T11`

---

## 1. Ce que cette sous-étape devait faire

C'est la **dernière** avant la porte `G2`, et elle porte trois choses distinctes :

- **`US008`** — « une base vide est construite **uniquement** par migrations ; les migrations sont
  testées sur PostgreSQL **réel** » ;
- **`US007`** — « le générateur produit jusqu'à **25 entités** et **5 000 profils** avec
  **historiques cohérents** et **cas limites** » ;
- les **25 contrôles de recette du modèle §30**, et la **checklist de la porte `G2`**.

---

## 2. Le contrôle de migrations, et ce que la comparaison ajoute

**Chaque sous-étape avait éprouvé SA migration à la main** — montée, descente, remontée. Aucun
contrôle n'éprouvait la **chaîne entière** sur une base neuve, et surtout **aucun ne vérifiait
qu'elle produit le bon schéma**.

`make migrations-check` crée une base **jetable**, exige qu'elle porte **0 table**, applique la
chaîne, puis **compare** :

| Signature | Éléments identiques de part et d'autre |
|---|---:|
| colonnes, avec type et nullabilité | **269** |
| contraintes, avec leur type | **94** |
| index | **85** |
| déclencheurs non internes | **8** |
| fonctions | **196** |

**C'est la comparaison qui prouve le critère.** Sans elle, on saurait que la chaîne **s'applique** —
pas qu'elle **aboutit** au schéma qui tourne. Puis il redescend à `base`, exige qu'**aucune table
métier** ne survive — c'est l'étape qui trouve les `downgrade()` fautifs, comme celui de `T5` qui
renommait avant de supprimer — remonte, et exige une signature **identique**.

La base jetable est supprimée dans un `finally`, même en cas d'échec.

---

## 3. Le classement des 25 contrôles du §30, et ce qu'il a trouvé

Le §30 énumère 25 contrôles, et **la plupart portent sur des tables que le LOT 2 ne crée pas**.
Sous-traiter une partie de la liste en silence aurait été le pire choix : la porte se prononce sur le
modèle, elle doit savoir lesquels sont acquis, reportés, ou **inapplicables**.

`make recette-modele-check` **lit les 25 dans le modèle** — un contrôle nouveau ou reformulé fait
échouer la cible plutôt que d'être ignoré — et exige que chacun soit classé :

| Statut | Nombre |
|---|---:|
| **acquis**, avec un test nommé dont l'existence est **vérifiée** | **10** |
| **partiel**, avec son résiduel nommé | **1** |
| reporté, avec son lot | **13** |
| **inapplicable**, avec son écart | **1** |

**Et il a trouvé un défaut à sa première exécution : neuf des noms de tests que j'avais écrits
n'existaient pas.** Je les avais construits par raisonnement au lieu de les relever — exactement
`T11-3`, où j'avais deviné huit noms de contraintes. **Cette fois le contrôle l'a dit avant que je ne
publie**, ce qui est précisément ce qu'on attend de lui.

**Deux classements méritent d'être lus :**

- **§30.4 — « un consultant actif possède un DSM actif » est PARTIEL.** L'**unicité** est acquise
  depuis `T8`. L'**existence** ne peut pas être portée par la base : l'appartenance doit exister
  **avant** qu'une affectation DSM ne la référence, donc une contrainte à l'insertion serait
  circulaire. C'est une règle de **processus**, rattachée au LOT 7 ;
- **§30.8 — « un bureau publié possède entre un et trois responsables » est INAPPLICABLE.** Le §8.3
  ne déclare **aucun état de publication** sur `office` : la condition n'a rien à quoi se rattacher.
  C'est `ECART-031`.

---

## 4. Mon motif SQLite échouait sur un dépôt exemplaire — le §7.25 le jour même

La fiche exige : « aucune dépendance à SQLite n'existe pour les tests d'intégration » est un critère
de sortie, « et **un contrôle devra le vérifier**, plutôt que de compter sur la vigilance ».

Ma première version cherchait le mot `sqlite`. Elle a trouvé **16 occurrences** — et **toutes étaient
de la prose affirmant son exclusion** :

```text
apps/api/tests/conftest.py     « execution sur PostgreSQL reel, jamais SQLite »
apps/api/alembic/env.py        « SQLite, dont les capacites de migration diffèrent trop »
apps/api/tests/test_socle...   « Jamais SQLite — critere de sortie du lot »
```

**Le contrôle échouait donc sur un dépôt exemplaire, et il aurait appris à passer outre.** C'est le
**§7.25 de la passation, que `T11` venait d'écrire**, rejoué dans le contrôle suivant.

Corrigé en cherchant un **usage** — un `import`, une URL `sqlite://`, une dépendance déclarée —
jamais le mot. **99 fichiers examinés, 0 usage réel.**

---

## 5. Le générateur, et trois choix qui comptent

**Il passe par les dépôts de `T11`.** `DepotLocal.creer` renseigne `entity_id` lui-même : un
générateur écrit en SQL direct pourrait fabriquer une relation croisée que la base refuserait, et le
diagnostic sur 5 000 lignes serait pénible.

**Il est déterministe** — `random.Random(graine)`, jamais le générateur global. Un jeu non
reproductible **rend inexploitable l'échec qu'il révèle** : on ne peut ni le rejouer, ni le réduire.
Un témoin exige que deux graines **différentes** produisent des jeux différents, sans quoi un
générateur ignorant sa graine passerait.

**Les valeurs énumérées sont importées du code, pas redéclarées.** Ma première version en avait
**inventé trois** — `fonction_support`, `stagiaire`, `alternant` — alors que le §6.2 n'en déclare que
**deux**, `consultant` et `dg`. La contrainte de vérification les a refusées immédiatement ; mais une
liste recopiée qui se trouverait valide aujourd'hui **divergerait demain**. C'est `ECART-021`, et la
parade est l'import.

**Et `dg` est écartée de la boucle de masse**, ce qui n'est pas un oubli : le déclencheur
`dg_implique_dsm_local` exige une responsabilité `DSM` préalable, donc elle ne s'attribue que par
`attribuer_la_categorie_dg`. Elle figure aux cas limites.

**Les sept cas limites, chacun nommé :**

| Cas limite | Ce qu'il éprouve |
|---|---|
| mobilité inter-entités **séquentielle** | `ex_entity_membership_sans_chevauchement` n'a **pas** de clause `WHERE` |
| une catégorie `dg` créée par le service | le déclencheur la refuserait sans `DSM` préalable |
| un client **globalement archivé, localement actif** | le §7.2 l'autorise — d'où la lecture sur `entity_client` |
| une activation locale **archivée**, client actif | le cas inverse du précédent |
| **un** cercle principal et **deux** secondaires | le §8.2 les autorise explicitement |
| une **succession** `intercontract` puis `mission` | les plages sont semi-ouvertes `[a,b)` |
| une entité **archivée** sans appartenance | `entity_membership_entite_non_archivee` en refuserait une |

---

## 6. Le §30.25 mesuré, et pourquoi il n'exige PAS l'usage d'un index

« Les 5 000 profils et 25 entités restent **exploitables** avec les index définis. » **« Exploitables »
est une grandeur, donc il faut mesurer.**

**Mesure du 20/08/2026 : 27 936 lignes en 21,5 s**, 26 entités, 5 129 personnes.

| Requête | Durée | Lignes |
|---|---:|---:|
| recherche d'une personne par e-mail normalisé | **0,6 ms** | 1 |
| membres occupants d'une entité | **1,0 ms** | 208 |
| missions actives d'une entité, avec leur client | **0,8 ms** | 101 |
| cercle principal actif de chaque membre | **1,3 ms** | 201 |
| responsabilités Framework actives | **0,6 ms** | 6 |
| comptage via `DepotLocal` | **0,8 ms** | 209 |

> **Le test n'exige pas l'usage d'un index, délibérément.** Sur 5 000 lignes, un **parcours
> séquentiel est souvent le plan optimal** : PostgreSQL le choisit parce qu'il est plus rapide, pas
> malgré lui. Un test qui exigerait « aucun Seq Scan » exigerait donc **le contraire de la
> performance**, et échouerait sur un livrable conforme — le défaut du §7.20.
>
> Il exige une **durée**, qui est la grandeur du critère, et **rapporte** le plan pour que le lecteur
> voie ce que la base a fait. C'est aussi la sixième proposition du §7.0 : le nombre affiché et le
> seuil auquel on le compare doivent mesurer la même chose.

**Et un détail que seule l'exécution révèle : `ANALYZE` est indispensable.** PostgreSQL choisit ses
plans sur des **statistiques** ; sur un jeu engendré dans une transaction, il raisonne sur des tables
qu'il croit vides, et la mesure ne dirait rien de la réalité.

---

## 7. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `make migrations-check` | **code 0** — 269 colonnes, 94 contraintes, 85 index, 8 déclencheurs, 196 fonctions identiques |
| `make recette-modele-check` | **code 0** — 25 classés : 10 acquis, 1 partiel, 13 reportés, 1 inapplicable |
| `uv run pytest` | **373 tests, 0 échec** — 367 avant `T12`, et **204** sont d'intégration |
| `make check` | **code 0**, `recette-modele-check` y est désormais |
| `make isolation-check` · `isolation-temoin` | code 0 · les 4 défauts nommés |
| `make historisation-check` · `alembic-check` · `code-check` | 7 relations · 1 tête · 34 fichiers |
| `make jeu-de-donnees ARGS="--entites 2 --profils 5"` | **code 0** puis **refus** au second appel |

---

## 8. Sept défauts, tous dans mon travail

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T12-1` | **Neuf noms de tests DEVINÉS** dans le classement du §30 | le contrôle lui-même, avant publication |
| `T12-2` | Mon motif SQLite cherchait **le mot**, et échouait sur 16 occurrences de prose | la première exécution |
| `T12-3` | Je comptais des **lignes de journal** en croyant compter des révisions : « 0 révision appliquée » alors que **19 tables venaient d'être créées** | le diagnostic, après avoir fait dire au contrôle l'état réel |
| `T12-4` | **Trois catégories professionnelles inventées** dans le générateur — le §6.2 n'en déclare que deux | la contrainte de vérification, immédiatement |
| `T12-5` | Indice de Booster **constant d'une entité à l'autre** : unicité d'e-mail violée **à 25 entités**, pas à 3 | le premier essai à l'échelle |
| `T12-6` | Deux générations dans **une même transaction** : `entity.code` est unique globalement | le test de déterminisme, sur un générateur correct |
| `T12-7` | Un libellé de cas limite portait un **UUID**, donc non comparable | le test de déterminisme |

**`T12-2` est le plus instructif, parce qu'il rejoue une leçon écrite le jour même.** `T11` avait
produit le §7.25 — *un garde-fou à faux positifs est pire qu'aucun garde-fou* — et mon contrôle
suivant l'a commis. **Un piège documenté n'est pas un piège désarmé**, et c'est la troisième fois de
ce projet que la même phrase s'applique.

**`T12-3` est la sixième proposition du §7.0 dans un contrôle que je venais d'écrire.** Je comparais
un **nombre de lignes de journal** à un **nombre de révisions**. Le remède a été le §7.18 : faire
dire au contrôle l'état de ce qu'il mesure — 19 tables créées, sortie vide — plutôt que de corriger à
l'aveugle. Le compte est désormais lu **en base**, dans `alembic_version`.

**`T12-5` est le §7.16 sous une forme nouvelle.** Trente profils passaient ; cinq mille non. **Ce
qui n'a jamais tourné à l'ÉCHELLE n'est pas éprouvé** — le §7.16 parlait d'une autre machine, il faut
y ajouter l'autre volume.

**`T12-6` et `T12-7` ont ceci de commun que le générateur était CORRECT** : c'étaient mes tests qui
étaient faux. Le second est particulièrement net — j'avais interpolé un UUID dans un **libellé
descriptif**, ce qui le rendait non comparable. Un libellé n'a pas à porter une valeur aléatoire.

---

## 9. Ce qui n'est PAS couvert

- **13 contrôles du §30 sont reportés**, chacun rattaché à son lot par le contrôle. Ce n'est pas une
  omission : ils portent sur des tables que ce lot ne crée pas ;
- **§30.4, l'existence d'un DSM**, et **§30.8, le bureau publié** — motifs au §3 ;
- **Row-Level Security**, que le §2.5 cite comme « compatibilité future ». Rien ne la datant, elle
  n'est pas inventée ;
- **`ECART-012` attend Léa**, et c'est le seul point du lot en attente d'une décision produit ;
- **`make jeu-de-donnees` et la suite de tests s'excluent** : de nombreux tests comparent des comptes
  **absolus**. La cible l'annonce en sortie, plutôt que de laisser le désordre se découvrir ;
- **le générateur n'engendre aucun `technical_role_assignment`** : le §8.6 rattache `SUPER_ADMIN` à
  une notion d'administration que le LOT 3 posera, et fabriquer des rôles techniques avant
  l'authentification serait inventer.

---

## 10. Ce que la porte `G2` doit savoir

**Les six critères techniques sont acquis et mesurés. Le septième est la décision de Jonathan.** La
[checklist de validation `G2`](checklist-validation-G2.md) la lui remet : les sept critères avec leurs
preuves, les huit stories, les 25 contrôles du §30 classés, une démonstration guidée, ce qui reste
ouvert, et ce que la pose du tag déclenchera.

**Trois points à dire explicitement à la porte :**

1. **`ECART-032`** — le backlog interdit plus large que le cahier, la matrice **et** le modèle. Le
   livrable est conforme au document prévalent, mais un relecteur du backlog conclurait à un critère
   manquant ;
2. **`ECART-031`** — une règle du §8.4 est **inapplicable**, non oubliée ;
3. **le tag `v0.2.0` déclenchera `images.yml`**, comme `v0.1.0` l'a fait, et publiera l'étiquette
   `0.2.0`. **Le dire avant de poser le tag, pas après** — leçon de `G1`.
