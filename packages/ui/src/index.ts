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
 *   UI ». **Les onglets existent desormais** (chantier front hors lot,
 *   sous-etape S1, `DEC-672`, `Onglets.tsx`, sur `@radix-ui/react-tabs`) mais
 *   ne sont PAS encore exportes ici : aucun ecran ne les consomme avant S2
 *   (migration de `PageAdministration.tsx` et `PageEvenements.tsx`), et
 *   `make cadre-check` exige qu'un composant expose par ce fichier soit
 *   EMPLOYE par un ecran du frontend (critere de `T11` du LOT 1) — l'exporter
 *   maintenant serait livrer du code non eprouve. Les autres familles —
 *   menus, modales, tableaux, lecteurs video — restent absentes pour la meme
 *   raison, faute de consommateur reel.
 *
 *   Aucune couleur de cercle : c'est une notion metier du LOT 6.
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
export type { ProprietesBouton, VarianteBouton } from './Bouton.js';
export { Carte } from './Carte.js';
//  LOT 5, T10 — la carte retournable accessible, story MVP-L05-US003.
export { CarteRetournable } from './CarteRetournable.js';
export type { ProprietesCarteRetournable } from './CarteRetournable.js';
//  LOT 8, T12 — le carrousel manuel et accessible, cahier §13.3/§13.4.
export { Carrousel } from './Carrousel.js';
export type { ProprietesCarrousel } from './Carrousel.js';
export { Alerte } from './Alerte.js';
export type { ProprietesAlerte, TonAlerte, UrgenceAlerte } from './Alerte.js';
export type { NiveauTitre, ProprietesCarte } from './Carte.js';
export { Notification } from './Notification.js';
export type { ProprietesNotification, TonNotification } from './Notification.js';
//  `Onglets` (chantier front, S1, `DEC-672`) n'est PAS exporte ici : voir
//  l'en-tete de ce fichier — aucun ecran ne le consomme avant S2.
export {
  atteintSeuil,
  contraste,
  luminance,
  melangerCouleurs,
  SEUIL_AA_GRAND_TEXTE,
  SEUIL_AA_TEXTE_NORMAL,
} from './contraste.js';
export {
  ACCENTS_ADMIS,
  DEGRADE_MARQUE,
  ESPACEMENTS,
  LARGEURS_RECETTE,
  MARQUE,
  OMBRES,
  RAYONS,
  SEUIL_ACCENT,
  THEMES,
  TYPOGRAPHIE,
} from './jetons.js';
export type { CoupleColore } from './jetons.js';

export const PACKAGE_NAME = '@onboarding/ui';
