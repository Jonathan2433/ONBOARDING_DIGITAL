# Compte rendu — LOT 4, sous-étape `T7`

**La carte de France, et le moment où j'ai arrêté de dessiner**
**Story :** `MVP-L04-US001` · **Réalisée le :** 23 août 2026
**Décision produite :** `DEC-550` · **Écart consigné :** aucun
**Migration produite :** **aucune**

---

## 1. Trois mesures ont fermé le choix avant d'écrire

Le corpus nomme la carte **six** fois et n'en dit qu'un mot : « **illustrative** ». Aucun format,
aucune source de données, aucune coordonnée.

| Mesure | Résultat |
|---|---|
| **le schéma** | `entity` porte `city` mais **ni latitude ni longitude** — une carte à marqueurs exigerait donc une colonne au modèle, ou des positions inventées |
| **le prototype** | sa `FranceMap` est une **image base64 avec un seul bouton posé dessus**, `alt="Carte eXalt"` — **aucun SVG de carte, aucune coordonnée, aucune bibliothèque**. L'intention n'est **pas** une carte de données |
| **`DEP-006`** | **OUVERTE**, échéance **ce lot** : « charte, logo et typographie officiels exploitables », Léa / eXalt. Le visuel officiel n'existe pas |

Le prototype a été lu **sans être greppé en entier** — 2,7 Mo dont l'essentiel en base64, §7.13 : motifs
comptés, puis contextes extraits et tronqués.

Réutiliser son image est **interdit** par la règle 4 — « aucune ligne de code du prototype réutilisée »
— et ne rien livrer contredirait la roadmap, qui inclut la carte au LOT 4. **Il ne restait qu'un
chemin, et je n'ai donc pas eu de question à poser.**

---

## 2. Le moment où j'ai arrêté de dessiner, et pourquoi c'est la bonne décision

Trois versions du tracé ont été faites et **regardées à l'écran** :

| Version | Ce que l'œil voit |
|---|---|
| 1 | une forme ronde quelconque — pas la France |
| 2 | la Bretagne et la Corse apparaissent, le nord est trop pointu |
| 3 | « la France, à peu près » |

> **Je me suis arrêté là, et le motif est de fond : auteurer une illustration de marque appartient à
> `DEP-006`.** Continuer aurait été la règle §6.5 — ne jamais inventer ce qui n'est pas décidé —
> enfreinte sur une **image** au lieu d'une valeur.

**Ce qui est livré est ce que le critère demande** : l'emplacement, sa place exacte dans le DOM, et son
caractère **décoratif**, tous trois tenus par `make cadre-check`. L'illustration elle-même est un
remplacement d'**une ligne** : un `<img>` à la place du `<svg>`, sans toucher au reste. C'est le parti
de `DEC-491` pour les couleurs — des jetons provisoires, dérivés et remplaçables sans refonte.

**Et le code le dit.** Un tracé approximatif présenté comme une carte de référence serait une
affirmation que je ne peux pas tenir — §7.0, septième point.

---

## 3. Décorative par construction, et le prototype invitait à l'enfreindre

| Exigence | Pourquoi |
|---|---|
| `aria-hidden="true"` | elle est retirée de l'arbre d'accessibilité : elle n'apporte rien que la liste ne donne |
| `focusable="false"` | un `<svg>` est focusable dans certains moteurs ; l'attribut le ferme |
| **aucun élément interactif** | **le prototype posait un BOUTON sur son image.** Un élément interactif dans un sous-arbre `aria-hidden` est atteignable au clavier **sans être annoncé** — pire qu'un bouton absent |
| ni `role="img"` ni `<title>` | ce serait annoncer une carte qui n'informe pas |

`make cadre-check` exige **les quatre**, et la carte ne s'affiche que quand il y a des entités à
illustrer : sur un écran d'erreur ou vide, elle occuperait la place du message.

---

## 4. Trois défauts, tous dans mes propres contrôles ou mon propre CSS

### `cadre-check` cherchait un marqueur qui n'existait plus

Il cherchait `className="nat-carte"` dans `PageNationale.tsx`. `T7` a mis la carte dans son propre
composant : la page ne porte plus que `<CarteDeFrance />`, le motif ne trouvait plus rien, et le
contrôle annonçait « la carte n'existe pas encore » **suivi de `ok`** — alors qu'elle existait.

> **Même classe qu'à `T4`**, où il disait `ok` en ayant compté zéro route. Un contrôle dont la
> condition ne décrit plus la réalité ne mesure plus rien.

### Deux motifs se déclenchaient sur leurs propres commentaires

Le docstring de `CarteDeFrance.tsx` explique qu'elle ne doit porter « ni `<a>`, ni `<button>` » et
« pas de `role="img"`, pas de `<title>` ». Mes deux motifs y ont trouvé **exactement ce qu'ils
interdisaient**, et ont signalé un livrable conforme.

> **C'est le défaut `T11` du LOT 2 à l'identique**, et `verifier-ecrans.py` l'avait déjà résolu — il
> retire les commentaires CSS avant de chercher. La correction n'avait pas été portée ici : **§7.34,
> troisième fois** — une instance corrigée n'est pas la classe corrigée.

Un helper `sans_commentaires_tsx` est posé et appliqué aux **trois** lectures de TSX du contrôle.

### Un défaut de cascade que seule la mesure pouvait attraper

La carte mesurait **1 152 × 1 152 px** au lieu de 352, `max-width` calculé à `100%` alors que la
feuille dit `22rem`. Cause : ma propre règle de `T3`

```css
.app-principal img, .app-principal svg { max-width: 100%; height: auto; }
```

vaut **0,1,1** en spécificité contre **0,1,0** pour une classe seule : elle l'emportait. Le sélecteur
est passé à `.nat-carte .nat-carte-dessin`, soit 0,2,0.

> **Aucun contrôle statique ne résout une cascade.** La feuille contenait bien `max-width: 22rem`, et
> tout lecteur l'aurait cru appliqué. C'est précisément pourquoi le critère de `T3` dit « **mesuré** ».

---

## 5. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `make check` | **code 0** — **683** pytest, **196** Vitest (90 `ui`, **89 `web`**, 17 `contracts`) |
| `make cadre-check` | **code 0** — **20 contrôles**, dans `make check` et dans la CI |
| `make cadre-temoin` | **code 0** — il échoue en nommant **les neuf** motifs attendus |
| `residu-check` `entites-check` `ecrans-check` `web-check` | **code 0** pour les quatre |
| `docs-check` `audit` `icloud-verify` | **code 0** pour les trois |

**Mesures dans un vrai navigateur** : la liste **précède** la carte dans le DOM · `aria-hidden="true"`
et `focusable="false"` sur le dessin · **0** élément focusable dans la carte · la séquence des
focusables de la page est `lien d'évitement → main → les deux entités`, **la carte n'y figure pas** ·
352 × 352 après correction de la cascade · aucun débordement.

---

## 6. Ce qui reste, et qui n'est pas de mon ressort

> **`DEP-006` est ouverte et son échéance est ce lot.** « Charte, logo et typographie officiels
> exploitables, licence web incluse », Léa / eXalt. Le tracé livré est un provisoire ; l'illustration
> officielle le remplace en une ligne.

C'est le seul point du LOT 4 qui dépende de quelqu'un d'autre, et il vaut d'être dit maintenant plutôt
qu'à la porte `G4`.

---

## 7. Ce que `T8` devra savoir

1. **les cinq règles du §23.3 deviennent toutes exigibles** : ne pas modifier l'entité principale, ne
   pas transférer les responsabilités, recharger les permissions, **annuler les requêtes et caches de
   l'entité précédente**, et rester visible dans l'en-tête. La quatrième est **déjà** tenue depuis
   `T2` — `AbortController` et couplage de l'état au code — et un test la fabrique sous latence ;
2. **le changement d'entité est une NAVIGATION**, pas une écriture : l'entité vit dans l'adresse
   depuis `DEC-545`. Si `T8` en faisait une écriture, elle deviendrait le premier vrai consommateur de
   `_proteger_du_csrf`, livré au LOT 3 et toujours sans usage ;
3. **`cadre-check` compte 20 contrôles et son témoin en nomme neuf.** Toute exigence ajoutée doit
   l'être **dans les deux** : un contrôle sans témoin ne prouve pas qu'il sait échouer.
