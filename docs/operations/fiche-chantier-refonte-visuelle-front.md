# Fiche de chantier — Refonte visuelle du front

**Nature :** chantier transversal, **PAS un lot** de la roadmap — hors numérotation `LOT n`,
hors épic/stories du backlog. Demandé directement par Jonathan le 25/10/2026, à la fermeture
de `G10`.
**Ouvert par Jonathan le :** 25 octobre 2026
**État :** **REPRIS le 27/10/2026 (`DEC-673`)**, après que `S1`-`S8` ont été déclarées
techniquement complètes puis confrontées par Jonathan à des captures d'écran réelles (voir §8).
`S1` (fondations), `S2` (migration des onglets), `S3` (page nationale + cadre applicatif), `S4`
(page entité), `S5` (Framework, cercle, bureau), `S6` (trombinoscope et profil), `S7` (événements
et mon onboarding), `S8` (recette visuelle finale), **`S9` (bascule clair/sombre)** et **`S10`
(trombinoscope/profil « pop ») FAITES**.
`S11` à `S14` restent à faire (§8.2). Les six critères de sortie du §7 restent tenus pour le
périmètre `S1`-`S8` ; la reprise porte ses propres critères, au §8.3.

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
6. **Trombinoscope et profil. FAITE** (27/10/2026). Deux fichiers, `PageTrombinoscope.tsx` et
   `PageProfil.tsx` (plus `PanneauDuCycleDeVie.tsx`, partagé par le second) — **mesuré avant tout
   code** : le trombinoscope employait déjà `CarteRetournable` (LOT 5 `T10`) pour chaque
   collaborateur, et le statut de l'en-tête du profil ainsi que le type de responsabilité portaient
   déjà un `Badge` (LOT 5 `T11`) ; aucun des deux écrans n'employait `Carte`, et le type
   d'appartenance d'un cercle (« Principal »/« Secondaire ») sur le profil restait un `<span>` de
   texte simple, exact pendant de ce que `S5` avait déjà corrigé sur `PageCercle.tsx` pour la même
   notion.
   - **`PageTrombinoscope.tsx`** : le statut du verso devient un `Badge` — il rejoint celui de la
     fiche profil, les deux écrans disant désormais la même chose de la même façon. Aucune `Carte`
     n'y est introduite : la grille de collaborateurs reste une liste de `CarteRetournable`, comme
     `PageFramework.tsx` garde ses propres cartes de liste (`Link`) hors `Carte` à `S5`.
   - **`PageProfil.tsx`** : l'identité (avatar, métier, statut) et les cinq blocs (Informations
     professionnelles, Cercles, Responsabilités Framework, Présentation, Historique
     organisationnel) deviennent des `Carte` — remplaçant le `<header>`/`<section
     className="profil-bloc">` écrits à la main. Le type d'appartenance d'un cercle devient un
     `Badge` (`ton="marque"` pour Principal, `ton="neutre"` pour Secondaire — même convention que
     `S5`). `PanneauDuCycleDeVie.tsx`, qui partageait `.profil-bloc` par un commentaire explicite,
     devient lui aussi une `Carte` — sinon la dernière section de la page serait restée seule dans
     l'ancien habillage.
   - **Le niveau de titre est explicite, pas le défaut.** L'identité garde `h2` (titre du
     document), les cinq blocs et le panneau de cycle de vie passent `niveauTitre="h3"` : ils
     étaient déjà des `<h3>` SOUS ce `h2`, et laisser `Carte` imposer son défaut aurait **aplati**
     une hiérarchie correcte en sept `h2` frères — exactement le cas que `niveauTitre` existe pour
     couvrir, documenté dans l'en-tête même de `Carte` (« une carte imbriquée dans une section plus
     profonde »). `PageCercle.tsx`/`PageFramework.tsx` (`S5`) n'avaient pas ce problème : leurs
     sections étaient déjà des `h2` frères avant la migration.
   - **Vérification demandée par la fiche : `CarteRetournable` reste le bon véhicule.**
     Documenté dans l'en-tête de `PageTrombinoscope.tsx` et prouvé par un test dédié : `Carte`
     n'accepte ni `className` ni `style` (`ProprietesCarte` les exclut explicitement) — elle ne
     pourrait pas porter `--carte-cercle` (§10.1) et n'offre aucun recto/verso, la richesse que le
     critère de `MVP-L05-US003` exige. `CarteRetournable` fournit déjà les deux sur un `<button>`
     natif (la propriété STRUCTURELLE du §7.35 de la passation) : c'est le bon véhicule, et rien du
     §13.2 ne s'ajoute à une carte dont le contenu est déjà une photo et un nom.
   - **Deux classes CSS devenues mortes, retirées plutôt que laissées traîner** : `.profil-entete`
     et `.profil-bloc`/`.profil-bloc h3` (remplacées par `.ex-carte`/`.ex-carte__titre`, qui
     ajoutent au passage l'ombre douce du cahier §13.2 que `.profil-bloc` n'avait jamais portée) ;
     `.profil-cercle-role` (remplacée par le `Badge`). `.profil-identite` (nouvelle) ne garde que la
     mise en page interne — avatar à côté du bloc métier/statut — que `Carte` ne connaît pas.
     `.profil-cercle` passe de `align-items: baseline` à `center`, même motif que
     `.cercle-liste-membres li` à `S5` : le second enfant est désormais un `Badge`, pas du texte
     dont la ligne de base s'alignerait.
   **Zéro régression** : 331 tests Vitest du frontend (+5 : deux au trombinoscope — le `Badge` de
   statut, la vérification du véhicule — et trois au profil — les six régions nommées, le `Badge`
   du type d'appartenance, la région du panneau de cycle de vie), `make cadre-check` (25 contrôles,
   dont « les 8 composants exportés sont testés et employés » — `Carte`/`Badge`/`CarteRetournable`
   confirmés), `make icloud-verify`, `make sources-check`, Ruff/Prettier/ESLint/mypy (276 fichiers)/
   `tsc --noEmit` (trois paquets) verts. `make check` complet buté sur 78 échecs **environnementaux**
   `pytest` identiques au compte déjà documenté à `S5` (1 914 passés), aucun fichier Python touché.
   Aller-retour réel effectué après `make code-refresh`/`make apercu` : trombinoscope et une fiche
   profil de l'entité de démonstration (`BORDEA00`, 76 collaborateurs) vus à travers Caddy en HTTPS,
   à 1280 px et à 375 px — les cartes colorées, le badge de statut et les six régions nommées
   confirmés à l'écran, aucun débordement à 375 px, décor nettoyé par `make apercu-fin`.
7. **Événements et mon onboarding. FAITE** (27/10/2026). Deux fichiers, `PageEvenements.tsx` et
   `PageMonOnboarding.tsx` — **mesuré avant tout code** : `PageEvenements.tsx` employait déjà
   `Badge` pour l'état annulé (LOT 8 `T9`), et `.evenements-carte` (CSS) était déjà identique,
   trait pour trait, à `.accueil-evenements-carte` que `T12` du LOT 8 avait posée pour le
   carrousel de la page entité — aucune divergence visuelle à corriger entre les deux. Ce qui
   manquait était `Carte` elle-même : le panneau de chaque onglet restait un `<div>` nu, sans
   l'ombre douce ni le fond qu'apporte `.ex-carte`.
   - **`Carrousel` (LOT 8, `T12`) ne s'applique PAS à l'écran de liste complète**, et c'est la
     vérification que demandait la fiche : il est réservé à une liste résumée et bornée
     (`NOMBRE_MONTRE`, avec un lien « voir plus »), jamais à un écran qui porte sa propre
     pagination serveur — en faire un carrousel aurait cassé la pagination par page
     (`donnees.pages`) en la remplaçant par un défilement continu que l'API ne sait pas servir.
     La « cohérence avec les carrousels » est donc visuelle (même recette de carte), pas
     structurelle : le panneau de chaque onglet devient une `Carte` **sans titre** — un simple
     `<div className="ex-carte">`, jamais une région — pour ne pas dupliquer le nom déjà porté
     par le `tabpanel` d'`Onglets`.
   - **`PageMonOnboarding.tsx` : défaut latent trouvé en mesurant, pas construit par cette
     sous-étape.** `application.css` ne portait AUCUNE règle pour les classes `.onboarding-*` de
     ce fichier depuis sa création au LOT 7 `T13` — l'écran rendait du HTML entièrement brut,
     sans mise en page ni habillage d'aucune sorte. Les deux sections (fiche d'arrivée, parcours)
     deviennent des `<Carte titre="…">` — mêmes `h2` frères qu'avant, aucune hiérarchie à
     préserver ici (contrairement à `PageProfil` en `S6`, qui avait un `h2` englobant). L'état de
     la fiche et l'état d'une tâche deviennent des `Badge`, selon la MÊME convention à quatre
     tons (`neutre`/`ok`/`ko`/`marque`) déjà posée pour les événements
     (`PageGestionDesEvenements.tsx`/`PageEditionEvenement.tsx`, hors périmètre mais même
     idiome) plutôt qu'une nouvelle inventée ici. Le marqueur « Obligatoire » d'une tâche devient
     aussi un `Badge`. La mise en page manquante reprend TEXTUELLEMENT les recettes déjà posées
     ailleurs (`.profil-champs` pour les grilles dt/dd, `.liens-formulaire` pour les champs de
     saisie, `.evenements-carte` pour la carte de tâche) — rien n'est inventé, §6.4.
   **Zéro régression** : 335 tests Vitest du frontend (+4 : un au panneau des événements — le
   panneau actif est une vraie `Carte` — et trois à « Mon onboarding » — les deux régions
   nommées, l'état de la fiche en `Badge`, l'état et le marqueur « Obligatoire » d'une tâche en
   `Badge`), `make cadre-check` (25 contrôles), `make icloud-verify`, `make sources-check`,
   Ruff/Prettier/ESLint/mypy (276 fichiers)/`tsc --noEmit` (trois paquets) verts. `make check`
   complet buté sur 78 échecs **environnementaux** `pytest` identiques au compte déjà documenté
   à `S5`/`S6` (1 914 passés), aucun fichier Python touché. Aller-retour réel effectué après
   `make code-refresh`/`make apercu` : un événement réel créé puis publié dans l'entité de
   démonstration (`BORDEA00`), vu avec sa carte et son badge « Annulé » à travers Caddy en
   HTTPS, à 1280 px et à 375 px, aucun débordement ; la fiche d'arrivée et le panneau « Mon
   parcours » vus en direct pour un compte temporaire doté d'une appartenance réelle — les deux
   comme de vraies `Carte`, l'état de la fiche comme un vrai `Badge` — décor nettoyé (événement,
   rôle technique et appartenance retirés, `make apercu-fin`).
8. **Recette visuelle finale. FAITE** (27/10/2026). Pas de code applicatif : une vérification sur
   le périmètre entier du §4, dans un vrai navigateur, à travers Caddy en HTTPS.
   - **Les cinq largeurs du §13.4 (320/390/768/1280/1920), mesurées, pas devinées.** Chaque écran
     du périmètre a été visité et son `document.documentElement.scrollWidth` confronté à son
     `clientWidth` aux cinq largeurs — jamais un simple coup d'œil, qui aurait pu manquer un
     débordement d'un pixel. **Zéro débordement horizontal sur aucun écran, à aucune largeur** :
     `PageNationale`, `PageEntite`, `PageFramework`, `PageCercle`, `PageBureau`,
     `PageTrombinoscope`, `PageProfil` (deux variantes — profil incomplet et profil avec cercle/
     responsabilité), `PageEvenements`, `PageMonOnboarding` (avec une fiche et un parcours réels,
     pas seulement l'état vide), `PageConnexion`. Le menu bascule bien de la barre mobile au menu
     du haut à 768 px exactement, comme posé par `S3`.
   - **Contraste AA : aucune nouvelle combinaison n'existe, et c'est mesuré plutôt que supposé.**
     `jetons.test.ts` (`S1`) couvre déjà le dégradé bleu→rose aux cinq points de mesure — y compris
     la zone morte à t=0,75 — et les seize couples neutres/états sur les deux surfaces (`fond`,
     `fondDoux`) des deux thèmes. **Vérifié une par une, les couleurs que `S4`-`S7` ont réellement
     posées n'en ajoutent aucune** : `Badge ton="marque"` réutilise `MARQUE.bleu` (déjà testé),
     `ton="ok"`/`"ko"`/`"neutre"` réutilisent `--ok`/`--ko`/`--encre` sur `--fond-doux` (déjà
     testés), les icônes `lucide-react` héritent `currentColor` sans déclarer de couleur propre.
     Zéro couple nouveau à mesurer, donc aucune extension de `jetons.test.ts` — l'étendre aurait
     dupliqué des assertions déjà vraies sans rien prouver de plus (§7.27).
   - **`make cadre-check` (25 contrôles), `make ecrans-check` (8 contrôles) et `make web-check`
     (7 contrôles) rejoués, 0 échec.** `make test-frontend` : 926 tests Vitest passés (459
     `contracts`, 132 `ui`, 335 `web`), 0 échec. `uv run mypy` (276 fichiers), Ruff, ESLint,
     Prettier verts.
   - **Capture avant/après par écran, sous la forme validée par Jonathan (`AskUserQuestion`,
     27/10/2026) : l'« après » est capturé en direct, l'« avant » reste la description déjà écrite
     dans le compte rendu de chaque sous-étape** — reconstruire un conteneur `web` depuis le commit
     d'avant le chantier pour des paires d'images littérales a été explicitement écarté comme
     disproportionné au regard de ce que `S1`-`S7` documentent déjà (la grille `.evenements-carte`
     nue devient `.ex-carte`, l'`<article>`/`<dl>` du profil devient `Carte`/`Badge`, etc.).
     Décor réel posé pour l'« après » : `SUPER_ADMIN` temporaire sur `apercu-demo@exalt-company.com`
     (aucune donnée réelle, §2 de la passation), `BORDEA00` consultée pour ses données Framework
     réelles (4 cercles, 1 bureau, 3 responsabilités pourvues, 76 collaborateurs), une appartenance,
     une fiche d'arrivée et un parcours avec une tâche posés temporairement pour voir `PageMonOnboarding`
     peuplée — tout retiré après capture, vérifié à zéro ligne résiduelle, puis `make apercu-fin`.
   - **Un point vérifié plutôt que supposé : le cinquième élément du §13.2, « animations courtes et
     non essentielles », était déjà présent avant `S8` — aucune sous-étape ne l'a jamais construit,
     et `S8` aurait pu le découvrir manquant.** Mesuré : `.app-evitement`/`.app-lien`/
     `.app-navigation-lien`/`.app-barre-lien` (120 ms, cadre applicatif, donc sur **chaque** écran
     authentifié du périmètre), `.nat-entite` (page nationale) et `CarteRetournable` (180 ms, flip,
     trombinoscope) portent déjà une transition courte, et les trois respectent
     `prefers-reduced-motion` (`application.css` §14.2, `composants.css`). `Carte` elle-même reste
     volontairement STATIQUE — ni transition ni `:hover`, cahier §13.2 ne l'exigeant que pour les
     éléments interactifs, qu'elle n'est pas. Rien à ajouter : les cinq éléments du critère de
     sortie 1 sont bien présents, et aucun ne l'est par construction de `S8`.
   - **Aucun défaut trouvé sur les écrans du périmètre.** La seule observation hors périmètre :
     `PageNationale` rend une liste de 26+ entités plutôt qu'une carte de France graphique pour la
     session `SUPER` utilisée ici — comportement de `CarteDeFrance.tsx`, explicitement **non
     touché** par ce chantier (§3, `DEP-006`), non mesuré avant `S8` et donc non imputable à lui.
9. **Bascule clair/sombre. FAITE** (27/10/2026, reprise `DEC-673`, voir §8). `jetons.css`
   suivait `@media (prefers-color-scheme: dark)` depuis le LOT 1 `T5` — juste pour la seule page
   de statut de l'époque, jamais reconsidéré quand `S1`-`S8` ont étendu ces jetons à toute
   l'application métier. **Un second site du même défaut, non prévu au découpage, a été trouvé en
   construisant S9** : `apps/web/src/styles.css` (propre à la page de statut) est en réalité
   importée GLOBALEMENT par `main.tsx`, pour CHAQUE page — sa propre règle `@media` continuait de
   suivre le système par-dessus le correctif de `jetons.css`, un bouton qui semblait n'avoir aucun
   effet. Les deux feuilles reçoivent le même mécanisme : un attribut `data-theme="sombre"` sur
   `<html>` remplace la préférence système, l'absence d'attribut étant le clair — jamais une
   troisième valeur. Nouveau module `packages/ui/src/theme.ts` (`appliquerLeTheme`,
   `lireLeThemeStocke`, pur, sans JSX) : la préférence est mémorisée **par appareil**
   (`localStorage`), jamais par compte — rien dans le corpus ne décide qu'elle doive survivre à un
   changement de machine (§6.5). **Arbitrage de Jonathan du 27/10/2026** : le clair est désormais
   TOUJOURS le thème de la première visite, quelle que soit la préférence système — cohérent avec
   le prototype et `exalt-company.com`, qui n'ont ni l'un ni l'autre de variante sombre. Nouveau
   composant `BoutonBasculerTheme` (`apps/web`, icônes `Sun`/`Moon` de `lucide-react`,
   `aria-pressed` suivant l'état réel), posé dans le SEUL `Squelette` partagé par les six états du
   cadre applicatif et dans le bandeau de `PageNationale` — deux emplacements, un seul composant
   (§7.27). **Un défaut de disposition trouvé en mesurant aux cinq largeurs** : à 1280 px, le
   bouton — cinquième enfant de `.app-entete` — forçait l'entité active (seul enfant à
   `min-width: 0`) à couper « Bordeaux » au milieu du mot plutôt que de passer à la ligne ; corrigé
   par `flex-wrap: wrap` sur `.app-entete`, mesuré avant/après sur les cinq largeurs du §13.4,
   zéro débordement (`scrollWidth`/`clientWidth`). **La préférence est appliquée une fois, dans
   `main.tsx`, avant tout rendu** — sans cette ligne, un chargement direct de `/statut`, d'une page
   de connexion ou d'une page d'erreur (aucune ne porte le bouton) ignorerait un choix « sombre »
   fait ailleurs sur le même appareil. `make ecrans-check`/`make web-check`/`make test-frontend`
   rejoués, 0 échec — 938 tests Vitest (459 `contracts`, 140 `ui`, 339 `web`).
10. **Trombinoscope/profil « pop ». FAITE** (28/10/2026). Les trois défauts constatés au §8.1
    corrigés par RÉEMPLOI, zéro nouveau composant, zéro nouvelle mesure de contraste :
    - **l'avatar neutre gris sur gris** (`.trombi-avatar`) prend la MÊME couleur que l'avatar neutre
      du profil (`.profil-avatar`, LOT 5) — `--marque-bleu`/`--marque-bleu-texte`, un couple déjà
      mesuré AA par `jetons.test.ts` (LOT 1 `T10`). Aucune nouvelle combinaison : une réutilisation
      stricte, §7.27 ;
    - **la pastille de cercle au recto** réutilise le `Badge` du design system TEL QUEL — déjà une
      pastille (`border-radius: var(--rayon-pastille)`), déjà accessible (le texte est obligatoire
      dans son type). `ton="marque"` pour la forme, la couleur du cercle posée en `style` inline
      (`background`/`color`), avec repli `ton="neutre"` sans couleur résolue. Nouvelle fonction
      `texteDuCercle` (`apps/web/src/affichage.ts`), appariée à `couleurDuCercle` (LOT 1 `T10`) :
      les QUATRE couples qu'elle expose sont les mêmes que `MARQUE` dans `jetons.ts`, déjà prouvés
      par `jetons.test.ts` — exposer leur texte n'ajoute donc AUCUNE mesure de contraste à faire.
      Sans cercle, AUCUNE pastille n'est rendue (une pastille vide n'ajouterait rien ; le verso dit
      toujours « Aucun cercle principal » en toutes lettres, §10.1 inchangé) ;
    - **la hauteur de carte harmonisée** : `CarteRetournable` (`packages/ui`) ne s'étirait pas dans
      sa cellule de grille — `.trombi-grille` (CSS Grid) étire déjà ses `<li>` par défaut
      (`align-items: stretch`), mais l'`<article>` qu'ils contiennent n'en héritait pas, laissant
      chaque carte à la hauteur de son seul contenu. `height: 100%` sur `.ui-carte-retournable` et
      `flex: 1 1 auto` sur sa face poussent désormais « Voir plus » en bas de la carte quelle que
      soit la hauteur de la rangée — vérifié en direct, une carte sans aucun cercle ni métier/statut
      (« Noa Chevalier ») s'aligne exactement sur ses trois voisines de rangée.
    - **Témoin de nettoyage** : « Data » existe désormais deux fois dans le DOM d'une carte (la
      pastille du recto, cachée par `hidden` après retournement, et le `<dd>` du verso) —
      `getByText` ne filtre pas la visibilité, donc les quatre tests existants qui lisaient le nom
      du cercle après un clic ont dû être scopés (`{ selector: '.trombi-verso dd' }`), régression
      de test attendue et documentée dans le fichier lui-même, pas un défaut du livrable.
    - **Contrôles** : `pnpm test` 344/344 (`web`, +5), 140/140 (`ui`, inchangé), lint/format/
      `tsc --noEmit` (3 paquets) verts, `make ecrans-check` (8 contrôles) et `make web-check`
      (7 contrôles) rejoués sur le conteneur reconstruit, 0 échec, `make trombinoscope-check`
      (38 contrôles API) inchangé — aucune route touchée. **Aller-retour réel effectué** après
      `make code-refresh` : lien magique réel consommé pour un compte temporaire (entité
      `BORDEA00`, qui porte les quatre jetons de couleur du design system), les quatre pastilles
      vues avec leur couple couleur/texte attendu, l'avatar neutre coloré, et la harmonisation de
      hauteur confirmée aux cinq largeurs du §13.4 (320/390/768/1280/1920, `scrollWidth`/
      `clientWidth` confrontés, aucun débordement) — en thème clair et en thème sombre. Décor
      nettoyé (adresse de courriel du compte de test restaurée, session et lien magique retirés).
    - **Hors périmètre de `S10`, volontairement** : la fiche de profil (`PageProfil.tsx`) n'a reçu
      AUCUNE pastille de cercle — elle n'a pas de structure recto/verso, et le constat du §8.1 ne
      visait que « montré en pastille au recto **de la carte** », donc le trombinoscope seul. Son
      avatar neutre était déjà coloré depuis le LOT 5 et n'avait rien à corriger.

Chaque sous-étape suit la boucle habituelle : annoncer, exécuter, contrôler (`make test-frontend`,
`make ecrans-check`, contraste), rapporter, attendre ta validation avant la suivante.

## 6. Questions tranchées par Jonathan le 25/10/2026

- **Le violet du §13.2** : **dégradé bleu → rose uniquement**, aucune quatrième teinte ajoutée.
- **Radix UI (§13.3)** : **inclus**, borné à `@radix-ui/react-tabs` pour les onglets (§2.1) — les
  autres primitives Radix restent hors périmètre faute de consommateur réel.
- **Ordre des sous-étapes** : aucune objection reçue — l'ordre du §5 est retenu (fondations →
  onglets → national → entité → cercles/bureaux → trombinoscope/profil → onboarding → recette).

## 7. Critères de sortie

1. **TENU (`S8`, 27/10/2026).** Les cinq éléments du §13.2 (dégradés, badges étendus, icônes
   maîtrisées, cartes généralisées, animations courtes) sont présents sur les écrans du périmètre
   §4 — les quatre premiers construits par `S1`/`S3`-`S7`, le cinquième déjà présent (transitions
   courtes du cadre applicatif, de `.nat-entite` et de `CarteRetournable`), vérifié plutôt que
   construit à nouveau.
2. **TENU (`S2`, 25/10/2026).** `PageAdministration.tsx`/`PageEvenements.tsx` consomment `Onglets`
   (`@radix-ui/react-tabs`), aucun motif ARIA fabriqué à la main ne subsiste pour les onglets.
3. **TENU (`S8`, 27/10/2026).** Aucune régression de contraste AA : mesuré, pas supposé —
   `jetons.test.ts` (posé par `S1`) couvre déjà chaque combinaison couleur/dégradé réellement
   employée par `S4`-`S7`, confirmé une par une, zéro couple nouveau à ajouter.
4. **TENU.** Aucune nouvelle dépendance visuelle au-delà de `@radix-ui/react-tabs`, nommée au §2.1
   — confirmé par `package.json` inchangé depuis `S1`.
5. **TENU (`S8`, 27/10/2026).** Les cinq largeurs de recette du §13.4 sont vérifiées sans
   débordement, mesuré (`scrollWidth`/`clientWidth`) sur chaque écran du périmètre §4.
6. **TENU.** `DEP-006` reste intacte : aucun logo ni illustration de marque inventés à sa place —
   `CarteDeFrance.tsx` non touché de `S1` à `S8`.

## 8. Reprise du chantier — `S9` à `S14` (`DEC-673`, 27/10/2026)

### 8.1 Constat

Jonathan a confronté des captures d'écran réelles de l'application (trombinoscope, page cercle,
Framework) aux captures équivalentes du prototype et du site réel `exalt-company.com`. Mesuré
avant tout code :

- **le thème sombre suivait la préférence système** (`@media (prefers-color-scheme: dark)`,
  hérité du LOT 1 `T5`, jamais repensé pour l'app métier) — sans aucun bouton pour revenir au
  clair, contrairement au prototype et au site réel, qui n'ont ni l'un ni l'autre de variante
  sombre ;
- **l'avatar neutre du trombinoscope est gris sur gris** (`.trombi-avatar`, LOT 5), jamais coloré ;
- **les cartes d'une même rangée du trombinoscope n'ont pas une hauteur égale** quand leur contenu
  diffère (métier/statut absents) ;
- **le nom du cercle n'est jamais montré en pastille au recto** de la carte, relégué au verso en
  texte brut (§10.1, décision jamais retranchée depuis) ;
- **la liste des membres d'un cercle ou d'un bureau reste un texte brut sans photo**
  (`PageCercle.tsx`), `S5` ayant délibérément limité sa portée à l'habillage (`Carte`/`Badge`),
  jamais à la restructuration du contenu — documenté dans le fichier lui-même.

Consultation de `https://www.exalt-company.com/fr-fr/` pour inspiration : fond **toujours blanc**,
un seul bloc sombre délibéré (bande CTA, pied de page) jamais le thème de lecture par défaut ;
palette de marque identique à `MARQUE` (`DEC-491`) ; motifs distinctifs absents de notre design
system — cadres de photo **hexagonaux**, gros chiffres bold pour les compteurs, soulignés
« tracé main » jaunes, pastilles à pointeur coloré.

### 8.2 Arbitrages de Jonathan (`AskUserQuestion`, 27/10/2026)

1. **Niveau d'inspiration** : **emprunter aussi les motifs du vrai site** (hexagones, gros
   chiffres, soulignés), pas seulement recolorer le système existant — risque et effort plus
   élevés qu'une passe de couleur seule, assumés.
2. **Thème par défaut** : **toujours clair**, y compris au tout premier chargement, quelle que
   soit la préférence système — jamais déduit, un bouton explicite permet de choisir le sombre.

### Découpage retenu

| | Sous-étape |
|---|---|
| `S9` | Bascule thème clair/sombre — **FAITE** |
| `S10` | Trombinoscope/profil « pop » : avatar sur fond de marque coloré, pastille de cercle au recto, hauteur de carte harmonisée — **FAITE** |
| `S11` | Cadres hexagonaux pour les photos (profil, trombinoscope, représentants de bureau) |
| `S12` | Cartes-photo des membres d'un cercle/bureau — extension du contrat, réutilisation de `resoudre_la_miniature` (LOT 5) |
| `S13` | Accents visuels : gros chiffres bold, soulignés « tracé main » décoratifs |
| `S14` | Recette visuelle finale de la reprise, même format que `S8` |

### 8.3 Critères de sortie de la reprise

1. Un bouton explicite permet de basculer entre thème clair et sombre sur toute page de
   l'application, mémorisé par appareil.
2. Le thème clair est actif à la première visite sur un appareil, quelle que soit la préférence
   système.
3. Les cinq largeurs de recette du §13.4 restent sans débordement sur chaque écran modifié par
   `S9`-`S13`.
4. Aucune régression de contraste AA sur les combinaisons déjà prouvées ; chaque nouvelle
   combinaison (pastille de cercle, hexagone, soulignement décoratif) est mesurée par
   `jetons.test.ts` ou son équivalent avant d'être employée.
5. Le périmètre reste celui du §4 : aucun écran du back-office, aucune donnée réelle.
