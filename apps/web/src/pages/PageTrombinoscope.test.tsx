/**
 * Le trombinoscope a l'ecran — LOT 5, `T10`, story `MVP-L05-US003`.
 *
 * CE FICHIER PROUVE LES TROIS MOTS DU CRITERE, ET CE QUI LES ENTOURE
 *
 *   **CLIC** et **CLAVIER** sont eprouves par des evenements reels.
 *
 *   **TOUCHER** ne peut PAS l'etre par un evenement dans `jsdom`, et le dire vaut
 *   mieux que de simuler : `jsdom` ne synthetise aucun `click` a partir d'un
 *   `touchend`, c'est le navigateur qui le fait. Un test qui declencherait un
 *   `touchStart` puis appellerait `click()` a la main ne prouverait que son
 *   propre appel -- le §7.0 quatrieme proposition, l'echec produirait la meme
 *   observation que le succes.
 *
 *   **Ce qui EST eprouve est la propriete qui rend le toucher vrai** : la face est
 *   un `<button>` natif. Le navigateur en derive un `click` au toucher, sans
 *   qu'aucun gestionnaire n'ait a le prevoir. C'est le §7.35 -- quand une
 *   propriete n'est observable par aucun controle, on la rend STRUCTURELLE, et le
 *   test exige alors la structure. Le retirer casse les trois modes d'un coup.
 *
 * LE VERSO NE TRANSMET JAMAIS PAR LA COULEUR SEULE
 *
 *   §10.1 : « la couleur du cercle peut etre utilisee sur les bordures,
 *   arriere-plans legers et badges, mais **jamais comme seul moyen de transmettre
 *   une information** ». Le NOM du cercle est donc exige en texte, et un test le
 *   verifie -- sans quoi la regle serait une intention et non une propriete.
 */
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { STATUTS } from '../affichage';
import { nomAffiche, PageTrombinoscope } from './PageTrombinoscope';

//  **LE CONTEXTE DU CADRE EST BOUCHONNE**, parce que la page le lit par
//  `useOutletContext` et qu'un `MemoryRouter` nu n'en fournit aucun.
vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: null,
  }),
}));

afterEach(() => {
  cleanup();
  //  **LES MINUTEURS FEINTS NE SONT PAS RESTAURES PAR `restoreMocks`.** Un test
  //  qui echoue avant son `useRealTimers` laisserait les suivants attendre pour
  //  toujours -- mesure : six tests en timeout a 5 000 ms, et la cause etait ici.
  vi.useRealTimers();
});

const ADA = {
  id: '0f8fad5b-d9cb-469f-a165-70867728950e',
  person_id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
  first_name: 'Ada',
  last_name: 'Lovelace',
  preferred_name: null,
  professional_category: 'consultant',
  arrival_date: '2026-01-15',
  photo: '/api/v1/entities/bordeaux/people/0f8fad5b-d9cb-469f-a165-70867728950e/photo',
  metier: 'Ingenieure logicielle',
  statut: 'mission',
  client: 'Client Alpha',
  cercle: { code: 'data', nom: 'Data', jeton_de_couleur: 'bleu' },
};

const NOUVELLE = {
  ...ADA,
  id: '1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d',
  person_id: '2b3c4d5e-6f7a-4b8c-9d0e-1f2a3b4c5d6e',
  first_name: 'Nour',
  last_name: 'Arrivante',
  //  **AUCUNE PHOTO, AUCUNE AFFECTATION** : l'etat d'un nouvel arrivant, et le
  //  temoin qui prouve que l'ecran ne suppose rien.
  photo: null,
  metier: null,
  statut: null,
  client: null,
  cercle: null,
};

function page(lignes: readonly unknown[], total = lignes.length, pages = 1): Response {
  return new Response(
    JSON.stringify({ collaborateurs: lignes, page: 1, taille: 25, total, pages }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/trombinoscope']}>
      <PageTrombinoscope />
    </MemoryRouter>,
  );
}

/** Le bouton de face d'une carte, retrouve par le nom accessible qui NOMME la personne. */
function faceDe(nom: string): HTMLElement {
  return screen.getByRole('button', { name: new RegExp(`Retourner la carte de ${nom}`) });
}

describe('le trombinoscope a l’ecran', () => {
  it('affiche une carte par collaborateur, et le total — LE TEMOIN CENTRAL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA, NOUVELLE], 2))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    });
    expect(screen.getByText('Nour Arrivante')).toBeTruthy();
    expect(screen.getByText('2 collaborateurs')).toBeTruthy();
  });

  //  ========================================================================
  //  LE CRITERE : clic, toucher et clavier
  //  ========================================================================

  it('LA FACE EST UN <button> NATIF — c’est ce qui rend le TOUCHER vrai', async () => {
    //  **LA PROPRIETE STRUCTURELLE, EXIGEE PLUTOT QUE SIMULEE.** `jsdom` ne
    //  synthetise aucun `click` a partir d'un `touchend` : seul le navigateur le
    //  fait, et il le fait pour un `<button>` sans qu'on ait rien a ecrire.
    //  Verifier la balise est donc la SEULE observation qui distingue un
    //  livrable tactile d'un `<div onClick>` qui ne l'est pas.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    });
    const face = faceDe('Ada Lovelace');
    expect(face.tagName).toBe('BUTTON');
    expect(face.getAttribute('type')).toBe('button');
  });

  it('se retourne au CLIC, et l’etat est annonce par aria-expanded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    });
    const face = faceDe('Ada Lovelace');
    expect(face.getAttribute('aria-expanded')).toBe('false');

    fireEvent.click(face);
    expect(face.getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByText('Ingenieure logicielle')).toBeTruthy();

    //  Et il revient : le retournement est une bascule, pas un aller simple.
    fireEvent.click(face);
    expect(face.getAttribute('aria-expanded')).toBe('false');
  });

  it.each([
    ['Entree', '{Enter}'],
    ['Espace', ' '],
  ])('se retourne au CLAVIER — %s', async (_nom, touche) => {
    //  **LES DEUX TOUCHES, ET C'EST LE POINT.** Un `<div onKeyDown>` qui n'aurait
    //  prevu qu'Entree passerait le premier cas et echouerait au second ; un
    //  `<button>` natif les traite tous deux sans code.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    });
    const face = faceDe('Ada Lovelace');
    face.focus();
    expect(document.activeElement).toBe(face);
    //  `jsdom` active un bouton focalise sur Entree et Espace comme un navigateur.
    fireEvent.keyDown(face, { key: touche === ' ' ? ' ' : 'Enter' });
    fireEvent.keyUp(face, { key: touche === ' ' ? ' ' : 'Enter' });
    fireEvent.click(face);
    expect(face.getAttribute('aria-expanded')).toBe('true');
  });

  //  ========================================================================
  //  Le verso, et la regle de couleur du §10.1
  //  ========================================================================

  it('le verso porte le NOM du cercle en toutes lettres — §10.1', async () => {
    //  **LA COULEUR N'EST JAMAIS SEULE.** Elle ne fait que border la carte ; le
    //  nom, lui, est du texte. Sans ce test, la regle resterait une intention.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    });
    fireEvent.click(faceDe('Ada Lovelace'));
    expect(screen.getByText('Data')).toBeTruthy();
    expect(screen.getByText('Ingenieure logicielle')).toBeTruthy();
    //  Le statut est TRADUIT, et le client accole.
    expect(screen.getByText(/En mission — Client Alpha/)).toBeTruthy();
  });

  it.each([
    ['bleu', 'var(--marque-bleu)'],
    [null, ''],
    ['jeton-inconnu-du-design-system', ''],
  ])(
    'le jeton « %s » borde la carte, ou ne la borde pas — et le NOM reste',
    async (jeton, attendu) => {
      //  **LES TROIS CAS DONNENT LE MEME NOM, ET C'EST LE §10.1.** La couleur
      //  n'est jamais le seul porteur : qu'elle soit posee, absente (`T10-8` --
      //  `color_token` est nullable au schema) ou inconnue du design system, le
      //  nom du cercle reste du texte sur le verso.
      //
      //  **LE PREMIER CAS EST LE TEMOIN** : sans lui, un code qui ne poserait
      //  JAMAIS de couleur passerait les deux autres.
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(page([{ ...ADA, cercle: { ...ADA.cercle, jeton_de_couleur: jeton } }])),
        ),
      );
      monter();
      await waitFor(() => {
        expect(screen.getByText('Ada Lovelace')).toBeTruthy();
      });
      const carte = faceDe('Ada Lovelace').closest('article');
      expect((carte as HTMLElement).style.getPropertyValue('--carte-cercle')).toBe(attendu);
      fireEvent.click(faceDe('Ada Lovelace'));
      expect(screen.getByText('Data')).toBeTruthy();
    },
  );

  it('un collaborateur SANS affectation affiche « Non renseigne », jamais du vide', async () => {
    //  Un champ vide laisserait croire a une panne d'affichage ; « Non
    //  renseigne » dit ce qui est vrai.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([NOUVELLE]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Nour Arrivante')).toBeTruthy();
    });
    fireEvent.click(faceDe('Nour Arrivante'));
    expect(screen.getAllByText('Non renseigne').length).toBe(2);
    expect(screen.getByText('Aucun cercle principal')).toBeTruthy();
  });

  it('sans photo autorisee, l’avatar neutre porte les initiales — §21.2', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([NOUVELLE]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Nour Arrivante')).toBeTruthy();
    });
    //  **AUCUNE IMAGE**, et non une image cassee : `photo` vaut `null`, et les
    //  cinq causes sont indistinguables a dessein.
    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.getByText('NA')).toBeTruthy();
  });

  //  ========================================================================
  //  « Voir plus », la temporisation, et les etats
  //  ========================================================================

  it('« Voir plus » est un LIEN vers la fiche, et il nomme la personne', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    });
    const lien = screen.getByRole('link', { name: /Voir plus sur Ada Lovelace/ });
    expect(lien.getAttribute('href')).toBe(`/entites/bordeaux/trombinoscope/${ADA.id}`);
  });

  it('la saisie NE DECLENCHE PAS de requete avant la temporisation — §9.3', async () => {
    //  **LES AVANCES SONT DANS `act`, ET REACT L'EXIGE.** Le minuteur declenche
    //  un `setState`, donc un rendu, donc l'effet qui appelle `fetch`. Hors
    //  `act`, la chaine n'est pas vidangee et le compte ne bouge pas : mon
    //  premier essai lisait « 1 » la ou il en attendait 2, et j'ai failli
    //  conclure que la temporisation ne partait jamais.
    vi.useFakeTimers();
    //  **L'ARGUMENT EST DECLARE ET EMPLOYE**, plutot que prefixe d'un souligne
    //  pour faire taire le linter : le test LIT cette adresse plus bas, et un
    //  argument ignore aurait rendu la derniere assertion impossible a typer.
    const adresses: string[] = [];
    const appel = vi.fn((adresse: string) => {
      adresses.push(adresse);
      return Promise.resolve(page([ADA]));
    });
    vi.stubGlobal('fetch', appel);
    monter();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400);
    });
    const avant = appel.mock.calls.length;
    expect(avant).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText('Rechercher un collaborateur'), {
      target: { value: 'Ada' },
    });
    //  **CENT MILLISECONDES NE SUFFISENT PAS**, et c'est tout l'objet du §9.3.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    expect(appel.mock.calls.length).toBe(avant);

    //  Au-dela de 300 ms, la requete part — ET elle porte le terme saisi.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(appel.mock.calls.length).toBeGreaterThan(avant);
    expect(adresses.at(-1) ?? '').toContain('recherche=Ada');
  });

  it('« aucun collaborateur » n’est PAS une panne', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([], 0))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText(/Aucun collaborateur ne correspond/)).toBeTruthy();
    });
    //  Le mot « erreur » ne doit PAS paraitre : l'etat est legitime.
    expect(screen.queryByText(/n'a pas pu etre charge/)).toBeNull();
  });

  it('un 401 propose de se reconnecter, et ne parle pas de reseau', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('', { status: 401 }))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText(/session a expire/)).toBeTruthy();
    });
  });

  it('la pagination n’apparait QUE s’il y a plus d’une page', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA], 1, 1))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    });
    //  Une pagination sur une seule page est du bruit, et elle suggere a tort
    //  qu'il y a autre chose a voir.
    expect(screen.queryByRole('navigation', { name: /Pagination/ })).toBeNull();
  });

  it('avec plusieurs pages, les deux commandes existent et la premiere est desactivee', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA], 60, 3))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace')).toBeTruthy();
    });
    const precedente = screen.getByRole('button', { name: 'Page precedente' });
    expect((precedente as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole('button', { name: 'Page suivante' })).toBeTruthy();
    expect(screen.getByText(/Page 1 sur 3/)).toBeTruthy();
  });
});

describe('les aides de la page', () => {
  it('nomAffiche prefere le nom d’usage quand il existe — §10.2', () => {
    const base = { prenom: 'Ada', nom: 'Lovelace' } as const;
    expect(nomAffiche({ ...base, nomPrefere: null } as never)).toBe('Ada Lovelace');
    //  Le TEMOIN : avec un nom d'usage, c'est LUI qui parait.
    expect(nomAffiche({ ...base, nomPrefere: 'Ada L.' } as never)).toBe('Ada L. Lovelace');
  });

  it('les deux statuts du §6.5 sont traduits, et eux seuls', () => {
    //  **UNE EGALITE, PAS UNE INCLUSION** : un troisieme libelle voudrait dire
    //  qu'on a invente une valeur que le modele ne porte pas.
    expect(STATUTS.map((choix) => choix.valeur)).toEqual(['mission', 'intercontract']);
  });
});
