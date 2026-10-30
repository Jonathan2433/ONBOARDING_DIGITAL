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
  SEUIL_AA_TEXTE_NORMAL,
} from './contraste.js';
import {
  ACCENTS_ADMIS,
  DEGRADE_MARQUE,
  ESPACEMENTS,
  LARGEURS_RECETTE,
  MARQUE,
  RAYONS,
  SEUIL_ACCENT,
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

describe('le degrade de marque — chantier front, DEC-672', () => {
  it('va bien du bleu au rose, et rien d autre — pas de troisieme teinte', () => {
    expect(DEGRADE_MARQUE.de).toBe(MARQUE.bleu.surface);
    expect(DEGRADE_MARQUE.vers).toBe(MARQUE.rose.surface);
    expect(DEGRADE_MARQUE.css).toBe(
      `linear-gradient(135deg, ${MARQUE.bleu.surface}, ${MARQUE.rose.surface})`,
    );
  });

  // CINQ POINTS LE LONG DU DEGRADE, PAS SEULEMENT SES DEUX BORNES. Un controle
  // qui ne mesurerait que `de` et `vers` manquerait tout defaut vivant ENTRE les
  // deux — meme principe que le §7.38 de la passation, « mesurer la grandeur
  // qu'une hypothese predit, pas une grandeur voisine ».
  const POINTS = [0, 0.25, 0.5, 0.75, 1] as const;
  const couleursDuDegrade = POINTS.map(
    (t) => [t, melangerCouleurs(DEGRADE_MARQUE.de, DEGRADE_MARQUE.vers, t)] as const,
  );

  it('ne peut pas etre mesure a moins de cinq points', () => {
    // Le compte, pas seulement son contenu : un tableau vide passerait les
    // `it.each` suivants sans jamais les executer.
    expect(couleursDuDegrade).toHaveLength(5);
  });

  // LA PREMIERE VERSION DE CE TEST SUPPOSAIT QU'UN DES DEUX TEXTES RESTE
  // TOUJOURS LISIBLE, PARTOUT SUR LE DEGRADE — ET LA MESURE L'A REFUTEE. A
  // t=0,75 (#d536b4), le blanc rend 4,19 et le texte sombre 4,16 : LES DEUX
  // echouent au seuil de 4,5. Il existe donc une ZONE MORTE du degrade ou
  // AUCUNE couleur de texte, ni l'une ni l'autre, n'atteint AA — pas seulement
  // une zone ou une des deux suffit. C'est une justification PLUS FORTE encore
  // de la regle « jamais de texte en clair sur ce degrade » que ce qui avait
  // ete suppose avant de mesurer.
  it('a t=0,75, NI LE BLANC NI LE TEXTE SOMBRE n atteignent AA — une zone morte reelle', () => {
    const milieu = melangerCouleurs(DEGRADE_MARQUE.de, DEGRADE_MARQUE.vers, 0.75);
    const avecBlanc = contraste(milieu, '#FFFFFF');
    const avecSombre = contraste(milieu, '#1A1A1A');
    expect(avecBlanc, `blanc sur ${milieu}`).toBeLessThan(SEUIL_AA_TEXTE_NORMAL);
    expect(avecSombre, `sombre sur ${milieu}`).toBeLessThan(SEUIL_AA_TEXTE_NORMAL);
  });

  // LA RAISON D'ETRE DE LA REGLE « JAMAIS DE TEXTE EN CLAIR SUR LE DEGRADE » :
  // AUCUNE des deux couleurs de texte ne couvre a elle seule les CINQ points.
  // Si l'une le faisait, la regle du commentaire de `jetons.ts` serait une
  // precaution inutile plutot qu'une necessite mesuree.
  it('confirme qu AUCUNE couleur de texte unique ne couvre tout le degrade', () => {
    const toutBlanc = couleursDuDegrade.every(
      ([, couleur]) => contraste(couleur, '#FFFFFF') >= SEUIL_AA_TEXTE_NORMAL,
    );
    const toutSombre = couleursDuDegrade.every(
      ([, couleur]) => contraste(couleur, '#1A1A1A') >= SEUIL_AA_TEXTE_NORMAL,
    );
    expect(toutBlanc, 'le blanc suffirait partout : la regle serait superflue').toBe(false);
    expect(toutSombre, 'le sombre suffirait partout : la regle serait superflue').toBe(false);
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
  const surfaces = ['fond', 'fondDoux'] as const;
  const encres = ['encre', 'encreDouce', 'ok', 'ko'] as const;
  const couples = (['clair', 'sombre'] as const).flatMap((theme) =>
    surfaces.flatMap((surface) =>
      encres.map(
        (n) => [`${theme}/${n} sur ${surface}`, THEMES[theme][surface], THEMES[theme][n]] as const,
      ),
    ),
  );

  it('forme bien les SEIZE couples attendus — deux themes, deux surfaces, quatre encres', () => {
    expect(couples).toHaveLength(16);
  });

  it.each(couples)('%s atteint AA pour du texte normal', (nom, fond, couleur) => {
    const mesure = contraste(fond, couleur);
    expect(mesure, `${nom} rend ${mesure.toFixed(2)}`).toBeGreaterThanOrEqual(
      SEUIL_AA_TEXTE_NORMAL,
    );
  });

  it('garde les noms de T5 : renommer ferait divorcer la page de son design system', () => {
    const attendus = ['fond', 'fondDoux', 'encre', 'encreDouce', 'trait', 'ok', 'ko'];
    expect(Object.keys(THEMES.clair)).toEqual(attendus);
    expect(Object.keys(THEMES.sombre)).toEqual(attendus);
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

  it('ne telecharge aucune police : la pile est SYSTEME (cahier 13.1, roadmap 2.3)', () => {
    expect(TYPOGRAPHIE.pile).toContain('system-ui');
    expect(TYPOGRAPHIE.pile).not.toMatch(/https?:|url\(|@import/);
    expect(TYPOGRAPHIE.pileMonospace).not.toMatch(/https?:|url\(|@import/);
  });
});
