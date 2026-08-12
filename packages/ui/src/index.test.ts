/**
 * Controle minimal du squelette du design system.
 *
 * Ce test existe pour que la chaine de tests de ce paquet prouve quelque
 * chose. L'option `--passWithNoTests` a ete ecartee volontairement : une
 * suite vide qui « passe » est exactement le controle qui ne peut pas
 * echouer, et qui ne prouve donc rien.
 */
import { describe, expect, it } from 'vitest';

import { PACKAGE_NAME } from './index';

describe('squelette du design system', () => {
  it('expose le nom du paquet', () => {
    expect(PACKAGE_NAME).toBe('@onboarding/ui');
  });
});
