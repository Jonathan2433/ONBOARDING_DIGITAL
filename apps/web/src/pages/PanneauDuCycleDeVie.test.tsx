/**
 * Archiver et restaurer, a l'ecran — LOT 5, `T11`, story `MVP-L05-US007`.
 *
 * LE TEST LE PLUS IMPORTANT EST UNE ABSENCE D'APPEL
 *
 *   Un bouton qui agit AVANT confirmation archiverait un profil sur un clic
 *   distrait -- et un test qui ne verifierait que « la confirmation s'affiche »
 *   passerait quand meme. Ce qui est exige est donc que `fetch` n'ait **pas** ete
 *   appele tant que rien n'est confirme.
 *
 * ET LE REFUS DE MONTRER EST APPARIE A UN TEMOIN QUI MONTRE
 *
 *   « `DSM` ne voit pas le bouton » est satisfait par un composant qui ne rend
 *   jamais rien. Chaque refus de role a donc son temoin -- `ESM`, `ADM-E`,
 *   `SUPER` — ne differant que par la valeur en cause.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PanneauDuCycleDeVie } from './PanneauDuCycleDeVie';

import { EN_TETE_CLE_IDEMPOTENCE, EN_TETE_JETON_CSRF } from '@onboarding/contracts';

afterEach(cleanup);

const CODE = 'bordeaux';
const CIBLE = '0f8fad5b-d9cb-469f-a165-70867728950e';

const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

/** La version LUE sur la fiche affichee — §18.4, concurrence optimiste. */
const VERSION = 7;

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** La session repond toujours ; l'action rend ce que le test demande. */
function servir(action: { charge: unknown; statut?: number }): void {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) =>
      Promise.resolve(
        url.endsWith('/auth/session') ? json(SESSION) : json(action.charge, action.statut ?? 200),
      ),
    ),
  );
}

function appels(): { 0: string; 1?: RequestInit }[] {
  return (globalThis.fetch as unknown as { mock: { calls: { 0: string; 1?: RequestInit }[] } }).mock
    .calls;
}

function monter(options: {
  roles: readonly string[] | null;
  archive?: boolean;
  surSucces?: () => void;
}): void {
  render(
    <PanneauDuCycleDeVie
      appartenance={CIBLE}
      archive={options.archive ?? false}
      codeEntite={CODE}
      roles={options.roles}
      surSucces={options.surSucces ?? (() => undefined)}
      version={VERSION}
    />,
  );
}

describe('qui voit les actions', () => {
  it.each(['ESM', 'ADM-E', 'SUPER'])('« %s » voit le bouton — LE TEMOIN', (role) => {
    monter({ roles: [role] });
    expect(screen.getByRole('button', { name: 'Archiver ce profil' })).toBeTruthy();
  });

  it.each(['EMP', 'NEW', 'DSM', 'BOOST', 'OFFICE'])('« %s » ne voit RIEN du tout', (role) => {
    //  **NI BOUTON GRISE, NI MESSAGE « vous n'avez pas le droit ».** Le §20.1 est
    //  le refus par defaut, et un bouton desactive apprend qu'une action existe
    //  — sur un profil dont on ne gere pas le cycle de vie, c'est une
    //  information de trop.
    const { container } = render(
      <PanneauDuCycleDeVie
        appartenance={CIBLE}
        archive={false}
        codeEntite={CODE}
        roles={[role]}
        surSucces={() => undefined}
        version={VERSION}
      />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('ne montre rien tant que les permissions ne sont pas arrivees', () => {
    //  `null` n'est pas « aucun role » : c'est « pas encore connus ». Montrer le
    //  bouton puis le retirer serait pire que d'attendre.
    const { container } = render(
      <PanneauDuCycleDeVie
        appartenance={CIBLE}
        archive={false}
        codeEntite={CODE}
        roles={null}
        surSucces={() => undefined}
        version={VERSION}
      />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('un cumul suffit dès qu’UN role donne l’action — §23.1', () => {
    monter({ roles: ['EMP', 'DSM', 'ADM-E'] });
    expect(screen.getByRole('button', { name: 'Archiver ce profil' })).toBeTruthy();
  });
});

describe('l’action proposee suit l’ETAT du profil', () => {
  it('un profil actif se fait ARCHIVER', () => {
    monter({ roles: ['ESM'] });
    expect(screen.getByRole('button', { name: 'Archiver ce profil' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Restaurer ce profil' })).toBeNull();
  });

  it('un profil archive se fait RESTAURER', () => {
    monter({ roles: ['ESM'], archive: true });
    expect(screen.getByRole('button', { name: 'Restaurer ce profil' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Archiver ce profil' })).toBeNull();
  });
});

describe('la confirmation', () => {
  it('N’ENVOIE RIEN tant qu’elle n’est pas confirmee — LE TEST QUI COMPTE', () => {
    servir({ charge: {} });
    monter({ roles: ['ESM'] });
    fireEvent.click(screen.getByRole('button', { name: 'Archiver ce profil' }));
    //  La consequence est annoncee…
    expect(screen.getByText(/acces de cette personne est revoque/)).toBeTruthy();
    //  …et RIEN n'est parti.
    expect(appels()).toHaveLength(0);
  });

  it('annonce ce que `T8` a MESURE, pas une formule de politesse', () => {
    servir({ charge: {} });
    monter({ roles: ['ESM'] });
    fireEvent.click(screen.getByRole('button', { name: 'Archiver ce profil' }));
    expect(screen.getByText(/affectations en cours sont cloturees/)).toBeTruthy();

    cleanup();
    servir({ charge: {} });
    monter({ roles: ['ESM'], archive: true });
    fireEvent.click(screen.getByRole('button', { name: 'Restaurer ce profil' }));
    //  La restauration NE ROUVRE RIEN — §23.4, arbitrage de `T8`.
    expect(screen.getByText(/ne sont PAS rouvertes/)).toBeTruthy();
  });

  it('« Annuler » revient au repos, sans aucun appel', () => {
    servir({ charge: {} });
    monter({ roles: ['ESM'] });
    fireEvent.click(screen.getByRole('button', { name: 'Archiver ce profil' }));
    fireEvent.click(screen.getByRole('button', { name: 'Annuler' }));
    expect(screen.getByRole('button', { name: 'Archiver ce profil' })).toBeTruthy();
    expect(appels()).toHaveLength(0);
  });
});

describe('l’action', () => {
  //  **LA FORME REELLE D'UN ARCHIVAGE**, relevee sur la pile le 12/09/2026 : il
  //  ne porte AUCUN `relations_a_redonner`. L'inventer symetrique a la
  //  restauration est ce qui a coute le defaut `T11-7`.
  const SUCCES = {
    version: 4,
    etat_precedent: 'active',
    etat_nouveau: 'archived',
    sessions_revoquees: 2,
    liens_invalides: 0,
    relations_closes: { circle_membership: 1 },
    consultants_sans_dsm: [],
    roles_globaux_conserves: 0,
    relations_futures_conservees: {},
  };

  async function confirmer(options: {
    charge: unknown;
    statut?: number;
    archive?: boolean;
    surSucces?: () => void;
  }): Promise<void> {
    servir({ charge: options.charge, statut: options.statut ?? 200 });
    monter({
      roles: ['ESM'],
      archive: options.archive ?? false,
      ...(options.surSucces === undefined ? {} : { surSucces: options.surSucces }),
    });
    const libelle = options.archive === true ? 'Restaurer ce profil' : 'Archiver ce profil';
    fireEvent.click(screen.getByRole('button', { name: libelle }));
    fireEvent.click(screen.getByRole('button', { name: /^Confirmer/ }));
  }

  it('porte le jeton anti-CSRF ET une cle d’idempotence', async () => {
    await confirmer({ charge: SUCCES });
    await waitFor(() => {
      expect(appels().length).toBeGreaterThanOrEqual(2);
    });
    //  Le premier appel lit la session, le second agit.
    const action = appels().find((appel) => appel[0].endsWith('/archivage'));
    const enTetes = (action?.[1]?.headers ?? {}) as Record<string, string>;
    expect(enTetes[EN_TETE_JETON_CSRF]).toBe('un-jeton-anti-csrf');
    //  **UNE CLE PAR TENTATIVE** : un double clic ne doit produire qu'un effet,
    //  et c'est le mode de defaillance d'un bouton qui agit (§18.4).
    expect(enTetes[EN_TETE_CLE_IDEMPOTENCE]).toMatch(/^[0-9a-f-]{36}$/);
    expect(action?.[1]?.method).toBe('POST');
  });

  it('porte la VERSION dans le corps — sans elle, l’API rend 422', async () => {
    //  **CE TEST MANQUAIT, ET SON ABSENCE A COUTE UN DEFAUT.** Mon premier client
    //  envoyait `{}` : les onze autres tests le passaient, parce qu'un `fetch`
    //  bouchonne rend 200 quel que soit le corps. Seule la pile reelle l'a dit --
    //  `422 Field required`, defaut `T11-6`.
    //
    //  §18.4 : la version vient de la FICHE AFFICHEE, jamais d'une relecture.
    //  Relire juste avant d'agir ferait disparaitre la concurrence optimiste.
    await confirmer({ charge: SUCCES });
    await waitFor(() => {
      expect(appels().length).toBeGreaterThanOrEqual(2);
    });
    const action = appels().find((appel) => appel[0].endsWith('/archivage'));
    expect(JSON.parse(String(action?.[1]?.body))).toEqual({ version: VERSION });
  });

  it('affiche les DEUX etats et la version', async () => {
    await confirmer({ charge: SUCCES });
    await waitFor(() => {
      expect(screen.getByText(/active → archived/)).toBeTruthy();
    });
    expect(screen.getByText(/version 4/)).toBeTruthy();
  });

  it('NOMME les affectations que la restauration n’a pas rouvertes', async () => {
    //  Les taire laisserait un profil actif sans DSM ni cercle, sans que
    //  personne le sache.
    await confirmer({
      archive: true,
      charge: {
        version: 5,
        etat_precedent: 'archived',
        etat_nouveau: 'active',
        relations_a_redonner: ['dsm_assignment', 'circle_membership'],
      },
    });
    await waitFor(() => {
      expect(screen.getByText('dsm_assignment')).toBeTruthy();
    });
    expect(screen.getByText('circle_membership')).toBeTruthy();
    expect(screen.getByText(/NON rouvertes/)).toBeTruthy();
  });

  it('un ARCHIVAGE ne parle jamais d’affectations a redonner', async () => {
    //  Le temoin de la regle precedente : l'archivage ne laisse rien a redonner,
    //  et sa reponse ne porte meme pas le champ. Defaut `T11-7`.
    await confirmer({ charge: SUCCES });
    await waitFor(() => {
      expect(screen.getByText(/active → archived/)).toBeTruthy();
    });
    expect(screen.queryByText(/NON rouvertes/)).toBeNull();
  });

  it('un ARCHIVAGE montre ce qu’il a REELLEMENT clos, table par table', async () => {
    //  L'annoncer avant le geste est une promesse ; le montrer apres est une
    //  mesure. C'est ce que `T8` produit, et le taire perdrait l'information.
    await confirmer({ charge: SUCCES });
    await waitFor(() => {
      expect(screen.getByText(/circle_membership — 1/)).toBeTruthy();
    });
    expect(screen.getByText(/2 session\(s\) revoquee\(s\)/)).toBeTruthy();
  });

  it('previent la page du succes, pour qu’elle recharge', async () => {
    const surSucces = vi.fn();
    await confirmer({ charge: SUCCES, surSucces });
    await waitFor(() => {
      expect(surSucces).toHaveBeenCalledTimes(1);
    });
  });

  it('ne la previent PAS d’un refus', async () => {
    const surSucces = vi.fn();
    await confirmer({ charge: { code: 'etat_incompatible' }, statut: 409, surSucces });
    await waitFor(() => {
      expect(screen.getByText(/pas dans un etat qui permet/)).toBeTruthy();
    });
    expect(surSucces).not.toHaveBeenCalled();
  });
});

describe('les refus, et chacun dit une chose differente', () => {
  it.each([
    [401, /session a expire/],
    [403, /role ne permet pas cette action/],
    [404, /introuvable, ou il n’est pas dans votre perimetre/],
    [409, /pas dans un etat qui permet l’archivage/],
    [500, /n’a pas pu aboutir/],
  ])('un %s rend son propre message', async (statut, motif) => {
    //  **LES CINQ SONT DISTINCTS, ET C'EST VOULU.** Le `403` parle du ROLE, le
    //  `409` de l'ETAT — §23.2, une interdiction liee a la ressource prevaut sur
    //  le cumul des roles, si bien qu'un SUPER recoit le `409` comme tout le
    //  monde. Les confondre ferait chercher un droit qu'on a deja.
    servir({ charge: { code: 'refus' }, statut: statut as number });
    monter({ roles: ['SUPER'] });
    fireEvent.click(screen.getByRole('button', { name: 'Archiver ce profil' }));
    fireEvent.click(screen.getByRole('button', { name: /^Confirmer/ }));
    await waitFor(() => {
      expect(screen.getByText(motif as RegExp)).toBeTruthy();
    });
  });

  it('le 409 de la RESTAURATION ne dit pas la meme chose que celui de l’archivage', async () => {
    servir({ charge: { code: 'etat_incompatible' }, statut: 409 });
    monter({ roles: ['SUPER'], archive: true });
    fireEvent.click(screen.getByRole('button', { name: 'Restaurer ce profil' }));
    fireEvent.click(screen.getByRole('button', { name: /^Confirmer/ }));
    await waitFor(() => {
      expect(screen.getByText(/deja actif/)).toBeTruthy();
    });
  });

  it('une panne reseau n’est PAS un refus de droit', async () => {
    //  Les confondre ferait douter d'un droit alors que le service ne repond
    //  pas. §7.6 — ne masque pas une cause que tu vas interpreter.
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new TypeError('reseau'))),
    );
    monter({ roles: ['ESM'] });
    fireEvent.click(screen.getByRole('button', { name: 'Archiver ce profil' }));
    fireEvent.click(screen.getByRole('button', { name: /^Confirmer/ }));
    await waitFor(() => {
      expect(screen.getByText(/n’a pas pu aboutir/)).toBeTruthy();
    });
  });

  it('« Fermer » ramene au bouton, pour pouvoir reessayer', async () => {
    servir({ charge: { code: 'refus' }, statut: 403 });
    monter({ roles: ['ESM'] });
    fireEvent.click(screen.getByRole('button', { name: 'Archiver ce profil' }));
    fireEvent.click(screen.getByRole('button', { name: /^Confirmer/ }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Fermer' })).toBeTruthy();
    });
    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }));
    expect(screen.getByRole('button', { name: 'Archiver ce profil' })).toBeTruthy();
  });
});
