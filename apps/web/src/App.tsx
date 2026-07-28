/**
 * Racine applicative.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002.
 *
 * Il n'y a volontairement AUCUN routeur : `DEC-456` n'installe pas React Router
 * avant le LOT 4, faute d'usage. Le LOT 1 n'a qu'une seule page, et la
 * navigation appartient au LOT 4.
 *
 * La frontiere d'erreur enveloppe la page et non l'inverse : une exception levee
 * dans `PageStatut` doit etre rattrapee au-dessus d'elle (cahier §17.4).
 */
import type { JSX } from 'react';

import { FrontiereErreur } from './FrontiereErreur';
import { PageStatut } from './pages/PageStatut';

export function App(): JSX.Element {
  return (
    <FrontiereErreur>
      <PageStatut />
    </FrontiereErreur>
  );
}
