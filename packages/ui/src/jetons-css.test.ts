/**
 * Le controle de divergence entre `jetons.ts` et `jetons.css`.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007.
 *
 * POURQUOI CE CONTROLE EXISTE
 *
 *   Les jetons vivent a deux endroits : un module TypeScript, source de verite,
 *   et une feuille de proprietes personnalisees pour le CSS. Deux copies d'une
 *   meme valeur divergent — c'est la lecon de `ECART-022`, ou `.env.example`
 *   declarait deux fois la meme variable, et de `ECART-021` sur les nombres
 *   recopies.
 *
 *   La parade n'est pas de promettre d'y penser : c'est ce controle. Il LIT les
 *   deux fichiers et echoue des qu'une valeur differe ou qu'une variable manque
 *   d'un cote. Sans lui, une couleur corrigee dans le TypeScript et oubliee dans
 *   le CSS produirait deux palettes, et le contrôle de contraste ne verrait que
 *   la premiere — donc validerait une palette qui n'est pas celle qui s'affiche.
 *
 * IL COMPTE CE QU'IL EXAMINE. Un controle qui n'annonce pas combien de couples il
 * a compares peut toujours n'en avoir compare aucun : ici, un fichier CSS vide
 * ferait passer toutes les assertions individuelles. Le compte attendu l'empeche.
 */

import { describe, expect, it } from 'vitest';

import {
  DEGRADE_MARQUE,
  ESPACEMENTS,
  MARQUE,
  OMBRES,
  RAYONS,
  THEMES,
  TYPOGRAPHIE,
} from './jetons.js';

// `?raw` de Vite plutot que `node:fs` : le contenu du fichier arrive comme une
// chaine, sans ajouter @types/node au projet. C'est Vite qui lit le disque, et
// Vitest emploie la meme chaine de transformation.
import CSS from './jetons.css?raw';

/**
 * Les declarations de `:root`, hors selecteur du theme sombre — c'est-a-dire
 * le theme clair.
 *
 * Le decoupage s'arrete au premier `:root[data-theme` : cette regle porte les
 * memes noms avec les valeurs du theme sombre, et les melanger ferait comparer
 * une valeur claire a une valeur sombre. **CE MARQUEUR A REMPLACE `@media`
 * depuis S9 (`DEC-673`)** : le sombre n'est plus active par la preference
 * systeme mais par un attribut explicite, voir l'en-tete de `jetons.css`.
 */
function declarations(portee: string): Map<string, string> {
  const marqueurSombre = ':root[data-theme';
  const bloc =
    portee === 'clair'
      ? CSS.slice(0, CSS.indexOf(marqueurSombre))
      : CSS.slice(CSS.indexOf(marqueurSombre));
  const trouvees = new Map<string, string>();
  // DECOUPAGE PAR DECLARATION, ET NON PAR LIGNE. Premiere version de ce parseur :
  // une expression reguliere ancree en debut de ligne, qui exigeait la valeur sur
  // la MEME ligne que le nom. Trois declarations de `jetons.css` s'etendent sur
  // deux lignes — la pile de polices et les deux ombres — et le controle les
  // signalait « absentes ». C'etait le PARSEUR qui etait en cause, pas la feuille,
  // et l'echec pointait donc la mauvaise cause. Une valeur CSS ne contient jamais
  // de point-virgule ici : le decoupage sur `;` est donc exact, et il est
  // indifferent aux retours a la ligne.
  for (const declaration of bloc.split(';')) {
    const m = /(--[a-z0-9-]+)\s*:\s*([\s\S]+)/.exec(declaration);
    // Les deux groupes sont gardes explicitement : `tsc` strict ne deduit pas
    // qu'une correspondance implique la presence de ses groupes captures, et il a
    // raison de ne pas le deduire — une expression modifiee pourrait les perdre.
    const nom = m?.[1];
    const valeur = m?.[2];
    if (nom !== undefined && valeur !== undefined) trouvees.set(nom, valeur.trim());
  }
  return trouvees;
}

/** Comparaison insensible a la casse et aux espaces surnumeraires. */
function memeValeur(a: string, b: string): boolean {
  const normaliser = (v: string): string => v.toLowerCase().replace(/\s+/g, ' ').trim();
  return normaliser(a) === normaliser(b);
}

const CLAIR = declarations('clair');
const SOMBRE = declarations('sombre');

/** Les couples (nom CSS, valeur attendue) derives du module TypeScript. */
const ATTENDUS: ReadonlyArray<readonly [string, string]> = [
  ['--marque-bleu', MARQUE.bleu.surface],
  ['--marque-bleu-texte', MARQUE.bleu.texte],
  ['--marque-bleu-fonce', MARQUE.bleuFonce.surface],
  ['--marque-bleu-fonce-texte', MARQUE.bleuFonce.texte],
  ['--marque-rose', MARQUE.rose.surface],
  ['--marque-rose-texte', MARQUE.rose.texte],
  ['--marque-jaune', MARQUE.jaune.surface],
  ['--marque-jaune-texte', MARQUE.jaune.texte],
  ['--degrade-marque', DEGRADE_MARQUE.css],
  ['--fond', THEMES.clair.fond],
  ['--fond-doux', THEMES.clair.fondDoux],
  ['--encre', THEMES.clair.encre],
  ['--encre-douce', THEMES.clair.encreDouce],
  ['--trait', THEMES.clair.trait],
  ['--ok', THEMES.clair.ok],
  ['--ko', THEMES.clair.ko],
  ['--espace-xs', ESPACEMENTS.xs],
  ['--espace-s', ESPACEMENTS.s],
  ['--espace-m', ESPACEMENTS.m],
  ['--espace-l', ESPACEMENTS.l],
  ['--espace-xl', ESPACEMENTS.xl],
  ['--espace-xxl', ESPACEMENTS.xxl],
  ['--rayon-s', RAYONS.s],
  ['--rayon-m', RAYONS.m],
  ['--rayon-l', RAYONS.l],
  ['--rayon-pastille', RAYONS.pastille],
  ['--ombre-douce', OMBRES.douce],
  ['--ombre-posee', OMBRES.posee],
  ['--police', TYPOGRAPHIE.pile],
  ['--police-monospace', TYPOGRAPHIE.pileMonospace],
  ['--taille-xs', TYPOGRAPHIE.tailles.xs],
  ['--taille-s', TYPOGRAPHIE.tailles.s],
  ['--taille-m', TYPOGRAPHIE.tailles.m],
  ['--taille-l', TYPOGRAPHIE.tailles.l],
  ['--taille-xl', TYPOGRAPHIE.tailles.xl],
];

const SOMBRE_ATTENDUS: ReadonlyArray<readonly [string, string]> = [
  ['--fond', THEMES.sombre.fond],
  ['--fond-doux', THEMES.sombre.fondDoux],
  ['--encre', THEMES.sombre.encre],
  ['--encre-douce', THEMES.sombre.encreDouce],
  ['--trait', THEMES.sombre.trait],
  ['--ok', THEMES.sombre.ok],
  ['--ko', THEMES.sombre.ko],
];

describe('la feuille de jetons ne divergs pas du module TypeScript', () => {
  it('declare autant de variables que le module en attend, theme clair', () => {
    // SANS CE COMPTE, un fichier CSS vide ferait passer chaque assertion
    // individuelle sur `undefined` — non, `toBe` echouerait, mais un fichier
    // AMPUTE de quelques lignes passerait pour complet si l'on ne comptait pas.
    expect(CLAIR.size, `variables lues dans :root : ${[...CLAIR.keys()].join(', ')}`).toBe(
      ATTENDUS.length,
    );
  });

  it.each(ATTENDUS)('%s vaut la meme chose des deux cotes', (nom, attendue) => {
    const lue = CLAIR.get(nom);
    expect(lue, `${nom} absente de jetons.css`).toBeDefined();
    expect(
      memeValeur(lue as string, attendue),
      `${nom} : CSS « ${lue} » contre TypeScript « ${attendue} »`,
    ).toBe(true);
  });

  it('declare les sept variables du theme sombre, et pas davantage', () => {
    expect(SOMBRE.size, `variables lues dans @media : ${[...SOMBRE.keys()].join(', ')}`).toBe(
      SOMBRE_ATTENDUS.length,
    );
  });

  it.each(SOMBRE_ATTENDUS)('%s du theme sombre vaut la meme chose', (nom, attendue) => {
    const lue = SOMBRE.get(nom);
    expect(lue, `${nom} absente du theme sombre`).toBeDefined();
    expect(
      memeValeur(lue as string, attendue),
      `${nom} sombre : CSS « ${lue} » contre TypeScript « ${attendue} »`,
    ).toBe(true);
  });

  it('ne telecharge aucune police et ne referme aucun CDN', () => {
    expect(CSS).not.toMatch(/@import|url\(\s*['"]?https?:/);
  });
});
