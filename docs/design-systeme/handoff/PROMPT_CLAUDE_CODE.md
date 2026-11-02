Tu travailles sur le dépôt ONBOARDING_DIGITAL (monorepo : `packages/ui` + `apps/web`).

Objectif : appliquer le nouveau design système eXalt à tout le front, en t'inspirant de la structure du prototype V1 mais **sans réutiliser son code**.

Fichiers fournis dans `docs/design-systeme/` :
- `DESIGN_SYSTEME.md` — la spécification complète (source de vérité, à lire en entier avant de coder).
- `jetons.css` — la proposition de jetons v2.
- `polices/` — Century Gothic Regular + Bold.
- `marque/` — logos eXalt bleu et blanc.
- `pictos/exalt-icons.json` — pictogrammes officiels `{clé: {name, viewBox, path}}`.
- `reference.png` (si présent) — capture de la page design système.

Procède par étapes, une PR (ou un commit) par étape, en lançant lint, typecheck et tests à chaque fois :

1. **Fondations** — copie les polices dans `packages/ui/polices/` avec deux `@font-face` (400, 700, `font-display: swap`). Mets à jour `jetons.ts` (source de vérité) puis `jetons.css` selon `jetons.css` fourni, en conservant les noms existants. Ajoute les nouvelles paires surface/texte aux tests de contraste (AA 4,5:1). Passe `--ombre-douce` et `--ombre-posee` à `none` et remplace leurs usages par des bordures.
2. **Pictos** — crée un composant `Picto` dans `packages/ui` qui rend uniquement les clés utilisées (cf. §4 et §6 de la spec), extraites du JSON en SVG local, en `currentColor`.
3. **Composants** — étends `Bouton`, `Badge`, `Carte` et ajoute `Pastille`, `Avatar`, `Champ`, `Liste`, `Onglets`, `Progression`, `CaseACocher`, `CarteRetournable` selon §5. Exporte-les depuis `index.ts`. Chaque composant doit avoir un test d'accessibilité (rôle, focus, clavier).
4. **Données** — crée la table `CERCLES` (§4) côté données ; aucun hex en dur dans les écrans.
5. **Écrans** — applique les motifs §6 dans cet ordre : Cadre/Navigation, Accueil entité, Trombinoscope, Cercle, Framework, Événements, Mon onboarding. Garde les routes, la logique et les appels API existants ; ne change que la présentation.
6. **Nettoyage** — supprime toute couleur V1 listée en §2, tout `linear-gradient`, toute `box-shadow`, tout emoji. Vérifie `prefers-reduced-motion` et le thème sombre.
7. **Décisions** — consigne les écarts de §8 dans la doc de décisions du dépôt.

Règles :
- Pas de nouvelle dépendance, pas de CDN.
- Vouvoiement dans tous les textes.
- Chaque information portée par une couleur l'est aussi par un libellé.
- En cas de conflit entre la spec et le code existant, demande-moi avant de trancher.

Commence par lire `DESIGN_SYSTEME.md`, `packages/ui/README.md`, `packages/ui/src/jetons.ts` et `apps/web/src/routes.ts`, puis propose-moi un plan détaillé de l'étape 1 avant de modifier quoi que ce soit.
