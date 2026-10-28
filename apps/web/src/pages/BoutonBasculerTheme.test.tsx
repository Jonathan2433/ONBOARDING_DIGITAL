/**
 * Le bouton de bascule clair/sombre — chantier front hors lot, S9
 * (`DEC-672`/`DEC-673`).
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { BoutonBasculerTheme } from './BoutonBasculerTheme';

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
});

describe('BoutonBasculerTheme', () => {
  it("s'affiche en « Thème sombre » au premier rendu, aucune preference stockee", () => {
    render(<BoutonBasculerTheme />);
    expect(screen.getByRole('button', { name: /Thème sombre/ }).getAttribute('aria-pressed')).toBe(
      'false',
    );
    //  **LE CLAIR EST TOUJOURS LE DEFAUT, MEME SANS AUCUNE PREFERENCE
    //  STOCKEE** — l'arbitrage du 27/10/2026, jamais la preference systeme.
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false);
  });

  it('bascule vers le sombre au clic, pose `data-theme` et le memorise', () => {
    render(<BoutonBasculerTheme />);
    fireEvent.click(screen.getByRole('button', { name: /Thème sombre/ }));
    expect(screen.getByRole('button', { name: /Thème clair/ }).getAttribute('aria-pressed')).toBe(
      'true',
    );
    expect(document.documentElement.getAttribute('data-theme')).toBe('sombre');
    expect(window.localStorage.getItem('onboarding-theme')).toBe('sombre');
  });

  it('revient au clair sur un second clic — retire `data-theme`, ne le laisse pas vide', () => {
    render(<BoutonBasculerTheme />);
    const bouton = screen.getByRole('button');
    fireEvent.click(bouton);
    fireEvent.click(bouton);
    expect(screen.getByRole('button', { name: /Thème sombre/ }).getAttribute('aria-pressed')).toBe(
      'false',
    );
    expect(document.documentElement.hasAttribute('data-theme')).toBe(false);
  });

  it('reprend le sombre deja memorise sur cet appareil au premier rendu', () => {
    window.localStorage.setItem('onboarding-theme', 'sombre');
    render(<BoutonBasculerTheme />);
    expect(screen.getByRole('button', { name: /Thème clair/ }).getAttribute('aria-pressed')).toBe(
      'true',
    );
    expect(document.documentElement.getAttribute('data-theme')).toBe('sombre');
  });
});
