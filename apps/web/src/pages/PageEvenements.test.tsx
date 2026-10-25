/**
 * Les evenements a l'ecran — LOT 8, `T9`, story `MVP-L08-US003` (2/2).
 *
 * LE TEMOIN DE LA FICHE : « onglets a venir/passes, badge annule, mobile et
 * clavier. » Ce fichier eprouve les quatre : le changement d'onglet relance
 * l'appel avec le bon `classement` ET reinitialise la page, un evenement
 * annule reste visible avec son badge, et les onglets sont de vrais `<button>`
 * — la reponse au clavier est donc STRUCTURELLE (Tab, Entree, Espace activent
 * un bouton nativement), meme parti que `PageTrombinoscope.tsx`.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageEvenements } from './PageEvenements';

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: null,
  }),
}));

afterEach(() => {
  cleanup();
});

function pageDesEvenements(supplement: Record<string, unknown> = {}): Response {
  return new Response(
    JSON.stringify({
      classement: 'a_venir',
      evenements: [
        {
          identifiant: 'ev1',
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
      ...supplement,
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/evenements']}>
      <Routes>
        <Route path="/entites/:code/evenements" element={<PageEvenements />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('les evenements a l’ecran', () => {
  it('affiche les evenements a venir par defaut — LE TEMOIN CENTRAL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDesEvenements())),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Petit-dejeuner d’accueil')).toBeTruthy();
    });
    expect(screen.getByText('Salle Atrium')).toBeTruthy();
    expect(screen.getByText('Rencontre avec les nouveaux arrivants')).toBeTruthy();
    expect(screen.getByText(/08:00 - 09:30/)).toBeTruthy();
    //  Pas de badge sur un evenement publie, non annule.
    expect(screen.queryByText('Annule')).toBeNull();
  });

  it('un evenement ANNULE reste visible, avec son badge — cahier §10.6', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          pageDesEvenements({
            evenements: [
              {
                identifiant: 'ev2',
                titre: 'Atelier annule',
                description: null,
                commence_le: '2026-10-20T14:00:00+00:00',
                finit_le: '2026-10-20T15:00:00+00:00',
                lieu: null,
                etat: 'cancelled',
                annule_le: '2026-10-05T10:00:00+00:00',
                motif_d_annulation: 'Intervenant indisponible',
              },
            ],
          }),
        ),
      ),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Atelier annule')).toBeTruthy();
    });
    expect(screen.getByText('Annule')).toBeTruthy();
  });

  it('les deux onglets sont de vrais boutons — la reponse au clavier est STRUCTURELLE', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(pageDesEvenements())),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'A venir' })).toBeTruthy();
    });
    const aVenir = screen.getByRole('tab', { name: 'A venir' });
    const passes = screen.getByRole('tab', { name: 'Passes' });
    expect(aVenir.tagName).toBe('BUTTON');
    expect(passes.tagName).toBe('BUTTON');
    expect(aVenir.getAttribute('aria-selected')).toBe('true');
    expect(passes.getAttribute('aria-selected')).toBe('false');
  });

  it('change d’onglet relance l’appel avec `classement=passes` ET reinitialise la page', async () => {
    const requete = vi.fn<(cible: string | URL | Request) => Promise<Response>>(() =>
      Promise.resolve(pageDesEvenements({ page: 2, pages: 2, total: 30 })),
    );
    vi.stubGlobal('fetch', requete);
    monter();
    await waitFor(() => {
      expect(screen.getByText('Page 2 sur 2')).toBeTruthy();
    });
    requete.mockImplementation(() =>
      Promise.resolve(
        pageDesEvenements({
          classement: 'passes',
          evenements: [],
          page: 1,
          pages: 0,
          total: 0,
        }),
      ),
    );
    //  `fireEvent.mouseDown`, PAS `.click` — Radix active un onglet sur
    //  `onMouseDown` (S2, `DEC-672`, voir `Onglets.test.tsx`).
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'Passes' }));
    await waitFor(() => {
      expect(screen.getByText('Aucun evenement passe.')).toBeTruthy();
    });
    const derniereRequete = requete.mock.calls.at(-1)?.[0];
    expect(String(derniereRequete)).toContain('classement=passes');
    expect(String(derniereRequete)).toContain('page=1');
  });

  it('pagine — la page suivante relance l’appel avec `page=2`', async () => {
    const requete = vi.fn<(cible: string | URL | Request) => Promise<Response>>(() =>
      Promise.resolve(pageDesEvenements({ page: 1, pages: 2, total: 30 })),
    );
    vi.stubGlobal('fetch', requete);
    monter();
    await waitFor(() => {
      expect(screen.getByText('Page 1 sur 2')).toBeTruthy();
    });
    requete.mockImplementation(() =>
      Promise.resolve(pageDesEvenements({ page: 2, pages: 2, total: 30 })),
    );
    fireEvent.click(screen.getByText('Page suivante'));
    await waitFor(() => {
      expect(screen.getByText('Page 2 sur 2')).toBeTruthy();
    });
    const derniereRequete = requete.mock.calls.at(-1)?.[0];
    expect(String(derniereRequete)).toContain('page=2');
  });

  it('une liste vide dit qu’il n’y a aucun evenement a venir', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(pageDesEvenements({ evenements: [], page: 1, pages: 0, total: 0 })),
      ),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Aucun evenement a venir pour le moment.')).toBeTruthy();
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
