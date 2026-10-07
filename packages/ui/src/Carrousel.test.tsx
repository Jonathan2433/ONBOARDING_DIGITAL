/**
 * Carrousel — comportement manuel et accessible, LOT 8 `T12`.
 *
 * JSDOM N'APPLIQUE AUCUNE MISE EN PAGE : `scrollWidth`/`clientWidth` valent
 * zero par defaut, et `scrollBy` n'existe meme pas sur un element (mesure
 * directe, node -e, 06/10/2026 — `'scrollBy' in element` rend `false`). Les
 * tests qui eprouvent les butees et le defilement DEFINISSENT donc ces
 * proprietes explicitement sur le noeud rendu : c'est la geometrie d'un vrai
 * navigateur qui est simulee, jamais le composant qui est affaibli.
 */
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Carrousel } from './Carrousel.js';

afterEach(() => {
  cleanup();
});

/** `clientWidth`/`scrollWidth` sont des accesseurs SANS mutateur sous jsdom :
 * une simple affectation leve `TypeError`, d'ou `defineProperty`. `scrollLeft`
 * et `scrollBy` n'existent pas du tout sous jsdom et s'affectent normalement. */
function simulerLaGeometrie(
  piste: HTMLUListElement,
  valeurs: {
    readonly scrollLeft: number;
    readonly clientWidth: number;
    readonly scrollWidth: number;
  },
): void {
  Object.defineProperty(piste, 'scrollLeft', { configurable: true, value: valeurs.scrollLeft });
  Object.defineProperty(piste, 'clientWidth', { configurable: true, value: valeurs.clientWidth });
  Object.defineProperty(piste, 'scrollWidth', { configurable: true, value: valeurs.scrollWidth });
}

function rendreTroisElements(): { readonly piste: HTMLUListElement } {
  render(
    <Carrousel libelle="Arrivees recentes">
      <li key="a">Ada</li>
      <li key="b">Grace</li>
      <li key="c">Katherine</li>
    </Carrousel>,
  );
  const piste = screen.getByRole('list', { name: 'Arrivees recentes' }) as HTMLUListElement;
  return { piste };
}

describe('Carrousel', () => {
  it("n'impose AUCUNE region : seules la liste et les commandes sont nommees — une Carte englobante est deja une region", () => {
    rendreTroisElements();
    expect(screen.queryByRole('region')).toBeNull();
    expect(screen.getByRole('list', { name: 'Arrivees recentes' })).toBeTruthy();
    expect(
      screen.getByRole('button', { name: 'Arrivees recentes : element precedent' }),
    ).toBeTruthy();
    expect(
      screen.getByRole('button', { name: 'Arrivees recentes : element suivant' }),
    ).toBeTruthy();
  });

  it('rend chaque element dans l ordre du DOM, atteignable comme une liste', () => {
    const { piste } = rendreTroisElements();
    const items = within(piste).getAllByRole('listitem');
    expect(items.map((item) => item.textContent)).toEqual(['Ada', 'Grace', 'Katherine']);
  });

  it('ne defile JAMAIS seul : aucune minuterie n appelle le defilement', () => {
    vi.useFakeTimers();
    const { piste } = rendreTroisElements();
    const defilement = vi.fn();
    piste.scrollBy = defilement;
    vi.advanceTimersByTime(30_000);
    expect(defilement).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('sans debordement — piste et cadre de meme largeur — les deux commandes sont desactivees', () => {
    const { piste } = rendreTroisElements();
    simulerLaGeometrie(piste, { scrollLeft: 0, clientWidth: 300, scrollWidth: 300 });
    fireEvent.scroll(piste);
    const precedent = screen.getByRole('button', { name: /element precedent/ });
    const suivant = screen.getByRole('button', { name: /element suivant/ });
    expect((precedent as HTMLButtonElement).disabled).toBe(true);
    expect((suivant as HTMLButtonElement).disabled).toBe(true);
  });

  it('au debut d une piste debordante, seule « suivant » est actionnable', () => {
    const { piste } = rendreTroisElements();
    simulerLaGeometrie(piste, { scrollLeft: 0, clientWidth: 300, scrollWidth: 900 });
    fireEvent.scroll(piste);
    const precedent = screen.getByRole('button', { name: /element precedent/ });
    const suivant = screen.getByRole('button', { name: /element suivant/ });
    expect((precedent as HTMLButtonElement).disabled).toBe(true);
    expect((suivant as HTMLButtonElement).disabled).toBe(false);
  });

  it('en fin de piste, seule « precedent » est actionnable', () => {
    const { piste } = rendreTroisElements();
    simulerLaGeometrie(piste, { scrollLeft: 600, clientWidth: 300, scrollWidth: 900 });
    fireEvent.scroll(piste);
    const precedent = screen.getByRole('button', { name: /element precedent/ });
    const suivant = screen.getByRole('button', { name: /element suivant/ });
    expect((precedent as HTMLButtonElement).disabled).toBe(false);
    expect((suivant as HTMLButtonElement).disabled).toBe(true);
  });

  it('« suivant » defile la piste d une largeur de cadre, vers l avant', () => {
    const { piste } = rendreTroisElements();
    simulerLaGeometrie(piste, { scrollLeft: 0, clientWidth: 300, scrollWidth: 900 });
    fireEvent.scroll(piste);
    const defilement = vi.fn();
    piste.scrollBy = defilement;
    screen.getByRole('button', { name: /element suivant/ }).click();
    expect(defilement).toHaveBeenCalledWith({ left: 300 });
  });

  it('« precedent » defile la piste vers l arriere', () => {
    const { piste } = rendreTroisElements();
    simulerLaGeometrie(piste, { scrollLeft: 600, clientWidth: 300, scrollWidth: 900 });
    fireEvent.scroll(piste);
    const defilement = vi.fn();
    piste.scrollBy = defilement;
    screen.getByRole('button', { name: /element precedent/ }).click();
    expect(defilement).toHaveBeenCalledWith({ left: -300 });
  });

  it('n impose jamais `behavior` a `scrollBy` : CSS seul decide du mouvement', () => {
    const { piste } = rendreTroisElements();
    simulerLaGeometrie(piste, { scrollLeft: 0, clientWidth: 300, scrollWidth: 900 });
    fireEvent.scroll(piste);
    const defilement = vi.fn();
    piste.scrollBy = defilement;
    screen.getByRole('button', { name: /element suivant/ }).click();
    const argument = defilement.mock.calls[0]?.[0] as Record<string, unknown> | undefined;
    expect(argument).toBeDefined();
    expect(argument).not.toHaveProperty('behavior');
  });
});
