/**
 * Liste — un choix deroulant avec son libelle.
 *
 * Chantier design systeme v2 hors lot, etape `E3` (`DEC-682`), charte 5, qui
 * decrit « Champ / Liste » d'une seule phrase : meme libelle, meme hauteur,
 * meme rayon, meme bordure, meme focus.
 *
 * UN `<select>` NATIF, ET PAS UNE LISTE REFAITE A LA MAIN
 *
 *   Une liste deroulante reconstruite en `<div role="listbox">` demanderait de
 *   reimplementer et de prouver : l'ouverture au clavier, les fleches, la
 *   recherche par frappe, l'echappement, le defilement, le rendu natif sur
 *   mobile. Le `<select>` donne tout cela, et la charte ne demande rien qu'il
 *   ne sache faire.
 *
 *   Le prix est connu : l'apparence de la liste DEROULEE appartient au systeme
 *   et ne se stylise pas. Seule la boite fermee suit la charte. Ce prix est
 *   accepte — il vaut mieux qu'un composant dont l'accessibilite dependrait de
 *   notre propre code.
 *
 * LA BORDURE SUIT L'ARBITRAGE DE `Champ` — voir son en-tete.
 */

import { useId } from 'react';
import type { ReactNode, SelectHTMLAttributes } from 'react';

export interface ProprietesListe extends Omit<
  SelectHTMLAttributes<HTMLSelectElement>,
  'className' | 'id'
> {
  /** Le libelle visible. Obligatoire, meme motif que `Champ`. */
  readonly libelle: ReactNode;
  /** Les `<option>`. */
  readonly children: ReactNode;
  /** Aide facultative, reliee par `aria-describedby`. */
  readonly aide?: ReactNode;
}

export function Liste({ libelle, children, aide, ...reste }: ProprietesListe): ReactNode {
  const identifiant = useId();
  const identifiantAide = `${identifiant}-aide`;

  return (
    <div className="ex-champ">
      <label className="ex-champ__libelle" htmlFor={identifiant}>
        {libelle}
      </label>
      <select
        className="ex-champ__saisie ex-champ__saisie--liste"
        id={identifiant}
        aria-describedby={aide === undefined ? undefined : identifiantAide}
        {...reste}
      >
        {children}
      </select>
      {aide !== undefined && (
        <p className="ex-champ__aide" id={identifiantAide}>
          {aide}
        </p>
      )}
    </div>
  );
}
