/**
 * Le depot et l'autorisation d'une photo de profil — LOT 11, `T2`.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminAutorisationPhoto,
  cheminDepotDePhoto,
  cheminDroitsDePhoto,
  cheminEtatDUnMedia,
  cheminRetraitAutorisationPhoto,
  validerLAutorisation,
  validerLeDepotDePhoto,
  validerLeRetrait,
  validerLesDroitsDePhoto,
  validerLEtatDUnMedia,
} from './media.js';

describe('les chemins de la photo — segments encodes, jamais vides', () => {
  it('le depot, les droits et les deux routes d’autorisation portent code + appartenance', () => {
    expect(cheminDepotDePhoto('exalt', 'a 1')).toBe('/api/v1/entities/exalt/people/a%201/photo');
    expect(cheminDroitsDePhoto('exalt', 'a1')).toBe(
      '/api/v1/entities/exalt/people/a1/photo/droits',
    );
    expect(cheminAutorisationPhoto('exalt', 'a1')).toBe(
      '/api/v1/entities/exalt/people/a1/photo/autorisation',
    );
    expect(cheminRetraitAutorisationPhoto('exalt', 'a1')).toBe(
      '/api/v1/entities/exalt/people/a1/photo/autorisation/retrait',
    );
  });

  it('l’etat d’un media porte code + media, jamais appartenance', () => {
    expect(cheminEtatDUnMedia('exalt', 'm 1')).toBe('/api/v1/entities/exalt/media/m%201/etat');
  });

  it('refuse un code d’entite ou un segment vide', () => {
    expect(() => cheminDepotDePhoto('', 'a1')).toThrow(TypeError);
    expect(() => cheminDepotDePhoto('exalt', '')).toThrow(TypeError);
    expect(() => cheminEtatDUnMedia('exalt', '')).toThrow(TypeError);
  });
});

describe('validerLeDepotDePhoto', () => {
  it('accepte une reponse pending', () => {
    expect(validerLeDepotDePhoto({ id: 'm1', state: 'pending' })).toStrictEqual({
      identifiant: 'm1',
      etat: 'pending',
    });
  });

  it('refuse une charge non objet', () => {
    expect(() => validerLeDepotDePhoto(null)).toThrow(TypeError);
  });
});

describe('validerLesDroitsDePhoto', () => {
  it('accepte les deux booleens', () => {
    expect(
      validerLesDroitsDePhoto({ peut_deposer: true, peut_gerer_autorisation: false }),
    ).toStrictEqual({ peutDeposer: true, peutGererAutorisation: false });
  });

  it('refuse un champ absent', () => {
    expect(() => validerLesDroitsDePhoto({ peut_deposer: true })).toThrow(TypeError);
  });
});

describe('validerLEtatDUnMedia', () => {
  it('accepte un media ready, sans code de rejet', () => {
    expect(validerLEtatDUnMedia({ id: 'm1', state: 'ready', rejection_code: null })).toStrictEqual({
      identifiant: 'm1',
      etat: 'ready',
      codeDeRejet: null,
    });
  });

  it('accepte un media rejete, avec son code', () => {
    expect(
      validerLEtatDUnMedia({ id: 'm1', state: 'rejected', rejection_code: 'contenu_illisible' }),
    ).toStrictEqual({ identifiant: 'm1', etat: 'rejected', codeDeRejet: 'contenu_illisible' });
  });

  it('refuse un code de rejet ni chaine ni null', () => {
    expect(() => validerLEtatDUnMedia({ id: 'm1', state: 'rejected', rejection_code: 42 })).toThrow(
      TypeError,
    );
  });
});

describe('validerLAutorisation', () => {
  it('accepte une autorisation accordee', () => {
    expect(validerLAutorisation({ id: 'auth1', granted_at: '2026-10-31T09:00:00Z' })).toStrictEqual(
      { identifiant: 'auth1', accordeeLe: '2026-10-31T09:00:00Z' },
    );
  });
});

describe('validerLeRetrait', () => {
  it('accepte zero — idempotent, ce n’est pas un refus', () => {
    expect(validerLeRetrait({ autorisations_retirees: 0 })).toStrictEqual({
      autorisationsRetirees: 0,
    });
  });

  it('accepte un compte positif', () => {
    expect(validerLeRetrait({ autorisations_retirees: 2 })).toStrictEqual({
      autorisationsRetirees: 2,
    });
  });

  it('refuse un compte non entier', () => {
    expect(() => validerLeRetrait({ autorisations_retirees: 1.5 })).toThrow(TypeError);
  });
});
