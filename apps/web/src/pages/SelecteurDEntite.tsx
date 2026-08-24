/**
 * Changer d'entite consultee — LOT 4, `T8`, story `MVP-L04-US002`.
 *
 * « Changer d'entite consultee a tout moment. » Le cahier §23.3 et la matrice
 * §23.3 posent cinq regles ; celle-ci en porte la cinquieme -- « doit etre
 * visible dans l'en-tete de l'application » -- et rend la premiere possible.
 *
 * C'EST UNE NAVIGATION, DONC DES LIENS. PAS UN FORMULAIRE, PAS UN `<select>`.
 *
 *   `DEC-545` : l'entite consultee vit dans l'ADRESSE. Changer d'entite est donc
 *   un changement d'URL, et l'element qui change une URL est un `<a>`. Trois
 *   consequences que rien d'autre n'aurait donnees :
 *
 *     - les regles 1 et 2 du §23.3 -- « ne modifie pas l'entite principale »,
 *       « ne transfere pas ses responsabilites » -- sont tenues par construction :
 *       il n'y a AUCUNE ecriture, donc aucun endroit ou l'une des deux pourrait
 *       arriver ;
 *     - le choix survit a un rechargement, et le bouton « precedent » du
 *       navigateur ramene a l'entite d'avant. Un `<select>` avec un `onChange`
 *       aurait exige d'ecrire ces deux comportements ;
 *     - chaque entite a une adresse partageable.
 *
 *   **Un `<select>` aurait aussi ete un piege d'accessibilite** : son `onChange`
 *   se declenche a la FLECHE sur certains navigateurs, donc parcourir la liste au
 *   clavier aurait navigue a chaque touche.
 *
 * `<details>` ET `<summary>`, POUR LA MEME RAISON QU'EN `T5`
 *
 *   Le repli est natif : le navigateur porte l'etat ouvert/ferme, l'annonce, et
 *   gere Entree et Espace. Aucun `aria-expanded` a maintenir, aucune gestion de
 *   focus a ecrire -- et `T3` a mesure ce que coute une gestion de focus qu'on
 *   croit correcte : le lien d'evitement de `T3` ne sautait rien (`ECART-043`).
 *
 * L'ENTITE COURANTE RESTE DANS LA LISTE, ET ELLE EST MARQUEE
 *
 *   La retirer donnerait une liste dont la composition change a chaque
 *   navigation, donc des positions qui bougent sous le curseur. Elle porte
 *   `aria-current="true"` -- l'attribut, non une classe : une classe seule
 *   n'informerait qu'un oeil, et le §14.2 l'interdit.
 *
 * IL NE S'AFFICHE PAS QUAND IL N'Y A RIEN A CHOISIR
 *
 *   Une seule entite active : le replier serait un arret de tabulation pour un
 *   choix inexistant. Meme regle que « Plus » dans la barre mobile (`DEC-548`).
 */
import { type JSX } from 'react';
import { Link } from 'react-router';

import { type EntiteDuPortail } from '@onboarding/contracts';

import { cheminDeLEntite } from '../routes';

/** Le nombre d'entites en dessous duquel le selecteur n'a rien a offrir. */
const ENTITES_MINIMUM = 2;

export function SelecteurDEntite({
  courante,
  entites,
}: {
  readonly courante: EntiteDuPortail;
  readonly entites: readonly EntiteDuPortail[];
}): JSX.Element | null {
  if (entites.length < ENTITES_MINIMUM) {
    return null;
  }

  return (
    <details className="app-selecteur">
      <summary className="app-selecteur-bouton">Changer d&rsquo;entite</summary>
      {/*
        `aria-label` sur le `<nav>` : la page en porte deja deux -- le menu
        principal et la barre mobile -- et deux reperes de meme role sans nom
        distinct sont indistinguables dans la liste des reperes d'un lecteur
        d'ecran. Meme motif qu'en `T4`.
      */}
      <nav className="app-selecteur-liste" aria-label="Entites">
        <ul>
          {entites.map((entite) => {
            const active = entite.code === courante.code;
            return (
              <li key={entite.code}>
                <Link
                  className="app-selecteur-lien"
                  to={cheminDeLEntite(entite.code)}
                  //  `aria-current` prend `true` et non `page` : la cible n'est
                  //  pas la page courante mais l'ENTITE courante -- la rubrique
                  //  consultee, elle, ne change pas. C'est le menu principal qui
                  //  porte `aria-current="page"`.
                  {...(active ? { 'aria-current': 'true' as const } : {})}
                >
                  <span className="app-selecteur-nom">{entite.nom}</span>
                  <span className="app-selecteur-ville">{entite.ville}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </details>
  );
}
