/**
 * L'affichage conditionnel — LOT 4, `T9`, story `MVP-L04-US005`.
 *
 * CE FICHIER PROUVE LE MASQUAGE. IL NE PROUVE PAS L'AUTORITE, ET C'EST LE POINT.
 *
 *   La roadmap du LOT 4 dit « **route guards uniquement ergonomiques** » et
 *   « contrôles d'autorisation systématiques dans l'**API** ». La matrice §2.6 :
 *   « le frontend peut masquer ou afficher les actions pour améliorer
 *   l'expérience, mais **l'API reste l'autorité finale** ».
 *
 *   L'autorité est éprouvée dans `apps/api/tests/test_garde_de_role.py`, sur de
 *   vraies requêtes HTTP — le §24.20 exige que « les actions interdites soient
 *   refusées côté API, **même si la requête est construite manuellement** ».
 *
 *   **Un fichier de tests frontend qui prétendrait prouver l'autorisation serait
 *   exactement le défaut que le critère de `T9` cherche à empêcher** : « un menu
 *   masqué ET un appel direct refusé par l'API — les deux, sinon le lot n'a rien
 *   prouvé ».
 *
 * LES DEUX SENS SONT TESTES, TOUJOURS
 *
 *   Un test qui ne vérifierait que le masquage serait satisfait par un menu qui
 *   n'affiche jamais rien. Chaque condition est donc éprouvée **présente et
 *   absente**.
 */
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';

import { ROLES_ADMINISTRATION } from '@onboarding/contracts';

import { droitsDeNavigation, RUBRIQUES, rubriqueEstVisible } from '../routes';
import { BarreMobile } from './BarreMobile';
import { NavigationPrincipale } from './NavigationPrincipale';

afterEach(cleanup);

describe('les droits de navigation viennent des rôles que l API a rendus', () => {
  it('rend tout à false quand les droits sont INCONNUS — refus par défaut du §20.1', () => {
    expect(droitsDeNavigation(null, false)).toEqual({
      aUnParcoursActif: false,
      peutAdministrer: false,
    });
  });

  it("n'ouvre PAS l'administration à un simple employé", () => {
    expect(droitsDeNavigation(['EMP'], false).peutAdministrer).toBe(false);
  });

  it("ouvre l'administration pour CHACUN des trois rôles du §20 — pris un par un", () => {
    //  **UN PAR UN, ET NON TOUS ENSEMBLE.** Une liste passée en bloc serait
    //  satisfaite par une implémentation qui ne reconnaît qu'un seul des trois.
    expect(ROLES_ADMINISTRATION.length).toBe(3);
    for (const role of ROLES_ADMINISTRATION) {
      expect(droitsDeNavigation([role], false).peutAdministrer).toBe(true);
    }
  });

  it("n'ouvre pas l'administration sur un rôle voisin mais distinct", () => {
    //  `DSM`, `BOOST` et `OFFICE` sont des responsabilités Framework ; le §20 ne
    //  leur donne AUCUNE colonne. Un `includes` sur un préfixe ou une casse
    //  relâchée les laisserait passer.
    for (const role of ['DSM', 'BOOST', 'OFFICE', 'NEW', 'esm', 'adm-e', 'ADM']) {
      expect(droitsDeNavigation([role], false).peutAdministrer).toBe(false);
    }
  });

  it('aUnParcoursActif est un ARGUMENT réel depuis LOT 7, T13 — épreuvé dans les DEUX sens', () => {
    //  Le §8.2 conditionne « Mon onboarding » à « lorsqu'un parcours actif
    //  existe ». `droitsDeNavigation` reste PURE : c'est `CadreApplicatif` qui
    //  interroge l'API et lui passe le résultat (voir son en-tête). Un test qui
    //  ne vérifierait qu'un sens serait satisfait par une fonction qui ignore
    //  son second argument — §7.39, un témoin par valeur en cause.
    expect(droitsDeNavigation(['SUPER'], true).aUnParcoursActif).toBe(true);
    expect(droitsDeNavigation(['SUPER'], false).aUnParcoursActif).toBe(false);
  });

  it("aUnParcoursActif ne dépend d'AUCUN rôle — c'est un fait du parcours, pas de la matrice", () => {
    for (const roles of [null, ['EMP'], ['SUPER'], ['OFFICE']]) {
      expect(droitsDeNavigation(roles, true).aUnParcoursActif).toBe(true);
    }
  });
});

describe('le prédicat de visibilité couvre TOUTES les rubriques conditionnelles', () => {
  it('chaque rubrique à condition est traitée par le prédicat, aucune oubliée', () => {
    //  **CE TEST ATTRAPE L'OUBLI QUI SERAIT SILENCIEUX.** Une septième rubrique
    //  conditionnelle ajoutée sans branche dans `rubriqueEstVisible` retomberait
    //  sur `return rubrique.condition === undefined`, donc serait masquée POUR
    //  TOUJOURS — y compris au super-administrateur — sans que rien ne le dise.
    const conditionnelles = RUBRIQUES.filter((r) => r.condition !== undefined);
    expect(conditionnelles.length).toBeGreaterThan(0);
    const tousLesDroits = { aUnParcoursActif: true, peutAdministrer: true };
    for (const rubrique of conditionnelles) {
      expect(rubriqueEstVisible(rubrique, tousLesDroits)).toBe(true);
    }
  });

  it('une rubrique sans condition est visible même sans aucun droit', () => {
    const aucunDroit = { aUnParcoursActif: false, peutAdministrer: false };
    for (const rubrique of RUBRIQUES.filter((r) => r.condition === undefined)) {
      expect(rubriqueEstVisible(rubrique, aucunDroit)).toBe(true);
    }
  });
});

function monterMenu(peutAdministrer: boolean, aUnParcoursActif = false): void {
  render(
    <MemoryRouter>
      <NavigationPrincipale
        code="bordeaux"
        peutAdministrer={peutAdministrer}
        aUnParcoursActif={aUnParcoursActif}
      />
    </MemoryRouter>,
  );
}

function monterBarre(peutAdministrer: boolean, aUnParcoursActif = false): void {
  render(
    <MemoryRouter>
      <BarreMobile
        code="bordeaux"
        peutAdministrer={peutAdministrer}
        aUnParcoursActif={aUnParcoursActif}
      />
    </MemoryRouter>,
  );
}

describe('les deux repères de navigation masquent la MÊME chose', () => {
  it("le menu principal masque « Administration » sans le droit, et l'affiche avec", () => {
    monterMenu(false);
    expect(screen.queryByRole('link', { name: 'Administration' })).toBeNull();
    cleanup();

    monterMenu(true);
    expect(screen.getByRole('link', { name: 'Administration' })).toBeTruthy();
  });

  it("la barre mobile masque « Administration » sans le droit, et l'affiche avec", () => {
    monterBarre(false);
    expect(screen.queryByRole('link', { name: 'Administration' })).toBeNull();
    cleanup();

    monterBarre(true);
    expect(screen.getByRole('link', { name: 'Administration' })).toBeTruthy();
  });

  it('« Mon onboarding » est masqué SANS parcours actif, et affiché AVEC — LOT 7, T13', () => {
    //  **LES DEUX SENS, DANS LES DEUX REPÈRES** : un test qui ne vérifierait que
    //  l'affichage serait satisfait par un menu qui montre tout ; un test qui ne
    //  vérifierait que le masquage serait satisfait par un menu qui ne montre
    //  jamais rien. Le §8.2 conditionne la rubrique au parcours, pas aux droits
    //  d'administration — `peutAdministrer` reste `false` dans les deux appels.
    for (const monter of [monterMenu, monterBarre]) {
      monter(false, false);
      expect(screen.queryByRole('link', { name: 'Mon onboarding' })).toBeNull();
      cleanup();

      monter(false, true);
      expect(screen.getByRole('link', { name: 'Mon onboarding' })).toBeTruthy();
      cleanup();
    }
  });
});
