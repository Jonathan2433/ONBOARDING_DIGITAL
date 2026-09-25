/**
 * L'icone d'un lien interne — LOT 6, `T10`, `MVP-L06-US005`, `QO-123`.
 *
 * `reference_d_icone` EST UNE DONNEE OPAQUE, ET C'EST DELIBERE
 *
 *   Le modele §15.3 nomme le champ et ne dit rien de son contenu — ni
 *   bibliotheque, ni convention de nommage, ni caractere obligatoire ou
 *   facultatif par `link_type`. `QO-123` porte la question a Lea, avec
 *   Jonathan pour la bibliotheque : `lucide-react` est le choix retenu, en
 *   attendant la convention.
 *
 *   **CET ECRAN NE TRANCHE DONC PAS DE CONVENTION** : le champ reste un texte
 *   libre, que l'utilisateur tape lui-meme — le nom d'une icone `lucide-react`,
 *   en kebab-case (ex. `link`, `book-open`). Imposer une liste fermee ou un
 *   mappage par type de lien serait inventer ce que le corpus ne decide pas
 *   (§6.5).
 *
 * CHARGEMENT PARESSEUX, ET UN NOM INCONNU NE FAIT RIEN
 *
 *   `DynamicIcon` de `lucide-react/dynamic` importe l'icone A LA DEMANDE :
 *   aucune des ~1500 icones n'entre dans le paquet tant qu'un lien ne la
 *   reference pas. Un nom qui ne correspond a aucune icone connue ne leve pas —
 *   l'ecran affiche alors le lien SANS icone, plutot que de le faire echouer
 *   pour un champ facultatif.
 */
import type { JSX } from 'react';

import { DynamicIcon, dynamicIconImports, type IconName } from 'lucide-react/dynamic';

/** `null` si la reference est absente ou ne correspond a aucune icone connue. */
export function nomDIconeValide(reference: string | null): IconName | null {
  if (reference === null || !(reference in dynamicIconImports)) {
    return null;
  }
  return reference as IconName;
}

export interface ProprietesIconeDeLien {
  readonly reference: string | null;
  readonly taille?: number;
}

export function IconeDeLien({ reference, taille = 20 }: ProprietesIconeDeLien): JSX.Element | null {
  const nom = nomDIconeValide(reference);
  if (nom === null) {
    return null;
  }
  return <DynamicIcon aria-hidden="true" name={nom} size={taille} />;
}
