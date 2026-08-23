/**
 * L'entite consultee — LOT 4, sous-etape `T2`.
 *
 * CE FICHIER PROUVE QUATRE CHOSES
 *
 *   1. **l'entite est resolue depuis l'adresse**, et son nom s'affiche. C'est le
 *      temoin central : sans lui, tous les refus ci-dessous seraient satisfaits par
 *      une page qui n'affiche jamais rien ;
 *   2. **« introuvable » et « erreur » sont DEUX ecrans distincts.** Confondre une
 *      panne reseau avec une entite absente dirait a l'utilisateur que l'entite
 *      n'existe pas alors que c'est sa connexion qui a lache -- et c'est le critere
 *      de `T10`, applique a une lecture ;
 *   3. **une reponse tardive de l'entite QUITTEE ne s'affiche pas** sous la nouvelle
 *      adresse. C'est le §23.3, « annule les requetes et caches associes a l'entite
 *      precedente », et le defaut n'apparait que sous latence -- donc jamais en
 *      developpement local ;
 *   4. **le code est encode dans le chemin appele.** `entity.code` est une chaine
 *      libre de 64 caracteres, sans motif impose : un `/` non encode appellerait une
 *      autre route.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CHEMINS } from '../routes';
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

function monter(code: string): void {
  render(
    <MemoryRouter initialEntries={[`/entites/${code}`]}>
      <Routes>
        <Route path={CHEMINS.entite} element={<PageEntite />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("l'entite consultee vient de l'adresse", () => {
  it("affiche l'entite resolue — LE TEMOIN CENTRAL", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
    );
    monter('bordeaux');
    //  **LE TITRE, PAS N'IMPORTE QUEL TEXTE.** Ma premiere version cherchait
    //  `/eXalt Bordeaux/` n'importe ou et trouvait DEUX noeuds -- le titre et le
    //  message -- ce qui faisait echouer le test sur un livrable correct. Cibler
    //  le titre est plus exact ET prouve davantage : le §9.2 etape 4 demande un
    //  « affichage clair de l'entite consultee ».
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /eXalt Bordeaux/ })).toBeTruthy(),
    );
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
    //  Un code contenant un caractere reserve : sans encodage, le chemin appele
    //  ne serait pas celui qu'on croit emettre.
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
    await waitFor(() => expect(screen.getByText(/Entite introuvable/)).toBeTruthy());
    expect(screen.getByText(/Revenir a la liste des entites/)).toBeTruthy();
  });

  it("rend « erreur » sur 500, et NE DIT RIEN de l'existence de l'entite", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'erreur_interne' } }, 500))),
    );
    monter('bordeaux');
    await waitFor(() => expect(screen.getByText(/Chargement impossible/)).toBeTruthy());
    //  **LA DISTINCTION EST LE POINT.** Un ecran qui dirait « introuvable » sur une
    //  panne apprendrait a l'utilisateur une chose fausse.
    expect(screen.queryByText(/Entite introuvable/)).toBeNull();
  });

  it('rend « erreur » quand le transport lache, sans pretendre a une absence', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );
    monter('bordeaux');
    await waitFor(() => expect(screen.getByText(/Chargement impossible/)).toBeTruthy());
    expect(screen.queryByText(/Entite introuvable/)).toBeNull();
  });

  it("n'affiche PAS l'entite quittee quand sa reponse arrive en retard — §23.3", async () => {
    //  Bordeaux repond LENTEMENT, Paris repond tout de suite. Sans le couplage
    //  etat/code, la reponse de Bordeaux arriverait apres celle de Paris et
    //  s'afficherait sous l'adresse de Paris.
    //  **INITIALISEE A UNE FONCTION INERTE, ET NON A `null`.** TypeScript ne voit
    //  pas la fermeture du `Promise` comme executee : avec `| null`, il restreint
    //  la variable a `null` et refuse l'appel. Un `!` mentirait sur ce qu'on sait ;
    //  une fonction inerte dit la verite -- si la fermeture n'a pas tourne,
    //  l'appel ne fait rien et le test echoue sur son assertion, pas sur un plantage.
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
          <Route path={CHEMINS.entite} element={<PageEntite />} />
        </Routes>
      </MemoryRouter>,
    );
    //  On quitte Bordeaux avant sa reponse, puis on ouvre Paris.
    unmount();
    monter('paris');
    await waitFor(() => expect(screen.getByRole('heading', { name: /eXalt Paris/ })).toBeTruthy());

    //  La reponse de Bordeaux arrive MAINTENANT, apres celle de Paris.
    repondreBordeaux();
    await new Promise((resoudre) => setTimeout(resoudre, 0));
    expect(screen.queryAllByText(/eXalt Bordeaux/)).toHaveLength(0);
    expect(screen.getByRole('heading', { name: /eXalt Paris/ })).toBeTruthy();
  });

  it("affiche l'entite meme sous StrictMode, qui monte deux fois", async () => {
    //  React monte deux fois en developpement, donc l'effet part deux fois et le
    //  premier appel est ABANDONNE. Un abandon traite comme une erreur ferait
    //  clignoter « Chargement impossible » sur une entite parfaitement valide.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
    );
    render(
      <StrictMode>
        <MemoryRouter initialEntries={['/entites/bordeaux']}>
          <Routes>
            <Route path={CHEMINS.entite} element={<PageEntite />} />
          </Routes>
        </MemoryRouter>
      </StrictMode>,
    );
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /eXalt Bordeaux/ })).toBeTruthy(),
    );
    expect(screen.queryByText(/Chargement impossible/)).toBeNull();
  });
});
