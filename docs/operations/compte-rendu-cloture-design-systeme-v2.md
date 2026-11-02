# Clôture du chantier Design System v2 — `E6` et `E7`

**Date :** 2 novembre 2026  
**Décisions :** `DEC-682` (fondations et réalisation `E1` à `E5`) · `DEC-684`
(nettoyage et décisions `E6`/`E7`)  
**État :** **chantier clos**

---

## 1. Réconciliation préalable

L’identifiant `DEC-681` avait été attribué deux fois : d’abord à la recette `T7` du LOT 11,
puis à l’ouverture du chantier Design System v2. La chronologie fait foi :

- `DEC-681` reste la décision de `T7` du LOT 11 ;
- le chantier Design System v2, `E1` à `E5`, est réindexé en `DEC-682` ;
- la validation de `G11` est `DEC-683` ;
- la présente clôture groupée de `E6` et `E7` est `DEC-684`.

Le prochain identifiant libre est `DEC-685`. Aucun comportement applicatif ne dépend de ces
identifiants ; la correction porte sur la traçabilité documentaire et les références du code.

## 2. Ce que le chantier a livré

| Étape | Résultat |
|---|---|
| `E1` | Century Gothic auto-hébergée, palette et jetons v2, contrastes mesurés, thème sombre explicite, retrait des ombres et dégradés |
| `E2` | Générateur et catalogue local de pictogrammes officiels, composant `Picto`, contrôles de divergence et d’accessibilité |
| `E3` | Composants de la charte : boutons, badges, cartes, pastilles, avatars, champs, listes, progression et cases à cocher |
| `E4` | Table typée des huit cercles avec surface, texte et pictogramme dérivés des données |
| `E5` | Adoption des composants et pictogrammes par les écrans, sans dupliquer les composants existants |
| `E6` | Retrait des résidus historiques, traduction sémantique des badges et unification structurelle du focus |
| `E7` | Arbitrages finaux, écarts documentés et fermeture du chantier |

## 3. `E6` — nettoyage réellement effectué

### Badges

`TonBadge` ne porte plus que les six significations de la charte : `mission`,
`intercontrat`, `enrichissement`, `booster`, `annule` et `info`. Les quatre anciens tons
`neutre`, `ok`, `ko` et `marque` sont supprimés du type, des styles et des tests. Tous les
consommateurs ont été traduits selon leur sens :

- états génériques et compteurs → `info` ;
- annulation et archivage → `annule` ;
- tâche obligatoire → `enrichissement` ;
- responsabilité Booster → `booster` ;
- situation professionnelle → `mission` ou `intercontrat`, avec `info` comme repli explicite.

La vérification finale ne trouve aucune utilisation d’un ton supprimé.

### Focus

Les **20** règles `:focus-visible` qui portaient encore un `outline` écrit localement dans les
feuilles de l’application consomment désormais `var(--anneau-focus)`. Les deux règles historiques
du trombinoscope ont disparu avec les classes mortes `.trombi-critere` et `.trombi-champ`.

Le contrôle `verifier-ecrans.py` dérive les feuilles CSS des écrans et refuse dorénavant toute
règle de focus qui définit un `outline` sans le jeton commun. Le contrôle porte sur la propriété
rendue, pas sur une liste maintenue à la main.

### Cibles tactiles

La contradiction interne de la charte est fermée : sa taille de bouton `s` à 36 px contredisait
sa règle transversale de cible tactile d’au moins 44 px. Les tailles `s` et `m` ont désormais une
hauteur minimale de 44 px ; `s` reste compacte par son padding horizontal.

## 4. `E7` — décisions finales

1. **La charte visuelle v2 prévaut pour la forme.** L’interface reste plate, sans ombre ni
   dégradé, et les portraits restent ronds. Cet arbitrage remplace les choix du chantier visuel
   précédent lorsque les deux se contredisent.
2. **L’accessibilité prévaut sur une valeur isolée de la charte.** L’anneau de focus reste opaque
   et thématique, les champs gardent une frontière mesurée, les boutons ont une cible de 44 px et
   les cartes utilisent 24 px (`--espace-l`) plutôt que le padding isolé de 22 px.
3. **Le thème reste un choix explicite.** `data-theme` et la préférence mémorisée sont conservés ;
   un retour au seul `prefers-color-scheme` réintroduirait l’impossibilité de revenir au clair.
4. **Les couleurs de cercle sont des couples indissociables.** Une surface qui ne bascule pas
   porte un texte littéral qui ne bascule pas. Cette règle évite les six échecs de contraste
   mesurés dans la charte remise.
5. **`--ok` et `--ko` restent des couleurs sémantiques bornées.** Elles servent à la page de
   statut et aux retours fonctionnels explicites de succès ou d’erreur (`Alerte`, `Notification`,
   validation de champ). Le texte et le rôle portent toujours le sens ; la couleur n’est jamais
   l’unique information. Cette décision élargit explicitement la formulation initiale « page de
   statut uniquement », qui était incompatible avec les retours d’erreur accessibles existants.
6. **Les six tons de `Badge` expriment le métier.** Un badge n’est plus un raccourci générique
   « vert/rouge/bleu » ; son nom décrit ce qu’il signifie.

## 5. Ce qui reste volontairement hors du chantier

Ces points ne bloquent pas la clôture parce qu’ils demandent une décision produit, un contenu ou
une dépendance externe :

- confirmation de la licence de diffusion web de Century Gothic avant la production ;
- vidéo d’accueil, bloc Vision et contenus encore signalés comme provisoires ;
- action Teams actuellement inerte ;
- seuils métier des phases du parcours d’onboarding ;
- filtre Cercle du trombinoscope et contenu « J’attends d’eXalt » ;
- remplacement des pictogrammes libres restants de `lucide-react`, seulement lorsqu’un équivalent
  officiel existe dans le catalogue eXalt.

Ces éléments restent visibles dans les registres de dépendances, de questions ou dans les lots
fonctionnels concernés. Ils ne justifient pas de maintenir `E6` ou `E7` ouverts.

## 6. Contrôles de clôture

Les contrôles exécutés sur l'arbre final donnent :

- formatage, Ruff, ESLint, mypy strict et TypeScript strict : **verts** ;
- documentation : **5** documents immuables intacts, **267** décisions cohérentes, prochain
  identifiant `DEC-685` ;
- tests Python sans dépendance externe : **493/493** ;
- frontend : **1 204/1 204** — 478 contrats, 346 UI, 380 web ;
- contrôle des écrans à travers Caddy : **10/10**, dont **27** règles de focus consommant toutes
  `var(--anneau-focus)` ;
- suite Python complète sur la base locale de démonstration : **2 010 réussites, 82 échecs
  environnementaux**. Les échecs sont les assertions historiques qui supposent des tables vides
  et trouvent le jeu de démonstration (par exemple 5 213 appartenances) ; aucune ne concerne le
  code frontend ou documentaire de `E6`/`E7`. Le jeu n'a pas été détruit pour maquiller ce résultat.

La traçabilité GitHub est elle aussi réconciliée : les jalons `G0` à `G11` sont fermés ; les
reliquats des LOTS 5, 6, 8 et 10 sont clos avec leur preuve ; `#211` reste seule ouverte, hors
jalon, classée V1/frontend/P1. Aucun test n'est neutralisé pour faire passer cette clôture.
