/**
 * CaseACocher — une case et son libelle.
 *
 * Chantier design systeme v2 hors lot, etape `E3` (`DEC-682`), charte 5 et 6.7.
 *
 * UNE VRAIE `<input type="checkbox">`, ET `accent-color` PLUTOT QU'UN DESSIN
 *
 *   La charte 5 demande « 20px, cochee = fond bleu + coche blanche ». La facon
 *   habituelle d'y arriver est `appearance: none` puis un dessin maison : une
 *   coche en pseudo-element, ou une image SVG encodee dans la feuille. Les deux
 *   ont un cout reel ici — la seconde ecrirait une couleur EN DUR dans
 *   `composants.css`, ce que le controle des jetons refuse a juste titre ; la
 *   premiere fait perdre l'etat `indeterminate` et le rendu natif des reglages
 *   de contraste eleve du systeme.
 *
 *   `accent-color: var(--marque-bleu)` donne exactement ce que la charte decrit
 *   — fond bleu, coche blanche — en laissant le navigateur dessiner. L'etat
 *   coche reste donc celui du systeme, y compris en contraste eleve et en mode
 *   force colors.
 *
 * LE LIBELLE ENVELOPPE LA CASE
 *
 *   `<label><input/> texte</label>` relie les deux SANS identifiant : la cible
 *   de clic couvre le texte, et il n'y a pas d'`id` a tenir unique. C'est la
 *   seule forme qui n'ait aucune facon de se desynchroniser.
 *
 *   **LA CASE RESTE NATIVE**, donc Espace la coche, Tab l'atteint, et son etat
 *   est annonce — rien de tout cela n'est reimplemente ici.
 *
 * TERMINE N'EST JAMAIS VERT
 *
 *   La charte 6.7 est explicite : une tache terminee se signale par un fond
 *   `--teinte-bleu` et un texte barre, « jamais vert ». `--ok` est borne a la
 *   page de statut (charte 2). Le barre n'est pas une couleur : il reste
 *   perceptible sans distinguer les teintes, et le libelle, lui, ne change pas.
 */

import type { InputHTMLAttributes, ReactNode } from 'react';

export interface ProprietesCaseACocher extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'className' | 'type'
> {
  /** Le libelle visible. Obligatoire : une case sans nom n'est pas cochable. */
  readonly libelle: ReactNode;
}

export function CaseACocher({ libelle, ...reste }: ProprietesCaseACocher): ReactNode {
  return (
    <label className="ex-case">
      <input className="ex-case__boite" type="checkbox" {...reste} />
      <span className="ex-case__libelle">{libelle}</span>
    </label>
  );
}
