# Fiche de lot — LOT 4

**Portail national, sélection d'entité et navigation**
**Porte de validation :** `G4`, tag `v0.4.0` prévu
**Ouvert par Jonathan le :** 22 août 2026 — décision `DEC-541`
**Rédigée le :** 22 août 2026, au franchissement de la porte `G3`
**Statut de cette fiche :** **découpage VALIDÉ par Jonathan le 22/08/2026** — « parfait »
**Avancement :** **`T1` et `T2` terminées** le 23/08/2026. Dix sous-étapes restantes

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
| **`T3`** | **Le cadre applicatif et les cinq largeurs.** Layouts mobile, tablette, bureau, et l'entité active **visible partout**. | `US004` | Aucun débordement horizontal à **320, 390, 768, 1 280, 1 920** px, mesuré · la liste des pages est **dérivée du routeur** |
| **`T4`** | **La navigation principale, au clavier.** Les six rubriques du §8.2, dont deux conditionnelles. | `US004` | **Toutes** les actions atteignables au clavier · aucun piège de focus · l'ordre de tabulation suit l'ordre visuel |
| **`T5`** | **La barre inférieure mobile**, et l'accès « Plus » du §8.2. | `US003` | Utilisable à **320 et 390** px · focus et libellés corrects · les rubriques principales restent atteignables |
| **`T6`** | **La page nationale : la liste accessible.** Et le critère qui commande sa structure. | `US001` | **La liste précède la carte dans le DOM**, pas seulement à l'œil · navigable au clavier · seules les entités actives |
| **`T7`** | **La carte de France illustrative.** Voir §8 — ni format ni coordonnées ne sont donnés. | `US001` | La carte est **décorative** au sens de l'accessibilité : elle n'est pas le seul moyen d'atteindre une entité |
| **`T8`** | **Le changement d'entité, de bout en bout.** | `US002` | L'entité active reste visible · les données rechargées sont **celles de la nouvelle entité** · aucun reste de la précédente |
| **`T9`** | **L'affichage conditionnel, et le témoin qui compte.** Les menus masquent ; l'API refuse. | `US005` | Un menu masqué **et** un appel direct à la route **refusé par l'API** — les deux, sinon le lot n'a rien prouvé |
| **`T10`** | **Les états d'erreur et la perte de connexion.** | `US006` | Un `fetch` qui échoue **après l'envoi** n'affiche **jamais** « sauvegardé » · `403`, `404`, `500` · l'identifiant de corrélation est affiché |
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

# 8. Ce que le corpus NE tranche PAS — UN point, l'autre était tranché

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

---

# 9. Traçabilité GitHub

À créer **après validation du découpage** : un epic `MVP-L04`, sept issues pour les sept stories, et
le jalon `G4` — qui existe déjà, vide.

**Et la routine qui ne change pas :** une pull request par sous-étape, `Closes #N` **ne fonctionne pas
depuis `develop`** (§7.19), donc chaque issue est refermée **à la main** avec ses critères cochés et
leurs preuves.
