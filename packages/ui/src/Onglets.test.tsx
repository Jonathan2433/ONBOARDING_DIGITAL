/**
 * Onglets — comportement accessible sur primitive Radix, chantier front hors
 * lot, sous-etape S1 (`DEC-672`).
 *
 * CE QUE CES TESTS PROUVENT, ET CE QU'ILS NE PROUVENT PAS
 *
 *   Ils prouvent le contrat accessible (role, nom, etat, clavier) et le choix
 *   de conception — un SEUL panneau rendu, jamais un par onglet. Ils ne
 *   prouvent PAS le rendu visuel : jsdom n'applique aucune feuille de style,
 *   comme pour tous les autres composants de ce paquet (voir l'en-tete de
 *   `composants.test.tsx`).
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { JSX } from 'react';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Onglets } from './Onglets.js';

afterEach(() => {
  cleanup();
});

const ONGLETS = [
  { valeur: 'organisation', libelle: 'Organisation' },
  { valeur: 'pilotage', libelle: 'Pilotage' },
  { valeur: 'audit', libelle: 'Audit' },
] as const;

/** Un hote controle, comme un vrai appelant (`PageAdministration.tsx`). */
function OngletsControles({
  surChangement,
}: {
  readonly surChangement?: (valeur: string) => void;
}): JSX.Element {
  const [actif, setActif] = useState<string>('organisation');
  return (
    <Onglets
      libelleDeLaListe="Groupes de l'administration"
      onChangerDOnglet={(v) => {
        setActif(v);
        surChangement?.(v);
      }}
      onglets={[...ONGLETS]}
      valeurActive={actif}
    >
      Contenu de {actif}
    </Onglets>
  );
}

describe('Onglets', () => {
  it('expose une liste nommee et trois onglets avec leur libelle', () => {
    render(<OngletsControles />);
    expect(screen.getByRole('tablist', { name: "Groupes de l'administration" })).toBeTruthy();
    for (const o of ONGLETS) {
      expect(screen.getByRole('tab', { name: o.libelle })).toBeTruthy();
    }
  });

  it("l'onglet actif porte aria-selected, les deux autres non", () => {
    render(<OngletsControles />);
    expect(screen.getByRole('tab', { name: 'Organisation' }).getAttribute('aria-selected')).toBe(
      'true',
    );
    expect(screen.getByRole('tab', { name: 'Pilotage' }).getAttribute('aria-selected')).toBe(
      'false',
    );
  });

  // UN SEUL PANNEAU DANS LE DOM — le choix de conception documente dans
  // l'en-tete du composant. Si ce test echouait, les trois sections de
  // l'administration monteraient simultanement, chacune declenchant son propre
  // appel reseau.
  it('ne rend QU UN SEUL panneau, jamais un par onglet', () => {
    render(<OngletsControles />);
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
    expect(screen.getByRole('tabpanel').textContent).toBe('Contenu de organisation');
  });

  // `fireEvent.mouseDown`, PAS `fireEvent.click` — MESURE, PAS DEVINE.
  // `@radix-ui/react-tabs` active un onglet sur `onMouseDown`, jamais sur
  // `onClick` (lu dans `node_modules/@radix-ui/react-tabs/dist/index.mjs`,
  // 25/10/2026). `fireEvent.click` ne simule qu'un seul evenement `click`, sans
  // le `mousedown` qui le precede dans un vrai navigateur : le premier essai de
  // ce test restait sur l'onglet initial, en silence, pour cette raison precise.
  it('au mousedown sur un autre onglet, le contenu change ET le panneau reste unique', () => {
    render(<OngletsControles />);
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'Audit' }));
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
    expect(screen.getByRole('tabpanel').textContent).toBe('Contenu de audit');
    expect(screen.getByRole('tab', { name: 'Audit' }).getAttribute('aria-selected')).toBe('true');
  });

  it('appelle onChangerDOnglet avec la valeur activee, jamais le libelle', () => {
    const surChangement = vi.fn();
    render(<OngletsControles surChangement={surChangement} />);
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'Pilotage' }));
    expect(surChangement).toHaveBeenCalledWith('pilotage');
  });

  // LA FLECHE DROITE DEPLACE LE FOCUS — ce qu'AUCUN des deux motifs fabriques a
  // la main dans ce depot ne faisait (mesure avant d'ecrire ce composant,
  // `PageAdministration.tsx` et `PageEvenements.tsx`). C'est Radix qui le
  // fournit ; ce test confirme que le cablage ne l'a pas perdu en route.
  // RADIX DEPLACE LE FOCUS DANS UN `setTimeout`, PAS DANS LE GESTIONNAIRE
  // SYNCHRONE — mesure directe dans
  // `@radix-ui/react-roving-focus/dist/index.mjs` apres un premier echec de ce
  // test : `document.activeElement` lu immediatement apres `fireEvent.keyDown`
  // montrait encore le premier onglet. `waitFor` attend le prochain tour de
  // boucle au lieu de supposer que le deplacement est synchrone.
  it('ArrowRight deplace le focus au prochain onglet SANS l activer — mode manuel', async () => {
    render(<OngletsControles />);
    const premier = screen.getByRole('tab', { name: 'Organisation' });
    const second = screen.getByRole('tab', { name: 'Pilotage' });
    premier.focus();
    fireEvent.keyDown(premier, { key: 'ArrowRight' });
    await waitFor(() => {
      expect(document.activeElement).toBe(second);
    });
    // Le focus a bouge, mais PAS le contenu : en mode manuel, parcourir les
    // onglets au clavier ne declenche aucun appel reseau tant que rien ne
    // confirme l'intention. Voir l'en-tete du composant.
    expect(screen.getByRole('tabpanel').textContent).toBe('Contenu de organisation');
  });

  it('Entree sur l onglet focalise l active enfin — confirmation explicite requise', async () => {
    render(<OngletsControles />);
    const premier = screen.getByRole('tab', { name: 'Organisation' });
    const second = screen.getByRole('tab', { name: 'Pilotage' });
    premier.focus();
    fireEvent.keyDown(premier, { key: 'ArrowRight' });
    await waitFor(() => {
      expect(document.activeElement).toBe(second);
    });
    fireEvent.keyDown(second, { key: 'Enter' });
    expect(screen.getByRole('tabpanel').textContent).toBe('Contenu de pilotage');
  });
});
