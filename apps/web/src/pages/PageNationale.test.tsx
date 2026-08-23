/**
 * La page nationale — LOT 4, sous-etape `T6`, cahier §8.3, story `US001`.
 *
 * CE FICHIER PROUVE SEPT CHOSES
 *
 *   1. **la liste s'affiche**, une entree par entite active rendue par l'API ;
 *   2. **la liste precede l'emplacement de la carte DANS LE DOM.** C'est le critere
 *      de sortie de `T6`, et la distinction est tout : un ordre obtenu par `order`
 *      en CSS satisferait l'oeil et laisserait la carte avant la liste pour un
 *      lecteur d'ecran ;
 *   3. **chaque entite est un LIEN vers son adresse**, donc atteignable au clavier
 *      par construction ;
 *   4. **le code est encode** dans chaque adresse ;
 *   5. **« aucune entite active » n'est PAS une panne.** Confondre les deux dirait
 *      a l'utilisateur une chose fausse ;
 *   6. **un 401 propose de se reconnecter**, et ne parle pas d'un probleme reseau ;
 *   7. **le frontend ne refiltre RIEN.** L'API filtre sur `status = active` ; le
 *      refaire ici donnerait deux regles, et le jour ou l'une change l'autre
 *      mentirait.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageNationale } from './PageNationale';

afterEach(cleanup);

const BORDEAUX = {
  id: '0f8fad5b-d9cb-469f-a165-70867728950e',
  code: 'bordeaux',
  nom: 'eXalt Bordeaux',
  ville: 'Bordeaux',
};
const LILLE = {
  id: '1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d',
  code: 'lille',
  nom: 'eXalt Lille',
  ville: 'Lille',
};

function json(charge: unknown, statut: number): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/']}>
      <PageNationale />
    </MemoryRouter>,
  );
}

describe('la page nationale', () => {
  it('affiche une entree par entite — LE TEMOIN CENTRAL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200))),
    );
    monter();
    await waitFor(() =>
      expect(screen.getByRole('navigation', { name: 'Liste des entites' })).toBeTruthy(),
    );
    const liens = [...screen.getByRole('navigation').querySelectorAll('a')];
    expect(liens).toHaveLength(2);
    expect(liens.map((a) => a.textContent)).toEqual(['eXalt BordeauxBordeaux', 'eXalt LilleLille']);
  });

  it("LA LISTE PRECEDE L'EMPLACEMENT DE LA CARTE DANS LE DOM — §8.3", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [BORDEAUX] }, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('navigation')).toBeTruthy());

    //  **CE TEST MORDRA A `T7`.** Il n'y a pas encore de carte ; le jour ou elle
    //  arrivera avec la classe `nat-carte`, ce test exigera qu'elle vienne APRES
    //  la liste. Un test ecrit maintenant contre un element absent serait vide ;
    //  celui-ci exige l'ordre DES QUE les deux existent, et il constate en
    //  attendant que la carte n'est pas la.
    const principal = screen.getByRole('main');
    const liste = principal.querySelector('.nat-liste');
    const carte = principal.querySelector('.nat-carte');
    expect(liste).toBeTruthy();
    if (carte !== null) {
      expect(liste!.compareDocumentPosition(carte)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    } else {
      //  Constat explicite : l'absence est un etat connu, pas un oubli du test.
      expect(carte).toBeNull();
    }
  });

  it('chaque entite est un lien vers son adresse, code ENCODE', async () => {
    const bizarre = { ...BORDEAUX, code: 'bord/eaux' };
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [bizarre] }, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('navigation')).toBeTruthy());
    const lien = screen.getByRole('navigation').querySelector('a');
    expect(lien?.getAttribute('href')).toBe('/entites/bord%2Feaux');
    expect(lien?.getAttribute('href')).not.toContain('bord/eaux');
    //  Aucun `tabindex` : focusable nativement.
    expect(lien?.getAttribute('tabindex')).toBeNull();
  });

  it("« aucune entite active » n'est PAS une panne", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [] }, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByText(/Aucune entite active/)).toBeTruthy());
    //  **LA DISTINCTION EST LE POINT.** Un ecran d'erreur ici dirait a
    //  l'utilisateur que quelque chose est casse alors que rien ne l'est.
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.queryByRole('navigation', { name: 'Liste des entites' })).toBeNull();
  });

  it('un 401 propose de se reconnecter, et ne parle pas de reseau', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'session_refusee' } }, 401))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByText(/session a expire/)).toBeTruthy();
    expect(screen.getByRole('link', { name: /Se reconnecter/ })).toBeTruthy();
    //  Un message de panne reseau serait faux : le serveur a repondu.
    expect(screen.queryByText(/verifiez votre connexion/i)).toBeNull();
  });

  it('une panne parle de reseau, et NE PRETEND RIEN sur les entites', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByText(/verifiez votre connexion/i)).toBeTruthy();
    expect(screen.queryByText(/Aucune entite active/)).toBeNull();
  });

  it("NE REFILTRE RIEN : il rend ce que l'API renvoie", async () => {
    //  **L'API FILTRE SUR `status = active`**, et `make entites-check` le prouve.
    //  Si le frontend refiltrait, il y aurait DEUX regles. Ce test le verifie en
    //  renvoyant une entite que le frontend ne peut pas juger -- il n'a pas le
    //  statut, et il ne doit pas en avoir besoin.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('navigation')).toBeTruthy());
    expect([...screen.getByRole('navigation').querySelectorAll('a')]).toHaveLength(2);
  });

  it("porte un lien d'evitement dont la cible est FOCUSABLE", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [BORDEAUX] }, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('main')).toBeTruthy());
    expect(screen.getByRole('link', { name: /Aller au contenu/ }).getAttribute('href')).toBe(
      '#contenu',
    );
    //  `ECART-043` : sans `tabindex="-1"`, le lien ferait defiler sans deplacer le
    //  focus, et le Tab suivant repartirait du debut.
    expect(screen.getByRole('main').getAttribute('tabindex')).toBe('-1');
  });
});

describe('la carte de France — LOT 4, `T7`, cahier §8.3', () => {
  it('est rendue APRES la liste dans le DOM', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [BORDEAUX] }, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('navigation')).toBeTruthy());
    const principal = screen.getByRole('main');
    const liste = principal.querySelector('.nat-liste');
    const carte = principal.querySelector('.nat-carte');
    expect(liste).toBeTruthy();
    expect(carte).toBeTruthy();
    //  **CE TEST MORDAIT DEJA AVANT QUE LA CARTE N'EXISTE**, et il mord
    //  maintenant sur l'ordre reel. §8.3 : « sur mobile, la liste precede la
    //  carte » -- dans le DOM, pas seulement a l'oeil.
    expect(liste!.compareDocumentPosition(carte!)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it("est DECORATIVE : hors de l'arbre d'accessibilite, et sans rien de focusable", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [BORDEAUX] }, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('main').querySelector('.nat-carte')).toBeTruthy());
    const dessin = screen.getByRole('main').querySelector('.nat-carte svg');
    expect(dessin?.getAttribute('aria-hidden')).toBe('true');
    //  Un `<svg>` peut etre focusable dans certains moteurs : l'attribut le ferme.
    expect(dessin?.getAttribute('focusable')).toBe('false');
    //  **AUCUN ELEMENT FOCUSABLE DEDANS.** Le prototype posait un BOUTON sur son
    //  image ; un element interactif dans un sous-arbre `aria-hidden` est
    //  atteignable au clavier SANS etre annonce -- pire qu'un bouton absent.
    const carte = screen.getByRole('main').querySelector('.nat-carte');
    expect(carte!.querySelectorAll('a, button, input, [tabindex]')).toHaveLength(0);
    //  Ni `role="img"` ni `<title>` : elle n'informe pas, la liste le fait.
    expect(dessin?.getAttribute('role')).toBeNull();
    expect(dessin?.querySelector('title')).toBeNull();
  });

  it("n'est PAS le seul moyen d'atteindre une entite — le critere de sortie", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [BORDEAUX, LILLE] }, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('navigation')).toBeTruthy());
    //  Chaque entite a son lien dans la LISTE, et la carte n'en porte aucun.
    const liens = [...screen.getByRole('navigation').querySelectorAll('a')];
    expect(liens).toHaveLength(2);
    const carte = screen.getByRole('main').querySelector('.nat-carte');
    expect(carte!.querySelectorAll('a')).toHaveLength(0);
  });

  it("n'apparait PAS quand il n'y a rien a illustrer", async () => {
    //  Une carte decorative sur un ecran d'erreur ou vide occuperait la place du
    //  message sans rien apporter.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ entites: [] }, 200))),
    );
    monter();
    await waitFor(() => expect(screen.getByText(/Aucune entite active/)).toBeTruthy());
    expect(screen.getByRole('main').querySelector('.nat-carte')).toBeNull();
  });

  it("n'apparait PAS sur un ecran d'erreur", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(json({ erreur: { code: 'session_refusee' } }, 401))),
    );
    monter();
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByRole('main').querySelector('.nat-carte')).toBeNull();
  });
});
