# Compte rendu — sous-étape `T10` du LOT 1

**Exécutée le :** 30 juillet 2026
**Objet :** design system minimal — jetons et composants de base — et contrat API partagé
**Story :** `MVP-L01-US007`, **`P1`**, issue [#8](https://github.com/Jonathan2433/ONBOARDING_DIGITAL/issues/8)
**Fondement :** cahier §13.1 à §13.4, §14, §18.7 ; backlog `MVP-L01-US007` ; `DEC-451`, `DEC-456`, `DEC-465`, `DEC-471`
**Décisions produites :** `DEC-491` à `DEC-493` · **Question ouverte :** `QO-115` · **Risque CLOS :** `ROAD-RSK-032`

---

## 1. Le critère, et ce qui le prouve

> « Les tokens, composants de base et génération/partage des contrats sont initialisés **sans
> dépendance visuelle arbitraire**. » — backlog, littéral

**Les quatre derniers mots sont tout le sujet**, et c'est le seul endroit du lot où la règle « ne
jamais inventer ce qui n'est pas décidé » était en jeu de façon aussi directe.

| Volet du critère | Preuve | Résultat |
|---|---|---|
| Tokens **initialisés** | couleurs, espacements, rayons, ombres, typographie, 5 largeurs de recette | 34 propriétés, source TS + projection CSS |
| **Sans dépendance visuelle arbitraire** | valeurs **relevées** du prototype qui les nomme, et **recalculées** contre WCAG 2.2 AA | 4 couleurs de marque, 12 couples de contraste vérifiés |
| Composants **de base** | `Bouton`, `Badge`, `Carte`, éprouvés par leur **contrat accessible** | 90 tests dans `packages/ui` |
| Contrat **généré et partagé** | manifeste unique lu par TypeScript **et** Python, `apps/web` le consomme | 5 tests, 3 témoins |

---

## 2. « Sans dépendance visuelle arbitraire » — comment le critère a été satisfait

### 2.1 Ce que le corpus fournit, mesuré avant d'écrire

| Source | Ce qu'elle donne |
|---|---|
| Cahier §13.1 | exige « la charte graphique » et « la police officielle » — **aucune des deux n'est dans le corpus**, et aucun fichier de design n'est versionné |
| Cahier §13.1 | « des couleurs de cercles propres à chaque entité » — **aucune valeur** |
| Cahier §13.2 | direction **qualitative** : cartes arrondies, ombres douces, **« dégradés bleu, rose et violet »** |
| Cahier §13.3 | **Radix UI prescrit**, et **12 familles** de composants |
| Cahier §13.4 | **cinq largeurs de recette**, littéralement |

**Mesure du 30/07/2026 : le cahier ne contient aucune couleur hexadécimale.** Zéro occurrence.

### 2.2 Le prototype nomme sa propre palette, et c'est ce qui rend la reprise défendable

Extraites de `docs/prototype/V1.html` **sans le lire en entier** — 1 903 lignes courtes examinées,
les 150 lignes de Base64 écartées, conformément au piège documenté :

```js
const EXALT_BLUE      = "#5853FF";
const EXALT_DARK_BLUE = "#2F2F9B";
const EXALT_PINK      = "#FF2C9B";
const EXALT_YELLOW    = "#FFDA3E";
```

**Ce ne sont pas des couleurs que j'ai déduites : le prototype les nomme.** Et elles corroborent
littéralement le « bleu, rose et violet » du §13.2 — **deux sources concordantes**. Arbitrage de
Jonathan du 30/07/2026, sur quatre options présentées.

**Aucune ligne de code du prototype n'est reprise.** Seules des valeurs de couleur, ce que le §13.2
désigne comme « l'intention du prototype ».

### 2.3 La mesure a CORRIGÉ le prototype, et c'est le résultat le plus utile

Contrastes WCAG 2.2 recalculés :

| Couleur | sur blanc | sur fond sombre | Ce que la mesure impose |
|---|---:|---:|---|
| `#5853FF` bleu | 5,13 | 3,46 | texte blanc |
| `#2F2F9B` bleu foncé | 10,50 | **1,69** | texte blanc ; **inutilisable en accent sur fond sombre** |
| `#FF2C9B` rose | 3,45 | 5,13 | **texte foncé obligatoire** |
| `#FFDA3E` jaune | **1,37** | 12,95 | **texte foncé obligatoire ; inutilisable en accent sur fond clair** |

**Le prototype n'avait vu le problème qu'à moitié.** Son `circleTextColors` ne corrige que le
jaune — « texte foncé sur fond jaune ». La mesure montre que **le rose et le vert de succès le
réclament aussi**. Le reprendre tel quel aurait reconduit deux défauts d'accessibilité.

**Conséquence de conception :** les couleurs de marque sont des **surfaces** portant chacune son
texte apparié mesuré, jamais des couleurs de texte libres. Et deux d'entre elles sont
**explicitement exclues** des accents, par thème — une exclusion que le contrôle vérifie, parce
qu'une absence est aussi un résultat de mesure.

### 2.4 Les neutres ne sont pas réinventés

`apps/web/src/styles.css` déclare depuis `T5` sept propriétés sémantiques — `--encre`,
`--encre-douce`, `--fond`, `--fond-doux`, `--trait`, `--ok`, `--ko` — en thème clair **et** sombre.
Mesure : **les huit couples atteignent AA**, de 6,57 à 17,40. Le design system les **reprend** sous
les mêmes noms. Les renommer aurait fait divorcer la page de statut de son propre design system.

---

## 3. Ce qui n'est PAS livré, et pourquoi

1. **Neuf des douze familles de composants du §13.3** — menus, modales, onglets, tableaux, alertes,
   carrousels, lecteurs vidéo, états vides et chargements. Le critère dit « initialisés » ; livrer un
   menu déroulant sans écran qui l'emploie serait du code non éprouvé. Elles arrivent au LOT 4.
2. **Radix UI n'est pas installé.** Le cahier §13.3 le prescrit pour les composants qui ont besoin de
   primitives accessibles — ceux du point 1. Les trois composants livrés partent du **HTML natif**,
   qui porte gratuitement rôle, activation clavier et état désactivé. Conséquence assumée :
   `DEP-018` reste libre, et **aucune dépendance externe nouvelle n'entre dans le projet** —
   vérifié sur le verrou, **284 paquets avant, 284 après**.
3. **Les huit couleurs de cercle.** Le prototype les déclare, indexées par nom de cercle : `Produit
   #5853FF`, `Design #FF2C9B`, `Projet #2F2F9B`, `Change #FFDA3E`, `Data #9B53FF`, `Shield #FF5398`,
   `Forge #53B4FF`, `IT #FF8C53`. **Un cercle est une notion métier du LOT 6**, et `ECART-014` montre
   que sa dénomination n'est même pas stabilisée. Les inscrire aurait anticipé le LOT 6 ; elles sont
   relevées **ici** pour que le LOT 6 les retrouve.
4. **La charte graphique et la police officielle.** `QO-115`. Le prototype référence explicitement
   « la charte EXALT » : **elle existe, nous ne l'avons pas.** La pile typographique est donc
   **système**, sans téléchargement ni CDN — ce que la roadmap §2.3 interdit par ailleurs.
5. **Le rendu visuel n'est pas testé.** `jsdom` n'applique aucune feuille de style. Le contraste est
   vérifié sur les **jetons**, la cohérence jetons/CSS par un contrôle de divergence, et le contrat
   accessible des composants par leur rôle et leur nom. Il faut le dire plutôt que de laisser croire
   que ces tests prouvent l'apparence.

---

## 4. Le contrat : pourquoi le sens de vérification est inversé

**« Génération » supposait une source à générer. Il n'y en avait pas.** Mesure du 30/07/2026 sur le
schéma OpenAPI réellement servi : `components.schemas` est **vide**. Les routes de santé rendent des
dictionnaires sans modèle de réponse déclaré. Générer depuis ce schéma aurait produit des types
`unknown`, donc **l'illusion d'un contrat typé**.

**Le sens retenu :** un manifeste JSON **déclare** le contrat — chemins, méthodes, codes
exploitables — et un contrôle Python vérifie que le schéma servi le **respecte**. Une route ajoutée,
retirée ou renommée sans mise à jour du manifeste fait échouer `make check`.

**Pourquoi JSON :** le contrat a deux consommateurs qui ne parlent pas la même langue. Un fichier
TypeScript serait illisible depuis Python, un fichier Python illisible depuis le navigateur. C'est le
motif de `DEC-466` — une seule source, pas deux copies qui divergent.

**Et le « partage », c'est le déplacement.** Les types étaient dans `apps/web/src/api/sante.ts`
depuis `T5`, où ils étaient justes — mais **pas partagés** : un second consommateur les aurait
recopiés. `apps/web` ne garde que le transport. **Les 25 tests de `T5` passent sans modification**,
ce qui est la preuve que le déplacement n'a rien changé au comportement.

**Un constat que ce contrôle a produit dès sa première exécution :** l'API ne documentait **pas** le
503 de `/health/ready` dans son schéma, alors que le frontend le traite comme un état **dégradé
exploitable** depuis `T5`. Un consommateur qui aurait engendré son client depuis ce schéma aurait
traité le diagnostic comme une erreur imprévue. La route le documente désormais.

---

## 5. Contrôles exécutés, et leurs témoins

### 5.1 Les contrôles livrés

| Contrôle | Ce qu'il fait | Peut-il échouer ? |
|---|---|---|
| Contraste des jetons | **recalcule** les 12 couples déclarés contre les seuils AA | oui — 3 témoins |
| Exclusions mesurées | vérifie l'**absence** des couples que la mesure interdit | oui |
| Divergence jetons/CSS | lit les deux fichiers, compare 34 + 7 variables | oui — 2 témoins |
| Composants | rôle, nom accessible, clavier, état, région nommée | oui |
| Feuille des composants | **aucune couleur en dur**, focus visible jamais annulé | oui |
| Contrat contre schéma | égalité des chemins **dans les deux sens**, codes documentés | oui — 3 témoins |

### 5.2 Témoins — 11, tous concluants

| Maillon | Défaut injecté | Résultat |
|---|---|---|
| Contraste, mauvais appariement | blanc sur le jaune | **échec**, « rend 1.37, seuil 4.5 » |
| Contraste, exclusion levée | jaune réintroduit en accent clair | **échec sur DEUX contrôles** |
| Largeurs de recette | une des cinq retirée | **échec** |
| Divergence, valeur changée | une couleur modifiée dans le CSS seul | **échec**, les deux valeurs nommées |
| Divergence, variable retirée | `--rayon-pastille` supprimée du CSS | **échec**, « 33 au lieu de 34 » |
| Formule de contraste | noir/blanc, identité, symétrie | 21, 1, égalité |
| Couleur mal formée | `#fff`, `rouge`, `5853FF` | **lève** au lieu de rendre `NaN` |
| Contrat, chemin fantôme | déclaré, non servi | **échec**, le chemin nommé |
| Contrat, chemin retiré | servi, non déclaré | **échec** sur le garde-fou de détecteur muet |
| Contrat, 503 retiré du schéma | `responses=` supprimé de la route | **échec**, « code 503 ABSENT du schéma » |
| **`jsx-a11y` sur `packages/ui`** | image sans `alt`, `div` cliquable, lien vide | **5 erreurs d'accessibilité détectées** |

**Le dernier mérite un mot :** `eslint-plugin-jsx-a11y` est le motif déterminant de `DEC-451`, et il
n'avait jamais examiné de fichier dans `packages/ui` — ce paquet n'avait aucun `.tsx`. Éprouvé, il
examine et il **sait échouer** là où vivent désormais les composants.

### 5.3 Non-régression

| Contrôle | Résultat |
|---|---|
`make check` | **code 0** — 144 pytest, 116 Vitest |
`icloud-verify` · `env-check` · `docs-check` · `images-check` | code 0 |
`make audit` | **code 0, zéro avis** — voir §6 |
Tests de `T5` | **25 sur 25**, sans modification, après déplacement du contrat |

**Compte de tests : 139 → 144 pytest, 27 → 116 Vitest.** Soit **260** au total, contre 166 à
l'entrée.

---

## 6. Un événement extérieur, et il n'est pas de `T10`

**En cours de sous-étape, `make audit` est passé de 1 avis toléré à 4 avis hauts.** Avant de rien
conclure, j'ai mesuré : un arbre de travail créé sur le commit d'**avant** `T10` rend **exactement
les mêmes 4 avis**. `pnpm audit` interroge la base d'avis en direct : ce sont donc des avis
**nouvellement publiés** sur des dépendances préexistantes, et **`T10` n'en introduit aucun** — le
verrou compte 284 paquets avant comme après.

**Conséquence à connaître : la CI était devenue rouge sur `develop`, indépendamment de `T10`.**

Les deux avis sont **corrigeables**, ce qui les met sous le coup de `DEC-474` :

| Avis | Paquet | Vulnérable | Corrigé par |
|---|---|---|---|
| `GHSA-2v37-7h3g-55p8` | `nanoid` | `<3.3.17` | `3.3.18` retenu |
| `GHSA-rgw5-rvv9-x895` | `brace-expansion` | `>=4.0.0 <5.0.9` | `5.0.9` retenu |

`pnpm update -r brace-expansion nanoid` suffit, **dans les plages déjà déclarées**, sans forcer
aucune version majeure. Mesuré après : lint, formatage, typage et les deux suites de tests restent à
zéro.

### 6.1 Et un effet de bord qui ferme un risque ouvert

**`brace-expansion` est passé de `1.1.16` à `1.1.18`, et cela corrige `GHSA-mh99-v99m-4gvg`** — le
seul avis que le projet tolérait, `DEC-474`.

`T6` avait mesuré, et à raison pour sa date, que « la dernière version publiée de la ligne 1.x EST
1.1.16 : il n'existe aucun correctif dans cette ligne », et que forcer la ligne 5 casserait ESLint.
**Ce qui n'existait pas existe maintenant.** Vérifié dans les deux sens : l'audit est vert **avec et
sans** la tolérance.

La tolérance est donc **retirée** — `DEC-493` — et **`ROAD-RSK-032` est clos**. Une tolérance qui ne
couvre plus rien n'est pas neutre : elle avalerait silencieusement une réapparition du même avis.

> **La leçon, et elle vaut pour tous les résiduels acceptés du projet :** un risque accepté parce
> qu'« aucun correctif n'existe » doit être **réévalué**, pas archivé. Ici l'écosystème a bougé en
> un jour. `ROAD-RSK-033` — les 23 avis sans correctif de `python:3.12-slim` — est dans exactement
> cette situation, et mérite le même réexamen avant le LOT 13.

---

## 7. Défauts détectés pendant `T10`

**Quatre défauts. Les quatre dans mon propre travail**, aucun dans le livrable.

| # | Défaut | Nature | Traitement |
|---:|---|---|---|
| `T10-1` | **Mon analyseur du CSS exigeait la valeur sur la MÊME ligne que le nom de la variable.** Trois déclarations de `jetons.css` s'étendent sur deux lignes — la pile de polices et les deux ombres — et le contrôle de divergence les signalait donc « absentes de `jetons.css` » | **Un échec qui pointe la mauvaise cause.** Le message accusait la feuille de style alors que le parseur était en cause. Même classe que `T6-4` et `T9-2` : un contrôle qui échoue pour une raison étrangère à ce qu'il mesure envoie chercher au mauvais endroit | Découpage par **déclaration** — sur `;` — et non par ligne, donc indifférent aux retours à la ligne. Une valeur CSS ne porte jamais de point-virgule ici, le découpage est donc exact |
| `T10-2` | **Mes deux contrôles qui LISENT les feuilles de style étaient MUETS.** Vitest neutralise les imports CSS par défaut : tout import d'une feuille rend une chaîne **vide**, y compris en `?raw`. Mesure : 45 tests en échec, « expected 0 to be greater than 20 » | **Le pire des deux cas : muet sans être absent.** Sans le compte confronté à un attendu, ces contrôles auraient **passé** sur une feuille vide et validé une palette qui ne s'affiche pas | `css: true` dans la configuration Vitest, et le motif documenté à l'endroit du réglage. **C'est le compte attendu qui a sauvé le contrôle**, pas la chance |
| `T10-3` | **Le DOM s'accumulait entre les tests de composant.** `getByRole('button')` échouait en « Found multiple elements » — 7 tests en échec. Le nettoyage automatique de Testing Library ne s'installe qu'avec `globals: true`, que nos deux configurations n'activent pas | **Échec d'échafaudage, pas de livrable.** Les composants étaient corrects | `afterEach(cleanup)` explicite, **comme `apps/web` le fait depuis `T5`** — j'ai repris la convention existante au lieu d'en inventer une |
| `T10-4` | **J'ai supposé des fixtures pytest qui n'existent pas** — `parametres_valides`, `monkeypatch_module` — au lieu de lire `conftest.py`. Et `creer_application()` sans argument a été refusée par les onze garde-fous du §20.3, ce qui est leur rôle | **Une supposition là où une lecture suffisait.** C'est la classe du §9.0 : vérifier avant de bâtir dessus | Conventions réelles reprises — `environnement_vierge` et `Parametres(**VARIABLES_MINIMALES)`, comme `test_sante.py` depuis `T3` |

### 7.1 Ce que ces quatre défauts enseignent

**`T10-2` est le plus instructif du lot pour ce qu'il dit des contrôles qui lisent des fichiers.**
Deux contrôles conçus pour attraper une divergence lisaient une chaîne **vide** et ne le savaient
pas. Ils n'étaient pas absents — ils étaient **muets**. Ce qui les a sauvés n'est pas la vigilance :
c'est la troisième proposition de la règle du lot, **compter et confronter le compte à un attendu**.
Sans le « 34 variables attendues », les 34 comparaisons individuelles auraient toutes porté sur
`undefined` et le contrôle aurait pu être lu comme concluant.

**`T10-1`, `T10-3` et `T10-4` partagent une propriété** : trois fois, l'échec venait de mon
échafaudage et non du livrable, et deux fois la réponse était **de lire ce que le dépôt fait déjà**
plutôt que d'inventer. `apps/web` avait le `afterEach(cleanup)` ; `test_sante.py` avait
l'assembleur de paramètres. Les chercher aurait coûté deux minutes.

---

## 8. Recommandations pour la suite

1. **`T11` — la porte `G1`.** Les sept critères sont désormais tous acquis sauf la validation de
   Jonathan. Vérifier les nombres **par les commandes de dérivation**, pas en les recopiant.
2. **`QO-115` est à instruire avant le LOT 4** : la charte graphique et la police officielle. Les
   jetons livrés sont défendables mais restent une approximation de la charte réelle.
3. **Les huit couleurs de cercle sont relevées au §3** pour que le LOT 6 les retrouve sans rouvrir
   le prototype.
4. **Radix UI reste à installer au LOT 4**, avec les composants qui en ont besoin. `DEP-018` est
   libre.
5. **`ROAD-RSK-033` mérite le réexamen que `ROAD-RSK-032` vient de recevoir** : un résiduel accepté
   faute de correctif n'est pas un dossier clos.
6. **`eslint-plugin-jsx-a11y` déclare ESLint ^3..^9 alors que nous exécutons ESLint 10.** Le greffon
   fonctionne — éprouvé deux fois par témoin négatif — mais cette plage de paires reste à surveiller.

---

## 9. État à la sortie de `T10`

| | |
|---|---|
| Sous-étape | **`T10` terminée.** Story `MVP-L01-US007` prête pour validation, issue `#8` **à refermer à la main** |
| Décisions | `DEC-491` à `DEC-493`. Prochaine libre : **`DEC-494`** |
| Écarts | Aucun nouveau. Prochain libre : `ECART-025` |
| Risques | **`ROAD-RSK-032` CLOS.** Prochain libre : `ROAD-RSK-035` |
| Questions | **`QO-115` ouverte** — charte et police. 34 ouvertes sur 39. Prochaine libre : **`QO-116`** |
| Dépendances | **Aucune ajoutée** — 284 paquets avant, 284 après. Prochaine libre : `DEP-018` |
| Tests | **260** — 144 pytest, 116 Vitest. C'était 166 à l'entrée |
| Audit | **zéro avis, zéro tolérance** — c'était 1 avis toléré |
| Cibles `Makefile` | **50** — inchangé |

### Les 7 critères de la porte `G1`

| | Critère | État |
|:--:|---|---|
| ☑ | Tous les services démarrent sur le Mac M5 | `T2`, `T6`, `T8`, machine réellement propre en `T9` |
| ☑ | Les images multiarchitectures sont construites | `T7`, natives sur les deux depuis `T8` |
| ☑ | Aucun secret réel n'est présent | vérifié automatiquement depuis `T6`. **`T10` n'a créé aucun secret** |
| ☑ | Une migration Alembic vide ou initiale s'exécute | `T3`, sur une base créée de zéro en `T9` |
| ☑ | Les logs possèdent un identifiant de corrélation | `T4`, **et le nom de l'en-tête est désormais partagé et vérifié** |
| ☑ | La CI bloque une erreur de lint, de test et de secret | `T6`, prouvé trois fois |
| ☐ | Jonathan valide le socle | **`T11`** |

**Les six critères techniques sont acquis, et les huit stories du lot sont livrées.** Il ne reste que
`T11` : contrôles de sortie, checklist remise à Jonathan, et le tag **`v0.1.0`** sur `main`
(`DEC-428`).
