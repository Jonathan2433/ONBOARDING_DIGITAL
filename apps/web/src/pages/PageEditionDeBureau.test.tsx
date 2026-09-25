/**
 * Editer la page de contenu d'un bureau, a l'ecran — LOT 6, `T10`.
 *
 * MEME TEMOIN QUE `PageEditionDeCercle.test.tsx` : le bureau est resolu
 * D'ABORD pour obtenir son `identifiant`, seul moyen de distinguer sa page
 * parmi PLUSIEURS.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageEditionDeBureau } from './PageEditionDeBureau';

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: { roles: ['ESM'], estEntitePrincipale: true },
  }),
}));

afterEach(cleanup);

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function bureauServi(supplement: Record<string, unknown> = {}): unknown {
  return {
    identifiant: 'o-bdg',
    code: 'bdg',
    nom: 'BDG',
    description: null,
    localisation: null,
    responsables: [],
    nombre_de_responsables: 0,
    publie: false,
    chemin_detaille: '/entites/bordeaux/framework/bureaux/bdg',
    ...supplement,
  };
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/framework/bureaux/bdg/editer']}>
      <Routes>
        <Route
          path="/entites/:code/framework/bureaux/:codeBureau/editer"
          element={<PageEditionDeBureau />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('la resolution du bureau AVANT la page de gestion', () => {
  it('trouve la page dont l’office_id correspond, parmi PLUSIEURS pages', async () => {
    const appel = vi.fn((url: string) => {
      if (url.includes('/offices/')) {
        return Promise.resolve(json(bureauServi()));
      }
      if (url.endsWith('/pages/gestion')) {
        return Promise.resolve(
          json({
            pages: [
              {
                identifiant: 'p-autre',
                type_de_page: 'OFFICE',
                titre: 'Un autre bureau',
                slug: 'autre',
                etat: 'draft',
                version: 1,
                circle_id: null,
                office_id: 'o-autre',
              },
              {
                identifiant: 'p-bdg',
                type_de_page: 'OFFICE',
                titre: 'BDG',
                slug: 'bdg',
                etat: 'draft',
                version: 1,
                circle_id: null,
                office_id: 'o-bdg',
              },
            ],
          }),
        );
      }
      if (url.endsWith('/gestion')) {
        return Promise.resolve(
          json({
            identifiant: 'p-bdg',
            type_de_page: 'OFFICE',
            titre: 'BDG',
            slug: 'bdg',
            etat: 'draft',
            version: 1,
            publiee_le: null,
            blocs: [],
            nombre_de_blocs: 0,
          }),
        );
      }
      throw new Error(`URL non attendue : ${url}`);
    });
    vi.stubGlobal('fetch', appel);
    monter();

    await waitFor(() => {
      expect(screen.getByText('Blocs (0)')).toBeTruthy();
    });
    const appelDetail = appel.mock.calls.find(
      (c) => String(c[0]).endsWith('/gestion') && !String(c[0]).endsWith('/pages/gestion'),
    );
    expect(String(appelDetail?.[0])).toContain('p-bdg');
  });

  it('un bureau introuvable affiche un refus, jamais la page de gestion', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ detail: 'introuvable' }, 404))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText(/n'a pas pu etre charge/)).toBeTruthy();
    });
  });
});
