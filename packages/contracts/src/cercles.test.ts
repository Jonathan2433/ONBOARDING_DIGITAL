/**
 * Le contrat de la page d'un cercle — LOT 6, `T3`.
 *
 * **LA FORME EST CELLE QUE LA PILE A SERVIE**, relevee le 14/09/2026. Un bouchon
 * prouve ce qu'on a ecrit dans le bouchon, jamais ce que l'API fait — §7.43.
 */
import { describe, expect, it } from 'vitest';

import {
  cheminCercle,
  CODES_CERCLE,
  TYPES_D_APPARTENANCE_AU_CERCLE,
  validerLaPageDuCercle,
} from './cercles.js';

const UNE_PAGE = {
  identifiant: 'c1',
  code: 'DATA',
  nom: 'Data',
  description: 'Le cercle Data',
  jeton_de_couleur: 'bleu',
  booster: { identifiant: 'a1', prenom: 'Lea', nom: 'Martin', photo: null },
  membres: [
    {
      appartenance: 'm1',
      prenom: 'Tess',
      nom: 'Durand',
      type_d_appartenance: 'principal',
      photo: '/api/v1/entities/DATA/people/m1/photo',
    },
    {
      appartenance: 'm2',
      prenom: 'Sam',
      nom: 'Petit',
      type_d_appartenance: 'secondary',
      photo: null,
    },
  ],
  total_des_membres: 2,
  page: 1,
  taille: 25,
  pages: 1,
  chemin_detaille: '/entites/BORDEA00/framework/cercles/DATA',
};

//  **LE COUPLE DU §7.42** : le meme cercle SANS jeton et SANS Booster, et sans
//  aucun membre. Ni moitie ne suffit — sans le temoin, un code qui ne rendrait
//  jamais de jeton passerait ; sans le cas, `str(None)` reste invisible.
const UNE_PAGE_NUE = {
  ...UNE_PAGE,
  code: 'FORGE',
  nom: 'Forge',
  description: null,
  jeton_de_couleur: null,
  booster: null,
  membres: [],
  total_des_membres: 0,
  pages: 1,
};

describe('les natures d’appartenance', () => {
  it('sont les DEUX du modele §8.2', () => {
    expect([...TYPES_D_APPARTENANCE_AU_CERCLE]).toEqual(['principal', 'secondary']);
  });
});

describe('les codes exploitables', () => {
  it('annoncent un 422, que la synthese Framework n’a pas', () => {
    //  Le `422` vient de `taille` et de `page` : c'est la seule difference de
    //  forme entre cette route et celle du Framework, qui n'a aucun parametre.
    expect(CODES_CERCLE).toContain(422);
    expect(CODES_CERCLE).toContain(401);
    expect(CODES_CERCLE).toContain(404);
  });

  it('n’annoncent AUCUN 403 — la matrice §5 n’examine aucun role', () => {
    expect(CODES_CERCLE).not.toContain(403);
  });
});

describe('le chemin', () => {
  it('encode ses DEUX segments, et refuse un segment vide', () => {
    expect(cheminCercle('BORDEA 00', 'DATA')).toContain('BORDEA%2000');
    expect(cheminCercle('x', 'a/b')).toContain('a%2Fb');
    //  Un segment vide rendrait le chemin d'une AUTRE ressource.
    expect(() => cheminCercle('', 'DATA')).toThrow(TypeError);
    expect(() => cheminCercle('x', '')).toThrow(TypeError);
  });
});

describe('le validateur', () => {
  it('traduit un cercle peuple', () => {
    const c = validerLaPageDuCercle(UNE_PAGE);
    expect(c.code).toBe('DATA');
    expect(c.membres).toHaveLength(2);
    expect(c.membres[0]?.typeDAppartenance).toBe('principal');
    expect(c.membres[1]?.typeDAppartenance).toBe('secondary');
    expect(c.booster?.nom).toBe('Martin');
  });

  describe('la photo — chantier front hors lot S12 (DEC-673)', () => {
    it('distingue un membre AVEC photo d’un membre SANS, meme cercle', () => {
      //  **LE COUPLE, PAS UNE SEULE MOITIE.** Sans l’un des deux, un validateur
      //  qui rendrait toujours `null` passerait aussi bien que l’inverse.
      const c = validerLaPageDuCercle(UNE_PAGE);
      expect(c.membres[0]?.photo).toBe('/api/v1/entities/DATA/people/m1/photo');
      expect(c.membres[1]?.photo).toBeNull();
    });

    it('rend `null` pour un Booster sans photo, jamais une chaine vide', () => {
      expect(validerLaPageDuCercle(UNE_PAGE).booster?.photo).toBeNull();
    });

    it('refuse un chemin de photo hors du prefixe versionne', () => {
      const corrompue = {
        ...UNE_PAGE,
        membres: [{ ...UNE_PAGE.membres[0], photo: 'https://ailleurs.test/x.jpg' }],
      };
      expect(() => validerLaPageDuCercle(corrompue)).toThrow(TypeError);
    });
  });

  it('rend `null` — et NON la chaine « None » — sur un cercle sans jeton', () => {
    //  **LE CAS QUI A COUTE `T10-8`.**
    const c = validerLaPageDuCercle(UNE_PAGE_NUE);
    expect(c.jetonDeCouleur).toBeNull();
    expect(c.jetonDeCouleur).not.toBe('None');
  });

  it('garantit qu’un cercle a TOUJOURS un nom, meme sans couleur', () => {
    //  Le §8.1 du MODELE : « la couleur ne constitue jamais la seule information
    //  visuelle ». Ce test porte sur la STRUCTURE du contrat, pas sur un rendu.
    for (const page of [UNE_PAGE, UNE_PAGE_NUE]) {
      const c = validerLaPageDuCercle(page);
      expect(c.nom.length).toBeGreaterThan(0);
      expect(c.code.length).toBeGreaterThan(0);
    }
  });

  it('distingue un Booster ABSENT d’un Booster manquant', () => {
    expect(validerLaPageDuCercle(UNE_PAGE_NUE).booster).toBeNull();
    const sansCle: Record<string, unknown> = { ...UNE_PAGE };
    delete sansCle['booster'];
    //  `undefined` n'est ni un objet ni `null` : la reponse est malformee.
    expect(() => validerLaPageDuCercle(sansCle)).toThrow(TypeError);
  });

  it('refuse un tableau de membres ABSENT, la ou vide est accepte', () => {
    //  **LE TEMOIN QUI REND LE PRECEDENT NON TRIVIAL.** Un validateur qui
    //  traduirait l'absence en `[]` passerait les deux, et une reponse tronquee
    //  ressemblerait a un cercle sans membre.
    expect(validerLaPageDuCercle(UNE_PAGE_NUE).membres).toEqual([]);
    const sansMembres: Record<string, unknown> = { ...UNE_PAGE };
    delete sansMembres['membres'];
    expect(() => validerLaPageDuCercle(sansMembres)).toThrow(TypeError);
  });

  it('refuse une taille hors du §18.2', () => {
    //  La laisser passer ferait afficher une page dont la borne n'est plus celle
    //  du cahier — et c'est une reponse que l'API ne devrait pas produire.
    expect(() => validerLaPageDuCercle({ ...UNE_PAGE, taille: 30 })).toThrow(TypeError);
    for (const taille of [25, 50, 100]) {
      expect(validerLaPageDuCercle({ ...UNE_PAGE, taille }).taille).toBe(taille);
    }
  });

  it('refuse `pages` a zero — il vaut AU MOINS 1, meme sans membre', () => {
    //  `0` ne distinguerait pas « aucun membre » de « chargement ».
    expect(() => validerLaPageDuCercle({ ...UNE_PAGE_NUE, pages: 0 })).toThrow(TypeError);
    expect(validerLaPageDuCercle(UNE_PAGE_NUE).pages).toBe(1);
  });

  it.each(['identifiant', 'code', 'nom', 'chemin_detaille'])(
    'refuse une page sans « %s »',
    (champ) => {
      const partielle: Record<string, unknown> = { ...UNE_PAGE };
      delete partielle[champ];
      expect(() => validerLaPageDuCercle(partielle)).toThrow(TypeError);
    },
  );
});
