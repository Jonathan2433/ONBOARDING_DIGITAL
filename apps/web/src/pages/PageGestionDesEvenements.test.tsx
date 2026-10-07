/**
 * Gerer les evenements, a l'ecran — LOT 8, `T10`, `MVP-L08-US004`.
 *
 * LE TEMOIN CENTRAL : LE SOMMAIRE REND DES BROUILLONS, QUE `T9` REFUSE
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  depuisDatetimeLocal,
  PageGestionDesEvenements,
  versDatetimeLocal,
} from './PageGestionDesEvenements';

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/evenements/gestion']}>
      <PageGestionDesEvenements />
    </MemoryRouter>,
  );
}

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: { roles: ['ESM'], estEntitePrincipale: true },
  }),
}));

afterEach(cleanup);

const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function evenementDeGestion(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 'ev1',
    titre: 'Brouillon de rentree',
    etat: 'draft',
    commence_le: '2026-10-12T08:00:00+00:00',
    finit_le: '2026-10-12T09:30:00+00:00',
    version: 1,
    ...modifications,
  };
}

function evenementCree(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 'ev2',
    titre: 'Nouveau',
    description: null,
    commence_le: '2026-11-01T08:00:00+00:00',
    finit_le: '2026-11-01T09:00:00+00:00',
    lieu: null,
    etat: 'draft',
    version: 1,
    portee: 'entite',
    ...modifications,
  };
}

function servir(reponses: {
  liste: unknown[];
  creation?: { charge: unknown; statut?: number };
}): ReturnType<typeof vi.fn> {
  const appel = vi.fn((url: string, options?: RequestInit) => {
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json(SESSION));
    }
    if (url.endsWith('/events/gestion')) {
      return Promise.resolve(json({ evenements: reponses.liste }));
    }
    if (url.endsWith('/events') && options?.method === 'POST') {
      return Promise.resolve(
        json(reponses.creation?.charge ?? evenementCree(), reponses.creation?.statut ?? 201),
      );
    }
    throw new Error(`URL non attendue : ${url}`);
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

describe('le sommaire rend TOUS les etats', () => {
  it('un BROUILLON reste visible ici, que la consultation (T9) refuse', async () => {
    servir({ liste: [evenementDeGestion()] });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Brouillon de rentree')).toBeTruthy();
    });
    expect(screen.getByText('Brouillon')).toBeTruthy();
  });

  it('un ARCHIVE est servi avec son badge', async () => {
    servir({ liste: [evenementDeGestion({ etat: 'archived', titre: 'Vieille affaire' })] });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Vieille affaire')).toBeTruthy();
    });
    expect(screen.getByText('Archive')).toBeTruthy();
  });

  it('un sommaire VIDE affiche un message, pas une liste vide muette', async () => {
    servir({ liste: [] });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Aucun evenement pour le moment.')).toBeTruthy();
    });
  });
});

describe('creer un evenement', () => {
  it('le formulaire envoie la portee et les dates converties, puis recharge', async () => {
    const appel = servir({ liste: [] });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Nouvel evenement')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Nouvel evenement'));
    fireEvent.change(screen.getByLabelText('Titre'), { target: { value: 'Rentree' } });
    fireEvent.change(screen.getByLabelText('Debut'), { target: { value: '2026-11-01T08:00' } });
    fireEvent.change(screen.getByLabelText('Fin'), { target: { value: '2026-11-01T09:00' } });
    fireEvent.click(screen.getByText('Creer l’evenement'));

    await waitFor(() => {
      const creation = appel.mock.calls.find(
        (c) =>
          String(c[0]).endsWith('/events') && (c[1] as RequestInit | undefined)?.method === 'POST',
      );
      expect(creation).toBeTruthy();
      const corps = JSON.parse(String((creation?.[1] as RequestInit).body)) as {
        titre: string;
        commence_le: string;
        portee: string;
      };
      expect(corps.titre).toBe('Rentree');
      expect(corps.commence_le).toBe('2026-11-01T08:00:00+00:00');
      expect(corps.portee).toBe('entite');
    });
  });

  it('le cercle n’est envoye QUE si la portee « cercle » est choisie', async () => {
    const appel = servir({ liste: [] });
    monter();
    await waitFor(() => {
      expect(screen.getByText('Nouvel evenement')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Nouvel evenement'));
    fireEvent.change(screen.getByLabelText('Titre'), { target: { value: 'Atelier' } });
    fireEvent.change(screen.getByLabelText('Debut'), { target: { value: '2026-11-01T08:00' } });
    fireEvent.change(screen.getByLabelText('Fin'), { target: { value: '2026-11-01T09:00' } });
    fireEvent.change(screen.getByLabelText('Portee'), { target: { value: 'cercle' } });
    fireEvent.change(screen.getByLabelText('Code du cercle'), { target: { value: 'CERCLE-A' } });
    fireEvent.click(screen.getByText('Creer l’evenement'));

    await waitFor(() => {
      const creation = appel.mock.calls.find(
        (c) =>
          String(c[0]).endsWith('/events') && (c[1] as RequestInit | undefined)?.method === 'POST',
      );
      const corps = JSON.parse(String((creation?.[1] as RequestInit).body)) as {
        portee: string;
        cercle?: string;
        bureau?: string;
      };
      expect(corps.portee).toBe('cercle');
      expect(corps.cercle).toBe('CERCLE-A');
      expect(corps.bureau).toBeUndefined();
    });
  });
});

describe('la conversion de date, sans aucun `Date`', () => {
  it('versDatetimeLocal/depuisDatetimeLocal sont l’inverse l’un de l’autre, sans fuseau', () => {
    expect(versDatetimeLocal('2026-10-12T08:00:00+00:00')).toBe('2026-10-12T08:00');
    expect(depuisDatetimeLocal('2026-10-12T08:00')).toBe('2026-10-12T08:00:00+00:00');
  });
});
