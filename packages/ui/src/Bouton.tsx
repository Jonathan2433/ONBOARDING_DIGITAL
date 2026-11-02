/**
 * Bouton — composant de base du design system.
 *
 * LOT 1, sous-etape T10, story MVP-L01-US007. Cahier des charges 13.3, 14.
 * ETENDU par le chantier design systeme v2, etape `E3` (`DEC-681`), charte 5.
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
 *
 * LES QUATRE VARIANTES DE LA CHARTE 5
 *
 *   `primaire` (bleu plein), `secondaire` (surface, bordure, texte titre),
 *   `sombre` (bleu fonce plein, pour l'enchainement d'un parcours) et `discret`
 *   (transparent, texte bleu). Les quatre couples sont DEJA mesures AA :
 *   `MARQUE.bleu`, `MARQUE.bleuFonce` et `--titre` sur surface.
 *
 *   **IL N'Y A PAS DE VARIANTE ROSE, ET CE N'EST PAS UN OUBLI.** La charte 5
 *   ecrit « pas de bouton rose a texte blanc » : le rose de marque porte l'encre,
 *   jamais le blanc, sous peine de 2,9:1. L'union fermee ci-dessous rend cette
 *   interdiction STRUCTURELLE — `variante="rose"` ne compile pas — plutot que de
 *   la confier a un commentaire que personne ne relit (§7.35).
 *
 *   **`discret` BASCULE EN THEME SOMBRE.** `--marque-bleu` ne rend que 2,91:1
 *   sur une surface sombre, sous le seuil du texte ; `composants.css` lui donne
 *   `--titre` (7,44:1) sous `[data-theme='sombre']`. Meme regle que l'anneau de
 *   focus et que `Progression` — voir l'en-tete de `jetons.ts`.
 *
 * LES DEUX TAILLES, ET LA TENSION QUE LA CHARTE PORTE AVEC ELLE-MEME
 *
 *   La charte 5 donne « tailles `s` 36px / `m` 44px ». Sa propre regle 1.6 exige
 *   pourtant « cibles tactiles >= 44px ». Les deux ne peuvent pas etre vraies en
 *   meme temps pour `s`.
 *
 *   Le defaut est donc `m` : sans rien demander, on obtient la taille qui
 *   respecte 1.6. `s` reste disponible — il tient WCAG 2.2 AA (critere 2.5.8,
 *   qui exige 24x24 et non 44) — et l'ecart est consigne a `E7`. Tension signalee
 *   a Jonathan plutot que tranchee en silence.
 */

import type { ButtonHTMLAttributes, ReactNode } from 'react';

/** Les quatre variantes de la charte 5. Aucune n'est rose : voir l'en-tete. */
export type VarianteBouton = 'primaire' | 'secondaire' | 'sombre' | 'discret';

/** `m` vaut 44px — la cible tactile de la charte 1.6. `s` vaut 36px. */
export type TailleBouton = 's' | 'm';

export interface ProprietesBouton extends Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  'className'
> {
  /** Le libelle. Obligatoire : un bouton sans nom accessible n'est pas activable. */
  readonly children: ReactNode;
  /** `primaire` par defaut. */
  readonly variante?: VarianteBouton;
  /** `m` par defaut — la seule qui tienne les 44px de la charte 1.6. */
  readonly taille?: TailleBouton;
}

export function Bouton({
  children,
  variante = 'primaire',
  taille = 'm',
  type = 'button',
  ...reste
}: ProprietesBouton): ReactNode {
  return (
    <button
      className="ex-bouton"
      data-variante={variante}
      data-taille={taille}
      type={type}
      {...reste}
    >
      {children}
    </button>
  );
}
