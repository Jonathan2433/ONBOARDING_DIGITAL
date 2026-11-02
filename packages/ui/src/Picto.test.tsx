/**
 * Picto — accessibilite, couleur et taille.
 *
 * Chantier design systeme v2 hors lot, etape `E2` (`DEC-681`).
 *
 * LE TEMOIN DECISIF EST UNE PAIRE, ET IL FALLAIT QU'IL EN SOIT UNE
 *
 *   « Le picto decoratif n'est pas annonce » se verifie mal par le seul nom
 *   accessible du bouton qui le porte : un `<svg>` sans texte ne contribue a ce
 *   nom NI quand il est masque, NI quand il ne l'est pas. Un `aria-hidden`
 *   supprime par megarde laisserait donc le nom intact, et le controle serait
 *   vert sur un defaut (§7.0, quatrieme proposition).
 *
 *   Les deux moities qui mordent vraiment : l'absence de `role="img"` dans
 *   l'arbre — directement observable — et la MEME scene AVEC `titre`, ou le nom
 *   du bouton change reellement. Sans la seconde, rien ne prouverait que le
 *   chemin accessible fonctionne ; sans la premiere, rien ne prouverait que le
 *   defaut est bien l'absence d'annonce.
 */

import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { Picto } from './Picto.js';
import { PICTOS } from './pictos.js';

afterEach(() => {
  cleanup();
});

/** Le `<svg>` rendu. `getByRole` ne sert pas : decoratif, il n'a aucun role. */
function svgRendu(conteneur: HTMLElement): SVGSVGElement {
  const svg = conteneur.querySelector('svg');
  if (svg === null) {
    throw new Error('aucun <svg> rendu');
  }
  return svg;
}

describe('Picto — le picto decoratif ne parle pas, et le picto nomme parle', () => {
  it("n'expose AUCUN role quand il accompagne un libelle visible", () => {
    render(
      <button type="button">
        <Picto nom="feu-d-artifice" />
        Vie eXalt
      </button>,
    );

    expect(screen.queryByRole('img')).toBeNull();
    expect(screen.getByRole('button', { name: 'Vie eXalt' })).toBeTruthy();
  });

  it("porte aria-hidden, et c'est ce qui le retire de l'arbre", () => {
    const { container } = render(<Picto nom="loupe" />);
    expect(svgRendu(container).getAttribute('aria-hidden')).toBe('true');
    expect(svgRendu(container).getAttribute('role')).toBeNull();
  });

  it('TEMOIN APPARIE : le MEME bouton, seul le `titre` change, et le nom apparait', () => {
    //  Sans ce temoin, « le nom vaut Vie eXalt » serait satisfait par un
    //  composant qui ne saurait PAS se nommer du tout. Ici la scene est la
    //  meme — un bouton dont le picto est le seul contenu — et le nom passe de
    //  RIEN a quelque chose : le chemin accessible existe, et il est emprunte.
    render(
      <>
        <button type="button" data-cas="muet">
          <Picto nom="feu-d-artifice" />
        </button>
        <button type="button" data-cas="nomme">
          <Picto nom="feu-d-artifice" titre="Feu d'artifice" />
        </button>
      </>,
    );

    expect(screen.getByRole('button', { name: '' }).dataset['cas']).toBe('muet');
    expect(screen.getByRole('button', { name: "Feu d'artifice" }).dataset['cas']).toBe('nomme');
    expect(screen.getByRole('img', { name: "Feu d'artifice" })).toBeTruthy();
  });

  it('MESURE : un picto NOMME colle au libelle voisin — le defaut decoratif est le bon', () => {
    //  Mesure du 02/11/2026, pas une supposition : le nom accessible du bouton
    //  vaut « Feu d'artificeVie eXalt », SANS espace. La concatenation du calcul
    //  de nom n'en insere pas entre deux contenus en ligne. Ce n'est pas un
    //  defaut du composant — c'est la demonstration que `titre` ne doit servir
    //  qu'a un picto SEUL, et donc que `aria-hidden` par defaut est le bon
    //  choix plutot qu'une precaution.
    //
    //  Ce test fige la mesure : si une version de la bibliotheque de calcul
    //  changeait cette concatenation, il faudrait le savoir, pas le decouvrir
    //  sur un ecran.
    render(
      <button type="button">
        <Picto nom="feu-d-artifice" titre="Feu d'artifice" />
        Vie eXalt
      </button>,
    );

    expect(screen.getByRole('button', { name: "Feu d'artificeVie eXalt" })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Vie eXalt' })).toBeNull();
  });

  it('nomme ne porte PAS aria-hidden : les deux regimes sont exclusifs', () => {
    //  `aria-hidden` et `role="img"` sur le meme noeud donnent un element
    //  annonce par certaines technologies et tu par d'autres.
    const { container } = render(<Picto nom="organigramme" titre="Organigramme" />);
    expect(svgRendu(container).getAttribute('aria-hidden')).toBeNull();
    expect(svgRendu(container).getAttribute('role')).toBe('img');
  });
});

describe('Picto — la couleur vient du contexte', () => {
  it('pose fill="currentColor" sur le svg', () => {
    const { container } = render(<Picto nom="fusee" />);
    expect(svgRendu(container).getAttribute('fill')).toBe('currentColor');
  });

  it('ne pose AUCUN fill sur les courbes, sans quoi currentColor ne servirait a rien', () => {
    //  La moitie qui mord : un `fill` sur un `<path>` l'emporte sur celui du
    //  `<svg>`. Le picto garderait alors sa couleur d'origine sur une surface de
    //  cercle, et le couple surface/texte prouve par `jetons.test.ts` ne
    //  vaudrait plus rien pour lui.
    const { container } = render(<Picto nom="ampoule-idee" />);
    const courbes = [...svgRendu(container).querySelectorAll('path')];
    expect(courbes.length).toBeGreaterThan(0);
    for (const courbe of courbes) {
      expect(courbe.getAttributeNames().sort()).toEqual(['d']);
    }
  });
});

describe('Picto — la taille et la forme', () => {
  it('vaut 24px par defaut, le plancher de la charte 4', () => {
    const { container } = render(<Picto nom="serveur" />);
    expect(svgRendu(container).getAttribute('width')).toBe('24');
    expect(svgRendu(container).getAttribute('height')).toBe('24');
  });

  it.each([24, 32, 40, 44, 48] as const)('applique la taille %i aux deux dimensions', (taille) => {
    const { container } = render(<Picto nom="dialogue" taille={taille} />);
    expect(svgRendu(container).getAttribute('width')).toBe(String(taille));
    expect(svgRendu(container).getAttribute('height')).toBe(String(taille));
  });

  it("garde le viewBox de l'icone et ne force PAS preserveAspectRatio", () => {
    //  Les boites officielles ne sont pas carrees — `0 0 58.05 63.95` pour la
    //  fusee. Poser `preserveAspectRatio="none"` etirerait le dessin dans le
    //  carre demande ; l'absence d'attribut vaut `xMidYMid meet`, donc une
    //  inscription centree sans deformation.
    const { container } = render(<Picto nom="fusee" taille={48} />);
    const svg = svgRendu(container);
    expect(svg.getAttribute('viewBox')).toBe(PICTOS.fusee.viewBox);
    expect(svg.getAttribute('viewBox')).toBe('0 0 58.05 63.95');
    expect(svg.getAttribute('preserveAspectRatio')).toBeNull();
  });
});

describe('Picto — les douze icones rendent toutes leur dessin', () => {
  const cles = Object.keys(PICTOS) as (keyof typeof PICTOS)[];

  it('le perimetre examine est bien de douze', () => {
    //  Le compte annonce : sans lui, une table vide ferait passer la boucle
    //  ci-dessous en n'examinant rien (§7.0, 3e proposition).
    expect(cles).toHaveLength(12);
  });

  it.each(cles)('%s rend autant de <path> que la table en declare', (cle) => {
    const { container } = render(<Picto nom={cle} />);
    const courbes = svgRendu(container).querySelectorAll('path');
    expect(courbes).toHaveLength(PICTOS[cle].chemins.length);
    expect(courbes.length).toBeGreaterThan(0);
    expect(courbes[0]?.getAttribute('d')).toBe(PICTOS[cle].chemins[0]);
  });
});
