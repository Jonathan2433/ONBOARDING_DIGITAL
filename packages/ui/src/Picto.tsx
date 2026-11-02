/**
 * Picto — les pictogrammes officiels eXalt, en SVG local.
 *
 * Chantier design systeme v2 hors lot, etape `E2` (`DEC-681`). Charte 1.4, 4, 6, 7.
 *
 * IL REMPLACE LES EMOJI, ET C'EST UNE REGLE NON NEGOCIABLE
 *
 *   Charte 1.4 : « Pas d'emoji. Les pictogrammes officiels eXalt les
 *   remplacent. » Un emoji n'est pas un dessin mais un CARACTERE : sa forme
 *   depend de la police du systeme, un lecteur d'ecran l'annonce par son nom
 *   Unicode (« fusee » lu au milieu d'une phrase), et sa couleur echappe au
 *   theme. Les douze icones de `pictos.ts` n'ont aucun de ces defauts.
 *
 * DECORATIF PAR DEFAUT, ET CE DEFAUT EST LE BON
 *
 *   Charte 1.3 : « le mot porte le sens ; la couleur n'est qu'un renfort ». La
 *   meme chose vaut du dessin. Relu une par une, CHACUNE des cinq apparitions
 *   que la spec decrit accompagne un libelle visible — tuile « Vie eXalt » (6.2),
 *   bloc « Vision » (6.5), bandeau « Parcours · En mission » (6.7), tuile de
 *   cercle avec son nom (6.4), etat vide avec son titre (7).
 *
 *   Un picto qui s'annoncerait en plus du libelle ferait donc entendre deux fois
 *   la meme information : `aria-hidden` est la bonne reponse, pas un oubli. Le
 *   temoin decisif de `Picto.test.tsx` le mesure la ou cela compte — le nom
 *   accessible d'un bouton qui porte un picto vaut EXACTEMENT son libelle.
 *
 *   `titre` est l'echappatoire pour le cas inverse, un picto SEUL sans texte a
 *   cote. Il n'est employe par aucun ecran a ce jour, et il est quand meme
 *   fourni : sans lui, le premier qui en aura besoin posera un `aria-label` sur
 *   le `<svg>` — ou il est IGNORE, faute de `role`. Donner le chemin juste, et
 *   l'eprouver, vaut mieux que de laisser inventer le chemin faux.
 *
 * LA COULEUR N'EST PAS ICI, ET C'EST STRUCTUREL
 *
 *   Le `<svg>` porte `fill="currentColor"` et les courbes ne portent aucun
 *   `fill` — le generateur REFUSE une icone qui en porterait un. Un picto prend
 *   donc la couleur de texte de son contexte : pose sur la surface d'un cercle,
 *   il prend le texte apparie de ce cercle, sans qu'aucun couple ne soit
 *   redeclare. C'est ce qui permet a la charte 4 de ne donner qu'un nom de picto
 *   par cercle, jamais une couleur.
 *
 * LA TAILLE EST UN ENSEMBLE FERME, ET C'EST LA CHARTE 4 RENDUE STRUCTURELLE
 *
 *   « taille >= 24px » est une regle qu'un commentaire ne tient pas. Les cinq
 *   valeurs admises sont celles que la spec emploie reellement — 24 (le
 *   plancher), 32 (cartes de bureau, 6.5), 40 (bloc Vision, 6.5), 44 (tuile de
 *   cercle, 6.4), 48 (etat vide, 7). Ecrire `taille={16}` ne compile pas, et
 *   ajouter une sixieme valeur est une ligne visible en relecture plutot qu'un
 *   nombre magique au fond d'un ecran.
 *
 *   Le `viewBox` reste celui de l'icone, rarement carre (`0 0 58.05 63.95` pour
 *   la fusee). `preserveAspectRatio` n'est jamais pose, donc il vaut son defaut
 *   `xMidYMid meet` : le dessin est inscrit dans le carre demande, centre, sans
 *   deformation. Le poser a `none` etirerait les icones — un test l'interdit.
 *
 * AUCUNE PROPRIETE LIBRE, PAS MEME `className`
 *
 *   Meme parti que `Badge` : ce qu'un appelant peut passer est ferme. Un
 *   `fill="red"` ou un `style` arbitraire traverserait la charte sans qu'aucun
 *   controle de jetons ne le voie — c'est exactement ce que `make ecrans-check`
 *   cherche dans les feuilles, et qu'il ne saurait pas lire dans du JSX.
 */

import type { ReactNode } from 'react';

import { PICTOS, type ClePicto } from './pictos.js';

/** Les tailles que la spec emploie. Le plancher de la charte 4 est le minimum. */
export type TaillePicto = 24 | 32 | 40 | 44 | 48;

export interface ProprietesPicto {
  /** La cle du pictogramme. Un nom inconnu ne compile pas. */
  readonly nom: ClePicto;
  /** 24 par defaut — le plancher de la charte 4. */
  readonly taille?: TaillePicto;
  /**
   * Le nom accessible, pour un picto SEUL, sans libelle visible a cote.
   * Omis — le cas normal — le picto est decoratif et n'est pas annonce.
   */
  readonly titre?: string;
}

export function Picto({ nom, taille = 24, titre }: ProprietesPicto): ReactNode {
  const { viewBox, chemins } = PICTOS[nom];

  //  Deux regimes exclusifs, jamais melanges : `aria-hidden` ET `role="img"` sur
  //  le meme noeud donnent un element annonce par certaines technologies et tu
  //  par d'autres, donc un comportement qu'aucun test ne decrit.
  const accessibilite =
    titre === undefined
      ? ({ 'aria-hidden': true } as const)
      : ({ role: 'img', 'aria-label': titre } as const);

  return (
    <svg
      className="ex-picto"
      viewBox={viewBox}
      width={taille}
      height={taille}
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      {...accessibilite}
    >
      {chemins.map((courbe, rang) => (
        //  Le rang EST l'identite : la liste vient d'un module engendre, elle ne
        //  se reordonne ni ne se filtre jamais. Prendre la courbe elle-meme pour
        //  cle ferait d'une chaine de 2 500 caracteres un identifiant React.
        <path key={rang} d={courbe} />
      ))}
    </svg>
  );
}
