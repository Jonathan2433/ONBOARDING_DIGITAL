# Fiche de chantier — Refonte visuelle du front

**Nature :** chantier transversal, **PAS un lot** de la roadmap — hors numérotation `LOT n`,
hors épic/stories du backlog. Demandé directement par Jonathan le 25/10/2026, à la fermeture
de `G10`.
**Ouvert par Jonathan le :** 25 octobre 2026
**État :** **VALIDÉ** — découpage et les deux questions ouvertes tranchées par Jonathan le
25/10/2026 (`DEC-672`)
**Sous-étape suivante :** `S1` — Fondations (jetons de dégradé + primitive Radix `Tabs`)

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

1. **Fondations.** Deux volets indépendants, un seul `packages/ui` touché :
   - jetons de dégradé dérivés des couleurs déjà validées
     (`--degrade-marque: linear-gradient(135deg, var(--marque-bleu), var(--marque-rose))`, bleu→rose
     uniquement — décision du 25/10/2026), contraste du texte sur dégradé remesuré (pas seulement
     sur une couleur plate, §7.0) ;
   - `@radix-ui/react-tabs` posée comme dépendance, nouveau composant `Onglets` dans `packages/ui`
     construit dessus, ses propres tests ; **aucun écran migré à cette étape**, seulement la
     primitive et sa preuve isolée.
2. **Migration des onglets existants.** `PageAdministration.tsx` et `PageEvenements.tsx` basculent
   sur `Onglets` ; le motif ARIA fabriqué à la main est retiré des deux fichiers. Sous-étape
   structurelle, aucun habillage visuel nouveau.
3. **Page nationale + cadre applicatif.** Bandeau d'accueil (dégradé), carte de France existante
   conservée telle quelle (`DEP-006`), navigation et barre mobile avec icônes `lucide-react`.
4. **Page entité.** Généraliser `Carte` aux trois blocs d'information, badges pour les compteurs,
   vérifier le carrousel déjà en place.
5. **Framework, cercle, bureau.** Appliquer `Carte`/`Badge` (actuellement absents de ces trois
   écrans), icônes de bureau (`lucide-react`, pas d'emoji brut — accessibilité, cohérence avec le
   reste du design system).
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
2. `PageAdministration.tsx`/`PageEvenements.tsx` consomment `Onglets` (`@radix-ui/react-tabs`),
   aucun motif ARIA fabriqué à la main ne subsiste pour les onglets.
3. Aucune régression de contraste AA (mesuré, pas supposé — `jetons.test.ts` étendu).
4. Aucune nouvelle dépendance visuelle au-delà de `@radix-ui/react-tabs`, nommée ici.
5. Les cinq largeurs de recette du §13.4 sont vérifiées sans débordement.
6. `DEP-006` reste intacte : aucun logo ni illustration de marque inventés à sa place.
