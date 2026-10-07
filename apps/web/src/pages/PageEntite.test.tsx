/**
 * L'accueil d'une entite a l'ecran — LOT 8, `T11`, `MVP-L08-US001` (2/2) et
 * `MVP-L08-US006` (2/2).
 *
 * LE TEMOIN CENTRAL N'EST PAS UN REFUS, C'EST UNE PRESENCE
 *
 *   Avant `T11`, un role SANS droit d'edition ne voyait STRICTEMENT RIEN de
 *   la presentation — `PanneauEditionDeContenu` rend `null` pour lui. Le
 *   temoin le plus utile de cette sous-etape est donc qu'un role de simple
 *   lecture (`EMP`) voit desormais les CINQ sections, dans l'ordre du cahier
 *   §8.4 — pas seulement qu'il ne voit pas de bouton d'edition.
 *
 * ET UN COUPLE POUR L'OUVERTURE EXTERNE, MEME MOTIF QUE `T39` DU LOT 5
 *
 *   Un lien SERVABLE et un lien REFUSE par `urlEstServable` : la moitie seule
 *   laisserait passer soit un lien qui n'indique jamais l'ouverture externe,
 *   soit un lien refuse qui disparaitrait silencieusement au lieu de
 *   s'afficher desactive et visible.
 */
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageEntite } from './PageEntite';

afterEach(cleanup);

const CODE = 'bordeaux';

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

const ACCUEIL_DE_BASE = {
  presentation: null,
  framework: { responsabilites: [], cercles: [], bureaux: [] },
  arrivees_recentes: { arrivees: [], page: 1, taille: 25, total: 0, pages: 0 },
  evenements_a_venir: {
    classement: 'a_venir',
    evenements: [],
    page: 1,
    taille: 25,
    total: 0,
    pages: 0,
  },
  liens_internes: { liens: [], nombre_de_liens: 0 },
};

let rolesActuels: readonly string[] | null = null;

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: CODE, nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    get permissions() {
      return rolesActuels === null ? null : { roles: rolesActuels };
    },
  }),
}));

/** Route les appels par URL — meme montage que `PanneauEditionDeContenu.test.tsx`. */
function servir(accueil: Record<string, unknown>, listeDeGestion: unknown[] = []): void {
  const appel = vi.fn((url: string) => {
    if (url.endsWith('/accueil')) {
      return Promise.resolve(json(accueil));
    }
    if (url.endsWith('/pages/gestion')) {
      return Promise.resolve(json({ pages: listeDeGestion }));
    }
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json({ personne: 'p1', jeton_csrf: 'x' }));
    }
    throw new Error(`URL non attendue dans ce test : ${url}`);
  });
  vi.stubGlobal('fetch', appel);
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={[`/entites/${CODE}`]}>
      <Routes>
        <Route path="/entites/:code" element={<PageEntite />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("l'accueil compose les cinq sections, dans l'ordre du cahier §8.4", () => {
  it('les affiche TOUTES pour un role SANS droit d’edition — LE TEMOIN CENTRAL', async () => {
    rolesActuels = ['EMP'];
    servir(ACCUEIL_DE_BASE);
    monter();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Presentation' })).toBeTruthy();
    });
    const titres = screen.getAllByRole('heading').map((titre) => titre.textContent);
    expect(titres).toEqual([
      'Presentation',
      'Framework',
      'Arrivees recentes',
      'Evenements a venir',
      'Ressources internes',
    ]);
  });

  it('dit « aucun contenu de presentation » quand `presentation` vaut `null`', async () => {
    rolesActuels = ['EMP'];
    servir(ACCUEIL_DE_BASE);
    monter();
    await waitFor(() => {
      expect(screen.getByText(/Aucun contenu de presentation/)).toBeTruthy();
    });
  });

  it('rend le texte des blocs de presentation, par la clef `texte`', async () => {
    rolesActuels = ['EMP'];
    servir({
      ...ACCUEIL_DE_BASE,
      presentation: {
        identifiant: 'p1',
        type_de_page: 'HOME',
        titre: 'Bienvenue',
        slug: 'presentation',
        publiee_le: null,
        blocs: [
          { identifiant: 'b1', type_de_bloc: 'TITLE', ordre: 0, contenu: { texte: 'Salut !' } },
        ],
        nombre_de_blocs: 1,
      },
    });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Salut !')).toBeTruthy();
    });
  });

  it('une arrivee recente mene au profil, avec sa date', async () => {
    rolesActuels = ['EMP'];
    servir({
      ...ACCUEIL_DE_BASE,
      arrivees_recentes: {
        arrivees: [
          {
            appartenance: 'm1',
            person_id: 'pe1',
            first_name: 'Lea',
            last_name: 'Martin',
            preferred_name: null,
            arrival_date: '2026-10-01',
            short_intro: null,
            fun_fact: null,
          },
        ],
        page: 1,
        taille: 25,
        total: 1,
        pages: 1,
      },
    });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Lea Martin')).toBeTruthy();
    });
    const lien = screen.getByText('Lea Martin').closest('a');
    expect(lien?.getAttribute('href')).toBe(`/entites/${CODE}/trombinoscope/m1`);
    expect(screen.getByText(/Arrive le/).textContent).toContain('2026');
  });

  it('un evenement ANNULE reste visible, avec un badge — jamais une couleur seule', async () => {
    rolesActuels = ['EMP'];
    servir({
      ...ACCUEIL_DE_BASE,
      evenements_a_venir: {
        classement: 'a_venir',
        evenements: [
          {
            identifiant: 'ev1',
            titre: 'Pot de rentree',
            description: null,
            commence_le: '2026-10-10T08:00:00+00:00',
            finit_le: '2026-10-10T09:00:00+00:00',
            lieu: null,
            etat: 'cancelled',
            annule_le: '2026-10-05T00:00:00+00:00',
            motif_d_annulation: null,
          },
        ],
        page: 1,
        taille: 25,
        total: 1,
        pages: 1,
      },
    });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Pot de rentree')).toBeTruthy();
    });
    expect(screen.getByText('Annule')).toBeTruthy();
  });

  describe("l'ouverture externe des liens internes — `MVP-L08-US006` (2/2)", () => {
    const LIEN_SERVABLE = {
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
    const LIEN_REFUSE = {
      identifiant: 'l2',
      libelle: 'Academy',
      //  `https:alert(1)` — protocole `https`, AUCUN hote. `urlEstServable`
      //  le refuse, voir `liens.ts`.
      url: 'https:alert(1)',
      type_de_lien: 'ACADEMY',
      description: null,
      reference_d_icone: null,
      rang: 2,
      actif: true,
      version: 1,
    };

    it('un lien SERVABLE s’ouvre dans un nouvel onglet, et le dit clairement', async () => {
      rolesActuels = ['EMP'];
      servir({
        ...ACCUEIL_DE_BASE,
        liens_internes: { liens: [LIEN_SERVABLE], nombre_de_liens: 1 },
      });
      monter();
      await waitFor(() => {
        expect(screen.getByText('Hub')).toBeTruthy();
      });
      const lien = screen.getByText('Hub').closest('a');
      expect(lien?.getAttribute('target')).toBe('_blank');
      expect(lien?.getAttribute('rel')).toBe('noopener noreferrer');
      expect(lien?.textContent).toContain('Ouvre dans un nouvel onglet');
    });

    it('un lien REFUSE par `urlEstServable` s’affiche DESACTIVE et VISIBLE, jamais absent', async () => {
      rolesActuels = ['EMP'];
      servir({
        ...ACCUEIL_DE_BASE,
        liens_internes: { liens: [LIEN_REFUSE], nombre_de_liens: 1 },
      });
      monter();
      await waitFor(() => {
        expect(screen.getByText('Academy')).toBeTruthy();
      });
      expect(screen.getByText('Academy').closest('a')).toBeNull();
      expect(screen.getByText('Adresse non affichable')).toBeTruthy();
    });
  });

  it('ne propose PAS « Gerer les liens internes » a un role sans ce droit', async () => {
    rolesActuels = ['EMP'];
    servir(ACCUEIL_DE_BASE);
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Ressources internes' })).toBeTruthy();
    });
    expect(screen.queryByText('Gerer les liens internes')).toBeNull();
  });

  it('propose « Gerer les liens internes » a un role qui le peut — ESM', async () => {
    rolesActuels = ['ESM'];
    servir(ACCUEIL_DE_BASE);
    monter();
    await waitFor(() => {
      expect(screen.getByText('Gerer les liens internes')).toBeTruthy();
    });
  });

  it("l'edition de la presentation COEXISTE avec sa lecture, pour un role editeur — pas de regression", async () => {
    rolesActuels = ['ESM'];
    servir(ACCUEIL_DE_BASE, []);
    monter();
    //  **LE PANNEAU D'EDITION RESTE LA**, exactement comme avant `T11` : un
    //  role qui pouvait deja creer la page de presentation le peut toujours.
    await waitFor(() => {
      expect(screen.getByText('Creer la page')).toBeTruthy();
    });
  });

  it('refuse par defaut — une session expiree (401) l’affiche, jamais un cadre vide', async () => {
    rolesActuels = ['EMP'];
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'non_authentifie' } }, 401))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText(/session a expire/)).toBeTruthy();
    });
  });
});

describe("`T12` : les trois listes de l'accueil defilent en carrousel", () => {
  const DEUX_ARRIVEES = {
    arrivees: [
      {
        appartenance: 'm1',
        person_id: 'pe1',
        first_name: 'Ada',
        last_name: 'Lovelace',
        preferred_name: null,
        arrival_date: '2026-10-01',
        short_intro: null,
        fun_fact: null,
      },
      {
        appartenance: 'm2',
        person_id: 'pe2',
        first_name: 'Grace',
        last_name: 'Hopper',
        preferred_name: null,
        arrival_date: '2026-10-02',
        short_intro: null,
        fun_fact: null,
      },
    ],
    page: 1,
    taille: 25,
    total: 2,
    pages: 1,
  };

  const DEUX_EVENEMENTS = {
    classement: 'a_venir',
    evenements: [
      {
        identifiant: 'ev1',
        titre: 'Pot de rentree',
        description: null,
        commence_le: '2026-10-10T08:00:00+00:00',
        finit_le: '2026-10-10T09:00:00+00:00',
        lieu: null,
        etat: 'published',
        annule_le: null,
        motif_d_annulation: null,
      },
      {
        identifiant: 'ev2',
        titre: 'Atelier accueil',
        description: null,
        commence_le: '2026-10-12T08:00:00+00:00',
        finit_le: '2026-10-12T09:00:00+00:00',
        lieu: null,
        etat: 'published',
        annule_le: null,
        motif_d_annulation: null,
      },
    ],
    page: 1,
    taille: 25,
    total: 2,
    pages: 1,
  };

  const DEUX_LIENS = {
    liens: [
      {
        identifiant: 'l1',
        libelle: 'Hub',
        url: 'https://hub.exemple.test/',
        type_de_lien: 'HUB',
        description: null,
        reference_d_icone: null,
        rang: 1,
        actif: true,
        version: 1,
      },
      {
        identifiant: 'l2',
        libelle: 'eXalt Academy',
        url: 'https://academy.exemple.test/',
        type_de_lien: 'ACADEMY',
        description: null,
        reference_d_icone: null,
        rang: 2,
        actif: true,
        version: 1,
      },
    ],
    nombre_de_liens: 2,
  };

  it('arrivees recentes : une region nommee, deux commandes, et TOUS les elements presents', async () => {
    rolesActuels = ['EMP'];
    servir({ ...ACCUEIL_DE_BASE, arrivees_recentes: DEUX_ARRIVEES });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    });
    const region = screen.getByRole('region', { name: 'Arrivees recentes' });
    const piste = within(region).getByRole('list', { name: 'Arrivees recentes' });
    expect(within(piste).getByText('Ada Lovelace')).toBeTruthy();
    expect(within(piste).getByText('Grace Hopper')).toBeTruthy();
    expect(
      within(region).getByRole('button', { name: 'Arrivees recentes : element precedent' }),
    ).toBeTruthy();
    expect(
      within(region).getByRole('button', { name: 'Arrivees recentes : element suivant' }),
    ).toBeTruthy();
  });

  it('evenements a venir : la Carte porte un carrousel avec les deux evenements', async () => {
    rolesActuels = ['EMP'];
    servir({ ...ACCUEIL_DE_BASE, evenements_a_venir: DEUX_EVENEMENTS });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Pot de rentree')).toBeTruthy();
    });
    const piste = screen.getByRole('list', { name: 'Evenements a venir' });
    expect(within(piste).getByText('Pot de rentree')).toBeTruthy();
    expect(within(piste).getByText('Atelier accueil')).toBeTruthy();
  });

  it("liens internes : un carrousel, MEME SANS plafond `NOMBRE_MONTRE` — aucun n'a jamais ete tronque ici", async () => {
    rolesActuels = ['EMP'];
    servir({ ...ACCUEIL_DE_BASE, liens_internes: DEUX_LIENS });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Hub')).toBeTruthy();
    });
    const piste = screen.getByRole('list', { name: 'Ressources internes' });
    expect(within(piste).getByText('Hub')).toBeTruthy();
    expect(within(piste).getByText('eXalt Academy')).toBeTruthy();
  });

  it('aucun carrousel n’apparait quand la section est vide — pas de commandes inutiles', async () => {
    rolesActuels = ['EMP'];
    servir(ACCUEIL_DE_BASE);
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Arrivees recentes' })).toBeTruthy();
    });
    //  La `<Carte>` reste une region nommee dans les deux etats (vide ou non) :
    //  c'est l'absence de LISTE, pas de region, qui distingue le carrousel.
    expect(screen.queryByRole('list', { name: 'Arrivees recentes' })).toBeNull();
    expect(screen.queryByRole('list', { name: 'Evenements a venir' })).toBeNull();
    expect(screen.queryByRole('list', { name: 'Ressources internes' })).toBeNull();
  });
});
