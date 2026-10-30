/**
 * Le bouton de bascule clair/sombre — chantier front hors lot, S9
 * (`DEC-672`/`DEC-673`).
 *
 * DEUX EMPLACEMENTS, UN SEUL COMPOSANT — meme motif que `BoutonSignalerUnBug`
 * (§7.27)
 *
 *   L'en-tete fonctionnel de `CadreApplicatif` (visible des qu'une entite est
 *   choisie) et le bandeau de `PageNationale` (visible juste apres la
 *   connexion, avant tout choix d'entite). Ni l'un ni l'autre ne lui passe de
 *   propriete : la preference est PAR APPAREIL, jamais liee a une entite ou a
 *   un role.
 *
 * LA LOGIQUE VIT DANS `@onboarding/ui`, PAS ICI
 *
 *   `appliquerLeTheme`/`lireLeThemeStocke` (`packages/ui/src/theme.ts`)
 *   portent l'attribut `data-theme` et la memorisation ; ce composant ne fait
 *   que lire l'etat initial UNE FOIS et reagir au clic. Les icones
 *   (`lucide-react`) restent ici : ce paquet est deja une dependance de
 *   `apps/web`, pas de `packages/ui`, memes raisons que `Building2`/`icones.tsx`.
 *
 * `aria-pressed`, PAS UN SIMPLE LIBELLE QUI CHANGE
 *
 *   Un bouton a deux etats persistants est un bouton a BASCULE au sens de
 *   WCAG 4.1.2 : `aria-pressed` le dit a un lecteur d'ecran sans qu'il ait a
 *   deviner le sens du texte visible, qui change lui aussi pour rester
 *   explicite au clavier comme a l'oeil (§14.2, l'information n'est jamais
 *   portee par la seule icone).
 */
import { Moon, Sun } from 'lucide-react';
import { type JSX, useEffect, useState } from 'react';

import { appliquerLeTheme, lireLeThemeStocke, type Theme } from '@onboarding/ui';

export function BoutonBasculerTheme(): JSX.Element {
  //  **INITIALISE DEPUIS LE STOCKAGE, JAMAIS DEPUIS LE SYSTEME.** `null` veut
  //  dire « rien n'a encore ete choisi sur cet appareil », et c'est alors le
  //  clair qui s'applique — l'arbitrage du 27/10/2026, voir `theme.ts`.
  const [theme, setTheme] = useState<Theme>(() => lireLeThemeStocke() ?? 'clair');

  //  Applique a CHAQUE changement, y compris le premier rendu : le CSS seul ne
  //  sait pas encore que ce choix existe tant que l'attribut n'est pas pose.
  useEffect(() => {
    appliquerLeTheme(theme);
  }, [theme]);

  const estSombre = theme === 'sombre';

  return (
    <button
      type="button"
      className="app-bascule-theme"
      //  **LE BOUTON REPRESENTE « THEME SOMBRE », ET `aria-pressed` SUIT SON
      //  ETAT ACTUEL** — vrai quand le sombre est actif, jamais l'inverse.
      aria-pressed={estSombre}
      onClick={() => {
        setTheme(estSombre ? 'clair' : 'sombre');
      }}
    >
      {estSombre ? <Sun aria-hidden="true" size={18} /> : <Moon aria-hidden="true" size={18} />}
      {estSombre ? 'Thème clair' : 'Thème sombre'}
    </button>
  );
}
