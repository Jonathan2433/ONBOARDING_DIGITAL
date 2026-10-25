/**
 * Le contrat du traitement des signalements — LOT 10, `T12`/`T15`, `US006`.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminChangementDEtatSignalement,
  cheminHistoriqueSignalement,
  cheminSignalements,
  peutTraiterLesSignalements,
  validerLeChangementDEtatSignalement,
  validerLesSignalements,
  validerLHistoriqueSignalement,
} from './traitementDesSignalements.js';

function ligne(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 's1',
    etat: 'new',
    description: 'Le bouton ne répond pas',
    etapes_de_reproduction: null,
    chemin_de_page: '/entites/bordeaux/trombinoscope',
    entite_id: 'e1',
    rapporteur_id: 'p1',
    cree_le: '2026-10-01T10:00:00Z',
    version: 1,
    version_application: '0.10.0',
    environnement: 'production',
    resume_navigateur: 'Chrome 130 / macOS',
    jeton_de_correlation: 'corr1',
    ...modifications,
  };
}

describe('les chemins du traitement des signalements', () => {
  it('liste, pagine et filtre par état', () => {
    expect(cheminSignalements('bordeaux', 1, 25, 'new')).toBe(
      '/api/v1/entities/bordeaux/bug-reports?page=1&taille=25&etat=new',
    );
  });

  it('l’historique encode ses deux segments', () => {
    expect(cheminHistoriqueSignalement('a b', 's 1')).toBe(
      '/api/v1/entities/a%20b/bug-reports/s%201/historique',
    );
  });

  it('le changement d’état encode ses deux segments', () => {
    expect(cheminChangementDEtatSignalement('bordeaux', 's1')).toBe(
      '/api/v1/entities/bordeaux/bug-reports/s1/etat',
    );
  });

  it('refuse un segment vide', () => {
    expect(() => cheminSignalements('', 1, 25)).toThrow(TypeError);
    expect(() => cheminHistoriqueSignalement('bordeaux', '')).toThrow(TypeError);
    expect(() => cheminChangementDEtatSignalement('', 's1')).toThrow(TypeError);
  });
});

describe('peutTraiterLesSignalements — ADM-E/SUPER seuls', () => {
  it('admet ADM-E et SUPER', () => {
    expect(peutTraiterLesSignalements(['ADM-E'])).toBe(true);
    expect(peutTraiterLesSignalements(['SUPER'])).toBe(true);
  });

  it('refuse ESM — lecture fonctionnelle, jamais le droit de changer l’état', () => {
    expect(peutTraiterLesSignalements(['ESM'])).toBe(false);
  });

  it('refuse `null`', () => {
    expect(peutTraiterLesSignalements(null)).toBe(false);
  });
});

describe('validerLesSignalements', () => {
  it('accepte une ligne complète', () => {
    const resultat = validerLesSignalements({
      signalements: [ligne()],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    });
    expect(resultat.signalements[0]).toMatchObject({
      identifiant: 's1',
      etat: 'new',
      versionApplication: '0.10.0',
    });
  });

  it('les quatre champs techniques à `null` — lecture fonctionnelle de l’ESM, jamais absents', () => {
    const resultat = validerLesSignalements({
      signalements: [
        ligne({
          version_application: null,
          environnement: null,
          resume_navigateur: null,
          jeton_de_correlation: null,
        }),
      ],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    });
    expect(resultat.signalements[0]?.versionApplication).toBeNull();
    expect(resultat.signalements[0]?.environnement).toBeNull();
    expect(resultat.signalements[0]?.resumeNavigateur).toBeNull();
    expect(resultat.signalements[0]?.jetonDeCorrelation).toBeNull();
  });

  it('refuse un « signalements » absent du tableau', () => {
    expect(() => validerLesSignalements({ page: 1, taille: 25, total: 0, pages: 1 })).toThrow(
      TypeError,
    );
  });
});

describe('validerLHistoriqueSignalement', () => {
  it('accepte un historique avec un changement d’état', () => {
    const resultat = validerLHistoriqueSignalement({
      evenements: [
        {
          survenu_le: '2026-10-01T10:00:00Z',
          ancien_etat: 'new',
          nouvel_etat: 'investigating',
          commentaire: 'Pris en charge',
          acteur_id: 'adm1',
        },
      ],
    });
    expect(resultat.evenements[0]?.nouvelEtat).toBe('investigating');
  });

  it('refuse une charge non objet', () => {
    expect(() => validerLHistoriqueSignalement(null)).toThrow(TypeError);
  });
});

describe('validerLeChangementDEtatSignalement', () => {
  it('accepte etat et version', () => {
    expect(validerLeChangementDEtatSignalement({ etat: 'investigating', version: 2 })).toEqual({
      etat: 'investigating',
      version: 2,
    });
  });

  it('refuse une charge non objet', () => {
    expect(() => validerLeChangementDEtatSignalement(null)).toThrow(TypeError);
  });
});
