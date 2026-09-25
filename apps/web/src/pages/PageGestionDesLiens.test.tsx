/**
 * Gerer les liens internes, a l'ecran — LOT 6, `T10`, `MVP-L06-US005`.
 *
 * LE TEMOIN CENTRAL : UN LIEN INACTIF RESTE VISIBLE ICI
 *
 *   L'accueil de `T9` ne sert que les liens actifs ; cet ecran sert les DEUX,
 *   sans quoi desactiver serait un aller sans retour. Un test l'exige.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageGestionDesLiens } from './PageGestionDesLiens';

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

function lien(modifications: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: 'l1',
    libelle: 'Hub',
    url: 'https://hub.exemple.test/',
    type_de_lien: 'HUB',
    description: null,
    reference_d_icone: null,
    rang: 0,
    actif: true,
    version: 1,
    ...modifications,
  };
}

function servir(reponses: {
  liste: unknown[];
  ecriture?: { charge: unknown; statut?: number };
}): ReturnType<typeof vi.fn> {
  const appel = vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json(SESSION));
    }
    if (url.endsWith('/liens/gestion')) {
      return Promise.resolve(
        json({ liens: reponses.liste, nombre_de_liens: reponses.liste.length }),
      );
    }
    if (url.endsWith('/liens/ordre')) {
      return Promise.resolve(
        json(
          reponses.ecriture?.charge ?? {
            liens: reponses.liste,
            nombre_de_liens: reponses.liste.length,
          },
          reponses.ecriture?.statut ?? 200,
        ),
      );
    }
    if (url.includes('/liens/') && !url.endsWith('/liens/gestion')) {
      return Promise.resolve(
        json(reponses.ecriture?.charge ?? lien(), reponses.ecriture?.statut ?? 200),
      );
    }
    if (url.endsWith('/liens')) {
      return Promise.resolve(
        json(reponses.ecriture?.charge ?? lien(), reponses.ecriture?.statut ?? 201),
      );
    }
    throw new Error(`URL non attendue : ${url}`);
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

describe('deux populations — actifs ET inactifs', () => {
  it('un lien INACTIF reste visible, marque comme tel', async () => {
    servir({
      liste: [
        lien({ actif: true }),
        lien({ identifiant: 'l2', libelle: 'Academy', actif: false, rang: 1 }),
      ],
    });
    render(<PageGestionDesLiens />);
    await waitFor(() => {
      expect(screen.getByText('Academy')).toBeTruthy();
    });
    const item = screen.getByText('Academy').closest('li');
    expect(item?.getAttribute('data-actif')).toBe('false');
  });
});

describe('creer un lien', () => {
  it('le formulaire s’ouvre, exige libelle et adresse, puis recharge la liste', async () => {
    const appel = servir({ liste: [lien()] });
    render(<PageGestionDesLiens />);
    await waitFor(() => {
      expect(screen.getByText('Hub')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Nouveau lien'));
    fireEvent.change(screen.getByLabelText('Libelle'), { target: { value: 'Academy' } });
    fireEvent.change(screen.getByLabelText('Adresse (https uniquement)'), {
      target: { value: 'https://academy.exemple.test/' },
    });
    fireEvent.click(screen.getByText('Creer le lien'));

    await waitFor(() => {
      const creation = appel.mock.calls.find(
        (c) =>
          String(c[0]).endsWith('/liens') && (c[1] as RequestInit | undefined)?.method === 'POST',
      );
      expect(creation).toBeTruthy();
    });
  });
});

describe('basculer actif/inactif', () => {
  it('desactiver envoie version et actif=false, sans toucher aux autres champs', async () => {
    const appel = servir({ liste: [lien()], ecriture: { charge: lien({ actif: false }) } });
    render(<PageGestionDesLiens />);
    await waitFor(() => {
      expect(screen.getByText('Desactiver')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Desactiver'));

    await waitFor(() => {
      const modification = appel.mock.calls.find(
        (c) =>
          String(c[0]).endsWith('/liens/l1') && (c[1] as RequestInit | undefined)?.method === 'PUT',
      );
      expect(modification).toBeTruthy();
      const corps = JSON.parse(String((modification?.[1] as RequestInit).body)) as {
        actif: boolean;
        version: number;
        libelle: string;
      };
      expect(corps.actif).toBe(false);
      expect(corps.version).toBe(1);
      expect(corps.libelle).toBe('Hub');
    });
  });
});

describe('reordonner', () => {
  it('« Monter » envoie la liste COMPLETE des identifiants, ordre echange', async () => {
    const appel = servir({
      liste: [lien({ rang: 0 }), lien({ identifiant: 'l2', libelle: 'Academy', rang: 1 })],
    });
    render(<PageGestionDesLiens />);
    await waitFor(() => {
      expect(screen.getByText('Academy')).toBeTruthy();
    });
    const monterBoutons = screen.getAllByText('Monter');
    fireEvent.click(monterBoutons[1] as HTMLElement);

    await waitFor(() => {
      const reordonnance = appel.mock.calls.find((c) => String(c[0]).endsWith('/liens/ordre'));
      expect(reordonnance).toBeTruthy();
      const corps = JSON.parse(String((reordonnance?.[1] as RequestInit).body)) as {
        ordre: string[];
      };
      expect(corps.ordre).toEqual(['l2', 'l1']);
    });
  });
});
