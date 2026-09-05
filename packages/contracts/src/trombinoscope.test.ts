/**
 * Le contrat du trombinoscope, cote TypeScript — LOT 5, `T2`.
 *
 * CE QUE CES TESTS PROUVENT
 *
 *   Que le chemin est LU DU MANIFESTE et non recopie, et que le validateur
 *   REFUSE ce qui n'a pas la forme attendue. Un validateur qui accepterait tout
 *   donnerait la meme observation qu'un validateur correct sur une reponse
 *   valide -- §7.0, quatrieme proposition. Chaque refus a donc son test.
 *
 *   **ET LES QUATRE NOMBRES DE L'ENVELOPPE ONT CHACUN LE LEUR.** C'est la
 *   classe de defaut la plus insidieuse ici : un `total` absent qui vaudrait 0
 *   serait indistinguable d'un trombinoscope legitimement vide.
 */
import { describe, expect, it } from 'vitest';

import {
  cheminTrombinoscope,
  CODES_TROMBINOSCOPE,
  CONTRAT_API,
  GABARIT_CHEMIN_TROMBINOSCOPE,
  TAILLE_PAR_DEFAUT,
  TAILLES_DE_PAGE,
  validerLeTrombinoscope,
} from './index';

const UNE_LIGNE = {
  id: '0f8fad5b-d9cb-469f-a165-70867728950e',
  person_id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
  first_name: 'Ada',
  last_name: 'Lovelace',
  preferred_name: null,
  professional_category: 'consultant',
  arrival_date: '2026-01-15',
};

const UNE_PAGE = {
  collaborateurs: [UNE_LIGNE],
  page: 1,
  taille: 25,
  total: 1,
  pages: 1,
};

describe('le chemin', () => {
  it('est lu du manifeste, jamais recopie', () => {
    const declare = CONTRAT_API.endpoints.find((e) => e.cle === 'trombinoscopeDeLEntite');
    expect(GABARIT_CHEMIN_TROMBINOSCOPE).toBe(declare?.chemin);
    expect(GABARIT_CHEMIN_TROMBINOSCOPE).toContain('{code}');
  });

  it('n’annonce AUCUN 403 — la matrice §5 ne distingue aucun role', () => {
    expect([...CODES_TROMBINOSCOPE].sort((a, b) => a - b)).toEqual([200, 401, 404, 422]);
  });

  it('encode le code, sinon le chemin obtenu serait celui d’une autre ressource', () => {
    expect(cheminTrombinoscope('bor deaux/x')).toBe('/api/v1/entities/bor%20deaux%2Fx/people');
  });

  it('leve sur un code vide plutot que de viser la liste des entites', () => {
    expect(() => cheminTrombinoscope('')).toThrow(TypeError);
  });

  it('n’ajoute une chaine de requete que lorsqu’on lui donne des valeurs', () => {
    expect(cheminTrombinoscope('bordeaux')).toBe('/api/v1/entities/bordeaux/people');
    expect(cheminTrombinoscope('bordeaux', 2)).toBe('/api/v1/entities/bordeaux/people?page=2');
    expect(cheminTrombinoscope('bordeaux', 2, 50)).toBe(
      '/api/v1/entities/bordeaux/people?page=2&taille=50',
    );
    expect(cheminTrombinoscope('bordeaux', undefined, 100)).toBe(
      '/api/v1/entities/bordeaux/people?taille=100',
    );
  });
});

describe('les trois tailles', () => {
  it('sont celles du cahier §18.2, et le defaut en fait partie', () => {
    expect(TAILLES_DE_PAGE).toEqual([25, 50, 100]);
    expect(TAILLES_DE_PAGE).toContain(TAILLE_PAR_DEFAUT);
    expect(TAILLE_PAR_DEFAUT).toBe(25);
    expect(Math.max(...TAILLES_DE_PAGE)).toBe(100);
  });
});

describe('le validateur', () => {
  it('accepte une page bien formee et traduit vers le camelCase', () => {
    const page = validerLeTrombinoscope(UNE_PAGE);
    expect(page.collaborateurs[0]).toEqual({
      id: UNE_LIGNE.id,
      personneId: UNE_LIGNE.person_id,
      prenom: 'Ada',
      nom: 'Lovelace',
      nomPrefere: null,
      categorieProfessionnelle: 'consultant',
      dateArrivee: '2026-01-15',
    });
    expect(page.total).toBe(1);
  });

  it('accepte un nom prefere renseigne', () => {
    const page = validerLeTrombinoscope({
      ...UNE_PAGE,
      collaborateurs: [{ ...UNE_LIGNE, preferred_name: 'Ada L.' }],
    });
    expect(page.collaborateurs[0]?.nomPrefere).toBe('Ada L.');
  });

  it('refuse une reponse sans tableau — sinon elle vaudrait « aucun collaborateur »', () => {
    expect(() => validerLeTrombinoscope({})).toThrow(TypeError);
    expect(() => validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: null })).toThrow(TypeError);
  });

  it('refuse un non-objet', () => {
    expect(() => validerLeTrombinoscope(null)).toThrow(TypeError);
    expect(() => validerLeTrombinoscope('texte')).toThrow(TypeError);
  });

  //  **CHACUN DES QUATRE NOMBRES A SON TEST**, parce que l'absence de l'un
  //  d'eux ne doit PAS valoir 0 : 0 est la valeur d'un trombinoscope vide, donc
  //  l'echec produirait la meme observation que le succes.
  it.each(['page', 'taille', 'total', 'pages'])('refuse « %s » absent', (champ) => {
    const ampute: Record<string, unknown> = { ...UNE_PAGE };
    delete ampute[champ];
    expect(() => validerLeTrombinoscope(ampute)).toThrow(TypeError);
  });

  it.each(['page', 'taille', 'total', 'pages'])('refuse « %s » non nombre', (champ) => {
    expect(() => validerLeTrombinoscope({ ...UNE_PAGE, [champ]: '1' })).toThrow(TypeError);
  });

  it.each(['id', 'person_id', 'first_name', 'last_name', 'professional_category', 'arrival_date'])(
    'refuse une ligne dont « %s » manque',
    (champ) => {
      const ligne: Record<string, unknown> = { ...UNE_LIGNE };
      delete ligne[champ];
      expect(() => validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: [ligne] })).toThrow(
        TypeError,
      );
    },
  );

  it('refuse un « preferred_name » qui n’est ni chaine ni null', () => {
    expect(() =>
      validerLeTrombinoscope({
        ...UNE_PAGE,
        collaborateurs: [{ ...UNE_LIGNE, preferred_name: 42 }],
      }),
    ).toThrow(TypeError);
  });

  it('refuse une ligne non objet', () => {
    expect(() => validerLeTrombinoscope({ ...UNE_PAGE, collaborateurs: ['x'] })).toThrow(TypeError);
  });
});
