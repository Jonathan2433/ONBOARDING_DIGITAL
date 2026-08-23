/**
 * Le cadre applicatif — LOT 4, sous-etapes `T2` et `T3`.
 *
 * CE FICHIER PROUVE CINQ CHOSES
 *
 *   1. **l'entite est resolue depuis l'adresse** et son nom s'affiche. C'est le
 *      temoin central : sans lui, tous les refus seraient satisfaits par un cadre
 *      qui n'affiche jamais rien ;
 *   2. **elle est dans l'EN-TETE, pas seulement dans le contenu.** Le §23.3 exige
 *      « visible dans l'en-tete de l'application », et une page interne rendue
 *      sous le cadre l'obtient sans rien faire ;
 *   3. **« introuvable » et « erreur » sont DEUX ecrans distincts.** Confondre une
 *      panne reseau avec une entite absente dirait a l'utilisateur que l'entite
 *      n'existe pas alors que c'est sa connexion qui a lache ;
 *   4. **une reponse tardive de l'entite QUITTEE ne s'affiche pas** sous la
 *      nouvelle adresse — §23.3, « annule les requetes et caches associes a
 *      l'entite precedente ». Le defaut n'apparait que sous latence ;
 *   5. **le code est encode dans le chemin appele.**
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CHEMINS } from '../routes';
import { CadreApplicatif } from './CadreApplicatif';
import { PageEntite } from './PageEntite';

afterEach(cleanup);

const BORDEAUX = {
  id: '0f8fad5b-d9cb-469f-a165-70867728950e',
  code: 'bordeaux',
  nom: 'eXalt Bordeaux',
  ville: 'Bordeaux',
};

function json(charge: unknown, statut: number): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Monte le cadre AVEC sa page interne, comme `App.tsx` le fait. */
function monter(code: string, strict = false): void {
  const arbre = (
    <MemoryRouter initialEntries={[`/entites/${code}`]}>
      <Routes>
        <Route path={CHEMINS.entite} element={<CadreApplicatif />}>
          <Route index element={<PageEntite />} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
  render(strict ? <StrictMode>{arbre}</StrictMode> : arbre);
}

describe("l'entite consultee vient de l'adresse", () => {
  it("affiche l'entite resolue — LE TEMOIN CENTRAL", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
    );
    monter('bordeaux');
    //  **L'ENTITE EST DANS LE `banner`, ET LE TITRE EST CELUI DE LA PAGE.**
    //  Mesure a l'ecran : avec le nom de l'entite en `<h1>`, il apparaissait DEUX
    //  fois et un lecteur d'ecran l'entendait deux fois. Le `<h1>` porte donc le
    //  libelle du cahier §8.1, « Accueil de l'entite ».
    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Bordeaux'));
    expect(screen.getByRole('heading', { name: /Accueil de l/ })).toBeTruthy();
    //  Et le nom n'est PAS repete dans le titre.
    expect(screen.getByRole('heading', { name: /Accueil de l/ }).textContent).not.toContain(
      'eXalt Bordeaux',
    );
  });

  it("porte l'entite dans l'EN-TETE, et la page interne est rendue dessous — §23.3", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
    );
    monter('bordeaux');
    await waitFor(() => expect(screen.getByRole('banner')).toBeTruthy());

    //  L'entite est DANS le repere `banner`, pas ailleurs sur la page : c'est ce
    //  que « visible dans l'en-tete » veut dire, et une page qui l'afficherait
    //  dans son contenu ne le satisferait pas.
    const entete = screen.getByRole('banner');
    expect(entete.textContent).toContain('eXalt Bordeaux');
    expect(entete.textContent).toContain('Bordeaux');
    expect(entete.querySelector('[data-code-entite="bordeaux"]')).toBeTruthy();

    //  Et la page interne est bien rendue SOUS le cadre, dans `main`.
    const principal = screen.getByRole('main');
    expect(principal.textContent).toContain('Vous consultez eXalt Bordeaux');
  });

  it("porte un lien d'evitement qui vise le contenu — §14.2", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
    );
    monter('bordeaux');
    await waitFor(() => expect(screen.getByRole('main')).toBeTruthy());
    const evitement = screen.getByRole('link', { name: /Aller au contenu/ });
    expect(evitement.getAttribute('href')).toBe('#contenu');
    //  La cible existe VRAIMENT : un lien d'evitement qui pointe dans le vide est
    //  pire que pas de lien, il consomme un arret de tabulation pour rien.
    expect(screen.getByRole('main').id).toBe('contenu');
  });

  it('appelle le chemin de resolution, code ENCODE', async () => {
    const appels: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn((chemin: string) => {
        appels.push(chemin);
        return Promise.resolve(json(BORDEAUX, 200));
      }),
    );
    monter(encodeURIComponent('bord/eaux'));
    await waitFor(() => expect(appels.length).toBeGreaterThan(0));
    expect(appels[0]).toBe('/api/v1/entities/bord%2Feaux');
    expect(appels[0]).not.toContain('bord/eaux');
  });

  it('rend « introuvable » sur 404, et propose le retour a la liste', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'entite_introuvable' } }, 404))),
    );
    monter('inconnue');
    await waitFor(() => expect(screen.getByRole('heading', { name: /introuvable/ })).toBeTruthy());
    expect(screen.getByText(/Revenir a la liste des entites/)).toBeTruthy();
    //  L'en-tete ne montre AUCUNE entite : il n'y en a pas a montrer.
    expect(screen.getByRole('banner').querySelector('.app-entite')).toBeNull();
  });

  it("rend « erreur » sur 500, et NE DIT RIEN de l'existence de l'entite", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'erreur_interne' } }, 500))),
    );
    monter('bordeaux');
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /Chargement impossible/ })).toBeTruthy(),
    );
    expect(screen.queryByText(/Entite introuvable/)).toBeNull();
  });

  it('rend « erreur » quand le transport lache, sans pretendre a une absence', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );
    monter('bordeaux');
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /Chargement impossible/ })).toBeTruthy(),
    );
    expect(screen.queryByText(/Entite introuvable/)).toBeNull();
  });

  it("n'affiche PAS l'entite quittee quand sa reponse arrive en retard — §23.3", async () => {
    //  **INITIALISEE A UNE FONCTION INERTE, ET NON A `null`.** TypeScript ne voit
    //  pas la fermeture du `Promise` comme executee : avec `| null`, il restreint
    //  la variable a `null` et refuse l'appel. Un `!` mentirait sur ce qu'on sait.
    let repondreBordeaux: () => void = () => {};
    vi.stubGlobal(
      'fetch',
      vi.fn((chemin: string) => {
        if (chemin.endsWith('/bordeaux')) {
          return new Promise<Response>((resoudre) => {
            repondreBordeaux = () => resoudre(json(BORDEAUX, 200));
          });
        }
        return Promise.resolve(
          json({ ...BORDEAUX, code: 'paris', nom: 'eXalt Paris', ville: 'Paris' }, 200),
        );
      }),
    );

    const { unmount } = render(
      <MemoryRouter initialEntries={['/entites/bordeaux']}>
        <Routes>
          <Route path={CHEMINS.entite} element={<CadreApplicatif />}>
            <Route index element={<PageEntite />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    unmount();
    monter('paris');
    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Paris'));

    repondreBordeaux();
    await new Promise((resoudre) => setTimeout(resoudre, 0));
    expect(screen.queryAllByText(/eXalt Bordeaux/)).toHaveLength(0);
    expect(screen.getByRole('banner').textContent).toContain('eXalt Paris');
  });

  it("affiche l'entite meme sous StrictMode, qui monte deux fois", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
    );
    monter('bordeaux', true);
    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Bordeaux'));
    expect(screen.queryByText(/Chargement impossible/)).toBeNull();
  });
});
