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
 * SON CONTENU RESTE MINCE, ET DEUX SECTIONS DE MOINS SONT EN FAUX — `T10`
 *
 *   Le §8.4 du cahier donne l'ordre des sections de l'accueil : presentation
 *   locale, Framework, personnes recemment arrivees, evenements, liens
 *   internes. `T10` ecrit l'EDITION de la presentation (une page `HOME`,
 *   §13 « Creer un contenu general ») et branche le lien vers la gestion des
 *   liens internes. **Le RENDU de ces sections dans l'accueil n'est pas fait**
 *   -- aucun ecran ne consommait encore `pageDeContenu`/`liens.ts` en LECTURE
 *   ici, et l'assembler appartient a une sous-etape que le decoupage de `T3` a
 *   `T9` n'a jamais nommee. Framework a son propre ecran depuis `T9`
 *   (`/framework`) ; arrivees recentes et evenements restent LOTS 7 et 8.
 */
import type { JSX } from 'react';
import { Link } from 'react-router';

import { CHEMINS, cheminDeRubrique, cheminGestionDesLiensALEcran } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';
import { PanneauEditionDeContenu } from './PanneauEditionDeContenu';

import { Alerte } from '@onboarding/ui';

export function PageEntite(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const roles = permissions?.roles ?? null;

  return (
    <>
      <Alerte data-code-entite={entite.code}>
        Vous consultez {entite.nom}. Le choix vit dans l&rsquo;adresse : il survit a un
        rechargement, et un lien partage ouvre la meme entite.
      </Alerte>
      <Alerte>
        Framework, arrivees recentes et evenements arrivent progressivement — voyez{' '}
        <Link className="app-lien" to={cheminDeRubrique(entite.code, 'framework')}>
          la page Framework
        </Link>{' '}
        des maintenant.
      </Alerte>

      <section>
        <h3>Presentation de l&rsquo;entite</h3>
        <PanneauEditionDeContenu
          cibleCorrespond={(page) => page.typeDePage === 'HOME' && page.slug === 'presentation'}
          codeEntite={entite.code}
          demandeDeCreation={{ type_de_page: 'HOME', titre: entite.nom, slug: 'presentation' }}
          roles={roles}
        />
      </section>

      <p>
        <Link className="app-lien" to={cheminGestionDesLiensALEcran(entite.code)}>
          Gerer les liens internes
        </Link>
      </p>

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
