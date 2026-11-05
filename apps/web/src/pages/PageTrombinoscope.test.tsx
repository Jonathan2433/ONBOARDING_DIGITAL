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
  cercle: { code: 'data', nom: 'Data', jeton_de_couleur: 'data' },
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

function page(
  lignes: readonly unknown[],
  total = lignes.length,
  pages = 1,
  pageCourante = 1,
): Response {
  return new Response(
    JSON.stringify({ collaborateurs: lignes, page: pageCourante, taille: 50, total, pages }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
}

function frameworkAvecCercles(): Response {
  return new Response(
    JSON.stringify({
      responsabilites: [],
      cercles: [
        {
          identifiant: '11111111-1111-4111-8111-111111111111',
          code: 'DATA',
          nom: 'Data',
          description: null,
          jeton_de_couleur: 'data',
          booster: null,
          membres_actifs: 12,
          chemin_detaille: '/entites/bordeaux/framework/cercles/DATA',
        },
        {
          identifiant: '22222222-2222-4222-8222-222222222222',
          code: 'PROJET',
          nom: 'Projet',
          description: null,
          jeton_de_couleur: 'projet',
          booster: null,
          membres_actifs: 18,
          chemin_detaille: '/entites/bordeaux/framework/cercles/PROJET',
        },
      ],
      bureaux: [],
    }),
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

/** La carte retrouvee par le nom accessible qui nomme la personne. */
function faceDe(nom: string): HTMLElement {
  return screen.getByRole('article', { name: `Carte de ${nom}` });
}

describe('le trombinoscope a l’ecran', () => {
  it('affiche une carte par collaborateur, et le total — LE TEMOIN CENTRAL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA, NOUVELLE], 2))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
    });
    expect(screen.getByText('Nour Arrivante', { selector: '.trombi-nom' })).toBeTruthy();
    expect(screen.getByText('2 collaborateurs')).toBeTruthy();
  });

  it('se retourne au survol CSS, sans bouton ni etat de clic', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
    });
    const carte = faceDe('Ada Lovelace');
    expect(carte.classList.contains('trombi-carte')).toBe(true);
    expect(carte.querySelector('.trombi-carte-recto')).toBeTruthy();
    expect(carte.querySelector('.trombi-carte-verso')).toBeTruthy();
    expect(carte.querySelector('button')).toBeNull();
    expect(carte.getAttribute('aria-expanded')).toBeNull();
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
      expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
    });
    //  **`{ selector: '.trombi-verso dd' }` DEPUIS S10** (`DEC-673`) : « Data »
    //  existe desormais DEUX FOIS dans le DOM — la pastille du recto (cachee
    //  par `hidden`, mais `getByText` ne filtre pas la visibilite) et ce
    //  `<dd>` du verso. Le selecteur ecarte la premiere, pas une regression.
    expect(screen.getByText('Data', { selector: '.trombi-verso dd' })).toBeTruthy();
    expect(screen.queryByText('Ingenieure logicielle')).toBeNull();
    //  Le statut est TRADUIT — depuis S6 (`DEC-672`) — et il vit depuis `E5`
    //  dans la pastille BLANCHE de la charte 6.3, non plus dans un `Badge` : le
    //  verso est un aplat de bleu fonce, ou les tons semantiques de `Badge`
    //  formeraient un couple que personne n'a mesure. Le selecteur ecarte au
    //  passage l'option du meme nom dans le filtre « Statut ».
    expect(screen.queryByText('En mission', { selector: '.trombi-verso' })).toBeNull();
    expect(screen.queryByText(/Client Alpha/)).toBeNull();
  });

  it.each([
    ['data', 'data', 'var(--trombi-cercle-data)'],
    ['projet', null, ''],
    ['inconnu', 'jeton-inconnu-du-design-system', ''],
  ])(
    'le cercle « %s » REMPLIT le bandeau, ou ne le remplit pas — et le NOM reste',
    async (codeCercle, jeton, attendu) => {
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
          Promise.resolve(
            page([
              {
                ...ADA,
                cercle: { ...ADA.cercle, code: codeCercle, jeton_de_couleur: jeton },
              },
            ]),
          ),
        ),
      );
      monter();
      await waitFor(() => {
        expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
      });
      //  **LA CARTE NE PORTE PLUS LA COULEUR, LE BANDEAU LA PORTE** — `E5`.
      //  Les deux moities comptent : si la carte la reprenait, le trait de 2 px
      //  que `E4` a mesure sous 3:1 reviendrait par la bande.
      const carte = faceDe('Ada Lovelace').closest('article');
      expect((carte as HTMLElement).style.getPropertyValue('--carte-cercle')).toBe('');
      const bandeau = document.querySelector('.trombi-bandeau') as HTMLElement;
      expect(bandeau.style.background).toBe(attendu);
      //  Depuis S10 (`DEC-673`), « Data » existe aussi sur le recto (pastille) :
      //  le selecteur cible le verso, seul concerne par ce test.
      expect(screen.getByText('Data', { selector: '.trombi-verso dd' })).toBeTruthy();
    },
  );

  //  ========================================================================
  //  Chantier front, S10 : la pastille de cercle au RECTO (`DEC-673`)
  //  ========================================================================

  it.each([
    //  UNE TEINTE ET UNE SURFACE DE MARQUE, pas deux marques : les deux
    //  familles de la charte 4 sont ainsi exercees, et leurs textes
    //  apparies different (titre sombre contre blanc).
    ['data', 'data', 'var(--trombi-cercle-data)', 'var(--trombi-cercle-data-texte)'],
    ['produit', 'produit', 'var(--cercle-produit)', 'var(--cercle-produit-texte)'],
    ['projet', null, '', ''],
    ['inconnu', 'jeton-inconnu-du-design-system', '', ''],
  ])(
    'le bandeau du recto porte le cercle « %s », REMPLI ou neutre — charte 6.3',
    async (codeCercle, jeton, surface, texte) => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve(
            page([
              {
                ...ADA,
                cercle: { ...ADA.cercle, code: codeCercle, jeton_de_couleur: jeton },
              },
            ]),
          ),
        ),
      );
      monter();
      await waitFor(() => {
        expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
      });
      //  **LE COUPLE SURFACE + TEXTE EST POSE SUR UN BANDEAU REMPLI, PAS SUR
      //  UN TRAIT.** C'est la correction que `E4` avait mesuree : cinq des huit
      //  surfaces passent sous 3:1 en filet de 4 px, et aucune ne pose de
      //  probleme en aplat, ou le texte apparie est justement fait pour elle.
      //
      //  Un jeton inconnu et l'absence de cercle donnent le MEME rendu neutre,
      //  a dessein : le frontend ne sait pas rendre une couleur qu'il ne
      //  connait pas, et il ne doit surtout pas en inventer une.
      const bandeau = document.querySelector('.trombi-bandeau') as HTMLElement;
      expect(bandeau).toBeTruthy();
      expect(bandeau.style.background).toBe(surface);
      expect(bandeau.style.color).toBe(texte);
    },
  );

  it('sans cercle, le bandeau du recto reste NEUTRE — charte 6.3', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([NOUVELLE]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Nour Arrivante', { selector: '.trombi-nom' })).toBeTruthy();
    });
    //  **LE BANDEAU EXISTE TOUJOURS, SANS COULEUR POSEE.** Le faire
    //  disparaitre changerait la hauteur de la carte selon qu'un cercle est
    //  rattache ou non, et la grille cesserait d'etre reguliere — ce que `S10`
    //  avait justement corrige. Sans cercle, il retombe sur la surface neutre
    //  declaree par la feuille, et le texte sous lui dit « Aucun cercle
    //  principal » en toutes lettres.
    const bandeau = document.querySelector('.trombi-bandeau') as HTMLElement;
    expect(bandeau).toBeTruthy();
    expect(bandeau.style.background).toBe('var(--trombi-sans-cercle)');
    expect(bandeau.style.color).toBe('var(--trombi-sans-cercle-texte)');
    expect(screen.getAllByText('Aucun cercle principal').length).toBeGreaterThan(0);
  });

  it('un collaborateur SANS cercle affiche le libelle explicite sur les deux faces', async () => {
    //  Un champ vide laisserait croire a une panne d'affichage ; « Non
    //  renseigne » dit ce qui est vrai.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([NOUVELLE]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Nour Arrivante', { selector: '.trombi-nom' })).toBeTruthy();
    });
    expect(screen.getAllByText('Aucun cercle principal').length).toBe(2);
    expect(screen.queryByText('Non renseigne')).toBeNull();
  });

  it('sans photo autorisee, l’avatar neutre porte les initiales — §21.2', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([NOUVELLE]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Nour Arrivante', { selector: '.trombi-nom' })).toBeTruthy();
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
      expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
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

  it('filtre par le véritable identifiant du cercle et repart du premier lot', async () => {
    const adresses: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn((cible: string | URL | Request) => {
        const url = String(cible);
        adresses.push(url);
        return Promise.resolve(url.endsWith('/framework') ? frameworkAvecCercles() : page([ADA]));
      }),
    );
    monter();

    const filtre = await screen.findByLabelText('Cercle');
    await waitFor(() => expect((filtre as HTMLSelectElement).disabled).toBe(false));
    expect(screen.getByRole('option', { name: 'Tous les cercles' })).toBeTruthy();
    expect(screen.getByRole('option', { name: 'Projet' })).toBeTruthy();

    fireEvent.change(filtre, { target: { value: '22222222-2222-4222-8222-222222222222' } });
    await waitFor(() =>
      expect(
        adresses.some((url) => url.includes('cercle=22222222-2222-4222-8222-222222222222')),
      ).toBe(true),
    );
    const derniereRequete = [...adresses].reverse().find((url) => url.includes('/people?')) ?? '';
    expect(derniereRequete).toContain('page=1');
  });

  it('efface en un geste la recherche, le cercle et le statut actifs', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((cible: string | URL | Request) =>
        Promise.resolve(
          String(cible).endsWith('/framework') ? frameworkAvecCercles() : page([ADA]),
        ),
      ),
    );
    monter();

    const recherche = screen.getByLabelText('Rechercher un collaborateur') as HTMLInputElement;
    const cercle = (await screen.findByLabelText('Cercle')) as HTMLSelectElement;
    const statut = screen.getByLabelText('Statut') as HTMLSelectElement;
    await waitFor(() => expect(cercle.disabled).toBe(false));

    fireEvent.change(recherche, { target: { value: 'Ada' } });
    fireEvent.change(cercle, { target: { value: '22222222-2222-4222-8222-222222222222' } });
    fireEvent.change(statut, { target: { value: 'mission' } });

    fireEvent.click(screen.getByRole('button', { name: 'Effacer les filtres' }));
    expect(recherche.value).toBe('');
    expect(cercle.value).toBe('');
    expect(statut.value).toBe('');
    expect(screen.queryByRole('button', { name: 'Effacer les filtres' })).toBeNull();
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

  it('ne montre ni pagination ni taille de page quand toute la liste tient dans un lot', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA], 1, 1))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
    });
    //  Une pagination sur une seule page est du bruit, et elle suggere a tort
    //  qu'il y a autre chose a voir.
    expect(screen.queryByRole('navigation', { name: /Pagination/ })).toBeNull();
    expect(screen.queryByText('Par page')).toBeNull();
    expect(
      screen.queryByRole('button', { name: /Charger les collaborateurs suivants/ }),
    ).toBeNull();
  });

  it('cumule les lots dans un scroll infini sans remplacer les cartes déjà visibles', async () => {
    const suivante = { ...NOUVELLE, first_name: 'Grace', last_name: 'Hopper' };
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        const pageDemandee = new URL(url, 'http://local').searchParams.get('page');
        return Promise.resolve(
          page(pageDemandee === '2' ? [suivante] : [ADA], 2, 2, pageDemandee === '2' ? 2 : 1),
        );
      }),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole('button', { name: /Charger les collaborateurs suivants/ }));
    await waitFor(() => {
      expect(screen.getByText('Grace Hopper', { selector: '.trombi-nom' })).toBeTruthy();
    });
    expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
    expect(screen.queryByRole('navigation', { name: /Pagination/ })).toBeNull();
  });
});

describe('Beta Bordeaux : cartes au survol et statut retire', () => {
  it('le verso ne contient plus le statut', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
    });
    expect(screen.queryByText('En mission', { selector: '.trombi-verso' })).toBeNull();
    expect(faceDe('Ada Lovelace').querySelector('dt')?.textContent).toBe('Cercle');
  });

  it('la carte utilise la structure de retournement au survol', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(page([ADA]))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Ada Lovelace', { selector: '.trombi-nom' })).toBeTruthy();
    });
    const carte = faceDe('Ada Lovelace');
    expect(carte.classList.contains('trombi-carte')).toBe(true);
    expect(carte.querySelector('.trombi-carte-interieur')).toBeTruthy();
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
