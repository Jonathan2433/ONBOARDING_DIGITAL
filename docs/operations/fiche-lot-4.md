# Fiche de lot — LOT 4

**Portail national, sélection d'entité et navigation**
**Porte de validation :** `G4`, tag `v0.4.0` prévu
**Ouvert par Jonathan le :** 22 août 2026 — décision `DEC-541`
**Rédigée le :** 22 août 2026, au franchissement de la porte `G3`
**Statut de cette fiche :** **découpage VALIDÉ par Jonathan le 22/08/2026** — « parfait »
**Avancement :** **`T1` à `T7` terminées** le 23/08/2026, **`T8` à `T10` le 24/08/2026**. Deux sous-étapes restantes

> **Aucune ligne de code de ce lot n'est écrite avant que tu n'aies validé le §3.** C'est la règle qui
> a tenu aux LOTS 2 et 3, et elle tient ici.

---

# 1. Ce que le lot doit produire

**L'objectif de la roadmap, littéralement :** « fournir le squelette utilisateur final et la
consultation inter-entités **en lecture seule** ».

Aucune écriture métier. Le portail devient utilisable, l'utilisateur choisit l'entité qu'il consulte,
et la navigation existe à cinq largeurs. **Rien n'est modifiable.**

## 1.1 Les sept stories, comptées dans le backlog

| Story | Priorité | Ce qu'elle exige |
|---|---|---|
| `MVP-L04-US001` | `P0` | choisir une entité depuis la page nationale — **la liste précède la carte sur mobile**, seules les entités **actives** sont proposées, le choix est **mémorisé pour la session** |
| `MVP-L04-US002` | `P0` | changer d'entité à tout moment — l'entité active reste **visible**, le changement recharge les données autorisées, **aucune permission locale n'est transférée** |
| `MVP-L04-US003` | `P0` | naviguer avec une barre inférieure responsive — accessible à **320 et 390 px**, focus et libellés corrects |
| `MVP-L04-US004` | `P0` | naviguer aux layouts tablette et bureau — **768, 1280, 1920 px**, et **le clavier atteint toutes les actions** |
| `MVP-L04-US005` | `P0` | ne voir que les menus correspondant à ses droits — les menus **masquent**, **l'API refuse néanmoins** |
| `MVP-L04-US006` | `P1` | comprendre une perte de connexion ou une erreur — hors connexion **après chargement**, pages `403`/`404`/`500`, identifiant de corrélation |
| `MVP-L04-US007` | `P1` | stabiliser les composants de navigation et retours système — documentés et **accessibles** |

**Sept, non huit.** Compté dans le backlog par `grep -c '^| \`MVP-L04-US'`, pas recopié.

## 1.2 Les six critères de sortie de la roadmap

| | Critère | Ce qui le rendra prouvable |
|:--:|---|---|
| ☐ | la liste précède la carte sur mobile | l'ordre dans le DOM, pas l'ordre visuel — un `order` CSS ne changerait rien pour un lecteur d'écran |
| ☐ | la navigation est **intégralement** utilisable au clavier | parcours de tabulation mesuré, et **aucun piège de focus** |
| ☐ | l'entité active est visible sur **toutes** les pages internes | la liste des pages **dérivée du routeur**, non recopiée |
| ☐ | les menus reflètent les permissions **sans les remplacer** | un témoin qui prouve que l'API **refuse** ce que le menu a masqué |
| ☐ | les erreurs réseau n'indiquent **jamais à tort** qu'une action est sauvegardée | le cas d'un `fetch` qui échoue **après** l'envoi |
| ☐ | **Jonathan valide les parcours de navigation** | la porte |

---

# 2. Ce que le corpus tranche déjà, et qu'il ne faut pas réinventer

**J'allais déclarer ouverte une décision déjà prise, et je l'ai vérifiée avant.** C'est la leçon la
plus chère du LOT 3 — le §8 de sa fiche a été faux **trois fois sur quatre**.

| Ce qu'on croirait à instruire | Ce que le corpus dit |
|---|---|
| les rubriques du menu principal | **le §8.2 les énumère** : Accueil · Framework · Trombinoscope · Événements · **Mon onboarding, uniquement lorsqu'un parcours actif existe** · **Administration, uniquement selon les permissions** |
| la barre mobile | **§8.2** : « sur mobile, une barre de navigation inférieure est utilisée. Les fonctions secondaires sont regroupées dans un accès **Plus** lorsque nécessaire » |
| le contenu de la page nationale | **§8.3** : une **liste accessible** des entités, une **carte de France**, un accès à chaque entité **active**. Et « sur mobile, **la liste précède la carte** » |
| les largeurs de recette | **cinq**, énumérées au cahier : 320, 390, 768, 1 280, 1 920 px. `LARGEURS_RECETTE` les porte déjà dans `packages/ui` depuis `T10` du LOT 1 |
| les familles de composants | **§13.3 en énumère douze** : boutons, champs, cartes, badges, menus, modales, onglets, tableaux, alertes, carrousels, lecteurs vidéo, états vides et chargements |
| l'arborescence complète | **le §8.1** la donne en diagramme, jusqu'aux sept sections d'administration |

**Trois composants existent déjà** dans `packages/ui` depuis `T10` du LOT 1 — `Bouton`, `Badge`,
`Carte` — avec des jetons **recalculés contre WCAG 2.2 AA**. Ne réinvente ni couleur ni espacement.

---

# 3. Le découpage proposé — douze sous-étapes

**L'API d'abord, et ce n'est pas un détail de goût.** La roadmap dit « route guards **uniquement
ergonomiques** · contrôles d'autorisation **systématiques dans l'API** », et la règle 5 du projet dit
que l'API est l'autorité finale. Commencer par l'interface produirait des écrans dont on ne saurait
pas s'ils protègent quoi que ce soit.

| | Sous-étape | Story | Critère de sortie |
|---|---|---|---|
| ~~**`T1`**~~ | ~~**Lister les entités, côté API.**~~ **TERMINÉE le 23/08/2026.** `DEC-543`, `DEC-544`. **Le critère nommait DEUX états non actifs, le modèle en déclare TROIS** — `draft` est le troisième, `ECART-039`, et c'est le §7.34 écrit la veille. Le filtre est écrit `= active`, **dérivé** de l'énumération, et un test **sans base** exige les quatre statuts connus : sans lui, mes trois témoins continueraient de passer en ne couvrant plus la classe. **Aucun contrôle de rôle**, et ce n'est pas un oubli : la matrice §5 met `ANON` à tiret et les **huit** rôles authentifiés à la coche — en ajouter un exigerait plus que la matrice. **`SERVICE` n'est pas une colonne de ce tableau**, le §22 dit « aucun rôle humain », et j'ai failli consigner un écart là où le corpus tranche. **Le résiduel de `DEC-531` est réexaminé** : l'entorse du `GET` qui écrit **se généralise** au lieu de disparaître, et un test la mesure. **Le piège `Annotated` est MESURÉ** — 422 sur `loc: ["query", "a"]`, donc un livrable qui *paraît* protégé. **674 tests** et **143 Vitest**, `make entites-check` — 10 contrôles, témoin négatif sur le conteneur reconstruit. Compte rendu : [`compte-rendu-t1-lot-4.md`](compte-rendu-t1-lot-4.md) | `US001` | ☑ |
| ~~**`T2`**~~ | ~~**L'entité consultée : où elle vit.**~~ **TERMINÉE le 23/08/2026.** `DEC-545`. **LE CAHIER L'AVAIT TRANCHÉ, et le §8 de cette fiche disait le contraire** : le §4.1, le §8.1, le §9.1 et le §9.2 font **tous** atterrir sur la page nationale après connexion, si bien qu'une mémoire serveur du dernier choix n'aurait **aucun consommateur**. `ECART-040`, et c'est le §7.29 pour la quatrième fois en deux lots. **L'entité vit donc dans l'ADRESSE** — aucune colonne, aucun stockage navigateur, **aucune migration**. **Le §23.3 existe et donne CINQ règles** que la fiche ne citait pas ; la quatrième, « annule les requêtes et caches associés à l'entité précédente », est implémentée et **testée sous latence fabriquée**. Une entité non active rend **404 identique** à une entité absente — le LOT 9 créera des brouillons. **683 tests** et **156 Vitest**, `entites-check` passe de 10 à **13 contrôles**. **Et mon nettoyage incomplet a cassé 23 tests du LOT 2** : `residu-check` a nommé la cause en un nombre. Compte rendu : [`compte-rendu-t2-lot-4.md`](compte-rendu-t2-lot-4.md) | `US001`, `US002` | ☑ |
| ~~**`T3`**~~ | ~~**Le cadre applicatif et les cinq largeurs.**~~ **TERMINÉE le 23/08/2026.** `DEC-546`. **DEUX DÉFAUTS ANTÉRIEURS L'ONT BLOQUÉE, ET IL A FALLU LES RÉPARER POUR MESURER.** `ECART-042` : `code-refresh` ne reconstruisait pas `web`, si bien que **le frontend servi était celui du LOT 1** depuis un mois — 9 fichiers contre 24 — et `ecrans-check` passait, le repli SPA rendant `text/html` pour n'importe quel chemin. `ECART-041` : **rien n'importait `jetons.css` ni `composants.css`**, donc **14 des 21 propriétés de `auth.css` ne résolvaient rien** et les trois boutons des huit écrans rendaient `border-radius: 0px` — **les huit écrans du LOT 3 n'avaient jamais porté le design system**. Mesuré avant et après dans un vrai navigateur. **Le cadre est une route de mise en page** : toute page interne hérite de l'en-tête par construction. **Le `<h1>` ne répète plus le nom de l'entité** — `useMatches` exige un data router, mesuré, donc le mécanisme de titre est **différé à `T4` avec ses rubriques en main**. **Débordement mesuré à SIX largeurs**, le cahier écrivant « 1 920 px **et plus** » : 0 débordement, 0 élément hors viewport. **683 tests** et **158 Vitest**, `make cadre-check` — 9 contrôles et son témoin, dans `make check` et dans la CI. Compte rendu : [`compte-rendu-t3-lot-4.md`](compte-rendu-t3-lot-4.md) | `US004` | ☑ |
| ~~**`T4`**~~ | ~~**La navigation principale, au clavier.**~~ **TERMINÉE le 23/08/2026.** `DEC-547`. **`RUBRIQUES` est la source unique** : le menu s'en rend, les six routes en sont **engendrées**, et le `<h1>` s'en dérive — `cadre-check` exige que `App.tsx` l'itère, et confronte les six libellés au §8.2 **mot pour mot**. **Le clavier est tenu en n'ajoutant RIEN** : six `<a href>`, aucun gestionnaire de touches, aucun `tabindex` — donc aucun piège possible. **Marche au clavier mesurée** : huit Tab, huit arrêts, `outline: solid 2px` sur les huit, le focus **sort** du menu au sixième. **Les deux rubriques conditionnelles sont ABSENTES par défaut** — aucune table de parcours n'existe (LOT 7), aucune route ne rend les rôles (`T9`) — et les tests éprouvent **les deux** états, séparément. **`ECART-043` : le lien d'évitement de `T3` ne sautait rien**, sa cible n'étant pas focusable — et mon test vérifiait le `href` et l'`id`, tous deux justes. **`ECART-044` : `verifier-ecrans.py` lisait les libellés du fichier entier**, alors que la même correction avait déjà été faite une fonction plus bas. **683 tests** et **173 Vitest**, `cadre-check` passe de 9 à **14 contrôles**, témoin sur **cinq** motifs. Compte rendu : [`compte-rendu-t4-lot-4.md`](compte-rendu-t4-lot-4.md) | `US004` | ☑ |
| ~~**`T5`**~~ | ~~**La barre inférieure mobile.**~~ **TERMINÉE le 23/08/2026.** `DEC-548`. **« Lorsque nécessaire » du §8.2 est MESURÉ, non supposé** : à `--taille-xs`, « Trombinoscope » fait 92 px et « Mon onboarding » 96 px ; à 320 px, **quatre** cellules de 80 px tiennent — un libellé sur deux lignes — et **six** cellules de 53 px en mettraient une sur **trois**. « Plus » apparaît donc dès qu'une conditionnelle existe. **Les deux lectures possibles coïncidaient**, et la mesure a rendu la question à Jonathan inutile. **« Plus » est un `<details>`** : aucun code ne touche au focus, donc aucun piège n'est possible — le contrôle interdit `.focus()`, `useRef` et `addEventListener` dans la barre. **Les deux repères ne coexistent jamais**, vérifié dans les **deux** sens ; un seul repère visible à 768 px, mesuré. **Cibles de 80×44 à 320 px et 98×44 à 390**, aucun libellé rogné, **césure française** mesurée — « Trombino-/scope » au lieu de « Trombinosc/ope ». **683 tests** et **183 Vitest**, `cadre-check` passe de 14 à **18 contrôles**, témoin sur **sept** motifs — dont un que j'ai dû rendre exact, ayant produit un **faux positif** dès sa première exécution. Compte rendu : [`compte-rendu-t5-lot-4.md`](compte-rendu-t5-lot-4.md) | `US003` | ☑ |
| ~~**`T6`**~~ | ~~**La page nationale : la liste accessible.**~~ **TERMINÉE le 23/08/2026.** `DEC-549`. **UN ARBITRAGE DE JONATHAN, PRIS SUR LE SENS PARCE QUE LA MESURE AVAIT ÔTÉ LE COÛT** : `/` était la page de statut depuis `T5` du LOT 1, et `verifier-page-statut.sh` n'en exigeait que la **coquille React** — jamais le contenu. La racine est donc la page nationale, le statut passe à `/statut`, et le contrôle vérifie désormais que cette adresse est **servie**. **La page nationale n'emploie pas le cadre applicatif** : on est **au-dessus** de l'entité, on la choisit. **La liste précède la carte DANS LE DOM**, et le contrôle exige qu'aucune règle CSS ne les réordonne — il **mordra à `T7`**. **Le frontend ne refiltre RIEN** : mesuré de bout en bout, sur quatre entités dont une `draft`, la page en affiche **trois**. Trois colonnes à 1 280 px, aucun débordement de 320 à 1 280. **683 tests** et **191 Vitest**, `cadre-check` passe de 18 à **19 contrôles**, témoin sur **huit** motifs. Compte rendu : [`compte-rendu-t6-lot-4.md`](compte-rendu-t6-lot-4.md) | `US001` | ☑ |
| ~~**`T7`**~~ | ~~**La carte de France illustrative.**~~ **TERMINÉE le 23/08/2026.** `DEC-550`. **TROIS MESURES ONT FERMÉ LE CHOIX AVANT D'ÉCRIRE** : `entity` ne porte **ni latitude ni longitude** ; **le prototype montre que l'intention n'est PAS une carte de données** — sa `FranceMap` est une image avec **un bouton posé dessus** ; et **`DEP-006` est OUVERTE, échéance ce lot**. Réutiliser l'image du prototype est interdit par la règle 4, ne rien livrer contredirait la roadmap. **Le tracé est donc dessiné à la main, approximatif, et assumé comme tel** : trois versions regardées à l'écran, et je me suis arrêté — auteurer une illustration de marque appartient à `DEP-006`. **Ce qui est livré est ce que le critère demande** : l'emplacement, sa place **après la liste dans le DOM**, et son caractère **décoratif** — `aria-hidden`, `focusable="false"`, aucun élément interactif, ni `role="img"` ni `<title>`. Le prototype invitait à l'enfreindre. **Deux défauts de mes propres contrôles** : le marqueur de la carte ne voyait plus rien après extraction du composant, et **deux motifs se déclenchaient sur leurs propres commentaires** — `verifier-ecrans.py` avait déjà résolu cela, §7.34 pour la troisième fois. **Et un défaut de cascade que seule la mesure pouvait attraper** : ma règle de `T3` `.app-principal svg` l'emportait, la carte mesurait **1 152 px** au lieu de 352. **683 tests** et **196 Vitest**, `cadre-check` passe de 19 à **20 contrôles**, témoin sur **neuf** motifs. Compte rendu : [`compte-rendu-t7-lot-4.md`](compte-rendu-t7-lot-4.md) | `US001` | ☑ |
| ~~**`T8`**~~ | ~~**Le changement d'entité, de bout en bout.**~~ **TERMINÉE le 24/08/2026.** `DEC-552`. **LA RÈGLE N'A PAS ÉTÉ INVENTÉE : LA MATRICE §5.1 LA DONNE ENTIÈRE** — « hors de son entité principale, une personne possède **uniquement** les droits `EMP` », et le super-administrateur est « la seule exception globale ». Le cahier §23.3 et la matrice §23.3 posent cinq règles ; la §5.1 dit ce que **deviennent** les permissions, et c'est la section dédiée que le §7.29 apprend à chercher. **Les deux premières règles sont des interdictions d'écriture, et un `GET` les tient par construction** : depuis `DEC-545` le changement d'entité est une **navigation**. On ne les croit pas pour autant — les **quatre** tables de rattachement sont relevées par empreinte avant/après, et l'empreinte porte **son propre témoin**. **Le décor discrimine les quatre règles en DEUX appels**, et le droit local de l'autre entité **existe vraiment en base** : sans lui, son absence dans la réponse serait indistinguable d'une absence de donnée. **Quatre défauts, dont trois dans mes propres contrôles.** `make permissions-check` exigeait plus que le critère sur le 404 — l'identifiant de corrélation est engendré par requête, §7.20 ; **mon contrôle d'ordre ne discriminait pas**, et la conclusion a porté sur le **code** — l'ordre vient désormais de l'énumération ; mon témoin de latence **démontait l'arbre**, donc n'exerçait rien (§7.25) ; et **un vrai défaut vu au navigateur** — les droits arrivés **avant** l'entité étaient perdus, l'API rendait `est_entite_principale: false` et la mention du §5.1 n'apparaissait pas. Corrigé en deux essais, chacun attrapé par le témoin de latence. **697 tests** et **207 Vitest**, `cadre-check` passe de 20 à **21 contrôles**, témoin sur **onze** motifs, et `make permissions-check` en apporte **quinze**. Compte rendu : [`compte-rendu-t8-lot-4.md`](compte-rendu-t8-lot-4.md) | `US002` | ☑ |
| ~~**`T9`**~~ | ~~**L'affichage conditionnel, et le témoin qui compte.**~~ **TERMINÉE le 24/08/2026.** `DEC-553`, `ECART-046`. **LE §8.2 NE DIT PAS QUELLES PERMISSIONS, ET LE §20 DE LA MATRICE LE DIT** : son tableau donne une colonne à **trois** rôles — `ESM`, `ADM-E`, `SUPER`. **`ESM` est celui qu'on perdrait** : l'intuition dit « administrateur d'entité et super-administrateur », et le §20 lui donne **quatre actions d'attribution que `ADM-E` n'a pas**. **La liste vit dans le MANIFESTE du contrat**, lu par TypeScript et par Python — parce que ma première version l'écrivait **deux fois**, deux dérivations du même §20 sans rien pour les confronter (§7.27). **Le prédicat de visibilité aussi était DUPLIQUÉ** depuis `T4`, dans le menu **et** dans la barre : un seul exemplaire désormais, et `cadre-check` l'exige. **« Mon onboarding » est masqué pour tout le monde**, sa condition étant trivialement fausse — aucune table de parcours n'existe — et un test l'épingle pour que le LOT 7 doive le changer délibérément. **Le garde-fou d'API refuse 403**, après **six** des huit vérifications du §2.6, les deux autres étant nommées comme hors de portée de ce lot. **Le 403 est choisi contre le 404**, qui dirait faux. **Et le résiduel est nommé, pas tu** : le lot n'a **aucune route métier à refuser** — ses trois routes sont ouvertes aux huit rôles par la matrice §5 — donc le garde-fou est prouvé par **12 tests** sur une application jetable, comme `exiger_un_scope` au LOT 3, et **pas à travers Caddy**. Arbitrage de Jonathan. **709 tests** et **220 Vitest**, `cadre-check` passe de 21 à **23 contrôles**, témoin sur **treize** motifs. Compte rendu : [`compte-rendu-t9-lot-4.md`](compte-rendu-t9-lot-4.md) | `US005` | ☑ |
| ~~**`T10`**~~ | ~~**Les états d'erreur et la perte de connexion.**~~ **TERMINÉE le 24/08/2026.** `DEC-554`. **LE CRITÈRE NOMMAIT UN PIÈGE, ET LE §17.2 LE RÉSOUT** : « aucune action n'est déclarée enregistrée **sans confirmation de l'API** ». Le lot est en lecture seule, mais les **écritures du LOT 3** existent, et c'est sur elles que la règle porte. **Elle est rendue MÉCANIQUE plutôt que testée** : `cadre-check` confronte les états qui rendent `data-ton='succes'` aux états affectés dans un `catch`, et exige l'intersection vide — exact, pas heuristique, et éprouvé en injectant le défaut réel. **Trois états distincts là où il y en avait un** : hors connexion, **session expirée** et erreur. **Le 401 a été vu au NAVIGATEUR** : le cadre disait « L'entité n'a pas pu être chargée », alors que l'utilisateur était simplement déconnecté — même classe que `T8-4`. **Le réessai est un bouton qui réessaie**, là où le portail écrivait « puis réessayez » sans rien pour le faire. **Et le §17.4 dit « copiable », la fiche disait « affiché »** : le cahier prévaut, le client du portail capture désormais l'en-tête, et l'échec de copie est **dit**. **Aucune branche 403 n'est ajoutée** : mesuré sur le contrat, aucune des trois routes du portail ne le déclare. **709 tests** — inchangés, `T10` est frontend seul — et **228 Vitest**, `cadre-check` passe de 23 à **24 contrôles**, témoin sur **quatorze** motifs. Compte rendu : [`compte-rendu-t10-lot-4.md`](compte-rendu-t10-lot-4.md) | `US006` | ☑ |
| **`T11`** | **Les composants du design system que ces écrans emploient.** Consolidés et documentés, non inventés d'avance. | `US007` (`P1`) | Chaque composant livré est **employé** par un écran de ce lot · contraste mesuré · `jsx-a11y` sans exception |
| **`T12`** | **Recette, reclassements du §30 et checklist `G4`.** | — | Les **six** critères de sortie prouvés · les contrôles du §30 qui deviennent acquis le sont **avec un test nommé** |

**Douze sous-étapes, comme les LOTS 2 et 3.** Une pull request par sous-étape, un compte rendu, et
les registres tenus **dans la même pull request** que le travail.

> **`T11` arrive après les écrans qui emploient ses composants, et c'est délibéré.** `T10` du LOT 1 a
> établi le principe : livrer un menu déroulant sans écran qui l'emploie serait du code non éprouvé.
> Les composants sont **consolidés** à partir de ce que `T3` à `T10` ont réellement eu besoin.

---

# 4. Ce que ce lot NE fera PAS

**Au-delà de son périmètre :** aucune écriture métier — le lot est en **lecture seule** · aucun contenu
d'accueil d'entité, dont les cinq sections du §8.4 appartiennent aux LOTS 5, 6 et 7 · aucun
trombinoscope (LOT 5) · aucun cercle ni bureau (LOT 6) · aucun événement (LOT 7) · aucun écran
d'administration — seule sa **visibilité conditionnelle** est ici · aucun import (LOT 9).

**`axe` et Playwright**, nommés au §17.1, appartiennent au **LOT 12**. Ce lot mesure l'accessibilité
par `jsx-a11y`, par le contraste calculé, et par des parcours de tabulation **écrits à la main**.

**Les interdits absolus, qui ne dépendent d'aucun lot :** aucun contournement de l'authentification ·
aucun jeton dans `localStorage` · aucune donnée réelle de collaborateur · aucune modification d'une
migration appliquée ni des cinq documents de cadrage · aucune exposition de service hors `127.0.0.1` ·
aucune référence d'image par `latest` seul · aucune ligne du prototype historique.

---

# 5. Ce qui est livré et attend son premier consommateur

Trois choses du LOT 3 n'ont **aucun consommateur** aujourd'hui, et ce lot les fournira :

| Livré | Où | Ce que le LOT 4 en fait |
|---|---|---|
| la **dépendance de scope** | `app/auth/dependances.py`, `exiger_un_scope` | rien, sauf si une route de ce lot doit être appelée par un script — improbable |
| la **protection CSRF sur les routes métier** | `app/auth/routes.py`, `_proteger_du_csrf` | rien : le lot est en **lecture seule**, et le CSRF protège les écritures |
| le **rafraîchissement de session** | `GET …/auth/session` | **c'est ici que le résiduel doit être réexaminé** : cette route écrit sans exiger de jeton, et `T3` la mettra sur le chemin de chaque page |

> **Le troisième point est le seul qui demande une décision**, et il est nommé dans `DEC-531` :
> « à réexaminer au LOT 4 ». À instruire en `T2` ou `T3`, pas plus tard.

---

# 6. Les risques propres à ce lot

| Risque | Pourquoi il est réel ici | Parade proposée |
|---|---|---|
| **les route guards deviennent une sécurité** | c'est la confusion que la roadmap interdit en une phrase, et elle est facile à commettre : masquer un menu *ressemble* à protéger | `T9` exige **les deux mesures** : le menu masqué **et** l'appel direct refusé. Une seule ne prouve rien |
| **le responsive est affirmé, non mesuré** | « ça a l'air bien à 320 px » n'est pas une mesure. `LARGEURS_RECETTE` existe depuis un lot et **n'a jamais servi** | mesurer le **débordement horizontal** aux cinq largeurs, et échouer sinon — c'est le §7.16 : ce qui n'a jamais tourné n'est pas éprouvé |
| **la carte devient le seul chemin** | une carte cliquable est séduisante et **inaccessible** si rien ne la double | le §8.3 met la liste **en premier** sur mobile ; `T6` livre la liste **avant** `T7` ne livre la carte |
| **le clavier est oublié** | `jsx-a11y` vérifie le JSX, **pas** un parcours de tabulation | un parcours écrit à la main en `T4`, avec les pièges de focus nommés |
| **« sauvegardé » affiché à tort** | un `fetch` qui échoue après l'envoi est le cas que personne ne teste | `T10` l'éprouve **explicitement**, avec un `fetch` qui rejette après émission |

---

# 7. Deux leçons du LOT 3 qui s'appliquent directement

**La réponse générique ne doit pas être défaite par l'interface.** `T11` du LOT 3 l'a prouvé pour la
connexion ; le même raisonnement vaut ici : un écran qui distinguerait « entité inexistante » de
« entité à laquelle vous n'avez pas accès » serait un **oracle d'existence**, ce que le §2.5 interdit.
`T1` doit donc rendre la **même** réponse dans les deux cas.

**Un contrôle qui compte doit dire combien il a examiné.** Les cinq largeurs, les six rubriques, les
pages internes : chaque compte doit être **dérivé** de sa source — le cahier, le routeur — jamais
recopié. Le §7.27 a été payé six fois au LOT 3.

---

# 8. Ce que le corpus NE tranche PAS — **AUCUN point ne reste**

> **CE §8 S'EST TROMPÉ, ET IL FAUT LE LIRE EN LE SACHANT.** Il annonçait **deux** points ouverts. Le
> second — « où vit l'entité consultée » — **était tranché par le cahier**, et `T2` l'a établi le
> 23/08/2026 : le §4.1, le §8.1, le §9.1 et le §9.2 font **tous** atterrir sur la page nationale après
> connexion, si bien qu'une mémoire serveur du dernier choix n'aurait **aucun consommateur**. Le
> cahier a en outre une section entière, **§23.3 « Changement d'entité »**, avec **cinq** règles que ce
> §8 ne citait pas. `ECART-040`, `DEC-545`.
>
> **Le §8 de la fiche du LOT 3 s'était trompé trois fois sur quatre. Celui-ci une fois sur deux.**
> La leçon §7.29 est donc à appliquer au point qui reste : *cherche la décision dans le cahier avant
> de la prendre — et cherche-la par ses SYNONYMES, pas par le mot que la fiche emploie.* Ici,
> « mémorisé » ne donnait rien ; ce sont « changement d'entité » et le diagramme du §8.1 qui ont
> tranché.

| Point | Ce que le corpus dit exactement | Quand l'instruire |
|---|---|---|
| **La carte de France : format et coordonnées** | Le corpus la nomme **trois fois** et n'en dit qu'un mot : « **illustrative** ». Aucun format, aucune source de données. Et `entity` porte `city` et `country_code` mais **ni latitude ni longitude** — mesuré sur le schéma réel. Il faudra donc soit poser des positions, soit ne pas en poser | **`T7`.** Trois options se dessinent, et aucune n'est évidente : une carte **décorative** sans marqueurs, des positions **portées par le code** pour les villes connues, ou une colonne au modèle — qui serait une modification du schéma, donc à instruire |
| ~~**Où vit l'entité consultée**~~ | **CE POINT N'ÉTAIT PAS OUVERT.** `ECART-040` : le cahier détermine le parcours en quatre endroits, et l'entité vit donc dans l'**adresse** — aucune colonne, aucun stockage, aucune migration | **CLOS en `T2`**, `DEC-545` |

**Le point qui reste ne bloque rien avant `T7`**, et le §23.3 du cahier — cinq règles sur le changement d'entité — est désormais cité au compte rendu de `T2`. Ses trois autres règles sont exigibles en `T3`, `T8` et `T9`.

> **MISE À JOUR DU 24/08/2026, À LA SORTIE DE `T8` : LES CINQ RÈGLES SONT TENUES, ET PROUVÉES.** La quatrième — « annule les requêtes et caches » — l'était depuis `T2` ; la cinquième — « visible dans l'en-tête » — depuis `T3` ; les deux premières le sont **par construction**, le changement étant une navigation, et `make permissions-check` compare les quatre tables de rattachement avant/après pour l'exiger ; la troisième — « recharge les permissions » — a désormais son porteur. **Et ce que la fiche ne disait pas : la matrice §5.1 détermine entièrement CE QUE deviennent les permissions.** Aucune décision n'était à prendre.

---

# 9. Traçabilité GitHub

À créer **après validation du découpage** : un epic `MVP-L04`, sept issues pour les sept stories, et
le jalon `G4` — qui existe déjà, vide.

**Et la routine qui ne change pas :** une pull request par sous-étape, `Closes #N` **ne fonctionne pas
depuis `develop`** (§7.19), donc chaque issue est refermée **à la main** avec ses critères cochés et
leurs preuves.
