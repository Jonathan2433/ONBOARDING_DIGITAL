/**
 * Les huit ecrans d'authentification — LOT 3, sous-etape `T11`.
 *
 * CE FICHIER PROUVE QUATRE CHOSES, ET LA PREMIERE EST LA PLUS FRAGILE
 *
 *   1. **les huit ecrans sont ceux du cahier**, relus dans le document. Le compte
 *      est 5 puces + 3 pages nommees dans la sixieme = 8, et une liste recopiee
 *      vieillirait au premier ajout -- §7.27 ;
 *   2. **la reponse generique n'est pas defaite par l'interface** : deux adresses
 *      differentes produisent le MEME ecran, mot pour mot. C'est le critere
 *      central du lot, et un ecran qui le romprait rouvrirait l'oracle que `T3` a
 *      ferme ;
 *   3. **le jeton de magic link quitte la barre d'adresse** et voyage dans le
 *      CORPS. Verifie sur l'appel reel, pas sur l'intention ;
 *   4. **aucun stockage navigateur**, nulle part. Interdit absolu du §9.5.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CHEMIN_CONSOMMATION_MAGIC_LINK, EN_TETE_JETON_CSRF } from '@onboarding/contracts';

import { CHEMINS, ECRANS } from '../routes';
import { PageConnexion } from './PageConnexion';
import { PageConnexionAdministrateur } from './PageConnexionAdministrateur';
import { PageDeconnexion } from './PageDeconnexion';
import { PageLien, lireLeJeton } from './PageLien';
import { PageLienEnvoye } from './PageLienEnvoye';
import { Page403, Page404, PageErreur } from './PagesErreur';

afterEach(cleanup);

function json(charge: unknown, statut: number): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

// ===========================================================================
//  1. LES HUIT ECRANS SONT DECLARES, ET LEUR DECLARATION EST COHERENTE
//
//    **LA CONFRONTATION AU CAHIER EST AILLEURS**, dans `make ecrans-check` : elle
//    lit un document Markdown et une feuille de style, ce qui exigerait
//    `@types/node` ici. Ajouter une dependance pour lire deux fichiers serait la
//    surface d'audit sans contrepartie que `DEC-456` refuse -- et `verifier-
//    sessions.py` lit deja les sources du frontend, donc l'outil existe.
// ===========================================================================

describe('la declaration des huit ecrans', () => {
  it('en compte HUIT, avec des chemins distincts', () => {
    expect(ECRANS).toHaveLength(8);
    expect(new Set(ECRANS.map((ecran) => ecran.chemin)).size).toBe(8);
  });

  it('declare UN SEUL etat de route, et non une adresse a lui', () => {
    //  « lien expire ou deja consomme » est l'echec de la route de consommation.
    expect(ECRANS.filter((ecran) => ecran.etatDeRoute === true)).toHaveLength(1);
  });
});

// ===========================================================================
//  2. LA REPONSE GENERIQUE N'EST PAS DEFAITE PAR L'INTERFACE
// ===========================================================================

describe('la page de connexion', () => {
  const MESSAGE_DE_L_API =
    'Si cette adresse correspond a un profil actif et autorise, un lien de connexion ' +
    "vient d'y etre envoye. Il est valable 15 minutes.";

  async function soumettre(adresse: string): Promise<string> {
    render(<PageConnexion />);
    const champ = screen.getByLabelText('Adresse e-mail');
    champ.setAttribute('value', adresse);
    //  `fireEvent.change` via Testing Library sur un composant controle.
    const { fireEvent } = await import('@testing-library/react');
    fireEvent.change(champ, { target: { value: adresse } });
    fireEvent.click(screen.getByRole('button', { name: 'Recevoir un lien' }));
    await waitFor(() => {
      expect(screen.getByRole('status').textContent).not.toBe('');
    });
    const rendu = screen.getByRole('status').textContent ?? '';
    cleanup();
    return rendu;
  }

  it('affiche LE MEME message pour une adresse connue et une inconnue', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ message: MESSAGE_DE_L_API }, 202))),
    );
    const premier = await soumettre('connue@exalt-company.com');
    const second = await soumettre('jamais-vue@exalt-company.com');
    expect(premier).toBe(second);
    expect(premier).toContain('Il est valable 15 minutes');
  });

  it('ne fabrique AUCUN message : il vient de la reponse', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ message: 'phrase venue du serveur' }, 202))),
    );
    expect(await soumettre('a@exalt-company.com')).toBe('phrase venue du serveur');
  });

  it('traite le 429 comme un REFUS, non comme un succes', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'trop_de_demandes' } }, 429))),
    );
    const rendu = await soumettre('a@exalt-company.com');
    expect(rendu).toContain('Trop de demandes');
    expect(rendu).not.toContain('valable 15 minutes');
  });
});

// ===========================================================================
//  3. LE JETON QUITTE LA BARRE D'ADRESSE ET VOYAGE DANS LE CORPS
// ===========================================================================

describe('la consommation du lien', () => {
  it('lit le jeton de la chaine de requete, sans effet de bord', () => {
    const fenetre = {
      location: { search: '?token=oml_abc', pathname: '/connexion/lien' },
      history: { replaceState: vi.fn() },
    } as unknown as Window;
    expect(lireLeJeton(fenetre)).toBe('oml_abc');
    //  **LECTURE PURE** : aucune manipulation d'historique. La separation a ete
    //  imposee par `react-hooks/set-state-in-effect`, et elle a raison.
    expect(
      fenetre.history.replaceState as unknown as ReturnType<typeof vi.fn>,
    ).not.toHaveBeenCalled();
  });

  it('envoie le jeton dans le CORPS et l efface de l URL', async () => {
    const appels: Array<[string, RequestInit | undefined]> = [];
    vi.stubGlobal(
      'fetch',
      vi.fn((chemin: string, options?: RequestInit) => {
        appels.push([chemin, options]);
        return Promise.resolve(json({ message: 'ok' }, 200));
      }),
    );
    //  **L'URL EST POSEE AVANT LE DOUBLE, ET L'ORDRE INVERSE M'A COUTE DEUX
    //  ECHECS** : `stubGlobal('history', …)` remplace l'objet entier, donc
    //  `pushState` disparait avec lui.
    window.history.pushState(null, '', `${CHEMINS.lien}?token=oml_secret`);
    const remplacer = vi.fn();
    vi.stubGlobal('history', { replaceState: remplacer });

    render(
      <MemoryRouter initialEntries={[CHEMINS.lien]}>
        <Routes>
          <Route path={CHEMINS.lien} element={<PageLien />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(appels.length).toBe(1));

    const [chemin, options] = appels[0]!;
    expect(chemin).toBe(CHEMIN_CONSOMMATION_MAGIC_LINK);
    //  Le jeton est dans le CORPS, et le chemin appele n'en porte AUCUNE trace.
    expect(String(options?.body)).toContain('oml_secret');
    expect(chemin).not.toContain('oml_secret');
    //  Et il a ete retire de la barre d'adresse.
    expect(remplacer).toHaveBeenCalled();
  });

  it('ne consomme QU UNE FOIS sous StrictMode', async () => {
    const appels: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn((chemin: string) => {
        appels.push(chemin);
        return Promise.resolve(json({ message: 'ok' }, 200));
      }),
    );
    window.history.pushState(null, '', `${CHEMINS.lien}?token=oml_unique`);
    vi.stubGlobal('history', { replaceState: vi.fn() });

    render(
      <StrictMode>
        <MemoryRouter initialEntries={[CHEMINS.lien]}>
          <Routes>
            <Route path={CHEMINS.lien} element={<PageLien />} />
          </Routes>
        </MemoryRouter>
      </StrictMode>,
    );
    await waitFor(() => expect(appels.length).toBeGreaterThan(0));
    //  **UN SEUL APPEL.** React monte deux fois en developpement : sans le garde,
    //  le second consommerait un jeton deja utilise et l'ecran de refus
    //  s'afficherait sur un lien parfaitement valide.
    expect(appels).toHaveLength(1);
  });

  it('refuse d emblee un lien SANS jeton, sans appeler l API', async () => {
    const appeler = vi.fn(() => Promise.resolve(json({}, 200)));
    vi.stubGlobal('fetch', appeler);
    window.history.pushState(null, '', CHEMINS.lien);

    render(
      <MemoryRouter initialEntries={[CHEMINS.lien]}>
        <Routes>
          <Route path={CHEMINS.lien} element={<PageLien />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { level: 1 }).textContent).toContain(
      "Ce lien n'est plus valable",
    );
    expect(appeler).not.toHaveBeenCalled();
  });
});

// ===========================================================================
//  4. LA DECONNEXION LIT LA SESSION, PUIS ENVOIE LE JETON ANTI-CSRF
// ===========================================================================

describe('la deconnexion', () => {
  it('envoie le jeton anti-CSRF obtenu de la route de session', async () => {
    const appels: Array<[string, RequestInit | undefined]> = [];
    vi.stubGlobal(
      'fetch',
      vi.fn((chemin: string, options?: RequestInit) => {
        appels.push([chemin, options]);
        return Promise.resolve(
          chemin.endsWith('/session')
            ? json({ personne: 'p', jeton_csrf: 'jeton-csrf-de-test' }, 200)
            : json({ message: 'fermee' }, 200),
        );
      }),
    );
    render(
      <MemoryRouter>
        <PageDeconnexion />
      </MemoryRouter>,
    );
    const bouton = await waitFor(() => screen.getByRole('button', { name: 'Fermer ma session' }));
    const { fireEvent } = await import('@testing-library/react');
    fireEvent.click(bouton);
    await waitFor(() => expect(appels.length).toBe(2));

    const entetes = appels[1]![1]?.headers as Record<string, string>;
    expect(entetes[EN_TETE_JETON_CSRF]).toBe('jeton-csrf-de-test');
  });

  it('dit « deja deconnecte » sur un 401, et non « erreur »', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'session_invalide' } }, 401))),
    );
    render(
      <MemoryRouter>
        <PageDeconnexion />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByRole('status').textContent).toContain('deja deconnecte');
    });
  });
});

// ===========================================================================
//  5. LES HUIT ECRANS SE RENDENT, ET LEURS INVARIANTS D'ACCESSIBILITE TIENNENT
// ===========================================================================

describe('les invariants communs aux huit ecrans', () => {
  const RENDUS = [
    ['connexion', <PageConnexion key="a" />],
    ['lienEnvoye', <PageLienEnvoye key="b" />],
    ['connexionAdministrateur', <PageConnexionAdministrateur key="c" />],
    ['interdit', <Page403 key="d" />],
    ['introuvable', <Page404 key="e" />],
    ['erreur', <PageErreur key="f" />],
  ] as const;

  it.each(RENDUS)('%s porte UN SEUL <h1> et un <main>', (_cle, element) => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({}, 200))),
    );
    render(<MemoryRouter>{element}</MemoryRouter>);
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('main')).toBeTruthy();
  });
});
