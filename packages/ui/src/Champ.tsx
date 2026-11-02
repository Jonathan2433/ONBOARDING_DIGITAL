/**
 * Champ — une saisie avec son libelle.
 *
 * Chantier design systeme v2 hors lot, etape `E3` (`DEC-681`), charte 5.
 *
 * LE LIBELLE EST UN VRAI `<label for>`, ET C'EST TOUT L'INTERET DU COMPOSANT
 *
 *   Un `aria-label` serait invisible a l'oeil ; un texte pose a cote sans
 *   `for` ne serait relie a rien ; un `placeholder` disparait des qu'on tape et
 *   n'est pas un nom accessible. Le `<label for>` natif donne les trois choses
 *   qu'il faut d'un coup : le nom accessible, l'annonce au lecteur d'ecran, et
 *   l'agrandissement de la cible — cliquer le libelle met le focus dans le
 *   champ (WCAG 1.3.1, 3.3.2, 2.5.8).
 *
 *   `useId` et non un compteur : deux champs rendus cote a cote doivent porter
 *   des identifiants distincts, y compris en rendu concurrent. Meme montage que
 *   `Carte`.
 *
 * L'AIDE ET L'ERREUR SONT RELIEES, PAS SEULEMENT AFFICHEES
 *
 *   `aria-describedby` rattache le texte d'aide au champ : sans lui, un lecteur
 *   d'ecran annonce le nom du champ et rien d'autre, et l'aide reste un
 *   paragraphe orphelin que personne n'entend au bon moment.
 *
 *   Une erreur pose EN PLUS `aria-invalid`. **L'ERREUR N'EST JAMAIS PORTEE PAR
 *   LA SEULE COULEUR** (WCAG 1.4.1) : c'est le message qui l'enonce, la bordure
 *   ne fait que le renforcer.
 *
 * LA BORDURE N'EST PAS CELLE QUE LA CHARTE ECRIT, ET C'EST UN ARBITRAGE
 *
 *   La charte 5 demande « bordure trait-fort ». Mesure : 1,44:1 en theme clair
 *   et 1,93:1 en sombre, quand WCAG 1.4.11 exige 3:1 pour la limite d'un
 *   composant de saisie — autrement dit une bordure qu'on ne voit pas.
 *   Arbitrage explicite de Jonathan du 02/11/2026 : `--encre-douce` la remplace
 *   (4,96:1 et 5,81:1). Ecart consigne a `E7`.
 */

import { useId } from 'react';
import type { InputHTMLAttributes, ReactNode } from 'react';

export interface ProprietesChamp extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'className' | 'id'
> {
  /** Le libelle visible. Obligatoire : un champ sans nom n'est pas remplissable. */
  readonly libelle: ReactNode;
  /** Aide facultative, reliee au champ par `aria-describedby`. */
  readonly aide?: ReactNode;
  /** Message d'erreur. Present, il pose aussi `aria-invalid`. */
  readonly erreur?: ReactNode;
}

export function Champ({ libelle, aide, erreur, ...reste }: ProprietesChamp): ReactNode {
  const identifiant = useId();
  const identifiantAide = `${identifiant}-aide`;
  const identifiantErreur = `${identifiant}-erreur`;

  //  Les deux descriptions sont CUMULEES quand les deux existent : `aria-describedby`
  //  accepte plusieurs identifiants, et n'en garder qu'un ferait disparaitre
  //  l'aide des qu'une erreur survient — au moment ou elle sert le plus.
  const descriptions = [
    aide === undefined ? undefined : identifiantAide,
    erreur === undefined ? undefined : identifiantErreur,
  ].filter((valeur): valeur is string => valeur !== undefined);

  return (
    <div className="ex-champ" data-erreur={erreur === undefined ? 'non' : 'oui'}>
      <label className="ex-champ__libelle" htmlFor={identifiant}>
        {libelle}
      </label>
      <input
        className="ex-champ__saisie"
        id={identifiant}
        aria-describedby={descriptions.length === 0 ? undefined : descriptions.join(' ')}
        aria-invalid={erreur === undefined ? undefined : true}
        {...reste}
      />
      {aide !== undefined && (
        <p className="ex-champ__aide" id={identifiantAide}>
          {aide}
        </p>
      )}
      {erreur !== undefined && (
        <p className="ex-champ__erreur" id={identifiantErreur}>
          {erreur}
        </p>
      )}
    </div>
  );
}
