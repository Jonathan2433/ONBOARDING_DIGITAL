# Compte rendu — `T11` du LOT 8 : l'accueil final desktop

**Sous-étape :** la onzième du lot — composer les cinq sections de l'accueil,
dans l'ordre du cahier §8.4, avec ouverture externe explicite des liens
**Date :** 6 octobre 2026
**Décision :** `DEC-630`
**Stories :** `MVP-L08-US001` (2/2), `MVP-L08-US006` (2/2)

---

# 1. État du lot

| | |
|---|---|
| Lot | **LOT 8**, ouvert le 01/10/2026 (`DEC-619`), **quatorze** sous-étapes |
| Faites | `T1` à `T10`, **`T11`** |
| Restent | `T12` à `T14` |
| Issues | épic `#206`, stories `#207` à `#212`, jalon `G8` |

---

# 2. Un trou réel trouvé en construisant l'écran, pas anticipé par la fiche

`T8` (agrégat d'accueil, `DEC-627`) a servi `GET …/accueil` sans qu'aucun
écran n'en consomme la section « présentation » **en lecture**. La seule
page qui en affichait quelque chose était `PanneauEditionDeContenu` (LOT 6,
`T10`) — un composant d'**édition**, qui rend `null` dès que l'appelant n'a
pas de droit d'édition :

```tsx
if (roles === null || !peutEditerUnContenu(roles)) {
  return null;
}
```

Or la matrice §5 donne « Lecture » aux **huit** rôles authentifiés sur la
présentation, le Framework, les arrivées récentes, les événements et les
liens internes — sans aucune divergence entre ces six ressources. Un `EMP`
ou un `NEW`, qui n'a jamais de droit d'édition, ne voyait donc **strictement
rien** de la présentation depuis l'ouverture du LOT 6 : ni son titre, ni ses
blocs, rien qu'un cadre vide. Ce n'était pas un défaut d'une route — la
route lit tout — c'était l'absence de tout écran qui lise ce que la matrice
autorise.

`T11` ne corrige rien de `PanneauEditionDeContenu`, qui reste exactement ce
qu'il était pour les rôles éditoriaux : il **ajoute**, au-dessus, le rendu en
lecture de la même section, pour tous. Les deux régimes coexistent sur la
même carte « Présentation » : le texte des blocs en haut, le panneau
d'édition en dessous pour qui peut écrire.

---

# 3. Ce que la sous-étape a produit

| Fichier | Ce qu'il porte |
|---|---|
| `packages/contracts/src/accueil.ts` | Premier module de contrat de l'agrégat : `AccueilDEntite`, `ArriveeRecente`, `PageDesArriveesRecentes`, `validerLAccueil`, `cheminAccueil` |
| `packages/contracts/src/accueil.test.ts` | **13 tests** |
| `packages/contracts/src/index.ts` | Réexports étendus |
| `apps/web/src/api/accueil.ts` | `lireLAccueil`, même montage `lire<T>` que `evenements.ts` |
| `apps/web/src/affichage.ts` | `heureDeLEvenement`/`plageDeLEvenement`, déplacées depuis `PageEvenements.tsx` — `T11` en est le second consommateur |
| `apps/web/src/pages/PageEvenements.tsx` | Importe désormais `plageDeLEvenement` depuis `../affichage`, ne la déclare plus localement |
| `apps/web/src/pages/PageEntite.tsx` | Réécrit : les cinq sections de l'accueil, dans l'ordre, en `<Carte>` |
| `apps/web/src/pages/PageEntite.test.tsx` | **11 tests** (nouveau fichier — aucun test direct n'existait avant `T11`) |
| `apps/web/src/pages/CadreApplicatif.test.tsx` | Un test mis à jour pour mocker `/accueil` et scoper une requête `getByRole('status')` devenue ambiguë |
| `apps/web/src/pages/application.css` | Classes `.accueil-*` |

## 3.1 Le frontend n'est pas l'autorité — encore, et dans un sens nouveau

Jusqu'ici, « le frontend n'est pas l'autorité » signifiait : un bouton
visible peut recevoir un 403. `T11` en ajoute une variante : **une section
absente ne veut pas dire qu'elle est refusée** — elle peut simplement n'avoir
jamais été câblée. La matrice reste la référence ; c'est à chaque écran de
la lire entièrement, pas seulement la partie qu'un composant voisin
affichait déjà.

## 3.2 `texteDuBloc(bloc, 'texte')` — la clef n'est pas inventée

`QO-121` reste ouverte : le corpus ne nomme aucune clef de `payload_json`.
Mais `texte` n'est pas une invention de `T11` — c'est la clef que **toutes**
les fixtures du dépôt emploient déjà pour un contenu textuel :
`test_ecriture_des_contenus.py` (API), `gestionDuContenu.test.ts` et
`PanneauEditionDeContenu.test.tsx` (frontend). La reprendre plutôt que d'en
choisir une autre évite une deuxième convention pour la même chose.

## 3.3 `NOMBRE_MONTRE = 5` — un choix de cette sous-étape, pas une invention

`T8` l'écrivait explicitement : aucun document ne nomme de borne d'éléments
affichés par section, et le choix est délibérément laissé à `T11`/`T12`.
Chaque section plafonne donc à cinq éléments avec un lien vers l'écran
complet (Framework, trombinoscope, événements) — aucun carrousel, qui reste
le sujet propre de `T12` (mobile).

## 3.4 L'ouverture externe explicite — `MVP-L08-US006` (2/2)

Le critère d'acceptation dit « indiquent clairement l'ouverture externe »
sans imposer de mécanisme. Chaque lien servable (`urlEstServable`, déjà la
troisième barrière d'affichage depuis le LOT 6) s'ouvre dans un nouvel onglet
— `target="_blank" rel="noopener noreferrer"` — et porte une mention
**textuelle visible**, « Ouvre dans un nouvel onglet », jamais une icône
seule (même discipline que `Badge`, WCAG 1.4.1). Un lien refusé s'affiche
désactivé et visible, jamais silencieusement absent — mesuré en tentant
d'insérer un lien de la forme `https:alert(1)` dans la base réelle : la
contrainte `ck_internal_link_url_https` (migration `0019`, LOT 6) le refuse
avant même d'atteindre l'écran, confirmant qu'aucune donnée réelle ne peut
exercer cette branche autrement que par un test de composant.

## 3.5 `heureDeLEvenement`/`plageDeLEvenement` partagées — `T9` en gagne un second consommateur

`PageEvenements.tsx` (`T9`) déclarait ces deux fonctions localement, seule
consommatrice jusqu'ici. `T11` en devient le second écran : les deux
fonctions sont déplacées dans `apps/web/src/affichage.ts` — le module posé
au LOT 5 pour « ce que deux écrans au moins doivent présenter de la même
façon » — plutôt que recopiées (§7.27).

---

# 4. Contrôles exécutés

| Contrôle | Résultat |
|---|---|
| `uv run pytest -q --collect-only` | **1 564**, inchangé — aucune ligne Python touchée |
| `uv run mypy` (depuis la racine) | vert, **197** fichiers, inchangé |
| `pnpm --filter @onboarding/contracts test` | **380/380** (+13) |
| `pnpm --filter web test` | **290/290** (+11) |
| `pnpm --filter @onboarding/ui test` | **111/111**, inchangé |
| `pnpm run typecheck` (tsc, 3 paquets) | vert |
| `pnpm run lint` / `pnpm run format:check` | vert |
| **aller-retour réel** (§7.43) | décor psql réel (entité `t11demo`, ESM `t11-esm@exalt-company.com` avec responsabilité réelle, cercle, bureau, événement à venir, arrivée récente, deux liens internes), lien magique réel consommé **deux fois** — une fois pour l'ESM (rôle éditeur), une fois pour l'arrivante (rôle de simple lecture, aucune responsabilité) — vérifié en HTTPS desktop **et** mobile (375 px) ; décor nettoyé après coup, zéro résidu vérifié par comptage direct |
| **témoin central** | le rôle de simple lecture voit les CINQ sections et aucun panneau d'édition ; l'ESM voit les cinq sections ET le panneau d'édition sous la présentation — les deux régimes coexistent, rien n'a régressé pour l'éditeur |

**Zéro régression** : le total Vitest passe de **757** à **781** (+24 :
+13 `contracts`, +11 `web`, +0 `ui`), le total pytest reste à **1 564**
puisqu'aucune ligne Python n'a été touchée — confirmé par `git status`.

---

# 5. Décisions

- `DEC-630` consigne la réalisation de `T11` ;
- aucun écart nouveau n'est ouvert ; `ECART-068` reste intact.

---

# 6. Un défaut documentaire trouvé et corrigé au passage

En mettant à jour `CLAUDE.md`, la règle n°1 du §2 (« un lot à la fois »)
annonçait encore « `T1` à `T8` sont faites […] `T9` est la suivante » —
deux sous-étapes après leur fusion effective. Cette règle n'avait pas été
mise à jour par les passes documentaires de `T9` ni de `T10`, qui avaient
pourtant corrigé les autres mentions du document (§1, §9.1, §9.2). Corrigé
dans la même passe que `T11`, même discipline que le §9.1 de `T10`
(« vérifie ce que la documentation affirme », §7.11).

---

# 7. Ce que `T11` laisse

- l'accueil final desktop complet : les cinq sections du cahier §8.4, dans
  l'ordre, pour les huit rôles authentifiés ;
- le trou de lecture de la présentation est comblé pour tous les écrans
  futurs qui consulteraient l'accueil ;
- `T12` (accueil mobile, carrousels accessibles, vidéo sur action) doit
  décider de la présentation en carrousel — `NOMBRE_MONTRE = 5` reste le
  plafond desktop posé ici, à réutiliser ou à justifier de ne pas reprendre,
  pas à re-décider sans le dire ;
- `T13` (contrôle de pile réelle) devra couvrir l'accueil au même titre que
  les autres écrans — aucun script `make accueil-check` n'existe encore.

# Validation demandée à Jonathan

`T11` est faite. Après fusion, la prochaine sous-étape est `T12` : l'accueil
mobile, les carrousels accessibles et la vidéo chargée sur action.
