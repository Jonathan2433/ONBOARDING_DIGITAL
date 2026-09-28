/**
 * « Mon onboarding » à l'écran — LOT 7, `T13`.
 *
 * TROIS COUPLES, ET AUCUNE MOITIÉ NE SUFFIRAIT — MÊME DISCIPLINE QUE `PageProfil`
 *
 *   brouillon / publiée — les champs sont éditables dans un cas, en lecture
 *   seule dans l'autre (§6.2) ;
 *   tâche `todo` / `completed` — chacune propose SA propre action, jamais
 *   les deux à la fois ;
 *   avec appartenance / sans — la page appelle l'API dans un cas, et
 *   N'APPELLE RIEN dans l'autre (refus par défaut, §20.1).
 *
 * AUCUNE FENÊTRE DE CINQ MINUTES N'EST SIMULÉE ICI
 *
 *   Le bouton « Annuler » est toujours proposé sur une tâche `completed` ; le
 *   test du 409 prouve que c'est le MESSAGE qui change, jamais la présence du
 *   bouton — la fenêtre reste l'affaire de l'API (voir `../api/onboarding.ts`).
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageMonOnboarding } from './PageMonOnboarding';

const APPARTENANCE = '0f8fad5b-d9cb-469f-a165-70867728950e';
const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

let appartenanceDuCadre: string | null = APPARTENANCE;

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: { roles: ['EMP'], estEntitePrincipale: true, appartenance: appartenanceDuCadre },
  }),
}));

afterEach(() => {
  cleanup();
  appartenanceDuCadre = APPARTENANCE;
});

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function fiche(supplement: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 'f1',
    version: 1,
    state: 'draft',
    entity_membership_id: APPARTENANCE,
    person_id: 'p1',
    first_name: 'Ada',
    last_name: 'Lovelace',
    preferred_name: null,
    arrival_date: '2026-10-01',
    metier: 'Ingenieure logicielle',
    statut: 'mission',
    client: 'Client Alpha',
    dsm: 'Dominique Lesmanager',
    cercle_principal: { code: 'DATA', nom: 'Donnees', jeton_de_couleur: null },
    short_intro: null,
    fun_fact: null,
    validated_at: null,
    published_at: null,
    recent_until: null,
    ...supplement,
  };
}

function tache(supplement: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: 't1',
    task_reference_id: 'r1',
    title_snapshot: 'Signer le contrat',
    description_snapshot: null,
    required: true,
    due_at: '2026-10-08T00:00:00Z',
    state: 'todo',
    completed_at: null,
    reopened_at: null,
    ...supplement,
  };
}

function parcoursAvecInstance(taches: Record<string, unknown>[]): Record<string, unknown> {
  return {
    instance: {
      id: 'i1',
      template_version_id: 'v1',
      reference_date: '2026-10-01',
      state: 'active',
      started_at: '2026-10-01T09:00:00Z',
      completed_at: null,
    },
    progression: { taches_obligatoires_totales: 1, taches_obligatoires_terminees: 0 },
    prochaine_tache: taches[0] ?? null,
    taches,
  };
}

const PARCOURS_VIDE = { instance: null, progression: null, prochaine_tache: null, taches: [] };

/** Route les appels par URL/methode — meme montage que `PanneauEditionDeContenu.test.tsx`. */
function servir(options: {
  ficheCharge?: unknown;
  ficheStatut?: number;
  parcoursCharge?: unknown;
  parcoursStatut?: number;
  ecritureFiche?: { charge: unknown; statut?: number };
  validationFiche?: { charge: unknown; statut?: number };
  completion?: { charge: unknown; statut?: number };
  annulation?: { charge: unknown; statut?: number };
}): ReturnType<typeof vi.fn> {
  const appel = vi.fn((url: string, init?: RequestInit) => {
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json(SESSION));
    }
    if (url.endsWith('/arrival-profile/validation')) {
      return Promise.resolve(
        json(options.validationFiche?.charge ?? {}, options.validationFiche?.statut ?? 200),
      );
    }
    if (url.endsWith('/arrival-profile')) {
      if (init?.method === 'PATCH') {
        return Promise.resolve(
          json(options.ecritureFiche?.charge ?? {}, options.ecritureFiche?.statut ?? 200),
        );
      }
      return Promise.resolve(json(options.ficheCharge ?? fiche(), options.ficheStatut ?? 200));
    }
    if (url.endsWith('/completion')) {
      return Promise.resolve(
        json(options.completion?.charge ?? {}, options.completion?.statut ?? 200),
      );
    }
    if (url.endsWith('/annulation')) {
      return Promise.resolve(
        json(options.annulation?.charge ?? {}, options.annulation?.statut ?? 200),
      );
    }
    if (url.endsWith('/onboarding-parcours')) {
      return Promise.resolve(
        json(options.parcoursCharge ?? PARCOURS_VIDE, options.parcoursStatut ?? 200),
      );
    }
    return Promise.resolve(json({ erreur: { code: 'inattendu', message: url } }, 404));
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

function monter(): void {
  render(<PageMonOnboarding />);
}

describe('sans appartenance — refus par defaut du §20.1', () => {
  it("n'appelle AUCUNE route de l'onboarding", async () => {
    appartenanceDuCadre = null;
    const appel = servir({});
    monter();

    await waitFor(() =>
      expect(screen.getByText(/Aucun onboarding ne vous est rattaché/)).toBeTruthy(),
    );
    expect(appel).not.toHaveBeenCalled();
  });
});

describe('la fiche d’arrivée — brouillon', () => {
  it('affiche les champs organisationnels en lecture seule — LE TEMOIN CENTRAL', async () => {
    servir({ ficheCharge: fiche() });
    monter();

    await waitFor(() => expect(screen.getByText('Ingenieure logicielle')).toBeTruthy());
    expect(screen.getByText('mission')).toBeTruthy();
    expect(screen.getByText('Client Alpha')).toBeTruthy();
    expect(screen.getByText('Dominique Lesmanager')).toBeTruthy();
    expect(screen.getByText('Donnees')).toBeTruthy();
  });

  it('propose la présentation et le fun fact EN ÉCRITURE, « Enregistrer » désactivé sans modification', async () => {
    servir({ ficheCharge: fiche() });
    monter();

    await waitFor(() => expect(screen.getByLabelText(/Présentation courte/)).toBeTruthy());
    const bouton = screen.getByRole('button', { name: 'Enregistrer' }) as HTMLButtonElement;
    expect(bouton.disabled).toBe(true);
  });

  it('« Valider et publier » reste désactivé tant qu’aucune présentation n’est renseignée', async () => {
    servir({ ficheCharge: fiche() });
    monter();

    await waitFor(() => expect(screen.getByLabelText(/Présentation courte/)).toBeTruthy());
    const bouton = screen.getByRole('button', {
      name: 'Valider et publier',
    }) as HTMLButtonElement;
    expect(bouton.disabled).toBe(true);
  });

  it('enregistre la présentation — PATCH avec la version LUE, jamais recalculee', async () => {
    const appel = servir({
      ficheCharge: fiche(),
      ecritureFiche: { charge: { id: 'f1', version: 2, state: 'draft' } },
    });
    monter();

    await waitFor(() => expect(screen.getByLabelText(/Présentation courte/)).toBeTruthy());
    fireEvent.change(screen.getByLabelText(/Présentation courte/), {
      target: { value: 'Bonjour, je suis Ada.' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }));

    await waitFor(() => {
      const appelPatch = appel.mock.calls.find(
        (c) => (c[1] as RequestInit | undefined)?.method === 'PATCH',
      );
      expect(appelPatch).toBeTruthy();
      const corps = JSON.parse(String((appelPatch?.[1] as RequestInit).body)) as Record<
        string,
        unknown
      >;
      expect(corps['version']).toBe(1);
      expect(corps['short_intro']).toBe('Bonjour, je suis Ada.');
      expect('fun_fact' in corps).toBe(false);
    });
  });

  it('devient utilisable après enregistrement — « Valider et publier » s’active', async () => {
    servir({
      ficheCharge: fiche({ short_intro: 'Bonjour, je suis Ada.' }),
    });
    monter();

    await waitFor(() => expect(screen.getByLabelText(/Présentation courte/)).toBeTruthy());
    const bouton = screen.getByRole('button', {
      name: 'Valider et publier',
    }) as HTMLButtonElement;
    expect(bouton.disabled).toBe(false);
  });

  it('valide et publie — POST sur la route de validation', async () => {
    const appel = servir({
      ficheCharge: fiche({ short_intro: 'Bonjour, je suis Ada.' }),
      validationFiche: {
        charge: {
          id: 'f1',
          version: 2,
          state: 'published',
          validated_at: '2026-10-02T09:00:00Z',
          published_at: '2026-10-02T09:00:00Z',
          recent_until: '2026-11-01',
        },
      },
    });
    monter();

    await waitFor(() => expect(screen.getByLabelText(/Présentation courte/)).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Valider et publier' }));

    await waitFor(() => {
      expect(
        appel.mock.calls.some((c) => String(c[0]).endsWith('/arrival-profile/validation')),
      ).toBe(true);
    });
  });

  it('rapporte le refus en 422 — présentation manquante', async () => {
    servir({
      ficheCharge: fiche({ short_intro: 'Bonjour, je suis Ada.' }),
      validationFiche: { charge: { erreur: { code: 'x' } }, statut: 422 },
    });
    monter();

    await waitFor(() => expect(screen.getByLabelText(/Présentation courte/)).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Valider et publier' }));

    await waitFor(() =>
      expect(screen.getByText(/obligatoire avant de valider et publier/)).toBeTruthy(),
    );
  });
});

describe('la fiche d’arrivée — publiée, §6.2', () => {
  it('rend la présentation et le fun fact en LECTURE SEULE, aucun champ éditable', async () => {
    servir({
      ficheCharge: fiche({
        state: 'published',
        short_intro: 'Bonjour, je suis Ada.',
        fun_fact: 'Joue du theorbe.',
        validated_at: '2026-10-02T09:00:00Z',
        published_at: '2026-10-02T09:00:00Z',
        recent_until: '2026-11-01',
      }),
    });
    monter();

    await waitFor(() => expect(screen.getByText('Bonjour, je suis Ada.')).toBeTruthy());
    expect(screen.getByText('Joue du theorbe.')).toBeTruthy();
    expect(screen.queryByLabelText(/Présentation courte/)).toBeNull();
    expect(screen.queryByRole('button', { name: 'Enregistrer' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Valider et publier' })).toBeNull();
  });
});

describe('le parcours — aucune instance affectée', () => {
  it('affiche un message, aucune tache', async () => {
    servir({ ficheCharge: fiche(), parcoursCharge: PARCOURS_VIDE });
    monter();

    await waitFor(() =>
      expect(screen.getByText(/Aucun parcours ne vous a encore été affecté/)).toBeTruthy(),
    );
  });
});

describe('le parcours — une instance ACTIVE avec des taches', () => {
  it('affiche la progression et la liste des taches', async () => {
    servir({
      ficheCharge: fiche(),
      parcoursCharge: parcoursAvecInstance([tache()]),
    });
    monter();

    await waitFor(() => expect(screen.getByText('Signer le contrat')).toBeTruthy());
    expect(screen.getByText(/0 \/ 1 tâches/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Marquer comme terminée' })).toBeTruthy();
  });

  it('termine une tache — POST sur la route de completion', async () => {
    const appel = servir({
      ficheCharge: fiche(),
      parcoursCharge: parcoursAvecInstance([tache()]),
      completion: { charge: tache({ state: 'completed', completed_at: '2026-10-08T09:00:00Z' }) },
    });
    monter();

    await waitFor(() => expect(screen.getByText('Signer le contrat')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Marquer comme terminée' }));

    await waitFor(() => {
      expect(appel.mock.calls.some((c) => String(c[0]).endsWith('/completion'))).toBe(true);
    });
  });

  it('propose « Annuler » sur une tache TERMINEE, jamais « Marquer comme terminée »', async () => {
    servir({
      ficheCharge: fiche(),
      parcoursCharge: parcoursAvecInstance([
        tache({ state: 'completed', completed_at: '2026-10-08T09:00:00Z' }),
      ]),
    });
    monter();

    await waitFor(() => expect(screen.getByRole('button', { name: 'Annuler' })).toBeTruthy());
    expect(screen.queryByRole('button', { name: 'Marquer comme terminée' })).toBeNull();
  });

  it('annule une completion — POST sur la route d’annulation', async () => {
    const appel = servir({
      ficheCharge: fiche(),
      parcoursCharge: parcoursAvecInstance([
        tache({ state: 'completed', completed_at: '2026-10-08T09:00:00Z' }),
      ]),
      annulation: { charge: tache() },
    });
    monter();

    await waitFor(() => expect(screen.getByRole('button', { name: 'Annuler' })).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Annuler' }));

    await waitFor(() => {
      expect(appel.mock.calls.some((c) => String(c[0]).endsWith('/annulation'))).toBe(true);
    });
  });

  it('rapporte le refus en 409 sur l’annulation, SANS faire disparaitre le bouton', async () => {
    servir({
      ficheCharge: fiche(),
      parcoursCharge: parcoursAvecInstance([
        tache({ state: 'completed', completed_at: '2026-10-08T09:00:00Z' }),
      ]),
      annulation: { charge: { erreur: { code: 'delai_d_annulation_depasse' } }, statut: 409 },
    });
    monter();

    await waitFor(() => expect(screen.getByRole('button', { name: 'Annuler' })).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Annuler' }));

    await waitFor(() => expect(screen.getByText(/délai de cinq minutes/)).toBeTruthy());
    expect(screen.getByRole('button', { name: 'Annuler' })).toBeTruthy();
  });

  it('n’agit JAMAIS sur une tache ANNULEE — aucun bouton', async () => {
    servir({
      ficheCharge: fiche(),
      parcoursCharge: parcoursAvecInstance([tache({ state: 'cancelled' })]),
    });
    monter();

    await waitFor(() => expect(screen.getByText('Signer le contrat')).toBeTruthy());
    expect(screen.queryByRole('button', { name: 'Marquer comme terminée' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Annuler' })).toBeNull();
  });
});

describe('les refus de chargement', () => {
  it('la session expirée sur la fiche est rapportee — 401', async () => {
    servir({ ficheStatut: 401, ficheCharge: { erreur: { code: 'session_absente' } } });
    monter();

    await waitFor(() => expect(screen.getByText(/session a expiré/)).toBeTruthy());
  });
});
