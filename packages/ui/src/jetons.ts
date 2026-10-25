/**
 * Jetons du design system eXalt — la source de verite unique.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 13.1 a 13.4, 14.
 *
 * ============================================================================
 *  D'OU VIENNENT CES VALEURS — le critere dit « sans dependance visuelle
 *  arbitraire », et c'est la seule partie de ce fichier qui ne se negocie pas.
 * ============================================================================
 *
 * CE QUE LE CAHIER DES CHARGES FOURNIT, ET CE QU'IL NE FOURNIT PAS
 *
 *   13.1 exige « la charte graphique » et « la police officielle lorsque sa
 *   licence web le permet ». MESURE DU 29/07/2026 : ni l'une ni l'autre n'est
 *   dans le corpus, aucun fichier de design n'est versionne, et le cahier ne
 *   contient AUCUNE couleur hexadecimale — zero occurrence de `#rrggbb`.
 *
 *   13.2 donne en revanche une direction ARTISTIQUE explicite : « visuel, colore,
 *   ludique, cartes arrondies, ombres douces, DEGRADES BLEU, ROSE ET VIOLET,
 *   portraits ronds ».
 *
 *   13.4 donne cinq largeurs de recette, litteralement.
 *
 * LES COULEURS DE MARQUE SONT RELEVEES, PAS CHOISIES
 *
 *   Le prototype historique NOMME lui-meme sa palette. Extraites de
 *   `docs/prototype/V1.html` — lignes courtes seulement, les 150 lignes de
 *   Base64 ecartees, conformement au piege documente :
 *
 *       const EXALT_BLUE      = "#5853FF";
 *       const EXALT_DARK_BLUE = "#2F2F9B";
 *       const EXALT_PINK      = "#FF2C9B";
 *       const EXALT_YELLOW    = "#FFDA3E";
 *
 *   Ces quatre valeurs corroborent litteralement le « bleu, rose et violet » du
 *   13.2. Elles sont donc tracees a DEUX sources qui concordent, et non inventees.
 *   Arbitrage de Jonathan du 29/07/2026 : les reprendre.
 *
 *   AUCUNE LIGNE DE CODE DU PROTOTYPE N'EST REPRISE. Seules des valeurs de
 *   couleur, ce que le 13.2 designe comme « l'intention du prototype ». La regle
 *   qui interdit de reutiliser le code du prototype reste entiere.
 *
 * LES NEUTRES ET LES ETATS VIENNENT DE `T5`, ET NE SONT PAS REDEFINIS ICI
 *
 *   `apps/web/src/styles.css` declare depuis `T5` sept proprietes semantiques —
 *   `--encre`, `--encre-douce`, `--fond`, `--fond-doux`, `--trait`, `--ok`,
 *   `--ko` — en theme clair ET sombre. Mesure : les huit couples atteignent AA,
 *   de 6,57 a 17,40. Les redefinir aurait cree deux sources de verite pour la
 *   meme chose, ce que `ECART-022` a appris a ne pas faire. Le design system les
 *   REPREND et se contente d'AJOUTER la couche de marque, qui manquait.
 *
 * ============================================================================
 *  CE QUE LA MESURE IMPOSE, ET QUI N'ETAIT PAS PREVISIBLE
 * ============================================================================
 *
 * Contrastes WCAG 2.2 releves le 29/07/2026 :
 *
 *     couleur              sur blanc   sur fond sombre
 *     #5853FF bleu             5,13          3,46
 *     #2F2F9B bleu fonce      10,50          1,69
 *     #FF2C9B rose             3,45          5,13
 *     #FFDA3E jaune            1,37         12,95
 *
 * DEUX CONSEQUENCES, ET ELLES CONTRAIGNENT LA CONCEPTION :
 *
 *   1. LES COULEURS DE MARQUE SONT DES SURFACES, PAS DES COULEURS DE TEXTE.
 *      Le jaune sur fond clair rend 1,37 et le bleu fonce sur fond sombre 1,69 :
 *      tous deux tres en dessous du seuil de 4,5. Chaque couleur de marque porte
 *      donc son `texte` apparie, determine par la MESURE et non par un choix.
 *
 *   2. LE PROTOTYPE AVAIT VU LE PROBLEME A MOITIE. Il declare un
 *      `circleTextColors` qui ne corrige QUE le jaune — « texte fonce sur fond
 *      jaune ». La mesure montre que le ROSE et le VERT de succes le reclament
 *      aussi : 4,94 et 5,48 avec du texte fonce, contre 3,45 et 3,11 avec du
 *      blanc. Reprendre le prototype tel quel aurait donc reconduit deux defauts
 *      d'accessibilite.
 *
 * `jetons.test.ts` RECALCULE chacun de ces couples et ECHOUE sous le seuil. Les
 * ratios ecrits en commentaire sont indicatifs ; le controle, lui, mesure.
 *
 * ============================================================================
 *  CE QUE CE FICHIER NE CONTIENT PAS, ET POURQUOI
 * ============================================================================
 *
 *   - LES COULEURS DE CERCLE. Le prototype en declare huit, indexees par nom de
 *     cercle : Produit, Design, Projet, Change, Data, Shield, Forge, IT. Le
 *     cahier 13.1 les mentionne — « des couleurs de cercles propres a chaque
 *     entite ». Mais un cercle est une notion METIER du LOT 6, et `ECART-014`
 *     montre que sa denomination n'est meme pas stabilisee. Les inscrire ici
 *     serait anticiper le LOT 6. Les huit valeurs sont relevees dans le compte
 *     rendu de `T10` pour que le LOT 6 les retrouve.
 *
 *   - LA POLICE OFFICIELLE. Elle n'est pas nommee par le corpus, et le 13.1 la
 *     conditionne a sa licence web. La pile ci-dessous est donc SYSTEME : aucun
 *     telechargement, aucune dependance a un CDN — ce que la roadmap 2.3
 *     interdit par ailleurs. Question ouverte au registre.
 */

import { SEUIL_AA_GRAND_TEXTE, SEUIL_AA_TEXTE_NORMAL } from './contraste.js';

/** Un fond et le texte qui doit s'y poser, avec le seuil que le couple doit atteindre. */
export interface CoupleColore {
  /** La couleur de surface, en `#rrggbb`. */
  readonly surface: string;
  /** La couleur de texte a poser dessus. Determinee par la mesure. */
  readonly texte: string;
  /** Le seuil WCAG que ce couple doit atteindre. */
  readonly seuil: number;
}

/**
 * Les quatre couleurs de marque, relevees du prototype qui les nomme.
 *
 * Employees en SURFACE. Chacune porte le texte que la mesure impose.
 */
export const MARQUE = {
  bleu: { surface: '#5853FF', texte: '#FFFFFF', seuil: SEUIL_AA_TEXTE_NORMAL },
  bleuFonce: { surface: '#2F2F9B', texte: '#FFFFFF', seuil: SEUIL_AA_TEXTE_NORMAL },
  rose: { surface: '#FF2C9B', texte: '#1A1A1A', seuil: SEUIL_AA_TEXTE_NORMAL },
  jaune: { surface: '#FFDA3E', texte: '#1A1A1A', seuil: SEUIL_AA_TEXTE_NORMAL },
} as const satisfies Record<string, CoupleColore>;

/**
 * Le degrade de marque — cahier 13.2, « degrades bleu, rose et violet ».
 *
 * Chantier front hors lot, sous-etape S1 (`DEC-672`, 25/10/2026). Arbitrage
 * explicite de Jonathan : BLEU VERS ROSE UNIQUEMENT, aucune troisieme teinte
 * violette ajoutee — coherent avec `MARQUE` ci-dessus, qui n'en relevait deja
 * aucune du prototype (`DEC-491`, LOT 1 `T10`).
 *
 * UN DEGRADE DECORATIF, JAMAIS UN FOND DE TEXTE DIRECT — ET C'EST MESURE
 *
 *   Ni le blanc ni le texte sombre n'atteignent AA (4,5) sur l'ETENDUE ENTIERE
 *   du degrade : le blanc tombe a 3,45 a l'extremite rose, le texte sombre
 *   tombe a 3,39 a l'extremite bleue. **ET LA MESURE VA PLUS LOIN QUE CETTE
 *   SEULE CONSTATATION** : vers t=0,75 (`#D536B4`), les DEUX rendent sous le
 *   seuil a la fois — blanc 4,19, sombre 4,16 — une vraie ZONE MORTE ou aucune
 *   couleur de texte, ni l'une ni l'autre, n'atteint AA. `jetons.test.ts` le
 *   prouve explicitement plutot que de supposer qu'un des deux textes reste
 *   toujours lisible quelque part sur le degrade.
 *
 *   LA REGLE QUI EN DECOULE : ce degrade est un fond DECORATIF. Tout texte qui
 *   doit s'y superposer vit dans un conteneur opaque (`Carte`, `Badge`, une
 *   pastille sur `--fond`), jamais directement sur le degrade. Un composant
 *   qui poserait du texte en clair sur `DEGRADE_MARQUE.css` romprait l'AA sans
 *   qu'aucun contrôle de ce fichier ne puisse le voir — a verifier a l'oeil,
 *   dans les sous-etapes d'ecran qui l'emploient.
 */
export const DEGRADE_MARQUE = {
  de: MARQUE.bleu.surface,
  vers: MARQUE.rose.surface,
  css: `linear-gradient(135deg, ${MARQUE.bleu.surface}, ${MARQUE.rose.surface})`,
} as const;

/**
 * Les couleurs de marque employees en ACCENT — texte ou bordure sur le fond de
 * la page. Le seuil y est celui du GRAND texte, et deux d'entre elles n'y sont
 * volontairement PAS admises.
 *
 * Le jaune sur fond clair rend 1,37 et le bleu fonce sur fond sombre 1,69 :
 * aucune taille de texte ne les rachete. Les omettre n'est pas un oubli, c'est
 * le resultat de la mesure — et `jetons.test.ts` verifie qu'ils sont bien absents,
 * sans quoi une reintroduction distraite passerait inapercue.
 */
export const ACCENTS_ADMIS = {
  clair: { bleu: MARQUE.bleu.surface, bleuFonce: MARQUE.bleuFonce.surface },
  sombre: { bleu: MARQUE.bleu.surface, rose: MARQUE.rose.surface },
} as const;

/**
 * Les neutres et les etats, REPRIS de `T5` sans modification.
 *
 * Source : `apps/web/src/styles.css`. Les noms sont ceux que `T5` a choisis ; le
 * design system ne les renomme pas, sous peine de faire divorcer la page de
 * statut de son propre design system.
 */
export const THEMES = {
  clair: {
    fond: '#FFFFFF',
    fondDoux: '#F4F4F5',
    encre: '#1A1A1A',
    encreDouce: '#555555',
    trait: '#D4D4D8',
    ok: '#0F6B3F',
    ko: '#9B1C1C',
  },
  sombre: {
    fond: '#18181B',
    fondDoux: '#27272A',
    encre: '#F4F4F5',
    encreDouce: '#A1A1AA',
    trait: '#3F3F46',
    ok: '#6EE7A8',
    ko: '#FCA5A5',
  },
} as const;

/**
 * Espacements, en pixels. Echelle de 4, qui est celle des valeurs deja employees
 * par la page de statut de `T5`.
 */
export const ESPACEMENTS = {
  xs: '4px',
  s: '8px',
  m: '16px',
  l: '24px',
  xl: '32px',
  xxl: '48px',
} as const;

/**
 * Rayons de bordure. Le cahier 13.2 dit « cartes arrondies » : le rayon des
 * cartes est donc franc, et non decoratif.
 */
export const RAYONS = {
  s: '6px',
  m: '12px',
  l: '16px',
  pastille: '999px',
} as const;

/**
 * Ombres. Le cahier 13.2 dit « ombres DOUCES » : opacite faible et diffusion
 * large, jamais de trait dur.
 */
export const OMBRES = {
  douce: '0 1px 3px rgb(0 0 0 / 8%), 0 4px 12px rgb(0 0 0 / 6%)',
  posee: '0 2px 6px rgb(0 0 0 / 10%), 0 8px 24px rgb(0 0 0 / 8%)',
} as const;

/**
 * Typographie. PILE SYSTEME, et c'est un choix contraint, pas un defaut.
 *
 * Le cahier 13.1 exige « la police officielle lorsque sa licence web le
 * permet ». Elle n'est pas nommee dans le corpus et sa licence n'est pas
 * tranchee. Une pile systeme ne telecharge rien, ne depend d'aucun CDN — ce que
 * la roadmap 2.3 interdit — et se remplacera par une declaration `@font-face`
 * le jour ou la police sera connue, sans toucher aux composants.
 */
export const TYPOGRAPHIE = {
  pile:
    "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', " +
    "Arial, 'Noto Sans', sans-serif",
  pileMonospace: "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace",
  tailles: { xs: '12px', s: '14px', m: '16px', l: '20px', xl: '28px' },
  graisses: { normale: 400, moyenne: 600, forte: 700 },
  hauteurs: { serree: 1.25, normale: 1.5 },
} as const;

/**
 * Les cinq largeurs de recette du cahier 13.4, litteralement.
 *
 * Ce ne sont pas des points de rupture choisis : c'est la liste que le cahier
 * impose de recetter. `jetons.test.ts` verifie qu'elles sont bien cinq et dans
 * cet ordre — une largeur retiree par distraction ferait echouer le controle.
 */
export const LARGEURS_RECETTE = [320, 390, 768, 1280, 1920] as const;

/** Le seuil applique aux accents, exporte pour que le controle le relise. */
export const SEUIL_ACCENT = SEUIL_AA_GRAND_TEXTE;
