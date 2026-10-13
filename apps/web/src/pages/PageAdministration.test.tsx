/**
 * « Administration » à l'écran — LOT 9, `T14`, les SEPT groupes du cahier §8.1/§10.8.
 *
 * CE QUE CE FICHIER ÉPROUVE, ET CE QU'IL N'ÉPROUVE PAS
 *
 *   Ce fichier teste la COQUILLE à onglets SEULE — quels groupes apparaissent
 *   pour quel rôle, et que changer d'onglet affiche le bon panneau. Le
 *   contenu de chaque section (formulaires, règles de permission fines) est
 *   éprouvé dans son propre fichier (`administration/Section*.test.tsx`) —
 *   dupliquer ces assertions ici reviendrait à la classe `DEC-466`/`ECART-022`
 *   d'une règle testée deux fois, qui diverge au premier changement.
 *
 * LE PREMIER ONGLET MONTÉ EST « ORGANISATION », ET CHAQUE TEST SERT SES APPELS
 *
 *   Un `fetch` non couvert répond 404 plutôt que de lever : les sections
 *   affichent alors une alerte de refus, ce que ces tests n'examinent pas —
 *   seule la PRÉSENCE du bon titre de panneau compte ici.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PageAdministration } from './PageAdministration';

const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

let rolesDuCadre: readonly string[] = ['SUPER'];

vi.mock('./CadreApplicatif', () => ({
  useEntiteConsultee: () => ({
    entite: { id: 'e1', code: 'bordeaux', nom: 'eXalt Bordeaux', ville: 'Bordeaux' },
    permissions: { roles: rolesDuCadre, estEntitePrincipale: true, appartenance: null },
  }),
}));

afterEach(() => {
  cleanup();
  rolesDuCadre = ['SUPER'];
});

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Un `fetch` qui sert des reponses VIDES mais bien formees pour toutes les routes connues. */
function servirDesReponsesVides(): ReturnType<typeof vi.fn> {
  const appel = vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json(SESSION));
    }
    if (url.includes('/job-catalog')) {
      return Promise.resolve(json({ metiers: [] }));
    }
    if (url.includes('/framework')) {
      return Promise.resolve(json({ responsabilites: [], cercles: [], bureaux: [] }));
    }
    if (url.includes('/clients')) {
      return Promise.resolve(json({ clients: [] }));
    }
    if (url.endsWith('/entities')) {
      return Promise.resolve(json({ entites: [] }));
    }
    if (url.includes('/administration/tableau-de-bord')) {
      return Promise.resolve(
        json({
          profils_actifs: 0,
          arrivees_futures: 0,
          onboardings_actifs: 0,
          taches_en_retard: 0,
          profils_incomplets: 0,
          derniers_imports_en_echec: [],
        }),
      );
    }
    if (url.includes('/onboarding-suivi/taches-en-retard')) {
      return Promise.resolve(json({ taches: [], page: 1, taille: 25, total: 0, pages: 1 }));
    }
    if (url.endsWith('/task-references')) {
      return Promise.resolve(json({ taches: [], nombre_de_taches: 0 }));
    }
    if (url.endsWith('/onboarding/templates')) {
      return Promise.resolve(json({ modeles: [], nombre_de_modeles: 0 }));
    }
    return Promise.resolve(json({ erreur: { code: 'inattendu', message: url } }, 404));
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

function monter(): void {
  render(<PageAdministration />);
}

describe('la coquille à onglets — un SUPER voit les sept groupes', () => {
  it('affiche les sept onglets, dans l’ordre du cahier §8.1/§10.8', async () => {
    servirDesReponsesVides();
    monter();

    await waitFor(() => expect(screen.getByRole('tablist')).toBeTruthy());
    const onglets = screen.getAllByRole('tab').map((o) => o.textContent);
    expect(onglets).toEqual([
      'Organisation',
      'Onboarding',
      'Contenu',
      'Données',
      'Pilotage',
      'Configuration',
      'Super-administration',
    ]);
  });

  it('monte « Organisation » par défaut', async () => {
    servirDesReponsesVides();
    monter();

    await waitFor(() => expect(screen.getByText('Créer un collaborateur')).toBeTruthy());
  });

  it('changer d’onglet affiche le panneau correspondant', async () => {
    servirDesReponsesVides();
    monter();

    await waitFor(() => expect(screen.getByText('Créer un collaborateur')).toBeTruthy());
    fireEvent.click(screen.getByRole('tab', { name: 'Super-administration' }));

    await waitFor(() => expect(screen.getByText('Créer une entité')).toBeTruthy());
    expect(screen.queryByText('Créer un collaborateur')).toBeNull();
  });

  it('« Contenu » et « Configuration » affichent un message « à venir »', async () => {
    servirDesReponsesVides();
    monter();

    await waitFor(() => expect(screen.getByText('Créer un collaborateur')).toBeTruthy());
    fireEvent.click(screen.getByRole('tab', { name: 'Contenu' }));

    await waitFor(() =>
      expect(screen.getByText(/« Contenu » arrive dans un lot ultérieur/)).toBeTruthy(),
    );
  });
});

describe('un rôle sans aucun droit — refus par défaut, §20.1', () => {
  it('un EMP ne voit que les trois groupes SANS garde de rôle (Contenu, Pilotage, Configuration)', async () => {
    //  « Aucun rôle n'y est refusé » pour Pilotage (le suivi se dégrade
    //  jusqu'à `Soi`, LOT 7 `T12`) ; Contenu et Configuration n'ont tout
    //  simplement AUCUNE garde, faute de route à garder (`SectionAVenir`).
    //  §20.1 porte sur ce que le MENU PRINCIPAL annonce (`droitsDeNavigation`,
    //  `routes.ts`), pas sur ce qu'un accès direct à cette page peut encore
    //  montrer quand rien ne distingue les rôles.
    rolesDuCadre = ['EMP'];
    servirDesReponsesVides();
    monter();

    await waitFor(() => expect(screen.getByRole('tablist')).toBeTruthy());
    const onglets = screen.getAllByRole('tab').map((o) => o.textContent);
    expect(onglets).toEqual(['Contenu', 'Pilotage', 'Configuration']);
  });

  it('un ESM voit Organisation, Onboarding, Contenu, Données, Pilotage et Configuration, mais PAS Super-administration', async () => {
    rolesDuCadre = ['ESM'];
    servirDesReponsesVides();
    monter();

    await waitFor(() => expect(screen.getByRole('tablist')).toBeTruthy());
    const onglets = screen.getAllByRole('tab').map((o) => o.textContent);
    expect(onglets).not.toContain('Super-administration');
    expect(onglets).toContain('Organisation');
  });
});
