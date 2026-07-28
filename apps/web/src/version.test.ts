/**
 * Controle minimal du squelette frontend.
 *
 * Comme cote Python, ce test n'existe que pour garantir que la chaine de
 * tests s'execute reellement : une suite vide qui « passe » ne prouve rien.
 * Les tests Vitest et Testing Library de la page de statut arrivent en T5.
 */
import { describe, expect, it } from 'vitest';

import { VERSION } from './version';

describe('squelette du frontend', () => {
  it('expose une version', () => {
    expect(VERSION).toBe('0.1.0');
  });
});
