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
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageEntite } from './PageEntite';

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

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
      expect(screen.getByRole('heading', { name: 'eXalt Bordeaux' })).toBeTruthy();
    });
    //  **LES DEUX PREMIERS TITRES ONT CHANGE A `E5`, ET C'EST LA CHARTE 6.2.**
    //  « Presentation » etait le titre d'une `Carte` ; la charte en fait une
    //  PASTILLE — « Presentation de l'entite » — surmontant le nom de l'entite,
    //  qui devient le titre de la section. Le second est l'emplacement pose
    //  pour la video et les tuiles, en attente de contenu (arbitrage de
    //  Jonathan du 02/11/2026).
    //
    //  **LE RESTE DE L'ORDRE EST INCHANGE, ET C'EST CE QUI COMPTE ICI** : les
    //  cinq sections du cahier §8.4 se suivent toujours dans leur ordre, et
    //  c'est ce que ce temoin eprouve depuis `T11` du LOT 8.
    const titres = screen.getAllByRole('heading', { level: 2 }).map((titre) => titre.textContent);
    expect(titres).toEqual([
      'eXalt Bordeaux',
      'Le mot de la direction',
      'Découvre ton parcours d’onboarding',
      'Les moments à ne pas manquer',
      'Framework',
      'Arrivees recentes',
      'Ressources internes',
    ]);
    //  La pastille de la charte porte bien le mot que la `Carte` portait avant.
    expect(screen.getByText(/Presentation de l.entite/)).toBeTruthy();
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
      expect(screen.getAllByText('Pot de rentree').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('Annulé')).toBeTruthy();
  });

  it('actualise le compte à rebours chaque seconde', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-03T12:00:00Z'));
    rolesActuels = ['EMP'];
    servir({
      ...ACCUEIL_DE_BASE,
      evenements_a_venir: {
        classement: 'a_venir',
        evenements: [
          {
            identifiant: 'ev-direct',
            titre: 'Rendez-vous direct',
            description: null,
            commence_le: '2026-11-03T12:00:05+00:00',
            finit_le: '2026-11-03T13:00:00+00:00',
            lieu: null,
            image: null,
            etat: 'published',
            annule_le: null,
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
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    const compte = screen.getByLabelText('Compte à rebours avant Rendez-vous direct');
    expect(within(compte).getByText('05')).toBeTruthy();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(within(compte).getByText('04')).toBeTruthy();
  });

  it('rend les dates du calendrier cliquables et affiche le détail sélectionné', async () => {
    rolesActuels = ['EMP'];
    servir({
      ...ACCUEIL_DE_BASE,
      evenements_a_venir: {
        classement: 'a_venir',
        evenements: [
          {
            identifiant: 'ev-1',
            titre: 'Premier événement',
            description: 'Premier détail',
            commence_le: '2026-11-05T18:00:00+00:00',
            finit_le: '2026-11-05T20:00:00+00:00',
            lieu: 'Bordeaux',
            image: null,
            etat: 'published',
            annule_le: null,
            motif_d_annulation: null,
          },
          {
            identifiant: 'ev-2',
            titre: 'Deuxième événement',
            description: 'Deuxième détail',
            commence_le: '2026-11-10T18:00:00+00:00',
            finit_le: '2026-11-10T20:00:00+00:00',
            lieu: 'Mérignac',
            image: null,
            etat: 'published',
            annule_le: null,
            motif_d_annulation: null,
          },
        ],
        page: 1,
        taille: 25,
        total: 2,
        pages: 1,
      },
    });
    monter();
    const date = await screen.findByRole('button', { name: /Deuxième événement/ });
    fireEvent.click(date);

    const detail = document.querySelector('.temps-forts-selection') as HTMLElement;
    expect(within(detail).getByText('Deuxième événement')).toBeTruthy();
    expect(within(detail).getByText('Deuxième détail')).toBeTruthy();
    expect(date.getAttribute('aria-pressed')).toBe('true');
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

  it("garde l'accueil en lecture seule pour un role editeur", async () => {
    rolesActuels = ['ESM'];
    servir(ACCUEIL_DE_BASE, []);
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'eXalt Bordeaux' })).toBeTruthy();
    });
    expect(screen.queryByText('Creer la page')).toBeNull();
    expect(screen.queryByText(/Etat :/)).toBeNull();
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

  it('les temps forts reprennent les deux événements dans les rendez-vous', async () => {
    rolesActuels = ['EMP'];
    servir({ ...ACCUEIL_DE_BASE, evenements_a_venir: DEUX_EVENEMENTS });
    monter();
    await waitFor(() => {
      expect(screen.getAllByText('Pot de rentree').length).toBeGreaterThan(0);
    });
    const region = screen.getByRole('region', { name: '🔥 Prochains rendez-vous' });
    expect(within(region).getByText('Pot de rentree')).toBeTruthy();
    expect(within(region).getByText('Atelier accueil')).toBeTruthy();
  });

  it('duplique les événements dans une piste continue purement décorative', async () => {
    rolesActuels = ['EMP'];
    servir({ ...ACCUEIL_DE_BASE, evenements_a_venir: DEUX_EVENEMENTS });
    monter();
    await waitFor(() => {
      expect(screen.getAllByText('Pot de rentree').length).toBeGreaterThan(0);
    });

    const bandeau = document.querySelector('.temps-forts-defile');
    expect(bandeau?.getAttribute('aria-hidden')).toBe('true');
    const groupes = bandeau?.querySelectorAll('.temps-forts-defile-groupe') ?? [];
    expect(groupes).toHaveLength(2);
    for (const groupe of groupes) {
      expect(groupe.textContent).toContain('Pot de rentree');
      expect(groupe.textContent).toContain('Atelier accueil');
    }
    expect(groupes[1]?.getAttribute('data-copie')).toBe('true');
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
    expect(screen.queryByRole('region', { name: '🔥 Prochains rendez-vous' })).toBeNull();
    expect(screen.queryByRole('list', { name: 'Ressources internes' })).toBeNull();
  });
});

describe('chantier front, S4 : des `Badge` pour les compteurs (`DEC-672`)', () => {
  const FRAMEWORK_AVEC_DONNEES = {
    responsabilites: [
      {
        type_de_responsabilite: 'DSM',
        titulaires: [{ identifiant: 't1', prenom: 'Ada', nom: 'Lovelace' }],
        chemin_detaille: null,
      },
      { type_de_responsabilite: 'BOOSTER', titulaires: [], chemin_detaille: null },
    ],
    cercles: [
      {
        identifiant: 'c1',
        code: 'C1',
        nom: 'Cercle un',
        description: null,
        jeton_de_couleur: null,
        booster: null,
        membres_actifs: 3,
        chemin_detaille: '/x',
      },
      {
        identifiant: 'c2',
        code: 'C2',
        nom: 'Cercle deux',
        description: null,
        jeton_de_couleur: null,
        booster: null,
        membres_actifs: 2,
        chemin_detaille: '/y',
      },
    ],
    bureaux: [
      {
        identifiant: 'b1',
        code: 'B1',
        nom: 'Bureau un',
        description: null,
        localisation: null,
        responsables: [],
        chemin_detaille: '/z',
      },
    ],
  };

  it('Framework : trois Badge, derives des listes et non d’une phrase prose', async () => {
    rolesActuels = ['EMP'];
    servir({ ...ACCUEIL_DE_BASE, framework: FRAMEWORK_AVEC_DONNEES });
    monter();
    await waitFor(() => {
      expect(screen.getByText('2 cercles')).toBeTruthy();
    });
    expect(screen.getByText('1 bureau')).toBeTruthy();
    //  Une seule des deux responsabilites a un titulaire : le compte est
    //  POURVUES, pas le nombre total de responsabilites du Framework.
    expect(screen.getByText('1 responsabilite pourvue')).toBeTruthy();
    //  Et chacun est bien un `Badge` du design system (`.ex-badge`), pas un
    //  texte libre : la classe porte le ton `marque` pose par le composant.
    expect(screen.getByText('2 cercles').closest('.ex-badge')).toBeTruthy();
  });

  it('Framework : zero cercle, bureau et responsabilite se lisent au singulier', async () => {
    rolesActuels = ['EMP'];
    servir(ACCUEIL_DE_BASE);
    monter();
    await waitFor(() => {
      expect(screen.getByText('0 cercle')).toBeTruthy();
    });
    expect(screen.getByText('0 bureau')).toBeTruthy();
    expect(screen.getByText('0 responsabilite pourvue')).toBeTruthy();
  });

  it('Arrivees recentes : le Badge reflete le TOTAL, pas la longueur de la page affichee', async () => {
    rolesActuels = ['EMP'];
    servir({
      ...ACCUEIL_DE_BASE,
      arrivees_recentes: {
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
        ],
        page: 1,
        taille: 25,
        total: 5,
        pages: 1,
      },
    });
    monter();
    await waitFor(() => {
      expect(screen.getByText('5 arrivees')).toBeTruthy();
    });
  });

  it('Arrivees recentes : aucun Badge quand la section est vide — l’Alerte suffit deja', async () => {
    rolesActuels = ['EMP'];
    servir(ACCUEIL_DE_BASE);
    monter();
    await waitFor(() => {
      expect(screen.getByText('Aucune arrivee recente pour le moment.')).toBeTruthy();
    });
    const badges = [...document.querySelectorAll('.ex-badge')].map((b) => b.textContent ?? '');
    expect(badges.some((texte) => texte.includes('arrivee'))).toBe(false);
  });

  it('les temps forts affichent les événements et un état vide explicite', async () => {
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
            etat: 'published',
            annule_le: null,
            motif_d_annulation: null,
          },
        ],
        page: 1,
        taille: 25,
        total: 3,
        pages: 1,
      },
    });
    monter();
    await waitFor(() => {
      expect(screen.getAllByText('Pot de rentree').length).toBeGreaterThan(0);
    });

    cleanup();
    rolesActuels = ['EMP'];
    servir(ACCUEIL_DE_BASE);
    monter();
    await waitFor(() => {
      expect(screen.getByText('Aucun événement à venir pour le moment.')).toBeTruthy();
    });
    expect(screen.queryByRole('region', { name: '🔥 Prochains rendez-vous' })).toBeNull();
  });
});
