/**
 * Configuration ESLint du monorepo - format « flat config ».
 *
 * LOT 1, sous-etape T1, story MVP-L01-US001. Decision DEC-451.
 *
 * Repartition des roles, volontaire :
 *   - la verification de types est faite par `tsc --noEmit` avec la
 *     configuration stricte de tsconfig.base.json (cahier 17.1) ;
 *   - ESLint porte les regles de lint, dont l'accessibilite JSX ;
 *   - Prettier porte le formatage. `eslint-config-prettier` desactive les
 *     regles ESLint qui entreraient en conflit, et doit rester EN DERNIER.
 *
 * eslint-plugin-jsx-a11y est la raison d'etre du choix d'ESLint plutot que
 * d'un outil unifie : le cahier des charges 14 fait de l'accessibilite une
 * exigence dure, auditee au LOT 12.
 */
import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '**/coverage/**',
      '.venv/**',
      'docs/prototype/**',
      // Copies de conflit iCloud : « node_modules 2 » et assimiles.
      '**/* [0-9]/**',
      '**/* [0-9][0-9]/**',
    ],
  },

  js.configs.recommended,
  tseslint.configs.recommended,

  // Fichiers d'outillage : ils s'executent sous Node.
  {
    files: ['*.js', '*.config.js', '**/*.config.ts'],
    languageOptions: { globals: { ...globals.node } },
  },

  // Code du frontend : il s'execute dans le navigateur.
  {
    files: ['apps/web/src/**/*.{ts,tsx}', 'packages/*/src/**/*.{ts,tsx}'],
    languageOptions: { globals: { ...globals.browser } },
  },

  // Accessibilite : uniquement la ou il y a du JSX.
  {
    files: ['**/*.{jsx,tsx}'],
    ...jsxA11y.flatConfigs.recommended,
  },

  // `configs.flat.recommended` et non `configs['recommended-latest']` : ce
  // dernier est encore au format eslintrc, qu'ESLint 10 refuse.
  reactHooks.configs.flat.recommended,

  // Doit rester le dernier element : desactive les regles conflictuelles.
  prettier,
);
