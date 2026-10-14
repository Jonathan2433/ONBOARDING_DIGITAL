/**
 * « Onboarding » à l'écran — LOT 7, `T14`, déplacé sous son onglet par le LOT 9 `T14`.
 *
 * REPRISE À L'IDENTIQUE DE `PageAdministration.test.tsx` (LOT 7)
 *
 *   Le composant ne change AUCUNE règle en migrant : ces tests le prouvent en
 *   restant ceux d'origine, adaptés au seul fait que `code`/`roles` sont
 *   désormais des PROPS du composant, et non lus via `useEntiteConsultee`.
 *
 * DEUX COUPLES, ET AUCUNE MOITIÉ NE SUFFIRAIT
 *
 *   rôle de gestion (DSM…SUPER) / rôle sans droit (EMP, OFFICE) — le
 *   catalogue et les modèles n'appellent AUCUNE route dans le second cas ;
 *   version `retired` avec un rôle qui restaure (ESM) / sans (DSM).
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SectionOnboarding } from './SectionOnboarding';

const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

afterEach(() => {
  cleanup();
});

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function tacheDeReference(supplement: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'r1',
    entity_id: 'e1',
    code: 'badge-acces',
    title: 'Demander un badge',
    description: null,
    category: null,
    active: true,
    ...supplement,
  };
}

function version(supplement: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'v1',
    template_id: 'm1',
    version_number: 1,
    state: 'draft',
    change_summary: null,
    ...supplement,
  };
}

function modele(supplement: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'm1',
    entity_id: 'e1',
    name: 'Onboarding consultant',
    target_status: 'mission',
    scope_type: 'ENTITY',
    scope_person_id: null,
    scope_circle_id: null,
    state: 'active',
    versions: [version()],
    ...supplement,
  };
}

/** Route les appels par URL/méthode — même montage que `PageMonOnboarding.test.tsx`. */
function servir(options: {
  catalogue?: unknown[];
  modeles?: unknown[];
  creationTache?: { charge: unknown; statut?: number };
  creationModele?: { charge: unknown; statut?: number };
  creationVersion?: { charge: unknown; statut?: number };
  definitionTaches?: { charge: unknown; statut?: number };
  publication?: { charge: unknown; statut?: number };
  archivage?: { charge: unknown; statut?: number };
  restauration?: { charge: unknown; statut?: number };
}): ReturnType<typeof vi.fn> {
  const appel = vi.fn((url: string, init?: RequestInit) => {
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json(SESSION));
    }
    if (url.endsWith('/task-references')) {
      if (init?.method === 'POST') {
        return Promise.resolve(
          json(
            options.creationTache?.charge ?? tacheDeReference(),
            options.creationTache?.statut ?? 201,
          ),
        );
      }
      return Promise.resolve(
        json({
          taches: options.catalogue ?? [],
          nombre_de_taches: (options.catalogue ?? []).length,
        }),
      );
    }
    if (url.endsWith('/onboarding/templates')) {
      if (init?.method === 'POST') {
        return Promise.resolve(
          json(options.creationModele?.charge ?? modele(), options.creationModele?.statut ?? 201),
        );
      }
      return Promise.resolve(
        json({ modeles: options.modeles ?? [], nombre_de_modeles: (options.modeles ?? []).length }),
      );
    }
    if (url.endsWith('/versions')) {
      return Promise.resolve(
        json(options.creationVersion?.charge ?? version(), options.creationVersion?.statut ?? 201),
      );
    }
    if (url.endsWith('/tasks')) {
      return Promise.resolve(
        json(
          options.definitionTaches?.charge ?? { taches: [], nombre_de_taches: 0 },
          options.definitionTaches?.statut ?? 200,
        ),
      );
    }
    if (url.endsWith('/publication')) {
      return Promise.resolve(
        json(
          options.publication?.charge ?? version({ state: 'published' }),
          options.publication?.statut ?? 200,
        ),
      );
    }
    if (url.endsWith('/archivage')) {
      return Promise.resolve(
        json(
          options.archivage?.charge ?? { id: 'v1', version_number: 1, state: 'retired' },
          options.archivage?.statut ?? 200,
        ),
      );
    }
    if (url.endsWith('/restauration')) {
      return Promise.resolve(
        json(
          options.restauration?.charge ?? version({ state: 'published' }),
          options.restauration?.statut ?? 200,
        ),
      );
    }
    return Promise.resolve(json({ erreur: { code: 'inattendu', message: url } }, 404));
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

function monter(roles: readonly string[]): void {
  render(<SectionOnboarding code="bordeaux" roles={roles} />);
}

describe('un rôle SANS aucun droit de gestion — refus par défaut du §20.1', () => {
  it("n'appelle NI le catalogue NI les modèles", async () => {
    const appel = servir({});
    monter(['EMP']);

    await waitFor(() =>
      expect(
        screen.getByText(/Votre rôle ne porte aucun droit de gestion sur ce groupe/),
      ).toBeTruthy(),
    );
    expect(appel.mock.calls.some((c) => (c[0] as string).endsWith('/task-references'))).toBe(false);
    expect(appel.mock.calls.some((c) => (c[0] as string).endsWith('/onboarding/templates'))).toBe(
      false,
    );
  });
});

describe('un DSM — droit de gestion sur son propre périmètre', () => {
  it('affiche le catalogue et les modèles', async () => {
    servir({ catalogue: [tacheDeReference()], modeles: [modele()] });
    monter(['DSM']);

    await waitFor(() => expect(screen.getByText('Catalogue des tâches')).toBeTruthy());
    expect(screen.getByText('Demander un badge')).toBeTruthy();
    expect(screen.getByText('Onboarding consultant')).toBeTruthy();
  });

  it('crée une tâche de référence — POST avec le code et le titre saisis', async () => {
    const appel = servir({ catalogue: [] });
    monter(['DSM']);

    await waitFor(() => expect(screen.getByLabelText(/Code \(identifiant stable\)/)).toBeTruthy());
    fireEvent.change(screen.getByLabelText(/Code \(identifiant stable\)/), {
      target: { value: 'nouveau-badge' },
    });
    fireEvent.change(screen.getByLabelText('Titre'), { target: { value: 'Nouveau badge' } });
    fireEvent.click(screen.getByRole('button', { name: 'Créer une tâche de référence' }));

    await waitFor(() => {
      const appelPost = appel.mock.calls.find(
        (c) =>
          (c[0] as string).endsWith('/task-references') &&
          (c[1] as RequestInit | undefined)?.method === 'POST',
      );
      expect(appelPost).toBeTruthy();
      const corps = JSON.parse(String((appelPost?.[1] as RequestInit).body)) as Record<
        string,
        unknown
      >;
      expect(corps['code']).toBe('nouveau-badge');
      expect(corps['title']).toBe('Nouveau badge');
      expect(corps['portee']).toBe('ENTITE');
    });
  });

  it('crée un modèle — POST avec le nom saisi et la portée ENTITY', async () => {
    const appel = servir({ modeles: [] });
    monter(['DSM']);

    await waitFor(() => expect(screen.getByLabelText('Nom du modèle')).toBeTruthy());
    fireEvent.change(screen.getByLabelText('Nom du modèle'), {
      target: { value: 'Onboarding mission' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Créer un modèle/ }));

    await waitFor(() => {
      const appelPost = appel.mock.calls.find(
        (c) =>
          (c[0] as string).endsWith('/onboarding/templates') &&
          (c[1] as RequestInit | undefined)?.method === 'POST',
      );
      expect(appelPost).toBeTruthy();
      const corps = JSON.parse(String((appelPost?.[1] as RequestInit).body)) as Record<
        string,
        unknown
      >;
      expect(corps['name']).toBe('Onboarding mission');
      expect(corps['portee']).toBe('ENTITY');
    });
  });

  it('crée une nouvelle version pour un modèle existant', async () => {
    const appel = servir({ modeles: [modele({ versions: [] })] });
    monter(['DSM']);

    await waitFor(() => expect(screen.getByText('Onboarding consultant')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Créer une nouvelle version' }));

    await waitFor(() => {
      expect(appel.mock.calls.some((c) => (c[0] as string).endsWith('/versions'))).toBe(true);
    });
  });

  it('publie une version brouillon — le bouton n’apparaît QUE sur `draft`', async () => {
    servir({ modeles: [modele({ versions: [version()] })] });
    monter(['DSM']);

    await waitFor(() => expect(screen.getByText('Version 1')).toBeTruthy());
    expect(screen.getByRole('button', { name: 'Publier cette version' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Archiver cette version' })).toBeNull();
  });

  it('archive une version publiée — le bouton n’apparaît QUE sur `published`', async () => {
    servir({ modeles: [modele({ versions: [version({ state: 'published' })] })] });
    monter(['DSM']);

    await waitFor(() => expect(screen.getByText('Publiée')).toBeTruthy());
    expect(screen.getByRole('button', { name: 'Archiver cette version' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Publier cette version' })).toBeNull();
  });

  it('NE PROPOSE PAS « Restaurer » sur une version archivée — DSM exclu EN BLOC, §9', async () => {
    servir({ modeles: [modele({ versions: [version({ state: 'retired' })] })] });
    monter(['DSM']);

    await waitFor(() => expect(screen.getByText('Archivée')).toBeTruthy());
    expect(screen.queryByRole('button', { name: 'Restaurer cette version' })).toBeNull();
  });
});

describe('un ESM — restaure une version archivée, `ECART-066` résolu', () => {
  it('propose « Restaurer » sur une version `retired`', async () => {
    servir({ modeles: [modele({ versions: [version({ state: 'retired' })] })] });
    monter(['ESM']);

    await waitFor(() => expect(screen.getByText('Archivée')).toBeTruthy());
    expect(screen.getByRole('button', { name: 'Restaurer cette version' })).toBeTruthy();
  });
});
