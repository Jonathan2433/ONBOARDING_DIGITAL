/**
 * Ecran 4 sur 8 — connexion administrateur. LOT 3, `T11`, story `US003`.
 *
 * UN SEUL GABARIT DE REFUS POUR CINQ CAUSES, ET L'ECRAN NE DOIT PAS L'AFFAIBLIR
 *
 *   L'API rend `400` pour un compte inconnu, un mot de passe faux, un compte
 *   verrouille, desactive, ou sans mot de passe actif -- `T5`. Un ecran qui
 *   distinguerait ces cas revelerait qu'une adresse porte un compte
 *   administrateur, et -- pire -- apprendrait a un attaquant qu'il a **reussi a
 *   verrouiller** le titulaire.
 *
 * LE 429 EST DISTINGUE DU 400, MAIS SANS DIRE POURQUOI
 *
 *   `T8` limite a cinq echecs par adresse en quinze minutes. Afficher « trop de
 *   tentatives » plutot que « identifiants refuses » est utile a l'utilisateur
 *   legitime et n'apprend rien : la limite s'applique a **toute** adresse, connue
 *   ou non, ce qui est precisement ce qui l'empeche d'etre un oracle.
 *
 * `autoComplete="current-password"` ET `type="password"`
 *
 *   Le premier laisse le gestionnaire de mots de passe faire son travail -- ce qui
 *   est une mesure de securite, pas un confort. Le second empeche l'affichage en
 *   clair.
 */
import { useState, type FormEvent, type JSX } from 'react';
import { Bouton } from '@onboarding/ui';

import { connecterUnAdministrateur } from '../api/auth';
import { Cadre } from './Cadre';

type Etat = 'saisie' | 'envoi' | 'connecte' | 'refuse' | 'limite' | 'indisponible';

const MESSAGE_REFUS = 'Identifiants refuses.';
const MESSAGE_LIMITE =
  'Trop de tentatives ont ete faites recemment. Patientez quelques minutes avant ' +
  'de recommencer.';
const MESSAGE_INDISPONIBLE = "Le service n'a pas pu traiter la demande. Reessayez dans un instant.";

export function PageConnexionAdministrateur(): JSX.Element {
  const [email, setEmail] = useState('');
  const [motDePasse, setMotDePasse] = useState('');
  const [etat, setEtat] = useState<Etat>('saisie');

  async function soumettre(evenement: FormEvent<HTMLFormElement>): Promise<void> {
    evenement.preventDefault();
    setEtat('envoi');
    try {
      const reponse = await connecterUnAdministrateur(email, motDePasse);
      if (reponse.statut === 200) {
        setEtat('connecte');
      } else if (reponse.statut === 429 || reponse.statut === 503) {
        setEtat('limite');
      } else {
        setEtat('refuse');
      }
    } catch {
      //  **UNE PANNE RESEAU N'EST PAS UN REFUS D'IDENTIFIANTS.** Les confondre
      //  ferait douter un administrateur de son mot de passe alors que le service
      //  ne repond pas -- et c'est le §7.6 : ne masque pas une cause que tu vas
      //  interpreter.
      setEtat('indisponible');
    }
    //  **LE MOT DE PASSE EST EFFACE DANS TOUS LES CAS**, succes compris : le
    //  laisser en memoire de composant le laisserait dans un instantane React
    //  DevTools, et dans tout rapport d'erreur qui capturerait l'etat.
    setMotDePasse('');
  }

  const MESSAGES: Partial<Record<Etat, string>> = {
    refuse: MESSAGE_REFUS,
    limite: MESSAGE_LIMITE,
    indisponible: MESSAGE_INDISPONIBLE,
    connecte: 'Identifiants acceptes. Votre session est ouverte.',
  };
  const message = MESSAGES[etat] ?? '';

  return (
    <Cadre
      titre="Connexion administrateur"
      introduction="Reserve aux comptes administrateurs locaux. Les autres profils passent par un lien de connexion."
    >
      <form
        className="auth-formulaire"
        onSubmit={(evenement) => {
          void soumettre(evenement);
        }}
        noValidate
      >
        <div className="auth-champ">
          <label className="auth-etiquette" htmlFor="admin-email">
            Adresse e-mail
          </label>
          <input
            className="auth-saisie"
            id="admin-email"
            name="email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(evenement) => setEmail(evenement.target.value)}
          />
        </div>
        <div className="auth-champ">
          <label className="auth-etiquette" htmlFor="admin-mot-de-passe">
            Mot de passe
          </label>
          <input
            className="auth-saisie"
            id="admin-mot-de-passe"
            name="mot_de_passe"
            type="password"
            autoComplete="current-password"
            required
            value={motDePasse}
            onChange={(evenement) => setMotDePasse(evenement.target.value)}
          />
        </div>
        <Bouton
          type="submit"
          variante="primaire"
          disabled={etat === 'envoi' || email === '' || motDePasse === ''}
        >
          {etat === 'envoi' ? 'Verification…' : 'Se connecter'}
        </Bouton>
      </form>

      <p
        className="auth-message"
        data-ton={etat === 'connecte' ? 'succes' : etat === 'saisie' ? undefined : 'refus'}
        role="status"
        aria-live="polite"
      >
        {message}
      </p>
    </Cadre>
  );
}
