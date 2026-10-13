/**
 * « Pilotage » à l'écran — tableau de bord (LOT 9, `T5`/`T14`) et suivi des
 * tâches en retard (LOT 7, `T12`, déplacé ici par le LOT 9 `T14`).
 *
 * LE SUIVI EST REPRIS À L'IDENTIQUE DE `PageAdministration.test.tsx` (LOT 7)
 *
 *   Aucune règle changée en migrant — ces tests le prouvent.
 *
 * LE TABLEAU DE BORD EST GARDÉ SÉPARÉMENT DU SUIVI
 *
 *   `OFFICE` n'y voit rien, mais voit quand même le suivi — aucun rôle n'y
 *   est refusé (portée dégradée à `Soi`).
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SectionPilotage } from './SectionPilotage';

afterEach(() => {
  cleanup();
});

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

const SUIVI_VIDE = { taches: [], page: 1, taille: 25, total: 0, pages: 1 };

function tableauDeBord(supplement: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    profils_actifs: 10,
    arrivees_futures: 2,
    onboardings_actifs: 3,
    taches_en_retard: 1,
    profils_incomplets: 0,
    derniers_imports_en_echec: [],
    ...supplement,
  };
}

function servir(options: {
  suivi?: unknown;
  tableau?: unknown;
  statutTableau?: number;
}): ReturnType<typeof vi.fn> {
  const appel = vi.fn((url: string) => {
    if (url.includes('/onboarding-suivi/taches-en-retard')) {
      return Promise.resolve(json(options.suivi ?? SUIVI_VIDE));
    }
    if (url.includes('/administration/tableau-de-bord')) {
      return Promise.resolve(
        json(options.tableau ?? tableauDeBord(), options.statutTableau ?? 200),
      );
    }
    return Promise.resolve(json({ erreur: { code: 'inattendu', message: url } }, 404));
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

function monter(roles: readonly string[] | null): void {
  render(<SectionPilotage code="bordeaux" roles={roles} />);
}

describe('le tableau de bord — OFFICE exclu', () => {
  it('affiche les six grandeurs pour un ESM', async () => {
    servir({ tableau: tableauDeBord({ profils_actifs: 42 }) });
    monter(['ESM']);

    await waitFor(() => expect(screen.getByText('Tableau de bord')).toBeTruthy());
    expect(screen.getByText('42')).toBeTruthy();
  });

  it("n'appelle PAS le tableau de bord pour un OFFICE, mais charge le suivi", async () => {
    const appel = servir({});
    monter(['OFFICE']);

    await waitFor(() =>
      expect(screen.getByText(/Aucune tâche en retard dans votre périmètre/)).toBeTruthy(),
    );
    expect(
      appel.mock.calls.some((c) => (c[0] as string).includes('/administration/tableau-de-bord')),
    ).toBe(false);
    expect(screen.queryByText('Tableau de bord')).toBeNull();
  });
});

describe('le suivi des tâches en retard — aucun rôle n’y est jamais refusé', () => {
  it('affiche les tâches en retard, avec le collaborateur concerné', async () => {
    servir({
      suivi: {
        taches: [
          {
            id: 't1',
            title_snapshot: 'Signer le contrat',
            due_at: '2026-09-20T00:00:00Z',
            state: 'todo',
            instance_id: 'i1',
            appartenance_id: 'a1',
            person_id: 'p1',
            first_name: 'Nouvelle',
            last_name: 'Arrivante',
          },
        ],
        page: 1,
        taille: 25,
        total: 1,
        pages: 1,
      },
    });
    monter(['ESM']);

    await waitFor(() => expect(screen.getByText('Signer le contrat')).toBeTruthy());
    expect(screen.getByText('Nouvelle Arrivante')).toBeTruthy();
  });

  it('pagine — « Page suivante » recharge avec `page=2`', async () => {
    const appel = servir({
      suivi: { taches: [], page: 1, taille: 25, total: 30, pages: 2 },
    });
    monter(['ESM']);

    await waitFor(() => expect(screen.getByText('Page 1 / 2')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Page suivante' }));

    await waitFor(() => {
      expect(appel.mock.calls.some((c) => (c[0] as string).includes('page=2'))).toBe(true);
    });
  });
});
