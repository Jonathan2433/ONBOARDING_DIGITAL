/**
 * Ecrans 6, 7 et 8 sur 8 — pages `403`, `404` et erreur generale. LOT 3, `T11`.
 *
 * TROIS ECRANS DANS UN FICHIER, ET C'EST DELIBERE
 *
 *   Le corpus les enumere dans **une seule puce** — « pages `403`, `404` et erreur
 *   generale » — parce qu'ils partagent leur forme : un titre, une explication, un
 *   chemin de retour. Trois fichiers de vingt lignes quasi identiques divergeraient
 *   au premier changement de formulation, et c'est le §7.27 applique a du JSX.
 *
 *   Ils restent **trois ecrans** dans le compte des huit : `routes.ts` les declare
 *   separement, et le test qui relit le cahier les compte separement.
 *
 * AUCUN DES TROIS NE DIT CE QUI A ECHOUE, ET C'EST UNE REGLE DE SECURITE
 *
 *   Le §17.4 du cahier veut un echec **bruyant** cote exploitation et **discret**
 *   cote interface. Un `403` qui dirait « il vous manque le scope people:read »
 *   renseignerait un attaquant sur la structure des droits ; un `404` qui dirait
 *   « cette entite existe mais vous n'y avez pas acces » serait un oracle
 *   d'existence — exactement ce que le §2.5 interdit.
 *
 *   L'identifiant de correlation est **la** chose utile a montrer : il permet a
 *   Jonathan de retrouver la trace complete dans les journaux, sans que la page
 *   n'en revele rien.
 */
import type { JSX } from 'react';
import { Link } from 'react-router';

import { CHEMINS } from '../routes';
import { BoutonSignalerUnBug } from './BoutonSignalerUnBug';
import { Cadre } from './Cadre';

interface ProprietesEcranDErreur {
  readonly titre: string;
  readonly explication: string;
  /** Identifiant de correlation a afficher, quand l'API en a rendu un. */
  readonly correlation?: string;
}

function EcranDErreur({ titre, explication, correlation }: ProprietesEcranDErreur): JSX.Element {
  return (
    <Cadre titre={titre}>
      <p className="auth-message" data-ton="refus">
        {explication}
      </p>
      {correlation === undefined ? null : (
        <p className="auth-aide">
          Identifiant a communiquer en cas de demande d&rsquo;assistance :{' '}
          <code>{correlation}</code>
        </p>
      )}
      <ul className="auth-liens">
        <li>
          <Link className="auth-lien" to={CHEMINS.statut}>
            Retour a l&rsquo;accueil
          </Link>
        </li>
        <li>
          <Link className="auth-lien" to={CHEMINS.connexion}>
            Se connecter
          </Link>
        </li>
      </ul>
      {/*
        **CAHIER §10.12 : « pied de page, pages d'erreur, menu mobile ».**
        Les trois écrans de ce fichier SONT les « pages d'erreur » du cahier —
        voir la démonstration citée au §9.6, « création d'un signalement
        depuis une page d'erreur ». Aucune entité n'est dans le contexte ici :
        voir l'en-tête d'`app/support/routes.py` pour la résolution côté API.
      */}
      <BoutonSignalerUnBug />
    </Cadre>
  );
}

export function Page403(): JSX.Element {
  return (
    <EcranDErreur
      titre="Acces refuse"
      explication="Vous n'avez pas les droits necessaires pour cette page. Si vous pensez que c'est une erreur, contactez votre administrateur d'entite."
    />
  );
}

export function Page404(): JSX.Element {
  return (
    <EcranDErreur
      titre="Page introuvable"
      explication="Cette adresse ne correspond a aucune page. Le lien que vous avez suivi est peut-etre incomplet ou perime."
    />
  );
}

export interface ProprietesPageErreur {
  readonly correlation?: string;
}

export function PageErreur({ correlation }: ProprietesPageErreur = {}): JSX.Element {
  return (
    <EcranDErreur
      titre="Une erreur est survenue"
      explication="Le service n'a pas pu traiter votre demande. Reessayez dans un instant ; si le probleme persiste, signalez-le."
      {...(correlation === undefined ? {} : { correlation })}
    />
  );
}
