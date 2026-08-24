# Compte rendu — LOT 4, sous-étape `T11`

**Deux orphelins, une duplication à moi, et un badge que l'écran a déplacé**
**Story :** `MVP-L04-US007` (`P1`) · **Réalisée le :** 24 août 2026
**Décision produite :** `DEC-555` · **Écart consigné :** aucun
**Migration produite :** **aucune**

---

## 1. La mesure a trouvé deux orphelins avant que le contrôle n'existe

`T11` arrive **après** les écrans, et c'est délibéré : les composants sont **consolidés** à partir de
ce que `T3` à `T10` ont réellement eu besoin. La première chose à faire était donc de mesurer ce que
les écrans emploient.

| Composant, livré en `T10` du LOT 1 | Importé par |
|---|---|
| `Bouton` | **3** écrans d'authentification |
| `Badge` | **aucun** |
| `Carte` | **aucun** |

Le critère de sortie dit « chaque composant livré est **employé** par un écran de ce lot », et `T10`
du LOT 1 avait établi le principe : livrer un composant sans écran qui l'emploie, c'est livrer du code
non éprouvé.

> **Attention à la façon de mesurer.** `Carte` apparaît dans `CarteDeFrance.tsx` — sans y être
> importé. Une recherche par **mot** aurait donc conclu qu'il a un consommateur, et le contrôle
> aurait été aveugle à l'orphelin qu'il devait trouver. La détection porte sur les **imports depuis
> `@onboarding/ui`**.

---

## 2. Le critère est devenu un contrôle

`make cadre-check` **dérive de `index.ts`** la liste des composants exportés, et exige de chacun :

- qu'il apparaisse dans les tests de `packages/ui` ;
- qu'il soit **importé** par un module du frontend.

**La liste est dérivée, jamais écrite** — une liste littérale vieillirait au premier composant
ajouté, et c'est précisément le cas à attraper (§7.27).

Sortie actuelle :

```text
ok  les 5 composants exportes sont TESTES et EMPLOYES :
    Alerte, Badge, Bouton, Carte, Notification
```

**Éprouvé sur un vrai orphelin** : l'import de `Badge` retiré de son écran, le contrôle a répondu
`NON EMPLOYES par un ecran : ['Badge']`.

---

## 3. La mesure a désigné le composant à créer

| Motif répété dans le frontend | Occurrences |
|---|---|
| `className="app-message"` | **11** |
| `className="app-liens"` · `"app-lien"` | 4 · 4 |
| tout le reste | ≤ 2 |

Onze exemplaires du même trio ton/rôle/texte : c'est la famille **« alertes »** du backlog, et de loin
le motif le plus répété. D'où `Alerte`.

**Il couvre TROIS familles du backlog, et le dire vaut mieux qu'en inventer trois.** « Alertes »,
« loaders » et « états vides » ne se distinguent pas par leur structure — ce sont tous un message avec
un rôle :

| `urgence` | `role` | Ce que cela sert |
|---|---|---|
| `alerte` | `alert` | interrompt la lecture — une erreur le mérite |
| `information` | `status` | n'interrompt pas — un chargement, un état vide |
| `aucune` *(défaut)* | *aucun* | un texte informatif que rien ne rend urgent |

Livrer trois composants dont deux ne différeraient que par une constante serait la « surface d'audit
sans contrepartie » que `DEC-456` refuse, et un lecteur aurait **trois** endroits à lire pour
comprendre **une** règle.

> **`aria-live` n'est pas écrit, et c'est mesuré.** `role="alert"` implique `aria-live="assertive"`,
> `role="status"` implique `polite` — les deux sont dans la spécification ARIA. Les écrire en plus est
> une redondance qui peut diverger, et c'est la leçon du `<details>` de `T8`, où un `aria-expanded`
> aurait doublé l'état que le navigateur porte déjà.

---

## 4. `Notification` était la seule des six familles absente partout

Le §17.4 la demande, le backlog `US007` la nomme, et **rien ne l'implémentait**. Les cinq autres
existaient sous une forme ou une autre dans les écrans.

**Ce qui la distingue d'une `Alerte` est structurel, pas cosmétique :**

| | décrit | conséquence sur le balisage |
|---|---|---|
| `Alerte` | **l'état de l'écran** — elle reste tant que l'état dure | apparaît **avec** son état, son rôle est lu à l'entrée |
| `Notification` | **le résultat d'une action** — elle n'a plus de sens ensuite | son conteneur doit être présent **avant** son texte |

Un `aria-live` ajouté au DOM **en même temps que son contenu** n'est pas annoncé de façon fiable : les
lecteurs d'écran observent les mutations d'une région **déjà connue**. `Notification` rend donc
**toujours** son conteneur, même vide — ce qui est exactement l'état au premier rendu.

**Aucune disparition automatique**, et le motif est d'accessibilité : WCAG 2.2.1 demande de pouvoir
prolonger toute limite de temps, et « notifications **temporaires** » au §17.3 veut dire *liées à
l'action*, pas *minutées*. C'est l'appelant qui décide quand elle disparaît.

Son consommateur : le résultat de la copie de l'identifiant de corrélation — un **résultat d'action**,
donc exactement son cas.

---

## 5. Une duplication était la mienne, d'une seule sous-étape

`T10` a écrit dans `PanneauDErreur.tsx` son propre `<button className="app-action">`, alors que
`packages/ui` porte un `Bouton` depuis `T10` du LOT 1. Mesuré : **trois** écrans l'importaient, le
portail non.

C'est §7.27, et je l'ai commis **une sous-étape avant de le corriger**. Le panneau emploie maintenant
`Bouton` pour ses deux actions — `primaire` pour le réessai, `secondaire` pour la copie.

---

## 6. `Badge` a changé de place après mesure à l'écran

Ma première version le posait sur la mention du §5.1 — « Consultation uniquement, sans
modification : cette entité n'est pas votre entité principale » — au motif que c'est « un état court
et permanent ».

| Largeur | Ce que l'œil voit |
|---|---|
| 1 280 px | une ligne, acceptable |
| 375 px | **trois lignes dans une pastille**, visuellement faux |

**Un composant dont la justesse dépend de la largeur est le mauvais composant pour une phrase de
vingt mots.** La mention est devenue une `Alerte` — `ton="avertissement"`, ce n'est ni un succès ni
une erreur mais une restriction — et `Badge` a trouvé un emploi où il est juste : **l'étiquette de
lot** de `PageRubrique`, « LOT 6 », qui tient sur une ligne à toute largeur.

`Carte`, elle, n'est pas forcée : le bloc de corrélation **est** une section titrée, exactement ce que
`PageStatut` rendait à la main depuis `T5` du LOT 1.

---

## 7. Le CSS mort supprimé — et un faux positif de mon propre contrôle

Six blocs sont devenus morts : `.app-message`, `.app-action`, `.app-action-discrete`,
`.app-consultation`, `.app-correlation`, `.app-correlation-annonce`. Du CSS que personne n'applique
est du code non éprouvé, et le laisser laisserait croire qu'il sert.

**Leur suppression a fait échouer `cadre-check` — sur un livrable correct.** Le contrôle des classes
interactives lisait la **source TSX brute**, et le docstring de `PanneauDErreur.tsx` **raconte** que
`T10` écrivait `<button className="app-action">` — pour expliquer qu'il ne le fait plus. Il exigeait
donc une règle `:focus-visible` pour une classe que plus aucun élément ne porte.

> **Troisième occurrence de cette classe dans ce même fichier.** `T7` l'avait corrigée pour deux
> autres contrôles ; celui-ci lisait encore le brut. §7.34 — une instance corrigée n'est pas la
> classe corrigée. Et §7.25 : un garde-fou qui refuse du code correct apprend à passer outre.

---

## 8. Les trois critères de sortie, un par un

| Critère | Comment il est tenu |
|---|---|
| « chaque composant livré est **employé** par un écran de ce lot » | **un contrôle**, dérivé de `index.ts` : 5 composants, tous testés et importés |
| « contraste **mesuré** » | `jetons.test.ts` **recalcule** les contrastes — 11 appels à `contraste`/`atteintSeuil` — contre WCAG 2.2 AA. Les tons d'`Alerte` portent sur la **bordure** et jamais sur le texte, précisément parce que le jaune de marque rend 1,37 avec du texte clair (`DEC-491`) |
| « `jsx-a11y` **sans exception** » | **zéro** `eslint-disable`, mesuré sur `apps/web/src`, `packages/ui/src` et `eslint.config.js` |

---

## 9. Mesures

| Grandeur | Valeur, dérivée |
|---|---|
| pytest | **709** — inchangé, `T11` est frontend seul |
| Vitest | **235** — **97** `ui`, 121 `web`, 17 `contracts` |
| `make cadre-check` | **25 contrôles**, 0 échec — 24 avant `T11` |
| `make cadre-temoin` | **15 motifs** exigés et nommés — 14 avant |
| Composants exportés | **5** — `Alerte`, `Badge`, `Bouton`, `Carte`, `Notification` |
| `residu-check` · `permissions-check` · `entites-check` · `ecrans-check` | 0 · 0 · 0 · 0 |
| CSS retiré | **6 blocs**, 1 989 octets |
| Migration | **aucune** |

**Vu dans un vrai navigateur, à 375 px et à 1 280 px** : la mention du §5.1 en alerte bordée, « LOT 6 »
en badge d'une ligne, et le panneau d'erreur complet — `Alerte`, `Bouton` primaire, `Carte` titrée,
`Bouton` secondaire, `Notification` vide et invisible.

---

## 10. Ce que `T11` ne fait pas, et ce qu'elle laisse à `T12`

- **les « menus » du backlog restent dans l'application**, et ce n'est pas un oubli. Le sélecteur
  d'entité et l'accès « Plus » sont des `<details>` **de navigation** : leur contenu est fait de
  `<Link>` liés aux routes du portail, donc ils ne sont pas réutilisables hors de lui. Un composant
  générique n'aurait eu qu'un seul consommateur — ce que le critère de `T11` refuse justement ;
- **les « messages de champs » restent dans les formulaires d'authentification**, où `T11` du LOT 3
  les a posés. Les extraire sans second consommateur serait le même défaut ;
- **`PageStatut` emploie encore les classes neutres d'avant `packages/ui`.** Elle partage désormais la
  **logique** avec le portail — `reseau.ts`, depuis `T10` — mais pas le balisage : le même message de
  copie s'affiche dans deux habillages. La faire converger demanderait de réécrire une page du LOT 1
  qui n'est plus la page d'accueil depuis `DEC-549`, et ce n'est le critère d'aucune sous-étape. **À
  signaler à `G4`** ;
- **`DEP-006` reste ouverte** — « charte, logo et typographie officiels », Léa / eXalt — et son
  échéance est ce lot. Les jetons de `DEC-491` sont **relevés du prototype et recalculés** contre
  WCAG ; le jour où la charte arrive, c'est `jetons.ts` qui change, en un endroit.
