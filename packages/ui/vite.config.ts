/**
 * Configuration Vitest du design system.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007.
 *
 * Elle reprend celle de `apps/web` plutot que d'en inventer une autre : les deux
 * paquets rendent du JSX et emploient Testing Library, et deux configurations de
 * test qui divergent finissent par produire des resultats qu'on ne peut plus
 * comparer. Trois reglages y sont repris pour les memes motifs mesures en `T5` :
 *
 *   - `defineConfig` vient de `vitest/config` et non de `vite` : avec Vitest 4,
 *     la signature exportee par `vite` ne connait pas la cle `test` ;
 *   - `environment: 'jsdom'` — Testing Library a besoin d'un DOM (`DEC-471`) ;
 *   - `restoreMocks` et `unstubGlobals` — un test qui laisse fuir son bouchon
 *     fait passer ou echouer le suivant pour une raison invisible.
 *
 * Ce paquet n'a PAS de serveur de developpement : il n'est pas une application.
 * Aucune cle `server` n'est donc declaree.
 */
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],

  test: {
    environment: 'jsdom',

    // `css: true` N'EST PAS DECORATIF, et c'est une mesure, pas une supposition.
    //
    // Deux controles de ce paquet LISENT les feuilles de style pour verifier
    // qu'elles ne divergent pas des jetons et qu'elles ne contournent pas les
    // variables. Ils les importent en `?raw`.
    //
    // Vitest neutralise les imports CSS par defaut : `css` vaut `false`, et tout
    // import d'une feuille rend une chaine VIDE — y compris en `?raw`. Mesure du
    // 30/07/2026 : 45 tests en echec, « expected 0 to be greater than 20 » et
    // « expected '' to contain :focus-visible ». Les controles etaient donc muets
    // sans etre absents, ce qui est le pire des deux — ils auraient pu passer sur
    // une feuille vide si le compte n'avait pas ete confronte a un attendu.
    css: true,

    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    restoreMocks: true,
    unstubGlobals: true,
  },
});
