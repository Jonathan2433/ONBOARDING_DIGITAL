/**
 * Tests de la page de statut.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002.
 *
 * FONDEMENT — fiche du LOT 1 §6 : « Vitest et Testing Library sur la page de
 * statut ; etat de chargement, etat d'erreur, etat hors connexion ». Les trois
 * y sont, plus l'etat nominal et l'etat DEGRADE — un 503 n'est pas une erreur,
 * et une page qui confondrait les deux jetterait le diagnostic.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { CHEMIN_READY, CHEMIN_VERSION, EN_TETE_CORRELATION } from '../api/sante';
import { PageStatut } from './PageStatut';

const CORRELATION = '6a66ca32-40be-4717-83ff-7f8942ea1f8b';

const READY_NOMINAL = {
  statut: 'pret',
  dependances: [
    { nom: 'postgresql', statut: 'disponible', duree_ms: 0, motif: null },
    { nom: 'redis', statut: 'disponible', duree_ms: 2, motif: null },
    { nom: 'minio', statut: 'disponible', duree_ms: 7, motif: null },
  ],
};

const READY_DEGRADE = {
  statut: 'indisponible',
  dependances: [
    { nom: 'postgresql', statut: 'disponible', duree_ms: 1, motif: null },
    { nom: 'redis', statut: 'indisponible', duree_ms: 3, motif: 'ConnectionError' },
    { nom: 'minio', statut: 'disponible', duree_ms: 5, motif: null },
  ],
};

const VERSION_REELLE = {
  version: '0.0.0-dev',
  revision: 'inconnue',
  environnement: 'development',
};

type Fabrique = () => Response | Promise<Response>;

function json(charge: unknown, statut: number): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: {
      'Content-Type': 'application/json',
      [EN_TETE_CORRELATION]: CORRELATION,
    },
  });
}

/**
 * Brancher un faux `fetch` par chemin.
 *
 * Les reponses sont fabriquees a CHAQUE appel : un objet `Response` ne se
 * consomme qu'une fois, et les tests de nouvelle tentative en demandent deux.
 * Un chemin non branche leve, pour qu'une faute de chemin echoue au lieu de
 * passer inapercue.
 */
function brancherApi(ready: Fabrique, version: Fabrique): { readonly appels: string[] } {
  const appels: string[] = [];
  const faux = vi.fn(async (entree: unknown): Promise<Response> => {
    const chemin = String(entree);
    appels.push(chemin);
    if (chemin === CHEMIN_READY) {
      return await ready();
    }
    if (chemin === CHEMIN_VERSION) {
      return await version();
    }
    throw new Error(`chemin non branche : ${chemin}`);
  });
  vi.stubGlobal('fetch', faux);
  return { appels };
}

function definirConnexion(enLigne: boolean): void {
  Object.defineProperty(window.navigator, 'onLine', {
    configurable: true,
    get: () => enLigne,
  });
}

const NOMINAL: Fabrique = () => json(READY_NOMINAL, 200);
const VERSION: Fabrique = () => json(VERSION_REELLE, 200);
const JAMAIS: Fabrique = () => new Promise<Response>(() => undefined);

/**
 * Attendre l'etat charge, puis rendre sa banniere.
 *
 * Ne JAMAIS attendre sur `findByRole('status')` : la banniere de chargement
 * porte elle aussi `role="status"`, donc la recherche aboutit immediatement et
 * n'attend rien du tout. Le tableau des dependances, lui, n'existe que dans
 * l'etat charge — c'est sur lui qu'il faut attendre.
 */
async function attendreEtatCharge(): Promise<HTMLElement> {
  await screen.findByRole('table');
  return screen.getByRole('status');
}

afterEach(() => {
  cleanup();
  definirConnexion(true);
  vi.unstubAllGlobals();
});

describe('etat de chargement', () => {
  it('annonce l’interrogation avant toute reponse', () => {
    brancherApi(JAMAIS, JAMAIS);

    render(<PageStatut />);

    expect(screen.getByRole('status').textContent).toContain('Interrogation de l’API');
    // `aria-busy` permet a un lecteur d'ecran de ne pas annoncer un contenu
    // encore instable (cahier §14.2).
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
  });
});

describe('etat nominal', () => {
  it('affiche les trois dependances sondees et la version du build', async () => {
    brancherApi(NOMINAL, VERSION);

    render(<PageStatut />);

    const banniere = await attendreEtatCharge();
    expect(banniere.textContent).toContain('Plateforme prête');

    const tableau = screen.getByRole('table');
    for (const nom of ['postgresql', 'redis', 'minio']) {
      expect(tableau.textContent).toContain(nom);
    }
    // Trois lignes de donnees, plus la ligne d'en-tete.
    expect(screen.getAllByRole('row')).toHaveLength(4);

    expect(screen.getByText('0.0.0-dev')).toBeDefined();
    expect(screen.getByText('inconnue')).toBeDefined();
    expect(screen.getByText('development')).toBeDefined();
  });

  it('nomme les services que l’API ne sonde pas', async () => {
    brancherApi(NOMINAL, VERSION);

    render(<PageStatut />);
    await screen.findByRole('table');

    const texte = document.body.textContent ?? '';
    for (const absent of ['worker Dramatiq', 'Mailpit', 'Caddy']) {
      expect(texte).toContain(absent);
    }
    // L'enumeration ouvre une phrase : elle doit donc commencer par une
    // majuscule. Ce test manquait en `T5`, et le defaut n'a ete vu qu'en lisant
    // la page rendue dans un navigateur : `toContain` est insensible a la
    // casse initiale de la phrase qui porte le mot cherche.
    expect(texte).toContain('Le worker Dramatiq, Mailpit et Caddy ne sont pas sondés');
    expect(texte).not.toContain('. le worker Dramatiq');
  });
});

describe('etat degrade', () => {
  // Le 503 est la reponse reelle de l'API quand Redis est arrete. La page doit
  // montrer QUELLE dependance manque et POURQUOI, pas un message generique.
  it('affiche la dependance en defaut et son motif sur un 503', async () => {
    brancherApi(() => json(READY_DEGRADE, 503), VERSION);

    render(<PageStatut />);

    const banniere = await attendreEtatCharge();
    expect(banniere.textContent).toContain('Plateforme dégradée');

    const tableau = screen.getByRole('table');
    expect(tableau.textContent).toContain('ConnectionError');
    expect(tableau.textContent).toContain('indisponible');
    // Temoin : les dependances saines restent affichees dans le meme 503.
    expect(tableau.textContent).toContain('disponible');
    // La version reste lisible : elle ne depend pas de `ready`.
    expect(screen.getByText('0.0.0-dev')).toBeDefined();
  });
});

describe('etat d’erreur', () => {
  it('signale l’echec et propose de reessayer', async () => {
    brancherApi(() => {
      throw new TypeError('Failed to fetch');
    }, VERSION);

    render(<PageStatut />);

    const alerte = await screen.findByRole('alert');
    expect(alerte.textContent).toContain('n’a pas pu être lu');
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeDefined();
  });

  it('recharge reellement l’etat quand on reessaie', async () => {
    let appel = 0;
    const { appels } = brancherApi(() => {
      appel += 1;
      if (appel === 1) {
        throw new TypeError('Failed to fetch');
      }
      return json(READY_NOMINAL, 200);
    }, VERSION);

    render(<PageStatut />);
    fireEvent.click(await screen.findByRole('button', { name: 'Réessayer' }));

    const banniere = await attendreEtatCharge();
    expect(banniere.textContent).toContain('Plateforme prête');
    // Le compte d'appels prouve qu'une seconde interrogation a bien eu lieu :
    // un bouton qui ne relance rien afficherait le meme ecran sans le dire.
    expect(appels.filter((c) => c === CHEMIN_READY)).toHaveLength(2);
  });
});

describe('etat hors connexion', () => {
  it('affiche un etat explicite et n’interroge pas l’API', () => {
    definirConnexion(false);
    const { appels } = brancherApi(NOMINAL, VERSION);

    render(<PageStatut />);

    expect(screen.getByRole('status').textContent).toContain('hors connexion');
    expect(appels).toHaveLength(0);
  });

  it('reprend l’interrogation au retour du reseau', async () => {
    definirConnexion(false);
    brancherApi(NOMINAL, VERSION);

    render(<PageStatut />);
    expect(screen.getByRole('status').textContent).toContain('hors connexion');

    definirConnexion(true);
    fireEvent(window, new Event('online'));

    const banniere = await attendreEtatCharge();
    expect(banniere.textContent).toContain('Plateforme prête');
  });
});

describe('identifiant de correlation', () => {
  it('l’affiche et le copie dans le presse-papiers', async () => {
    brancherApi(NOMINAL, VERSION);
    const writeText = vi.fn<(texte: string) => Promise<void>>().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    render(<PageStatut />);
    await screen.findByRole('table');

    expect(screen.getByText(CORRELATION)).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'Copier' }));

    expect(writeText).toHaveBeenCalledWith(CORRELATION);
    expect(await screen.findByText(/copié dans le presse-papiers/)).toBeDefined();
  });

  it('reste utilisable quand le presse-papiers est refuse', async () => {
    brancherApi(NOMINAL, VERSION);
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: vi.fn<(texte: string) => Promise<void>>().mockRejectedValue(new Error('refuse')),
      },
    });

    render(<PageStatut />);
    await screen.findByRole('table');
    fireEvent.click(screen.getByRole('button', { name: 'Copier' }));

    // L'identifiant reste affiche et selectionnable : la copie automatique
    // n'est jamais le seul moyen de le recuperer (cahier §17.4).
    expect(await screen.findByText(/Copie refusée/)).toBeDefined();
    expect(screen.getByText(CORRELATION)).toBeDefined();
  });
});
