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

import {
  droitsDeNavigation,
  RUBRIQUES,
  rubriqueEstVisible,
  UN_PARCOURS_ACTIF_EST_POSSIBLE,
} from '../routes';
import { BarreMobile } from './BarreMobile';
import { NavigationPrincipale } from './NavigationPrincipale';

afterEach(cleanup);

describe('les droits de navigation viennent des rôles que l API a rendus', () => {
  it('rend tout à false quand les droits sont INCONNUS — refus par défaut du §20.1', () => {
    expect(droitsDeNavigation(null)).toEqual({
      aUnParcoursActif: false,
      peutAdministrer: false,
    });
  });

  it("n'ouvre PAS l'administration à un simple employé", () => {
    expect(droitsDeNavigation(['EMP']).peutAdministrer).toBe(false);
  });

  it("ouvre l'administration pour CHACUN des trois rôles du §20 — pris un par un", () => {
    //  **UN PAR UN, ET NON TOUS ENSEMBLE.** Une liste passée en bloc serait
    //  satisfaite par une implémentation qui ne reconnaît qu'un seul des trois.
    expect(ROLES_ADMINISTRATION.length).toBe(3);
    for (const role of ROLES_ADMINISTRATION) {
      expect(droitsDeNavigation([role]).peutAdministrer).toBe(true);
    }
  });

  it("n'ouvre pas l'administration sur un rôle voisin mais distinct", () => {
    //  `DSM`, `BOOST` et `OFFICE` sont des responsabilités Framework ; le §20 ne
    //  leur donne AUCUNE colonne. Un `includes` sur un préfixe ou une casse
    //  relâchée les laisserait passer.
    for (const role of ['DSM', 'BOOST', 'OFFICE', 'NEW', 'esm', 'adm-e', 'ADM']) {
      expect(droitsDeNavigation([role]).peutAdministrer).toBe(false);
    }
  });

  it('AUCUN parcours actif ne peut exister au LOT 4, et le test l épingle', () => {
    //  Le §8.2 conditionne « Mon onboarding » à « lorsqu'un parcours actif
    //  existe ». Aucune table de parcours n'existe : la condition est
    //  trivialement fausse. Ce test force le lot qui les créera à le changer
    //  DÉLIBÉRÉMENT — §7.32, un test est un meilleur véhicule qu'un commentaire.
    expect(UN_PARCOURS_ACTIF_EST_POSSIBLE).toBe(false);
    expect(droitsDeNavigation(['SUPER']).aUnParcoursActif).toBe(false);
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

function monterMenu(peutAdministrer: boolean): void {
  render(
    <MemoryRouter>
      <NavigationPrincipale code="bordeaux" peutAdministrer={peutAdministrer} />
    </MemoryRouter>,
  );
}

function monterBarre(peutAdministrer: boolean): void {
  render(
    <MemoryRouter>
      <BarreMobile code="bordeaux" peutAdministrer={peutAdministrer} />
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

  it('« Mon onboarding » est masqué dans les DEUX, quels que soient les droits', () => {
    //  Aucun parcours ne peut exister : la rubrique est absente partout, et le
    //  rester est le comportement correct — pas un oubli.
    for (const monter of [monterMenu, monterBarre]) {
      for (const droit of [false, true]) {
        monter(droit);
        expect(screen.queryByRole('link', { name: /onboarding/i })).toBeNull();
        cleanup();
      }
    }
  });
});
