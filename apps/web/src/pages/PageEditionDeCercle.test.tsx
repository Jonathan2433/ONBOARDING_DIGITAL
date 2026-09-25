/**
 * Editer la page de contenu d'un cercle, a l'ecran — LOT 6, `T10`.
 *
 * LE TEMOIN CENTRAL : LE CERCLE EST RESOLU AVANT LA PAGE DE GESTION
 *
 *   Sans son `identifiant`, aucun filtre ne peut distinguer sa page de
 *   contenu de celle d'un autre cercle — la liste de gestion ne porte que
 *   `circle_id`. Un test exige que la liste soit appelee APRES le cercle, et
 *   que le filtre retienne la bonne page parmi plusieurs.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageEditionDeCercle } from './PageEditionDeCercle';

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

function cercleServi(supplement: Record<string, unknown> = {}): unknown {
  return {
    identifiant: 'c-data',
    code: 'data',
    nom: 'Data',
    description: null,
    jeton_de_couleur: null,
    booster: null,
    membres: [],
    total_des_membres: 0,
    page: 1,
    taille: 25,
    pages: 1,
    chemin_detaille: '/entites/bordeaux/framework/cercles/data',
    ...supplement,
  };
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/framework/cercles/data/editer']}>
      <Routes>
        <Route
          path="/entites/:code/framework/cercles/:codeCercle/editer"
          element={<PageEditionDeCercle />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('la resolution du cercle AVANT la page de gestion', () => {
  it('trouve la page dont le circle_id correspond, parmi PLUSIEURS pages', async () => {
    const appel = vi.fn((url: string) => {
      if (url.includes('/circles/')) {
        return Promise.resolve(json(cercleServi()));
      }
      if (url.endsWith('/pages/gestion')) {
        return Promise.resolve(
          json({
            pages: [
              {
                identifiant: 'p-autre',
                type_de_page: 'CIRCLE',
                titre: 'Un autre cercle',
                slug: 'autre',
                etat: 'draft',
                version: 1,
                circle_id: 'c-autre',
                office_id: null,
              },
              {
                identifiant: 'p-data',
                type_de_page: 'CIRCLE',
                titre: 'Data',
                slug: 'data',
                etat: 'draft',
                version: 1,
                circle_id: 'c-data',
                office_id: null,
              },
            ],
          }),
        );
      }
      if (url.endsWith('/gestion')) {
        return Promise.resolve(
          json({
            identifiant: 'p-data',
            type_de_page: 'CIRCLE',
            titre: 'Data',
            slug: 'data',
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
    //  La bonne page a ete lue, jamais celle de l'autre cercle.
    const appelDetail = appel.mock.calls.find(
      (c) => String(c[0]).endsWith('/gestion') && !String(c[0]).endsWith('/pages/gestion'),
    );
    expect(String(appelDetail?.[0])).toContain('p-data');
  });

  it('un cercle introuvable affiche un refus, jamais la page de gestion', async () => {
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
