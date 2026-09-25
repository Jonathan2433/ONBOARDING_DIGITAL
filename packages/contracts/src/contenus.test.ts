/**
 * Le contrat du rendu des blocs — LOT 6, `T5`, `MVP-L06-US004` (1 sur 3).
 *
 * LE TEST CENTRAL N'EST PAS UN REFUS
 *
 *   « Aucun HTML arbitraire » se satisfait tout seul quand rien n'est rendu
 *   (§7.39). Le test qui compte est donc qu'un bloc **legitime** passe, et que
 *   du balisage passe **comme du texte** — parce que c'est la preuve que cette
 *   couche sert des donnees et n'interprete rien.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminPageDeContenu,
  CODES_PAGE_DE_CONTENU,
  GABARIT_CHEMIN_PAGE_DE_CONTENU,
  texteDuBloc,
  TYPES_DE_PAGE_NOMMES,
  validerLaPageDeContenu,
} from './contenus.js';

const INJECTION = "<script>alert('xss')</script>";

function bloc(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 'b1',
    type_de_bloc: 'RICH_TEXT',
    ordre: 1,
    contenu: { texte: 'bonjour' },
    ...modifications,
  };
}

function charge(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 'p1',
    type_de_page: 'HOME',
    titre: 'Accueil',
    slug: 'accueil',
    publiee_le: '2026-01-01T00:00:00+00:00',
    blocs: [bloc()],
    nombre_de_blocs: 1,
    ...modifications,
  };
}

describe('le chemin', () => {
  it('vient du manifeste et non d’une chaine ecrite ici', () => {
    expect(GABARIT_CHEMIN_PAGE_DE_CONTENU).toBe(
      '/api/v1/entities/{code}/pages/{type_de_page}/{slug}',
    );
    expect(CODES_PAGE_DE_CONTENU).toEqual([200, 401, 404]);
  });

  it('encode les TROIS segments', () => {
    expect(cheminPageDeContenu('BD X', 'HOME', 'a/b')).toBe(
      '/api/v1/entities/BD%20X/pages/HOME/a%2Fb',
    );
  });

  it('LEVE sur un segment vide', () => {
    expect(() => cheminPageDeContenu('', 'HOME', 'x')).toThrow(TypeError);
    expect(() => cheminPageDeContenu('BDX', '', 'x')).toThrow(TypeError);
    expect(() => cheminPageDeContenu('BDX', 'HOME', '')).toThrow(TypeError);
    //  Le temoin : trois segments non vides passent.
    expect(() => cheminPageDeContenu('BDX', 'HOME', 'x')).not.toThrow();
  });
});

describe('le balisage traverse comme du TEXTE — le propos de T5', () => {
  it('un bloc legitime passe — LE TEMOIN qui rend le critere negatif non trivial', () => {
    const page = validerLaPageDeContenu(charge());

    expect(page.nombreDeBlocs).toBe(1);
    expect(page.blocs[0]?.typeDeBloc).toBe('RICH_TEXT');
    expect(texteDuBloc(page.blocs[0]!, 'texte')).toBe('bonjour');
  });

  it('un payload contenant du balisage est rendu INTACT, comme une chaine', () => {
    const page = validerLaPageDeContenu(
      charge({ blocs: [bloc({ contenu: { texte: INJECTION } })] }),
    );

    const texte = texteDuBloc(page.blocs[0]!, 'texte');
    //  **CE N'EST PAS UN DEFAUT : C'EST LA PREUVE.** La valeur arrive comme une
    //  `string`, et le type de retour de `texteDuBloc` ne peut rien rendre
    //  d'autre. Un ecran l'affiche donc comme du texte (§7.35).
    expect(typeof texte).toBe('string');
    expect(texte).toBe(INJECTION);
  });

  it('`texteDuBloc` rend la chaine VIDE sur une valeur non textuelle ou absente', () => {
    const page = validerLaPageDeContenu(charge({ blocs: [bloc({ contenu: { nombre: 42 } })] }));

    //  Une chaine vide affiche un bloc vide — visible. `undefined` afficherait
    //  « undefined » a l'ecran, ce qu'aucun relecteur ne comprendrait.
    expect(texteDuBloc(page.blocs[0]!, 'texte')).toBe('');
    expect(texteDuBloc(page.blocs[0]!, 'nombre')).toBe('');
  });
});

describe('le contenu d’un bloc doit etre un OBJET — §15.2, « champs structures »', () => {
  it.each([
    ['une chaine nue', 'du texte'],
    ['un nombre', 42],
    ['un tableau', ['a', 'b']],
    ['null', null],
  ])('REFUSE %s', (_nom, valeur) => {
    expect(() => validerLaPageDeContenu(charge({ blocs: [bloc({ contenu: valeur })] }))).toThrow(
      /n’est pas un objet/,
    );
  });

  it('le TEMOIN : un objet passe, meme VIDE', () => {
    //  Un bloc au contenu vide est legitime : les clefs ne sont pas contraintes
    //  (`QO-121`), donc l'absence de clef n'est pas une malformation.
    expect(() => validerLaPageDeContenu(charge({ blocs: [bloc({ contenu: {} })] }))).not.toThrow();
  });
});

describe('l’ordre est VERIFIE, jamais retrie', () => {
  it('REFUSE des blocs hors ordre', () => {
    const desordre = [bloc({ identifiant: 'b1', ordre: 2 }), bloc({ identifiant: 'b2', ordre: 1 })];

    //  Retrier ici masquerait une API qui aurait cesse de trier, et l'ecran
    //  afficherait le desordre le jour ou ce contrat serait retire (§7.35).
    expect(() => validerLaPageDeContenu(charge({ blocs: desordre, nombre_de_blocs: 2 }))).toThrow(
      /non ordonnes/,
    );
  });

  it('le TEMOIN : dans l’ordre, la charge passe — et les rangs EGAUX sont tolerés', () => {
    const ordonne = [bloc({ identifiant: 'b1', ordre: 1 }), bloc({ identifiant: 'b2', ordre: 1 })];

    expect(() =>
      validerLaPageDeContenu(charge({ blocs: ordonne, nombre_de_blocs: 2 })),
    ).not.toThrow();
  });
});

describe('les deux grandeurs doivent s’accorder — §7.0, sixieme proposition', () => {
  it('REFUSE un compte qui ne vaut pas la longueur du tableau', () => {
    expect(() => validerLaPageDeContenu(charge({ nombre_de_blocs: 3 }))).toThrow(
      /vaut 3 pour 1 bloc/,
    );
  });

  it('le TEMOIN : quand ils s’accordent, la charge passe', () => {
    expect(() => validerLaPageDeContenu(charge())).not.toThrow();
  });
});

describe('les etats que l’API peut legitimement rendre', () => {
  it('accepte une page SANS AUCUN BLOC — c’est un etat valide, pas une erreur', () => {
    const page = validerLaPageDeContenu(charge({ blocs: [], nombre_de_blocs: 0 }));

    expect(page.blocs).toEqual([]);
    expect(page.nombreDeBlocs).toBe(0);
  });

  it('REFUSE un tableau de blocs absent — ce n’est pas un tableau vide', () => {
    const sansBlocs = charge();
    delete sansBlocs['blocs'];

    expect(() => validerLaPageDeContenu(sansBlocs)).toThrow(/n’est pas un tableau/);
  });

  it('accepte `publiee_le` a null — le §15.1 ne lie PAS `state` a `published_at`', () => {
    expect(validerLaPageDeContenu(charge({ publiee_le: null })).publieeLe).toBeNull();
  });

  it('REFUSE `publiee_le` absent, qui n’est pas la meme chose que null', () => {
    const sansDate = charge();
    delete sansDate['publiee_le'];

    expect(() => validerLaPageDeContenu(sansDate)).toThrow(/ni chaine ni null/);
  });
});

describe('la liste des types de page est CONTROLEE, pas FERMEE', () => {
  it('nomme les cinq que le §15.1 ecrit', () => {
    expect(TYPES_DE_PAGE_NOMMES).toEqual(['HOME', 'FRAMEWORK', 'CIRCLE', 'OFFICE', 'LEGAL']);
  });

  it('n’en REFUSE pas un que le modele n’a pas encore nomme', () => {
    //  Le §15.1 s'ouvre par « …, **autre type controle** ». Fermer la liste ici
    //  bloquerait un lot ulterieur — l'erreur symetrique de celle du LOT 3 sur
    //  les scopes, §7.29 : les deux lectures fautives se font face.
    const page = validerLaPageDeContenu(charge({ type_de_page: 'EVENT' }));

    expect(page.typeDePage).toBe('EVENT');
  });
});
