# Fiche de chantier — Refonte visuelle du front

**Nature :** chantier transversal, **PAS un lot** de la roadmap — hors numérotation `LOT n`,
hors épic/stories du backlog. Demandé directement par Jonathan le 25/10/2026, à la fermeture
de `G10`.
**Ouvert par Jonathan le :** 25 octobre 2026
**État :** **VALIDÉ** — découpage et les deux questions ouvertes tranchées par Jonathan le
25/10/2026 (`DEC-672`). `S1` (fondations), `S2` (migration des onglets), `S3` (page nationale +
cadre applicatif), `S4` (page entité) et `S5` (Framework, cercle, bureau) **FAITES**.
**Sous-étape suivante :** `S6` — Trombinoscope et profil

> Comme pour un lot, le chantier se déroule une sous-étape à la fois (§6.1 de `CLAUDE.md`) :
> annoncer, exécuter UNE SEULE sous-étape, contrôler, rapporter, attendre la validation de
> Jonathan avant la suivante.

---

## 1. Constat qui déclenche ce chantier

**Mesuré le 25/10/2026, pas supposé.** Comparaison du prototype `docs/prototype/V1.html` (servi
localement, jamais versionné) et de l'application réelle (`https://app.onboarding.localhost`, à
travers Caddy en HTTPS) :

| | Prototype `V1.html` | Application réelle |
|---|---|---|
| Couleurs | dégradés bleu/rose/violet en bandeau | couleurs de marque **plates** uniquement, **aucun dégradé** dans les 1838 lignes d'`application.css` |
| Cartes | cartes arrondies colorées partout, carrousel photo par bureau | `Carte`/`Badge`/`Carrousel` existent (`packages/ui`) mais ne sont **PAS utilisés** sur `PageCercle.tsx`/`PageFramework.tsx` (Alerte seule) |
| Icônes/emoji | omniprésents (BDS 🧗, BDE 🎉, BDG 🎮…) | **zéro emoji** dans `apps/web/src/pages/*.tsx` ; `lucide-react` est une dépendance déjà posée (`DEC-591`, LOT 6 `T8`) mais peu exploitée |
| Portraits | ronds | **déjà ronds** (`border-radius: 50%`/`var(--rayon-pastille)`, trombinoscope et profil) — rien à faire ici |
| Ton | ludique, animations courtes | sobre, fonctionnel, aucune animation |

**Ce n'est pas un défaut de code, c'est un écart documenté par construction.** Le design system
(`packages/ui`, `DEC-491`, LOT 1 `T10`) a dérivé des couleurs et un contraste AA du prototype,
mais n'a jamais reçu de passe d'habillage visuel comparable au cahier §13.2 — chaque lot a livré
la **fonction**, jamais la **direction artistique** au-delà des jetons de base.

## 2. Ce que le cahier EXIGE réellement — §13.1 à §13.4, prévaut sur le prototype

Le prototype est une **référence d'intention** (règle n°4, §2 de `CLAUDE.md`), jamais la source
normative. La source normative est le cahier :

> **§13.1 Identité visuelle** — logo officiel, charte graphique, police officielle (si la licence
> web le permet), design identique pour toutes les entités, couleurs de cercles propres à chaque
> entité.
>
> **§13.2 Direction artistique** — « Le rendu reste proche de l'intention du prototype » : visuel,
> coloré, ludique, cartes arrondies, ombres douces, **dégradés bleu, rose et violet**, portraits
> ronds, badges, icônes/emojis/illustrations **maîtrisés**, animations courtes et **non
> essentielles**.
>
> **§13.3 Design system** — construit sur des primitives accessibles, **notamment Radix UI** ;
> couvre boutons, champs, cartes, badges, menus, modales, **onglets**, tableaux, alertes,
> carrousels, lecteurs vidéo, états vides et chargements.
>
> **§13.4 Responsive** — cinq largeurs de recette : 320, 390, 768, 1280, 1920 px et plus.

### 2.1 Radix UI — INCLUS, sur décision explicite de Jonathan du 25/10/2026

**`packages/ui` ne dépendait d'AUCUNE primitive Radix** (`package.json` : zéro dépendance) avant ce
chantier. Depuis le LOT 7 (`T14`), chaque composant à onglets a été **refabriqué à la main** (motif
WAI-ARIA `tablist`/`tab`/`tabpanel` recopié lot après lot : LOT 7 `T14`, LOT 8 `T9`, LOT 9 `T14`),
alors que le §13.3 nomme Radix explicitement.

**Périmètre retenu, pour rester dans la discipline du projet — jamais construire une primitive
sans consommateur réel (§7.27/§7.0 troisième proposition)** : Radix remplace ce que le dépôt
**réinvente déjà, plusieurs fois** —

- **`@radix-ui/react-tabs`** pour les **onglets** (§13.3) : deux consommateurs réels mesurés,
  `PageAdministration.tsx` (neuf onglets) et `PageEvenements.tsx` (deux onglets), chacun avec sa
  propre copie du motif ARIA. Un seul composant `Onglets` dans `packages/ui`, les deux écrans
  migrés, le motif fabriqué à la main retiré.

**Les autres primitives Radix (Dialog, DropdownMenu, Select, Tooltip…) ne sont PAS ajoutées dans
ce chantier**, faute de consommateur réel mesuré : `PanneauDuCycleDeVie.tsx` évite délibérément
une modale (confirmation en ligne, documenté dans son en-tête — `window.confirm` n'existe pas dans
`jsdom`), et `SelecteurDEntite.tsx` évite délibérément un menu/`<select>` (c'est une navigation,
pas un menu d'actions — un `onChange` y serait un piège d'accessibilité, documenté dans son
en-tête). Les ajouter maintenant construirait une primitive sans écran qui l'exige. Si un écran
futur en a besoin, la primitive Radix correspondante s'ajoute à ce moment-là, nommée explicitement
dans sa propre sous-étape.

## 3. Ce qui bloque, et qui N'EST PAS dans ce chantier

**`DEP-006` est OUVERTE** (« charte, logo et typographie officiels exploitables »), échéance
**LOT 14**. C'est elle qui explique pourquoi `CarteDeFrance.tsx` est un tracé approximatif fait à
la main (son propre en-tête le dit : « auteurer une illustration de marque appartient à `DEP-006`,
pas à ce lot »). Tant que `DEP-006` reste ouverte :

- **aucun logo officiel**, aucune police officielle, aucune illustration de marque définitive ;
- la carte de France reste le tracé provisoire actuel — le refaire maintenant serait un travail
  jeté le jour où `DEP-006` livre l'asset réel ;
- la couleur « violet » du §13.2 reste absente des jetons actuels (`DEC-491` a retenu
  bleu/bleu foncé/rose/jaune, pas violet). **Décision de Jonathan du 25/10/2026 : le dégradé reste
  bleu → rose uniquement**, aucune quatrième teinte ajoutée — cohérent avec le choix déjà fait par
  `DEC-491`, jamais rouvert.

**Ce chantier travaille donc avec ce qui est DÉJÀ décidé** : les jetons de couleur existants
(`--marque-bleu`, `--marque-bleu-fonce`, `--marque-rose`, `--marque-jaune`, tous mesurés AA),
`lucide-react` (déjà une dépendance), et les composants déjà construits (`Carte`, `Badge`,
`Carrousel`, `CarteRetournable`, `Alerte`, `Notification`, `Bouton`). **Une seule dépendance
nouvelle, nommée ici explicitement** : `@radix-ui/react-tabs` (§2.1, décision de Jonathan).
Aucune autre dépendance visuelle n'est ajoutée sans être nommée explicitement dans une sous-étape.

**Aucune photo ni image du prototype n'est reprise** — règle n°4, et le prototype contient de
toute façon des photos de personnes réelles non autorisées (`docs/prototype/README.md` §2). Tout
visuel ajouté est soit décoratif (formes, dégradés CSS, icônes `lucide-react`), soit une photo déjà
présente dans le pipeline média existant et son autorisation (LOT 5).

## 4. Périmètre proposé — écrans consommateurs, PAS le back-office

Le prototype ne modélise que le **portail de découverte** (carte nationale, page d'entité, cercles,
bureaux, trombinoscope) — il ne montre ni audit, ni RGPD, ni import CSV, ni back-office. Proposition
donc de restreindre ce chantier aux écrans que le prototype couvre réellement, et de laisser le
back-office (`PageAdministration.tsx` et ses sections) dans son habillage fonctionnel actuel, outil
interne où la densité d'information prime sur l'intention « ludique » du §13.2.

| Dans le périmètre | Hors périmètre |
|---|---|
| `PageNationale` (carte + liste), `CadreApplicatif`/`NavigationPrincipale`/`BarreMobile` | `PageAdministration` et ses huit sections |
| `PageEntite`, `PageFramework`, `PageCercle`, `PageBureau` | Écrans d'édition (`PageEdition*`, `PanneauEditionDeContenu`) — formulaires, pas de vitrine |
| `PageTrombinoscope`, `PageProfil` | `PageStatut` (page technique du LOT 1, volontairement neutre) |
| `PageEvenements`, `PageMonOnboarding` | `PagesErreur`/`PanneauDErreur` (déjà sobres par choix, cohérence à vérifier seulement) |
| `PageConnexion`/`PageLien*` (première impression) | |

**Exception structurelle au périmètre ci-dessus** : la migration des onglets vers
`@radix-ui/react-tabs` (§2.1) touche `PageAdministration.tsx`, bien que le back-office reste hors
périmètre pour l'habillage visuel (dégradés, cartes, icônes). C'est un changement **structurel et
d'accessibilité**, pas une passe de direction artistique — les deux ne sont pas liés.

## 5. Sous-étapes proposées — une à la fois, comme pour un lot

1. **Fondations. FAITE** (PR #297, fusionnée dans `develop` le 25/10/2026). Deux volets
   indépendants, un seul `packages/ui` touché :
   - jetons de dégradé dérivés des couleurs déjà validées
     (`--degrade-marque: linear-gradient(135deg, var(--marque-bleu), var(--marque-rose))`, bleu→rose
     uniquement — décision du 25/10/2026), contraste du texte sur dégradé remesuré (pas seulement
     sur une couleur plate, §7.0) — **une zone morte réelle trouvée et prouvée** : à t≈0,75 du
     dégradé, ni le blanc ni un texte sombre n'atteignent AA 4.5 simultanément, d'où la règle
     « ce dégradé est décoratif seul, jamais de texte directement dessus » ;
   - `@radix-ui/react-tabs` posée comme dépendance, nouveau composant `Onglets` dans `packages/ui`
     construit dessus, ses propres tests ; **aucun écran migré à cette étape**, seulement la
     primitive et sa preuve isolée — non exportée du paquet avant `S2` (`make cadre-check`, LOT 1
     `T11`, exige qu'un composant exposé soit employé par un écran).
2. **Migration des onglets existants. FAITE** (25/10/2026). `PageAdministration.tsx` et
   `PageEvenements.tsx` basculent sur `Onglets` ; le motif ARIA fabriqué à la main (neuf `<button>`
   plus deux, chacun sa propre copie `tablist`/`tab`/`tabpanel`) est retiré des deux fichiers,
   remplacé par la primitive de `S1` — gain réel, pas seulement structurel : la navigation au
   clavier (`ArrowLeft`/`ArrowRight`) qu'aucune des deux copies manuelles ne rendait est désormais
   fournie par Radix, en mode `activationMode="manual"` (aucun appel réseau déclenché en parcourant
   les onglets à la flèche). `Onglets` est désormais exporté par `packages/ui/src/index.ts`,
   `make cadre-check` le confirme « testé et employé ». Treize tests existants mis à jour
   (`fireEvent.click` → `fireEvent.mouseDown` sur l'activation d'un onglet — Radix active sur
   `onMouseDown`, mesuré en `S1`) ; zéro test nouveau, zéro régression de comportement : même
   contenu, mêmes règles de visibilité par rôle. Sous-étape structurelle, aucun habillage visuel
   nouveau — les deux écrans gardent leurs classes CSS propres (`evenements-panneau`, etc.) comme
   conteneurs de LAYOUT à l'intérieur du panneau que `Onglets` fournit.
3. **Page nationale + cadre applicatif. FAITE** (26/10/2026). Trois volets, aucune migration,
   aucune route nouvelle :
   - **Bandeau d'accueil (dégradé).** `PageNationale.tsx` seule — nouvelle classe `.nat-bandeau`,
     PROPRE à cette page et non `.app-entete` : ce dernier est le bandeau FONCTIONNEL du cadre
     applicatif, partagé par CHAQUE page interne une fois une entité choisie (nom, ville,
     sélecteur) — y poser un dégradé colorerait de facto l'en-tête de tous les écrans dont
     l'habillage visuel n'est pas dû avant `S4`-`S7`. Le texte (« eXalt Onboarding ») vit dans une
     pastille OPAQUE (`.nat-bandeau-pastille`, `--rayon-pastille`) posée sur le dégradé, jamais à
     même lui — `DEGRADE_MARQUE` (`packages/ui/jetons.ts`, `S1`) le dit explicitement : aucune
     couleur de texte n'atteint AA sur toute l'étendue du dégradé, une vraie zone morte existant
     vers t=0,75. Vérifié dans un vrai navigateur, HTTPS, 320/375/1024 px.
   - **Carte de France.** `CarteDeFrance.tsx` **non touchée**, conformément à `DEP-006` (§3) :
     aucune ligne modifiée.
   - **Navigation et barre mobile avec icônes `lucide-react`.** Nouveau module partagé
     `apps/web/src/iconesDeRubrique.tsx` (`IconeDeRubrique`), UNE SEULE source pour
     `NavigationPrincipale.tsx` ET `BarreMobile.tsx` — deux correspondances écrites séparément
     divergeraient au premier ajout (§7.27 de la passation, déjà la raison de l'extraction de
     `rubriqueEstVisible` dans `routes.ts` au LOT 4 `T9`). Six icônes statiques (`Home`, `Network`,
     `Users`, `Calendar`, `ClipboardCheck`, `Settings`), importées par leur nom depuis `lucide-react`
     — pas `lucide-react/dynamic`, réservé à un champ texte libre (`icones.tsx`, LOT 6 `T10`) : les
     six rubriques sont une liste FERMÉE connue à la compilation. Toutes `aria-hidden` : le libellé
     texte porte déjà l'information, l'icône la rappelle seulement à l'œil (§13.2, « icônes
     maîtrisées »). **Menu principal** : icône à côté du libellé (`display: inline-flex`, espace
     horizontal disponible, `overflow-x: auto` déjà en place). **Barre mobile** : icône AU-DESSUS du
     libellé (`flex-direction: column`), jamais à côté — la mesure du 23/08/2026 (`T5` du LOT 4)
     calait QUATRE cellules à 320 px en LARGEUR, et elle reste valide : empiler consomme de la
     HAUTEUR, que `min-height` laisse déjà croître pour « Trombinoscope » sur deux lignes, jamais la
     largeur du texte. **Panneau « Plus »** : icône à côté du libellé pour les rubriques
     secondaires, et un `MoreHorizontal` ajouté sur le bouton « Plus » lui-même (pas une rubrique de
     `RUBRIQUES`, donc pas `IconeDeRubrique`). Une seule règle de taille partagée,
     `.app-rubrique-icone` (`color: currentColor` — lucide-react pose `stroke="currentColor"` par
     défaut, donc l'icône suit la couleur du lien dans tous ses états sans règle de couleur
     supplémentaire). Vérifié dans un vrai navigateur à 320, 375 et 1024 px : aucun débordement,
     aucune troisième ligne de libellé.

   **Zéro régression** : les 313 tests Vitest du frontend passent (+7 nouveaux, décoratif de
   l'icône et de la pastille prouvé explicitement — un `<svg aria-hidden="true">` par lien,
   `textContent` inchangé). `make cadre-check` (25 contrôles), `make icloud-verify` et
   `uv run mypy`/`tsc --noEmit`/ESLint/Prettier verts. `make check` complet buté sur 78 échecs
   **environnementaux** `pytest` (jeu de démonstration du LOT 2 chargé sur cette machine, CLAUDE.md
   §11, aucun rapport avec ce travail — exclusivement frontend, zéro fichier Python touché, `make
   code-check` confirme les 166 fichiers de l'API identiques au dépôt). Aller-retour réel effectué
   après `make code-refresh`/`make apercu` : lien magique administrateur réel, page nationale et une
   entité consultées à travers Caddy en HTTPS, bandeau et icônes vus à 320/375/1024 px, décor
   nettoyé par `make apercu-fin`.

   **Un nettoyage non lié à ce travail, fait en chemin** : 137 copies de conflit iCloud (classe
   `ROAD-RSK-026`/`ECART-038`, §7.1/§7.34 de la passation), toutes git-ignorées et vérifiées
   byte-identiques à leur original avant suppression (`make icloud-verify` l'a confirmé dans les
   deux sens). Une seule, `packages/ui/src/index.ts`, était un FICHIER SUIVI reverté localement à
   son état `S1` (avant l'export d'`Onglets` par `S2`) — restaurée par `git checkout` avant de
   commencer `S3`.
4. **Page entité. FAITE** (26/10/2026). `apps/web/src/pages/PageEntite.tsx` — **mesuré AVANT tout
   code** : `Carte` couvrait déjà les cinq sections (posé par le LOT 8 `T11`) et `Carrousel` portait
   déjà les trois listes (LOT 8 `T12`) — ni l'un ni l'autre n'était donc à construire, contrairement
   à ce que la ligne ci-dessus laissait entendre avant vérification (§7.29 de la passation : chercher
   avant de bâtir). **Seul manquait « badges pour les compteurs »**, cahier §13.2 : les trois blocs
   d'INFORMATION (Framework, Arrivées récentes, Événements à venir — par opposition à Présentation et
   Ressources internes, des blocs de CONTENU) portent désormais leurs compteurs en `Badge` plutôt
   qu'en phrase prose. Framework : trois `Badge` (`N cercle(s)`, `N bureau(x)`, `N responsabilité(s)
   pourvue(s)`), toujours affichés, même à zéro — remplace l'unique phrase `.accueil-framework-resume`.
   Arrivées récentes et Événements à venir : un `Badge` reflétant le `total` de la pagination (pas la
   longueur de la page affichée, plafonnée à `NOMBRE_MONTRE`), affiché seulement aux côtés du
   carrousel — l'état vide garde sa seule `Alerte`, un badge « 0 » à côté aurait été redondant.
   `Carte de France` hors périmètre de cette sous-étape (`PageCercle.tsx`/`PageBureau.tsx`, `S5`).
   **Zéro régression** : 318 tests Vitest du frontend (+7, décoratif prouvé : chaque compteur est un
   vrai `.ex-badge`, le Framework reflète les listes réelles et non une phrase recopiée, le badge
   d'arrivées/événements suit le `total` et non la page affichée, et disparaît avec la section vide).
   `make cadre-check` (25 contrôles), `make icloud-verify`, `uv run mypy`/`tsc --noEmit`/ESLint/
   Prettier verts.
5. **Framework, cercle, bureau. FAITE** (26/10/2026). Trois fichiers, `PageFramework.tsx`,
   `PageCercle.tsx`, `PageBureau.tsx` — **mesuré avant tout code** : `Carte` et `Badge` n'étaient
   employés dans AUCUN des trois ; `PageBureau.tsx` faisait exception partielle, `Badge` y servait
   déjà l'état publié/brouillon depuis `T9` du LOT 6, seul `Carte` manquait.
   - **`PageFramework.tsx`** : les trois sections (Responsabilités, Cercles, Bureaux) deviennent
     des `<Carte titre="…">` — la région nommée et le `<h2>` que `Carte` fournit déjà remplacent le
     `<section aria-labelledby>`/`<h2 id>` écrits à la main. Les deux compteurs de prose (membres
     actifs d'un cercle, responsables d'un bureau) deviennent des `Badge`.
   - **`PageCercle.tsx`** : deux `Carte` (identité, membres) remplacent l'`<article>`/`<dl>`/`<ul>`
     écrits à la main ; le type d'appartenance (« Principal »/« Secondaire ») devient un `Badge`.
   - **`PageBureau.tsx`** : deux `Carte` (identité, responsables) remplacent l'`<article>`/
     `<header>` ; le `Badge` d'état existant est conservé tel quel.
   - **Icône de bureau** (`Building2`, `lucide-react`, décorative — `aria-hidden`) : un cercle
     garde sa bordure de couleur comme marque visuelle distinctive (déjà posée au LOT 6), un
     bureau n'en avait AUCUNE — l'icône rejoint le badge d'état, dans `PageFramework.tsx` (carte de
     la liste) et `PageBureau.tsx` (en-tête). Aucune icône PAR TYPE de bureau (BDS/BDE/BDG…) :
     `test_bureaux.py` l'affirme déjà, « entièrement configurables », donc un type n'est fermé
     nulle part — une icône générique marque la ressource, jamais une seconde source d'information
     sur un champ texte libre (§13.2, « icônes maîtrisées »).
   - **Défaut latent trouvé en mesurant, corrigé au passage, hors du périmètre demandé mais
     directement sur le fichier touché** : `Carte` n'accepte aucune `className`
     (`ProprietesCarte`, `packages/ui`), donc la variable de couleur `--cercle-couleur` ne peut
     plus vivre sur la carte elle-même — elle revient sur un conteneur dédié,
     `.cercle-identite`, qui la déclare ET la consomme, comme `.framework-carte-cercle`.
     **L'ancienne règle (`.cercle-entete`) déclarait déjà `--cercle-couleur`, mais sur un élément
     DIFFÉRENT de celui qui recevait le style en ligne** (le `<header>` enfant, quand l'inline
     visait l'`<article>` parent) : une règle qui cible un élément gagne toujours sur un style posé
     EN LIGNE par un ANCÊTRE pour la même propriété — la bordure colorée d'un cercle ne pouvait
     donc JAMAIS s'afficher, et aucun test ne l'éprouvait. Vérifié réellement : la bordure se
     colore désormais (bleu/rose/jaune selon le jeton) sur la page Framework ET sur la page de
     détail du cercle.
   **Zéro régression** : 326 tests Vitest du frontend (+8, dont un témoin dédié au défaut corrigé —
   la propriété `--cercle-couleur` est désormais lue avec une valeur non vide quand un jeton
   résout). `make cadre-check` (25 contrôles, qui a d'abord ÉCHOUÉ une fois sur une variable
   utilisée sans être déclarée par aucune feuille chargée — corrigé en déclarant
   `--cercle-couleur` sur `.cercle-identite`, exactement le motif que le contrôle exige pour
   `--framework-cercle-couleur`), `make icloud-verify`, `uv run mypy`/`tsc --noEmit`/ESLint/
   Prettier verts. Aller-retour réel effectué après `make code-refresh`/`make apercu` : Framework,
   un cercle et un bureau de l'entité de démonstration vus à travers Caddy en HTTPS, bordures
   colorées et icône de bureau confirmées à l'écran, décor nettoyé par `make apercu-fin`.
6. **Trombinoscope et profil.** Cartes, badges de statut/cercle, vérifier que `CarteRetournable`
   est le bon véhicule pour la richesse voulue.
7. **Événements et mon onboarding.** Cohérence avec les carrousels déjà posés au LOT 8.
8. **Recette visuelle.** Les cinq largeurs du §13.4 (320/390/768/1280/1920), contraste AA sur
   chaque nouvelle combinaison couleur/dégradé, `make ecrans-check`/`make web-check` rejoués,
   capture avant/après par écran.

Chaque sous-étape suit la boucle habituelle : annoncer, exécuter, contrôler (`make test-frontend`,
`make ecrans-check`, contraste), rapporter, attendre ta validation avant la suivante.

## 6. Questions tranchées par Jonathan le 25/10/2026

- **Le violet du §13.2** : **dégradé bleu → rose uniquement**, aucune quatrième teinte ajoutée.
- **Radix UI (§13.3)** : **inclus**, borné à `@radix-ui/react-tabs` pour les onglets (§2.1) — les
  autres primitives Radix restent hors périmètre faute de consommateur réel.
- **Ordre des sous-étapes** : aucune objection reçue — l'ordre du §5 est retenu (fondations →
  onglets → national → entité → cercles/bureaux → trombinoscope/profil → onboarding → recette).

## 7. Critères de sortie

1. Les cinq éléments du §13.2 absents aujourd'hui (dégradés, badges étendus, icônes maîtrisées,
   cartes généralisées, animations courtes) sont présents sur les écrans du périmètre §4.
2. **TENU (`S2`, 25/10/2026).** `PageAdministration.tsx`/`PageEvenements.tsx` consomment `Onglets`
   (`@radix-ui/react-tabs`), aucun motif ARIA fabriqué à la main ne subsiste pour les onglets.
3. Aucune régression de contraste AA (mesuré, pas supposé — `jetons.test.ts` étendu).
4. Aucune nouvelle dépendance visuelle au-delà de `@radix-ui/react-tabs`, nommée ici.
5. Les cinq largeurs de recette du §13.4 sont vérifiées sans débordement.
6. `DEP-006` reste intacte : aucun logo ni illustration de marque inventés à sa place.
