/**
 * La page detaillee d'un bureau a l'ecran — LOT 6, `T9`, story `MVP-L06-US003`.
 *
 * LE CRITERE : « BDS, BDE et BDG sont configurables ; un a trois responsables
 * actifs sont affiches. » La borne du §8.4 n'est pas tenue en base (`DEC-583`) :
 * ce fichier eprouve les trois cas que le contrat autorise explicitement — zero,
 * conforme, et hors borne — et que l'ecran RAPPORTE plutot qu'il ne refuse.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageBureau } from './PageBureau';

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: null,
  }),
}));

afterEach(() => {
  cleanup();
});

function pageDeBureau(supplement: Record<string, unknown> = {}): Response {
  return new Response(
    JSON.stringify({
      identifiant: 'b1',
      code: 'siege',
      nom: 'Siege',
      description: null,
      localisation: null,
      responsables: [{ identifiant: 'p1', prenom: 'Ada', nom: 'Lovelace', photo: null }],
      nombre_de_responsables: 1,
      publie: true,
      chemin_detaille: '/entites/bordeaux/framework/bureaux/siege',
      ...supplement,
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/framework/bureaux/siege']}>
      <Routes>
        <Route path="/entites/:code/framework/bureaux/:codeBureau" element={<PageBureau />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('la page detaillee d’un bureau a l’ecran', () => {
  it('affiche le responsable et l’etat de publication — LE TEMOIN CENTRAL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeBureau())),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    expect(screen.getByText('Publie')).toBeTruthy();
  });

  it('une localisation absente se lit « Non renseignee », jamais « null »', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeBureau({ localisation: null }))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    expect(screen.getByText('Non renseignee')).toBeTruthy();
    expect(screen.queryByText('null')).toBeNull();
  });

  it('ZERO responsable sur un bureau PUBLIE : rapporte, pas cache — §7.20, §8.4', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          pageDeBureau({ responsables: [], nombre_de_responsables: 0, publie: true }),
        ),
      ),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    expect(screen.getByText(/hors de la fourchette attendue/)).toBeTruthy();
    expect(screen.getByText('Aucun responsable pour le moment.')).toBeTruthy();
  });

  it('ZERO responsable sur un bureau EN BROUILLON : legitime, aucun avertissement', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          pageDeBureau({ responsables: [], nombre_de_responsables: 0, publie: false }),
        ),
      ),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    expect(screen.getByText('Brouillon')).toBeTruthy();
    expect(screen.queryByText(/hors de la fourchette attendue/)).toBeNull();
  });

  it('QUATRE responsables, publie : hors borne, rapporte quand meme les quatre', async () => {
    const quatre = ['Ada', 'Nour', 'Ines', 'Malo'].map((prenom, i) => ({
      identifiant: `p${String(i)}`,
      prenom,
      nom: 'X',
      photo: null,
    }));
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(pageDeBureau({ responsables: quatre, nombre_de_responsables: 4 })),
      ),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    expect(screen.getByText(/hors de la fourchette attendue/)).toBeTruthy();
    expect(screen.getByText('Malo X')).toBeTruthy();
  });
});

describe('chantier front, S5 : `Carte`/icone de bureau (`DEC-672`)', () => {
  it('l’identite et les responsables sont des `Carte` — deux regions nommees', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeBureau())),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    expect(screen.getByRole('region', { name: 'Siege' })).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Responsables (1)' })).toBeTruthy();
  });

  it('porte une icone DECORATIVE, aux cotes du badge d’etat — cahier §13.2', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeBureau())),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    const icone = screen.getByRole('region', { name: 'Siege' }).querySelector('svg');
    expect(icone).toBeTruthy();
    expect(icone?.getAttribute('aria-hidden')).toBe('true');
  });
});

describe('chantier front, S12 : cadres hexagonaux des responsables (DEC-673)', () => {
  it('sans photo, un responsable porte des initiales — AUCUNE `<img>`', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDeBureau())),
    );
    const { container } = render(
      <MemoryRouter initialEntries={['/entites/bordeaux/framework/bureaux/siege']}>
        <Routes>
          <Route path="/entites/:code/framework/bureaux/:codeBureau" element={<PageBureau />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('.bureau-avatar')?.textContent).toBe('AL');
  });

  it('avec une photo, un responsable porte une `<img>` — AUCUNE initiale', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          pageDeBureau({
            responsables: [
              {
                identifiant: 'p1',
                prenom: 'Ada',
                nom: 'Lovelace',
                photo: '/api/v1/entities/bordeaux/people/p1/photo',
              },
            ],
          }),
        ),
      ),
    );
    const { container } = render(
      <MemoryRouter initialEntries={['/entites/bordeaux/framework/bureaux/siege']}>
        <Routes>
          <Route path="/entites/:code/framework/bureaux/:codeBureau" element={<PageBureau />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    expect(container.querySelector('.bureau-avatar')).toBeNull();
    const image = container.querySelector('img');
    expect(image?.getAttribute('src')).toBe('/api/v1/entities/bordeaux/people/p1/photo');
    //  Le nom est juste a cote : un `alt` qui le repeterait le ferait annoncer
    //  deux fois par un lecteur d'ecran.
    expect(image?.getAttribute('alt')).toBe('');
  });
});
