# Compte rendu — LOT 2, sous-étape `T10`

**Contraintes de rôles et de périmètres**
**Story :** `MVP-L02-US005` — issue `#43`
**Réalisée le :** 19 août 2026
**Décision produite :** `DEC-514`
**Écart consigné :** `ECART-032`

---

## 1. Ce que cette sous-étape devait faire — et deux tiers étaient déjà faits

`US005` porte **trois** critères d'acceptation. Le premier travail a été de les **vérifier** au lieu
de les implémenter :

| Critère de `US005` | État avant `T10` | Où |
|---|---|---|
| « un seul Booster actif par cercle » | **déjà acquis** | `T8`, index partiel du §25.1, `ix_framework_responsibility_assignment_circle_id_booster_actif` |
| « aucune responsabilité active dans plusieurs entités » | **déjà acquis** | `T8`, déclencheur `booster_une_seule_entite` |
| « DG implique DSM local » | **à faire** | `T10`, déclencheur `dg_implique_dsm_local` |

**Réimplémenter aurait produit un doublon silencieux.** Une seconde contrainte de même objet n'aurait
rien cassé — donc rien ne l'aurait signalée — et aurait doublé la surface à maintenir. C'est le seul
cas de ce lot où la bonne action pour deux tiers d'une story était de **ne rien écrire**, et de le
prouver.

S'y ajoutent les **trois règles inter-tables notées en `T5`, `T6` et `T7`** comme relevant du §6.5, et
la règle de **non-effet** du §8.2.

---

## 2. `ECART-032` — le backlog interdit plus large que le cahier, et c'est lui l'exception

En vérifiant le deuxième critère, un écart de vocabulaire est apparu, et il touche la lecture de la
porte.

| Document | Ce qu'il écrit |
|---|---|
| **Backlog `US005`** | « aucune **responsabilité métier** active dans plusieurs entités » — donc les **quatre** types |
| Cahier des charges §4.1 | « une personne ne peut pas être **Booster** active dans plusieurs entités » |
| Matrice des rôles §3 | « Une personne ne peut pas être **Booster** active simultanément dans plusieurs entités. » |
| Modèle §8.4 | « une personne ne peut pas être **Booster** active dans plusieurs entités simultanément » |

**Trois documents sur quatre restreignent au seul Booster, dont le document prévalent.** Le §3 de la
préséance règle donc le cas sans arbitrage : le déclencheur de `T8` est **conforme**, et l'énoncé du
backlog est une généralisation de son propre résumé.

**Et l'énoncé large n'est pas appliqué délibérément, pas par commodité.** L'appliquer interdirait des
données que le corpus autorise ailleurs : la matrice §5.1 prévoit qu'un super-administrateur
« intervienne dans toutes les entités », et le §8.6 rend `entity_id` **nullable** pour `SUPER_ADMIN`
précisément pour cela. **L'erreur serait du côté coûteux** — un refus est un échec dur, une permission
se resserre plus tard. Même contresens que `T7` a évité sur les cercles secondaires et `T8` sur la
multiplicité des `DSM`.

Si Léa veut la portée large, elle est **techniquement immédiate** : retirer la condition
`NEW.responsibility_type = 'BOOSTER'` du déclencheur suffit.

---

## 3. « DG implique DSM local » — le modèle décrit une ACTION, le backlog une IMPLICATION

**Les deux énoncés ne demandent pas la même chose, et un seul est applicable par la base.**

| Source | Énoncé |
|---|---|
| Modèle §8.4 | « un DG reçoit **automatiquement** une responsabilité DSM dans la même transaction que son attribution de catégorie » |
| Backlog `US005` | « **DG implique** DSM local » |

Le premier est une **action** : créer une ligne. Or `framework_responsibility_assignment` porte
`assigned_by_person_id` en `NOT NULL`, et **un déclencheur ne sait pas qui attribue**. Les seules
valeurs disponibles seraient la personne elle-même — un DG qui se nomme DSM — ou un identifiant
technique inventé.

**Fabriquer un attributeur fabriquerait une trace d'audit fausse**, et la matrice §5.1 exige que les
interventions sensibles soient auditées. Le §7.0 interdit d'écrire une empreinte qu'on n'a pas
relevée ; **une responsabilité attribuée par personne relève de la même classe**. Une trace fausse est
pire qu'une trace absente : la seconde se voit.

**L'implication, elle, se vérifie sans rien inventer.** Le déclencheur refuse
`professional_category = 'dg'` s'il n'existe pas de responsabilité `DSM` active dans **la même
entité**. Le service qui créera la responsabilité — `T11` ou LOT 3 — **satisfera** cet invariant au
lieu de s'y substituer, et il connaîtra, lui, l'auteur de l'attribution.

**Cinq tests, dont trois témoins qui discriminent :**

| Test | Ce qu'il écarte |
|---|---|
| `dg` sans responsabilité → refusé | le cas nominal |
| `dg` avec `DSM` locale → accepté | un déclencheur qui refuserait tout |
| `dg` avec `DSM` dans une **autre** entité → refusé | le mot **local** |
| `consultant` sans responsabilité → accepté | un déclencheur qui s'appliquerait à toutes les catégories |
| `dg` avec **`ESM`** locale → refusé | un déclencheur qui se contenterait d'« une responsabilité quelconque » |

Le dernier est celui qui manquerait le plus : sans lui, un contrôle relâché aurait donné la même
observation que le contrôle juste.

---

## 4. « Une `mission` exige un client actif POUR L'ENTITÉ » — et `client.status` est le mauvais champ

Le §6.5 pose : « `mission` exige un client actif, `intercontract` interdit un client actif ». Le second
sens était acquis en `T5` par `ck_professional_status_assignment_client_selon_le_statut`, qui impose
`client_id IS NULL`. Le premier restait ouvert, et `T5` puis `T6` l'avaient noté.

**Le champ à lire n'est pas celui qu'on croit.** Le §7.2 autorise « archiver **localement** une
relation » : un client peut être

- globalement `active` mais **localement archivé** — donc pas actif pour l'entité ;
- globalement `archived` mais **localement actif** — donc actif pour l'entité.

Lire `client.status` aurait donné le mauvais verdict **dans les deux sens**. Le déclencheur exige donc
une ligne de `entity_client` **non archivée** pour le couple `(entity_id, client_id)`.

**Quatre tests, dont trois écartent une lecture trop faible :**

| Test | Ce qu'il écarte |
|---|---|
| client existant, **aucune** activation → refusé | le cas nominal |
| client existant **et activé** → accepté | un déclencheur qui refuserait tout |
| activation **archivée** → refusé | lire `entity_client` sans regarder `archived_at` |
| activation dans une **autre** entité → refusé | oublier « pour l'entité » |
| `intercontract` sans client → accepté | un déclencheur qui se réveillerait hors de son cas |

---

## 5. Deux effets de bord mesurés, que le critère ne visait pas

### 5.1 Le déclencheur masquait le bon message d'erreur

Ma première version se réveillait aussi quand `client_id` était **nul**. Une ligne `intercontract`
mal formée — statut `intercontract` **avec** un client, ou statut `mission` **sans** client —
recevait alors « pas de client actif dans cette entité », alors que la règle réellement enfreinte est
`client_selon_le_statut`, posée en `T5`.

**Un message juste sur le fond mais faux sur la cause enseigne à chercher au mauvais endroit.** Le
déclencheur est borné à `NEW.client_id IS NOT NULL`, et la contrainte de `T5` garde la parole sur le
cas nul.

### 5.2 Le déclencheur OMBRAGE la clé étrangère de `client_id`, et cela a inversé un test de `T6`

**Mesuré, et c'est le §7.21 pour la sixième fois de ce lot** — cette fois sur un test que j'avais moi-même
écrit trois sous-étapes plus tôt.

`T6` avait ajouté la clé étrangère `fk_professional_status_assignment_client_id_client`, acquittant une
dette de `T5` où `client_id` était un `uuid` libre. Son test le prouvait **par le comportement** : un
`client_id` inexistant devait produire le nom de la clé étrangère dans le message.

Ce test échoue depuis `0011`, et **le livrable est conforme** :

> **les déclencheurs `BEFORE ROW` s'exécutent AVANT la vérification des clés étrangères.**

Un `client_id` inexistant n'a donc **aucune** activation dans l'entité : le déclencheur parle le
premier. Et la clé n'est atteignable par aucun autre chemin — pour une ligne `intercontract`,
`client_selon_le_statut` impose `client_id IS NULL`.

**La clé étrangère est donc devenue inatteignable par le comportement.** Trois réactions, une seule
bonne — c'est le §7.20 :

- la **supprimer** : le §6.5 la veut, et elle redeviendrait la seule barrière si le déclencheur
  changeait ;
- **affaiblir le test** pour accepter l'un ou l'autre message : il ne discriminerait plus rien ;
- **le faire dire le vrai**, ce qui est retenu : il porte sur le mécanisme réel, **et prouve la clé par
  `pg_constraint`** — le catalogue prouve ce que le comportement ne peut plus prouver.

Même situation que la contrainte ombragée de `T4`, et même parti qu'en `(b)` de `DEC-511` : la règle
écrite est conservée.

---

## 6. Une règle de NON-EFFET, qui ne se prouve qu'en montrant que rien n'a changé

Le §8.2 pose : « le Booster d'un cercle secondaire ne modifie pas le cercle principal, le DSM, le
client ou le statut de la personne ».

**Aucune contrainte ne peut l'exprimer, et c'est normal : il n'y a rien à refuser.** Ce qui pourrait la
violer est un **service trop zélé**, pas une ligne. Le seul garde-fou possible est un test qui relève
l'état complet des quatre relations citées, ajoute un cercle **secondaire** *et* sa responsabilité de
`BOOSTER`, puis compare.

Même parti qu'en `T6` pour les alias clients — et le test est écrit pour que **son propre échec soit
distinguable** : il compare un quadruplet complet, non un compte.

---

## 7. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `make code-check` | **code 0** — 34 fichiers `.py` identiques de part et d'autre |
| `alembic upgrade head` | `0011` appliquée |
| `make alembic-check` | **code 0** — 1 tête attendue, 1 trouvée |
| `alembic check` | « No new upgrade operations detected » — le modèle et la base concordent |
| `make historisation-check` | **code 0** — les **7** relations du §25.2, **10** exclusions, **3** colonnes nullables toutes protégées |
| `uv run pytest` | **333 tests, 0 échec** — c'était 322 avant `T10` |
| `make check` | **code 0** |
| Schéma réel, **énuméré** | **18 tables métier** — 19 avec `alembic_version` — **8 déclencheurs** non internes, **8 fonctions** plpgsql, **10 exclusions** |

**Le compte de déclencheurs a été énuméré, pas déduit — et il l'a fallu.** Je portais « 8 avant
`T10` » en tête ; la liste en donne **8 après**, donc **6 avant**. Un compte de mémoire dans un rapport
est un `ECART-021` en puissance, et celui-ci a été attrapé par la seule discipline d'énumérer avant
d'écrire.

Les huit déclencheurs, par table :

```text
circle                                  circle_archivage_sans_membres_actifs
dsm_assignment                          dsm_responsabilite_active
entity                                  entity_code_immuable_apres_activation
entity_membership                       dg_implique_dsm_local                 ← T10
entity_membership                       entity_membership_entite_non_archivee
framework_responsibility_assignment     booster_une_seule_entite
person                                  person_anonymisation_terminale
professional_status_assignment          mission_client_actif_dans_l_entite    ← T10
```

---

## 8. Défauts, tous dans mon travail

| № | Défaut | Comment il a été trouvé |
|:--:|---|---|
| `T10-1` | Le déclencheur de mission se réveillait sur `client_id IS NULL` et **masquait** le message de `client_selon_le_statut` | un test de `T5` a produit le mauvais message d'erreur |
| `T10-2` | Le test de clé étrangère de `T6` échouait sur un livrable **conforme** : ombrage par le déclencheur `BEFORE` | l'exécution de la suite après la migration |
| `T10-3` | Mon script de correction des tests a **échoué sur son ancrage**, et n'a donc **rien écrit** dans `test_appartenance.py` | l'assertion du script, qui a levé au lieu de patcher à côté |
| `T10-4` | **Deux comptes de ce compte rendu même** : « 10 déclencheurs », par report d'un compte de mémoire ; et « 19 tables », qui comptait `alembic_version` sans le dire alors que la cartographie de `CLAUDE.md` en annonce **18** | l'énumération, faite **avant** d'écrire le nombre — et pour le second, la **confrontation à l'autre document** qui affirmait un nombre différent |

**`T10-3` est le seul défaut de ce lot dont la parade a fonctionné du premier coup.** Le script
assertait `count(ancre) == 1` avant chaque remplacement : l'ancre ayant changé, il a levé et
**n'a pas écrit un fichier à moitié patché**. Le même script en `T9` — défaut `T9-3` — n'assertait
pas, et son remplacement n'avait silencieusement rien fait. La leçon est déjà écrite au §7.0 :
un contrôle qui n'annonce pas ce qu'il a examiné peut n'avoir rien examiné. Ici la parade était
posée, et elle a servi.

**`T10-4` est plus instructif qu'il n'y paraît, et il a fallu DEUX passes pour l'épuiser.** Le
compte de six déclencheurs devenus huit n'aurait invalidé aucun contrôle : le nombre n'est cité
nulle part ailleurs. Il aurait simplement été **faux dans un rapport lu par Jonathan**, et un
lecteur ultérieur aurait bâti dessus.

**Puis le même défaut est réapparu deux paragraphes plus loin, dans le même document.** J'ai écrit
« 19 tables » — le nombre brut d'`information_schema` — alors que la cartographie de `CLAUDE.md`
annonce **18**. Les deux sont justes : `alembic_version` en est une, et ce n'est pas une table
métier. **Mais un nombre juste qui ne dit pas ce qu'il mesure produit exactement le même désordre
qu'un nombre faux** — c'est la sixième proposition du §7.0, celle de `T7` sur les tailles d'image,
et elle vient de se rejouer dans un compte rendu au lieu d'un contrôle.

**Ce qui l'a attrapé n'est pas la vigilance mais une confrontation** : la cartographie affirmait un
autre nombre, et deux documents en désaccord obligent à mesurer. La leçon est donc pratique — quand
un compte existe déjà ailleurs, **va le lire avant d'écrire le tien**. `ECART-021` et `ECART-023`
réunis. **Le tableau ci-dessus liste les huit noms de déclencheurs**, et le §7 nomme les deux
grandeurs de tables, pour que le prochain les compte plutôt que de les croire.

---

## 9. Ce qui n'est PAS couvert

- **la création automatique de la responsabilité DSM** (§8.4) n'est **pas** faite : seule
  l'implication est appliquée. Le motif est au §3 — le déclencheur ne connaît pas l'attributeur.
  **À faire au service**, `T11` ou LOT 3 ;
- **« un bureau publié a entre un et trois responsables actifs »** reste inapplicable :
  `ECART-031`, `office` ne déclare aucun état de publication ;
- **« l'administrateur d'entité ne peut pas créer ou clôturer ces affectations »** (§8.4) est une
  règle de **permission**, non de donnée : elle relève du LOT 3, et la base n'a pas de notion de
  rôle appelant. `QO-116` porte déjà le sujet voisin du moindre privilège ;
- **l'énoncé large de `ECART-032`** n'est pas appliqué, et le motif est au §2 ;
- **`assignment_reason` « obligatoire pour changement sensible »** (§8.4) n'est pas contraint : le
  modèle ne définit pas « changement sensible ». Ne rien inventer — §6.5.

---

## 10. Ce que `T11` devra savoir

1. **`T11` porte l'isolation inter-entités, `US006`** — et le travail de `T5` l'a largement préparée :
   les **clés étrangères composites** `(id, entity_id)` du §25.3 font que la base refuse déjà une
   relation dont les deux bouts ne sont pas dans la même entité. `T11` doit **le mesurer** avant de
   poser quoi que ce soit, exactement comme `T10` l'a fait pour `US005` — deux tiers de la story
   pourraient être acquis.
2. **Le critère de `US006` dit « les tests démontrent l'absence de fuite ».** Une absence ne se
   démontre pas en montrant qu'un cas passe : il faut **compter** les chemins de fuite examinés et
   confronter ce compte à un attendu **dérivé** du §25.3. C'est la troisième proposition du §7.0, et
   c'est ce que `make historisation-check` fait pour le §25.2.
3. **Les deux déclencheurs de `T10` lisent des tables voisines** — `framework_responsibility_assignment`
   et `entity_client`. Un service qui insérerait dans un ordre différent les rencontrera. L'ordre est
   contraint : la responsabilité `DSM` **avant** la catégorie `dg`, l'activation locale du client
   **avant** la situation `mission`.
4. **La création automatique de la responsabilité DSM revient à `T11` ou au LOT 3**, et elle devra
   fournir un `assigned_by_person_id` réel.
