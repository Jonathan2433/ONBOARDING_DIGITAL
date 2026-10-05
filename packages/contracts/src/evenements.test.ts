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
  cheminAnnulationDEvenement,
  cheminArchivageDEvenement,
  cheminEvenement,
  cheminEvenements,
  cheminEvenementPourGestion,
  cheminEvenementsPourGestion,
  cheminMediasDEvenement,
  cheminPublicationDEvenement,
  cheminRestaurationDEvenement,
  CLASSEMENTS_D_EVENEMENTS,
  CODES_EVENEMENTS,
  peutGererLesEvenements,
  peutRestaurerUnEvenement,
  ROLES_GESTION_DES_EVENEMENTS,
  ROLES_RESTAURATION_D_UN_EVENEMENT,
  validerLaPageDesEvenements,
  validerLesEvenementsPourGestion,
  validerLesMediasDEvenement,
  validerLEvenementAnnule,
  validerLEvenementArchive,
  validerLEvenementCree,
  validerLEvenementEcrit,
  validerLEvenementPourGestion,
  validerLEvenementRestaure,
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

// =============================================================================
//  La gestion — LOT 8, `T10`
// =============================================================================

describe('les chemins de gestion', () => {
  it('encodent leurs deux segments, et refusent un code ou un evenement vide', () => {
    expect(cheminEvenement('BORDEA 00', 'e1')).toContain('BORDEA%2000');
    expect(cheminPublicationDEvenement('BORDEA00', 'e 1')).toContain('e%201');
    expect(cheminAnnulationDEvenement('BORDEA00', 'e1')).toContain('/annulation');
    expect(cheminArchivageDEvenement('BORDEA00', 'e1')).toContain('/archivage');
    expect(cheminRestaurationDEvenement('BORDEA00', 'e1')).toContain('/restauration');
    expect(cheminMediasDEvenement('BORDEA00', 'e1')).toContain('/medias');
    expect(cheminEvenementPourGestion('BORDEA00', 'e1')).toContain('/gestion');

    expect(() => cheminEvenement('', 'e1')).toThrow(TypeError);
    expect(() => cheminEvenement('BORDEA00', '')).toThrow(TypeError);
    expect(() => cheminEvenementsPourGestion('')).toThrow(TypeError);
  });

  it('cheminEvenementsPourGestion encode son seul segment', () => {
    expect(cheminEvenementsPourGestion('BORDEA 00')).toContain('BORDEA%2000');
  });
});

const EVENEMENT_DE_GESTION = {
  identifiant: 'e1',
  titre: 'Brouillon',
  etat: 'draft',
  commence_le: '2026-10-12T08:00:00+00:00',
  finit_le: '2026-10-12T09:30:00+00:00',
  version: 1,
};

describe('le validateur de la liste de gestion', () => {
  it('traduit un sommaire, brouillon compris — la lecture publique le refuse', () => {
    const p = validerLesEvenementsPourGestion({ evenements: [EVENEMENT_DE_GESTION] });
    expect(p.evenements[0]?.etat).toBe('draft');
    expect(p.evenements[0]?.version).toBe(1);
  });

  it('refuse un tableau ABSENT, la ou vide est accepte', () => {
    expect(validerLesEvenementsPourGestion({ evenements: [] }).evenements).toEqual([]);
    expect(() => validerLesEvenementsPourGestion({})).toThrow(TypeError);
  });
});

const EVENEMENT_POUR_GESTION = {
  identifiant: 'e1',
  titre: 'Brouillon',
  description: null,
  commence_le: '2026-10-12T08:00:00+00:00',
  finit_le: '2026-10-12T09:30:00+00:00',
  lieu: null,
  etat: 'draft',
  version: 1,
  annule_le: null,
  motif_d_annulation: null,
  archive_le: null,
  cercles: ['CERCLE-A'],
  bureaux: [],
  medias: [{ media: 'm1', role: 'Affiche', ordre: 0 }],
};

describe('le validateur de la lecture unique de gestion', () => {
  it('porte version, cercles, bureaux et medias — ce que T2 ne porte jamais', () => {
    const e = validerLEvenementPourGestion(EVENEMENT_POUR_GESTION);
    expect(e.version).toBe(1);
    expect(e.cercles).toEqual(['CERCLE-A']);
    expect(e.bureaux).toEqual([]);
    expect(e.medias).toEqual([{ media: 'm1', role: 'Affiche', ordre: 0 }]);
  });

  it('rend un evenement ARCHIVE avec sa date', () => {
    const e = validerLEvenementPourGestion({
      ...EVENEMENT_POUR_GESTION,
      etat: 'archived',
      archive_le: '2026-10-05T10:00:00+00:00',
    });
    expect(e.etat).toBe('archived');
    expect(e.archiveLe).toBe('2026-10-05T10:00:00+00:00');
  });

  it('refuse « cercles »/« bureaux »/« medias » qui ne sont pas des tableaux', () => {
    expect(() =>
      validerLEvenementPourGestion({ ...EVENEMENT_POUR_GESTION, cercles: 'CERCLE-A' }),
    ).toThrow(TypeError);
    expect(() => validerLEvenementPourGestion({ ...EVENEMENT_POUR_GESTION, bureaux: [1] })).toThrow(
      TypeError,
    );
    expect(() => validerLEvenementPourGestion({ ...EVENEMENT_POUR_GESTION, medias: {} })).toThrow(
      TypeError,
    );
  });
});

describe('les validateurs des reponses d’ecriture', () => {
  it('validerLEvenementCree traduit la portee', () => {
    const c = validerLEvenementCree({
      identifiant: 'e1',
      titre: 'Nouveau',
      description: null,
      commence_le: '2026-10-12T08:00:00+00:00',
      finit_le: '2026-10-12T09:30:00+00:00',
      lieu: null,
      etat: 'draft',
      version: 1,
      portee: 'consultants',
    });
    expect(c.portee).toBe('consultants');
    expect(() =>
      validerLEvenementCree({
        identifiant: 'e1',
        titre: 'Nouveau',
        description: null,
        commence_le: '2026-10-12T08:00:00+00:00',
        finit_le: '2026-10-12T09:30:00+00:00',
        lieu: null,
        etat: 'draft',
        version: 1,
        portee: 'inventee',
      }),
    ).toThrow(TypeError);
  });

  it('validerLEvenementEcrit sert modifier ET publier, meme forme', () => {
    const e = validerLEvenementEcrit({
      identifiant: 'e1',
      titre: 'Modifie',
      description: null,
      commence_le: '2026-10-12T08:00:00+00:00',
      finit_le: '2026-10-12T09:30:00+00:00',
      lieu: null,
      etat: 'published',
      version: 2,
    });
    expect(e.etat).toBe('published');
    expect(e.version).toBe(2);
  });

  it('validerLEvenementAnnule porte le motif, facultatif', () => {
    const a = validerLEvenementAnnule({
      version: 3,
      etat: 'cancelled',
      annule_le: '2026-10-05T10:00:00+00:00',
      motif_d_annulation: null,
    });
    expect(a.etat).toBe('cancelled');
    expect(a.motifDAnnulation).toBeNull();
  });

  it('validerLEvenementArchive porte sa date', () => {
    const a = validerLEvenementArchive({
      version: 4,
      etat: 'archived',
      archive_le: '2026-10-05T10:00:00+00:00',
    });
    expect(a.archiveLe).toBe('2026-10-05T10:00:00+00:00');
  });

  it('validerLEvenementRestaure ne rend JAMAIS que draft — pas un troisieme champ', () => {
    const r = validerLEvenementRestaure({ version: 5, etat: 'draft' });
    expect(r).toEqual({ version: 5, etat: 'draft' });
  });

  it('validerLesMediasDEvenement traduit la liste ordonnee', () => {
    const m = validerLesMediasDEvenement({
      version: 6,
      medias: [
        { media: 'm1', role: 'Affiche', ordre: 0 },
        { media: 'm2', role: 'Video', ordre: 1 },
      ],
    });
    expect(m.medias).toHaveLength(2);
    expect(m.medias[1]?.role).toBe('Video');
  });
});

describe('les roles de gestion, lus du manifeste', () => {
  it('rolesGestionDesEvenements est plus LARGE que rolesRestaurationDUnEvenement', () => {
    for (const role of ROLES_RESTAURATION_D_UN_EVENEMENT) {
      expect(ROLES_GESTION_DES_EVENEMENTS).toContain(role);
    }
    expect(ROLES_GESTION_DES_EVENEMENTS.length).toBeGreaterThan(
      ROLES_RESTAURATION_D_UN_EVENEMENT.length,
    );
  });

  it('peutGererLesEvenements/peutRestaurerUnEvenement ne decident rien seuls', () => {
    expect(peutGererLesEvenements(['DSM'])).toBe(true);
    expect(peutGererLesEvenements(['EMP'])).toBe(false);
    expect(peutRestaurerUnEvenement(['DSM'])).toBe(false);
    expect(peutRestaurerUnEvenement(['ESM'])).toBe(true);
  });
});
