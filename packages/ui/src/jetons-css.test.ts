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
  ANNEAU_FOCUS,
  CERCLES,
  ESPACEMENTS,
  MARQUE,
  MOUVEMENT,
  OMBRES,
  RAYONS,
  TEINTES,
  THEMES,
  TYPOGRAPHIE,
} from './jetons.js';

// `?raw` de Vite plutot que `node:fs` : le contenu du fichier arrive comme une
// chaine, sans ajouter @types/node au projet. C'est Vite qui lit le disque, et
// Vitest emploie la meme chaine de transformation.
import CSS from './jetons.css?raw';

/**
 * La feuille DEPOUILLEE DE SES COMMENTAIRES.
 *
 * **CE N'EST PAS UNE COMMODITE, C'EST UN CORRECTIF.** La premiere version du
 * controle « aucun CDN » lisait la feuille brute et echouait — sur le
 * COMMENTAIRE qui explique ce que ce controle interdit, lequel cite forcement
 * `@import` et `url(https:)` pour etre comprehensible. Un garde-fou qui refuse
 * la documentation de lui-meme apprend a passer outre : §7.25 de la passation,
 * ou la meme faute avait deja ete commise deux fois.
 *
 * Le depouillement sert AUSSI le releve des declarations : un commentaire qui
 * cite un nom de variable ne doit pas etre compte comme une declaration, sans
 * quoi un jeton reellement absent pourrait etre compense par sa mention en
 * prose, et le compte paraitrait juste.
 */
const CSS_NU = CSS.replace(/\/\*[\s\S]*?\*\//g, '');

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
      ? CSS_NU.slice(0, CSS_NU.indexOf(marqueurSombre))
      : CSS_NU.slice(CSS_NU.indexOf(marqueurSombre));
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
  ['--police', TYPOGRAPHIE.pile],
  ['--police-monospace', TYPOGRAPHIE.pileMonospace],

  ['--marque-bleu', MARQUE.bleu.surface],
  ['--marque-bleu-texte', MARQUE.bleu.texte],
  ['--marque-bleu-fonce', MARQUE.bleuFonce.surface],
  ['--marque-bleu-fonce-texte', MARQUE.bleuFonce.texte],
  ['--marque-rose', MARQUE.rose.surface],
  ['--marque-rose-texte', MARQUE.rose.texte],
  ['--marque-jaune', MARQUE.jaune.surface],
  ['--marque-jaune-texte', MARQUE.jaune.texte],

  ['--teinte-bleu', TEINTES.bleu.surface],
  ['--teinte-bleu-texte', TEINTES.bleu.texte],
  ['--teinte-rose', TEINTES.rose.surface],
  ['--teinte-rose-texte', TEINTES.rose.texte],
  ['--teinte-jaune', TEINTES.jaune.surface],
  ['--teinte-jaune-texte', TEINTES.jaune.texte],
  ['--teinte-gris', TEINTES.gris.surface],
  ['--teinte-gris-texte', TEINTES.gris.texte],
  ['--teinte-gris-sourd', TEINTES.grisSourd.surface],
  ['--teinte-gris-sourd-texte', TEINTES.grisSourd.texte],

  //  LES HUIT CERCLES, SURFACE ET TEXTE. C'est ce couple-la que la charte
  //  fournie ecrivait en `var(--encre)` / `var(--titre)` : six cercles sur huit
  //  tombaient alors sous le seuil en theme sombre. Les comparer ici au
  //  TypeScript, ou ils REUTILISENT les objets de `MARQUE` et `TEINTES`,
  //  garantit qu'aucune couleur de cercle ne diverge de sa source.
  ['--cercle-produit', CERCLES.produit.surface],
  ['--cercle-produit-texte', CERCLES.produit.texte],
  ['--cercle-projet', CERCLES.projet.surface],
  ['--cercle-projet-texte', CERCLES.projet.texte],
  ['--cercle-design', CERCLES.design.surface],
  ['--cercle-design-texte', CERCLES.design.texte],
  ['--cercle-change', CERCLES.change.surface],
  ['--cercle-change-texte', CERCLES.change.texte],
  ['--cercle-data', CERCLES.data.surface],
  ['--cercle-data-texte', CERCLES.data.texte],
  ['--cercle-shield', CERCLES.shield.surface],
  ['--cercle-shield-texte', CERCLES.shield.texte],
  ['--cercle-forge', CERCLES.forge.surface],
  ['--cercle-forge-texte', CERCLES.forge.texte],
  ['--cercle-it', CERCLES.it.surface],
  ['--cercle-it-texte', CERCLES.it.texte],

  ['--fond', THEMES.clair.fond],
  ['--surface', THEMES.clair.surface],
  ['--fond-doux', THEMES.clair.fondDoux],
  ['--encre', THEMES.clair.encre],
  ['--encre-douce', THEMES.clair.encreDouce],
  ['--titre', THEMES.clair.titre],
  ['--trait', THEMES.clair.trait],
  ['--trait-fort', THEMES.clair.traitFort],
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
  ['--rayon-xl', RAYONS.xl],
  ['--rayon-pastille', RAYONS.pastille],

  ['--ombre-douce', OMBRES.douce],
  ['--ombre-posee', OMBRES.posee],

  ['--anneau-focus', ANNEAU_FOCUS.trait],
  ['--anneau-focus-decalage', ANNEAU_FOCUS.decalage],

  ['--taille-surtitre', TYPOGRAPHIE.tailles.surtitre],
  ['--taille-xs', TYPOGRAPHIE.tailles.xs],
  ['--taille-s', TYPOGRAPHIE.tailles.s],
  ['--taille-m', TYPOGRAPHIE.tailles.m],
  ['--taille-l', TYPOGRAPHIE.tailles.l],
  ['--taille-xl', TYPOGRAPHIE.tailles.xl],
  ['--taille-xxl', TYPOGRAPHIE.tailles.xxl],
  ['--taille-display', TYPOGRAPHIE.tailles.display],
  //  Les graisses sont des NOMBRES cote TypeScript et des chaines en CSS : la
  //  conversion est explicite ici plutot que laissee a une comparaison laxiste.
  ['--graisse-normale', String(TYPOGRAPHIE.graisses.normale)],
  ['--graisse-forte', String(TYPOGRAPHIE.graisses.forte)],
  ['--interlettrage-display', TYPOGRAPHIE.interlettrages.display],
  ['--interlettrage-titre', TYPOGRAPHIE.interlettrages.titre],
  ['--interlettrage-sous-titre', TYPOGRAPHIE.interlettrages.sousTitre],
  ['--interlettrage-surtitre', TYPOGRAPHIE.interlettrages.surtitre],

  ['--duree-rapide', MOUVEMENT.durees.rapide],
  ['--duree-base', MOUVEMENT.durees.base],
  ['--duree-lente', MOUVEMENT.durees.lente],
  ['--courbe-sortie', MOUVEMENT.courbes.sortie],
  ['--courbe-ressort', MOUVEMENT.courbes.ressort],
];

/**
 * Les neutres du theme sombre — LES SEULS JETONS QUI BASCULENT.
 *
 * Toute variable absente de cette liste garde sa valeur claire en theme sombre,
 * et c'est VOULU pour les surfaces de marque, les teintes et les cercles : leur
 * texte est ecrit en litteral, donc le couple reste celui qui a ete mesure. Voir
 * l'en-tete de `jetons.ts`.
 */
const SOMBRE_ATTENDUS: ReadonlyArray<readonly [string, string]> = [
  ['--fond', THEMES.sombre.fond],
  ['--surface', THEMES.sombre.surface],
  ['--fond-doux', THEMES.sombre.fondDoux],
  ['--encre', THEMES.sombre.encre],
  ['--encre-douce', THEMES.sombre.encreDouce],
  ['--titre', THEMES.sombre.titre],
  ['--trait', THEMES.sombre.trait],
  ['--trait-fort', THEMES.sombre.traitFort],
  ['--ok', THEMES.sombre.ok],
  ['--ko', THEMES.sombre.ko],
  //  ONZIEME DEPUIS `E3`, et ce n'est PAS un neutre : c'est l'anneau de focus,
  //  dont le bleu doit basculer parce que `--marque-bleu` ne rend que 2,91:1
  //  sur une surface sombre — sous le seuil de 3:1 d'un indicateur de focus.
  ['--anneau-focus', ANNEAU_FOCUS.traitSombre],
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

  it('declare les onze bascules du theme sombre, et pas davantage', () => {
    //  « ET PAS DAVANTAGE » EST LA MOITIE UTILE DE CE CONTROLE. Si une surface
    //  de marque, une teinte ou un cercle etait redeclare ici, son texte —
    //  ecrit en litteral dans `:root` — cesserait de lui correspondre, et le
    //  couple mesure ne serait plus celui qui s'affiche. C'est exactement le
    //  defaut que la charte fournie portait : six cercles sur huit sous le
    //  seuil en theme sombre.
    expect(
      SOMBRE.size,
      `variables lues dans :root[data-theme] : ${[...SOMBRE.keys()].join(', ')}`,
    ).toBe(SOMBRE_ATTENDUS.length);
  });

  it.each(SOMBRE_ATTENDUS)('%s du theme sombre vaut la meme chose', (nom, attendue) => {
    const lue = SOMBRE.get(nom);
    expect(lue, `${nom} absente du theme sombre`).toBeDefined();
    expect(
      memeValeur(lue as string, attendue),
      `${nom} sombre : CSS « ${lue} » contre TypeScript « ${attendue} »`,
    ).toBe(true);
  });

  it('ne tire aucune police d un CDN — la fonte est AUTO-HEBERGEE', () => {
    //  **CE CONTROLE A CHANGE DE SENS EN v2 SANS CHANGER D'ASSERTION.** Tant que
    //  la pile etait systeme, il ne pouvait rien attraper : aucune police
    //  n'etait chargee du tout. Depuis que Century Gothic est declaree, il
    //  garde la seule exigence qui compte — la roadmap 2.3 interdit les CDN,
    //  jamais l'auto-hebergement — et il mord vraiment.
    expect(CSS_NU).not.toMatch(/@import|url\(\s*['"]?https?:/);

    //  Et le temoin positif, sans lequel l'assertion ci-dessus serait satisfaite
    //  par une feuille qui ne declare AUCUNE police (§7.39) : les deux graisses
    //  sont bien servies, depuis un chemin RELATIF au depot.
    const fontFaces = CSS_NU.match(/@font-face/g) ?? [];
    expect(fontFaces, 'les deux graisses de Century Gothic doivent etre declarees').toHaveLength(2);
    expect(CSS_NU).toMatch(/url\('\.\.\/polices\/CenturyGothic\.ttf'\)/);
    expect(CSS_NU).toMatch(/url\('\.\.\/polices\/CenturyGothic-Bold\.ttf'\)/);
    expect(CSS_NU.match(/font-display:\s*swap/g) ?? []).toHaveLength(2);
  });
});
