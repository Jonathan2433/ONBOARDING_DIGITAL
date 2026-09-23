/**
 * La page detaillee d'un cercle, a l'ecran — LOT 6, `T9`, story `MVP-L06-US002`.
 *
 * LE CRITERE, MOT POUR MOT
 *
 *   « Couleur, description, membres et Booster sont affiches sans reposer
 *   uniquement sur la couleur. »
 *
 * LA COULEUR N'EST JAMAIS LA SEULE INFORMATION, ET C'EST LE COUPLE DU §7.42
 *
 *   `jetonDeCouleur` est nullable au contrat (`circle.color_token`, modele §8.1).
 *   Un cercle sans jeton reste parfaitement lisible : le nom est un `<h2>` en
 *   texte, la couleur ne fait que teinter une bordure. `couleurDuCercle` rend
 *   `undefined` pour un jeton nul OU inconnu, et les deux cas laissent la
 *   bordure neutre — jamais la chaine « None », defaut `T10-8`.
 *
 * LA PAGINATION SUIT LE §18.2, ET LE PARAMETRE VIT EN ETAT LOCAL
 *
 *   Comme le trombinoscope de `T10` du LOT 5 : la page courante n'est pas dans
 *   l'adresse, elle est dans l'etat du composant. Changer de page ne change pas
 *   l'URL de la ressource consultee — un cercle a une seule adresse d'ecran.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import { couleurDuCercle } from '../affichage';
import { lireLeCercle } from '../api/organisation';
import { cheminDeRubrique } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';

import { TAILLE_PAR_DEFAUT, type PageDuCercle } from '@onboarding/contracts';
import { Alerte } from '@onboarding/ui';

const TAILLE = TAILLE_PAR_DEFAUT;

/** « Principal » ou « Secondaire » — §8.2, la distinction porte des droits (`ARB-DROIT-004`). */
function libelleDAppartenance(type: string): string {
  return type === 'principal' ? 'Principal' : 'Secondaire';
}

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'page'; readonly page: PageDuCercle }
  | { readonly phase: 'erreur'; readonly statut: number };

export function PageCercle(): JSX.Element {
  const { entite } = useEntiteConsultee();
  const { codeCercle } = useParams<{ codeCercle: string }>();
  const [page, setPage] = useState(1);
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });

  useEffect(() => {
    if (codeCercle === undefined) {
      return undefined;
    }
    const abandon = new AbortController();
    void lireLeCercle(entite.code, codeCercle, page, TAILLE, abandon.signal).then(
      (reponse) => {
        setEtat(
          reponse.statut === 200 && reponse.corps !== null
            ? { phase: 'page', page: reponse.corps }
            : { phase: 'erreur', statut: reponse.statut },
        );
      },
      (cause: unknown) => {
        if (!abandon.signal.aborted) {
          setEtat({ phase: 'erreur', statut: 0 });
        }
        return cause;
      },
    );
    return () => {
      abandon.abort();
    };
  }, [entite.code, codeCercle, page]);

  const retour = (
    <p className="cercle-retour">
      <Link className="app-lien" to={cheminDeRubrique(entite.code, 'framework')}>
        Retour au Framework
      </Link>
    </p>
  );

  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement du cercle…</Alerte>;
  }

  if (etat.phase === 'erreur') {
    return (
      <>
        <Alerte ton={etat.statut === 401 ? 'avertissement' : 'erreur'} urgence="alerte">
          {etat.statut === 401
            ? 'Votre session a expire. Reconnectez-vous pour consulter ce cercle.'
            : etat.statut === 404
              ? "Ce cercle est introuvable, ou n'est plus actif."
              : "Le cercle n'a pas pu etre charge. Reessayez dans un instant."}
        </Alerte>
        {retour}
      </>
    );
  }

  const c = etat.page;
  const couleur = couleurDuCercle(c.jetonDeCouleur);

  return (
    <article
      className="cercle"
      style={couleur === undefined ? undefined : ({ '--cercle-couleur': couleur } as never)}
    >
      <header className="cercle-entete">
        <h2 className="cercle-nom">{c.nom}</h2>
        {c.description === null ? null : <p className="cercle-description">{c.description}</p>}
      </header>

      <dl className="cercle-champs">
        <dt>Booster</dt>
        <dd>{c.booster === null ? 'Aucun Booster' : `${c.booster.prenom} ${c.booster.nom}`}</dd>
      </dl>

      <section className="cercle-membres">
        <h3>Membres ({c.totalDesMembres})</h3>
        {c.membres.length === 0 ? (
          <Alerte>Aucun membre pour le moment.</Alerte>
        ) : (
          <ul className="cercle-liste-membres">
            {c.membres.map((membre) => (
              <li key={membre.appartenance}>
                <span className="cercle-membre-nom">
                  {membre.prenom} {membre.nom}
                </span>
                <span className="cercle-membre-type">
                  {libelleDAppartenance(membre.typeDAppartenance)}
                </span>
              </li>
            ))}
          </ul>
        )}

        {c.pages > 1 ? (
          <nav aria-label="Pagination des membres du cercle" className="cercle-pagination">
            <button
              type="button"
              className="cercle-page"
              disabled={c.page <= 1}
              onClick={() => {
                setPage((precedente) => Math.max(1, precedente - 1));
              }}
            >
              Page precedente
            </button>
            <span className="cercle-position">
              Page {c.page} sur {c.pages}
            </span>
            <button
              type="button"
              className="cercle-page"
              disabled={c.page >= c.pages}
              onClick={() => {
                setPage((precedente) => precedente + 1);
              }}
            >
              Page suivante
            </button>
          </nav>
        ) : null}
      </section>

      {retour}
    </article>
  );
}
