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

function json(charge: unknown, statut: number): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Monte le cadre AVEC ses six routes internes, comme `App.tsx` le fait.
 *
 * Les routes sont engendrees depuis `RUBRIQUES`, exactement comme dans
 * l'application : un montage de test qui les enumererait a la main divergerait au
 * premier ajout, et le test cesserait d'eprouver ce que l'application fait.
 */
function monter(code: string, strict = false, chemin?: string): void {
  const arbre = (
    <MemoryRouter initialEntries={[chemin ?? `/entites/${code}`]}>
      <Routes>
        <Route path={CHEMINS.entite} element={<CadreApplicatif />}>
          {RUBRIQUES.map((rubrique) =>
            rubrique.suffixe === '' ? (
              <Route key={rubrique.cle} index element={<PageEntite />} />
            ) : (
              <Route
                key={rubrique.cle}
                path={rubrique.suffixe}
                element={<PageRubrique libelle={rubrique.libelle} lot={rubrique.lot} />}
              />
            ),
          )}
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
    //  **ET ELLE EST FOCUSABLE PAR PROGRAMME.** Ce test-ci manquait, et son
    //  absence a laisse passer un lien d'evitement qui ne sautait rien : mesure du
    //  23/08/2026, le focus partait sur `<body>` et le Tab suivant repartait du
    //  debut du document. Le `href` et l'`id` correspondaient pourtant -- le
    //  succes du test et la justesse du livrable etaient deux grandeurs
    //  differentes (§7.0, quatrieme proposition).
    //
    //  `-1` et non `0` : focusable par programme, hors de l'ordre de tabulation.
    expect(screen.getByRole('main').getAttribute('tabindex')).toBe('-1');
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

describe('le cadre porte la navigation et le titre — LOT 4, `T4`', () => {
  it('rend le menu principal quand une entite est resolue', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
    );
    monter('bordeaux');
    await waitFor(() =>
      expect(screen.getByRole('navigation', { name: 'Menu principal' })).toBeTruthy(),
    );
    //  **L'ORDRE DU DOM EST L'ORDRE VISUEL, ET IL Y A DEUX REPERES DEPUIS `T5`.**
    //  En-tete, menu du haut, contenu, barre du bas : c'est ce que l'oeil parcourt,
    //  donc ce que le Tab parcourt. La barre est en DERNIER parce qu'elle est
    //  ancree en bas de l'ecran.
    const reperes = [...document.querySelectorAll('header, nav, main')].map(
      (e) => e.tagName + (e.getAttribute('aria-label') ? `[${e.getAttribute('aria-label')}]` : ''),
    );
    expect(reperes).toEqual(['HEADER', 'NAV[Menu principal]', 'MAIN', 'NAV[Barre de navigation]']);
  });

  it("NE rend AUCUN menu quand l'entite est introuvable", async () => {
    //  **UN MENU SANS ENTITE POINTERAIT VERS `/entites/undefined/...`.** Pire
    //  qu'aucun menu : il donnerait six liens qui ne menent nulle part, tous
    //  atteignables au clavier, ce que le critere de `T4` interdit en substance.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'entite_introuvable' } }, 404))),
    );
    monter('inconnue');
    await waitFor(() => expect(screen.getByRole('heading', { name: /introuvable/ })).toBeTruthy());
    //  NI le menu du haut, NI la barre du bas : les deux ont besoin d'un code.
    expect(screen.queryByRole('navigation', { name: 'Menu principal' })).toBeNull();
    expect(screen.queryByRole('navigation', { name: 'Barre de navigation' })).toBeNull();
  });

  it('derive le titre de la page de `RUBRIQUES` — une source, pas deux', async () => {
    for (const rubrique of RUBRIQUES) {
      cleanup();
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
      );
      const chemin =
        rubrique.suffixe === '' ? '/entites/bordeaux' : `/entites/bordeaux/${rubrique.suffixe}`;
      monter('bordeaux', false, chemin);
      //  **CHAQUE rubrique, non la premiere.** Un test qui n'en verifierait qu'une
      //  passerait sur un titre constant, ce que `T3` avait justement.
      await waitFor(() =>
        expect(screen.getByRole('heading', { name: rubrique.titre })).toBeTruthy(),
      );
    }
  });

  it("le lien d'evitement precede le menu, donc il le saute", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
    );
    monter('bordeaux');
    await waitFor(() =>
      expect(screen.getByRole('navigation', { name: 'Menu principal' })).toBeTruthy(),
    );
    //  C'est le SENS du lien d'evitement : il doit venir avant ce qu'il saute.
    //  Pose en `T3`, il ne sautait que l'en-tete ; il saute desormais le menu.
    const evitement = screen.getByRole('link', { name: /Aller au contenu/ });
    const premierLienDuMenu = screen
      .getByRole('navigation', { name: 'Menu principal' })
      .querySelector('a');
    expect(premierLienDuMenu).toBeTruthy();
    expect(evitement.compareDocumentPosition(premierLienDuMenu!)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });
});
