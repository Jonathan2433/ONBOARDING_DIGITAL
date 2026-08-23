/**
 * La barre de navigation inferieure — LOT 4, `T5`, story `MVP-L04-US003`.
 *
 * CE QUE LE CAHIER DIT, ET CE QU'IL LAISSE MESURER
 *
 *   §8.2 : « Sur mobile, une barre de navigation inferieure est utilisee. Les
 *   fonctions secondaires sont regroupees dans un acces "Plus" **lorsque
 *   necessaire**. »
 *
 *   `US003` : « Les **rubriques principales** restent accessibles a 320 et 390
 *   px ; le focus et les libelles sont corrects. »
 *
 *   « Lorsque necessaire » n'est ni un gout ni une supposition : c'est une
 *   MESURE. Faite le 23/08/2026 dans un vrai navigateur, a `--taille-xs` = 12 px
 *   avec la police reelle :
 *
 *       libelle              largeur
 *       Accueil                 44 px
 *       Framework               66 px
 *       Evenements              73 px
 *       Administration          87 px
 *       Trombinoscope           92 px
 *       Mon onboarding          96 px
 *
 *       cellules a 320 px    largeur    resultat
 *       4                      80 px    « Trombinoscope » passe sur 2 lignes
 *       6                      53 px    « Mon onboarding » passe sur 3 LIGNES
 *
 *   **Quatre cellules tiennent, six non.** La barre porte donc les QUATRE
 *   rubriques inconditionnelles, et « Plus » apparait des qu'une conditionnelle
 *   existe -- ce qui est exactement « lorsque necessaire », mesure a l'appui.
 *
 *   Et les libelles ne sont ni tronques ni abreges : `US003` exige qu'ils soient
 *   « corrects ». Un « Trombi... » ne l'est pas, et abreger en « Trombi » serait
 *   inventer un libelle que le §8.2 ne donne pas.
 *
 * `<details>` PLUTOT QU'UN BOUTON ET UN PANNEAU, ET C'EST LE §7.2
 *
 *   Un `<button aria-expanded>` avec son panneau exigerait de gerer l'ouverture,
 *   la fermeture par `Escape`, et le RETOUR du focus au bouton -- c'est-a-dire
 *   exactement le terrain ou naissent les pieges de focus que `T4` a pris soin de
 *   rendre impossibles.
 *
 *   `<details>`/`<summary>` est nativement focusable, s'ouvre au clavier par
 *   `Entree` et par `Espace`, et **aucun code ne touche au focus** -- donc aucun
 *   piege n'est possible. Changer de forme plutot que promettre de l'attention.
 *
 *   **Ce que `<details>` ne fait PAS, et il faut le dire** : il ne se ferme pas
 *   sur `Escape`. Le panneau se referme en reactivant son resume, ou en naviguant
 *   -- le changement de route demonte la barre. Ce n'est pas une modale : rien
 *   n'est piege derriere, et le reste de la page reste atteignable.
 *
 * LES DEUX BARRES NE COEXISTENT JAMAIS
 *
 *   Le §8.2 dit « SUR MOBILE » : la feuille cache le menu du haut sous 768 px et
 *   la barre au-dela. Deux reperes de navigation visibles en meme temps
 *   donneraient deux fois les memes liens dans l'ordre de tabulation.
 */
import type { JSX } from 'react';
import { NavLink } from 'react-router';

import { cheminDeRubrique, RUBRIQUES } from '../routes';

export interface ProprietesBarre {
  readonly code: string;
  /** Voir `NavigationPrincipale` : faux par defaut, aucune source avant le LOT 7. */
  readonly aUnParcoursActif?: boolean;
  /** Voir `NavigationPrincipale` : faux par defaut, aucune source avant `T9`. */
  readonly peutAdministrer?: boolean;
}

/**
 * Le nombre de cellules que 320 px acceptent, MESURE.
 *
 * Il n'est pas la pour etre lu par le code -- la barre porte les rubriques
 * inconditionnelles, quel que soit leur nombre -- mais pour que `cadre-check`
 * puisse **exiger** que ce nombre ne soit jamais depasse. Le jour ou une rubrique
 * inconditionnelle serait ajoutee, le controle le dira.
 */
export const CELLULES_MAXIMUM_A_320 = 4;

export function BarreMobile({
  code,
  aUnParcoursActif = false,
  peutAdministrer = false,
}: ProprietesBarre): JSX.Element {
  const principales = RUBRIQUES.filter((rubrique) => rubrique.condition === undefined);
  const secondaires = RUBRIQUES.filter((rubrique) => {
    if (rubrique.cle === 'monOnboarding') {
      return aUnParcoursActif;
    }
    if (rubrique.cle === 'administration') {
      return peutAdministrer;
    }
    return false;
  });

  return (
    //  `aria-label` distinct de celui du menu principal : deux reperes de
    //  navigation sans nom seraient indistinguables pour un lecteur d'ecran, et
    //  `T4` avait nomme le premier precisement en prevision de celui-ci.
    <nav className="app-barre" aria-label="Barre de navigation">
      <ul className="app-barre-liste">
        {principales.map((rubrique) => (
          <li className="app-barre-cellule" key={rubrique.cle}>
            <NavLink
              className="app-barre-lien"
              to={cheminDeRubrique(code, rubrique.suffixe)}
              end={rubrique.suffixe === ''}
            >
              {rubrique.libelle}
            </NavLink>
          </li>
        ))}
        {secondaires.length === 0 ? null : (
          <li className="app-barre-cellule" key="plus">
            {/*
              **« PLUS » N'APPARAIT QUE S'IL A QUELQUE CHOSE A CONTENIR.** C'est
              la lecture mesuree de « lorsque necessaire » du §8.2 : avec six
              cellules a 320 px, « Mon onboarding » passerait sur TROIS lignes.
            */}
            <details className="app-barre-plus">
              <summary className="app-barre-lien">Plus</summary>
              <ul className="app-barre-panneau">
                {secondaires.map((rubrique) => (
                  <li key={rubrique.cle}>
                    <NavLink
                      className="app-barre-lien-secondaire"
                      to={cheminDeRubrique(code, rubrique.suffixe)}
                    >
                      {rubrique.libelle}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </details>
          </li>
        )}
      </ul>
    </nav>
  );
}
