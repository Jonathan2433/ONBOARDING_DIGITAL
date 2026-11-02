/**
 * Design system eXalt — point d'entree du paquet.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007.
 *
 * CE QUE CE PAQUET CONTIENT
 *
 *   Les JETONS — couleurs, espacements, rayons, ombres, typographie, largeurs de
 *   recette — et TROIS composants de base. Le critere de la story dit
 *   « initialises » : c'est un socle eprouve, pas un catalogue complet.
 *
 *   Les jetons ne sont pas arbitraires, et c'est tout le point : les couleurs de
 *   marque sont RELEVEES du prototype qui les nomme lui-meme, les neutres sont
 *   REPRIS de la page de statut de `T5`, et chaque couple fond/texte est
 *   RECALCULE par `jetons.test.ts` contre les seuils de WCAG 2.2 AA. Voir
 *   l'en-tete de `jetons.ts` pour la tracabilite complete.
 *
 * CE QU'IL NE CONTIENT PAS, ET POURQUOI
 *
 *   Le cahier 13.3 enumere douze familles de composants — menus, modales,
 *   onglets, tableaux, alertes, carrousels, lecteurs video, etats vides. Elles
 *   arrivent avec les ecrans qui les emploient, et le cahier dit qu'elles
 *   seront construites au-dessus de primitives accessibles, « notamment Radix
 *   UI ». **Les onglets sont desormais ICI** (chantier front hors lot,
 *   sous-etapes S1/S2, `DEC-672`) : sur `@radix-ui/react-tabs`, avec DEUX
 *   consommateurs reels (`PageAdministration.tsx`, `PageEvenements.tsx`,
 *   migres en S2 — posee seule et testee en isolation par S1, l'exporter
 *   avant S2 aurait viole le critere de `T11` du LOT 1 : un composant expose
 *   ici doit etre EMPLOYE par un ecran). Les autres familles — menus,
 *   modales, tableaux, lecteurs video — restent absentes, faute de
 *   consommateur reel : livrer un menu deroulant sans ecran qui l'emploie
 *   serait du code non eprouve.
 *
 *   Aucune couleur de cercle : c'est une notion metier du LOT 6.
 *
 * LES COMPOSANTS DE LA CHARTE 5 — chantier design systeme v2, `E3` (`DEC-681`)
 *
 *   `Bouton` gagne deux variantes et deux tailles, `Badge` six tons, `Carte` une
 *   variante interactive ; `Pastille`, `Avatar`, `Champ`, `Liste`, `Progression`
 *   et `CaseACocher` arrivent ; `Onglets` et `CarteRetournable` EXISTAIENT DEJA
 *   et sont etendus plutot que recrees.
 *
 *   **AUCUN ECRAN NE LES EMPLOIE AVANT `E5`**, ce qui s'ecarte de la discipline
 *   d'`Onglets` entre `S1` et `S2` — un composant expose ici devait etre employe
 *   par un ecran (critere `T11` du LOT 1). L'instruction de `E3` est d'exposer
 *   les composants de la charte, et c'est elle qui est suivie ; l'ecart est
 *   nomme plutot que tu.
 *
 * LES PICTOGRAMMES — chantier design systeme v2, E2 (`DEC-681`)
 *
 *   `pictos.ts` porte les DOUZE icones officielles que la charte nomme,
 *   extraites des 382 du catalogue eXalt par `infra/scripts/engendrer-pictos.py`
 *   et verifiees contre lui par `pictos.test.ts`. `Picto` les rend en
 *   `currentColor`. Elles remplacent les emoji, que la charte 1.4 interdit.
 *
 *   `lucide-react` reste employe par `apps/web` pour ce que le catalogue eXalt
 *   ne couvre pas (bascule de theme, chevrons, icones de rubrique libres) : les
 *   deux ne se recouvrent pas, et `E5` dira lesquelles des secondes cedent la
 *   place aux premieres.
 *
 * LA BASCULE CLAIR/SOMBRE — chantier front hors lot, S9 (`DEC-672`/`DEC-673`)
 *
 *   `theme.ts` porte la logique (attribut `data-theme`, memorisation par
 *   appareil), sans aucun JSX : le bouton visible (`BoutonBasculerTheme`) vit
 *   dans `apps/web`, avec ses icones `lucide-react`, deja une dependance de
 *   l'application et non de ce paquet. Voir l'en-tete de `theme.ts` pour
 *   l'arbitrage complet — le clair est desormais TOUJOURS le theme de
 *   premiere visite, quelle que soit la preference systeme.
 *
 * COMMENT ON L'EMPLOIE
 *
 *   Les styles sont deux feuilles separees, a importer par l'application :
 *
 *       import '@onboarding/ui/jetons.css';       // les proprietes personnalisees
 *       import '@onboarding/ui/composants.css';   // les classes des composants
 *
 *   Separees, parce qu'un consommateur peut vouloir les jetons seuls — la page de
 *   statut de `T5`, par exemple, a ses propres styles et n'a besoin que des
 *   valeurs.
 */

export { Badge } from './Badge.js';
export type { ProprietesBadge, TonBadge } from './Badge.js';
export { Bouton } from './Bouton.js';
export type { ProprietesBouton, TailleBouton, VarianteBouton } from './Bouton.js';
export { Carte } from './Carte.js';
//  LOT 5, T10 — la carte retournable accessible, story MVP-L05-US003.
export { CarteRetournable } from './CarteRetournable.js';
export type { ProprietesCarteRetournable } from './CarteRetournable.js';
//  LOT 8, T12 — le carrousel manuel et accessible, cahier §13.3/§13.4.
export { Carrousel } from './Carrousel.js';
export type { ProprietesCarrousel } from './Carrousel.js';
export { Alerte } from './Alerte.js';
export type { ProprietesAlerte, TonAlerte, UrgenceAlerte } from './Alerte.js';
export type { NiveauTitre, ProprietesCarte, VarianteCarte } from './Carte.js';
export { Notification } from './Notification.js';
export type { ProprietesNotification, TonNotification } from './Notification.js';
//  Chantier design systeme v2, E3 (`DEC-681`) — les composants de la charte 5.
//  `Picto` les rejoint ici : `E2` l'avait volontairement laisse hors du barillet
//  faute de consommateur, et l'instruction de `E3` est d'exposer les composants
//  de la charte. Leurs consommateurs arrivent a `E5`.
export { Avatar, initiales } from './Avatar.js';
export type { ProprietesAvatar, TailleAvatar } from './Avatar.js';
export { CaseACocher } from './CaseACocher.js';
export type { ProprietesCaseACocher } from './CaseACocher.js';
export { Champ } from './Champ.js';
export type { ProprietesChamp } from './Champ.js';
export { Liste } from './Liste.js';
export type { ProprietesListe } from './Liste.js';
export { Pastille } from './Pastille.js';
export type { ProprietesPastille } from './Pastille.js';
export { Picto } from './Picto.js';
export type { ProprietesPicto, TaillePicto } from './Picto.js';
export { PICTOS } from './pictos.js';
export type { ClePicto, DefinitionDePicto } from './pictos.js';
export { Progression } from './Progression.js';
export type { ProprietesProgression } from './Progression.js';
//  Chantier front hors lot, S1/S2 (`DEC-672`) — onglets sur primitive Radix.
export { Onglets } from './Onglets.js';
export type { DefinitionDOnglet, ProprietesOnglets } from './Onglets.js';
export {
  atteintSeuil,
  contraste,
  luminance,
  melangerCouleurs,
  SEUIL_AA_GRAND_TEXTE,
  SEUIL_AA_TEXTE_NORMAL,
} from './contraste.js';
//  `DEGRADE_MARQUE` et `DECOUPES` ont ete RETIRES par la refonte v2 (`DEC-681`) :
//  la charte 1.1 interdit les degrades, et ses avatars sont ronds — voir
//  l'en-tete de `jetons.ts`, section « ce que ce fichier ne contient plus ».
export {
  ACCENTS_ADMIS,
  ANNEAU_FOCUS,
  CERCLES,
  ESPACEMENTS,
  LARGEURS_RECETTE,
  MARQUE,
  MOUVEMENT,
  OMBRES,
  RAYONS,
  SEUIL_ACCENT,
  TEINTES,
  THEMES,
  TYPOGRAPHIE,
} from './jetons.js';
//  `E4` ajoute `CleCercle` et `DefinitionDeCercle` : la table des cercles porte
//  desormais `{ nom, surface, texte, picto }`, et ses huit cles SONT les valeurs
//  que `circle.color_token` prend. Voir l'en-tete de `jetons.ts`.
export type { CleCercle, CoupleColore, DefinitionDeCercle } from './jetons.js';
//  Chantier front hors lot, S9 (`DEC-672`/`DEC-673`) — la bascule clair/sombre.
export { appliquerLeTheme, CLE_DE_STOCKAGE_DU_THEME, lireLeThemeStocke } from './theme.js';
export type { Theme } from './theme.js';

export const PACKAGE_NAME = '@onboarding/ui';
