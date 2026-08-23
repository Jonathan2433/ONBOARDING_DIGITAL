/**
 * Le menu principal — LOT 4, sous-etape `T4`, cahier §8.2 et §14.2.
 *
 * CE FICHIER PROUVE SIX CHOSES
 *
 *   1. **les six rubriques viennent du cahier**, et leur nombre est derive de
 *      `RUBRIQUES` : une liste recopiee vieillirait au premier ajout ;
 *   2. **les deux conditionnelles sont ABSENTES par defaut**, et presentes quand
 *      leur condition est vraie. **Les deux etats**, non le seul etat courant ;
 *   3. **tout est un lien avec un `href`** : atteignable au clavier par
 *      construction, sans aucun gestionnaire de touches a se rappeler ;
 *   4. **l'ordre du DOM est celui de `RUBRIQUES`.** Sans `tabindex` positif -- ce
 *      que `make cadre-check` exige -- l'ordre de focus sequentiel **est** l'ordre
 *      du document : c'est la specification HTML. Asserter l'ordre du DOM asserte
 *      donc l'ordre de tabulation, et la marche au clavier reelle est consignee au
 *      compte rendu ;
 *   5. **`aria-current="page"` est porte par UNE SEULE rubrique**, la courante ;
 *   6. **l'accueil n'est PAS courant sur une sous-rubrique.** Sans `end`, le
 *      chemin de l'accueil etant un prefixe de tous les autres, DEUX rubriques
 *      porteraient `aria-current` -- et un lecteur d'ecran annoncerait deux pages
 *      courantes.
 */
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';

import { CHEMINS, RUBRIQUES } from '../routes';
import { NavigationPrincipale, type ProprietesNavigation } from './NavigationPrincipale';

afterEach(cleanup);

const CODE = 'bordeaux';

function monter(chemin: string, proprietes: Partial<ProprietesNavigation> = {}): void {
  render(
    <MemoryRouter initialEntries={[chemin]}>
      <Routes>
        <Route
          path={`${CHEMINS.entite}/*`}
          element={<NavigationPrincipale code={CODE} {...proprietes} />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

function liens(): HTMLAnchorElement[] {
  return [...screen.getByRole('navigation').querySelectorAll('a')];
}

describe('le menu principal', () => {
  it('declare SIX rubriques, dont DEUX conditionnelles — derive, pas recopie', () => {
    expect(RUBRIQUES).toHaveLength(6);
    expect(RUBRIQUES.filter((r) => r.condition !== undefined)).toHaveLength(2);
    //  Les deux conditions sont celles du §8.2, mot pour mot. `cadre-check` les
    //  confronte au document ; ici on verifie qu'elles sont bien portees.
    const conditions = RUBRIQUES.filter((r) => r.condition !== undefined).map((r) => r.cle);
    expect(conditions).toEqual(['monOnboarding', 'administration']);
  });

  it("n'affiche QUE les quatre inconditionnelles par defaut — refus par defaut, §20.1", () => {
    monter(`/entites/${CODE}`);
    const libelles = liens().map((a) => a.textContent);
    expect(libelles).toEqual(['Accueil', 'Framework', 'Trombinoscope', 'Evenements']);
    //  **UNE RUBRIQUE MONTREE A TORT SUGGERE UN DROIT QU'ON N'A PAS.**
    expect(libelles).not.toContain('Mon onboarding');
    expect(libelles).not.toContain('Administration');
  });

  it('affiche « Mon onboarding » quand un parcours actif existe — §8.2', () => {
    monter(`/entites/${CODE}`, { aUnParcoursActif: true });
    expect(liens().map((a) => a.textContent)).toContain('Mon onboarding');
    //  L'autre conditionnelle reste absente : les deux conditions sont
    //  INDEPENDANTES, et un test qui les activerait ensemble ne le prouverait pas.
    expect(liens().map((a) => a.textContent)).not.toContain('Administration');
  });

  it('affiche « Administration » selon les permissions — §8.2, matrice §5', () => {
    monter(`/entites/${CODE}`, { peutAdministrer: true });
    expect(liens().map((a) => a.textContent)).toContain('Administration');
    expect(liens().map((a) => a.textContent)).not.toContain('Mon onboarding');
  });

  it('affiche les SIX quand les deux conditions sont vraies', () => {
    monter(`/entites/${CODE}`, { aUnParcoursActif: true, peutAdministrer: true });
    expect(liens()).toHaveLength(6);
  });

  it('ne rend que des LIENS, chacun avec un `href` — atteignable au clavier', () => {
    monter(`/entites/${CODE}`, { aUnParcoursActif: true, peutAdministrer: true });
    const tous = liens();
    expect(tous).toHaveLength(6);
    for (const lien of tous) {
      //  Un `<a>` sans `href` n'est PAS focusable : le lien existerait a l'oeil et
      //  serait invisible au clavier.
      expect(lien.getAttribute('href')).toBeTruthy();
      expect(lien.tagName).toBe('A');
      //  Aucun `tabindex` du tout : l'element est focusable nativement.
      expect(lien.getAttribute('tabindex')).toBeNull();
    }
  });

  it("l'ordre du DOM est celui de `RUBRIQUES`, donc l'ordre de tabulation", () => {
    monter(`/entites/${CODE}`, { aUnParcoursActif: true, peutAdministrer: true });
    //  Sans `tabindex` positif — ce que `make cadre-check` exige — l'ordre de
    //  focus sequentiel EST l'ordre du document : specification HTML. Asserter
    //  l'un asserte l'autre.
    expect(liens().map((a) => a.textContent)).toEqual(RUBRIQUES.map((r) => r.libelle));
  });

  it('porte `aria-current="page"` sur UNE SEULE rubrique, la courante', () => {
    monter(`/entites/${CODE}/framework`);
    const courants = liens().filter((a) => a.getAttribute('aria-current') === 'page');
    expect(courants).toHaveLength(1);
    expect(courants[0]?.textContent).toBe('Framework');
  });

  it("l'accueil n'est PAS courant sur une sous-rubrique — le piege de `end`", () => {
    //  **SANS `end`, DEUX RUBRIQUES SERAIENT COURANTES.** Le chemin de l'accueil,
    //  `/entites/bordeaux`, est un prefixe de `/entites/bordeaux/framework`.
    monter(`/entites/${CODE}/trombinoscope`);
    const accueil = liens().find((a) => a.textContent === 'Accueil');
    expect(accueil?.getAttribute('aria-current')).toBeNull();
    expect(liens().filter((a) => a.getAttribute('aria-current') === 'page')).toHaveLength(1);
  });

  it('nomme son repere : un second `<nav>` arrivera a `T5`', () => {
    monter(`/entites/${CODE}`);
    //  Deux `<nav>` sans nom seraient indistinguables pour un lecteur d'ecran.
    expect(screen.getByRole('navigation', { name: 'Menu principal' })).toBeTruthy();
  });

  it('encode le code dans chaque adresse', () => {
    render(
      <MemoryRouter initialEntries={['/entites/bord%2Feaux']}>
        <Routes>
          <Route path={`${CHEMINS.entite}/*`} element={<NavigationPrincipale code="bord/eaux" />} />
        </Routes>
      </MemoryRouter>,
    );
    for (const lien of liens()) {
      expect(lien.getAttribute('href')).toContain('bord%2Feaux');
      expect(lien.getAttribute('href')).not.toContain('bord/eaux');
    }
  });
});
