/**
 * La carte retournable — LOT 5, `T10`, story `MVP-L05-US003`.
 *
 * CE FICHIER EPROUVE LE COMPOSANT SEUL, SANS ECRAN AUTOUR
 *
 *   `PageTrombinoscope.test.tsx` l'eprouve **en situation** — une grille, des
 *   donnees, un lien vers la fiche. Ici il est seul, et ce qui est verifie est ce
 *   qui doit rester vrai quel que soit l'appelant : la balise de la face, la
 *   bascule, l'etat annonce, et le fait que la face cachee soit reellement
 *   RETIREE du document plutot que masquee a l'oeil.
 *
 *   Les deux niveaux sont necessaires : un composant juste dans une page fausse
 *   passerait le second test et pas le premier, et l'inverse est vrai aussi.
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { CarteRetournable } from './CarteRetournable';

afterEach(cleanup);

function monter(): void {
  render(
    <CarteRetournable
      nomAccessible="Retourner la carte de Ada Lovelace"
      recto={<span>RECTO</span>}
      verso={<span>VERSO</span>}
      voirPlus={<a href="/profil">Voir plus</a>}
    />,
  );
}

/**
 * La face qui PORTE un texte est-elle cachee ?
 *
 * **`queryByText` NE RESPECTE PAS `hidden`, ET JE L'AVAIS CRU.** Mon premier
 * test affirmait « la face cachee est absente de la requete » : c'est faux,
 * `queryByText` parcourt le DOM sans regarder la visibilite, et les deux tests
 * qui s'y fiaient ont echoue. La mesure exacte est l'attribut lui-meme.
 */
function estCachee(texte: string): boolean {
  const face = screen.getByText(texte).closest('[hidden]');
  return face !== null;
}

describe('la carte retournable', () => {
  it('LA FACE EST UN <button> NATIF — clic, toucher et clavier par construction', () => {
    //  **LA PROPRIETE STRUCTURELLE.** `jsdom` ne synthetise aucun `click` a
    //  partir d'un `touchend` : c'est le navigateur qui le fait, et il le fait
    //  pour un `<button>`. Exiger la balise est donc la seule observation qui
    //  distingue un livrable tactile d'un `<div onClick>` qui ne l'est pas.
    monter();
    const face = screen.getByRole('button', { name: 'Retourner la carte de Ada Lovelace' });
    expect(face.tagName).toBe('BUTTON');
    expect(face.getAttribute('type')).toBe('button');
  });
});

describe('les faces', () => {
  it('montre le recto au depart, et cache le verso', () => {
    monter();
    expect(estCachee('RECTO')).toBe(false);
    expect(estCachee('VERSO')).toBe(true);
  });

  it('bascule au clic, et l’etat est porte par aria-expanded', () => {
    monter();
    const face = screen.getByRole('button', { name: 'Retourner la carte de Ada Lovelace' });
    expect(face.getAttribute('aria-expanded')).toBe('false');

    fireEvent.click(face);
    expect(face.getAttribute('aria-expanded')).toBe('true');
    expect(estCachee('VERSO')).toBe(false);
    expect(estCachee('RECTO')).toBe(true);

    //  Et il revient : le retournement est une bascule, pas un aller simple.
    fireEvent.click(face);
    expect(face.getAttribute('aria-expanded')).toBe('false');
    expect(estCachee('RECTO')).toBe(false);
  });
});

describe('la structure', () => {
  it('la face cachee porte `hidden`, l’attribut — pas une classe', () => {
    //  **LA DIFFERENCE COMPTE.** `hidden` retire l'element du parcours de
    //  tabulation ET de l'arbre d'accessibilite ; une classe CSS ne fait ni
    //  l'un ni l'autre, et un lecteur d'ecran annoncerait le verso cache.
    const { container } = render(
      <CarteRetournable
        nomAccessible="Retourner"
        recto={<span>R</span>}
        verso={<span>V</span>}
        voirPlus={<a href="/x">Voir plus</a>}
      />,
    );
    const verso = container.querySelector('.ui-carte-retournable__verso');
    expect(verso?.hasAttribute('hidden')).toBe(true);
  });

  it('« Voir plus » est FRERE du bouton, jamais enfant', () => {
    //  **UN LIEN DANS UN BOUTON EST UN IMBRIQUEMENT INTERACTIF INVALIDE** : le
    //  navigateur en fait ce qu'il veut, et le clavier n'atteint pas toujours
    //  les deux. Ce test le fige.
    monter();
    const face = screen.getByRole('button', { name: 'Retourner la carte de Ada Lovelace' });
    const lien = screen.getByRole('link', { name: 'Voir plus' });
    expect(face.contains(lien)).toBe(false);
    //  Et les deux sont bien dans la meme carte.
    expect(face.closest('article')).toBe(lien.closest('article'));
  });

  it('le bouton pilote les faces par `aria-controls`', () => {
    const { container } = render(
      <CarteRetournable
        nomAccessible="Retourner"
        recto={<span>R</span>}
        verso={<span>V</span>}
        voirPlus={<a href="/x">Voir plus</a>}
      />,
    );
    const face = screen.getByRole('button', { name: 'Retourner' });
    const cible = face.getAttribute('aria-controls');
    expect(cible).toBeTruthy();
    //  **L'IDENTIFIANT DOIT DESIGNER UN ELEMENT QUI EXISTE**, sinon
    //  `aria-controls` ne dit rien — et rien ne le signalerait.
    expect(container.querySelector(`#${CSS.escape(String(cible))}`)).toBeTruthy();
  });
});
