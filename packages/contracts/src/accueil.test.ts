/**
 * Le contrat de l'agrégat d'accueil — LOT 8, `T11`.
 */
import { describe, expect, it } from 'vitest';

import {
  cheminAccueil,
  CODES_ACCUEIL,
  validerLaPageDesArriveesRecentes,
  validerLAccueil,
} from './accueil.js';

const UNE_PRESENTATION = {
  identifiant: 'p1',
  type_de_page: 'HOME',
  titre: 'Bienvenue',
  slug: 'presentation',
  publiee_le: '2026-10-01T08:00:00+00:00',
  blocs: [{ identifiant: 'b1', type_de_bloc: 'TITLE', ordre: 0, contenu: { texte: 'Bonjour' } }],
  nombre_de_blocs: 1,
};

const UN_FRAMEWORK = {
  responsabilites: [],
  cercles: [],
  bureaux: [],
};

const UNE_ARRIVEE = {
  appartenance: 'm1',
  person_id: 'pe1',
  first_name: 'Lea',
  last_name: 'Martin',
  preferred_name: null,
  arrival_date: '2026-10-01',
  short_intro: null,
  fun_fact: null,
};

const UN_EVENEMENT = {
  identifiant: 'e1',
  titre: 'Pot de rentree',
  description: null,
  commence_le: '2026-10-10T08:00:00+00:00',
  finit_le: '2026-10-10T09:00:00+00:00',
  lieu: null,
  etat: 'published',
  annule_le: null,
  motif_d_annulation: null,
};

const UN_LIEN = {
  identifiant: 'l1',
  libelle: 'Hub',
  url: 'https://hub.exemple.test/',
  type_de_lien: 'HUB',
  description: null,
  reference_d_icone: null,
  rang: 1,
  actif: true,
  version: 1,
};

function unAccueil(remplacements: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    presentation: UNE_PRESENTATION,
    framework: UN_FRAMEWORK,
    arrivees_recentes: { arrivees: [UNE_ARRIVEE], page: 1, taille: 25, total: 1, pages: 1 },
    evenements_a_venir: {
      classement: 'a_venir',
      evenements: [UN_EVENEMENT],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    },
    liens_internes: { liens: [UN_LIEN], nombre_de_liens: 1 },
    ...remplacements,
  };
}

describe('le chemin', () => {
  it('encode son segment et refuse un code vide', () => {
    expect(cheminAccueil('BORDEA 00')).toContain('BORDEA%2000');
    expect(cheminAccueil('x').endsWith('/accueil')).toBe(true);
    expect(() => cheminAccueil('')).toThrow(TypeError);
  });
});

describe('les codes exploitables', () => {
  it('n’annoncent AUCUN 403, et c’est le point', () => {
    //  La matrice §5 accorde la Lecture aux HUIT roles sans distinction sur
    //  chacune des six ressources composees : il n'y a aucun role a refuser.
    expect(CODES_ACCUEIL).not.toContain(403);
    expect(CODES_ACCUEIL).toContain(401);
    expect(CODES_ACCUEIL).toContain(404);
  });
});

describe('le validateur de l’accueil', () => {
  it('valide les cinq sections, dans leur forme camelCase', () => {
    const accueil = validerLAccueil(unAccueil());
    expect(accueil.presentation?.titre).toBe('Bienvenue');
    expect(accueil.framework).toEqual({ responsabilites: [], cercles: [], bureaux: [] });
    expect(accueil.arriveesRecentes.arrivees).toHaveLength(1);
    expect(accueil.arriveesRecentes.arrivees[0]).toEqual({
      appartenance: 'm1',
      personneId: 'pe1',
      prenom: 'Lea',
      nom: 'Martin',
      nomPrefere: null,
      dateArrivee: '2026-10-01',
      presentationCourte: null,
      funFact: null,
    });
    expect(accueil.evenementsAVenir.evenements).toHaveLength(1);
    expect(accueil.liensInternes.liens).toHaveLength(1);
  });

  it('accepte `presentation` a `null` — etat valide, pas une erreur', () => {
    const accueil = validerLAccueil(unAccueil({ presentation: null }));
    expect(accueil.presentation).toBeNull();
  });

  it('refuse `presentation` quand elle n’est ni objet ni null', () => {
    expect(() => validerLAccueil(unAccueil({ presentation: 'texte' }))).toThrow(TypeError);
  });

  it('refuse une charge utile non objet', () => {
    expect(() => validerLAccueil(null)).toThrow(TypeError);
    expect(() => validerLAccueil('x')).toThrow(TypeError);
  });

  it('refuse un Framework malforme — delegation reelle, pas une copie', () => {
    expect(() =>
      validerLAccueil(unAccueil({ framework: { responsabilites: [], cercles: [] } })),
    ).toThrow(TypeError);
  });

  it('refuse des liens internes malformes — delegation reelle', () => {
    expect(() => validerLAccueil(unAccueil({ liens_internes: { liens: [UN_LIEN] } }))).toThrow(
      TypeError,
    );
  });

  it('refuse des evenements malformes — delegation reelle', () => {
    expect(() =>
      validerLAccueil(
        unAccueil({
          evenements_a_venir: { evenements: [UN_EVENEMENT], page: 1, taille: 25, total: 1 },
        }),
      ),
    ).toThrow(TypeError);
  });
});

describe('les arrivees recentes', () => {
  it('rendent une liste vide, zero etant un total legitime', () => {
    const page = validerLaPageDesArriveesRecentes({
      arrivees: [],
      page: 1,
      taille: 25,
      total: 0,
      pages: 0,
    });
    expect(page.arrivees).toEqual([]);
  });

  it('exigent `pages` confronte a `total` et `taille` PAR LE CALCUL', () => {
    expect(() =>
      validerLaPageDesArriveesRecentes({
        arrivees: [UNE_ARRIVEE],
        page: 1,
        taille: 25,
        total: 26,
        pages: 1,
      }),
    ).toThrow(TypeError);
  });

  it('refusent un tableau « arrivees » absent — ce n’est pas un tableau vide', () => {
    expect(() =>
      validerLaPageDesArriveesRecentes({ page: 1, taille: 25, total: 0, pages: 0 }),
    ).toThrow(TypeError);
  });

  it('traduisent les colonnes de l’API au vocabulaire deja etabli', () => {
    const page = validerLaPageDesArriveesRecentes({
      arrivees: [
        {
          appartenance: 'm2',
          person_id: 'pe2',
          first_name: 'Omar',
          last_name: 'Durand',
          preferred_name: 'Omar D.',
          arrival_date: '2026-09-15',
          short_intro: 'Ravi de rejoindre l’equipe',
          fun_fact: 'Parle trois langues',
        },
      ],
      page: 1,
      taille: 25,
      total: 1,
      pages: 1,
    });
    expect(page.arrivees[0]).toEqual({
      appartenance: 'm2',
      personneId: 'pe2',
      prenom: 'Omar',
      nom: 'Durand',
      nomPrefere: 'Omar D.',
      dateArrivee: '2026-09-15',
      presentationCourte: 'Ravi de rejoindre l’equipe',
      funFact: 'Parle trois langues',
    });
  });
});
