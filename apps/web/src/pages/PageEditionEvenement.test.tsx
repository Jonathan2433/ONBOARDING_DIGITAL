/**
 * Editer un evenement, a l'ecran — LOT 8, `T10`, `MVP-L08-US004`.
 *
 * LE TEMOIN CENTRAL : LES BOUTONS DE CYCLE DE VIE SUIVENT L'ETAT
 *
 *   Un brouillon propose Publier et Archiver, jamais Annuler ni Restaurer ;
 *   un archive ne propose QUE Restaurer, et seulement a un role qui le porte
 *   (`ARB-DROIT-003` exclut DSM/BOOST/OFFICE en bloc).
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageEditionEvenement } from './PageEditionEvenement';

let rolesDeTest: readonly string[] = ['ESM'];

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: { roles: rolesDeTest, estEntitePrincipale: true },
  }),
}));

afterEach(() => {
  cleanup();
  rolesDeTest = ['ESM'];
});

const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function evenementPourGestion(
  modifications: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    identifiant: 'ev1',
    titre: 'Petit-dejeuner',
    description: null,
    commence_le: '2026-10-12T08:00:00+00:00',
    finit_le: '2026-10-12T09:30:00+00:00',
    lieu: null,
    etat: 'draft',
    version: 1,
    annule_le: null,
    motif_d_annulation: null,
    archive_le: null,
    cercles: [],
    bureaux: [],
    medias: [],
    ...modifications,
  };
}

/**
 * **L'ETAT MUTE REELLEMENT** : chaque ecriture modifie `actuel`, et
 * `/gestion` (relue par `recharger()`) sert desormais CET etat — sans quoi un
 * test de cycle de vie verifierait une reponse figee plutot que l'effet
 * observable d'un geste, exactement le piege du §7.43 de la passation.
 */
function servir(
  lecture: Record<string, unknown>,
  ecriture?: { charge: Record<string, unknown>; statut?: number },
): ReturnType<typeof vi.fn> {
  let actuel = lecture;
  const appel = vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json(SESSION));
    }
    if (url.endsWith('/events/ev1/gestion')) {
      return Promise.resolve(json(actuel));
    }
    if (url.endsWith('/events/ev1/medias')) {
      const corps = ecriture?.charge ?? { version: 2, medias: [] };
      actuel = { ...actuel, version: corps['version'], medias: corps['medias'] };
      return Promise.resolve(json(corps, ecriture?.statut ?? 200));
    }
    if (url.endsWith('/events/ev1/publication')) {
      const corps = ecriture?.charge ?? { ...actuel, etat: 'published', version: 2 };
      actuel = { ...actuel, ...corps };
      return Promise.resolve(json(corps, ecriture?.statut ?? 200));
    }
    if (url.endsWith('/events/ev1/archivage')) {
      const corps = ecriture?.charge ?? {
        version: 2,
        etat: 'archived',
        archive_le: '2026-10-05T10:00:00+00:00',
      };
      actuel = { ...actuel, ...corps };
      return Promise.resolve(json(corps, ecriture?.statut ?? 200));
    }
    if (url.endsWith('/events/ev1/restauration')) {
      const corps = ecriture?.charge ?? { version: 2, etat: 'draft' };
      actuel = { ...actuel, ...corps };
      return Promise.resolve(json(corps, ecriture?.statut ?? 200));
    }
    if (url.endsWith('/events/ev1')) {
      const corps = ecriture?.charge ?? actuel;
      actuel = { ...actuel, ...corps };
      return Promise.resolve(json(corps, ecriture?.statut ?? 200));
    }
    throw new Error(`URL non attendue : ${url}`);
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/evenements/ev1/editer']}>
      <Routes>
        <Route
          path="/entites/:code/evenements/:evenement/editer"
          element={<PageEditionEvenement />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('un BROUILLON propose Publier et Archiver, jamais Annuler ni Restaurer', () => {
  it('affiche les bons boutons de cycle de vie', async () => {
    servir(evenementPourGestion());
    monter();
    await waitFor(() => {
      expect(screen.getByText('Publier')).toBeTruthy();
    });
    expect(screen.getByText('Archiver')).toBeTruthy();
    expect(screen.queryByText('Annuler')).toBeNull();
    expect(screen.queryByText('Restaurer')).toBeNull();
  });
});

describe('un PUBLIE propose Annuler et Archiver, jamais Publier', () => {
  it('affiche les bons boutons de cycle de vie', async () => {
    servir(evenementPourGestion({ etat: 'published' }));
    monter();
    await waitFor(() => {
      expect(screen.getByText('Annuler')).toBeTruthy();
    });
    expect(screen.getByText('Archiver')).toBeTruthy();
    expect(screen.queryByText('Publier')).toBeNull();
  });
});

describe('un ARCHIVE ne propose QUE Restaurer, et aucun champ editable', () => {
  it('a un ESM', async () => {
    servir(evenementPourGestion({ etat: 'archived', archive_le: '2026-10-05T10:00:00+00:00' }));
    monter();
    await waitFor(() => {
      expect(screen.getByText('Restaurer')).toBeTruthy();
    });
    expect(screen.queryByText('Archiver')).toBeNull();
    expect(screen.queryByLabelText('Titre')).toBeNull();
  });

  it('JAMAIS a un BOOST, meme s’il porte l’archivage — `ARB-DROIT-003`', async () => {
    rolesDeTest = ['BOOST'];
    servir(evenementPourGestion({ etat: 'archived' }));
    monter();
    await waitFor(() => {
      expect(screen.getByText('Archive')).toBeTruthy();
    });
    expect(screen.queryByText('Restaurer')).toBeNull();
  });
});

describe('publier', () => {
  it('envoie la version, puis recharge l’evenement publie', async () => {
    const appel = servir(evenementPourGestion());
    monter();
    await waitFor(() => {
      expect(screen.getByText('Publier')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Publier'));

    await waitFor(() => {
      const publication = appel.mock.calls.find((c) => String(c[0]).endsWith('/publication'));
      expect(publication).toBeTruthy();
      const corps = JSON.parse(String((publication?.[1] as RequestInit).body)) as {
        version: number;
      };
      expect(corps.version).toBe(1);
    });
    await waitFor(() => {
      expect(screen.getByText('Annuler')).toBeTruthy();
    });
  });
});

describe('modifier', () => {
  it('envoie les cercles sous forme de liste, depuis le champ texte', async () => {
    const appel = servir(evenementPourGestion({ cercles: ['CERCLE-A'] }));
    monter();
    await waitFor(() => {
      expect(
        screen.getByLabelText('Cercles rattaches (codes separes par des virgules)'),
      ).toBeTruthy();
    });
    fireEvent.change(screen.getByLabelText('Cercles rattaches (codes separes par des virgules)'), {
      target: { value: 'CERCLE-A, CERCLE-B' },
    });
    fireEvent.click(screen.getByText('Enregistrer'));

    await waitFor(() => {
      const modification = appel.mock.calls.find(
        (c) =>
          String(c[0]).endsWith('/events/ev1') &&
          (c[1] as RequestInit | undefined)?.method === 'PUT',
      );
      expect(modification).toBeTruthy();
      const corps = JSON.parse(String((modification?.[1] as RequestInit).body)) as {
        cercles: string[];
      };
      expect(corps.cercles).toEqual(['CERCLE-A', 'CERCLE-B']);
    });
  });
});

describe('les medias', () => {
  it('ajouter puis enregistrer envoie la liste complete, dans l’ordre', async () => {
    const appel = servir(evenementPourGestion());
    monter();
    await waitFor(() => {
      expect(screen.getByLabelText('Identifiant du media (deja televerse, `ready`)')).toBeTruthy();
    });
    fireEvent.change(screen.getByLabelText('Identifiant du media (deja televerse, `ready`)'), {
      target: { value: 'm1' },
    });
    fireEvent.change(screen.getByLabelText('Role d’affichage'), {
      target: { value: 'Affiche' },
    });
    fireEvent.click(screen.getByText('Ajouter a la liste'));
    await waitFor(() => {
      expect(screen.getByText(/Affiche — m1/)).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Enregistrer les medias'));

    await waitFor(() => {
      const ecriture = appel.mock.calls.find((c) => String(c[0]).endsWith('/medias'));
      expect(ecriture).toBeTruthy();
      const corps = JSON.parse(String((ecriture?.[1] as RequestInit).body)) as {
        medias: { media: string; role: string }[];
      };
      expect(corps.medias).toEqual([{ media: 'm1', role: 'Affiche' }]);
    });
  });
});
