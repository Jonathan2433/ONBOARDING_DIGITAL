/**
 * La fiche profil a l'ecran — la route existe, son contenu est `T11`.
 *
 * POURQUOI CETTE PAGE PLUTOT QU'UN LIEN QUI TOMBE EN 404
 *
 *   « "Voir plus" ouvre le profil » est un critere de `US003`, donc de `T10`. Le
 *   lien doit donc MENER quelque part des maintenant. Un lien qui aboutit au
 *   fourre-tout 404 est atteignable et **inutile** : la navigation ne serait pas
 *   prouvee, elle serait simulee.
 *
 *   C'est exactement le motif de `PageRubrique`, pose au `T4` du LOT 4, et cette
 *   page en reprend la discipline : elle **dit quel lot** apportera le contenu,
 *   ce qui est une information vraie et utile, plutot qu'un ecran vide qui
 *   laisserait croire a une panne.
 *
 * ELLE NE CHARGE RIEN, ET C'EST LA LIMITE D'UNE SOUS-ETAPE
 *
 *   La route `GET .../people/{appartenance}` existe depuis `T4`, et cette page
 *   pourrait l'appeler. Elle ne le fait pas : `T11` est « la page de profil a
 *   l'ecran », et la faire ici prendrait sa substance. Une sous-etape a la fois.
 *
 *   **L'identifiant est neanmoins affiche**, parce qu'il est ce que la page a de
 *   vrai a montrer et qu'il rend le lien verifiable a l'oeil : on voit qu'on a
 *   suivi le bon collaborateur.
 */
import type { JSX } from 'react';
import { Link, useParams } from 'react-router';

import { cheminDeRubrique } from '../routes';

import { Alerte } from '@onboarding/ui';

export function PageProfilAVenir(): JSX.Element {
  const { code, appartenance } = useParams<{ code: string; appartenance: string }>();

  return (
    <section className="trombi-profil-a-venir">
      <Alerte urgence="information">
        La fiche complete de ce collaborateur arrive avec la sous-etape <strong>`T11`</strong> du
        LOT 5. Les donnees existent deja cote API depuis <strong>`T4`</strong> ; c&rsquo;est
        l&rsquo;ecran qui reste a faire.
      </Alerte>
      <p className="trombi-identifiant">
        Collaborateur : <code>{appartenance ?? 'inconnu'}</code>
      </p>
      {code === undefined ? null : (
        <p>
          <Link className="app-lien" to={cheminDeRubrique(code, 'trombinoscope')}>
            Retour au trombinoscope
          </Link>
        </p>
      )}
    </section>
  );
}
