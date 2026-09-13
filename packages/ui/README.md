# `packages/ui` — design system eXalt

**Créé en :** LOT 1, sous-étape `T1`, story `MVP-L01-US001`
**Rempli en :** LOT 1, sous-étape `T10`, `DEC-491`
**Consolidé en :** LOT 4, sous-étape `T11`
**Fondement :** cahier des charges §13.1 à §13.3, §14
**Dernière mise à jour :** 7 septembre 2026, `T5` du LOT 5

---

## 1. Les jetons ont été RELEVÉS, puis RECALCULÉS. Aucune couleur n'est inventée

**Le cahier §13.1 exige « la charte graphique » et « la police officielle » ; aucune des deux n'est
dans le corpus.** Mesure : aucun fichier de design versionné, et **zéro** couleur hexadécimale dans
le cahier des charges.

**Le prototype, lui, NOMME sa palette** — `EXALT_BLUE = #5853FF`, `EXALT_DARK_BLUE = #2F2F9B`,
`EXALT_PINK = #FF2C9B`, `EXALT_YELLOW = #FFDA3E` — et cela corrobore **littéralement** le « dégradés
bleu, rose et violet » du §13.2. **Deux sources concordantes, donc pas une invention** (`DEC-491`,
sur arbitrage de Jonathan entre quatre options).

### Et la mesure a CORRIGÉ le prototype — c'est le résultat le plus utile

| Couleur | Contraste mesuré | Conséquence |
|---|---|---|
| jaune sur fond clair | **1,37** | inutilisable comme couleur de **texte** |
| bleu foncé sur fond sombre | **1,69** | inutilisable comme couleur de **texte** |

Les couleurs de marque sont donc des **surfaces** portant un texte apparié **mesuré**, pas des
couleurs de texte libres. **Le prototype ne prévoyait du texte foncé que pour le jaune ; le rose et
le vert le réclament aussi.** Le reprendre tel quel aurait reconduit **deux** défauts
d'accessibilité.

`contraste.ts` calcule les ratios WCAG 2.2, et les tests **exigent** AA sur chaque paire déclarée —
donc un jeton ajouté sans son apparié fait échouer.

---

## 2. Ce que le paquet contient

**97 tests.** Les compter, jamais les recopier : `pnpm --filter @onboarding/ui test`.

| Fichier | Ce qu'il porte |
|---|---|
| `jetons.ts` · `jetons.css` | les jetons de couleur, typographie, espacement — **une seule source**, le CSS étant vérifié contre le TypeScript |
| `contraste.ts` | le calcul WCAG 2.2, et les paires appariées |
| `Bouton.tsx` · `Badge.tsx` · `Carte.tsx` | les trois composants de base, `T10` du LOT 1 |
| `Alerte.tsx` · `Notification.tsx` | ajoutés en `T11` du LOT 4 pour les états d'erreur et la perte de connexion |
| `composants.css` | les feuilles des composants |

> **`jetons.css` et `composants.css` doivent être IMPORTÉS pour agir**, et ne pas l'être est
> silencieux. Mesuré en `T3` du LOT 4 : **les deux feuilles n'étaient importées par personne**
> depuis un mois, et les écrans s'affichaient sans elles — `ECART-042`. Un contrôle de stack
> vérifie désormais qu'aucune couleur servie ne sort des jetons.

---

## 3. La contrainte qui ne se négocie pas

**Aucune couleur, aucune police, aucun espacement ne s'ajoute sans une source.** Le backlog l'écrit
littéralement : « **sans dépendance visuelle arbitraire** ». L'identité visuelle relève du cahier
§13.1 et de Léa, pas d'un choix d'implémentation.

En pratique, pour ajouter un jeton :

1. **trouve la source** — le cahier, ou le prototype qui le corrobore ;
2. **mesure le contraste** de chaque paire que le jeton rend possible ;
3. si la mesure contredit la source, **la mesure gagne**, et l'écart est consigné.

**L'accessibilité du cahier §14 est une exigence dure**, auditée au LOT 12 :
`eslint-plugin-jsx-a11y` est actif sur tout `.jsx` ou `.tsx` (`DEC-451`).

> **Ce linter n'avait jamais eu un seul fichier JSX à examiner avant `T5` du LOT 1** — il
> n'existait aucun `.tsx` dans ce dépôt. Motif déterminant de `DEC-451`, il a été **éprouvé par
> témoin négatif** avant d'être considéré actif. *Un contrôle qui n'a jamais eu de matière à
> examiner ne prouve rien.*

---

## 4. Le piège de `T11` du LOT 4, et il vaut pour tout composant nouveau

**Le critère était « chaque composant livré est EMPLOYÉ ».** Livrer un composant qu'aucun écran
n'utilise, c'est livrer du code mort qui **paraît** être un design system.

Un contrôle vérifie donc l'**emploi**, pas seulement l'existence : un composant exporté et jamais
importé par un écran fait échouer.

---

## 5. Commandes

```bash
pnpm --filter @onboarding/ui test   # 97 tests
make typecheck                       # tsc --noEmit strict
make test-frontend                   # les trois paquets : ui, web, contracts
```
