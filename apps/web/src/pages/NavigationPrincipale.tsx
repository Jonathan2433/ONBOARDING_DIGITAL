/**
 * Le menu principal — LOT 4, `T4`, story `MVP-L04-US004`, cahier §8.2.
 *
 * TOUT EST ATTEIGNABLE AU CLAVIER PARCE QUE TOUT EST UN LIEN
 *
 *   Le critere de sortie exige « **toutes** les actions atteignables au clavier ·
 *   aucun piege de focus · l'ordre de tabulation suit l'ordre visuel ». La facon
 *   de le tenir n'est pas d'ajouter des gestionnaires de touches : c'est de
 *   n'employer que des elements **nativement focusables**.
 *
 *   Six `<Link>`, donc six `<a href>`. Le navigateur les met dans l'ordre du DOM,
 *   qui est l'ordre visuel, et aucun code ne touche au focus -- donc **aucun piege
 *   n'est possible**. C'est le §7.2 : changer de forme plutot que promettre de
 *   l'attention. Un menu bati sur des `<div onClick>` aurait exige `tabindex`, des
 *   gestionnaires de fleches et un piege a eviter ; celui-ci n'a rien de tout cela
 *   a se rappeler.
 *
 *   **AUCUN `tabindex` POSITIF**, et le controle l'exige : un `tabindex="1"`
 *   sortirait l'element de l'ordre du document et ferait sauter le focus.
 *
 * `aria-current="page"` PLUTOT QU'UNE SEULE CLASSE
 *
 *   Le §14.2 interdit qu'une information soit « portee uniquement par la
 *   couleur ». Un menu qui ne signalerait la page courante que par une teinte
 *   serait exactement cela. `aria-current` la porte pour les technologies
 *   d'assistance, et la feuille de style **s'appuie sur cet attribut** plutot que
 *   sur une classe : l'etat visuel et l'etat annonce ne peuvent pas diverger.
 *
 * DEUX RUBRIQUES SONT CONDITIONNELLES, ET ABSENTES PAR DEFAUT
 *
 *   Le detail est dans `routes.ts`, au-dessus de `RUBRIQUES`. Ni le parcours actif
 *   ni les permissions de l'appelant ne sont calculables au `T4` -- aucune table
 *   de parcours n'existe, et aucune route ne rend les roles. **Le defaut est donc
 *   l'absence**, ce qui est le « refus par defaut » du §20.1 : une rubrique montree
 *   a tort suggere un droit qu'on n'a pas.
 *
 *   `T9` branchera la source. Les proprietes existent des maintenant pour que les
 *   tests eprouvent **les deux** etats, et non le seul etat courant.
 */
import type { JSX } from 'react';
import { NavLink } from 'react-router';

import { cheminDeRubrique, RUBRIQUES } from '../routes';

export interface ProprietesNavigation {
  /** Le `code` de l'entite consultee. */
  readonly code: string;
  /**
   * L'appelant a-t-il un parcours actif ? §8.2, « Mon onboarding ».
   * **Faux par defaut** : aucune table de parcours n'existe avant le LOT 7.
   */
  readonly aUnParcoursActif?: boolean;
  /**
   * L'appelant voit-il l'Administration ? §8.2, et matrice §5 ligne
   * « Administration » : `—` pour `ANON`, `EMP` et `NEW`.
   * **Faux par defaut** : aucune route ne rend les roles avant `T9`.
   */
  readonly peutAdministrer?: boolean;
}

export function NavigationPrincipale({
  code,
  aUnParcoursActif = false,
  peutAdministrer = false,
}: ProprietesNavigation): JSX.Element {
  const visibles = RUBRIQUES.filter((rubrique) => {
    if (rubrique.cle === 'monOnboarding') {
      return aUnParcoursActif;
    }
    if (rubrique.cle === 'administration') {
      return peutAdministrer;
    }
    return true;
  });

  return (
    //  `aria-label` parce qu'il y aura un second repere de navigation a `T5`, la
    //  barre inferieure : deux `<nav>` sans nom seraient indistinguables pour un
    //  lecteur d'ecran.
    <nav className="app-navigation" aria-label="Menu principal">
      <ul className="app-navigation-liste">
        {visibles.map((rubrique) => (
          <li key={rubrique.cle}>
            <NavLink
              className="app-navigation-lien"
              to={cheminDeRubrique(code, rubrique.suffixe)}
              //  `end` sur l'accueil SEULEMENT : sans lui, `/entites/x` serait
              //  considere actif sur `/entites/x/framework`, et DEUX rubriques
              //  porteraient `aria-current` en meme temps.
              //  `aria-current="page"` est pose par `NavLink` LUI-MEME quand le
              //  lien est actif. L'ecrire a la main le figerait.
              end={rubrique.suffixe === ''}
            >
              {rubrique.libelle}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
