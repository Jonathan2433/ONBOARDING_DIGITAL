/**
 * Le contrat du cycle des alertes opérationnelles — LOT 10, `T13`/`T15`, `US007`.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminAcquittementDAlerte,
  cheminAlertes,
  cheminCommentairesDAlerte,
  cheminUneAlerte,
  peutTraiterLesAlertes,
  validerLeCommentaireAjoute,
  validerLesAlertes,
  validerLesCommentairesDAlerte,
  validerLaTransitionDAlerte,
  validerUneAlerte,
} from './alertes.js';

function ligne(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 'al1',
    gravite: 'haute',
    source: 'uptime-kuma',
    etat: 'open',
    assigne_a: null,
    ouverte_le: '2026-10-01T10:00:00Z',
    acquittee_le: null,
    resolue_le: null,
    empreinte: 'empreinte-1',
    version: 1,
    ...modifications,
  };
}

describe('les chemins des alertes — ressource globale, aucun code d’entité', () => {
  it('liste, pagine et filtre par état', () => {
    expect(cheminAlertes(1, 25, 'open')).toBe('/api/v1/alerts?page=1&taille=25&etat=open');
  });

  it('les routes par alerte encodent leur segment', () => {
    expect(cheminUneAlerte('al 1')).toBe('/api/v1/alerts/al%201');
    expect(cheminCommentairesDAlerte('al1')).toBe('/api/v1/alerts/al1/commentaires');
    expect(cheminAcquittementDAlerte('al1')).toBe('/api/v1/alerts/al1/acquittement');
  });

  it('refuse un identifiant d’alerte vide', () => {
    expect(() => cheminUneAlerte('')).toThrow(TypeError);
  });
});

describe('peutTraiterLesAlertes — ADM-E/SUPER seuls, jamais ESM', () => {
  it('admet ADM-E et SUPER', () => {
    expect(peutTraiterLesAlertes(['ADM-E'])).toBe(true);
    expect(peutTraiterLesAlertes(['SUPER'])).toBe(true);
  });

  it('refuse ESM — périmètre LIMITE, lecture seule, confirmé sur les routes réelles', () => {
    expect(peutTraiterLesAlertes(['ESM'])).toBe(false);
  });

  it('refuse `null`', () => {
    expect(peutTraiterLesAlertes(null)).toBe(false);
  });
});

describe('validerUneAlerte / validerLesAlertes', () => {
  it('accepte une alerte complète', () => {
    expect(validerUneAlerte(ligne())).toMatchObject({ identifiant: 'al1', etat: 'open' });
  });

  it('`source`/`empreinte` à `null` — périmètre LIMITE de l’ESM, jamais absents', () => {
    const alerte = validerUneAlerte(ligne({ source: null, empreinte: null }));
    expect(alerte.source).toBeNull();
    expect(alerte.empreinte).toBeNull();
  });

  it('refuse une charge non objet', () => {
    expect(() => validerUneAlerte(null)).toThrow(TypeError);
  });

  it('valide une page d’alertes', () => {
    const page = validerLesAlertes({ alertes: [ligne()], page: 1, taille: 25, total: 1, pages: 1 });
    expect(page.alertes).toHaveLength(1);
  });

  it('refuse un « alertes » absent du tableau', () => {
    expect(() => validerLesAlertes({ page: 1, taille: 25, total: 0, pages: 1 })).toThrow(TypeError);
  });
});

describe('les commentaires et les transitions', () => {
  it('valide une liste de commentaires', () => {
    const resultat = validerLesCommentairesDAlerte({
      commentaires: [
        {
          identifiant: 'c1',
          contenu: 'Investigation en cours',
          cree_le: '2026-10-01T10:00:00Z',
          auteur_id: 'a1',
        },
      ],
    });
    expect(resultat.commentaires[0]?.contenu).toBe('Investigation en cours');
  });

  it('valide un commentaire ajouté', () => {
    expect(
      validerLeCommentaireAjoute({ identifiant: 'c1', cree_le: '2026-10-01T10:00:00Z' }),
    ).toEqual({ identifiant: 'c1', creeLe: '2026-10-01T10:00:00Z' });
  });

  it('valide une transition (acquittement/résolution, même forme)', () => {
    expect(validerLaTransitionDAlerte({ etat: 'acknowledged', version: 2 })).toEqual({
      etat: 'acknowledged',
      version: 2,
    });
  });

  it('refuse une charge non objet pour les trois', () => {
    expect(() => validerLesCommentairesDAlerte(null)).toThrow(TypeError);
    expect(() => validerLeCommentaireAjoute(null)).toThrow(TypeError);
    expect(() => validerLaTransitionDAlerte(null)).toThrow(TypeError);
  });
});
