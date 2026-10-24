/**
 * Le contrat du suivi d'une demande de droit RGPD — LOT 10, `T14`/`T15`, `US008`.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminClotureRGPD,
  cheminDemandesRGPD,
  cheminHistoriqueRGPD,
  cheminUneDemandeRGPD,
  cheminVerificationIdentiteRGPD,
  peutTraiterLesDemandesRGPD,
  validerLaTransitionRGPD,
  validerLesDemandesRGPD,
  validerLHistoriqueRGPD,
  validerUneDemandeRGPD,
} from './rgpd.js';

function ligne(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 'd1',
    personne_concernee_id: 'p1',
    type_demande: 'access',
    canal: 'e-mail',
    recue_le: '2026-10-01T10:00:00Z',
    identite_verifiee: false,
    responsable_id: 'adm1',
    echeance: '2026-10-31T10:00:00Z',
    en_retard: false,
    etat: 'received',
    reponse: null,
    cloturee_le: null,
    version: 1,
    ...modifications,
  };
}

describe('les chemins RGPD — ressource globale, aucun code d’entité', () => {
  it('liste, pagine et filtre par état et par type', () => {
    expect(cheminDemandesRGPD(1, 25, 'received', 'access')).toBe(
      '/api/v1/data-subject-requests?page=1&taille=25&etat=received&type_demande=access',
    );
  });

  it('les routes par demande encodent leur segment', () => {
    expect(cheminUneDemandeRGPD('d 1')).toBe('/api/v1/data-subject-requests/d%201');
    expect(cheminHistoriqueRGPD('d1')).toBe('/api/v1/data-subject-requests/d1/historique');
    expect(cheminVerificationIdentiteRGPD('d1')).toBe(
      '/api/v1/data-subject-requests/d1/verification-identite',
    );
    expect(cheminClotureRGPD('d1')).toBe('/api/v1/data-subject-requests/d1/cloture');
  });

  it('refuse un identifiant de demande vide', () => {
    expect(() => cheminUneDemandeRGPD('')).toThrow(TypeError);
  });
});

describe('peutTraiterLesDemandesRGPD — ADM-E/SUPER seuls, aucun plancher', () => {
  it('admet ADM-E et SUPER', () => {
    expect(peutTraiterLesDemandesRGPD(['ADM-E'])).toBe(true);
    expect(peutTraiterLesDemandesRGPD(['SUPER'])).toBe(true);
  });

  it('refuse ESM — aucune visibilité partielle, à la différence des alertes et des signalements', () => {
    expect(peutTraiterLesDemandesRGPD(['ESM'])).toBe(false);
  });

  it('refuse `null`', () => {
    expect(peutTraiterLesDemandesRGPD(null)).toBe(false);
  });
});

describe('validerUneDemandeRGPD / validerLesDemandesRGPD', () => {
  it('accepte une demande complète', () => {
    expect(validerUneDemandeRGPD(ligne())).toMatchObject({
      identifiant: 'd1',
      typeDemande: 'access',
      enRetard: false,
    });
  });

  it('« enRetard » est lu tel quel, jamais recalculé côté client', () => {
    const demande = validerUneDemandeRGPD(ligne({ en_retard: true }));
    expect(demande.enRetard).toBe(true);
  });

  it('refuse une charge non objet', () => {
    expect(() => validerUneDemandeRGPD(null)).toThrow(TypeError);
  });

  it('valide une page de demandes', () => {
    const page = validerLesDemandesRGPD({
      demandes: [ligne()],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    });
    expect(page.demandes).toHaveLength(1);
  });

  it('refuse un « demandes » absent du tableau', () => {
    expect(() => validerLesDemandesRGPD({ page: 1, taille: 25, total: 0, pages: 1 })).toThrow(
      TypeError,
    );
  });
});

describe('validerLHistoriqueRGPD', () => {
  it('accepte un historique avec anciennes/nouvelles valeurs opaques', () => {
    const resultat = validerLHistoriqueRGPD({
      evenements: [
        {
          survenu_le: '2026-10-01T10:00:00Z',
          anciennes_valeurs: { state: 'received' },
          nouvelles_valeurs: { state: 'closed' },
          acteur_id: 'adm1',
        },
      ],
    });
    expect(resultat.evenements[0]?.nouvellesValeurs).toEqual({ state: 'closed' });
  });

  it('refuse une charge non objet', () => {
    expect(() => validerLHistoriqueRGPD(null)).toThrow(TypeError);
  });
});

describe('validerLaTransitionRGPD', () => {
  it('accepte etat, identiteVerifiee et version', () => {
    expect(
      validerLaTransitionRGPD({ etat: 'closed', identite_verifiee: true, version: 2 }),
    ).toEqual({ etat: 'closed', identiteVerifiee: true, version: 2 });
  });

  it('refuse une charge non objet', () => {
    expect(() => validerLaTransitionRGPD(null)).toThrow(TypeError);
  });
});
