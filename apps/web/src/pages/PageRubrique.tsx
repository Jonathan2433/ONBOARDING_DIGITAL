/**
 * Une rubrique dont le contenu appartient a un lot ulterieur — LOT 4, `T4`.
 *
 * POURQUOI CES PAGES EXISTENT PLUTOT QUE DES LIENS QUI TOMBENT EN 404
 *
 *   Le critere de `T4` exige que **toutes** les actions du menu soient
 *   atteignables au clavier. Un lien qui aboutit au fourre-tout `404` est
 *   atteignable et **inutile** : la navigation ne serait pas prouvee, elle serait
 *   simulee.
 *
 *   Ces pages ne portent donc aucun contenu metier -- le §8.4 donne l'ordre des
 *   sections de l'accueil, et tout cela appartient aux LOTS 5 a 9. Elles disent
 *   **quel lot** l'apportera, ce qui est une information vraie et utile, plutot
 *   qu'un ecran vide qui laisserait croire a une panne.
 *
 * LE TITRE VIENT DU CADRE, PAS D'ICI
 *
 *   Le cadre porte l'unique `<h1>` du document et le derive de `RUBRIQUES`. Une
 *   page qui ecrirait le sien en donnerait deux, ce que `jsx-a11y` ne verifie pas
 *   parce que c'est une regle de document et non de JSX.
 */
import type { JSX } from 'react';

import { useEntiteConsultee } from './CadreApplicatif';

export interface ProprietesRubrique {
  readonly libelle: string;
  readonly lot: string;
}

export function PageRubrique({ libelle, lot }: ProprietesRubrique): JSX.Element {
  const { entite } = useEntiteConsultee();

  return (
    <p className="app-message" data-ton="neutre" data-rubrique={libelle}>
      La rubrique {libelle} de {entite.nom} arrive au {lot}. La navigation, elle, est en place :
      cette page est atteignable au clavier comme les autres.
    </p>
  );
}
