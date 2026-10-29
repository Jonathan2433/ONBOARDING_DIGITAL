/**
 * Le contrat de la page detaillee d'un bureau — LOT 6, `T4`, `MVP-L06-US003`.
 *
 * CE QUE CETTE SUITE EPROUVE, ET QUI EST L'INVERSE DE `cercles.test.ts`
 *
 *   Le contrat du cercle REFUSE une taille hors du §18.2 : la borne est tenue,
 *   donc une reponse qui l'enfreint est malformee.
 *
 *   Ici la borne du §8.4 n'est **pas** tenue en base — le declencheur est en
 *   `T7`, `DEC-583` — si bien qu'un bureau a zero ou a quatre responsables est
 *   une reponse **legitime** de l'API d'aujourd'hui. La refuser ferait echouer
 *   l'ecran sur un etat reel. Le validateur l'accepte donc, et une fonction
 *   separee porte la QUESTION de la conformite.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminBureau,
  CODES_BUREAU,
  GABARIT_CHEMIN_BUREAU,
  respecteLaBorneDuHuitQuatre,
  RESPONSABLES_MAXIMUM,
  RESPONSABLES_MINIMUM,
  validerLaPageDuBureau,
} from './bureaux.js';

const RESPONSABLE = {
  identifiant: 'r1',
  prenom: 'Ada',
  nom: 'Lovelace',
  //  Chantier front hors lot, S12 (DEC-673).
  photo: null,
};

function charge(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 'b1',
    code: 'SPORT',
    nom: 'Bureau des sports',
    description: null,
    localisation: null,
    responsables: [RESPONSABLE],
    nombre_de_responsables: 1,
    publie: true,
    chemin_detaille: '/entites/BDX/framework/bureaux/SPORT',
    ...modifications,
  };
}

describe('le chemin', () => {
  it('vient du manifeste et non d’une chaine ecrite ici', () => {
    //  `DEC-492` : le manifeste est la source UNIQUE, lue par TypeScript ET par
    //  Python. Une seconde ecriture du chemin divergerait au premier changement.
    expect(GABARIT_CHEMIN_BUREAU).toBe('/api/v1/entities/{code}/offices/{code_bureau}');
    expect(CODES_BUREAU).toEqual([200, 401, 404]);
  });

  it('encode les DEUX segments', () => {
    expect(cheminBureau('BD X', 'A/B')).toBe('/api/v1/entities/BD%20X/offices/A%2FB');
  });

  it('LEVE sur un segment vide, parce que le chemin obtenu designerait autre chose', () => {
    expect(() => cheminBureau('', 'SPORT')).toThrow(TypeError);
    expect(() => cheminBureau('BDX', '')).toThrow(TypeError);
    //  Le temoin : deux segments non vides passent.
    expect(() => cheminBureau('BDX', 'SPORT')).not.toThrow();
  });
});

describe('la borne du §8.4 est ACCEPTEE par le validateur, jamais imposee', () => {
  it('accepte ZERO responsable — ce que le §8.4 interdit, et que la base permet', () => {
    const lu = validerLaPageDuBureau(charge({ responsables: [], nombre_de_responsables: 0 }));

    expect(lu.responsables).toEqual([]);
    expect(lu.nombreDeResponsables).toBe(0);
  });

  it('accepte QUATRE responsables, et les rend TOUS LES QUATRE', () => {
    const quatre = [1, 2, 3, 4].map((n) => ({ ...RESPONSABLE, identifiant: `r${String(n)}` }));
    const lu = validerLaPageDuBureau(charge({ responsables: quatre, nombre_de_responsables: 4 }));

    //  Un validateur qui aurait tronque a `RESPONSABLES_MAXIMUM` aurait MENTI.
    expect(lu.responsables).toHaveLength(4);
    expect(lu.nombreDeResponsables).toBe(4);
  });
});

describe('les deux grandeurs doivent s’accorder — §7.0, sixieme proposition', () => {
  it('REFUSE un compte qui ne vaut pas la longueur du tableau', () => {
    expect(() =>
      validerLaPageDuBureau(charge({ responsables: [RESPONSABLE], nombre_de_responsables: 3 })),
    ).toThrow(/vaut 3 pour 1 responsable/);
  });

  it('le TEMOIN : quand ils s’accordent, la charge passe', () => {
    //  Sans ce temoin, un validateur qui refuserait TOUT donnerait la meme
    //  observation que le test precedent.
    expect(() => validerLaPageDuBureau(charge())).not.toThrow();
  });
});

describe('les champs que l’API peut rendre absents', () => {
  it('accepte `localisation` et `description` a null — le §8.3 les dit facultatifs', () => {
    const lu = validerLaPageDuBureau(charge());

    expect(lu.localisation).toBeNull();
    expect(lu.description).toBeNull();
  });

  it('le TEMOIN : quand elles sont renseignees, elles sont servies telles quelles', () => {
    const lu = validerLaPageDuBureau(
      charge({ localisation: 'Bordeaux, 2e etage', description: 'Les tournois' }),
    );

    expect(lu.localisation).toBe('Bordeaux, 2e etage');
    expect(lu.description).toBe('Les tournois');
  });

  it('REFUSE un champ ABSENT, qui n’est pas la meme chose qu’un champ a null', () => {
    const sansLocalisation = charge();
    delete sansLocalisation['localisation'];

    expect(() => validerLaPageDuBureau(sansLocalisation)).toThrow(/ni chaine ni null/);
  });

  it('REFUSE un tableau de responsables absent — ce n’est pas un tableau vide', () => {
    const sansTableau = charge();
    delete sansTableau['responsables'];

    //  La difference compte doublement : zero responsable est justement
    //  l'anomalie que le §8.4 vise, et la fabriquer serait un faux signal.
    expect(() => validerLaPageDuBureau(sansTableau)).toThrow(/n’est pas un tableau/);
  });
});

describe('`publie` n’est jamais coerce', () => {
  it('REFUSE une valeur qui n’est pas un booleen', () => {
    expect(() => validerLaPageDuBureau(charge({ publie: 'true' }))).toThrow(/booleen/);
  });

  it('REFUSE l’absence, qui serait tombee sur `false`', () => {
    const sansPublie = charge();
    delete sansPublie['publie'];

    //  Un `Boolean(undefined)` aurait rendu `false` : le bureau aurait paru
    //  brouillon, donc conforme au §8.4 quoi qu'il arrive.
    expect(() => validerLaPageDuBureau(sansPublie)).toThrow(/booleen/);
  });

  it('le TEMOIN : `false` est une valeur legitime et passe', () => {
    const lu = validerLaPageDuBureau(
      charge({ publie: false, responsables: [], nombre_de_responsables: 0 }),
    );

    expect(lu.publie).toBe(false);
  });
});

describe('la photo d’un responsable — chantier front hors lot S12 (DEC-673)', () => {
  it('distingue un responsable AVEC photo d’un responsable SANS, meme bureau', () => {
    //  **LE COUPLE, PAS UNE SEULE MOITIE** — meme motif que `cercles.test.ts`.
    const avecPhoto = { ...RESPONSABLE, photo: '/api/v1/entities/BDX/people/r1/photo' };
    const sansPhoto = { ...RESPONSABLE, identifiant: 'r2' };
    const lu = validerLaPageDuBureau(
      charge({ responsables: [avecPhoto, sansPhoto], nombre_de_responsables: 2 }),
    );

    expect(lu.responsables[0]?.photo).toBe('/api/v1/entities/BDX/people/r1/photo');
    expect(lu.responsables[1]?.photo).toBeNull();
  });

  it('refuse un chemin de photo hors du prefixe versionne', () => {
    const corrompu = { ...RESPONSABLE, photo: 'https://ailleurs.test/x.jpg' };
    expect(() => validerLaPageDuBureau(charge({ responsables: [corrompu] }))).toThrow(TypeError);
  });
});

describe('respecteLaBorneDuHuitQuatre — une QUESTION, pas une exigence', () => {
  function bureau(publie: boolean, combien: number) {
    const responsables = Array.from({ length: combien }, (_, n) => ({
      ...RESPONSABLE,
      identifiant: `r${String(n)}`,
    }));
    return validerLaPageDuBureau(charge({ publie, responsables, nombre_de_responsables: combien }));
  }

  it.each([
    [0, false, 'un bureau PUBLIE sans responsable enfreint le §8.4'],
    [1, true, 'le minimum'],
    [2, true, 'entre les deux'],
    [3, true, 'le maximum'],
    [4, false, 'un de trop enfreint aussi'],
  ])('publie avec %i responsable(s) : conforme=%s — %s', (combien, attendu) => {
    //  Le motif est le TROISIEME element de chaque ligne : il est rendu dans le
    //  titre du test par `%s`, donc lisible dans la sortie, sans etre un
    //  parametre inutilise que le lint refuse.
    expect(respecteLaBorneDuHuitQuatre(bureau(true, combien))).toBe(attendu);
  });

  it('un bureau NON PUBLIE a zero responsable n’enfreint RIEN', () => {
    //  « lorsqu'il est publie » : la borne ne mord qu'a partir de la. C'est le
    //  temoin qui rend la ligne « publie, zero -> false » non triviale.
    expect(respecteLaBorneDuHuitQuatre(bureau(false, 0))).toBe(true);
  });

  it('les deux bornes sont celles que le §8.4 ecrit', () => {
    expect([RESPONSABLES_MINIMUM, RESPONSABLES_MAXIMUM]).toEqual([1, 3]);
  });
});
