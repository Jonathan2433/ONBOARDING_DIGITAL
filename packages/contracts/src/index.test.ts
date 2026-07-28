/**
 * Controle minimal du squelette du contrat API partage.
 *
 * Meme role que son equivalent dans `packages/ui` : garantir que la chaine
 * de tests de ce paquet s'execute reellement.
 */
import { describe, expect, it } from 'vitest';

import { PACKAGE_NAME } from './index';

describe('squelette du contrat API', () => {
  it('expose le nom du paquet', () => {
    expect(PACKAGE_NAME).toBe('@onboarding/contracts');
  });
});
