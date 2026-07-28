/**
 * Configuration Vite et Vitest du frontend.
 *
 * LOT 1, sous-etape T1, story MVP-L01-US001 : outillage seul.
 * Le serveur de developpement, le point d'entree `index.html` et la page de
 * statut relevent de la sous-etape T5 ; le service `web` de la stack Docker,
 * de T2.
 */
// `defineConfig` vient de `vitest/config` et non de `vite` : avec Vitest 4,
// la signature exportee par `vite` ne connait pas la cle `test`.
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
});
