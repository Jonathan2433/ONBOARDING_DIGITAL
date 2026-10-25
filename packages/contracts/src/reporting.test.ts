/**
 * Le contrat du reporting étendu — LOT 10, `T10`/`T15`, `MVP-L10-US003`.
 */

import { describe, expect, it } from 'vitest';

import {
  cheminDetailOnboarding,
  cheminIndicateurs,
  cheminProfilsIncomplets,
  CODES_INDICATEURS,
  validerLeDetailOnboarding,
  validerLesIndicateurs,
  validerLesProfilsIncomplets,
} from './reporting.js';

describe('les chemins du reporting', () => {
  it('les indicateurs ne paginent pas', () => {
    expect(cheminIndicateurs('bordeaux')).toBe('/api/v1/entities/bordeaux/reporting');
  });

  it('les indicateurs portent les filtres facultatifs', () => {
    expect(cheminIndicateurs('bordeaux', { dsm: 'd1' })).toBe(
      '/api/v1/entities/bordeaux/reporting?dsm=d1',
    );
  });

  it('le détail onboarding pagine et filtre', () => {
    expect(cheminDetailOnboarding('bordeaux', 2, 50, { cercle: 'c1' })).toBe(
      '/api/v1/entities/bordeaux/reporting/onboarding?page=2&taille=50&cercle=c1',
    );
  });

  it('les profils incomplets paginent', () => {
    expect(cheminProfilsIncomplets('bordeaux', 1, 25)).toBe(
      '/api/v1/entities/bordeaux/reporting/profils-incomplets?page=1&taille=25',
    );
  });

  it('les trois chemins refusent un code vide', () => {
    expect(() => cheminIndicateurs('')).toThrow(TypeError);
    expect(() => cheminDetailOnboarding('', 1, 25)).toThrow(TypeError);
    expect(() => cheminProfilsIncomplets('', 1, 25)).toThrow(TypeError);
  });

  it('les codes exploitables des indicateurs couvrent 200', () => {
    expect(CODES_INDICATEURS).toContain(200);
  });
});

describe('validerLesIndicateurs', () => {
  function indicateurs(modifications: Record<string, unknown> = {}): Record<string, unknown> {
    return {
      onboardings_termines: 5,
      progression_moyenne: { taches_obligatoires_totales: 20, taches_obligatoires_terminees: 12 },
      duree_moyenne_jours: 14.5,
      arrivees_30_jours: 3,
      repartition_par_cercle: [{ identifiant: 'c1', libelle: 'Change', profils_actifs: 4 }],
      repartition_par_client: [],
      repartition_par_dsm: [],
      ...modifications,
    };
  }

  it('accepte une réponse complète', () => {
    const resultat = validerLesIndicateurs(indicateurs());
    expect(resultat.onboardingsTermines).toBe(5);
    expect(resultat.progressionMoyenne).toEqual({
      tachesObligatoiresTotales: 20,
      tachesObligatoiresTerminees: 12,
    });
    expect(resultat.repartitionParCercle).toEqual([
      { identifiant: 'c1', libelle: 'Change', profilsActifs: 4 },
    ]);
  });

  it('« durée moyenne » est `null`, jamais `0`, quand la population est vide (§7.0 sixième proposition)', () => {
    const resultat = validerLesIndicateurs(indicateurs({ duree_moyenne_jours: null }));
    expect(resultat.dureeMoyenneJours).toBeNull();
  });

  it('refuse une « progression_moyenne » absente', () => {
    const { progression_moyenne, ...sansProgression } = indicateurs();
    void progression_moyenne;
    expect(() => validerLesIndicateurs(sansProgression)).toThrow(TypeError);
  });

  it('refuse une charge non objet', () => {
    expect(() => validerLesIndicateurs(null)).toThrow(TypeError);
  });
});

describe('validerLeDetailOnboarding', () => {
  it('accepte une page avec un élément', () => {
    const resultat = validerLeDetailOnboarding({
      elements: [
        {
          appartenance_id: 'a1',
          person_id: 'p1',
          prenom: 'Nouvelle',
          nom: 'Arrivante',
          date_de_reference: '2026-10-01',
          debute_le: '2026-10-01T08:00:00Z',
          taches_obligatoires_totales: 10,
          taches_obligatoires_terminees: 4,
        },
      ],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    });
    expect(resultat.elements[0]?.prenom).toBe('Nouvelle');
  });

  it('refuse un « elements » absent du tableau', () => {
    expect(() => validerLeDetailOnboarding({ page: 1, taille: 25, total: 0, pages: 1 })).toThrow(
      TypeError,
    );
  });
});

describe('validerLesProfilsIncomplets', () => {
  it('accepte une page avec un profil incomplet', () => {
    const resultat = validerLesProfilsIncomplets({
      elements: [
        {
          appartenance_id: 'a1',
          person_id: 'p1',
          prenom: 'Nouvelle',
          nom: 'Arrivante',
          metier_manquant: true,
          cercle_principal_manquant: false,
          dsm_manquant: false,
          statut_manquant: false,
        },
      ],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    });
    expect(resultat.elements[0]?.metierManquant).toBe(true);
  });

  it('refuse une charge non objet', () => {
    expect(() => validerLesProfilsIncomplets(null)).toThrow(TypeError);
  });
});
