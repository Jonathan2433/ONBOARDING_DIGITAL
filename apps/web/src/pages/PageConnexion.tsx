/**
 * Ecran 1 sur 8 — page de connexion. LOT 3, `T11`, story `MVP-L03-US001`.
 *
 * LA REPONSE EST GENERIQUE, ET L'ECRAN NE DOIT PAS LA DEFAIRE
 *
 *   L'API rend **le meme 202, le meme corps et les memes en-tetes** que l'adresse
 *   existe ou non -- c'est le critere central du lot, et `T3` l'a obtenu en
 *   n'ayant qu'un seul chemin de code. **Un ecran qui afficherait deux messages
 *   differents rouvrirait l'oracle cote interface.**
 *
 *   Le message affiche vient donc de la reponse, et cette page ne construit
 *   AUCUNE phrase qui dependrait de l'adresse saisie.
 *
 * AUCUNE VALIDATION DE FORME SUR L'ADRESSE, ET C'EST DELIBERE
 *
 *   Meme motif que l'API en `T3` : une adresse jugee mal formee produirait un
 *   message different, et un attaquant y lirait « cette adresse a une forme
 *   acceptable » puis « cette adresse existe ». Le champ est `type="email"` --
 *   l'aide native du navigateur, qui ne dit rien de la base -- et rien de plus.
 *
 * LES DEUX REFUS QUE L'API PEUT RENDRE SONT TRAITES, ET DISTINGUES DU SUCCES
 *
 *   `429` (limitation de debit, `T8`) et `503` (compteur injoignable) ne sont pas
 *   des succes : les afficher comme tels ferait croire a l'utilisateur qu'un lien
 *   arrive. Ils portent le meme gabarit de message pour ne rien reveler de la
 *   dimension depassee, et `details.secondes_avant_reprise` dit quand reessayer.
 */
import { useState, type FormEvent, type JSX } from 'react';
import { Bouton } from '@onboarding/ui';

import { demanderUnLien } from '../api/auth';
import { Cadre } from './Cadre';

type Etat = 'saisie' | 'envoi' | 'confirme' | 'refuse';

const MESSAGE_REFUS =
  'Trop de demandes ont ete faites recemment, ou le service est momentanement ' +
  'indisponible. Patientez quelques minutes avant de recommencer.';

const MESSAGE_INDISPONIBLE = "Le service n'a pas pu traiter la demande. Reessayez dans un instant.";

export function PageConnexion(): JSX.Element {
  const [email, setEmail] = useState('');
  const [etat, setEtat] = useState<Etat>('saisie');
  const [message, setMessage] = useState('');

  async function soumettre(evenement: FormEvent<HTMLFormElement>): Promise<void> {
    evenement.preventDefault();
    setEtat('envoi');
    try {
      const reponse = await demanderUnLien(email);
      if (reponse.statut === 202) {
        //  LE MESSAGE VIENT DE L'API. Le fabriquer ici rouvrirait l'oracle : le
        //  serveur rend une seule phrase, connue ou non.
        setMessage(reponse.corps?.message ?? '');
        setEtat('confirme');
      } else {
        setMessage(MESSAGE_REFUS);
        setEtat('refuse');
      }
    } catch {
      //  Une panne reseau n'est pas un refus, et la confondre avec un 429
      //  suggererait a l'utilisateur qu'il a trop insiste.
      setMessage(MESSAGE_INDISPONIBLE);
      setEtat('refuse');
    }
  }

  return (
    <Cadre
      titre="Se connecter"
      introduction="Saisissez votre adresse professionnelle. Un lien de connexion valable 15 minutes vous sera envoye."
    >
      <form
        className="auth-formulaire"
        onSubmit={(evenement) => {
          void soumettre(evenement);
        }}
        noValidate
      >
        <div className="auth-champ">
          <label className="auth-etiquette" htmlFor="email">
            Adresse e-mail
          </label>
          <input
            className="auth-saisie"
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            aria-describedby="email-aide"
            onChange={(evenement) => setEmail(evenement.target.value)}
          />
          <p className="auth-aide" id="email-aide">
            La reponse est la meme quelle que soit l&rsquo;adresse saisie.
          </p>
        </div>
        <Bouton type="submit" variante="primaire" disabled={etat === 'envoi' || email === ''}>
          {etat === 'envoi' ? 'Envoi en cours…' : 'Recevoir un lien'}
        </Bouton>
      </form>

      {/*
        `aria-live="polite"` : sans lui, la confirmation apparait sans etre
        annoncee, et c'est precisement le seul retour que cette page donne.
      */}
      <p
        className="auth-message"
        data-ton={etat === 'confirme' ? 'succes' : etat === 'refuse' ? 'refus' : undefined}
        role="status"
        aria-live="polite"
      >
        {message}
      </p>
    </Cadre>
  );
}
