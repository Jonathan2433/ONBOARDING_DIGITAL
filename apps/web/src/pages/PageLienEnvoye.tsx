/**
 * Ecran 2 sur 8 — confirmation de demande de lien. LOT 3, `T11`.
 *
 * POURQUOI CET ECRAN EXISTE ALORS QUE `PageConnexion` CONFIRME DEJA
 *
 *   Le corpus l'enumere separement, et il a une raison : un utilisateur qui
 *   rafraichit apres avoir demande un lien ne doit pas reposter le formulaire.
 *   Cette page est l'adresse **stable** de la confirmation, atteignable au
 *   rechargement.
 *
 * ELLE NE DIT RIEN DE L'ADRESSE, ET C'EST LE MEME CRITERE
 *
 *   Aucun parametre, aucune adresse affichee. Porter l'adresse dans l'URL la
 *   mettrait dans l'historique du navigateur et dans tout journal d'acces -- meme
 *   motif que le jeton de `T4` -- et surtout, une page qui afficherait
 *   « lien envoye a jean@exemple.fr » confirmerait a un attaquant qu'il a saisi
 *   une adresse existante.
 */
import type { JSX } from 'react';
import { Link } from 'react-router';

import { CHEMINS } from '../routes';
import { Cadre } from './Cadre';

export function PageLienEnvoye(): JSX.Element {
  return (
    <Cadre
      titre="Verifiez votre messagerie"
      introduction="Si cette adresse correspond a un profil actif et autorise, un lien de connexion vient d'y etre envoye. Il est valable 15 minutes."
    >
      <p className="auth-message" data-ton="succes">
        Le lien ne peut servir qu&rsquo;une seule fois. Si vous en demandez un nouveau, le precedent
        cesse immediatement de fonctionner.
      </p>
      <ul className="auth-liens">
        <li>
          <Link className="auth-lien" to={CHEMINS.connexion}>
            Demander un autre lien
          </Link>
        </li>
      </ul>
    </Cadre>
  );
}
