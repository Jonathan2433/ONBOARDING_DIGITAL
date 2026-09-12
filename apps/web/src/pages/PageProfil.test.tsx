/**
 * La fiche profil a l'ecran — LOT 5, `T11`, stories `MVP-L05-US004` et `US008`.
 *
 * CE FICHIER PORTE TROIS COUPLES, ET AUCUNE MOITIE NE SUFFIRAIT
 *
 *   `null` / `[]` sur un axe d'historique — « hors de ton perimetre » contre
 *   « rien a montrer ». Les confondre ferait croire a un DSM que son consultant
 *   n'a jamais porte de responsabilite.
 *
 *   jeton pose / jeton absent sur un cercle — la bordure prend la couleur, ou
 *   reste neutre, et le NOM est du texte dans les deux cas (§10.1).
 *
 *   fiche 200 + historique 403 — l'etat NORMAL d'un employe, et c'est lui qui
 *   prouve que les deux appels sont independants. Un ecran qui enchainerait les
 *   requetes n'afficherait rien du tout dans ce cas.
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { dateComplete, moisAnnee, PageProfil } from './PageProfil';

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: null,
  }),
}));

afterEach(cleanup);

const APPARTENANCE = '0f8fad5b-d9cb-469f-a165-70867728950e';

const FICHE = {
  id: APPARTENANCE,
  person_id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
  first_name: 'Ada',
  last_name: 'Lovelace',
  preferred_name: null,
  professional_category: 'consultant',
  arrival_date: '2025-09-08',
  short_bio: 'Ingenieure passionnee.',
  fun_fact: 'Joue du theorbe.',
  metier: 'Ingenieure logicielle',
  statut: 'mission',
  client: 'Client Alpha',
  dsm: 'Dominique Lesmanager',
  cercle_principal: { code: 'DATA', nom: 'Donnees', jeton_de_couleur: 'bleu' },
  cercles_secondaires: [{ code: 'CLOUD', nom: 'Cloud', jeton_de_couleur: null }],
  responsabilites: [{ type: 'BOOSTER', cercle: 'Donnees', bureau: null }],
  photo: null,
};

const HISTOIRE = {
  metier: [{ metier: 'Ingenieure logicielle', debut: '2025-09-08T00:00:00Z', fin: null }],
  statut: [
    {
      statut: 'mission',
      client: 'Client Alpha',
      debut: '2025-09-08T00:00:00Z',
      fin: '2026-01-01T00:00:00Z',
    },
  ],
  cercle: [
    { code: 'DATA', nom: 'Donnees', type: 'principal', debut: '2025-09-08T00:00:00Z', fin: null },
  ],
  dsm: [{ dsm: 'Dominique Lesmanager', debut: '2025-09-08T00:00:00Z', fin: null }],
  responsabilites: [],
};

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Les deux appels sont distingues par leur chemin, jamais par leur ordre. */
function servir(
  fiche: { charge: unknown; statut?: number },
  histoire: { charge: unknown; statut?: number },
): void {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) =>
      Promise.resolve(
        url.endsWith('/historique')
          ? json(histoire.charge, histoire.statut ?? 200)
          : json(fiche.charge, fiche.statut ?? 200),
      ),
    ),
  );
}

function monter(): void {
  render(
    <MemoryRouter initialEntries={[`/entites/bordeaux/trombinoscope/${APPARTENANCE}`]}>
      <Routes>
        <Route element={<PageProfil />} path="/entites/:code/trombinoscope/:appartenance" />
      </Routes>
    </MemoryRouter>,
  );
}

describe('la fiche a l’ecran', () => {
  it('rend les champs du §10.2 — LE TEMOIN CENTRAL', async () => {
    servir({ charge: FICHE }, { charge: HISTOIRE });
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Ada Lovelace' })).toBeTruthy();
    });
    //  **L'ENTITE VIENT DU CADRE, PAS DE L'API** : la route ne la sert pas, et le
    //  §10.2 la liste pourtant parmi les champs du profil.
    expect(screen.getByText('eXalt Bordeaux')).toBeTruthy();
    //  **CHACUN PARAIT DEUX FOIS, ET C'EST JUSTE** : une fois dans la fiche,
    //  une fois dans l'axe correspondant de l'historique. Un `getByText` levait
    //  « Found multiple elements » -- l'attendu etait faux, pas le livrable.
    expect(screen.getAllByText('Ingenieure logicielle')).toHaveLength(2);
    expect(screen.getAllByText('Dominique Lesmanager')).toHaveLength(2);
    expect(screen.getAllByText('Donnees').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Ingenieure passionnee.')).toBeTruthy();
    expect(screen.getByText('Joue du theorbe.')).toBeTruthy();
    //  La date d'arrivee se lit au JOUR, la seule qui le fasse.
    expect(screen.getByText('8 septembre 2025')).toBeTruthy();
  });

  it('affiche « Non renseigne » pour un champ nul, jamais du vide', async () => {
    //  Un champ vide laisserait croire a une panne d'affichage ; et le §10.2
    //  autorise l'absence -- un nouvel arrivant n'a ni fun fact ni client.
    servir(
      { charge: { ...FICHE, dsm: null, client: null, short_bio: null, fun_fact: null } },
      { charge: HISTOIRE },
    );
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Ada Lovelace' })).toBeTruthy();
    });
    expect(screen.getAllByText('Non renseigne').length).toBeGreaterThanOrEqual(3);
  });

  it('le nom PREFERE remplace le prenom quand il existe', async () => {
    servir({ charge: { ...FICHE, preferred_name: 'Ada L.' } }, { charge: HISTOIRE });
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Ada L. Lovelace' })).toBeTruthy();
    });
  });

  //  ======================================================================
  //  La photo — §21.2
  //  ======================================================================

  it('sans photo, un avatar d’INITIALES et AUCUNE image cassee', async () => {
    servir({ charge: FICHE }, { charge: HISTOIRE });
    const { container } = render(
      <MemoryRouter initialEntries={[`/entites/bordeaux/trombinoscope/${APPARTENANCE}`]}>
        <Routes>
          <Route element={<PageProfil />} path="/entites/:code/trombinoscope/:appartenance" />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(container.querySelector('.profil-avatar')).toBeTruthy();
    });
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('.profil-avatar')?.textContent).toBe('AL');
  });

  it('avec photo, un `<img>` dont l’alternative est VIDE', async () => {
    //  Le nom est juste a cote : un `alt` qui le repeterait le ferait annoncer
    //  deux fois par un lecteur d'ecran.
    servir({ charge: { ...FICHE, photo: '/api/v1/…/photo' } }, { charge: HISTOIRE });
    const { container } = render(
      <MemoryRouter initialEntries={[`/entites/bordeaux/trombinoscope/${APPARTENANCE}`]}>
        <Routes>
          <Route element={<PageProfil />} path="/entites/:code/trombinoscope/:appartenance" />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(container.querySelector('img')).toBeTruthy();
    });
    expect(container.querySelector('img')?.getAttribute('alt')).toBe('');
  });

  //  ======================================================================
  //  Les cercles — §10.1, la couleur n'est jamais seule
  //  ======================================================================

  it('le cercle porte son NOM en texte, et la couleur ne fait que border', async () => {
    servir({ charge: FICHE }, { charge: HISTOIRE });
    const { container } = render(
      <MemoryRouter initialEntries={[`/entites/bordeaux/trombinoscope/${APPARTENANCE}`]}>
        <Routes>
          <Route element={<PageProfil />} path="/entites/:code/trombinoscope/:appartenance" />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(container.querySelectorAll('.profil-cercle').length).toBe(2);
    });
    const cercles = [...container.querySelectorAll('.profil-cercle')] as HTMLElement[];
    //  **LE COUPLE** : le principal porte « bleu », le secondaire aucun jeton.
    //  Sans le premier, un code qui ne poserait JAMAIS de couleur passerait.
    expect(cercles[0]?.style.getPropertyValue('--profil-cercle')).toBe('var(--marque-bleu)');
    expect(cercles[1]?.style.getPropertyValue('--profil-cercle')).toBe('');
    //  Et les DEUX noms restent lisibles, ce qui est ce que le §10.1 protege.
    expect(cercles[0]?.textContent).toContain('Donnees');
    expect(cercles[1]?.textContent).toContain('Cloud');
  });

  //  ======================================================================
  //  Les refus de la FICHE
  //  ======================================================================

  it('un 404 rend UN SEUL message pour QUATRE causes', async () => {
    //  Distinguer « ce profil n'existe pas » de « il est hors de ton perimetre »
    //  apprendrait a un DSM de qui il n'est pas responsable.
    servir({ charge: { code: 'introuvable' }, statut: 404 }, { charge: {}, statut: 404 });
    monter();
    await waitFor(() => {
      expect(screen.getByText(/introuvable, ou il n’est pas dans votre perimetre/)).toBeTruthy();
    });
    expect(screen.queryByRole('heading', { name: 'Ada Lovelace' })).toBeNull();
  });

  it('un 401 parle de SESSION, pas de droits', async () => {
    servir({ charge: {}, statut: 401 }, { charge: {}, statut: 401 });
    monter();
    await waitFor(() => {
      expect(screen.getByText(/session a expire/)).toBeTruthy();
    });
  });

  //  ======================================================================
  //  L'historique — le couple `null` / `[]`, et le refus normal
  //  ======================================================================

  it('rend les CINQ axes, et distingue `[]` de `null` — LE COUPLE', async () => {
    servir({ charge: FICHE }, { charge: { ...HISTOIRE, responsabilites: null } });
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Historique organisationnel' })).toBeTruthy();
    });
    for (const titre of ['Metiers', 'Situations', 'DSM', 'Responsabilites']) {
      expect(screen.getByRole('heading', { name: titre })).toBeTruthy();
    }
    //  `null` : hors perimetre. C'est le §20 de la matrice, que le §23.2 fait
    //  prevaloir sur le cumul des roles.
    expect(screen.getByText(/Hors de votre perimetre/)).toBeTruthy();
    //  Et aucune periode n'est inventee pour cet axe.
    expect(screen.queryByText('BOOSTER — Donnees')).toBeNull();
  });

  it('`[]` rend « aucune periode », ce qui n’est PAS « hors perimetre »', async () => {
    //  **SANS CE SECOND TEST, LE PRECEDENT NE PROUVE RIEN** : un ecran qui
    //  afficherait « hors perimetre » pour tout axe vide le passerait.
    servir({ charge: FICHE }, { charge: HISTOIRE });
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Responsabilites' })).toBeTruthy();
    });
    expect(screen.getByText('Aucune periode enregistree.')).toBeTruthy();
    expect(screen.queryByText(/Hors de votre perimetre/)).toBeNull();
  });

  it('une fiche SERVIE et un historique REFUSE : la fiche s’affiche quand meme', async () => {
    //  **C'EST L'ETAT NORMAL D'UN EMPLOYE**, pas une panne : le §5 lui donne
    //  « Fiches collaborateur » en Lecture, et sa ligne « Audit » lui refuse
    //  l'historique. Un ecran qui enchainerait les deux requetes n'afficherait
    //  rien du tout ici.
    servir({ charge: FICHE }, { charge: { code: 'acces_refuse' }, statut: 403 });
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Ada Lovelace' })).toBeTruthy();
    });
    expect(screen.getByText(/ne donne pas acces a l’historique/)).toBeTruthy();
    //  La fiche, elle, est complete.
    //  Un seul exemplaire ici : l'historique est refuse, donc son axe DSM
    //  n'est pas rendu. C'est le meme temoin que ci-dessus, vu par son absence.
    expect(screen.getAllByText('Dominique Lesmanager')).toHaveLength(1);
  });

  it('lance les DEUX appels, et ne les enchaine pas', async () => {
    servir({ charge: FICHE }, { charge: HISTOIRE });
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Ada Lovelace' })).toBeTruthy();
    });
    const appels = (globalThis.fetch as unknown as { mock: { calls: string[][] } }).mock.calls;
    expect(appels).toHaveLength(2);
    expect(appels.filter((appel) => appel[0]?.endsWith('/historique'))).toHaveLength(1);
  });

  it('une periode CLOSE affiche ses deux bornes, une periode COURANTE dit « aujourd’hui »', async () => {
    servir({ charge: FICHE }, { charge: HISTOIRE });
    monter();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Situations' })).toBeTruthy();
    });
    expect(screen.getByText('septembre 2025 → janvier 2026')).toBeTruthy();
    expect(screen.getAllByText(/→ aujourd’hui/).length).toBeGreaterThan(0);
  });
});

describe('le formatage des dates', () => {
  it('NE PASSE PAS par `Date` — le 1er janvier UTC reste JANVIER', () => {
    //  **LE PIEGE MESURE** : `new Date('2026-01-01T00:00:00Z').getMonth()` rend
    //  **11**, decembre, dans tout fuseau a l'est de Greenwich. Une periode close
    //  le 1er janvier deviendrait close en decembre, et le defaut ne se verrait
    //  qu'a Paris -- jamais sur un executeur en UTC. §7.16.
    expect(moisAnnee('2026-01-01T00:00:00Z')).toBe('janvier 2026');
    expect(new Date('2026-01-01T00:00:00Z').getUTCMonth()).toBe(0);
  });

  it('rend le mois pour une periode, le jour pour une date d’arrivee', () => {
    expect(moisAnnee('2025-06-25T00:00:00Z')).toBe('juin 2025');
    expect(dateComplete('2025-09-08')).toBe('8 septembre 2025');
  });

  it('rend la chaine telle quelle si le mois est hors bornes, plutot que « undefined »', () => {
    //  Une valeur que l'API ne devrait jamais servir : la montrer fait chercher
    //  la cause au bon endroit, « undefined 2025 » ferait chercher un defaut
    //  d'affichage.
    expect(moisAnnee('2025-13-01T00:00:00Z')).toBe('2025-13-01T00:00:00Z');
  });
});
