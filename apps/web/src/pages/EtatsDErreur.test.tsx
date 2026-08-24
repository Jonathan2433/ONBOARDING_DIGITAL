/**
 * Les états d'erreur et la perte de connexion — LOT 4, `T10`, story `MVP-L04-US006`.
 *
 * LE CRITÈRE NOMMAIT UN PIÈGE, ET LE §17.2 LE RÉSOUT
 *
 *   La fiche écrit « un `fetch` qui échoue **après l'envoi** n'affiche **jamais**
 *   “sauvegardé” ». Ce lot est en lecture seule : il n'y a rien à sauvegarder.
 *
 *   Le cahier §17.2 dit ce que cela signifie : « Après perte de connexion sur une
 *   page déjà chargée, l'utilisateur voit un état explicite et **aucune action
 *   n'est déclarée enregistrée sans confirmation de l'API**. » Le succès doit
 *   donc venir de la **réponse**, jamais du fait d'avoir émis la requête — et les
 *   écritures existent : ce sont celles du LOT 3.
 *
 *   **Cette propriété est rendue MÉCANIQUE plutôt que testée ici** :
 *   `make cadre-check` confronte les états qui rendent `data-ton='succes'` aux
 *   états affectés dans un `catch`, et exige que l'intersection soit vide. Un test
 *   par écran vieillirait au premier écran ajouté ; le contrôle, non.
 *
 *   Ce fichier éprouve ce qui reste : l'état **explicite** de perte de connexion,
 *   le **réessai qui réessaie**, et la **corrélation copiable** du §17.4.
 */
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CHEMINS, RUBRIQUES } from '../routes';
import { CadreApplicatif } from './CadreApplicatif';
import { PageEntite } from './PageEntite';
import { PageRubrique } from './PageRubrique';

afterEach(cleanup);

const BORDEAUX = {
  id: '0f8fad5b-d9cb-469f-a165-70867728950e',
  code: 'bordeaux',
  nom: 'eXalt Bordeaux',
  ville: 'Bordeaux',
};
const CORRELATION = 'c0rr-3l4t-10n0-t10a';

function json(charge: unknown, statut: number, correlation?: string): Response {
  const entetes: Record<string, string> = { 'Content-Type': 'application/json' };
  if (correlation !== undefined) {
    entetes['X-Request-ID'] = correlation;
  }
  return new Response(JSON.stringify(charge), { status: statut, headers: entetes });
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux']}>
      <Routes>
        <Route path={CHEMINS.entite} element={<CadreApplicatif />}>
          {RUBRIQUES.map((rubrique) =>
            rubrique.suffixe === '' ? (
              <Route key={rubrique.cle} index element={<PageEntite />} />
            ) : (
              <Route
                key={rubrique.cle}
                path={rubrique.suffixe}
                element={
                  <PageRubrique cle={rubrique.cle} libelle={rubrique.libelle} lot={rubrique.lot} />
                }
              />
            ),
          )}
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

/** Reposer `navigator.onLine`, que chaque test manipule. */
function poserLaConnexion(enLigne: boolean): void {
  Object.defineProperty(navigator, 'onLine', { value: enLigne, configurable: true });
}

beforeEach(() => poserLaConnexion(true));

describe('la perte de connexion sur une page déjà chargée — §17.2', () => {
  it("affiche un état EXPLICITE, et il n'est pas confondu avec une erreur", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Bordeaux'));

    //  La connexion tombe APRÈS le chargement — c'est le cas que le §17.2 nomme.
    await act(async () => {
      poserLaConnexion(false);
      window.dispatchEvent(new Event('offline'));
      await Promise.resolve();
    });

    const message = screen.getByRole('status').textContent ?? '';
    expect(message).toContain('connexion reseau est perdue');
    //  **IL DIT QUE CE QUI EST AFFICHÉ EST PÉRIMÉ**, ce qui est l'information
    //  utile : sans cela, l'utilisateur croirait lire l'état courant.
    expect(message).toContain("date d'avant la coupure");
    //  Et ce n'est PAS un `alert` : l'utilisateur constate déjà la coupure, et
    //  interrompre sa lecture n'ajoute rien.
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('recharge de lui-même au RETOUR de la connexion', async () => {
    const appels = vi.fn(() => Promise.resolve(json(BORDEAUX, 200)));
    vi.stubGlobal('fetch', appels);
    monter();
    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Bordeaux'));
    const avant = appels.mock.calls.length;

    await act(async () => {
      poserLaConnexion(false);
      window.dispatchEvent(new Event('offline'));
      await Promise.resolve();
    });
    await act(async () => {
      poserLaConnexion(true);
      window.dispatchEvent(new Event('online'));
      await Promise.resolve();
    });

    await waitFor(() => expect(appels.mock.calls.length).toBeGreaterThan(avant));
    //  **LE TÉMOIN QUI COMPTE** : sans lui, un test qui vérifie seulement que
    //  l'écran revient serait satisfait par un écran qui n'a jamais rien rechargé
    //  et affiche encore ses données périmées.
    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Bordeaux'));
  });
});

describe("l'écran d'erreur porte un réessai et une corrélation — §17.4", () => {
  it('le bouton RÉESSAIE réellement, et un second appel est émis', async () => {
    let echouer = true;
    const appels = vi.fn(() =>
      Promise.resolve(echouer ? json({ erreur: {} }, 500, CORRELATION) : json(BORDEAUX, 200)),
    );
    vi.stubGlobal('fetch', appels);
    monter();

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    const bouton = screen.getByRole('button', { name: 'Reessayer' });
    const avant = appels.mock.calls.length;

    //  Le service se rétablit, puis on réessaie.
    echouer = false;
    await act(async () => {
      bouton.click();
      await Promise.resolve();
    });

    await waitFor(() => expect(appels.mock.calls.length).toBeGreaterThan(avant));
    //  **ET L'ÉCRAN SE RÉTABLIT.** Un bouton qui relancerait sans que rien ne
    //  change serait exactement l'avertissement faux du §7.21.
    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Bordeaux'));
  });

  it("affiche l'identifiant de corrélation et le rend COPIABLE — §17.4", async () => {
    const ecrits: string[] = [];
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: (t: string) => {
          ecrits.push(t);
          return Promise.resolve();
        },
      },
      configurable: true,
    });
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: {} }, 500, CORRELATION))),
    );
    monter();

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    //  **AFFICHÉ EN CLAIR**, donc sélectionnable à la main : la copie n'est
    //  jamais le seul moyen.
    expect(screen.getByText(CORRELATION)).toBeTruthy();

    await act(async () => {
      screen.getByRole('button', { name: 'Copier' }).click();
      await Promise.resolve();
    });

    expect(ecrits).toEqual([CORRELATION]);
    //  **INTERROGÉ PAR LE TEXTE, PAS PAR UNE CLASSE.** `T11` a réécrit le panneau
    //  sur le design system, et `.app-correlation-annonce` est devenue
    //  `.ex-notification` : mes deux assertions de `T10` ont échoué sur un
    //  livrable **meilleur**. Un test qui épingle une classe CSS épingle une
    //  décision d'implémentation ; ce qui compte est ce que l'utilisateur lit.
    await waitFor(() => expect(screen.getByText(/copié dans le presse-papiers/)).toBeTruthy());
  });

  it('reste utilisable quand le presse-papiers est REFUSÉ', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: () => Promise.reject(new Error('refuse')) },
      configurable: true,
    });
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: {} }, 500, CORRELATION))),
    );
    monter();

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    await act(async () => {
      screen.getByRole('button', { name: 'Copier' }).click();
      await Promise.resolve();
    });

    //  **L'ÉCHEC EST DIT, ET L'IDENTIFIANT RESTE LÀ.** Un bouton qui échouerait en
    //  silence serait pire que pas de bouton — §7.21.
    await waitFor(() => expect(screen.getByText(/Copie refusée par le navigateur/)).toBeTruthy());
    //  Et l'identifiant reste là, sélectionnable à la main.
    expect(screen.getByText(CORRELATION)).toBeTruthy();
  });

  it("n'affiche AUCUNE corrélation quand la requête n'a pas abouti", async () => {
    //  Un échec de transport ne porte aucune corrélation : la requête n'a pas
    //  atteint l'API. Afficher un champ vide apprendrait à citer une valeur qui
    //  ne relie à rien.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );
    monter();

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    //  Aucune corrélation affichée : ni la valeur, ni le titre de son bloc.
    expect(screen.queryByRole('heading', { name: /correlation/i })).toBeNull();
    //  Le réessai, lui, reste proposé : c'est précisément le cas où il sert.
    expect(screen.getByRole('button', { name: 'Reessayer' })).toBeTruthy();
  });
});

describe('un 401 dit « session expirée », pas « chargement impossible »', () => {
  it('propose de se reconnecter, et AUCUN réessai — le défaut vu au navigateur', async () => {
    //  **CE TEST N'EXISTE PAS PAR PRUDENCE.** Le 24/08/2026, ma session de
    //  démonstration avait expiré : l'API rendait 401, et le cadre affichait
    //  « L'entité n'a pas pu être chargée. Cela ne dit rien de son existence » —
    //  une phrase **fausse**. L'utilisateur n'avait pas un problème de chargement,
    //  il était déconnecté. Même classe que `T8-4` : plausible, et seul l'écran
    //  l'a montré faux.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'session_refusee' } }, 401))),
    );
    monter();

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /Session expiree/ })).toBeTruthy(),
    );
    expect(screen.getByRole('status').textContent).toContain('Votre session a expire');
    //  Un lien vers la connexion, et **aucun bouton de réessai** : réessayer ne
    //  peut pas aboutir sans nouvelle session, et le proposer serait un
    //  avertissement faux (§7.21).
    expect(screen.getByRole('link', { name: 'Se reconnecter' }).getAttribute('href')).toBe(
      '/connexion',
    );
    expect(screen.queryByRole('button', { name: 'Reessayer' })).toBeNull();
  });

  it("ne confond PAS un 500 avec un 401 — le témoin dans l'autre sens", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: {} }, 500, CORRELATION))),
    );
    monter();

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.queryByRole('heading', { name: /Session expiree/ })).toBeNull();
    //  Et là le réessai a un sens, donc il est proposé.
    expect(screen.getByRole('button', { name: 'Reessayer' })).toBeTruthy();
  });
});
