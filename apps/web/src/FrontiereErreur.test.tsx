/**
 * Tests de la frontiere d'erreur.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002.
 *
 * FONDEMENT — cahier §17.4 : « error boundary React » et « aucun ecran blanc
 * silencieux ». Le test le plus important est le TEMOIN : sans frontiere, une
 * exception de rendu laisse un conteneur vide. C'est cette difference qui est
 * eprouvee, pas seulement la presence d'un message.
 */
import { cleanup, render, screen } from '@testing-library/react';
import type { JSX } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { FrontiereErreur } from './FrontiereErreur';

function Explose(): JSX.Element {
  throw new RangeError('rendu impossible');
}

function Sage(): JSX.Element {
  return <p>contenu normal</p>;
}

beforeEach(() => {
  // React ecrit lui-meme l'exception sur la console pendant le rendu : la
  // museler evite un bruit qui masquerait un vrai probleme dans la sortie des
  // tests. `restoreMocks` la retablit.
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
});

afterEach(() => {
  cleanup();
});

describe('FrontiereErreur', () => {
  it('laisse passer son contenu quand rien n’echoue', () => {
    render(
      <FrontiereErreur>
        <Sage />
      </FrontiereErreur>,
    );

    expect(screen.getByText('contenu normal')).toBeDefined();
  });

  it('remplace un rendu interrompu par un message, jamais par du vide', () => {
    const { container } = render(
      <FrontiereErreur>
        <Explose />
      </FrontiereErreur>,
    );

    expect(screen.getByRole('alert').textContent).toContain('interrompu');
    // Le coeur de l'exigence : l'ecran n'est PAS vide.
    expect(container.textContent).not.toBe('');
    expect(screen.getByRole('button', { name: 'Recharger la page' })).toBeDefined();
  });

  it('rapporte le type de l’exception, jamais son message', () => {
    render(
      <FrontiereErreur>
        <Explose />
      </FrontiereErreur>,
    );

    const texte = document.body.textContent ?? '';
    expect(texte).toContain('RangeError');
    // Meme discipline que `DEC-469` cote serveur : un message d'exception peut
    // transporter une valeur, il ne s'affiche donc pas.
    expect(texte).not.toContain('rendu impossible');
  });

  // TEMOIN NEGATIF : sans la frontiere, le meme composant vide le conteneur.
  // C'est ce qui prouve que la frontiere fait quelque chose.
  it('temoin : sans frontiere, le rendu laisse un conteneur vide', () => {
    expect(() => render(<Explose />)).toThrow(RangeError);
  });
});
