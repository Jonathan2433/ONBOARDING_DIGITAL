/**
 * La page Framework a l'ecran — LOT 6, `T9`, story `MVP-L06-US001`.
 *
 * CE FICHIER PORTE LE COUPLE DU §7.42, ET LA NAVIGATION REELLE VERS `T9`
 *
 *   Un cercle AVEC jeton, un cercle SANS — `jeton_de_couleur` etant nullable au
 *   catalogue. Une moitie seule laisserait passer le defaut `T10-8` : `str(None)`
 *   rendu comme un jeton plausible, ou une bordure qui ne se colore jamais.
 *
 *   **La navigation d'une carte de cercle est EPROUVEE, pas supposee** : le test
 *   monte `PageFramework` ET `PageCercle` sous le MEME routeur, clique le lien
 *   d'un cercle, et verifie que la page de cercle s'affiche reellement. Sans
 *   cela, `cercle.cheminDetaille` pourrait pointer n'importe ou et le test ne le
 *   verrait pas — §7.43, un bouchon prouve ce qu'on y a ecrit.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageCercle } from './PageCercle';
import { PageFramework } from './PageFramework';

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: null,
  }),
}));

afterEach(() => {
  cleanup();
});

const FRAMEWORK = {
  responsabilites: [
    {
      type_de_responsabilite: 'DIRECTION',
      titulaires: [
        {
          identifiant: 'dg1',
          prenom: 'Mathéa',
          nom: "D'Halluin",
          photo: '/api/v1/entities/bordeaux/people/dg1/photo?variant=thumbnail_list',
        },
        { identifiant: 'dg2', prenom: 'Julie', nom: 'Dumas', photo: null },
        { identifiant: 'dg3', prenom: 'Omar', nom: 'Lahjomri', photo: null },
      ],
      chemin_detaille: null,
    },
    {
      type_de_responsabilite: 'DSM',
      titulaires: [{ identifiant: 'p1', prenom: 'Ada', nom: 'Lovelace' }],
      chemin_detaille: '/entites/bordeaux/framework/responsabilites/dsm',
    },
    {
      type_de_responsabilite: 'ESM',
      titulaires: [],
      chemin_detaille: '/entites/bordeaux/framework/responsabilites/esm',
    },
    { type_de_responsabilite: 'BOOSTER', titulaires: [], chemin_detaille: null },
    { type_de_responsabilite: 'OFFICE_MANAGER', titulaires: [], chemin_detaille: null },
  ],
  cercles: [
    {
      identifiant: 'c1',
      code: 'data',
      nom: 'Data',
      description: null,
      jeton_de_couleur: 'produit',
      booster: {
        identifiant: 'booster-data',
        prenom: 'Hadrien',
        nom: 'Berling',
        photo: '/api/v1/entities/bordeaux/people/booster-data/photo?variant=thumbnail_list',
      },
      membres_actifs: 3,
      chemin_detaille: '/entites/bordeaux/framework/cercles/data',
    },
    {
      identifiant: 'c2',
      code: 'shield',
      nom: 'Shield',
      description: null,
      //  **LA SECONDE MOITIE DU COUPLE** : aucun jeton, et le nom doit rester lisible.
      jeton_de_couleur: null,
      booster: null,
      membres_actifs: 0,
      chemin_detaille: '/entites/bordeaux/framework/cercles/shield',
    },
  ],
  bureaux: [
    {
      identifiant: 'b1',
      code: 'siege',
      nom: 'Siege',
      description: null,
      localisation: null,
      responsables: [],
      chemin_detaille: '/entites/bordeaux/framework/bureaux/siege',
    },
  ],
};

const FRAMEWORK_AVEC_RESPONSABLES = {
  ...FRAMEWORK,
  bureaux: [
    {
      ...FRAMEWORK.bureaux[0],
      nom: 'Bureau du Gaming',
      description: 'Le bureau qui anime les rendez-vous gaming de Bordeaux.',
      localisation: 'Bordeaux centre',
      responsables: [
        {
          identifiant: 'office-1',
          prenom: 'Charles',
          nom: 'Vallais',
          photo: '/api/v1/entities/bordeaux/people/office-1/photo?variant=thumbnail_list',
        },
        {
          identifiant: 'office-2',
          prenom: 'Romain',
          nom: 'Hoarau',
          photo: null,
        },
      ],
    },
  ],
};

const FRAMEWORK_AVEC_TROIS_BUREAUX = {
  ...FRAMEWORK,
  bureaux: [
    {
      ...FRAMEWORK.bureaux[0],
      identifiant: 'bds',
      code: 'BDS',
      nom: 'Bureau du Sport',
    },
    {
      ...FRAMEWORK.bureaux[0],
      identifiant: 'bde',
      code: 'BDE',
      nom: 'Bureau des eXaltées',
    },
    {
      ...FRAMEWORK.bureaux[0],
      identifiant: 'bdg',
      code: 'BDG',
      nom: 'Bureau du Gaming',
    },
  ],
};

const CERCLE_DATA = {
  identifiant: 'c1',
  code: 'data',
  nom: 'Data',
  description: 'Le cercle Data',
  jeton_de_couleur: 'produit',
  booster: null,
  membres: [],
  total_des_membres: 0,
  page: 1,
  taille: 25,
  pages: 1,
  chemin_detaille: '/entites/bordeaux/framework/cercles/data',
};

function reponse(corps: unknown): Response {
  return new Response(JSON.stringify(corps), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={['/entites/bordeaux/framework']}>
      <Routes>
        <Route path="/entites/:code/framework" element={<PageFramework />} />
        <Route path="/entites/:code/framework/cercles/:codeCercle" element={<PageCercle />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('la page Framework a l’ecran', () => {
  it('affiche les trois familles — LE TEMOIN CENTRAL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    expect(screen.getByText('Shield')).toBeTruthy();
    expect(screen.getByText('Siege')).toBeTruthy();
    expect(screen.getByText('Direction générale')).toBeTruthy();
    expect(screen.getByText("Mathéa D'Halluin")).toBeTruthy();
    expect(screen.getByText('Julie Dumas')).toBeTruthy();
    expect(screen.getByText('Omar Lahjomri')).toBeTruthy();
    const photoDeMathea = screen.getByText("Mathéa D'Halluin").closest('li')?.querySelector('img');
    expect(photoDeMathea?.getAttribute('src')).toBe(
      '/api/v1/entities/bordeaux/people/dg1/photo?variant=thumbnail_list',
    );
    expect(screen.getByText('Ada Lovelace')).toBeTruthy();
  });

  it('LE COUPLE DU §7.42 : le nom du cercle reste du texte, avec jeton OU sans', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    //  **LE COUPLE TIENT, LE PORTEUR A CHANGE — `E5`.** La couleur etait sur
    //  le LIEN de la carte ; la charte 6.4 la met dans la TUILE a pictogramme
    //  de l'en-tete d'accordeon. Ce que ce test prouve est inchange : un jeton
    //  connu pose une couleur, son absence n'en pose aucune, et le nom reste
    //  du texte dans les deux cas.
    const avecJeton = screen.getByText('Data').closest('button');
    const sansJeton = screen.getByText('Shield').closest('button');
    expect(avecJeton).not.toBeNull();
    expect(sansJeton).not.toBeNull();
    const tuileAvec = avecJeton?.querySelector('.framework-accordeon-tuile') as HTMLElement;
    const tuileSans = sansJeton?.querySelector('.framework-accordeon-tuile') as HTMLElement;
    expect(tuileAvec.style.background).not.toBe('');
    expect(tuileSans.style.background).toBe('');
    //  Et le nom est du texte dans LES DEUX CAS — jamais porte par la seule couleur.
    expect(avecJeton?.textContent).toContain('Data');
    expect(sansJeton?.textContent).toContain('Shield');
  });

  it('les cartes de responsabilite DSM et ESM ne sont PAS des liens — ECART-062', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('DSM')).toBeTruthy();
    });
    //  `chemin_detaille` n'est pas `null` pour DSM/ESM, et pourtant aucune route
    //  ne la sert : la carte est de l'information, jamais un lien mort.
    expect(screen.getByText('DSM').closest('a')).toBeNull();
    expect(screen.getByText('ESM').closest('a')).toBeNull();
    //  BOOSTER et OFFICE_MANAGER portent aussi cette mention dans ce decor :
    //  deux occurrences, l'une comme l'autre legitimes.
    expect(screen.getAllByText('Personne actuellement').length).toBeGreaterThan(0);
  });

  it('une carte de cercle MENE reellement a sa page detaillee', async () => {
    const requete = vi.fn((cible: string | URL | Request) => {
      const url = String(cible);
      if (url.includes('/circles/')) {
        return Promise.resolve(reponse(CERCLE_DATA));
      }
      return Promise.resolve(reponse(FRAMEWORK));
    });
    vi.stubGlobal('fetch', requete);
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    //  **LA NAVIGATION PASSE PAR LE PANNEAU — `E5`.** Le nom du cercle ouvre
    //  desormais l'accordeon (charte 6.4) ; c'est le lien qu'il revele qui mene
    //  a la page detaillee. L'aller-retour reel reste eprouve, et c'est ce qui
    //  compte (§7.43) : seul le geste qui le declenche a change.
    fireEvent.click(screen.getByText('Data'));
    fireEvent.click(screen.getByText('Voir les membres du cercle Data'));
    await waitFor(() => {
      expect(screen.getByText('Le cercle Data')).toBeTruthy();
    });
  });

  it('affiche une erreur de session sur 401', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ detail: 'non authentifie' }), { status: 401 }),
        ),
      ),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText(/session a expire/)).toBeTruthy();
    });
  });
});

describe('chantier front, S5 : `Carte`/`Badge`/icone de bureau (`DEC-672`)', () => {
  it('les trois familles sont des `Carte` — trois regions nommees', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    expect(screen.getByRole('region', { name: 'Responsabilites' })).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Cercles' })).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Bureaux' })).toBeTruthy();
  });

  it('les compteurs de membres et de responsables sont des `Badge` reels, pas de la prose', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Data')).toBeTruthy();
    });
    //  Data : 3 membres actifs. Shield : 0 -- le couple du §7.42, applique au
    //  compteur plutot qu'a la couleur : la forme zero doit rester un vrai badge.
    expect(screen.getByText('3 membres').closest('.ex-badge')).not.toBeNull();
    expect(screen.getByText('0 membre').closest('.ex-badge')).not.toBeNull();
    //  Siege : zero responsable.
    expect(screen.getByText('0 responsable').closest('.ex-badge')).not.toBeNull();
  });

  it('le cercle se DEPLIE et se REPLIE — charte 6.4, `E5`', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => expect(screen.getByText('Data')).toBeTruthy());

    const bouton = screen.getByText('Data').closest('button') as HTMLButtonElement;
    //  **L'ETAT EST PORTE PAR `aria-expanded`**, pas par la seule rotation du
    //  chevron : l'etat vu et l'etat annonce viennent du meme attribut, et ils
    //  ne peuvent donc pas diverger (§14.2).
    expect(bouton.getAttribute('aria-expanded')).toBe('false');
    //  **LE PANNEAU EXISTE DEJA, MASQUE** — c'est ce qui permet a
    //  `aria-controls` de le designer avant meme qu'on l'ouvre.
    const panneau = document.getElementById(
      bouton.getAttribute('aria-controls') ?? '',
    ) as HTMLElement;
    expect(panneau).toBeTruthy();
    expect(panneau.hidden).toBe(true);

    fireEvent.click(bouton);
    expect(bouton.getAttribute('aria-expanded')).toBe('true');
    expect(panneau.hidden).toBe(false);
    //  Le panneau porte ce que `GET …/framework` sert deja — aucune lecture de
    //  plus n'est declenchee par le depliage.
    expect(within(panneau).getByText(/Booster/)).toBeTruthy();
    expect(
      within(panneau)
        .getByText('Hadrien Berling')
        .closest('.encart-booster')
        ?.querySelector('img')
        ?.getAttribute('src'),
    ).toBe('/api/v1/entities/bordeaux/people/booster-data/photo?variant=thumbnail_list');
    expect(within(panneau).getByText('Voir les membres du cercle Data')).toBeTruthy();

    //  Et il se referme : c'est une bascule, pas un aller simple.
    fireEvent.click(bouton);
    expect(bouton.getAttribute('aria-expanded')).toBe('false');
    expect(panneau.hidden).toBe(true);
  });

  it('DEUX cercles peuvent rester ouverts en meme temps', async () => {
    //  Rien dans la charte n'exige qu'en ouvrir un referme les autres, et
    //  comparer deux cercles est un geste naturel sur cette page.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => expect(screen.getByText('Data')).toBeTruthy());

    fireEvent.click(screen.getByText('Data').closest('button') as HTMLButtonElement);
    fireEvent.click(screen.getByText('Shield').closest('button') as HTMLButtonElement);
    expect(
      (screen.getByText('Data').closest('button') as HTMLElement).getAttribute('aria-expanded'),
    ).toBe('true');
    expect(
      (screen.getByText('Shield').closest('button') as HTMLElement).getAttribute('aria-expanded'),
    ).toBe('true');
  });

  it('un bureau se déplie avec sa description et les photos de ses responsables', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK_AVEC_RESPONSABLES))),
    );
    monter();
    await waitFor(() => expect(screen.getByText('Bureau du Gaming')).toBeTruthy());

    const bouton = screen.getByText('Bureau du Gaming').closest('button') as HTMLButtonElement;
    const panneau = document.getElementById(
      bouton.getAttribute('aria-controls') ?? '',
    ) as HTMLElement;
    expect(bouton.getAttribute('aria-expanded')).toBe('false');
    expect(panneau.hidden).toBe(true);

    fireEvent.click(bouton);
    expect(bouton.getAttribute('aria-expanded')).toBe('true');
    expect(panneau.hidden).toBe(false);
    expect(
      within(panneau).getByText('Le bureau qui anime les rendez-vous gaming de Bordeaux.'),
    ).toBeTruthy();
    expect(within(panneau).getByText('📍 Bordeaux centre')).toBeTruthy();
    expect(within(panneau).getByText('Charles Vallais')).toBeTruthy();
    expect(within(panneau).getByText('Romain Hoarau')).toBeTruthy();
    expect(
      within(panneau)
        .getByText('Charles Vallais')
        .closest('li')
        ?.querySelector('img')
        ?.getAttribute('src'),
    ).toBe('/api/v1/entities/bordeaux/people/office-1/photo?variant=thumbnail_list');
    expect(
      within(panneau).getByRole('link', { name: 'Voir la page du bureau Bureau du Gaming' }),
    ).toBeTruthy();

    fireEvent.click(bouton);
    expect(bouton.getAttribute('aria-expanded')).toBe('false');
    expect(panneau.hidden).toBe(true);
  });

  it('un bureau porte une icone DECORATIVE — cahier §13.2, « icones maitrisees »', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK))),
    );
    monter();
    await waitFor(() => {
      expect(screen.getByText('Siege')).toBeTruthy();
    });
    const icone = screen.getByText('Siege').closest('button')?.querySelector('svg');
    expect(icone).toBeTruthy();
    expect(icone?.getAttribute('aria-hidden')).toBe('true');
    //  **UN CERCLE PORTE DESORMAIS SON PICTOGRAMME OFFICIEL — `E4`/`E5`.** La
    //  table `CERCLES` associe un picto a chaque cercle de la charte, et la
    //  charte 6.4 le pose dans la tuile de l'en-tete. Il est DECORATIF comme
    //  celui du bureau : le nom du cercle est juste a cote, et l'annoncer le
    //  ferait entendre deux fois.
    const pictoDuCercle = screen
      .getByText('Data')
      .closest('button')
      ?.querySelector('.framework-accordeon-tuile svg');
    expect(pictoDuCercle).toBeTruthy();
    expect(pictoDuCercle?.getAttribute('aria-hidden')).toBe('true');
    //  **ET LE CERCLE SANS JETON N'EN PORTE AUCUN** : le design system ne sait
    //  pas dessiner un cercle qu'il ne connait pas, et il n'en invente pas.
    expect(
      screen.getByText('Shield').closest('button')?.querySelector('.framework-accordeon-tuile svg'),
    ).toBeNull();
  });

  it('associe un coureur au BDS, un cocktail au BDE et une manette au BDG', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(reponse(FRAMEWORK_AVEC_TROIS_BUREAUX))),
    );
    monter();
    await waitFor(() => expect(screen.getByText('Bureau du Sport')).toBeTruthy());

    const sport = screen.getByText('Bureau du Sport').closest('button');
    const exaltees = screen.getByText('Bureau des eXaltées').closest('button');
    const gaming = screen.getByText('Bureau du Gaming').closest('button');
    expect(sport?.querySelector('[data-icone-bureau="sport"]')).toBeTruthy();
    expect(exaltees?.querySelector('[data-icone-bureau="cocktail"]')).toBeTruthy();
    expect(gaming?.querySelector('[data-icone-bureau="gaming"]')).toBeTruthy();
    expect(sport?.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
    expect(exaltees?.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
    expect(gaming?.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
  });
});
