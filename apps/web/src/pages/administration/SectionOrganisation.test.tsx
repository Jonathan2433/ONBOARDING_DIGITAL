/**
 * « Organisation » — création de cercle/bureau et attribution du Booster/d'un
 * responsable de bureau, LOT 11, `T3`, hors backlog (`fiche-lot-11.md` §1.2).
 *
 * CE QUE CE FICHIER ÉPROUVE, ET CE QU'IL N'ÉPROUVE PAS
 *
 *   Seule la nouveauté de `T3` : création de cercle/bureau et attribution de
 *   responsabilités Framework. La création de collaborateur, le changement
 *   d'entité et le transfert en masse (LOT 9) ne sont PAS repris ici — aucune
 *   règle n'y a changé, et ce fichier n'existait pas avant `T3` (résidu
 *   antérieur, hors périmètre de cette sous-étape).
 *
 * DEUX GRILLES DE ROLES DISTINCTES, ET UN TEST LES SÉPARE
 *
 *   La création d'un cercle/bureau réutilise `ROLES_CYCLE_DE_VIE_FRAMEWORK`
 *   (ESM/ADM-E/SUPER) ; l'attribution du Booster/d'un responsable de bureau
 *   porte `ROLES_ATTRIBUTION_FRAMEWORK` (ESM/SUPER, `ADM-E` EXCLU) — un ADM-E
 *   doit donc voir « Créer un cercle » mais jamais « Booster et responsables
 *   de bureau ».
 *
 * LE RETRAIT N'EST PROPOSÉ QUE POUR UNE AFFECTATION DE CETTE SESSION
 *
 *   Voir l'en-tête de `SectionAttributionFramework` dans le composant source :
 *   `GET …/framework` ne rend que l'identifiant de la PERSONNE, jamais celui
 *   de la ligne `framework_responsibility_assignment`. Le bouton « Retirer »
 *   n'apparaît donc qu'après une attribution RÉUSSIE dans le même montage.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SectionOrganisation } from './SectionOrganisation';

const SESSION = { personne: 'p1', jeton_csrf: 'un-jeton-anti-csrf' };

afterEach(cleanup);

function json(charge: unknown, statut = 200): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: { 'Content-Type': 'application/json' },
  });
}

const FRAMEWORK_VIDE = { responsabilites: [], cercles: [], bureaux: [] };

function frameworkAvecCercleEtBureau(): Record<string, unknown> {
  return {
    responsabilites: [],
    cercles: [
      {
        identifiant: 'c1',
        code: 'DATA',
        nom: 'Data',
        description: null,
        jeton_de_couleur: null,
        booster: null,
        membres_actifs: 0,
        chemin_detaille: '/entities/bordeaux/circles/DATA',
      },
    ],
    bureaux: [
      {
        identifiant: 'b1',
        code: 'BDS',
        nom: 'BDS',
        description: null,
        localisation: null,
        responsables: [],
        chemin_detaille: '/entities/bordeaux/offices/BDS',
      },
    ],
  };
}

interface Options {
  readonly framework?: unknown;
  readonly collaborateurs?: unknown;
  readonly statutCreationCercle?: number;
  readonly creationCercle?: unknown;
  readonly statutAttributionBooster?: number;
  readonly attributionBooster?: unknown;
  readonly statutRetraitBooster?: number;
  readonly retraitBooster?: unknown;
  readonly statutAttributionResponsable?: number;
  readonly attributionResponsable?: unknown;
}

function servir(options: Options = {}): ReturnType<typeof vi.fn> {
  const appel = vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) {
      return Promise.resolve(json(SESSION));
    }
    if (url.includes('/people?')) {
      return Promise.resolve(
        json(
          options.collaborateurs ?? { collaborateurs: [], page: 1, taille: 25, total: 0, pages: 1 },
        ),
      );
    }
    if (url.includes('/job-catalog')) {
      return Promise.resolve(json({ metiers: [] }));
    }
    if (url.includes('/clients')) {
      return Promise.resolve(json({ clients: [] }));
    }
    if (url.includes('/framework')) {
      return Promise.resolve(json(options.framework ?? FRAMEWORK_VIDE));
    }
    if (url.endsWith('/circles')) {
      return Promise.resolve(
        json(
          options.creationCercle ?? { identifiant: 'c-neuf', code: 'DATA', version: 1 },
          options.statutCreationCercle ?? 201,
        ),
      );
    }
    if (url.endsWith('/offices')) {
      return Promise.resolve(json({ identifiant: 'b-neuf', code: 'BDS', version: 1 }, 201));
    }
    if (url.endsWith('/booster/retrait')) {
      return Promise.resolve(
        json(
          options.retraitBooster ?? { affectation: 'aff-booster-1' },
          options.statutRetraitBooster ?? 200,
        ),
      );
    }
    if (url.endsWith('/booster')) {
      return Promise.resolve(
        json(
          options.attributionBooster ?? { affectation: 'aff-booster-1', remplace: false },
          options.statutAttributionBooster ?? 200,
        ),
      );
    }
    if (url.includes('/responsables/') && url.endsWith('/retrait')) {
      return Promise.resolve(json({ affectation: 'aff-resp-1' }, 200));
    }
    if (url.endsWith('/responsables')) {
      return Promise.resolve(
        json(
          options.attributionResponsable ?? { affectation: 'aff-resp-1' },
          options.statutAttributionResponsable ?? 201,
        ),
      );
    }
    return Promise.resolve(json({ erreur: { code: 'inattendu', message: url } }, 404));
  });
  vi.stubGlobal('fetch', appel);
  return appel;
}

function appels(appel: ReturnType<typeof vi.fn>): { 0: string; 1?: RequestInit }[] {
  return (appel as unknown as { mock: { calls: { 0: string; 1?: RequestInit }[] } }).mock.calls;
}

function monter(roles: readonly string[] | null): void {
  render(<SectionOrganisation code="bordeaux" roles={roles} />);
}

describe('deux grilles distinctes — création contre attribution', () => {
  it('un ADM-E voit « Créer un cercle » mais PAS « Booster et responsables de bureau »', async () => {
    servir();
    monter(['ADM-E']);

    await waitFor(() => expect(screen.getByText('Créer un cercle')).toBeTruthy());
    expect(screen.queryByText('Booster et responsables de bureau')).toBeNull();
  });

  it('un ESM voit les deux', async () => {
    servir();
    monter(['ESM']);

    await waitFor(() => expect(screen.getByText('Créer un cercle')).toBeTruthy());
    expect(screen.getByText('Booster et responsables de bureau')).toBeTruthy();
  });

  it('un rôle sans aucun des trois droits ne voit rien — EMP, à tiret partout ici', async () => {
    servir();
    monter(['EMP']);

    expect(
      screen.getByText('Votre rôle ne porte aucun droit d’écriture sur ce groupe.'),
    ).toBeTruthy();
  });
});

describe('créer un cercle', () => {
  it('TEMOIN : la création réussie affiche une confirmation et vide les champs', async () => {
    servir();
    monter(['SUPER']);

    await waitFor(() => expect(screen.getByText('Créer un cercle')).toBeTruthy());
    //  SCOPÉ AU FORMULAIRE : « Code »/« Nom » existent aussi sur le
    //  formulaire de bureau, monté EN MÊME TEMPS dans `SectionCerclesEtBureaux`.
    const formulaire = within(screen.getByRole('region', { name: 'Créer un cercle' }));
    fireEvent.change(formulaire.getByLabelText('Code'), { target: { value: 'DATA' } });
    fireEvent.change(formulaire.getByLabelText('Nom'), { target: { value: 'Data' } });
    fireEvent.click(formulaire.getByRole('button', { name: 'Créer le cercle' }));

    await waitFor(() => expect(screen.getByText('Cercle « DATA » créé.')).toBeTruthy());
    expect((formulaire.getByLabelText('Code') as HTMLInputElement).value).toBe('');
  });

  it('un refus (409 code déjà pris) affiche le message correspondant', async () => {
    servir({ statutCreationCercle: 409, creationCercle: { code: 'code_deja_pris' } });
    monter(['SUPER']);

    await waitFor(() => expect(screen.getByText('Créer un cercle')).toBeTruthy());
    const formulaire = within(screen.getByRole('region', { name: 'Créer un cercle' }));
    fireEvent.change(formulaire.getByLabelText('Code'), { target: { value: 'DATA' } });
    fireEvent.change(formulaire.getByLabelText('Nom'), { target: { value: 'Data' } });
    fireEvent.click(formulaire.getByRole('button', { name: 'Créer le cercle' }));

    await waitFor(() =>
      expect(
        screen.getByText(
          'Cette ressource a changé d’état depuis votre dernière lecture. Rechargez.',
        ),
      ).toBeTruthy(),
    );
  });
});

describe('créer un bureau', () => {
  it('TEMOIN : la création réussie affiche une confirmation', async () => {
    servir();
    monter(['SUPER']);

    await waitFor(() => expect(screen.getByText('Créer un bureau')).toBeTruthy());
    const formulaire = within(screen.getByRole('region', { name: 'Créer un bureau' }));
    fireEvent.change(formulaire.getByLabelText('Code'), { target: { value: 'BDS' } });
    fireEvent.change(formulaire.getByLabelText('Nom'), { target: { value: 'BDS' } });
    fireEvent.click(formulaire.getByRole('button', { name: 'Créer le bureau' }));

    await waitFor(() => expect(screen.getByText('Bureau « BDS » créé.')).toBeTruthy());
  });
});

/**
 * **TOUJOURS SCOPÉ À LA RÉGION « Booster et responsables de bureau »** : un
 * ESM ou un SUPER porte AUSSI `peutEcrireSurUnCollaborateur` (`ROLES_D_
 * ECRITURE` inclut `ESM`/`SUPER`), donc `FormulaireChangementDEntite` et
 * `SectionTransfertEnMasse` sont montés EN MÊME TEMPS, chacun avec son PROPRE
 * bouton « Rechercher » — une requête globale (`screen.getByRole`) trouverait
 * plusieurs éléments.
 */
function sectionAttribution(): ReturnType<typeof within> {
  return within(screen.getByRole('region', { name: 'Booster et responsables de bureau' }));
}

describe('attribuer et retirer le Booster d’un cercle — toujours un remplacement', () => {
  async function ouvrirLaSectionDuCercle(): Promise<ReturnType<typeof within>> {
    await waitFor(() => expect(screen.getByText('Booster et responsables de bureau')).toBeTruthy());
    const section = sectionAttribution();
    fireEvent.change(section.getByLabelText('Cercle'), { target: { value: 'c1' } });
    await waitFor(() => expect(section.getByText(/Booster actuel/)).toBeTruthy());
    return section;
  }

  it('attribue le Booster trouvé par la recherche, puis le retire', async () => {
    const appel = servir({
      framework: frameworkAvecCercleEtBureau(),
      collaborateurs: {
        collaborateurs: [
          {
            id: 'appartenance-1',
            person_id: 'personne-1',
            first_name: 'Ada',
            last_name: 'Lovelace',
            preferred_name: null,
            professional_category: 'consultant',
            arrival_date: '2026-01-01',
            photo: null,
            metier: null,
            statut: null,
            client: null,
            cercle: null,
          },
        ],
        page: 1,
        taille: 25,
        total: 1,
        pages: 1,
      },
    });
    monter(['ESM']);
    const section = await ouvrirLaSectionDuCercle();

    fireEvent.change(section.getByLabelText('Rechercher une personne de cette entité'), {
      target: { value: 'Ada' },
    });
    fireEvent.click(section.getByRole('button', { name: 'Rechercher' }));

    await waitFor(() => expect(section.getByText('Ada Lovelace')).toBeTruthy());
    fireEvent.click(section.getByRole('button', { name: 'Choisir' }));

    await waitFor(() => expect(section.getByRole('button', { name: 'Retirer' })).toBeTruthy());

    //  Le corps envoyé porte `person_id`, PAS l'identifiant d'appartenance.
    const attribution = appels(appel).find((a) => (a[0] as string).endsWith('/booster'));
    expect(attribution).toBeDefined();
    const corps = JSON.parse(String(attribution?.[1]?.body)) as { person_id: string };
    expect(corps.person_id).toBe('personne-1');

    fireEvent.click(section.getByRole('button', { name: 'Retirer' }));
    await waitFor(() => expect(section.queryByRole('button', { name: 'Retirer' })).toBeNull());
  });

  it('un refus (403) affiche le message de refus de rôle', async () => {
    servir({
      framework: frameworkAvecCercleEtBureau(),
      statutAttributionBooster: 403,
      attributionBooster: { code: 'acces_refuse' },
      collaborateurs: {
        collaborateurs: [
          {
            id: 'appartenance-1',
            person_id: 'personne-1',
            first_name: 'Ada',
            last_name: 'Lovelace',
            preferred_name: null,
            professional_category: 'consultant',
            arrival_date: '2026-01-01',
            photo: null,
            metier: null,
            statut: null,
            client: null,
            cercle: null,
          },
        ],
        page: 1,
        taille: 25,
        total: 1,
        pages: 1,
      },
    });
    monter(['ESM']);
    const section = await ouvrirLaSectionDuCercle();

    fireEvent.change(section.getByLabelText('Rechercher une personne de cette entité'), {
      target: { value: 'Ada' },
    });
    fireEvent.click(section.getByRole('button', { name: 'Rechercher' }));
    await waitFor(() => expect(section.getByText('Ada Lovelace')).toBeTruthy());
    fireEvent.click(section.getByRole('button', { name: 'Choisir' }));

    await waitFor(() =>
      expect(
        section.getByText('Votre rôle ne permet pas cette action pour cette cible.'),
      ).toBeTruthy(),
    );
  });
});

describe('attribuer un responsable de bureau — ajoute, ne remplace jamais', () => {
  it('attribue un responsable sans fermer les précédents, et le retire', async () => {
    const appel = servir({
      framework: frameworkAvecCercleEtBureau(),
      collaborateurs: {
        collaborateurs: [
          {
            id: 'appartenance-2',
            person_id: 'personne-2',
            first_name: 'Grace',
            last_name: 'Hopper',
            preferred_name: null,
            professional_category: 'consultant',
            arrival_date: '2026-01-01',
            photo: null,
            metier: null,
            statut: null,
            client: null,
            cercle: null,
          },
        ],
        page: 1,
        taille: 25,
        total: 1,
        pages: 1,
      },
    });
    monter(['SUPER']);

    await waitFor(() => expect(screen.getByText('Booster et responsables de bureau')).toBeTruthy());
    const section = sectionAttribution();
    fireEvent.change(section.getByLabelText('Bureau'), { target: { value: 'b1' } });
    await waitFor(() => expect(section.getByText(/Responsables actuels/)).toBeTruthy());

    fireEvent.change(section.getByLabelText('Rechercher une personne de cette entité'), {
      target: { value: 'Grace' },
    });
    fireEvent.click(section.getByRole('button', { name: 'Rechercher' }));
    await waitFor(() => expect(section.getByText('Grace Hopper')).toBeTruthy());
    fireEvent.click(section.getByRole('button', { name: 'Choisir' }));

    await waitFor(() => expect(section.getByRole('button', { name: 'Retirer' })).toBeTruthy());

    const attribution = appels(appel).find((a) => (a[0] as string).endsWith('/responsables'));
    expect(attribution).toBeDefined();
    const corps = JSON.parse(String(attribution?.[1]?.body)) as { person_id: string };
    expect(corps.person_id).toBe('personne-2');

    fireEvent.click(section.getByRole('button', { name: 'Retirer' }));
    await waitFor(() => expect(section.queryByRole('button', { name: 'Retirer' })).toBeNull());
  });
});
