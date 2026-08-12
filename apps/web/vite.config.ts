/**
 * Configuration Vite et Vitest du frontend.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002.
 */
// `defineConfig` vient de `vitest/config` et non de `vite` : avec Vitest 4,
// la signature exportee par `vite` ne connait pas la cle `test`.
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],

  server: {
    // `0.0.0.0` et non le defaut `localhost` : dans un conteneur, un serveur lie
    // a la boucle locale n'est joignable par personne, pas meme par Caddy.
    host: '0.0.0.0',
    port: 5173,

    // Sans `strictPort`, Vite se rabat silencieusement sur le port suivant
    // quand 5173 est pris. Caddy mandate `web:5173` et le healthcheck sonde
    // 5173 : un repli silencieux produirait un 502 sans cause visible. Mieux
    // vaut un demarrage qui echoue bruyamment.
    strictPort: true,

    // Vite 8 installe un controle d'hote des lors que le serveur n'est PAS
    // lui-meme en HTTPS — c'est notre cas, Caddy termine TLS et mandate en
    // clair. Sans cette liste, l'en-tete `Host: app.onboarding.localhost`
    // est refuse : « Blocked request. This host is not allowed. » Verifie dans
    // le code de vite 8.1.5 installe, pas suppose.
    allowedHosts: ['app.onboarding.localhost'],
  },

  test: {
    // `jsdom` et non `node` : Testing Library a besoin d'un DOM. Le cahier
    // §17.1 impose Testing Library, la fiche §6 impose d'eprouver les trois
    // etats de la page. `DEC-471` motive le choix de jsdom.
    environment: 'jsdom',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],

    // Un test qui laisse fuir son bouchon fait passer ou echouer le suivant
    // pour une raison invisible. Les deux reglages rendent l'isolation
    // automatique plutot que dependante de la rigueur de chaque test.
    restoreMocks: true,
    unstubGlobals: true,
  },
});
