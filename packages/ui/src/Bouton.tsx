/**
 * Bouton — composant de base du design system.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 13.3, 14.
 *
 * UN VRAI `<button>`, ET C'EST UN CHOIX
 *
 *   Pas un `<div onClick>`. Un bouton natif porte gratuitement ce qu'il faudrait
 *   sinon reimplementer et prouver : le role, l'activation au clavier par Entree
 *   ET par Espace, la participation a l'ordre de tabulation, l'etat desactive
 *   annonce aux technologies d'assistance. Le cahier 14 impose WCAG 2.2 AA ;
 *   partir du natif est la facon la moins risquee d'y arriver.
 *
 * LE PIEGE DE `type`, ET IL EST REEL
 *
 *   Le defaut de HTML pour `<button>` dans un formulaire est `submit`. Un bouton
 *   « Annuler » place dans un formulaire soumettrait donc le formulaire. Ce
 *   composant met `button` par defaut, et `composants.test.tsx` le verifie.
 *   L'appelant peut toujours demander `submit` explicitement.
 */

import type { ButtonHTMLAttributes, ReactNode } from 'react';

/** Les deux variantes de `T10`. D'autres viendront avec les ecrans metier. */
export type VarianteBouton = 'primaire' | 'secondaire';

export interface ProprietesBouton extends Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  'className'
> {
  /** Le libelle. Obligatoire : un bouton sans nom accessible n'est pas activable. */
  readonly children: ReactNode;
  /** `primaire` par defaut. */
  readonly variante?: VarianteBouton;
}

export function Bouton({
  children,
  variante = 'primaire',
  type = 'button',
  ...reste
}: ProprietesBouton): ReactNode {
  return (
    <button className="ex-bouton" data-variante={variante} type={type} {...reste}>
      {children}
    </button>
  );
}
