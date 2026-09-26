/**
 * Le contrat du parcours d'onboarding — LOT 7, `T7`, `MVP-L07-US004`.
 *
 * `instance`/`progression`/`prochaine_tache` NULS ENSEMBLE, OU AUCUN DES
 * TROIS — le seul point structurel propre a ce contrat, meme forme que
 * `id`/`version` de `ficheArrivee.ts`.
 */

import { describe, expect, it } from 'vitest';

import {
  CODES_AFFECTATION_DU_PARCOURS,
  CODES_LECTURE_DU_PARCOURS,
  cheminDuParcours,
  GABARIT_CHEMIN_PARCOURS,
  validerLeParcours,
} from './parcoursOnboarding.js';

function tache(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 't1',
    task_reference_id: 'r1',
    title_snapshot: 'Signer le contrat',
    description_snapshot: null,
    required: true,
    due_at: '2026-10-08T00:00:00Z',
    state: 'todo',
    completed_at: null,
    reopened_at: null,
    ...modifications,
  };
}

function parcours(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    instance: {
      id: 'i1',
      template_version_id: 'v1',
      reference_date: '2026-10-01',
      state: 'active',
      started_at: '2026-10-01T09:00:00Z',
      completed_at: null,
    },
    progression: { taches_obligatoires_totales: 2, taches_obligatoires_terminees: 0 },
    prochaine_tache: tache(),
    taches: [tache()],
    ...modifications,
  };
}

describe('le chemin du parcours', () => {
  it('vient du manifeste, source unique (DEC-492)', () => {
    expect(GABARIT_CHEMIN_PARCOURS).toBe(
      '/api/v1/entities/{code}/people/{appartenance}/onboarding-parcours',
    );
    expect(CODES_LECTURE_DU_PARCOURS).toContain(200);
    expect(CODES_AFFECTATION_DU_PARCOURS).toContain(201);
    expect(CODES_AFFECTATION_DU_PARCOURS).toContain(409);
  });

  it('encode ses deux segments', () => {
    expect(cheminDuParcours('BORDEA00', 'a b')).toBe(
      '/api/v1/entities/BORDEA00/people/a%20b/onboarding-parcours',
    );
  });

  it('refuse un code ou une appartenance vide', () => {
    expect(() => cheminDuParcours('', 'a1')).toThrow(TypeError);
    expect(() => cheminDuParcours('BORDEA00', '')).toThrow(TypeError);
  });
});

describe('validerLeParcours', () => {
  it('accepte un parcours complet, deja affecte', () => {
    const valide = validerLeParcours(parcours());
    expect(valide.instance).toEqual({
      id: 'i1',
      versionDeModele: 'v1',
      dateDeReference: '2026-10-01',
      etat: 'active',
      demarreeLe: '2026-10-01T09:00:00Z',
      termineeLe: null,
    });
    expect(valide.progression).toEqual({
      tachesObligatoiresTotales: 2,
      tachesObligatoiresTerminees: 0,
    });
    expect(valide.prochaineTache?.titre).toBe('Signer le contrat');
    expect(valide.taches).toHaveLength(1);
  });

  it('accepte les trois NULS ENSEMBLE — aucun parcours affecte encore', () => {
    const valide = validerLeParcours(
      parcours({ instance: null, progression: null, prochaine_tache: null, taches: [] }),
    );
    expect(valide.instance).toBeNull();
    expect(valide.progression).toBeNull();
    expect(valide.prochaineTache).toBeNull();
    expect(valide.taches).toEqual([]);
  });

  it('refuse instance nulle mais progression non nulle — doivent etre nuls ENSEMBLE', () => {
    expect(() => validerLeParcours(parcours({ instance: null }))).toThrow(TypeError);
  });

  it('refuse prochaine_tache nulle seule', () => {
    expect(() => validerLeParcours(parcours({ prochaine_tache: null }))).toThrow(TypeError);
  });

  it('refuse une charge utile non objet', () => {
    expect(() => validerLeParcours(null)).toThrow(TypeError);
    expect(() => validerLeParcours([parcours()])).toThrow(TypeError);
  });

  it('refuse « taches » qui n’est pas un tableau', () => {
    expect(() => validerLeParcours(parcours({ taches: {} }))).toThrow(TypeError);
  });

  it('refuse un champ textuel obligatoire absent sur une tache', () => {
    const sansTitre = tache();
    delete sansTitre['title_snapshot'];
    expect(() => validerLeParcours(parcours({ taches: [sansTitre] }))).toThrow(TypeError);
  });

  it('refuse « required » non booleen', () => {
    expect(() => validerLeParcours(parcours({ taches: [tache({ required: 1 })] }))).toThrow(
      TypeError,
    );
  });

  it('refuse un compte de progression non entier', () => {
    expect(() =>
      validerLeParcours(
        parcours({
          progression: { taches_obligatoires_totales: 1.5, taches_obligatoires_terminees: 0 },
        }),
      ),
    ).toThrow(TypeError);
  });
});
