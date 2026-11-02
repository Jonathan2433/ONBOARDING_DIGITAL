# Design système — Onboarding Digital eXalt (v1)

Spécification d'implémentation pour `packages/ui` et `apps/web`.
Sources : prototype V1 (inspiration de structure et de ton uniquement, **aucun code V1 réutilisé**) + charte eXalt (règles visuelles).

## 1. Principes non négociables

1. **Flat** : aucun dégradé, aucune `box-shadow`, aucun « lift » au survol. Séparation = bordure `1px var(--trait)`, survol = `border-color: var(--marque-bleu)`.
2. **Couleur = surface** : chaque couleur de marque s'utilise avec son texte apparié (tableau §2). Le jaune n'est jamais une couleur de texte. Le rose porte l'encre, pas le blanc (sauf ≥ 24px gras).
3. **Le mot porte le sens** : statuts, cercles, étapes → toujours libellé (+ pictogramme). La couleur n'est qu'un renfort (WCAG 1.4.1).
4. **Pas d'emoji.** Les pictogrammes officiels eXalt (`pictos/exalt-icons.json`) les remplacent (ex. « ⚡ Booster » → badge texte « Booster »).
5. **Vouvoiement** partout (la V1 tutoie, la charte vouvoie).
6. **Focus visible** : `outline: 3px solid rgb(88 83 255 / 45%); outline-offset: 2px` sur tout élément interactif. Cibles tactiles ≥ 44px.
7. **Mouvement** neutralisé sous `prefers-reduced-motion: reduce`.

## 2. Jetons

Fichier complet : `jetons.css` (à reporter d'abord dans `jetons.ts`, source de vérité, puis projeter dans `jetons.css`). Les noms existants du dépôt sont conservés ; seules les valeurs changent et des jetons sont ajoutés.

| Surface | Hex | Texte apparié | Contraste |
|---|---|---|---|
| `--marque-bleu` | #5853FF | #FFFFFF | 5,1:1 |
| `--marque-bleu-fonce` | #2F2F9B | #FFFFFF | 10,5:1 |
| `--marque-rose` | #FF2C9B | `--encre` #1A1A2E | 5,0:1 |
| `--marque-jaune` | #FFDA3E | `--titre` #2F2F9B | 7,7:1 |
| `--teinte-bleu` | #ECEBFF | `--titre` | — |
| `--teinte-rose` | #FFE4F2 | `--titre` / `--encre` | — |
| `--teinte-jaune` | #FFF7D6 | `--titre` | — |
| `--teinte-gris` / `--fond-doux` | #F5F5F5 | `--titre` | — |

Neutres : `--fond` #FAFAFB · `--surface` #FFF · `--encre` #1A1A2E · `--encre-douce` #6E6E85 (tout texte secondaire, 4,9:1) · `--titre` #2F2F9B · `--trait` #E8E8EE · `--trait-fort` #D6D6E0 (champs).
`--ok` #0F6B3F / `--ko` #9B1C1C : conservés pour la page de statut uniquement (écart charte à consigner).

**Couleurs V1 à supprimer** : #F8F8FF, #FFF7E0, #E8E8FF, #6366F1, #9B53FF, #53B4FF, #FF8C53, #FF5398, gris #888/#999/#BBB, tous les `linear-gradient`.

Rayons : `--rayon-s` 8 · `--rayon-m` 14 (champs, tuiles) · `--rayon-l` 20 (cartes) · `--rayon-xl` 28 (sections d'accueil, fiche d'arrivée) · `--rayon-pastille` 999 (boutons, badges).
Espacements : échelle de 4 inchangée (4, 8, 16, 24, 32, 48).
Mouvement : 120ms (pression, `scale(.96)`) · 200ms (survol) · 360ms (retournement de carte). Courbes `cubic-bezier(.22,1,.36,1)` (sortie), `cubic-bezier(.34,1.56,.64,1)` (ressort).

Thème sombre (`prefers-color-scheme: dark`) : conserver les neutres sombres existants du dépôt ; `--titre` → #B3AFFF ; surfaces de marque inchangées.

## 3. Typographie

Century Gothic auto-hébergée (`polices/`), Regular 400 + Bold 700 uniquement, `font-display: swap`, **aucun CDN**. Pile : `'Century Gothic', 'Futura', system-ui, sans-serif`. Les graisses 800/900 de la V1 → 700.
⚠ Licence de diffusion à confirmer avant mise en production.

| Jeton | Taille | Graisse | Usage |
|---|---|---|---|
| `--taille-display` | 48 | 700, −0,025em | Accueil |
| `--taille-xxl` | 38 | 700, −0,02em | h1 de page |
| `--taille-xl` | 30 | 700, −0,02em | h2 |
| `--taille-l` | 20 | 700, −0,01em | h3, titres de carte |
| `--taille-m` | 16 | 400 | corps |
| `--taille-s` | 14 | 400 | secondaire |
| `--taille-xs` | 13 | 400 | légendes |
| `--taille-surtitre` | 12 | 700, +0,14em, MAJUSCULES | surtitres |

Titres en `--titre`, corps en `--encre`, secondaire en `--encre-douce`.

## 4. Cercles (données, pas en dur)

Créer une table `CERCLES` côté données : `{ nom, surface, texte, picto }`.

| Cercle | Surface | Texte | Picto |
|---|---|---|---|
| Produit | marque-bleu | blanc | `fusee` |
| Projet | marque-bleu-fonce | blanc | `plan-de-projet-fusee` |
| Design | marque-rose | encre | `ampoule-idee` |
| Change | marque-jaune | titre | `dialogue` |
| Data | teinte-bleu | titre | `camembert` |
| Shield | teinte-rose | titre | `bouclier-valide` |
| Forge | teinte-jaune | titre | `engrenages-multiples` |
| IT | teinte-gris | titre | `serveur` |

Pictos : extraire les SVG nécessaires de `pictos/exalt-icons.json` (`{clé: {name, viewBox, path}}`) en composants locaux, rendus en `currentColor`, taille ≥ 24px. Supprimer les pictos dessinés à la main de la V1 (CircleIcon).

## 5. Composants `packages/ui`

Chaque composant doit être utilisé par au moins un écran.

- **Bouton** (existant, à étendre) — variantes `primaire` (bleu/blanc, une par vue), `secondaire` (blanc, bordure trait-fort, texte titre), `sombre` (bleu foncé/blanc, enchaînement de parcours), `discret` (transparent, texte bleu). Forme pastille, tailles `s` 36px / `m` 44px. Pression `scale(.96)`. Pas de bouton rose à texte blanc.
- **Badge** (existant, à étendre) — tons : `mission` (bleu plein/blanc), `intercontrat` (teinte rose/encre), `enrichissement` (jaune/titre ; remplace l'indigo V1), `booster` (teinte bleu/titre), `annule` (gris/encre-douce), `info` (teinte bleu/titre). Pastille, 12–13px bold.
- **Carte** (existant) — surface blanche, bordure trait, rayon-l, padding 22px, aucune ombre ; variante `interactive` : survol bordure bleue.
- **Pastille** (nouveau) — surtitre de rubrique : fond jaune, texte titre, 13px bold, padding 6×16. Une seule par vue, au-dessus du h1.
- **Avatar** (nouveau) — tailles 32/40/56/72/84 ; photo servie par miniature, repli initiales (fond teinte bleu, texte titre) ; anneau optionnel 2px couleur du cercle.
- **Champ** / **Liste** (nouveau) — libellé 13px bold au-dessus, champ 44px, rayon-m, bordure trait-fort, focus bordure bleue 1.5px + anneau.
- **Onglets** (nouveau) — soulignement bleu 3px animé ; onglet actif `aria-selected`, texte titre.
- **Progression** (nouveau) — piste `--fond-doux`, remplissage **aplat bleu** (pas de dégradé bleu→rose), hauteur 10px, `role="progressbar"` + `aria-valuenow`.
- **CaseACocher** (nouveau) — 20px, cochée = fond bleu + coche blanche.
- **CarteRetournable** (nouveau) — voir §6.3.

## 6. Écrans (motifs)

### 6.1 Cadre applicatif — `Cadre.tsx`, `NavigationPrincipale.tsx`
En-tête blanc collant 64px, bordure basse trait, `backdrop-filter: blur(10px)` sur blanc 88%. Logo bleu (22px) + nom d'entité en encre-douce à gauche, rubriques au centre, avatar à droite. Rubrique active : texte titre + soulignement bleu 3px, `aria-current="page"`. < 768px : barre inférieure, 5 entrées max, picto + libellé, cibles ≥ 44px.

### 6.2 Accueil entité — `PageEntite`
Section blanche rayon-xl : Pastille « Présentation de l'entité » → h1 « eXalt Bordeaux » → intro (encre-douce, max 760px). Grille 2 colonnes (auto-fit, min 320px) : à gauche bloc vidéo sur fond bleu foncé (lecture sur action, jamais auto-play) ; à droite 4 tuiles (teinte bleu, teinte jaune, gris, CTA « Vie eXalt » bordure bleue + picto `feu-d-artifice`, sans animation pulsée). Puis Framework, arrivées récentes, événements, liens.

### 6.3 Trombinoscope — `PageTrombinoscope`
Filtres en ligne (Recherche, Cercle, Statut) → compteur de résultats → grille `repeat(auto-fill, minmax(170px, 1fr))`, gap 14.
**CarteRetournable** (236px de haut) : `<button aria-pressed>`, perspective 900px, rotation Y 360ms.
- Recto : bandeau 150px teinte/surface du cercle avec avatar 84px, puis nom (titre bold 14), rôle (encre-douce 13), cercle (titre bold 12).
- Verso : aplat bleu foncé (au lieu du dégradé V1), nom, rôle, client en pastille jaune, statut en pastille blanche.
- Activation : clic, Entrée/Espace ; survol en option (réglage). Contenu du verso exposé dans l'`aria-label` pour les lecteurs d'écran. Conserver le comportement clavier actuel du dépôt.

### 6.4 Cercle — `PageCercle`
Accordéon (`aria-expanded`) : tuile picto du cercle 44px + nom + badge « N membres » + chevron. Ouvert : bloc de présentation sur surface du cercle, encart « Booster » (teinte rose, bordure rose 1.5px, avatar 56px anneau rose, badge Booster), puis liste des membres en pastilles (avatar 32 + nom + rôle).

### 6.5 Framework — `PageFramework`, `PageBureau`
Bloc Vision sur bleu foncé (picto `organigramme` blanc 40px) + grille de bureaux (cartes blanches : picto 32px, nom, nombre de membres).

### 6.6 Événements — `PageEvenements`
Onglets « À venir / Passés ». Ligne d'événement : carte bordure trait (survol bleu) avec pavé date 76px (à venir : jaune/titre ; passé : teinte bleu/titre ; annulé : gris/encre-douce + badge « Annulé »), titre, méta (encre-douce 13), description.

### 6.7 Mon onboarding — `PageMonOnboarding`
- Bandeau parcours bleu plein : picto `profil-valide`, « Parcours · En mission », bouton « Changer » contour blanc.
- Carte checklist : « x / n tâches » + pourcentage bleu 22px bold, Progression, sélecteur d'étapes en pastilles (Avant l'arrivée, Jour 1, Semaine 1, Mois 1 ; active = bleu plein). Lignes : CaseACocher + libellé + responsable. Terminée = fond teinte bleu + texte barré (**jamais vert**).
- Ligne réunion clé : titre, horaire, bouton « Caler dans Teams ».
- **Fiche d'arrivée** (aperçu, max 480px, rayon-xl) : en-tête bleu plein (pastille jaune statut·entité, date d'arrivée, avatar 76 anneau jaune, nom 24 bold, rôle) ; corps en tuiles (Cercle / Mission en teinte bleu, « Qui suis-je ? » en gris — sans liseré gauche —, « J'attends d'eXalt » teinte rose, « Fun fact » teinte jaune) ; pied : logo bleu 16px + « pulse, make, learn ».

## 7. États
- **Vide** : picto `loupe` 48px, titre, aide en encre-douce.
- **Chargement** : squelettes `--fond-doux`, `aria-busy="true"`, sans scintillement si mouvement réduit.
- **Erreur / info** : alerte avec titre + message, ton danger / info.

## 8. Écarts à consigner (docs/ décisions)
- Ombres retirées vs cahier §13.2 « ombres douces » / « dégradés bleu/rose » → charte flat appliquée.
- `--ok` / `--ko` hors charte, limités à la page de statut.
- Licence Century Gothic à valider.
