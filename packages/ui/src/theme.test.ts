/**
 * La bascule clair/sombre — chantier front hors lot, S9 (`DEC-672`/`DEC-673`).
 *
 * CHAQUE REFUS A SON TEMOIN (§7.39 de la passation) : un module qui ne ferait
 * jamais rien satisferait « ne leve jamais » aussi bien qu'un module correct.
 * Chaque cas degrade (stockage absent, lecture qui leve, ecriture qui leve)
 * est donc apparie a un cas qui REUSSIT, pour prouver que ce n'est pas le
 * mecanisme entier qui est resté silencieux.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { appliquerLeTheme, CLE_DE_STOCKAGE_DU_THEME, lireLeThemeStocke } from './theme.js';

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
});

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
});

describe('lireLeThemeStocke', () => {
  it("rend `null` quand rien n'a jamais ete choisi", () => {
    expect(lireLeThemeStocke()).toBeNull();
  });

  it('rend le theme ecrit par `appliquerLeTheme`', () => {
    appliquerLeTheme('sombre');
    expect(lireLeThemeStocke()).toBe('sombre');
  });

  it('rend `null` sur une valeur de stockage qui n’est ni « clair » ni « sombre »', () => {
    window.localStorage.setItem(CLE_DE_STOCKAGE_DU_THEME, 'bleu-nuit');
    expect(lireLeThemeStocke()).toBeNull();
  });

  it('rend `null`, jamais une exception, quand `localStorage` leve a la lecture', () => {
    const original = Object.getOwnPropertyDescriptor(window, 'localStorage');
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get(): never {
        throw new DOMException('bloque');
      },
    });
    try {
      expect(lireLeThemeStocke()).toBeNull();
    } finally {
      if (original !== undefined) Object.defineProperty(window, 'localStorage', original);
    }
  });
});

describe('appliquerLeTheme', () => {
  it('pose `data-theme="sombre"` sur `<html>` pour le sombre', () => {
    appliquerLeTheme('sombre');
    expect(document.documentElement.getAttribute('data-theme')).toBe('sombre');
  });

  it("RETIRE l'attribut pour le clair — l'absence EST le clair, jamais une valeur ecrite", () => {
    appliquerLeTheme('sombre');
    appliquerLeTheme('clair');
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false);
  });

  it('memorise le choix sur cet appareil', () => {
    appliquerLeTheme('sombre');
    expect(window.localStorage.getItem(CLE_DE_STOCKAGE_DU_THEME)).toBe('sombre');
  });

  it("reste effectif sur le document MEME quand l'ecriture du stockage leve", () => {
    const original = Object.getPrototypeOf(window.localStorage).setItem as (
      this: Storage,
      cle: string,
      valeur: string,
    ) => void;
    Object.getPrototypeOf(window.localStorage).setItem = (): never => {
      throw new DOMException('quota depasse');
    };
    try {
      expect(() => {
        appliquerLeTheme('sombre');
      }).not.toThrow();
      //  **LE TEMOIN QUI COMPTE** : l'attribut est pose MEME SI la memorisation
      //  a echoue — la degradation porte sur la persistance, jamais sur la
      //  bascule elle-meme.
      expect(document.documentElement.getAttribute('data-theme')).toBe('sombre');
    } finally {
      Object.getPrototypeOf(window.localStorage).setItem = original;
    }
  });
});
