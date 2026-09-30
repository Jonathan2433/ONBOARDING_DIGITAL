/**
 * Le contrat du suivi des taches en retard par perimetre — LOT 7, `T12`/`T14`.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminSuiviOnboarding,
  CODES_SUIVI_ONBOARDING,
  GABARIT_CHEMIN_SUIVI_ONBOARDING,
  validerLeSuiviOnboarding,
} from './suiviOnboarding.js';

function tacheEnRetard(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 't1',
    title_snapshot: 'Signer le contrat',
    due_at: '2026-09-20T00:00:00Z',
    state: 'todo',
    instance_id: 'i1',
    appartenance_id: 'a1',
    person_id: 'p1',
    first_name: 'Nouvelle',
    last_name: 'Arrivante',
    ...modifications,
  };
}

describe('le chemin du suivi de l’onboarding', () => {
  it('vient du manifeste, source unique (DEC-492)', () => {
    expect(GABARIT_CHEMIN_SUIVI_ONBOARDING).toBe(
      '/api/v1/entities/{code}/onboarding-suivi/taches-en-retard',
    );
    expect(CODES_SUIVI_ONBOARDING).toContain(200);
    expect(CODES_SUIVI_ONBOARDING).toContain(422);
  });

  it('encode son segment', () => {
    expect(cheminSuiviOnboarding('a b')).toBe(
      '/api/v1/entities/a%20b/onboarding-suivi/taches-en-retard',
    );
  });

  it('refuse un code vide', () => {
    expect(() => cheminSuiviOnboarding('')).toThrow(TypeError);
  });
});

describe('validerLeSuiviOnboarding', () => {
  it('accepte une page avec une tache en retard', () => {
    const suivi = validerLeSuiviOnboarding({
      taches: [tacheEnRetard()],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    });
    expect(suivi.taches[0]).toEqual({
      id: 't1',
      titre: 'Signer le contrat',
      echeance: '2026-09-20T00:00:00Z',
      etat: 'todo',
      instanceId: 'i1',
      appartenanceId: 'a1',
      personneId: 'p1',
      prenom: 'Nouvelle',
      nom: 'Arrivante',
    });
  });

  it('accepte une page VIDE — « aucune tache en retard » est un etat legitime', () => {
    const suivi = validerLeSuiviOnboarding({ taches: [], page: 1, taille: 25, total: 0, pages: 1 });
    expect(suivi.taches).toEqual([]);
    //  **AU MOINS 1, MEME SANS TACHE** : 0 ne distinguerait pas d'un chargement.
    expect(suivi.pages).toBe(1);
  });

  it('refuse un « taches » absent du tableau', () => {
    expect(() => validerLeSuiviOnboarding({ page: 1, taille: 25, total: 0, pages: 1 })).toThrow(
      TypeError,
    );
  });

  it('refuse une charge non objet', () => {
    expect(() => validerLeSuiviOnboarding(null)).toThrow(TypeError);
  });
});
