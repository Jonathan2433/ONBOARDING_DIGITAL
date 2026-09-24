/**
 * Editer la page de contenu d'un bureau — LOT 6, `T10`, `MVP-L06-US004` (3/3).
 *
 * MEME RAISONNEMENT QUE `PageEditionDeCercle.tsx` : le bureau est lu D'ABORD
 * pour obtenir son `identifiant`, seul moyen de distinguer sa page de contenu
 * de celle d'un autre bureau dans la liste de gestion (`office_id`).
 */
import type { JSX } from 'react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import { lireLeBureau } from '../api/organisation';
import { cheminDeRubrique } from '../routes';
import { useEntiteConsultee } from './CadreApplicatif';
import { PanneauEditionDeContenu } from './PanneauEditionDeContenu';

import { Alerte } from '@onboarding/ui';

type Etat =
  | { readonly phase: 'chargement' }
  | { readonly phase: 'trouve'; readonly identifiant: string; readonly nom: string }
  | { readonly phase: 'erreur'; readonly statut: number };

export function PageEditionDeBureau(): JSX.Element {
  const { entite, permissions } = useEntiteConsultee();
  const { codeBureau } = useParams<{ codeBureau: string }>();
  const [etat, setEtat] = useState<Etat>({ phase: 'chargement' });
  const roles = permissions?.roles ?? null;

  useEffect(() => {
    if (codeBureau === undefined) {
      return undefined;
    }
    const abandon = new AbortController();
    void lireLeBureau(entite.code, codeBureau, abandon.signal).then(
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
  }, [entite.code, codeBureau]);

  const retour = (
    <p>
      <Link className="app-lien" to={cheminDeRubrique(entite.code, 'framework')}>
        Retour au Framework
      </Link>
    </p>
  );

  if (etat.phase === 'chargement') {
    return <Alerte urgence="information">Chargement du bureau…</Alerte>;
  }
  if (etat.phase === 'erreur' || codeBureau === undefined) {
    return (
      <>
        <Alerte
          ton={etat.phase === 'erreur' && etat.statut === 401 ? 'avertissement' : 'erreur'}
          urgence="alerte"
        >
          {etat.phase === 'erreur' && etat.statut === 401
            ? 'Votre session a expire. Reconnectez-vous pour editer ce bureau.'
            : "Ce bureau n'a pas pu etre charge."}
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
          page.typeDePage === 'OFFICE' && page.officeId === etat.identifiant
        }
        codeEntite={entite.code}
        demandeDeCreation={{
          type_de_page: 'OFFICE',
          titre: etat.nom,
          slug: codeBureau.toLowerCase(),
          bureau: codeBureau,
        }}
        roles={roles}
      />
      {retour}
    </>
  );
}
