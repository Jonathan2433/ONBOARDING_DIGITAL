/**
 * Le contrat du journal d'audit et de son export CSV — LOT 10, `T8`/`T9`/`T15`.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminExportDuJournal,
  cheminJournalDAudit,
  CODES_EXPORT_DU_JOURNAL,
  CODES_JOURNAL_D_AUDIT,
  peutConsulterLAudit,
  peutExporterLAudit,
  peutVoirLesDetailsTechniquesDeLAudit,
  validerLeJournalDAudit,
} from './audit.js';

function evenement(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'e1',
    occurred_at: '2026-10-01T10:00:00Z',
    action_code: 'collaborateur_cree',
    resource_type: 'person',
    resource_reference: 'p1',
    summary: 'Création de Nouvelle Arrivante',
    old_values: null,
    new_values: { first_name: 'Nouvelle' },
    reason: null,
    actor_person_id: 'acteur1',
    actor_service_account_id: null,
    correlation_token: 'corr1',
    retention_until: '2027-10-01T10:00:00Z',
    ...modifications,
  };
}

describe('les chemins du journal d’audit', () => {
  it('pagine et encode le code d’entité', () => {
    expect(cheminJournalDAudit('a b', 2, 50)).toBe('/api/v1/entities/a%20b/audit?page=2&taille=50');
  });

  it('ajoute les filtres facultatifs', () => {
    expect(cheminJournalDAudit('bordeaux', 1, 25, { actionCode: 'collaborateur_cree' })).toBe(
      '/api/v1/entities/bordeaux/audit?page=1&taille=25&action_code=collaborateur_cree',
    );
  });

  it('refuse un code vide', () => {
    expect(() => cheminJournalDAudit('', 1, 25)).toThrow(TypeError);
  });

  it('les codes exploitables couvrent 200 et 422', () => {
    expect(CODES_JOURNAL_D_AUDIT).toContain(200);
    expect(CODES_JOURNAL_D_AUDIT).toContain(422);
  });
});

describe('les chemins de l’export CSV', () => {
  it('ne pagine jamais, sans filtre', () => {
    expect(cheminExportDuJournal('bordeaux')).toBe('/api/v1/entities/bordeaux/audit/export');
  });

  it('porte les mêmes filtres que le journal, jamais la pagination', () => {
    expect(cheminExportDuJournal('bordeaux', { resourceType: 'person' })).toBe(
      '/api/v1/entities/bordeaux/audit/export?resource_type=person',
    );
  });

  it('refuse un code vide', () => {
    expect(() => cheminExportDuJournal('')).toThrow(TypeError);
  });

  it('les codes exploitables couvrent 200', () => {
    expect(CODES_EXPORT_DU_JOURNAL).toContain(200);
  });
});

describe('les trois grilles de rôles, jamais fusionnées', () => {
  it('peutConsulterLAudit admet DSM/ESM/BOOST/OFFICE/ADM-E/SUPER, refuse EMP et null', () => {
    expect(peutConsulterLAudit(['DSM'])).toBe(true);
    expect(peutConsulterLAudit(['SUPER'])).toBe(true);
    expect(peutConsulterLAudit(['EMP'])).toBe(false);
    expect(peutConsulterLAudit(null)).toBe(false);
  });

  it('peutVoirLesDetailsTechniquesDeLAudit n’admet qu’ADM-E/SUPER', () => {
    expect(peutVoirLesDetailsTechniquesDeLAudit(['ADM-E'])).toBe(true);
    expect(peutVoirLesDetailsTechniquesDeLAudit(['ESM'])).toBe(false);
  });

  it('peutExporterLAudit n’admet qu’ADM-E/SUPER', () => {
    expect(peutExporterLAudit(['SUPER'])).toBe(true);
    expect(peutExporterLAudit(['DSM'])).toBe(false);
  });
});

describe('validerLeJournalDAudit', () => {
  it('accepte une page avec un événement', () => {
    const journal = validerLeJournalDAudit({
      evenements: [evenement()],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    });
    expect(journal.evenements[0]).toEqual({
      id: 'e1',
      occurredAt: '2026-10-01T10:00:00Z',
      actionCode: 'collaborateur_cree',
      resourceType: 'person',
      resourceReference: 'p1',
      summary: 'Création de Nouvelle Arrivante',
      oldValues: null,
      newValues: { first_name: 'Nouvelle' },
      reason: null,
      actorPersonId: 'acteur1',
      actorServiceAccountId: null,
      correlationToken: 'corr1',
      retentionUntil: '2027-10-01T10:00:00Z',
    });
  });

  it('`resourceReference`/`correlationToken` à `null` — lecture fonctionnelle, jamais absents', () => {
    const journal = validerLeJournalDAudit({
      evenements: [evenement({ resource_reference: null, correlation_token: null })],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    });
    expect(journal.evenements[0]?.resourceReference).toBeNull();
    expect(journal.evenements[0]?.correlationToken).toBeNull();
  });

  it('accepte une page VIDE — « aucun événement » est un état légitime', () => {
    const journal = validerLeJournalDAudit({
      evenements: [],
      page: 1,
      taille: 25,
      total: 0,
      pages: 1,
    });
    expect(journal.evenements).toEqual([]);
  });

  it('refuse un « evenements » absent du tableau', () => {
    expect(() => validerLeJournalDAudit({ page: 1, taille: 25, total: 0, pages: 1 })).toThrow(
      TypeError,
    );
  });

  it('refuse une charge non objet', () => {
    expect(() => validerLeJournalDAudit(null)).toThrow(TypeError);
  });
});
