# Compte rendu — LOT 4, sous-étape `T4`

**La navigation principale, au clavier — et un lien d'évitement qui ne sautait rien**
**Story :** `MVP-L04-US004` · **Réalisée le :** 23 août 2026
**Décision produite :** `DEC-547` · **Écarts consignés :** `ECART-043`, `ECART-044`
**Migration produite :** **aucune**

---

## 1. Ce que le corpus tranche, et ce qu'il ne tranche pas

| Question | Ce que le corpus dit |
|---|---|
| **quelles rubriques ?** | le **§8.2** en donne six, mot pour mot, dont deux avec leur condition |
| **qui voit l'Administration ?** | la **matrice §5**, ligne « Administration » : `—` pour `ANON`, `EMP` et `NEW` ; un périmètre pour `DSM`, `ESM`, `BOOST`, `OFFICE`, `ADM-E` et `SUPER` |
| **quelles URL ?** | **rien.** Le §8.1 donne l'arbre, le §8.2 les libellés, aucun ne donne d'adresse. Les suffixes sont dérivés des libellés, sans accent ni espace — la convention que `/connexion/lien-envoye` applique déjà |
| **le clavier ?** | le **§14.2** : « navigation intégrale au clavier », « focus visible », « ordre de tabulation cohérent ». Le « piège de focus » est le mot de la fiche, non du cahier |

**Et deux conditions ne sont pas calculables à `T4`** — mesuré, pas supposé :

- « **Mon onboarding**, uniquement lorsqu'un parcours actif existe » : **aucune table de parcours n'existe**, sur les 26 tables réelles du schéma. C'est le LOT 7 ;
- « **Administration**, uniquement selon les permissions » : la matrice tranche *qui*, mais **aucune route ne rend les rôles de l'appelant**. C'est `T9`.

> **Les deux rubriques sont donc ABSENTES par défaut**, ce qui est le « refus par défaut » du §20.1 :
> une rubrique montrée à tort suggère un droit qu'on n'a pas. Les tests éprouvent **les deux** états,
> et **séparément** — les deux conditions sont indépendantes, et un test qui les activerait ensemble
> ne le prouverait pas.

---

## 2. `DEC-547` — une source, trois consommateurs

`RUBRIQUES`, dans `routes.ts`, porte les six entrées. **Le menu s'en rend, les six routes en sont
engendrées par `.map()`, et le `<h1>` s'en dérive.** Trois copies auraient divergé — `DEC-466`.

`make cadre-check` **exige** que `App.tsx` itère `RUBRIQUES` : une liste littérale de routes ferait
échouer le contrôle. Et les six `libelleCorpus` sont confrontés au cahier §8.2 **mot pour mot**.

### Le clavier : ne rien ajouter plutôt que tout gérer

> La façon de tenir « toutes les actions atteignables au clavier · aucun piège de focus » n'est pas
> d'ajouter des gestionnaires de touches. **C'est de n'employer que des éléments nativement
> focusables.**

Six `<Link>`, donc six `<a href>`. Le navigateur les met dans l'ordre du DOM, qui est l'ordre visuel,
et **aucun code ne touche au focus** — donc aucun piège n'est possible. C'est le §7.2 : changer de
forme plutôt que promettre de l'attention. Un menu bâti sur des `<div onClick>` aurait exigé
`tabindex`, des gestionnaires de flèches, et un piège à éviter.

Le contrôle **interdit tout `tabIndex` positif**. Sans `tabindex` positif, l'ordre de focus séquentiel
**est** l'ordre du document — c'est la spécification HTML — donc asserter l'ordre du DOM asserte
l'ordre de tabulation.

### `aria-current`, et pourquoi c'est le sélecteur CSS

Le §14.2 interdit qu'une information soit « portée uniquement par la couleur ». La feuille sélectionne
sur `aria-current`, posé par `NavLink` : **l'état annoncé et l'état visuel viennent de la même source
et ne peuvent pas diverger.** Un trait sous la rubrique double la couleur.

**Le piège de `end`** : le chemin de l'accueil est un **préfixe** de tous les autres. Sans `end`, deux
rubriques porteraient `aria-current` sur `/entites/x/framework`, et un lecteur d'écran annoncerait
deux pages courantes. Un test l'exige.

### Le titre : la seconde option, celle que `T3` avait mesurée

`T3` posait une constante faute de rubriques à distinguer, et avait mesuré que `handle` + `useMatches`
**exige un data router**. `T4` retient `useLocation`, et le motif n'est pas seulement qu'il n'a pas
cette contrainte : **il n'ajoute aucune source de vérité.** Le titre vient de `RUBRIQUES`, d'où le
menu se rend déjà. Migrer vers `createBrowserRouter` aurait permis `handle` au prix de **dupliquer le
libellé** entre la route et le menu.

**La comparaison porte sur le chemin complet, non sur une inclusion de chaîne** :
`/entites/framework-sud` contient « framework » sans être la rubrique Framework.

### Cinq pages qui disent quel lot les remplira

Un lien de menu qui aboutit au fourre-tout `404` est atteignable et **inutile** : la navigation serait
simulée, non prouvée. Ces pages ne portent aucun contenu métier — le §8.4 le donne, et il appartient
aux LOTS 5 à 9 — elles disent **quel lot** l'apportera.

---

## 3. `ECART-043` — le lien d'évitement ne sautait rien, et c'était mon test qui le cachait

Mesure dans un vrai navigateur, en activant le lien posé en `T3` :

| | Avant | Après |
|---|---|---|
| hash | `#contenu` | `#contenu` |
| `<main>` `tabindex` | **absent** | `-1` |
| focus après activation | **`<body>`** | **`main#contenu`** |

Le Tab suivant repartait donc du **début** du document, à travers le menu qu'on venait de sauter.

> **Mon test de `T3` vérifiait que le `href` vaut `#contenu` et que le `<main>` porte cet `id`.** Les
> deux étaient vrais, et le mécanisme ne fonctionnait pas. **Le succès du test et la justesse du
> livrable étaient deux grandeurs différentes** — §7.0, quatrième proposition — et c'est la forme la
> plus insidieuse, parce qu'on croit avoir prouvé.
>
> Ce que le test ne regardait pas : **le focus se déplace-t-il ?** C'est la seule question qui compte
> pour un lien d'évitement.

`-1` et non `0` : focusable **par programme**, hors de l'ordre de tabulation. Un `0` ajouterait un
arrêt sur le contenu entier. Un lien d'évitement qui ne saute rien est **pire** que pas de lien : il
apprend à ne pas s'en servir, ce qui est le §7.21 dans un autre costume.

## 4. `ECART-044` — une correction appliquée à une instance, pas à sa classe

`verifier-ecrans.py` lisait les `libelleCorpus` de **tout** `routes.ts`. `RUBRIQUES` en ajoute six, et
le contrôle en a compté **14** au lieu de 8, cherchant « Framework » dans la liste des huit écrans du
§17.5.

> **Et la même correction avait déjà été faite, une fonction plus bas.** Le docstring de
> `chemins_declares` le raconte : « UNE PREMIÈRE VERSION LISAIT TROP LARGE… L'extraction est donc
> **bornée au bloc `CHEMINS`** ». **§7.34, littéralement** : une instance corrigée n'est pas la classe
> corrigée.

`verifier-cadre.py` ne refait pas l'erreur : son `lire_rubriques` est bornée **dès sa première
écriture**, et son docstring dit pourquoi.

---

## 5. Un défaut de mon propre contrôle, et il disait « ok » sur ZÉRO

`cadre-check` comptait les `<Route>` **littéraux** du bloc du cadre. `T4` les engendre depuis
`RUBRIQUES` par `.map()` : le motif ne trouvait plus rien, et le contrôle a annoncé

```
ok       0 route(s) interne(s) sous le cadre
```

**Un compte affiché n'est un contrôle que s'il est confronté à un attendu** — §7.0, troisième
proposition, dans sa forme la plus crue. Il exige désormais que `App.tsx` **itère `RUBRIQUES`**, ce qui
est la propriété qui compte, et non un nombre de lignes.

---

## 6. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| `make check` | **code 0** — **683** pytest, **173** Vitest (90 `ui`, **66 `web`**, 17 `contracts`) |
| `make cadre-check` | **code 0** — **14 contrôles** (9 + 5), statique, dans `make check` et dans la CI |
| `make cadre-temoin` | **code 0** — il échoue en nommant **les cinq** motifs attendus |
| `make ecrans-check` | **code 0** après correction — 8 écrans déclarés, 8 attendus |
| `make entites-check` `residu-check` `evenements-check` | **code 0** pour les trois |
| `docs-check` `audit` `icloud-verify` | **code 0** pour les trois |

### La marche au clavier, mesurée dans un vrai navigateur

Huit `Tab`, huit arrêts enregistrés par un écouteur `focusin` :

| # | Élément | Dans le menu | Contour de focus |
|---:|---|---|---|
| 1 | `Aller au contenu` | non | `solid 2px` |
| 2 | `Accueil` | **oui** | `solid 2px` |
| 3 | `Framework` | **oui** | `solid 2px` |
| 4 | `Trombinoscope` | **oui** | `solid 2px` |
| 5 | `Evenements` | **oui** | `solid 2px` |
| 6 | `Revenir a la liste des entites` | **non** | `solid 2px` |
| 7 | `Aller au contenu` | non | `solid 2px` |
| 8 | `Accueil` | oui | `solid 2px` |

**Ce que cela prouve :** l'ordre suit l'ordre visuel · le focus **sort** du menu au sixième arrêt, donc
**aucun piège** · le cycle reprend au septième, celui du navigateur, intact · **focus visible sur les
huit**, et non sur un échantillon.

**Ce qui n'est PAS mesuré au clavier, et il faut le dire.** Le `Tab` immédiatement après l'activation
du lien d'évitement : le volet du navigateur a cessé de délivrer les événements clavier en cours de
session, et je ne l'ai pas obtenu. Ce qui est établi à sa place : le focus atterrit sur `main#contenu`
— **mesuré** — et l'élément qui suit `main` dans l'ordre du document est le lien du contenu, **pas** une
rubrique — **structurel**. Avec la spécification HTML, qui fait repartir la navigation séquentielle de
l'élément focalisé, la conclusion tient ; mais elle est **déduite**, non mesurée, et le dire vaut mieux
que de laisser croire.

---

## 7. Ce qui n'est PAS couvert

| Non couvert | Pourquoi, et quand |
|---|---|
| **la barre inférieure mobile** et l'accès « Plus » | `T5` |
| **la source des deux conditions** | le parcours actif au LOT 7, les rôles à `T9`. Les propriétés existent, les tests les éprouvent, la source manque |
| **le refus de l'API sur une action non autorisée** | `T9` — et c'est la moitié qui compte : « les menus masquent ; l'API refuse » |
| **le contenu des cinq rubriques** | LOTS 5, 6, 7, 8 et 9, et chaque page le dit |
| **les tests `axe`** | LOT 12, `MVP-L12-US003` |
| **un fil d'Ariane** | le corpus n'en nomme aucun. Ne pas en inventer |

---

## 8. Ce que `T5` devra savoir

1. **le second `<nav>` doit être NOMMÉ.** Celui du menu principal porte
   `aria-label="Menu principal"` précisément parce qu'un second arrive : deux repères de navigation
   sans nom sont indistinguables pour un lecteur d'écran ;
2. **`RUBRIQUES` est la source**, et la barre inférieure doit s'en rendre aussi. Le §8.2 dit « les
   fonctions secondaires sont regroupées dans un accès **“Plus”** lorsque nécessaire » — « lorsque
   nécessaire » est à instruire, pas à supposer ;
3. **le lien d'évitement saute désormais six liens**, et il en sautera plus. Sa cible doit rester
   focusable : `cadre-check` l'exige ;
4. **la cible tactile fait au moins 44 px** — `min-height` sur le lien de menu, recommandation WCAG
   2.2 AA « Target Size (Minimum) », 2.5.8. La barre mobile est le lieu où cela compte le plus.
