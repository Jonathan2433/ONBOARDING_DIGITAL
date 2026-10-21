/**
 * La barre inferieure mobile — LOT 4, sous-etape `T5`, cahier §8.2, story `US003`.
 *
 * CE FICHIER PROUVE SIX CHOSES
 *
 *   1. **les quatre rubriques principales y sont TOUJOURS.** `US003` : « les
 *      rubriques principales restent accessibles a 320 et 390 px » ;
 *   2. **« Plus » EXISTE TOUJOURS DEPUIS `T11` DU LOT 10** : il porte desormais
 *      en permanence le bouton « Reporter un bug » (cahier §10.12), la ou il
 *      n'existait avant que « lorsque necessaire » (§8.2) l'exigeait pour une
 *      rubrique conditionnelle. Ce que ce fichier prouve a change en
 *      consequence : aucune rubrique conditionnelle ne vide plus jamais « Plus »,
 *      seule la LISTE de rubriques qu'il contient varie ;
 *   3. **les rubriques conditionnelles vont sous « Plus », jamais dans la barre.**
 *      A six cellules de 53 px, un libelle passerait sur trois lignes -- mesure ;
 *   4. **les libelles sont COMPLETS**, ni tronques ni abreges. `US003` exige
 *      qu'ils soient « corrects » ;
 *   5. **« Plus » est un `<details>`**, donc ouvrable au clavier sans qu'aucun
 *      code ne touche au focus -- aucun piege n'est possible ;
 *   6. **le repere est NOMME**, et d'un nom distinct de celui du menu principal.
 */
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';

import { CHEMINS, RUBRIQUES } from '../routes';
import { BarreMobile, CELLULES_MAXIMUM_A_320, type ProprietesBarre } from './BarreMobile';

afterEach(cleanup);

const CODE = 'bordeaux';

function monter(chemin: string, proprietes: Partial<ProprietesBarre> = {}): void {
  render(
    <MemoryRouter initialEntries={[chemin]}>
      <Routes>
        <Route path={`${CHEMINS.entite}/*`} element={<BarreMobile code={CODE} {...proprietes} />} />
      </Routes>
    </MemoryRouter>,
  );
}

function barre(): HTMLElement {
  return screen.getByRole('navigation', { name: 'Barre de navigation' });
}

function cellules(): HTMLAnchorElement[] {
  return [...barre().querySelectorAll('.app-barre-liste > li > a')] as HTMLAnchorElement[];
}

describe('la barre inferieure mobile', () => {
  it('porte les QUATRE rubriques principales, et rien de conditionnel', () => {
    monter(`/entites/${CODE}`);
    const libelles = cellules().map((a) => a.textContent);
    expect(libelles).toEqual(['Accueil', 'Framework', 'Trombinoscope', 'Evenements']);
    //  Le nombre ne depasse pas ce que 320 px acceptent, mesure.
    expect(libelles).toHaveLength(CELLULES_MAXIMUM_A_320);
  });

  it('affiche TOUJOURS « Plus », meme SANS aucune rubrique conditionnelle — cahier §10.12', () => {
    monter(`/entites/${CODE}`);
    //  **DEPUIS `T11` DU LOT 10, « PLUS » N'EST PLUS JAMAIS VIDE** : il porte
    //  en permanence le bouton « Reporter un bug », meme quand aucune
    //  rubrique conditionnelle n'existe. Le revoir disparaitre serait
    //  reproduire l'avertissement faux du §7.21 — un menu mobile qui cesserait
    //  de donner acces au signalement sans que rien ne le dise.
    expect(barre().querySelector('details.app-barre-plus')).toBeTruthy();
    expect(screen.getByText('Plus')).toBeTruthy();
    expect(screen.getByText('Reporter un bug')).toBeTruthy();
    //  Et AUCUNE rubrique secondaire n'y figure, faute de condition vraie.
    const panneau = barre().querySelector('.app-barre-panneau');
    expect(panneau!.querySelectorAll('a')).toHaveLength(0);
  });

  it("ajoute les rubriques conditionnelles a « Plus » des QU'UNE existe", () => {
    monter(`/entites/${CODE}`, { aUnParcoursActif: true });
    expect(barre().querySelector('details')).toBeTruthy();
    expect(screen.getByText('Plus')).toBeTruthy();
    //  **ET ELLE N'ENTRE PAS DANS LA BARRE.** A six cellules de 53 px, « Mon
    //  onboarding » passerait sur TROIS lignes -- mesure du 23/08/2026.
    expect(cellules().map((a) => a.textContent)).not.toContain('Mon onboarding');
  });

  it('range les DEUX conditionnelles sous « Plus » quand les deux sont vraies', () => {
    monter(`/entites/${CODE}`, { aUnParcoursActif: true, peutAdministrer: true });
    expect(cellules()).toHaveLength(CELLULES_MAXIMUM_A_320);
    const panneau = barre().querySelector('.app-barre-panneau');
    expect(panneau).toBeTruthy();
    const secondaires = [...panneau!.querySelectorAll('a')].map((a) => a.textContent);
    expect(secondaires).toEqual(['Mon onboarding', 'Administration']);
  });

  it('donne des libelles COMPLETS, ni tronques ni abreges — `US003`', () => {
    monter(`/entites/${CODE}`, { aUnParcoursActif: true, peutAdministrer: true });
    const attendus = RUBRIQUES.map((r) => r.libelle);
    const tous = [...barre().querySelectorAll('a')].map((a) => a.textContent);
    for (const libelle of attendus) {
      expect(tous).toContain(libelle);
    }
    //  Aucun caractere de troncature : un « Trombi… » n'est pas un libelle correct.
    for (const texte of tous) {
      expect(texte).not.toMatch(/[…]|\.\.\./);
    }
  });

  it('ouvre « Plus » au clavier, et AUCUN code ne touche au focus', () => {
    monter(`/entites/${CODE}`, { peutAdministrer: true });
    const details = barre().querySelector('details');
    const resume = barre().querySelector('summary');
    expect(details).toBeTruthy();
    //  `<summary>` est nativement focusable et s'active par Entree comme par
    //  Espace : c'est le navigateur qui le fait, pas nous. Aucun `tabindex`.
    expect(resume?.getAttribute('tabindex')).toBeNull();
    expect(details?.hasAttribute('open')).toBe(false);
    (resume as HTMLElement).click();
    expect(details?.hasAttribute('open')).toBe(true);
  });

  it("nomme son repere, et d'un nom DISTINCT du menu principal", () => {
    monter(`/entites/${CODE}`);
    expect(screen.getByRole('navigation', { name: 'Barre de navigation' })).toBeTruthy();
    //  Deux reperes homonymes seraient indistinguables pour un lecteur d'ecran.
    expect(screen.queryByRole('navigation', { name: 'Menu principal' })).toBeNull();
  });

  it('porte `aria-current` sur la rubrique courante, une seule', () => {
    monter(`/entites/${CODE}/framework`);
    const courants = cellules().filter((a) => a.getAttribute('aria-current') === 'page');
    expect(courants).toHaveLength(1);
    expect(courants[0]?.textContent).toBe('Framework');
  });

  it("l'accueil n'est pas courant sur une sous-rubrique — le piege de `end`", () => {
    monter(`/entites/${CODE}/evenements`);
    const accueil = cellules().find((a) => a.textContent === 'Accueil');
    expect(accueil?.getAttribute('aria-current')).toBeNull();
  });

  it('encode le code dans chaque adresse', () => {
    render(
      <MemoryRouter initialEntries={['/entites/bord%2Feaux']}>
        <Routes>
          <Route path={`${CHEMINS.entite}/*`} element={<BarreMobile code="bord/eaux" />} />
        </Routes>
      </MemoryRouter>,
    );
    for (const lien of cellules()) {
      expect(lien.getAttribute('href')).toContain('bord%2Feaux');
      expect(lien.getAttribute('href')).not.toContain('bord/eaux');
    }
  });
});
