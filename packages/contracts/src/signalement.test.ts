/**
 * Le contrat du signalement d'un bug — LOT 10, `T11`, `MVP-L10-US005`.
 */
import { describe, expect, it } from 'vitest';

import { CHEMIN_SIGNALEMENT, CODES_SIGNALEMENT, validerUnSignalement } from './signalement.js';

describe('le chemin', () => {
  it('est une constante, sans code d’entite — voir l’en-tete du module', () => {
    expect(CHEMIN_SIGNALEMENT).toBe('/api/v1/bug-reports');
  });
});

describe('les codes exploitables', () => {
  it('annoncent 401, 403 et 422 — 403 vient du CSRF, jamais d’un role refuse', () => {
    //  `DEC-531` : les deux barrieres anti-CSRF protegent CETTE ecriture comme
    //  toutes les autres. « Aucun role refuse » reste vrai — voir
    //  `app/support/routes.py` — mais un 403 existe bel et bien, pour une
    //  AUTRE cause.
    expect(CODES_SIGNALEMENT).toContain(401);
    expect(CODES_SIGNALEMENT).toContain(403);
    expect(CODES_SIGNALEMENT).toContain(422);
  });
});

describe('le validateur', () => {
  it('valide une reponse complete, en camelCase', () => {
    const signalement = validerUnSignalement({
      identifiant: 's1',
      etat: 'new',
      cree_le: '2026-10-21T10:00:00+00:00',
    });
    expect(signalement).toEqual({
      identifiant: 's1',
      etat: 'new',
      creeLe: '2026-10-21T10:00:00+00:00',
    });
  });

  it('refuse une charge utile non objet', () => {
    expect(() => validerUnSignalement(null)).toThrow(TypeError);
    expect(() => validerUnSignalement('x')).toThrow(TypeError);
  });

  it('refuse un champ manquant', () => {
    expect(() => validerUnSignalement({ identifiant: 's1', etat: 'new' })).toThrow(TypeError);
  });
});
