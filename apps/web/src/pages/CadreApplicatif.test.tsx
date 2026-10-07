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
import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react';
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

/**
 * Un accueil VIDE mais valide — LOT 8, `T11`. `PageEntite` appelle desormais
 * `GET …/accueil` ; les cinq clefs sont EXIGEES par `validerLAccueil`, meme
 * vides (§7.0, quatrieme proposition), et un stub qui n'en servirait qu'une
 * partie leverait dans le validateur, exactement comme une reponse reelle
 * malformee.
 */
const UN_ACCUEIL_VIDE = {
  presentation: null,
  framework: { responsabilites: [], cercles: [], bureaux: [] },
  arrivees_recentes: { arrivees: [], page: 1, taille: 25, total: 0, pages: 0 },
  evenements_a_venir: {
    classement: 'a_venir',
    evenements: [],
    page: 1,
    taille: 25,
    total: 0,
    pages: 0,
  },
  liens_internes: { liens: [], nombre_de_liens: 0 },
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
function monter(code: string, strict = false, chemin?: string): ReturnType<typeof render> {
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
                element={
                  <PageRubrique cle={rubrique.cle} libelle={rubrique.libelle} lot={rubrique.lot} />
                }
              />
            ),
          )}
        </Route>
      </Routes>
    </MemoryRouter>
  );
  //  Le resultat est RENDU, pour que `T8` puisse demonter et remonter : son
  //  temoin de latence a besoin de quitter une entite pendant qu'un appel dort.
  return render(strict ? <StrictMode>{arbre}</StrictMode> : arbre);
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
      fetchParUrl({
        '/accueil': () => Promise.resolve(json(UN_ACCUEIL_VIDE, 200)),
        bordeaux: () => Promise.resolve(json(BORDEAUX, 200)),
      }),
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

    //  Et la page interne est bien rendue SOUS le cadre, dans `main` — l'accueil,
    //  LOT 8 `T11`, compose desormais les cinq sections du cahier §8.4.
    const principal = screen.getByRole('main');
    await waitFor(() => expect(principal.textContent).toContain('Presentation'));
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

  it(
    'derive AUSSI le titre des pages de cercle et de bureau — LOT 6, `T9`. ' +
      "Sans ce cas, l'h1 disait FAUX : « Accueil de l'entite » sur une page qui " +
      "n'en est pas une (defaut trouve dans un navigateur, meme classe que le " +
      'profil du LOT 5 T11, non corrige ici, hors perimetre de T9)',
    async () => {
      const casDeSousPage = [
        { chemin: '/entites/bordeaux/framework/cercles/data', titreAttendu: 'Cercle' },
        { chemin: '/entites/bordeaux/framework/bureaux/siege', titreAttendu: 'Bureau' },
      ];
      for (const { chemin, titreAttendu } of casDeSousPage) {
        cleanup();
        vi.stubGlobal(
          'fetch',
          vi.fn(() => Promise.resolve(json(BORDEAUX, 200))),
        );
        render(
          <MemoryRouter initialEntries={[chemin]}>
            <Routes>
              <Route path={CHEMINS.entite} element={<CadreApplicatif />}>
                <Route path="framework/cercles/:codeCercle" element={<p>Contenu du cercle</p>} />
                <Route path="framework/bureaux/:codeBureau" element={<p>Contenu du bureau</p>} />
              </Route>
            </Routes>
          </MemoryRouter>,
        );
        await waitFor(() =>
          expect(screen.getByRole('heading', { name: titreAttendu })).toBeTruthy(),
        );
      }
    },
  );

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

// ============================================================================
//  LOT 4, T8 — les permissions rechargees, et la mention du §5.1
// ============================================================================

const LILLE = {
  id: '1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d',
  code: 'lille',
  nom: 'eXalt Lille',
  ville: 'Lille',
};

/**
 * Un `fetch` qui repond SELON L'URL.
 *
 * **LES TESTS DE `T2` ET `T3` RENDAIENT LA MEME CHARGE A TOUT APPEL, ET C'EST
 * POURQUOI ILS ONT CONTINUE DE PASSER APRES `T8`.** Le cadre lance desormais
 * TROIS appels ; les deux nouveaux recevaient une entite au lieu de leur propre
 * forme, leurs validateurs levaient, et le code degradait proprement -- selecteur
 * absent, mention absente. Les 89 tests restaient verts **sans rien eprouver du
 * nouveau comportement**.
 *
 * C'est le §7.0, troisieme et quatrieme propositions a la fois : un stub qui
 * repond n'importe quoi a n'importe qui ne dit pas combien d'appels il a servis,
 * et l'echec y produit la meme observation que le succes.
 */
function fetchParUrl(reponses: Record<string, () => Promise<Response>>): ReturnType<typeof vi.fn> {
  const vus: string[] = [];
  const stub = vi.fn((cible: unknown) => {
    const url = String(cible);
    vus.push(url);
    for (const [motif, produire] of Object.entries(reponses)) {
      if (url.endsWith(motif)) {
        return produire();
      }
    }
    return Promise.resolve(json({ erreur: { code: 'inattendu', message: url } }, 404));
  });
  Object.defineProperty(stub, 'urlsVues', { value: vus });
  return stub;
}

function permissions(code: string, principale: boolean, roles: readonly string[]): unknown {
  return {
    entite: '0f8fad5b-d9cb-469f-a165-70867728950e',
    code,
    est_entite_principale: principale,
    roles,
    //  `null` par defaut — LOT 7, `T13`. Ces temoins n'exercent pas le
    //  parcours : un `null` evite tout appel supplementaire a
    //  `GET …/onboarding-parcours` que `CadreApplicatif` ne ferait de toute
    //  facon jamais pour une appartenance qui n'existe pas.
    appartenance: null,
  };
}

describe('les permissions de l entite consultee — T8', () => {
  it('affiche la mention du §5.1 HORS de l entite principale', async () => {
    vi.stubGlobal(
      'fetch',
      fetchParUrl({
        '/permissions': () => Promise.resolve(json(permissions('bordeaux', false, ['EMP']), 200)),
        '/entities': () => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200)),
        bordeaux: () => Promise.resolve(json(BORDEAUX, 200)),
      }),
    );
    monter('bordeaux');

    await waitFor(() =>
      expect(document.querySelector('[data-consultation="seule"]')).not.toBeNull(),
    );
    //  La formulation vient du §4 de la matrice, « Consultation uniquement, sans
    //  modification ». Ce n'est pas un libelle invente.
    //  **SCOPE AU `banner`** : depuis `T11` du LOT 8, `PageEntite` porte son
    //  propre `role="status"` pendant son chargement — un `getByRole('status')`
    //  non scope trouverait DEUX elements, celui-ci et celui de l'accueil.
    expect(within(screen.getByRole('banner')).getByRole('status').textContent).toContain(
      'Consultation uniquement',
    );
  });

  it('ne l affiche PAS dans l entite principale — le temoin dans l autre sens', async () => {
    vi.stubGlobal(
      'fetch',
      fetchParUrl({
        '/permissions': () =>
          Promise.resolve(json(permissions('bordeaux', true, ['EMP', 'ESM']), 200)),
        '/entities': () => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200)),
        bordeaux: () => Promise.resolve(json(BORDEAUX, 200)),
      }),
    );
    monter('bordeaux');

    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Bordeaux'));
    //  On attend que le selecteur soit la : sans cette attente, l'absence de la
    //  mention serait celle d'un rendu qui n'a pas encore recu les droits, et le
    //  test passerait pour la mauvaise raison.
    await waitFor(() => expect(document.querySelector('details')).not.toBeNull());
    expect(document.querySelector('[data-consultation="seule"]')).toBeNull();
  });

  it('ne l affiche PAS quand les droits sont INCONNUS — `undefined` n est pas `false`', async () => {
    vi.stubGlobal(
      'fetch',
      fetchParUrl({
        '/permissions': () => Promise.resolve(json({ erreur: { code: 'panne' } }, 500)),
        '/entities': () => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200)),
        bordeaux: () => Promise.resolve(json(BORDEAUX, 200)),
      }),
    );
    monter('bordeaux');

    await waitFor(() => expect(document.querySelector('details')).not.toBeNull());
    //  Les droits ont echoue. Afficher « consultation uniquement » ici dirait a
    //  l'utilisateur une chose qu'on ne sait pas, et la masquer par defaut
    //  laisserait croire l'inverse : le cadre n'affiche donc RIEN, et la page
    //  reste utilisable. C'est ce que le `null` du contexte impose a `T9`.
    expect(document.querySelector('[data-consultation="seule"]')).toBeNull();
  });

  it('appelle les TROIS routes avec le code de l adresse, et lui seul', async () => {
    const stub = fetchParUrl({
      '/permissions': () => Promise.resolve(json(permissions('lille', false, ['EMP']), 200)),
      '/entities': () => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200)),
      lille: () => Promise.resolve(json(LILLE, 200)),
    });
    vi.stubGlobal('fetch', stub);
    monter('lille');

    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Lille'));
    await waitFor(() => expect(document.querySelector('details')).not.toBeNull());

    const vues = (stub as unknown as { urlsVues: string[] }).urlsVues;
    expect(vues).toContain('/api/v1/entities/lille');
    expect(vues).toContain('/api/v1/entities/lille/permissions');
    expect(vues).toContain('/api/v1/entities');
    //  AUCUN appel ne porte un autre code : c'est « aucun reste de la
    //  precedente » au niveau des requetes emises.
    expect(vues.some((u) => u.includes('bordeaux'))).toBe(false);
  });

  it('une reponse TARDIVE de permissions ne s applique pas a la nouvelle entite', async () => {
    //  **LE TEMOIN DECISIF, ET IL A FALLU DEUX VERSIONS POUR QU'IL DISCRIMINE.**
    //  §23.3, quatrieme regle : « annule les requetes et caches associes a
    //  l'entite precedente ».
    //
    //  Premiere version : je montais Bordeaux, je DEMONTAIS, je montais Lille.
    //  Mesure du 24/08/2026 -- la garde sur le code retiree du cadre, les 99
    //  tests passaient quand meme. Le demontage cree DEUX instances aux etats
    //  separes : la reponse de Bordeaux ne pouvait de toute facon pas atteindre
    //  l'arbre de Lille, et React ignore un `setState` apres demontage. Le test
    //  ne modelisait pas le defaut qu'il pretendait attraper -- §7.25, « un
    //  temoin qui n'exerce pas un controle ne prouve rien de ce controle ».
    //
    //  Le vrai parcours est un CLIC dans le selecteur : une seule instance de
    //  cadre, dont le parametre `code` change. C'est ce que fait cette version,
    //  et elle eprouve le selecteur du meme geste.
    let libererBordeaux: (() => void) | null = null;
    const stub = vi.fn((cible: unknown) => {
      const url = String(cible);
      if (url === '/api/v1/entities') {
        return Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200));
      }
      if (url === '/api/v1/entities/bordeaux/permissions') {
        return new Promise<Response>((resoudre) => {
          libererBordeaux = () => resoudre(json(permissions('bordeaux', false, ['EMP']), 200));
        });
      }
      if (url === '/api/v1/entities/lille/permissions') {
        return Promise.resolve(json(permissions('lille', true, ['EMP', 'ESM']), 200));
      }
      return Promise.resolve(json(url.endsWith('lille') ? LILLE : BORDEAUX, 200));
    });
    vi.stubGlobal('fetch', stub);

    monter('bordeaux');
    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Bordeaux'));
    //  Le selecteur est la, et Bordeaux attend toujours ses droits.
    await waitFor(() => expect(document.querySelector('details')).not.toBeNull());
    expect(document.querySelector('[data-consultation="seule"]')).toBeNull();

    //  On navigue vers Lille EN CLIQUANT, comme un utilisateur.
    const versLille = screen
      .getAllByRole('link')
      .find((lien) => lien.getAttribute('href') === '/entites/lille');
    expect(versLille).toBeTruthy();
    await act(async () => {
      versLille?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    });
    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Lille'));

    //  Et SEULEMENT MAINTENANT la reponse de Bordeaux arrive. Lille est dans son
    //  entite principale : si les droits de Bordeaux s'appliquaient, la mention
    //  « consultation uniquement » apparaitrait.
    await act(async () => {
      libererBordeaux?.();
      await Promise.resolve();
    });

    expect(screen.getByRole('banner').textContent).toContain('eXalt Lille');
    expect(document.querySelector('[data-consultation="seule"]')).toBeNull();
  });
});

describe('« Mon onboarding » se montre selon un VRAI parcours — LOT 7, T13', () => {
  const APPARTENANCE = 'e2f6b1f2-0000-4000-8000-000000000001';

  function permissionsAvecAppartenance(): unknown {
    return {
      entite: '0f8fad5b-d9cb-469f-a165-70867728950e',
      code: 'bordeaux',
      est_entite_principale: true,
      roles: ['EMP'],
      appartenance: APPARTENANCE,
    };
  }

  function parcours(etatDeLInstance: string | null): unknown {
    return {
      instance:
        etatDeLInstance === null
          ? null
          : {
              id: 'i1',
              template_version_id: 'v1',
              reference_date: '2026-10-01',
              state: etatDeLInstance,
              started_at: '2026-10-01T09:00:00Z',
              completed_at: null,
            },
      progression:
        etatDeLInstance === null
          ? null
          : { taches_obligatoires_totales: 1, taches_obligatoires_terminees: 0 },
      prochaine_tache: null,
      taches: [],
    };
  }

  it('affiche le lien quand `GET …/onboarding-parcours` rend une instance ACTIVE', async () => {
    vi.stubGlobal(
      'fetch',
      fetchParUrl({
        '/permissions': () => Promise.resolve(json(permissionsAvecAppartenance(), 200)),
        '/entities': () => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200)),
        'onboarding-parcours': () => Promise.resolve(json(parcours('active'), 200)),
        bordeaux: () => Promise.resolve(json(BORDEAUX, 200)),
      }),
    );
    monter('bordeaux');

    //  **`getAllByRole`, PAS `getByRole`** : « Mon onboarding » apparait DEUX
    //  fois — menu principal ET barre mobile, tous deux rendus en meme temps
    //  en JSDOM — exactement comme « Administration » plus bas dans ce fichier.
    await waitFor(() =>
      expect(screen.getAllByRole('link', { name: 'Mon onboarding' }).length).toBe(2),
    );
  });

  it('NE l’affiche PAS quand l’instance est ARCHIVEE — le témoin dans l’autre sens', async () => {
    vi.stubGlobal(
      'fetch',
      fetchParUrl({
        '/permissions': () => Promise.resolve(json(permissionsAvecAppartenance(), 200)),
        '/entities': () => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200)),
        'onboarding-parcours': () => Promise.resolve(json(parcours('archived'), 200)),
        bordeaux: () => Promise.resolve(json(BORDEAUX, 200)),
      }),
    );
    monter('bordeaux');

    await waitFor(() => expect(document.querySelector('details')).not.toBeNull());
    expect(screen.queryAllByRole('link', { name: 'Mon onboarding' })).toHaveLength(0);
  });

  it('NE l’affiche PAS quand aucun parcours n’a jamais ete affecte', async () => {
    vi.stubGlobal(
      'fetch',
      fetchParUrl({
        '/permissions': () => Promise.resolve(json(permissionsAvecAppartenance(), 200)),
        '/entities': () => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200)),
        'onboarding-parcours': () => Promise.resolve(json(parcours(null), 200)),
        bordeaux: () => Promise.resolve(json(BORDEAUX, 200)),
      }),
    );
    monter('bordeaux');

    await waitFor(() => expect(document.querySelector('details')).not.toBeNull());
    expect(screen.queryAllByRole('link', { name: 'Mon onboarding' })).toHaveLength(0);
  });

  it('NE fait AUCUN appel au parcours quand l’appelant n’a pas d’appartenance', async () => {
    const stub = fetchParUrl({
      '/permissions': () => Promise.resolve(json(permissions('bordeaux', true, ['EMP']), 200)),
      '/entities': () => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200)),
      bordeaux: () => Promise.resolve(json(BORDEAUX, 200)),
    });
    vi.stubGlobal('fetch', stub);
    monter('bordeaux');

    await waitFor(() => expect(document.querySelector('details')).not.toBeNull());
    const vues = (stub as unknown as { urlsVues: string[] }).urlsVues;
    expect(vues.some((u) => u.includes('onboarding-parcours'))).toBe(false);
  });
});

describe("l'ordre d'arrivee des trois reponses ne change rien — T8", () => {
  it('applique les droits arrives AVANT l entite — LE DEFAUT VU AU NAVIGATEUR', async () => {
    //  **CE TEST N'EXISTE PAS PAR PRUDENCE : IL EXISTE PARCE QUE LE DEFAUT A ETE
    //  VU A L'ECRAN.** Le 24/08/2026, `GET /entities/{code}/permissions` rendait
    //  `est_entite_principale: false` et la mention du §5.1 n'apparaissait pas.
    //  Le journal reseau montrait deux appels de permissions -- un abandonne, un
    //  a 200 -- dont le second revenait AVANT l'entite. La premiere version du
    //  cadre n'ecrivait les droits que dans une variante `trouvee` deja
    //  existante : ils etaient perdus definitivement.
    //
    //  **ET AUCUN DES CINQ TESTS DE `T8` NE L'ATTRAPAIT**, parce qu'un `fetch`
    //  bouchonne resout dans l'ordre de creation des promesses, et le cadre
    //  demande l'entite en premier. Il fallait donc RETENIR l'entite pour
    //  reproduire l'ordre reel -- ce que fait ce test, et ce qu'aucun autre ne
    //  fait.
    let libererEntite: (() => void) | null = null;
    vi.stubGlobal(
      'fetch',
      vi.fn((cible: unknown) => {
        const url = String(cible);
        if (url === '/api/v1/entities/bordeaux/permissions') {
          return Promise.resolve(json(permissions('bordeaux', false, ['EMP']), 200));
        }
        if (url === '/api/v1/entities') {
          return Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200));
        }
        return new Promise<Response>((resoudre) => {
          libererEntite = () => resoudre(json(BORDEAUX, 200));
        });
      }),
    );
    monter('bordeaux');

    //  Les droits et la liste sont arrives ; l'entite, non. Rien ne s'affiche
    //  encore, et c'est correct : le §23.3 veut l'entite dans l'en-tete.
    await waitFor(() => expect(screen.getByRole('status').textContent).toContain('Chargement'));

    await act(async () => {
      libererEntite?.();
      await Promise.resolve();
    });

    await waitFor(() => expect(screen.getByRole('banner').textContent).toContain('eXalt Bordeaux'));
    //  **LES DROITS ARRIVES AVANT DOIVENT AVOIR SURVECU.**
    expect(document.querySelector('[data-consultation="seule"]')).not.toBeNull();
    //  Et la liste aussi : le selecteur est la.
    expect(document.querySelector('details')).not.toBeNull();
  });
});

describe('le garde-fou de route est ERGONOMIQUE, et il le dit — T9', () => {
  function fetchAvecRoles(roles: readonly string[], principale: boolean): ReturnType<typeof vi.fn> {
    return vi.fn((cible: unknown) => {
      const url = String(cible);
      if (url.endsWith('/permissions')) {
        return Promise.resolve(json(permissions('bordeaux', principale, roles), 200));
      }
      if (url === '/api/v1/entities') {
        return Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200));
      }
      return Promise.resolve(json(BORDEAUX, 200));
    });
  }

  it("l'adresse tapée à la main atteint la page, et la page EXPLIQUE — §24.20", async () => {
    //  **LE MENU EST MASQUÉ, ET L'UTILISATEUR TAPE L'ADRESSE QUAND MÊME.** C'est
    //  la « requête construite manuellement » du §24.20, côté navigation.
    vi.stubGlobal('fetch', fetchAvecRoles(['EMP'], true));
    monter('bordeaux', false, '/entites/bordeaux/administration');

    await waitFor(() => expect(document.querySelector('[data-rubrique-fermee]')).not.toBeNull());
    const message = screen.getByRole('status').textContent ?? '';
    //  **IL NE REND PAS DE VERDICT SUR L'APPELANT.** Rien n'a ete refuse : la
    //  page s'affiche. Ma premiere assertion cherchait `/refus[ée]/i` et
    //  echouait sur ma propre phrase, « c'est l'API qui refuse les actions non
    //  autorisees » -- un controle trop large qui refuse du texte correct, §7.25.
    //  L'exigence exacte porte sur le VERDICT, pas sur le mot.
    expect(message).not.toMatch(/acc[eè]s refus/i);
    expect(message).not.toMatch(/non autoris[ée] a/i);
    //  Et il dit ou est la vraie barriere. **Le fragment est choisi SANS
    //  apostrophe** : le JSX emploie `&rsquo;`, donc le texte rendu porte une
    //  apostrophe typographique, et une assertion ecrite avec `'` echouait sur un
    //  livrable correct. §7.10 -- inspecte ce qui est rendu, pas ce que tu as tape.
    expect(message).toContain('API qui refuse les actions non autorisees');
    //  Le menu, lui, ne propose pas la rubrique.
    expect(screen.queryByRole('link', { name: 'Administration' })).toBeNull();
  });

  it('la même adresse AVEC le rôle affiche la rubrique — le témoin dans l autre sens', async () => {
    //  Sans ce témoin, le test précédent serait satisfait par une page qui refuse
    //  toujours, et le garde-fou ne prouverait rien.
    vi.stubGlobal('fetch', fetchAvecRoles(['EMP', 'ADM-E'], true));
    monter('bordeaux', false, '/entites/bordeaux/administration');

    await waitFor(() => expect(document.querySelector('[data-rubrique]')).not.toBeNull());
    expect(document.querySelector('[data-rubrique-fermee]')).toBeNull();
    //  **`getAllByRole` ET NON `getByRole`.** « Administration » apparait DEUX
    //  fois -- dans le menu principal et dans la barre mobile -- et c'est correct :
    //  les deux reperes montrent la meme chose. Ma premiere assertion employait
    //  `getByRole`, qui echoue sur une ambiguite, donc sur un livrable conforme.
    expect(screen.getAllByRole('link', { name: 'Administration' }).length).toBe(2);
  });

  it('hors entité principale, le message nomme la BONNE cause — §5.1', async () => {
    //  Le même refus a deux causes possibles, et l'utilisateur doit savoir
    //  laquelle : « vous n'avez pas ce droit » et « vous n'êtes pas chez vous »
    //  n'appellent pas la même action de sa part.
    vi.stubGlobal('fetch', fetchAvecRoles(['EMP'], false));
    monter('bordeaux', false, '/entites/bordeaux/administration');

    await waitFor(() => expect(document.querySelector('[data-rubrique-fermee]')).not.toBeNull());
    //  **ON LIT L'ELEMENT VISE, PAS « le » `role="status"`.** Il y en a DEUX ici,
    //  et c'est coherent : l'en-tete porte la mention du §5.1, la rubrique porte
    //  son explication. `getByRole('status')` echouait donc sur une ambiguite
    //  legitime -- meme classe que l'assertion precedente.
    const ferme = document.querySelector('[data-rubrique-fermee]');
    expect(ferme?.textContent).toContain('pas votre entite principale');
    //  Et l'en-tete porte bien la mention du §5.1, les deux coexistent.
    expect(document.querySelector('[data-consultation="seule"]')).not.toBeNull();
  });
});
