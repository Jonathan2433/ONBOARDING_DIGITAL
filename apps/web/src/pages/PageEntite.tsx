/**
 * L'accueil d'une entite — LOT 4, `T2` puis `T3`.
 *
 * ELLE NE RESOUT PLUS L'ENTITE, ET C'EST LE SENS DE `T3`
 *
 *   `T2` faisait resoudre l'entite par cette page. `T3` la fait resoudre par
 *   `CadreApplicatif`, qui la porte dans l'en-tete de **toutes** les pages
 *   internes -- ce que le cahier §23.3 exige. Deux resolutions auraient pu
 *   afficher deux entites differentes le temps d'un rendu, et surtout la page
 *   aurait porte une responsabilite que le cadre tient mieux.
 *
 * ELLE NE PORTE NI `<h1>` NI EN-TETE
 *
 *   Le cadre en porte un seul, une fois. Une page qui ajouterait son propre
 *   titre de niveau 1 donnerait deux `<h1>` au document, ce que `jsx-a11y` ne
 *   verifie pas -- c'est une regle de document, pas de JSX -- et qui ferait
 *   perdre son repere a un lecteur d'ecran sans que rien n'echoue. Meme motif
 *   que `Cadre` pour les huit ecrans d'authentification.
 *
 * SON CONTENU EST DELIBEREMENT MINCE
 *
 *   Le §8.4 du cahier donne l'ordre des sections de l'accueil d'une entite --
 *   presentation locale, Framework, personnes recemment arrivees, evenements,
 *   cartes -- et **tout cela appartient aux LOTS 5, 6 et 7**. Les poser ici en
 *   faux serait livrer des ecrans que rien n'alimente.
 */
import type { JSX } from 'react';
import { Link } from 'react-router';

import { CHEMINS } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';

import { Alerte } from '@onboarding/ui';

export function PageEntite(): JSX.Element {
  const { entite } = useEntiteConsultee();

  return (
    <>
      <Alerte data-code-entite={entite.code}>
        Vous consultez {entite.nom}. Le choix vit dans l&rsquo;adresse : il survit a un
        rechargement, et un lien partage ouvre la meme entite.
      </Alerte>
      <Alerte>
        Les sections de l&rsquo;accueil — presentation, Framework, arrivees recentes et evenements —
        arrivent aux LOTS 5 a 7. La navigation principale arrive a la sous-etape suivante.
      </Alerte>
      <ul className="app-liens">
        <li>
          <Link className="app-lien" to={CHEMINS.statut}>
            Revenir a la liste des entites
          </Link>
        </li>
      </ul>
    </>
  );
}
