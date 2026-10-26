/**
 * La page Framework a l'ecran — LOT 6, `T9`, story `MVP-L06-US001`.
 *
 * CE FICHIER PORTE LE COUPLE DU §7.42, ET LA NAVIGATION REELLE VERS `T9`
 *
 *   Un cercle AVEC jeton, un cercle SANS — `jeton_de_couleur` etant nullable au
 *   catalogue. Une moitie seule laisserait passer le defaut `T10-8` : `str(None)`
 *   rendu comme un jeton plausible, ou une bordure qui ne se colore jamais.
 *
 *   **La navigation d'une carte de cercle est EPROUVEE, pas supposee** : le test
 *   monte `PageFramework` ET `PageCercle` sous le MEME routeur, clique le lien
 *   d'un cercle, et verifie que la page de cercle s'affiche reellement. Sans
 *   cela, `cercle.cheminDetaille` pourrait pointer n'importe ou et le test ne le
 *   verrait pas — §7.43, un bouchon prouve ce qu'on y a ecrit.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageCercle } from './PageCercle';
import { PageFramework } from './PageFramework';

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: null,
  }),
}));

afterEach(() => {
  cleanup();
});

const FRAMEWORK = {
  responsabilites: [
    {
      type_de_responsabilite: 'DSM',
      titulaires: [{ identifiant: 'p1', prenom: 'Ada', nom: 'Lovelace' }],
      chemin_detaille: '/entites/bordeaux/framework/responsabilites/dsm',
    },
    {
      type_de_responsabilite: 'ESM',
      titulaires: [],
      chemin_detaille: '/entites/bordeaux/framework/responsabilites/esm',
    },
    { type_de_responsabilite: 'BOOSTER', titulaires: [], chemin_detaille: null },
    { type_de_responsabilite: 'OFFICE_MANAGER', titulaires: [], chemin_detaille: null },
  ],
  cercles: [
    {
      identifiant: 'c1',
      code: 'data',
      nom: 'Data',
      description: null,
      jeton_de_couleur: 'bleu',
      booster: null,
      membres_actifs: 3,
      chemin_detaille: '/entites/bordeaux/framework/cercles/data',
    },
    {
      identifiant: 'c2',
      code: 'shield',
      nom: 'Shield',
      description: null,
      //  **LA SECONDE MOITIE DU COUPLE** : aucun jeton, et le nom doit rester lisible.
      jeton_de_couleur: null,
      booster: null,
      membres_actifs: 0,
      chemin_detaille: '/entites/bordeaux/framework/cercles/shield',
    },
  ],
  bureaux: [
    {
      identifiant: 'b1',
      code: 'siege',
      nom: 'Siege',
      description: null,
      localisation: null,
      responsables: [],
      chemin_detaille: '/entites/bordeaux/framework/bureaux/siege',
    },
  ],
};

const CERCLE_DATA = {
  identifiant: 'c1',
  code: 'data',
  nom: 'Data',
  description: 'Le cercle Data',
  jeton_de_couleur: 'bleu',
  booster: null,
  membres: [],
  total_des_membres: 0,
  page: 1,
  taille: 25,
  pages: 1,
  chemin_detaille: '/entites/bordeaux/framework/cercles/data',
};

function reponse(corps: unknown): Response {
  return new Response(JSON.stringify(corps), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/framework']}>
      <Routes>
        <Route path="/entites/:code/framework" element={<PageFramework />} />
        <Route path="/entites/:code/framework/cercles/:codeCercle" element={<PageCercle />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('la page Framework a l’ecran', () => {
  it('affiche les trois familles — LE TEMOIN CENTRAL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    expect(screen.getByText('Shield')).toBeTruthy();
    expect(screen.getByText('Siege')).toBeTruthy();
    expect(screen.getByText('Ada Lovelace')).toBeTruthy();
  });

  it('LE COUPLE DU §7.42 : le nom du cercle reste du texte, avec jeton OU sans', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    const avecJeton = screen.getByText('Data').closest('a');
    const sansJeton = screen.getByText('Shield').closest('a');
    expect(avecJeton).not.toBeNull();
    expect(sansJeton).not.toBeNull();
    //  Le jeton pose une propriete personnalisee EN LIGNE ; son absence n'en
    //  pose aucune, et la feuille la declare a une valeur neutre (§7.42).
    expect(avecJeton?.style.getPropertyValue('--framework-cercle-couleur')).not.toBe('');
    expect(sansJeton?.style.getPropertyValue('--framework-cercle-couleur')).toBe('');
    //  Et le nom est du texte dans LES DEUX CAS — jamais porte par la seule couleur.
    expect(avecJeton?.textContent).toContain('Data');
    expect(sansJeton?.textContent).toContain('Shield');
  });

  it('les cartes de responsabilite DSM et ESM ne sont PAS des liens — ECART-062', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('DSM')).toBeTruthy();
    });
    //  `chemin_detaille` n'est pas `null` pour DSM/ESM, et pourtant aucune route
    //  ne la sert : la carte est de l'information, jamais un lien mort.
    expect(screen.getByText('DSM').closest('a')).toBeNull();
    expect(screen.getByText('ESM').closest('a')).toBeNull();
    //  BOOSTER et OFFICE_MANAGER portent aussi cette mention dans ce decor :
    //  deux occurrences, l'une comme l'autre legitimes.
    expect(screen.getAllByText('Personne actuellement').length).toBeGreaterThan(0);
  });

  it('une carte de cercle MENE reellement a sa page detaillee', async () => {
    const requete = vi.fn((cible: string | URL | Request) => {
      const url = String(cible);
      if (url.includes('/circles/')) {
        return Promise.resolve(reponse(CERCLE_DATA));
      }
      return Promise.resolve(reponse(FRAMEWORK));
    });
    vi.stubGlobal('fetch', requete);
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Data'));
    await waitFor(() => {
      expect(screen.getByText('Le cercle Data')).toBeTruthy();
    });
  });

  it('affiche une erreur de session sur 401', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ detail: 'non authentifie' }), { status: 401 }),
        ),
      ),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText(/session a expire/)).toBeTruthy();
    });
  });
});

describe('chantier front, S5 : `Carte`/`Badge`/icone de bureau (`DEC-672`)', () => {
  it('les trois familles sont des `Carte` — trois regions nommees', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    expect(screen.getByRole('region', { name: 'Responsabilites' })).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Cercles' })).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Bureaux' })).toBeTruthy();
  });

  it('les compteurs de membres et de responsables sont des `Badge` reels, pas de la prose', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    //  Data : 3 membres actifs. Shield : 0 -- le couple du §7.42, applique au
    //  compteur plutot qu'a la couleur : la forme zero doit rester un vrai badge.
    expect(screen.getByText('3 membres').closest('.ex-badge')).not.toBeNull();
    expect(screen.getByText('0 membre').closest('.ex-badge')).not.toBeNull();
    //  Siege : zero responsable.
    expect(screen.getByText('0 responsable').closest('.ex-badge')).not.toBeNull();
  });

  it('un bureau porte une icone DECORATIVE — cahier §13.2, « icones maitrisees »', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    const icone = screen.getByText('Siege').closest('a')?.querySelector('svg');
    expect(icone).toBeTruthy();
    expect(icone?.getAttribute('aria-hidden')).toBe('true');
    //  Un cercle ne porte PAS cette icone : sa bordure coloree est deja sa
    //  propre marque visuelle, une seconde n'ajouterait aucune information.
    expect(screen.getByText('Data').closest('a')?.querySelector('svg')).toBeNull();
  });
});
