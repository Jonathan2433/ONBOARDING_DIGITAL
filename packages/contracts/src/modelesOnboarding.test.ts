/**
 * Le contrat des modeles d'onboarding et de leur cycle de vie — LOT 7, `T14`.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminArchivageDeVersion,
  cheminModelesOnboarding,
  cheminPublicationDeVersion,
  cheminRestaurationDeVersion,
  cheminTachesDeVersion,
  cheminVersionsDeModele,
  CODES_CONSULTATION_DES_MODELES,
  GABARIT_CHEMIN_MODELES_ONBOARDING,
  validerLArchivageDeVersion,
  validerLaPublicationDeVersion,
  validerLaRestaurationDeVersion,
  validerLesModelesOnboarding,
  validerLesTachesDeVersion,
  validerUneVersionCreee,
  validerUnModeleCree,
} from './modelesOnboarding.js';

function modele(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'm1',
    entity_id: 'e1',
    name: 'Onboarding consultant',
    target_status: 'mission',
    scope_type: 'ENTITY',
    scope_person_id: null,
    scope_circle_id: null,
    state: 'active',
    ...modifications,
  };
}

function version(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'v1',
    template_id: 'm1',
    version_number: 1,
    state: 'draft',
    change_summary: null,
    ...modifications,
  };
}

describe('les chemins des modeles d’onboarding', () => {
  it('viennent du manifeste, source unique (DEC-492)', () => {
    expect(GABARIT_CHEMIN_MODELES_ONBOARDING).toBe('/api/v1/entities/{code}/onboarding/templates');
    expect(CODES_CONSULTATION_DES_MODELES).toContain(200);
    expect(CODES_CONSULTATION_DES_MODELES).toContain(403);
  });

  it('cheminModelesOnboarding encode son segment', () => {
    expect(cheminModelesOnboarding('a b')).toBe('/api/v1/entities/a%20b/onboarding/templates');
  });

  it('cheminVersionsDeModele encode ses deux segments', () => {
    expect(cheminVersionsDeModele('e', 'm 1')).toBe(
      '/api/v1/entities/e/onboarding/templates/m%201/versions',
    );
  });

  it(
    'cheminTachesDeVersion, cheminPublicationDeVersion, cheminArchivageDeVersion et ' +
      'cheminRestaurationDeVersion encodent leurs trois segments',
    () => {
      expect(cheminTachesDeVersion('e', 'm', 'v')).toBe(
        '/api/v1/entities/e/onboarding/templates/m/versions/v/tasks',
      );
      expect(cheminPublicationDeVersion('e', 'm', 'v')).toBe(
        '/api/v1/entities/e/onboarding/templates/m/versions/v/publication',
      );
      expect(cheminArchivageDeVersion('e', 'm', 'v')).toBe(
        '/api/v1/entities/e/onboarding/templates/m/versions/v/archivage',
      );
      expect(cheminRestaurationDeVersion('e', 'm', 'v')).toBe(
        '/api/v1/entities/e/onboarding/templates/m/versions/v/restauration',
      );
    },
  );

  it('refusent un segment vide', () => {
    expect(() => cheminModelesOnboarding('')).toThrow(TypeError);
    expect(() => cheminVersionsDeModele('', 'm')).toThrow(TypeError);
    expect(() => cheminTachesDeVersion('e', 'm', '')).toThrow(TypeError);
  });
});

describe('validerUnModeleCree', () => {
  it('accepte un modele DSM avec sa portee', () => {
    const cree = validerUnModeleCree(
      modele({ scope_type: 'DSM', scope_person_id: 'p1', entity_id: 'e1' }),
    );
    expect(cree.portee).toBe('DSM');
    expect(cree.scopePersonId).toBe('p1');
    expect(cree.scopeCircleId).toBeNull();
  });

  it('accepte un modele GLOBAL, entiteId nul', () => {
    const cree = validerUnModeleCree(modele({ scope_type: 'GLOBAL', entity_id: null }));
    expect(cree.entiteId).toBeNull();
  });

  it('refuse une charge non objet', () => {
    expect(() => validerUnModeleCree(null)).toThrow(TypeError);
  });
});

describe('validerLesModelesOnboarding', () => {
  it('accepte une liste avec un modele et ses versions', () => {
    const page = validerLesModelesOnboarding({
      modeles: [{ ...modele(), versions: [version()] }],
      nombre_de_modeles: 1,
    });
    expect(page.nombreDeModeles).toBe(1);
    expect(page.modeles[0]?.versions).toEqual([
      {
        id: 'v1',
        modeleId: 'm1',
        numero: 1,
        etat: 'draft',
        resumeDuChangement: null,
      },
    ]);
  });

  it('accepte un modele SANS aucune version — tableau vide, jamais absent', () => {
    const page = validerLesModelesOnboarding({
      modeles: [{ ...modele(), versions: [] }],
      nombre_de_modeles: 1,
    });
    expect(page.modeles[0]?.versions).toEqual([]);
  });

  it('refuse un « modeles » absent du tableau', () => {
    expect(() => validerLesModelesOnboarding({ nombre_de_modeles: 0 })).toThrow(TypeError);
  });

  it('refuse un « versions » absent du tableau sur un modele', () => {
    expect(() =>
      validerLesModelesOnboarding({ modeles: [modele()], nombre_de_modeles: 1 }),
    ).toThrow(TypeError);
  });

  it('refuse quand nombre_de_modeles diverge du tableau rendu — §7.0, sixieme proposition', () => {
    expect(() =>
      validerLesModelesOnboarding({
        modeles: [{ ...modele(), versions: [] }],
        nombre_de_modeles: 2,
      }),
    ).toThrow(TypeError);
  });
});

describe('validerUneVersionCreee', () => {
  it('accepte une version brouillon avec un resume', () => {
    const creee = validerUneVersionCreee(version({ change_summary: 'Ajout du badge' }));
    expect(creee.resumeDuChangement).toBe('Ajout du badge');
    expect(creee.etat).toBe('draft');
  });
});

describe('validerLesTachesDeVersion', () => {
  function tacheDeVersion(modifications: Record<string, unknown> = {}): Record<string, unknown> {
    return {
      id: 't1',
      task_reference_id: 'ref1',
      display_order: 0,
      required: true,
      due_offset_days: 7,
      title_override: null,
      description_override: null,
      ...modifications,
    };
  }

  it('accepte la liste et son compte', () => {
    const taches = validerLesTachesDeVersion({
      taches: [tacheDeVersion()],
      nombre_de_taches: 1,
    });
    expect(taches.taches[0]?.ordre).toBe(0);
    expect(taches.taches[0]?.obligatoire).toBe(true);
  });

  it('accepte une liste VIDE — effacer la precedente, T5', () => {
    const taches = validerLesTachesDeVersion({ taches: [], nombre_de_taches: 0 });
    expect(taches.taches).toEqual([]);
  });

  it('refuse quand nombre_de_taches diverge', () => {
    expect(() =>
      validerLesTachesDeVersion({ taches: [tacheDeVersion()], nombre_de_taches: 0 }),
    ).toThrow(TypeError);
  });
});

describe('les trois reponses du cycle de vie — trois formes distinctes', () => {
  it('validerLaPublicationDeVersion exige published_at ET published_by_person_id', () => {
    const publiee = validerLaPublicationDeVersion({
      id: 'v1',
      version_number: 1,
      state: 'published',
      published_at: '2026-09-28T10:00:00Z',
      published_by_person_id: 'p1',
    });
    expect(publiee.publieeLe).toBe('2026-09-28T10:00:00Z');
  });

  it('validerLaPublicationDeVersion refuse published_at absent', () => {
    expect(() =>
      validerLaPublicationDeVersion({ id: 'v1', version_number: 1, state: 'published' }),
    ).toThrow(TypeError);
  });

  it('validerLArchivageDeVersion ne porte NI date NI acteur', () => {
    const archivee = validerLArchivageDeVersion({ id: 'v1', version_number: 1, state: 'retired' });
    expect(archivee).toEqual({ id: 'v1', numero: 1, etat: 'retired' });
  });

  it('validerLaRestaurationDeVersion accepte published_at NULLABLE', () => {
    const restauree = validerLaRestaurationDeVersion({
      id: 'v1',
      version_number: 1,
      state: 'published',
      published_at: null,
      published_by_person_id: null,
    });
    expect(restauree.publieeLe).toBeNull();
  });
});
