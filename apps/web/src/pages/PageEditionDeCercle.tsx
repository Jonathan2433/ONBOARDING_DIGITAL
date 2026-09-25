/**
 * Editer la page de contenu d'un cercle — LOT 6, `T10`, `MVP-L06-US004` (3/3).
 *
 * LE CERCLE EST D'ABORD LU, ET C'EST CE QUI DONNE `circleId`
 *
 *   La liste de gestion des pages porte `circle_id`, pas le `code` du cercle :
 *   il faut donc l'IDENTIFIANT du cercle pour trouver sa page, exactement
 *   comme `T3` l'a expose sous `identifiant` dans `PageDuCercle`. Sans cette
 *   lecture prealable, aucun filtre ne pourrait distinguer la page de CE
 *   cercle de celle d'un autre.
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import { lireLeCercle } from '../api/organisation';
import { cheminDeRubrique } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';
import { PanneauEditionDeContenu } from './PanneauEditionDeContenu';

import { TAILLE_PAR_DEFAUT } from '@onboarding/contracts';
import { Alerte } from '@onboarding/ui';

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'trouve'; readonly identifiant: string; readonly nom: string }
  | { readonly phase: 'erreur'; readonly statut: number };

export function PageEditionDeCercle(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const { codeCercle } = useParams<{ codeCercle: string }>();
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });
  const roles = permissions?.roles ?? null;

  useEffect(() => {
    if (codeCercle === undefined) {
      return undefined;
    }
    const abandon = new AbortController();
    void lireLeCercle(entite.code, codeCercle, 1, TAILLE_PAR_DEFAUT, abandon.signal).then(
      (reponse) => {
        if (abandon.signal.aborted) {
          return;
        }
        setEtat(
          reponse.statut === 200 && reponse.corps !== null
            ? { phase: 'trouve', identifiant: reponse.corps.identifiant, nom: reponse.corps.nom }
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
  }, [entite.code, codeCercle]);

  const retour = (
    <p>
      <Link className="app-lien" to={cheminDeRubrique(entite.code, 'framework')}>
        Retour au Framework
      </Link>
    </p>
  );

  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement du cercle…</Alerte>;
  }
  if (etat.phase === 'erreur' || codeCercle === undefined) {
    return (
      <>
        <Alerte
          ton={etat.phase === 'erreur' && etat.statut === 401 ? 'avertissement' : 'erreur'}
          urgence="alerte"
        >
          {etat.phase === 'erreur' && etat.statut === 401
            ? 'Votre session a expire. Reconnectez-vous pour editer ce cercle.'
            : "Ce cercle n'a pas pu etre charge."}
        </Alerte>
        {retour}
      </>
    );
  }

  return (
    <>
      <h2>{etat.nom}</h2>
      <PanneauEditionDeContenu
        cibleCorrespond={(page) =>
          page.typeDePage === 'CIRCLE' && page.circleId === etat.identifiant
        }
        codeEntite={entite.code}
        demandeDeCreation={{
          type_de_page: 'CIRCLE',
          titre: etat.nom,
          slug: codeCercle.toLowerCase(),
          cercle: codeCercle,
        }}
        roles={roles}
      />
      {retour}
    </>
  );
}
