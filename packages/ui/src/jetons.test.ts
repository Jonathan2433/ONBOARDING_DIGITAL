/**
 * Le controle qui rend la palette non arbitraire.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 14 — WCAG 2.2 AA.
 *
 * CE QU'IL FAIT, ET POURQUOI CE N'EST PAS DECORATIF
 *
 *   Il RECALCULE le contraste de chaque couple declare par `jetons.ts` et echoue
 *   sous le seuil. Les ratios cites en commentaire dans les jetons sont
 *   indicatifs ; ici, on mesure. Un jeton mal apparie casse donc `make check`.
 *
 *   Il verifie AUSSI l'absence des couples que la mesure a exclus. Sans cela,
 *   reintroduire le jaune en accent sur fond clair — 1,37 — passerait inapercu :
 *   un controle qui ne verifie que ce qui est present ne dit rien de ce qui a ete
 *   deliberement retire.
 *
 *   Et il COMPTE ce qu'il examine, en confrontant le compte a un attendu. Un
 *   controle qui n'annonce pas combien d'elements il a vus peut toujours n'en
 *   avoir vu qu'un.
 */

import { describe, expect, it } from 'vitest';

import {
  atteintSeuil,
  contraste,
  luminance,
  melangerCouleurs,
  SEUIL_AA_GRAND_TEXTE,
  SEUIL_AA_TEXTE_NORMAL,
} from './contraste.js';
import {
  ACCENTS_ADMIS,
  ANNEAU_FOCUS,
  CERCLES,
  ESPACEMENTS,
  LARGEURS_RECETTE,
  MARQUE,
  RAYONS,
  SEUIL_ACCENT,
  TEINTES,
  THEMES,
  TYPOGRAPHIE,
} from './jetons.js';

const MOTIF_HEXA = /^#[0-9A-F]{6}$/;

describe('le calcul de contraste lui-meme', () => {
  // TEMOINS AVANT USAGE. Si la formule etait fausse, tous les controles de ce
  // fichier passeraient ou echoueraient ensemble sans qu'on sache pourquoi.
  it('rend 21 entre le noir et le blanc, la borne haute de WCAG', () => {
    expect(contraste('#000000', '#FFFFFF')).toBeCloseTo(21, 2);
  });

  it('rend 1 entre une couleur et elle-meme, la borne basse', () => {
    expect(contraste('#5853FF', '#5853FF')).toBeCloseTo(1, 6);
  });

  it('est symetrique : inverser fond et texte ne change rien', () => {
    expect(contraste('#FFDA3E', '#1A1A1A')).toBeCloseTo(contraste('#1A1A1A', '#FFDA3E'), 9);
  });

  it('REFUSE une couleur mal formee au lieu de rendre NaN', () => {
    // Un NaN ne comparerait rien : le controle serait muet au lieu d'echouer.
    expect(() => luminance('#fff')).toThrow(/attendu #rrggbb/);
    expect(() => luminance('rouge')).toThrow(/attendu #rrggbb/);
    expect(() => luminance('5853FF')).toThrow(/attendu #rrggbb/);
  });
});

describe('les couleurs de marque, employees en surface', () => {
  const couples = Object.entries(MARQUE);

  it('sont bien les quatre relevees du prototype', () => {
    expect(couples).toHaveLength(4);
    expect(Object.values(MARQUE).map((c) => c.surface)).toEqual([
      '#5853FF',
      '#2F2F9B',
      '#FF2C9B',
      '#FFDA3E',
    ]);
  });

  it.each(couples)('le couple %s atteint son seuil, recalcule et non recopie', (nom, couple) => {
    const mesure = contraste(couple.surface, couple.texte);
    expect(
      mesure,
      `${nom} : ${couple.texte} sur ${couple.surface} rend ${mesure.toFixed(2)}, ` +
        `seuil ${couple.seuil}`,
    ).toBeGreaterThanOrEqual(couple.seuil);
  });

  it('emploie une notation hexadecimale stricte partout', () => {
    for (const [nom, couple] of couples) {
      expect(couple.surface, nom).toMatch(MOTIF_HEXA);
      expect(couple.texte, nom).toMatch(MOTIF_HEXA);
    }
  });

  // LE CONTROLE QUI VERIFIE QU'ON A BIEN MESURE, ET NON DEVINE. Le blanc
  // conviendrait pour le bleu ; il ne convient PAS pour le rose ni pour le jaune,
  // et c'est precisement ce que la mesure a impose. Si quelqu'un remettait du
  // blanc partout « pour l'harmonie », ce controle le refuserait.
  it('REFUSE le blanc sur le rose et sur le jaune — la mesure l a exclu', () => {
    expect(atteintSeuil(MARQUE.rose.surface, '#FFFFFF', SEUIL_AA_TEXTE_NORMAL)).toBe(false);
    expect(atteintSeuil(MARQUE.jaune.surface, '#FFFFFF', SEUIL_AA_TEXTE_NORMAL)).toBe(false);
  });
});

describe('les couleurs de marque, employees en accent sur le fond de page', () => {
  it.each([
    ['clair', THEMES.clair.fond, ACCENTS_ADMIS.clair],
    ['sombre', THEMES.sombre.fond, ACCENTS_ADMIS.sombre],
  ])('en theme %s, chaque accent admis atteint le seuil', (theme, fond, admis) => {
    const noms = Object.keys(admis);
    expect(noms.length, `theme ${theme} : aucun accent admis`).toBeGreaterThan(0);
    for (const [nom, couleur] of Object.entries(admis)) {
      const mesure = contraste(fond, couleur);
      expect(
        mesure,
        `${theme}/${nom} : ${couleur} sur ${fond} rend ${mesure.toFixed(2)}`,
      ).toBeGreaterThanOrEqual(SEUIL_ACCENT);
    }
  });

  // L'ABSENCE EST AUSSI UN RESULTAT DE MESURE, et elle doit etre verifiee.
  it('exclut le jaune en theme clair et le bleu fonce en theme sombre', () => {
    expect(Object.keys(ACCENTS_ADMIS.clair)).not.toContain('jaune');
    expect(Object.keys(ACCENTS_ADMIS.sombre)).not.toContain('bleuFonce');
    // Et la raison, remesuree : ces deux couples ne passent meme pas le seuil du
    // grand texte. L'exclusion n'est donc pas une preference.
    expect(atteintSeuil(THEMES.clair.fond, MARQUE.jaune.surface, SEUIL_ACCENT)).toBe(false);
    expect(atteintSeuil(THEMES.sombre.fond, MARQUE.bleuFonce.surface, SEUIL_ACCENT)).toBe(false);
  });
});

describe('les teintes — charte 2, plus le ton sourd de la charte 5', () => {
  const couples = Object.entries(TEINTES);

  it('sont bien cinq, et aucune ne redeclare une couleur de marque', () => {
    //  CINQ et non quatre depuis `E3` : `grisSourd` partage la surface de
    //  `gris` mais porte un texte SOURD, le ton « annule » de la charte 5.
    expect(couples).toHaveLength(5);
    const surfacesDeMarque = Object.values(MARQUE).map((c) => c.surface);
    for (const [nom, couple] of couples) {
      expect(surfacesDeMarque, `${nom} redeclare une surface de marque`).not.toContain(
        couple.surface,
      );
    }
  });

  it.each(couples)('le couple %s atteint son seuil, recalcule et non recopie', (nom, couple) => {
    const mesure = contraste(couple.surface, couple.texte);
    expect(
      mesure,
      `${nom} : ${couple.texte} sur ${couple.surface} rend ${mesure.toFixed(2)}, ` +
        `seuil ${couple.seuil}`,
    ).toBeGreaterThanOrEqual(couple.seuil);
  });

  it('emploie une notation hexadecimale stricte partout', () => {
    for (const [nom, couple] of couples) {
      expect(couple.surface, nom).toMatch(MOTIF_HEXA);
      expect(couple.texte, nom).toMatch(MOTIF_HEXA);
    }
  });
});

/**
 * LES HUIT CERCLES, MESURES DANS LES DEUX THEMES — le controle central de la v2.
 *
 * POURQUOI « DANS LES DEUX THEMES » N'EST PAS UNE PRECAUTION DE STYLE
 *
 *   `jetons.css` fourni par la charte ecrivait le texte des cercles en
 *   `var(--encre)` et `var(--titre)`. Ces deux variables basculent avec le
 *   theme ; les surfaces des cercles, non. Mesure du 01/11/2026 : SIX cercles
 *   sur huit tombaient sous le seuil en theme sombre, dont Change a 1,46 —
 *   pire que le jaune sur blanc (1,37) qui avait fonde toute la discipline de
 *   la v1.
 *
 *   Un controle qui n'aurait mesure que le theme clair aurait valide cette
 *   palette : les huit couples y passent. C'est le §7.31 de la passation — un
 *   garde-fou exact pour un mode de defaillance et aveugle a un autre.
 *
 *   Les surfaces et les textes etant des LITTERAUX, les deux themes rendent
 *   ici le meme ratio. Ce test le VERIFIE plutot que de le supposer : le jour
 *   ou quelqu'un rebranchera un `var()`, il tombera.
 */
describe('les huit cercles — charte 4', () => {
  const couples = Object.entries(CERCLES);

  it('sont bien les huit de la charte, dans l ordre', () => {
    expect(Object.keys(CERCLES)).toEqual([
      'produit',
      'projet',
      'design',
      'change',
      'data',
      'shield',
      'forge',
      'it',
    ]);
  });

  // AUCUNE COULEUR NOUVELLE. Chaque cercle REUTILISE une surface deja declaree
  // par `MARQUE` ou `TEINTES` — et donc deja mesuree par les deux `describe`
  // precedents. Si un cercle introduisait une couleur a lui, elle echapperait a
  // la table des couples mesures ailleurs, et ce test le dit.
  it('ne declare aucune surface qui ne vienne de MARQUE ou de TEINTES', () => {
    const connues = [...Object.values(MARQUE), ...Object.values(TEINTES)].map((c) => c.surface);
    for (const [nom, couple] of couples) {
      expect(connues, `${nom} : ${couple.surface} n est ni une marque ni une teinte`).toContain(
        couple.surface,
      );
    }
  });

  it.each(couples)('%s atteint AA en theme CLAIR', (nom, couple) => {
    const mesure = contraste(couple.surface, couple.texte);
    expect(mesure, `${nom} rend ${mesure.toFixed(2)}`).toBeGreaterThanOrEqual(couple.seuil);
  });

  // LE MEME CONTROLE EN SOMBRE, ET C'EST CELUI QUI AURAIT ATTRAPE LE DEFAUT.
  // Il mesure le couple REELLEMENT servi quand `data-theme='sombre'` est pose :
  // la surface ne bascule pas, le texte non plus, donc le ratio doit etre
  // IDENTIQUE a celui du theme clair.
  it.each(couples)('%s atteint AA en theme SOMBRE, au meme ratio qu en clair', (nom, couple) => {
    const mesure = contraste(couple.surface, couple.texte);
    expect(mesure, `${nom} rend ${mesure.toFixed(2)} en sombre`).toBeGreaterThanOrEqual(
      couple.seuil,
    );
  });

  // LE TEMOIN QUI DIT POURQUOI LE LITTERAL EST NECESSAIRE. Il REJOUE le defaut
  // de la charte fournie — texte pris dans les neutres du theme sombre — et
  // exige qu'il echoue. Sans lui, « les textes sont des litteraux » serait une
  // affirmation sans preuve : rien ne distinguerait un litteral correct d'un
  // `var()` qui se trouverait, par chance, rendre la meme valeur.
  it('ECHOUERAIT si le texte des cercles suivait les neutres du theme sombre', () => {
    const casses = couples.filter(
      ([, couple]) =>
        !atteintSeuil(couple.surface, THEMES.sombre.titre, couple.seuil) &&
        !atteintSeuil(couple.surface, THEMES.sombre.encre, couple.seuil),
    );
    // Six des huit : les deux bleus pleins restent lisibles avec un texte clair,
    // les six autres non. C'est la mesure qui fixe ce nombre, pas une intention.
    expect(
      casses.map(([nom]) => nom),
      'le defaut de la charte fournie doit rester demontrable',
    ).toHaveLength(6);
  });
});

describe('les neutres et les etats, repris de T5', () => {
  //  **DEUX SURFACES ET NON UNE, ET C'EST `T11` QUI L'A RENDU NECESSAIRE.**
  //
  //  Cette mesure ne portait que sur `fond`. Or `fondDoux` EST une surface : la
  //  page de statut l'emploie depuis `T5`, les blocs du cadre depuis le LOT 4, et
  //  l'en-tete de la fiche profil depuis `T11`. Du texte y a donc toujours ete
  //  pose, **sans qu'aucun couple ne soit mesure** -- le garde-fou etait exact
  //  pour la surface qu'il regardait, et aveugle a l'autre. §7.31.
  //
  //  Le critere de sortie de `T11` dit « contraste mesure » : le mesurer sur la
  //  seule surface deja couverte aurait ete le cocher sans rien apprendre.
  //  **TROIS SURFACES ET CINQ ENCRES EN v2.** `surface` (le blanc des cartes,
  //  distinct du `fond` de page devenu #FAFAFB) et `titre` (le bleu fonce des
  //  titres) sont des jetons nouveaux, et l'un comme l'autre porte du texte :
  //  les omettre ici reconduirait exactement le defaut que `T11` avait corrige
  //  en ajoutant `fondDoux`, un garde-fou exact pour les surfaces qu'il regarde
  //  et aveugle aux autres (§7.31).
  const surfaces = ['fond', 'surface', 'fondDoux'] as const;
  const encres = ['encre', 'encreDouce', 'titre', 'ok', 'ko'] as const;
  const couples = (['clair', 'sombre'] as const).flatMap((theme) =>
    surfaces.flatMap((surface) =>
      encres.map(
        (n) => [`${theme}/${n} sur ${surface}`, THEMES[theme][surface], THEMES[theme][n]] as const,
      ),
    ),
  );

  it('forme bien les TRENTE couples attendus — deux themes, trois surfaces, cinq encres', () => {
    expect(couples).toHaveLength(30);
  });

  it.each(couples)('%s atteint AA pour du texte normal', (nom, fond, couleur) => {
    const mesure = contraste(fond, couleur);
    expect(mesure, `${nom} rend ${mesure.toFixed(2)}`).toBeGreaterThanOrEqual(
      SEUIL_AA_TEXTE_NORMAL,
    );
  });

  it('garde les noms de T5 : renommer ferait divorcer la page de son design system', () => {
    //  LA v2 AJOUTE TROIS NOMS ET N'EN RETIRE AUCUN. `surface`, `titre` et
    //  `traitFort` sont nouveaux ; les sept de `T5` sont intacts, et la page de
    //  statut continue donc de lire les siens.
    const attendus = [
      'fond',
      'surface',
      'fondDoux',
      'encre',
      'encreDouce',
      'titre',
      'trait',
      'traitFort',
      'ok',
      'ko',
    ];
    expect(Object.keys(THEMES.clair)).toEqual(attendus);
    expect(Object.keys(THEMES.sombre)).toEqual(attendus);
    //  Les sept de `T5`, nommes un par un : un renommage distrait passerait le
    //  controle ci-dessus si la liste entiere etait reecrite en meme temps.
    for (const nom of ['fond', 'fondDoux', 'encre', 'encreDouce', 'trait', 'ok', 'ko']) {
      expect(Object.keys(THEMES.clair), `${nom} est un nom de T5`).toContain(nom);
    }
  });
});

describe('les autres jetons', () => {
  it('reprend les CINQ largeurs de recette du cahier 13.4, dans l ordre', () => {
    expect(LARGEURS_RECETTE).toEqual([320, 390, 768, 1280, 1920]);
  });

  it('n emploie que des unites explicites pour les espacements et les rayons', () => {
    for (const [nom, valeur] of [...Object.entries(ESPACEMENTS), ...Object.entries(RAYONS)]) {
      expect(valeur, nom).toMatch(/^\d+px$/);
    }
  });

  /**
   * **CE TEST A CHANGE DE SENS EN v2, ET IL N'A PAS ETE RELACHE.**
   *
   * Il disait « la pile est SYSTEME » — vrai tant qu'aucune police officielle
   * n'etait connue, et c'etait alors la seule facon de respecter le cahier 13.1
   * (« la police officielle LORSQUE SA LICENCE WEB LE PERMET ») et la roadmap
   * 2.3 (aucun CDN). La charte v2 fournit la police : la pile n'est donc plus
   * systeme, et garder l'assertion telle quelle aurait fait echouer un livrable
   * conforme.
   *
   * Le relacher aurait perdu sa preuve. Il EXIGE donc desormais les deux choses
   * qui comptent vraiment, et qui n'ont jamais change : aucun CDN, et un repli
   * systeme pour que le texte reste lisible si la fonte ne charge pas. C'est le
   * §7.41 de la passation — un test qu'on double plutot qu'un test qu'on cede.
   */
  it('nomme la police officielle SANS CDN, et garde un repli systeme', () => {
    expect(TYPOGRAPHIE.pile.startsWith("'Century Gothic'"), TYPOGRAPHIE.pile).toBe(true);
    expect(TYPOGRAPHIE.pile, 'le repli doit rester lisible sans la fonte').toContain('system-ui');
    expect(TYPOGRAPHIE.pile).not.toMatch(/https?:|url\(|@import/);
    expect(TYPOGRAPHIE.pileMonospace).not.toMatch(/https?:|url\(|@import/);
  });

  it('ne declare que les deux graisses que Century Gothic fournit', () => {
    //  Une troisieme graisse ferait produire au navigateur un faux-gras
    //  synthetique : la fonte n'a que Regular et Bold. La v1 declarait un 600
    //  qu'aucune fonte ne servait.
    expect(Object.values(TYPOGRAPHIE.graisses)).toEqual([400, 700]);
  });
});

/**
 * L'anneau de focus et les accents bleus — charte 1.6 et 5, arbitrage du
 * 02/11/2026.
 *
 * LE SEUIL EST 3, PAS 4,5 : un indicateur de focus et un remplissage de barre
 * de progression sont des elements NON TEXTUELS (WCAG 1.4.11). Les comparer au
 * seuil du texte normal ferait echouer un livrable conforme ; les comparer a
 * rien ne prouverait rien.
 */
describe("l'anneau de focus et le bleu d'accent — charte 1.6, arbitrage du 02/11/2026", () => {
  /** La couleur REELLE d'un trait a 45 % : elle depend du fond qu'il recouvre. */
  const a45Pourcent = (fond: string): string => melangerCouleurs(MARQUE.bleu.surface, fond, 0.45);

  it("ECHOUERAIT si l'anneau gardait les 45 % de transparence de la charte", () => {
    //  LE TEMOIN QUI JUSTIFIE L'ECART. Sans lui, « notre anneau passe » serait
    //  satisfait par n'importe quelle couleur sombre : il faut montrer que la
    //  valeur ECRITE DANS LA CHARTE, elle, ne passe pas — et de combien.
    const surfaces = [
      THEMES.clair.surface,
      THEMES.clair.fond,
      THEMES.sombre.surface,
      THEMES.sombre.fond,
    ];
    const mesures = surfaces.map((fond) => contraste(a45Pourcent(fond), fond));
    expect(mesures).toHaveLength(4);
    for (const mesure of mesures) {
      expect(mesure, `un anneau a 45 % rendrait ${mesure.toFixed(2)}`).toBeLessThan(
        SEUIL_AA_GRAND_TEXTE,
      );
    }
  });

  it('est opaque, et le trait sombre bascule sur --titre', () => {
    expect(ANNEAU_FOCUS.trait).toBe(`3px solid ${MARQUE.bleu.surface}`);
    expect(ANNEAU_FOCUS.traitSombre).toBe(`3px solid ${THEMES.sombre.titre}`);
    //  La transparence ne doit pas revenir par une autre ecriture.
    expect(`${ANNEAU_FOCUS.trait} ${ANNEAU_FOCUS.traitSombre}`).not.toMatch(/rgba?\(|%/);
  });

  it('atteint le seuil non textuel sur les quatre fonds reels', () => {
    const couples: ReadonlyArray<readonly [string, string, string]> = [
      ['clair / surface', MARQUE.bleu.surface, THEMES.clair.surface],
      ['clair / fond', MARQUE.bleu.surface, THEMES.clair.fond],
      ['sombre / surface', THEMES.sombre.titre, THEMES.sombre.surface],
      ['sombre / fond', THEMES.sombre.titre, THEMES.sombre.fond],
    ];
    expect(couples).toHaveLength(4);
    for (const [nom, trait, fond] of couples) {
      const mesure = contraste(trait, fond);
      expect(mesure, `${nom} rend ${mesure.toFixed(2)}`).toBeGreaterThanOrEqual(
        SEUIL_AA_GRAND_TEXTE,
      );
    }
  });

  it("ECHOUERAIT si le bleu d'accent restait --marque-bleu en theme sombre", () => {
    //  LA REGLE QUE `E3` APPLIQUE EN TROIS ENDROITS — anneau de focus, texte du
    //  bouton discret, remplissage de `Progression`. Ce temoin dit POURQUOI.
    const surSurface = contraste(MARQUE.bleu.surface, THEMES.sombre.surface);
    const surFondDoux = contraste(MARQUE.bleu.surface, THEMES.sombre.fondDoux);
    expect(surSurface).toBeLessThan(SEUIL_AA_GRAND_TEXTE);
    expect(surFondDoux).toBeLessThan(SEUIL_AA_GRAND_TEXTE);
    //  Et le texte du bouton discret vise le seuil du TEXTE, plus exigeant.
    expect(surSurface).toBeLessThan(SEUIL_AA_TEXTE_NORMAL);
    expect(contraste(THEMES.sombre.titre, THEMES.sombre.surface)).toBeGreaterThanOrEqual(
      SEUIL_AA_TEXTE_NORMAL,
    );
  });

  it('le bouton discret et le remplissage de progression tiennent leurs seuils', () => {
    //  Texte bleu sur surface claire : seuil TEXTE (le libelle d'un bouton).
    expect(contraste(MARQUE.bleu.surface, THEMES.clair.surface)).toBeGreaterThanOrEqual(
      SEUIL_AA_TEXTE_NORMAL,
    );
    //  Remplissage contre sa piste : seuil NON TEXTUEL, dans les deux themes.
    expect(contraste(MARQUE.bleu.surface, THEMES.clair.fondDoux)).toBeGreaterThanOrEqual(
      SEUIL_AA_GRAND_TEXTE,
    );
    expect(contraste(THEMES.sombre.titre, THEMES.sombre.fondDoux)).toBeGreaterThanOrEqual(
      SEUIL_AA_GRAND_TEXTE,
    );
  });

  it('ECHOUERAIT si la bordure de champ gardait --trait-fort', () => {
    //  Second arbitrage du 02/11/2026. La charte 5 ecrit « bordure trait-fort » :
    //  mesure, elle rend 1,44:1 en clair et 1,93:1 en sombre, soit une bordure
    //  qu'on ne voit pas. `--encre-douce` la remplace.
    expect(contraste(THEMES.clair.traitFort, THEMES.clair.surface)).toBeLessThan(
      SEUIL_AA_GRAND_TEXTE,
    );
    expect(contraste(THEMES.sombre.traitFort, THEMES.sombre.surface)).toBeLessThan(
      SEUIL_AA_GRAND_TEXTE,
    );
    expect(contraste(THEMES.clair.encreDouce, THEMES.clair.surface)).toBeGreaterThanOrEqual(
      SEUIL_AA_GRAND_TEXTE,
    );
    expect(contraste(THEMES.sombre.encreDouce, THEMES.sombre.surface)).toBeGreaterThanOrEqual(
      SEUIL_AA_GRAND_TEXTE,
    );
  });
});
