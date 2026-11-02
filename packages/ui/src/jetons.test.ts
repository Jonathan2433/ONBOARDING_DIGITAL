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

import { atteintSeuil, contraste, luminance, SEUIL_AA_TEXTE_NORMAL } from './contraste.js';
import {
  ACCENTS_ADMIS,
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

describe('les quatre teintes — charte 2', () => {
  const couples = Object.entries(TEINTES);

  it('sont bien quatre, et aucune ne redeclare une couleur de marque', () => {
    expect(couples).toHaveLength(4);
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
