/**
 * Le contrat de la lecture des evenements — LOT 8, `T9`.
 *
 * **LA FORME EST CELLE QUE `apps/api/app/events/routes.py` SERT** (`EvenementRendu`,
 * `ReponseDesEvenements`). Un bouchon prouve ce qu'on a ecrit dans le bouchon,
 * jamais ce que l'API fait — §7.43 — donc les noms de champs ci-dessous sont
 * relevés dans le code source Python, pas devines.
 */
import { describe, expect, it } from 'vitest';

import {
  CLASSEMENTS_D_EVENEMENTS,
  cheminEvenements,
  CODES_EVENEMENTS,
  validerLaPageDesEvenements,
} from './evenements.js';

const UNE_PAGE = {
  classement: 'a_venir',
  evenements: [
    {
      identifiant: 'e1',
      titre: 'Petit-dejeuner d’accueil',
      description: 'Rencontre avec les nouveaux arrivants',
      commence_le: '2026-10-12T08:00:00+00:00',
      finit_le: '2026-10-12T09:30:00+00:00',
      lieu: 'Salle Atrium',
      etat: 'published',
      annule_le: null,
      motif_d_annulation: null,
    },
  ],
  page: 1,
  taille: 25,
  total: 1,
  pages: 1,
};

const UN_EVENEMENT_ANNULE = {
  ...UNE_PAGE.evenements[0],
  identifiant: 'e2',
  etat: 'cancelled',
  annule_le: '2026-10-05T10:00:00+00:00',
  motif_d_annulation: 'Intervenant indisponible',
};

describe('les deux classements', () => {
  it('sont ceux du cahier §10.6', () => {
    expect([...CLASSEMENTS_D_EVENEMENTS]).toEqual(['a_venir', 'passes']);
  });
});

describe('les codes exploitables', () => {
  it('annoncent 401, 404 et 422, jamais 403 — la matrice §5 n’examine aucun role', () => {
    expect(CODES_EVENEMENTS).toContain(401);
    expect(CODES_EVENEMENTS).toContain(404);
    expect(CODES_EVENEMENTS).toContain(422);
    expect(CODES_EVENEMENTS).not.toContain(403);
  });
});

describe('le chemin', () => {
  it('encode son segment, et refuse un code vide', () => {
    expect(cheminEvenements('BORDEA 00')).toContain('BORDEA%2000');
    expect(() => cheminEvenements('')).toThrow(TypeError);
  });
});

describe('le validateur', () => {
  it('traduit une page d’evenements a venir', () => {
    const p = validerLaPageDesEvenements(UNE_PAGE);
    expect(p.classement).toBe('a_venir');
    expect(p.evenements).toHaveLength(1);
    expect(p.evenements[0]?.titre).toBe('Petit-dejeuner d’accueil');
    expect(p.evenements[0]?.commenceLe).toBe('2026-10-12T08:00:00+00:00');
  });

  it('refuse un classement inconnu', () => {
    expect(() => validerLaPageDesEvenements({ ...UNE_PAGE, classement: 'en_cours' })).toThrow(
      TypeError,
    );
  });

  it('sert un evenement ANNULE avec son motif — « reste visible avec un badge »', () => {
    const p = validerLaPageDesEvenements({ ...UNE_PAGE, evenements: [UN_EVENEMENT_ANNULE] });
    expect(p.evenements[0]?.etat).toBe('cancelled');
    expect(p.evenements[0]?.annuleLe).toBe('2026-10-05T10:00:00+00:00');
    expect(p.evenements[0]?.motifDAnnulation).toBe('Intervenant indisponible');
  });

  it('distingue une description ABSENTE d’une description manquante', () => {
    const sansDescription = { ...UNE_PAGE.evenements[0], description: null, lieu: null };
    const p = validerLaPageDesEvenements({ ...UNE_PAGE, evenements: [sansDescription] });
    expect(p.evenements[0]?.description).toBeNull();
    expect(p.evenements[0]?.lieu).toBeNull();
  });

  it('refuse un tableau d’evenements ABSENT, la ou vide est accepte', () => {
    const vide = validerLaPageDesEvenements({ ...UNE_PAGE, evenements: [], total: 0, pages: 0 });
    expect(vide.evenements).toEqual([]);
    const sansEvenements: Record<string, unknown> = { ...UNE_PAGE };
    delete sansEvenements['evenements'];
    expect(() => validerLaPageDesEvenements(sansEvenements)).toThrow(TypeError);
  });

  it('accepte `pages` a zero quand le total est nul — different du cercle', () => {
    const vide = { ...UNE_PAGE, evenements: [], total: 0, pages: 0 };
    expect(validerLaPageDesEvenements(vide).pages).toBe(0);
  });

  it('refuse `pages` qui ne correspond pas au calcul sur `total` et `taille`', () => {
    expect(() => validerLaPageDesEvenements({ ...UNE_PAGE, total: 30, pages: 1 })).toThrow(
      TypeError,
    );
    expect(validerLaPageDesEvenements({ ...UNE_PAGE, total: 30, pages: 2 }).pages).toBe(2);
  });

  it('refuse une taille hors du §18.2', () => {
    expect(() => validerLaPageDesEvenements({ ...UNE_PAGE, taille: 30, pages: 1 })).toThrow(
      TypeError,
    );
  });

  it.each(['identifiant', 'titre', 'commence_le', 'finit_le', 'etat'])(
    'refuse un evenement sans « %s »',
    (champ) => {
      const partiel: Record<string, unknown> = { ...UNE_PAGE.evenements[0] };
      delete partiel[champ];
      expect(() => validerLaPageDesEvenements({ ...UNE_PAGE, evenements: [partiel] })).toThrow(
        TypeError,
      );
    },
  );
});
