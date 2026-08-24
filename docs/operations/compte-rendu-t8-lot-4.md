# Compte rendu — LOT 4, sous-étape `T8`

**Le changement d'entité, et quatre défauts dont trois dans mes propres contrôles**
**Story :** `MVP-L04-US002` · **Réalisée le :** 24 août 2026
**Décision produite :** `DEC-552` · **Écart consigné :** aucun
**Migration produite :** **aucune**

---

## 1. La règle n'a pas été inventée : la matrice §5.1 la donne entière

Le cahier §23.3 et la matrice §23.3 posent les **mêmes cinq règles** du changement d'entité. Ni
l'un ni l'autre ne dit **ce que deviennent** les permissions. C'est la **matrice §5.1** qui le dit,
et c'est la section dédiée que le §7.29 apprend à chercher :

> « Lorsqu'une personne consulte une entité différente de son entité principale : elle possède
> uniquement les droits `EMP` ; ses responsabilités DSM, ESM, Booster, responsable de bureau ou
> administrateur d'entité ne s'appliquent pas ; aucune action de création, modification,
> publication, archivage, restauration ou export n'est proposée ; les contrôles côté API utilisent
> l'entité de la ressource, et non uniquement l'entité sélectionnée dans le frontend.
> Le super-administrateur constitue la seule exception globale. »

La résolution tient donc en **trois branches, toutes écrites** :

| Situation | Ce qui s'applique | Source |
|---|---|---|
| `SUPER_ADMIN` actif | l'exception globale | §5.1, dernière phrase |
| entité consultée **=** entité principale | **union** des responsabilités | §23.1 |
| entité consultée **≠** entité principale | **`EMP` seulement** | §5.1 |

**Aucune quatrième branche n'a été ajoutée**, et le §23.2 — « restriction la plus forte » — n'en est
pas une : il porte sur des interdictions liées à **la ressource ou à l'état**, et ce lot est en
lecture seule. **Il n'y avait donc aucune décision de fond à prendre, et aucune question à poser.**

---

## 2. Trois garanties étaient déjà structurelles, et c'est mesuré

Le §5.1 aurait pu demander du code défensif. Le socle du LOT 2 le rend inutile, et le §7.32 dit quoi
faire : ne pas écrire la défense, **exiger que la base continue d'interdire**.

| Mesure du 24/08/2026 | Ce qu'elle rend structurel |
|---|---|
| `ck_technical_role_assignment_portee_selon_le_role` : `CHECK ((role_type='ENTITY_ADMIN' AND entity_id IS NOT NULL) OR (role_type='SUPER_ADMIN' AND entity_id IS NULL))` | « le super-administrateur constitue la **seule** exception globale » est une **contrainte de base**, pas une convention |
| `framework_responsibility_assignment.entity_id` **NOT NULL** | « aucune permission locale n'est transférée » n'est pas une précaution de notre code : une responsabilité **sans entité ne peut pas exister** |
| `uq_entity_membership_person_id_occupante` : `UNIQUE (person_id) WHERE membership_state IN ('future','active')` | l'entité principale est **unique par construction** — il n'y a pas de cas « plusieurs entités principales » à arbitrer |

Les trois sont éprouvées par des tests qui exigent le **nom** de la contrainte violée. Si un lot
ultérieur les relâchait, celui qui le fait saurait qu'il doit relire
[`app/permissions/services.py`](../../apps/api/app/permissions/services.py).

---

## 3. Une contrainte mesurée a fermé la conception du décor avant la première exécution

`ex_framework_responsibility_assignment_sans_portee` exclut sur
`(person_id, responsibility_type, period)` — **sans `entity_id`**. Une personne **ne peut donc pas**
être `ESM` dans deux entités à la fois.

Ma première conception voulait « `ESM` dans A **et** `ESM` dans B ». La mesure l'a refusée. Le décor
emploie donc `ENTITY_ADMIN` pour l'entité B, dont l'exclusion, elle, **porte `entity_id`**.

**Le décor final discrimine les quatre règles en DEUX appels :**

| Décor | Attendu | Ce que son échec prouverait |
|---|---|---|
| A, principale · `ESM` actif | **présent** | rien ne serait accordé du tout |
| A · `ENTITY_ADMIN` actif | **présent** | l'union du §23.1 ne se ferait pas |
| A · `OFFICE_MANAGER` **clos** | **absent** | les périodes ne sont pas consultées — contrôle §24.12 |
| A · `DSM` **futur** | **absent** | le filtre est `ends_at IS NULL`, qui est vrai d'une affectation future |
| B, autre · `ENTITY_ADMIN` actif | **absent** | une permission locale est **transférée** — §5.1 |

> **Le droit local de B existe VRAIMENT en base, et un contrôle le vérifie avant.** Sans lui,
> l'absence de `ADM-E` dans la réponse serait indistinguable d'une **absence de donnée**. La
> différence est exactement celle du §7.0 : ce contrôle ne prouve pas qu'un rôle absent est absent,
> il prouve qu'un rôle **présent** ne s'applique pas.

---

## 4. Les deux premières règles sont des interdictions d'écriture, et on ne les croit pas

« Ne modifie pas l'entité principale de la personne », « ne transfère pas ses responsabilités ».

Depuis `DEC-545`, le changement d'entité est une **navigation** : il n'existe **aucun endroit** où
l'entité principale pourrait être modifiée. Le §7.32 dit quoi faire d'un état que la conception rend
impossible — **exiger qu'il le reste** :

- les **quatre** tables de rattachement — `entity_membership`,
  `framework_responsibility_assignment`, `technical_role_assignment`, `dsm_assignment` — sont
  relevées par **empreinte `md5` d'un agrégat trié** avant et après le parcours complet ;
- un `count(*)` n'aurait pas suffi : une ligne **modifiée** sans changement de nombre donnerait la
  même observation qu'un état intact ;
- **l'empreinte porte son propre témoin** : si elle ne bougeait pas après huit insertions, le
  contrôle ne mesurerait rien.

**Et ce qui change PAR CONCEPTION est nommé, pas tu.** `user_session.last_activity_at` est réécrit à
chaque lecture métier — `exiger_une_session` réutilise `lire_et_rafraichir`, seul chemin de
validation du projet, entorse examinée et acceptée par `DEC-531`. Le contrôle **exige** que
l'activité ait avancé et le **rapporte**. C'est le §7.20 : exiger ce qui est exigible, rapporter
visiblement ce qui ne l'est pas.

---

## 5. Quatre défauts, dont trois dans mes propres contrôles

### `T8-1` — mon contrôle du 404 exigeait plus que le critère

Je comparais les deux réponses 404 — celle des permissions et celle de `GET /entities/{code}` —
signature entière. **Échec sur un livrable conforme** : l'identifiant de corrélation est engendré
**par requête**, et le cahier §17.4 exige qu'il le soit pour qu'un utilisateur puisse le citer dans
un signalement.

Deux remèdes possibles, et le choix compte : **exclure** le champ des deux côtés rendrait le
contrôle aveugle à sa **disparition** — l'échec produirait alors la même observation que le succès.
La correction **épingle** la corrélation en l'envoyant, si bien que la comparaison reste **totale**.
Et c'est la parade que `verifier-entites.py` employait **déjà**, avec sa constante
`CORRELATION_FIXE`. §7.20, et §7.34 — une parade écrite une fois ne se propage pas toute seule.

### `T8-2` — mon contrôle d'ordre ne discriminait pas, et la conclusion a porté sur le CODE

Je rendais `tuple(sorted(ensemble))` et je vérifiais que deux appels rendent le même corps.
**Mesure : le `sorted` retiré du service, les quinze contrôles passaient TROIS FOIS sur trois.**

| Version du contrôle | Verdict avec le défaut |
|---|---|
| deux appels comparés entre eux | **vert** — l'itération d'un `set` est stable au sein d'un processus, et les deux appels tombent sur le même worker |
| « la réponse doit être triée » | **vert** — l'ordre du `set` de ce décor coïncide avec l'ordre alphabétique |
| impossible d'aller plus loin | deux ensembles égaux s'itèrent **identiquement** en CPython ; l'ordre ne varierait qu'**entre processus**, qu'aucune exécution unique n'observe |

**La conclusion a donc porté sur le livrable, pas sur le contrôle** : l'ordre vient désormais de
l'itération de `RoleDeLaMatrice`, donc le perdre exigerait de **supprimer la boucle**. C'est le §7.32
transposé — ne pas tester ce qu'on peut rendre impossible. Et l'ordre obtenu est celui du **tableau
§3 de la matrice**, qui est meilleur qu'alphabétique : c'est celui du document.

> **Au passage, mes contrôles 3 et 8 RETRIAIENT la réponse avant de la comparer.** Ils étaient donc
> aveugles à l'ordre eux aussi. Ils comparent maintenant la réponse **telle qu'elle est**, à un
> attendu **dérivé de l'énumération**.

### `T8-3` — mon témoin de latence n'exerçait rien

Il montait Bordeaux, **démontait**, montait Lille, puis libérait la réponse de Bordeaux. **La garde
sur le code retirée du cadre, les 99 tests passaient quand même.**

Le démontage crée **deux instances aux états séparés** : la réponse de Bordeaux ne pouvait de toute
façon pas atteindre l'arbre de Lille, et React ignore un `setState` après démontage. Le test ne
modélisait pas le défaut qu'il prétendait attraper — **§7.25, seconde leçon : un témoin qui n'exerce
pas un contrôle ne prouve rien de ce contrôle.**

Le vrai parcours est un **clic dans le sélecteur** : une seule instance, dont le paramètre `code`
change. La nouvelle version fait cela, et **éprouve le sélecteur du même geste**.

### `T8-4` — un vrai défaut du livrable, vu au navigateur

**Celui-là n'était pas dans un contrôle.** À l'écran, l'API rendait
`est_entite_principale: false` et la mention du §5.1 **n'apparaissait pas**.

Le journal réseau donnait la cause : **deux** appels de permissions — un `net::ERR_ABORTED`, un à
200 — et le second revenait **avant** l'entité. Ma première version n'écrivait la liste et les
droits que dans une variante `trouvee` **déjà existante** : arrivés avant, ils étaient perdus
définitivement.

**Et aucun des cinq tests de `T8` ne l'attrapait**, parce qu'un `fetch` bouchonné résout dans
l'ordre de création des promesses, et le cadre demande l'entité en premier. §7.16 — ce qui n'a jamais
tourné ailleurs n'est pas éprouvé — et §7.24 : le succès d'un test et la justesse du livrable sont
deux grandeurs différentes.

**La correction a demandé deux essais, et chacun a été attrapé par le témoin de latence :**

| Essai | Ce qu'il faisait | Ce que le témoin a dit |
|---|---|---|
| 1 | repartir d'une charge vide quand le code de l'état diffère | une réponse tardive de Bordeaux **écrasait** l'état de Lille : « expected 'eXalt Onboarding' to contain 'eXalt Lille' » |
| 2 | ignorer toute réponse dont le code diffère de celui de l'état | la **première** réponse du nouvel effet est dans ce cas elle aussi — Lille était ignorée, l'écran restait sur « Chargement » |
| 3 | **le nettoyage de l'effet pose `obsolete`** | vert, et les deux défauts réinjectés échouent |

**Ce qui discrimine n'est pas le code dans l'état, c'est l'effet courant** — et un effet nettoyé est
**par définition** supersédé. Un témoin qui attrape les régressions de deux correctifs successifs
vaut ce qu'il a coûté.

Un test **fixe désormais l'ordre inverse** — les droits avant l'entité — et il n'existait pas.

---

## 6. Ce que le sélecteur est, et pourquoi il n'est pas un formulaire

`DEC-545` : l'entité consultée vit dans l'**adresse**. Changer d'entité est donc un changement
d'URL, et l'élément qui change une URL est un `<a>`. Trois conséquences que rien d'autre n'aurait
données :

- les règles 1 et 2 du §23.3 sont tenues **par construction** — aucune écriture, donc aucun endroit
  où l'une des deux pourrait s'installer plus tard ;
- le choix **survit à un rechargement**, et le bouton « précédent » ramène à l'entité d'avant ;
- chaque entité a une **adresse partageable**.

**Un `<select onChange>` aurait été deux pièges** : son événement se déclenche à la **flèche** sur
certains navigateurs, donc parcourir la liste au clavier aurait navigué à chaque touche ; et il
aurait ouvert l'endroit où une écriture pourrait s'installer.

`make cadre-check` **l'exige** : le sélecteur ne doit contenir aucun des **six** motifs d'écriture
cherchés, et doit rendre au moins un `<Link>`. C'est une exigence d'**absence** — elle ne se déclare
pas, elle se vérifie.

**Et le contrôle des replis a été GÉNÉRALISÉ, pas recopié.** Sa première version ne portait que sur
`BarreMobile.tsx`, parce que « Plus » était le seul repli du jour. Une exigence écrite contre **un**
exemple ne couvre que cet exemple, §7.34 : tout module employant `<details>` est désormais examiné,
et le contrôle **annonce combien il en a trouvé** — **deux**.

---

## 7. Mesures

| Grandeur | Valeur, dérivée |
|---|---|
| `make permissions-check` | **15 contrôles, 0 échec**, à travers Caddy en HTTPS |
| `make cadre-check` | **21 contrôles**, 0 échec — 20 avant `T8` |
| `make cadre-temoin` | **11 motifs** exigés et nommés — 9 avant `T8` |
| pytest | **697**, dont **418** d'intégration |
| Vitest | **207** — 90 `ui`, **100** `web`, 17 `contracts` |
| `apps/api/tests/test_permissions.py` | **14 tests**, dont **3** qui exigent que la base continue d'interdire |
| Endpoints du contrat | **13** |
| Cibles `Makefile` | **81** |
| Migration | **aucune** — `T8` ne touche pas au schéma |

**Témoins négatifs réellement exécutés, cinq défauts injectés un par un :**

| Défaut injecté | Résultat |
|---|---|
| la branche du §5.1 neutralisée | `AUTRE entite : ['ADM-E', 'EMP'] au lieu de ['EMP'] — une permission locale a ete TRANSFEREE` |
| `ends_at IS NULL` au lieu de la plage | **2 échecs** : l'union rend `DSM` en trop, et « affectation FUTURE » échoue. Le rôle **clos** restait correctement absent — ce qui montre précisément ce que `ends_at IS NULL` couvre et ce qu'il ne couvre pas |
| le tri retiré | **vert trois fois sur trois** → c'est ce qui a fait rendre l'ordre **structurel** |
| la garde `obsolete` neutralisée | **1 échec**, le témoin de latence |
| les droits écrits seulement sur un état `trouvee` | **3 échecs**, dont le témoin central |

---

## 8. Ce que `T8` ne fait pas, et ce qu'elle laisse à la suite

- **aucune liste d'actions autorisées** dans la réponse. La matrice en déclare des dizaines, par
  ressource, et les inventer serait la règle §6.5 enfreinte. Le §5.1 dit où cela se joue : « les
  contrôles côté API utilisent l'entité de la **ressource** » — donc chaque route métier des lots
  suivants tranchera sur la sienne ;
- **`NEW` et `SERVICE` ne sont pas résolus, et c'est dit.** `NEW` suppose une fiche d'arrivée ou un
  onboarding actif : ni l'un ni l'autre n'existe dans le schéma, ils appartiennent aux LOTS 7 et 8.
  Le déduire d'autre chose serait une invention ;
- **aucun menu n'est encore masqué.** C'est `T9`, `US005` — « les menus masquent ; l'API refuse ».
  `T8` livre ce que `T9` consommera : les rôles par le contexte de l'`Outlet`, et le `null` qui
  distingue « inconnu » de « aucun droit » ;
- **la mention « consultation uniquement » n'est pas une invention** : sa formulation est celle du §4
  de la matrice, et ce qu'elle dit est la conséquence du §5.1 — « aucune action de création,
  modification, publication, archivage, restauration ou export n'est proposée ». L'utilisateur doit
  savoir **pourquoi** les actions manqueront, sans quoi il les croira cassées.

**Et une chose que `T9` doit savoir :** `est_entite_principale` n'est pas une commodité. C'est la
seule information du §5.1 qui **ne se lit pas** dans la liste des rôles — une personne sans
responsabilité rend `["EMP"]` dans son entité principale **et** ailleurs, et le §5.1 interdit de
*proposer* des actions hors de l'entité principale. Masquer sur la seule liste des rôles serait donc
faux dans exactement ce cas.
