/**
 * Deposer et autoriser une photo de profil, a l'ecran — LOT 11, `T2`,
 * `MVP-L11-US004`/`US005`.
 *
 * LE TEMOIN CENTRAL : RIEN TANT QUE LES DROITS NE SONT PAS CONNUS, OU SI
 * AUCUN DES DEUX N'EST ACCORDE
 *
 *   Meme discipline que `PanneauDuCycleDeVie` : un panneau qui apparaitrait
 *   puis disparaitrait est pire qu'un panneau absent — §20.1, le refus par
 *   defaut.
 *
 * LE SONDAGE EST EPROUVE AVEC DE VRAIES AVANCEES DE MINUTEUR, JAMAIS UN MOCK
 * DE `setTimeout`
 *
 *   `vi.useFakeTimers()` fait avancer le temps reellement simule par
 *   Vitest — un mock qui se contenterait d'appeler la fonction immediatement
 *   ne prouverait rien du delai entre deux sondages.
 */
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { PanneauPhoto } from './PanneauPhoto';

import { EN_TETE_CLE_IDEMPOTENCE, EN_TETE_JETON_CSRF } from '@onboarding/contracts';

afterEach(cleanup);

const CODE = 'bordeaux';
const APPARTENANCE = '0f8fad5b-d9cb-469f-a165-70867728950e';
const MEDIA = 'a4c0c7f1-4d8a-4f4b-9b0d-1234567890ab';
const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

interface Reponses {
  readonly droits?: { charge: unknown; statut?: number };
  readonly depot?: { charge: unknown; statut?: number };
  readonly etat?: { charge: unknown; statut?: number }[];
  readonly autorisation?: { charge: unknown; statut?: number };
  readonly retrait?: { charge: unknown; statut?: number };
}

/** Chaque chemin est servi independamment — `/etat` consomme sa liste dans l'ordre. */
function servir(reponses: Reponses): void {
  const etats = [...(reponses.etat ?? [])];
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.endsWith('/auth/session')) {
        return Promise.resolve(json(SESSION));
      }
      if (url.endsWith('/droits')) {
        const d = reponses.droits ?? {
          charge: { peut_deposer: true, peut_gerer_autorisation: true },
        };
        return Promise.resolve(json(d.charge, d.statut ?? 200));
      }
      if (url.endsWith('/etat')) {
        const prochain = etats.shift() ?? {
          charge: { id: MEDIA, state: 'ready', rejection_code: null },
        };
        return Promise.resolve(json(prochain.charge, prochain.statut ?? 200));
      }
      if (url.endsWith('/autorisation')) {
        const a = reponses.autorisation ?? {
          charge: { id: 'auth1', granted_at: '2026-10-31T09:00:00Z' },
        };
        return Promise.resolve(json(a.charge, a.statut ?? 201));
      }
      if (url.endsWith('/retrait')) {
        const r = reponses.retrait ?? { charge: { autorisations_retirees: 1 } };
        return Promise.resolve(json(r.charge, r.statut ?? 200));
      }
      //  Le depot — seul chemin restant, `POST …/photo`.
      const dep = reponses.depot ?? { charge: { id: MEDIA, state: 'pending' } };
      return Promise.resolve(json(dep.charge, dep.statut ?? 201));
    }),
  );
}

function appels(): { 0: string; 1?: RequestInit }[] {
  return (globalThis.fetch as unknown as { mock: { calls: { 0: string; 1?: RequestInit }[] } }).mock
    .calls;
}

function monter(surSucces: () => void = () => undefined): void {
  render(<PanneauPhoto appartenance={APPARTENANCE} codeEntite={CODE} surSucces={surSucces} />);
}

function fichier(nom = 'photo.jpg', type = 'image/jpeg'): File {
  return new File(['contenu'], nom, { type });
}

describe('les droits gouvernent ce qui est propose', () => {
  it('ne montre RIEN tant que les droits ne sont pas arrives', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(() => undefined)),
    );
    const { container } = render(
      <PanneauPhoto appartenance={APPARTENANCE} codeEntite={CODE} surSucces={() => undefined} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('ne montre RIEN si aucun des deux droits n’est accorde', async () => {
    servir({ droits: { charge: { peut_deposer: false, peut_gerer_autorisation: false } } });
    const { container } = render(
      <PanneauPhoto appartenance={APPARTENANCE} codeEntite={CODE} surSucces={() => undefined} />,
    );
    await waitFor(() => {
      expect(appels().some((a) => a[0].endsWith('/droits'))).toBe(true);
    });
    expect(container.innerHTML).toBe('');
  });

  it('montre le depot SEUL quand seul `peutDeposer` est accorde', async () => {
    servir({ droits: { charge: { peut_deposer: true, peut_gerer_autorisation: false } } });
    monter();
    await waitFor(() => {
      expect(screen.getByLabelText('Deposer une nouvelle photo')).toBeTruthy();
    });
    expect(screen.queryByRole('button', { name: 'Retirer l’autorisation actuelle' })).toBeNull();
  });

  it('montre le retrait SEUL quand seul `peutGererAutorisation` est accorde', async () => {
    servir({ droits: { charge: { peut_deposer: false, peut_gerer_autorisation: true } } });
    monter();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Retirer l’autorisation actuelle' })).toBeTruthy();
    });
    expect(screen.queryByLabelText('Deposer une nouvelle photo')).toBeNull();
  });
});

describe('le depot, le sondage, puis l’autorisation', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('porte le jeton anti-CSRF ET une cle d’idempotence au depot', async () => {
    servir({ etat: [{ charge: { id: MEDIA, state: 'ready', rejection_code: null } }] });
    monter();
    await vi.waitFor(() => {
      expect(screen.getByLabelText('Deposer une nouvelle photo')).toBeTruthy();
    });
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Deposer une nouvelle photo'), {
        target: { files: [fichier()] },
      });
    });
    await vi.waitFor(() => {
      expect(appels().some((a) => a[0].endsWith('/photo') && a[1]?.method === 'POST')).toBe(true);
    });
    const depot = appels().find((a) => a[0].endsWith('/photo') && a[1]?.method === 'POST');
    const enTetes = (depot?.[1]?.headers ?? {}) as Record<string, string>;
    expect(enTetes[EN_TETE_JETON_CSRF]).toBe('un-jeton-anti-csrf');
    expect(enTetes[EN_TETE_CLE_IDEMPOTENCE]).toMatch(/^[0-9a-f-]{36}$/);
  });

  it('sonde l’etat jusqu’a `ready`, PUIS propose l’autorisation', async () => {
    servir({
      etat: [
        { charge: { id: MEDIA, state: 'processing', rejection_code: null } },
        { charge: { id: MEDIA, state: 'ready', rejection_code: null } },
      ],
    });
    monter();
    await vi.waitFor(() => {
      expect(screen.getByLabelText('Deposer une nouvelle photo')).toBeTruthy();
    });
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Deposer une nouvelle photo'), {
        target: { files: [fichier()] },
      });
    });
    await vi.waitFor(() => {
      expect(screen.getByText(/Verification de la photo/)).toBeTruthy();
    });
    //  LE PREMIER SONDAGE PART IMMEDIATEMENT, SANS ATTENDRE — seul le SECOND
    //  (et les suivants) est separe par le delai. Il rend encore `processing`
    //  ici, donc le bouton n'apparait pas avant que le minuteur n'avance.
    expect(screen.queryByRole('button', { name: 'Autoriser l’affichage' })).toBeNull();
    //  Second sondage, apres le delai : `ready`.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    await vi.waitFor(() => {
      expect(screen.getByRole('button', { name: 'Autoriser l’affichage' })).toBeTruthy();
    });
  });

  it('un media REJETE affiche le message propre a son code', async () => {
    servir({
      etat: [{ charge: { id: MEDIA, state: 'rejected', rejection_code: 'format_non_autorise' } }],
    });
    monter();
    await vi.waitFor(() => {
      expect(screen.getByLabelText('Deposer une nouvelle photo')).toBeTruthy();
    });
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Deposer une nouvelle photo'), {
        target: { files: [fichier()] },
      });
    });
    await vi.waitFor(() => {
      expect(screen.getByText(/format d’image n’est pas accepte/)).toBeTruthy();
    });
  });

  it('accorder l’autorisation previent la page du succes', async () => {
    const surSucces = vi.fn();
    servir({ etat: [{ charge: { id: MEDIA, state: 'ready', rejection_code: null } }] });
    monter(surSucces);
    await vi.waitFor(() => {
      expect(screen.getByLabelText('Deposer une nouvelle photo')).toBeTruthy();
    });
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Deposer une nouvelle photo'), {
        target: { files: [fichier()] },
      });
    });
    await vi.waitFor(() => {
      expect(screen.getByRole('button', { name: 'Autoriser l’affichage' })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Autoriser l’affichage' }));
    await vi.waitFor(() => {
      expect(surSucces).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText(/desormais affichee/)).toBeTruthy();
  });

  it('un depot REFUSE (422) dit de verifier la taille et le type', async () => {
    servir({ depot: { charge: { code: 'fichier_trop_lourd' }, statut: 422 } });
    monter();
    await vi.waitFor(() => {
      expect(screen.getByLabelText('Deposer une nouvelle photo')).toBeTruthy();
    });
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Deposer une nouvelle photo'), {
        target: { files: [fichier()] },
      });
    });
    await vi.waitFor(() => {
      expect(screen.getByText(/10 Mo maximum/)).toBeTruthy();
    });
  });
});

describe('le retrait', () => {
  it('previent la page du succes des que le retrait aboutit', async () => {
    const surSucces = vi.fn();
    servir({});
    monter(surSucces);
    await vi.waitFor(() => {
      expect(screen.getByRole('button', { name: 'Retirer l’autorisation actuelle' })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Retirer l’autorisation actuelle' }));
    await vi.waitFor(() => {
      expect(surSucces).toHaveBeenCalledTimes(1);
    });
  });

  it('un refus de role (403) dit pourquoi, et n’appelle PAS `surSucces`', async () => {
    const surSucces = vi.fn();
    servir({ retrait: { charge: { code: 'photo_hors_perimetre' }, statut: 403 } });
    monter(surSucces);
    await vi.waitFor(() => {
      expect(screen.getByRole('button', { name: 'Retirer l’autorisation actuelle' })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Retirer l’autorisation actuelle' }));
    await vi.waitFor(() => {
      expect(screen.getByText(/ne permet pas de retirer/)).toBeTruthy();
    });
    expect(surSucces).not.toHaveBeenCalled();
  });
});
