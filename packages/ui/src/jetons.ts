/**
 * Jetons du design system eXalt — la source de verite unique.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 13.1 a 13.4, 14.
 * REFONTE v2 : chantier design systeme hors lot, etape E1 (`DEC-682`, 01/11/2026),
 * d'apres `docs/design-systeme/handoff/DESIGN_SYSTEME.md`, versionne avec ce code.
 *
 * ============================================================================
 *  D'OU VIENNENT CES VALEURS — le critere dit « sans dependance visuelle
 *  arbitraire », et c'est la seule partie de ce fichier qui ne se negocie pas.
 * ============================================================================
 *
 * CE QUI A CHANGE EN v2, ET CE QUI NE CHANGE PAS
 *
 *   La v1 (LOT 1 `T10`) avait RELEVE sa palette du prototype faute de charte
 *   versionnee : le cahier 13.1 exige « la charte graphique » et « la police
 *   officielle », et ni l'une ni l'autre n'etait dans le corpus. Mesure du
 *   29/07/2026, zero couleur hexadecimale dans le cahier.
 *
 *   LA CHARTE EXISTE DESORMAIS. `docs/design-systeme/handoff/` la porte, avec
 *   ses polices, ses logos et ses pictogrammes. Les quatre couleurs de marque
 *   y sont IDENTIQUES a celles relevees du prototype — la v1 avait vu juste —
 *   et ce que la v2 apporte est ce qui manquait : les teintes, les neutres
 *   bleutes, l'echelle typographique, et la police officielle elle-meme.
 *
 *   AUCUNE LIGNE DE CODE DU PROTOTYPE N'EST REPRISE, en v1 comme en v2.
 *
 * ============================================================================
 *  CE QUE LA MESURE IMPOSE — et elle a corrige la charte sur un point
 * ============================================================================
 *
 * Contrastes WCAG 2.2 recalcules le 01/11/2026, theme clair :
 *
 *     couple                                    mesure   annonce par la charte
 *     #5853FF bleu        + #FFFFFF blanc         5,13            5,1
 *     #2F2F9B bleu fonce  + #FFFFFF blanc        10,50           10,5
 *     #FF2C9B rose        + #1A1A2E encre         4,94            5,0
 *     #FFDA3E jaune       + #2F2F9B titre         7,67            7,7
 *     #ECEBFF teinte bleu + #2F2F9B titre         8,94          (non annonce)
 *     #FFE4F2 teinte rose + #2F2F9B titre         8,81          (non annonce)
 *     #FFF7D6 teinte jaune+ #2F2F9B titre         9,76          (non annonce)
 *     #F5F5F5 teinte gris + #2F2F9B titre         9,63          (non annonce)
 *
 * LE POINT QUE LA MESURE A CORRIGE, ET IL ETAIT DANS LA CHARTE ELLE-MEME
 *
 *   `jetons.css` fourni ecrivait le texte des cercles en `var(--encre)` et
 *   `var(--titre)`. Ces deux variables BASCULENT en theme sombre, alors que les
 *   surfaces de marque et les teintes, elles, ne basculent pas. Mesure du
 *   01/11/2026 : SIX cercles sur huit tombaient sous le seuil en sombre —
 *   Change a 1,46, pire que le jaune sur blanc (1,37) qui avait justifie toute
 *   la discipline de la v1.
 *
 *   LA REGLE QUI EN DECOULE, ET ELLE EST STRUCTURELLE :
 *
 *     une surface qui ne bascule pas porte un texte qui ne bascule pas.
 *
 *   Les textes apparies aux surfaces de marque et aux teintes sont donc des
 *   LITTERAUX, jamais des `var()`. C'est deja ce que la charte fait pour les
 *   quatre couples de marque, et ce que sa propre capture de reference montre :
 *   le badge jaune y garde un texte #2F2F9B en theme sombre, releve au pixel.
 *
 *   Seuls les neutres (`THEMES`) basculent, et leurs couples sont mesures dans
 *   LES DEUX themes par `jetons.test.ts`.
 *
 * ============================================================================
 *  CE QUE CE FICHIER NE CONTIENT PLUS, ET POURQUOI
 * ============================================================================
 *
 *   - LE DEGRADE DE MARQUE. La charte 1.1 est categorique : « aucun degrade ».
 *     `DEGRADE_MARQUE` et ses quatre temoins de « zone morte » sont retires —
 *     ils prouvaient qu'aucune couleur de texte ne couvre tout le degrade, ce
 *     qui n'a plus d'objet une fois le degrade supprime. La page nationale, son
 *     unique consommateur, passe a un aplat de bleu fonce.
 *
 *   - LA DECOUPE HEXAGONALE. `DECOUPES.hexagone` avait ete posee par le
 *     chantier `S11` (`DEC-673`, 28/10/2026) d'apres le site exalt-company.com.
 *     La capture de reference de la charte montre des avatars RONDS. Arbitrage
 *     de Jonathan du 01/11/2026 : la charte fait foi, `S11` est defait.
 *
 *   - LA GRAISSE 600. Century Gothic n'a que Regular (400) et Bold (700) ;
 *     declarer une graisse intermediaire ferait produire au navigateur un
 *     faux-gras synthetique, que la charte 3 exclut en ramenant les graisses
 *     800/900 de la V1 a 700.
 */

import { SEUIL_AA_GRAND_TEXTE, SEUIL_AA_TEXTE_NORMAL } from './contraste.js';
//  TYPE SEUL, DONC AUCUNE DEPENDANCE A L'EXECUTION — ce fichier reste la source
//  de verite des VALEURS et n'embarque pas les 88 courbes du catalogue. Ce que
//  l'import apporte est que `picto: 'fuse'` ne compile pas (§7.35).
import type { ClePicto } from './pictos.js';

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
 * Les quatre couleurs de marque. Employees en SURFACE.
 *
 * **LE TEXTE APPARIE EST UN LITTERAL, JAMAIS UNE `var()`** — voir l'en-tete,
 * section « le point que la mesure a corrige ». Ces quatre surfaces sont les
 * memes dans les deux themes ; leur texte doit l'etre aussi.
 */
export const MARQUE = {
  bleu: { surface: '#5853FF', texte: '#FFFFFF', seuil: SEUIL_AA_TEXTE_NORMAL },
  bleuFonce: { surface: '#2F2F9B', texte: '#FFFFFF', seuil: SEUIL_AA_TEXTE_NORMAL },
  rose: { surface: '#FF2C9B', texte: '#1A1A2E', seuil: SEUIL_AA_TEXTE_NORMAL },
  jaune: { surface: '#FFDA3E', texte: '#2F2F9B', seuil: SEUIL_AA_TEXTE_NORMAL },
} as const satisfies Record<string, CoupleColore>;

/**
 * Les teintes — fonds de tuiles, badges doux, cercles en teinte.
 *
 * Elles portent toutes le bleu fonce de titre, mesure de 8,81 a 9,76. La teinte
 * rose accepte AUSSI l'encre (14,32), que la charte 2 nomme en second : les deux
 * sont mesures, et c'est le titre qui est declare ici parce que c'est lui que la
 * charte cite en premier pour les quatre.
 *
 * **MEME REGLE DU LITTERAL QUE `MARQUE`** : ces surfaces ne basculent pas en
 * theme sombre (arbitrage de Jonathan du 01/11/2026, option « teintes
 * inchangees »), donc leur texte ne bascule pas non plus.
 */
export const TEINTES = {
  bleu: { surface: '#ECEBFF', texte: '#2F2F9B', seuil: SEUIL_AA_TEXTE_NORMAL },
  rose: { surface: '#FFE4F2', texte: '#2F2F9B', seuil: SEUIL_AA_TEXTE_NORMAL },
  jaune: { surface: '#FFF7D6', texte: '#2F2F9B', seuil: SEUIL_AA_TEXTE_NORMAL },
  gris: { surface: '#F5F5F5', texte: '#2F2F9B', seuil: SEUIL_AA_TEXTE_NORMAL },
  /**
   * MEME SURFACE QUE `gris`, MAIS UN TEXTE SOURD — le ton « annule » de la
   * charte 5, ajoute par `E3`.
   *
   * La charte ecrit « annule (gris/encre-douce) ». `--encre-douce` BASCULE avec
   * le theme, et cette surface NON : en sombre, `#A1A1AA` sur `#F5F5F5` rend
   * **2,35:1** — exactement le defaut que `E1` a corrige sur les huit cercles.
   * Le texte est donc un LITTERAL, et la regle structurelle de ce fichier tient :
   * une surface qui ne bascule pas porte un texte qui ne bascule pas.
   *
   * **4,55:1, soit 0,05 au-dessus du seuil.** C'est la marge la plus fine de
   * toute la palette, et elle est voulue : un badge fait 13px GRAS, ce que WCAG
   * ne classe PAS en « grand texte » (il faut 18,66px gras), donc le seuil
   * applicable est bien 4,5 et non 3. Assombrir le texte le rendrait moins
   * sourd, ce qui est tout le sens de ce ton.
   */
  grisSourd: { surface: '#F5F5F5', texte: '#6E6E85', seuil: SEUIL_AA_TEXTE_NORMAL },
} as const satisfies Record<string, CoupleColore>;

/**
 * Un cercle de la charte 4 : son nom, son couple de couleurs, son pictogramme.
 *
 * Il ETEND `CoupleColore` plutot que de l'encapsuler, et le motif est litteral :
 * la charte demande `{ nom, surface, texte, picto }`, et c'est exactement ce que
 * cette forme porte — `seuil` venant en plus, du couple reutilise.
 */
export interface DefinitionDeCercle extends CoupleColore {
  /** Le nom affiche, tel que la charte 4 l'ecrit : « Produit », « IT ». */
  readonly nom: string;
  /** La cle du pictogramme officiel dans `PICTOS`. */
  readonly picto: ClePicto;
}

/**
 * Les huit cercles — charte 4, « Cercles (donnees, pas en dur) ».
 *
 * Chantier design systeme v2, etape `E4` (`DEC-682`). `E1` n'avait pose que la
 * COULEUR et renvoyait le `picto` a plus tard ; il est ici, et la table porte
 * desormais les quatre colonnes que la charte demande.
 *
 * ============================================================================
 *  LA CLE EST LE JETON QUE LA BASE STOCKE — arbitrage de Jonathan, 02/11/2026
 * ============================================================================
 *
 * `circle.color_token` (modele 8.1, « Reference de couleur locale ») est un
 * texte LIBRE, nullable, sans aucune enumeration nulle part dans le corpus.
 * Mesure du 02/11/2026 sur la base de developpement : **112 cercles sans jeton**
 * et **quatre** qui en portent un — `bleu`, `rose`, `bleu-fonce`, `jaune`, sur
 * la seule entite de demonstration.
 *
 * **ET LE `picto` TRANCHE LA QUESTION DE LA CLE.** Une etiquette de COULEUR ne
 * peut pas designer un pictogramme : `bleu` ne dit pas s'il faut dessiner
 * `fusee` ou `camembert`. Deux cercles peuvent partager une surface ; ils ne
 * partagent pas leur dessin. La cle de cette table est donc une IDENTITE DE
 * CERCLE, pas une couleur — et le jeton stocke prend ces huit valeurs.
 *
 * Les deux autres lectures ont ete posees a Jonathan et ecartees par lui :
 * garder les etiquettes de couleur et les traduire rendrait QUATRE des huit
 * lignes — Data, Shield, Forge, IT — structurellement inatteignables, donc
 * leurs pictogrammes jamais affichables (§7.39) ; et laisser la table sans
 * consommateur reporterait le « pas en dur » de la charte sans rien resoudre.
 *
 * AUCUNE MIGRATION N'EST REQUISE : la colonne accepte deja n'importe quel texte
 * de 64 caracteres. Un jeton inconnu, et `null`, restent neutres exactement
 * comme avant — c'est le comportement que `couleurDuCercle` (`apps/web`) porte
 * depuis le LOT 5, et le defaut `T10-8` interdit de l'indexer par `null`.
 *
 * ============================================================================
 *  CE QUE LA FORME GARANTIT, SANS CONTROLE A MAINTENIR
 * ============================================================================
 *
 * `picto` est type `ClePicto` : une cle inventee ne compile pas. Le « >= 24px »
 * de la charte 4 etait deja tenu par `TaillePicto` a `E2` ; la fidelite du
 * pictogramme l'est ici. Ni l'un ni l'autre ne repose sur un commentaire
 * (§7.35 de la passation).
 *
 * Chaque couple reutilise une surface DEJA declaree par `MARQUE` ou `TEINTES` :
 * aucune couleur nouvelle n'est introduite ici, et `jetons.test.ts` l'exige.
 *
 * **LA CLE EST LE NOM EN MINUSCULES**, sans exception — `IT` donne `it`. C'est
 * ce qui fait qu'un neuvieme cercle ajoute a la charte entre ici sans qu'on ait
 * a inventer sa cle, et `cercles.test.ts` l'exige dans les deux sens contre le
 * tableau de `DESIGN_SYSTEME.md` lui-meme.
 */
export const CERCLES = {
  produit: { nom: 'Produit', ...MARQUE.bleu, picto: 'fusee' },
  projet: { nom: 'Projet', ...MARQUE.bleuFonce, picto: 'plan-de-projet-fusee' },
  design: { nom: 'Design', ...MARQUE.rose, picto: 'ampoule-idee' },
  change: { nom: 'Change', ...MARQUE.jaune, picto: 'dialogue' },
  data: { nom: 'Data', ...TEINTES.bleu, picto: 'camembert' },
  shield: { nom: 'Shield', ...TEINTES.rose, picto: 'bouclier-valide' },
  forge: { nom: 'Forge', ...TEINTES.jaune, picto: 'engrenages-multiples' },
  it: { nom: 'IT', ...TEINTES.gris, picto: 'serveur' },
} as const satisfies Record<string, DefinitionDeCercle>;

/** Les huit valeurs que `circle.color_token` peut prendre et que l'on sait rendre. */
export type CleCercle = keyof typeof CERCLES;

/**
 * Les couleurs de marque employees en ACCENT — texte ou bordure sur le fond de
 * la page. Le seuil y est celui du GRAND texte, et deux d'entre elles n'y sont
 * volontairement PAS admises.
 *
 * Le jaune sur fond clair rend 1,37 et le bleu fonce sur fond sombre 1,69 :
 * aucune taille de texte ne les rachete. Les omettre n'est pas un oubli, c'est
 * le resultat de la mesure — et `jetons.test.ts` verifie qu'ils sont bien
 * absents, sans quoi une reintroduction distraite passerait inapercue.
 *
 * `THEMES.sombre.titre` (#B3AFFF) ne figure pas ici : ce n'est pas une couleur
 * de marque employee en accent, c'est le neutre de titre du theme sombre, et il
 * est mesure avec les autres neutres.
 */
export const ACCENTS_ADMIS = {
  clair: { bleu: MARQUE.bleu.surface, bleuFonce: MARQUE.bleuFonce.surface },
  sombre: { bleu: MARQUE.bleu.surface, rose: MARQUE.rose.surface },
} as const;

/**
 * Les neutres et les etats — les SEULES couleurs qui basculent avec le theme.
 *
 * LES NOMS DE `T5` SONT CONSERVES, et c'est toujours la meme raison : la page de
 * statut declare `--encre`, `--fond`, `--trait`, `--ok` et `--ko` depuis `T5` du
 * LOT 1 ; les renommer ferait divorcer la page de son propre design system.
 * La v2 en AJOUTE trois — `surface`, `titre`, `traitFort` — sans en retirer un.
 *
 * `ok` ET `ko` SONT UN ECART A LA CHARTE, ASSUME ET BORNE. La charte 2 les dit
 * « conserves pour la page de statut uniquement », et sa capture montre que les
 * alertes metier passent au rose et au bleu de marque. Les jetons restent donc
 * declares et mesures ; leur retrait des composants `Alerte`/`Notification`
 * appartient a l'etape E3. Consigne au titre de la charte 8.
 *
 * **LE THEME SOMBRE S'ACTIVE PAR `data-theme`, PAS PAR `prefers-color-scheme`.**
 * La charte 2 mentionne `prefers-color-scheme` entre parentheses ; le depot a
 * tranche l'inverse le 27/10/2026, chantier `S9` (`DEC-673`), apres avoir mesure
 * qu'un systeme regle en sombre faisait basculer toute l'application SANS aucun
 * bouton pour revenir au clair. Revenir au `@media` rejouerait ce defaut : le
 * clair reste le theme de premiere visite.
 */
export const THEMES = {
  clair: {
    fond: '#FAFAFB',
    surface: '#FFFFFF',
    fondDoux: '#F5F5F5',
    encre: '#1A1A2E',
    encreDouce: '#6E6E85',
    titre: '#2F2F9B',
    trait: '#E8E8EE',
    traitFort: '#D6D6E0',
    ok: '#0F6B3F',
    ko: '#9B1C1C',
  },
  sombre: {
    fond: '#18181B',
    surface: '#27272A',
    fondDoux: '#27272A',
    encre: '#F4F4F5',
    encreDouce: '#A1A1AA',
    titre: '#B3AFFF',
    trait: '#3F3F46',
    traitFort: '#52525B',
    ok: '#6EE7A8',
    ko: '#FCA5A5',
  },
} as const;

/**
 * Espacements, en pixels. Echelle de 4, INCHANGEE depuis la v1 — la charte 2 le
 * dit explicitement, et c'est le seul groupe de jetons que la refonte ne touche
 * pas.
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
 * Rayons de bordure — charte 2.
 *
 * Plus francs qu'en v1 (6/12/16) : 8 pour les petits elements, 14 pour les
 * champs et les tuiles, 20 pour les cartes, 28 pour les grandes sections
 * d'accueil et la fiche d'arrivee, et la pastille pour les boutons et badges.
 */
export const RAYONS = {
  s: '8px',
  m: '14px',
  l: '20px',
  xl: '28px',
  pastille: '999px',
} as const;

/**
 * Ombres — NEUTRALISEES par la charte 1.1, « aucune box-shadow ».
 *
 * **POURQUOI `none` PLUTOT QUE LA SUPPRESSION DU JETON.** Le cahier 13.2 dit
 * « ombres douces », et la charte le contredit deliberement (ecart consigne,
 * charte 8). Garder le nom avec la valeur `none` rend ce choix LISIBLE a
 * l'endroit exact ou l'on chercherait l'ombre, et fait echouer bruyamment toute
 * tentative d'en redeclarer une ailleurs — un jeton supprime laisserait la voie
 * libre a une `box-shadow` ecrite en dur.
 *
 * La separation se fait desormais par une bordure `1px solid var(--trait)`.
 */
export const OMBRES = {
  douce: 'none',
  posee: 'none',
} as const;

/**
 * L'anneau de focus — charte 1.6, et c'est une exigence non negociable.
 *
 * **UN `outline`, JAMAIS UNE `box-shadow`.** La charte 1.6 ecrit
 * « outline: 3px solid …; outline-offset: 2px » ; `jetons.css` fourni le
 * proposait en `box-shadow`, ce que la charte 1.1 interdit par ailleurs. La
 * forme `outline` est retenue : elle est celle que la charte specifie, elle ne
 * participe pas au flux, et elle survit a `overflow: hidden`.
 *
 * **LA TRANSPARENCE DE 45 % DE LA CHARTE A ETE RETIREE, SUR ARBITRAGE EXPLICITE
 * DE JONATHAN (02/11/2026), ET LA MESURE EST LA RAISON.**
 *
 *   Un `outline` semi-transparent prend la couleur de ce qu'il recouvre. Compose
 *   sur les fonds reels, `rgb(88 83 255 / 45%)` donne :
 *
 *     #A3A0FF sur une surface claire  ->  2,33:1
 *     #423F9F sur une surface sombre  ->  1,73:1
 *
 *   WCAG 2.2 AA, critere 1.4.11, exige **3:1** pour un indicateur de focus. Les
 *   deux echouent, et c'est le SEUL repere de position pour qui navigue au
 *   clavier. Le cahier 14 fait de WCAG AA une exigence dure, et la regle de
 *   preseance du projet donne le cahier gagnant.
 *
 *   Le trait est donc OPAQUE, et il bascule : bleu de marque en theme clair
 *   (5,13:1), `--titre` en theme sombre (7,44:1). C'est la meme regle que pour
 *   le texte bleu du bouton discret et le remplissage de `Progression` — sur un
 *   fond sombre, le bleu d'accent est `--titre`, jamais `--marque-bleu`, qui n'y
 *   rend que 2,91:1.
 *
 *   **CE N'EST PAS UNE CORRECTION GRATUITE DE L'EXISTANT** : le depot employait
 *   deja un trait opaque `var(--marque-bleu)` partout depuis le LOT 1 — juste en
 *   theme clair, et en echec en sombre depuis `S9`. Ce jeton corrige les deux.
 *
 * Ecart avec la charte 1.6 a consigner (`E7`).
 */
export const ANNEAU_FOCUS = {
  trait: `3px solid ${MARQUE.bleu.surface}`,
  traitSombre: `3px solid ${THEMES.sombre.titre}`,
  decalage: '2px',
} as const;

/**
 * Typographie — Century Gothic, AUTO-HEBERGEE.
 *
 * LA POLICE OFFICIELLE EXISTE DESORMAIS, ET ELLE NE VIENT D'AUCUN CDN
 *
 *   Le cahier 13.1 exige « la police officielle lorsque sa licence web le
 *   permet », et la roadmap 2.3 interdit les CDN. La v1 s'etait donc rabattue
 *   sur une pile systeme, faute de police nommee. La charte 3 la nomme et la
 *   fournit : les deux fichiers vivent dans `packages/ui/polices/` et sont
 *   declares par `@font-face` dans `jetons.css`. Aucune requete sortante.
 *
 *   ⚠ LA LICENCE DE DIFFUSION RESTE A CONFIRMER AVANT MISE EN PRODUCTION.
 *   La charte 8 le dit elle-meme. Century Gothic est une police commerciale ;
 *   l'auto-heberger ne vaut pas licence. Point consigne, non resolu ici.
 *
 * `system-ui` RESTE DANS LA PILE, ET CE N'EST PAS UN RESIDU. C'est le repli qui
 * garantit un texte lisible si la police ne charge pas — `font-display: swap`
 * rend d'abord ce repli. `jetons.test.ts` l'exige explicitement.
 */
export const TYPOGRAPHIE = {
  pile: "'Century Gothic', 'Futura', system-ui, sans-serif",
  pileMonospace: "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace",
  /**
   * L'echelle de la charte 3. `surtitre` et `xs` partagent presque leur taille
   * et ne se distinguent que par l'emploi : `surtitre` est bold, en majuscules
   * et tres espace ; `xs` est du texte courant de legende.
   */
  tailles: {
    surtitre: '12px',
    xs: '13px',
    s: '14px',
    m: '16px',
    l: '20px',
    xl: '30px',
    xxl: '38px',
    display: '48px',
  },
  /** Century Gothic ne fournit que ces deux graisses — voir l'en-tete. */
  graisses: { normale: 400, forte: 700 },
  hauteurs: { serree: 1.25, normale: 1.5 },
  /** Interlettrage des grands titres, charte 3. Negatif : les titres se serrent. */
  interlettrages: {
    display: '-0.025em',
    titre: '-0.02em',
    sousTitre: '-0.01em',
    surtitre: '0.14em',
  },
} as const;

/**
 * Mouvement — charte 2.
 *
 * Trois durees seulement : la pression d'un bouton, le survol, et le
 * retournement d'une carte de trombinoscope. Toute animation qui les emploie
 * doit etre neutralisee sous `prefers-reduced-motion: reduce` (charte 1.7) —
 * une regle que le CSS porte, et qu'aucun jeton ne peut garantir a lui seul.
 */
export const MOUVEMENT = {
  durees: { rapide: '120ms', base: '200ms', lente: '360ms' },
  //  **LES ZEROS DE TETE ET LES ESPACES SONT CEUX DE PRETTIER, PAS UN CHOIX.**
  //  La charte ecrit `cubic-bezier(.22,1,.36,1)` ; Prettier normalise toute
  //  valeur CSS en `cubic-bezier(0.22, 1, 0.36, 1)`, strictement equivalente.
  //  La source doit porter la forme NORMALISEE, sans quoi le controle de
  //  divergence `jetons-css.test.ts` echouerait apres chaque `make format`.
  courbes: {
    sortie: 'cubic-bezier(0.22, 1, 0.36, 1)',
    ressort: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
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
