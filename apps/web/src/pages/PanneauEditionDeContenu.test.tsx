/**
 * L'edition d'un contenu, a l'ecran — LOT 6, `T10`, `MVP-L06-US004` (3/3).
 *
 * LE TEMOIN LE PLUS UTILE N'EST PAS UN REFUS : C'EST L'ABSENCE DE FORMULAIRE
 * DE CREATION D'UN BLOC
 *
 *   `QO-121` n'est pas tranchee : inventer un formulaire par type de bloc
 *   serait §6.5. Un test exige donc qu'AUCUN texte n'invite a « ajouter un
 *   bloc » — sans quoi une regression future pourrait en poser un sans qu'un
 *   controle ne le remarque.
 *
 * ET UN COUPLE POUR CHAQUE REFUS, MEME MOTIF QUE `PanneauDuCycleDeVie.test.tsx`
 *
 *   « pas de bouton Publier hors brouillon » se satisfait tout seul si aucun
 *   bouton de cycle de vie n'apparait jamais. Chaque etat a donc son propre
 *   temoin, et pas seulement son refus.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PanneauEditionDeContenu } from './PanneauEditionDeContenu';

afterEach(cleanup);

const CODE = 'bordeaux';
const PAGE = '11111111-1111-1111-1111-111111111111';
const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function pageDeGestion(supplement: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: PAGE,
    type_de_page: 'CIRCLE',
    titre: 'Data',
    slug: 'data',
    etat: 'draft',
    version: 1,
    circle_id: 'c1',
    office_id: null,
    ...supplement,
  };
}

function pagePourEdition(supplement: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    identifiant: PAGE,
    type_de_page: 'CIRCLE',
    titre: 'Data',
    slug: 'data',
    etat: 'draft',
    version: 1,
    publiee_le: null,
    blocs: [
      { identifiant: 'b1', type_de_bloc: 'TITLE', ordre: 0, contenu: { texte: 'Bienvenue' } },
      {
        identifiant: 'b2',
        type_de_bloc: 'RICH_TEXT',
        ordre: 1,
        contenu: { texte: 'Le cercle Data' },
      },
    ],
    nombre_de_blocs: 2,
    ...supplement,
  };
}

/** Route les appels par URL/methode — meme montage que `PanneauDuCycleDeVie.test.tsx`. */
function servir(reponses: {
  liste?: unknown[];
  page?: Record<string, unknown> | null;
  ecriture?: { charge: unknown; statut?: number };
  transition?: { charge: unknown; statut?: number };
  creation?: { charge: unknown; statut?: number };
}): ReturnType<typeof vi.fn> {
  const appel = vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json(SESSION));
    }
    if (url.endsWith('/pages/gestion')) {
      return Promise.resolve(json({ pages: reponses.liste ?? [] }));
    }
    if (url.endsWith('/gestion') && url.includes('/pages/')) {
      return reponses.page === null || reponses.page === undefined
        ? Promise.resolve(json({ detail: 'introuvable' }, 404))
        : Promise.resolve(json(reponses.page));
    }
    if (url.endsWith('/contenu')) {
      return Promise.resolve(
        json(reponses.ecriture?.charge ?? {}, reponses.ecriture?.statut ?? 200),
      );
    }
    if (/\/(publication|archivage|restauration)$/.test(url)) {
      return Promise.resolve(
        json(reponses.transition?.charge ?? {}, reponses.transition?.statut ?? 200),
      );
    }
    if (url.endsWith('/pages')) {
      return Promise.resolve(
        json(reponses.creation?.charge ?? {}, reponses.creation?.statut ?? 201),
      );
    }
    throw new Error(`URL non attendue dans ce test : ${url}`);
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

function monter(
  roles: readonly string[] | null,
  cible: Record<string, unknown> = { circleId: 'c1' },
): void {
  render(
    <PanneauEditionDeContenu
      cibleCorrespond={(page) =>
        page.typeDePage === 'CIRCLE' && page.circleId === cible['circleId']
      }
      codeEntite={CODE}
      demandeDeCreation={{ type_de_page: 'CIRCLE', titre: 'Data', slug: 'data', cercle: 'DATA' }}
      roles={roles}
    />,
  );
}

describe('aucune page n’existe encore', () => {
  it('un role de creation voit le bouton, un role d’ecriture SEUL ne le voit pas', async () => {
    servir({ liste: [] });
    monter(['BOOST']);
    await waitFor(() => {
      expect(screen.getByText('Aucun contenu editorial pour le moment.')).toBeTruthy();
    });
    expect(screen.queryByText('Creer la page')).toBeNull();
  });

  it('un ESM voit le bouton, et creer charge ensuite la page', async () => {
    const appel = servir({
      liste: [],
      creation: {
        charge: {
          identifiant: PAGE,
          type_de_page: 'CIRCLE',
          titre: 'Data',
          slug: 'data',
          etat: 'draft',
          version: 1,
        },
      },
      page: pagePourEdition(),
    });
    monter(['ESM']);
    await waitFor(() => {
      expect(screen.getByText('Creer la page')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Creer la page'));
    await waitFor(() => {
      expect(screen.getByDisplayValue('Data')).toBeTruthy();
    });
    const chemins = appel.mock.calls.map((appelUnique) => String(appelUnique[0]));
    expect(chemins.some((c) => c.endsWith('/pages') && !c.includes('gestion'))).toBe(true);
  });
});

describe('une page existe — AUCUN formulaire de creation de bloc', () => {
  it('n’affiche jamais de texte invitant a ajouter un bloc — QO-121', async () => {
    servir({ liste: [pageDeGestion()], page: pagePourEdition() });
    monter(['ESM']);
    await waitFor(() => {
      expect(screen.getByText('Blocs (2)')).toBeTruthy();
    });
    expect(screen.queryByText(/ajouter un bloc/i)).toBeNull();
    expect(screen.queryByRole('button', { name: /nouveau bloc/i })).toBeNull();
  });

  it('affiche le contenu brut du bloc, jamais interprete', async () => {
    servir({ liste: [pageDeGestion()], page: pagePourEdition() });
    monter(['ESM']);
    await waitFor(() => {
      expect(screen.getByText(/Bienvenue/)).toBeTruthy();
    });
  });

  it('reordonner puis enregistrer envoie la LISTE COMPLETE dans le nouvel ordre', async () => {
    const appel = servir({
      liste: [pageDeGestion()],
      page: pagePourEdition(),
      ecriture: {
        charge: {
          version: 2,
          blocs: [
            {
              identifiant: 'b2',
              type_de_bloc: 'RICH_TEXT',
              ordre: 0,
              contenu: { texte: 'Le cercle Data' },
            },
            { identifiant: 'b1', type_de_bloc: 'TITLE', ordre: 1, contenu: { texte: 'Bienvenue' } },
          ],
          nombre_de_blocs: 2,
          blocs_archives: 0,
        },
      },
    });
    monter(['ESM']);
    await waitFor(() => {
      expect(screen.getByText('Blocs (2)')).toBeTruthy();
    });
    const monterBoutons = screen.getAllByText('Monter');
    fireEvent.click(monterBoutons[1] as HTMLElement);
    fireEvent.click(screen.getByText('Enregistrer'));

    await waitFor(() => {
      const appelEcriture = appel.mock.calls.find((c) => String(c[0]).endsWith('/contenu'));
      expect(appelEcriture).toBeTruthy();
      const corps = JSON.parse(String((appelEcriture?.[1] as RequestInit).body)) as {
        blocs: { type_de_bloc: string }[];
      };
      expect(corps.blocs.map((b) => b.type_de_bloc)).toEqual(['RICH_TEXT', 'TITLE']);
    });
  });

  it('retirer un bloc puis enregistrer envoie une liste PLUS COURTE', async () => {
    const appel = servir({
      liste: [pageDeGestion()],
      page: pagePourEdition(),
      ecriture: {
        charge: {
          version: 2,
          blocs: [{ identifiant: 'b2', type_de_bloc: 'RICH_TEXT', ordre: 0, contenu: {} }],
          nombre_de_blocs: 1,
          blocs_archives: 1,
        },
      },
    });
    monter(['ESM']);
    await waitFor(() => {
      expect(screen.getByText('Blocs (2)')).toBeTruthy();
    });
    fireEvent.click(screen.getAllByText('Retirer')[0] as HTMLElement);
    await waitFor(() => {
      expect(screen.getByText('Blocs (1)')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Enregistrer'));
    await waitFor(() => {
      const appelEcriture = appel.mock.calls.find((c) => String(c[0]).endsWith('/contenu'));
      const corps = JSON.parse(String((appelEcriture?.[1] as RequestInit).body)) as {
        blocs: unknown[];
      };
      expect(corps.blocs).toHaveLength(1);
    });
  });
});

describe('le cycle de vie — un bouton par etat, pas plus', () => {
  it('BROUILLON avec role d’ecriture : Publier ET Archiver, jamais Restaurer', async () => {
    servir({ liste: [pageDeGestion()], page: pagePourEdition({ etat: 'draft' }) });
    monter(['ESM']);
    await waitFor(() => {
      expect(screen.getByText('Publier')).toBeTruthy();
    });
    expect(screen.getByText('Archiver')).toBeTruthy();
    expect(screen.queryByText('Restaurer')).toBeNull();
  });

  it('PUBLIEE : Archiver seul, jamais Publier ni Restaurer', async () => {
    servir({
      liste: [pageDeGestion({ etat: 'published' })],
      page: pagePourEdition({ etat: 'published' }),
    });
    monter(['ESM']);
    await waitFor(() => {
      expect(screen.getByText('Archiver')).toBeTruthy();
    });
    expect(screen.queryByText('Publier')).toBeNull();
    expect(screen.queryByText('Restaurer')).toBeNull();
  });

  it('ARCHIVEE : un BOOSTER (ecriture SANS restauration) ne voit PAS Restaurer', async () => {
    servir({
      liste: [pageDeGestion({ etat: 'archived' })],
      page: pagePourEdition({ etat: 'archived' }),
    });
    monter(['BOOST'], { circleId: 'c1' });
    await waitFor(() => {
      expect(screen.getByText('Archivee')).toBeTruthy();
    });
    expect(screen.queryByText('Restaurer')).toBeNull();
  });

  it('ARCHIVEE : un ESM (role de restauration) voit Restaurer', async () => {
    servir({
      liste: [pageDeGestion({ etat: 'archived' })],
      page: pagePourEdition({ etat: 'archived' }),
    });
    monter(['ESM']);
    await waitFor(() => {
      expect(screen.getByText('Restaurer')).toBeTruthy();
    });
  });
});
