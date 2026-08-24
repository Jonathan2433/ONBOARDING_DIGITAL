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
 *
 * LE GARDE-FOU DE ROUTE EST ERGONOMIQUE, ET LA ROADMAP L'ECRIT AINSI — LOT 4, `T9`
 *
 *   « **route guards uniquement ergonomiques** », et « contrôles d'autorisation
 *   systématiques dans l'**API** ». La matrice §2.6 dit la meme chose autrement :
 *   « le frontend peut masquer ou afficher les actions pour ameliorer
 *   l'experience, mais **l'API reste l'autorite finale** ».
 *
 *   **Masquer un menu ne protege RIEN, et cette page le dit a l'utilisateur.**
 *   Une adresse tapee a la main atteint la route ; ce qu'elle rencontre ici est
 *   une explication, pas une barriere. La barriere est cote API, et le §24.20 en
 *   fait un controle d'acceptation : « les actions interdites sont refusees cote
 *   API, **meme si la requete est construite manuellement** ».
 *
 *   **Le message ne dit donc PAS « acces refuse ».** Il dirait faux : rien n'a ete
 *   refuse, la page s'affiche. Il dit ce qui est vrai -- la rubrique n'est pas
 *   ouverte a cet appelant dans cette entite -- et **pourquoi** : le §5.1, dont
 *   les responsabilites ne s'appliquent pas hors de l'entite principale.
 */
import type { JSX } from 'react';

import { droitsDeNavigation, RUBRIQUES, rubriqueEstVisible } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';

export interface ProprietesRubrique {
  readonly libelle: string;
  readonly lot: string;
  /** La clé de `RUBRIQUES`, pour retrouver la condition du §8.2. */
  readonly cle: string;
}

export function PageRubrique({ libelle, lot, cle }: ProprietesRubrique): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const rubrique = RUBRIQUES.find((candidate) => candidate.cle === cle);

  //  **LE MEME PREDICAT QUE LE MENU, PAS UN SECOND.** Un garde-fou de route qui
  //  raisonnerait autrement que le menu produirait le cas le plus deroutant : une
  //  rubrique visible qu'on ne peut pas ouvrir, ou l'inverse.
  const ouverte =
    rubrique === undefined ||
    rubriqueEstVisible(rubrique, droitsDeNavigation(permissions?.roles ?? null));

  if (!ouverte) {
    return (
      <p className="app-message" data-ton="neutre" data-rubrique-fermee={libelle} role="status">
        La rubrique {libelle} n&rsquo;est pas ouverte pour vous dans {entite.nom}.{' '}
        {permissions !== null && !permissions.estEntitePrincipale
          ? "Ce n'est pas votre entite principale, et vos responsabilites ne s'y appliquent pas."
          : 'Elle depend de permissions que votre compte ne porte pas ici.'}{' '}
        Cet ecran est une explication, pas une barriere : c&rsquo;est l&rsquo;API qui refuse les
        actions non autorisees, meme demandees directement.
      </p>
    );
  }

  return (
    <p className="app-message" data-ton="neutre" data-rubrique={libelle}>
      La rubrique {libelle} de {entite.nom} arrive au {lot}. La navigation, elle, est en place :
      cette page est atteignable au clavier comme les autres.
    </p>
  );
}
