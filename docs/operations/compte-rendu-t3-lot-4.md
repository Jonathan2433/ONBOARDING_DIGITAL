# Compte rendu — LOT 4, sous-étape `T3`

**Le cadre applicatif et les cinq largeurs — et deux défauts qui vivaient depuis un mois**
**Story :** `MVP-L04-US004` (partiellement — `T4` la complète)
**Réalisée le :** 23 août 2026
**Décision produite :** `DEC-546` · **Écarts consignés :** `ECART-041`, `ECART-042`
**Migration produite :** **aucune**

---

## 1. Ce que la sous-étape devait faire, et ce qui l'a bloquée d'abord

Le critère : « Le cadre applicatif et les cinq largeurs. Layouts mobile, tablette, bureau, et
l'entité active visible partout » · « Aucun débordement horizontal à **320, 390, 768, 1 280,
1 920** px, **mesuré** · la liste des pages est **dérivée du routeur** ».

Le mot qui commande est **« mesuré »**. Et mesurer a exigé de découvrir, puis de réparer, deux
défauts antérieurs.

---

## 2. `ECART-042` — le frontend servi était celui du LOT 1

En cherchant où le cadre devait puiser ses jetons, j'ai regardé ce que le navigateur charge
réellement. **Une seule feuille, 28 règles** : `styles.css`, celle de la page de statut. Ni
`auth.css`, ni `jetons.css`.

Le conteneur, mesuré :

```
fichiers de frontend dans le conteneur : 9
fichiers de frontend dans le depot     : 24
```

Son `App.tsx` était celui du LOT 1. **Ni les huit écrans de `T11`, ni la page d'entité de `T2`.**
Aucun montage lié, donc aucun rattrapage à chaud.

**Cause :** `make code-refresh` reconstruisait **`api` et `worker`**, pas `web`. Le conteneur `web`
n'est rafraîchi que par `make up`, et la routine de sous-étape emploie `code-refresh`.

> **Et `make ecrans-check` passait.** Il exige que les huit chemins rendent `text/html` contenant
> `id="racine"` — or le repli SPA `try_files {path} /index.html` sert exactement cela pour
> **n'importe quel** chemin. **L'échec produisait la même observation que le succès** : §7.0,
> quatrième proposition.

Les deux défauts se couvraient l'un l'autre — une cible qui laissait le conteneur en arrière, un
contrôle qui disait que tout allait bien. `code-refresh` reconstruit désormais `web`.

**Un défaut de ma part dans la découverte, et il faut le dire :** j'ai écrit un `echo` contenant des
backticks non échappés, et le shell a exécuté `make up`. Inoffensif — la cible est idempotente et
fait partie de la routine — mais c'est la classe §7.2, et c'est ce `make up` accidentel qui a
rafraîchi le conteneur avant que je n'aie décidé de le faire.

---

## 3. `ECART-041` — les feuilles du design system n'étaient importées par personne

Le conteneur à jour, la mesure a montré un second défaut, **plus ancien**.

`T10` du LOT 1 a livré `jetons.css` — 34 propriétés, couples fond/texte recalculés contre WCAG 2.2
AA — et `composants.css`. `T11` du LOT 3 a écrit `auth.css` **entièrement en `var(--…)`** et employé
le composant `Bouton` dans **trois** écrans.

**Rien n'importait ces deux feuilles.**

| Mesure sur l'application servie | Avant | Après |
|---|---|---|
| `--marque-bleu` | *chaîne vide* | `#5853ff` |
| `--espace-m` | *chaîne vide* | `16px` |
| `--rayon-m` | *chaîne vide* | `12px` |
| `--police` | *chaîne vide* | `system-ui, -apple-system, …` |
| bouton « Recevoir un lien », fond | `rgba(19, 1, 1, 0.3)` | `rgb(88, 83, 255)` |
| bouton, rayon | `0px` | `12px` |

Sur les **21** propriétés qu'emploie `auth.css`, **14 ne résolvaient rien**. Les 7 autres résolvaient
**par accident** : `styles.css`, posée en `T5` du LOT 1 **avant** les jetons, définit les mêmes noms —
et leurs valeurs sont **identiques**, mesuré, donc la collision est bénigne.

> **Les huit écrans d'authentification du LOT 3 n'ont jamais porté le design system.** Leurs
> espacements, leurs rayons et leur typographie étaient ceux du navigateur, et leurs trois boutons
> étaient des boutons nus.

**Et `packages/ui/src/index.ts` écrivait les deux lignes d'import à poser**, en toutes lettres. Le
paquet documentait son emploi ; l'application ne l'a pas suivi, et aucun contrôle ne regardait.

**Cause :** `ecrans-check` exigeait qu'aucune couleur **littérale** ne soit écrite dans `auth.css` —
la **source** — jamais que les jetons **résolvent**. Le succès d'un contrôle et la justesse d'une page
sont deux grandeurs différentes (§7.24). Il était exact sur ce qu'il regardait ; il ne regardait pas
la bonne chose. **Et il n'examinait qu'un chemin écrit en dur**, soit une liste recopiée de un
élément — §7.27 — si bien qu'une feuille nouvelle lui échappait.

### Une erreur de ma part, que mon propre contrôle a corrigée

J'ai classé `composants.css` **« hors-application »**, en croyant qu'aucun code applicatif n'employait
`Bouton`, `Badge` ou `Carte`. Puis la mesure du bouton a montré `class="ex-bouton"` — une classe que
seule cette feuille définit — et **trois** écrans qui importent `Bouton`.

> **Une classification est une supposition ; une dérivation, non.** Le contrôle exige désormais que la
> feuille des composants soit chargée **dès qu'un module importe quoi que ce soit de
> `@onboarding/ui`**, sans qu'aucune liste n'ait à être tenue à jour. C'est le §7.27 : *si elle décrit
> un état que le code porte déjà, dérive-la.*

---

## 4. `DEC-546` — le cadre, et pourquoi il est une route de mise en page

Le §23.3 exige que l'entité soit « visible dans l'en-tête de l'application », et la roadmap « sur
**toutes** les pages internes ». Deux façons de tenir cela : demander à chaque page de l'afficher, ou
la porter **une fois** dans un cadre que toutes les pages traversent.

`CadreApplicatif` est donc une **route de mise en page** : il résout l'entité, la met dans
`<header>`, porte l'unique `<h1>` et rend ses enfants par `Outlet`. **Toute page ajoutée dessous
hérite de l'en-tête par construction** — et `T4` posera ses six rubriques là, sans rien à oublier.

**Ce qu'il ne porte pas, et ce n'est pas un oubli :** aucun `<nav>`, aucune barre inférieure. La
navigation est `T4`, la barre mobile `T5`. Poser un `<nav>` vide serait un **repère de page sans
contenu** : un lecteur d'écran l'annoncerait et n'y trouverait rien, ce qui est pire que son absence.

### Le titre : deux mécanismes essayés, et le premier est mesuré comme impossible ici

**Mesure à l'écran : le nom de l'entité apparaissait DEUX fois**, dans l'en-tête et en `<h1>`.

La façon idiomatique est `handle` sur la route, lu par `useMatches`. Elle a échoué :

```
Error: useMatches must be used within a data router.
```

`App.tsx` emploie le routeur **déclaratif**, `<BrowserRouter>` et `<Routes>`, choisi en `T11` pour que
les liens de magic link soient de vraies URL. Migrer l'architecture de routage pour un titre serait
disproportionné — et bâtir un mécanisme de titres **sans les rubriques qui le motivent** serait livrer
sans consommateur, ce que `T10` du LOT 1 et `T11` de ce lot refusent tous deux.

> Le `<h1>` porte donc **« Accueil de l'entité »**, le libellé du **§8.1** dont le diagramme nomme ce
> nœud. Une constante, pas un mécanisme. **`T4` tranchera avec ses six rubriques en main**, et il a le
> choix mesuré : migrer vers `createBrowserRouter`, ou dériver le titre du chemin par `useLocation`.

**Et deux règles de React ont eu raison contre moi, deux fois de suite.** `react-hooks/rules-of-hooks`
a refusé mon hook parce qu'il ne s'appelait pas `useX`, puis parce qu'il était appelé **après un
retour anticipé**. Les deux fois la règle disait vrai, et la parade n'était pas de la désactiver.

---

## 5. Les trois layouts, et le « et plus » que la fiche ne nomme pas

Le §13.4 impose de recetter **cinq** largeurs. Ce ne sont pas des points de rupture : c'est une liste
de recette. Les deux points retenus — **768** et **1 280** — séparent les trois layouts que la roadmap
nomme, et **tombent sur deux valeurs de cette liste** pour que la recette mesure exactement les
frontières. `cadre-check` relit `LARGEURS_RECETTE` dans `jetons.ts` et **exige** cette appartenance.

**Le cahier écrit « 1 920 px ET PLUS ».** La cinquième largeur est un **plancher**, pas un point, et le
critère de la fiche ne le dit pas. La mesure porte donc sur **six** largeurs.

### La mesure, dans un vrai navigateur, sur une entité au nom de 67 caractères

Décor : une entité nommée « eXalt Bordeaux Nouvelle-Aquitaine Métropole Développement Numérique »,
ville « Bordeaux-Mérignac-Pessac-Talence » — le cas de débordement le plus probable — consultée avec
une session réelle ouverte par une connexion administrateur à travers Caddy en HTTPS.

| Largeur | `clientWidth` | `scrollWidth` | Débordement | Éléments hors viewport | Layout |
|---:|---:|---:|---|---:|---|
| **320** | 320 | 320 | **non** | 0 | mobile |
| **390** | 390 | 390 | **non** | 0 | mobile, en-tête en colonne |
| **768** | 768 | 768 | **non** | 0 | tablette, en-tête en ligne |
| **1 280** | 1 280 | 1 280 | **non** | 0 | bureau, contenu 1 200 px |
| **1 920** | 1 920 | 1 920 | **non** | 0 | bureau, contenu 1 200 px centré |
| **2 560** | 2 560 | 2 560 | **non** | 0 | bureau, contenu 1 200 px centré |

La colonne « éléments hors viewport » n'est pas décorative : le contrôle énumère **tous** les
éléments dont le bord droit dépasse, et les nomme. Un `scrollWidth` égal au viewport avec un élément
en débordement caché serait indistinguable d'un vrai succès sans cette seconde mesure.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `make check` | **code 0** — **683** pytest, **158** Vitest (90 `ui`, **51 `web`**, 17 `contracts`) |
| `make cadre-check` | **code 0** — **9 contrôles**, statique, **dans `make check` et dans la CI** |
| `make cadre-temoin` | **code 0** — il échoue en nommant **les trois** motifs attendus |
| `make entites-check` | **code 0** — 13 contrôles |
| `make residu-check` | **code 0** — 23 tables, 0 ligne avant |
| `make ecrans-check` | **code 0** — et il annonce le chemin paramétré qu'il écarte |
| `api-check` `web-check` `sessions-check` `csrf-check` `evenements-check` | **code 0** pour les cinq |
| `docs-check` `audit` `icloud-verify` | **code 0** pour les trois |

**Les neuf contrôles de `cadre-check`** : les feuilles sont classées · toute `var()` d'une feuille
chargée est définie par une feuille chargée · toute feuille consommatrice est chargée · aucune largeur
fixe en pixels · les points de rupture sont dans les largeurs recettées · les transitions sont
neutralisées sous `prefers-reduced-motion` · aucun chargement paresseux, donc le graphe d'imports est
complet · les routes internes sont dérivées de `App.tsx` · la feuille des composants est chargée dès
qu'un module en importe un.

**Et il dit ce qu'il ne mesure pas** : le débordement réel exige un moteur de rendu ; le §17.1 nomme
Playwright et **le LOT 12 le possède**. L'anticiper serait faire le travail d'un lot postérieur.

---

## 7. Ce qui n'est PAS couvert

| Non couvert | Pourquoi, et quand |
|---|---|
| **la navigation principale** | `T4`. Aucun `<nav>` ici : un repère vide est pire que son absence |
| **la barre inférieure mobile** | `T5`, même raison |
| **le mécanisme de titre par page** | `T4`, avec ses six rubriques en main. Le choix est mesuré : `createBrowserRouter` ou `useLocation` |
| **la mesure automatisée du débordement** | **LOT 12** — le §17.1 nomme Playwright, et le LOT 12 le possède |
| **les tests `axe`** | **LOT 12** — `MVP-L12-US003` les nomme explicitement |
| **`ecrans-check` vérifiant que les écrans EXISTENT** | nommé et **reporté** dans `ECART-042`. La piste — exiger un type MIME JavaScript sur le module d'un écran — ne vaudrait que pour la cible `developpement`, et le §7.21 avertit contre un contrôle qui ne connaîtrait qu'un environnement |
| **`Radix UI`** | le §13.3 le nomme « notamment ». Aucun composant de ce cadre n'en a besoin ; `T4` en aura peut-être l'usage pour un menu |

---

## 8. Ce que `T4` devra savoir

1. **ses six rubriques se posent en enfants de la route de mise en page**, et elles hériteront de
   l'en-tête sans rien faire. `cadre-check` compte ces routes et le compte augmentera ;
2. **le mécanisme de titre reste à choisir**, et les deux options sont mesurées — `useMatches` exige
   un data router, `useLocation` non ;
3. **une contrainte à ne pas perdre**, trouvée dans le cahier §2.5 de la matrice et à la ligne 2135
   du cahier : « les contrôles côté API utilisent **l'entité de la ressource**, et non uniquement
   l'entité sélectionnée dans le frontend ». C'est pour `T9` et pour le LOT 5 : ne bâtis pas
   l'autorisation sur l'entité de l'adresse ;
4. **`make code-refresh` reconstruit désormais `web`.** Avant de conclure quoi que ce soit d'une
   mesure sur l'application servie, lance-le — et souviens-toi que `code-check` ne vérifie que l'API ;
5. **le §23.3 a cinq règles, et trois restent** : « recharge les permissions » (`T9`), « ne transfère
   pas ses responsabilités » (`T9`), « ne modifie pas l'entité principale » (LOT 5).
