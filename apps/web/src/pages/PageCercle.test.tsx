/**
 * La page detaillee d'un cercle a l'ecran — LOT 6, `T9`, story `MVP-L06-US002`.
 *
 * LE CRITERE : « couleur, description, membres et Booster sont affiches sans
 * reposer uniquement sur la couleur. » Ce fichier eprouve chacun des quatre, et
 * la pagination des membres — §18.2, reprise du trombinoscope de `T10` du LOT 5.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageCercle } from './PageCercle';

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: null,
  }),
}));

afterEach(() => {
  cleanup();
});

function pageDeCercle(supplement: Record<string, unknown> = {}): Response {
  return new Response(
    JSON.stringify({
      identifiant: 'c1',
      code: 'data',
      nom: 'Data',
      description: 'Le cercle Data',
      jeton_de_couleur: 'bleu',
      booster: { identifiant: 'p1', prenom: 'Ada', nom: 'Lovelace', photo: null },
      membres: [
        {
          appartenance: 'm1',
          prenom: 'Nour',
          nom: 'Arrivante',
          type_d_appartenance: 'principal',
          photo: null,
        },
      ],
      total_des_membres: 1,
      page: 1,
      taille: 25,
      pages: 1,
      chemin_detaille: '/entites/bordeaux/framework/cercles/data',
      ...supplement,
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/framework/cercles/data']}>
      <Routes>
        <Route path="/entites/:code/framework/cercles/:codeCercle" element={<PageCercle />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('la page detaillee d’un cercle a l’ecran', () => {
  it('affiche la description, le Booster et les membres — LE TEMOIN CENTRAL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeCercle())),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    expect(screen.getByText('Le cercle Data')).toBeTruthy();
    expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    expect(screen.getByText('Nour Arrivante')).toBeTruthy();
    expect(screen.getByText('Principal')).toBeTruthy();
  });

  it('un jeton NUL laisse le nom lisible sans couleur — defaut T10-8', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeCercle({ jeton_de_couleur: null, booster: null }))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    //  `str(None)` rendrait la chaine « None » : elle ne doit apparaitre nulle part.
    expect(screen.queryByText('None')).toBeNull();
    expect(screen.getByText('Aucun Booster')).toBeTruthy();
  });

  it('pagine — la page suivante relance l’appel avec `page=2`', async () => {
    const requete = vi.fn<(cible: string | URL | Request) => Promise<Response>>(() =>
      Promise.resolve(pageDeCercle({ page: 1, pages: 2, total_des_membres: 30 })),
    );
    vi.stubGlobal('fetch', requete);
    monter();
    await waitFor(() => {
      expect(screen.getByText('Page 1 sur 2')).toBeTruthy();
    });
    requete.mockImplementation(() =>
      Promise.resolve(pageDeCercle({ page: 2, pages: 2, total_des_membres: 30 })),
    );
    fireEvent.click(screen.getByText('Page suivante'));
    await waitFor(() => {
      expect(screen.getByText('Page 2 sur 2')).toBeTruthy();
    });
    const derniereRequete = requete.mock.calls.at(-1)?.[0];
    expect(String(derniereRequete)).toContain('page=2');
  });

  it('un 404 dit que le cercle est introuvable ou archive', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response(JSON.stringify({ detail: 'x' }), { status: 404 }))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText(/introuvable/)).toBeTruthy();
    });
  });
});

describe('chantier front, S5 : `Carte`/`Badge` (`DEC-672`)', () => {
  it('l’identite et les membres sont des `Carte` — deux regions nommees', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeCercle())),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    expect(screen.getByRole('region', { name: 'Data' })).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Membres (1)' })).toBeTruthy();
  });

  it('le type d’appartenance est un `Badge` reel, pas un simple texte', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeCercle())),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Principal')).toBeTruthy();
    });
    expect(screen.getByText('Principal').closest('.ex-badge')).not.toBeNull();
  });

  it('LE JETON DE COULEUR ATTEINT REELLEMENT LA BORDURE — defaut latent corrige, S5', async () => {
    //  Avant S5, la regle `.cercle-entete` redeclarait `--cercle-couleur` sur
    //  l'element meme qui posait la bordure, et la valeur en ligne du jeton
    //  n'etait donc JAMAIS lue -- aucun test ne l'eprouvait. Celui-ci lit la
    //  valeur de la propriete personnalisee la ou elle est desormais ecrite.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeCercle())),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    const conteneur = screen.getByText('Data').closest('.cercle-identite');
    expect(conteneur).not.toBeNull();
    expect((conteneur as HTMLElement).style.getPropertyValue('--cercle-couleur')).not.toBe('');
  });
});

describe('chantier front, S12 : cadres hexagonaux du Booster et des membres (DEC-673)', () => {
  it('sans photo, le Booster et le membre portent des initiales — AUCUNE `<img>`', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeCercle())),
    );
    const { container } = render(
      <MemoryRouter initialEntries={['/entites/bordeaux/framework/cercles/data']}>
        <Routes>
          <Route path="/entites/:code/framework/cercles/:codeCercle" element={<PageCercle />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('.cercle-booster .cercle-avatar')?.textContent).toBe('AL');
    expect(container.querySelector('.cercle-membre-identite .cercle-avatar')?.textContent).toBe(
      'NA',
    );
  });

  it('avec une photo, le Booster et le membre portent une `<img>` — AUCUNE initiale', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          pageDeCercle({
            booster: {
              identifiant: 'p1',
              prenom: 'Ada',
              nom: 'Lovelace',
              photo: '/api/v1/entities/bordeaux/people/p1/photo',
            },
            membres: [
              {
                appartenance: 'm1',
                prenom: 'Nour',
                nom: 'Arrivante',
                type_d_appartenance: 'principal',
                photo: '/api/v1/entities/bordeaux/people/m1/photo',
              },
            ],
          }),
        ),
      ),
    );
    const { container } = render(
      <MemoryRouter initialEntries={['/entites/bordeaux/framework/cercles/data']}>
        <Routes>
          <Route path="/entites/:code/framework/cercles/:codeCercle" element={<PageCercle />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    expect(container.querySelectorAll('.cercle-avatar')).toHaveLength(0);
    const images = container.querySelectorAll('img');
    expect(images).toHaveLength(2);
    expect(Array.from(images).map((img) => img.getAttribute('src'))).toEqual([
      '/api/v1/entities/bordeaux/people/p1/photo',
      '/api/v1/entities/bordeaux/people/m1/photo',
    ]);
    //  Le nom est juste a cote : un `alt` qui le repeterait le ferait annoncer
    //  deux fois par un lecteur d'ecran.
    expect(Array.from(images).every((img) => img.getAttribute('alt') === '')).toBe(true);
  });
});
