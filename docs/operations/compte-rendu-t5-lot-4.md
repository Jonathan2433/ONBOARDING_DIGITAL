# Compte rendu — LOT 4, sous-étape `T5`

**La barre inférieure mobile, et « lorsque nécessaire » rendu mesurable**
**Story :** `MVP-L04-US003` · **Réalisée le :** 23 août 2026
**Décision produite :** `DEC-548` · **Écart consigné :** aucun
**Migration produite :** **aucune**

---

## 1. « Lorsque nécessaire » était à instruire, et c'est une mesure

Le §8.2 dit : « Sur mobile, une barre de navigation inférieure est utilisée. Les fonctions
secondaires sont regroupées dans un accès **“Plus” lorsque nécessaire**. » Et `US003` :
« les **rubriques principales** restent accessibles à 320 et 390 px ; le focus et les libellés sont
**corrects**. »

J'avais écrit au compte rendu de `T4` que « lorsque nécessaire » était **à instruire, pas à
supposer**. La mesure l'a instruit — à `--taille-xs` = 12 px, avec la police réellement servie :

| Libellé | Largeur |
|---|---:|
| Accueil | 44 px |
| Framework | 66 px |
| Evenements | 73 px |
| Administration | 87 px |
| Trombinoscope | **92 px** |
| Mon onboarding | **96 px** |

| Cellules à 320 px | Largeur | Résultat |
|---:|---:|---|
| 3 | 106 px | tout sur une ligne |
| **4** | **80 px** | « Trombinoscope » sur **deux** lignes |
| 6 | 53 px | « Mon onboarding » sur **TROIS** lignes |

> **Quatre cellules tiennent, six non.** La barre porte donc les quatre rubriques
> inconditionnelles, et « Plus » apparaît **dès qu'une conditionnelle existe**.

**Et j'allais poser la question à Jonathan.** Deux lectures étaient possible — « les deux
conditionnelles sont les fonctions secondaires » et « ce qui ne tient pas va sous Plus » — et elles
**coïncident** : les quatre qui tiennent sont exactement les quatre inconditionnelles. La mesure a
rendu la question inutile.

**Les libellés ne sont ni tronqués ni abrégés.** `US003` exige qu'ils soient « corrects » : un
« Trombi… » ne l'est pas, et abréger en « Trombi » serait inventer un libellé que le §8.2 ne donne
pas.

---

## 2. `<details>` plutôt qu'un bouton, et c'est le §7.2

Un `<button aria-expanded>` avec son panneau aurait exigé de gérer l'ouverture, la fermeture par
`Escape`, et le **retour du focus** au bouton — c'est-à-dire exactement le terrain où naissent les
pièges de focus que `T4` a pris soin de rendre **impossibles**.

`<details>`/`<summary>` est nativement focusable, s'ouvre par `Entrée` comme par `Espace`, et **aucun
code ne touche au focus**. `cadre-check` **l'exige** : la barre ne doit contenir ni `.focus()`, ni
`useRef`, ni `addEventListener`.

**Ce que `<details>` ne fait PAS, et il faut le dire** : il ne se ferme pas sur `Escape`. Le panneau
se referme en réactivant son résumé, ou en naviguant. **Ce n'est pas une modale** : rien n'est piégé
derrière, et le reste de la page reste atteignable.

## 3. Les deux repères ne coexistent jamais

Le §8.2 dit « **sur mobile** ». Deux repères de navigation visibles en même temps donneraient deux
fois les mêmes liens dans l'ordre de tabulation, et un lecteur d'écran annoncerait deux navigations
pour une seule page.

Le contrôle le vérifie **dans les deux sens** — menu du haut caché par défaut **et** montré à partir
de 768 px, barre montrée par défaut **et** cachée à partir de 768 px. Un seul des trois suffirait à
laisser les deux visibles quelque part.

**Et la barre vient EN DERNIER dans le DOM**, parce qu'elle est ancrée en bas : la mettre avant le
contenu ferait diverger l'ordre de tabulation de l'ordre visuel, ce que le critère de `T4` interdit.

---

## 4. Les mesures, dans un vrai navigateur

| Largeur | Menu du haut | Barre | Repères visibles | Cibles | Libellé rogné | Débordement |
|---:|---|---|---:|---|---|---|
| **320** | **caché** | visible | 1 | 4 × **80×44** | **aucun** | **non** |
| **390** | **caché** | visible | 1 | 4 × **98×44** | **aucun** | **non** |
| **768** | visible | **cachée** | **1** | — | — | **non** |

« Libellé rogné » n'est pas une impression : le contrôle compare `scrollWidth`/`scrollHeight` à
`clientWidth`/`clientHeight` sur **chaque** lien. Et la réserve en bas du contenu passe de **76 px**
sous 768 à **24 px** au-delà — la barre ne masque jamais la fin d'une page, et n'en réserve pas la
place quand elle n'existe pas.

### La césure française, mesurée

| Mode | Coupure de « Trombinoscope » | Hauteur |
|---|---|---:|
| `overflow-wrap: anywhere` | « Trombinosc / ope » | 30 px |
| **`hyphens: auto`** | « **Trombino- / scope** » | 30 px |

`index.html` déclare `lang="fr"`, donc le navigateur sait couper le français. Même hauteur, coupure
lisible : c'est retenu.

---

## 5. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make check` | **code 0** — **683** pytest, **183** Vitest (90 `ui`, **76 `web`**, 17 `contracts`) |
| `make cadre-check` | **code 0** — **18 contrôles** (14 + 4), dans `make check` et dans la CI |
| `make cadre-temoin` | **code 0** — il échoue en nommant **les sept** motifs attendus |
| `make residu-check` `entites-check` `ecrans-check` | **code 0** pour les trois |
| `docs-check` `audit` `icloud-verify` | **code 0** pour les trois |

### Un défaut de mon propre contrôle, et c'était un FAUX POSITIF

Le contrôle « tout élément interactif a une règle `:focus-visible` » dérivait sa liste du **nommage**
des classes CSS — celles contenant `-lien` ou `-evitement`. Dès sa première exécution il a signalé
`.app-liens`, qui est le `<ul>` **conteneur** et n'est pas focusable.

> **Un garde-fou à faux positifs apprend à passer outre**, si bien que le jour où il a raison il n'est
> plus lu — §7.25. Il n'a pas été affaibli mais **rendu exact** (§7.20) : la liste est désormais
> dérivée du **TSX**, où le type d'élément — `<a>`, `<Link>`, `<NavLink>`, `<button>`, `<summary>` —
> détermine la focusabilité. Le nommage ne le dit pas ; le TSX si.

Il trouve maintenant **cinq** classes, toutes pourvues.

### Ce qui n'est PAS mesuré au clavier, et pourquoi

**La marche au clavier à 320 px avec la barre.** Le volet du navigateur a cessé de délivrer les
événements clavier — deux tentatives, zéro arrêt enregistré. Je ne le rapporte donc pas comme mesuré.

La marche de `T4` — huit `Tab`, huit arrêts, focus visible sur les huit — avait été mesurée **à 320 px
avec le menu du haut visible**, ce que `T5` change : c'est le §7.21, notre propre changement rend une
mesure obsolète.

Ce qui est établi à sa place, et qui tourne à **chaque** pull request :

- **aucun `tabIndex` positif** nulle part — donc l'ordre de focus séquentiel est l'ordre du document ;
- **l'ordre des repères dans le DOM** est asserté par un test : `HEADER`, `NAV[Menu principal]`,
  `MAIN`, `NAV[Barre de navigation]` ;
- **les cinq classes interactives ont une règle `:focus-visible` avec un `outline`** ;
- **le menu du haut est `display: none` sous 768 px**, mesuré.

Une exigence statique exacte qui tourne à chaque PR vaut mieux qu'une mesure manuelle qu'on ne peut
pas rejouer. Mais elle ne la remplace pas, et le dire vaut mieux que de laisser croire.

---

## 6. Ce qui n'est PAS couvert

| Non couvert | Pourquoi, et quand |
|---|---|
| **le bouton « Reporter un bug » dans le menu mobile** | le §9.5 du cahier le place « depuis le menu mobile », et les rapports de bug sont **LOT 13** (`bug_report`). L'emplacement est **noté**, pas préparé |
| **la source des deux conditions** | LOT 7 pour le parcours, `T9` pour les rôles. Les propriétés existent et les tests éprouvent les deux états |
| **`Escape` pour fermer « Plus »** | `<details>` ne le fait pas nativement. Ce n'est pas une modale : rien n'est piégé derrière |
| **la marche au clavier à 320 px** | non mesurée, voir le §5. Les exigences statiques la couvrent partiellement |

---

## 7. Ce que `T6` devra savoir

1. **la page nationale est la liste accessible des entités**, et son critère est structurel : « **la
   liste précède la carte dans le DOM**, pas seulement à l'œil ». `T7` apportera la carte, donc
   l'ordre se décide en `T6` ;
2. **le cadre applicatif ne s'applique PAS à la page nationale** : elle n'a pas d'entité consultée.
   Elle vit sous `/`, où la page de statut du LOT 1 est aujourd'hui servie — et `make web-check`
   l'exige. **Ce point est à instruire** : le cahier §4.1 dit « une page nationale après
   authentification », et la racine sert actuellement un écran technique ;
3. **`RUBRIQUES` est la source** du menu, des routes et des titres. La page nationale n'en est pas une
   rubrique — elle est **au-dessus** de l'entité ;
4. **`cadre-check` compte les rubriques inconditionnelles** et les borne à ce que 320 px acceptent. En
   ajouter une ferait échouer le contrôle, et c'est son rôle.
